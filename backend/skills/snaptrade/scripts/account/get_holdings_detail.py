"""Get detailed holdings for a specific account (positions + balances + orders)"""
from typing import Dict, Any
from skills.snaptrade.scripts._client import get_snaptrade_client


def get_holdings_detail(user_id: str, account_id: str) -> Dict[str, Any]:
    """
    Get detailed holdings for a single account including positions, balances, and open orders.

    Args:
        user_id: User's ID
        account_id: SnapTrade account ID

    Returns:
        dict with:
            - success (bool)
            - holdings (dict): Full holdings data from SnapTrade

    Example:
        from skills.snaptrade.scripts.account.get_holdings_detail import get_holdings_detail
        result = get_holdings_detail('user-123', 'acct-456')
        if result['success']:
            h = result['holdings']
            print(h)  # positions, balances, orders all in one
    """
    client = get_snaptrade_client()

    try:
        session = client._get_session(user_id)
        if not session or not session.is_connected:
            return {"success": False, "needs_auth": True, "error": "Not connected"}

        response = client.client.account_information.get_user_holdings(
            user_id=session.snaptrade_user_id,
            user_secret=session.snaptrade_user_secret,
            account_id=account_id,
        )
        data = response.body if hasattr(response, "body") else response
        return {"success": True, "holdings": data}
    except Exception as e:
        return {"success": False, "error": str(e)}
