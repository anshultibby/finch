"""
SnapTrade connection management routes
"""
from fastapi import APIRouter, HTTPException

from models import (
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
    from database import SessionLocal
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

