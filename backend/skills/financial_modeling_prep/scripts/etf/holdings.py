"""ETF holdings (constituents) — uses SEC EDGAR N-PORT for historical accuracy, FMP as fallback."""
from typing import List, Optional
from ..api import fmp
from .._cache import cache_key as _ck, load_cache as _lc, save_cache as _sc

_CACHE_DIR = '/tmp/fmp_etf_holdings_cache'


def get_etf_holdings(symbol: str, date: Optional[str] = None) -> list:
    """
    Get the constituent holdings of an ETF.

    When a date is provided, tries SEC EDGAR N-PORT first (exact quarterly filings,
    free, authoritative) then falls back to FMP. FMP's /etf-holder endpoint ignores
    the date parameter and always returns today's composition, which introduces
    survivorship bias in historical simulations.

    Args:
        symbol: ETF ticker, e.g. 'QQQ', 'SPY', 'VTI'
        date:   Historical snapshot date 'YYYY-MM-DD'. ALWAYS pass this for simulations.

    Returns:
        List of dicts, each holding:
            asset            – ticker of the held stock
            name             – company name
            weightPercentage – weight in the ETF (as %, e.g. 8.23 = 8.23%)
            source           – 'edgar_nport' or 'fmp' (indicates data origin)

    Example:
        holdings = get_etf_holdings('QQQ', date='2025-01-02')
        # Returns Dec 31, 2024 N-PORT filing — exact weights, no survivorship bias
        df = pd.DataFrame(holdings)
        print(df.sort_values('weightPercentage', ascending=False).head(5))
    """
    if date:
        from .edgar_nport import get_etf_holdings_historical
        nport = get_etf_holdings_historical(symbol, date)
        if nport:
            return nport

    # FMP fallback (returns current holdings regardless of date)
    cache_key = _ck(symbol.upper(), date or 'current')
    cached = _lc(_CACHE_DIR, cache_key)
    if cached is not None:
        return cached

    result = fmp(f'/etf-holder/{symbol}', {})
    if isinstance(result, dict) and 'error' in result:
        return result
    if isinstance(result, list):
        _sc(_CACHE_DIR, cache_key, result)
        return result
    return {'error': f'Unexpected response format: {type(result)}', 'raw': result}


def get_etf_holdings_at_dates(symbol: str, dates: List[str]) -> dict:
    """
    Fetch ETF constituent snapshots at multiple dates efficiently.
    Used for reconstitution tracking in multi-period simulations.

    Args:
        symbol: ETF ticker
        dates:  List of 'YYYY-MM-DD' strings (e.g. quarterly dates)

    Returns:
        {date_str: holdings_list} — only includes dates where data was returned
    """
    results = {}
    for d in dates:
        holdings = get_etf_holdings(symbol, date=d)
        if isinstance(holdings, list) and holdings:
            results[d] = holdings
    return results
