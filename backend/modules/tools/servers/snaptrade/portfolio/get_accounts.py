"""Get user's connected brokerage accounts"""
from typing import Dict, Any, List
from servers.snaptrade._client import get_snaptrade_client


async def get_accounts(user_id: str) -> Dict[str, Any]:
    """
    Get list of user's connected brokerage accounts
    
    Args:
        user_id: User's ID in your system
        
    Returns:
        dict with:
            - success (bool): Whether fetch succeeded
            - accounts (list): List of account objects with:
                - id (str): Account ID
                - name (str): Account name
                - type (str): Account type (e.g., "INDIVIDUAL", "IRA")
                - balance (float): Total account value
                - institution (str): Brokerage name
            - error (str): Error message if any
            
    Example:
        result = await get_accounts('user-123')
        if result['success']:
            for acc in result['accounts']:
                print(f"{acc['institution']}: ${acc['balance']:,.2f}")
    """
    client = get_snaptrade_client()
    
    try:
        # Get session to check if connected
        session = client._get_session(user_id)
        if not session or not session.is_connected:
            return {
                "success": False,
                "needs_auth": True,
                "error": "User not connected to any brokerage"
            }
        
        # Fetch accounts from SnapTrade
        response = client.client.account_information.list_user_accounts(
            user_id=session.snaptrade_user_id,
            user_secret=session.snaptrade_user_secret
        )
        
        accounts = []
        for acc in response.body:
            accounts.append({
                "id": acc.get('id'),
                "name": acc.get('name', ''),
                "type": acc.get('type', ''),
                "balance": float(acc.get('balance', {}).get('total', 0)),
                "institution": acc.get('institution_name', '')
            })
        
        return {
            "success": True,
            "accounts": accounts,
            "count": len(accounts)
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

