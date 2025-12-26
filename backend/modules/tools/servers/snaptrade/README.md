# SnapTrade Server

Secure OAuth access to user brokerage accounts (Robinhood, TD Ameritrade, E*TRADE, etc.)

## Security Architecture

- **OAuth Flow**: Users authenticate directly with their brokerage via SnapTrade
- **No Credentials Stored**: Your app never sees or stores brokerage passwords
- **Persistent Connection**: Once connected, users don't need to re-authenticate
- **Encrypted Storage**: Connection tokens securely managed by SnapTrade

## Discovery Pattern

**1. List available tools:**
```python
import os
os.listdir('servers/snaptrade')  # ['portfolio', '_client.py', 'api.py', 'README.md']
```

**2. Explore portfolio tools:**
```python
os.listdir('servers/snaptrade/portfolio')
# ['get_holdings.py', 'get_accounts.py', 'request_connection.py']
```

**3. Read a tool to see its signature:**
```python
with open('servers/snaptrade/portfolio/get_holdings.py') as f:
    print(f.read())
```

**4. Import and use:**
```python
from servers.snaptrade.portfolio.get_holdings import get_holdings

holdings = await get_holdings(user_id)
if holdings['success']:
    print(holdings['data']['csv'])  # Portfolio in CSV format
```

## Available Tools

### Portfolio Management

#### `get_holdings(user_id: str)`
Get user's current portfolio holdings from all connected accounts.

**Returns:**
- Holdings data in CSV format
- Total portfolio value
- Individual positions with quantities and values
- `needs_auth=True` if user hasn't connected brokerage yet

**Example:**
```python
from servers.snaptrade.portfolio.get_holdings import get_holdings

result = await get_holdings('user-123')

if result['success']:
    csv_data = result['data']['csv']
    print(csv_data)  # Ticker, Quantity, Value, etc.
elif result.get('needs_auth'):
    # User needs to connect brokerage
    print("Please connect your brokerage account first")
```

#### `get_accounts(user_id: str)`
List all connected brokerage accounts.

**Returns:**
- Account details (name, type, balance, institution)
- Total count of connected accounts

**Example:**
```python
from servers.snaptrade.portfolio.get_accounts import get_accounts

result = await get_accounts('user-123')

if result['success']:
    for account in result['accounts']:
        print(f"{account['institution']}: ${account['balance']:,.2f}")
```

#### `request_connection(user_id: str)`
Generate OAuth URL for user to connect their brokerage.

**Returns:**
- OAuth connection URL
- Instructions for user

**Example:**
```python
from servers.snaptrade.portfolio.request_connection import request_connection

result = request_connection('user-123')

if result['success']:
    print(f"Connect your brokerage at: {result['connection_url']}")
```

## Typical Workflow

```python
import sys
sys.path.insert(0, 'servers')

from snaptrade.portfolio.get_holdings import get_holdings
from snaptrade.portfolio.request_connection import request_connection

# Try to get portfolio
result = await get_holdings(user_id)

if result['success']:
    # User is connected - show portfolio
    print(result['data']['csv'])
    
elif result.get('needs_auth'):
    # User needs to connect - generate OAuth URL
    auth = request_connection(user_id)
    print(f"Connect at: {auth['connection_url']}")
```

## OAuth Connection Flow

1. **Check if connected:** Call `get_holdings()` first
2. **If needs_auth:** Call `request_connection()` to get OAuth URL
3. **User authenticates:** Visits URL, logs into brokerage via SnapTrade
4. **Auto-redirect:** SnapTrade redirects back to your app
5. **Connection persists:** User never needs to re-authenticate
6. **Access portfolio:** Call `get_holdings()` anytime

## Supported Brokerages

SnapTrade supports 20+ brokerages including:
- Robinhood
- TD Ameritrade
- E*TRADE
- Charles Schwab
- Fidelity
- Interactive Brokers
- Webull
- And more...

## Why SnapTrade?

- **No credential storage** - OAuth only
- **Battle-tested security** - Used by fintech companies
- **Persistent connections** - Users authenticate once
- **Real-time data** - Live portfolio updates
- **Multi-brokerage** - Aggregate across accounts

