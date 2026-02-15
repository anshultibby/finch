"""
Tool descriptions for all LLM-callable tools
Separated for better maintainability and readability
"""
import os
from pathlib import Path

from modules.tools.servers_tree import generate_servers_description


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

# Build EXECUTE_CODE_DESC dynamically with servers README content
_EXECUTE_CODE_BASE = """Execute Python code with direct API access and persistent filesystem (60s timeout).


**✍️ CODE STYLE REQUIREMENTS:**
- Write CONCISE code without verbose comments
- NO explanatory comments unless absolutely necessary for complex logic
- NO print statements like "Fetching data..." or "Processing..." unless needed for debugging
- Code should be clean and self-documenting through clear variable names
- NEVER include comments that just restate what the code does (e.g., "# Import pandas" above "import pandas")

**🎯 YOUR PRIMARY TOOL: Write Python code to accomplish most tasks**
Most of the other tools are available as various files that can be imported from or called in codes.

**🚨 CRITICAL: ALWAYS write code to files first, then execute**

Each execution starts FRESH - NO variables or imports persist between calls.

**Required workflow:**
0. If you don't have enough info then search the web for more information before you start.
1. Use `write_chat_file` to save your code to a descriptive .py file (e.g., `nvda_analysis.py`)
2. Use `execute_code(filename="nvda_analysis.py")` to run it
3. If errors occur, use `replace_in_chat_file` to fix and re-execute
4. Iterate as needed

**Why file-first is mandatory:**
- Errors are much faster to fix (just edit and rerun, no rewriting)
- Code is reusable and iterable
- User can see and download your work
- Debugging is easier with persistent files

**DO NOT use inline code (the `code` param) except for trivial one-liners like `print(os.listdir())`**
"""

_EXECUTE_CODE_GUIDELINES = """

<guidelines>
1. The filesystem persists across executions. Please write code to files in an incremental manner to solve the user's problem.
2. When working with data you can write code to sample the data first and then write the complete fix.
3. These packages are available:
pandas, numpy, requests, matplotlib, plotly, seaborn, scikit-learn, beautifulsoup4, scipy
Make sure you always import the packages you need.
4. Users love charts. Create them proactively to emphasize your points.
5. All the api keys you need are already set up in the environment variables. Please dont create dummy ones
</guidelines>
"""

# Dynamically build the full description with servers tree
EXECUTE_CODE_DESC = _EXECUTE_CODE_BASE + generate_servers_description() + _EXECUTE_CODE_GUIDELINES


# ============================================================================
# FILE MANAGEMENT TOOLS
# ============================================================================

WRITE_CHAT_FILE_DESC = """Write a file to the persistent chat filesystem (syncs to database).

**CRITICAL: Write CONCISE code without verbose comments. NO explanatory comments unless complex logic requires it.**

**When to use:**
- Saving reusable scripts/code
- Storing analysis results for later reference
- Creating data files that persist across sessions
"""

READ_CHAT_FILE_DESC = """Read a file from the persistent chat filesystem. **Supports partial reads, images, and API docs!**

**When to use:**
- Reading text files (code, data, configs)
- **VIEWING IMAGES** - Use this to see charts/visualizations you've created
- **Reading large files partially** - Use start_line/end_line for big files
- **READING API DOCUMENTATION** - Use from_api_docs=True to read server docs

**Reading API documentation (CRITICAL - do this BEFORE using any API):**
- `read_chat_file(filename="AGENTS.md", from_api_docs=True)` - Overview of all APIs
- `read_chat_file(filename="dome/AGENTS.md", from_api_docs=True)` - Dome API (Polymarket/Kalshi)
- `read_chat_file(filename="polygon_io/AGENTS.md", from_api_docs=True)` - Polygon.io stock data
- `read_chat_file(filename="financial_modeling_prep/AGENTS.md", from_api_docs=True)` - FMP fundamentals

**Partial reads (like Cursor):**
- `read_chat_file(filename="data.json")` - full file
- `read_chat_file(filename="data.json", start_line=1, end_line=50)` - first 50 lines
- `read_chat_file(filename="data.json", start_line=100, end_line=150)` - lines 100-150

**Returns for text files:**
- content: The file content (or selected lines)
- total_lines: Total lines in file
- start_line/end_line: Actual range returned (if partial)
- navigation: Hints about remaining content

**For images:** Returns the image data so you can visually inspect it.
"""

REPLACE_IN_CHAT_FILE_DESC = """Replace text in a file (targeted editing). Supports multiple edits in one call.

**CRITICAL: old_str must UNIQUELY identify the text to replace.**

If multiple matches exist, the operation will FAIL. Either:
1. Include more surrounding context (3-5 lines before/after) to make it unique
2. Set replace_all=True to replace ALL occurrences

**Single edit mode:**
- Use old_str + new_str for a single replacement

**Multiple edits mode (recommended for efficiency):**
- Use `edits` parameter with a list of edit objects
- Each edit object has: old_str, new_str, replace_all (optional)
- Edits are applied in sequence, so later edits see results of earlier ones
- If any edit fails, operation stops and returns partial results

Example with multiple edits:
```
edits=[
    {"old_str": "old_value1", "new_str": "new_value1"},
    {"old_str": "old_value2", "new_str": "new_value2"},
    {"old_str": "pattern", "new_str": "replacement", "replace_all": true}
]
```

**Use for:**
- Fixing code errors after execution
- Updating thresholds/parameters
- Modifying existing logic
- Making multiple related changes atomically
"""


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
# WEB SEARCH TOOLS
# ============================================================================

WEB_SEARCH_DESC = """Search the web using Google via Serper API.

**Use this tool when you need:**
- Current information not in your training data
- Recent news about companies, markets, or events
- Research on specific topics
- Verification of current facts

**Search types:**
- "search" (default): General web search
- "news": Google News search for recent articles
- "images": Image search

**Returns:**
- organic: List of web results with title, link, snippet
- news: List of news articles (if search_type="news")
- answerBox: Featured snippet if available
- knowledgeGraph: Knowledge panel if available

**Examples:**
- "NVIDIA Q4 2024 earnings results"
- "Federal Reserve interest rate decision January 2025"
- "best dividend stocks 2025"
"""

NEWS_SEARCH_DESC = """Search Google News for recent articles.

Shortcut for web_search with search_type="news".

**Use for:**
- Breaking news about companies
- Market-moving events
- Industry trends and developments
- Recent announcements

**Returns:** List of news articles with title, link, snippet, date, and source.
"""

SCRAPE_URL_DESC = """Scrape a webpage and convert to clean markdown text.

Uses Jina AI Reader which:
- Removes ads, navigation, footers
- Extracts main content
- Converts to clean markdown
- Handles JavaScript-rendered pages

**Use after web_search to:**
- Read full article content
- Extract detailed information from search results
- Get complete context from a webpage

**Returns:**
- content: Clean markdown text of the page
- title: Page title
- url: Final URL (after redirects)
"""


# ============================================================================
# DELEGATION TOOL (Two-tier agent system)
# ============================================================================

DELEGATE_EXECUTION_DESC = """Delegate execution to the Executor Agent.

**Prerequisites:** You must first create `tasks.md` with a checklist of tasks.

**How it works:**
1. You write `tasks.md` with `- [ ]` checklist items
2. Call this tool with a direction (what to focus on)
3. Executor works through tasks, creates files, executes code
4. Executor saves detailed results to `result_file`
5. You review results and update `tasks.md`

**result_file parameter:**
- Executor saves its detailed results to this file
- Use unique names for each delegation to avoid overwrites!
- Examples: `fetch_results.md`, `analysis_1.md`, `chart_fix.md`
- You can read it later with `read_chat_file(filename="...")`

**Direction examples:**
- "Complete all the data fetching tasks"
- "Fix the chart generation error and retry"  
- "Finish the remaining analysis tasks"

**After delegation:**
- Review the summary in the result
- Use `read_chat_file(filename=result_file)` for full details if needed
- Update `tasks.md` to mark completed tasks `[x]`
"""


FINISH_EXECUTION_DESC = """Signal that you're done and return results to Master Agent.

**Call this when:**
- You've completed all the tasks you can
- You hit an unrecoverable error
- You need to stop and report back

**Required:** summary of what you completed
**Optional:** list of files created, success status, error message

This returns control to the Master Agent with your results.
"""


# ============================================================================
# STRATEGY TOOLS
# ============================================================================

DEPLOY_STRATEGY_DESC = """Deploy chat files as an automated trading strategy.

**IMPORTANT - How to communicate with the user:**

1. BEFORE creating files, explain the strategy in plain language:
   - What it will monitor (e.g., "Fed rate cut markets on Kalshi")
   - What triggers action (e.g., "when price drops below 20 cents")
   - What action it takes (e.g., "buy $50 worth of YES contracts")
   - When it runs (e.g., "every hour" or "once daily at 9am ET")

2. AFTER deploying, summarize for the user:
   - "I've created a strategy called '{name}'"
   - Explain in 1-2 sentences what it does (no code details)
   - Mention the schedule in human terms ("runs every hour")
   - Remind them it needs approval before live trading
   - Offer to do a dry run to show what it *would* do

3. NEVER show code to the user unless they explicitly ask
   - Users don't need to understand Python
   - Focus on WHAT the strategy does, not HOW
   - Use analogies: "like setting a price alert that automatically buys"

4. Risk communication:
   - Always mention the maximum amount at risk per run
   - Explain any conditions/limits built in
   - Be clear about what "dry run" vs "live" means

**Example response to user:**
"I've set up a strategy called 'Fed Rate Dip Buyer' that:
 • Checks Fed rate cut markets every hour
 • Buys $50 of YES contracts when prices fall below 20¢
 • Maximum spend: $50 per trade, $200 per day
 
 Before it can trade with real money, you'll need to approve it.
 Want me to do a test run to show you what it would do right now?"

**Required files:**
- The entrypoint file (default: strategy.py) must define `async def strategy(ctx)`
- ctx provides: ctx.kalshi, ctx.alpaca (future), ctx.log(), ctx.read_json(), etc.

**Schedule (cron expressions):**
- "0 * * * *" = every hour at :00
- "*/30 * * * *" = every 30 minutes
- "0 9 * * *" = daily at 9am UTC
- "0 9 * * 1-5" = weekdays at 9am UTC
"""

LIST_STRATEGIES_DESC = """Get the user's strategies.

Use this when the user:
- Asks "what strategies do I have?"
- Wants to check status of their automations
- References a strategy by name
- Asks "how is X doing?"

**When presenting to user:**
- Show name and plain-language description
- Show status: 🟢 active, 🟡 paused/needs approval, ⚪ never run
- Show last run result in simple terms
- Don't show technical details unless asked

**Example response:**
"You have 2 strategies:

🟢 **Fed Rate Dip Buyer** - runs hourly
   Buys Fed markets when price drops below 20¢
   Last run: 15 min ago - checked 8 markets, no action taken

🟡 **Earnings Momentum** - paused
   Buys prediction markets before earnings announcements
   Needs approval before it can run live"
"""

GET_STRATEGY_DESC = """Get detailed info about a specific strategy.

Use when user asks:
- "How is my Fed strategy doing?"
- "What did X do last time?"
- "Show me the history of Y"

**Present execution history as a simple timeline:**
- "Today 3pm: Checked 5 markets, bought 2 for $40"
- "Today 2pm: Checked 5 markets, no action (prices too high)"
- "Yesterday: Ran 24 times, made 3 trades totaling $85"
"""

UPDATE_STRATEGY_DESC = """Update a strategy's settings.

Users might say:
- "Pause my Fed strategy" → enabled=False
- "Run it every 30 minutes instead" → schedule change
- "Change the buy threshold to 15 cents" → need to update config file
- "Increase the daily limit to $300" → max_daily_usd change

**Important:**
- Can only enable a strategy if it's approved
- When pausing, reassure user their positions are unaffected
- When changing limits, confirm the new limits clearly
"""

APPROVE_STRATEGY_DESC = """Approve a strategy for live execution.

**CRITICAL: Only call this when user explicitly confirms they want to approve.**

Before approving, remind user:
- "Once approved, this strategy can place real orders"
- "You can always pause it later"
- "Want me to do one more dry run first?"

After approving:
- "Your strategy is now approved for live trading"
- "It's still disabled - say 'enable it' when you're ready to start"
"""

RUN_STRATEGY_DESC = """Manually run a strategy.

**ALWAYS default to dry_run=True unless user explicitly says:**
- "run it for real"
- "live run"
- "execute it"
- "do it live"

**Dry run (default):**
- Shows what the strategy WOULD do
- No real orders placed
- Safe to run anytime

**Live run (dry_run=False):**
- Requires strategy to be approved
- Places real orders
- Costs real money

**After running, explain results clearly:**
- Dry run: "If this were live, it would have bought X for $Y"
- Live: "Done! Bought X for $Y. Your new balance is $Z"
"""

DELETE_STRATEGY_DESC = """Delete a strategy.

**Confirm before deleting:**
- "Are you sure you want to delete 'Strategy Name'?"
- "This won't affect any positions you already have"
- "The code files in your chat will still be there"
"""

GET_CHAT_FILES_FOR_STRATEGY_DESC = """Get list of files in current chat for strategy deployment.

Use this internally to see what files are available before calling deploy_strategy.
Don't expose file IDs to user - just use them when deploying.
"""


# ============================================================================
# MARKET DATA TOOLS (Polygon.io)
# ============================================================================

