"""
Bot management tool implementations — configure_bot, approve_bot, run_bot, close_position.

These tools are only functional when the agent is running in a bot-scoped chat
(i.e. context.data["bot_id"] is set). They call the CRUD layer directly.
"""
import logging
from typing import Optional, Dict, Any

from modules.agent.context import AgentContext

logger = logging.getLogger(__name__)


def _get_bot_id(context: AgentContext) -> str:
    """Extract bot_id from context, raising if not in a bot chat."""
    bot_id = (context.data or {}).get("bot_id")
    if not bot_id:
        raise ValueError("This tool is only available inside a bot chat.")
    return bot_id


async def configure_bot_impl(
    context: AgentContext,
    name: Optional[str] = None,
    mandate: Optional[str] = None,
    capital_usd: Optional[float] = None,
    max_positions: Optional[int] = None,
) -> Dict[str, Any]:
    """Update bot settings. Only provided fields are changed."""
    from database import get_db_session
    from crud.bots import get_bot, update_bot

    bot_id = _get_bot_id(context)
    user_id = context.user_id

    async with get_db_session() as db:
        bot = await get_bot(db, bot_id, user_id)
        if not bot:
            return {"success": False, "error": "Bot not found"}

        updates: Dict[str, Any] = {}
        if name is not None:
            updates["name"] = name
        if mandate is not None:
            updates["mandate"] = mandate

        # Capital fields go into config.capital
        if capital_usd is not None or max_positions is not None:
            config = dict(bot.config or {})
            capital = dict(config.get("capital", {}) or {})
            if capital_usd is not None:
                capital["amount_usd"] = capital_usd
                # Initialize balance if not set
                if capital.get("balance_usd") is None:
                    capital["balance_usd"] = capital_usd
            if max_positions is not None:
                capital["max_positions"] = max_positions
            updates["capital"] = capital

        bot = await update_bot(db, bot_id, user_id, updates)

        result = {
            "success": True,
            "message": "Bot updated successfully",
            "updated_fields": list(updates.keys()),
            "bot_name": bot.name,
        }
        if mandate is not None:
            result["mandate_preview"] = mandate[:200]
        return result


async def approve_bot_impl(context: AgentContext) -> Dict[str, Any]:
    """Mark bot as approved for live trading."""
    from database import get_db_session
    from crud.bots import get_bot, update_bot

    bot_id = _get_bot_id(context)
    user_id = context.user_id

    async with get_db_session() as db:
        bot = await get_bot(db, bot_id, user_id)
        if not bot:
            return {"success": False, "error": "Bot not found"}
        if bot.approved:
            return {"success": True, "message": "Bot is already approved"}

        bot = await update_bot(db, bot_id, user_id, {"approved": True, "enabled": True})
        return {
            "success": True,
            "message": f"Bot '{bot.name}' approved and enabled for live trading.",
        }


async def run_bot_impl(context: AgentContext, dry_run: bool = True) -> Dict[str, Any]:
    """Trigger an immediate bot tick."""
    from database import get_db_session
    from crud.bots import get_bot
    from modules.bots.executor import execute_bot_tick

    bot_id = _get_bot_id(context)
    user_id = context.user_id

    async with get_db_session() as db:
        bot = await get_bot(db, bot_id, user_id)
        if not bot:
            return {"success": False, "error": "Bot not found"}

        execution = await execute_bot_tick(db, bot, trigger="manual", dry_run=dry_run)
        data = execution.data or {}
        return {
            "success": execution.status == "success",
            "execution_id": str(execution.id),
            "status": execution.status,
            "summary": data.get("summary"),
            "actions_count": len(data.get("actions", [])),
            "dry_run": dry_run,
            "error": data.get("error"),
        }


async def schedule_wakeup_impl(
    context: AgentContext,
    trigger_at: str,
    reason: str,
    trigger_type: str = "custom",
    position_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Schedule a future wakeup for this bot."""
    from database import get_db_session
    from crud.bots import create_wakeup
    from datetime import datetime, timezone

    bot_id = _get_bot_id(context)
    user_id = context.user_id

    try:
        # Parse ISO datetime
        dt = datetime.fromisoformat(trigger_at.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
    except ValueError:
        return {"success": False, "error": f"Invalid datetime format: {trigger_at}. Use ISO 8601 (e.g. 2026-03-15T14:00:00Z)"}

    if dt <= datetime.now(timezone.utc):
        return {"success": False, "error": "trigger_at must be in the future"}

    wakeup_context = {}
    if position_id:
        wakeup_context["position_id"] = position_id

    async with get_db_session() as db:
        wakeup = await create_wakeup(
            db=db,
            bot_id=bot_id,
            user_id=user_id,
            trigger_at=dt,
            reason=reason,
            trigger_type=trigger_type,
            context=wakeup_context,
        )
        return {
            "success": True,
            "wakeup_id": str(wakeup.id),
            "trigger_at": dt.isoformat(),
            "reason": reason,
            "message": f"Wake-up scheduled for {dt.strftime('%B %d, %Y at %H:%M UTC')}",
        }


async def list_wakeups_impl(context: AgentContext) -> Dict[str, Any]:
    """List pending wakeups for this bot."""
    from database import get_db_session
    from crud.bots import list_wakeups

    bot_id = _get_bot_id(context)

    async with get_db_session() as db:
        wakeups = await list_wakeups(db, bot_id, status="pending")
        return {
            "success": True,
            "count": len(wakeups),
            "wakeups": [
                {
                    "id": str(w.id),
                    "trigger_at": w.trigger_at.isoformat(),
                    "trigger_type": w.trigger_type,
                    "reason": w.reason,
                    "context": w.context,
                }
                for w in wakeups
            ],
        }


async def cancel_wakeup_impl(context: AgentContext, wakeup_id: str) -> Dict[str, Any]:
    """Cancel a pending wakeup."""
    from database import get_db_session
    from crud.bots import cancel_wakeup

    _get_bot_id(context)  # Validate we're in a bot chat
    user_id = context.user_id

    async with get_db_session() as db:
        wakeup = await cancel_wakeup(db, wakeup_id, user_id)
        if not wakeup:
            return {"success": False, "error": "Wakeup not found or already triggered/cancelled"}
        return {"success": True, "message": "Wake-up cancelled"}


async def close_position_impl(context: AgentContext, position_id: str) -> Dict[str, Any]:
    """Close a specific open position by ID."""
    from database import get_db_session
    from crud.bots import get_bot, get_position, close_position, credit_capital_for_close

    bot_id = _get_bot_id(context)
    user_id = context.user_id

    async with get_db_session() as db:
        bot = await get_bot(db, bot_id, user_id)
        if not bot:
            return {"success": False, "error": "Bot not found"}

        pos = await get_position(db, position_id)
        if not pos or str(pos.bot_id) != bot_id:
            return {"success": False, "error": "Position not found or doesn't belong to this bot"}
        if pos.status == "closed":
            return {"success": False, "error": "Position is already closed"}

        exit_price = pos.current_price or pos.entry_price
        await close_position(db, pos, exit_price=exit_price, close_reason="manual_chat", closed_via="chat")
        realized_pnl = (exit_price - pos.entry_price) * pos.quantity
        await credit_capital_for_close(db, bot, pos.cost_usd, realized_pnl)

        return {
            "success": True,
            "message": f"Closed position on {pos.market_title or pos.market}",
            "exit_price": exit_price,
            "realized_pnl_usd": round(realized_pnl, 4),
        }
