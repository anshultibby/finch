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
    # Memory
    MEMORY_SEARCH_DESC,
    MEMORY_GET_DESC,
    MEMORY_WRITE_DESC,
)

# Import implementations
from modules.tools.implementations import control
from modules.tools.implementations import code_execution, file_management, etf_builder, web_search
from modules.tools.implementations import memory as memory_impl
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
def read_chat_file(
    *,
    context: AgentContext,
    filename: str,
    start_line: Optional[int] = None,
    end_line: Optional[int] = None,
    peek: bool = False,
):
    """Read file from chat directory, optionally by line range. Set peek=True to read first ~100 lines (like Cursor)."""
    return file_management.read_chat_file_impl(context, filename, start_line, end_line, peek)


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
# MEMORY TOOLS
# ============================================================================

@tool(
    name="memory_search",
    description=MEMORY_SEARCH_DESC,
    category="memory",
    hidden_from_ui=True,
)
async def memory_search(
    *,
    query: str,
    max_results: int = 6,
    context: AgentContext,
):
    """BM25 search over all persistent memory files in the user's sandbox."""
    params = memory_impl.MemorySearchParams(query=query, max_results=max_results)
    return await memory_impl.memory_search_impl(params, context)


@tool(
    name="memory_get",
    description=MEMORY_GET_DESC,
    category="memory",
    hidden_from_ui=True,
)
async def memory_get(
    *,
    path: str = "MEMORY.md",
    start_line: Optional[int] = None,
    end_line: Optional[int] = None,
    context: AgentContext,
):
    """Read a specific memory file or line range from the sandbox."""
    params = memory_impl.MemoryGetParams(path=path, start_line=start_line, end_line=end_line)
    return await memory_impl.memory_get_impl(params, context)


@tool(
    name="memory_write",
    description=MEMORY_WRITE_DESC,
    category="memory",
    hidden_from_ui=True,
)
async def memory_write(
    *,
    content: str,
    durable: bool = False,
    context: AgentContext,
):
    """Write a note to durable memory (MEMORY.md) or today's daily log."""
    params = memory_impl.MemoryWriteParams(content=content, durable=durable)
    return await memory_impl.memory_write_impl(params, context)


# ============================================================================
# BOT MANAGEMENT TOOLS
# ============================================================================

CONFIGURE_BOT_DESC = """Update this bot's settings. All parameters are optional — pass only what you want to change.

Use this to set your name, mandate, capital, and position limits.
Only available in bot chats."""

APPROVE_BOT_DESC = """Approve this bot for live trading. The bot must be approved before it can trade real money.
Only available in bot chats."""

RUN_BOT_DESC = """Trigger an immediate bot tick (autonomous run). Use dry_run=True to simulate without placing real orders.
Only available in bot chats."""

CLOSE_POSITION_DESC = """Close a specific open position by its ID. Returns the exit price and realized P&L.
Only available in bot chats."""


@tool(
    name="configure_bot",
    description=CONFIGURE_BOT_DESC,
    category="bot_management",
)
async def configure_bot(
    *,
    name: Optional[str] = None,
    mandate: Optional[str] = None,
    capital_usd: Optional[float] = None,
    max_positions: Optional[int] = None,
    context: AgentContext,
):
    """Update bot settings."""
    return await bots_impl.configure_bot_impl(
        context, name=name, mandate=mandate,
        capital_usd=capital_usd, max_positions=max_positions,
    )


@tool(
    name="approve_bot",
    description=APPROVE_BOT_DESC,
    category="bot_management",
)
async def approve_bot(*, context: AgentContext):
    """Approve bot for live trading."""
    return await bots_impl.approve_bot_impl(context)


@tool(
    name="run_bot",
    description=RUN_BOT_DESC,
    category="bot_management",
)
async def run_bot(*, dry_run: bool = True, context: AgentContext):
    """Trigger an immediate bot tick."""
    return await bots_impl.run_bot_impl(context, dry_run=dry_run)


@tool(
    name="close_position",
    description=CLOSE_POSITION_DESC,
    category="bot_management",
)
async def close_position(*, position_id: str, context: AgentContext):
    """Close a specific open position."""
    return await bots_impl.close_position_impl(context, position_id=position_id)


SCHEDULE_WAKEUP_DESC = """Schedule a future wake-up for this bot. When the time comes, a new chat thread
is created and the bot runs with full tool access, seeing the reason in its system prompt.

Use this to wake yourself up at important times — e.g. before a market resolves, to review
a position after a news event, or for any future action you want to take.

Parameters:
- trigger_at: ISO 8601 datetime string (UTC) for when to wake up (e.g. "2026-03-15T14:00:00Z")
- reason: Why you're waking up — this appears in your system prompt when triggered
- trigger_type: Category — "resolution_check", "periodic_review", or "custom" (default: "custom")
- position_id: Optional — link to a specific position this wakeup is about

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
    context: AgentContext,
):
    """Schedule a future wakeup."""
    return await bots_impl.schedule_wakeup_impl(
        context, trigger_at=trigger_at, reason=reason,
        trigger_type=trigger_type, position_id=position_id,
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
    # Memory
    'memory_search',
    'memory_get',
    'memory_write',
    # Bot Management
    'configure_bot',
    'approve_bot',
    'run_bot',
    'close_position',
    'schedule_wakeup',
    'list_wakeups_tool',
    'cancel_wakeup_tool',
]

