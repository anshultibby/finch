# Strategy Servers - Structured Trading Bots

Strategies are implemented as **server modules** with standardized interfaces.

## Structure

```
servers/strategies/
├── README.md                    # This file
├── _base.py                     # Base class with required interface
├── polymarket_copy_trader/      # Example strategy
│   ├── __init__.py
│   ├── strategy.py              # Main logic
│   └── config.json              # Strategy configuration
└── sports_betting/
    ├── __init__.py
    ├── strategy.py
    └── config.json
```

## Hard Priors (Required Fields)

Every strategy MUST define:

1. **Entry Signal** - `async def should_enter(ctx) -> bool`
2. **Exit Signal** - `async def should_exit(ctx, position) -> bool`
3. **Execution Platform** - Which service to use (polymarket, kalshi, alpaca)
4. **Polling Duration** - How often to check (in seconds)
5. **Risk Limits** - Max position size, daily limits

## Strategy Interface

```python
from servers.strategies._base import BaseStrategy

class MyStrategy(BaseStrategy):
    # Configuration
    name = "My Strategy"
    description = "What it does"
    platform = "polymarket"  # or "kalshi", "alpaca"
    polling_interval = 60  # seconds
    
    async def should_enter(self, ctx):
        """
        Entry signal logic
        
        Returns:
            bool: True if conditions met to enter trade
        """
        pass
    
    async def should_exit(self, ctx, position):
        """
        Exit signal logic
        
        Args:
            position: Current position data
            
        Returns:
            bool: True if should exit this position
        """
        pass
    
    async def execute_entry(self, ctx, signal):
        """
        Execute entry trade
        
        Args:
            signal: Entry signal data from should_enter()
        """
        pass
    
    async def execute_exit(self, ctx, position):
        """
        Execute exit trade
        
        Args:
            position: Position to exit
        """
        pass
```

## config.json Format

```json
{
  "name": "Polymarket Copy Trader",
  "description": "Copies trades from top Polymarket traders",
  "platform": "polymarket",
  "polling_interval": 60,
  "risk_limits": {
    "max_order_usd": 100,
    "max_daily_usd": 500,
    "max_position_usd": 200,
    "allowed_services": ["polymarket"]
  },
  "parameters": {
    "tracked_traders": [
      "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb"
    ],
    "copy_percentage": 0.5,
    "min_trade_size": 10
  }
}
```

## User Flow

1. **User asks AI**: "Create a bot to copy Polymarket trader X"
2. **AI generates** strategy module in `servers/strategies/`
3. **AI deploys** via `deploy_strategy` tool
4. **Scheduler runs** strategy at specified polling_interval
5. **Strategy checks** entry/exit signals
6. **Strategy executes** trades via platform API

## Benefits

- ✅ **Standardized interface** - All strategies follow same pattern
- ✅ **Type safety** - Clear contract enforced by base class
- ✅ **Easy to test** - Can mock ctx and test logic
- ✅ **Composable** - Strategies can import shared utilities
- ✅ **Version control** - Each strategy is a module in git
- ✅ **Hot reload** - Can update strategy code without restart
