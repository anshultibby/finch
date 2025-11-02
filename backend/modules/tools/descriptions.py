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

GET_FMP_DATA_DESC = """Universal tool to fetch ANY financial data from Financial Modeling Prep API. Call this ONE tool with the appropriate endpoint and parameters.

AVAILABLE ENDPOINTS:

**Company Info:**
- profile: Get company profile (params: symbol)

**Financial Statements:**
- income-statement: Income statement - revenue, expenses, net income, EPS (params: symbol, period [annual/quarter], limit)
- balance-sheet: Balance sheet - assets, liabilities, equity, debt (params: symbol, period, limit)
- cash-flow-statement: Cash flow - operating/investing/financing CF, FCF (params: symbol, period, limit)

**Key Metrics & Ratios:**
- key-metrics: Valuation ratios - P/E, P/B, EV/EBITDA, ROE, FCF yield (params: symbol, period, limit)
- financial-ratios: Financial ratios - liquidity, profitability, leverage (params: symbol, period, limit)
- financial-growth: Growth metrics - revenue/earnings/FCF growth (params: symbol, period, limit)

**Market Data:**
- quote: Real-time quote - current price, volume, day range (params: symbol)
- historical-price-eod/full: Historical prices - OHLCV data (params: symbol, from, to, limit)

**Analyst Data:**
- grade: Analyst recommendations over time (params: symbol, limit)
- price-target-consensus: Analyst price targets (params: symbol)
- grades: Analyst upgrades/downgrades (params: symbol, limit)

**Search & Screening:**
- search-symbol: Search for stock symbols (params: query, limit)
- company-screener: Screen stocks by criteria (params: marketCapMoreThan, priceMoreThan, limit, etc.)

**Market Movers:**
- biggest-gainers: Top gainers (no params)
- biggest-losers: Top losers (no params)
- most-actives: Most active stocks (no params)
- sector-performance-snapshot: Sector performance (no params)

**News:**
- news/stock: News for specific symbols (params: symbols, limit)
- news/stock-latest: Latest news (params: page, limit)

**ETF:**
- etf/holdings: ETF holdings (params: symbol)
- etf/info: ETF information (params: symbol)
- etf/sector-weightings: ETF sector allocation (params: symbol)

**Events:**
- earnings-calendar: Earnings announcements (params: from, to)
- dividends-calendar: Dividend payments (params: from, to)
- splits: Stock splits history (params: symbol)

**Economic:**
- treasury-rates: Treasury rates (params: from, to)
- economic-indicators: Economic data like GDP (params: name, from, to)

**Other:**
- stock-peers: Peer companies (params: symbol)
- esg-ratings: ESG scores (params: symbol)
- sec-filings-search/symbol: SEC filings (params: symbol, limit, from, to)

**Insider Trading:**
- senate-latest: Recent Senate trades (params: page, limit)
- house-latest: Recent House trades (params: page, limit)
- insider-trading/latest: Recent corporate insider trades (params: page, limit)
- insider-trading-search: Search insider trades (params: symbol, reportingCik, companyCik, transactionType, limit, page)
- insider-trading-statistics: Quarterly insider stats (params: symbol)

EXAMPLES:
- Get AAPL profile: get_fmp_data(endpoint="profile", params={"symbol": "AAPL"})
- Get income statement: get_fmp_data(endpoint="income-statement", params={"symbol": "AAPL", "period": "annual", "limit": 10})
- Get market gainers: get_fmp_data(endpoint="biggest-gainers", params={})
- Get Senate trades: get_fmp_data(endpoint="senate-latest", params={"page": 0, "limit": 50})
- Search AAPL insider trades: get_fmp_data(endpoint="insider-trading-search", params={"symbol": "AAPL", "limit": 50})

Use this tool for ANY financial data request including insider trading - just specify the endpoint and parameters."""


# ============================================================================
# FINANCIAL ANALYSIS AGENT DELEGATION
# ============================================================================

ANALYZE_FINANCIALS_DESC = """Delegate to a specialized financial metrics agent to comprehensively analyze stocks and financial data. This expert agent has access to ALL Financial Modeling Prep (FMP) tools and can:

FINANCIAL ANALYSIS:
- Income statements, balance sheets, cash flow statements (quarterly/annual)
- Key metrics (P/E, ROE, ROA, debt ratios, FCF yield, dividend yield, etc.)
- Financial ratios (liquidity, profitability, leverage, efficiency)
- Financial growth trends (revenue growth, earnings growth, etc.)
- Company profiles and detailed information

MARKET DATA & SCREENING:
- Real-time quotes and historical prices
- Screen stocks by market cap, price, sector, industry, country
- Find peer companies and competitors
- Identify market gainers, losers, and most active stocks
- Sector and industry performance analysis

ANALYST & INVESTOR DATA:
- Analyst recommendations and consensus ratings
- Price targets and analyst expectations
- Upgrades and downgrades from Wall Street analysts
- ESG (Environmental, Social, Governance) scores

CORPORATE EVENTS & NEWS:
- Earnings calendar and announcements
- Dividend schedules and payment dates
- Stock splits history
- Latest stock news and press releases
- SEC filings (10-K, 10-Q, 8-K)

ETF ANALYSIS:
- ETF holdings and composition
- ETF information (expense ratio, AUM, etc.)
- Sector weightings and allocations

The agent will intelligently select the right tools based on your objective and provide structured insights with key findings, trends, and actionable analysis. Use this for ANY comprehensive financial analysis task - the agent will figure out what data to fetch and how to analyze it.

EXAMPLES:
- "Analyze AAPL's profitability and cash generation over 5 years"
- "Compare TSLA vs F financial health and growth"
- "Find tech stocks under $100 with strong FCF"
- "What are analysts saying about NVDA?"
- "Show me the top gainers today and analyze why"
- "Compare AAPL to its peers in terms of valuation"
- "Analyze SPY ETF holdings and sector allocation"
- "What's MSFT's ESG score and how does it compare?"
"""


# ============================================================================
# VISUALIZATION TOOLS (Plotting Agent Delegation)
# ============================================================================

CREATE_PLOT_DESC = """Create an interactive chart or plot with optional trendlines. This tool delegates to a specialized plotting agent that will analyze your data and create the best visualization. Supports line charts, bar charts, scatter plots, and area charts. Can add trendlines (linear, polynomial, exponential, moving average) for analysis. The plot will be saved as a RESOURCE that you can reference in your response. After calling this tool, you can tell the user about the plot that was created and mention they can view it in the resources sidebar. Use this when the user asks to visualize data, show trends, create charts, or compare values graphically."""

