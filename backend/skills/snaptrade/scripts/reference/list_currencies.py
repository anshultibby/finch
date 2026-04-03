"""List all supported currencies and exchange rates"""
from typing import Dict, Any
from skills.snaptrade.scripts._client import get_snaptrade_client


def list_currencies() -> Dict[str, Any]:
    """
    List all supported currencies.

    Returns:
        dict with:
            - success (bool)
            - currencies (list)

    Example:
        from skills.snaptrade.scripts.reference.list_currencies import list_currencies
        result = list_currencies()
        for c in result['currencies']:
            print(c)
    """
    client = get_snaptrade_client()

    try:
        response = client.client.reference_data.list_all_currencies()
        data = response.body if hasattr(response, "body") else response
        currencies = data if isinstance(data, list) else [data]
        return {"success": True, "currencies": currencies}
    except Exception as e:
        return {"success": False, "error": str(e)}


def get_exchange_rate(currency_pair: str) -> Dict[str, Any]:
    """
    Get exchange rate for a currency pair.

    Args:
        currency_pair: e.g. "USDCAD"

    Returns:
        dict with:
            - success (bool)
            - rate (dict): Exchange rate data

    Example:
        from skills.snaptrade.scripts.reference.list_currencies import get_exchange_rate
        result = get_exchange_rate('USDCAD')
        print(result['rate'])
    """
    client = get_snaptrade_client()

    try:
        response = client.client.reference_data.get_currency_exchange_rate_pair(
            currency_pair=currency_pair
        )
        data = response.body if hasattr(response, "body") else response
        return {"success": True, "rate": data}
    except Exception as e:
        return {"success": False, "error": str(e)}
