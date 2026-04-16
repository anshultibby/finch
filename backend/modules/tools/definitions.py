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
    # Agent Management
    CREATE_AGENT_DESC,
)

# Import implementations
from modules.tools.implementations import control
from modules.tools.implementations import code_execution, file_management, etf_builder, web_search
from modules.tools.implementations import agents as agents_impl


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
# BROKERAGE / PORTFOLIO TOOLS (SnapTrade)
# ============================================================================

from modules.tools.implementations import snaptrade as snaptrade_impl


@tool(
    name="connect_brokerage",
    description=(
        "Start the brokerage connection flow for the user. "
        "Generates an OAuth URL for the user to link their brokerage account via SnapTrade. "
        "Returns a connection_url the user must open to authenticate. "
        "Call this when the user has no connected brokerage or wants to add a new one."
    ),
    category="portfolio",
)
async def connect_brokerage(*, context: AgentContext, broker: Optional[str] = None) -> Dict[str, Any]:
    """Generate OAuth URL for brokerage connection."""
    return await snaptrade_impl.connect_brokerage_impl(context, broker)


@tool(
    name="get_brokerage_status",
    description=(
        "Check whether the user has a connected brokerage account. "
        "Returns connected=True/False and a list of account names. "
        "Always call this first before attempting get_portfolio."
    ),
    category="portfolio",
)
async def get_brokerage_status(*, context: AgentContext) -> Dict[str, Any]:
    """Check brokerage connection status."""
    return await snaptrade_impl.get_brokerage_status_impl(context)


@tool(
    name="get_portfolio",
    description=(
        "Fetch the user's live portfolio holdings across all connected brokerage accounts. "
        "Returns positions with symbol, shares, current_price, average_purchase_price (cost basis), "
        "gain_loss, and gain_loss_percent. "
        "Use this to get the data needed for tax loss harvesting analysis. "
        "Requires a connected brokerage — call get_brokerage_status first."
    ),
    category="portfolio",
)
async def get_portfolio(*, context: AgentContext) -> Dict[str, Any]:
    """Fetch portfolio holdings with cost basis for TLH analysis."""
    return await snaptrade_impl.get_portfolio_impl(context)


# ============================================================================
# TLH / SWAP PRESENTATION TOOL
# ============================================================================

from modules.tools.implementations import alpaca as alpaca_impl

PRESENT_SWAPS_DESC = """Present tax loss harvesting results to the user as interactive swap cards.
Pass the path to the saved TLH plan JSON file (e.g. '/home/user/data/tlh_plan.json').
The tool reads the file from the sandbox, extracts harvest_now + borderline opportunities,
and renders them as cards in the 'Opportunities' sidebar tab.
After calling this, tell the user to check the Opportunities tab."""


@tool(
    name="present_swaps",
    description=PRESENT_SWAPS_DESC,
    category="swaps"
)
async def present_swaps(*, context: AgentContext, plan_file: str):
    """Present TLH swap opportunities as interactive cards."""
    return await alpaca_impl.present_swaps_impl(context, plan_file)


# ============================================================================
# AGENT MANAGEMENT TOOLS
# ============================================================================

@tool(
    name="create_agent",
    description=CREATE_AGENT_DESC,
    category="agent_management",
)
async def create_agent(
    *,
    name: str,
    task: str,
    platform: str = "research",
    capital_usd: Optional[float] = None,
    icon: Optional[str] = None,
    context: AgentContext,
) -> Dict[str, Any]:
    """Create a new autonomous sub-agent with a queued task."""
    return await agents_impl.create_agent_impl(
        context=context, name=name, task=task, platform=platform,
        capital_usd=capital_usd, icon=icon,
    )




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
    # Brokerage / Portfolio
    'connect_brokerage', 'get_brokerage_status', 'get_portfolio',
    # TLH
    'present_swaps',
    # Agent Management
    'create_agent',
]

