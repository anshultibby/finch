"""Historical daily OHLCV price data from FMP"""
from ..api import fmp


def get_historical_prices(symbol: str, from_date: str = None, to_date: str = None, limit: int = None) -> dict:
    """
    Get daily historical OHLCV prices for a stock or ETF.

    Args:
        symbol:    Ticker symbol, e.g. 'AAPL', 'QQQ'
        from_date: Start date 'YYYY-MM-DD' (optional)
        to_date:   End date   'YYYY-MM-DD' (optional)
        limit:     Max number of bars to return (optional, newest first)

    Returns:
        dict with keys:
            symbol  – ticker
            prices  – list of dicts (newest first), each:
                        date, open, high, low, close, adjClose,
                        volume, unadjustedVolume, change, changePercent,
                        vwap, label, changeOverTime

    Example:
        data = get_historical_prices('QQQ', from_date='2025-01-01', to_date='2025-12-31')
        if 'error' in data:
            print(data['error'])
        else:
            import pandas as pd
            df = pd.DataFrame(data['prices'])
            df['date'] = pd.to_datetime(df['date'])
            df = df.sort_values('date')
            print(df[['date', 'close']].tail())
    """
    params = {}
    if from_date:
        params['from'] = from_date
    if to_date:
        params['to'] = to_date
    if limit:
        params['timeseries'] = limit

    result = fmp(f'/historical-price-full/{symbol}', params)

    if isinstance(result, dict) and 'error' in result:
        return result
    if isinstance(result, dict) and 'historical' in result:
        return {'symbol': symbol, 'prices': result['historical']}
    if isinstance(result, dict) and 'historicalStockList' in result:
        # batch response — return first symbol
        first = result['historicalStockList'][0] if result['historicalStockList'] else {}
        return {'symbol': first.get('symbol', symbol), 'prices': first.get('historical', [])}

    return {'error': f'Unexpected response format: {type(result)}', 'raw': result}
