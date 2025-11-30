"""
Central tool definitions file
All LLM-callable tools are defined here using the @tool decorator
"""
import json
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from modules.tools import tool, tool_registry
from modules.agent.context import AgentContext
from models.sse import OptionButton, SSEEvent

# Import business logic modules (API clients)
from modules.tools.clients.snaptrade import snaptrade_tools
from modules.tools.clients.apewisdom import apewisdom_tools
from modules.tools.clients.fmp import fmp_tools  # Universal FMP tool (includes insider trading)
from modules.tools.clients.plotting import create_chart

# Import tool descriptions
from modules.tools.descriptions import (
    # Portfolio
    GET_PORTFOLIO_DESC, REQUEST_BROKERAGE_CONNECTION_DESC,
    # Reddit sentiment
    GET_REDDIT_TRENDING_DESC, GET_REDDIT_TICKER_SENTIMENT_DESC, COMPARE_REDDIT_SENTIMENT_DESC,
    # Financial metrics (FMP - Universal tool including insider trading)
    GET_FMP_DATA_DESC
)


# ============================================================================
# PORTFOLIO TOOLS (SnapTrade)
# ============================================================================

@tool(
    description=GET_PORTFOLIO_DESC,
    category="portfolio",
    requires_auth=True
)
async def get_portfolio(
    *,
    context: AgentContext
):
    """Get user's portfolio holdings"""
    if not context.user_id:
        yield {
            "success": False,
            "message": "User ID required",
            "needs_auth": True
        }
        return
    
    # Call client which will yield SSE events and then result
    async for item in snaptrade_tools.get_portfolio_streaming(
        user_id=context.user_id
    ):
        yield item


@tool(
    description=REQUEST_BROKERAGE_CONNECTION_DESC,
    category="portfolio",
    requires_auth=False
)
def request_brokerage_connection(
    *,
    context: AgentContext
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
    context: AgentContext,
    limit: int = 10
):
    """
    Get trending stocks from Reddit communities
    
    Args:
        limit: Number of trending stocks to return (default 10, max 50)
    """
    # Yield status event
    yield SSEEvent(
        event="tool_status",
        data={
            "status": "fetching",
            "message": f"Scanning r/wallstreetbets for top {limit} trending stocks..."
        }
    )
    
    result = await apewisdom_tools.get_trending_stocks(limit=limit)
    
    if result.get("success"):
        mentions = result.get("data", {}).get("mentions", [])
        # Yield log event
        yield SSEEvent(
            event="tool_log",
            data={
                "level": "info",
                "message": f"Found {len(mentions)} trending stocks"
            }
        )
    
    # Yield final result
    yield result


@tool(
    description=GET_REDDIT_TICKER_SENTIMENT_DESC,
    category="reddit_sentiment"
)
async def get_reddit_ticker_sentiment(
    *,
    context: AgentContext,
    ticker: str
):
    """
    Get Reddit sentiment for a specific stock ticker
    
    Args:
        ticker: Stock ticker symbol (e.g., 'GME', 'TSLA', 'AAPL')
    """
    yield SSEEvent(
        event="tool_status",
        data={
            "status": "analyzing",
            "message": f"Analyzing Reddit sentiment for ${ticker.upper()} from r/wallstreetbets..."
        }
    )
    
    result = await apewisdom_tools.get_ticker_sentiment(ticker=ticker)
    
    if result.get("success"):
        data = result.get("data", {})
        mentions = data.get("mentions", 0)
        yield SSEEvent(
            event="tool_log",
            data={
                "level": "info",
                "message": f"Found {mentions} Reddit mentions"
            }
        )
    
    yield result


@tool(
    description=COMPARE_REDDIT_SENTIMENT_DESC,
    category="reddit_sentiment"
)
async def compare_reddit_sentiment(
    *,
    context: AgentContext,
    tickers: List[str]
):
    """
    Compare Reddit sentiment for multiple tickers
    
    Args:
        tickers: List of ticker symbols to compare (e.g., ['GME', 'AMC', 'TSLA'])
    """
    tickers_str = ", ".join([t.upper() for t in tickers])
    yield SSEEvent(
        event="tool_status",
        data={
            "status": "analyzing",
            "message": f"Comparing Reddit sentiment: {tickers_str}"
        }
    )
    
    result = await apewisdom_tools.compare_tickers_sentiment(tickers=tickers)
    
    if result.get("success"):
        yield SSEEvent(
            event="tool_log",
            data={
                "level": "info",
                "message": f"Compared {len(tickers)} tickers"
            }
        )
    
    yield result


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
    context: AgentContext,
    endpoint: str,
    params: Optional[Dict[str, Any]] = None
):
    """Universal tool to fetch ANY financial data from FMP API including insider trading. See description for available endpoints."""
    # Handle case where params might be passed as a JSON string
    if isinstance(params, str):
        try:
            params = json.loads(params)
        except json.JSONDecodeError:
            params = {}
    
    # Emit initial status with readable endpoint name and specific parameters
    endpoint_name = endpoint.replace('_', ' ').replace('-', ' ').title()
    symbol_str = params.get('symbol', '') if params else ''
    
    if symbol_str:
        yield SSEEvent(
            event="tool_status",
            data={
                "status": "executing",
                "message": f"Starting {endpoint_name} fetch for {symbol_str}..."
            }
        )
    else:
        yield SSEEvent(
            event="tool_status",
            data={
                "status": "executing",
                "message": f"Starting {endpoint_name} data fetch..."
            }
        )
    
    # Call FMP client - it will also yield SSE events  
    async for item in fmp_tools.get_fmp_data_streaming(
        endpoint=endpoint, 
        params=params or {}
    ):
        if isinstance(item, SSEEvent):
            yield item
        else:
            result = item
    
    # Emit final status based on result
    if result.get("success"):
        count = result.get("count", 0)
        if count > 0:
            yield SSEEvent(
                event="tool_status",
                data={
                    "status": "completed",
                    "message": f"✓ Retrieved {count} {endpoint_name.lower()} records"
                }
            )
        else:
            yield SSEEvent(
                event="tool_status",
                data={
                    "status": "completed",
                    "message": f"✓ {endpoint_name} data retrieved successfully"
                }
            )
    else:
        error_msg = result.get("message", "Unknown error")
        yield SSEEvent(
            event="tool_status",
            data={
                "status": "error",
                "message": f"✗ {error_msg}"
            }
        )
    
    yield result


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
    context: AgentContext,
    params: PresentOptionsInput
):
    """
    Present option buttons to the user
    
    Args:
        params: PresentOptionsInput containing question and option buttons
    """
    # Yield options event
    yield SSEEvent(
        event="tool_options",
        data={
        "question": params.question,
        "options": [opt.model_dump() for opt in params.options]
        }
    )
    
    # Yield final result indicating options were presented
    # The conversation should pause here waiting for user selection
    yield {
        "success": True,
        "message": "Options presented to user. Waiting for user selection.",
        "question": params.question,
        "options": [opt.model_dump() for opt in params.options],
        "_stop_response": True  # Signal that response should end after this
    }


# ============================================================================
# ANALYTICS TOOLS (Transaction History & Performance)
# ============================================================================

@tool(
    description="""Sync and retrieve the user's complete transaction history from their connected brokerage.
    This fetches all stock trades (buys, sells), dividends, and fees for analysis.
    
    Use this when the user asks about:
    - Past trades or transaction history
    - "What stocks have I traded?"
    - "Show me my transactions"
    - Before analyzing performance (to ensure data is up-to-date)
    
    Parameters:
    - symbol: Optional ticker to filter (e.g., 'AAPL')
    - limit: Max transactions to return (default 100, max 500)
    """,
    category="analytics",
    requires_auth=True
)
async def get_transaction_history(
    *,
    context: AgentContext,
    symbol: Optional[str] = None,
    limit: int = 100
):
    """Fetch user's transaction history"""
    from services.transaction_sync import transaction_sync_service
    from crud import transactions as tx_crud
    from database import SessionLocal
    
    if not context.user_id:
        yield {
            "success": False,
            "message": "User ID required",
            "needs_auth": True
        }
        return
    
    # First, sync transactions from SnapTrade
    yield SSEEvent(
        event="tool_status",
        data={
            "status": "syncing",
            "message": "Syncing your latest transactions from brokerage..."
        }
    )
    
    sync_result = await transaction_sync_service.sync_user_transactions(context.user_id)
    
    if not sync_result.get("success"):
        yield {
            "success": False,
            "message": sync_result.get("message", "Failed to sync transactions")
        }
        return
    
    # Now fetch transactions from DB
    db = SessionLocal()
    try:
        transactions = tx_crud.get_transactions(
            db,
            user_id=context.user_id,
            symbol=symbol,
            limit=min(limit, 500)
        )
        
        # Format transactions for display
        formatted = []
        for tx in transactions:
            formatted.append({
                "id": str(tx.id),
                "symbol": tx.symbol,
                "type": tx.transaction_type,
                "date": tx.transaction_date.isoformat(),
                "quantity": float(tx.data.get("quantity", 0)),
                "price": float(tx.data.get("price")) if tx.data.get("price") else None,
                "total": float(tx.data.get("total_amount", 0)),
                "description": tx.data.get("description", "")
            })
        
        yield {
            "success": True,
            "data": {
                "transactions": formatted,
                "total_count": len(formatted),
                "synced": sync_result.get("transactions_inserted", 0) + sync_result.get("transactions_updated", 0)
            },
            "message": f"Found {len(formatted)} transactions" + (f" for {symbol}" if symbol else "")
        }
        
    finally:
        db.close()


@tool(
    description="""Analyze the user's overall portfolio performance including win rate, P&L, best/worst trades,
    and behavioral patterns. This provides a comprehensive performance report.
    
    Use this when the user asks:
    - "How am I doing?"
    - "Analyze my performance"
    - "What's my win rate?"
    - "Show me my trading stats"
    - "Am I a good trader?"
    
    Parameters:
    - period: Time period to analyze (all_time, ytd, 1m, 3m, 6m, 1y)
    """,
    category="analytics",
    requires_auth=True
)
async def analyze_portfolio_performance(
    *,
    context: AgentContext,
    period: str = "all_time"
):
    """Analyze overall portfolio performance"""
    from services.analytics import analytics_service
    from services.transaction_sync import transaction_sync_service
    
    if not context.user_id:
        yield {
            "success": False,
            "message": "User ID required",
            "needs_auth": True
        }
        return
    
    # Sync transactions first (with background sync)
    yield SSEEvent(
        event="tool_status",
        data={
            "status": "syncing",
            "message": "Checking for latest transactions..."
        }
    )
    
    sync_result = await transaction_sync_service.sync_user_transactions(
        context.user_id,
        background_sync=True  # Enable background sync
    )
    
    # Calculate performance metrics
    yield SSEEvent(
        event="tool_status",
        data={
            "status": "analyzing",
            "message": f"Analyzing your trading performance ({period})..."
        }
    )
    
    metrics = analytics_service.calculate_performance_metrics(
        context.user_id,
        period=period
    )
    
    # Build staleness message
    staleness_msg = ""
    if sync_result.get("cached") and sync_result.get("staleness_seconds"):
        staleness_seconds = sync_result["staleness_seconds"]
        if staleness_seconds < 60:
            staleness_msg = f" (data from {staleness_seconds}s ago)"
        elif staleness_seconds < 3600:
            staleness_msg = f" (data from {staleness_seconds // 60}m ago)"
        else:
            staleness_msg = f" (data from {staleness_seconds // 3600}h ago)"
        
        if sync_result.get("background_sync"):
            staleness_msg += " - updating in background"
    
    if metrics.get("total_trades", 0) == 0:
        yield {
            "success": True,
            "data": metrics,
            "message": f"No closed trades found in this period{staleness_msg}. Connect your brokerage and make some trades to see analytics!",
            "data_staleness_seconds": sync_result.get("staleness_seconds"),
            "background_sync": sync_result.get("background_sync", False)
        }
        return
    
    yield {
        "success": True,
        "data": metrics,
        "message": f"Performance analysis complete for {period}{staleness_msg}. You've made {metrics['total_trades']} trades with a {metrics['win_rate']:.1f}% win rate!",
        "data_staleness_seconds": sync_result.get("staleness_seconds"),
        "background_sync": sync_result.get("background_sync", False)
    }


@tool(
    description="""Identify behavioral patterns in the user's trading such as:
    - Early exit on winners / Holding losers too long
    - Overtrading
    - Risk/reward imbalance
    - High/low win rate tendencies
    
    Use this when the user asks:
    - "What patterns do you see in my trading?"
    - "What am I doing wrong?"
    - "How can I improve?"
    - "What are my bad habits?"
    """,
    category="analytics",
    requires_auth=True
)
async def identify_trading_patterns(
    *,
    context: AgentContext
):
    """Identify behavioral trading patterns"""
    from services.analytics import analytics_service
    from services.transaction_sync import transaction_sync_service
    
    if not context.user_id:
        yield {
            "success": False,
            "message": "User ID required",
            "needs_auth": True
        }
        return
    
    # Sync first (with background sync)
    yield SSEEvent(
        event="tool_status",
        data={
            "status": "analyzing",
            "message": "Analyzing your trading patterns..."
        }
    )
    
    sync_result = await transaction_sync_service.sync_user_transactions(
        context.user_id,
        background_sync=True
    )
    
    patterns = analytics_service.analyze_trading_patterns(context.user_id)
    
    # Build staleness message
    staleness_msg = ""
    if sync_result.get("cached") and sync_result.get("staleness_seconds"):
        staleness_seconds = sync_result["staleness_seconds"]
        if staleness_seconds < 60:
            staleness_msg = f" (data from {staleness_seconds}s ago)"
        elif staleness_seconds < 3600:
            staleness_msg = f" (data from {staleness_seconds // 60}m ago)"
        else:
            staleness_msg = f" (data from {staleness_seconds // 3600}h ago)"
    
    if not patterns:
        yield {
            "success": True,
            "data": {"patterns": []},
            "message": f"Not enough trading history to detect patterns yet{staleness_msg}. Keep trading and check back after 10+ closed positions!",
            "data_staleness_seconds": sync_result.get("staleness_seconds"),
            "background_sync": sync_result.get("background_sync", False)
        }
        return
    
    yield {
        "success": True,
        "data": {"patterns": patterns},
        "message": f"Found {len(patterns)} trading patterns to review{staleness_msg}",
        "data_staleness_seconds": sync_result.get("staleness_seconds"),
        "background_sync": sync_result.get("background_sync", False)
    }


# ============================================================================
# TRADING STRATEGY TOOLS
# ============================================================================

@tool(
    description="""Create a custom trading strategy from natural language description.
    
The system will parse your strategy idea, determine required data sources (price history, 
insider trades, technical indicators, etc.), and create a structured, backtest-ready 
strategy definition.

Examples:
- "Buy when 3+ insiders buy over $500K total in 30 days AND RSI is below 30"
- "Buy stocks breaking above 20-day high with volume 2x average, sell at 15% profit or 7% stop"
- "Buy when a stock gaps up 5%+ on earnings with positive analyst upgrades"

Be specific about:
- Entry conditions (what signals to buy)
- Exit conditions (when to sell)
- Risk management (stop loss %, profit target %, max hold time)""",
    category="strategy"
)
async def create_trading_strategy(
    *,
    context: AgentContext,
    strategy_description: str,
    strategy_name: str
):
    """
    Create a custom trading strategy from natural language
    
    Args:
        strategy_description: Detailed description of the strategy logic
        strategy_name: Short, descriptive name for the strategy
    """
    from services.strategy_parser import StrategyParserService
    from crud.strategy import create_strategy
    
    yield SSEEvent(
        event="tool_status",
        data={
            "status": "parsing",
            "message": f"Analyzing your strategy idea: '{strategy_name}'..."
        }
    )
    
    try:
        # Parse strategy using LLM
        parser = StrategyParserService()
        strategy = await parser.parse_strategy(
            user_id=context.user_id,
            natural_language_input=strategy_description
        )
        
        # Override name if provided
        strategy.name = strategy_name
        
        # Validate strategy
        validation = parser.validate_strategy(strategy)
        if not validation["valid"]:
            yield {
                "success": False,
                "error": "Strategy validation failed",
                "issues": validation["issues"]
            }
            return
        
        # Save to database
        db_strategy = create_strategy(context.db, strategy)
        
        yield {
            "success": True,
            "strategy_id": strategy.id,
            "strategy_name": strategy.name,
            "description": strategy.description,
            "timeframe": strategy.timeframe,
            "entry_conditions": [
                {
                    "field": c.field,
                    "operator": c.operator,
                    "value": c.value,
                    "description": c.description
                }
                for c in strategy.entry_conditions
            ],
            "exit_conditions": [
                {
                    "field": c.field,
                    "operator": c.operator,
                    "value": c.value,
                    "description": c.description
                }
                for c in strategy.exit_conditions
            ],
            "risk_parameters": {
                "stop_loss_pct": strategy.risk_parameters.stop_loss_pct,
                "take_profit_pct": strategy.risk_parameters.take_profit_pct,
                "max_hold_days": strategy.risk_parameters.max_hold_days,
                "position_size_pct": strategy.risk_parameters.position_size_pct
            },
            "message": f"Strategy '{strategy_name}' created successfully! Ready to backtest."
        }
        
    except Exception as e:
        yield {
            "success": False,
            "error": str(e),
            "message": "Failed to create strategy. Please try rephrasing your description."
        }


@tool(
    description="""Backtest a trading strategy on historical data to see how it would have performed.
    
Returns detailed performance metrics including:
- Total return %
- Win rate
- Profit factor (avg win / avg loss)
- Max drawdown
- Sharpe ratio
- Individual trade history
- Equity curve for visualization

Default backtest period is 2 years. You can specify custom start/end dates.""",
    category="strategy"
)
async def backtest_strategy(
    *,
    context: AgentContext,
    strategy_id: str,
    start_date: str = None,  # YYYY-MM-DD
    end_date: str = None,    # YYYY-MM-DD
    initial_capital: float = 100000
):
    """
    Backtest a strategy on historical data
    
    Args:
        strategy_id: ID of the strategy to backtest
        start_date: Start date (YYYY-MM-DD). Defaults to 2 years ago
        end_date: End date (YYYY-MM-DD). Defaults to today
        initial_capital: Starting capital for backtest (default $100,000)
    """
    from services.strategy_backtest import BacktestEngine
    from crud.strategy import get_strategy, save_backtest
    from modules.tools.fmp_client import FMPClient
    from datetime import date, timedelta
    
    # Get strategy
    strategy = get_strategy(context.db, strategy_id)
    if not strategy:
        yield {
            "success": False,
            "error": f"Strategy {strategy_id} not found"
        }
        return
    
    # Check ownership
    if strategy.user_id != context.user_id:
        yield {
            "success": False,
            "error": "You don't have permission to access this strategy"
        }
        return
    
    # Parse dates
    if not end_date:
        end_date = date.today()
    else:
        end_date = date.fromisoformat(end_date)
    
    if not start_date:
        start_date = end_date - timedelta(days=730)  # 2 years
    else:
        start_date = date.fromisoformat(start_date)
    
    yield SSEEvent(
        event="tool_status",
        data={
            "status": "running",
            "message": f"Backtesting '{strategy.name}' from {start_date} to {end_date}..."
        }
    )
    
    try:
        # Run backtest
        fmp_client = FMPClient()
        engine = BacktestEngine(fmp_client)
        
        backtest = await engine.run_backtest(
            strategy=strategy,
            start_date=start_date,
            end_date=end_date,
            initial_capital=initial_capital
        )
        
        # Save backtest results
        save_backtest(context.db, backtest)
        
        # Format best/worst trades
        best_trade = None
        worst_trade = None
        
        if backtest.best_trade:
            best_trade = {
                "ticker": backtest.best_trade.ticker,
                "entry_date": backtest.best_trade.entry_date.isoformat(),
                "exit_date": backtest.best_trade.exit_date.isoformat(),
                "entry_price": backtest.best_trade.entry_price,
                "exit_price": backtest.best_trade.exit_price,
                "pnl": backtest.best_trade.pnl,
                "pnl_pct": backtest.best_trade.pnl_pct,
                "days_held": backtest.best_trade.days_held
            }
        
        if backtest.worst_trade:
            worst_trade = {
                "ticker": backtest.worst_trade.ticker,
                "entry_date": backtest.worst_trade.entry_date.isoformat(),
                "exit_date": backtest.worst_trade.exit_date.isoformat(),
                "entry_price": backtest.worst_trade.entry_price,
                "exit_price": backtest.worst_trade.exit_price,
                "pnl": backtest.worst_trade.pnl,
                "pnl_pct": backtest.worst_trade.pnl_pct,
                "days_held": backtest.worst_trade.days_held
            }
        
        yield {
            "success": True,
            "backtest_id": backtest.backtest_id,
            "strategy_name": strategy.name,
            "period": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "days": (end_date - start_date).days
            },
            "performance": {
                "total_trades": backtest.total_trades,
                "winning_trades": backtest.winning_trades,
                "losing_trades": backtest.losing_trades,
                "win_rate": backtest.win_rate,
                "total_return_pct": backtest.total_return_pct,
                "total_return_dollars": backtest.total_return_dollars,
                "final_equity": backtest.final_equity,
                "avg_win_pct": backtest.avg_win_pct,
                "avg_loss_pct": backtest.avg_loss_pct,
                "profit_factor": backtest.profit_factor,
                "max_drawdown_pct": backtest.max_drawdown_pct,
                "sharpe_ratio": backtest.sharpe_ratio
            },
            "best_trade": best_trade,
            "worst_trade": worst_trade,
            "equity_curve": backtest.equity_curve,
            "message": f"Backtest complete: {backtest.total_trades} trades, {backtest.win_rate:.1f}% win rate, {backtest.total_return_pct:+.2f}% return"
        }
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        yield {
            "success": False,
            "error": str(e),
            "message": "Backtest failed. Please check the strategy definition and try again."
        }


@tool(
    description="""List all trading strategies created by the user with their basic info and status.
    
Shows strategy name, timeframe, creation date, and active status.""",
    category="strategy"
)
def list_user_strategies(
    *,
    context: AgentContext,
    active_only: bool = True
):
    """
    Get all trading strategies for the current user
    
    Args:
        active_only: If true, only return active strategies (default True)
    """
    from crud.strategy import get_user_strategies
    
    try:
        strategies = get_user_strategies(context.db, context.user_id, active_only)
        
        if not strategies:
            return {
                "success": True,
                "strategies": [],
                "count": 0,
                "message": "You haven't created any trading strategies yet. Use create_trading_strategy to get started!"
            }
        
        strategy_list = []
        for strategy in strategies:
            strategy_list.append({
                "strategy_id": strategy.id,
                "name": strategy.name,
                "description": strategy.description,
                "timeframe": strategy.timeframe,
                "is_active": strategy.is_active,
                "created_at": strategy.created_at.isoformat()
            })
        
        return {
            "success": True,
            "strategies": strategy_list,
            "count": len(strategy_list),
            "message": f"Found {len(strategy_list)} active strategies" if active_only else f"Found {len(strategy_list)} strategies"
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


@tool(
    description="""Compare performance of all user's strategies side-by-side.
    
Shows which strategies are generating the best signals and returns.
Returns leaderboard sorted by performance.""",
    category="strategy"
)
def compare_strategies(
    *,
    context: AgentContext
):
    """
    Compare all user strategies by performance
    """
    from crud.strategy import compare_user_strategies
    
    try:
        comparisons = compare_user_strategies(context.db, context.user_id)
        
        if not comparisons:
            return {
                "success": True,
                "strategies": [],
                "message": "No strategies to compare yet. Create some strategies first!"
            }
        
        comparison_list = []
        for comp in comparisons:
            comparison_list.append({
                "strategy_name": comp.strategy_name,
                "timeframe": comp.timeframe,
                "signals_generated": comp.signals_generated,
                "win_rate": comp.win_rate,
                "actual_return_pct": comp.actual_return_pct,
                "hypothetical_return_pct": comp.hypothetical_return_pct,
                "last_signal": comp.last_signal.isoformat() if comp.last_signal else None,
                "is_active": comp.is_active
            })
        
        return {
            "success": True,
            "strategies": comparison_list,
            "count": len(comparison_list),
            "message": f"Compared {len(comparison_list)} strategies"
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
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
    
    # Visualization tools
    tool_registry.register_function(create_chart)
    
    # Interactive options tool
    tool_registry.register_function(present_options)
    
    # Analytics tools
    tool_registry.register_function(get_transaction_history)
    tool_registry.register_function(analyze_portfolio_performance)
    tool_registry.register_function(identify_trading_patterns)
    
    # Strategy tools
    tool_registry.register_function(create_trading_strategy)
    tool_registry.register_function(backtest_strategy)
    tool_registry.register_function(list_user_strategies)
    tool_registry.register_function(compare_strategies)


# Auto-register on import
register_all_tools()

