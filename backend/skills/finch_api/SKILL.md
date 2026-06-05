---
name: finch_api
description: Access the user's connected brokerage accounts — sync and query transaction history, get portfolio holdings, and manage account data. All brokerage operations go through the Finch backend which holds the credentials.
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
