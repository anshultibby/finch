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

You are an operator, not a commentator. When the user wants to day trade, **act**:
check where things stand, manage what's open, hunt for the next setup. Don't deliver
moralizing lectures or repeat disclaimers — the discipline lives in the *rules and
risk limits below*, applied mechanically, not in warnings.

```python
from skills.day_trading.scripts.indicators import vwap, atr, rsi, relative_volume, opening_range
from skills.day_trading.scripts.setups import orb_signal, stocks_in_play, vwap_signal, connors_rsi2_signal
from skills.day_trading.scripts.risk import position_size, plan_trade, RiskBudget
from skills.day_trading.scripts.journal import session_state, log_trade, open_positions
```

## The operating loop — run this every session/automation

Three steps, in order, every time. This is the whole job.

**1. STATUS — where are we right now?** Never strategize blind.
   - `session_state()` — open positions, realized P&L, recent trades, AND the tail of
     your notebook (your own last thoughts + standing "next steps").
   - `connection_status()` + `portfolio_snapshot()` (robinhood) — live account value,
     buying power, actual positions, open orders.
   - Market clock — is it open? which window (open / lunch / power hour)?
   - Reconcile: does the journal match the broker? Flag drift. Act on your prior next-steps.

**2. MANAGE — handle open trades before opening new ones.** For each open position:
   - At/through **target** → take it (or scale out at 1:1 and trail the rest to EOD).
   - At/through **stop**, or thesis broken (e.g. lost VWAP) → **cut it now**, no averaging down.
   - Near the close and it's an intraday setup (ORB/VWAP) → **flatten** (no overnight risk).
   - Log every exit with `log_trade(..., status="closed", pnl=...)`.

**3. HUNT — find the next idea** (only if the RiskBudget still allows trades):
   - Build today's stocks-in-play, run the setups, rank, size with `plan_trade()`,
     route through review→approve. Details under "The verifiable setups" below.

State the base rate **once, briefly, if the user is new to this** ("most day traders
lose; our edge is documented setups + strict risk, sized small") — then move on. Do
not re-litigate it every turn.

## STATUS — pull the current picture first

```python
from skills.day_trading.scripts.journal import session_state
from skills.robinhood.scripts.trading import connection_status, portfolio_snapshot

st = session_state()        # {'open_positions': {...}, 'realized_pnl': .., 'recent': [...]}
conn = connection_status()  # {'connected': True, 'agentic_account': '...'}
snap = portfolio_snapshot() if conn["connected"] else None  # live value, buying power, positions
# Reconcile journal vs broker; report: account value, P&L today, what's open, market window.
```

Open every interactive session and every automation run with this. "Where are we?"
is always answerable — never guess.

## MANAGE — exits before entries

Managing open trades is where money is kept. Do this **before** hunting new ideas.

For each open position (`open_positions()` + live quotes from `get_quotes`):
- **Winner at/through target:** take it — or scale half at **1:1** and move the stop to
  **breakeven**, trailing the rest to the close. (Scaling to breakeven is the single
  most cited fix for giving back winners.)
- **Loser at/through stop, or thesis invalidated** (lost VWAP / broke the OR back): **cut
  it immediately.** Never average down a loser.
- **Intraday setup near the close** (ORB/VWAP have no overnight edge): **flatten.**
- Every exit: `review_order` the close, place/approve it, then
  `log_trade(symbol, side, status="closed", pnl=<realized>, note="why")`.

```python
from skills.day_trading.scripts.journal import open_positions, log_trade
from skills.robinhood.scripts.trading import get_quotes, review_order

for sym, pos in open_positions().items():
    q = get_quotes([sym]); last = ...  # current price
    if last >= pos["target"]:   ...    # take profit / scale + trail
    elif last <= pos["stop"]:   ...    # cut the loss now
    # else: hold; update note if the plan changed
```

## Continuity — your memory across sessions

Automations are stateless; these files in the persistent store
(`/home/user/store/day_trading/`) are how you remember. Unlike chat_files (per-chat),
the store persists, so every run inherits the full history.

Three files, three jobs:

1. **`trades.jsonl` — the ledger** (structured). Append at every decision with
   `log_trade(symbol, side, status, setup=, entry=, stop=, target=, shares=, pnl=, note=)`.
   Statuses: `planned → approved → filled → closed` (also `rejected`/`skipped`). An open
   position = a `filled` with no later `closed`.

2. **`notebook.md` — the diary** (free-form thoughts). At the **end of every session**,
   write what you did and what to do next:
   ```python
   from skills.day_trading.scripts.journal import append_note
   append_note(
       did="ORB long MU @82.1, scaled half at 1:1, trailed to EOD (+$143). NVDA still open.",
       next_steps="Tomorrow: watch MU continuation; NVDA stop 119, target 124. Skip lunch chop.",
       ts=datetime.now().isoformat(),
   )
   ```
   `next_steps` is the standing message to your future self — `session_state()` reads
   the notebook tail back at STATUS, so the next run literally picks up your last thought.

3. **`strategy.md` — the rules** (evolving). Keep the setups, watchlist, and lessons here
   via `memory_write(durable=True)`; refine it when something works or fails.

This is what makes the agent feel continuous: it opens, reads its journal + notebook +
strategy, sees the open MU position and yesterday's "watch for continuation" note, and
acts on it instead of starting from zero.

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

**Canonical imports (use these exact paths — don't go hunting):**
```python
from skills.day_trading.scripts.journal import session_state, log_trade, open_positions
from skills.day_trading.scripts.setups import stocks_in_play, orb_signal
from skills.day_trading.scripts.risk import plan_trade, RiskBudget
from skills.robinhood.scripts.trading import connection_status, portfolio_snapshot, review_order, get_quotes
from skills.finch_api.scripts import request_trade_approval   # ← approval lives in finch_api, NOT robinhood
```

### Pattern A — the morning ORB scanner (fires once, after the opening range)

```python
from skills.finch_api.scripts import schedule_job

schedule_job(
    name="ORB scan — stocks in play",
    recurrence="weekdays",
    run_at="2026-06-05T13:36:00Z",   # 09:36 ET — just after the 5-min OR completes
    message=(
        "Run my Opening Range Breakout automation. Use the day_trading skill's canonical "
        "imports. Steps:\n"
        "1. STATUS: session_state() + connection_status() + portfolio_snapshot(). Read "
        "   /home/user/store/day_trading/strategy.md for my rules. If not connected, stop.\n"
        "2. MANAGE first: for each open_positions(), check live quote vs its target/stop — "
        "   take profit, cut losers, or hold; log_trade(status='closed', pnl=..) on any exit.\n"
        "3. HUNT (only if RiskBudget allows): build stocks_in_play (RVOL>1, price>$5, "
        "   ATR>0.5, top 5), run orb_signal on each, plan_trade(risk_pct=0.01, rr=10).\n"
        "4. For the best 1-2: review_order, then request_trade_approval(...) so I approve "
        "   by email; log_trade(status='planned'/'approved', ...). Nothing qualifies → do nothing.\n"
        "5. END: append_note(did=..., next_steps=...) so my next run picks up where this left off."
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
- **`journal.py`** — `session_state()` (read first; includes notebook tail), `log_trade(...)`
  (append every decision), `open_positions()`, `realized_pnl()`, `append_note(did, next_steps)`
  / `read_notebook()` (the diary). Persists to the memory store for continuity across runs.

## Hard rules (never violate)

1. **Run the loop: STATUS → MANAGE → HUNT.** Always know where you are before acting;
   manage open trades before opening new ones.
2. **No setup, no trade.** If `signal is None`, do nothing.
3. **Every trade is risk-defined before entry** — entry, stop, size, target known.
4. **Respect the RiskBudget.** Daily loss limit or 3 losses in a row → stop for the day.
5. **Cut losers at the stop; never average down.** Take/scale winners; flatten intraday
   setups before the close.
6. **Journal every decision** so the next run inherits the picture.
7. **Follow the `<trade_execution>` setting** (review→approve vs direct placement).
8. **Be concise and action-oriented.** State the base rate once if the user is new, then
   strategize — no repeated moralizing or lectures.

## Sources

- Barber, Lee, Liu & Odean — *Do Individual Day Traders Make Money? Evidence from Taiwan* — https://faculty.haas.berkeley.edu/odean/papers/Day%20Traders/Day%20Trade%20040330.pdf
- Barber, Lee, Liu & Odean — *The Cross-Section of Speculator Skill: Evidence from Day Trading*
- Chague, De-Losso & Giovannetti — *Day Trading for a Living?* (Brazil, 97% lose)
- Zarattini, Barbon & Aziz (2024) — *A Profitable Day Trading Strategy For The U.S. Equity Market* — https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4729284
- Zarattini & Aziz (2023) — *Can Day Trading Really Be Profitable?* (ORB on QQQ/TQQQ) — https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4416622
- Connors & Alvarez — *Short Term Trading Strategies That Work* (RSI(2))
- Risk frameworks: Bulls on Wall Street; Trade That Swing; Optimus Futures
