"""
Strategies — automated trading bots.

The strategy contract:
  strategy.py  — defines @strategy.on_entry / @strategy.on_exit handlers
  config.json  — platform, capital, risk limits, schedule

The LLM uses create_strategy to scaffold these files, deploy_from_files to
promote them to a standalone strategy record, and query_strategies to inspect
and learn from existing strategies.

Strategies run in the user's persistent E2B sandbox (same as chat code),
ensuring full isolation and access to skill libraries.
"""
from .deploy_from_files import deploy_strategy_from_files, DeployStrategyFromFilesParams

__all__ = [
    "deploy_strategy_from_files",
    "DeployStrategyFromFilesParams",
]
