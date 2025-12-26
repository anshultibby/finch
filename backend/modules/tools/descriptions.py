"""
Tool descriptions for all LLM-callable tools
Separated for better maintainability and readability
"""

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

**🚨 CRITICAL: Execution Strategy**

Each execution starts FRESH - NO variables or imports persist between calls.

**Two approaches:**

1. **Inline Code (code param)** - Quick testing & exploration
   - Use for: Testing APIs, exploring data, one-off calculations
   - Each execution is self-contained - include ALL imports and code
   - Example: `execute_code(code="import os; print(os.listdir('servers'))")`

2. **File Execution (filename param)** - Complex multi-step workflows
   - Use for: Analysis requiring multiple steps, avoiding NameErrors
   - Write complete script to .py file with ALL imports and logic
   - Then execute the file
   - File persists in filesystem, can be edited/rerun later

**File-based workflow example:**

```python
# Step 1: Write complete analysis to file
execute_code(code='''
with open("stock_analysis.py", "w") as f:
    f.write(\"\"\"
import pandas as pd
from servers.fmp.market.gainers import get_gainers

# Fetch and analyze
gainers = get_gainers()
df = pd.DataFrame(gainers)
print(f"Found {len(df)} gainers")
print(df[['symbol', 'price', 'changesPercentage']].head(10))
df.to_csv('gainers_analysis.csv')
\"\"\")
''')

# Step 2: Execute the file
execute_code(filename="stock_analysis.py")
```

**When to use each approach:**
- ✅ Inline: Quick tests, exploring APIs, checking file contents
- ✅ File: Multi-step analysis, complex workflows, when you get NameErrors

**🚨 CRITICAL: Progressive Disclosure - ALWAYS Explore First**

The execution environment has a `servers/` directory with API implementations.
**NEVER assume imports exist - ALWAYS discover the structure first!**

**Step 1: List available API servers**
```python
import os
print("Available API servers:", os.listdir('servers'))
# Example output: ['fmp', 'polygon', 'reddit', 'tradingview', 'README.md']
```

**Step 2: Explore a server's categories**
```python
# See what's available in FMP
print("FMP categories:", os.listdir('servers/fmp'))
# Output: ['company', 'financials', 'market', 'insider', 'analyst', ...]
```

**Step 3: Read the server README for usage patterns**
```python
with open('servers/README.md') as f:
    print(f.read())
```

**Step 4: Discover tools in a category**
```python
# See what company tools exist
print("Company tools:", os.listdir('servers/fmp/company'))
# Output: ['profile.py', 'executives.py', '__init__.py']
```

**Step 5: Read the tool file to see its signature and docs**
```python
with open('servers/fmp/company/profile.py') as f:
    print(f.read())
# Shows: function signature, docstring with params & returns
```

**Step 6: Import and use the tool**
```python
from servers.fmp.company.profile import get_profile
profile = get_profile('AAPL')
print(type(profile), profile.keys() if isinstance(profile, dict) else profile[:1])
```

**This discovery pattern is MANDATORY for all API usage!**

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

**🌐 API Usage Examples (After Discovery)**

```python
# Financial Modeling Prep (fundamentals, insider trading)
# ⚠️ Rate limited - prefer Polygon for price data
from servers.fmp.company.profile import get_profile
from servers.fmp.insider.insider_trading import get_insider_trading
from servers.fmp.financials.key_metrics import get_key_metrics

profile = get_profile('AAPL')
insider = get_insider_trading('AAPL', limit=100)
metrics = get_key_metrics('AAPL', period='annual')

# Polygon (market data - PREFERRED for prices/quotes)
# ✅ Better rate limits, use for backtesting
from servers.polygon.market.historical_prices import get_historical_prices
from servers.polygon.market.quote import get_quote
from datetime import datetime, timedelta

end = datetime.now()
start = end - timedelta(days=365)
prices = get_historical_prices('AAPL', start.strftime('%Y-%m-%d'), end.strftime('%Y-%m-%d'))
quote = get_quote('AAPL')

# Reddit sentiment (ApeWisdom)
from servers.reddit.get_trending_stocks import get_trending_stocks
trending = get_trending_stocks(limit=20)
```

**🚨 Common Mistakes to Avoid:**
- ❌ `from finch_runtime import fmp` - This doesn't exist!
- ❌ Assuming import paths - Always discover first with `os.listdir()`
- ❌ Using APIs without reading their docstrings
- ✅ List → Explore → Read → Import → Test → Use

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

READ_CHAT_FILE_DESC = """Read a file from the persistent chat filesystem. **Supports images for visual review!**

**When to use:**
- Reading text files (code, data, configs)
- **VIEWING IMAGES** - Use this to see charts/visualizations you've created and verify they look correct

**For images:** Returns the image data so you can visually inspect it. Use this to:
- Double-check your charts look correct before presenting to user
- Verify axis labels, legends, and titles are readable
- Check that data visualization makes sense

**In code execution, prefer standard Python for text files:**
```python
with open('data.csv') as f:
    content = f.read()
```

**Example - Verify a chart:**
After creating a chart, use this tool to view it:
`read_chat_file(filename="portfolio_performance.png")`
Then describe what you see to verify it matches your intent."""

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

