---
name: day_trading
description: "Run an autonomous LIVE day-trading operation: a self-scheduling agent that wakes at market triggers, scans stocks-in-play, trades documented setups (5-min ORB, VWAP reclaim, RSI(2) swing), and schedules its own next wakeup. Trades live and unconstrained — no risk gates. Code owns the signals; the agent owns catalyst triage, sizing and pacing. Pairs with robinhood (execution), polygon_io (historical data) and FMP (same-day data)."
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
**code** owns the signals and the journal; the **broker's resting orders** own
the millisecond work (entries at levels, protective stops); **you** own the
judgment — *why* is a stock moving (catalyst triage), how much to size, and what
to do when reality deviates from plan. There are no risk gates — sizing and
pacing are yours. Be an operator, not a commentator: decide and act.

```python
from skills.day_trading.scripts.clock import session
from skills.day_trading.scripts.data import stocks_in_play, rth_today_bars
from skills.day_trading.scripts.setups import orb_signal, vwap_state, connors_rsi2_signal
from skills.day_trading.scripts.risk import RiskBudget, plan_trade
from skills.day_trading.scripts import journal
from skills.robinhood.scripts.trading import (connection_status, portfolio_snapshot,
                                              get_quotes, get_orders, review_order, cancel_order)
from skills.day_trading.scripts.journal import session_state, append_note
from skills.library.scripts.notes import read, find, write_section, tasks
from skills.finch_api.scripts import schedule_job, list_jobs, get_job, request_trade_approval  # approval = finch_api, NOT robinhood
from skills.fred.scripts import upcoming_events        # macro calendar (module is `releases`)
```
The scripts' docstrings are the reference — read them; don't reimplement them.

## How a trading day flows (reference — your wakeup goal drives)

You're an autonomous agent pursuing a goal, not a script executing fixed steps.
Your **wakeup message is your instruction**; the four moments below (nightly
review → open positions → check positions → close out) are the proven rhythm to
draw on and the tools to use at each — not a mandatory sequence. Judge what the
moment needs.

**Whatever you do, every run opens the same way:** `session()` (ET-correct clock
— never the server's; exit if not a trading day / closed) → `journal.session_state()`
(your memory: open positions, pending orders, today's P&L, plan, the previous
run's note, and any tasks due today) → `connection_status()` + `portfolio_snapshot()`
→ reconcile journal vs broker and fix drift in the journal first.

## Where your work goes

You have no memory between runs — only what you filed. File by **what changes
it**, which gives every fact exactly one home. Read `library`'s SKILL.md once;
it owns the general pattern and the index → outline → section access path.

| What you learned | Goes in | Who sees it |
|---|---|---|
| A view on a company | `stocks/{SYMBOL}/thesis.md` | the user, in Analysis |
| Work spanning runs | `tasks/{slug}.md` | the user, in Tasks |
| What happened today | `append_note(did, next_steps=...)` | you |
| A rule you now follow | `playbooks/day-trading.md` | you |
| A trade event | `log_trade(...)` | the ledger |

**Anything ticker-specific goes in `stocks/{SYMBOL}/thesis.md`** — via
`write_chat_file`, which syncs it to that stock's Analysis tab. Sections the
next run will want: `Thesis`, `Invalidation`, `History`. A thesis written into
a daily log is invisible to the user and unfindable to you.

**Anything you're waiting on becomes a task file** — "does the MU thesis
survive the DRAM print", "watch for the NVDA guide" — with a `review` date. The
next run picks it up from `tasks_due` without reading any history at all.

## Context discipline — read narrow, then go deep

A tool result you pull in early is re-sent to the model on *every* later call in
that run, so a 40K-token read is charged thirty times over. This operation's
old diary was exactly that: ~38% of a nightly run's bill, for one file.

| Want | Call | Not |
|---|---|---|
| Where the operation stands | `session_state()` | reading files |
| What's on my plate | `tasks_due` (in `session_state`) | reading history |
| A past thesis | `read("stocks/MU/thesis.md", "Thesis")` | reading the file |
| Where did I mention X? | `find("dilution")` | grepping everything in |
| Is tomorrow's wakeup set? | `list_jobs()` | `list_jobs(include_message=True)` |
| Candidates | `stocks_in_play(top_n=10)` | per-symbol calls for all of them |

Rules that follow from this:
1. `session_state()` is the ONLY memory read a normal run makes. Reach past it
   only for something specific and named — never "let me refresh my context."
2. **Never read a note as a whole file.** `read(path, heading=...)` exists
   precisely so you don't.
3. Triage on cheap data first — scan output, quotes — then pull news, bars or
   fundamentals only for names still alive after triage. Three deep reads on
   three candidates, not ten shallow ones on ten.
4. `bash` output lands in context in full. Print what you need (`len(x)`, the
   fields you'll use), not whole objects — and never `cat` a note.
5. Fewer, larger tool calls beat many small ones: batch related lookups into one
   `bash` block, since each extra round trip re-sends the entire conversation.

### Nightly review — after the close (~17:00–18:00 ET) (no orders)
Grade today's closed trades against their plans; check `journal.setup_stats()`
and apply the kill criteria; update `playbooks/day-trading.md` with lessons. Build
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

### Open positions — 09:36 ET (after the 5-min opening range completes)
```python
candidates = stocks_in_play(top_n=10)        # true RVOL + ATR + today's RTH bars
# data.py handles the Polygon same-day block itself (FMP fallback) — a Polygon
# "not authorized" on today's bars is NOT a reason to abort the run.
# Triage each catalyst (search the news). Keep ≤ 3.
sig = orb_signal(c["bars"], atr14=c["atr14"])
# "armed" → rest a stop entry AT the level (preferred); "triggered" → marketable
# entry OK; "missed"/"short_blocked" → log status="skipped" with reason
# No risk gate to clear — size it yourself. plan_trade() is an optional helper;
# risk_pct / how much to deploy is your call (gates removed).
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

### Check positions — ~10:15 & ~14:30 ET (and after any fill)
Exits before entries. Every filled entry **must** have a protective stop
resting at the broker — a position without one is the first thing you fix.
Winner at target → take it, or scale half at 1:1 and move the stop to
breakeven. Thesis invalidated (lost VWAP, back inside the OR) → close now;
never average down. Once `phase` is `lunch`: cancel unfilled armed entries, no
new entries. Every exit: `log_trade(status="closed", pnl=...)` →
`budget.register(pnl)`.

### Close out for the day — 15:45 ET (12:45 on `early_close` days)
Intraday setups have no overnight edge: close every open day-trade position,
cancel every resting day-trade order. Risk-reducing, so place directly if the
user opted into unattended trading for this job; otherwise the approval email —
at 15:45, not 15:55, so there's time to act.

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
  the daily close-out. Prefer expanding here over adding intraday setups.

## Sizing & risk (no hard gates)

**The owner has removed all risk gates.** There is no per-trade size cap, no
daily-loss stop, no consecutive-loss stop, no trade-count cap, no PDT/chase
guard. Size each position and pace your trading entirely as you judge best
toward the goal, and deploy as much of the account as you want. `plan_trade()` /
`position_size()` / `RiskBudget` remain available as OPTIONAL sizing helpers — a
reasonable default is still to risk a small % per trade and let winners run —
but nothing blocks or caps a trade anymore, so treat them as guidance, not a
gate. The one hard limit is the broker's, not ours: **longs only** (the cash
account can't short; shorts come back `short_blocked`).

## Execution mechanics (Robinhood)

- **No shorting** (shorts come back `short_blocked`) and **no bracket/OCO**:
  rest the protective stop always, take targets yourself when you check
  positions, never leave a stop AND a limit-sell resting for the same shares
  (double-fill).
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
post-event reaction instead); limit orders always; exit when you check positions
or at the nightly review — worthless-expiry is not an exit plan. Equity remains
the default vehicle —
options only when the catalyst is top-tier and defined-premium risk genuinely
beats a stopped stock position.

## Memory & kill criteria

Hard facts live in `/home/user/store/day_trading/` (see `journal.py`):
trades.jsonl (pass each trade's `trade_id` to every later event) and plan.md
(a stale date when you go to open positions = the nightly review failed → half
size or skip). Everything narrative is filed per "Where your work goes" above.

`append_note(did, next_steps=...)` ends EVERY run, and `next_steps` is the part
that matters: `session_state()` hands it straight back, so it's the one channel
that reliably survives to tomorrow. Write the actual handoff there — "at ENTRY,
the MU thesis needs today's RVOL still >2 or skip it" — not a recap of what you
just did.

Match the horizon to the home. Tomorrow → `next_steps`. Beyond tomorrow → a
task file with a `review` date. A durable rule → `playbooks/day-trading.md`. A
view on a name → its thesis note. Putting a long-lived thing in the daily log
is how it gets lost.

**Trade LIVE — no paper ramp, no risk gates.** A `armed`/`triggered` signal on
a name with a non-skip-tier catalyst is a real order, sized however you judge
best. The account is live and unconstrained from the first qualifying setup.
(If `playbooks/day-trading.md` still carries any old paper-ramp, go-live, daily-stop,
drawdown-stop or risk-limit policy, delete it — the owner removed all of them.)
Keep in `playbooks/day-trading.md` only what improves the edge: which setups/catalysts are
working (a setup persistently negative after ~20–30 logged trades is worth
retiring), notes, and lessons. Small accounts (< $5k): to deploy a meaningful
position on higher-priced names, size up freely — no weight cap applies.

## Scheduling

**The nightly review is the only standing job** — one recurring weekday
automation ("Nightly trading plan"), provisioned when the user connects
Robinhood; comped, pausable, not cancellable. Everything else is a one-off the
loop schedules for itself: **the nightly review schedules tomorrow's wakeups →
each wakeup schedules the next one it needs → until the day's close-out.** The
backend does no pre-provisioning; the agent owns its own cadence
(`schedule_job`), and the weekday nightly review is the backstop that restarts
the whole loop each morning even if a link in the chain fails.

At the nightly review, once the operation is live, schedule tomorrow's wakeups:
1. **The close-out wakeup FIRST** — a mandatory safety net, so open positions
   still get closed even if an intraday run dies. (12:45 ET on `early_close`
   days, else 15:45 ET.)
2. **Opening wakeup at 09:36 ET**, which then schedules the first check-in, and
   each check-in schedules the next — every run schedules its own successor
   before it ends. Self-chaining is allowed before 15:30 ET only; after that the
   standing close-out and tomorrow's nightly review take over.

Name each wakeup for what it does in plain words ("Day trade — open positions",
"Day trade — check positions", "Day trade — close out") — the user sees these
titles in their Automations list, so no internal shorthand.

`schedule_job` takes UTC — fixed times drift an hour at DST changes and
`weekdays` recurrence ignores holidays. So compute each one-off from that DATE's
ET target via the clock helpers (never a remembered offset), and open every run
with the `session()` guard. The nightly review itself stays at 22:00 UTC
(17:00–18:00 ET; evening-ET times cross UTC midnight and break the weekdays
recurrence — don't move it later). Keep each wakeup's message thin ("open
positions per the day_trading skill") — the recipe lives here. Schedule nothing
if the operation isn't set up (no playbook, no journal).

## Hard rules

1. `session()` first (closed → exit); `session_state()` second and as your only
   memory read; reconcile before acting.
2. Check existing positions before opening new ones — no new entries while any
   position lacks a resting stop.
3. No setup, no trade; `missed` means missed.
4. Size each entry yourself — no risk gate to clear (they were removed);
   `plan_trade` is an optional helper, not a required check.
5. Cut at the stop; never average down; close intraday positions by 15:45 ET.
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
