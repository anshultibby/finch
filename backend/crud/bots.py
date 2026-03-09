"""
CRUD operations for Trading Bots.
"""
from typing import Optional, List
from datetime import datetime, timezone
import uuid
import logging
import re

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func, case

from models.bot import TradingBot, BotExecution, BotFile, BotPosition, TradeLog, BotWakeup
from schemas.bots import (
    CreateBotRequest,
    UpdateBotRequest,
    BotConfig,
    BotStats,
    ExitConfig,
    CapitalConfig,
)

logger = logging.getLogger(__name__)


# ============================================================================
# Bot CRUD
# ============================================================================

def _slugify(name: str) -> str:
    """Convert bot name to a filesystem-safe directory name."""
    slug = re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-')
    return slug or 'bot'


def _compute_pnl(side: Optional[str], entry_price: float, current_price: float, quantity: float) -> float:
    """Compute P&L accounting for position side (no side inverts the price movement)."""
    if side == "no":
        return (entry_price - current_price) * quantity
    return (current_price - entry_price) * quantity


def _get_capital_balance(bot: TradingBot) -> tuple[dict, dict, float]:
    """Extract config, capital dict, and current balance from a bot. Returns (config, capital, balance)."""
    config = dict(bot.config or {})
    capital = dict(config.get("capital") or {})
    balance = capital.get("balance_usd")
    if balance is None:
        balance = capital.get("amount_usd") or 0.0
    return config, capital, balance


async def create_bot(
    db: AsyncSession,
    user_id: str,
    request: CreateBotRequest,
) -> TradingBot:
    """Create a new trading bot."""
    bot_id = str(uuid.uuid4())
    directory = f"bots/{_slugify(request.name)}-{bot_id[:8]}"

    bot_config = BotConfig(platform=request.platform)
    if request.capital_amount and request.capital_amount > 0:
        bot_config.capital = CapitalConfig(
            amount_usd=request.capital_amount,
            balance_usd=request.capital_amount,
        )
    config = bot_config.model_dump(mode="json")

    bot = TradingBot(
        id=bot_id,
        user_id=user_id,
        name=request.name,
        icon=request.icon,
        directory=directory,
        enabled=False,
        approved=False,
        config=config,
        stats=BotStats().model_dump(mode="json"),
    )
    db.add(bot)
    await db.commit()
    await db.refresh(bot)
    logger.info(f"Created bot '{request.name}' (id={bot_id}) for user {user_id}")
    return bot


async def get_bot(
    db: AsyncSession,
    bot_id: str,
    user_id: Optional[str] = None,
) -> Optional[TradingBot]:
    query = select(TradingBot).where(TradingBot.id == bot_id)
    if user_id:
        query = query.where(TradingBot.user_id == user_id)
    result = await db.execute(query)
    return result.scalars().first()


async def list_bots(
    db: AsyncSession,
    user_id: str,
    enabled_only: bool = False,
) -> List[TradingBot]:
    query = select(TradingBot).where(TradingBot.user_id == user_id)
    if enabled_only:
        query = query.where(TradingBot.enabled == True)
    query = query.order_by(TradingBot.created_at.desc())
    result = await db.execute(query)
    return list(result.scalars().all())


async def update_bot(
    db: AsyncSession,
    bot_id: str,
    user_id: str,
    request: UpdateBotRequest,
) -> Optional[TradingBot]:
    bot = await get_bot(db, bot_id, user_id)
    if not bot:
        return None

    if request.name is not None:
        bot.name = request.name
    if request.icon is not None:
        bot.icon = request.icon
    if request.enabled is not None:
        if request.enabled and not bot.approved:
            raise ValueError("Cannot enable bot that is not approved")
        bot.enabled = request.enabled

    config = dict(bot.config or {})
    if request.mandate is not None:
        config["mandate"] = request.mandate
    if request.schedule is not None:
        config["schedule"] = request.schedule
    if request.schedule_description is not None:
        config["schedule_description"] = request.schedule_description
    if request.risk_limits is not None:
        config["risk_limits"] = request.risk_limits.model_dump(mode="json")
    if request.capital is not None:
        existing_capital = config.get("capital") or {}
        updated = {**existing_capital, **request.capital.model_dump(mode="json", exclude_none=True)}
        # Auto-initialize balance when amount_usd is first set and balance doesn't exist
        if "amount_usd" in updated and "balance_usd" not in existing_capital:
            updated["balance_usd"] = updated["amount_usd"]
        config["capital"] = updated
    if request.paper_mode is not None:
        config["paper_mode"] = request.paper_mode
    if request.model is not None:
        config["model"] = request.model
    bot.config = config

    await db.commit()
    await db.refresh(bot)
    logger.info(f"Updated bot {bot_id}")
    return bot


async def approve_bot(
    db: AsyncSession,
    bot_id: str,
    user_id: str,
) -> Optional[TradingBot]:
    bot = await get_bot(db, bot_id, user_id)
    if not bot:
        return None

    bot.approved = True
    config = dict(bot.config or {})
    config["approved_at"] = datetime.now(timezone.utc).isoformat()
    bot.config = config

    await db.commit()
    await db.refresh(bot)
    logger.info(f"Approved bot {bot_id}")
    return bot


async def delete_bot(
    db: AsyncSession,
    bot_id: str,
    user_id: str,
) -> bool:
    bot = await get_bot(db, bot_id, user_id)
    if not bot:
        return False

    # Delete related records
    await db.execute(
        BotFile.__table__.delete().where(BotFile.bot_id == bot_id)
    )
    await db.execute(
        BotPosition.__table__.delete().where(BotPosition.bot_id == bot_id)
    )
    await db.execute(
        BotExecution.__table__.delete().where(BotExecution.bot_id == bot_id)
    )
    await db.execute(
        TradeLog.__table__.delete().where(TradeLog.bot_id == bot_id)
    )

    await db.delete(bot)
    await db.commit()
    logger.info(f"Deleted bot {bot_id}")
    return True


async def update_bot_stats(
    db: AsyncSession,
    bot_id: str,
    execution: BotExecution,
) -> None:
    bot = await get_bot(db, bot_id)
    if not bot:
        return

    stats = dict(bot.stats or {})
    data = execution.data or {}

    stats["total_runs"] = stats.get("total_runs", 0) + 1
    if execution.status == "success":
        stats["successful_runs"] = stats.get("successful_runs", 0) + 1
    else:
        stats["failed_runs"] = stats.get("failed_runs", 0) + 1

    stats["last_run_at"] = execution.started_at.isoformat()
    stats["last_run_status"] = execution.status
    stats["last_run_summary"] = data.get("summary")

    bot.stats = stats
    await db.commit()


# ============================================================================
# BotFile CRUD
# ============================================================================

async def get_bot_files(
    db: AsyncSession,
    bot_id: str,
    file_type: Optional[str] = None,
) -> List[BotFile]:
    query = select(BotFile).where(BotFile.bot_id == bot_id)
    if file_type:
        query = query.where(BotFile.file_type == file_type)
    result = await db.execute(query)
    return list(result.scalars().all())


async def upsert_bot_file(
    db: AsyncSession,
    bot_id: str,
    filename: str,
    content: str,
    file_type: str = "code",
) -> BotFile:
    """Create or update a bot file."""
    result = await db.execute(
        select(BotFile).where(
            BotFile.bot_id == bot_id,
            BotFile.filename == filename,
        )
    )
    existing = result.scalar_one_or_none()
    if existing:
        existing.content = content
        existing.file_type = file_type
        await db.commit()
        await db.refresh(existing)
        return existing

    file = BotFile(
        id=str(uuid.uuid4()),
        bot_id=bot_id,
        filename=filename,
        content=content,
        file_type=file_type,
    )
    db.add(file)
    await db.commit()
    await db.refresh(file)
    return file


# ============================================================================
# Execution CRUD
# ============================================================================

async def create_execution(
    db: AsyncSession,
    bot: TradingBot,
    trigger: str,
) -> BotExecution:
    execution = BotExecution(
        id=uuid.uuid4(),
        bot_id=bot.id,
        user_id=bot.user_id,
        status="running",
        started_at=datetime.now(timezone.utc),
        data={"trigger": trigger, "logs": [], "actions": []},
    )
    db.add(execution)
    await db.commit()
    await db.refresh(execution)
    return execution


async def complete_execution(
    db: AsyncSession,
    execution: BotExecution,
    status: str,
    result: Optional[dict] = None,
    error: Optional[str] = None,
    summary: Optional[str] = None,
    actions: Optional[list] = None,
    logs: Optional[List[str]] = None,
) -> BotExecution:
    execution.status = status

    now = datetime.now(timezone.utc)
    data = dict(execution.data or {})
    data["completed_at"] = now.isoformat()
    data["duration_ms"] = int(
        (now - execution.started_at).total_seconds() * 1000
    )

    if result is not None:
        data["result"] = result
    if error is not None:
        data["error"] = error
    if summary is not None:
        data["summary"] = summary
    if actions is not None:
        data["actions"] = actions
    if logs is not None:
        data["logs"] = logs

    execution.data = data
    await db.commit()
    await db.refresh(execution)

    await update_bot_stats(db, execution.bot_id, execution)
    await recompute_bot_pnl(db, execution.bot_id)
    return execution


async def list_executions(
    db: AsyncSession,
    bot_id: str,
    limit: int = 20,
) -> List[BotExecution]:
    query = (
        select(BotExecution)
        .where(BotExecution.bot_id == bot_id)
        .order_by(BotExecution.started_at.desc())
        .limit(limit)
    )
    result = await db.execute(query)
    return list(result.scalars().all())


async def get_execution(
    db: AsyncSession,
    execution_id: str,
    user_id: Optional[str] = None,
) -> Optional[BotExecution]:
    query = select(BotExecution).where(BotExecution.id == execution_id)
    if user_id:
        query = query.where(BotExecution.user_id == user_id)
    result = await db.execute(query)
    return result.scalars().first()


async def get_due_bots(db: AsyncSession) -> List[TradingBot]:
    """Return all enabled+approved bots (scheduler handles timing)."""
    query = select(TradingBot).where(
        and_(TradingBot.enabled == True, TradingBot.approved == True)
    )
    result = await db.execute(query)
    return list(result.scalars().all())


# ============================================================================
# Position CRUD
# ============================================================================

async def create_position(
    db: AsyncSession,
    bot: TradingBot,
    market: str,
    side: str,
    entry_price: float,
    quantity: float,
    cost_usd: float,
    exit_config: ExitConfig,
    entered_via: Optional[str] = None,
    paper: bool = False,
) -> BotPosition:
    now = datetime.now(timezone.utc)
    initial_history = [{"t": now.isoformat(), "price": entry_price}]
    position = BotPosition(
        bot_id=bot.id,
        user_id=bot.user_id,
        market=market,
        platform=bot.config.get("platform", "kalshi"),
        side=side,
        entry_price=entry_price,
        entry_time=now,
        quantity=quantity,
        cost_usd=cost_usd,
        status="open",
        exit_config=exit_config.model_dump(mode="json"),
        entered_via=entered_via,
        paper=paper,
        price_history=initial_history,
    )
    db.add(position)
    await db.commit()
    await db.refresh(position)
    logger.info(f"Created position {position.id} for bot {bot.id}: {market} {side}")
    return position


async def count_open_positions_batch(
    db: AsyncSession,
    bot_ids: List[str],
) -> dict[str, int]:
    result = await db.execute(
        select(BotPosition.bot_id, func.count().label("cnt"))
        .where(
            BotPosition.bot_id.in_(bot_ids),
            BotPosition.status == "open",
        )
        .group_by(BotPosition.bot_id)
    )
    return {row.bot_id: row.cnt for row in result}


async def get_open_positions(
    db: AsyncSession,
    bot_id: str,
) -> List[BotPosition]:
    result = await db.execute(
        select(BotPosition).where(
            BotPosition.bot_id == bot_id,
            BotPosition.status == "open",
        ).order_by(BotPosition.entry_time.desc())
    )
    return list(result.scalars().all())


async def list_positions(
    db: AsyncSession,
    bot_id: str,
    status: Optional[str] = None,
    limit: int = 50,
) -> List[BotPosition]:
    query = select(BotPosition).where(BotPosition.bot_id == bot_id)
    if status:
        query = query.where(BotPosition.status == status)
    query = query.order_by(BotPosition.entry_time.desc()).limit(limit)
    result = await db.execute(query)
    return list(result.scalars().all())


async def get_position(
    db: AsyncSession,
    position_id: str,
    user_id: Optional[str] = None,
) -> Optional[BotPosition]:
    query = select(BotPosition).where(BotPosition.id == position_id)
    if user_id:
        query = query.where(BotPosition.user_id == user_id)
    result = await db.execute(query)
    return result.scalars().first()


async def update_position_price(
    db: AsyncSession,
    position: BotPosition,
    current_price: float,
) -> BotPosition:
    now = datetime.now(timezone.utc)
    position.current_price = current_price
    position.unrealized_pnl_usd = _compute_pnl(position.side, position.entry_price, current_price, position.quantity)
    position.last_priced_at = now

    history = list(position.price_history or [])
    history.append({"t": now.isoformat(), "price": current_price})
    if len(history) > 500:
        history = history[-500:]
    position.price_history = history

    await db.commit()
    await db.refresh(position)
    return position


async def update_position_monitor_note(
    db: AsyncSession,
    position: BotPosition,
    note: str,
) -> BotPosition:
    position.monitor_note = note
    await db.commit()
    await db.refresh(position)
    return position


async def close_position(
    db: AsyncSession,
    position: BotPosition,
    exit_price: float,
    close_reason: str,
    closed_via: Optional[str] = None,
) -> BotPosition:
    now = datetime.now(timezone.utc)
    position.status = "closed"
    position.exit_price = exit_price
    position.realized_pnl_usd = _compute_pnl(position.side, position.entry_price, exit_price, position.quantity)
    position.close_reason = close_reason
    position.closed_at = now
    position.closed_via = closed_via
    position.unrealized_pnl_usd = None
    position.current_price = exit_price

    history = list(position.price_history or [])
    history.append({"t": now.isoformat(), "price": exit_price})
    position.price_history = history
    await db.commit()
    await db.refresh(position)
    logger.info(
        f"Closed position {position.id}: {position.market} reason={close_reason} "
        f"pnl=${position.realized_pnl_usd:.2f}"
    )
    return position


def get_capital_balance(bot: TradingBot) -> Optional[float]:
    """Get the bot's current capital balance, or None if not set."""
    _, _, balance = _get_capital_balance(bot)
    return balance


async def adjust_capital(
    db: AsyncSession,
    bot_id: str,
    user_id: str,
    delta: float,
    reason: str = "manual",
) -> Optional[TradingBot]:
    """Add or withdraw capital. delta > 0 = deposit, delta < 0 = withdraw."""
    bot = await get_bot(db, bot_id, user_id)
    if not bot:
        return None

    config, capital, current = _get_capital_balance(bot)
    new_balance = current + delta
    if new_balance < 0:
        raise ValueError(f"Insufficient balance: ${current:.2f} available, tried to withdraw ${abs(delta):.2f}")

    capital["balance_usd"] = new_balance
    config["capital"] = capital
    bot.config = config
    await db.commit()
    await db.refresh(bot)
    logger.info(f"Capital {reason}: bot {bot_id} {'+' if delta >= 0 else ''}{delta:.2f} -> ${new_balance:.2f}")
    return bot


async def deduct_capital_for_position(db: AsyncSession, bot: TradingBot, cost_usd: float) -> bool:
    """Deduct capital when opening a position. Returns False if insufficient funds."""
    config, capital, current = _get_capital_balance(bot)

    if cost_usd > current:
        return False

    capital["balance_usd"] = current - cost_usd
    config["capital"] = capital
    bot.config = config
    await db.commit()
    return True


async def credit_capital_for_close(db: AsyncSession, bot: TradingBot, cost_usd: float, realized_pnl: float) -> None:
    """Return cost + P&L to capital when closing a position."""
    config, capital, current = _get_capital_balance(bot)

    capital["balance_usd"] = current + cost_usd + realized_pnl
    config["capital"] = capital
    bot.config = config
    await db.commit()


# ============================================================================
# Trade Log CRUD
# ============================================================================

async def create_trade_log(
    db: AsyncSession,
    bot: TradingBot,
    action: str,
    market: str,
    side: str,
    price: float,
    quantity: int,
    cost_usd: float,
    execution_id: Optional[str] = None,
    dry_run: bool = False,
    status: str = "executed",
    approval_token: Optional[str] = None,
    expires_at=None,
) -> TradeLog:
    """Create a trade log entry for every buy/sell attempt."""
    log = TradeLog(
        bot_id=bot.id,
        user_id=bot.user_id,
        execution_id=execution_id,
        action=action,
        market=market,
        platform=bot.config.get("platform", "kalshi"),
        side=side,
        price=price,
        quantity=quantity,
        cost_usd=cost_usd,
        status=status,
        approval_token=approval_token,
        dry_run=dry_run,
        expires_at=expires_at,
    )
    db.add(log)
    await db.commit()
    await db.refresh(log)
    logger.info(f"Trade log: {action} {market} {side} x{quantity} @ {price}c = ${cost_usd:.2f} [{status}]")
    return log


async def update_trade_log_status(
    db: AsyncSession,
    trade_log: TradeLog,
    status: str,
    error: Optional[str] = None,
    position_id: Optional[str] = None,
    order_response: Optional[dict] = None,
) -> TradeLog:
    """Update a trade log's status after execution or approval."""
    trade_log.status = status
    if error:
        trade_log.error = error
    if position_id:
        trade_log.position_id = position_id
    if order_response:
        trade_log.order_response = order_response
    if status == "approved":
        trade_log.approved_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(trade_log)
    return trade_log


async def get_trade_log_by_token(
    db: AsyncSession,
    token: str,
) -> Optional[TradeLog]:
    """Find a trade log by its approval token."""
    result = await db.execute(
        select(TradeLog).where(TradeLog.approval_token == token)
    )
    return result.scalars().first()


async def list_trade_logs(
    db: AsyncSession,
    bot_id: Optional[str] = None,
    user_id: Optional[str] = None,
    limit: int = 50,
) -> List[TradeLog]:
    """List trade logs, optionally filtered by bot or user."""
    query = select(TradeLog).order_by(TradeLog.created_at.desc()).limit(limit)
    if bot_id:
        query = query.where(TradeLog.bot_id == bot_id)
    if user_id:
        query = query.where(TradeLog.user_id == user_id)
    result = await db.execute(query)
    return list(result.scalars().all())


async def recompute_bot_pnl(db: AsyncSession, bot_id: str) -> None:
    """Recompute P&L stats from positions and persist into bot.stats."""
    bot = await get_bot(db, bot_id)
    if not bot:
        return

    is_paper = BotPosition.paper == True
    is_live = BotPosition.paper == False
    is_closed = BotPosition.status == "closed"
    is_open = BotPosition.status == "open"

    r = await db.execute(
        select(
            # Live stats
            func.sum(case((and_(is_closed, is_live), BotPosition.realized_pnl_usd), else_=0)),
            func.sum(case((is_live, BotPosition.cost_usd), else_=0)),
            func.sum(case((and_(is_open, is_live), BotPosition.unrealized_pnl_usd), else_=0)),
            # Paper stats
            func.sum(case((and_(is_closed, is_paper), BotPosition.realized_pnl_usd), else_=0)),
            func.sum(case((and_(is_open, is_paper), BotPosition.unrealized_pnl_usd), else_=0)),
        ).where(BotPosition.bot_id == bot_id)
    )
    row = r.one()
    total_profit = float(row[0] or 0.0)
    total_spent = float(row[1] or 0.0)
    open_unrealized = float(row[2] or 0.0)
    paper_profit = float(row[3] or 0.0)
    paper_unrealized = float(row[4] or 0.0)

    stats = dict(bot.stats or {})
    stats["total_profit_usd"] = total_profit
    stats["total_spent_usd"] = total_spent
    stats["open_unrealized_pnl"] = open_unrealized
    stats["paper_profit_usd"] = paper_profit
    stats["paper_unrealized_pnl"] = paper_unrealized
    bot.stats = stats
    await db.commit()
    logger.info(
        f"Recomputed P&L for bot {bot_id}: "
        f"realized=${total_profit:.2f} spent=${total_spent:.2f} unrealized=${open_unrealized:.2f} "
        f"paper_realized=${paper_profit:.2f} paper_unrealized=${paper_unrealized:.2f}"
    )


# ============================================================================
# Wakeup CRUD
# ============================================================================

async def create_wakeup(
    db: AsyncSession,
    bot_id: str,
    user_id: str,
    trigger_at: datetime,
    reason: str,
    trigger_type: str = "custom",
    context: Optional[dict] = None,
) -> BotWakeup:
    """Schedule a future wakeup for a bot."""
    wakeup = BotWakeup(
        bot_id=bot_id,
        user_id=user_id,
        trigger_at=trigger_at,
        trigger_type=trigger_type,
        reason=reason,
        context=context or {},
        status="pending",
    )
    db.add(wakeup)
    await db.commit()
    await db.refresh(wakeup)
    logger.info(f"Scheduled wakeup for bot {bot_id} at {trigger_at}: {reason[:80]}")
    return wakeup


async def get_due_wakeups(db: AsyncSession) -> List[BotWakeup]:
    """Get all pending wakeups whose trigger_at has passed."""
    now = datetime.now(timezone.utc)
    result = await db.execute(
        select(BotWakeup).where(
            BotWakeup.status == "pending",
            BotWakeup.trigger_at <= now,
        ).order_by(BotWakeup.trigger_at.asc())
    )
    return list(result.scalars().all())


async def list_wakeups(
    db: AsyncSession,
    bot_id: str,
    status: Optional[str] = "pending",
    limit: int = 20,
) -> List[BotWakeup]:
    """List wakeups for a bot."""
    query = (
        select(BotWakeup)
        .where(BotWakeup.bot_id == bot_id)
        .order_by(BotWakeup.trigger_at.asc())
        .limit(limit)
    )
    if status:
        query = query.where(BotWakeup.status == status)
    result = await db.execute(query)
    return list(result.scalars().all())


async def cancel_wakeup(
    db: AsyncSession,
    wakeup_id: str,
    user_id: Optional[str] = None,
) -> Optional[BotWakeup]:
    """Cancel a pending wakeup."""
    query = select(BotWakeup).where(BotWakeup.id == wakeup_id, BotWakeup.status == "pending")
    if user_id:
        query = query.where(BotWakeup.user_id == user_id)
    result = await db.execute(query)
    wakeup = result.scalars().first()
    if not wakeup:
        return None
    wakeup.status = "cancelled"
    await db.commit()
    await db.refresh(wakeup)
    return wakeup


async def mark_wakeup_triggered(
    db: AsyncSession,
    wakeup: BotWakeup,
    chat_id: str,
) -> BotWakeup:
    """Mark a wakeup as triggered and link it to the chat it created."""
    wakeup.status = "triggered"
    wakeup.triggered_at = datetime.now(timezone.utc)
    wakeup.chat_id = chat_id
    await db.commit()
    await db.refresh(wakeup)
    return wakeup
