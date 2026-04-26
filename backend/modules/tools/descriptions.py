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

ESTIMATE_TIME_DESC = """Estimate how long this task will take. Call this FIRST before any other tools.

Give a single overall time estimate for the entire task. The user has nothing to do while waiting, so just tell them roughly how long.

Guidelines:
- Quick question / data lookup: ~30 seconds
- Portfolio review or stock research: ~1-2 minutes
- Tax-loss harvesting or strategy creation: ~3-5 minutes
- Complex multi-step analysis: ~5-10 minutes

Set estimated_tools to the number of tool calls you expect to make (used for progress bar).
Set description to a short phrase the user sees while waiting (e.g. "Analyzing your portfolio...").

If the task requires no tools (just a text response), skip calling this tool entirely."""

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
_EXECUTE_CODE_BASE = """Run bash in a persistent sandboxed VM (60s timeout). 
Full Linux — python3, pip, curl, jq, cat, tee, heredoc, whatever you need.

The filesystem persists across calls. Write files, read them back, run scripts — it's just a shell.
When you wanna run code that you are not sure about it is best to write a file and then run it.
this way the iteration and debugging process is much easier.
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
# AGENT MANAGEMENT TOOLS
# ============================================================================

CREATE_AGENT_DESC = """Create a sub-agent and queue its task in one call.

The task is saved as the agent's first message. The agent runs in its own chat
and writes results to the shared sandbox (/home/user/).

Parameters:
  name: short descriptive name (e.g. "TLH Analyzer 2025")
  task: precise instructions — what to do, what files to write, what format
  platform: "research" (default) or "trading"

Task instructions should be brief and precise:
  - What data to fetch and from where
  - What computation to run
  - Where to write results (e.g. /home/user/results/NAME.md)
  - Output format

After creating, tell the user the agent is running and they can peek at progress.
Do NOT write the task as a separate message — put it all in the task parameter."""



# ============================================================================
# MARKET DATA TOOLS (Polygon.io)
# ============================================================================

