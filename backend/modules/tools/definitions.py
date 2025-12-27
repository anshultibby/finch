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
    BUILD_CUSTOM_ETF_DESC
)

# Import implementations
from modules.tools.implementations import control
from modules.tools.implementations import code_execution, file_management, etf_builder


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
    name="execute_code",
    description=EXECUTE_CODE_DESC,
    category="code"
)
async def execute_code(
    *, 
    code: Optional[str] = None,
    filename: Optional[str] = None,
    context: AgentContext
):
    """Execute Python code with virtual persistent filesystem
    
    Args:
        code: Python code to execute directly (provide this OR filename)
        filename: Filename of saved code to execute (provide this OR code)
    """
    # Construct params object for implementation
    params = code_execution.ExecuteCodeParams(code=code, filename=filename)
    async for item in code_execution.execute_code_impl(params, context):
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
def read_chat_file(*, context: AgentContext, filename: str):
    """Read file from chat directory"""
    return file_management.read_chat_file_impl(context, filename)


@tool(
    name="replace_in_chat_file",
    description=REPLACE_IN_CHAT_FILE_DESC,
    category="files"
)
async def replace_in_chat_file(*, old_str: str, new_str: str, filename: str, replace_all: bool = False, context: AgentContext):
    """Replace text in file (targeted editing, requires unique match unless replace_all=True)"""
    async for item in file_management.replace_in_chat_file_impl(old_str, new_str, filename, context, replace_all):
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
# TOOL EXPORTS
# ============================================================================

__all__ = [
    # Control
    'idle',
    # Code Execution (Universal Interface)
    'execute_code',
    # File Management (Essential utilities)
    'write_chat_file', 'read_chat_file', 'replace_in_chat_file',
    # ETF Builder
    'build_custom_etf'
]

