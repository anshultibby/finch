"""
Trade setups — research-backed signals as pure functions.

Each takes bars/prices and returns a dict with a `state` and exact levels. They
make NO network calls and place NO orders. Bars must be RTH-only (use
data.rth_today_bars / refine_candidates — polygon includes premarket otherwise).

ORB states are the contract with the execution layer:
    forming   — opening range not complete; do nothing yet
    armed     — range set, no breakout yet → place a resting STOP order at the
                boundary and let the broker do the watching
    triggered — breakout printed and price is still within chase range → a
                marketable entry is acceptable
    missed    — breakout printed but price ran beyond the chase guard; entering
                now destroys the asymmetry that makes the edge work. Skip.

See SKILL.md for citations and win-rate/payoff profiles.
"""
from typing import List, Dict, Optional, Literal
from .indicators import opening_range, vwap, vwap_series, rsi, sma


def orb_signal(bars: List[Dict], atr14: Optional[float] = None,
               or_minutes: int = 5, stop_atr_mult: float = 0.10,
               max_chase_r: float = 0.5,
               long_only: bool = True) -> dict:
    """
    5-minute Opening Range Breakout on stocks-in-play (Zarattini, Barbon & Aziz
    2024: Sharpe ≈ 2.4, ~17% win rate, winners dwarf losers).

    Direction = the FULL opening-range candle (open of first bar vs close of the
    last bar inside the window) — not the first 1-min bar. Entry is a stop order
    at the OR boundary; stop is stop_atr_mult×ATR(14) beyond entry (fallback:
    opposite side of the range); exit at the close (10R target optional).

    max_chase_r: if the breakout already printed, only allow entry while price
    is within this many R of the entry level — past that, return "missed".
    long_only=True because Robinhood cannot short; short breakouts come back
    as state="short_blocked" so the caller knows the setup existed.

    Bars must be today's RTH 1-min bars.
    """
    if not bars:
        return {"setup": "orb", "state": "forming", "signal": None, "reason": "no bars"}
    rng = opening_range(bars, or_minutes)
    window_end = int(bars[0]["timestamp"]) + or_minutes * 60 * 1000
    in_window = [b for b in bars if int(b["timestamp"]) < window_end]
    post = [b for b in bars if int(b["timestamp"]) >= window_end]
    if not rng or not in_window or not post:
        return {"setup": "orb", "state": "forming", "signal": None,
                "reason": "opening range still forming"}
    or_high, or_low = rng
    # Direction from the whole opening-range candle:
    direction = ("long" if float(in_window[-1]["close"]) >= float(in_window[0]["open"])
                 else "short")
    last = float(post[-1]["close"])

    if direction == "long":
        entry, opp = or_high, or_low
        stop = entry - stop_atr_mult * atr14 if atr14 else opp
        broke = any(float(b["high"]) > or_high for b in post)
        chase_ok = last <= entry + max_chase_r * abs(entry - stop)
    else:
        entry, opp = or_low, or_high
        stop = entry + stop_atr_mult * atr14 if atr14 else opp
        broke = any(float(b["low"]) < or_low for b in post)
        chase_ok = last >= entry - max_chase_r * abs(entry - stop)

    if direction == "short" and long_only:
        state = "short_blocked"
    elif not broke:
        state = "armed"
    elif chase_ok:
        state = "triggered"
    else:
        state = "missed"

    return {
        "setup": "orb",
        "state": state,
        "signal": direction if state in ("armed", "triggered") else None,
        "direction": direction,
        "entry": round(entry, 4), "stop": round(stop, 4),
        "or_high": round(or_high, 4), "or_low": round(or_low, 4),
        "last": round(last, 4), "atr14": round(atr14, 4) if atr14 else None,
        "reason": {
            "armed": f"{direction} bias — rest a stop entry at {round(entry, 4)}",
            "triggered": f"{direction} breakout printed, still within {max_chase_r}R of entry",
            "missed": "breakout ran past the chase guard — entering now flips the asymmetry",
            "short_blocked": "short setup, but the broker can't short — skip",
        }[state],
    }


def vwap_state(bars: List[Dict], touch_atr_frac: float = 0.15,
               atr14: Optional[float] = None, lookback: int = 6) -> dict:
    """
    VWAP regime + pullback trigger, kept honest by separating the two:

      bias    — which side of VWAP price is on. True ~half the day; NOT an entry.
      trigger — an actual pullback-reclaim: within `lookback` bars price touched
                VWAP (within touch_atr_frac×ATR, or 0.1% without ATR), held it,
                and the latest bar closed back in the bias direction on volume
                above the pullback bars' average.

    Long entry = trigger with bias "long"; stop below the pullback low (never ON
    VWAP — wicks). Best in the first hour. Bars must be RTH-only.
    """
    if len(bars) < lookback + 2:
        return {"setup": "vwap", "bias": None, "trigger": False, "signal": None,
                "reason": "not enough bars"}
    v = vwap(bars)
    vs = vwap_series(bars)
    last = float(bars[-1]["close"])
    bias = "long" if last > v else "short"
    tol = (touch_atr_frac * atr14) if atr14 else last * 0.001

    recent = bars[-lookback:]
    touched = held = False
    pull_low, pull_high = float("inf"), float("-inf")
    for b, w in zip(recent, vs[-lookback:]):
        lo, hi = float(b["low"]), float(b["high"])
        pull_low, pull_high = min(pull_low, lo), max(pull_high, hi)
        if bias == "long":
            if lo <= w + tol:
                touched = True
            held = float(b["close"]) > w - tol
        else:
            if hi >= w - tol:
                touched = True
            held = float(b["close"]) < w + tol
    pull_vol = sum(float(b["volume"]) for b in recent[:-1]) / max(len(recent) - 1, 1)
    last_bar = recent[-1]
    vol_ok = float(last_bar["volume"]) > pull_vol
    closed_with_bias = (float(last_bar["close"]) > float(last_bar["open"])) == (bias == "long")
    trigger = touched and held and vol_ok and closed_with_bias

    stop = pull_low if bias == "long" else pull_high
    return {
        "setup": "vwap",
        "bias": bias,
        "trigger": trigger,
        "signal": bias if trigger else None,
        "vwap": round(v, 4), "last": round(last, 4),
        "entry": round(last, 4), "stop": round(stop, 4),
        "reason": ("pullback touched VWAP, held, and reclaimed on volume" if trigger
                   else f"bias {bias}, but no completed pullback-reclaim — bias alone is NOT a setup"),
    }


def connors_rsi2_signal(daily_closes: List[float]) -> dict:
    """
    Connors RSI(2) mean reversion — a SWING edge (1–5 day hold), not intraday.
    >75% historical win rate on broad ETFs (SPY/QQQ); weaker on single names.

    Long only when close > 200-day SMA; enter when RSI(2) < 10 (stronger < 5);
    exit when close > 5-day SMA. Connors found fixed stops hurt results —
    control risk via sizing + the trend filter (keep a catastrophe stop live).
    """
    if len(daily_closes) < 201:
        return {"setup": "connors_rsi2", "signal": None, "reason": "need ~200 daily closes"}
    sma200, sma5 = sma(daily_closes, 200), sma(daily_closes, 5)
    r2 = rsi(daily_closes, 2)
    last = daily_closes[-1]
    in_uptrend = last > sma200
    entry = in_uptrend and r2 is not None and r2 < 10
    return {
        "setup": "connors_rsi2",
        "signal": "long" if entry else None,
        "rsi2": round(r2, 2) if r2 is not None else None,
        "above_200sma": in_uptrend,
        "exit_above_5sma": last > sma5 if sma5 else None,
        "reason": ("oversold pullback in an uptrend — entry" if entry
                   else "no entry (need close>200SMA and RSI2<10)"),
    }
