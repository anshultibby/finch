---
name: routines
description: Set up a "routine" — a standing request the user makes in plain English that Finch carries out on its own, on a schedule (a morning brief, a watch on a filing feed, an alert when a stock moves). Use whenever the user asks for something recurring, scheduled, or "tell me when / keep an eye on / every morning".
metadata:
  emoji: "🔁"
  category: product
  is_system: true
  auto_on: true
  requires:
    env: []
    bins: []
---

# Routines

A **routine** is a standing request the user makes in chat and you carry out on
your own, on a schedule — *"email me a summary every morning"*, *"tell me if NVDA
drops 5%"*, *"let me know when there's a new 13-D filing on TSLA"*.

The user never learns a new concept: they just say it, you set it up, and you
confirm *"Got it — it's in your Routines."* Results reach them as notifications
(`report_insight`). Under the hood a routine is a scheduled job; you don't need
to know more than the calls below.

## Creating a routine

```python
from skills.finch_api.scripts.client import schedule_job

schedule_job(
    message="<instructions for the run — see below>",
    recurrence="daily",          # None | hourly | daily | weekdays | weekly | every_<N>m
    name="Morning summary",      # short, human — this is the label the user sees
)
```

`recurrence="every_15m"` is the form for sub-hourly checks. `run_at` (ISO-8601
UTC) or `in_minutes` sets the first run; default is 60 minutes out.

**The `message` is instructions to a future you.** Each run is a FRESH agent
session with your full toolset in the sandbox — so the message should say what to
do, and the run does it (fetches data, decides, notifies). Write it as if briefing
yourself with no memory of this conversation. Put the user's intent, the exact
symbols/thresholds, and what to send.

## The two shapes of a routine

**1. Always report** (a brief) — the run always produces output:

```
"Compose the user's morning summary: pull their portfolio + watchlist, the
overnight moves and any headlines that explain them, and send it with
send_morning_brief(subject, markdown). Keep it to what a holder would act on."
```

**2. Watch and only speak when it matters** (an alert) — the run checks a
condition and stays silent unless it's met:

```
"Check NVDA's day change (get_quote). If it's down 5% or more from the prior
close, report_insight(title, body, alert=True) explaining the move. Otherwise do
nothing — no news is the normal outcome."
```

Both are the same routine; the difference is entirely in the instructions.

## Remembering across runs (required for "new item" watches)

Each run is a fresh session — it does **not** remember prior runs. For a watch
like *"tell me on a NEW filing"*, the run must persist what it has already seen,
or it will re-alert on the same item every time. Two options:

- **Durable memory** — `memory_write(durable=True)` writes to `/home/user/MEMORY.md`,
  which every future run can read. Store the last-seen id / timestamp there.
- **The ledger** — `list_events()` returns what past runs reported; use it to
  check "did I already flag this?"

Pattern for a new-filing watch:

```
"Fetch recent institutional-ownership / insider filings for TSLA
(get_institutional_ownership / get_insider_trading). Read /home/user/MEMORY.md
for the last filing id you recorded. If there are filings newer than that,
report_insight(...) about them and memory_write the newest id (durable=True).
If nothing is new, do nothing."
```

## Connecting a routine to a widget

A routine can read a widget the user already has (`finch_api("GET",
f"/widgets/{id}/data")`) and alert on changes in it — so "watch my widget" is
just a routine whose instructions read that widget's tiles and compare to memory.

## Notifying the user

- `report_insight(title, body, alert=False)` — writes to the activity ledger
  ("while you were gone"). Quiet; the user sees it when they check.
- `report_insight(..., alert=True)` — ALSO sends a push. Reserve for urgent,
  decision-relevant things; a wrong alert erodes trust fast.
- `send_morning_brief(subject, markdown)` — the brief's email+push delivery.

`title` = one punchy line with numbers (≤80 chars). `body` = up to ~3 short
lines. Never alert on "nothing happened."

## Limits — know them and explain them

Routines spend credits every run (each run is a real agent session). Free is
capped; Pro opens it up. **These are enforced by the backend — a create that
exceeds them raises an error. Relay it plainly and offer the upgrade.**

| | Free | Pro |
|---|---|---|
| Active routines | 2 | unlimited |
| Runs per day (across all their routines) | 5 | unbounded |
| How often each can check | at most hourly | down to every 5 min |

When a user asks for something the free plan can't do (a 3rd routine, or checks
more often than hourly), say so in one line and name the specific unlock:
*"Free routines can have 2 running and check at most hourly — Pro lifts that to
unlimited and every 5 minutes. Want to upgrade, or should I set this up hourly
for now?"* Never silently downgrade what they asked for without telling them.

A free routine that hits its 5-runs-a-day budget goes quiet until tomorrow —
that's expected, not a failure. If a user asks why a routine stopped mid-day,
it's the daily run budget; the fix is Pro.

## Managing existing routines

- `list_jobs()` — what the user has, when each runs, health.
- `update_job(job_id, message=..., recurrence=...)` — change one.
- `cancel_job(job_id)` — remove one (frees a slot against the cap).

Built-in routines Finch provisions (morning brief, heartbeat) don't count against
the user's cap and are Finch-comped — leave those to their own configuration.
