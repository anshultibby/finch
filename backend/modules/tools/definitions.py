"""
Central tool definitions file
All LLM-callable tools are defined here using the @tool decorator
"""
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from modules.tools import tool, ToolContext, tool_registry
from models.sse import OptionButton

# Import business logic modules (API clients)
from modules.tools.clients.snaptrade import snaptrade_tools
from modules.tools.clients.apewisdom import apewisdom_tools
from modules.tools.clients.fmp import fmp_tools  # Universal FMP tool (includes insider trading)
from modules.tools.clients.plotting import create_chart

# Import agent modules
from modules.agent.plotting_agent import plotting_agent
from modules.agent.financial_metrics_agent import financial_metrics_agent

# Import tool descriptions
from modules.tools.descriptions import (
    # Portfolio
    GET_PORTFOLIO_DESC, REQUEST_BROKERAGE_CONNECTION_DESC,
    # Reddit sentiment
    GET_REDDIT_TRENDING_DESC, GET_REDDIT_TICKER_SENTIMENT_DESC, COMPARE_REDDIT_SENTIMENT_DESC,
    # Financial metrics (FMP - Universal tool including insider trading)
    GET_FMP_DATA_DESC,
    # Financial analysis agent
    ANALYZE_FINANCIALS_DESC,
    # Visualization
    CREATE_PLOT_DESC
)


# ============================================================================
# PORTFOLIO TOOLS (SnapTrade)
# ============================================================================

@tool(
    description=GET_PORTFOLIO_DESC,
    category="portfolio",
    requires_auth=True
)
def get_portfolio(
    *,
    context: ToolContext
) -> Dict[str, Any]:
    """Get user's portfolio holdings"""
    if not context.user_id:
        return {
            "success": False,
            "message": "User ID required",
            "needs_auth": True
        }
    
    return snaptrade_tools.get_portfolio(user_id=context.user_id)


@tool(
    description=REQUEST_BROKERAGE_CONNECTION_DESC,
    category="portfolio",
    requires_auth=False
)
def request_brokerage_connection(
    *,
    context: ToolContext
) -> Dict[str, Any]:
    """Request user to connect their brokerage account"""
    return {
        "success": True,
        "needs_auth": True,
        "message": "Please connect your brokerage account through SnapTrade to continue.",
        "action_required": "show_connection_modal"
    }


# ============================================================================
# REDDIT SENTIMENT TOOLS (ApeWisdom)
# ============================================================================

@tool(
    description=GET_REDDIT_TRENDING_DESC,
    category="reddit_sentiment"
)
async def get_reddit_trending_stocks(
    *,
    context: ToolContext,
    limit: int = 10
) -> Dict[str, Any]:
    """
    Get trending stocks from Reddit communities
    
    Args:
        limit: Number of trending stocks to return (default 10, max 50)
    """
    return await apewisdom_tools.get_trending_stocks(limit=limit)


@tool(
    description=GET_REDDIT_TICKER_SENTIMENT_DESC,
    category="reddit_sentiment"
)
async def get_reddit_ticker_sentiment(
    *,
    context: ToolContext,
    ticker: str
) -> Dict[str, Any]:
    """
    Get Reddit sentiment for a specific stock ticker
    
    Args:
        ticker: Stock ticker symbol (e.g., 'GME', 'TSLA', 'AAPL')
    """
    return await apewisdom_tools.get_ticker_sentiment(ticker=ticker)


@tool(
    description=COMPARE_REDDIT_SENTIMENT_DESC,
    category="reddit_sentiment"
)
async def compare_reddit_sentiment(
    *,
    context: ToolContext,
    tickers: List[str]
) -> Dict[str, Any]:
    """
    Compare Reddit sentiment for multiple tickers
    
    Args:
        tickers: List of ticker symbols to compare (e.g., ['GME', 'AMC', 'TSLA'])
    """
    return await apewisdom_tools.compare_tickers_sentiment(tickers=tickers)


# ============================================================================
# FINANCIAL METRICS TOOLS (Financial Modeling Prep)
# Universal tool for ALL FMP data including insider trading
# ============================================================================

@tool(
    description=GET_FMP_DATA_DESC,
    category="financial_metrics"
)
async def get_fmp_data(
    *,
    context: ToolContext,
    endpoint: str,
    params: Optional[Dict[str, Any]] = None
):
    """Universal tool to fetch ANY financial data from FMP API including insider trading. See description for available endpoints."""
    return await fmp_tools.get_fmp_data(endpoint=endpoint, params=params or {})

# ============================================================================
# FINANCIAL ANALYSIS TOOLS (Financial Metrics Agent Delegation)
# ============================================================================

class AnalyzeFinancialsRequest(BaseModel):
    """Request parameters for financial analysis"""
    objective: str = Field(
        description="Detailed description of what to analyze. Examples: 'Analyze AAPL profitability trends', 'Compare TSLA vs F', 'Find tech stocks under $100', 'What are today's biggest gainers?', 'Analyze SPY ETF holdings'"
    )
    symbols: List[str] = Field(
        default_factory=list,
        description="List of stock ticker symbols to analyze (e.g., ['AAPL'], ['TSLA', 'F']). Can be empty for market screening/search tasks."
    )
    
    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "objective": "Analyze Apple's profitability and cash generation over the past 5 years",
                    "symbols": ["AAPL"]
                },
                {
                    "objective": "Find technology stocks under $50 with market cap over $1B",
                    "symbols": []
                },
                {
                    "objective": "Show me today's biggest gainers and analyze why they're up",
                    "symbols": []
                }
            ]
        }


@tool(
    description=ANALYZE_FINANCIALS_DESC,
    category="financial_analysis"
)
async def analyze_financials(
    *,
    context: ToolContext,
    objective: str,
    symbols: List[str]
) -> Dict[str, Any]:
    """
    Analyze financial metrics and fundamentals for stocks using specialized FMP agent
    
    Args:
        objective: Detailed objective describing what to analyze (e.g., "Analyze Apple's profitability and compare to Microsoft", "Find growth stocks in tech sector")
        symbols: List of ticker symbols to analyze (can be empty for screening/search tasks)
    """
    try:
        import json
        
        # Build message for financial metrics agent
        symbols_str = ", ".join(symbols)
        user_message = f"Objective: {objective}\n\nSymbols to analyze: {symbols_str}"
        
        # Create agent context for financial metrics agent
        from modules.agent.context import AgentContext
        metrics_context = AgentContext(
            user_id=context.user_id,
            chat_id=context.chat_id,
            resource_manager=context.resource_manager
        )
        
        # Build messages using base class
        messages = financial_metrics_agent.build_messages(
            user_message,
            resource_manager=context.resource_manager
        )
        
        # Create LLM config for financial metrics agent
        from modules.agent.llm_config import LLMConfig
        llm_config = LLMConfig.from_config(
            model=financial_metrics_agent.get_model(),
            stream=False
        )
        
        # Run financial metrics agent's tool loop
        result = await financial_metrics_agent.run_tool_loop(
            initial_messages=messages,
            context=metrics_context,
            max_iterations=10,  # Allow multiple tool calls for comprehensive analysis
            llm_config=llm_config
        )
        
        if not result.get("success"):
            return {
                "success": False,
                "message": result.get("message", "Financial metrics agent failed")
            }
        
        # Return the agent's analysis
        return {
            "success": True,
            "objective": objective,
            "symbols": symbols,
            "analysis": result.get("content", ""),
            "tool_results": result.get("tool_results", []),
            "message": "Financial analysis complete. See 'analysis' field for detailed insights."
        }
    
    except Exception as e:
        return {
            "success": False,
            "message": f"Failed to analyze financials: {str(e)}"
        }


# ============================================================================
# VISUALIZATION TOOLS (Plotting Agent Delegation)
# ============================================================================

class CreatePlotRequest(BaseModel):
    """Request parameters for creating a plot"""
    objective: str = Field(
        description="Clear description of what to visualize. Examples: 'Create a line chart showing price trends', 'Compare these values with a bar chart', 'Show correlation with trendline'"
    )
    data: Optional[Dict[str, Any]] = Field(
        None,
        description="Optional data to visualize. Can be raw data - the plotting agent will structure it appropriately. Can include arrays, objects, or structured data."
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "objective": "Create a line chart showing AAPL stock price with a linear trendline",
                "data": {
                    "dates": ["2024-01", "2024-02", "2024-03", "2024-04"],
                    "prices": [150, 155, 153, 160]
                }
            }
        }


@tool(
    description=CREATE_PLOT_DESC,
    category="visualization"
)
async def create_plot(
    *,
    context: ToolContext,
    objective: str,
    data: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Create a plot by delegating to the specialized plotting agent
    
    Args:
        objective: What you want to visualize (e.g., "Show portfolio allocation as a pie chart")
        data: Optional data to visualize (the agent will structure it appropriately)
    """
    try:
        import json
        
        # Build message for plotting agent
        user_message = f"Objective: {objective}"
        if data:
            user_message += f"\n\nData provided:\n{json.dumps(data, indent=2)}"
        
        # Create agent context for plotting agent
        from modules.agent.context import AgentContext
        plotting_context = AgentContext(
            user_id=context.user_id,
            chat_id=context.chat_id,
            resource_manager=context.resource_manager
        )
        
        # Build messages using base class (resource_manager passed via kwargs)
        messages = plotting_agent.build_messages(
            user_message,
            resource_manager=context.resource_manager
        )
        
        # Create LLM config for plotting agent (GPT-5/o1 doesn't support custom temperature)
        from modules.agent.llm_config import LLMConfig
        llm_config = LLMConfig.from_config(
            model=plotting_agent.get_model(),
            stream=False
            # Note: temperature not set - o1 models only support default (1.0)
        )
        
        # Run plotting agent's tool loop (it will automatically call create_chart)
        result = await plotting_agent.run_tool_loop(
            initial_messages=messages,
            context=plotting_context,
            max_iterations=3,  # Plotting should be quick
            llm_config=llm_config
        )
        
        if not result.get("success"):
            return {
                "success": False,
                "message": result.get("message", "Plotting agent failed")
            }
        
        # Extract the plotting result from tool_results
        tool_results = result.get("tool_results", [])
        if tool_results:
            # Get the plot result from the plotting agent
            plot_result = tool_results[0]["result"]
            
            # Enhance the result with resource information
            if plot_result.get("success"):
                plot_result["resource_type"] = "plot"
                plot_result["message"] = f"{plot_result.get('message', '')}. This plot has been saved as a resource and can be viewed in the resources sidebar."
            
            return plot_result
        else:
            # Agent responded without calling tools
            return {
                "success": False,
                "message": f"Plotting agent couldn't create chart: {result.get('content', 'No response')}"
            }
    
    except Exception as e:
        return {
            "success": False,
            "message": f"Failed to create plot: {str(e)}"
        }


# ============================================================================
# INTERACTIVE OPTIONS TOOL
# ============================================================================

class PresentOptionsInput(BaseModel):
    """Input model for present_options tool"""
    question: str = Field(
        ...,
        description="The question to ask the user (shown above the option buttons)"
    )
    options: List[OptionButton] = Field(
        ...,
        description="List of option buttons to present (2-6 options)",
        min_length=2,
        max_length=6
    )


@tool(
    description="""Present interactive option buttons to the user for them to choose from.

Use this when you want to guide the user through a workflow with specific choices rather than open-ended questions.

Examples:
- Investment timeframes (short/medium/long term)
- Analysis depth (quick/standard/deep)
- Portfolio actions (review/opportunities/trim)
- Stock screening criteria (growth/value/dividend)

The user will select one option, and their selection will be returned as the next message.
You should then acknowledge their choice and proceed with the appropriate action.

This provides better UX than asking open-ended questions for well-defined workflows.

IMPORTANT: Do NOT generate any follow-up text after calling this tool. The conversation will pause to wait for user selection.""",
    category="interaction"
)
async def present_options(
    *,
    context: ToolContext,
    params: PresentOptionsInput
) -> Dict[str, Any]:
    """
    Present option buttons to the user
    
    Args:
        params: PresentOptionsInput containing question and option buttons
    """
    # Emit options event through stream_handler if available
    if context.stream_handler:
        await context.stream_handler.emit("options", {
            "question": params.question,
            "options": [opt.model_dump() for opt in params.options]
        })
    
    # Return result indicating options were presented
    # The conversation should pause here waiting for user selection
    return {
        "success": True,
        "message": "Options presented to user. Waiting for user selection.",
        "question": params.question,
        "options": [opt.model_dump() for opt in params.options],
        "_stop_response": True  # Signal that response should end after this
    }


# ============================================================================
# REGISTER ALL TOOLS
# ============================================================================

def register_all_tools():
    """Register all tools with the global registry"""
    # Portfolio tools
    tool_registry.register_function(get_portfolio)
    tool_registry.register_function(request_brokerage_connection)
    
    # Reddit sentiment tools
    tool_registry.register_function(get_reddit_trending_stocks)
    tool_registry.register_function(get_reddit_ticker_sentiment)
    tool_registry.register_function(compare_reddit_sentiment)
    
    # Financial metrics tools (FMP - Universal tool including insider trading)
    tool_registry.register_function(get_fmp_data)
    
    # Financial analysis tools (Financial Metrics Agent)
    tool_registry.register_function(analyze_financials)
    
    # Visualization tools (main agent)
    tool_registry.register_function(create_plot)
    
    # Low-level plotting tools (for plotting sub-agent)
    tool_registry.register_function(create_chart)
    
    # Interactive options tool
    tool_registry.register_function(present_options)


# Auto-register on import
register_all_tools()

