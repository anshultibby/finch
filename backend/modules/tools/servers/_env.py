"""
Sandbox Environment Variables

This module provides API key access for code running in the CODE EXECUTION SANDBOX.
The sandbox subprocess doesn't have database access, so it reads from environment
variables that were set by the parent process.

For code running in the MAIN APP (outside sandbox), use services.api_keys.ApiKeyService instead.

Usage in sandbox (server clients):
    from ._env import get_api_key
    
    # Get secure key wrapper (safe to print/log)
    api_key = get_api_key('FMP')
    if api_key:
        # Use .get() to extract the actual key for API calls
        response = requests.get(url, params={'apikey': api_key.get()})
"""
import os
from typing import Optional, Dict
from ._secure_key import SecureKey, secure_key_or_none


# API key environment variable names
_API_KEY_ENV_VARS = {
    'FMP': 'FMP_API_KEY',
    'POLYGON': 'POLYGON_API_KEY',
    'SERPER': 'SERPER_API_KEY',
    'DOME': 'DOME_API_KEY',
}


def get_user_id() -> Optional[str]:
    """
    Get the current user ID from environment.
    
    This is set by the code execution sandbox to identify the user.
    
    Returns:
        User ID string or None if not set
    """
    return os.getenv('FINCH_USER_ID') or None


def get_api_key(name: str) -> Optional[SecureKey]:
    """
    Get a secure API key wrapper by short name (SANDBOX ONLY).
    
    The returned SecureKey prevents accidental logging/printing while
    allowing normal use in API calls via .get() method.
    
    The parent process (main app) fetches keys using ApiKeyService
    and passes them to this subprocess via environment variables.
    
    Args:
        name: Short name (FMP, POLYGON, SERPER, DOME)
        
    Returns:
        SecureKey wrapper or None if not set
        
    Example:
        api_key = get_api_key('FMP')
        if api_key:
            print(f"Using key: {api_key}")  # Safe: prints "SecureKey(abcd****xyz9)"
            response = requests.get(url, params={'apikey': api_key.get()})
    """
    env_var = _API_KEY_ENV_VARS.get(name.upper())
    if not env_var:
        return None
    
    key_value = os.getenv(env_var)
    return secure_key_or_none(key_value)


def require_api_key(name: str) -> SecureKey:
    """
    Get a secure API key, raising error if not set (SANDBOX ONLY).
    
    Args:
        name: Short name (FMP, POLYGON, SERPER, DOME)
        
    Returns:
        SecureKey wrapper
        
    Raises:
        ValueError: If API key is not set
        
    Example:
        api_key = require_api_key('FMP')
        response = requests.get(url, params={'apikey': api_key.get()})
    """
    key = get_api_key(name)
    if not key:
        env_var = _API_KEY_ENV_VARS.get(name.upper(), f'{name}_API_KEY')
        raise ValueError(f"{env_var} not set in sandbox environment")
    return key


def get_kalshi_credentials() -> Optional[Dict[str, SecureKey]]:
    """
    Get Kalshi credentials (API key ID + private key) from environment (SANDBOX ONLY).
    
    Kalshi requires both an API key ID and RSA private key.
    
    Returns:
        Dict with 'api_key_id' and 'private_key' as SecureKey wrappers,
        or None if not configured
        
    Example:
        creds = get_kalshi_credentials()
        if creds:
            client = KalshiClient(
                api_key_id=creds['api_key_id'].get(),
                private_key=creds['private_key'].get()
            )
    """
    api_key_id = os.getenv('KALSHI_API_KEY_ID')
    private_key = os.getenv('KALSHI_PRIVATE_KEY')
    
    if not api_key_id or not private_key:
        return None
    
    return {
        'api_key_id': SecureKey(api_key_id),
        'private_key': SecureKey(private_key)
    }

