---
name: finch_api
description: "The user's Finch account. SCHEDULE AUTOMATIONS from any chat — schedule_job() creates a wakeup (one-off or recurring) that runs an instruction later; use it whenever the user says remind me / every morning / check daily / alert me when / keep an eye on. Also: propose catalyst trade ideas and read their scorecard, request one-click trade approval, report insights to the activity ledger, send the morning brief, search past chats, and sync/query connected brokerage transactions and holdings."
metadata:
  emoji: "🏦"
  category: brokerage
  is_system: true
  auto_on: true
  requires:
    env: []
    bins: []
---

# Connected Accounts

Access the user's connected brokerage data from the sandbox. All requests go through the Finch backend, which holds the SnapTrade credentials — **do NOT try to call SnapTrade or any brokerage API directly from the sandbox**.

## How It Works

The sandbox has `FINCH_API_URL` and `FINCH_AUTH_TOKEN` env vars. This client uses them to call the backend, which authenticates the user and talks to SnapTrade on their behalf. Data flows sandbox → backend → sandbox without touching agent context.

## Server-Side Tools (use these directly, not from sandbox)

These tools are available as agent tools and run server-side. Call them normally:

- **`get_brokerage_status`** — check if user has a connected brokerage, account count, account details
- **`get_portfolio`** — current holdings with prices, P&L, cost basis (call `get_brokerage_status` first)
- **`connect_brokerage`** — initiate OAuth flow to connect a new broker

## Sandbox Client (for data the tools don't cover)

Use this when you need **transaction history**, **activity logs**, or other brokerage data not available through the server-side tools above.

```python
from skills.finch_api.scripts import sync_transactions, get_transactions, finch_api
```

### Sync Transactions

Triggers a server-side fetch of brokerage transactions from SnapTrade into the database. Call this before querying transactions if the data might be stale.

```python
result = sync_transactions()
# {"success": true, "transactions_fetched": 42, "transactions_inserted": 10, ...}

# With date range
result = sync_transactions(start_date="2025-01-01", end_date="2026-01-01")

# Force re-sync even if recently synced
result = sync_transactions(force_resync=True)
```

### Get Transactions

Fetch previously synced transactions from the database. Always call `sync_transactions()` first if data might be stale.

```python
# All recent transactions
txns = get_transactions(limit=200)

# Filter by symbol
txns = get_transactions(symbol="AAPL")

# Date range
txns = get_transactions(start_date="2025-06-01", end_date="2026-01-01")
```

Each transaction has:
- `symbol` — ticker (e.g. "AAPL")
- `type` — BUY, SELL, DIVIDEND, TRANSFER, FEE, INTEREST, SPLIT
- `date` — ISO timestamp
- `data` — dict with `quantity`, `price`, `fee`, `total_amount`, `currency`, `description`

### Generic API Call

Call any backend endpoint:

```python
data = finch_api("GET", "/api/some/endpoint", params={"key": "value"})
data = finch_api("POST", "/api/some/endpoint", body={"key": "value"})
```

User auth is automatically injected.

## Error Handling

```python
from skills.finch_api.scripts.client import FinchAuthError, FinchAPIError, FinchConnectionError

try:
    txns = get_transactions()
except FinchAuthError:
    print("Auth token expired — user may need to start a new session")
except FinchAPIError as e:
    print(f"Backend error: HTTP {e.status}")
except FinchConnectionError:
    print("Cannot reach backend")
```

## Common Workflow: Portfolio + Transaction Analysis

```python
# 1. Use the server-side tools for current portfolio
#    (call get_brokerage_status, then get_portfolio as agent tools)

# 2. Sync and fetch transaction history in sandbox code
from skills.finch_api.scripts import sync_transactions, get_transactions

sync_transactions()  # ensure DB is up to date
txns = get_transactions(limit=500)  # max 500 per request

# 3. Analyze in pandas, build charts, etc.
import pandas as pd
df = pd.DataFrame([
    {
        "symbol": t["data"]["symbol"] if "symbol" in t.get("data", {}) else t["symbol"],
        "type": t["type"],
        "date": t["date"],
        "quantity": t["data"].get("quantity"),
        "price": t["data"].get("price"),
        "total": t["data"].get("total_amount"),
    }
    for t in txns
])
```

## Notes

- Transaction sync defaults to the last 12 months
- Max 500 transactions per `get_transactions()` call — paginate with date ranges for more
- Sync has a 5-minute cooldown to avoid hammering SnapTrade
- Dates use ISO format: `"2025-06-01"` or `"2025-06-01T00:00:00"`
- Activity types: BUY, SELL, DIVIDEND, INTEREST, TRANSFER, FEE, SPLIT

## Scheduled Jobs

Schedule work to run later — one-off or recurring. Running a job = the backend sends your `message` to the agent (as the user) at the scheduled time, so it runs with full tools (notifications, portfolio, web, etc.).

**Alerts are just recurring jobs**: e.g. a daily job whose message is "Check if NVDA is below $200; if so, notify me, otherwise do nothing."

```python
from skills.finch_api.scripts import schedule_job, list_jobs, update_job, cancel_job

# One-off in 30 minutes
schedule_job("Summarize today's market close for my watchlist", in_minutes=30, name="Market close recap")

# Recurring alert (checks + notifies only if met)
schedule_job(
    "Check if NVDA is below $200. If yes, notify me. If not, do nothing.",
    run_at="2026-06-02T13:30:00Z", recurrence="weekdays", name="NVDA dip alert",
)

list_jobs()                              # {"jobs": [...], "recurring": "1/5", "oneoff": "0/10"}
update_job("<id>", run_at="2026-06-03T14:00:00Z")   # modify
cancel_job("<id>")                       # cancel
```

Write the `message` as a **self-contained instruction** — it runs fresh with no prior chat context. Include everything needed. Limits per user: **5 recurring + 10 one-off**; if a limit is hit you'll get an error — tell the user and offer to cancel one.

## Trade Approval (one-click email)

When an automation wants to place a **real** trade but shouldn't trade unattended,
stage it for the user to approve from an email. The user clicks **Approve** and the
backend places the order — you never place it directly.

```python
from skills.finch_api.scripts import request_trade_approval

# After reviewing the order (see the robinhood skill's review_order):
res = request_trade_approval(
    account_number=acct,
    order_params={"symbol": "AAPL", "side": "buy", "type": "market", "dollar_amount": "100.00"},
    summary="BUY $100 of AAPL (market) — est. ~0.45 sh @ $221.30",
    ttl_minutes=60,
)
# {"token": "...", "status": "pending", "expires_at": "...", "email_sent": true}
```

- `order_params` mirrors the Robinhood order args **without** `account_number`
  (pass that separately): `symbol`, `side`, `type`, `quantity`|`dollar_amount`,
  `limit_price`, …
- The link **expires** (default 60 min, 5–1440) — if it lapses, no trade is placed.
- This is the **default path for automated trading**: review → email for approval.
  Only place orders directly (in the robinhood skill) when the user has explicitly
  opted into unattended execution for that automation.

## Morning Brief Delivery

The daily morning-brief automation (system job `morning_brief`) composes a short
markdown digest of the user's holdings + watchlist and delivers it with:

```python
from skills.finch_api.scripts import send_morning_brief

send_morning_brief(
    subject="Finch brief: NVDA +4% pre-market",
    markdown="## Your stocks\n- **NVDA** +4% pre-market on ...",
)
# {"email": true, "push": true}
```

The backend emails the rendered brief (Resend) and sends a push notification.
Only use this from the morning-brief automation — for ad-hoc chat results the
normal chat-completion notification already covers delivery.

## Judging a Move (every proactive update)

Finch's updates must be deliberate: for every move you mention, say **why** it
moved and **whether it matters**. Before you characterize a move, get the
measured read:

```python
from skills.finch_api.scripts import explain_move

r = explain_move("TSLA")
# {"verdict": "noise", "driver": "macro",
#  "headline": "Broad market selloff ahead of earnings",
#  "explanation": "...", "watch": "Q3 earnings Oct 21 — margins, robotaxi timeline",
#  "context": {"typical_move_pct": 1.61, "move_multiple": 1.3, "spy_change_pct": -1.11,
#              "sector_change_pct": -0.84, "idiosyncratic_pct": -1.29,
#              "volume_ratio": 1.6, "earnings": "Earnings are due in 3 day(s)", ...}}
```

The framework (same rubric the app's alerts, digest and "why is it moving" use —
source of truth is `services/monitoring/move_context.py::FRAMEWORK`):

1. **Unusual for this stock?** Today vs its typical daily move: <1.5x routine,
   1.5–3x notable, >3x a real event. 5% is huge for KO and quiet for a biotech.
2. **Driver: macro, sector or company.** Macro = the whole market moved (rates,
   Fed, inflation/jobs data, dollar, oil, geopolitics). Sector = peers and the
   sector ETF moved together. Company = it moved on its own (earnings, guidance,
   analyst action, product, legal/regulatory, management, deal).
3. **Verdict — exactly one:**
   - `noise` — routine for the stock, or explained by market/sector with no
     company news. The investment case didn't change.
   - `news` — a real event that moves the price but fits the existing story
     (a beat that sells off on high expectations, a one-off).
   - `narrative_shift` — the reason people own or avoid it changed (guidance
     reset, competitive threat, regulatory/legal turn, management change, broken
     thesis). Rare — most days are not this.
4. Ground everything in sources; never invent news. If the cause is unclear,
   say so and lean `noise`.
5. Close with what would confirm or change the call (next print, a date, a level).

Write macro and micro separately: lead with the day's macro/sector theme only if
it actually drove the user's names, then the company-specific stories. Saying
"nothing changed the story" is a useful update; padding is not.

## Reporting Insights (heartbeat & automations)

When an automation (especially the `heartbeat` system job) finds something the
user should know — an unusual move in a holding, news that changes a thesis, a
risk building in their portfolio — report it to their activity ledger:

```python
from skills.finch_api.scripts import report_insight

report_insight(
    title="NFLX -9% on a subscriber-guidance cut — story change",
    body="Guidance now implies flat net adds into 2027 — the growth case rested on 8%+.\n"
         "6.4x its typical move on 3x volume; the market was flat, so this is all company.\n"
         "Watch: management's ad-tier commentary on Thursday's call.",
    alert=True, verdict="narrative_shift", driver="company", symbol="NFLX",
)
# {"recorded": true, "alerted": false}
```

Always pass `verdict`, `driver` and `symbol` — the app labels the insight with
them. `alert=True` ALSO sends a push notification — reserve it for urgent,
decision-relevant items a holder should know about right now, and never for
`noise`. A wrong alert
erodes trust fast; when in doubt, record without alerting. The insight shows
up in the user's "while you were gone" recap and activity feed.

## Agent Memory (fresh-chat runs)

Heartbeat runs each start in a FRESH chat — cross-run memory is queried, not
accumulated:

```python
from skills.finch_api.scripts import list_events, search_past_chats

list_events(limit=15)                    # the ledger: what you already reported
list_events(event_type="insight")        # just your insights
search_past_chats("GTLB thesis")         # dig into earlier conversations
```

Call `list_events()` FIRST in a heartbeat run so you never repeat yourself.
Reach for `search_past_chats()` only when the ledger isn't enough — it does a
content search across all the user's chats, including previous automation runs.
