"""
Trade ideas API — the agent proposes, the user decides, a sweep scores.

Ideas are scored whether or not they were approved, so GET /ideas returns the
scorecard alongside the list. That's the number that says whether the bot is
actually any good.
"""
from fastapi import APIRouter, Depends, HTTPException

from auth.dependencies import get_current_user_id
from schemas.trade_ideas import Idea, IdeaCreate, IdeaDecision, IdeaList
from services import trade_ideas
from utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/ideas", tags=["ideas"])


@router.get("", response_model=IdeaList)
async def list_ideas(limit: int = 100, user_id: str = Depends(get_current_user_id)):
    return await trade_ideas.list_ideas(user_id, limit=min(limit, 500))


@router.post("", response_model=Idea)
async def propose_idea(body: IdeaCreate, user_id: str = Depends(get_current_user_id)):
    try:
        return await trade_ideas.propose(user_id, body)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.post("/{idea_id}/decide", response_model=Idea)
async def decide_idea(idea_id: str, body: IdeaDecision,
                      user_id: str = Depends(get_current_user_id)):
    try:
        idea = await trade_ideas.decide(user_id, idea_id, body)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    if not idea:
        raise HTTPException(status_code=404, detail="Idea not found")
    return idea
