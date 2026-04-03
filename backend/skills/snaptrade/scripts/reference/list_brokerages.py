"""List all supported brokerages"""
from typing import Dict, Any
from skills.snaptrade.scripts._client import get_snaptrade_client


def list_brokerages() -> Dict[str, Any]:
    """
    List all brokerages supported by SnapTrade.

    Returns:
        dict with:
            - success (bool)
            - brokerages (list): Brokerage objects with id, name, status
            - count (int)

    Example:
        from skills.snaptrade.scripts.reference.list_brokerages import list_brokerages
        result = list_brokerages()
        for b in result['brokerages']:
            print(b.get('name'))
    """
    client = get_snaptrade_client()

    try:
        response = client.client.reference_data.list_all_brokerages()
        data = response.body if hasattr(response, "body") else response
        brokerages = data if isinstance(data, list) else [data]
        return {"success": True, "brokerages": brokerages, "count": len(brokerages)}
    except Exception as e:
        return {"success": False, "error": str(e)}
