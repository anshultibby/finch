"""
SnapTrade connection management routes
"""
from fastapi import APIRouter, HTTPException, Depends

from schemas import (
    SnapTradeConnectionRequest,
    SnapTradeConnectionResponse,
    SnapTradeCallbackRequest,
    SnapTradeStatusResponse
)
from modules.tools.clients import snaptrade_tools
from auth.dependencies import get_current_user_id, verify_user_access

router = APIRouter(prefix="/snaptrade", tags=["snaptrade"])


@router.post("/connect", response_model=SnapTradeConnectionResponse)
async def initiate_connection(
    request: SnapTradeConnectionRequest,
    authenticated_user_id: str = Depends(get_current_user_id),
):
    """
    Initiate SnapTrade OAuth connection flow

    Returns a redirect URI that the frontend should open to allow
    the user to connect their brokerage account via SnapTrade.
    """
    await verify_user_access(request.user_id, authenticated_user_id)
    try:
        result = await snaptrade_tools.get_login_redirect_uri(
            user_id=request.user_id,
            redirect_uri=request.redirect_uri
        )
        
        if result["success"]:
            return SnapTradeConnectionResponse(
                success=True,
                message="Connection URL generated successfully",
                redirect_uri=result["redirect_uri"]
            )
        else:
            return SnapTradeConnectionResponse(
                success=False,
                message=result.get("message", "Failed to generate connection URL")
            )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/callback", response_model=SnapTradeStatusResponse)
async def handle_callback(
    request: SnapTradeCallbackRequest,
    authenticated_user_id: str = Depends(get_current_user_id),
):
    """
    Handle callback after user successfully connects via SnapTrade Portal

    Verifies the connection and fetches connected account information.
    """
    await verify_user_access(request.user_id, authenticated_user_id)
    try:
        result = await snaptrade_tools.handle_connection_callback(
            user_id=request.user_id
        )
        
        if result["success"]:
            return SnapTradeStatusResponse(
                success=True,
                message=result["message"],
                is_connected=True,
                account_count=result.get("account_count"),
                brokerages=result.get("brokerages")
            )
        else:
            return SnapTradeStatusResponse(
                success=False,
                message=result["message"],
                is_connected=False
            )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status/{user_id}", response_model=SnapTradeStatusResponse)
async def check_connection_status(
    user_id: str,
    authenticated_user_id: str = Depends(get_current_user_id),
):
    """
    Check if user has an active SnapTrade connection
    """
    await verify_user_access(user_id, authenticated_user_id)
    is_connected = await snaptrade_tools.has_active_connection(user_id)

    return SnapTradeStatusResponse(
        success=True,
        message="Connected" if is_connected else "Not connected",
        is_connected=is_connected
    )


@router.delete("/disconnect/{user_id}")
async def disconnect(
    user_id: str,
    authenticated_user_id: str = Depends(get_current_user_id),
):
    """
    Disconnect from SnapTrade and clear user session
    """
    await verify_user_access(user_id, authenticated_user_id)
    snaptrade_tools.disconnect(user_id)

    return {
        "success": True,
        "message": "Disconnected successfully"
    }


@router.delete("/reset/{user_id}")
async def reset_portfolio(
    user_id: str,
    authenticated_user_id: str = Depends(get_current_user_id),
):
    """
    Fully reset a user's SnapTrade connection.
    Deletes the user from SnapTrade API, removes all brokerage accounts
    and the snaptrade_users record from DB so they can reconnect fresh.
    """
    await verify_user_access(user_id, authenticated_user_id)
    result = await snaptrade_tools.reset_user(user_id)
    return result


@router.get("/accounts/{user_id}")
async def get_accounts(
    user_id: str,
    authenticated_user_id: str = Depends(get_current_user_id),
):
    """
    Get list of user's connected brokerage accounts
    """
    await verify_user_access(user_id, authenticated_user_id)
    result = await snaptrade_tools.get_connected_accounts(user_id)
    return result


@router.get("/brokerages")
async def get_brokerages():
    """
    Get list of available brokerages that can be connected
    """
    result = snaptrade_tools.get_available_brokerages()  # sync, no DB
    return result


@router.post("/connect/broker")
async def connect_broker(
    request: dict,
    authenticated_user_id: str = Depends(get_current_user_id),
):
    """
    Initiate connection to a specific brokerage

    Request body:
    {
        "user_id": str,
        "redirect_uri": str,
        "broker_id": str (optional - if not provided, shows all brokers)
    }
    """
    user_id = request.get("user_id")
    redirect_uri = request.get("redirect_uri")
    broker_id = request.get("broker_id")

    if not user_id or not redirect_uri:
        raise HTTPException(status_code=400, detail="user_id and redirect_uri are required")

    await verify_user_access(user_id, authenticated_user_id)
    
    result = await snaptrade_tools.get_login_redirect_uri_for_broker(
        user_id=user_id,
        redirect_uri=redirect_uri,
        broker_id=broker_id
    )
    
    if result["success"]:
        return SnapTradeConnectionResponse(
            success=True,
            message="Connection URL generated successfully",
            redirect_uri=result["redirect_uri"]
        )
    else:
        return SnapTradeConnectionResponse(
            success=False,
            message=result.get("message", "Failed to generate connection URL")
        )


@router.delete("/accounts/{user_id}/{account_id}")
async def disconnect_account(
    user_id: str,
    account_id: str,
    authenticated_user_id: str = Depends(get_current_user_id),
):
    """
    Disconnect a specific brokerage account
    """
    await verify_user_access(user_id, authenticated_user_id)
    result = await snaptrade_tools.disconnect_account(user_id, account_id)
    return result


@router.patch("/accounts/{user_id}/{account_id}/visibility")
async def toggle_account_visibility(
    user_id: str,
    account_id: str,
    request: dict,
    authenticated_user_id: str = Depends(get_current_user_id),
):
    """
    Toggle account visibility (include/exclude from portfolio view)

    Request body:
    {
        "is_visible": bool
    }
    """
    await verify_user_access(user_id, authenticated_user_id)
    from core.database import get_db_session
    from crud import brokerage_account as brokerage_crud

    is_visible = request.get("is_visible", True)

    async with get_db_session() as db:
        account = await brokerage_crud.get_account_by_account_id_async(db, user_id, account_id)
        if not account:
            return {
                "success": False,
                "message": "Account not found"
            }

        account.is_active = is_visible

    return {
        "success": True,
        "message": f"Account visibility {'enabled' if is_visible else 'disabled'}"
    }


@router.get("/portfolio/{user_id}")
async def get_portfolio(
    user_id: str,
    authenticated_user_id: str = Depends(get_current_user_id),
):
    """
    Get user's complete portfolio with holdings, accounts, and performance metrics

    Returns:
    - accounts: List of all connected accounts with balances
    - holdings: Aggregated positions across all accounts
    - total_value: Total portfolio value
    - performance: Gain/loss metrics
    """
    await verify_user_access(user_id, authenticated_user_id)
    import uuid as uuid_mod
    from datetime import datetime, timezone, timedelta
    from sqlalchemy import select, delete
    from core.database import get_db_session

    cache_ttl = timedelta(minutes=5)

    # Check DB cache
    try:
        from models.brokerage import PortfolioHoldingsCache
        async with get_db_session() as db:
            row = (await db.execute(
                select(PortfolioHoldingsCache).where(
                    PortfolioHoldingsCache.user_id == user_id,
                )
            )).scalars().first()

            if row and (datetime.now(timezone.utc) - row.computed_at) < cache_ttl:
                data = row.portfolio_data
                data["cached"] = True
                return data
    except Exception:
        PortfolioHoldingsCache = None

    # Cache miss or stale — fetch from SnapTrade
    result = await snaptrade_tools.get_portfolio(user_id)

    if result.get("success") and PortfolioHoldingsCache is not None:
        try:
            async with get_db_session() as db:
                await db.execute(
                    delete(PortfolioHoldingsCache).where(
                        PortfolioHoldingsCache.user_id == user_id,
                    )
                )
                db.add(PortfolioHoldingsCache(
                    id=uuid_mod.uuid4(),
                    user_id=user_id,
                    portfolio_data=result,
                    computed_at=datetime.now(timezone.utc),
                ))
        except Exception:
            pass

    return result


@router.get("/portfolio/{user_id}/holdings")
async def get_portfolio_holdings(
    user_id: str,
    authenticated_user_id: str = Depends(get_current_user_id),
):
    """
    Get detailed holdings with position-level data
    """
    await verify_user_access(user_id, authenticated_user_id)
    result = await snaptrade_tools.get_portfolio(user_id)
    return result


@router.get("/portfolio/{user_id}/performance")
async def get_portfolio_performance(
    user_id: str,
    authenticated_user_id: str = Depends(get_current_user_id),
):
    """
    Get portfolio performance metrics including gains, losses, and returns
    """
    await verify_user_access(user_id, authenticated_user_id)
    portfolio = await snaptrade_tools.get_portfolio(user_id)
    
    if not portfolio.get("success"):
        return portfolio
    
    # Calculate performance metrics from holdings
    holdings_csv = portfolio.get("holdings_csv", "")
    if not holdings_csv:
        return {
            "success": True,
            "total_gain_loss": 0,
            "total_gain_loss_percent": 0,
            "total_value": portfolio.get("total_value", 0),
            "total_cost": 0
        }
    
    # Parse CSV to calculate totals
    import csv
    import io
    
    reader = csv.DictReader(io.StringIO(holdings_csv))
    total_value = 0
    total_cost = 0
    
    for row in reader:
        try:
            value = float(row.get("value", 0))
            cost = float(row.get("total_cost", 0) or 0)
            total_value += value
            if cost > 0:
                total_cost += cost
        except (ValueError, TypeError):
            continue
    
    gain_loss = total_value - total_cost if total_cost > 0 else 0
    gain_loss_percent = (gain_loss / total_cost * 100) if total_cost > 0 else 0
    
    return {
        "success": True,
        "total_value": round(total_value, 2),
        "total_cost": round(total_cost, 2),
        "total_gain_loss": round(gain_loss, 2),
        "total_gain_loss_percent": round(gain_loss_percent, 2)
    }


@router.get("/portfolio/{user_id}/history")
async def get_portfolio_history(
    user_id: str,
    start_date: str = None,
    end_date: str = None,
    account_id: str = None,
    authenticated_user_id: str = Depends(get_current_user_id),
):
    """
    Get historical portfolio value time series (daily equity values).
    Returns data suitable for a Robinhood-style portfolio chart.
    """
    await verify_user_access(user_id, authenticated_user_id)
    result = await snaptrade_tools.get_portfolio_history(
        user_id, start_date=start_date, end_date=end_date, account_id=account_id
    )
    return result


@router.post("/portfolio/{user_id}/build-history")
async def build_portfolio_history_endpoint(
    user_id: str,
    account_id: str = None,
    force: bool = False,
    authenticated_user_id: str = Depends(get_current_user_id),
):
    """
    Backfill portfolio value history. Checks DB for fresh data first — only rebuilds
    if today's snapshot is missing or force=true. Saves results to portfolio_snapshots.
    """
    await verify_user_access(user_id, authenticated_user_id)
    import asyncio
    import uuid
    from datetime import date as date_type
    from sqlalchemy import select, delete
    from skills.snaptrade.scripts.portfolio.build_history import build_portfolio_history
    from core.database import get_db_session
    from models.brokerage import PortfolioSnapshot

    snapshot_account_key = account_id or "all"

    if not force:
        # Return cached DB data if today's snapshot already exists
        async with get_db_session() as db:
            today = date_type.today()
            matching = (await db.execute(
                select(PortfolioSnapshot)
                .where(PortfolioSnapshot.user_id == user_id)
                .where(PortfolioSnapshot.data["account_id"].astext == snapshot_account_key)
                .order_by(PortfolioSnapshot.snapshot_date.desc())
            )).scalars().all()

            if matching and matching[0].snapshot_date >= today:
                equity_series = [
                    {"date": str(s.snapshot_date), "value": float(s.data.get("total_value", 0))}
                    for s in sorted(matching, key=lambda s: s.snapshot_date)
                ]
                if len(equity_series) > 1:
                    return {"success": True, "equity_series": equity_series, "cached": True}

    # Pre-fetch session in async context so sync executor can use it
    session = await snaptrade_tools._get_session(user_id)
    if not session or not session.is_connected:
        return {"success": False, "error": "Not connected."}
    creds = (session.snaptrade_user_id, session.snaptrade_user_secret)

    # Rebuild from scratch
    result = await asyncio.get_event_loop().run_in_executor(
        None, lambda: build_portfolio_history(user_id, account_id=account_id, creds=creds)
    )

    if not result.get("success") or not result.get("equity_series"):
        return result

    equity_series = result["equity_series"]
    intraday_series = result.get("intraday_series", [])

    async with get_db_session() as db:
        # Save daily snapshots
        await db.execute(
            delete(PortfolioSnapshot)
            .where(PortfolioSnapshot.user_id == user_id)
            .where(PortfolioSnapshot.data["account_id"].astext == snapshot_account_key)
        )
        for point in equity_series:
            db.add(PortfolioSnapshot(
                id=uuid.uuid4(),
                user_id=user_id,
                snapshot_date=date_type.fromisoformat(point["date"]),
                data={"total_value": point["value"], "account_id": snapshot_account_key},
            ))

        # Save intraday series
        if intraday_series:
            from datetime import datetime, timezone
            from models.brokerage import PortfolioIntradayCache
            await db.execute(
                delete(PortfolioIntradayCache).where(
                    PortfolioIntradayCache.user_id == user_id,
                    PortfolioIntradayCache.account_id == snapshot_account_key,
                )
            )
            db.add(PortfolioIntradayCache(
                id=uuid.uuid4(),
                user_id=user_id,
                account_id=snapshot_account_key,
                days_back=7,
                equity_series=intraday_series,
                computed_at=datetime.now(timezone.utc),
            ))

    result["snapshots_saved"] = len(equity_series)
    return result


@router.get("/portfolio/{user_id}/intraday")
async def get_portfolio_intraday(
    user_id: str,
    account_id: str = None,
    days: int = 7,
    authenticated_user_id: str = Depends(get_current_user_id),
):
    """
    Get hourly portfolio value for the last N days.
    Returns cached intraday series from the last build-history run.
    """
    await verify_user_access(user_id, authenticated_user_id)
    from datetime import date as date_type, timedelta
    from sqlalchemy import select
    from models.brokerage import PortfolioIntradayCache
    from core.database import get_db_session

    account_key = account_id or "all"

    async with get_db_session() as db:
        row = (await db.execute(
            select(PortfolioIntradayCache).where(
                PortfolioIntradayCache.user_id == user_id,
                PortfolioIntradayCache.account_id == account_key,
            )
        )).scalars().first()

        if row and row.equity_series:
            series = row.equity_series
            if days < 7:
                cutoff = (date_type.today() - timedelta(days=days + 1)).isoformat()
                series = [p for p in series if p["date"] >= cutoff]
            return {"success": True, "equity_series": series, "cached": True}

    return {"success": True, "equity_series": [], "cached": False}


@router.delete("/portfolio/{user_id}/cache")
async def clear_portfolio_cache(
    user_id: str,
    authenticated_user_id: str = Depends(get_current_user_id),
):
    """Clear all cached portfolio data (snapshots + intraday + in-memory) for a user."""
    await verify_user_access(user_id, authenticated_user_id)
    from sqlalchemy import delete
    from models.brokerage import PortfolioSnapshot, PortfolioIntradayCache
    from core.database import get_db_session

    async with get_db_session() as db:
        snap_result = await db.execute(
            delete(PortfolioSnapshot).where(PortfolioSnapshot.user_id == user_id)
        )
        intra_result = await db.execute(
            delete(PortfolioIntradayCache).where(PortfolioIntradayCache.user_id == user_id)
        )

    from skills.snaptrade.scripts.portfolio.build_history import clear_caches
    clear_caches()

    return {
        "success": True,
        "snapshots_deleted": snap_result.rowcount,
        "intraday_deleted": intra_result.rowcount,
    }

