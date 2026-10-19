"""
Theses API — the user's own reason for owning/watching each stock, kept in the
memory store (see services.theses), plus a story check of today's move against it.

- GET    /theses                    -> all of the user's theses
- GET    /theses/{symbol}           -> one thesis, or null if none
- PUT    /theses/{symbol}           -> create/rewrite (story log is kept)
- DELETE /theses/{symbol}
- POST   /theses/{symbol}/log       -> append a dated development to the story log
- GET    /theses/{symbol}/check     -> today's move judged against the thesis
"""
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from auth.dependencies import get_current_user_id
from services import theses
from services.monitoring.cache import TTLCache
from utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/theses", tags=["theses"])

# Per-user story checks are LLM calls; a re-open within a few minutes shouldn't
# pay twice. Keyed by (user, symbol) and dropped when the thesis is edited.
_check_cache = TTLCache(ttl_seconds=20 * 60, max_entries=2000)


class ThesisBody(BaseModel):
    why: str = Field(..., min_length=1, max_length=2000)
    breaks: Optional[str] = Field(None, max_length=2000)
    stance: Literal["own", "watch", "avoid"] = "own"


class StoryEntry(BaseModel):
    note: str = Field(..., min_length=1, max_length=400)
    verdict: Literal["noise", "news", "narrative_shift"] = "news"
    status: Optional[Literal["intact", "weakened", "broken"]] = None
    source: Optional[str] = Field(None, max_length=200)


def _sym(symbol: str) -> str:
    try:
        return theses.normalize_symbol(symbol)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("")
async def list_theses(user_id: str = Depends(get_current_user_id)):
    return {"theses": await theses.list_theses(user_id)}


@router.get("/{symbol}")
async def get_thesis(symbol: str, user_id: str = Depends(get_current_user_id)):
    """The thesis, or null — not having written one yet is a normal state,
    not an error (every stock page asks)."""
    return await theses.get_thesis(user_id, _sym(symbol))


@router.put("/{symbol}")
async def put_thesis(symbol: str, body: ThesisBody, user_id: str = Depends(get_current_user_id)):
    sym = _sym(symbol)
    try:
        t = await theses.save_thesis(user_id, sym, body.why, body.breaks, body.stance)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    _check_cache.set((user_id, sym), None)
    return t


@router.delete("/{symbol}")
async def delete_thesis(symbol: str, user_id: str = Depends(get_current_user_id)):
    sym = _sym(symbol)
    _check_cache.set((user_id, sym), None)
    return {"deleted": await theses.delete_thesis(user_id, sym)}


@router.post("/{symbol}/log")
async def append_story(symbol: str, entry: StoryEntry, user_id: str = Depends(get_current_user_id)):
    t = await theses.log_story(user_id, _sym(symbol), entry.note, entry.verdict, entry.status, entry.source)
    if not t:
        raise HTTPException(status_code=404, detail="No thesis for this symbol — save one first")
    return t


@router.get("/{symbol}/check")
async def check_thesis(symbol: str, user_id: str = Depends(get_current_user_id)):
    """Today's move (Finch's shared read) judged against this user's thesis.

    Routine noise is answered without an LLM call — a normal day never moves a
    thesis. Returns {read, check} where check is {status, reason} or null.
    """
    from services.move_explainer import explain_move

    sym = _sym(symbol)
    t = await theses.get_thesis(user_id, sym)
    if not t:
        raise HTTPException(status_code=404, detail="No thesis for this symbol")

    cached = _check_cache.get((user_id, sym))
    if cached:
        return cached

    try:
        read = await explain_move(sym)
    except ValueError:
        raise HTTPException(status_code=404, detail=f"No quote found for {sym}")

    if read.get("verdict") == "noise":
        check = {"status": "intact", "reason": "A routine day for this stock — nothing here touches your thesis."}
    else:
        check = await theses.check_against_thesis(user_id, t, theses.describe_read(read))

    result = {"read": read, "check": check}
    _check_cache.set((user_id, sym), result)
    return result
