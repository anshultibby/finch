"""
Create Strategy — helper for the LLM to scaffold new strategy files.

Generates two files:
  strategy.py  — logic using the @strategy.on_entry / @strategy.on_exit contract
  config.json  — platform, capital, risk limits, schedule

The LLM calls this helper, writes the returned files to chat files, then calls
deploy_strategy to promote them to a first-class strategy object.
"""
import json
from typing import Optional


def create_strategy(
    name: str,
    thesis: str,
    platform: str,
    total_capital: float,
    capital_per_trade: float,
    max_positions: int,
    strategy_code: str,
    description: str,
    schedule: Optional[str] = None,
    schedule_description: Optional[str] = None,
    max_order_usd: Optional[float] = None,
    max_daily_usd: Optional[float] = None,
) -> dict:
    """
    Scaffold a new strategy as two files: strategy.py and config.json.

    Args:
        name: Strategy display name
        thesis: Why this strategy will make money (plain English)
        platform: "kalshi" or "alpaca"
        total_capital: Total USD allocated to this strategy
        capital_per_trade: USD to risk per trade
        max_positions: Maximum concurrent open positions
        strategy_code: Full content of strategy.py — must use the
            @strategy.on_entry / @strategy.on_exit decorator pattern.
            See contract below.
        description: One-sentence plain-language description
        schedule: Cron expression (e.g. "*/5 * * * *")
        schedule_description: Human-readable schedule (e.g. "Every 5 minutes")
        max_order_usd: Maximum USD for a single order
        max_daily_usd: Maximum USD spend per day

    Returns:
        {
            "success": bool,
            "files": {"strategy.py": ..., "config.json": ...},
            "errors": [...]   # only present on failure
        }

    strategy.py contract
    --------------------
    The file must import from `finch` and use the decorator pattern:

        from finch import strategy, EntrySignal, ExitSignal, Position

        @strategy.on_entry
        async def check_entry(ctx) -> list[EntrySignal]:
            ...
            return [EntrySignal(market_id=..., side="yes", reason="...", confidence=0.8)]

        @strategy.on_exit
        async def check_exit(ctx, position: Position) -> ExitSignal | None:
            ...
            return ExitSignal(position_id=position.position_id, reason="...")

    ctx provides:
        ctx.kalshi     — KalshiContextWrapper (enforces dry_run + risk limits)
        ctx.alpaca     — AlpacaContextWrapper
        ctx.log(msg)   — structured logging visible in execution history
        ctx.dry_run    — bool, True for test runs
        ctx.strategy_id, ctx.user_id, ctx.execution_id
    """
    errors = []

    if platform not in ("kalshi", "alpaca"):
        errors.append(f"Invalid platform '{platform}'. Must be 'kalshi' or 'alpaca'.")

    if capital_per_trade > total_capital:
        errors.append("capital_per_trade cannot exceed total_capital")

    if "@strategy.on_entry" not in strategy_code:
        errors.append("strategy_code must use @strategy.on_entry decorator")

    if "@strategy.on_exit" not in strategy_code:
        errors.append("strategy_code must use @strategy.on_exit decorator")

    if errors:
        return {"success": False, "errors": errors}

    config = {
        "name": name,
        "thesis": thesis,
        "platform": platform,
        "description": description,
        "capital": {
            "total": total_capital,
            "per_trade": capital_per_trade,
            "max_positions": max_positions,
        },
        "schedule": schedule,
        "schedule_description": schedule_description,
        "risk_limits": {
            "max_order_usd": max_order_usd or capital_per_trade,
            "max_daily_usd": max_daily_usd or total_capital * 0.1,
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
            "Write these files to chat files and call deploy_strategy."
        ),
    }
