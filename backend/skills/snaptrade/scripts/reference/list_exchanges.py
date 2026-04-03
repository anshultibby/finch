"""List stock exchanges"""
from typing import Dict, Any
from skills.snaptrade.scripts._client import get_snaptrade_client


def list_exchanges() -> Dict[str, Any]:
    """
    List all stock exchanges.

    Returns:
        dict with:
            - success (bool)
            - exchanges (list)

    Example:
        from skills.snaptrade.scripts.reference.list_exchanges import list_exchanges
        result = list_exchanges()
        for e in result['exchanges']:
            print(e)
    """
    client = get_snaptrade_client()

    try:
        response = client.client.reference_data.get_stock_exchanges()
        data = response.body if hasattr(response, "body") else response
        exchanges = data if isinstance(data, list) else [data]
        return {"success": True, "exchanges": exchanges}
    except Exception as e:
        return {"success": False, "error": str(e)}
