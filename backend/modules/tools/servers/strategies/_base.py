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


class StrategyConfig(BaseModel):
    """Configuration for a strategy (loaded from config.json)"""
    name: str
    description: str
    platform: Literal["polymarket", "kalshi", "alpaca"]
    polling_interval: int = Field(ge=1, description="Polling interval in seconds")
    risk_limits: Dict[str, Any] = Field(default_factory=dict)
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
    
    @abstractmethod
    async def should_enter(self, ctx) -> list[EntrySignal]:
        """
        Check if strategy should enter new positions
        
        Args:
            ctx: StrategyContext with access to APIs and state
            
        Returns:
            List of EntrySignal objects (empty if no signals)
            
        Example:
            async def should_enter(self, ctx):
                # Check markets
                markets = await ctx.polymarket.get_markets(tags=['crypto'])
                
                signals = []
                for market in markets['markets']:
                    if self._should_buy(market):
                        signals.append(EntrySignal(
                            market_id=market['condition_id'],
                            market_name=market['title'],
                            side='yes',
                            reason='Price below threshold',
                            confidence=0.75
                        ))
                
                return signals
        """
        pass
    
    @abstractmethod
    async def should_exit(self, ctx, position: Position) -> Optional[ExitSignal]:
        """
        Check if strategy should exit an open position
        
        Args:
            ctx: StrategyContext
            position: Current position to evaluate
            
        Returns:
            ExitSignal if should exit, None otherwise
            
        Example:
            async def should_exit(self, ctx, position):
                # Exit if profit > 20%
                if position.unrealized_pnl > position.size * 0.20:
                    return ExitSignal(
                        position_id=position.position_id,
                        reason='Take profit at +20%'
                    )
                
                # Exit if loss > 10%
                if position.unrealized_pnl < -position.size * 0.10:
                    return ExitSignal(
                        position_id=position.position_id,
                        reason='Stop loss at -10%'
                    )
                
                return None
        """
        pass
    
    @abstractmethod
    async def execute_entry(self, ctx, signal: EntrySignal) -> Dict[str, Any]:
        """
        Execute entry trade based on signal
        
        Args:
            ctx: StrategyContext
            signal: Entry signal from should_enter()
            
        Returns:
            Dict with execution results
            
        Example:
            async def execute_entry(self, ctx, signal):
                size_usd = self.config.risk_limits.get('max_order_usd', 100)
                
                result = await ctx.polymarket.create_order(
                    token_id=signal.market_id,
                    side='BUY',
                    amount=size_usd
                )
                
                ctx.log(f"Entered {signal.market_name}: {result}")
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
