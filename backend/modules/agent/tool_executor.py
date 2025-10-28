"""
Tool execution logic for the AI agent
"""
from typing import Dict, Any
from modules.snaptrade_tools import snaptrade_tools
from modules.apewisdom_tools import apewisdom_tools
from modules.insider_trading_tools import insider_trading_tools


async def execute_tool(
    function_name: str,
    function_args: Dict[str, Any],
    session_id: str
) -> Dict[str, Any]:
    """
    Execute a tool and return its result
    
    Args:
        function_name: Name of the tool to execute
        function_args: Arguments to pass to the tool
        session_id: User session ID for context
        
    Returns:
        Tool execution result as dictionary
    """
    print(f"🔧 Executing tool: {function_name} for session: {session_id}", flush=True)
    
    # Brokerage connection
    if function_name == "request_brokerage_connection":
        return {
            "success": True,
            "needs_auth": True,
            "message": "Please connect your brokerage account through SnapTrade to continue.",
            "action_required": "show_connection_modal"
        }
    
    # Portfolio tools
    if function_name == "get_portfolio":
        print(f"📊 get_portfolio tool called for session: {session_id}", flush=True)
        if not snaptrade_tools.has_active_connection(session_id):
            print(f"❌ No active connection, returning needs_auth", flush=True)
            return {
                "success": False,
                "needs_auth": True,
                "message": "You need to connect your brokerage account first."
            }
        
        print(f"✅ Active connection found, calling snaptrade_tools.get_portfolio", flush=True)
        result = snaptrade_tools.get_portfolio(session_id=session_id)
        print(f"📊 Portfolio result: {result}", flush=True)
        return result
    
    # Reddit sentiment tools
    if function_name == "get_reddit_trending_stocks":
        print(f"📊 get_reddit_trending_stocks tool called", flush=True)
        limit = function_args.get("limit", 10)
        result = await apewisdom_tools.get_trending_stocks(limit=limit)
        print(f"📊 Reddit trending result: {result}", flush=True)
        return result
    
    if function_name == "get_reddit_ticker_sentiment":
        print(f"📊 get_reddit_ticker_sentiment tool called", flush=True)
        ticker = function_args.get("ticker", "")
        result = await apewisdom_tools.get_ticker_sentiment(ticker=ticker)
        print(f"📊 Reddit ticker sentiment result: {result}", flush=True)
        return result
    
    if function_name == "compare_reddit_sentiment":
        print(f"📊 compare_reddit_sentiment tool called", flush=True)
        tickers = function_args.get("tickers", [])
        result = await apewisdom_tools.compare_tickers_sentiment(tickers=tickers)
        print(f"📊 Reddit comparison result: {result}", flush=True)
        return result
    
    # Congressional trading tools
    if function_name == "get_recent_senate_trades":
        print(f"🏛️ get_recent_senate_trades tool called", flush=True)
        limit = function_args.get("limit", 50)
        result = await insider_trading_tools.get_recent_senate_trades(limit=limit)
        if result.get("success"):
            print(f"🏛️ Senate trades: Found {result.get('total_count', 0)} trades", flush=True)
        else:
            print(f"🏛️ Senate trades failed: {result.get('message')}", flush=True)
        return result
    
    if function_name == "get_recent_house_trades":
        print(f"🏛️ get_recent_house_trades tool called", flush=True)
        limit = function_args.get("limit", 50)
        result = await insider_trading_tools.get_recent_house_trades(limit=limit)
        if result.get("success"):
            print(f"🏛️ House trades: Found {result.get('total_count', 0)} trades", flush=True)
        else:
            print(f"🏛️ House trades failed: {result.get('message')}", flush=True)
        return result
    
    # Insider trading tools
    if function_name == "get_recent_insider_trades":
        print(f"💼 get_recent_insider_trades tool called", flush=True)
        limit = function_args.get("limit", 100)
        result = await insider_trading_tools.get_recent_insider_trades(limit=limit)
        if result.get("success"):
            print(f"💼 Insider trades: Found {result.get('total_count', 0)} trades", flush=True)
        else:
            print(f"💼 Insider trades failed: {result.get('message')}", flush=True)
        return result
    
    if function_name == "search_ticker_insider_activity":
        print(f"🔍 search_ticker_insider_activity tool called", flush=True)
        ticker = function_args.get("ticker", "")
        limit = function_args.get("limit", 50)
        result = await insider_trading_tools.search_ticker_insider_activity(ticker=ticker, limit=limit)
        if result.get("success"):
            summary = result.get('summary', {})
            print(f"🔍 {ticker}: {summary.get('total_trades', 0)} trades ({summary.get('purchases', 0)} buys, {summary.get('sales', 0)} sells)", flush=True)
        else:
            print(f"🔍 {ticker} search failed: {result.get('message')}", flush=True)
        return result
    
    if function_name == "get_portfolio_insider_activity":
        print(f"📊 get_portfolio_insider_activity tool called", flush=True)
        tickers = function_args.get("tickers", [])
        days_back = function_args.get("days_back", 90)
        
        # Limit to max 20 tickers to avoid overwhelming API/response
        if len(tickers) > 20:
            print(f"⚠️ Limiting tickers from {len(tickers)} to 20 to avoid overload", flush=True)
            tickers = tickers[:20]
        
        result = await insider_trading_tools.get_portfolio_insider_activity(tickers=tickers, days_back=days_back)
        if result.get("success"):
            print(f"📊 Portfolio insider activity: Found activity in {len(result.get('tickers_with_activity', []))} tickers", flush=True)
        else:
            print(f"📊 Portfolio insider activity result: {result.get('message')}", flush=True)
        return result
    
    if function_name == "get_insider_trading_statistics":
        print(f"📊 get_insider_trading_statistics tool called", flush=True)
        symbol = function_args.get("symbol", "")
        result = await insider_trading_tools.get_insider_trading_statistics(symbol=symbol)
        if result.get("success"):
            summary = result.get('summary', {})
            print(f"📊 {symbol} statistics: {summary.get('total_quarters', 0)} quarters analyzed", flush=True)
        else:
            print(f"📊 {symbol} statistics failed: {result.get('message')}", flush=True)
        return result
    
    if function_name == "search_insider_trades":
        print(f"🔍 search_insider_trades tool called", flush=True)
        result = await insider_trading_tools.search_insider_trades(
            symbol=function_args.get("symbol"),
            reporting_cik=function_args.get("reporting_cik"),
            company_cik=function_args.get("company_cik"),
            transaction_type=function_args.get("transaction_type"),
            limit=function_args.get("limit", 50),
            page=function_args.get("page", 0)
        )
        if result.get("success"):
            print(f"🔍 Search found {result.get('total_count', 0)} trades", flush=True)
        else:
            print(f"🔍 Search failed: {result.get('message')}", flush=True)
        return result
    
    # Unknown tool
    return {
        "success": False,
        "message": f"Unknown tool: {function_name}"
    }

