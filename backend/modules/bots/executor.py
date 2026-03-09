"""
Bot Executor — runs a bot tick using LLM reasoning with full tool access.

Flow:
  1. Load bot config, context.md + memory.md from DB/VM
  2. Load open positions (refreshed prices) + recent closed
  3. Build system prompt with all context
  4. Multi-turn LLM loop with trading + research tools
  5. Apply trading actions (buy/sell) server-side with risk enforcement
  6. Log execution, persist state, refresh prices
"""
import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from models.bot import TradingBot, BotExecution
from schemas.bots import ExitConfig
from crud.bots import (
    create_execution,
    complete_execution,
    get_open_positions,
    create_position,
    update_position_price,
    update_position_monitor_note,
    close_position,
    list_positions,
    get_bot_files,
    upsert_bot_file,
    get_position,
    deduct_capital_for_position,
    credit_capital_for_close,
    create_trade_log,
    update_trade_log_status,
)
from .prompts import build_tick_system_prompt

logger = logging.getLogger(__name__)

EXECUTION_TIMEOUT_SECONDS = 120


async def execute_bot_tick(
    db: AsyncSession,
    bot: TradingBot,
    trigger: str = "manual",
    dry_run: bool = True,
) -> BotExecution:
    """
    Execute a single bot tick — LLM reasons about markets and decides actions.

    For now, uses the same sandbox-based execution as the old strategy system
    but will transition to a direct LLM agent loop.
    """
    execution = await create_execution(db, bot, trigger)
    config = bot.config or {}

    # Load positions
    open_positions = await get_open_positions(db, bot.id)
    open_positions_data = [_position_to_dict(p) for p in open_positions]
    closed_positions = await list_positions(db, bot.id, status="closed", limit=20)
    closed_positions_data = [_position_to_dict(p) for p in closed_positions]

    # Load context files from DB
    files = await get_bot_files(db, bot.id)
    context_md = ""
    memory_md = ""
    daily_note = ""
    for f in files:
        if f.filename == "CONTEXT.md" or f.file_type == "context":
            context_md = f.content
        elif f.filename == "MEMORY.md" or f.file_type == "memory":
            memory_md = f.content

    # Use mandate from config if no CONTEXT.md file exists
    mandate = context_md or config.get("mandate", "")

    # Fetch Kalshi client for price operations
    kalshi_client = await _get_kalshi_client(db, bot.user_id)

    capital = config.get("capital", {})
    budget = capital.get("amount_usd", 5)

    try:
        # Build the tick actions using simplified approach
        # (In full implementation, this would be a multi-turn LLM agent loop)
        result = await asyncio.wait_for(
            _run_tick_simple(
                db, bot, config, mandate, memory_md,
                open_positions_data, closed_positions_data,
                kalshi_client, dry_run,
            ),
            timeout=EXECUTION_TIMEOUT_SECONDS,
        )
    except asyncio.TimeoutError:
        msg = f"Bot tick timed out after {EXECUTION_TIMEOUT_SECONDS}s"
        logger.error(f"Bot {bot.id} timed out")
        return await complete_execution(
            db, execution,
            status="failed",
            error=msg,
            summary="Bot tick timed out",
        )
    except Exception as e:
        logger.exception(f"Bot {bot.id} tick failed: {e}")
        return await complete_execution(
            db, execution,
            status="failed",
            error=str(e),
            summary=f"Bot tick failed: {str(e)[:100]}",
        )

    # Apply actions
    actions_list = result.get("actions", [])
    if actions_list:
        await _apply_actions(db, bot, execution, actions_list, config, dry_run, kalshi_client)

    # Persist state updates
    state_update = result.get("state_update")
    if state_update and isinstance(state_update, dict):
        new_config = dict(bot.config or {})
        existing_state = new_config.get("state", {})
        existing_state.update(state_update)
        new_config["state"] = existing_state
        bot.config = new_config
        await db.commit()

    # Refresh prices for open positions not updated by actions
    updated_ids = {
        a.get("position_id") for a in actions_list
        if a.get("action") in ("sell", "update_note")
    }
    await _refresh_open_position_prices(db, bot, config, kalshi_client, exclude_ids=updated_ids)

    status = "success" if result.get("status") == "success" else "failed"

    return await complete_execution(
        db, execution,
        status=status,
        summary=result.get("summary"),
        error=result.get("error"),
        actions=actions_list,
        logs=result.get("logs", []),
    )


async def _run_tick_simple(
    db: AsyncSession,
    bot: TradingBot,
    config: dict,
    mandate: str,
    memory_md: str,
    open_positions: list[dict],
    closed_positions: list[dict],
    kalshi_client,
    dry_run: bool,
) -> dict:
    """
    Run a simplified tick — scan markets based on mandate and make decisions.

    This is a bridge implementation. The full version will use a multi-turn
    LLM agent loop with BaseAgent infrastructure.
    """
    logs = []
    actions = []
    platform = config.get("platform", "kalshi")

    if platform != "kalshi" or not kalshi_client:
        return {
            "status": "success",
            "summary": "No Kalshi client available — skipping tick",
            "logs": ["No Kalshi credentials configured"],
            "actions": [],
        }

    # For now, return a simple scan result
    # The full LLM agent loop will be implemented in Phase 2
    try:
        # Get some markets to show the system works
        data = await asyncio.get_event_loop().run_in_executor(
            None, lambda: kalshi_client.get("/markets", params={"limit": 10, "status": "open"})
        )
        markets = data.get("markets", [])
        logs.append(f"Scanned {len(markets)} markets")

        summary = f"Scanned {len(markets)} markets. Mandate: {mandate[:100] if mandate else 'None set'}"

        return {
            "status": "success",
            "summary": summary,
            "logs": logs,
            "actions": actions,
        }
    except Exception as e:
        return {
            "status": "failed",
            "summary": f"Tick failed: {str(e)[:100]}",
            "error": str(e),
            "logs": logs,
            "actions": [],
        }


async def _get_kalshi_client(db: AsyncSession, user_id: str):
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


async def _apply_actions(
    db: AsyncSession,
    bot: TradingBot,
    execution: BotExecution,
    actions: list[dict],
    config: dict,
    dry_run: bool,
    kalshi_client,
) -> None:
    """Process action dicts from the bot's tick.

    Capital enforcement:
    - Capital check happens BEFORE any exchange API call
    - Risk limits are checked against actual cost_usd (not just requested amount)
    - Sell verifies position is still open to prevent double-credit
    - Paper (dry_run) positions are tracked separately and don't affect live capital
    """
    execution_id = str(execution.id)
    risk_limits = config.get("risk_limits", {})
    capital = config.get("capital", {})
    max_order_usd = risk_limits.get("max_order_usd")
    max_daily_usd = risk_limits.get("max_daily_usd")
    amount_usd = capital.get("amount_usd", 5)

    total_spent_this_run = 0.0

    for action in actions:
        action_type = action.get("action")

        if action_type == "buy":
            market = action.get("market", "")
            side = action.get("side", "yes")
            order_amount = action.get("amount_usd", amount_usd)

            # Fetch price first so we can check actual cost
            entry_price = 0
            quantity = 0
            try:
                entry_price, quantity = await _get_market_price_and_qty(kalshi_client, market, side, order_amount)
            except Exception as e:
                logger.error(f"Failed to get market price for {market}: {e}")
                continue

            cost_usd = (quantity * entry_price) / 100

            # Risk limits — check actual cost, not just requested amount
            if max_order_usd and cost_usd > max_order_usd:
                logger.warning(f"BLOCKED: ${cost_usd:.2f} exceeds max_order_usd ${max_order_usd}")
                continue
            if max_daily_usd and (total_spent_this_run + cost_usd) > max_daily_usd:
                logger.warning(f"BLOCKED: ${total_spent_this_run + cost_usd:.2f} would exceed max_daily_usd ${max_daily_usd}")
                continue

            # Capital check BEFORE placing any order
            if not dry_run:
                has_funds = await deduct_capital_for_position(db, bot, cost_usd)
                if not has_funds:
                    logger.warning(f"BLOCKED: insufficient capital for ${cost_usd:.2f} order on {market}")
                    continue

            # Log the trade attempt
            trade_log = await create_trade_log(
                db=db, bot=bot, action="buy", market=market, side=side,
                price=entry_price, quantity=quantity, cost_usd=cost_usd,
                execution_id=execution_id, dry_run=dry_run,
                status="dry_run" if dry_run else "executed",
            )

            if dry_run:
                logger.info(f"[PAPER] Buy {market} {side} x{quantity} @ {entry_price}c (${cost_usd:.2f})")
            else:
                if not kalshi_client:
                    # Refund the capital we just deducted
                    await credit_capital_for_close(db, bot, cost_usd, 0)
                    await update_trade_log_status(db, trade_log, "failed", error="No Kalshi client")
                    continue
                try:
                    order_result = await _place_kalshi_order(kalshi_client, market, side, "buy", quantity)
                    await update_trade_log_status(db, trade_log, "executed", order_response=order_result if isinstance(order_result, dict) else None)
                except Exception as e:
                    logger.error(f"Failed to place buy order for {market}: {e}")
                    # Refund capital on failed order
                    await credit_capital_for_close(db, bot, cost_usd, 0)
                    await update_trade_log_status(db, trade_log, "failed", error=str(e))
                    continue

            total_spent_this_run += cost_usd

            try:
                position = await create_position(
                    db=db,
                    bot=bot,
                    market=market,
                    side=side,
                    entry_price=entry_price,
                    quantity=quantity,
                    cost_usd=cost_usd,
                    exit_config=ExitConfig(),
                    entered_via=execution_id,
                    paper=dry_run,
                )
                await update_trade_log_status(db, trade_log, trade_log.status, position_id=str(position.id))
            except Exception as e:
                logger.error(f"Failed to create position for {market}: {e}")
                # Refund capital if position creation failed (live only)
                if not dry_run:
                    await credit_capital_for_close(db, bot, cost_usd, 0)

        elif action_type == "sell":
            position_id = action.get("position_id", "")
            reason = action.get("reason", "manual")

            pos = await get_position(db, position_id)
            if not pos:
                logger.warning(f"Sell skipped: position {position_id} not found")
                continue
            if pos.status == "closed":
                logger.warning(f"Sell skipped: position {position_id} already closed")
                continue

            exit_price = pos.current_price or pos.entry_price
            if kalshi_client:
                try:
                    mkt_data = await _fetch_kalshi_market(kalshi_client, pos.market)
                    bid = mkt_data.get("yes_bid") or 0
                    ask = mkt_data.get("yes_ask") or 0
                    if bid and ask:
                        exit_price = (bid + ask) / 2
                    elif bid:
                        exit_price = bid
                except Exception:
                    pass

            # Log the sell trade
            trade_log = await create_trade_log(
                db=db, bot=bot, action="sell", market=pos.market, side=pos.side,
                price=exit_price, quantity=int(pos.quantity),
                cost_usd=pos.cost_usd,
                execution_id=execution_id, dry_run=dry_run,
                status="dry_run" if dry_run else "executed",
            )
            trade_log.position_id = pos.id

            if not dry_run:
                if not kalshi_client:
                    await update_trade_log_status(db, trade_log, "failed", error="No Kalshi client")
                    continue
                try:
                    order_result = await _place_kalshi_order(kalshi_client, pos.market, pos.side, "sell", int(pos.quantity))
                    await update_trade_log_status(db, trade_log, "executed", order_response=order_result if isinstance(order_result, dict) else None)
                except Exception as e:
                    logger.error(f"Failed to place sell order: {e}")
                    await update_trade_log_status(db, trade_log, "failed", error=str(e))
                    continue

            try:
                await close_position(db=db, position=pos, exit_price=exit_price, close_reason=reason, closed_via=execution_id)
                # Return cost + realized P&L to capital balance (live positions only)
                if not pos.paper:
                    realized_pnl = (exit_price - pos.entry_price) * pos.quantity
                    await credit_capital_for_close(db, bot, pos.cost_usd, realized_pnl)
            except Exception as e:
                logger.error(f"Failed to close position {position_id}: {e}")

        elif action_type == "update_note":
            position_id = action.get("position_id", "")
            note = action.get("note", "")
            pos = await get_position(db, position_id)
            if pos:
                try:
                    await update_position_monitor_note(db, pos, note)
                except Exception as e:
                    logger.error(f"Failed to update note: {e}")


async def _get_market_price_and_qty(kalshi_client, market: str, side: str, amount_usd: float) -> tuple[float, int]:
    if not kalshi_client:
        raise RuntimeError("No Kalshi client available")
    mkt = await _fetch_kalshi_market(kalshi_client, market)
    if side == "yes":
        price = mkt.get("yes_ask") or mkt.get("yes_bid") or mkt.get("last_price") or 50
    else:
        price = mkt.get("no_ask") or mkt.get("no_bid") or mkt.get("last_price") or 50
    quantity = max(1, int((amount_usd * 100) / price))
    return price, quantity


async def _fetch_kalshi_market(kalshi_client, market: str) -> dict:
    data = await asyncio.get_event_loop().run_in_executor(
        None, lambda: kalshi_client.get(f"/markets/{market}")
    )
    return data.get("market", data)


async def _place_kalshi_order(kalshi_client, market: str, side: str, action: str, count: int) -> dict:
    from kalshi_trading.scripts import kalshi as kalshi_lib
    result = await asyncio.get_event_loop().run_in_executor(
        None,
        lambda: kalshi_lib.place_order(ticker=market, side=side, action=action, count=count, order_type="market"),
    )
    return result


def _position_to_dict(position) -> dict:
    return {
        "id": str(position.id),
        "market": position.market,
        "platform": position.platform,
        "side": position.side,
        "status": position.status,
        "entry_price": position.entry_price,
        "entry_time": position.entry_time.isoformat() if position.entry_time else None,
        "quantity": position.quantity,
        "cost_usd": position.cost_usd,
        "current_price": position.current_price,
        "unrealized_pnl_usd": position.unrealized_pnl_usd,
        "monitor_note": position.monitor_note,
        "paper": position.paper,
        "market_title": position.market_title,
        "event_ticker": position.event_ticker,
        "exit_price": position.exit_price,
        "realized_pnl_usd": position.realized_pnl_usd,
        "close_reason": position.close_reason,
        "closed_at": position.closed_at.isoformat() if position.closed_at else None,
    }


async def _refresh_open_position_prices(
    db: AsyncSession,
    bot,
    config: dict,
    kalshi_client,
    exclude_ids: set,
) -> None:
    """Fetch current market prices for open positions not updated this run."""
    platform = config.get("platform", "kalshi")
    if platform != "kalshi" or not kalshi_client:
        return

    positions = await get_open_positions(db, bot.id)
    stale = [p for p in positions if str(p.id) not in exclude_ids]
    if not stale:
        return

    try:
        for pos in stale:
            try:
                data = await asyncio.get_event_loop().run_in_executor(
                    None, lambda m=pos.market: kalshi_client.get(f"/markets/{m}")
                )
                mkt = data.get("market", data)
                yes_bid = mkt.get("yes_bid") or 0
                yes_ask = mkt.get("yes_ask") or 0
                if yes_bid and yes_ask:
                    price = (yes_bid + yes_ask) / 2
                elif yes_bid:
                    price = yes_bid
                elif yes_ask:
                    price = yes_ask
                else:
                    price = None

                changed = False
                if not pos.market_title and mkt.get("title"):
                    pos.market_title = mkt["title"]
                    changed = True
                event_ticker = mkt.get("event_ticker")
                if not pos.event_ticker and event_ticker:
                    pos.event_ticker = event_ticker
                    changed = True

                if price is not None:
                    now = datetime.now(timezone.utc)
                    pos.current_price = price
                    pos.unrealized_pnl_usd = (price - pos.entry_price) * pos.quantity
                    pos.last_priced_at = now
                    existing = list(pos.price_history or [])
                    existing.append({"t": now.isoformat(), "price": price})
                    if len(existing) > 500:
                        existing = existing[-500:]
                    pos.price_history = existing
                    await db.commit()
                    await db.refresh(pos)
                elif changed:
                    await db.commit()
            except Exception as e:
                logger.debug(f"Price refresh skipped for {pos.market}: {e}")
    except Exception as e:
        logger.debug(f"Price refresh aborted for bot {bot.id}: {e}")
