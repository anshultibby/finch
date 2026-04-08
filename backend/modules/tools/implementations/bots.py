"""
Bot management tool implementations — configure_bot, schedule_wakeup, place_trade, etc.

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



async def schedule_wakeup_impl(
    context: AgentContext,
    trigger_at: str,
    reason: str,
    trigger_type: str = "custom",
    position_id: Optional[str] = None,
    recurrence: Optional[str] = None,
    message: Optional[str] = None,
) -> Dict[str, Any]:
    """Schedule a future wakeup for this bot, optionally recurring."""
    from core.database import get_db_session
    from crud.bots import create_wakeup, compute_next_trigger
    from datetime import datetime, timezone

    bot_id = _get_bot_id(context)
    user_id = context.user_id

    # Validate recurrence pattern by checking if compute_next_trigger can parse it
    if recurrence and compute_next_trigger(recurrence, datetime.now(timezone.utc)) is None:
        return {"success": False, "error": f"Invalid recurrence '{recurrence}'. Use: every_30m, every_1h, every_4h, daily_9am, daily_2pm, etc."}

    try:
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
            recurrence=recurrence,
            message=message,
        )
        summary = f"Wake-up scheduled for {dt.strftime('%B %d, %Y at %H:%M UTC')}"
        if recurrence:
            summary += f" (recurring: {recurrence})"
        result = {
            "success": True,
            "wakeup_id": str(wakeup.id),
            "trigger_at": dt.isoformat(),
            "reason": reason,
            "summary": summary,
        }
        if recurrence:
            result["recurrence"] = recurrence
        if message:
            result["message"] = message
        return result


async def list_wakeups_impl(context: AgentContext) -> Dict[str, Any]:
    """List pending wakeups for this bot."""
    from core.database import get_db_session
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
                    "recurrence": w.recurrence,
                    "message": w.message,
                }
                for w in wakeups
            ],
        }


async def cancel_wakeup_impl(context: AgentContext, wakeup_id: str) -> Dict[str, Any]:
    """Cancel a pending wakeup."""
    from core.database import get_db_session
    from crud.bots import cancel_wakeup

    _get_bot_id(context)  # Validate we're in a bot chat
    user_id = context.user_id

    async with get_db_session() as db:
        wakeup = await cancel_wakeup(db, wakeup_id, user_id)
        if not wakeup:
            return {"success": False, "error": "Wakeup not found or already triggered/cancelled"}
        return {"success": True, "message": "Wake-up cancelled"}


# ---------------------------------------------------------------------------
# place_trade — unified buy/sell with platform-agnostic tracking
# ---------------------------------------------------------------------------

async def place_trade_impl(
    context: AgentContext,
    action: str,
    market: str,
    side: str = "yes",
    count: int = 1,
    reason: str = "",
    price: Optional[int] = None,
    position_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Submit a trade for user approval. All trades require confirmation before executing.

    Creates a pending_approval TradeLog and notifies the user. The trade will not
    execute until the user approves it in the UI or via the approval link.
    """
    import secrets
    from datetime import datetime, timezone, timedelta
    from core.database import get_db_session
    from crud.bots import get_bot, create_trade_log

    bot_id = _get_bot_id(context)
    user_id = context.user_id

    # --- Validation ---
    if action not in ("buy", "sell"):
        return {"success": False, "error": f"Invalid action '{action}'. Must be 'buy' or 'sell'."}
    if action == "buy" and side not in ("yes", "no"):
        return {"success": False, "error": f"Invalid side '{side}'. Must be 'yes' or 'no'."}
    if count < 1:
        return {"success": False, "error": "count must be at least 1"}
    if action == "buy" and price is None:
        return {"success": False, "error": "price is required for buy orders (cents, 1-99). Check the market price first."}
    if action == "sell" and not position_id:
        return {"success": False, "error": "position_id is required for sell orders."}
    if price is not None and (price < 1 or price > 99):
        return {"success": False, "error": f"price must be 1-99 cents, got {price}."}

    async with get_db_session() as db:
        bot = await get_bot(db, bot_id, user_id)
        if not bot:
            return {"success": False, "error": "Bot not found"}

        # Fetch market title for display (best-effort)
        market_title = ""
        if action == "buy":
            try:
                client = await get_platform_client(db, user_id, bot.config.get("platform", "kalshi"))
                if client:
                    mkt_data = await fetch_market_data(client, bot.config.get("platform", "kalshi"), market)
                    market_title = mkt_data.get("title", "")
            except Exception:
                pass

        token = secrets.token_urlsafe(32)
        expires_at = datetime.now(timezone.utc) + timedelta(hours=2)
        cost_usd = (count * price) / 100 if action == "buy" and price else 0.0

        pending_params = {
            "action": action,
            "market": market,
            "side": side,
            "count": count,
            "price": price,
            "reason": reason,
            "position_id": position_id,
        }

        trade_log = await create_trade_log(
            db=db, bot=bot, action=action, market=market, side=side,
            price=price or 0, quantity=count, cost_usd=cost_usd,
            status="pending_approval",
            approval_token=token,
            expires_at=expires_at,
            market_title=market_title,
            reason=reason,
            pending_params=pending_params,
        )

        return {
            "success": True,
            "status": "pending_approval",
            "trade_id": str(trade_log.id),
            "message": (
                f"Trade submitted for approval — your owner must confirm before it executes. "
                f"Do not submit this trade again."
            ),
        }


async def _execute_buy(
    db, bot, platform: str, user_id: str, is_paper: bool, config: dict,
    market: str, side: str, count: int, reason: str,
    price: int,
) -> Dict[str, Any]:
    """Execute a buy order — platform-agnostic tracking, platform-specific execution."""
    from crud.bots import (
        create_trade_log, update_trade_log_status,
        create_position, deduct_capital_for_position,
        credit_capital_for_close,
        recompute_bot_pnl,
    )
    from schemas.bots import ExitConfig

    risk_limits = config.get("risk_limits") or {}
    capital = config.get("capital") or {}

    # --- Get market data (for title/event_ticker only) ---
    client = await get_platform_client(db, user_id, platform)
    if not client and not is_paper:
        return {"success": False, "error": f"No {platform} credentials configured."}

    market_title = ""
    event_ticker = ""
    if client:
        try:
            mkt_data = await fetch_market_data(client, platform, market)
            market_title = mkt_data.get("title", "")
            event_ticker = mkt_data.get("event_ticker", "")
        except Exception as e:
            return {"success": False, "error": f"Failed to fetch market data for {market}: {e}"}

    cost_usd = (count * price) / 100

    # --- Risk checks ---
    max_order_usd = risk_limits.get("max_order_usd")
    if max_order_usd and cost_usd > max_order_usd:
        return {"success": False, "error": f"Order ${cost_usd:.2f} exceeds max_order_usd ${max_order_usd}"}

    if not is_paper:
        has_funds = await deduct_capital_for_position(db, bot, cost_usd)
        if not has_funds:
            balance = capital.get("balance_usd", 0)
            return {"success": False, "error": f"Insufficient capital. Need ${cost_usd:.2f}, have ${balance:.2f}"}

    # --- Create trade log (pending until we know fill status) ---
    trade_log = await create_trade_log(
        db=db, bot=bot, action="buy", market=market, side=side,
        price=price, quantity=count, cost_usd=cost_usd,
        status="pending",
        market_title=market_title,
    )

    # --- Place order on exchange ---
    order_response = None
    try:
        order_response = await _place_order(
            client, platform, market, side, "buy", count, price=price,
        )
    except Exception as e:
        logger.error(f"{platform} order failed for {market}: {e}")
        await credit_capital_for_close(db, bot, cost_usd, 0)
        await update_trade_log_status(db, trade_log, "failed", error=str(e))
        return {"success": False, "error": f"Order failed: {e}"}

    # --- Check fill status from exchange response ---
    fill_status = _parse_fill_status(order_response, count)

    if fill_status["status"] == "resting":
        # Order is on the book but nothing filled — refund capital and warn
        await credit_capital_for_close(db, bot, cost_usd, 0)
        await update_trade_log_status(db, trade_log, "resting",
                                      order_response=order_response)
        return {
            "success": False,
            "error": (
                f"Limit order resting (unfilled) — your price of {price}c "
                f"didn't match any sellers. The order is on the book but no "
                f"contracts were bought. Consider raising your price closer "
                f"to the ask, or use a price you saw from get_market_price."
            ),
            "order_id": fill_status.get("order_id"),
        }

    if fill_status["status"] == "partial":
        filled = fill_status["filled_count"]
        filled_cost = (filled * price) / 100
        unfilled_cost = cost_usd - filled_cost
        await credit_capital_for_close(db, bot, unfilled_cost, 0)
        status = "partial"
        qty, pos_cost = filled, filled_cost
    else:
        status = "executed"
        qty, pos_cost = count, cost_usd

    # --- Create position for filled contracts ---
    position_id = None
    try:
        position = await create_position(
            db=db, bot=bot, market=market, side=side,
            entry_price=price, quantity=qty, cost_usd=pos_cost,
            exit_config=ExitConfig(), paper=False,
            market_title=market_title, event_ticker=event_ticker,
        )
        position_id = str(position.id)
    except Exception as e:
        logger.error(f"Failed to create position for {market}: {e}")
        await credit_capital_for_close(db, bot, pos_cost, 0)

    await update_trade_log_status(db, trade_log, status,
                                  order_response=order_response,
                                  position_id=position_id)

    # Recompute P&L stats after trade
    await recompute_bot_pnl(db, bot.id)

    if status == "partial":
        return {
            "success": True,
            "message": (
                f"Partially filled: {filled}/{count} contracts of "
                f"{side.upper()} on {market_title or market} "
                f"(limit @ {price}c, ${filled_cost:.2f}). "
                f"Remaining {count - filled} contracts are resting on the book."
            ),
            "trade": {
                "action": "buy", "market": market, "market_title": market_title,
                "side": side, "count": filled, "requested_count": count,
                "price_cents": price, "cost_usd": round(filled_cost, 2),
                "paper": False, "reason": reason, "fill_status": "partial",
                "position_id": position_id,
            },
        }

    return {
        "success": True,
        "message": (
            f"Bought {count}x {side.upper()} on "
            f"{market_title or market} (filled @ {price}c, ${cost_usd:.2f})"
        ),
        "trade": {
            "action": "buy",
            "market": market,
            "market_title": market_title,
            "side": side,
            "count": count,
            "price_cents": price,
            "cost_usd": round(cost_usd, 2),
            "paper": False,
            "reason": reason,
            "fill_status": "filled",
            "position_id": position_id,
        },
    }


async def _execute_sell(
    db, bot, platform: str, user_id: str, is_paper: bool,
    position_id: str, reason: str,
    price: Optional[int] = None,
) -> Dict[str, Any]:
    """Execute a sell order — closes an existing position."""
    from crud.bots import (
        get_position, close_position, credit_capital_for_close,
        create_trade_log, update_trade_log_status,
        recompute_bot_pnl,
    )

    pos = await get_position(db, position_id)
    if not pos or str(pos.bot_id) != str(bot.id):
        return {"success": False, "error": "Position not found or doesn't belong to this bot"}
    if pos.status == "closed":
        return {"success": False, "error": "Position is already closed"}

    # --- Get exit price ---
    client = await get_platform_client(db, user_id, platform)
    if price is not None:
        exit_price = price
    elif client:
        try:
            exit_price = int(await _get_mid_price(client, platform, pos.market, pos.side))
        except Exception:
            exit_price = pos.current_price or pos.entry_price
    else:
        exit_price = pos.current_price or pos.entry_price

    # --- Place sell order on exchange (live only) ---
    order_response = None
    sell_qty = int(pos.quantity)
    if not pos.paper and client:
        try:
            order_response = await _place_order(
                client, platform, pos.market, pos.side, "sell", sell_qty,
                price=exit_price,
            )
        except Exception as e:
            logger.error(f"Sell order failed for position {position_id}: {e}")
            return {"success": False, "error": f"Sell order failed: {e}"}

        # --- Check fill status ---
        fill_status = _parse_fill_status(order_response, sell_qty)

        if fill_status["status"] == "resting":
            return {
                "success": False,
                "error": (
                    f"Sell order resting (unfilled) — your price of {exit_price}c "
                    f"didn't match any buyers. The order is on the book but no "
                    f"contracts were sold. Consider lowering your price closer "
                    f"to the bid."
                ),
                "order_id": fill_status.get("order_id"),
            }

        if fill_status["status"] == "partial":
            filled = fill_status["filled_count"]
            filled_cost = round((filled / sell_qty) * pos.cost_usd, 2)
            # Reduce position quantity and credit capital for the sold portion
            remaining_qty = sell_qty - filled
            pos.quantity = remaining_qty
            pos.cost_usd = round(pos.cost_usd - filled_cost, 2)
            realized_pnl = round((filled * (100 - exit_price) / 100) - filled_cost, 2) if pos.side == "no" else round((filled * exit_price / 100) - filled_cost, 2)
            await credit_capital_for_close(db, bot, filled_cost, realized_pnl)
            await db.commit()
            trade_log = await create_trade_log(
                db=db, bot=bot, action="sell", market=pos.market, side=pos.side,
                price=exit_price, quantity=filled, cost_usd=filled_cost,
                status="partial",
                market_title=pos.market_title,
                realized_pnl_usd=realized_pnl,
            )
            await update_trade_log_status(db, trade_log, "partial",
                                          order_response=order_response,
                                          position_id=str(pos.id))
            return {
                "success": True,
                "message": (
                    f"Partially sold {filled}/{sell_qty} contracts on "
                    f"{pos.market_title or pos.market} (P&L: ${realized_pnl:.2f}). "
                    f"Position reduced to {remaining_qty} contracts."
                ),
                "trade": {
                    "action": "sell", "market": pos.market,
                    "market_title": pos.market_title, "side": pos.side,
                    "count": filled, "requested_count": sell_qty,
                    "exit_price_cents": exit_price, "realized_pnl_usd": realized_pnl,
                    "paper": False, "reason": reason, "fill_status": "partial",
                },
            }

    # --- Close position (computes realized_pnl_usd correctly) ---
    close_reason = reason or "manual"
    await close_position(db, pos, exit_price=exit_price, close_reason=close_reason, closed_via="chat")
    realized_pnl = pos.realized_pnl_usd or 0.0
    await credit_capital_for_close(db, bot, pos.cost_usd, realized_pnl)

    # --- Log the trade with realized P&L ---
    trade_log = await create_trade_log(
        db=db, bot=bot, action="sell", market=pos.market, side=pos.side,
        price=exit_price, quantity=sell_qty, cost_usd=pos.cost_usd,
        status="executed",
        market_title=pos.market_title,
        realized_pnl_usd=realized_pnl,
    )
    if order_response:
        await update_trade_log_status(db, trade_log, "executed",
                                      order_response=order_response,
                                      position_id=str(pos.id))

    # Recompute P&L stats after trade
    await recompute_bot_pnl(db, bot.id)

    return {
        "success": True,
        "message": (
            f"Sold position on "
            f"{pos.market_title or pos.market} — P&L: ${realized_pnl:.2f}"
        ),
        "trade": {
            "action": "sell",
            "market": pos.market,
            "market_title": pos.market_title,
            "side": pos.side,
            "count": sell_qty,
            "exit_price_cents": exit_price,
            "realized_pnl_usd": round(realized_pnl, 2),
            "paper": False,
            "reason": reason,
            "fill_status": "filled",
        },
    }


# ---------------------------------------------------------------------------
# execute_approved_trade — called by the approve route to actually execute
# ---------------------------------------------------------------------------

async def execute_approved_trade(db, trade_log) -> dict:
    """
    Execute a trade that was previously submitted for approval.
    Called by the approve_trade route after user confirms.

    Reads execution params from trade_log.pending_params and runs the actual
    platform order, then updates the trade_log in place (no new log created).
    """
    from crud.bots import (
        get_bot, update_trade_log_status,
        create_position, deduct_capital_for_position,
        get_position, close_position, credit_capital_for_close,
        recompute_bot_pnl,
    )
    from schemas.bots import ExitConfig

    params = trade_log.pending_params or {}
    action = params.get("action") or trade_log.action
    market = params.get("market") or trade_log.market
    side = params.get("side") or trade_log.side or "yes"
    count = params.get("count") or trade_log.quantity or 1
    price = params.get("price") or int(trade_log.price or 0) or None
    reason = params.get("reason", "")
    sell_position_id = params.get("position_id")

    bot = await get_bot(db, str(trade_log.bot_id), trade_log.user_id)
    if not bot:
        await update_trade_log_status(db, trade_log, "failed", error="Bot not found")
        return {"success": False, "error": "Bot not found"}

    platform = (bot.config or {}).get("platform", "kalshi")
    user_id = trade_log.user_id
    client = await get_platform_client(db, user_id, platform)
    if not client:
        await update_trade_log_status(db, trade_log, "failed", error=f"No {platform} credentials")
        return {"success": False, "error": f"No {platform} credentials configured"}

    if action == "buy":
        cost_usd = (count * price) / 100

        # Capital check
        has_funds = await deduct_capital_for_position(db, bot, cost_usd)
        if not has_funds:
            balance = (bot.config or {}).get("capital", {}).get("balance_usd", 0)
            await update_trade_log_status(db, trade_log, "failed",
                                          error=f"Insufficient capital: need ${cost_usd:.2f}, have ${balance:.2f}")
            return {"success": False, "error": f"Insufficient capital. Need ${cost_usd:.2f}, have ${balance:.2f}"}

        # Place order
        order_response = None
        try:
            order_response = await _place_order(client, platform, market, side, "buy", count, price=price)
        except Exception as e:
            await credit_capital_for_close(db, bot, cost_usd, 0)
            await update_trade_log_status(db, trade_log, "failed", error=str(e))
            return {"success": False, "error": f"Order failed: {e}"}

        fill_status = _parse_fill_status(order_response, count)

        if fill_status["status"] == "resting":
            await credit_capital_for_close(db, bot, cost_usd, 0)
            await update_trade_log_status(db, trade_log, "resting", order_response=order_response)
            return {
                "success": False,
                "error": f"Limit order resting (unfilled) — price {price}c didn't match any sellers.",
                "order_id": fill_status.get("order_id"),
            }

        filled = fill_status.get("filled_count", count)
        filled_cost = (filled * price) / 100
        if fill_status["status"] == "partial":
            await credit_capital_for_close(db, bot, cost_usd - filled_cost, 0)
            qty, pos_cost = filled, filled_cost
            final_status = "partial"
        else:
            qty, pos_cost = count, cost_usd
            final_status = "executed"

        # Create position
        position_id_created = None
        try:
            position = await create_position(
                db=db, bot=bot, market=market, side=side,
                entry_price=price, quantity=qty, cost_usd=pos_cost,
                exit_config=ExitConfig(), paper=False,
                market_title=trade_log.market_title, event_ticker="",
            )
            position_id_created = str(position.id)
        except Exception as e:
            logger.error(f"Failed to create position after approval: {e}")
            await credit_capital_for_close(db, bot, pos_cost, 0)

        await update_trade_log_status(db, trade_log, final_status,
                                      order_response=order_response,
                                      position_id=position_id_created)
        await recompute_bot_pnl(db, bot.id)
        return {"success": True, "status": final_status,
                "message": f"Executed: bought {qty}x {side.upper()} on {trade_log.market_title or market} @ {price}c"}

    else:  # sell
        pos = await get_position(db, sell_position_id)
        if not pos or str(pos.bot_id) != str(bot.id):
            await update_trade_log_status(db, trade_log, "failed", error="Position not found")
            return {"success": False, "error": "Position not found"}
        if pos.status == "closed":
            await update_trade_log_status(db, trade_log, "failed", error="Position already closed")
            return {"success": False, "error": "Position is already closed"}

        exit_price = price or int(await _get_mid_price(client, platform, pos.market, pos.side))
        sell_qty = int(pos.quantity)

        order_response = None
        if not pos.paper:
            try:
                order_response = await _place_order(client, platform, pos.market, pos.side, "sell", sell_qty, price=exit_price)
            except Exception as e:
                await update_trade_log_status(db, trade_log, "failed", error=str(e))
                return {"success": False, "error": f"Sell order failed: {e}"}

            fill_status = _parse_fill_status(order_response, sell_qty)
            if fill_status["status"] == "resting":
                await update_trade_log_status(db, trade_log, "resting", order_response=order_response)
                return {"success": False, "error": f"Sell order resting — price {exit_price}c didn't match any buyers."}

        await close_position(db, pos, exit_price=exit_price, close_reason=reason or "approved", closed_via="chat")
        realized_pnl = pos.realized_pnl_usd or 0.0
        await credit_capital_for_close(db, bot, pos.cost_usd, realized_pnl)

        await update_trade_log_status(db, trade_log, "executed",
                                      order_response=order_response,
                                      position_id=str(pos.id),
                                      realized_pnl_usd=realized_pnl)
        await recompute_bot_pnl(db, bot.id)
        return {"success": True, "status": "executed",
                "message": f"Sold position on {pos.market_title or pos.market} — P&L: ${realized_pnl:.2f}"}


# ---------------------------------------------------------------------------
# list_trades — let the bot see its own trade history
# ---------------------------------------------------------------------------

async def list_trades_impl(context: AgentContext, limit: int = 20) -> Dict[str, Any]:
    """List recent trade logs for this bot."""
    from core.database import get_db_session
    from crud.bots import list_trade_logs

    bot_id = _get_bot_id(context)
    user_id = context.user_id

    async with get_db_session() as db:
        trades = await list_trade_logs(db, user_id=user_id, bot_id=bot_id, limit=limit)
        return {
            "success": True,
            "count": len(trades),
            "trades": [
                {
                    "id": str(t.id),
                    "action": t.action,
                    "market": t.market,
                    "market_title": t.market_title,
                    "side": t.side,
                    "price": t.price,
                    "quantity": t.quantity,
                    "cost_usd": t.cost_usd,
                    "realized_pnl_usd": t.realized_pnl_usd,
                    "status": t.status,
                    "created_at": t.created_at.isoformat() if t.created_at else None,
                    "error": t.error,
                }
                for t in trades
            ],
        }


# ---------------------------------------------------------------------------
# cancel_order — cancel a resting (unfilled) order on the exchange
# ---------------------------------------------------------------------------

async def cancel_order_impl(context: AgentContext, order_id: str) -> Dict[str, Any]:
    """Cancel a resting order on the exchange."""
    from core.database import get_db_session
    from crud.bots import get_bot, update_trade_log_by_order_id

    bot_id = _get_bot_id(context)
    user_id = context.user_id

    async with get_db_session() as db:
        bot = await get_bot(db, bot_id, user_id)
        if not bot:
            return {"success": False, "error": "Bot not found"}

        config = bot.config or {}
        platform = config.get("platform", "kalshi")

        client = await get_platform_client(db, user_id, platform)
        if not client:
            return {"success": False, "error": f"No {platform} credentials configured."}

        try:
            result = await _cancel_order(client, platform, order_id)
        except Exception as e:
            logger.error(f"Failed to cancel order {order_id}: {e}")
            return {"success": False, "error": f"Cancel failed: {e}"}

        # Update the associated trade log to reflect cancellation
        await update_trade_log_by_order_id(db, order_id, "cancelled")

        return {
            "success": True,
            "message": f"Order {order_id} cancelled.",
            "order_id": order_id,
            "cancel_response": result,
        }


# ---------------------------------------------------------------------------
# Fill status parsing
# ---------------------------------------------------------------------------

def _parse_fill_status(order_response: dict, requested_count: int) -> dict:
    """
    Parse exchange order response to determine fill status.

    Kalshi POST /portfolio/orders returns an "order" object with:
      - status: "resting" | "executed" | "canceled" | ...
      - remaining_count: contracts still unfilled
      - order_id: unique order identifier
    """
    if not order_response:
        # No response (e.g. paper trade) — assume filled
        return {"status": "filled", "filled_count": requested_count}

    order = order_response.get("order", order_response)
    order_status = order.get("status", "")
    order_id = order.get("order_id")

    logger.info(f"Order response — status: {order_status}, order_id: {order_id}")
    logger.debug(f"Full order response: {order_response}")

    # Default remaining to requested_count (assume unfilled) so that missing
    # fields don't accidentally count as filled
    remaining = order.get("remaining_count", requested_count)
    filled_count = requested_count - remaining

    # Trust the status field first — "executed" means fully filled on Kalshi
    if order_status == "executed":
        return {"status": "filled", "filled_count": requested_count, "order_id": order_id}
    elif order_status == "resting":
        if filled_count > 0:
            return {"status": "partial", "filled_count": filled_count, "order_id": order_id}
        return {"status": "resting", "filled_count": 0, "order_id": order_id}
    else:
        # Unknown status — check remaining_count if present, otherwise assume resting
        if "remaining_count" in order and remaining == 0:
            return {"status": "filled", "filled_count": requested_count, "order_id": order_id}
        elif filled_count > 0:
            return {"status": "partial", "filled_count": filled_count, "order_id": order_id}
        else:
            return {"status": "resting", "filled_count": 0, "order_id": order_id}


# ---------------------------------------------------------------------------
# Platform-agnostic dispatch layer
#
# Each platform implements: _get_client, _fetch_market, _get_mid_price, _place_order
# Currently only Kalshi is supported. To add Polymarket/Alpaca, add elif branches.
# ---------------------------------------------------------------------------

async def get_platform_client(db, user_id: str, platform: str):
    """Get an authenticated client for the given platform."""
    if platform == "kalshi":
        return await _get_kalshi_client(db, user_id)
    # elif platform == "polymarket": ...
    logger.warning(f"No client implementation for platform: {platform}")
    return None


async def fetch_market_data(client, platform: str, market: str) -> dict:
    """Fetch market data (price, title, etc.) from the platform."""
    if platform == "kalshi":
        return await _fetch_kalshi_market(client, market)
    raise RuntimeError(f"Unsupported platform: {platform}")


async def _get_mid_price(client, platform: str, market: str, side: str) -> float:
    """Get the mid price for a market/side."""
    if platform == "kalshi":
        return await _get_kalshi_mid_price(client, market, side)
    raise RuntimeError(f"Unsupported platform: {platform}")


async def _place_order(
    client, platform: str, market: str, side: str, action: str, count: int,
    price: int,
) -> dict:
    """Place a limit order on the platform at the specified price."""
    if platform == "kalshi":
        return await _place_kalshi_order(client, market, side, action, count, price)
    raise RuntimeError(f"Unsupported platform: {platform}")


async def _cancel_order(client, platform: str, order_id: str) -> dict:
    """Cancel a resting order on the platform."""
    if platform == "kalshi":
        return await _cancel_kalshi_order(client, order_id)
    raise RuntimeError(f"Unsupported platform: {platform}")


# ---------------------------------------------------------------------------
# Kalshi-specific implementations
# ---------------------------------------------------------------------------

async def _get_kalshi_client(db, user_id: str):
    """Create a Kalshi HTTP client using the user's credentials."""
    from services.api_keys import ApiKeyService
    from skills.kalshi_trading.scripts._client import KalshiHTTPClient

    svc = ApiKeyService(db, user_id)
    creds = await svc.get_kalshi_credentials()
    if not creds:
        return None

    api_key_id = creds["api_key_id"].get()
    private_key = creds["private_key"].get().replace("\\n", "\n")
    return KalshiHTTPClient(api_key_id, private_key)


async def _fetch_kalshi_market(kalshi_client, market: str) -> dict:
    """Fetch market data from Kalshi."""
    import asyncio
    data = await asyncio.get_event_loop().run_in_executor(
        None, lambda: kalshi_client.get(f"/markets/{market}")
    )
    return data.get("market", data)


async def _get_kalshi_mid_price(kalshi_client, market: str, side: str) -> float:
    """Get mid price for a market/side."""
    mkt = await _fetch_kalshi_market(kalshi_client, market)
    if side == "yes":
        bid = mkt.get("yes_bid") or 0
        ask = mkt.get("yes_ask") or 0
    else:
        bid = mkt.get("no_bid") or 0
        ask = mkt.get("no_ask") or 0
    if bid and ask:
        return (bid + ask) / 2
    return bid or ask or mkt.get("last_price") or 50


async def _place_kalshi_order(
    kalshi_client, market: str, side: str, action: str, count: int,
    price: int,
) -> dict:
    """Place a limit order on Kalshi at the specified price (cents)."""
    import asyncio

    body = {
        "ticker": market,
        "side": side,
        "action": action,
        "count": count,
        "type": "limit",
    }
    if side == "yes":
        body["yes_price"] = price
    else:
        body["no_price"] = price

    result = await asyncio.get_event_loop().run_in_executor(
        None,
        lambda: kalshi_client.post("/portfolio/orders", body=body),
    )
    return result


async def _cancel_kalshi_order(kalshi_client, order_id: str) -> dict:
    """Cancel a resting order on Kalshi via DELETE /portfolio/orders/{order_id}."""
    import asyncio

    result = await asyncio.get_event_loop().run_in_executor(
        None,
        lambda: kalshi_client.delete(f"/portfolio/orders/{order_id}"),
    )
    return result
