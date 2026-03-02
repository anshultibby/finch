---
name: snaptrade
description: Connect and manage brokerage accounts via SnapTrade. View portfolio holdings, account balances, and trade history across 20+ brokers including Robinhood, Schwab, Fidelity.
homepage: https://snaptrade.com
metadata:
  emoji: "🏦"
  category: brokerage
  is_system: true
  requires:
    env:
      - SNAPTRADE_CLIENT_ID
      - SNAPTRADE_CONSUMER_KEY
    bins: []
---

# SnapTrade Skill

Connect and manage brokerage accounts via SnapTrade. Supports 20+ brokers including Robinhood, Schwab, Fidelity, E*Trade, and more.

## Authentication Flow

SnapTrade requires OAuth user authorization:

1. Call `request_connection()` to get OAuth link
2. User authorizes through broker's OAuth flow
3. Use `get_accounts()` and `get_holdings()` with returned user_id

## Import Pattern

```python
from skills.snaptrade.scripts.portfolio.request_connection import request_connection
from skills.snaptrade.scripts.portfolio.get_accounts import get_accounts
from skills.snaptrade.scripts.portfolio.get_holdings import get_holdings
```

## Request Connection

```python
from skills.snaptrade.scripts.portfolio.request_connection import request_connection

# Generate OAuth connection link
result = request_connection(user_id="user-123")

if 'error' in result:
    print(f"Error: {result['error']}")
else:
    print(f"Connect URL: {result['connect_url']}")
    print(f"User ID: {result['user_id']}")
    print(f"Session: {result['session_id']}")
```

Send the `connect_url` to the user. After they authorize, their accounts are linked.

## List Connected Accounts

```python
from skills.snaptrade.scripts.portfolio.get_accounts import get_accounts

# Get all linked accounts (async - returns promise-like)
accounts = await get_accounts(user_id="user-123")

for account in accounts['accounts']:
    print(f"Account: {account['name']} ({account['brokerage']['name']})")
    print(f"  ID: {account['id']}")
    print(f"  Number: {account['number']}")
    print(f"  Type: {account.get('type', 'Unknown')}")
```

## Get Portfolio Holdings

```python
from skills.snaptrade.scripts.portfolio.get_holdings import get_holdings

# Get all holdings across all linked accounts
holdings = await get_holdings(user_id="user-123")

for account in holdings['accounts']:
    print(f"\n{account['account_name']} ({account['brokerage_name']})")
    print(f"Cash: ${account['cash']['total']:.2f} {account['cash']['currency']}")
    
    print("Positions:")
    for position in account['positions']:
        symbol = position['symbol']['symbol']
        qty = position['units']
        price = position['price']
        value = qty * price
        
        print(f"  {symbol}: {qty} shares @ ${price:.2f} = ${value:.2f}")
    
    total_value = sum(p['units'] * p['price'] for p in account['positions']) + account['cash']['total']
    print(f"Total Value: ${total_value:.2f}")
```

## Common Workflows

### Complete Portfolio Overview

```python
async def get_full_portfolio(user_id):
    """Get comprehensive portfolio across all brokerages"""
    
    # Get accounts
    accounts = await get_accounts(user_id=user_id)
    if 'error' in accounts:
        print(f"Error: {accounts['error']}")
        return None
    
    # Get holdings
    holdings = await get_holdings(user_id=user_id)
    
    portfolio = {
        'accounts': [],
        'total_value': 0,
        'total_cash': 0,
        'all_positions': []
    }
    
    for account in holdings.get('accounts', []):
        account_data = {
            'name': account['account_name'],
            'brokerage': account['brokerage_name'],
            'cash': account['cash']['total'],
            'currency': account['cash']['currency'],
            'positions': []
        }
        
        for position in account['positions']:
            symbol = position['symbol']['symbol']
            qty = position['units']
            price = position['price']
            value = qty * price
            
            pos_data = {
                'symbol': symbol,
                'quantity': qty,
                'price': price,
                'value': value
            }
            
            account_data['positions'].append(pos_data)
            portfolio['all_positions'].append({**pos_data, 'account': account['account_name']})
        
        account_value = sum(p['value'] for p in account_data['positions']) + account_data['cash']
        account_data['total_value'] = account_value
        
        portfolio['accounts'].append(account_data)
        portfolio['total_value'] += account_value
        portfolio['total_cash'] += account_data['cash']
    
    return portfolio

# Usage
portfolio = await get_full_portfolio("user-123")
print(f"Total Portfolio Value: ${portfolio['total_value']:,.2f}")
print(f"Cash Allocation: {portfolio['total_cash']/portfolio['total_value']:.1%}")
```

### Find Overlapping Positions

```python
def find_overlaps(holdings):
    """Find same stock held across multiple accounts"""
    
    symbol_accounts = {}
    
    for account in holdings.get('accounts', []):
        account_name = account['account_name']
        
        for position in account['positions']:
            symbol = position['symbol']['symbol']
            qty = position['units']
            
            if symbol not in symbol_accounts:
                symbol_accounts[symbol] = []
            
            symbol_accounts[symbol].append({
                'account': account_name,
                'quantity': qty
            })
    
    # Show overlaps
    for symbol, accounts in symbol_accounts.items():
        if len(accounts) > 1:
            total = sum(a['quantity'] for a in accounts)
            print(f"\n{symbol}: {total} total shares across {len(accounts)} accounts")
            for a in accounts:
                print(f"  - {a['account']}: {a['quantity']}")
```

### Calculate Asset Allocation

```python
def calculate_allocation(holdings):
    """Calculate allocation by asset type/sector"""
    
    total_value = 0
    positions_by_type = {}
    
    for account in holdings.get('accounts', []):
        for position in account['positions']:
            symbol = position['symbol']['symbol']
            qty = position['units']
            price = position['price']
            value = qty * price
            
            # Categorize (you'd need external data for real categories)
            # For now, group by first letter as example
            category = symbol[0]  # Simplified - use real categorization
            
            if category not in positions_by_type:
                positions_by_type[category] = {'value': 0, 'symbols': []}
            
            positions_by_type[category]['value'] += value
            positions_by_type[category]['symbols'].append(symbol)
            total_value += value
    
    # Print allocation
    print("Portfolio Allocation:")
    for category, data in sorted(positions_by_type.items(), key=lambda x: x[1]['value'], reverse=True):
        pct = data['value'] / total_value * 100
        print(f"  {category}: {pct:.1f}% (${data['value']:,.2f}) - {len(data['symbols'])} positions")
```

## Error Handling

All functions return dict with error key on failure:

```python
result = await get_accounts(user_id="invalid")
if 'error' in result:
    print(f"Error: {result['error']}")
    if 'needs_reauth' in result:
        print("User needs to reauthorize - generate new connect URL")
```

## Supported Brokerages

- Alpaca
- Charles Schwab
- E*Trade
- Fidelity
- Interactive Brokers
- Robinhood
- TD Ameritrade
- Tradier
- Webull
- And 15+ more

## Notes

- All portfolio functions are async (require `await`)
- User must authorize through OAuth before accessing data
- Connections can expire and need reauthorization
- Rate limits vary by brokerage
- Some brokerages restrict certain data (e.g., options, crypto)

## When to Use This Skill

- User asks to see their brokerage portfolio, holdings, or account balance
- User wants to connect a new brokerage account (Robinhood, Schwab, Fidelity, etc.)
- User asks "what stocks do I own" or "what's my portfolio worth"
- User wants to compare their holdings against market data
- Do NOT use for trading — SnapTrade is read-only portfolio viewing
