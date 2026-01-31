"""
Base Strategy Class - Defines required interface for all strategies

All strategies must inherit from BaseStrategy and implement:
- should_enter()
- should_exit()
- execute_entry()
- execute_exit()
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Literal
from pydantic import BaseModel, Field
import json
from pathlib import Path


class CapitalAllocation(BaseModel):
    """How capital is allocated across the strategy"""
    # Total capital available to the strategy
    total_capital: float = Field(description="Total USD allocated to this strategy")
    
    # Per-trade sizing
    capital_per_trade: float = Field(description="USD to risk per single trade")
    
    # Position limits
    max_positions: int = Field(default=5, description="Maximum concurrent positions")
    max_position_size: float = Field(description="Max USD in any single position")
    
    # Risk limits
    max_daily_loss: float = Field(description="Stop trading if daily loss exceeds this (USD)")
    max_total_drawdown: float = Field(default=0.20, description="Stop if total drawdown exceeds % (0-1)")
    
    # Position sizing method
    sizing_method: Literal["fixed", "kelly", "percent_capital"] = Field(
        default="fixed",
        description="How to size positions: fixed USD, Kelly criterion, or % of capital"
    )
    
    @property
    def available_capital_per_position(self) -> float:
        """How much capital can be used per position"""
        return min(self.capital_per_trade, self.max_position_size)
    
    @property
    def max_capital_deployed(self) -> float:
        """Maximum capital that can be in positions at once"""
        return min(
            self.max_positions * self.max_position_size,
            self.total_capital * 0.8  # Never use more than 80% of total capital
        )


class StrategyConfig(BaseModel):
    """Configuration for a strategy (loaded from config.json)"""
    # Identity & Thesis
    name: str
    thesis: str = Field(description="Why this strategy will make money (human-readable)")
    
    # Platform & Execution
    platform: Literal["polymarket", "kalshi", "alpaca"]
    execution_frequency: int = Field(ge=1, description="Check for signals every N seconds")
    
    # Capital Management
    capital: CapitalAllocation
    
    # Script filenames (stored as separate ChatFiles)
    entry_script: str = Field(default="entry.py", description="Script that returns entry signals")
    exit_script: str = Field(default="exit.py", description="Script that returns exit signals")
    
    # Entry/Exit descriptions (for UI display)
    entry_description: str = Field(description="When to enter (human-readable)")
    exit_description: str = Field(description="When to exit (human-readable)")
    
    # Optional parameters
    parameters: Dict[str, Any] = Field(default_factory=dict)


class Position(BaseModel):
    """Represents an open position"""
    position_id: str
    market_id: str
    market_name: str
    side: str  # 'yes', 'no', 'buy', 'sell'
    size: float
    entry_price: float
    current_price: float
    unrealized_pnl: float
    entry_time: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


class EntrySignal(BaseModel):
    """Signal to enter a position"""
    market_id: str
    market_name: str
    side: str
    reason: str
    confidence: float = Field(ge=0, le=1)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ExitSignal(BaseModel):
    """Signal to exit a position"""
    position_id: str
    reason: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


class BaseStrategy(ABC):
    """
    Base class for all trading strategies
    
    Strategies must implement:
    1. should_enter() - Returns entry signals
    2. should_exit() - Returns exit signals for open positions
    3. execute_entry() - Executes entry trade
    4. execute_exit() - Executes exit trade
    
    The scheduler will:
    1. Call should_enter() to check for new opportunities
    2. Call should_exit() for each open position
    3. Execute trades via execute_entry()/execute_exit()
    """
    
    def __init__(self, config: StrategyConfig):
        self.config = config
        self.state = {}  # For persisting state between runs
    
    @classmethod
    def load_from_directory(cls, directory: Path):
        """Load strategy from directory containing config.json"""
        config_path = directory / "config.json"
        if not config_path.exists():
            raise FileNotFoundError(f"config.json not found in {directory}")
        
        with open(config_path) as f:
            config_data = json.load(f)
        
        config = StrategyConfig(**config_data)
        return cls(config)
    
    # =========================================================================
    # Required Methods (Must implement)
    # =========================================================================
    
    async def should_enter(self, ctx) -> list[EntrySignal]:
        """
        Execute entry script to check for entry signals
        
        The entry script (entry.py) should return a list of EntrySignal dicts.
        This base implementation loads and executes the script.
        """
        entry_script_code = self._load_script(self.config.entry_script)
        
        # Execute entry script with ctx available
        namespace = {'ctx': ctx, 'EntrySignal': EntrySignal}
        exec(entry_script_code, namespace)
        
        # Entry script should define a function: async def check_entry(ctx)
        if 'check_entry' in namespace:
            result = await namespace['check_entry'](ctx)
            if isinstance(result, list):
                return [EntrySignal(**s) if isinstance(s, dict) else s for s in result]
        
        return []
    
    async def should_exit(self, ctx, position: Position) -> Optional[ExitSignal]:
        """
        Execute exit script to check if position should be exited
        
        The exit script (exit.py) should return an ExitSignal dict or None.
        This base implementation loads and executes the script.
        """
        exit_script_code = self._load_script(self.config.exit_script)
        
        # Execute exit script with ctx and position available
        namespace = {'ctx': ctx, 'position': position, 'ExitSignal': ExitSignal}
        exec(exit_script_code, namespace)
        
        # Exit script should define: async def check_exit(ctx, position)
        if 'check_exit' in namespace:
            result = await namespace['check_exit'](ctx, position)
            if isinstance(result, dict):
                return ExitSignal(**result)
            return result
        
        return None
    
    def _load_script(self, filename: str) -> str:
        """Load script code from strategy files"""
        # In real implementation, this would load from ChatFiles
        # For now, scripts are expected to be in self._script_cache
        if not hasattr(self, '_script_cache'):
            self._script_cache = {}
        
        if filename not in self._script_cache:
            raise ValueError(f"Script {filename} not found in strategy files")
        
        return self._script_cache[filename]
    
    @abstractmethod
    async def execute_entry(self, ctx, signal: EntrySignal, position_size: float) -> Dict[str, Any]:
        """
        Execute entry trade based on signal
        
        Args:
            ctx: StrategyContext
            signal: Entry signal from should_enter()
            position_size: Calculated position size in USD
            
        Returns:
            Dict with execution results
            
        Example:
            async def execute_entry(self, ctx, signal, position_size):
                result = await ctx.polymarket.create_order(
                    token_id=signal.market_id,
                    side='BUY',
                    amount=position_size
                )
                
                ctx.log(f"Entered {signal.market_name}: ${position_size}")
                return result
        """
        pass
    
    @abstractmethod
    async def execute_exit(self, ctx, position: Position, signal: ExitSignal) -> Dict[str, Any]:
        """
        Execute exit trade based on signal
        
        Args:
            ctx: StrategyContext
            position: Position to exit
            signal: Exit signal from should_exit()
            
        Returns:
            Dict with execution results
            
        Example:
            async def execute_exit(self, ctx, position, signal):
                result = await ctx.polymarket.create_order(
                    token_id=position.market_id,
                    side='SELL',
                    amount=position.size
                )
                
                ctx.log(f"Exited {position.market_name}: {signal.reason}")
                return result
        """
        pass
    
    # =========================================================================
    # Optional Hooks
    # =========================================================================
    
    async def on_start(self, ctx):
        """Called when strategy starts (optional)"""
        ctx.log(f"🚀 {self.config.name} started")
    
    async def on_stop(self, ctx):
        """Called when strategy stops (optional)"""
        ctx.log(f"🛑 {self.config.name} stopped")
    
    async def on_error(self, ctx, error: Exception):
        """Called when error occurs (optional)"""
        ctx.log(f"❌ Error: {error}")
    
    # =========================================================================
    # Helper Methods
    # =========================================================================
    
    def get_param(self, key: str, default: Any = None) -> Any:
        """Get parameter from config"""
        return self.config.parameters.get(key, default)
    
    def save_state(self, ctx, key: str, value: Any):
        """Persist state between runs"""
        self.state[key] = value
        # Could save to DB here if needed
    
    def load_state(self, ctx, key: str, default: Any = None) -> Any:
        """Load persisted state"""
        return self.state.get(key, default)
