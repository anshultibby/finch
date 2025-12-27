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

READ_CHAT_FILE_DESC = """Read a file from the persistent chat filesystem. **Supports images for visual review!**

**When to use:**
- Reading text files (code, data, configs)
- **VIEWING IMAGES** - Use this to see charts/visualizations you've created and verify they look correct

**For images:** Returns the image data so you can visually inspect it. Use this to:
- Double-check your charts look correct before presenting to user
- Verify axis labels, legends, and titles are readable
- Check that data visualization makes sense
"""

REPLACE_IN_CHAT_FILE_DESC = """Replace text in a file

**Use for:**
- Fixing code errors after execution
- Updating thresholds/parameters
- Modifying existing logic
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
# MARKET DATA TOOLS (Polygon.io)
# ============================================================================

