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


async def configure_bot_impl(
    context: AgentContext,
    name: Optional[str] = None,
    capital_usd: Optional[float] = None,
    max_positions: Optional[int] = None,
) -> Dict[str, Any]:
    """Update bot settings. Only provided fields are changed."""
    from core.database import get_db_session
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

        return {
            "success": True,
            "message": "Bot updated successfully",
            "updated_fields": list(updates.keys()),
            "bot_name": bot.name,
        }


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
    Place a trade with full tracking — TradeLog, BotPosition, capital management.

    Platform-agnostic tracking layer. The platform-specific order execution
    is dispatched based on bot.config.platform.

    Buy flow:
      1. Check capital/risk → 2. Place limit order at caller's price →
      3. Create TradeLog → 4. Create BotPosition → 5. Deduct capital

    Sell flow (requires position_id):
      1. Look up position → 2. Place sell order at caller's price (or market bid) →
      3. Create TradeLog → 4. Close BotPosition → 5. Credit capital back
    """
    from core.database import get_db_session
    from crud.bots import (
        get_bot, create_trade_log, update_trade_log_status,
        create_position, deduct_capital_for_position,
        get_position, close_position, credit_capital_for_close,
    )
    from schemas.bots import ExitConfig

    bot_id = _get_bot_id(context)
    user_id = context.user_id

    # --- Validation ---
    if action not in ("buy", "sell"):
        return {"success": False, "error": f"Invalid action '{action}'. Must be 'buy' or 'sell'."}
    if side not in ("yes", "no"):
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

        config = bot.config or {}
        platform = config.get("platform", "kalshi")
        is_paper = False

        if action == "sell":
            return await _execute_sell(
                db, bot, platform, user_id, is_paper,
                position_id, reason, price,
            )
        else:
            return await _execute_buy(
                db, bot, platform, user_id, is_paper, config,
                market, side, count, reason, price,
            )


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

    # --- Create trade log (pending) ---
    trade_log = await create_trade_log(
        db=db, bot=bot, action="buy", market=market, side=side,
        price=price, quantity=count, cost_usd=cost_usd,
        status="executed",
        market_title=market_title,
    )

    # --- Place order on exchange ---
    order_response = None
    try:
        order_response = await _place_order(
            client, platform, market, side, "buy", count, price=price,
        )
        await update_trade_log_status(db, trade_log, "executed",
                                      order_response=order_response)
    except Exception as e:
        logger.error(f"{platform} order failed for {market}: {e}")
        await credit_capital_for_close(db, bot, cost_usd, 0)
        await update_trade_log_status(db, trade_log, "failed", error=str(e))
        return {"success": False, "error": f"Order failed: {e}"}

    # --- Create position ---
    try:
        position = await create_position(
            db=db, bot=bot, market=market, side=side,
            entry_price=price, quantity=count, cost_usd=cost_usd,
            exit_config=ExitConfig(), paper=False,
            market_title=market_title, event_ticker=event_ticker,
        )
        await update_trade_log_status(db, trade_log, trade_log.status,
                                      position_id=str(position.id))
    except Exception as e:
        logger.error(f"Failed to create position for {market}: {e}")
        await credit_capital_for_close(db, bot, cost_usd, 0)

    return {
        "success": True,
        "message": (
            f"Bought {count}x {side.upper()} on "
            f"{market_title or market} (limit @ {price}c, ${cost_usd:.2f})"
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
    if not pos.paper and client:
        try:
            order_response = await _place_order(
                client, platform, pos.market, pos.side, "sell", int(pos.quantity),
                price=exit_price,
            )
        except Exception as e:
            logger.error(f"Sell order failed for position {position_id}: {e}")
            return {"success": False, "error": f"Sell order failed: {e}"}

    # --- Close position (computes realized_pnl_usd correctly) ---
    close_reason = reason or "manual"
    await close_position(db, pos, exit_price=exit_price, close_reason=close_reason, closed_via="chat")
    realized_pnl = pos.realized_pnl_usd or 0.0
    await credit_capital_for_close(db, bot, pos.cost_usd, realized_pnl)

    # --- Log the trade with realized P&L ---
    trade_log = await create_trade_log(
        db=db, bot=bot, action="sell", market=pos.market, side=pos.side,
        price=exit_price, quantity=int(pos.quantity), cost_usd=pos.cost_usd,
        status="executed",
        market_title=pos.market_title,
        realized_pnl_usd=realized_pnl,
    )
    if order_response:
        await update_trade_log_status(db, trade_log, "executed",
                                      order_response=order_response,
                                      position_id=str(pos.id))

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
            "count": int(pos.quantity),
            "exit_price_cents": exit_price,
            "realized_pnl_usd": round(realized_pnl, 2),
            "paper": False,
            "reason": reason,
        },
    }


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
                    "status": t.status,
                    "created_at": t.created_at.isoformat() if t.created_at else None,
                    "error": t.error,
                }
                for t in trades
            ],
        }


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
