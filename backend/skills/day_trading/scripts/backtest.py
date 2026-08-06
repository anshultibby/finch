"""
Event-driven backtester for the day-trading setups.

The point of this module: answer "does this setup actually have an edge, after
costs?" with evidence, instead of trusting the citation in setups.py. It reuses
the LIVE code verbatim — orb_signal() for the signal, plan_trade()/position_size()
for sizing, and RiskBudget for the daily circuit breaker — so a backtest is a
faithful replay of what the automation would have done, not a parallel
reimplementation that can silently drift from production.

What it does NOT do (known limitations — state them when you report results):
  - Fills are modelled, not real: a resting stop-entry fills at the trigger
    level + slippage_bps; a stop-out fills at the stop − slippage_bps. Gaps
    through the stop are modelled as filling at the bar's open (worse of the
    two), but true queue position / partial fills are not simulated.
  - The historical "stocks in play" universe is reconstructed from Polygon
    grouped daily bars (gap% + volume-vs-prior-day), which is coarser than the
    live first-5-min RVOL scan (that needs intraday history we won't pull for
    the whole market). Treat it as a good proxy, not identical to live.
  - Survivorship / delisting and hard-to-borrow are ignored (long-only here,
    so borrow doesn't bite, but delisted tickers simply won't return data).
  - Point-in-time universe only reflects tickers Polygon returns for that date.

Everything here is a pure function of market data + params. No orders, no journal
writes. Feed a StrategySpec, get a metrics dict + the full trade blotter back.
"""
import time
from dataclasses import dataclass, asdict
from datetime import date, timedelta
from typing import Dict, Any, List, Optional

from skills.polygon_io.scripts.api import polygon
from skills.polygon_io.scripts.market.intraday import get_intraday_bars
from .clock import is_trading_day, rth_only, to_et, close_time
from .indicators import atr
from .setups import orb_signal
from .risk import RiskBudget, plan_trade


# ── strategy spec ────────────────────────────────────────────────────────────
# A "strategy" is data, not code: this spec is what the research loop mutates and
# ranks, and what gets promoted to live once its backtest clears the bar. Keep it
# JSON-serialisable so a validated spec can be stored and handed to execution.

@dataclass
class StrategySpec:
    setup: str = "orb"                 # only "orb" implemented today
    # universe / in-play reconstruction
    min_price: float = 5.0
    max_price: float = 2000.0
    min_day_volume: float = 1_000_000
    min_abs_gap_pct: float = 2.0
    max_abs_gap_pct: float = 30.0      # above this, a "gap" is almost always a
                                       # split / merger / halt — not tradeable
                                       # ORB momentum. Exclude corporate actions.
    top_n: int = 10                    # names traded per day (by rvol proxy)
    # signal params (passed straight to orb_signal)
    or_minutes: int = 5
    stop_atr_mult: float = 0.10
    max_chase_r: float = 0.5
    min_stop_frac: float = 0.002       # reject stops tighter than 0.2% of entry:
                                       # a near-zero stop turns a normal wiggle
                                       # into a many-R loss (and flags bad data)
    # sizing / risk (passed to plan_trade + RiskBudget)
    risk_pct: float = 0.01
    rr: float = 10.0
    max_leverage: float = 4.0
    max_weight: float = 0.25
    max_daily_loss_pct: float = 0.03
    max_consecutive_losses: int = 3
    max_trades_per_day: int = 10
    # cost model
    slippage_bps: float = 5.0          # 5 bps each side (entry and exit)
    commission_per_trade: float = 0.0  # Robinhood equities = $0

    def to_dict(self) -> dict:
        return asdict(self)


# ── data access (with per-symbol daily cache to keep API calls sane) ──────────

_daily_cache: Dict[str, List[dict]] = {}
_PACE_SECONDS = 0.0  # sleep between Polygon calls; raise on throttled tiers


def _pace() -> None:
    if _PACE_SECONDS:
        time.sleep(_PACE_SECONDS)


def _grouped_daily(day: str) -> List[dict]:
    """All-market OHLCV for one date (1 API call). Empty list if unavailable."""
    resp = polygon(f"/v2/aggs/grouped/locale/us/market/stocks/{day}",
                   {"adjusted": "true"})
    _pace()
    return (resp or {}).get("results", []) or []


def _daily_bars(symbol: str, end: str, warmup: int = 40) -> List[dict]:
    """Adjusted daily bars up to and including `end`, cached per symbol.
    Shaped for indicators.atr(): high/low/close/timestamp."""
    key = f"{symbol}:{end}"
    if key in _daily_cache:
        return _daily_cache[key]
    start = (date.fromisoformat(end) - timedelta(days=warmup * 2)).isoformat()
    resp = polygon(f"/v2/aggs/ticker/{symbol.upper()}/range/1/day/{start}/{end}",
                   {"adjusted": "true", "sort": "asc", "limit": 120})
    bars = [{"high": r["h"], "low": r["l"], "close": r["c"], "timestamp": r["t"]}
            for r in (resp or {}).get("results", []) or []]
    _pace()
    _daily_cache[key] = bars
    return bars


def _atr_asof(symbol: str, day: str, period: int = 14) -> Optional[float]:
    """ATR(period) using bars strictly BEFORE `day` (no lookahead)."""
    bars = [b for b in _daily_bars(symbol, day) if to_et(int(b["timestamp"])).date().isoformat() < day]
    return atr(bars, period) if len(bars) > period else None


def _intraday_rth(symbol: str, day: str) -> List[dict]:
    """One ET day of RTH 1-min bars (historical; Polygon serves these fine)."""
    resp = get_intraday_bars(symbol, day, day, "1min")
    _pace()
    if "error" in resp:
        return []
    return rth_only(resp.get("bars", []), date.fromisoformat(day))


# ── historical in-play universe ──────────────────────────────────────────────

def historical_in_play(day: str, spec: StrategySpec) -> List[Dict[str, Any]]:
    """Reconstruct the day's stocks-in-play from grouped daily bars: gappers on
    elevated volume vs the prior session. Coarser than the live first-5-min RVOL
    scan but point-in-time and cheap (2 grouped calls). Returns up to top_n dicts
    sorted by rvol proxy desc."""
    d = date.fromisoformat(day)
    prev = d - timedelta(days=1)
    for _ in range(6):  # walk back over weekends/holidays to the prior session
        if is_trading_day(prev):
            break
        prev -= timedelta(days=1)

    today = {r["T"]: r for r in _grouped_daily(day)}
    yday = {r["T"]: r for r in _grouped_daily(prev.isoformat())}
    out = []
    for sym, t in today.items():
        y = yday.get(sym)
        if not y:
            continue
        price = t.get("c") or 0
        vol, pvol = t.get("v") or 0, y.get("v") or 0
        pclose = y.get("c") or 0
        if not (spec.min_price < price < spec.max_price) or vol < spec.min_day_volume or not pclose:
            continue
        # Require it was ALREADY liquid yesterday — otherwise vol/pvol explodes on
        # fresh IPOs and low-float penny runners (prev_volume ≈ 0), which dominate
        # a raw rvol ranking and are not the "stocks in play" the setup targets.
        if pvol < spec.min_day_volume:
            continue
        gap_pct = 100 * ((t.get("o") or pclose) - pclose) / pclose
        if not (spec.min_abs_gap_pct <= abs(gap_pct) <= spec.max_abs_gap_pct):
            continue
        out.append({"symbol": sym, "price": round(price, 2),
                    "gap_pct": round(gap_pct, 2),
                    "rvol_proxy": round(vol / pvol, 2) if pvol else 0})
    out.sort(key=lambda x: x["rvol_proxy"], reverse=True)
    return out[:spec.top_n]


# ── single-name single-day simulation ────────────────────────────────────────

def simulate_orb_day(symbol: str, day: str, equity: float, spec: StrategySpec
                     ) -> Optional[Dict[str, Any]]:
    """Replay one ORB trade for one symbol on one day. Returns a trade record,
    or None if there was no signal / no fill / zero-share sizing.

    Model: after the opening-range window, a resting stop-entry sits at the OR
    boundary. It fills the first bar that trades through it (gap-through fills at
    that bar's open — the honest, worse price). From the fill bar forward: a
    stop-out fills at the stop, the target (rr·R) fills if touched, otherwise the
    position is flattened at the session close. Long-only (Robinhood can't short)."""
    bars = _intraday_rth(symbol, day)
    if len(bars) < spec.or_minutes + 2:
        return None
    atr14 = _atr_asof(symbol, day)
    sig = orb_signal(bars, atr14, or_minutes=spec.or_minutes,
                     stop_atr_mult=spec.stop_atr_mult, max_chase_r=spec.max_chase_r,
                     long_only=True)
    if sig.get("direction") != "long" or sig.get("entry") is None:
        return None  # short_blocked or no valid range
    entry, stop = sig["entry"], sig["stop"]
    if entry <= stop:
        return None
    # Sanity guards — the OR level is the real tradable price, so re-check the
    # price band here (grouped daily close can disagree with intraday on odd
    # tickers) and floor the stop distance so a data glitch can't book a −6R.
    if not (spec.min_price <= entry <= spec.max_price):
        return None
    if (entry - stop) / entry < spec.min_stop_frac:
        return None

    plan = plan_trade(equity, entry, stop, side="long", risk_pct=spec.risk_pct,
                      rr=spec.rr, max_leverage=spec.max_leverage, max_weight=spec.max_weight)
    shares = plan["shares"]
    if shares <= 0:
        return None
    target = plan["target"]

    window_end = int(bars[0]["timestamp"]) + spec.or_minutes * 60 * 1000
    post = [b for b in bars if int(b["timestamp"]) >= window_end]
    slip = spec.slippage_bps / 10_000.0

    # 1) find the fill
    fill_price = None
    fill_idx = None
    for i, b in enumerate(post):
        if float(b["high"]) >= entry:
            # gap-through → fill at the open if it opened above the trigger
            fill_price = max(float(b["open"]), entry) * (1 + slip)
            fill_idx = i
            break
    if fill_price is None:
        return None  # stop-entry never triggered

    # 2) walk forward to the exit
    exit_price, exit_reason = None, None
    for b in post[fill_idx:]:
        lo, hi = float(b["low"]), float(b["high"])
        if lo <= stop:                       # stop-out (gap-down fills at open)
            exit_price = min(float(b["open"]), stop) * (1 - slip)
            exit_reason = "stop"
            break
        if hi >= target:                     # target hit
            exit_price = target * (1 - slip)
            exit_reason = "target"
            break
    if exit_price is None:                    # flatten at the close
        exit_price = float(post[-1]["close"]) * (1 - slip)
        exit_reason = "eod"

    r_per_share = entry - stop
    pnl = shares * (exit_price - fill_price) - spec.commission_per_trade
    return {
        "day": day, "symbol": symbol, "side": "long",
        "entry": round(fill_price, 4), "stop": round(stop, 4),
        "target": round(target, 4), "exit": round(exit_price, 4),
        "exit_reason": exit_reason, "shares": shares,
        "pnl": round(pnl, 2),
        "r_multiple": round((exit_price - fill_price) / r_per_share, 3) if r_per_share else 0,
        "rvol_proxy": None,  # filled in by caller
    }


# ── the backtest loop ────────────────────────────────────────────────────────

def backtest_orb(start: str, end: str, equity: float = 30_000.0,
                 spec: Optional[StrategySpec] = None, verbose: bool = False,
                 pace_seconds: float = 0.0) -> Dict[str, Any]:
    """Replay the ORB operation day-by-day over [start, end] (ET dates, inclusive).

    Per day: reconstruct the in-play universe, then for each name (in rvol order)
    check the daily RiskBudget gate BEFORE entering and register the result after,
    exactly like the live ENTRY decision point. Equity compounds across days.

    Returns {"spec", "metrics", "trades", "daily", "skipped"}. This is the single
    call the research loop uses to score a candidate strategy."""
    spec = spec or StrategySpec()
    global _PACE_SECONDS
    _PACE_SECONDS = pace_seconds
    d0, d1 = date.fromisoformat(start), date.fromisoformat(end)
    trades: List[dict] = []
    daily: List[dict] = []
    skipped = {"no_data": 0, "gated": 0, "no_signal": 0}
    equity_curve = [equity]
    cur_equity = equity

    d = d0
    while d <= d1:
        if not is_trading_day(d):
            d += timedelta(days=1)
            continue
        day = d.isoformat()
        in_play = historical_in_play(day, spec)
        if not in_play:
            skipped["no_data"] += 1
            d += timedelta(days=1)
            continue

        budget = RiskBudget(starting_equity=cur_equity,
                            max_daily_loss_pct=spec.max_daily_loss_pct,
                            max_consecutive_losses=spec.max_consecutive_losses,
                            max_trades=spec.max_trades_per_day,
                            risk_pct_per_trade=spec.risk_pct)
        day_pnl = 0.0
        day_trades = 0
        for cand in in_play:
            gate = budget.can_trade(account_value=cur_equity)
            if not gate["ok"]:
                skipped["gated"] += 1
                break  # circuit breaker tripped — done for the day
            rec = simulate_orb_day(cand["symbol"], day, cur_equity, spec)
            if rec is None:
                skipped["no_signal"] += 1
                continue
            rec["rvol_proxy"] = cand["rvol_proxy"]
            budget.register(rec["pnl"])
            cur_equity += rec["pnl"]
            day_pnl += rec["pnl"]
            day_trades += 1
            trades.append(rec)
        equity_curve.append(cur_equity)
        if day_trades:
            daily.append({"day": day, "trades": day_trades,
                          "pnl": round(day_pnl, 2), "equity": round(cur_equity, 2)})
            if verbose:
                print(f"{day}: {day_trades} trades, pnl {day_pnl:+.2f}, equity {cur_equity:.2f}")
        d += timedelta(days=1)

    return {
        "spec": spec.to_dict(),
        "metrics": summarize(trades, equity, equity_curve, len(daily)),
        "trades": trades,
        "daily": daily,
        "skipped": skipped,
    }


# ── metrics ──────────────────────────────────────────────────────────────────

def summarize(trades: List[dict], starting_equity: float,
              equity_curve: Optional[List[float]] = None,
              trading_days: int = 0) -> Dict[str, Any]:
    """Standardised scorecard for a run. Expectancy (avg R) and profit factor are
    the headline numbers; max drawdown and Sharpe say whether the equity curve is
    survivable. A viable strategy needs expectancy_r > 0 AND profit_factor > 1
    AND a drawdown you can stomach — on a sample big enough to trust (n ≥ ~30)."""
    n = len(trades)
    if n == 0:
        return {"n_trades": 0, "note": "no trades — universe/params too tight or no data"}
    pnls = [t["pnl"] for t in trades]
    rs = [t["r_multiple"] for t in trades]
    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p < 0]
    total = sum(pnls)
    gross_win = sum(wins)
    gross_loss = -sum(losses)

    # max drawdown off the equity curve
    curve = equity_curve or [starting_equity, starting_equity + total]
    peak = curve[0]
    max_dd = 0.0
    for v in curve:
        peak = max(peak, v)
        max_dd = max(max_dd, (peak - v) / peak if peak else 0)

    # daily-return Sharpe (annualised, 252)
    rets = []
    for i in range(1, len(curve)):
        prev = curve[i - 1]
        rets.append((curve[i] - prev) / prev if prev else 0)
    sharpe = None
    if len(rets) > 1:
        mean = sum(rets) / len(rets)
        var = sum((r - mean) ** 2 for r in rets) / (len(rets) - 1)
        sd = var ** 0.5
        sharpe = round((mean / sd) * (252 ** 0.5), 2) if sd else None

    return {
        "n_trades": n,
        "trading_days": trading_days,
        "win_rate": round(len(wins) / n, 3),
        "avg_win": round(gross_win / len(wins), 2) if wins else 0.0,
        "avg_loss": round(-gross_loss / len(losses), 2) if losses else 0.0,
        "avg_r": round(sum(rs) / n, 3),
        "expectancy_r": round(sum(rs) / n, 3),  # avg R per trade — the edge, in R
        "expectancy_dollars": round(total / n, 2),
        "profit_factor": round(gross_win / gross_loss, 2) if gross_loss else None,
        "total_pnl": round(total, 2),
        "return_pct": round(100 * total / starting_equity, 2) if starting_equity else 0.0,
        "max_drawdown_pct": round(100 * max_dd, 2),
        "sharpe_annualised": sharpe,
        "final_equity": round(curve[-1], 2),
        "exit_breakdown": {
            reason: sum(1 for t in trades if t["exit_reason"] == reason)
            for reason in ("target", "stop", "eod")
        },
    }


# ── research loop: score, gate, rank ─────────────────────────────────────────
# This is what turns the backtester into a strategy-finder. Propose a handful of
# StrategySpec variants, backtest each over the same window, and let is_viable()
# + the ranking decide which (if any) earns real money. The winner's spec is what
# you write into strategy.md and trade — a strategy is a validated artifact, not
# a guess.

def is_viable(metrics: Dict[str, Any], min_trades: int = 30,
              max_drawdown_pct: float = 25.0) -> Dict[str, Any]:
    """Gate a backtest's scorecard: does this strategy actually have an edge you
    can trade? Deliberately strict — the null result ("not viable") is the
    common, correct answer, and shipping a strategy that only looked good on 6
    trades is how accounts die. All four must hold:
      · enough trades to trust the sample (n ≥ min_trades)
      · positive expectancy in R (the edge, net of the win-rate/payoff tradeoff)
      · profit factor > 1 (gross wins outweigh gross losses)
      · a drawdown you can sit through (≤ max_drawdown_pct)
    """
    reasons = []
    n = metrics.get("n_trades", 0)
    if n < min_trades:
        reasons.append(f"only {n} trades (need ≥ {min_trades} to trust the sample)")
    if metrics.get("expectancy_r", 0) <= 0:
        reasons.append(f"expectancy {metrics.get('expectancy_r')}R ≤ 0 (no edge)")
    pf = metrics.get("profit_factor")
    if pf is not None and pf <= 1:
        reasons.append(f"profit factor {pf} ≤ 1 (losses outweigh wins)")
    dd = metrics.get("max_drawdown_pct", 0)
    if dd > max_drawdown_pct:
        reasons.append(f"max drawdown {dd}% > {max_drawdown_pct}% (unsurvivable)")
    return {"viable": not reasons, "reasons": reasons or ["clears every gate"]}


def research_strategies(start: str, end: str, specs: List[StrategySpec],
                        equity: float = 30_000.0, min_trades: int = 30,
                        pace_seconds: float = 0.0) -> Dict[str, Any]:
    """Backtest each candidate spec over the SAME window and rank them. Returns
    the ranked table + the best VIABLE spec (or None) ready to promote to
    strategy.md. Ranks by expectancy_r, tie-broken by profit factor — a strategy
    that clears is_viable() always sorts above one that doesn't.

    Cost warning: this is (len(specs) × days × top_n) data pulls. Start with a
    few specs over ~40-60 trading days; raise pace_seconds on a throttled Polygon
    tier. Log what you ran — never imply more coverage than you paid for."""
    ranked = []
    for spec in specs:
        run = backtest_orb(start, end, equity=equity, spec=spec, pace_seconds=pace_seconds)
        m = run["metrics"]
        verdict = is_viable(m, min_trades=min_trades)
        ranked.append({"spec": spec.to_dict(), "metrics": m,
                       "viable": verdict["viable"], "why": verdict["reasons"]})
    ranked.sort(key=lambda r: (r["viable"], r["metrics"].get("expectancy_r", 0),
                               r["metrics"].get("profit_factor") or 0), reverse=True)
    best = next((r for r in ranked if r["viable"]), None)
    return {"window": {"start": start, "end": end}, "ranked": ranked,
            "best_viable": best}
