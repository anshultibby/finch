"""Get cash balances for a specific brokerage account"""
from typing import Dict, Any
from skills.snaptrade.scripts._client import get_snaptrade_client


def get_balances(user_id: str, account_id: str) -> Dict[str, Any]:
    """
    Get cash balances for a specific account.

    Args:
        user_id: User's ID
        account_id: SnapTrade account ID (from get_accounts)

    Returns:
        dict with:
            - success (bool)
            - balances (list): Each has currency, cash, buying_power

    Example:
        from skills.snaptrade.scripts.account.get_balances import get_balances
        result = get_balances('user-123', 'acct-456')
        for b in result['balances']:
            print(f"{b['currency']}: cash={b['cash']}, buying_power={b['buying_power']}")
    """
    client = get_snaptrade_client()

    try:
        session = client._get_session(user_id)
        if not session or not session.is_connected:
            return {"success": False, "needs_auth": True, "error": "Not connected"}

        response = client.client.account_information.get_user_account_balance(
            user_id=session.snaptrade_user_id,
            user_secret=session.snaptrade_user_secret,
            account_id=account_id,
        )
        data = response.body if hasattr(response, "body") else response
        balances = data if isinstance(data, list) else [data]
        return {"success": True, "balances": balances}
    except Exception as e:
        return {"success": False, "error": str(e)}
