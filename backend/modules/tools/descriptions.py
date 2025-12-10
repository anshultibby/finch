"""
Tool descriptions for all LLM-callable tools
Separated for better maintainability and readability
"""

# ============================================================================
# PORTFOLIO TOOLS (SnapTrade)
# ============================================================================

GET_PORTFOLIO_DESC = """Fetch the user's current brokerage portfolio holdings (Robinhood, TD Ameritrade, etc.), including stocks they own, quantities, current prices, and total value. 

**When to use:** User asks about portfolio/stocks/holdings/current positions. ALWAYS call this tool first - don't ask for connection upfront.

**Authentication handling:** Tool automatically handles auth. If user isn't connected, it returns needs_auth=true → then call request_brokerage_connection.

**Returns:** Holdings data in CSV format - all positions aggregated across accounts."""

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

GET_FMP_DATA_DESC = """Financial Modeling Prep API - Comprehensive financial data via fmp-data Python client

**⚠️ RATE LIMITS: FMP has aggressive rate limits. For market data (quotes, historical prices), prefer Polygon instead.**

**Best use cases for FMP:**
- Company fundamentals (income statements, balance sheets, ratios)
- Insider trading data (senate, house, corporate insiders)
- Company profiles and executive information
- Market screeners and search

**Avoid FMP for:**
- Historical price data (use Polygon - better limits)
- Real-time quotes for multiple stocks (use Polygon)
- High-frequency data fetching (use Polygon)

**🎯 IMPORTANT: Use execute_code tool for FMP API calls (not this tool directly)**

This tool is API_DOCS_ONLY - it provides documentation but doesn't make API calls.
To actually fetch FMP data:
1. Use `execute_code` tool with Python code
2. Import from working directory: `from finch_runtime import fmp`
3. Call fmp client methods directly in your code

**🚨 CRITICAL: FMP uses modular structure - ALWAYS use fmp.category.method():**
```python
# ✅ CORRECT (these are the ACTUAL methods that exist):
fmp.company.get_profile('AAPL')
fmp.market.get_quote('AAPL')
fmp.market.get_historical_price('AAPL', from_date='2024-01-01', to_date='2024-12-31')
fmp.insider.get_insider_trading('AAPL')

# ❌ WRONG - These methods DON'T EXIST:
fmp.get_profile('AAPL')  # ❌ NO!
fmp.quotes.get_quote('AAPL')  # ❌ NO! Use fmp.market.get_quote()
fmp.historical.get_historical_prices()  # ❌ NO! Use fmp.market.get_historical_price()
fmp.fundamentals.*  # ❌ NO! Use fmp.fundamental.* (singular)
```

**🔍 DISCOVERY: Before using FMP, ALWAYS read the docs in your code:**
```python
# Read finch_runtime.py to see the client wrapper
with open('finch_runtime.py') as f:
    print(f.read())

# This shows you the exact client structure and how to use it
```

**Usage in execute_code:**
```python
from finch_runtime import fmp

# Company Information
profile = fmp.company.get_profile('AAPL')  # Dict with company details
executives = fmp.company.get_executives('AAPL')  # Company executives
search_results = fmp.company.search('Apple', limit=10)  # Search companies

# Market Data (Quotes & Historical Prices)
quote = fmp.market.get_quote('AAPL')  # Current price, volume, change
historical = fmp.market.get_historical_price(
    'AAPL', 
    from_date='2024-01-01', 
    to_date='2024-12-31'
)  # Historical OHLCV data

# Market Movers
gainers = fmp.market.get_gainers(limit=20)
losers = fmp.market.get_losers(limit=20)
active = fmp.market.get_most_active(limit=20)

# Financial Statements (note: "fundamental" is SINGULAR)
income = fmp.fundamental.get_income_statement('AAPL', period='annual', limit=5)
balance = fmp.fundamental.get_balance_sheet('AAPL', period='quarterly', limit=8)
cash_flow = fmp.fundamental.get_cash_flow_statement('AAPL', period='annual', limit=5)

# Key Metrics & Ratios
metrics = fmp.fundamental.get_key_metrics('AAPL', period='annual', limit=5)
ratios = fmp.fundamental.get_ratios('AAPL', period='annual', limit=5)

# Insider Trading
insider = fmp.insider.get_insider_trading('AAPL', limit=100)
senate = fmp.insider.get_senate_trading('AAPL', limit=100)
house = fmp.insider.get_house_trading('AAPL', limit=100)
```

**⚠️ COMMON MISTAKES TO AVOID:**
1. Using `fmp.quotes.*` - quotes are under `fmp.market.get_quote()`
2. Using `fmp.historical.*` - historical prices are `fmp.market.get_historical_price()`
3. Using `fmp.fundamentals.*` - it's `fmp.fundamental.*` (SINGULAR)
4. Using `fmp.search.*` - search is `fmp.company.search()`
5. Calling methods directly on `fmp` - MUST use category first (e.g., `fmp.company.*`)

**Base URL:** https://financialmodelingprep.com
**API Key:** Automatically configured
**Library Docs:** https://github.com/MehdiZare/fmp-data

**Main Client Categories:**
- `fmp.company`: Company profiles, executives, search
- `fmp.market`: Quotes, historical prices, market movers
- `fmp.fundamental`: Financial statements, metrics, ratios (SINGULAR!)
- `fmp.insider`: Insider, senate, house trading data

**Note:** All methods return Python dicts/lists. If you're unsure about a method, read finch_runtime.py or try exploring the client in code first."""


# ============================================================================
# PLANNING TOOLS
# ============================================================================

CREATE_PLAN_DESC = """Create or replace a structured plan for complex multi-step tasks (3+ steps).

**When to use planning:**
- Multi-step research/analysis tasks (gather → analyze → synthesize)
- Complex workflows with clear phases (screen stocks → build ETF → backtest → visualize)
- Building/creating something with distinct stages
- Any task where showing progress structure helps user follow along
- Default to using planning for non-trivial tasks - improves UX!

**When NOT to use:**
- Simple questions or single-action tasks
- Quick data fetches or lookups
- Conversational back-and-forth

**Phase titles:**
Make them descriptive and action-oriented:
- ✓ GOOD: "Fetch portfolio data and calculate returns", "Analyze trading patterns and identify issues"
- ✗ BAD: "Phase 1", "Data", "Analysis"

**Plans are flexible:** Discard and recreate if direction changes - just call create_plan again."""

ADVANCE_PLAN_DESC = "Advance to the next phase in your current plan. Call this when you've completed the current phase and are ready to move to the next one."


# ============================================================================
# WEB CONTENT TOOLS
# ============================================================================

FETCH_WEBPAGE_DESC = "Fetch and read content from any web URL. Useful for reading API documentation, articles, or any web content."


# ============================================================================
# CONTROL TOOLS
# ============================================================================

IDLE_DESC = """Signal that you have completed all tasks and are ready for the user's next input.

Use this tool when:
- You have finished answering the user's question
- You have completed all requested tasks
- You are waiting for additional user input or clarification
- You have nothing more to add to the current conversation

This helps the interface know when to return to an input-ready state.

Do NOT use this tool if:
- You are still processing information
- You are waiting for tool results
- You have more analysis or information to provide"""


# ============================================================================
# CODE EXECUTION TOOL - Universal Interface for All Operations
# ============================================================================

EXECUTE_CODE_DESC = """Execute Python code with direct API access and persistent filesystem (60s timeout).

**🚫 CRITICAL FILE REFERENCE RULE: When you create files, reference them naturally in your response text using [file:filename] syntax. NEVER create separate "Files Created" or "Files Saved" sections. NEVER write "📁 Files Created:" or "I've saved detailed analysis files for you:". This is a hard rule.**

**✍️ CODE STYLE REQUIREMENTS:**
- Write CONCISE code without verbose comments
- NO explanatory comments unless absolutely necessary for complex logic
- NO print statements like "Fetching data..." or "Processing..." unless needed for debugging
- Code should be clean and self-documenting through clear variable names
- NEVER include comments that just restate what the code does (e.g., "# Import pandas" above "import pandas")
- **When unsure about API structure or data format: TEST FIRST with small samples and print statements to explore, THEN write clean final code**

**🎯 YOUR PRIMARY TOOL: Write Python code to accomplish most tasks**

This is your universal interface for:
- API calls (FMP, Polygon, Reddit) 
- Data analysis & transformation
- File operations (read, write, list, search)
- Visualization & charting
- Backtesting & calculations
- Multi-step workflows with intermediate data

**Execution Modes (mode parameter):**

1. **isolated (default)** - Fresh state each execution
   - New Python process, no state persistence
   - Use for: Production scripts, final code, one-off analysis
   
2. **notebook** - Persistent state like Jupyter! 🚀
   - Variables, imports, functions persist between calls
   - Build up analysis incrementally across multiple executions
   - Use for: Iterative development, data exploration, debugging
   - Reset state: `execute_code(code="__reset_kernel__", mode="notebook")`

**Code Source:**
1. **Inline Code** (code param): Quick analysis - no file created
2. **File Execution** (filename param): Run a saved .py file

**🔥 Notebook Mode Examples (Incremental Development):**

```python
# Cell 1: Import and load data (slow - do once!)
execute_code(mode="notebook", code=\"\"\"
import pandas as pd
from finch_runtime import fmp

# This persists for next cells!
profiles = [fmp.company.get_profile(t) for t in ['AAPL', 'MSFT', 'GOOGL']]
df = pd.DataFrame(profiles)
print(f"Loaded {len(df)} profiles")
\"\"\")

# Cell 2: Analyze (df is still here!)
execute_code(mode="notebook", code=\"\"\"
# df persists from Cell 1!
print(df[['companyName', 'mktCap', 'pe']].head())
avg_mktcap = df['mktCap'].mean()
print(f"Avg Market Cap: ${avg_mktcap:,.0f}")
\"\"\")

# Cell 3: Visualize (use df and avg_mktcap!)
execute_code(mode="notebook", code=\"\"\"
import matplotlib.pyplot as plt
df.plot(x='companyName', y='mktCap', kind='bar')
plt.axhline(avg_mktcap, color='r', linestyle='--', label='Average')
plt.savefig('market_caps.png')
\"\"\")

# Reset if needed
execute_code(mode="notebook", code="__reset_kernel__")
```

**When to use notebook mode:**
- ✅ Exploring data interactively
- ✅ Debugging (inspect intermediate values)
- ✅ Large dataset (load once, use many times)
- ✅ Building up complex analysis step-by-step
- ✅ Testing API responses before final code

**When to use isolated mode:**
- ✅ Final production scripts
- ✅ One-off calculations
- ✅ When you want guaranteed clean state

**🚨 CRITICAL: Progressive Disclosure - Discover Before Using**

The execution environment contains a filesystem with API documentation and helpers.
**ALWAYS explore before making API calls:**

```python
# 1. See what's available in your environment
import os
print("Available files:", os.listdir('.'))
print("API docs:", os.listdir('apis/'))

# 2. Read API documentation
with open('finch_runtime.py') as f:
    print(f.read())

# 3. Explore client structure dynamically
from finch_runtime import fmp
print("FMP categories:", dir(fmp.client))
print("Company methods:", dir(fmp.company))

# 4. Test with small samples first
result = fmp.company.get_profile('AAPL')
print(type(result))
print(result.keys() if isinstance(result, dict) else result[:2])
```

**📁 File Operations (Pure Python - No Tool Calls Needed)**

```python
# List files/directories
import os
files = os.listdir('.')  # Current directory
files = os.listdir('analysis/')  # Subdirectory

# Read files
with open('data.csv') as f:
    content = f.read()

# Write files (auto-saves to database)
with open('results.csv', 'w') as f:
    f.write(data)

# Check if file exists
if os.path.exists('portfolio.csv'):
    # Load and use it

# Create directories
os.makedirs('analysis/2024', exist_ok=True)

# Search in files (use grep/find patterns)
import fnmatch
py_files = [f for f in os.listdir('.') if fnmatch.fnmatch(f, '*.py')]
```

**🚨 FILE NAMING (Professional Developer Standards):**
- ✗ FORBIDDEN: `script.py`, `data.csv`, `chart.png`, `output.csv`, `results.csv`
- ✓ REQUIRED: `nvda_insider_trades_2024.csv`, `portfolio_vs_spy_ytd.png`, `momentum_strategy_backtest.py`
- Include context: tickers, date ranges, strategy names, metrics

**📎 After Creating Files - Reference Them:**
- Use `[file:filename.ext]` in your response to create clickable links
- Images (.png, .jpg, .jpeg, .gif, .svg) embed inline automatically
- CRITICAL: NEVER create "Files Created" sections or file summary lists with emojis (like "📁 Files Created"). Reference files naturally in your explanation text.

**🌐 API Clients (Pre-configured & Ready)**

```python
from finch_runtime import fmp, reddit, polygon

# Financial Modeling Prep (fundamentals, insider trading)
# ⚠️ Rate limited - prefer Polygon for price data
profile = fmp.company.get_profile('AAPL')
insider = fmp.insider.get_insider_trading('AAPL', limit=100)
metrics = fmp.fundamental.get_key_metrics('AAPL', period='annual')

# Polygon (market data - PREFERRED for prices/quotes)
# ✅ Better rate limits, use for backtesting
from datetime import datetime, timedelta
end = datetime.now()
start = end - timedelta(days=365)
aggs = polygon.get_aggs('AAPL', 1, 'day', start.strftime('%Y-%m-%d'), end.strftime('%Y-%m-%d'))
snapshot = polygon.get_snapshot_ticker('stocks', 'AAPL')

# Reddit sentiment (ApeWisdom)
trending = reddit.get_trending(limit=20)
sentiment = reddit.get_ticker_sentiment('GME')
```

**🚨 Common API Mistakes (Read finch_runtime.py to avoid these!):**
- ❌ `fmp.quotes.*` → Use `fmp.market.get_quote()`
- ❌ `fmp.historical.*` → Use `fmp.market.get_historical_price()`  
- ❌ `fmp.fundamentals.*` → Use `fmp.fundamental.*` (SINGULAR!)
- ❌ `fmp.get_profile()` → Use `fmp.company.get_profile()`

**💾 Data Persistence & Multi-Step Workflows**

The filesystem persists across executions. Use it for:

```python
# Step 1: Fetch and save data
data = fetch_large_dataset()
with open('raw_data.csv', 'w') as f:
    f.write(data.to_csv())

# Step 2 (later execution): Load and analyze
import pandas as pd
df = pd.read_csv('raw_data.csv')
results = analyze(df)
with open('analysis_results.json', 'w') as f:
    import json
    json.dump(results, f)

# Data flows through code environment - NOT through LLM context!
```

**🔍 Code Quality Best Practices:**

```python
# When unsure about data structure, test with small sample first
result = api_call()
print(type(result), len(result) if hasattr(result, '__len__') else '')
print(result[:2] if isinstance(result, list) else result)

# Validate data (only print if error/important)
if not data or len(data) == 0:
    print("⚠️ No data returned from API")

# Safe dictionary access
value = item.get('key', default_value)

# Error handling
try:
    result = risky_operation()
except Exception as e:
    print(f"Error: {e}")
```

**📊 Visualization (Users LOVE Charts):**

```python
import matplotlib.pyplot as plt
import pandas as pd

plt.figure(figsize=(12, 6))
plt.plot(dates, prices, label='Portfolio')
plt.plot(dates, benchmark, label='SPY')
plt.title('Portfolio vs SPY - YTD Performance')
plt.legend()
plt.savefig('portfolio_vs_spy_ytd.png')

# Remember to reference it: [file:portfolio_vs_spy_ytd.png]
```

**🔄 Error Recovery Pattern:**

If code fails:
1. Read the error message carefully
2. Fix the issue (update variable, correct API method, add error handling)  
3. Re-run the code
4. **Don't give up after one failure!**

**📦 Available Packages:**
pandas, numpy, requests, matplotlib, plotly, seaborn, scikit-learn, beautifulsoup4, scipy

**⚠️ NOT AVAILABLE:** yfinance, yahoo_fin

**Environment Details:**
- Timeout: 60 seconds
- Working directory: Persistent across executions
- API keys: Pre-configured (FMP_API_KEY, POLYGON_API_KEY)
- Python: 3.x with standard library + packages above"""


# ============================================================================
# FILE MANAGEMENT TOOLS
# ============================================================================

WRITE_CHAT_FILE_DESC = """Write a file to the persistent chat filesystem (syncs to database).

**CRITICAL: Write CONCISE code without verbose comments. NO explanatory comments unless complex logic requires it.**

**When to use:**
- Saving reusable scripts/code
- Storing analysis results for later reference
- Creating data files that persist across sessions

**In code execution, you can also use standard Python:**
```python
with open('results.csv', 'w') as f:
    f.write(data)  # Also syncs to DB automatically
```

Use this tool when you want explicit streaming feedback during file save."""

READ_CHAT_FILE_DESC = """Read a file from the persistent chat filesystem.

**In code execution, prefer standard Python:**
```python
with open('data.csv') as f:
    content = f.read()
```

Use this tool only if you need to read a file outside of code execution context."""

REPLACE_IN_CHAT_FILE_DESC = """Replace text in a file (like str_replace in Cursor).

**Use for:**
- Fixing code errors after execution
- Updating thresholds/parameters
- Modifying existing logic

**Example:** Replace "limit=10" with "limit=50" in script.py"""


# ============================================================================
# ETF BUILDER TOOL
# ============================================================================

BUILD_CUSTOM_ETF_DESC = """Build a custom ETF portfolio with specified stocks weighted by market capitalization.

**What it does:**
- Takes list of tickers and creates weighted portfolio (market cap weighted only for now)
- Fetches current market data (prices, market caps) for all tickers
- Calculates portfolio weights and displays allocation breakdown
- Returns structured data ready for backtesting

**Typical workflow:**
1. Screen stocks (execute_code) → Get list of tickers
2. Build ETF (this tool) → Get portfolio allocation
3. Backtest (execute_code) → Analyze historical performance
4. Visualize if needed (execute_code with matplotlib/plotly)
5. Compare to benchmarks (SPY, QQQ, etc.)

**Use cases:**
- After screening, build portfolio from top candidates
- Create thematic portfolios (e.g., "AI stocks", "dividend aristocrats")
- Build custom indices for backtesting

**Returns:** Portfolio composition with weights, prices, and market caps"""


# ============================================================================
# MARKET DATA TOOLS (Polygon.io)
# ============================================================================

POLYGON_API_DOCS_DESC = """Polygon.io REST API - Real-time and historical market data

**✅ PREFERRED FOR MARKET DATA: Polygon has better rate limits than FMP**

**Best use cases for Polygon:**
- Historical price data (OHLCV) - excellent for backtesting
- Real-time quotes and snapshots
- Batch data fetching for multiple tickers
- High-frequency data needs
- Previous close, daily aggregates

**🎯 IMPORTANT: Use execute_code tool for Polygon API calls (not this tool directly)**

This tool is API_DOCS_ONLY - it provides documentation but doesn't make API calls.
To actually fetch Polygon data:
1. Use `execute_code` tool with Python code
2. Import from working directory: `from finch_runtime import polygon`
3. Call polygon methods directly in your code

**Usage in execute_code:**
```python
from finch_runtime import polygon
from datetime import datetime

# Historical price data (OHLCV) - Best for backtesting
aggs = polygon.get_aggs(
    ticker='AAPL',
    multiplier=1,
    timespan='day',  # 'minute', 'hour', 'day', 'week', 'month'
    from_='2024-01-01',
    to='2024-12-31'
)
# Returns iterator of aggregate bars with open, high, low, close, volume

# Current snapshot (real-time quote)
snapshot = polygon.get_snapshot_ticker('stocks', 'AAPL')

# Ticker details (name, market cap, etc.)
details = polygon.get_ticker_details('AAPL')

# Previous day's close
prev_close = polygon.get_previous_close_agg('AAPL')

# Search tickers
tickers = polygon.list_tickers(search='Apple', market='stocks', limit=10)

# All stocks for a specific date
all_stocks = polygon.get_grouped_daily_aggs('2024-12-10')
```

**Base URL:** https://api.polygon.io
**API Key:** Automatically configured

**Documentation:**
- Python client: https://polygon.readthedocs.io/en/latest/Stocks.html
- REST API: https://polygon.io/docs/stocks/getting-started

**Common Methods:**
- get_aggs(ticker, multiplier, timespan, from_, to): Historical OHLCV bars
- get_snapshot_ticker(ticker_type, ticker): Current market snapshot
- get_ticker_details(ticker): Ticker information
- get_previous_close_agg(ticker): Previous day's data
- list_tickers(search, market, limit): Search tickers
- get_grouped_daily_aggs(date): All tickers for a date"""
