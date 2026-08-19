# Routines

A **Routine** is a standing request the user makes in chat and Finch carries out
on its own — a morning brief, a watch on a filing feed, a rebalance-if-I-drift.
This doc pins the model so the backend cleanup and the frontend build to the same
thing.

> **Status:** design agreed, not built. The scheduling engine (`scheduled_jobs` +
> the waker) already exists; "Routine" is the user-facing name for it plus a
> config surface and plan gating. Another session is concurrently refactoring
> `notifications.py` / `main.py` / `system_jobs.py` — this spec is written to sit
> on top of that cleanup, not fight it.

## The one-paragraph model

The user **never learns a new concept**. They ask in plain English (*"tell me if
NVDA drops 5%"*, *"email me a summary every morning"*); Finch recognizes a
standing request and sets it up; results arrive as **notifications**; the user
tunes them in a **Routines** list (each row in their own words, each with an
on/off). "Routine" is the only new word, and it's a familiar one (Apple/Google/
Alexa). Everything underneath is invisible to the user.

## Three user-facing surfaces, all pre-known

| Surface | Word | What it is |
|---|---|---|
| Make one | **chat** | the user just says it; the agent confirms *"Got it — it's in your Routines."* |
| See/manage | **Routines** | a plain list, each row phrased in the user's words, on/off toggle, "last run" |
| Receive | **Notifications** | tell-me (push/email) or ask-me (approval) — both already exist |

There is no config form, no trigger/outcome jargon, no watch-DSL. The user types
a sentence; the agent decides schedule + instructions from it.

## Under the hood: Routine = a `scheduled_jobs` row

Nothing new to build in the engine. A Routine **is** a `ScheduledJob`
(`services/job_scheduler.py`, `models/jobs.py`), run by the existing waker.
`run_job` already hands the row's `message` to the full agent, as the user, in
their E2B sandbox:

```python
# job_scheduler.py — run_job()
service.send_message_stream(message=job.message, user_id=job.user_id, auth_token=...)
```

So **a run is a normal agent session** — it writes and runs whatever code it
needs (FMP, widgets, diffs), then `report_insight(...)` to notify. The
instructions are the logic; there is no separate condition language.

A Routine row varies in only three things:

| | field | notes |
|---|---|---|
| **when** | `recurrence` / `run_at` | `daily`, `weekdays`, `hourly`, `every_<N>m` |
| **what** | `message` | plain-English instructions the agent runs (arbitrary code included) |
| **memory** | — | how a watcher remembers across runs: durable sandbox memory (`memory_write(durable=True)` → `/home/user/MEMORY.md`) or the `agent_events` ledger. Heartbeat already works this way ("each run is a FRESH chat and the ledger is your memory"). |

Morning brief and heartbeat are already rows in this table — they become
Routines by renaming, not migrating.

## Plan gating

Routines spend real resources (each run = a sandbox agent session = credits), so
free is capped and Pro is opened up. Enforced at provision time in `schedule()`,
which already has an `enforce_limits` path and `_count_active`.

| | Free | Pro |
|---|---|---|
| **Max active routines** | **2** | unlimited (soft cap, e.g. 50, to bound abuse) |
| **Runs per day** (shared across all the user's routines) | **5** | unbounded (credits are the bound) |
| **Minimum interval** | **1 hour** (`every_<N>m` ⇒ N ≥ 60) | **5 minutes** (N ≥ 5) |
| **Credits** | charged per run | charged per run |

The **daily run cap is the primary free-tier cost lever** — it bounds spend
directly regardless of how the routines are configured. The interval floor stays
only so a single routine can't burn the whole daily budget in five minutes; with
a 5-run/day cap it's a guardrail, not the main control.

Implementation levers:
- **Count cap** — `RECURRING_LIMIT` (currently a flat `5`) becomes plan-aware:
  read `CreditsService.get_user_plan(db, user_id)`, cap at 2 for free / high for
  Pro. Reuse `_count_active(db, user_id, recurring=True)` in `schedule()`.
- **Daily run cap** — enforced in the waker, not at provision time. Before
  running a user routine, `_claim_due` / `run_job` counts today's user-routine
  runs for that user and **skips** (does not run, does not advance credit spend)
  once ≥ 5. `run_count` is lifetime, so this needs a per-day count — cheapest is
  a COUNT over `agent_events` (source `scheduled_job`) since local midnight, or a
  small per-user daily counter. Built-ins (`system_key` set) are exempt from the
  count.
- **Interval floor** — validate `recurrence` in `schedule()`: parse `every_(\d+)m`,
  reject `N < 60` for free / `N < 5` for Pro, with an error the chat agent relays
  ("Checking more often than hourly needs Pro").
- **Built-ins are exempt** — Finch-provisioned rows (`system_key` set,
  `enforce_limits=False`) skip all three caps, exactly as today. Only
  user-created routines are gated.

### The one wrinkle: graceful degradation at the cap

A daily run cap means a free routine can **stop mid-day** — a routine set to
check hourly runs at 7/8/9/10/11am, hits 5, and goes quiet until midnight. That
reads as "my routine broke" unless it's surfaced. Handle it, don't hide it:
- The Routines list shows a budget line: **"3 of 5 daily runs used."**
- When a run is skipped for budget, drop **one** quiet ledger note ("Paused for
  today — Pro removes the daily limit"), not a push, and never repeat it.
- Skipped runs are **not** charged and **not** retried; the schedule resumes at
  midnight. A skipped run must still advance `run_at` so it doesn't re-fire in a
  loop (same discipline as the deploy re-fire bug — advance on skip).

### Credits — charge correctly

- User routines run with `comped=False` (the default) → the run's token spend is
  deducted from the user's balance in `run_job`, at the correct model rate.
  (The Aug 2026 pricing fix in `credits.py` is a prerequisite: Fable/Haiku were
  mispriced and would over/under-charge routine runs.)
- Built-in routines (morning brief, heartbeat) keep `comped=True` — Finch eats
  the cost, refunded post-run.
- A Routine's row already tracks `last_run_credits` / `credits_spent`, so the
  Routines list can show the user what each one costs them.

## Transparency (required — the caps are only OK if these are all true)

A cap the user can't see reads as a broken feature. Every limit must be visible,
every run accountable, and the way out always one tap away. The Routines surface
must show:

1. **The limits, plainly** — "Free: 2 routines, 5 runs/day." Not buried in docs;
   on the Routines screen.
2. **Usage against them** — "2 of 2 routines · 3 of 5 runs used today." Live, so
   the user knows where they stand before a routine goes quiet.
3. **Per-run history with outcome** — each run shows when it ran and what
   happened: **ran** (with the result / a link to its run-chat `job-{id}-r{n}`),
   **skipped** (with the reason — "daily limit reached"), or **failed** (with a
   short error). Ran-runs already produce run-chats + `agent_events`; **skipped
   runs must write their own record** (a ledger row with the skip reason) so the
   history never has silent gaps.
4. **A path to Pro at every friction point** — an upgrade CTA on the limit line,
   on the skip note, and when creating routine #3 or choosing a sub-hourly
   interval. The message names the specific unlock ("Pro: unlimited routines and
   checks every 5 min"), not a generic paywall.

This turns each cap from a wall into a visible, fair boundary with a door.

## What's net-new vs reused

| Piece | State |
|---|---|
| Scheduling engine (`scheduled_jobs`, waker, `run_job`) | ✅ exists |
| Agent-runs-arbitrary-code on a schedule | ✅ exists (`run_job` → `ChatService`) |
| Durable cross-run memory | ✅ exists (`memory_write(durable=True)`, ledger) |
| Notification delivery + approvals | ✅ exists (`notifications.py`, pending-trade approvals) |
| Plan-aware count cap + interval floor | 🔨 new — small change in `schedule()` |
| `skills/routines/SKILL.md` (agent contract: schedule + instructions + report_insight + durable memory + FMP/widget watch) | 🔨 new file |
| `/routines` user surface (list/toggle/delete; likely reuses `routes/jobs.py`) | 🔨 mostly exists as `/jobs`; needs the Routines framing |
| Rename automations/heartbeat/monitor → Routines in the UI | 🔨 frontend (web + mobile parity) |

## Non-goals (v1)

- No condition DSL — the agent's code is the condition.
- No new table — Routines are `scheduled_jobs`.
- No user-facing trigger/outcome vocabulary — the user types a sentence.
- Tasks (`agent_tasks`, the to-do tracker) are unrelated and untouched.
