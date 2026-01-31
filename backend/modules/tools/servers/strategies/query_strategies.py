"""
Query Strategies - Tool for LLM to learn from existing strategies

Allows LLM to:
1. List all user strategies
2. View strategy performance (P&L, win rate, etc.)
3. Read strategy code (entry.py, exit.py)
4. Analyze what works and what doesn't
"""
from typing import Optional, List, Dict, Any


async def list_strategies(user_id: str) -> Dict[str, Any]:
    """
    Get all strategies for a user with their performance stats
    
    Args:
        user_id: User ID
        
    Returns:
        Dict with list of strategies and their stats
        
    Example:
        strategies = await list_strategies("user_123")
        
        # Returns:
        {
            "strategies": [
                {
                    "id": "strat_abc",
                    "name": "Copy Trader",
                    "thesis": "Copy successful traders",
                    "platform": "polymarket",
                    "mode": "paper",
                    "track_record": {
                        "paper_trades": 15,
                        "paper_pnl": 125.50,
                        "paper_win_rate": 0.73,
                        "total_trades": 15,
                        "total_pnl": 125.50
                    },
                    "capital": {
                        "total_capital": 5000,
                        "capital_deployed": 450,
                        "capital_available": 4550
                    }
                }
            ]
        }
    """
    from database import get_db_session
    from crud.strategies import list_strategies as crud_list
    
    async with get_db_session() as db:
        strategies = await crud_list(db, user_id)
        
        result = {
            "strategies": [],
            "total": len(strategies)
        }
        
        for strat in strategies:
            config = strat.config or {}
            stats = strat.stats or {}
            
            result["strategies"].append({
                "id": strat.id,
                "name": strat.name,
                "thesis": config.get("thesis", ""),
                "platform": config.get("platform", ""),
                "mode": stats.get("mode", "paper"),
                "enabled": strat.enabled,
                "approved": strat.approved,
                "track_record": {
                    "total_trades": stats.get("total_trades", 0),
                    "total_pnl": stats.get("total_pnl", 0.0),
                    "win_rate": stats.get("win_rate", 0.0),
                    "paper_trades": stats.get("paper_trades", 0),
                    "paper_pnl": stats.get("paper_pnl", 0.0),
                    "live_trades": stats.get("live_trades", 0),
                    "live_pnl": stats.get("live_pnl", 0.0),
                },
                "capital": config.get("capital", {}),
                "entry_description": config.get("entry_description", ""),
                "exit_description": config.get("exit_description", ""),
                "created_at": strat.created_at.isoformat(),
            })
        
        return result


async def get_strategy_code(user_id: str, strategy_id: str) -> Dict[str, Any]:
    """
    Get the code for a strategy (entry.py, exit.py, config.json)
    
    Args:
        user_id: User ID
        strategy_id: Strategy ID
        
    Returns:
        Dict with file contents
        
    Example:
        code = await get_strategy_code("user_123", "strat_abc")
        
        # Returns:
        {
            "entry_code": "async def check_entry(ctx):\\n    ...",
            "exit_code": "async def check_exit(ctx, position):\\n    ...",
            "config": {...}
        }
    """
    from database import get_db_session
    from crud.strategies import get_strategy, load_strategy_files
    
    async with get_db_session() as db:
        strategy = await get_strategy(db, strategy_id, user_id)
        
        if not strategy:
            return {"error": "Strategy not found"}
        
        # Load files
        files = await load_strategy_files(db, strategy)
        
        config = strategy.config or {}
        entry_script = config.get("entry_script", "entry.py")
        exit_script = config.get("exit_script", "exit.py")
        
        return {
            "strategy_id": strategy_id,
            "name": strategy.name,
            "entry_code": files.get(entry_script, ""),
            "exit_code": files.get(exit_script, ""),
            "config": config,
            "stats": strategy.stats or {}
        }


async def get_top_strategies(
    user_id: str,
    metric: str = "pnl",
    limit: int = 5
) -> Dict[str, Any]:
    """
    Get top performing strategies
    
    Args:
        user_id: User ID
        metric: Sort by "pnl", "win_rate", or "sharpe"
        limit: Number of strategies to return
        
    Returns:
        List of top strategies with their code
        
    Example:
        # See what's working best
        top = await get_top_strategies("user_123", metric="win_rate")
        
        # Learn from the best
        for strat in top['strategies']:
            print(f"{strat['name']}: {strat['track_record']['win_rate']:.0%}")
            print(f"Entry logic: {strat['entry_code'][:200]}...")
    """
    strategies_result = await list_strategies(user_id)
    strategies = strategies_result["strategies"]
    
    # Sort by metric
    if metric == "pnl":
        strategies.sort(key=lambda s: s["track_record"]["total_pnl"], reverse=True)
    elif metric == "win_rate":
        strategies.sort(key=lambda s: s["track_record"]["win_rate"], reverse=True)
    elif metric == "sharpe":
        strategies.sort(
            key=lambda s: s["track_record"].get("sharpe_ratio", 0),
            reverse=True
        )
    
    # Get code for top strategies
    top_strategies = []
    for strat in strategies[:limit]:
        code = await get_strategy_code(user_id, strat["id"])
        top_strategies.append({**strat, **code})
    
    return {
        "metric": metric,
        "strategies": top_strategies
    }


async def analyze_strategy_performance(
    user_id: str,
    strategy_id: str
) -> Dict[str, Any]:
    """
    Get detailed performance analysis of a strategy
    
    Args:
        user_id: User ID
        strategy_id: Strategy ID
        
    Returns:
        Detailed performance metrics
        
    Example:
        analysis = await analyze_strategy_performance("user_123", "strat_abc")
        
        # Returns:
        {
            "summary": "Strategy has 73% win rate in paper trading",
            "metrics": {
                "total_trades": 15,
                "winning_trades": 11,
                "losing_trades": 4,
                "win_rate": 0.73,
                "avg_win": 15.20,
                "avg_loss": -8.50,
                "largest_win": 45.00,
                "largest_loss": -12.00,
                "profit_factor": 1.96
            },
            "recommendation": "Ready to graduate to live trading"
        }
    """
    from database import get_db_session
    from crud.strategies import get_strategy, list_executions
    
    async with get_db_session() as db:
        strategy = await get_strategy(db, strategy_id, user_id)
        
        if not strategy:
            return {"error": "Strategy not found"}
        
        stats = strategy.stats or {}
        
        # Calculate metrics
        total_trades = stats.get("total_trades", 0)
        winning_trades = stats.get("winning_trades", 0)
        losing_trades = stats.get("losing_trades", 0)
        
        metrics = {
            "total_trades": total_trades,
            "winning_trades": winning_trades,
            "losing_trades": losing_trades,
            "win_rate": winning_trades / total_trades if total_trades > 0 else 0,
            "total_pnl": stats.get("total_pnl", 0.0),
            "avg_win": stats.get("avg_win", 0.0),
            "avg_loss": stats.get("avg_loss", 0.0),
            "largest_win": stats.get("largest_win", 0.0),
            "largest_loss": stats.get("largest_loss", 0.0),
            "sharpe_ratio": stats.get("sharpe_ratio"),
            "max_drawdown": stats.get("max_drawdown", 0.0),
        }
        
        # Generate recommendation
        mode = stats.get("mode", "paper")
        recommendation = ""
        
        if mode == "paper":
            paper_trades = stats.get("paper_trades", 0)
            paper_win_rate = stats.get("paper_win_rate", 0)
            
            if paper_trades >= 20 and paper_win_rate > 0.55:
                recommendation = "✅ Ready to graduate to live trading"
            else:
                remaining = max(0, 20 - paper_trades)
                recommendation = f"⏳ Need {remaining} more paper trades before live"
        elif mode == "live":
            recommendation = "🚀 Currently trading live"
        
        return {
            "strategy_id": strategy_id,
            "name": strategy.name,
            "mode": mode,
            "metrics": metrics,
            "recommendation": recommendation,
            "summary": f"Win rate: {metrics['win_rate']:.0%}, P&L: ${metrics['total_pnl']:.2f}"
        }


# Usage examples for LLM
USAGE_EXAMPLES = """
# List all strategies
strategies = await list_strategies(ctx.user_id)
print(f"You have {strategies['total']} strategies")

# Find best performer
top = await get_top_strategies(ctx.user_id, metric="win_rate", limit=3)
print(f"Best strategy: {top['strategies'][0]['name']}")

# Learn from it
best = top['strategies'][0]
print(f"Entry logic:\\n{best['entry_code']}")

# Analyze performance
analysis = await analyze_strategy_performance(ctx.user_id, "strat_abc")
print(analysis['recommendation'])
"""
