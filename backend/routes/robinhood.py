"""
Robinhood credential management routes
"""
from fastapi import APIRouter, HTTPException

from models import RobinhoodCredentials, RobinhoodCredentialsResponse
from modules import robinhood_tools

router = APIRouter(prefix="/robinhood", tags=["robinhood"])


@router.post("/credentials", response_model=RobinhoodCredentialsResponse)
async def set_credentials(credentials: RobinhoodCredentials):
    """
    Set Robinhood credentials and establish connection
    
    This logs into Robinhood and stores the session for the user.
    The session is used by tools to fetch portfolio data.
    """
    try:
        # Attempt to login and create session
        result = robinhood_tools.setup_robinhood_connection(
            username=credentials.username,
            password=credentials.password,
            session_id=credentials.session_id,
            mfa_code=credentials.mfa_code
        )
        
        if result["success"]:
            return RobinhoodCredentialsResponse(
                success=True,
                message=result["message"],
                has_credentials=True
            )
        else:
            return RobinhoodCredentialsResponse(
                success=False,
                message=result["message"],
                has_credentials=False
            )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/credentials/{session_id}", response_model=RobinhoodCredentialsResponse)
async def check_credentials(session_id: str):
    """
    Check if user has an active Robinhood session
    """
    has_session = robinhood_tools.has_active_session(session_id)
    
    return RobinhoodCredentialsResponse(
        success=True,
        message="Active Robinhood session" if has_session else "No active session",
        has_credentials=has_session
    )


@router.delete("/credentials/{session_id}")
async def logout(session_id: str):
    """
    Logout from Robinhood and clear session
    """
    robinhood_tools.logout(session_id)
    
    return {
        "success": True,
        "message": "Logged out successfully"
    }

