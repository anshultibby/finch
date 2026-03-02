"""
Query Strategies — helpers for the LLM to inspect and learn from existing strategies.
"""
from typing import Optional, Dict, Any


async def list_strategies(user_id: str) -> Dict[str, Any]:
    """Get all strategies for a user with their performance stats."""
    from database import get_db_session
    from crud.strategies import list_strategies as crud_list

    async with get_db_session() as db:
        strategies = await crud_list(db, user_id)

        result: list[dict] = []
        for strat in strategies:
            config = strat.config or {}
            stats = strat.stats or {}
            result.append({
                "id": strat.id,
                "name": strat.name,
                "platform": config.get("platform", ""),
                "thesis": config.get("thesis", ""),
                "enabled": strat.enabled,
                "approved": strat.approved,
                "track_record": {
                    "total_runs": stats.get("total_runs", 0),
                    "successful_runs": stats.get("successful_runs", 0),
                    "last_run_summary": stats.get("last_run_summary"),
                },
                "schedule": config.get("schedule_description"),
                "created_at": strat.created_at.isoformat(),
            })

        return {"strategies": result, "total": len(result)}


async def get_strategy_code(user_id: str, strategy_id: str) -> Dict[str, Any]:
    """Get the code files for a strategy."""
    from database import get_db_session
    from crud.strategies import get_strategy, load_strategy_files

    async with get_db_session() as db:
        strategy = await get_strategy(db, strategy_id, user_id)
        if not strategy:
            return {"error": "Strategy not found"}

        files = await load_strategy_files(db, strategy)
        config = strategy.config or {}

        return {
            "strategy_id": strategy_id,
            "name": strategy.name,
            "platform": config.get("platform", ""),
            "files": files,
            "config": config,
            "stats": strategy.stats or {},
        }


async def analyze_strategy_performance(user_id: str, strategy_id: str) -> Dict[str, Any]:
    """Get performance analysis of a strategy."""
    from database import get_db_session
    from crud.strategies import get_strategy

    async with get_db_session() as db:
        strategy = await get_strategy(db, strategy_id, user_id)
        if not strategy:
            return {"error": "Strategy not found"}

        stats = strategy.stats or {}
        total_runs = stats.get("total_runs", 0)
        successful_runs = stats.get("successful_runs", 0)
        failed_runs = stats.get("failed_runs", 0)

        success_rate = successful_runs / total_runs if total_runs > 0 else 0

        return {
            "strategy_id": strategy_id,
            "name": strategy.name,
            "metrics": {
                "total_runs": total_runs,
                "successful_runs": successful_runs,
                "failed_runs": failed_runs,
                "success_rate": success_rate,
                "total_spent_usd": stats.get("total_spent_usd", 0.0),
                "total_profit_usd": stats.get("total_profit_usd", 0.0),
                "last_run_at": stats.get("last_run_at"),
                "last_run_summary": stats.get("last_run_summary"),
            },
            "summary": (
                f"{strategy.name}: {total_runs} run(s), "
                f"{success_rate:.0%} success rate"
            ),
        }
