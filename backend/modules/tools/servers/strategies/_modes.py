"""
Strategy Execution Modes

Strategies can run in different modes:
1. BACKTEST - Historical data simulation
2. PAPER - Live data, fake trades (shadow mode)
3. LIVE - Real money trading
"""
from enum import Enum
from typing import Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel


class ExecutionMode(str, Enum):
    """Strategy execution mode"""
    BACKTEST = "backtest"  # Historical data
    PAPER = "paper"        # Live data, fake trades
    LIVE = "live"          # Real money


class TradeRecord(BaseModel):
    """Record of a single trade"""
    trade_id: str
    timestamp: datetime
    mode: ExecutionMode
    
    # Entry
    market_id: str
    market_name: str
    entry_side: str
    entry_price: float
    entry_size: float
    entry_reason: str
    
    # Exit
    exit_timestamp: Optional[datetime] = None
    exit_price: Optional[float] = None
    exit_reason: Optional[str] = None
    
    # P&L
    realized_pnl: Optional[float] = None
    pnl_pct: Optional[float] = None
    
    # Metadata
    metadata: Dict[str, Any] = {}
    
    @property
    def is_closed(self) -> bool:
        return self.exit_timestamp is not None
    
    @property
    def duration_seconds(self) -> Optional[float]:
        if not self.exit_timestamp:
            return None
        return (self.exit_timestamp - self.timestamp).total_seconds()


class StrategyTrackRecord(BaseModel):
    """Complete track record for a strategy"""
    strategy_id: str
    
    # Mode tracking
    current_mode: ExecutionMode
    
    # Backtest results
    backtest_start: Optional[datetime] = None
    backtest_end: Optional[datetime] = None
    backtest_trades: int = 0
    backtest_pnl: float = 0.0
    backtest_win_rate: float = 0.0
    
    # Paper trading results
    paper_start: Optional[datetime] = None
    paper_end: Optional[datetime] = None
    paper_trades: int = 0
    paper_pnl: float = 0.0
    paper_win_rate: float = 0.0
    
    # Live trading results
    live_start: Optional[datetime] = None
    live_trades: int = 0
    live_pnl: float = 0.0
    live_win_rate: float = 0.0
    
    # Aggregate stats (all modes)
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    avg_win: float = 0.0
    avg_loss: float = 0.0
    largest_win: float = 0.0
    largest_loss: float = 0.0
    max_drawdown: float = 0.0
    sharpe_ratio: Optional[float] = None
    
    def update_from_trade(self, trade: TradeRecord):
        """Update track record with a new closed trade"""
        if not trade.is_closed or trade.realized_pnl is None:
            return
        
        # Update mode-specific stats
        if trade.mode == ExecutionMode.BACKTEST:
            self.backtest_trades += 1
            self.backtest_pnl += trade.realized_pnl
            if not self.backtest_start:
                self.backtest_start = trade.timestamp
            self.backtest_end = trade.exit_timestamp
            
        elif trade.mode == ExecutionMode.PAPER:
            self.paper_trades += 1
            self.paper_pnl += trade.realized_pnl
            if not self.paper_start:
                self.paper_start = trade.timestamp
            self.paper_end = trade.exit_timestamp
            
        elif trade.mode == ExecutionMode.LIVE:
            self.live_trades += 1
            self.live_pnl += trade.realized_pnl
            if not self.live_start:
                self.live_start = trade.timestamp
        
        # Update aggregate stats
        self.total_trades += 1
        
        if trade.realized_pnl > 0:
            self.winning_trades += 1
            self.avg_win = (
                (self.avg_win * (self.winning_trades - 1) + trade.realized_pnl)
                / self.winning_trades
            )
            self.largest_win = max(self.largest_win, trade.realized_pnl)
        else:
            self.losing_trades += 1
            self.avg_loss = (
                (self.avg_loss * (self.losing_trades - 1) + trade.realized_pnl)
                / self.losing_trades
            )
            self.largest_loss = min(self.largest_loss, trade.realized_pnl)
        
        # Recalculate win rates
        if self.backtest_trades > 0:
            self.backtest_win_rate = sum(
                1 for t in self._get_trades(ExecutionMode.BACKTEST)
                if t.realized_pnl and t.realized_pnl > 0
            ) / self.backtest_trades
        
        if self.paper_trades > 0:
            self.paper_win_rate = sum(
                1 for t in self._get_trades(ExecutionMode.PAPER)
                if t.realized_pnl and t.realized_pnl > 0
            ) / self.paper_trades
        
        if self.live_trades > 0:
            self.live_win_rate = sum(
                1 for t in self._get_trades(ExecutionMode.LIVE)
                if t.realized_pnl and t.realized_pnl > 0
            ) / self.live_trades
    
    def _get_trades(self, mode: ExecutionMode) -> list[TradeRecord]:
        """Get trades for a specific mode (would query DB in real implementation)"""
        # Placeholder - would actually query database
        return []
    
    def get_summary(self) -> Dict[str, Any]:
        """Get human-readable summary"""
        return {
            "current_mode": self.current_mode.value,
            "total_trades": self.total_trades,
            "win_rate": self.winning_trades / self.total_trades if self.total_trades > 0 else 0,
            "total_pnl": self.backtest_pnl + self.paper_pnl + self.live_pnl,
            "paper_performance": {
                "trades": self.paper_trades,
                "pnl": self.paper_pnl,
                "win_rate": self.paper_win_rate,
            } if self.paper_trades > 0 else None,
            "live_performance": {
                "trades": self.live_trades,
                "pnl": self.live_pnl,
                "win_rate": self.live_win_rate,
            } if self.live_trades > 0 else None,
        }


def should_graduate_to_live(track_record: StrategyTrackRecord) -> tuple[bool, str]:
    """
    Determine if a strategy should graduate from paper to live trading
    
    Criteria:
    - At least 20 paper trades
    - Win rate > 55%
    - Positive P&L
    - Max drawdown < 20%
    """
    if track_record.paper_trades < 20:
        return False, f"Need {20 - track_record.paper_trades} more paper trades"
    
    if track_record.paper_win_rate < 0.55:
        return False, f"Win rate too low: {track_record.paper_win_rate:.1%} (need >55%)"
    
    if track_record.paper_pnl <= 0:
        return False, f"Paper P&L is negative: ${track_record.paper_pnl:.2f}"
    
    if abs(track_record.max_drawdown) > 0.20:
        return False, f"Max drawdown too large: {track_record.max_drawdown:.1%}"
    
    return True, "✅ Strategy meets graduation criteria!"
