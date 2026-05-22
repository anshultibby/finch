---
name: connected_accounts
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
