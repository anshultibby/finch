"""
FMP (Financial Modeling Prep) API

Progressive disclosure: Explore directories to find endpoints, read .md files for details.

Quick start:
    from servers.fmp.api import fmp
    
    profile = fmp('/profile/AAPL')
    income = fmp('/income-statement/AAPL', {'period': 'annual', 'limit': 5})
"""

from .api import fmp

__all__ = ['fmp']
