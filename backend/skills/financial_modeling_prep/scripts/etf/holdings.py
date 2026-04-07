"""ETF holdings (constituents) from FMP"""
from ..api import fmp


def get_etf_holdings(symbol: str, date: str = None) -> list:
    """
    Get the constituent holdings of an ETF.

    Args:
        symbol: ETF ticker, e.g. 'QQQ', 'SPY', 'VTI'
        date:   Optional date 'YYYY-MM-DD' for historical snapshot (defaults to latest)

    Returns:
        List of dicts, each holding:
            asset           – ticker of the held stock
            name            – company name
            weightPercentage – weight in the ETF (as a decimal, e.g. 0.0823 = 8.23%)
            sharesNumber    – number of shares held
            marketValue     – market value of the position
            updated         – date of the filing

    Example:
        holdings = get_etf_holdings('QQQ')
        if not holdings or isinstance(holdings, dict):
            raise RuntimeError(f"Failed: {holdings}")

        import pandas as pd
        df = pd.DataFrame(holdings)
        df = df.sort_values('weightPercentage', ascending=False)
        print(df[['asset', 'name', 'weightPercentage']].head(20))
    """
    params = {'symbol': symbol}
    if date:
        params['date'] = date

    result = fmp('/etf-holder/' + symbol, params)

    if isinstance(result, dict) and 'error' in result:
        return result
    if isinstance(result, list):
        return result
    return {'error': f'Unexpected response format: {type(result)}', 'raw': result}
