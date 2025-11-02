"""
API Client modules for external services.

Each client module handles communication with a specific external API:
- fmp: Financial Modeling Prep (financial data, insider trading)
- apewisdom: Reddit sentiment data
- snaptrade: Portfolio and brokerage data
- plotting: Chart generation
"""
from .fmp import fmp_tools
from .apewisdom import apewisdom_tools
from .snaptrade import snaptrade_tools
from .plotting import create_chart

__all__ = ['fmp_tools', 'apewisdom_tools', 'snaptrade_tools', 'create_chart']

