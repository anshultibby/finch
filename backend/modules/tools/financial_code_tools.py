"""
Financial Code Generation Tools

Simple, focused tools for generating and executing financial analysis code.
No "strategy" abstraction - just clean code generation.
"""
from modules.tools import tool
from modules.agent.context import AgentContext
from models.sse import SSEEvent
from typing import List, Optional, Dict, Any, AsyncGenerator
from pydantic import BaseModel, Field
from utils.logger import get_logger
import os

logger = get_logger(__name__)


class GenerateFinancialCodeParams(BaseModel):
    """Generate Python code for financial analysis"""
    description: str = Field(
        ...,
        description="What the code should do (e.g., 'Calculate revenue growth and compare to industry average')"
    )
    function_name: str = Field(
        default="analyze",
        description="Name for the generated function"
    )
    data_sources: Optional[List[str]] = Field(
        None,
        description="FMP endpoints to use (auto-detected if not provided)"
    )
    save_as: Optional[str] = Field(
        None,
        description="Filename to save code to (optional)"
    )


class ExecuteFinancialCodeParams(BaseModel):
    """Execute saved or inline financial code"""
    code: Optional[str] = Field(
        None,
        description="Python code to execute (provide this OR filename)"
    )
    filename: Optional[str] = Field(
        None,
        description="Filename of saved code (provide this OR code)"
    )
    function_name: str = Field(
        default="analyze",
        description="Function to call in the code"
    )
    ticker: str = Field(
        ...,
        description="Stock ticker to analyze"
    )
    data_sources: Optional[List[str]] = Field(
        None,
        description="FMP endpoints to fetch"
    )


@tool(
    name="generate_financial_code",
    description="""Generate validated Python code for financial analysis.

**What it does:**
- Takes a plain English description
- Generates Python code with FMP data access
- Validates syntax and security
- Tests with sample data
- Returns working code
- Creates todo.md to track progress (Manus-style)

**Example:**
"Calculate revenue growth over last 3 years and profit margin trend"

**Returns:** Validated Python function ready to use.""",
    category="analysis"
)
async def generate_financial_code(
    *,
    params: GenerateFinancialCodeParams,
    context: AgentContext
) -> AsyncGenerator[SSEEvent | Dict[str, Any], None]:
    """Generate financial analysis code"""
    from modules.financial_code_generator import financial_code_generator
    from modules.resource_manager import resource_manager
    from modules.todo_manager import todo_manager
    import os
    
    logger.info(f"Generating code: {params.description}")
    
    # Create todo.md path (in chat directory)
    chat_dir = f"resources/{context.user_id}/chats/{context.chat_id}"
    os.makedirs(chat_dir, exist_ok=True)
    todo_path = f"{chat_dir}/todo.md"
    
    final_result = None
    
    # Determine save path (Manus approach: file path passed through)
    code_save_path = None
    if params.save_as:
        # Create full path in chat directory
        chat_dir = f"resources/{context.user_id}/chats/{context.chat_id}"
        os.makedirs(chat_dir, exist_ok=True)
        code_save_path = f"{chat_dir}/{params.save_as}"
    
    # Generate code with progress tracking
    async for event in financial_code_generator.generate_code(
        task_description=params.description,
        function_name=params.function_name,
        data_sources=params.data_sources,
        todo_path=todo_path,
        save_path=code_save_path  # Pass file path (Manus approach)
    ):
        yield event
        
        if isinstance(event, dict) and "success" in event:
            final_result = event
    
    # Add metadata header if saved
    if final_result and final_result.get("success") and code_save_path:
        # Read generated code
        with open(code_save_path, 'r') as f:
            code = f.read()
        
        # Add header comment
        full_code = f"""'''
{params.description}

Generated function: {params.function_name}
Data sources: {', '.join(final_result.get('data_sources', []))}
'''

{code}
"""
        
        # Write back with header
        with open(code_save_path, 'w') as f:
            f.write(full_code)
        
        final_result["saved_to"] = code_save_path
        final_result["filename"] = params.save_as
    
    # Clean up todo.md (task complete)
    if final_result and final_result.get("success"):
        try:
            todo_manager.cleanup(todo_path)
        except:
            pass  # Not critical
    
    yield final_result


@tool(
    name="execute_financial_code",
    description="""Execute financial analysis code on a ticker.

**What it does:**
- Fetches FMP data for the ticker
- Runs your code with that data
- Returns analysis results

**Use for:**
- Running generated code
- Testing code on real tickers
- Batch analysis across multiple stocks""",
    category="analysis"
)
async def execute_financial_code(
    *,
    params: ExecuteFinancialCodeParams,
    context: AgentContext
) -> AsyncGenerator[SSEEvent | Dict[str, Any], None]:
    """Execute financial code on a ticker"""
    from modules.code_sandbox import code_sandbox
    from modules.tools.clients.fmp import FMPClient
    from modules.resource_manager import resource_manager
    
    yield SSEEvent(event="tool_status", data={
        "status": "loading",
        "message": f"Loading code for {params.ticker}..."
    })
    
    try:
        # Get code (from param or file)
        if params.code:
            code = params.code
        elif params.filename:
            code = resource_manager.read_chat_file(
                context.user_id,
                context.chat_id,
                params.filename
            )
            if not code:
                yield {"success": False, "error": f"File '{params.filename}' not found"}
                return
        else:
            yield {"success": False, "error": "Provide either 'code' or 'filename'"}
            return
        
        # Fetch data
        yield SSEEvent(event="tool_status", data={
            "status": "fetching",
            "message": f"Fetching data for {params.ticker}..."
        })
        
        fmp = FMPClient()
        data = {}
        
        if params.data_sources:
            for source in params.data_sources:
                try:
                    result = await fmp.get_financial_data(params.ticker, source, period='annual', limit=3)
                    data[source] = result
                except Exception as e:
                    logger.warning(f"Failed to fetch {source}: {e}")
                    data[source] = []
        
        # Execute code
        yield SSEEvent(event="tool_status", data={
            "status": "executing",
            "message": "Running analysis..."
        })
        
        result = code_sandbox.execute_function(
            code,
            params.function_name,
            ticker=params.ticker,
            data=data
        )
        
        if not result["success"]:
            yield {
                "success": False,
                "error": result["error"],
                "traceback": result.get("traceback")
            }
            return
        
        yield SSEEvent(event="tool_status", data={
            "status": "complete",
            "message": f"✓ Analysis complete for {params.ticker}"
        })
        
        yield {
            "success": True,
            "ticker": params.ticker,
            "result": result["result"],
            "message": f"✓ Analyzed {params.ticker}"
        }
    
    except Exception as e:
        logger.error(f"Error executing code: {str(e)}", exc_info=True)
        yield {"success": False, "error": str(e)}


@tool(
    name="batch_execute_code",
    description="""Execute financial code on multiple tickers.

Returns results for all tickers in a table format.""",
    category="analysis"
)
async def batch_execute_code(
    *,
    code: Optional[str],
    filename: Optional[str],
    function_name: str,
    tickers: List[str],
    data_sources: Optional[List[str]],
    context: AgentContext
) -> AsyncGenerator[SSEEvent | Dict[str, Any], None]:
    """Execute code on multiple tickers"""
    from modules.code_sandbox import code_sandbox
    from modules.tools.clients.fmp import FMPClient
    from modules.resource_manager import resource_manager
    import asyncio
    
    # Get code
    if code:
        exec_code = code
    elif filename:
        exec_code = resource_manager.read_chat_file(context.user_id, context.chat_id, filename)
    else:
        yield {"success": False, "error": "Provide 'code' or 'filename'"}
        return
    
    yield SSEEvent(event="batch_start", data={
        "tickers": tickers,
        "count": len(tickers)
    })
    
    results = []
    fmp = FMPClient()
    
    for i, ticker in enumerate(tickers):
        yield SSEEvent(event="batch_progress", data={
            "ticker": ticker,
            "index": i + 1,
            "total": len(tickers)
        })
        
        try:
            # Fetch data
            data = {}
            if data_sources:
                for source in data_sources:
                    try:
                        result = await fmp.get_financial_data(ticker, source, period='annual', limit=3)
                        data[source] = result
                    except:
                        data[source] = []
            
            # Execute
            exec_result = code_sandbox.execute_function(
                exec_code,
                function_name,
                ticker=ticker,
                data=data
            )
            
            if exec_result["success"]:
                results.append({
                    "ticker": ticker,
                    **exec_result["result"]
                })
            else:
                results.append({
                    "ticker": ticker,
                    "error": exec_result["error"]
                })
        
        except Exception as e:
            results.append({"ticker": ticker, "error": str(e)})
        
        await asyncio.sleep(0.1)  # Rate limiting
    
    yield {
        "success": True,
        "results": results,
        "count": len(results),
        "message": f"✓ Analyzed {len(results)} tickers"
    }
