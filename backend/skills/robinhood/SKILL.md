---
name: robinhood
description: Trade the user's real Robinhood account via Robinhood's official agentic-trading MCP. Read accounts/positions/quotes and place, review, or cancel live equity orders. Only works once the user has connected Robinhood from the Portfolio screen.
metadata:
  emoji: "🪶"
  category: trading
  is_system: true
  requires:
    env:
      - ROBINHOOD_MCP_TOKEN
    bins:
      - mcp
---

# Robinhood Agentic Trading Skill

Connects to Robinhood's official agentic-trading MCP server (`get_equity_quotes`,
`place_equity_order`, …) using the user's OAuth token, which the backend injects
as `ROBINHOOD_MCP_TOKEN`. **If that env var is missing, the user hasn't connected
Robinhood — tell them to connect it from the Portfolio screen; do not guess.**

Live trades use real money. Trading is only permitted on the user's isolated
**agentic account** (`agentic_allowed: true`); other accounts are rejected by
Robinhood. Always `review_order` and show the user the estimate before
`place_order`, unless they've explicitly said to skip review.

## Read account state

```python
from skills.robinhood.scripts.trading import get_accounts, get_positions, get_quotes

accounts = get_accounts()                      # find the agentic_allowed=True account
acct = next(a["account_number"] for a in accounts["data"]["accounts"] if a.get("agentic_allowed"))

positions = get_positions(acct)
quotes = get_quotes(["AAPL", "MSFT"])
```

## Review, then place an order

```python
from skills.robinhood.scripts.trading import review_order, place_order

# 1) Simulate first — surfaces buying-power / PDT / halt alerts and the estimate.
preview = review_order(account_number=acct, symbol="AAPL", side="buy",
                       type="market", dollar_amount="100.00")
print(preview)   # show this to the user and confirm before placing

# 2) Place the real order.
result = place_order(account_number=acct, symbol="AAPL", side="buy",
                     type="market", dollar_amount="100.00")
```

## Other calls

```python
from skills.robinhood.scripts.trading import get_orders, cancel_order, search, get_tradability

get_orders(acct, state="filled")             # order history
get_tradability(acct, ["AAPL", "TSLA"])      # per-session eligibility / fractional
search("nvidia")                              # resolve a name -> ticker / instrument
cancel_order(acct, order_id)                  # cancel an open order
```

## Generic escape hatch

Any MCP tool can be called directly by name:

```python
from skills.robinhood.scripts._client import call
call("get_portfolio", account_number=acct)
```

## Key notes

- Order params mirror the MCP tool: provide exactly one of `quantity` or
  `dollar_amount`; `dollar_amount` requires `type="market"`. `limit_price` is
  required for limit orders.
- Prices: equities in dollars. Quotes return a live price + the prior close.
- The token is short-lived and auto-refreshed by the backend each run — never
  print it or write it to disk.
