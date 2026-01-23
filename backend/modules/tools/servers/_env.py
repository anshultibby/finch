"""
Sandbox Environment Variables

This module provides API keys for code running in the sandbox.
It uses os.getenv because the sandbox subprocess receives env vars
from the parent process (see code_execution.py).

Usage in server clients:
    from ._env import get_api_key
    api_key = get_api_key('FMP')
"""
import os
from typing import Optional

# API key names that are passed to the sandbox
_API_KEYS = {
    'FMP': 'FMP_API_KEY',
    'POLYGON': 'POLYGON_API_KEY', 
    'SERPER': 'SERPER_API_KEY',
}


def get_user_id() -> Optional[str]:
    """
    Get the current user ID from environment.
    
    This is set by the code execution sandbox to identify the user
    for per-user API credentials (like Kalshi).
    
    Returns:
        User ID string or None if not set
    """
    return os.getenv('FINCH_USER_ID') or None


def get_api_key(name: str) -> Optional[str]:
    """
    Get an API key by short name.
    
    Args:
        name: Short name (FMP, POLYGON, SERPER)
        
    Returns:
        API key string or None if not set
    """
    env_var = _API_KEYS.get(name.upper())
    if not env_var:
        return None
    return os.getenv(env_var) or None


def require_api_key(name: str) -> str:
    """
    Get an API key, raising error if not set.
    
    Args:
        name: Short name (FMP, POLYGON, SERPER)
        
    Returns:
        API key string
        
    Raises:
        ValueError: If API key is not set
    """
    key = get_api_key(name)
    if not key:
        env_var = _API_KEYS.get(name.upper(), f'{name}_API_KEY')
        raise ValueError(f"{env_var} not set")
    return key

