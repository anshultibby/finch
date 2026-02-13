"""Get institutional ownership from 13F SEC filings"""
from ..api import fmp


def _fetch_holders_for_date(symbol: str, date: str):
    """Fetch all pages of holders for a specific quarter end date."""
    all_holders = []
    page = 0
    while True:
        params = {'symbol': symbol, 'date': date, 'page': page}
        data = fmp('/institutional-ownership/institutional-holders/symbol-ownership-percent', params)
        if not data or isinstance(data, dict) and 'error' in data:
            break
        if isinstance(data, list):
            all_holders.extend(data)
            if len(data) < 50:
                break
        else:
            all_holders.append(data)
            break
        page += 1
        if page > 10:
            break
    return all_holders


def get_institutional_ownership(symbol: str, date: str = None):
    """
    Get institutional holders (hedge funds, mutual funds) from 13F filings.
    
    Shows the most recent filing per holder, matching how NASDAQ displays data.
    Merges the last two complete quarters plus any available current quarter filings.
    
    Args:
        symbol: Stock ticker (e.g., 'AAPL')
        date: Specific quarter end date (e.g., '2025-12-31'). If None, gets latest data.
        
    Returns:
        List of dicts with holder details including sharesNumber, changeInSharesNumber, etc.
    """
    if date:
        # Specific date requested - just return that quarter's data
        return _fetch_holders_for_date(symbol, date)
    
    # Get quarterly summary to find available dates
    summary = fmp('/institutional-ownership/symbol-ownership', {'symbol': symbol})
    if not isinstance(summary, list) or not summary:
        return []
    
    # Get the two most recent complete quarters from summary
    dates = [s['date'] for s in summary[:2]]
    
    # Also try to get the next quarter (may have partial data from early filers)
    # Calculate next quarter end date from the most recent
    from datetime import datetime
    if dates:
        latest = datetime.strptime(dates[0], '%Y-%m-%d')
        year, month = latest.year, latest.month
        # Calculate next quarter end
        if month == 3:
            next_q_str = f'{year}-06-30'
        elif month == 6:
            next_q_str = f'{year}-09-30'
        elif month == 9:
            next_q_str = f'{year}-12-31'
        else:  # month == 12
            next_q_str = f'{year + 1}-03-31'
        dates.insert(0, next_q_str)
    
    holder_map = {}
    # Fetch older quarters first, then newer (so newer overwrites)
    for d in reversed(dates):
        holders = _fetch_holders_for_date(symbol, d)
        for h in holders:
            name = h.get('investorName', '').upper()
            if name:
                holder_map[name] = h
    
    return list(holder_map.values())


def get_institutional_ownership_summary(symbol: str, year: int = None, quarter: int = None):
    """
    Get summary of institutional ownership for a symbol.
    
    Args:
        symbol: Stock ticker (e.g., 'AAPL')
        year: Filing year (e.g., 2025)
        quarter: Filing quarter (1-4)
        
    Returns:
        Dict with investorsHolding, numberOf13Fshares, totalInvested, ownershipPercent, etc.
    """
    params = {'symbol': symbol}
    if year:
        params['year'] = year
    if quarter:
        params['quarter'] = quarter
    return fmp('/institutional-ownership/symbol-ownership', params)


def get_institutional_holders_list(limit: int = 100):
    """
    Get list of institutional investors that file 13F reports.
    
    Returns:
        List of dicts: cik, name, lastFilingDate
    """
    return fmp('/institutional-holders-list', {'limit': limit})
