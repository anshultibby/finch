"""
API routes for Trading Bots.
"""
import time as _time_module
from typing import Optional, List, Dict, Any, Tuple
from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.ext.asyncio import AsyncSession

_candle_cache: Dict[Tuple, Tuple[float, Any]] = {}
_CANDLE_TTL = 300

from database import get_async_db
from crud import bots as crud
from crud.bots import get_open_positions, list_positions, get_position, close_position, count_open_positions_batch
from models.bots import (
    CreateBotRequest,
    UpdateBotRequest,
    BotResponse,
    BotDetailResponse,
    BotPositionResponse,
    ExecutionResponse,
    ExecutionDetailResponse,
    RunBotRequest,
    RunBotResponse,
    BotStats,
    CapitalConfig,
    RiskLimits,
    ExitConfig,
    ExecutionAction,
)

router = APIRouter(prefix="/bots", tags=["bots"])


def _get_user_id(x_user_id: str = Header(..., alias="X-User-ID")) -> str:
    return x_user_id


def _bot_to_response(bot, open_positions_count: int = 0) -> BotResponse:
    config = bot.config or {}
    stats = bot.stats or {}
    return BotResponse(
        id=bot.id,
        name=bot.name,
        icon=bot.icon,
        platform=config.get("platform", "kalshi"),
        enabled=bot.enabled,
        approved=bot.approved,
        schedule_description=config.get("schedule_description"),
        total_runs=stats.get("total_runs", 0),
        last_run_at=stats.get("last_run_at"),
        last_run_status=stats.get("last_run_status"),
        last_run_summary=stats.get("last_run_summary"),
        open_positions_count=open_positions_count,
        total_profit_usd=float(stats.get("total_profit_usd", 0.0)),
        open_unrealized_pnl=float(stats.get("open_unrealized_pnl", 0.0)),
        created_at=bot.created_at,
        updated_at=bot.updated_at,
    )


async def _bot_to_detail_response(bot, db: AsyncSession) -> BotDetailResponse:
    config = bot.config or {}
    stats_dict = bot.stats or {}

    files = await crud.get_bot_files(db, bot.id)
    active_positions = await get_open_positions(db, bot.id)
    recent_closed = await list_positions(db, bot.id, status="closed", limit=20)

    capital = None
    if config.get("capital"):
        try:
            capital = CapitalConfig(**config["capital"])
        except Exception:
            pass

    risk_limits = None
    if config.get("risk_limits"):
        try:
            risk_limits = RiskLimits(**config["risk_limits"])
        except Exception:
            pass

    return BotDetailResponse(
        id=bot.id,
        name=bot.name,
        icon=bot.icon,
        platform=config.get("platform", "kalshi"),
        enabled=bot.enabled,
        approved=bot.approved,
        schedule_description=config.get("schedule_description"),
        total_runs=stats_dict.get("total_runs", 0),
        last_run_at=stats_dict.get("last_run_at"),
        last_run_status=stats_dict.get("last_run_status"),
        last_run_summary=stats_dict.get("last_run_summary"),
        created_at=bot.created_at,
        updated_at=bot.updated_at,
        mandate=config.get("mandate", ""),
        schedule=config.get("schedule"),
        risk_limits=risk_limits,
        capital=capital,
        paper_mode=config.get("paper_mode", True),
        model=config.get("model", "claude-sonnet-4-20250514"),
        directory=bot.directory,
        total_profit_usd=float(stats_dict.get("total_profit_usd", 0.0)),
        open_unrealized_pnl=float(stats_dict.get("open_unrealized_pnl", 0.0)),
        stats=BotStats(**stats_dict),
        files=[{"filename": f.filename, "content": f.content, "file_type": f.file_type} for f in files],
        positions=[_position_to_response(p) for p in active_positions],
        closed_positions=[_position_to_response(p) for p in recent_closed],
    )


def _position_to_response(position) -> BotPositionResponse:
    exit_cfg = position.exit_config or {}
    try:
        exit_config = ExitConfig(**exit_cfg)
    except Exception:
        exit_config = ExitConfig()

    return BotPositionResponse(
        id=str(position.id),
        bot_id=position.bot_id,
        market=position.market,
        platform=position.platform,
        side=position.side,
        entry_price=position.entry_price,
        entry_time=position.entry_time,
        quantity=position.quantity,
        cost_usd=position.cost_usd,
        status=position.status,
        exit_config=exit_config,
        entered_via=str(position.entered_via) if position.entered_via else None,
        closed_via=str(position.closed_via) if position.closed_via else None,
        closed_at=position.closed_at,
        exit_price=position.exit_price,
        realized_pnl_usd=position.realized_pnl_usd,
        close_reason=position.close_reason,
        current_price=position.current_price,
        unrealized_pnl_usd=position.unrealized_pnl_usd,
        last_priced_at=position.last_priced_at,
        price_history=position.price_history or [],
        market_title=position.market_title,
        event_ticker=position.event_ticker,
        monitor_note=position.monitor_note,
        created_at=position.created_at,
        updated_at=position.updated_at,
    )


def _execution_to_response(execution) -> ExecutionResponse:
    data = execution.data or {}
    return ExecutionResponse(
        id=str(execution.id),
        bot_id=execution.bot_id,
        status=execution.status,
        started_at=execution.started_at,
        completed_at=data.get("completed_at"),
        trigger=data.get("trigger", "unknown"),
        summary=data.get("summary"),
        error=data.get("error"),
        actions_count=len(data.get("actions", [])),
    )


def _execution_to_detail_response(execution) -> ExecutionDetailResponse:
    data = execution.data or {}
    actions = [ExecutionAction(**a) for a in data.get("actions", [])]
    return ExecutionDetailResponse(
        id=str(execution.id),
        bot_id=execution.bot_id,
        status=execution.status,
        started_at=execution.started_at,
        completed_at=data.get("completed_at"),
        trigger=data.get("trigger", "unknown"),
        summary=data.get("summary"),
        error=data.get("error"),
        actions_count=len(actions),
        duration_ms=data.get("duration_ms"),
        logs=data.get("logs", []),
        actions=actions,
        result=data.get("result"),
    )


# ============================================================================
# Bot CRUD endpoints
# ============================================================================

@router.post("", response_model=BotDetailResponse)
async def create_bot(
    request: CreateBotRequest,
    user_id: str = Depends(_get_user_id),
    db: AsyncSession = Depends(get_async_db),
):
    bot = await crud.create_bot(db, user_id, request)
    return await _bot_to_detail_response(bot, db)


@router.get("", response_model=List[BotResponse])
async def list_bots(
    enabled_only: bool = False,
    user_id: str = Depends(_get_user_id),
    db: AsyncSession = Depends(get_async_db),
):
    bots = await crud.list_bots(db, user_id, enabled_only)
    bot_ids = [b.id for b in bots]
    counts = await count_open_positions_batch(db, bot_ids) if bot_ids else {}
    return [_bot_to_response(b, counts.get(b.id, 0)) for b in bots]


@router.get("/{bot_id}", response_model=BotDetailResponse)
async def get_bot(
    bot_id: str,
    user_id: str = Depends(_get_user_id),
    db: AsyncSession = Depends(get_async_db),
):
    bot = await crud.get_bot(db, bot_id, user_id)
    if not bot:
        raise HTTPException(status_code=404, detail="Bot not found")
    return await _bot_to_detail_response(bot, db)


@router.patch("/{bot_id}", response_model=BotDetailResponse)
async def update_bot(
    bot_id: str,
    request: UpdateBotRequest,
    user_id: str = Depends(_get_user_id),
    db: AsyncSession = Depends(get_async_db),
):
    try:
        bot = await crud.update_bot(db, bot_id, user_id, request)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if not bot:
        raise HTTPException(status_code=404, detail="Bot not found")
    return await _bot_to_detail_response(bot, db)


@router.delete("/{bot_id}")
async def delete_bot(
    bot_id: str,
    user_id: str = Depends(_get_user_id),
    db: AsyncSession = Depends(get_async_db),
):
    success = await crud.delete_bot(db, bot_id, user_id)
    if not success:
        raise HTTPException(status_code=404, detail="Bot not found")
    return {"success": True}


@router.post("/{bot_id}/approve", response_model=BotDetailResponse)
async def approve_bot(
    bot_id: str,
    user_id: str = Depends(_get_user_id),
    db: AsyncSession = Depends(get_async_db),
):
    bot = await crud.approve_bot(db, bot_id, user_id)
    if not bot:
        raise HTTPException(status_code=404, detail="Bot not found")
    return await _bot_to_detail_response(bot, db)


# ============================================================================
# Bot Execution
# ============================================================================

@router.post("/{bot_id}/run", response_model=RunBotResponse)
async def run_bot(
    bot_id: str,
    request: RunBotRequest = RunBotRequest(),
    user_id: str = Depends(_get_user_id),
    db: AsyncSession = Depends(get_async_db),
):
    """Manually trigger a bot tick."""
    bot = await crud.get_bot(db, bot_id, user_id)
    if not bot:
        raise HTTPException(status_code=404, detail="Bot not found")

    if not request.dry_run and not bot.approved:
        raise HTTPException(
            status_code=400,
            detail="Bot must be approved before live execution",
        )

    from modules.bots.executor import execute_bot_tick

    trigger = "dry_run" if request.dry_run else "manual"
    execution = await execute_bot_tick(
        db=db,
        bot=bot,
        trigger=trigger,
        dry_run=request.dry_run,
    )

    data = execution.data or {}
    actions = [ExecutionAction(**a) for a in data.get("actions", [])]

    return RunBotResponse(
        execution_id=str(execution.id),
        status=execution.status,
        summary=data.get("summary"),
        actions=actions,
        error=data.get("error"),
    )


@router.get("/{bot_id}/executions", response_model=List[ExecutionResponse])
async def list_bot_executions(
    bot_id: str,
    limit: int = 20,
    user_id: str = Depends(_get_user_id),
    db: AsyncSession = Depends(get_async_db),
):
    bot = await crud.get_bot(db, bot_id, user_id)
    if not bot:
        raise HTTPException(status_code=404, detail="Bot not found")
    executions = await crud.list_executions(db, bot_id, limit)
    return [_execution_to_response(e) for e in executions]


@router.get("/{bot_id}/executions/{execution_id}", response_model=ExecutionDetailResponse)
async def get_bot_execution(
    bot_id: str,
    execution_id: str,
    user_id: str = Depends(_get_user_id),
    db: AsyncSession = Depends(get_async_db),
):
    execution = await crud.get_execution(db, execution_id, user_id)
    if not execution or execution.bot_id != bot_id:
        raise HTTPException(status_code=404, detail="Execution not found")
    return _execution_to_detail_response(execution)


# ============================================================================
# Positions
# ============================================================================

@router.get("/{bot_id}/positions", response_model=List[BotPositionResponse])
async def list_bot_positions(
    bot_id: str,
    status: Optional[str] = None,
    limit: int = 50,
    user_id: str = Depends(_get_user_id),
    db: AsyncSession = Depends(get_async_db),
):
    bot = await crud.get_bot(db, bot_id, user_id)
    if not bot:
        raise HTTPException(status_code=404, detail="Bot not found")
    positions = await list_positions(db, bot_id, status=status, limit=limit)
    return [_position_to_response(p) for p in positions]


@router.get("/{bot_id}/positions/{position_id}/market")
async def get_position_market(
    bot_id: str,
    position_id: str,
    user_id: str = Depends(_get_user_id),
    db: AsyncSession = Depends(get_async_db),
):
    bot = await crud.get_bot(db, bot_id, user_id)
    if not bot:
        raise HTTPException(status_code=404, detail="Bot not found")

    position = await get_position(db, position_id, user_id)
    if not position or position.bot_id != bot_id:
        raise HTTPException(status_code=404, detail="Position not found")

    if position.platform != "kalshi":
        raise HTTPException(status_code=400, detail="Market data only available for Kalshi positions")

    from services.api_keys import ApiKeyService
    svc = ApiKeyService(db, user_id)
    creds = await svc.get_kalshi_credentials()
    if not creds:
        raise HTTPException(status_code=400, detail="Kalshi credentials not configured")

    import asyncio
    from skills.kalshi_trading.scripts._client import KalshiHTTPClient

    api_key_id = creds["api_key_id"].get()
    private_key = creds["private_key"].get().replace("\\n", "\n")
    client = KalshiHTTPClient(api_key_id, private_key)

    try:
        market = await asyncio.get_event_loop().run_in_executor(
            None, lambda: client.get(f"/markets/{position.market}")
        )
        return {"market": market.get("market", market)}
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Kalshi API error: {str(e)}")


@router.get("/{bot_id}/positions/{position_id}/candlesticks")
async def get_position_candlesticks(
    bot_id: str,
    position_id: str,
    period_interval: int = 60,
    hours: int = 168,
    user_id: str = Depends(_get_user_id),
    db: AsyncSession = Depends(get_async_db),
):
    from utils.logger import get_logger
    logger = get_logger(__name__)

    bot = await crud.get_bot(db, bot_id, user_id)
    if not bot:
        raise HTTPException(status_code=404, detail="Bot not found")

    position = await get_position(db, position_id, user_id)
    if not position or position.bot_id != bot_id:
        raise HTTPException(status_code=404, detail="Position not found")

    if position.platform != "kalshi":
        raise HTTPException(status_code=400, detail="Candlesticks only available for Kalshi positions")

    from services.api_keys import ApiKeyService
    svc = ApiKeyService(db, user_id)
    creds = await svc.get_kalshi_credentials()
    if not creds:
        raise HTTPException(status_code=400, detail="Kalshi credentials not configured")

    import asyncio
    import re
    from datetime import datetime, timezone as tz
    from skills.kalshi_trading.scripts._client import KalshiHTTPClient

    api_key_id = creds["api_key_id"].get()
    private_key = creds["private_key"].get().replace("\\n", "\n")
    client = KalshiHTTPClient(api_key_id, private_key)

    event_ticker = position.event_ticker or position.market
    parts = event_ticker.split("-")
    series_parts = []
    for i, part in enumerate(parts):
        if re.match(r"^\d{2}", part):
            break
        if i > 0 and len(part) > 10 and not part.isalpha():
            break
        series_parts.append(part)
    series_ticker = ("-".join(series_parts) if series_parts else parts[0]).upper()

    cache_key = (position.market, period_interval, hours)
    now = _time_module.time()
    cached = _candle_cache.get(cache_key)
    if cached and (now - cached[0]) < _CANDLE_TTL:
        return cached[1]

    end_ts = int(now)
    start_ts = end_ts - (hours * 3600)

    try:
        data = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: client.get(
                f"/series/{series_ticker}/markets/{position.market}/candlesticks",
                params={"start_ts": start_ts, "end_ts": end_ts, "period_interval": period_interval},
            ),
        )
        candles = data.get("candlesticks", [])
        history = []
        for c in candles:
            ts = c.get("end_period_ts")
            if not ts:
                continue
            yes_bid = c.get("yes_bid") or {}
            yes_ask = c.get("yes_ask") or {}
            price_ohlc = c.get("price") or {}

            def mid(field: str):
                b, a = yes_bid.get(field), yes_ask.get(field)
                if b is not None and a is not None:
                    return (b + a) / 2
                return price_ohlc.get(field)

            o, h, l, cl = mid("open"), mid("high"), mid("low"), mid("close")
            if cl is None:
                continue
            history.append({
                "t": datetime.fromtimestamp(ts, tz=tz.utc).isoformat(),
                "open": o if o is not None else cl,
                "high": h if h is not None else cl,
                "low": l if l is not None else cl,
                "close": cl,
            })
        result = {"history": history, "series_ticker": series_ticker}
        _candle_cache[cache_key] = (_time_module.time(), result)
        return result
    except Exception as e:
        logger.error(f"Candlesticks failed for {position.market}: {e}")
        return {"history": [], "series_ticker": series_ticker, "error": str(e)}


@router.post("/{bot_id}/positions/{position_id}/close", response_model=BotPositionResponse)
async def close_bot_position(
    bot_id: str,
    position_id: str,
    user_id: str = Depends(_get_user_id),
    db: AsyncSession = Depends(get_async_db),
):
    bot = await crud.get_bot(db, bot_id, user_id)
    if not bot:
        raise HTTPException(status_code=404, detail="Bot not found")

    position = await get_position(db, position_id, user_id)
    if not position or position.bot_id != bot_id:
        raise HTTPException(status_code=404, detail="Position not found")
    if position.status == "closed":
        raise HTTPException(status_code=400, detail="Position is already closed")

    exit_price = position.current_price or position.entry_price
    closed = await close_position(
        db=db,
        position=position,
        exit_price=exit_price,
        close_reason="manual",
    )
    await crud.recompute_bot_pnl(db, bot_id)
    return _position_to_response(closed)


# ============================================================================
# Bot Chats
# ============================================================================

@router.get("/{bot_id}/chats")
async def list_bot_chats(
    bot_id: str,
    user_id: str = Depends(_get_user_id),
    db: AsyncSession = Depends(get_async_db),
):
    """List all chats scoped to this bot."""
    from sqlalchemy import select
    from models.db import Chat

    bot = await crud.get_bot(db, bot_id, user_id)
    if not bot:
        raise HTTPException(status_code=404, detail="Bot not found")

    result = await db.execute(
        select(Chat)
        .where(Chat.bot_id == bot_id, Chat.user_id == user_id)
        .order_by(Chat.updated_at.desc())
    )
    chats = result.scalars().all()
    return [
        {
            "chat_id": c.chat_id,
            "title": c.title,
            "icon": c.icon,
            "created_at": c.created_at.isoformat() if c.created_at else None,
            "updated_at": c.updated_at.isoformat() if c.updated_at else None,
        }
        for c in chats
    ]


@router.post("/{bot_id}/chats")
async def create_bot_chat(
    bot_id: str,
    user_id: str = Depends(_get_user_id),
    db: AsyncSession = Depends(get_async_db),
):
    """Create a new chat scoped to this bot."""
    import uuid
    from models.db import Chat

    bot = await crud.get_bot(db, bot_id, user_id)
    if not bot:
        raise HTTPException(status_code=404, detail="Bot not found")

    chat_id = str(uuid.uuid4())
    chat = Chat(
        chat_id=chat_id,
        user_id=user_id,
        bot_id=bot_id,
        title=None,
    )
    db.add(chat)
    await db.commit()
    await db.refresh(chat)

    return {
        "chat_id": chat.chat_id,
        "bot_id": bot_id,
        "title": chat.title,
        "created_at": chat.created_at.isoformat() if chat.created_at else None,
    }
