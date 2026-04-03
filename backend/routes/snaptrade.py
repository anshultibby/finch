"""
SnapTrade connection management routes
"""
from fastapi import APIRouter, HTTPException

from schemas import (
    SnapTradeConnectionRequest,
    SnapTradeConnectionResponse,
    SnapTradeCallbackRequest,
    SnapTradeStatusResponse
)
from modules.tools.clients import snaptrade_tools

router = APIRouter(prefix="/snaptrade", tags=["snaptrade"])


@router.post("/connect", response_model=SnapTradeConnectionResponse)
async def initiate_connection(request: SnapTradeConnectionRequest):
    """
    Initiate SnapTrade OAuth connection flow
    
    Returns a redirect URI that the frontend should open to allow
    the user to connect their brokerage account via SnapTrade.
    """
    try:
        result = snaptrade_tools.get_login_redirect_uri(
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
async def handle_callback(request: SnapTradeCallbackRequest):
    """
    Handle callback after user successfully connects via SnapTrade Portal
    
    Verifies the connection and fetches connected account information.
    """
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
async def check_connection_status(user_id: str):
    """
    Check if user has an active SnapTrade connection
    """
    print(f"📊 Checking connection status for user: {user_id}", flush=True)
    is_connected = snaptrade_tools.has_active_connection(user_id)
    print(f"📊 Connection status result: {is_connected}", flush=True)
    
    response = SnapTradeStatusResponse(
        success=True,
        message="Connected" if is_connected else "Not connected",
        is_connected=is_connected
    )
    print(f"📊 Returning response: {response}", flush=True)
    
    return response


@router.delete("/disconnect/{user_id}")
async def disconnect(user_id: str):
    """
    Disconnect from SnapTrade and clear user session
    """
    snaptrade_tools.disconnect(user_id)
    
    return {
        "success": True,
        "message": "Disconnected successfully"
    }


@router.get("/accounts/{user_id}")
async def get_accounts(user_id: str):
    """
    Get list of user's connected brokerage accounts
    """
    result = await snaptrade_tools.get_connected_accounts(user_id)
    return result


@router.get("/brokerages")
async def get_brokerages():
    """
    Get list of available brokerages that can be connected
    """
    result = snaptrade_tools.get_available_brokerages()
    return result


@router.post("/connect/broker")
async def connect_broker(request: dict):
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
    
    result = snaptrade_tools.get_login_redirect_uri_for_broker(
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
async def disconnect_account(user_id: str, account_id: str):
    """
    Disconnect a specific brokerage account
    """
    result = await snaptrade_tools.disconnect_account(user_id, account_id)
    return result


@router.patch("/accounts/{user_id}/{account_id}/visibility")
async def toggle_account_visibility(user_id: str, account_id: str, request: dict):
    """
    Toggle account visibility (include/exclude from portfolio view)
    
    Request body:
    {
        "is_visible": bool
    }
    """
    from core.database import SessionLocal
    from crud import brokerage_account as brokerage_crud
    
    is_visible = request.get("is_visible", True)
    
    db = SessionLocal()
    try:
        account = brokerage_crud.get_account_by_account_id(db, user_id, account_id)
        if not account:
            return {
                "success": False,
                "message": "Account not found"
            }
        
        account.is_active = is_visible
        db.commit()
        
        return {
            "success": True,
            "message": f"Account visibility {'enabled' if is_visible else 'disabled'}"
        }
    finally:
        db.close()


@router.get("/portfolio/{user_id}")
async def get_portfolio(user_id: str):
    """
    Get user's complete portfolio with holdings, accounts, and performance metrics
    
    Returns:
    - accounts: List of all connected accounts with balances
    - holdings: Aggregated positions across all accounts
    - total_value: Total portfolio value
    - performance: Gain/loss metrics
    """
    result = await snaptrade_tools.get_portfolio(user_id)
    return result


@router.get("/portfolio/{user_id}/holdings")
async def get_portfolio_holdings(user_id: str):
    """
    Get detailed holdings with position-level data
    """
    result = await snaptrade_tools.get_portfolio(user_id)
    return result


@router.get("/portfolio/{user_id}/performance")
async def get_portfolio_performance(user_id: str):
    """
    Get portfolio performance metrics including gains, losses, and returns
    """
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
async def get_portfolio_history(user_id: str, start_date: str = None, end_date: str = None, account_id: str = None):
    """
    Get historical portfolio value time series (daily equity values).
    Returns data suitable for a Robinhood-style portfolio chart.
    """
    result = await snaptrade_tools.get_portfolio_history(
        user_id, start_date=start_date, end_date=end_date, account_id=account_id
    )
    return result


@router.post("/portfolio/{user_id}/build-history")
async def build_portfolio_history_endpoint(user_id: str, account_id: str = None):
    """
    Backfill portfolio value history by replaying SnapTrade activities
    and fetching historical prices from FMP. Saves to portfolio_snapshots.
    This can take a while for accounts with lots of history.
    """
    import asyncio
    import uuid
    from datetime import date as date_type
    from skills.snaptrade.scripts.portfolio.build_history import build_portfolio_history
    from core.database import get_db_session
    from models.brokerage import PortfolioSnapshot

    # Step 1: Heavy computation in thread (no DB needed)
    result = await asyncio.get_event_loop().run_in_executor(
        None, lambda: build_portfolio_history(user_id, account_id=account_id)
    )

    if not result.get("success") or not result.get("equity_series"):
        return result

    # Step 2: Save snapshots using async session (no sync pool needed)
    snapshot_account_key = account_id or "all"
    equity_series = result["equity_series"]
    saved = 0

    async with get_db_session() as db:
        # Delete old snapshots for this account
        from sqlalchemy import select, delete
        old_snaps = (await db.execute(
            select(PortfolioSnapshot).where(PortfolioSnapshot.user_id == user_id)
        )).scalars().all()

        for s in old_snaps:
            if isinstance(s.data, dict) and s.data.get("account_id", "all") == snapshot_account_key:
                await db.delete(s)

        # Insert new snapshots
        for point in equity_series:
            db.add(PortfolioSnapshot(
                id=uuid.uuid4(),
                user_id=user_id,
                snapshot_date=date_type.fromisoformat(point["date"]),
                data={"total_value": point["value"], "account_id": snapshot_account_key},
            ))
            saved += 1

    result["snapshots_saved"] = saved
    return result


@router.get("/portfolio/{user_id}/intraday")
async def get_portfolio_intraday(user_id: str, account_id: str = None, days: int = 7):
    """
    Get hourly portfolio value for the last N days.
    Uses current holdings x FMP intraday prices.
    """
    import asyncio
    from skills.snaptrade.scripts.portfolio.build_history import build_intraday_history
    result = await asyncio.get_event_loop().run_in_executor(
        None, lambda: build_intraday_history(user_id, account_id=account_id, days_back=days)
    )
    return result


@router.get("/debug-activities/{user_id}/{account_id}")
async def debug_activities(user_id: str, account_id: str, limit: int = 5):
    """Debug: dump raw activity objects to see structure."""
    import asyncio
    session = snaptrade_tools._get_session(user_id)
    if not session:
        return {"error": "No session"}
    client = snaptrade_tools.client
    resp = await asyncio.get_event_loop().run_in_executor(None, lambda: client.account_information.get_account_activities(
        user_id=session.snaptrade_user_id, user_secret=session.snaptrade_user_secret,
        account_id=account_id, start_date="2026-03-01", end_date="2026-04-02", limit=limit,
    ))
    data = resp.body if hasattr(resp, "body") else resp
    items = data if isinstance(data, list) else data.get("data", [])
    results = []
    for item in items[:limit]:
        row = {}
        for attr in ["type", "units", "amount", "price", "fee", "description", "trade_date", "settlement_date"]:
            row[attr] = str(getattr(item, attr, None))[:100] if hasattr(item, attr) else None
        # Dig into symbol
        sym_obj = getattr(item, "symbol", None)
        if sym_obj:
            row["symbol_type"] = type(sym_obj).__name__
            row["symbol_attrs"] = [a for a in dir(sym_obj) if not a.startswith("_")][:15]
            inner_sym = getattr(sym_obj, "symbol", None)
            if inner_sym:
                row["symbol.symbol_type"] = type(inner_sym).__name__
                row["symbol.symbol"] = str(inner_sym)[:100]
                inner2 = getattr(inner_sym, "symbol", None)
                if inner2:
                    row["symbol.symbol.symbol"] = str(inner2)[:100]
            row["symbol.description"] = str(getattr(sym_obj, "description", ""))[:100]
            row["symbol.id"] = str(getattr(sym_obj, "id", ""))[:100]
        results.append(row)
    return results


@router.get("/test-endpoints/{user_id}/{account_id}")
async def test_endpoints(user_id: str, account_id: str):
    """Temporary: test which SnapTrade endpoints work for this account."""
    import asyncio
    session = snaptrade_tools._get_session(user_id)
    if not session:
        return {"error": "No session"}

    client = snaptrade_tools.client
    uid = session.snaptrade_user_id
    secret = session.snaptrade_user_secret
    results = {}

    # Activities
    try:
        resp = await asyncio.get_event_loop().run_in_executor(None, lambda: client.account_information.get_account_activities(
            user_id=uid, user_secret=secret, account_id=account_id, start_date="2025-01-01", end_date="2026-04-02"
        ))
        data = resp.body if hasattr(resp, "body") else resp
        items = data if isinstance(data, list) else data.get("data", [])
        results["activities"] = {"status": "OK", "count": len(items)}
        if items:
            first = items[0]
            if isinstance(first, dict):
                results["activities"]["sample_keys"] = list(first.keys())[:10]
                results["activities"]["sample"] = {k: str(first[k])[:50] for k in list(first.keys())[:8]}
            else:
                attrs = {a: str(getattr(first, a, None))[:50] for a in ["type", "trade_date", "amount", "symbol", "units", "price", "settlement_date", "description"] if hasattr(first, a)}
                results["activities"]["sample"] = attrs
    except Exception as e:
        results["activities"] = {"status": "FAILED", "error": str(e)[:200]}

    # Balances
    try:
        resp = await asyncio.get_event_loop().run_in_executor(None, lambda: client.account_information.get_user_account_balance(
            user_id=uid, user_secret=secret, account_id=account_id
        ))
        data = resp.body if hasattr(resp, "body") else resp
        results["balances"] = {"status": "OK", "data": str(data)[:300]}
    except Exception as e:
        results["balances"] = {"status": "FAILED", "error": str(e)[:200]}

    # Orders
    try:
        resp = await asyncio.get_event_loop().run_in_executor(None, lambda: client.account_information.get_user_account_orders(
            user_id=uid, user_secret=secret, account_id=account_id, state="all"
        ))
        data = resp.body if hasattr(resp, "body") else resp
        items = data if isinstance(data, list) else data.get("data", [])
        results["orders"] = {"status": "OK", "count": len(items)}
    except Exception as e:
        results["orders"] = {"status": "FAILED", "error": str(e)[:200]}

    return results

