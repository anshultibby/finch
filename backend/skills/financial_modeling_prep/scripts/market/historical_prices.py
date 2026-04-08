"""Historical daily OHLCV price data from FMP"""
from ..api import fmp
from .._cache import cache_key as _cache_key_fn, load_cache as _load_cache_fn, save_cache as _save_cache_fn

_CACHE_DIR = '/tmp/fmp_price_cache'


def _cache_key(symbol: str, from_date: str, to_date: str) -> str:
    return _cache_key_fn(symbol, from_date, to_date)


def _load_cache(key: str):
    return _load_cache_fn(_CACHE_DIR, key)


def _save_cache(key: str, data) -> None:
    _save_cache_fn(_CACHE_DIR, key, data)


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
    # Cache historical data (past dates never change) — skip cache for limit queries
    cache_key = None
    if from_date and to_date and not limit and ',' not in symbol:
        cache_key = _cache_key(symbol, from_date, to_date)
        cached = _load_cache(cache_key)
        if cached is not None:
            return cached

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
        out = {'symbol': symbol, 'prices': result['historical']}
        if cache_key:
            _save_cache(cache_key, out)
        return out
    if isinstance(result, dict) and 'historicalStockList' in result:
        # Batch response (comma-separated symbols) — return first symbol only
        first = result['historicalStockList'][0] if result['historicalStockList'] else {}
        return {'symbol': first.get('symbol', symbol), 'prices': first.get('historical', [])}

    return {'error': f'Unexpected response format: {type(result)}', 'raw': result}


def get_batch_historical_prices(
    symbols: list,
    from_date: str,
    to_date: str,
    batch_size: int = 25,
) -> dict:
    """
    Fetch historical prices for multiple symbols efficiently.

    Uses FMP batch endpoint (/historical-price-full/A,B,C) to minimize HTTP calls.
    Results are cached per-symbol for subsequent calls with the same date range.

    Args:
        symbols:    List of ticker symbols
        from_date:  Start date 'YYYY-MM-DD'
        to_date:    End date   'YYYY-MM-DD'
        batch_size: Symbols per batch request (FMP supports up to ~50, 25 is safe)

    Returns:
        dict: {symbol -> {'symbol': ..., 'prices': [...]}}
        Missing symbols are absent from the dict (not errors).

    Example:
        data = get_batch_historical_prices(['AAPL', 'MSFT', 'GOOGL'],
                                           from_date='2025-01-02', to_date='2025-12-31')
        for sym, hist in data.items():
            print(sym, len(hist['prices']), 'bars')
    """
    results: dict = {}
    uncached: list = []

    # Check cache first
    for sym in symbols:
        key = _cache_key(sym, from_date, to_date)
        cached = _load_cache(key)
        if cached is not None:
            results[sym] = cached
        else:
            uncached.append(sym)

    # Batch-fetch uncached symbols
    params = {'from': from_date, 'to': to_date}
    still_missing: list = []
    for i in range(0, len(uncached), batch_size):
        batch = uncached[i:i + batch_size]
        batch_str = ','.join(batch)
        raw = fmp(f'/historical-price-full/{batch_str}', params)

        if not isinstance(raw, dict):
            still_missing.extend(batch)
            continue

        entries = []
        if 'historicalStockList' in raw:
            entries = raw['historicalStockList']
        elif 'historical' in raw:
            # Single-symbol response format (batch of 1, or FMP fallback when only one has data)
            sym_key = raw.get('symbol', batch[0] if len(batch) == 1 else None)
            if sym_key:
                entries = [{'symbol': sym_key, 'historical': raw['historical']}]

        returned = set()
        for entry in entries:
            sym = entry.get('symbol', '')
            prices = entry.get('historical', [])
            if sym and prices:
                out = {'symbol': sym, 'prices': prices}
                results[sym] = out
                returned.add(sym)
                key = _cache_key(sym, from_date, to_date)
                _save_cache(key, out)

        # FMP batch endpoint silently drops some symbols — retry them individually
        still_missing.extend(s for s in batch if s not in returned)

    for sym in still_missing:
        raw = fmp(f'/historical-price-full/{sym}', params)
        if isinstance(raw, dict) and 'historical' in raw and raw['historical']:
            out = {'symbol': sym, 'prices': raw['historical']}
            results[sym] = out
            key = _cache_key(sym, from_date, to_date)
            _save_cache(key, out)

    return results
