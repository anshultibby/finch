"""
CRUD operations for Trading Bots.
"""
from typing import Optional, List
from datetime import datetime, timezone
import uuid
import logging
import re

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func

from models.db import TradingBot, BotExecution, BotFile, BotPosition
from models.bots import (
    CreateBotRequest,
    UpdateBotRequest,
    BotConfig,
    BotStats,
    ExitConfig,
)

logger = logging.getLogger(__name__)


# ============================================================================
# Bot CRUD
# ============================================================================

def _slugify(name: str) -> str:
    """Convert bot name to a filesystem-safe directory name."""
    slug = re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-')
    return slug or 'bot'


async def create_bot(
    db: AsyncSession,
    user_id: str,
    request: CreateBotRequest,
) -> TradingBot:
    """Create a new trading bot."""
    bot_id = str(uuid.uuid4())
    directory = f"bots/{_slugify(request.name)}-{bot_id[:8]}"

    config = BotConfig(platform=request.platform).model_dump(mode="json")

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
        select(BotFile).where(BotFile.bot_id == bot_id).with_for_update()
    )
    await db.execute(
        BotFile.__table__.delete().where(BotFile.bot_id == bot_id)
    )
    await db.execute(
        BotPosition.__table__.delete().where(BotPosition.bot_id == bot_id)
    )
    await db.execute(
        BotExecution.__table__.delete().where(BotExecution.bot_id == bot_id)
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

    data = dict(execution.data or {})
    data["completed_at"] = datetime.now(timezone.utc).isoformat()
    data["duration_ms"] = int(
        (datetime.now(timezone.utc) - execution.started_at).total_seconds() * 1000
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
    query = (
        select(BotPosition)
        .where(BotPosition.bot_id == bot_id)
        .order_by(BotPosition.entry_time.desc())
        .limit(limit)
    )
    if status:
        query = query.where(BotPosition.status == status)
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
    position.unrealized_pnl_usd = (current_price - position.entry_price) * position.quantity
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
    position.realized_pnl_usd = (exit_price - position.entry_price) * position.quantity
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


async def recompute_bot_pnl(db: AsyncSession, bot_id: str) -> None:
    """Recompute P&L stats from positions and persist into bot.stats."""
    bot = await get_bot(db, bot_id)
    if not bot:
        return

    r = await db.execute(
        select(func.sum(BotPosition.realized_pnl_usd)).where(
            BotPosition.bot_id == bot_id,
            BotPosition.status == "closed",
        )
    )
    total_profit = float(r.scalar() or 0.0)

    r = await db.execute(
        select(func.sum(BotPosition.cost_usd)).where(
            BotPosition.bot_id == bot_id,
        )
    )
    total_spent = float(r.scalar() or 0.0)

    r = await db.execute(
        select(func.sum(BotPosition.unrealized_pnl_usd)).where(
            BotPosition.bot_id == bot_id,
            BotPosition.status == "open",
        )
    )
    open_unrealized = float(r.scalar() or 0.0)

    stats = dict(bot.stats or {})
    stats["total_profit_usd"] = total_profit
    stats["total_spent_usd"] = total_spent
    stats["open_unrealized_pnl"] = open_unrealized
    bot.stats = stats
    await db.commit()
    logger.info(
        f"Recomputed P&L for bot {bot_id}: "
        f"realized=${total_profit:.2f} spent=${total_spent:.2f} unrealized=${open_unrealized:.2f}"
    )
