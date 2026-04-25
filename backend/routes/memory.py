"""
Cognee memory API — stock knowledge graph seeding, retrieval, and MEMORY.md history.

- Seed: frontend triggers on stock page open
- Remember/recall/improve: sandbox skill scripts + frontend
- Current/history: frontend memory viewer tab
"""
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel
from typing import Optional

from auth.dependencies import get_current_user_id
from utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/memory", tags=["memory"])


class RememberRequest(BaseModel):
    ticker: str
    content: str
    session_id: Optional[str] = None


class RecallRequest(BaseModel):
    query: str
    ticker: Optional[str] = None
    session_id: Optional[str] = None
    top_k: int = 5


class ImproveRequest(BaseModel):
    ticker: Optional[str] = None
    session_ids: Optional[list[str]] = None


# ---------------------------------------------------------------------------
# Stock knowledge seeding
# ---------------------------------------------------------------------------

@router.post("/seed/{symbol}")
async def seed_stock(
    symbol: str,
    background_tasks: BackgroundTasks,
    user_id: str = Depends(get_current_user_id),
    days: int = 60,
):
    from services.cognee_memory import seed_stock as _seed, _seeded_tickers
    symbol = symbol.upper().strip()
    if symbol in _seeded_tickers:
        return {"status": "already_seeded", "ticker": symbol}
    background_tasks.add_task(_seed, symbol, days)
    return {"status": "seeding", "ticker": symbol}


@router.post("/remember")
async def remember(
    req: RememberRequest,
    user_id: str = Depends(get_current_user_id),
):
    from services.cognee_memory import remember_stock
    result = await remember_stock(req.ticker, req.content, req.session_id)
    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error", "Unknown error"))
    return result


@router.post("/recall")
async def recall(
    req: RecallRequest,
    user_id: str = Depends(get_current_user_id),
):
    from services.cognee_memory import recall_stock
    results = await recall_stock(req.query, req.ticker, req.session_id, req.top_k)
    return {"results": results}


@router.post("/improve")
async def improve(
    req: ImproveRequest,
    user_id: str = Depends(get_current_user_id),
):
    from services.cognee_memory import improve_memory
    result = await improve_memory(req.ticker, req.session_ids)
    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error", "Unknown error"))
    return result


@router.get("/status/{symbol}")
async def seed_status(
    symbol: str,
    user_id: str = Depends(get_current_user_id),
):
    from services.cognee_memory import _seeded_tickers
    symbol = symbol.upper().strip()
    return {"ticker": symbol, "seeded": symbol in _seeded_tickers}


@router.get("/datasets")
async def list_datasets(
    user_id: str = Depends(get_current_user_id),
):
    import cognee
    try:
        datasets = await cognee.datasets.list_datasets()
        return {"datasets": [ds.name for ds in datasets] if datasets else []}
    except Exception as e:
        return {"datasets": [], "error": str(e)}


# ---------------------------------------------------------------------------
# MEMORY.md viewer endpoints
# ---------------------------------------------------------------------------

@router.get("/current")
async def get_current_memory(
    user_id: str = Depends(get_current_user_id),
):
    from services.cognee_memory import get_current_memory as _get
    content = await _get(user_id)
    return {"content": content}


@router.get("/history")
async def get_memory_history(
    user_id: str = Depends(get_current_user_id),
    limit: int = 20,
):
    from services.cognee_memory import get_memory_history as _get
    snapshots = await _get(user_id, limit=limit)
    return {"snapshots": snapshots}
