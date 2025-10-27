"""
Robinhood tools for portfolio management

SECURITY NOTES:
- Credentials (username/password) are NEVER passed to the LLM
- Access tokens are NEVER logged or exposed to the LLM
- robin_stocks manages sessions internally via pickle file

MULTI-USER LIMITATION:
- robin_stocks uses a single global pickle file (~/.tokens/robinhood.pickle)
- Only 1 Robinhood user can be logged in at a time
- For production multi-tenant setup, see: MULTI_USER_AUTH_PLAN.md
"""
import robin_stocks.robinhood as rh
from typing import Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel
import json


class RobinhoodSession(BaseModel):
    """
    Session data for a logged-in Robinhood user
    SECURITY: Only stores authentication status, never credentials or tokens
    """
    logged_in: bool
    logged_in_at: str  # ISO format timestamp
    last_activity: str  # ISO format timestamp
    
    class Config:
        # Allow updating timestamps
        validate_assignment = True


class RobinhoodTools:
    """
    Tools for interacting with Robinhood API
    
    SECURITY ARCHITECTURE:
    - Credentials flow: Frontend → API endpoint → This class → robin_stocks
    - LLM never sees: username, password, access_token, refresh_token
    - Session tracking: Only stores {logged_in: bool} per session_id
    - Actual auth: Managed by robin_stocks library (stored in ~/.tokens/)
    """
    
    def __init__(self):
        # Store active sessions per session_id (only logged_in status, no credentials)
        self._sessions: Dict[str, RobinhoodSession] = {}
        # Try to use existing cached Robinhood session if available
        # robin_stocks stores session in ~/.tokens/robinhood.pickle by default
        self._check_existing_session()
    
    def _check_existing_session(self) -> bool:
        """Check if there's an existing cached Robinhood session"""
        try:
            # Try to get account info with cached session
            account = rh.account.load_account_profile()
            return account is not None
        except:
            return False
    
    def setup_robinhood_connection(self, username: str, password: str, session_id: str, mfa_code: Optional[str] = None) -> Dict[str, Any]:
        """
        Setup Robinhood connection with user credentials
        
        This is called after the user provides their credentials via the frontend.
        Creates and stores a robin_stocks session.
        
        Args:
            username: Robinhood username
            password: Robinhood password
            session_id: User session ID
            mfa_code: Optional MFA/2FA code
            
        Returns:
            Dictionary with success status and message
        """
        try:
            # Warn if another user is already logged in (multi-user limitation)
            if len(self._sessions) > 0 and session_id not in self._sessions:
                print("⚠️  WARNING: Multiple users detected. robin_stocks uses global session storage.", flush=True)
                print("⚠️  New login will overwrite previous user's session.", flush=True)
                print("⚠️  See MULTI_USER_AUTH_PLAN.md for production implementation.", flush=True)
            
            # First check if we already have a valid cached session
            if self._check_existing_session():
                # SECURITY: Only store that user is logged in
                now = datetime.now().isoformat()
                self._sessions[session_id] = RobinhoodSession(
                    logged_in=True,
                    logged_in_at=now,
                    last_activity=now
                )
                return {
                    "success": True,
                    "message": "Already logged in using cached session! I can now fetch your portfolio data."
                }
            
            # Login to Robinhood with session persistence
            # store_session=True will cache the login so user doesn't need to re-authenticate
            # Version 3.4.0+ handles the device verification workflow automatically
            print(f"🔐 Attempting Robinhood login for {username}...", flush=True)
            print("⏳ Waiting for device verification (this may take up to 60 seconds)...", flush=True)
            
            login_result = rh.login(
                username=username,
                password=password, 
                expiresIn=86400,  # 24 hours session
                mfa_code=mfa_code,
                store_session=True  # Cache the session for future use
            )
            
            print(f"✅ Login result type: {type(login_result)}", flush=True)
            # SECURITY: Never log the full result as it contains access_token!
            if isinstance(login_result, dict):
                safe_keys = [k for k in login_result.keys() if k not in ['access_token', 'refresh_token']]
                print(f"✅ Login result keys: {safe_keys}", flush=True)
                if 'detail' in login_result:
                    print(f"✅ Login detail: {login_result['detail']}", flush=True)
            
            # Check if login was successful
            # login_result can be:
            # - dict with 'access_token' or 'detail' on success
            # - dict with 'challenge' if challenge is required
            # - None or empty dict on failure
            
            if login_result and isinstance(login_result, dict):
                print(f"📊 Login result keys: {login_result.keys()}", flush=True)
                
                # Check if it's a challenge response (device verification)
                if 'challenge' in login_result:
                    challenge_type = login_result['challenge'].get('type', 'unknown')
                    challenge_id = login_result['challenge'].get('id', 'unknown')
                    print(f"⚠️ Challenge required: {challenge_type} (ID: {challenge_id})", flush=True)
                    return {
                        "success": False,
                        "message": f"🔐 Device verification required. Please approve the push notification on your Robinhood app and try logging in again. Challenge type: {challenge_type}"
                    }
                
                # Check for successful login (has access_token or detail)
                if 'access_token' in login_result or 'detail' in login_result:
                    # SECURITY: Only store that user is logged in, no sensitive data
                    now = datetime.now().isoformat()
                    self._sessions[session_id] = RobinhoodSession(
                        logged_in=True,
                        logged_in_at=now,
                        last_activity=now
                    )
                    
                    print(f"✅ Session stored for session_id: {session_id}", flush=True)
                    print(f"✅ Total active sessions: {len(self._sessions)}", flush=True)
                    
                    detail = login_result.get('detail', 'Login successful')
                    print(f"✅ {detail}", flush=True)
                    
                    return {
                        "success": True,
                        "message": "Successfully connected to Robinhood! I can now fetch your portfolio data."
                    }
            
            # If we get here, login failed
            print(f"❌ Login failed - result: {login_result}", flush=True)
            return {
                "success": False,
                "message": "Failed to connect to Robinhood. Please check your credentials. If you received a push notification, approve it on your phone and try again."
            }
        except Exception as e:
            error_msg = str(e)
            print(f"❌ Exception during login: {error_msg}", flush=True)
            import traceback
            traceback.print_exc()
            
            # Check for device challenge (push notification)
            if "challenge" in error_msg.lower():
                return {
                    "success": False,
                    "message": "⏳ Please approve the login notification on your Robinhood app, then try logging in again. The session will be cached for future use."
                }
            
            # Check if MFA/SMS code is required
            if "mfa" in error_msg.lower() or "two-factor" in error_msg.lower():
                return {
                    "success": False,
                    "message": "Two-factor authentication required. Please enter your 6-digit code from your authenticator app or SMS.",
                    "requires_mfa": True
                }
            
            return {
                "success": False,
                "message": f"Login error: {error_msg}. If you received a push notification, please approve it on your phone and try again."
            }
    
    def logout(self, session_id: str) -> None:
        """Logout from Robinhood"""
        try:
            rh.logout()
            if session_id in self._sessions:
                del self._sessions[session_id]
        except:
            pass
    
    def get_portfolio(self, session_id: str) -> Dict[str, Any]:
        """
        Get user's portfolio holdings using stored session
        
        Tool for LLM to fetch portfolio data.
        Uses the robin_stocks session stored in context.
        
        Returns:
            Dictionary containing portfolio holdings and summary
        """
        try:
            print(f"🔍 Checking portfolio for session_id: {session_id}", flush=True)
            print(f"🔍 Active sessions: {list(self._sessions.keys())}", flush=True)
            
            # Check if user has an active session
            session = self._sessions.get(session_id)
            if not session or not session.logged_in:
                print(f"❌ No active session found for {session_id}", flush=True)
                return {
                    "success": False,
                    "message": "Not connected to Robinhood. Please provide your login credentials first.",
                    "needs_auth": True
                }
            
            print(f"🔍 Session logged_in: {session.logged_in} (logged in at: {session.logged_in_at})", flush=True)
            
            # Update last activity
            session.last_activity = datetime.now().isoformat()
            
            print(f"✅ Active session found, fetching portfolio...", flush=True)
            # SECURITY: Get portfolio data using robin_stocks cached session
            # robin_stocks manages the session internally, we never expose tokens
            holdings = rh.build_holdings()
            
            if not holdings:
                return {
                    "success": True,
                    "message": "Portfolio is empty",
                    "holdings": {},
                    "total_value": 0.0,
                    "total_equity": 0.0
                }
            
            # Calculate totals
            total_equity = sum(float(holding.get("equity", 0)) for holding in holdings.values())
            
            # Format holdings for readability
            formatted_holdings = {}
            for symbol, data in holdings.items():
                formatted_holdings[symbol] = {
                    "name": data.get("name", symbol),
                    "quantity": float(data.get("quantity", 0)),
                    "price": float(data.get("price", 0)),
                    "equity": float(data.get("equity", 0)),
                    "percent_change": float(data.get("percent_change", 0)),
                    "average_buy_price": float(data.get("average_buy_price", 0))
                }
            
            return {
                "success": True,
                "holdings": formatted_holdings,
                "total_equity": round(total_equity, 2),
                "holdings_count": len(holdings)
            }
            
        except Exception as e:
            return {
                "success": False,
                "message": f"Error fetching portfolio: {str(e)}"
            }
    
    def has_active_session(self, session_id: str) -> bool:
        """Check if user has an active Robinhood session"""
        session = self._sessions.get(session_id)
        has_session = session is not None and session.logged_in
        print(f"🔍 has_active_session({session_id}): {has_session}", flush=True)
        return has_session


# Tool definitions for LiteLLM
ROBINHOOD_TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "get_portfolio",
            "description": "Fetch the user's current Robinhood portfolio holdings, including stocks they own, quantities, current prices, total equity, and performance data. ALWAYS call this tool first when the user asks about their portfolio, stocks, holdings, or account value. This tool will automatically handle authentication - if the user isn't logged in, it will tell you to request login. Do not guess or assume - call this tool to check.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "request_robinhood_login",
            "description": "Request the user to provide Robinhood login credentials. ONLY use this tool if get_portfolio returns an authentication error. Do NOT call this proactively - always try get_portfolio first.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    }
]


# Global tools instance
robinhood_tools = RobinhoodTools()

