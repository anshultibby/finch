---
name: snaptrade
description: Connect and manage brokerage accounts via SnapTrade. View portfolio, trade stocks/options, manage orders, and access account data across 20+ brokers including Robinhood, Schwab, Fidelity.
homepage: https://snaptrade.com
metadata:
  emoji: "🏦"
  category: brokerage
  is_system: true
  auto_on: true
  requires:
    env:
      - SNAPTRADE_CLIENT_ID
      - SNAPTRADE_CONSUMER_KEY
    bins: []
---

# SnapTrade Skill

Connect and manage brokerage accounts via SnapTrade. Supports 20+ brokers including Robinhood, Schwab, Fidelity, E*Trade, and more.

## Authentication Flow

1. Call `request_connection()` to get OAuth link
2. User authorizes through broker's OAuth flow
3. Use any function with the returned user_id

## Available Scripts

### Portfolio

```python
from skills.snaptrade.scripts.portfolio.request_connection import request_connection
from skills.snaptrade.scripts.portfolio.get_accounts import get_accounts
from skills.snaptrade.scripts.portfolio.get_holdings import get_holdings
```

### Account Information

```python
from skills.snaptrade.scripts.account.get_balances import get_balances
from skills.snaptrade.scripts.account.get_positions import get_positions
from skills.snaptrade.scripts.account.get_orders import get_orders
from skills.snaptrade.scripts.account.get_activities import get_activities
from skills.snaptrade.scripts.account.get_holdings_detail import get_holdings_detail
from skills.snaptrade.scripts.account.get_option_holdings import get_option_holdings
from skills.snaptrade.scripts.account.get_return_rates import get_return_rates
```

### Trading

```python
from skills.snaptrade.scripts.trading.get_quotes import get_quotes
from skills.snaptrade.scripts.trading.place_order import place_order
from skills.snaptrade.scripts.trading.preview_order import preview_order
from skills.snaptrade.scripts.trading.cancel_order import cancel_order
from skills.snaptrade.scripts.trading.place_option_order import place_option_order
```

### Connection Management

```python
from skills.snaptrade.scripts.connections.list_connections import list_connections
from skills.snaptrade.scripts.connections.refresh_connection import refresh_connection
from skills.snaptrade.scripts.connections.disconnect_account import disconnect_account
from skills.snaptrade.scripts.connections.delete_connection import delete_connection
```

### Reference Data

```python
from skills.snaptrade.scripts.reference.search_symbols import search_symbols
from skills.snaptrade.scripts.reference.list_brokerages import list_brokerages
from skills.snaptrade.scripts.reference.get_symbol_detail import get_symbol_detail
from skills.snaptrade.scripts.reference.list_currencies import list_currencies, get_exchange_rate
from skills.snaptrade.scripts.reference.list_exchanges import list_exchanges
```

## Example: Trading Workflow

All functions take `user_id` as the first arg; account-scoped ones take `account_id` second.

```python
from skills.snaptrade.scripts.reference.search_symbols import search_symbols
from skills.snaptrade.scripts.trading.get_quotes import get_quotes
from skills.snaptrade.scripts.trading.preview_order import preview_order
from skills.snaptrade.scripts.trading.place_order import place_order
from skills.snaptrade.scripts.account.get_orders import get_orders
from skills.snaptrade.scripts.trading.cancel_order import cancel_order

# 1. Search for symbol to get universal symbol ID
symbols = search_symbols('user-123', 'acct-456', 'AAPL')
symbol_id = symbols['symbols'][0]['id']

# 2. Get quote
quotes = get_quotes('user-123', 'acct-456', ['AAPL'])

# 3. Preview order (always preview before placing)
impact = preview_order('user-123', 'acct-456', 'BUY', symbol_id, 'Limit', 'Day', quantity=10, price=150.00)

# 4. Place order
order = place_order('user-123', 'acct-456', 'BUY', symbol_id, 'Limit', 'Day', quantity=10, price=150.00)

# 5. Check status / cancel if needed
orders = get_orders('user-123', 'acct-456', state='Executed')
cancel_order('user-123', 'acct-456', order['order']['brokerage_order_id'])
```

### Option Orders

```python
from skills.snaptrade.scripts.trading.place_option_order import place_option_order
legs = [
    {"symbol": "opt-id-1", "action": "BUY_TO_OPEN", "quantity": 1},
    {"symbol": "opt-id-2", "action": "SELL_TO_OPEN", "quantity": 1},
]
result = place_option_order('user-123', 'acct-456', 'Limit', 'Day', legs, price=2.50)
```

## Error Handling

All functions return `{"success": False, "error": "..."}` on failure.
Check for `needs_auth: True` to know if the user needs to reconnect.

## Notes

- `get_holdings` (portfolio) is async (requires `await`), all other functions are sync
- User must authorize through OAuth before accessing data
- Use `search_symbols` to get universal symbol IDs needed for trading
- Connections can expire -- use `refresh_connection` or reconnect
- Activity types: BUY, SELL, DIVIDEND, INTEREST, TRANSFER, FEE
- Order types: Market, Limit, StopLimit, StopLoss
- Time in force: Day, GTC (good til cancelled), FOK (fill or kill)
- Option actions: BUY_TO_OPEN, BUY_TO_CLOSE, SELL_TO_OPEN, SELL_TO_CLOSE
