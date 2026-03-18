"""
Bot Executor — runs a bot tick using LLM reasoning with full tool access.

Flow:
  1. Load bot config, STRATEGY.md + MEMORY.md from DB/VM
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
from .prompts import build_bot_system_prompt

logger = logging.getLogger(__name__)

EXECUTION_TIMEOUT_SECONDS = 120


async def execute_bot_tick(
    db: AsyncSession,
    bot: TradingBot,
    trigger: str = "manual",
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

    # Ensure bot has its own sandbox directory (migrate legacy files on first run)
    bot_dir = bot.directory or f"bots/{str(bot.id)[:8]}"
    await ensure_bot_directory(bot.user_id, bot_dir)

    # Load context files from DB (bot_files is the synced mirror)
    files = await get_bot_files(db, bot.id)
    strategy_md = ""
    memory_md = ""
    daily_note = ""
    for f in files:
        if f.filename == "STRATEGY.md" or f.file_type == "strategy":
            strategy_md = f.content
        elif f.filename == "MEMORY.md" or f.file_type == "memory":
            memory_md = f.content
        # Legacy fallbacks
        elif f.filename == "CONTEXT.md" or f.file_type == "context":
            strategy_md = strategy_md or f.content
        elif f.filename == "AGENTS.md" or f.file_type == "agents":
            memory_md = memory_md or f.content

    # Legacy: fall back to config.mandate if no STRATEGY.md file exists yet
    if not strategy_md:
        strategy_md = config.get("mandate", "")

    # Bootstrap from sandbox if not in DB (source of truth is sandbox files)
    bot_dir = bot.directory or f"bots/{str(bot.id)[:8]}"
    from modules.tools.implementations.code_execution import read_sandbox_file
    if not strategy_md:
        try:
            raw = await read_sandbox_file(bot.user_id, f"{bot_dir}/STRATEGY.md")
            if raw:
                strategy_md = raw.decode("utf-8", errors="replace").strip()
        except Exception:
            pass
    if not memory_md:
        try:
            raw = await read_sandbox_file(bot.user_id, f"{bot_dir}/MEMORY.md")
            if raw:
                memory_md = raw.decode("utf-8", errors="replace").strip()
        except Exception:
            pass

    # Fetch Kalshi client for price operations
    kalshi_client = await _get_kalshi_client(db, bot.user_id)

    capital = config.get("capital", {})
    budget = capital.get("amount_usd", 5)

    try:
        # Build the tick actions using simplified approach
        # (In full implementation, this would be a multi-turn LLM agent loop)
        result = await asyncio.wait_for(
            _run_tick_simple(
                db, bot, config, strategy_md, memory_md,
                open_positions_data, closed_positions_data,
                kalshi_client,
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
        await _apply_actions(db, bot, execution, actions_list, config, kalshi_client)

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

    # Sync STRATEGY.md and MEMORY.md from sandbox to bot_files DB
    await _sync_bot_docs_from_sandbox(db, bot)

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
    strategy_md: str,
    memory_md: str,
    open_positions: list[dict],
    closed_positions: list[dict],
    kalshi_client,
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

        summary = f"Scanned {len(markets)} markets. Strategy: {strategy_md[:100] if strategy_md else 'None set'}"

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


async def ensure_bot_directory(user_id: str, bot_directory: str) -> None:
    """Create the bot's sandbox directory and migrate any legacy files from /home/user/.

    Creates the bot's per-bot directory in the sandbox. Removes any leftover
    shared-location files (/home/user/MEMORY.md, etc.) to prevent old bot
    data from contaminating new bots.
    """
    from modules.tools.implementations.code_execution import (
        get_or_create_sandbox,
    )

    try:
        envs = {}
        entry = await get_or_create_sandbox(user_id, envs)
        sbx = entry.sbx

        bot_home = f"/home/user/{bot_directory}"

        # Create bot directory. Remove any leftover shared-location files
        # to prevent old bot data from contaminating new bots.
        script = (
            "import os, shutil\n"
            f"bot_home = {bot_home!r}\n"
            "os.makedirs(bot_home + '/memory', exist_ok=True)\n"
            "# Remove leftover shared-location files — each bot starts clean\n"
            "for fname in ['STRATEGY.md', 'MEMORY.md', 'AGENTS.md']:\n"
            "    old = f'/home/user/{fname}'\n"
            "    if os.path.exists(old):\n"
            "        os.remove(old)\n"
            "# Clean up legacy shared memory dir\n"
            "old_mem = '/home/user/memory'\n"
            "if os.path.exists(old_mem) and old_mem != bot_home + '/memory':\n"
            "    shutil.rmtree(old_mem, ignore_errors=True)\n"
        )
        script_path = "/home/user/.finch_migrate_bot_dir.py"
        await sbx.files.write(script_path, script)
        await sbx.commands.run(f"python3 {script_path}", cwd="/home/user", timeout=15)
    except Exception as e:
        logger.debug(f"Bot directory setup/migration failed (non-fatal): {e}")


async def _sync_bot_docs_from_sandbox(db: AsyncSession, bot: TradingBot) -> None:
    """Read STRATEGY.md, MEMORY.md, and daily logs from sandbox and sync to bot_files DB."""
    from modules.tools.implementations.code_execution import (
        read_sandbox_file,
        get_or_create_sandbox,
    )

    bot_dir = bot.directory or f"bots/{str(bot.id)[:8]}"

    # Sync strategy + memory
    for filename, file_type in [("STRATEGY.md", "strategy"), ("MEMORY.md", "memory")]:
        try:
            raw = await read_sandbox_file(bot.user_id, f"{bot_dir}/{filename}")
            if raw:
                content = raw.decode("utf-8", errors="replace").strip()
                if content:
                    await upsert_bot_file(db, bot.id, filename, content=content, file_type=file_type)
        except Exception as e:
            logger.debug(f"Sync {filename} failed (non-fatal): {e}")

    # Sync daily logs (memory/*.md)
    try:
        entry = await get_or_create_sandbox(bot.user_id, {})
        sbx = entry.sbx
        memory_dir = f"/home/user/{bot_dir}/memory"
        result = await sbx.commands.run(
            f"ls {memory_dir}/*.md 2>/dev/null || true",
            timeout=10,
        )
        if result.stdout:
            for line in result.stdout.strip().split("\n"):
                line = line.strip()
                if not line or not line.endswith(".md"):
                    continue
                filename = line.split("/")[-1]
                try:
                    raw = await read_sandbox_file(bot.user_id, f"{bot_dir}/memory/{filename}")
                    if raw:
                        content = raw.decode("utf-8", errors="replace").strip()
                        if content:
                            await upsert_bot_file(db, bot.id, filename, content=content, file_type="log")
                except Exception as e:
                    logger.debug(f"Sync log {filename} failed (non-fatal): {e}")
    except Exception as e:
        logger.debug(f"Sync daily logs failed (non-fatal): {e}")


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
    kalshi_client,
) -> None:
    """Process action dicts from the bot's tick.

    Capital enforcement:
    - Capital check happens BEFORE any exchange API call
    - Risk limits are checked against actual cost_usd (not just requested amount)
    - Sell verifies position is still open to prevent double-credit
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
            has_funds = await deduct_capital_for_position(db, bot, cost_usd)
            if not has_funds:
                logger.warning(f"BLOCKED: insufficient capital for ${cost_usd:.2f} order on {market}")
                continue

            # Log the trade attempt
            trade_log = await create_trade_log(
                db=db, bot=bot, action="buy", market=market, side=side,
                price=entry_price, quantity=quantity, cost_usd=cost_usd,
                execution_id=execution_id,
                status="executed",
            )

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
                    paper=False,
                )
                await update_trade_log_status(db, trade_log, trade_log.status, position_id=str(position.id))
            except Exception as e:
                logger.error(f"Failed to create position for {market}: {e}")
                # Refund capital if position creation failed
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
                execution_id=execution_id,
                status="executed",
            )
            trade_log.position_id = pos.id

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
                # Return cost + realized P&L to capital balance
                realized_pnl = pos.realized_pnl_usd or 0.0
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
        lambda: kalshi_lib.post("/portfolio/orders", body={"ticker": market, "side": side, "action": action, "count": count, "type": "market"}),
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
