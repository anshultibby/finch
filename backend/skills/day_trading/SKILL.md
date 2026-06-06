---
name: day_trading
description: "Evidence-based short-term / day trading playbook. Verifiable, backtested strategies (Opening Range Breakout on 'stocks in play', VWAP reclaim, Connors RSI(2) mean reversion), professional risk management (1% sizing, daily loss limits, R-multiples), and ready-to-run helper functions for indicators, setups, and position sizing. Built to run as scheduled automations that scan, build a risk-defined trade, and email a one-click approval link — not to trade blindly. Pairs with the robinhood (execution) and polygon_io (intraday data) skills."
metadata:
  emoji: "📈"
  category: trading
  is_system: true
  requires:
    env: []
    bins: []
---

# Day Trading Skill

A disciplined, **evidence-first** approach to short-term trading. Everything here
is grounded in published research or professional consensus — citations inline —
not blog folklore. The skill ships callable helpers (`indicators.py`, `setups.py`,
`risk.py`) and is designed to **run as automations** (scheduled jobs that scan →
build a risk-defined trade → email the user for one-click approval).

```python
from skills.day_trading.scripts.indicators import vwap, atr, rsi, relative_volume, opening_range
from skills.day_trading.scripts.setups import orb_signal, stocks_in_play, vwap_signal, connors_rsi2_signal
from skills.day_trading.scripts.risk import position_size, plan_trade, RiskBudget
```

## Read this first — the honest base rate

Lead with this whenever a user asks you to day trade. It is not a disclaimer, it
shapes the whole approach:

- **<1% of day traders earn persistent profits net of fees;** 80%+ lose
  (Barber, Lee, Liu & Odean, *Do Individual Day Traders Make Money? Evidence from
  Taiwan*). In Brazil, **97% of those who persisted 300+ days lost money**
  (Chague, De-Losso & Giovannetti). The most-active US traders underperformed the
  market by **~6.5 percentage points/year** (Barber & Odean 2000).
- **The edge that survives is structural, not predictive:** a *positive-expectancy
  setup* + *asymmetric risk/reward* + *iron risk limits*. Most losers have an
  occasionally-right setup and no risk control.
- **Costs and discipline kill more accounts than bad picks.** Commissions, spread,
  slippage, and tilt are the real adversaries.

So: trade **only** documented setups, **only** with defined risk, **size small**,
and **prefer automations** that enforce the rules mechanically over discretionary
clicking.

## The verifiable setups

### 1. Opening Range Breakout (ORB) on "stocks in play" — the flagship

The most rigorously documented retail day-trading edge. Zarattini, Barbon & Aziz,
*A Profitable Day Trading Strategy For The U.S. Equity Market* (SSRN 4729284, 2024),
tested the 5-minute ORB across 7,000+ US stocks, 2016–2023: **Sharpe ≈ 2.4, beta
≈ 0**, robust across parameters. The single-name precursor (SSRN 4416622, 2023) on
QQQ/TQQQ returned **1,484% (TQQQ) vs 169% buy-and-hold**, ~33%/yr alpha.

Why it works: it only trades **stocks in play** (abnormal volume from a catalyst),
rides the morning's directional momentum, and is **asymmetric** — ~17% win rate but
winners dwarf losers (small ATR-based stop, let the rest run to the close).

Rules (all encoded in `setups.py`):
1. **Universe:** top ~1,000 by dollar volume, price > $5, ATR(14) > $0.50.
2. **Stocks in play:** relative volume = today's first-5-min volume ÷ average
   first-5-min volume over the prior 14 days. Keep **RVOL > 1**, trade the **top
   ~20**.
3. **Opening range:** first **5 minutes** (the tested optimum).
4. **Direction:** set by the first 5-min bar — up → longs only, down → shorts only.
5. **Entry:** stop order at the OR **high** (long) / **low** (short).
6. **Stop:** a small fraction of ATR(14) beyond entry (≈0.1×ATR), or the opposite
   end of the opening range.
7. **Exit:** **at the close** (EOD time stop) — or a 10R target (2023 paper). No
   overnight risk.
8. **Sizing:** risk **1%** of the per-position budget; cap weight at equal-weight
   (≤ 1/N), leverage ≤ 4x.

```python
from skills.polygon_io.scripts.market.intraday import get_today_bars
from skills.polygon_io.scripts.market.historical_prices import get_historical_prices

bars  = get_today_bars("NVDA", "1min")["bars"]            # today's 1-min bars
daily = get_historical_prices("NVDA", days=30)["prices"]  # for ATR(14); adapt keys
sig = orb_signal(bars, or_minutes=5, atr_bars=daily, stop_atr_mult=0.10)
# {'signal': 'long', 'entry': 10.5, 'stop': 10.3, 'or_high': 10.5, ...}
if sig["signal"]:
    plan = plan_trade(equity=25_000, entry=sig["entry"], stop=sig["stop"],
                      side=sig["signal"], risk_pct=0.01, rr=10)
    # → shares, target, dollars at risk; route plan through robinhood review→approve
```

### 2. VWAP reclaim / pullback

VWAP is the institutional benchmark — **~60–70% of US volume is algo-executed
against it**, so it acts as intraday support/resistance. Best in the first hour,
on 1–5 min charts.

- **Long:** price holds **above** VWAP (uptrend); buy a pullback that touches/holds
  the line as volume dries up then re-emerges. **Stop just below the pullback low**
  — never *on* VWAP (wicks). Mirror for shorts below VWAP.
- **Always require volume confirmation;** weak-volume breaks fail.

```python
sig = vwap_signal(get_today_bars("AAPL", "1min")["bars"], trend_bias="long")
# {'signal':'long','vwap':189.2,'above_vwap':True,'entry':...,'stop':...}
```

### 3. Connors RSI(2) mean reversion — a *swing* edge (1–5 day hold)

Not intraday, but the most reproducible **short-term** long signal. Connors &
Alvarez backtests show **>75% win rate** on indices. Best on broad ETFs (SPY/QQQ);
weaker on single names.

- **Trend filter:** longs only when close > **200-day SMA**.
- **Entry:** **RSI(2) < 10** (stronger edge < 5).
- **Exit:** close > **5-day SMA**.
- Connors found fixed stops *hurt* net results — control risk via **sizing + the
  ETF trend filter**, and still keep a catastrophe stop on live single names.

```python
closes = [p["close"] for p in get_historical_prices("SPY", days=260)["prices"]]
sig = connors_rsi2_signal(closes)   # {'signal':'long','rsi2':4.1,'above_200sma':True}
```

## Risk management — the part you actually control

Consensus of professional/prop-firm rules (Bulls on Wall Street; Trade That Swing;
Optimus Futures), all encoded in `risk.py`:

| Rule | Value |
|------|-------|
| Risk per trade | **1%** of equity (0.5–2% range) |
| Position size | `risk$ ÷ |entry − stop|` (use `position_size()`) |
| Daily loss limit | **−3%** of account, then **stop for the day** (1–2% when new) |
| Consecutive losses | stop after **3 in a row** |
| Trades/day | a few **quality** setups; hard cap ~10 |
| Risk/reward | **≥ 2:1**; ORB uses **10R** to pay for the low win rate |
| Leverage | **≤ 4x** (PDT: need **$25k** for >3 day trades / 5 days on margin) |

```python
budget = RiskBudget(starting_equity=25_000, max_daily_loss_pct=0.03,
                    max_consecutive_losses=3, risk_pct_per_trade=0.01)
if budget.can_trade()["ok"]:
    plan = plan_trade(25_000, entry=sig["entry"], stop=sig["stop"], side="long", rr=10)
    # ...place via review→approve, then after the trade closes:
    budget.register(realized_pnl)   # circuit breaker updates; re-check can_trade()
```

Manage the open trade: **take partials at 1:1 and move the stop to breakeven** —
the single most cited fix for turning winners into losers.

## When to trade (intraday timing)

- **09:30–10:30 ET** — highest volume/volatility; where ORB and VWAP setups live.
- **15:00–16:00 ET** — "power hour," second-best window.
- **11:30–14:00 ET** — lunchtime chop; lowest edge, sit out.
- The old **overnight drift** edge is largely arbitraged away — don't rely on it.

## ⭐ Run it as an automation (preferred)

Discretionary day trading is where discipline breaks. The high-leverage move is to
encode a setup as a **scheduled job** (from the `finch_api` skill) that fires at the
right minute, evaluates the rules, builds a risk-defined trade, and routes it
through the **robinhood review→approve** loop so the user one-click-approves by
email. The automation *is* the discipline.

**Safety default: never trade unattended.** Scan → `review_order` → email approval.
Only `place_order` directly inside a job if the user has explicitly opted into
unattended trading for that automation, and always keep a dollar cap.

### Pattern A — the morning ORB scanner (fires once, after the opening range)

```python
from skills.finch_api.scripts import schedule_job

schedule_job(
    name="ORB scan — stocks in play",
    recurrence="weekdays",
    run_at="2026-06-05T13:36:00Z",   # 09:36 ET — just after the 5-min OR completes
    message=(
        "Run my Opening Range Breakout automation. Read /home/user/store/strategy.md "
        "for my rules first. Then:\n"
        "1. connection_status(); if not connected, stop.\n"
        "2. Build today's 'stocks in play': for my watchlist, pull first-5-min volume "
        "   vs the prior-14-day average (polygon_io), keep RVOL>1, price>$5, ATR>0.5, "
        "   rank top 5 with stocks_in_play().\n"
        "3. For each, orb_signal(get_today_bars(sym,'1min'), atr_bars=daily). "
        "   If signal fires, plan_trade(equity, entry, stop, side, risk_pct=0.01, rr=10).\n"
        "4. Enforce RiskBudget: 1% risk/trade, skip if today's loss limit is hit.\n"
        "5. review_order the best 1-2 candidates, then request_trade_approval(...) so I "
        "   approve by email. If nothing qualifies, do nothing (no email)."
    ),
)
```

### Pattern B — self-chaining for intraday cadence

A one-off job can schedule the next run at the end of its own run, so you control
the cadence (tighten near a catalyst, back off in the lunch chop):

```python
# ...at the end of an automation's message instruction:
# "If the market is still open and it's before 15:30 ET, schedule_job(in_minutes=15, "
# "message=<this same instruction>) to re-scan; otherwise stop for the day."
```

### Pattern C — the end-of-day flatten (ORB has no overnight risk)

```python
schedule_job(
    name="EOD flatten — day-trade book",
    recurrence="weekdays",
    run_at="2026-06-05T19:55:00Z",   # 15:55 ET
    message=("For each open day-trade position on my agentic account, review_order a "
             "closing order and request_trade_approval so I flatten before the close."),
)
```

### Persist the strategy in memory

Keep the thesis, the exact rules, the watchlist, and post-trade learnings in durable
memory so every run reads them instead of re-deriving:

```python
memory_write(durable=True)  # → MEMORY.md / /home/user/store/strategy.md
```

Each automation run should **read the rules, act, then append what happened**
(what fired, fills, P&L, what to adjust) — the strategy compounds over sessions.

## Helper reference

- **`indicators.py`** — `sma`, `ema`, `rsi(values, period)` (use 2 for Connors),
  `atr(bars, 14)`, `vwap(bars)` / `vwap_series`, `opening_range(bars, minutes)`,
  `relative_volume(today_open_vol, prior_open_vols)`. Pure functions over OHLCV
  bar dicts (polygon_io shape); no network, no deps.
- **`setups.py`** — `orb_signal`, `stocks_in_play`, `vwap_signal`,
  `connors_rsi2_signal`. Each returns a dict with `signal` + entry/stop levels;
  none place orders.
- **`risk.py`** — `position_size`, `plan_trade` (full risk-defined plan with target),
  `RiskBudget` (daily-loss / consecutive-loss / trade-count circuit breaker).

## Hard rules (never violate)

1. **No setup, no trade.** If `signal is None`, do nothing.
2. **Every trade is risk-defined before entry** — entry, stop, size, target known.
3. **Respect the RiskBudget.** Daily loss limit or 3 losses in a row → stop.
4. **Default to review→approve.** Unattended trading only on explicit opt-in + cap.
5. **State the base rate honestly** when the user asks to "make money day trading."

## Sources

- Barber, Lee, Liu & Odean — *Do Individual Day Traders Make Money? Evidence from Taiwan* — https://faculty.haas.berkeley.edu/odean/papers/Day%20Traders/Day%20Trade%20040330.pdf
- Barber, Lee, Liu & Odean — *The Cross-Section of Speculator Skill: Evidence from Day Trading*
- Chague, De-Losso & Giovannetti — *Day Trading for a Living?* (Brazil, 97% lose)
- Zarattini, Barbon & Aziz (2024) — *A Profitable Day Trading Strategy For The U.S. Equity Market* — https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4729284
- Zarattini & Aziz (2023) — *Can Day Trading Really Be Profitable?* (ORB on QQQ/TQQQ) — https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4416622
- Connors & Alvarez — *Short Term Trading Strategies That Work* (RSI(2))
- Risk frameworks: Bulls on Wall Street; Trade That Swing; Optimus Futures
