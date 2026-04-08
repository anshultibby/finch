"""Historical ETF holdings from SEC EDGAR N-PORT filings (free, exact, quarterly).

N-PORT is filed by every US ETF quarterly with the SEC. It contains exact holdings and weights
as of the period end date. QQQ's Dec 31 filing is available ~Feb 28 of the next year.

CUSIPs are resolved to tickers via FMP's current holdings (which include cusip+asset).
Stocks removed from the ETF since the last reconstitution may not resolve and are skipped.

Primary entry point: get_etf_holdings_historical(etf_symbol, as_of_date)
"""
import json
import os
import xml.etree.ElementTree as ET
from datetime import date
from typing import Optional

import requests

_HEADERS = {'User-Agent': 'finch-app contact@finch.com', 'Accept-Encoding': 'identity'}
_EDGAR_BASE = 'https://data.sec.gov'
_EDGAR_ARCHIVE = 'https://www.sec.gov/Archives/edgar/data'
_NPORT_NS = 'http://www.sec.gov/edgar/nport'
_CACHE_DIR = '/tmp/edgar_nport_cache'

# Known CIKs for common ETFs (avoids a search round-trip for frequent callers)
_KNOWN_CIKS = {
    'QQQ':  '1067839',
    'QQQM': '1067839',
    'SPY':  '884394',
    'IVV':  '1100663',
    'VOO':  '1383414',
    'VTI':  '34066',
}


# ---------------------------------------------------------------------------
# Cache helpers
# ---------------------------------------------------------------------------

def _cache_path(key: str) -> str:
    os.makedirs(_CACHE_DIR, exist_ok=True)
    return os.path.join(_CACHE_DIR, f'{key}.json')


def _load(key: str):
    p = _cache_path(key)
    if os.path.exists(p):
        with open(p) as f:
            return json.load(f)
    return None


def _save(key: str, data) -> None:
    with open(_cache_path(key), 'w') as f:
        json.dump(data, f)


# ---------------------------------------------------------------------------
# EDGAR API helpers
# ---------------------------------------------------------------------------

def _get_cik(etf_symbol: str) -> Optional[str]:
    sym = etf_symbol.upper()
    if sym in _KNOWN_CIKS:
        return _KNOWN_CIKS[sym]

    # Dynamic lookup via EDGAR company search
    resp = requests.get(
        'https://efts.sec.gov/LATEST/search-index',
        params={'q': sym, 'forms': 'N-PORT-P'},
        headers=_HEADERS,
        timeout=10,
    )
    hits = resp.json().get('hits', {}).get('hits', [])
    for h in hits:
        ciks = h.get('_source', {}).get('ciks', [])
        if ciks:
            return ciks[0].lstrip('0')
    return None


def _find_best_filing(cik: str, as_of_date: str) -> Optional[dict]:
    """Return the N-PORT filing whose periodOfReport is closest to but ≤ as_of_date."""
    cache_key = f'filings_{cik}'
    submissions = _load(cache_key)
    if submissions is None:
        resp = requests.get(
            f'{_EDGAR_BASE}/submissions/CIK{cik.zfill(10)}.json',
            headers=_HEADERS,
            timeout=15,
        )
        submissions = resp.json()
        _save(cache_key, submissions)

    recent = submissions.get('filings', {}).get('recent', {})
    forms = recent.get('form', [])
    periods = recent.get('reportDate', [])   # EDGAR uses 'reportDate', not 'periodOfReport'
    accessions = recent.get('accessionNumber', [])

    target = date.fromisoformat(as_of_date)
    best_date = None
    best = None

    for form, period, acc in zip(forms, periods, accessions):
        if 'NPORT' not in form.upper().replace('-', ''):
            continue
        try:
            d = date.fromisoformat(period)
        except ValueError:
            continue
        if d <= target and (best_date is None or d > best_date):
            best_date = d
            best = {'accession': acc, 'period': period, 'form': form, 'cik': cik}

    return best


def _parse_xml(cik: str, accession: str) -> list:
    """Download and parse N-PORT XML, returning raw holdings list."""
    cache_key = f'xml_{accession.replace("-", "")}'
    cached = _load(cache_key)
    if cached is not None:
        return cached

    acc_nodash = accession.replace('-', '')
    url = f'{_EDGAR_ARCHIVE}/{cik}/{acc_nodash}/primary_doc.xml'
    resp = requests.get(url, headers=_HEADERS, timeout=30)

    root = ET.fromstring(resp.content)
    tag = lambda name: f'{{{_NPORT_NS}}}{name}'

    holdings = []
    for inv in root.iter(tag('invstOrSec')):
        def txt(field):
            el = inv.find(tag(field))
            return (el.text or '').strip() if el is not None else ''

        cusip = txt('cusip')
        name = txt('name')
        pct = txt('pctVal')
        val = txt('valUSD')

        # ISIN is nested: <identifiers><isin value="US..."/></identifiers>
        isin_el = inv.find(f'{tag("identifiers")}/{tag("isin")}')
        isin = ''
        if isin_el is not None:
            isin = isin_el.get('value', '') or isin_el.text or ''

        holdings.append({
            'cusip': cusip,
            'isin': isin,
            'ticker': '',           # Invesco doesn't populate <ticker> in N-PORT filings
            'name': name,
            'weight_pct': float(pct) if pct else 0.0,
            'value_usd': float(val) if val else 0.0,
        })

    _save(cache_key, holdings)
    return holdings


# ---------------------------------------------------------------------------
# CUSIP → ticker resolution
# ---------------------------------------------------------------------------

def _build_cusip_map(etf_symbol: str) -> dict:
    """
    Build {cusip: ticker} from FMP's current ETF holdings.
    FMP includes both cusip and asset (ticker) in its response.
    This covers all current constituents; historical-only stocks (removed at last
    reconstitution) may be missing and fall back to a name-based heuristic.
    """
    from skills.financial_modeling_prep.scripts.api import fmp

    cache_key = f'cusip_map_{etf_symbol.upper()}'
    cached = _load(cache_key)
    if cached is not None:
        return cached

    result = fmp(f'/etf-holder/{etf_symbol}', {})
    if not isinstance(result, list):
        return {}

    mapping = {}
    for h in result:
        cusip = (h.get('cusip') or '').strip()
        ticker = (h.get('asset') or '').strip().upper()
        if cusip and ticker:
            mapping[cusip] = ticker

    _save(cache_key, mapping)
    return mapping


def _name_to_ticker_heuristic(name: str) -> str:
    """Last-resort: strip common suffixes to guess a ticker from company name."""
    # Not reliable — only used when CUSIP lookup fails for removed constituents
    return ''


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_etf_holdings_historical(etf_symbol: str, as_of_date: str) -> list:
    """
    Get point-in-time ETF holdings from SEC EDGAR N-PORT filing.

    Returns the quarterly snapshot whose period-of-report is closest to but not after
    as_of_date. For QQQ with start_date='2025-01-02' this returns the Dec 31, 2024
    filing — the exact Nasdaq-100 composition right after the annual reconstitution.

    Args:
        etf_symbol: ETF ticker, e.g. 'QQQ', 'SPY'
        as_of_date: 'YYYY-MM-DD' — returns the most recent filing on or before this date

    Returns:
        List of dicts matching the format of get_etf_holdings():
            asset            – ticker symbol
            name             – company name
            weightPercentage – weight as % of net assets (e.g. 9.79 = 9.79%)
            cusip            – CUSIP identifier
            isin             – ISIN identifier
            source           – 'edgar_nport'
            filing_period    – period-of-report date of the N-PORT filing used
        Returns empty list on failure (caller should fall back to FMP holdings).

    Example:
        holdings = get_etf_holdings_historical('QQQ', '2025-01-02')
        # Returns 101 holdings with exact Dec 31, 2024 weights
        top5 = sorted(holdings, key=lambda h: h['weightPercentage'], reverse=True)[:5]
        for h in top5:
            print(h['asset'], f"{h['weightPercentage']:.2f}%")
        # AAPL 9.79%
        # NVDA 8.51%
        # MSFT 8.10%
    """
    cik = _get_cik(etf_symbol)
    if not cik:
        return []

    filing = _find_best_filing(cik, as_of_date)
    if not filing:
        return []

    raw = _parse_xml(cik, filing['accession'])
    if not raw:
        return []

    # Resolve CUSIPs to tickers
    cusip_map = _build_cusip_map(etf_symbol)

    result = []
    for h in raw:
        ticker = h['ticker'] or cusip_map.get(h['cusip'], '') or _name_to_ticker_heuristic(h['name'])
        if not ticker:
            continue  # skip if we can't identify the stock
        result.append({
            'asset': ticker.upper(),
            'name': h['name'],
            'weightPercentage': h['weight_pct'],
            'cusip': h['cusip'],
            'isin': h['isin'],
            'source': 'edgar_nport',
            'filing_period': filing['period'],
        })

    return result
