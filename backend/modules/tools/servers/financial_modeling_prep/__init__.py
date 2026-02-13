"""
Financial Modeling Prep - Stock Fundamentals & Ownership Data

MODULES & FUNCTIONS:

company.profile:        get_profile(symbol) -> dict
company.executives:     get_executives(symbol) -> list

market.quote:           get_quote_snapshot(symbol) -> list  # Always returns LIST
market.gainers:         get_gainers() -> list
                        get_losers() -> list
                        get_actives() -> list

financials.income_statement:  get_income_statement(symbol, period='annual', limit=5)
financials.balance_sheet:     get_balance_sheet(symbol, period='annual', limit=5)
financials.cash_flow:         get_cash_flow(symbol, period='annual', limit=5)
financials.key_metrics:       get_key_metrics(symbol, period='annual', limit=5)
                              get_key_metrics_ttm(symbol)
financials.ratios:            get_ratios(symbol, period='annual', limit=5)

analyst.price_target:   get_price_targets(symbol) -> list
                        get_price_target_consensus(symbol) -> dict

insider.insider_roster:     get_insider_roster(symbol) -> list  # Officers, directors, 10%+ owners
insider.insider_trading:    get_insider_trading(symbol=None, limit=100) -> list
insider.insider_statistics: get_insider_statistics(symbol) -> dict
insider.senate_trading:     get_senate_trading(symbol=None) -> list
insider.house_trading:      get_house_trading(symbol=None) -> list

ownership.institutional_ownership: get_institutional_ownership(symbol) -> list  # 13F filers

earnings.earnings_calendar: get_earnings_calendar(from_date=None, to_date=None) -> list
                            get_historical_earnings(symbol) -> list

search.search:          search(query, limit=10, exchange=None) -> list

EXAMPLES:
  from servers.financial_modeling_prep.company.profile import get_profile
  profile = get_profile('AAPL')
  
  from servers.financial_modeling_prep.market.quote import get_quote_snapshot
  quote = get_quote_snapshot('AAPL')[0]  # Returns LIST, use [0]
  
  from servers.financial_modeling_prep.insider.insider_roster import get_insider_roster
  insiders = get_insider_roster('AAPL')  # Who owns/controls the company
"""

from .api import fmp

__all__ = ['fmp']
