"""Get stock peers — companies in the same sector/exchange with similar market cap."""
from ..api import fmp


def get_stock_peers(symbol: str):
    """
    Get peer companies for a given stock (same exchange, sector, similar market cap).

    Args:
        symbol: Stock ticker (e.g., 'AAPL')

    Returns:
        list[str]: List of peer ticker symbols (e.g., ['MSFT', 'NVDA', 'ADBE', ...])
    """
    result = fmp(f'/stock_peers?symbol={symbol}')
    if isinstance(result, dict) and 'peersList' in result:
        return result['peersList']
    if isinstance(result, list) and result and 'peersList' in result[0]:
        return result[0]['peersList']
    return result
