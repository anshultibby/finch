"""
Tool descriptions for all LLM-callable tools
Separated for better maintainability and readability
"""
import os
from pathlib import Path

from modules.tools.skills_registry import generate_skills_description


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

# Build EXECUTE_CODE_DESC dynamically with skills README content
_EXECUTE_CODE_BASE = """Run bash in a persistent sandboxed VM (60s timeout). Full Linux — python3, pip, curl, jq, cat, tee, heredoc, whatever you need.

The filesystem persists across calls. Write files, read them back, run scripts — it's just a shell.

**Style:**
- Concise. No verbose comments or progress prints.
- Use python3 for data work, bash for everything else.

**Skill scripts** live at `/home/user/skills/<name>/` and are importable directly in python3:
```
python3 -c "from skills.polygon_io.scripts.market.quote import get_last_trade; print(get_last_trade('AAPL'))"
```
Read skill docs with: `cat /home/user/skills/<name>/SKILL.md`
"""

_EXECUTE_CODE_GUIDELINES = """
<guidelines>
1. Available python packages: pandas, numpy, requests, matplotlib, plotly, seaborn, scikit-learn, beautifulsoup4, scipy
2. Install missing packages inline: `pip install <package> -q && python3 script.py`
3. Users love charts — create them proactively.
4. If you don't have enough info, use web_search before running code.
</guidelines>
"""

# Dynamically build the full description with skills registry
EXECUTE_CODE_DESC = _EXECUTE_CODE_BASE + generate_skills_description() + _EXECUTE_CODE_GUIDELINES


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

READ_CHAT_FILE_DESC = """Read a file from the persistent chat filesystem. **Supports partial reads and images!**

**CRITICAL - NEVER READ ENTIRE LARGE FILES UNLESS NECESSARY:**
- `peek=True` reads first ~100 lines (like Cursor's default preview)
- For large data files, use code to parse them instead of reading them fully
- Reading thousands of lines wastes tokens and slows you down

**When to use:**
- Reading text files (code, data, configs) created during this chat session
- **VIEWING IMAGES** - Use this to see charts/visualizations you've created
- **Peeking at large files** - Use peek=True to read first ~100 lines

**Peek at files (PREFERRED for large files):**
- `read_chat_file(filename="data.json", peek=True)` - first ~100 lines only
- `read_chat_file(filename="large_log.txt", peek=True)` - first ~100 lines
- **After peeking, write code to parse the file instead of reading it all**

**Partial reads (for specific sections):**
- `read_chat_file(filename="data.json", start_line=100, end_line=200)` - lines 100-200
- `read_chat_file(filename="code.py", start_line=50, end_line=150)` - specific section

**Returns for text files:**
- content: The file content (or selected lines)
- total_lines: Total lines in file
- start_line/end_line: Actual range returned (if partial)
- navigation: Hints about remaining content

**For images:** Returns the image data so you can visually inspect it.

**For skill documentation:** Use bash instead: `bash('cat /home/user/skills/<name>/SKILL.md')`
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
1. Screen stocks (bash) → Get list of tickers
2. Build ETF (this tool) → Get portfolio allocation
3. Backtest (bash) → Analyze historical performance
4. Visualize if needed (bash with matplotlib/plotly)
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
# STRATEGY TOOLS
# ============================================================================

DEPLOY_STRATEGY_DESC = """Promote strategy files from the current chat into a standalone strategy.

**When to use:**
Call this after writing strategy.py + config.json as chat files. It copies
those files into the strategy's own storage (independent of the chat) and
creates the strategy record.

**IMPORTANT: Deploy proactively. Do not ask the user "should I deploy?" — just do it.**
If you've written the strategy files and the user asked you to build a strategy, deploy it.

**Required files (must exist as ChatFiles with these exact names):**
- strategy.py  — single `async def run(ctx)` function (see strategies skill for contract)
- config.json  — platform, capital, risk_limits, schedule

**Strategy code contract:**
strategy.py must define `async def run(ctx)` — no decorators, no classes.
Use ctx.kalshi.place_order() (not create_order) for placing trades.
All Kalshi prices are in CENTS (0-100).

**After deploying, summarize for the user (no code details):**
- "I've created a strategy called '{name}'"
- Explain what it does in 1-2 sentences
- Mention the schedule in human terms
- Remind them it needs approval before live trading
- Offer to do a dry run

**Example response:**
"I've set up a strategy called 'NHL Copy Trader' that:
 • Checks every 15 minutes for consensus trades from top Polymarket sports traders
 • Places matching bets on Kalshi when ≥2 traders agree on a team
 • Max spend: $50 per trade, $200 per day (paper mode — no real money until approved)
 
 Want me to do a test run to show you what it would do right now?"

**Schedule (cron expressions):**
- "0 * * * *"    = every hour at :00
- "*/30 * * * *" = every 30 minutes
- "*/15 * * * *" = every 15 minutes
- "0 9 * * *"    = daily at 9am UTC
- "0 9 * * 1-5"  = weekdays at 9am UTC
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
"""

GET_STRATEGY_CODE_DESC = """Get the full code files for a strategy.

Use when the user asks to see, edit, or review a strategy's code.
Returns all files (strategy.py, config.json, etc.) for the given strategy_id.
"""


# ============================================================================
# MEMORY TOOLS
# ============================================================================

MEMORY_SEARCH_DESC = """Semantically search across all your persistent memory files.

Runs BM25 keyword search over MEMORY.md and all memory/YYYY-MM-DD.md daily logs.
Returns ranked snippets — the most relevant facts from past sessions.

**Use this at the start of a session when the user's request might relate to prior work:**
- "analyze X again" → search "X analysis results"
- "how did that strategy do?" → search "strategy performance backtest"
- "remember my preferences?" → search "user preferences trading style"
- Any topic the user has discussed before

**Returns:** list of snippets with source file and relevance score.
"""

MEMORY_GET_DESC = """Read a specific memory file (or a line range within it).

**Files:**
- `MEMORY.md` — durable long-term facts and preferences (default)
- `memory/YYYY-MM-DD.md` — a specific day's running notes

**When to use:**
- You got a search hit and want to read the full surrounding context
- You want to review everything stored about a topic
- Start of session full memory review (read MEMORY.md)

Use memory_search first to find the right file/range, then memory_get to read it.
"""

MEMORY_WRITE_DESC = """Write a note or fact to persistent memory.

**durable=True → MEMORY.md** (use for):
- User preferences ("user prefers momentum strategies over mean-reversion")
- Key decisions ("decided to use 7% trailing stop as default")
- Important results ("AAPL backtest Jan-Dec 2024: +23% vs +18% buy-and-hold")
- Recurring context ("user trades Kalshi prediction markets, focuses on political events")

**durable=False (default) → today's daily log**:
- Today's analysis notes
- What was researched/found this session
- Intermediate results worth remembering

**Always write memory when:**
- User says "remember this"
- You produce a key insight, backtest result, or strategy outcome
- You learn something durable about the user's preferences or style
"""


# ============================================================================
# MARKET DATA TOOLS (Polygon.io)
# ============================================================================

