---
name: strategies
description: Deploy and manage automated trading strategies. Create, deploy, and monitor algorithmic trading bots that run on schedules.
homepage: https://docs.finch.ai/strategies
metadata:
  emoji: "🤖"
  category: automation
  is_system: true
  requires:
    env: []
    bins: []
---

# Strategies Skill

Deploy and manage automated trading strategies that run in the user's sandbox on a schedule.

## Strategy Contract

A strategy consists of two files:

**strategy.py** — defines a single `async def run(ctx)` function. Write whatever logic you need.

```python
async def run(ctx):
    """
    ctx.kalshi     — full Kalshi client (dry_run aware, risk-limited on writes)
    ctx.dry_run    — bool, True in paper mode
    ctx.log(msg)   — visible in execution history
    ctx.strategy_id, ctx.user_id
    """
    ctx.log("Checking positions...")
    portfolio = ctx.kalshi.get_portfolio()
    ctx.log(f"Balance: ${portfolio['balance']:.2f}")

    # Browse markets
    events = ctx.kalshi.get_events(limit=20)
    for event in events.get("events", []):
        for market in event.get("markets", []):
            ticker = market["ticker"]
            yes_ask = market["yes_ask"]  # price in CENTS

            if yes_ask < 20:  # example: buy if price below 20¢
                ctx.log(f"Buying {ticker} at {yes_ask}¢")
                ctx.kalshi.place_order(
                    ticker=ticker,
                    side="yes",
                    action="buy",
                    count=1,
                    order_type="market",
                )

    # Check open positions for exit
    positions = ctx.kalshi.get_positions()
    for pos in positions.get("positions", []):
        pnl = pos.get("realized_pnl", 0)
        if pnl < -1000:  # stop loss at -$10 (pnl in cents)
            ctx.log(f"Stop loss on {pos['ticker']}")
            ctx.kalshi.place_order(
                ticker=pos["ticker"],
                side="yes" if pos["position"] > 0 else "no",
                action="sell",
                count=abs(pos["position"]),
                order_type="market",
            )
```

**config.json** — platform, capital, risk limits, schedule:

```json
{
  "platform": "kalshi",
  "name": "Strategy Name",
  "thesis": "Why this will make money",
  "description": "What the strategy does",
  "capital": { "total": 500, "per_trade": 50, "max_positions": 5 },
  "schedule": "0 * * * *",
  "schedule_description": "Every hour",
  "risk_limits": {
    "max_order_usd": 50,
    "max_daily_usd": 200,
    "allowed_services": ["kalshi"]
  }
}
```

## ctx.kalshi

Full proxy over the `kalshi_trading` skill. All read methods pass through directly.
Write methods (`place_order`, `cancel_order`) are intercepted for dry_run and risk limits.

Read methods (pass-through, always safe):
- `ctx.kalshi.get_balance()`
- `ctx.kalshi.get_portfolio()`  — balance + positions in one call
- `ctx.kalshi.get_positions(limit=100)`
- `ctx.kalshi.get_events(limit=20, status="open", series_ticker=None)`
- `ctx.kalshi.get_event(event_ticker)`
- `ctx.kalshi.get_market(ticker)`
- `ctx.kalshi.get_markets(limit=100, status="open", event_ticker=None)`
- `ctx.kalshi.get_orderbook(ticker, depth=10)`
- `ctx.kalshi.get_orders(ticker=None, status="resting")`

Write methods (dry_run aware + risk-limited):
- `ctx.kalshi.place_order(ticker, side, action, count, order_type="market", price=None)`
  - `side`: `"yes"` or `"no"`
  - `action`: `"buy"` or `"sell"`
  - `price`: limit price in cents (1–99), required for limit orders
  - No-op in paper mode; blocked if `max_order_usd` or `max_daily_usd` exceeded
- `ctx.kalshi.cancel_order(order_id)`

Prices are in **CENTS** (0–100). Divide by 100 for dollars.

## Lifecycle

1. Use `write_chat_file` to write `strategy.py` and `config.json` — they appear in the chat for the user to review
2. Call `deploy_strategy` with the file IDs → files promoted to strategy_files table
3. User reviews + approves in Strategy Panel
4. User enables → scheduler starts ticking
5. Each tick: sandbox runner loads files fresh from DB, calls `run(ctx)`
6. StrategyExecution audit records stored in DB

**Iterating:** use `replace_in_chat_file` to edit `strategy.py` or `config.json`, then call `deploy_strategy` again with the updated file IDs to push a new version.

## NEVER do these things

```python
# WRONG — do not write strategy files via bash
bash("cat > strategy.py << 'EOF' ...")

# WRONG — do not test by running the file directly (no credentials in bash context)
bash("python3 strategy.py")

# WRONG — do not import kalshi directly inside strategy.py
from kalshi_trading.scripts import kalshi  # BREAKS — use ctx.kalshi instead

# WRONG — do not use print() inside strategy.py
print("something")  # use ctx.log("something")

# WRONG — do not use a class or top-level code
class MyStrategy:  # BREAKS — only async def run(ctx) is valid
    def on_entry(self): ...

# WRONG — wrong config.json field names
{"capital": {"initial_usd": 1000, "max_order_usd": 50}}  # BREAKS
# CORRECT:
{"capital": {"total": 1000, "per_trade": 50, "max_positions": 10}}
```

## Schedule Examples

```
"0 * * * *"      # Every hour
"*/30 * * * *"   # Every 30 minutes
"0 */4 * * *"    # Every 4 hours
"0 9 * * *"      # Daily at 9am UTC
"0 9 * * 1-5"    # Weekdays at 9am UTC
```

## When to Use

- User wants to automate a trading task on a schedule
- User asks "run this every day" or "buy when X happens"
- User wants to build an algorithmic trading bot
- Do NOT use for one-off analysis — use `execute_code` (bash) instead
