"""
Centralized API Key Management Service

Provides a unified interface for accessing API keys from multiple sources:
1. Global config keys (from environment/settings) — system-owned, shared
2. User-specific keys (from encrypted database storage) — per-user

All keys are wrapped in SecureKey to prevent accidental logging.
"""
from typing import Optional, Dict
from sqlalchemy.ext.asyncio import AsyncSession
import logging

from core.config import Config
from crud.user_api_keys import get_decrypted_credentials
from modules.tools.apis._secure_key import SecureKey, secure_key_or_none

logger = logging.getLogger(__name__)


class ApiKeyService:
    """
    Service for retrieving API keys with automatic fallback logic.

    Priority order:
    1. User-specific keys (if user_id provided and key exists in DB)
    2. Global config keys (from .env / environment settings)

    All keys are returned as SecureKey wrappers for safe handling.
    """

    # service_name → primary env var name for get_key() lookups.
    # Multi-var services (Reddit, Snaptrade) use the primary credential here;
    # individual env vars are resolved dynamically via get_env_var().
    _SERVICE_PRIMARY_VAR: Dict[str, str] = {
        "FMP":       "FMP_API_KEY",
        "POLYGON":   "POLYGON_API_KEY",
        "SERPER":    "SERPER_API_KEY",
        "REDDIT":    "REDDIT_CLIENT_ID",
        "SNAPTRADE": "SNAPTRADE_CLIENT_ID",
        "ODDS":      "ODDS_API_KEY",
    }
    
    def __init__(self, db: Optional[AsyncSession] = None, user_id: Optional[str] = None):
        """
        Initialize API key service.
        
        Args:
            db: Database session (required for user-specific keys)
            user_id: User ID (required for user-specific keys)
        """
        self.db = db
        self.user_id = user_id
    
    async def get_key(self, service: str) -> Optional[SecureKey]:
        """
        Get API key for a service with automatic fallback.
        
        Tries user-specific key first (if available), then falls back to global config.
        
        Args:
            service: Service name (FMP, POLYGON, SERPER, KALSHI, etc.)
            
        Returns:
            SecureKey wrapper or None if not found
            
        Example:
            service = ApiKeyService(db, user_id)
            key = await service.get_key('FMP')
            if key:
                response = requests.get(url, params={'apikey': key.get()})
        """
        service = service.upper()
        
        # Try user-specific key first
        if self.db and self.user_id:
            user_key = await self._get_user_key(service)
            if user_key:
                logger.debug(f"Using user-specific key for {service}")
                return user_key
        
        # Fallback to global config key
        global_key = self._get_global_key(service)
        if global_key:
            logger.debug(f"Using global config key for {service}")
            return global_key
        
        logger.debug(f"No API key found for {service}")
        return None
    
    async def get_kalshi_credentials(self) -> Optional[Dict[str, SecureKey]]:
        """
        Get Kalshi credentials (api_key_id + private_key).
        
        Kalshi requires both values, so this returns None if either is missing.
        
        Returns:
            Dict with 'api_key_id' and 'private_key' as SecureKey wrappers,
            or None if not configured
            
        Example:
            service = ApiKeyService(db, user_id)
            creds = await service.get_kalshi_credentials()
            if creds:
                client = KalshiHTTPClient(
                    creds['api_key_id'].get(),
                    creds['private_key'].get()
                )
        """
        # Try user-specific credentials first
        if self.db and self.user_id:
            user_creds = await self._get_user_kalshi_credentials()
            if user_creds:
                logger.debug("Using user-specific Kalshi credentials")
                return user_creds
        
        # Note: Kalshi typically doesn't have global credentials
        # (it's per-user by nature), but we could add support if needed
        
        logger.debug("No Kalshi credentials found")
        return None
    
    async def require_key(self, service: str) -> SecureKey:
        """
        Get API key or raise error if not found.
        
        Args:
            service: Service name
            
        Returns:
            SecureKey wrapper
            
        Raises:
            ValueError: If API key not found
        """
        key = await self.get_key(service)
        if not key:
            raise ValueError(f"API key for {service} not found. Please configure in settings.")
        return key
    
    async def _get_user_key(self, service: str) -> Optional[SecureKey]:
        """Get user-specific API key from database"""
        try:
            creds = await get_decrypted_credentials(self.db, self.user_id, service.lower())
            if not creds:
                return None
            
            # Extract the key value (different services use different field names)
            # Try common field names in order of preference
            key_value = creds.get('api_key') or creds.get('key') or creds.get('token')
            
            if not key_value:
                logger.warning(f"Credentials found for {service} but no key field present")
                return None
            
            return secure_key_or_none(key_value)
        
        except Exception as e:
            logger.error(f"Error fetching user key for {service}: {e}")
            return None
    
    async def _get_user_kalshi_credentials(self) -> Optional[Dict[str, SecureKey]]:
        """Get user-specific Kalshi credentials from database"""
        try:
            creds = await get_decrypted_credentials(self.db, self.user_id, 'kalshi')
            if not creds:
                return None
            
            api_key_id = creds.get('api_key_id')
            private_key = creds.get('private_key')
            
            if not api_key_id or not private_key:
                return None
            
            return {
                'api_key_id': SecureKey(api_key_id),
                'private_key': SecureKey(private_key)
            }
        
        except Exception as e:
            logger.error(f"Error fetching user Kalshi credentials: {e}")
            return None
    
    def get_env_var(self, env_var: str) -> Optional[SecureKey]:
        """
        Get the value for a specific environment variable name from global config.

        Used by _build_sandbox_env to resolve each env var from SKILL_ENV_KEYS.
        Resolves directly from Config via attribute lookup — no manual registry needed.
        User-owned vars like KALSHI_API_KEY_ID must be fetched via get_kalshi_credentials().
        """
        val = getattr(Config, env_var, None)
        return secure_key_or_none(val) if val is not None else None

    def _get_global_key(self, service: str) -> Optional[SecureKey]:
        """Get global API key from config"""
        env_var = self._SERVICE_PRIMARY_VAR.get(service)
        if not env_var:
            return None
        return self.get_env_var(env_var)
