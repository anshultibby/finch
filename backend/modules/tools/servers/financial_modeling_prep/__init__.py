"""
Financial Modeling Prep - Fundamental Data & Company Research

CAPABILITIES:
- Company profiles (sector, industry, description, market cap, employees)
- Financial statements (income, balance sheet, cash flow) - quarterly & annual
- Key metrics and financial ratios (PE, ROE, debt ratios, growth rates)
- Earnings calendar and estimates
- Stock quotes with fundamentals (PE, EPS, market cap in one call)
- Market gainers/losers/actives screening
- Analyst price targets and ratings
- Insider trading and Senate stock trades

KEY MODULES:
- market.quote: Quotes with fundamentals (returns LIST even for single stock)
- market.gainers: Top market gainers (filter for liquidity - price > $10)
- company.profile: Full company profile and description
- financials.*: Income statement, balance sheet, cash flow, key metrics
- analyst.price_target: Analyst price targets and consensus
- insider.*: Insider trading activity, Senate trades
- earnings.earnings_calendar: Upcoming and historical earnings dates
- search.search: Search for companies by name or ticker

USAGE PATTERN:
Most functions take symbol as first argument. Results are lists or dicts.
"""

from .api import fmp

__all__ = ['fmp']
