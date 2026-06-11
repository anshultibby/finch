---
name: robinhood
description: Trade the user's real Robinhood account via Robinhood's official agentic-trading MCP. Check connection status, read the portfolio (value, buying power, positions), place/review/cancel live equity orders and single-leg option orders (long calls/puts, covered calls, CSPs — no spreads), and build scheduled trading automations that email the user a one-click approval link. Only works once the user has connected Robinhood from the Portfolio screen.
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

## Connection status (always check first)

Before any read or trade, confirm the user is connected and grab the tradable
agentic account. This never raises for a missing connection — it returns a
`reason` to relay.

```python
from skills.robinhood.scripts.trading import connection_status

st = connection_status()
# {"connected": True, "agentic_account": "abc123", "accounts": [...], "reason": "Connected."}
if not st["connected"]:
    # Tell the user st["reason"] (e.g. "connect Robinhood from the Portfolio screen") and stop.
    ...
acct = st["agentic_account"]   # only the agentic_allowed account can trade
```

## Portfolio snapshot

One call for account value, buying power, and open positions (resolves the
agentic account automatically):

```python
from skills.robinhood.scripts.trading import portfolio_snapshot

snap = portfolio_snapshot()
# {"connected": True, "agentic_account": "...", "portfolio": {...}, "positions": {...}}
```

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

## Building trading automations

A trading automation = a **scheduled job** (from the `finch_api` skill) whose
`message` is a self-contained instruction to run a strategy. When the job fires,
the backend runs that message as the user with full tools — including this skill.

**Safety rule (default): review → email for approval, never trade unattended.**
The automation evaluates its rule, `review_order`s the candidate, then calls
`request_trade_approval(...)` so the user gets a one-click Approve link by email.
The backend places the order only if the user clicks Approve. Only place orders
directly with `place_order` inside a job when the user has *explicitly* opted into
unattended trading for that automation (and even then, keep a dollar cap).

### Pattern: a recurring strategy run

```python
from skills.finch_api.scripts import schedule_job

schedule_job(
    name="Mean-reversion check — watchlist",
    recurrence="weekdays",
    run_at="2026-06-05T13:45:00Z",   # 9:45 ET, after the open
    message=(
        "Run my mean-reversion strategy on Robinhood. Steps:\n"
        "1. connection_status(); if not connected, stop.\n"
        "2. For AAPL, MSFT, NVDA: get_quotes; if a name is >5% below its 5-day "
        "   average, it's a candidate.\n"
        "3. For each candidate: review_order (buy $200, market), then "
        "   request_trade_approval(...) so I approve by email. Cap total at $600.\n"
        "4. If nothing qualifies, do nothing (no email)."
    ),
)
```

### Self-chaining (one-offs that schedule the next run)

Jobs don't have to be recurring — a one-off job can schedule the next one at the
end of its run, so the model controls the cadence (e.g. tighten to every 15 min
near a catalyst, back off otherwise):

```python
# ...inside an automation's message instruction:
# "After acting, schedule_job(in_minutes=15, message=<this same instruction>) "
# "only if the market is still open; otherwise schedule for the next open."
```

### Persist the strategy

Keep the thesis, signals, and risk rules in durable memory (`memory_write(durable=True)`
→ MEMORY.md) and have each run read them first, so the strategy evolves without
re-stating it in every job message.

### Heavier research

For multi-step screening before trading, spin up a sub-agent with `create_agent`
to research candidates, then hand the shortlist to the review→approve loop.

### Notes

- Equities + **single-leg options** (see below); crypto/futures not yet.
- Every placed trade also fires a Robinhood push notification; the user can
  disconnect the agent in one tap from the app.
- Job limits: **5 recurring + 10 one-off** per user (see the finch_api skill).

## Options (single-leg only)

Requires the agentic account to have `option_level_2`/`option_level_3` — check
`connection_status()["options_enabled"]` first. **The MCP supports single legs
only** (long calls/puts, covered calls, cash-secured puts); multi-leg spreads
are app-only even on level-3 accounts.

```python
from skills.robinhood.scripts.trading import (get_option_chains, find_option_instruments,
    get_option_quotes, get_option_positions, review_option_order, place_option_order)
import uuid

chains = get_option_chains("AAPL")                     # expirations + chain ids
inst = find_option_instruments("AAPL", expiration_date="2026-07-17",
                               strike_price="230.0000", type="call")
oid = inst["data"]["results"][0]["id"]                 # option instrument UUID
quotes = get_option_quotes([oid])                      # live bid/ask + prior close

# Review first — surface order_checks alerts, fees, collateral verbatim:
preview = review_option_order(acct, oid, side="buy", position_effect="open",
                              quantity="1", type="limit", price="3.50",
                              chain_symbol="AAPL", underlying_type="equity")
# Place with an idempotency key; REUSE the same ref_id on transport-failure retries:
result = place_option_order(acct, oid, side="buy", position_effect="open",
                            quantity="1", type="limit", price="3.50",
                            ref_id=uuid.uuid4().hex)
```

Mechanics: `price`/`stop_price` are **per contract** (×100 for dollars);
`position_effect="close"` + opposite side to exit; `stop_market` is
sell-to-close only with the stop below the current ask; market/stop_market are
GFD + regular-hours only; default everything else to limit orders — option
spreads are wide and market orders get poor fills.

## Key notes

- Order params mirror the MCP tool: provide exactly one of `quantity` or
  `dollar_amount`; `dollar_amount` requires `type="market"`. `limit_price` is
  required for limit orders.
- Prices: equities in dollars. Quotes return a live price + the prior close.
- The token is short-lived and auto-refreshed by the backend each run — never
  print it or write it to disk.
