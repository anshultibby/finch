"""
Strategies - Automated Trading Bots

CAPABILITIES:
- Create automated trading strategies for Polymarket, Kalshi, or Alpaca
- Define custom entry/exit logic with Python code
- Schedule strategies to run on intervals (every N minutes/hours/days)
- Track strategy performance, positions, and execution history
- Approve strategies for live trading vs dry-run mode

KEY MODULES:
- create_strategy: Create new strategies with entry/exit code
- deploy_from_files: Write files + create strategy record in one call
- query_strategies: List, search, and get strategy details

USAGE PATTERN:
Strategies need: name, thesis, platform, execution_frequency, capital settings.
Entry code: async def check_entry(ctx) -> list of entry signals
Exit code: async def check_exit(ctx, position) -> exit signal or None
Context (ctx) provides: market data, portfolio state, logging, config access.

Strategies start in dry-run mode. Must be approved before live trading.

DEPLOYMENT VIA CODE EXECUTION:
If you have raw file contents (entry.py, exit.py, config.json),
use deploy_from_files.deploy_strategy_from_files(...) to save ChatFiles
and create the strategy record in one call.

If running inside code execution, you can omit user_id/chat_id because
FINCH_USER_ID and FINCH_CHAT_ID are injected into the environment.
"""

from ._base import BaseStrategy, StrategyConfig, Position, EntrySignal, ExitSignal
from .deploy_from_files import (
    deploy_strategy_from_files,
    DeployStrategyFromFilesParams,
    inspect_strategy,
    claim_strategy,
)
from ._loader import StrategyLoader
from ._executor import execute_strategy_cycle

__all__ = [
    'BaseStrategy',
    'StrategyConfig',
    'Position',
    'EntrySignal',
    'ExitSignal',
    'DeployStrategyFromFilesParams',
    'deploy_strategy_from_files',
    'inspect_strategy',
    'claim_strategy',
    'StrategyLoader',
    'execute_strategy_cycle',
]
