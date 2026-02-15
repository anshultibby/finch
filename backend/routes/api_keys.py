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
from modules.tools.clients.polymarket import test_polymarket_credentials
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
        # Validate service-specific requirements and normalize credentials
        credentials = request.credentials.copy()
        
        if request.service == "kalshi":
            if "api_key_id" not in credentials:
                raise HTTPException(
                    status_code=400,
                    detail="Kalshi requires 'api_key_id' in credentials"
                )
            if "private_key" not in credentials:
                raise HTTPException(
                    status_code=400,
                    detail="Kalshi requires 'private_key' in credentials"
                )
            # Normalize private key: convert literal \n to actual newlines
            if '\\n' in credentials["private_key"]:
                credentials["private_key"] = credentials["private_key"].replace('\\n', '\n')
        elif request.service == "polymarket":
            if "private_key" not in credentials:
                raise HTTPException(
                    status_code=400,
                    detail="Polymarket requires 'private_key' in credentials"
                )
            # Normalize private key for Polymarket too
            if '\\n' in credentials["private_key"]:
                credentials["private_key"] = credentials["private_key"].replace('\\n', '\n')
        
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
        elif request.service == "polymarket":
            private_key = creds.get("private_key", "")
            funder_address = creds.get("funder_address")
            
            logger.info(f"Testing Polymarket credentials - private_key length: {len(private_key)}")
            
            result = await test_polymarket_credentials(
                private_key=private_key,
                funder_address=funder_address
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
    
    try:
        if request.service == "kalshi":
            api_key_id = request.credentials.get("api_key_id")
            private_key = request.credentials.get("private_key")
            
            if not api_key_id or not private_key:
                raise HTTPException(
                    status_code=400,
                    detail="Kalshi requires 'api_key_id' and 'private_key'"
                )
            
            # Normalize private key format
            # If the key contains literal \n (two chars: backslash + n), replace with actual newlines
            if '\\n' in private_key:
                logger.info("Normalizing private key: converting literal \\n to actual newlines")
                private_key = private_key.replace('\\n', '\n')
            
            # Additional validation: check if key looks correct
            if '-----BEGIN' not in private_key or '-----END' not in private_key:
                raise HTTPException(
                    status_code=400,
                    detail="Invalid private key format: missing BEGIN/END markers"
                )
            
            result = await test_kalshi_credentials(api_key_id, private_key)
            return TestApiKeyResponse(**result)
        elif request.service == "polymarket":
            private_key = request.credentials.get("private_key")
            funder_address = request.credentials.get("funder_address")
            
            if not private_key:
                raise HTTPException(
                    status_code=400,
                    detail="Polymarket requires 'private_key'"
                )
            
            # Normalize private key before testing
            if '\\n' in private_key:
                private_key = private_key.replace('\\n', '\n')
            
            result = await test_polymarket_credentials(private_key, funder_address)
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
