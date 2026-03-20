"""
Central tool definitions file - Registry only
All LLM-callable tools are defined here using the @tool decorator.
Implementations are in modules/tools/implementations/
"""
from typing import Dict, Any, List, Optional
from modules.tools import tool
from modules.agent.context import AgentContext

# Import tool descriptions
from modules.tools.descriptions import (
    # Control
    IDLE_DESC,
    # Code Execution (Universal Interface)
    EXECUTE_CODE_DESC,
    # File Management (Convenient wrappers with DB sync)
    WRITE_CHAT_FILE_DESC, READ_CHAT_FILE_DESC, REPLACE_IN_CHAT_FILE_DESC,
    # ETF Builder
    BUILD_CUSTOM_ETF_DESC,
    # Web Search
    WEB_SEARCH_DESC, NEWS_SEARCH_DESC, SCRAPE_URL_DESC,
)

# Import implementations
from modules.tools.implementations import control
from modules.tools.implementations import code_execution, file_management, etf_builder, web_search
from modules.tools.implementations import bots as bots_impl


# ============================================================================
# MARKET DATA & WEB - Done in Code via execute_code
# ============================================================================
# API calls (FMP, Polygon, Reddit) are now done directly in code via finch_runtime.
# Web scraping can be done with requests/beautifulsoup in execute_code.
# No separate tool definitions needed - all via code execution.


# ============================================================================
# CONTROL TOOLS
# ============================================================================

@tool(
    description=IDLE_DESC,
    category="control",
    hidden_from_ui=True
)
def idle(*, context: AgentContext) -> Dict[str, Any]:
    """Signal completion and return to idle state"""
    return control.idle_impl(context)


# ============================================================================
# CODE EXECUTION TOOL
# ============================================================================

@tool(
    name="bash",
    description=EXECUTE_CODE_DESC,
    category="code"
)
async def bash(*, cmd: str, context: AgentContext):
    """Run a bash command in the persistent sandbox."""
    params = code_execution.BashParams(cmd=cmd)
    async for item in code_execution.bash_impl(params, context):
        yield item


# ============================================================================
# FILE MANAGEMENT TOOLS (Convenient Wrappers)
# ============================================================================

@tool(
    name="write_chat_file",
    description=WRITE_CHAT_FILE_DESC,
    category="files"
)
async def write_chat_file(*, context: AgentContext, filename: str, file_content: str):
    """Write file to chat directory with DB sync"""
    async for item in file_management.write_chat_file_impl(context, filename, file_content):
        yield item


@tool(
    name="read_chat_file",
    description=READ_CHAT_FILE_DESC,
    category="files"
)
async def read_chat_file(
    *,
    context: AgentContext,
    filename: str,
    start_line: Optional[int] = None,
    end_line: Optional[int] = None,
    peek: bool = False,
):
    """Read file from chat directory, optionally by line range. Set peek=True to read first ~100 lines (like Cursor)."""
    return await file_management.read_chat_file_impl(context, filename, start_line, end_line, peek)


@tool(
    name="replace_in_chat_file",
    description=REPLACE_IN_CHAT_FILE_DESC,
    category="files"
)
async def replace_in_chat_file(
    *,
    filename: str,
    old_str: Optional[str] = None,
    new_str: Optional[str] = None,
    replace_all: bool = False,
    edits: Optional[List[file_management.EditItem]] = None,
    context: AgentContext
):
    """Replace text in file. Supports single edit (old_str/new_str) or multiple edits."""
    async for item in file_management.replace_in_chat_file_impl(old_str, new_str, filename, context, replace_all, edits):
        yield item


# ============================================================================
# ETF BUILDER TOOL
# ============================================================================

@tool(
    name="build_custom_etf",
    description=BUILD_CUSTOM_ETF_DESC,
    category="analysis"
)
async def build_custom_etf(*, params: etf_builder.BuildCustomETFParams, context: AgentContext):
    """Build a custom ETF portfolio"""
    async for item in etf_builder.build_custom_etf_impl(params, context):
        yield item


# ============================================================================
# WEB SEARCH TOOLS
# ============================================================================

@tool(
    name="web_search",
    description=WEB_SEARCH_DESC,
    category="web"
)
def web_search_tool(
    *,
    query: str,
    num_results: int = 10,
    search_type: str = "search",
    context: AgentContext
):
    """Search the web using Google via Serper API"""
    return web_search.web_search_impl(query, context, num_results, search_type)


@tool(
    name="news_search",
    description=NEWS_SEARCH_DESC,
    category="web"
)
def news_search(
    *,
    query: str,
    num_results: int = 10,
    context: AgentContext
):
    """Search Google News for recent articles"""
    return web_search.news_search_impl(query, context, num_results)


@tool(
    name="scrape_url",
    description=SCRAPE_URL_DESC,
    category="web"
)
def scrape_url(
    *,
    url: str,
    timeout: int = 30,
    context: AgentContext
):
    """Scrape a webpage and convert to clean markdown text"""
    return web_search.scrape_url_impl(url, context, timeout)


# ============================================================================
# BOT MANAGEMENT TOOLS
# ============================================================================

CONFIGURE_BOT_DESC = """Update this bot's settings. All parameters are optional — pass only what you want to change.

Use this to set your name, capital, and position limits.
Only available in bot chats."""

PLACE_TRADE_DESC = """Place a trade (buy or sell) with full tracking. This is the ONLY way you should place trades.

**IMPORTANT:** Do NOT use bash/code to place orders directly (e.g. kalshi.post("/portfolio/orders")).
Always use this tool — it automatically handles tracking, capital, and risk limits.

**Buy:** Opens a new position.
- action: "buy"
- market: Market ticker (e.g. "KXNHLGAME-26MAR09OTTVAN-OTT")
- side: "yes" or "no"
- count: Number of contracts (default: 1)
- price: Price in cents (1-99). REQUIRED. Check the market price first and set this to the price you're willing to pay.
- reason: Brief explanation of why you're trading

**Sell:** Closes an existing position.
- action: "sell"
- position_id: ID of the position to close (required for sells)
- price: Price in cents (1-99). Optional for sells — if omitted, uses current market bid.
- reason: Why you're exiting

**Fill behavior:** This places a LIMIT order. If your price doesn't cross the spread, the order
will rest on the book unfilled and return success=false with status "resting". Only filled
(or partially filled) orders create positions.

**Strategies for getting filled:**
1. **Aggressive (immediate fill):** Set your buy price at or above the current ask price
   (or sell price at or below the current bid). This crosses the spread and fills instantly.
   Costs more but guarantees execution.
2. **Iterative (price improvement):** Place a limit order at your desired price. If it comes
   back as "resting", cancel it with cancel_order, then retry at a slightly better price.
   Repeat until filled. This can get better prices but takes multiple steps.
3. **Patient (passive):** Place at your price and leave it. The order sits on the book and
   may fill later if the market moves to you.

**Tip:** Always check the market's bid/ask spread first. For thin markets, the spread can be
wide (10-20¢). Pricing at the mid-point often won't fill — you may need to cross to the ask.

What it does automatically:
- Checks capital balance and risk limits
- Places a limit order at your specified price
- Checks fill status from the exchange response
- Creates a trade log entry (status: executed, partial, resting, or failed)
- Creates/closes a tracked position (only for filled contracts)
- Manages capital balance (deduct on buy, credit on sell, refund if unfilled)

Use bash for research only (checking markets, prices, events).
Only available in bot chats."""

CANCEL_ORDER_DESC = """Cancel a resting (unfilled) order on the exchange by its order ID.

Use this when a limit order didn't fill (place_trade returned status "resting") and you want to:
- Retry at a different price
- Abandon the trade entirely

The order_id is returned by place_trade when the order rests unfilled.
Only available in bot chats."""


@tool(
    name="configure_bot",
    description=CONFIGURE_BOT_DESC,
    category="bot_management",
)
async def configure_bot(
    *,
    name: Optional[str] = None,
    capital_usd: Optional[float] = None,
    max_positions: Optional[int] = None,
    context: AgentContext,
):
    """Update bot settings."""
    return await bots_impl.configure_bot_impl(
        context, name=name,
        capital_usd=capital_usd, max_positions=max_positions,
    )


@tool(
    name="place_trade",
    description=PLACE_TRADE_DESC,
    category="bot_management",
)
async def place_trade(
    *,
    action: str,
    market: str = "",
    side: str = "yes",
    count: int = 1,
    reason: str = "",
    price: Optional[int] = None,
    position_id: Optional[str] = None,
    context: AgentContext,
):
    """Place a trade (buy or sell) with full tracking."""
    return await bots_impl.place_trade_impl(
        context, action=action, market=market, side=side, count=count,
        reason=reason, price=price,
        position_id=position_id,
    )


LIST_TRADES_DESC = """List your recent trade history. Shows all tracked trades with status, price, P&L.
Use this to review your performance, check what trades were executed, and analyze patterns.
Only available in bot chats."""


@tool(
    name="list_trades",
    description=LIST_TRADES_DESC,
    category="bot_management",
)
async def list_trades(*, limit: int = 20, context: AgentContext):
    """List recent trades for this bot."""
    return await bots_impl.list_trades_impl(context, limit=limit)


@tool(
    name="cancel_order",
    description=CANCEL_ORDER_DESC,
    category="bot_management",
)
async def cancel_order(*, order_id: str, context: AgentContext):
    """Cancel a resting order on the exchange."""
    return await bots_impl.cancel_order_impl(context, order_id=order_id)


SCHEDULE_WAKEUP_DESC = """Schedule a future wake-up for this bot. When the time comes, a new chat thread
is created and the bot runs with full tool access, seeing the reason in its system prompt.

Use this to wake yourself up at important times — e.g. before a market resolves, to review
a position after a news event, or for any future action you want to take.

Parameters:
- trigger_at: ISO 8601 datetime string (UTC) for when to wake up (e.g. "2026-03-15T14:00:00Z")
- reason: Why you're waking up — this appears in your system prompt when triggered
- trigger_type: Category — "resolution_check", "periodic_review", or "custom" (default: "custom")
- position_id: Optional — link to a specific position this wakeup is about
- recurrence: Optional — set a recurring schedule. Supported patterns:
    "every_30m", "every_1h", "every_4h" — interval-based
    "daily_9am", "daily_2pm" — daily at a specific hour (UTC)
  When set, the bot will be automatically re-woken at each interval.
- message: Optional — custom instruction/prompt sent to the bot when this wakeup fires.
  Use this to tell your future self exactly what to do (e.g. "Scan weather markets and
  look for mispriced contracts expiring this week"). If not set, defaults to
  "Wakeup triggered. Proceed."

Only available in bot chats."""

LIST_WAKEUPS_DESC = """List your scheduled wake-ups. Returns pending wakeups with their trigger times and reasons.
Only available in bot chats."""

CANCEL_WAKEUP_DESC = """Cancel a pending wake-up by its ID. Only available in bot chats."""


@tool(
    name="schedule_wakeup",
    description=SCHEDULE_WAKEUP_DESC,
    category="bot_management",
)
async def schedule_wakeup(
    *,
    trigger_at: str,
    reason: str,
    trigger_type: str = "custom",
    position_id: Optional[str] = None,
    recurrence: Optional[str] = None,
    message: Optional[str] = None,
    context: AgentContext,
):
    """Schedule a future wakeup."""
    return await bots_impl.schedule_wakeup_impl(
        context, trigger_at=trigger_at, reason=reason,
        trigger_type=trigger_type, position_id=position_id,
        recurrence=recurrence, message=message,
    )


@tool(
    name="list_wakeups",
    description=LIST_WAKEUPS_DESC,
    category="bot_management",
)
async def list_wakeups_tool(*, context: AgentContext):
    """List pending wakeups."""
    return await bots_impl.list_wakeups_impl(context)


@tool(
    name="cancel_wakeup",
    description=CANCEL_WAKEUP_DESC,
    category="bot_management",
)
async def cancel_wakeup_tool(*, wakeup_id: str, context: AgentContext):
    """Cancel a pending wakeup."""
    return await bots_impl.cancel_wakeup_impl(context, wakeup_id=wakeup_id)


# ============================================================================
# TOOL EXPORTS
# ============================================================================

__all__ = [
    # Control
    'idle',
    # Code Execution
    'bash',
    # File Management
    'write_chat_file', 'read_chat_file', 'replace_in_chat_file',
    # ETF Builder
    'build_custom_etf',
    # Web Search
    'web_search_tool', 'news_search', 'scrape_url',
    # Bot Management
    'configure_bot',
    'place_trade',
    'cancel_order',
    'list_trades',
    'schedule_wakeup',
    'list_wakeups_tool',
    'cancel_wakeup_tool',
]

