---
name: finch_api
description: Call the Finch backend directly from the sandbox to sync and fetch brokerage transactions, portfolio data, and other resources that require server-side credentials.
metadata:
  emoji: "🔗"
  category: backend
  is_system: true
  auto_on: true
  requires:
    env: []
    bins: []
---

# Finch Backend API

Call the Finch backend directly from the sandbox. Use this whenever you need data that requires server-side credentials (e.g. SnapTrade user_secret) that are NOT available in the sandbox.

**IMPORTANT**: Do NOT try to call SnapTrade or other credential-gated APIs directly from the sandbox. Use this client instead — it calls the backend which has the credentials.

## Usage

```python
from skills.finch_api.scripts import sync_transactions, get_transactions, finch_api

# Sync brokerage transactions into the DB (triggers server-side SnapTrade fetch)
result = sync_transactions()
# result: {"success": true, "transactions_fetched": 42, "transactions_inserted": 10, ...}

# Fetch synced transactions from the DB
txns = get_transactions(symbol="AAPL", limit=50)
# txns: [{"symbol": "AAPL", "type": "BUY", "date": "...", "data": {...}}, ...]

# Fetch all transactions in a date range
txns = get_transactions(start_date="2025-01-01", end_date="2026-01-01")

# Generic: call any backend endpoint
data = finch_api("GET", "/api/some/endpoint", params={"key": "value"})
```

## Available Functions

### `sync_transactions(start_date=None, end_date=None, force_resync=False)`
Triggers a server-side sync of brokerage transactions from SnapTrade into the database. Defaults to last 12 months. Returns sync stats (fetched, inserted, updated counts).

### `get_transactions(symbol=None, start_date=None, end_date=None, limit=100)`
Fetches previously synced transactions from the database. Max limit is 500. Returns a list of transaction dicts.

### `finch_api(method, path, params=None, body=None)`
Generic escape hatch to call any backend API endpoint. User auth is automatically injected.

## Error Handling

- `FinchAuthError` — 401/403, token expired or invalid
- `FinchAPIError` — other HTTP errors (4xx/5xx)
- `FinchConnectionError` — backend unreachable

## Dates

Use ISO format strings: `"2025-06-01"` or `"2025-06-01T00:00:00"`.
