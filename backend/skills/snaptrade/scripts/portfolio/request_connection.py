"""Request user to connect their brokerage account"""
from typing import Dict, Any
from servers.snaptrade._client import get_snaptrade_client


def request_connection(user_id: str) -> Dict[str, Any]:
    """
    Generate OAuth connection URL for user to connect brokerage
    
    Args:
        user_id: User's ID in your system
        
    Returns:
        dict with:
            - success (bool): Whether URL generation succeeded
            - connection_url (str): URL to redirect user to for OAuth
            - message (str): Instructions for user
            
    Example:
        result = request_connection('user-123')
        if result['success']:
            print(f"Connect at: {result['connection_url']}")
    
    Flow:
        1. Call this to get connection URL
        2. User visits URL and authenticates with brokerage
        3. SnapTrade redirects back to your callback URL
        4. Connection persists - no re-auth needed
    """
    client = get_snaptrade_client()
    
    try:
        # Generate connection URL
        redirect_url = client.get_oauth_url(user_id)
        
        return {
            "success": True,
            "connection_url": redirect_url,
            "message": "Visit the URL to securely connect your brokerage account via SnapTrade OAuth"
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

