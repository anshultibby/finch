---
name: alpaca
description: Execute trades via Alpaca. Supports paper trading (instant, $100k simulated) and live trading. Use for executing TLH swaps, mirroring portfolios, and managing orders.
metadata:
  emoji: "🦙"
  category: trading
  is_system: true
  requires:
    env: [ALPACA_API_KEY, ALPACA_SECRET_KEY]
    bins: []
---

# Alpaca Trading Skill

Execute trades via Alpaca's API. Paper trading is the default — instant activation, no KYC needed.

## Quick Start

```python
# Check account status
from skills.alpaca.scripts.account import get_account_info, get_positions
info = get_account_info(paper=True)
print(f"Buying power: ${info['buying_power']:,.2f}")

# See current positions
positions = get_positions(paper=True)
for p in positions:
    print(f"  {p['symbol']}: {p['qty']} shares, P&L: ${p['unrealized_pl']:,.2f}")
```

## Execute a TLH Swap

```python
from skills.alpaca.scripts.trading import execute_swap

# Sell the loser, buy the replacement in one call
result = execute_swap(
    sell_symbol="TSLA",
    sell_qty=10,
    buy_symbol="RIVN",
    buy_notional=1500.00,  # dollar amount
    paper=True,
)
print(f"Sell order: {result['sell_order']['status']}")
print(f"Buy order: {result['buy_order']['status']}")
```

## Mirror Real Portfolio into Paper Account

After connecting a brokerage via SnapTrade and getting positions with `get_portfolio`, mirror them into the Alpaca paper account:

```python
from skills.alpaca.scripts.trading import mirror_portfolio

# positions = list from get_portfolio tool, each with {symbol, units}
result = mirror_portfolio(positions, paper=True)
print(f"Mirrored {result['total_mirrored']} positions")
if result['errors']:
    print(f"Errors: {result['errors']}")
```

## Place Individual Orders

```python
from skills.alpaca.scripts.trading import place_order

# Buy by share count
place_order("AAPL", qty=5, side="buy", paper=True)

# Buy by dollar amount
place_order("MSFT", notional=1000.00, side="buy", paper=True)

# Sell
place_order("TSLA", qty=10, side="sell", paper=True)
```

## Check Order Status

```python
from skills.alpaca.scripts.trading import get_orders

orders = get_orders(paper=True, limit=10)
for o in orders:
    print(f"  {o['side']} {o['symbol']}: {o['status']} (filled: {o['filled_qty']})")
```

## Key Notes

- **Paper trading** uses $100,000 simulated balance. No KYC or account opening needed.
- **All functions default to paper=True** for safety. Set paper=False only for live trading.
- Orders use **market orders with day time-in-force** for simplicity.
- The `execute_swap` function does sell first, then buy — if the sell fails, the buy is not attempted.
- Use `mirror_portfolio` right after connecting a brokerage to replicate the user's real holdings in paper.
