# Strategy System - Complete Architecture

## Overview

Users create automated trading bots (strategies) through AI conversation. Each strategy is defined by:

## **What is a Strategy?**

A strategy consists of:

1. **📝 Thesis** - Why this will make money (plain English)
2. **📜 Entry Script** (`entry.py`) - Executable code that returns entry signals
3. **📜 Exit Script** (`exit.py`) - Executable code that returns exit signals  
4. **💰 Capital Allocation** - Total capital, per-trade size, position limits
5. **⏱️ Execution Frequency** - How often to run (in seconds)
6. **🎯 Platform** - Where to execute (`polymarket`, `kalshi`, `alpaca`)
7. **📊 Track Record** - Backtest → Paper → Live progression

## Key Concepts

### 1. **Hard Priors** (Required for Every Strategy)

Every strategy MUST define:
- ✅ **Thesis**: Why this strategy will make money
- ✅ **Entry Script**: Returns `list[EntrySignal]`
- ✅ **Exit Script**: Returns `ExitSignal | None` for each position
- ✅ **Execution Platform**: `polymarket`, `kalshi`, or `alpaca`
- ✅ **Execution Frequency**: Check for signals every N seconds
- ✅ **Capital Allocation**:
  - Total capital allocated to strategy
  - Capital per single trade
  - Max concurrent positions
  - Position sizing method (fixed, Kelly, % of capital)

### 2. **Server-Like Architecture**

Strategies are structured like your existing servers (`servers/dome/`, `servers/kalshi/`):

```
servers/strategies/
├── _base.py           # BaseStrategy interface
├── _loader.py         # Loads strategies from DB files
├── _executor.py       # Runs entry/exit cycle
└── README.md          # Documentation
```

### 3. **User Strategies as Database Files**

When AI creates a strategy, it generates **3 files** saved as ChatFiles:

```
1. entry.py        - Entry signal logic (executable script)
2. exit.py         - Exit signal logic (executable script)
3. config.json     - Configuration with hard priors
```

These are stored in the `chat_files` table, linked to the strategy via `file_ids`.

### 4. **Capital Management**

Each strategy has its own capital allocation:

```json
{
  "capital": {
    "total_capital": 5000,           // Total USD for this strategy
    "capital_per_trade": 100,        // USD per single trade
    "max_positions": 5,              // Max concurrent positions
    "max_position_size": 500,        // Max USD in any single position
    "max_daily_loss": 200,           // Stop if daily loss > this
    "sizing_method": "kelly"         // fixed | kelly | percent_capital
  }
}
```

**Capital Tracking:**
- System tracks deployed capital vs available
- Won't enter new trades if capital exhausted
- Won't enter if max positions reached
- Position sizing can scale with confidence (Kelly)

### 5. **Execution Modes & Track Record**

Strategies progress through modes:

```
BACKTEST → PAPER (shadow) → LIVE
```

**Backtest**: Historical data simulation
- Tests strategy logic on past data
- Fast way to validate approach
- Results shown in UI

**Paper Trading** (Shadow Mode):
- Real-time data, fake trades
- Runs alongside market
- Builds track record before risking money
- Must meet criteria to graduate to live

**Live Trading**:
- Real money execution
- Only after proving success in paper
- Full audit trail

**Graduation Criteria** (Paper → Live):
- Minimum 20 paper trades
- Win rate > 55%
- Positive P&L
- Max drawdown < 20%

---

## User Flow

### Creating a Strategy

```
USER: "Create a bot to copy Polymarket trader 0x742d35..."

AI: [Generates 2 files]
    1. strategy.py:
       - Implements BaseStrategy
       - should_enter(): Check trader's recent trades
       - should_exit(): Stop loss / take profit
       - execute_entry(): Copy the trade
       - execute_exit(): Exit position
    
    2. config.json:
       {
         "name": "Polymarket Copy Trader",
         "platform": "polymarket",
         "polling_interval": 60,
         "risk_limits": { "max_order_usd": 100 },
         "parameters": { "tracked_traders": ["0x742d..."] }
       }

AI: [Uses deploy_strategy tool]
    - Saves files to chat_files table
    - Creates Strategy record with file_ids
    - Sets polling_interval in config

AI: "✅ Strategy created! It will check every 60 seconds.
     Approve it in the UI to enable live trading."
```

### Viewing Strategies

User navigates to `/strategies` page to see:

```
┌─────────────────────────────────────────────────────────────┐
│  🤖 Trading Strategies                    ➕ Create New     │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  📊 Polymarket Copy Trader                      ✅ Active   │
│  Copies trades from top traders                             │
│  ⏱️ Runs every 60 seconds                                   │
│  ┌─────┬─────┬─────┐                                        │
│  │ 42  │ 40  │  2  │                                        │
│  │Runs │ ✓   │  ✗  │                                        │
│  └─────┴─────┴─────┘                                        │
│  [Pause] [Test Run]                                         │
│                                                              │
│  ─────────────────────────────────────────────────────────  │
│                                                              │
│  📊 Sports Betting Bot                      💤 Paused       │
│  Bets on live NBA games                                     │
│  ⏱️ Runs every 30 seconds                                   │
│  [Enable] [Test Run]                                        │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Strategy Details View

Click a strategy to see:

**Overview Tab:**
- Description
- Schedule
- Risk limits
- Performance stats (P&L, win rate, etc.)

**Execution History Tab:**
- List of all runs (scheduled, manual, dry run)
- Expandable logs and actions for each run
- Error details if failed

**Live Activity Tab:**
- Real-time status (running/paused)
- Latest execution logs (terminal-style)
- Actions taken (orders placed, positions closed)

---

## Execution Flow

### 1. Background Scheduler (runs every 60 seconds)

```python
# backend/modules/strategies/scheduler.py

class StrategyScheduler:
    async def run_once(self):
        # Get all enabled + approved strategies
        strategies = await get_due_strategies(db)
        
        for strategy in strategies:
            if self._should_run_now(strategy):
                await execute_strategy(db, strategy)
    
    def _should_run_now(self, strategy):
        # Check if polling_interval seconds have passed
        polling_interval = strategy.config['polling_interval']
        last_run = strategy.stats['last_run_at']
        
        return seconds_since(last_run) >= polling_interval
```

### 2. Strategy Executor

```python
# backend/modules/strategies/executor.py

async def execute_strategy(db, strategy, trigger, dry_run):
    # Load strategy from database files
    from servers.strategies._executor import execute_strategy_cycle
    
    ctx = StrategyContext(
        user_id=strategy.user_id,
        strategy_id=strategy.id,
        dry_run=dry_run,
        ...
    )
    
    # Run the strategy cycle
    result = await execute_strategy_cycle(db, strategy, ctx)
    
    # Save execution results
    await complete_execution(db, execution, result)
```

### 3. Strategy Cycle

```python
# backend/modules/tools/servers/strategies/_executor.py

async def execute_strategy_cycle(db, strategy_db_record, ctx):
    # 1. Load strategy class from files
    strategy = await loader.load_strategy(db, strategy_id, file_ids)
    
    # 2. Load open positions from platform
    positions = await _load_open_positions(ctx, strategy)
    
    # 3. Check exit signals for each position
    for position in positions:
        exit_signal = await strategy.should_exit(ctx, position)
        if exit_signal:
            await strategy.execute_exit(ctx, position, exit_signal)
    
    # 4. Check entry signals
    entry_signals = await strategy.should_enter(ctx)
    
    # 5. Execute entries
    for signal in entry_signals:
        await strategy.execute_entry(ctx, signal)
    
    # 6. Return summary
    return {
        'entries': len(entry_signals),
        'exits': len(exits_executed),
        'logs': ctx.get_logs(),
        'actions': ctx.get_actions()
    }
```

---

## Example Strategy Implementation

### strategy.py

```python
from servers.strategies import BaseStrategy, EntrySignal, ExitSignal, Position

class PolymarketCopyTrader(BaseStrategy):
    async def should_enter(self, ctx) -> list[EntrySignal]:
        """Check if tracked traders made new trades"""
        poly = await ctx.polymarket
        signals = []
        
        tracked_traders = self.get_param('tracked_traders', [])
        
        for trader_wallet in tracked_traders:
            trades = await poly.get_trade_history(
                maker_address=trader_wallet,
                limit=20
            )
            
            for trade in trades['trades']:
                if trade['id'] not in self.processed_trades:
                    self.processed_trades.add(trade['id'])
                    
                    signals.append(EntrySignal(
                        market_id=trade['token_id'],
                        market_name=trade['market_slug'],
                        side='yes',
                        reason=f"Copy trade from {trader_wallet[:10]}...",
                        confidence=0.8
                    ))
        
        return signals
    
    async def should_exit(self, ctx, position: Position):
        """Check stop loss / take profit"""
        pnl_pct = position.unrealized_pnl / position.size
        
        if pnl_pct < -0.10:  # -10% stop loss
            return ExitSignal(
                position_id=position.position_id,
                reason="Stop loss triggered"
            )
        
        if pnl_pct > 0.20:  # +20% take profit
            return ExitSignal(
                position_id=position.position_id,
                reason="Take profit triggered"
            )
        
        return None
    
    async def execute_entry(self, ctx, signal: EntrySignal):
        """Place buy order"""
        poly = await ctx.polymarket
        size = self.config.risk_limits['max_order_usd']
        
        return await poly.create_order(
            token_id=signal.market_id,
            side='BUY',
            amount=size
        )
    
    async def execute_exit(self, ctx, position: Position, signal: ExitSignal):
        """Place sell order"""
        poly = await ctx.polymarket
        
        return await poly.create_order(
            token_id=position.position_id,
            side='SELL',
            amount=position.size
        )
```

### config.json

```json
{
  "name": "Polymarket Copy Trader",
  "description": "Copies trades from top Polymarket traders",
  "platform": "polymarket",
  "polling_interval": 60,
  "risk_limits": {
    "max_order_usd": 100,
    "max_daily_usd": 500,
    "allowed_services": ["polymarket"]
  },
  "parameters": {
    "tracked_traders": ["0x742d35Cc..."],
    "copy_percentage": 0.5,
    "wallet_address": "0xUSER_WALLET..."
  }
}
```

---

## UI/UX Features

### Strategy Cards (Left Panel)
- ✅ Name, description, status badge
- ✅ Run count, success rate stats
- ✅ Schedule display ("Runs every 60 seconds")
- ✅ Pause/Enable toggle
- ✅ Test Run button (dry run)

### Strategy Details (Right Panel)

**Overview Tab:**
- Status banner (if needs approval)
- Description
- Schedule visualization
- Risk limits display
- Performance stats (P&L, win rate)

**Execution History Tab:**
- Timeline of all runs
- Expandable execution cards
- Logs viewer (terminal-style)
- Actions list (orders placed)
- Error details

**Live Activity Tab:**
- Live status indicator (🟢 Active / 💤 Paused)
- Latest logs streaming
- Real-time actions feed
- Next execution countdown

---

## Key Benefits

1. **Standardized Interface**: All strategies follow same pattern
2. **Type Safety**: Hard priors enforced by BaseStrategy
3. **Easy Testing**: Can test entry/exit logic independently
4. **Composable**: Strategies can share utilities
5. **Hot Reload**: Update code without restart
6. **Audit Trail**: Every action logged to database
7. **Risk Management**: Built-in limits enforced
8. **User Confidence**: Real-time monitoring builds trust

---

## Next Steps

1. ✅ BaseStrategy interface defined
2. ✅ Loader and executor implemented
3. ✅ Scheduler updated for polling_interval
4. ✅ UI created for strategy management
5. ⏳ AI tool to generate strategies
6. ⏳ Polymarket client implementation (for execute_entry/exit)
7. ⏳ Position tracking in database
8. ⏳ Real-time logs streaming to UI
