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
from modules import snaptrade_tools

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
            session_id=request.session_id,
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
        result = snaptrade_tools.handle_connection_callback(
            session_id=request.session_id
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


@router.get("/status/{session_id}", response_model=SnapTradeStatusResponse)
async def check_connection_status(session_id: str):
    """
    Check if user has an active SnapTrade connection
    """
    print(f"📊 Checking connection status for session: {session_id}", flush=True)
    is_connected = snaptrade_tools.has_active_connection(session_id)
    print(f"📊 Connection status result: {is_connected}", flush=True)
    
    response = SnapTradeStatusResponse(
        success=True,
        message="Connected" if is_connected else "Not connected",
        is_connected=is_connected
    )
    print(f"📊 Returning response: {response}", flush=True)
    
    return response


@router.delete("/disconnect/{session_id}")
async def disconnect(session_id: str):
    """
    Disconnect from SnapTrade and clear session
    """
    snaptrade_tools.disconnect(session_id)
    
    return {
        "success": True,
        "message": "Disconnected successfully"
    }

