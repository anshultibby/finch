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
# INSIDER TRADING TOOLS (Financial Modeling Prep)
# ============================================================================

GET_SENATE_TRADES_DESC = """Get recent stock trading disclosures from U.S. Senators. Shows what stocks senators are buying and selling. Use when user asks about Senate trades, congressional trades, or what politicians are buying."""

GET_HOUSE_TRADES_DESC = """Get recent stock trading disclosures from U.S. House Representatives. Shows what stocks house members are buying and selling. Use when user asks about House trades or congressional activity."""

GET_INSIDER_TRADES_DESC = """Get recent corporate insider trades (SEC Form 4 filings). Shows what company executives, directors, and major shareholders are buying and selling. Use when user asks about insider trades, insider buying/selling, or Form 4 filings."""

SEARCH_TICKER_INSIDER_DESC = """Search for all insider trading activity (Senate, House, and corporate insiders) for a specific stock ticker. Use when user asks about insider activity for a particular stock."""

GET_PORTFOLIO_INSIDER_DESC = """Get insider trading activity for stocks in the user's portfolio. Shows which portfolio stocks have recent insider/congressional activity. REQUIRES get_portfolio to be called first to get the list of tickers."""

GET_INSIDER_STATISTICS_DESC = """Get quarterly aggregated insider trading statistics for a specific stock. Shows historical trends of insider buying vs selling over time, including buy/sell ratios, average transaction sizes, and patterns. Useful for analyzing long-term insider sentiment."""

SEARCH_INSIDER_TRADES_DESC = """Search insider trades with advanced filters. Filter by specific stock, insider CIK, company CIK, or transaction type (P-Purchase, S-Sale, A-Award, etc.). Useful for finding specific patterns or tracking particular insiders."""


# ============================================================================
# FINANCIAL METRICS TOOLS (Financial Modeling Prep)
# ============================================================================

GET_COMPANY_PROFILE_DESC = """Get comprehensive company profile and information including CEO, industry, sector, market cap, description, and key details. Use this when user asks about basic company information or wants to know about a company."""

GET_INCOME_STATEMENT_DESC = """Get income statement data (revenue, expenses, net income, EPS, etc.) for a stock. Shows profitability and operating performance over time. Use when analyzing revenue, profitability, or earnings."""

GET_BALANCE_SHEET_DESC = """Get balance sheet data (assets, liabilities, equity, debt, cash, etc.) for a stock. Shows financial position and capital structure. Use when analyzing financial health, debt levels, or asset base."""

GET_CASH_FLOW_DESC = """Get cash flow statement data (operating CF, investing CF, financing CF, free cash flow, CapEx) for a stock. Shows how the company generates and uses cash. Use when analyzing cash generation, FCF, or capital allocation."""

GET_KEY_METRICS_DESC = """Get key metrics and valuation ratios (P/E, P/B, EV/EBITDA, ROE, ROA, debt ratios, FCF yield, dividend yield, etc.). Shows valuation and performance metrics. Use when analyzing valuation or comparing stocks."""

GET_FINANCIAL_RATIOS_DESC = """Get financial ratios (liquidity, profitability, leverage, efficiency ratios). Includes current ratio, quick ratio, ROE, ROA, debt/equity, profit margins, asset turnover, etc. Use when analyzing financial health or operational efficiency."""

GET_FINANCIAL_GROWTH_DESC = """Get financial growth metrics (revenue growth, earnings growth, EPS growth, FCF growth, etc.) over time. Shows growth trends and rates. Use when analyzing growth or comparing growth rates."""

GET_QUOTE_DESC = """Get real-time stock quote (current price, change, volume, day high/low, 52-week high/low, market cap, P/E, moving averages). Use when user asks for current stock price or market data."""

GET_HISTORICAL_PRICES_DESC = """Get historical stock prices (OHLCV data) for technical analysis or price trends. Returns daily prices with open, high, low, close, and volume. Use when analyzing price history or creating price charts."""

GET_ANALYST_RECOMMENDATIONS_DESC = """Get analyst recommendations (strong buy, buy, hold, sell, strong sell ratings) over time. Shows Wall Street consensus. Use when user asks about analyst ratings or what analysts think."""


# ============================================================================
# SCREENING & SEARCH
# ============================================================================

SCREEN_STOCKS_DESC = """Screen stocks based on financial criteria like market cap, price, sector, industry. Find stocks matching specific investment criteria. Use when user wants to find stocks with certain characteristics."""


# ============================================================================
# MARKET MOVERS & PERFORMANCE
# ============================================================================

GET_TOP_GAINERS_DESC = """Get biggest stock gainers today. Shows stocks with largest price increases. Use when user asks what stocks are up the most or what's moving."""

GET_TOP_LOSERS_DESC = """Get biggest stock losers today. Shows stocks with largest price decreases. Use when user asks what stocks are down the most."""

GET_MOST_ACTIVE_DESC = """Get most actively traded stocks. Shows stocks with highest trading volume. Use when user asks what stocks are most active or have highest volume."""

GET_SECTOR_PERFORMANCE_DESC = """Get sector performance showing how different market sectors are performing. Use when user asks about sector performance or which sectors are doing well."""


# ============================================================================
# NEWS & PRESS RELEASES
# ============================================================================

GET_STOCK_NEWS_DESC = """Get latest stock news articles. Optionally filter by specific symbols. Use when user asks for news about stocks."""


# ============================================================================
# ETF DATA
# ============================================================================

GET_ETF_HOLDINGS_DESC = """Get ETF holdings showing what stocks/assets an ETF contains. Use when user asks what's in an ETF or wants to see ETF composition."""

GET_ETF_INFO_DESC = """Get ETF information including expense ratio, AUM, and other key details. Use when user asks about ETF details or characteristics."""


# ============================================================================
# CORPORATE EVENTS
# ============================================================================

GET_EARNINGS_CALENDAR_DESC = """Get earnings calendar showing upcoming earnings announcements. Use when user asks when companies report earnings or wants to see earnings schedule."""

GET_DIVIDENDS_CALENDAR_DESC = """Get dividends calendar showing upcoming dividend payments. Use when user asks about dividend payment dates or dividend schedule."""


# ============================================================================
# ANALYST DATA (EXTENDED)
# ============================================================================

GET_PRICE_TARGET_DESC = """Get analyst price targets showing where analysts think a stock will trade. Use when user asks about price targets or analyst expectations."""

GET_UPGRADES_DOWNGRADES_DESC = """Get analyst upgrades and downgrades showing rating changes from Wall Street analysts. Use when user asks about analyst ratings changes or upgrades/downgrades."""


# ============================================================================
# COMPARISONS & PEERS
# ============================================================================

GET_PEER_COMPANIES_DESC = """Get peer companies in the same sector and market cap range. Use when user wants to compare a stock to its competitors or find similar companies."""


# ============================================================================
# ESG
# ============================================================================

GET_ESG_SCORES_DESC = """Get ESG (Environmental, Social, Governance) scores showing how sustainable/ethical a company is. Use when user asks about ESG, sustainability, or social responsibility."""


# ============================================================================
# SEC FILINGS
# ============================================================================

GET_SEC_FILINGS_DESC = """Get SEC filings like 10-K, 10-Q, 8-K for regulatory documents. Use when user asks about SEC filings or wants to see official company documents."""


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

