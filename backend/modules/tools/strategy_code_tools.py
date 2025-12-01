"""
Strategy Code Tools - LLM generates executable code for strategies

Much faster and more reliable than LLM-per-rule interpretation:
- One LLM call to generate code vs. hundreds to execute
- Deterministic results (same inputs → same outputs)
- Debuggable (can inspect/modify the actual code)
- Perfect for backtesting
"""
from modules.tools import tool
from modules.agent.context import AgentContext
from models.sse import SSEEvent
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
import logging
import json

logger = logging.getLogger(__name__)


# ============================================================================
# Pydantic Models
# ============================================================================

class CreateCodeStrategyParams(BaseModel):
    """Parameters for creating a code-based strategy"""
    name: str = Field(..., description="Strategy name")
    description: str = Field(..., description="Natural language description of the strategy logic")
    data_sources: List[str] = Field(
        default_factory=list,
        description="FMP endpoints to fetch (e.g., 'income-statement', 'key-metrics')"
    )
    risk_params: Dict[str, Any] = Field(
        default_factory=lambda: {
            "budget": 1000,
            "max_positions": 5,
            "position_size_pct": 20,
            "stop_loss_pct": 10,
            "take_profit_pct": 25
        },
        description="Risk management parameters"
    )


class ExecuteCodeStrategyParams(BaseModel):
    """Parameters for executing a code-based strategy"""
    strategy_name: str = Field(..., description="Name of strategy to execute")
    candidates: Optional[List[str]] = Field(
        None,
        description="Specific tickers to screen (if None, uses SP500)"
    )
    limit: Optional[int] = Field(
        10,
        description="Max candidates to screen"
    )


# ============================================================================
# File Management Tools
# ============================================================================

@tool(
    name="list_chat_files",
    description="List files in the current chat session",
    category="files"
)
def list_chat_files(*, context: AgentContext):
    """List files in chat directory"""
    from modules.resource_manager import resource_manager
    
    try:
        files = resource_manager.list_chat_files(context.user_id, context.chat_id)
        return {
            "success": True,
            "files": files,
            "count": len(files),
            "path": f"resources/{context.user_id}/chats/{context.chat_id}/"
        }
    except Exception as e:
        logger.error(f"Error listing chat files: {str(e)}", exc_info=True)
        return {"success": False, "error": str(e)}


@tool(
    name="write_chat_file",
    description="Write a file to the current chat session",
    category="files"
)
def write_chat_file(
    *,
    context: AgentContext,
    filename: str,
    content: str
):
    """Write file to chat directory"""
    from modules.resource_manager import resource_manager
    
    try:
        path = resource_manager.write_chat_file(
            context.user_id,
            context.chat_id,
            filename,
            content
        )
        return {
            "success": True,
            "path": path,
            "message": f"Wrote {filename} to chat directory"
        }
    except Exception as e:
        logger.error(f"Error writing chat file: {str(e)}", exc_info=True)
        return {"success": False, "error": str(e)}


@tool(
    name="read_chat_file",
    description="Read a file from the current chat session",
    category="files"
)
def read_chat_file(
    *,
    context: AgentContext,
    filename: str
):
    """Read file from chat directory"""
    from modules.resource_manager import resource_manager
    
    try:
        content = resource_manager.read_chat_file(
            context.user_id,
            context.chat_id,
            filename
        )
        if content is None:
            return {"success": False, "error": f"File '{filename}' not found"}
        
        return {
            "success": True,
            "content": content,
            "filename": filename
        }
    except Exception as e:
        logger.error(f"Error reading chat file: {str(e)}", exc_info=True)
        return {"success": False, "error": str(e)}


# ============================================================================
# Strategy Code Tools
# ============================================================================

@tool(
    name="create_code_strategy",
    description="""Create a strategy by generating executable Python code.

This is MUCH better than rule-based strategies because:
- Fast: One LLM call to generate vs. hundreds to execute
- Deterministic: Same inputs → same outputs
- Debuggable: You can see and modify the actual code
- Perfect for backtesting

**Workflow:**
1. User describes strategy (e.g., "Buy tech stocks with >20% revenue growth")
2. LLM generates Python screening function
3. Code is validated in sandbox
4. Strategy saved as markdown file with embedded code
5. Execute strategy → runs code directly on each ticker (no LLM calls!)

**Example:**
{
    "name": "High Growth Tech",
    "description": "Buy technology stocks with revenue growth >20% and P/E ratio <30",
    "data_sources": ["income-statement", "key-metrics"],
    "risk_params": {
        "budget": 1000,
        "max_positions": 5,
        "position_size_pct": 20,
        "stop_loss_pct": 10,
        "take_profit_pct": 25
    }
}

The LLM will generate a `screen(ticker, data)` function and `manage(ticker, position, data)` function.""",
    category="strategy"
)
async def create_code_strategy(
    *,
    context: AgentContext,
    params: CreateCodeStrategyParams
):
    """Create a strategy by generating code"""
    from modules.strategy_code_generator import strategy_code_generator
    from modules.resource_manager import resource_manager
    
    yield SSEEvent(event="tool_status", data={
        "status": "generating",
        "message": f"Generating code for '{params.name}'..."
    })
    
    try:
        # Generate screening code
        yield SSEEvent(event="tool_status", data={
            "status": "generating",
            "message": "Generating screening function..."
        })
        
        screening_result = await strategy_code_generator.generate_screening_code(
            strategy_description=params.description,
            data_sources=params.data_sources
        )
        
        if not screening_result["success"]:
            yield {
                "success": False,
                "error": f"Failed to generate screening code: {screening_result['error']}"
            }
            return
        
        # Generate management code
        yield SSEEvent(event="tool_status", data={
            "status": "generating",
            "message": "Generating position management function..."
        })
        
        management_result = await strategy_code_generator.generate_management_code(
            strategy_description=params.description,
            risk_params=params.risk_params
        )
        
        if not management_result["success"]:
            yield {
                "success": False,
                "error": f"Failed to generate management code: {management_result['error']}"
            }
            return
        
        # Save strategy as markdown
        yield SSEEvent(event="tool_status", data={
            "status": "saving",
            "message": "Saving strategy..."
        })
        
        strategy_path = resource_manager.save_strategy(
            user_id=context.user_id,
            strategy_name=params.name,
            description=params.description,
            screening_code=screening_result["code"],
            management_code=management_result["code"],
            metadata=params.risk_params
        )
        
        yield {
            "success": True,
            "strategy_name": params.name,
            "path": strategy_path,
            "screening_code": screening_result["code"],
            "management_code": management_result["code"],
            "screening_explanation": screening_result["explanation"],
            "management_explanation": management_result["explanation"],
            "message": f"✓ Created '{params.name}' with generated code!"
        }
    
    except Exception as e:
        logger.error(f"Error creating code strategy: {str(e)}", exc_info=True)
        yield {"success": False, "error": str(e)}


@tool(
    name="execute_code_strategy",
    description="""Execute a code-based strategy by running generated code on candidates.

This is FAST because:
- No LLM calls during execution (code runs directly)
- Can screen 100 stocks in seconds
- Deterministic results

Returns buy/sell/hold signals with reasoning.""",
    category="strategy"
)
async def execute_code_strategy(
    *,
    context: AgentContext,
    params: ExecuteCodeStrategyParams
):
    """Execute a code-based strategy"""
    from modules.resource_manager import resource_manager
    from modules.code_sandbox import code_sandbox
    from modules.tools.clients.fmp import FMPClient
    import re
    import asyncio
    
    yield SSEEvent(event="tool_status", data={
        "status": "loading",
        "message": f"Loading strategy '{params.strategy_name}'..."
    })
    
    try:
        # Get strategy markdown
        strategy_md = resource_manager.get_strategy(context.user_id, params.strategy_name)
        if not strategy_md:
            yield {"success": False, "error": f"Strategy '{params.strategy_name}' not found"}
            return
        
        # Extract code from markdown
        # Find all python code blocks
        code_blocks = re.findall(r'```python\n(.*?)```', strategy_md, re.DOTALL)
        if len(code_blocks) < 1:
            yield {"success": False, "error": "No code blocks found in strategy"}
            return
        
        screening_code = code_blocks[0]
        management_code = code_blocks[1] if len(code_blocks) > 1 else None
        
        # Get candidates
        if params.candidates:
            tickers = params.candidates[:params.limit] if params.limit else params.candidates
        else:
            # Default: SP500 top N by market cap
            fmp = FMPClient()
            sp500 = await fmp.get_sp500_list()
            tickers = [t['symbol'] for t in sp500[:params.limit]] if params.limit else [t['symbol'] for t in sp500]
        
        yield SSEEvent(event="tool_status", data={
            "status": "screening",
            "message": f"Screening {len(tickers)} candidates..."
        })
        
        # Extract data sources from markdown (look for FMP endpoints mentioned)
        data_sources = []
        if 'income-statement' in strategy_md or 'income_stmt' in screening_code:
            data_sources.append('income-statement')
        if 'key-metrics' in strategy_md or 'key_metrics' in screening_code:
            data_sources.append('key-metrics')
        if 'balance-sheet' in strategy_md or 'balance_sheet' in screening_code:
            data_sources.append('balance-sheet')
        if 'financial-ratios' in strategy_md or 'ratios' in screening_code:
            data_sources.append('financial-ratios')
        
        # If no data sources found, use defaults
        if not data_sources:
            data_sources = ['key-metrics', 'income-statement']
        
        # Screen candidates
        buy_signals = []
        skip_count = 0
        error_count = 0
        
        fmp = FMPClient()
        
        for ticker in tickers:
            try:
                # Fetch data
                data = {}
                for ds in data_sources:
                    try:
                        # Map friendly names to FMP endpoints
                        endpoint_map = {
                            'income-statement': 'income-statement',
                            'balance-sheet': 'balance-sheet-statement',
                            'cash-flow': 'cash-flow-statement',
                            'key-metrics': 'key-metrics',
                            'financial-ratios': 'ratios',
                            'financial-growth': 'financial-growth'
                        }
                        actual_endpoint = endpoint_map.get(ds, ds)
                        result = await fmp.get_financial_data(ticker, actual_endpoint, period='annual', limit=3)
                        data[ds] = result
                    except Exception as e:
                        logger.warning(f"Failed to fetch {ds} for {ticker}: {e}")
                        data[ds] = []
                
                # Execute screening code
                result = code_sandbox.execute_function(
                    screening_code,
                    "screen",
                    ticker=ticker,
                    data=data
                )
                
                if not result["success"]:
                    logger.warning(f"Error screening {ticker}: {result['error']}")
                    error_count += 1
                    continue
                
                decision = result["result"]
                if decision.get("action") == "BUY":
                    buy_signals.append({
                        "ticker": ticker,
                        "action": "BUY",
                        "signal": decision.get("signal", "BULLISH"),
                        "confidence": decision.get("confidence", 50),
                        "reason": decision.get("reason", "")
                    })
                else:
                    skip_count += 1
            
            except Exception as e:
                logger.error(f"Error screening {ticker}: {str(e)}")
                error_count += 1
            
            # Rate limiting
            await asyncio.sleep(0.1)
        
        yield {
            "success": True,
            "strategy_name": params.strategy_name,
            "buy_signals": buy_signals,
            "summary": {
                "screened": len(tickers),
                "buy_signals": len(buy_signals),
                "skipped": skip_count,
                "errors": error_count
            },
            "message": f"✓ Found {len(buy_signals)} BUY signals from {len(tickers)} candidates"
        }
    
    except Exception as e:
        logger.error(f"Error executing code strategy: {str(e)}", exc_info=True)
        yield {"success": False, "error": str(e)}


@tool(
    name="list_code_strategies",
    description="List all code-based strategies",
    category="strategy"
)
def list_code_strategies(*, context: AgentContext):
    """List code-based strategies"""
    from modules.resource_manager import resource_manager
    
    try:
        strategies = resource_manager.list_strategies(context.user_id)
        return {
            "success": True,
            "strategies": strategies,
            "count": len(strategies)
        }
    except Exception as e:
        logger.error(f"Error listing strategies: {str(e)}", exc_info=True)
        return {"success": False, "error": str(e)}


@tool(
    name="get_code_strategy",
    description="Get the full markdown/code for a strategy",
    category="strategy"
)
def get_code_strategy(
    *,
    context: AgentContext,
    strategy_name: str
):
    """Get strategy details"""
    from modules.resource_manager import resource_manager
    
    try:
        content = resource_manager.get_strategy(context.user_id, strategy_name)
        if not content:
            return {"success": False, "error": f"Strategy '{strategy_name}' not found"}
        
        return {
            "success": True,
            "strategy_name": strategy_name,
            "content": content
        }
    except Exception as e:
        logger.error(f"Error getting strategy: {str(e)}", exc_info=True)
        return {"success": False, "error": str(e)}


@tool(
    name="delete_code_strategy",
    description="Delete a code-based strategy",
    category="strategy"
)
def delete_code_strategy(
    *,
    context: AgentContext,
    strategy_name: str
):
    """Delete a strategy"""
    from modules.resource_manager import resource_manager
    
    try:
        success = resource_manager.delete_strategy(context.user_id, strategy_name)
        if not success:
            return {"success": False, "error": f"Strategy '{strategy_name}' not found"}
        
        return {
            "success": True,
            "message": f"Deleted strategy '{strategy_name}'"
        }
    except Exception as e:
        logger.error(f"Error deleting strategy: {str(e)}", exc_info=True)
        return {"success": False, "error": str(e)}

