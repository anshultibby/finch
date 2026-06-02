"""
Robinhood agentic-trading connection routes.

Implements the user-facing half of the MCP OAuth flow: kick off authorization,
receive the browser redirect, expose connection status + the live agentic
account. Token storage/refresh and MCP calls live in services/robinhood_auth.py.
"""
from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi.responses import RedirectResponse
from pydantic import BaseModel

from core.config import settings
from auth.dependencies import get_current_user_id, verify_user_access
from services import robinhood_auth
from utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/robinhood", tags=["robinhood"])


class ConnectRequest(BaseModel):
    user_id: str


class ConnectResponse(BaseModel):
    success: bool
    authorize_url: str | None = None
    message: str | None = None


@router.post("/connect", response_model=ConnectResponse)
async def connect(
    request: ConnectRequest,
    authenticated_user_id: str = Depends(get_current_user_id),
):
    """Begin the Robinhood OAuth flow. Returns the URL the frontend should open
    so the user can log in, consent, and fund their agentic account."""
    await verify_user_access(request.user_id, authenticated_user_id)
    try:
        url = await robinhood_auth.begin_connect(request.user_id)
        return ConnectResponse(success=True, authorize_url=url)
    except Exception as e:
        logger.error(f"Robinhood connect failed for {request.user_id}: {e}")
        raise HTTPException(status_code=502, detail="Failed to start Robinhood connection")


@router.get("/callback")
async def callback(
    code: str = Query(default=""),
    state: str = Query(default=""),
    error: str = Query(default=""),
):
    """OAuth redirect target. The browser lands here after Robinhood consent; we
    exchange the code, persist the connection, then bounce back into the app."""
    base = settings.FRONTEND_URL.rstrip("/")
    if error or not code or not state:
        return RedirectResponse(url=f"{base}/portfolio?robinhood=error")
    try:
        user_id = await robinhood_auth.complete_callback(code, state)
        status = "connected" if user_id else "error"
    except Exception as e:
        logger.error(f"Robinhood callback failed: {e}")
        status = "error"
    return RedirectResponse(url=f"{base}/portfolio?robinhood={status}")


@router.get("/status/{user_id}")
async def status(
    user_id: str,
    authenticated_user_id: str = Depends(get_current_user_id),
):
    """Whether this user has a live Robinhood connection."""
    await verify_user_access(user_id, authenticated_user_id)
    return {"is_connected": await robinhood_auth.is_connected(user_id)}


@router.get("/accounts/{user_id}")
async def accounts(
    user_id: str,
    authenticated_user_id: str = Depends(get_current_user_id),
):
    """Live view of the connected agentic account (number, buying power, balance)."""
    await verify_user_access(user_id, authenticated_user_id)
    if not await robinhood_auth.is_connected(user_id):
        return {"is_connected": False, "accounts": [], "agentic_account": None, "portfolio": None}
    try:
        data = await robinhood_auth.get_connected_accounts(user_id)
        return {"is_connected": True, **data}
    except Exception as e:
        logger.error(f"Robinhood accounts fetch failed for {user_id}: {e}")
        raise HTTPException(status_code=502, detail="Failed to load Robinhood account")


@router.delete("/disconnect/{user_id}")
async def disconnect(
    user_id: str,
    authenticated_user_id: str = Depends(get_current_user_id),
):
    """Clear the stored Robinhood connection."""
    await verify_user_access(user_id, authenticated_user_id)
    await robinhood_auth.disconnect(user_id)
    return {"success": True, "message": "Disconnected"}
