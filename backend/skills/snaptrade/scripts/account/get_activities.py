"""Get transaction history (buys, sells, dividends, etc.)"""
from typing import Dict, Any, Optional
from skills.snaptrade.scripts._client import get_snaptrade_client


def get_activities(
    user_id: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    activity_type: Optional[str] = None,
    accounts: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Get transaction/activity history across accounts.

    Args:
        user_id: User's ID
        start_date: Optional start date (YYYY-MM-DD)
        end_date: Optional end date (YYYY-MM-DD)
        activity_type: Optional filter - "BUY", "SELL", "DIVIDEND", "INTEREST", "TRANSFER", "FEE"
        accounts: Optional comma-separated account IDs to filter

    Returns:
        dict with:
            - success (bool)
            - activities (list): Activity objects
            - count (int)

    Example:
        from skills.snaptrade.scripts.account.get_activities import get_activities
        result = get_activities('user-123', start_date='2025-01-01', activity_type='DIVIDEND')
        for a in result['activities']:
            print(a)
    """
    client = get_snaptrade_client()

    try:
        session = client._get_session(user_id)
        if not session or not session.is_connected:
            return {"success": False, "needs_auth": True, "error": "Not connected"}

        kwargs = {
            "user_id": session.snaptrade_user_id,
            "user_secret": session.snaptrade_user_secret,
        }
        if start_date:
            kwargs["start_date"] = start_date
        if end_date:
            kwargs["end_date"] = end_date
        if activity_type:
            kwargs["type"] = activity_type
        if accounts:
            kwargs["accounts"] = accounts

        response = client.client.transactions_and_reporting.get_activities(**kwargs)
        data = response.body if hasattr(response, "body") else response
        activities = data if isinstance(data, list) else [data]
        return {"success": True, "activities": activities, "count": len(activities)}
    except Exception as e:
        return {"success": False, "error": str(e)}
