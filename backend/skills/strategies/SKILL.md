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

**strategy.py** — uses the `@strategy.on_entry` / `@strategy.on_exit` decorator pattern:

```python
from finch import strategy, EntrySignal, ExitSignal, Position

@strategy.on_entry
async def check_entry(ctx) -> list[EntrySignal]:
    """Return signals for positions to open."""
    from kalshi_trading.scripts import kalshi
    markets = kalshi.get_events(limit=20)
    signals = []
    for m in markets.get("events", []):
        # ...your logic...
        signals.append(EntrySignal(
            market_id="KXBTC-...",
            side="yes",
            reason="price dip",
            confidence=0.8,
        ))
    return signals

@strategy.on_exit
async def check_exit(ctx, position: Position) -> ExitSignal | None:
    """Return an exit signal if we should close this position, or None."""
    if position.unrealized_pnl < -10:
        return ExitSignal(position_id=position.position_id, reason="stop loss")
    return None
```

**config.json** — platform, capital, and risk settings:

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

## ctx Object

`ctx` is injected into check_entry / check_exit:

- `ctx.kalshi` — KalshiContextWrapper (dry_run aware, risk limited)
  - `.get_balance()`, `.get_positions()`, `.get_events()`, `.get_market(ticker)`
  - `.create_order(ticker, side, action, count, order_type, price)`
  - `.cancel_order(order_id)`
- `ctx.dry_run` — bool, True when doing a test run
- `ctx.strategy_id`, `ctx.user_id`, `ctx.execution_id`
- `ctx.log(msg)` — structured log visible in execution history

## Deploying From Code Execution

If you want to deploy a strategy from within code execution (bash tool):

```python
from strategies.scripts.deploy_from_files import deploy_strategy_from_files

result = deploy_strategy_from_files(
    name="Fed Rate Monitor",
    description="Buy Fed rate cut markets when price dips",
    files={
        "strategy.py": open("strategy.py").read(),
        "config.json": open("config.json").read(),
    }
    # user_id and chat_id are auto-read from FINCH_USER_ID / FINCH_CHAT_ID env vars
)
print(result["strategy_id"])
```

## Querying Strategies

```python
from strategies.scripts.query_strategies import list_strategies, get_strategy_code

# List all strategies
result = await list_strategies(user_id="...")
for s in result["strategies"]:
    print(s["name"], s["platform"])

# Get code
code = await get_strategy_code(user_id="...", strategy_id="...")
print(code["files"]["strategy.py"])
```

## Lifecycle

1. LLM writes strategy.py + config.json as chat files
2. LLM calls `deploy_strategy` tool → files promoted to strategy_files table
3. User reviews + approves in Strategy Panel
4. User enables → scheduler starts ticking
5. Each tick: sandbox runner loads files, runs check_exit then check_entry
6. StrategyExecution audit records stored in DB

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
