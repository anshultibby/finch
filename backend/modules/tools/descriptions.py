"""
Tool descriptions for all LLM-callable tools
Separated for better maintainability and readability
"""

# ============================================================================
# PORTFOLIO TOOLS (SnapTrade)
# ============================================================================

GET_PORTFOLIO_DESC = """Fetch the user's current brokerage portfolio holdings (Robinhood, TD Ameritrade, etc.), including stocks they own, quantities, current prices, and total value. Returns data in efficient CSV format: holdings_csv contains all unique positions aggregated across accounts. ALWAYS call this tool first when the user asks about their portfolio, stocks, holdings, or account value. This tool will automatically handle authentication - if the user isn't connected, it will tell you to request connection. Do not guess or assume - call this tool to check."""

REQUEST_BROKERAGE_CONNECTION_DESC = """Request the user to connect their brokerage account via SnapTrade. ONLY use this tool if get_portfolio returns an authentication error. Do NOT call this proactively - always try get_portfolio first."""


# ============================================================================
# REDDIT SENTIMENT TOOLS (ApeWisdom)
# ============================================================================

GET_REDDIT_TRENDING_DESC = """Get the most talked about and trending stocks from Reddit communities like r/wallstreetbets, r/stocks, and r/investing. Shows current mentions, upvotes, and ranking. Use this when user asks about what's popular/trending on Reddit, what stocks Reddit is talking about, or meme stocks."""

GET_REDDIT_TICKER_SENTIMENT_DESC = """Get Reddit sentiment and mentions for a specific stock ticker. Shows how many times it's been mentioned, upvotes, rank, and 24h change. Use this when user asks about Reddit sentiment for a specific stock."""

COMPARE_REDDIT_SENTIMENT_DESC = """Compare Reddit sentiment for multiple stock tickers. Shows which stocks are more popular on Reddit. Use this when user wants to compare multiple stocks or asks which one Reddit prefers."""


# ============================================================================
# FINANCIAL METRICS TOOLS (Financial Modeling Prep) - UNIVERSAL TOOL
# (Includes: financials, market data, analyst data, insider trading, and more)
# ============================================================================

GET_FMP_DATA_DESC = """Financial Modeling Prep API - Comprehensive financial data

**Workflow for Using FMP API:**
1. Use `fetch_webpage` tool to get documentation: https://site.financialmodelingprep.com/developer/docs
2. Parse the HTML to discover available endpoints and their parameters
3. Write Python code using `fmp.fetch()` to call the endpoints
4. Execute the code with `execute_code` tool

**Usage in Code:**
```python
from finch_runtime import fmp

# Use the simple fetch() method
quote = fmp.fetch('quote', {'symbol': 'AAPL'})
income = fmp.fetch('income-statement', {'symbol': 'AAPL', 'period': 'annual', 'limit': 5})
insider_trades = fmp.fetch('insider-trading', {'symbol': 'NVDA', 'limit': 100})
```

**Base URL:** https://financialmodelingprep.com/api/v3
**API Key:** Automatically added by fmp.fetch()
**Documentation:** https://site.financialmodelingprep.com/developer/docs

**Common Endpoints:**
- quote, profile, income-statement, balance-sheet-statement, cash-flow-statement
- key-metrics, ratios, financial-growth, historical-price-full
- insider-trading, senate-trading, house-trading
- search-symbol, company-screener, biggest-gainers, most-actives"""
