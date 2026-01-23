"""
Secure CRUD operations for User API Keys

SECURITY:
- All credentials are encrypted as a single blob before storage
- Decrypted credentials are NEVER logged or returned to frontend
- Only masked metadata is exposed via API responses
"""
from typing import Optional, Dict, Any
from datetime import datetime, timezone
import json
import logging

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from models.db import UserSettings
from models.api_keys import ApiKeyInfo
from services.encryption import encryption_service

logger = logging.getLogger(__name__)


def _mask_key_id(key_id: str) -> str:
    """Mask API key ID for safe display: show first 4 and last 4 chars"""
    if not key_id:
        return "****"
    if len(key_id) <= 8:
        return "*" * len(key_id)
    return f"{key_id[:4]}{'*' * (len(key_id) - 8)}{key_id[-4:]}"


def _encrypt_api_keys(api_keys: Dict[str, Any]) -> str:
    """
    Encrypt the entire API keys dictionary as a single blob
    
    Args:
        api_keys: Dictionary of service -> credentials
        
    Returns:
        Fernet-encrypted string
    """
    json_str = json.dumps(api_keys)
    return encryption_service.encrypt(json_str)


def _decrypt_api_keys(encrypted: str) -> Dict[str, Any]:
    """
    Decrypt the API keys blob
    
    Args:
        encrypted: Fernet-encrypted string
        
    Returns:
        Dictionary of service -> credentials
        
    Raises:
        cryptography.fernet.InvalidToken: If decryption fails
    """
    json_str = encryption_service.decrypt(encrypted)
    return json.loads(json_str)


async def get_or_create_user_settings(db: AsyncSession, user_id: str) -> UserSettings:
    """Get or create user settings row"""
    result = await db.execute(
        select(UserSettings).where(UserSettings.user_id == user_id)
    )
    settings = result.scalars().first()
    
    if not settings:
        settings = UserSettings(user_id=user_id, settings={})
        db.add(settings)
        await db.commit()
        await db.refresh(settings)
        logger.info(f"Created user settings for user {user_id}")
    
    return settings


async def save_api_key(
    db: AsyncSession,
    user_id: str,
    service: str,
    credentials: Dict[str, Any]
) -> ApiKeyInfo:
    """
    Save or update API credentials for a service
    
    Args:
        db: Async database session
        user_id: User ID
        service: Service name (e.g., "kalshi")
        credentials: Service-specific credentials dict
        
    Returns:
        ApiKeyInfo with masked data (safe for frontend)
    """
    settings = await get_or_create_user_settings(db, user_id)
    
    # Decrypt existing keys or start fresh
    api_keys = {}
    if settings.encrypted_api_keys:
        try:
            api_keys = _decrypt_api_keys(settings.encrypted_api_keys)
        except Exception as e:
            logger.error(f"Failed to decrypt existing keys for user {user_id}: {e}")
            # Start fresh if decryption fails (key rotation, corruption, etc.)
            api_keys = {}
    
    # Add timestamp to credentials
    credentials["created_at"] = datetime.now(timezone.utc).isoformat()
    
    # Update credentials for this service
    api_keys[service] = credentials
    
    # Re-encrypt and save
    settings.encrypted_api_keys = _encrypt_api_keys(api_keys)
    await db.commit()
    
    # Log without any credential details
    logger.info(f"Saved API key for user {user_id}, service {service}")
    
    # Return safe info
    return ApiKeyInfo(
        service=service,
        api_key_id=credentials.get("api_key_id", ""),
        api_key_id_masked=_mask_key_id(credentials.get("api_key_id", "")),
        has_private_key=bool(credentials.get("private_key")),
        created_at=credentials["created_at"]
    )


async def get_api_keys_info(db: AsyncSession, user_id: str) -> list[ApiKeyInfo]:
    """
    Get list of API keys info (masked, safe for frontend)
    
    Args:
        db: Async database session
        user_id: User ID
        
    Returns:
        List of ApiKeyInfo with masked data
    """
    settings = await get_or_create_user_settings(db, user_id)
    
    if not settings.encrypted_api_keys:
        return []
    
    try:
        api_keys = _decrypt_api_keys(settings.encrypted_api_keys)
    except Exception as e:
        logger.error(f"Failed to decrypt keys for user {user_id}: {e}")
        return []
    
    result = []
    for service, creds in api_keys.items():
        result.append(ApiKeyInfo(
            service=service,
            api_key_id=creds.get("api_key_id", ""),
            api_key_id_masked=_mask_key_id(creds.get("api_key_id", "")),
            has_private_key=bool(creds.get("private_key")),
            created_at=creds.get("created_at")
        ))
    
    return result


async def get_decrypted_credentials(
    db: AsyncSession,
    user_id: str,
    service: str
) -> Optional[Dict[str, Any]]:
    """
    Get decrypted credentials for a service (SERVER-SIDE USE ONLY)
    
    ⚠️  SECURITY: This returns decrypted secrets!
    - NEVER log the return value
    - NEVER return to frontend/API response
    - Use ONLY for making authenticated API calls
    
    Args:
        db: Async database session
        user_id: User ID
        service: Service name
        
    Returns:
        Decrypted credentials dict, or None if not found
    """
    settings = await get_or_create_user_settings(db, user_id)
    
    if not settings.encrypted_api_keys:
        return None
    
    try:
        api_keys = _decrypt_api_keys(settings.encrypted_api_keys)
    except Exception as e:
        logger.error(f"Failed to decrypt keys for user {user_id}: {e}")
        return None
    
    creds = api_keys.get(service)
    if creds:
        # Update last accessed (for audit purposes) - stored in non-encrypted settings
        if "api_key_last_used" not in settings.settings:
            settings.settings = {**settings.settings, "api_key_last_used": {}}
        settings.settings["api_key_last_used"][service] = datetime.now(timezone.utc).isoformat()
        await db.commit()
    
    return creds


async def delete_api_key(db: AsyncSession, user_id: str, service: str) -> bool:
    """
    Delete API credentials for a service
    
    Args:
        db: Async database session
        user_id: User ID
        service: Service name to delete
        
    Returns:
        True if deleted, False if not found
    """
    settings = await get_or_create_user_settings(db, user_id)
    
    if not settings.encrypted_api_keys:
        return False
    
    try:
        api_keys = _decrypt_api_keys(settings.encrypted_api_keys)
    except Exception as e:
        logger.error(f"Failed to decrypt keys for user {user_id}: {e}")
        return False
    
    if service not in api_keys:
        return False
    
    del api_keys[service]
    
    # Re-encrypt (or set to None if empty)
    if api_keys:
        settings.encrypted_api_keys = _encrypt_api_keys(api_keys)
    else:
        settings.encrypted_api_keys = None
    
    await db.commit()
    logger.info(f"Deleted API key for user {user_id}, service {service}")
    
    return True


async def has_api_key(db: AsyncSession, user_id: str, service: str) -> bool:
    """
    Check if user has credentials for a service (without decrypting)
    
    Note: This still requires decryption to check, but doesn't expose credentials
    """
    creds = await get_decrypted_credentials(db, user_id, service)
    return creds is not None
