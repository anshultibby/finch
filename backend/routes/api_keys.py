"""
API routes for user API key management

SECURITY:
- Credentials are encrypted at rest
- Private keys are NEVER returned in responses
- Only masked metadata is exposed
- Test endpoint validates credentials without storing sensitive data in logs
- Authentication required: Users can only access their own API keys
"""
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_async_db
from schemas.api_keys import (
    SaveApiKeyRequest,
    ApiKeysResponse,
    ApiKeyResponse,
    TestApiKeyRequest,
    TestApiKeyResponse,
    ApiKeyInfo
)
from crud import user_api_keys
from auth.dependencies import get_current_user_id, verify_user_access
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api-keys", tags=["api-keys"])


@router.get("/{user_id}", response_model=ApiKeysResponse)
async def get_user_api_keys(
    user_id: str,
    db: AsyncSession = Depends(get_async_db),
    authenticated_user_id: str = Depends(get_current_user_id)
):
    """
    Get list of user's saved API keys (masked, no secrets)
    
    Returns only metadata - never returns actual credentials
    
    SECURITY: Users can only access their own API keys
    """
    # Verify user is accessing their own keys
    await verify_user_access(user_id, authenticated_user_id)
    
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
    db: AsyncSession = Depends(get_async_db),
    authenticated_user_id: str = Depends(get_current_user_id)
):
    """
    Save or update API credentials for a service
    
    Credentials are encrypted before storage. The response only contains
    masked metadata, never the actual credentials.
    
    SECURITY: Users can only save their own API keys
    """
    # Verify user is saving their own keys
    await verify_user_access(user_id, authenticated_user_id)
    
    try:
        credentials = request.credentials.copy()

        key_info = await user_api_keys.save_api_key(
            db=db,
            user_id=user_id,
            service=request.service,
            credentials=credentials
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
    db: AsyncSession = Depends(get_async_db),
    authenticated_user_id: str = Depends(get_current_user_id)
):
    """
    Delete API credentials for a service
    
    SECURITY: Users can only delete their own API keys
    """
    # Verify user is deleting their own keys
    await verify_user_access(user_id, authenticated_user_id)
    
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
    db: AsyncSession = Depends(get_async_db),
    authenticated_user_id: str = Depends(get_current_user_id)
):
    """
    Test saved API credentials by making a simple API call
    
    For Kalshi: Fetches account balance to verify credentials work
    
    SECURITY: Users can only test their own API keys
    """
    # Verify user is testing their own keys
    await verify_user_access(user_id, authenticated_user_id)
    
    raise HTTPException(
        status_code=400,
        detail=f"Testing not supported for service: {request.service}"
    )


@router.post("/{user_id}/test-credentials", response_model=TestApiKeyResponse)
async def test_credentials_before_save(
    user_id: str,
    request: SaveApiKeyRequest,
    db: AsyncSession = Depends(get_async_db),
    authenticated_user_id: str = Depends(get_current_user_id)
):
    """
    Test API credentials BEFORE saving them
    
    This allows users to verify credentials work before committing them to storage.
    Credentials are NOT saved - only tested.
    
    SECURITY: Users can only test credentials for their own account
    """
    # Verify user is testing credentials for their own account
    await verify_user_access(user_id, authenticated_user_id)

    raise HTTPException(
        status_code=400,
        detail=f"Testing not supported for service: {request.service}"
    )
