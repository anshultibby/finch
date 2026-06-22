"""
CASParser routes — Indian demat portfolio via CDSL OTP fetch.

Connect flow:
  POST /casparser/connect/initiate   → sends OTP to user's CDSL-registered mobile
  POST /casparser/connect/verify     → verifies OTP, parses latest eCAS, stores holdings

Portfolio:
  GET  /casparser/status/{user_id}   → connection + last-sync info
  GET  /casparser/portfolio/{user_id}→ cached demat holdings
  POST /casparser/portfolio/{user_id}/refresh → re-fetch with stored credentials (new OTP flow)

Disconnect:
  DELETE /casparser/{user_id}        → remove connection + cached data
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from datetime import datetime, timezone
import uuid

from core.database import get_async_db
from auth.dependencies import get_current_user_id, verify_user_access
from models.brokerage import CASParserConnection
from schemas.casparser import (
    CASParserInitiateRequest,
    CASParserVerifyRequest,
    CASParserStatusResponse,
    CASParserPortfolioResponse,
    CASParserDematAccount,
    CASParserHolding,
)
from modules.tools.clients.casparser import casparser_client, CASParserError
from services.encryption import encryption_service
from utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/casparser", tags=["casparser"])


# ---------------------------------------------------------------------------
# Connect
# ---------------------------------------------------------------------------

@router.post("/connect/initiate")
async def initiate_connect(
    body: CASParserInitiateRequest,
    authenticated_user_id: str = Depends(get_current_user_id),
):
    """
    Step 1: Call CASParser which logs into the CDSL portal and triggers an OTP
    SMS to the mobile number registered with that demat account.
    Returns a session_id the frontend must pass back in /verify.
    """
    try:
        session_id = await casparser_client.initiate_otp(body.pan, body.bo_id, body.dob)
    except CASParserError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("CASParser initiate_otp unexpected error")
        raise HTTPException(status_code=500, detail="Failed to initiate OTP. Try again.")

    return {"session_id": session_id, "message": "OTP sent to CDSL-registered mobile"}


@router.post("/connect/verify")
async def verify_connect(
    body: CASParserVerifyRequest,
    authenticated_user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_async_db),
):
    """
    Step 2: Verify OTP → download + parse latest eCAS PDF → store holdings.
    We also re-encrypt and persist PAN/DOB so we can refresh later.
    The frontend must pass back the pan/bo_id/dob from step 1 alongside the session_id + OTP.
    """
    pan = body.pan
    bo_id = body.bo_id
    dob = body.dob

    try:
        files = await casparser_client.verify_otp(body.session_id, body.otp)
    except CASParserError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception:
        logger.exception("CASParser verify_otp unexpected error")
        raise HTTPException(status_code=500, detail="OTP verification failed. Try again.")

    if not files:
        raise HTTPException(status_code=400, detail="No CAS files returned. Ensure the BO ID is correct.")

    # Parse the most recent file
    latest = files[0]
    pdf_url = latest.get("url") or latest.get("download_url") or latest.get("link")
    if not pdf_url:
        raise HTTPException(status_code=500, detail=f"Unexpected file format: {latest}")

    try:
        parsed = await casparser_client.parse_cas(pdf_url, pan)
    except CASParserError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception:
        logger.exception("CASParser parse_cas unexpected error")
        raise HTTPException(status_code=500, detail="Failed to parse CAS file.")

    investor_name, demat_accounts, _ = casparser_client.extract_holdings(parsed)

    pan_enc = encryption_service.encrypt(pan.upper())
    dob_enc = encryption_service.encrypt(dob)

    # Upsert the connection row
    result = await db.execute(
        select(CASParserConnection).where(CASParserConnection.user_id == authenticated_user_id)
    )
    conn = result.scalar_one_or_none()

    holdings_data = {"demat_accounts": demat_accounts, "raw": parsed}
    now = datetime.now(timezone.utc)

    if conn:
        conn.pan_encrypted = pan_enc
        conn.bo_id = bo_id
        conn.dob_encrypted = dob_enc
        conn.investor_name = investor_name or conn.investor_name
        conn.is_connected = True
        conn.holdings_cache = holdings_data
        conn.holdings_fetched_at = now
    else:
        conn = CASParserConnection(
            id=uuid.uuid4(),
            user_id=authenticated_user_id,
            pan_encrypted=pan_enc,
            bo_id=bo_id,
            dob_encrypted=dob_enc,
            investor_name=investor_name,
            is_connected=True,
            holdings_cache=holdings_data,
            holdings_fetched_at=now,
        )
        db.add(conn)

    await db.commit()

    total = sum(len(a.get("holdings", [])) for a in demat_accounts)
    return {
        "is_connected": True,
        "investor_name": investor_name,
        "total_holdings": total,
        "accounts_found": len(demat_accounts),
        "holdings_fetched_at": now.isoformat(),
    }


# ---------------------------------------------------------------------------
# Status
# ---------------------------------------------------------------------------

@router.get("/status/{user_id}", response_model=CASParserStatusResponse)
async def get_status(
    user_id: str,
    authenticated_user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_async_db),
):
    await verify_user_access(user_id, authenticated_user_id)

    result = await db.execute(
        select(CASParserConnection).where(CASParserConnection.user_id == user_id)
    )
    conn = result.scalar_one_or_none()

    if not conn or not conn.is_connected:
        return CASParserStatusResponse(is_connected=False)

    pan = encryption_service.decrypt(conn.pan_encrypted)
    total = 0
    if conn.holdings_cache:
        accounts = conn.holdings_cache.get("demat_accounts") or []
        total = sum(len(a.get("holdings", [])) for a in accounts)

    return CASParserStatusResponse(
        is_connected=True,
        investor_name=conn.investor_name,
        pan_last4=pan[-4:] if pan else None,
        holdings_fetched_at=conn.holdings_fetched_at,
        total_holdings=total,
    )


# ---------------------------------------------------------------------------
# Portfolio
# ---------------------------------------------------------------------------

@router.get("/portfolio/{user_id}", response_model=CASParserPortfolioResponse)
async def get_portfolio(
    user_id: str,
    authenticated_user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_async_db),
):
    await verify_user_access(user_id, authenticated_user_id)

    result = await db.execute(
        select(CASParserConnection).where(CASParserConnection.user_id == user_id)
    )
    conn = result.scalar_one_or_none()

    if not conn or not conn.is_connected or not conn.holdings_cache:
        return CASParserPortfolioResponse(is_connected=False)

    raw_accounts = conn.holdings_cache.get("demat_accounts") or []
    accounts = [
        CASParserDematAccount(
            dp_name=a["dp_name"],
            dp_id=a["dp_id"],
            client_id=a["client_id"],
            holdings=[
                CASParserHolding(
                    isin=h["isin"],
                    name=h["name"],
                    quantity=h["quantity"],
                    face_value=h.get("face_value"),
                )
                for h in a.get("holdings", [])
            ],
        )
        for a in raw_accounts
    ]
    total = sum(len(a.holdings) for a in accounts)

    return CASParserPortfolioResponse(
        is_connected=True,
        investor_name=conn.investor_name,
        accounts=accounts,
        holdings_fetched_at=conn.holdings_fetched_at,
        total_holdings=total,
    )


# ---------------------------------------------------------------------------
# Refresh (re-run OTP flow with stored credentials)
# ---------------------------------------------------------------------------

@router.post("/portfolio/{user_id}/refresh")
async def refresh_portfolio(
    user_id: str,
    authenticated_user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_async_db),
):
    """
    Initiates a fresh OTP flow using stored credentials.
    The frontend must complete the OTP step via /connect/verify.
    Returns a new session_id.
    """
    await verify_user_access(user_id, authenticated_user_id)

    result = await db.execute(
        select(CASParserConnection).where(CASParserConnection.user_id == user_id)
    )
    conn = result.scalar_one_or_none()
    if not conn:
        raise HTTPException(status_code=404, detail="No CDSL connection found. Please connect first.")

    pan = encryption_service.decrypt(conn.pan_encrypted)
    dob = encryption_service.decrypt(conn.dob_encrypted)

    try:
        session_id = await casparser_client.initiate_otp(pan, conn.bo_id, dob)
    except CASParserError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {"session_id": session_id, "message": "OTP sent to CDSL-registered mobile"}


# ---------------------------------------------------------------------------
# Disconnect
# ---------------------------------------------------------------------------

@router.delete("/{user_id}")
async def disconnect(
    user_id: str,
    authenticated_user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_async_db),
):
    await verify_user_access(user_id, authenticated_user_id)

    await db.execute(
        delete(CASParserConnection).where(CASParserConnection.user_id == user_id)
    )
    await db.commit()
    return {"success": True}
