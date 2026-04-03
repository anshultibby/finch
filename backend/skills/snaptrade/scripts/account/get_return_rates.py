"""Get return rates for an account"""
from typing import Dict, Any
from skills.snaptrade.scripts._client import get_snaptrade_client


def get_return_rates(user_id: str, account_id: str) -> Dict[str, Any]:
    """
    Get time-weighted return rates for a specific account.

    Args:
        user_id: User's ID
        account_id: SnapTrade account ID

    Returns:
        dict with:
            - success (bool)
            - return_rates (dict): Return rate data

    Example:
        from skills.snaptrade.scripts.account.get_return_rates import get_return_rates
        result = get_return_rates('user-123', 'acct-456')
        print(result['return_rates'])
    """
    client = get_snaptrade_client()

    try:
        session = client._get_session(user_id)
        if not session or not session.is_connected:
            return {"success": False, "needs_auth": True, "error": "Not connected"}

        response = client.client.account_information.get_user_account_return_rates(
            user_id=session.snaptrade_user_id,
            user_secret=session.snaptrade_user_secret,
            account_id=account_id,
        )
        data = response.body if hasattr(response, "body") else response
        return {"success": True, "return_rates": data}
    except Exception as e:
        return {"success": False, "error": str(e)}
