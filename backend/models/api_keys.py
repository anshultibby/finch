"""
Pydantic models for User API Key management
"""
from typing import Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field


class KalshiCredentials(BaseModel):
    """Kalshi API credentials"""
    api_key_id: str = Field(..., description="Kalshi API Key ID")
    private_key: str = Field(..., description="RSA private key (PEM format)")


class SaveApiKeyRequest(BaseModel):
    """Request to save API credentials for a service"""
    service: str = Field(..., description="Service name (e.g., 'kalshi')")
    credentials: Dict[str, Any] = Field(..., description="Service-specific credentials")


class ApiKeyInfo(BaseModel):
    """API key info for display (no secrets)"""
    service: str
    api_key_id: str
    api_key_id_masked: str
    has_private_key: bool
    created_at: Optional[str] = None


class ApiKeysResponse(BaseModel):
    """Response with user's API keys info"""
    success: bool
    keys: list[ApiKeyInfo]
    message: str


class ApiKeyResponse(BaseModel):
    """Response for single API key operation"""
    success: bool
    message: str
    key: Optional[ApiKeyInfo] = None


class TestApiKeyRequest(BaseModel):
    """Request to test API credentials"""
    service: str


class TestApiKeyResponse(BaseModel):
    """Response from testing API key"""
    success: bool
    message: str
    balance: Optional[float] = None
