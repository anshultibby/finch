"""Get details for a specific symbol by ticker"""
from typing import Dict, Any
from skills.snaptrade.scripts._client import get_snaptrade_client


def get_symbol_detail(ticker: str) -> Dict[str, Any]:
    """
    Get detailed info for a symbol by ticker.

    Args:
        ticker: Ticker symbol (e.g. "AAPL")

    Returns:
        dict with:
            - success (bool)
            - symbol (dict): Symbol detail (id, name, exchange, type, currency)

    Example:
        from skills.snaptrade.scripts.reference.get_symbol_detail import get_symbol_detail
        result = get_symbol_detail('AAPL')
        print(result['symbol'])
    """
    client = get_snaptrade_client()

    try:
        response = client.client.reference_data.get_symbols_by_ticker(query=ticker)
        data = response.body if hasattr(response, "body") else response
        return {"success": True, "symbol": data}
    except Exception as e:
        return {"success": False, "error": str(e)}
