"""
API routes for user API key management

SECURITY:
- Credentials are encrypted at rest
- Private keys are NEVER returned in responses
- Only masked metadata is exposed
- Test endpoint validates credentials without storing sensitive data in logs
"""
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_async_db
from models.api_keys import (
    SaveApiKeyRequest,
    ApiKeysResponse,
    ApiKeyResponse,
    TestApiKeyRequest,
    TestApiKeyResponse,
    ApiKeyInfo
)
from crud import user_api_keys
from modules.tools.clients.kalshi import test_kalshi_credentials
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api-keys", tags=["api-keys"])


@router.get("/{user_id}", response_model=ApiKeysResponse)
async def get_user_api_keys(
    user_id: str,
    db: AsyncSession = Depends(get_async_db)
):
    """
    Get list of user's saved API keys (masked, no secrets)
    
    Returns only metadata - never returns actual credentials
    """
    try:
        keys = await user_api_keys.get_api_keys_info(db, user_id)
        return ApiKeysResponse(
            success=True,
            keys=keys,
            message=f"Found {len(keys)} API key(s)"
        )
    except Exception as e:
        logger.error(f"Error fetching API keys for user {user_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch API keys")


@router.post("/{user_id}", response_model=ApiKeyResponse)
async def save_api_key(
    user_id: str,
    request: SaveApiKeyRequest,
    db: AsyncSession = Depends(get_async_db)
):
    """
    Save or update API credentials for a service
    
    Credentials are encrypted before storage. The response only contains
    masked metadata, never the actual credentials.
    """
    try:
        # Validate service-specific requirements
        if request.service == "kalshi":
            if "api_key_id" not in request.credentials:
                raise HTTPException(
                    status_code=400,
                    detail="Kalshi requires 'api_key_id' in credentials"
                )
            if "private_key" not in request.credentials:
                raise HTTPException(
                    status_code=400,
                    detail="Kalshi requires 'private_key' in credentials"
                )
        
        key_info = await user_api_keys.save_api_key(
            db=db,
            user_id=user_id,
            service=request.service,
            credentials=request.credentials
        )
        
        return ApiKeyResponse(
            success=True,
            message=f"API key for {request.service} saved successfully",
            key=key_info
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error saving API key for user {user_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to save API key")


@router.delete("/{user_id}/{service}", response_model=ApiKeyResponse)
async def delete_api_key(
    user_id: str,
    service: str,
    db: AsyncSession = Depends(get_async_db)
):
    """
    Delete API credentials for a service
    """
    try:
        deleted = await user_api_keys.delete_api_key(db, user_id, service)
        
        if deleted:
            return ApiKeyResponse(
                success=True,
                message=f"API key for {service} deleted successfully"
            )
        else:
            raise HTTPException(
                status_code=404,
                detail=f"No API key found for service: {service}"
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting API key for user {user_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete API key")


@router.post("/{user_id}/test", response_model=TestApiKeyResponse)
async def test_api_key(
    user_id: str,
    request: TestApiKeyRequest,
    db: AsyncSession = Depends(get_async_db)
):
    """
    Test saved API credentials by making a simple API call
    
    For Kalshi: Fetches account balance to verify credentials work
    """
    try:
        # Get decrypted credentials (server-side only)
        creds = await user_api_keys.get_decrypted_credentials(db, user_id, request.service)
        
        if not creds:
            raise HTTPException(
                status_code=404,
                detail=f"No API key found for service: {request.service}"
            )
        
        # Test based on service
        if request.service == "kalshi":
            api_key_id = creds.get("api_key_id", "")
            private_key = creds.get("private_key", "")
            
            # Debug: Log key info (NOT the actual key content!)
            logger.info(f"Testing Kalshi credentials - api_key_id length: {len(api_key_id)}, private_key length: {len(private_key)}")
            logger.info(f"api_key_id starts with: {api_key_id[:8] if len(api_key_id) > 8 else api_key_id}...")
            logger.info(f"private_key starts with: {private_key[:30] if len(private_key) > 30 else 'too short'}...")
            
            result = await test_kalshi_credentials(
                api_key_id=api_key_id,
                private_key_pem=private_key
            )
            return TestApiKeyResponse(**result)
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Testing not supported for service: {request.service}"
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error testing API key for user {user_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to test API key")


@router.post("/{user_id}/test-credentials", response_model=TestApiKeyResponse)
async def test_credentials_before_save(
    user_id: str,
    request: SaveApiKeyRequest,
    db: AsyncSession = Depends(get_async_db)
):
    """
    Test API credentials BEFORE saving them
    
    This allows users to verify credentials work before committing them to storage.
    Credentials are NOT saved - only tested.
    """
    try:
        if request.service == "kalshi":
            api_key_id = request.credentials.get("api_key_id")
            private_key = request.credentials.get("private_key")
            
            if not api_key_id or not private_key:
                raise HTTPException(
                    status_code=400,
                    detail="Kalshi requires 'api_key_id' and 'private_key'"
                )
            
            result = await test_kalshi_credentials(api_key_id, private_key)
            return TestApiKeyResponse(**result)
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Testing not supported for service: {request.service}"
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error testing credentials: {e}")
        raise HTTPException(status_code=500, detail="Failed to test credentials")
