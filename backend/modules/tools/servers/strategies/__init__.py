"""
Strategy Servers - User-created trading bots with standardized interface

Each user can create custom strategies that are:
- Stored as files in database (similar to chat files)
- Loaded dynamically at runtime
- Executed on schedule with standardized interface
"""

from ._base import BaseStrategy, StrategyConfig, Position, EntrySignal, ExitSignal
from ._loader import StrategyLoader
from ._executor import execute_strategy_cycle

__all__ = [
    'BaseStrategy',
    'StrategyConfig',
    'Position',
    'EntrySignal',
    'ExitSignal',
    'StrategyLoader',
    'execute_strategy_cycle',
]
