"""
Robinhood-related Pydantic models
"""
from pydantic import BaseModel
from typing import Optional


class RobinhoodCredentials(BaseModel):
    """Model for Robinhood login credentials"""
    username: str
    password: str
    session_id: str
    mfa_code: Optional[str] = None


class RobinhoodCredentialsResponse(BaseModel):
    """Response after setting credentials"""
    success: bool
    message: str
    has_credentials: bool

