"""
Create Strategy — reference scaffold for the correct strategy contract.

This module is NOT called by the LLM directly. It exists as documentation
and a helper the LLM can import for validation.

The correct workflow is:
  1. LLM calls write_chat_file("strategy.py", <code>) — using the contract below
  2. LLM calls write_chat_file("config.json", <json>)
  3. LLM calls deploy_strategy tool with the file IDs

Contract: strategy.py must use @strategy.on_entry / @strategy.on_exit.
The runner injects ctx and handles dry_run / risk limits automatically.
"""
import json
from typing import Optional


STRATEGY_PY_TEMPLATE = '''async def run(ctx):
    """
    ctx.kalshi     — full Kalshi client (dry_run aware, risk-limited on writes)
    ctx.dry_run    — bool, True in paper mode
    ctx.log(msg)   — visible in execution history

    Read:  ctx.kalshi.get_portfolio(), get_events(), get_market(ticker), get_positions(), ...
    Write: ctx.kalshi.place_order(ticker, side, action, count, order_type, price)
           ctx.kalshi.cancel_order(order_id)
    All prices are in CENTS (0-100).
    """
    ctx.log("Running strategy tick...")

    # --- your logic here ---
'''

CONFIG_TEMPLATE = {
    "platform": "kalshi",
    "name": "Strategy Name",
    "thesis": "Why this will make money",
    "description": "What the strategy does in one sentence",
    "capital": {
        "total": 500,
        "per_trade": 50,
        "max_positions": 5,
    },
    "schedule": "0 * * * *",
    "schedule_description": "Every hour",
    "risk_limits": {
        "max_order_usd": 50,
        "max_daily_usd": 200,
        "allowed_services": ["kalshi"],
    },
}


def create_strategy(
    name: str,
    thesis: str,
    platform: str,
    strategy_code: str,
    description: str,
    schedule: Optional[str] = None,
    schedule_description: Optional[str] = None,
    total: float = 500,
    per_trade: float = 50,
    max_positions: int = 5,
    max_order_usd: Optional[float] = None,
    max_daily_usd: Optional[float] = None,
) -> dict:
    """
    Validate and scaffold strategy files matching the runner contract.

    Returns {"success": True, "files": {"strategy.py": ..., "config.json": ...}}
    or {"success": False, "errors": [...]}.

    The LLM should write these files via write_chat_file then call deploy_strategy.
    """
    errors = []

    if platform not in ("kalshi", "alpaca"):
        errors.append(f"Invalid platform '{platform}'. Must be 'kalshi' or 'alpaca'.")

    if per_trade > total:
        errors.append("per_trade cannot exceed total capital")

    if "@strategy.on_entry" not in strategy_code:
        errors.append("strategy_code must use @strategy.on_entry decorator")

    if "@strategy.on_exit" not in strategy_code:
        errors.append("strategy_code must use @strategy.on_exit decorator")

    if "from finch import" not in strategy_code:
        errors.append("strategy_code must start with: from finch import strategy, EntrySignal, ExitSignal, Position")

    if errors:
        return {"success": False, "errors": errors}

    config = {
        "name": name,
        "thesis": thesis,
        "platform": platform,
        "description": description,
        "capital": {
            "total": total,
            "per_trade": per_trade,
            "max_positions": max_positions,
        },
        "schedule": schedule,
        "schedule_description": schedule_description,
        "risk_limits": {
            "max_order_usd": max_order_usd or per_trade,
            "max_daily_usd": max_daily_usd or total * 0.1,
            "allowed_services": [platform],
        },
    }

    return {
        "success": True,
        "files": {
            "strategy.py": strategy_code,
            "config.json": json.dumps(config, indent=2),
        },
        "message": (
            f"Strategy '{name}' scaffolded. "
            "Write these as chat files then call deploy_strategy."
        ),
    }
