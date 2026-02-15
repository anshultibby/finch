"""
Kalshi client helper - gets credentials from environment variables

In the code execution sandbox, credentials are passed via environment
variables (set by the parent process which fetches them from the database).
This avoids the subprocess needing direct database access.
"""
from typing import Optional, Tuple
import logging
from .._env import get_kalshi_credentials

logger = logging.getLogger(__name__)


def get_credentials() -> Tuple[Optional[str], Optional[str]]:
    """
    Get Kalshi credentials from environment variables.
    
    Returns:
        Tuple of (api_key_id, private_key) or (None, None) if not set
        
    Note: Returns raw strings for backward compatibility. The credentials
    are securely wrapped during retrieval from environment.
    """
    creds = get_kalshi_credentials()
    if not creds:
        return None, None
    
    # Extract raw values for the client
    return creds['api_key_id'].get(), creds['private_key'].get()


def create_client():
    """
    Create a new Kalshi client from environment credentials.
    
    Returns a fresh client each time to avoid event loop issues.
    The caller is responsible for closing the client.
    
    Returns:
        KalshiClient if credentials are set, None otherwise
    """
    api_key_id, private_key = get_credentials()
    
    if not api_key_id or not private_key:
        logger.debug("Kalshi credentials not found in environment")
        return None
    
    try:
        from modules.tools.clients.kalshi import KalshiClient
        return KalshiClient(api_key_id, private_key)
    except Exception as e:
        logger.error(f"Failed to create Kalshi client: {e}")
        return None


# Keep for backward compatibility
def get_client_sync(user_id: str = None):
    """Deprecated: Use create_client() instead"""
    return create_client()
