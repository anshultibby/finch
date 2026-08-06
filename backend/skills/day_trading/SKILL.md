---
name: day_trading
description: "Run a disciplined day-trading operation: scheduled decision points (plan → entry → manage → flatten), backtested setups (5-min ORB on stocks-in-play, VWAP reclaim, RSI(2) swing), code-enforced risk gates that persist across runs, and LLM catalyst triage. Pairs with robinhood (execution), polygon_io (historical data) and FMP (same-day data). Routes trades through email approval by default."
metadata:
  emoji: "📈"
  category: trading
  is_system: true
  auto_on: true
  requires:
    env: []
    bins: []
---

# Day Trading Skill

## Division of labor

You can't watch the tape — you wake at scheduled moments, act, and die. So:
**code** owns signals, sizing, risk gates, and the journal; the **broker's
resting orders** own the millisecond work (entries at levels, protective
stops); **you** own exactly two judgment calls — *why* is a stock moving
(catalyst triage), and what to do when reality deviates from plan. Everything
else is mechanical. Be an operator, not a commentator: state the base rate once
for a new user ("most day traders lose; our edge is documented setups + strict
risk, sized small"), then act.

```python
from skills.day_trading.scripts.clock import session
from skills.day_trading.scripts.data import stocks_in_play, rth_today_bars
from skills.day_trading.scripts.setups import orb_signal, vwap_state, connors_rsi2_signal
from skills.day_trading.scripts.risk import RiskBudget, plan_trade
from skills.day_trading.scripts.backtest import (StrategySpec, backtest_orb,
                                                 research_strategies, is_viable)
from skills.day_trading.scripts import journal
from skills.robinhood.scripts.trading import (connection_status, portfolio_snapshot,
                                              get_quotes, get_orders, review_order, cancel_order)
from skills.finch_api.scripts import schedule_job, request_trade_approval  # approval = finch_api, NOT robinhood
```
The scripts' docstrings are the reference — read them; don't reimplement them.

## The trading day = four scheduled decision points

**Every run opens the same way:** `session()` (ET-correct clock — never the
server's; exit if not a trading day / closed) → `journal.session_state()` (your
memory: open positions, pending orders, today's P&L, plan, notebook) →
`connection_status()` + `portfolio_snapshot()` → reconcile journal vs broker
and fix drift in the journal first.

### PLAN — nightly, after the close (~17:00–18:00 ET) (no orders)
Grade today's closed trades against their plans; check `journal.setup_stats()`
and apply the kill criteria; update `strategy.md` with lessons. Build
tomorrow's event map and watch ideas:
- `get_earnings_calendar(...)` (financial_modeling_prep): tonight's after-close
  + tomorrow's pre-open reporters → likely stocks-in-play.
- `upcoming_events(days=1)` (fred skill): scheduled macro prints with ET times.
  Write them into the plan — they set tomorrow's rules of engagement (below).
One line of catalyst triage per name. Set tomorrow's risk: 1%/trade, **halved
after a losing day**. `journal.write_plan(...)`, then `append_note(...)`.

**Macro-event rules of engagement** (from the plan's event map):
- 08:30 ET high-impact print (CPI, NFP, PCE, GDP): gaps and RVOL spike — the
  in-play scan gets *richer*, and ATR-based sizing already adapts. Trade the
  reaction via the normal pipeline; never trade the forecast.
- FOMC day: no new entries after 13:30 ET; holding through the 14:00 decision
  only with the stop already at breakeven. Expect the 14:00–15:00 whipsaw.

### ENTRY — 09:36 ET (after the 5-min opening range completes)
```python
candidates = stocks_in_play(top_n=10)        # true RVOL + ATR + today's RTH bars
# data.py handles the Polygon same-day block itself (FMP fallback) — a Polygon
# "not authorized" on today's bars is NOT a reason to abort the run.
# Triage each catalyst (search the news). Keep ≤ 3.
budget = RiskBudget.from_journal(equity)     # inherits today's losses from prior runs
if budget.can_trade(account_value=equity)["ok"]:
    sig = orb_signal(c["bars"], atr14=c["atr14"])
    # "armed" → rest a stop entry AT the level (preferred); "triggered" → marketable
    # entry OK; "missed"/"short_blocked" → log status="skipped" with reason
    plan = plan_trade(equity, sig["entry"], sig["stop"], risk_pct=0.01, rr=10)
    # review_order → request_trade_approval → log_trade(status="planned", phase=...)
```

**"No trade" is the default; a trade is the exception that must justify
itself.** Take at most the best 1–2 — few decisive positions beat many small
opinions. Before any entry, fill ALL of:

```text
Catalyst:     today's specific headline + why it's durable — quoted
Numbers:      today's RVOL / gap% / ATR from THIS run's tool calls
Levels:       entry/stop/size/target from plan_trade(), never estimated
Invalidation: what kills the thesis before the stop
Bear case:    one honest paragraph against the trade
```

Can't fill a field → skip. Bear case stronger than catalyst → skip. Catalyst
ranking: earnings beat + raise ≫ upgrade > sympathy > unexplained spike >
dilution/pump (skip the last two outright).

### MANAGE — ~10:15 & ~14:30 ET (and after any fill)
Exits before entries. Every filled entry **must** have a protective stop
resting at the broker — a position without one is the first thing you fix.
Winner at target → take it, or scale half at 1:1 and move the stop to
breakeven. Thesis invalidated (lost VWAP, back inside the OR) → close now;
never average down. Once `phase` is `lunch`: cancel unfilled armed entries, no
new entries. Every exit: `log_trade(status="closed", pnl=...)` →
`budget.register(pnl)`.

### FLATTEN — 15:45 ET (12:45 on `early_close` days)
Intraday setups have no overnight edge: close every open day-trade position,
cancel every resting day-trade order. Risk-reducing, so place directly if the
user opted into unattended trading for this job; otherwise the approval email —
at 15:45, not 15:55, so there's time to act.

## RESEARCH — find & validate a strategy before trading it (on demand / weekly)

Don't trade a setup on faith in its citation — **prove it has an edge on this
account's universe, then promote the winner.** A strategy is a validated
`StrategySpec`, not a guess. Run this when there's no validated spec in
`strategy.md`, when results drift, or on a weekly cadence:

```python
# 1. Propose a few candidate specs (vary the knobs that matter).
specs = [
    StrategySpec(),                                   # the documented baseline
    StrategySpec(stop_atr_mult=0.20, rr=4.0),         # wider stop, nearer target
    StrategySpec(min_abs_gap_pct=4.0, top_n=6),       # only the strongest gaps
]
# 2. Backtest all over the SAME recent window and rank by expectancy.
report = research_strategies("2026-05-01", "2026-06-30", specs, equity=1000)
best = report["best_viable"]        # None if nothing clears is_viable()
```

`backtest_orb` / `research_strategies` reuse the LIVE signal, sizing and risk
code, so a backtest is a faithful replay — but read the "known limitations" in
`backtest.py` (modelled fills, a coarser historical in-play universe) and state
them when you report. `is_viable()` is deliberately strict: **n ≥ 30, positive
expectancy_R, profit factor > 1, drawdown ≤ 25%.** "Not viable" is the common,
correct answer — when nothing clears, say so and keep trading paper / stay flat;
never promote a strategy that only looked good on a handful of trades.

**Promote:** write the winning spec (its exact params) and its scorecard into
`strategy.md` as the operation's current strategy; ENTRY then trades those
params. Note the Polygon-tier rate limits — pace multi-day runs and never imply
more coverage than you paid for.

## Setups (full rules in `setups.py` docstrings)

- **ORB on stocks-in-play** (flagship): ~17% win rate, winners dwarf losers —
  the stop and chase guard ARE the strategy. Only `armed`/`triggered` are
  tradeable. Zarattini/Barbon/Aziz 2024 (SSRN 4729284): Sharpe ≈ 2.4.
- **VWAP reclaim**: `bias` is not an entry; only a `trigger` (pullback → held →
  reclaimed on volume) is. First hour only.
- **Connors RSI(2)**: 1–5 day swing on SPY/QQQ, not intraday.
- **Catalyst swing** (judgment, same gates): a top-tier durable catalyst that
  passes the full template can justify a 1–3 day hold with a defined stop —
  post-news drift is the best-documented edge for a reading agent. Exempt from
  FLATTEN. Prefer expanding here over adding intraday setups.

## Risk gates (`risk.py` — never reimplement, never bypass)

1%/trade (halved after a losing day) · ≤25% equity per name, ≤4× leverage ·
−3% day → stop (open risk counts) · 3 straight losses → stop · ≤10 trades/day ·
PDT enforced under $25k · no ORB entry >0.5R past the level.

**Always `RiskBudget.from_journal(equity)`** — a bare `RiskBudget()` forgets
the losses earlier runs took today.

## Execution mechanics (Robinhood)

- **No shorting** (shorts come back `short_blocked`) and **no bracket/OCO**:
  rest the protective stop always, take targets yourself at MANAGE, never leave
  a stop AND a limit-sell resting for the same shares (double-fill).
- Default flow per `<trade_execution>`: `review_order` →
  `request_trade_approval` (one-click email). Direct `place_order` in
  automations only with explicit per-job opt-in + a dollar cap.
- `dollar_amount` needs market orders; use share `quantity` for stop/limit.
- Cash agentic account: PDT doesn't apply, but **only settled funds** —
  same-day reuse of sale proceeds risks good-faith violations; trust
  `get_portfolio` buying power, not your arithmetic.

**Options** (if `connection_status()["options_enabled"]`; single-leg only):
permitted **only** as the vehicle for the catalyst-swing setup — never for
intraday ORB/VWAP (theta + spreads turn small edges negative). Rules: long
calls/puts only; premium paid = the position's entire risk budget
(`contracts = floor(risk$ / (premium×100))`, no separate stop needed); ≥ 2–3
weeks to expiry, delta ≥ 0.5 — directional instruments, not lottery tickets;
**never 0DTE; never buy ahead of a known binary event** (IV crush — trade the
post-event reaction instead); limit orders always; exit by MANAGE/PLAN review,
worthless-expiry is not an exit plan. Equity remains the default vehicle —
options only when the catalyst is top-tier and defined-premium risk genuinely
beats a stopped stock position.

## Memory, paper ramp, kill criteria

Persistent store `/home/user/store/day_trading/` (see `journal.py`):
trades.jsonl (pass each trade's `trade_id` to every later event), plan.md
(stale date at ENTRY = nightly failed → half size or skip), notebook.md
(`append_note` ends EVERY run), strategy.md (the evolving rules).

New user → paper first (`paper=True` in log_trade extras, skip the order
step). The ramp is measured in **logged paper trades, not sessions** — target
~10, then go live once the user has seen the stats. Paper trades are free:
during the ramp, a candidate that passes the mechanical gates (`can_trade` ok,
`plan_trade` shares > 0, signal `armed`/`triggered`) and whose catalyst is not
skip-tier MUST be taken on paper and managed honestly through MANAGE/FLATTEN.
"No trade is the default" governs live money; a paper ramp that logs zero
trades for weeks is over-filtering, teaches nothing, and never ends. Kill
criteria go in `strategy.md` before trade one: a setup negative after ~20–30
logged trades retires itself; 10% account drawdown → full stop pending user
reset. Small accounts (< $5k): the default ¼-equity weight cap leaves almost
no tradeable universe — use `plan_trade(..., max_weight=0.5)` and note it in
strategy.md; skip setups whose instruments exceed the cap outright (e.g.
RSI(2) on SPY at 4-figure share prices).

## Scheduling

**The nightly PLAN is the only standing job** — one recurring weekday
automation ("Nightly trading plan"), provisioned when the user connects
Robinhood; comped, pausable, not cancellable. Everything else is a one-off the
loop schedules for itself: **PLAN schedules tomorrow's wakes → each wake
schedules the next it needs → until FLATTEN.** The backend does no
pre-provisioning; the agent owns its own cadence (`schedule_job`), and the
weekday PLAN is the backstop that restarts the whole loop each morning even if
a chain link fails.

At PLAN, once the operation is live, schedule tomorrow's chain:
1. **FLATTEN near the close FIRST** — a mandatory safety wake, so open positions
   still get closed even if an intraday run dies. (12:45 ET on `early_close`
   days, else 15:45 ET.)
2. **ENTRY at 09:36 ET.** ENTRY then schedules MANAGE, MANAGE the next MANAGE —
   each run schedules its own successor before it ends. Self-chaining is allowed
   before 15:30 ET only; after that the standing FLATTEN and tomorrow's PLAN take
   over.

`schedule_job` takes UTC — fixed times drift an hour at DST changes and
`weekdays` recurrence ignores holidays. So compute each one-off from that DATE's
ET target via the clock helpers (never a remembered offset), and open every run
with the `session()` guard. PLAN itself stays at 22:00 UTC (17:00–18:00 ET;
evening-ET times cross UTC midnight and break the weekdays recurrence — don't
move it later). Keep each wake's message thin ("execute the day_trading skill's
ENTRY decision point exactly") — the recipe lives here. Schedule nothing if the
operation isn't set up (no strategy.md, no journal).

## Hard rules

1. `session()` first (closed → exit); `session_state()` second; reconcile
   before acting.
2. MANAGE before HUNT — no new entries while any position lacks a resting stop.
3. No setup, no trade; `missed` means missed.
4. Every entry passes `plan_trade` + `RiskBudget.from_journal().can_trade()`
   **before** any order.
5. Cut at the stop; never average down; flatten intraday by 15:45 ET.
6. Every number AND every position in your picture comes from a tool call in
   THIS run — never a remembered price, a remembered book, or a prior about how
   a ticker "usually" behaves.
7. No re-entry into a symbol you exited today, and yesterday's thesis carries
   zero weight — every candidate re-qualifies from scratch each morning.
8. User trade ideas go through the same template and gates — the pipeline may
   say no. Enthusiasm, yours or theirs, is not an input.
9. Journal every decision with its `trade_id`; `append_note` ends every run.
10. Unattended placement only with explicit per-automation user opt-in.

## Sources

ORB: Zarattini/Barbon/Aziz SSRN 4729284, Zarattini/Aziz SSRN 4416622 · RSI(2):
Connors & Alvarez · Base rates: Barber et al. (Taiwan), Chague et al. (Brazil,
~97% lose) · LLM-trading evidence behind the design: Lopez-Lira & Tang
2304.07619 + critiques 2309.17322/2504.14765, Profit Mirage 2510.07920,
FINSABER 2505.07078, Alpha Arena (nof1.ai 2025).
