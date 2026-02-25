# Kalshi API

Kalshi prediction market trading (authenticated). **REQUIRES API KEYS**

## API Design

All functions require authentication via API keys (automatically configured in environment).
**All functions are synchronous (no `await` needed).** They handle async internally.

```python
from servers.kalshi.portfolio import get_kalshi_balance, get_kalshi_positions
from servers.kalshi.markets import get_kalshi_events, get_kalshi_market
from servers.kalshi.trading import place_kalshi_order

# Check balance (synchronous - no await needed)
balance = get_kalshi_balance()
print(f"Balance: ${balance['balance']:.2f}")

# Get positions
positions = get_kalshi_positions(limit=10)

# Browse markets
events = get_kalshi_events(limit=20, status="open")

# Get specific market with pricing
market = get_kalshi_market(ticker="KXBTC-23DEC31-T100000")
```

## Functions

**All functions are synchronous (no `await` needed).**

### portfolio.py

- `get_kalshi_balance()` → dict
  - Returns `{"balance": float, "portfolio_value": float}` (in dollars)

- `get_kalshi_positions(limit: int = 100)` → dict
  - Returns `{"positions": [...], "count": int}`

- `get_kalshi_portfolio()` → dict
  - Returns combined balance + positions

### markets.py

- `get_kalshi_events(limit: int = 20, status: str = "open")` → dict
  - Returns `{"events": [...], "count": int}`
  - Status: "open", "closed", or "settled"

- `get_kalshi_market(ticker: str)` → dict
  - Returns market details including yes_bid, yes_ask, volume, open_interest (prices in cents)

### trading.py

- `place_kalshi_order(ticker, side, action, count, order_type="market", price=None)` → dict
  - `side`: "yes" or "no"
  - `action`: "buy" or "sell"
  - `order_type`: "market" (default) or "limit"
  - `price`: cents (1-99), required only for limit orders

- `get_kalshi_orders(ticker=None, status="resting")` → dict
  - Returns `{"orders": [...], "count": int}`
  - Status: "resting", "pending", "executed", "canceled"

- `cancel_kalshi_order(order_id: str)` → dict
  - Returns `{"order_id": str, "status": "canceled"}`

## Identifiers

- **ticker**: Market ticker (e.g., "KXBTC-23DEC31-T100000")
- **event_ticker**: Event series ticker
- **order_id**: Order identifier for cancellation

## Authentication

API keys are pre-configured in environment variables. No manual setup needed.

## Models

See `kalshi/models.py` (via `read_chat_file(filename="kalshi/models.py", from_api_docs=True)`) for Pydantic models if available, otherwise responses are dictionaries.
