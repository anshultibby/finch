"""
Market data API — public endpoints for quotes, profiles, search, movers, news, and historical prices.
All FMP calls are synchronous, so we use asyncio.to_thread() to avoid blocking the event loop.
FMP responses are cached at the fmp() call layer (see scripts/api.py).
"""
import asyncio
from fastapi import APIRouter, HTTPException, Query
from datetime import date, timedelta, datetime, time as dtime, timezone
from zoneinfo import ZoneInfo

router = APIRouter(prefix="/market", tags=["market"])

ET = ZoneInfo("America/New_York")


def _market_session() -> str:
    now = datetime.now(ET)
    if now.weekday() >= 5:
        return "closed"
    t = now.time()
    if dtime(4, 0) <= t < dtime(9, 30):
        return "pre"
    if dtime(9, 30) <= t < dtime(16, 0):
        return "regular"
    if dtime(16, 0) <= t < dtime(20, 0):
        return "after"
    return "closed"


# ---------------------------------------------------------------------------
# 1. Historical prices (% change series) — existing endpoint
# ---------------------------------------------------------------------------

@router.get("/prices")
async def get_prices(symbols: str, days: int = 365):
    """
    Return normalized price series (% change from window-start anchor) for up to 5 symbols.

    For short windows (≤7 days) we use FMP intraday bars (5min / 30min) and anchor the
    baseline to the last close *before* the window — so the 1D chart's last-point %
    matches the "Today +X%" shown in the quote header.

    Query params:
        symbols  – comma-separated tickers, e.g. "AAPL,QQQ"
        days     – lookback in calendar days (default 365)

    Returns:
        { symbol: [{ date, pct }, ...] }
    """
    ticker_list = [s.strip().upper() for s in symbols.split(",") if s.strip()]
    if not ticker_list or len(ticker_list) > 5:
        raise HTTPException(status_code=400, detail="Provide 1–5 comma-separated symbols")

    if days <= 1:
        interval = "5min"
    elif days <= 7:
        interval = "30min"
    else:
        interval = None

    today = date.today()
    cutoff = (today - timedelta(days=days)).isoformat()
    pad = 10 if interval is None else 7
    from_date = (today - timedelta(days=days + pad)).isoformat()
    to_date = today.isoformat()

    from skills.financial_modeling_prep.scripts.api import fmp
    from skills.financial_modeling_prep.scripts.market.historical_prices import get_historical_prices

    def _partition(bars: list, cutoff_day: str, date_key: str, close_keys: tuple):
        """Split oldest-first bars around cutoff_day. Base = last pre-cutoff close."""
        base = None
        in_window: list[tuple[str, float]] = []
        for b in bars:
            d = b.get(date_key, "")
            c = next((b[k] for k in close_keys if b.get(k) is not None), None)
            if c is None or not d:
                continue
            if d[:10] < cutoff_day:
                base = c
            else:
                if " " in d:
                    iso = d.replace(" ", "T") + "Z"
                else:
                    iso = d
                in_window.append((iso, c))
        return base, in_window

    def _normalize(bars: list, date_key: str = "date", close_keys: tuple = ("adjClose", "close")) -> list:
        base, in_window = _partition(bars, cutoff, date_key, close_keys)
        # Pre-market / weekend fallback: cutoff can be today with no bars yet. Roll
        # back to the most recent trading day present in the data.
        if not in_window:
            latest_day = max(
                (b[date_key][:10] for b in bars if b.get(date_key)),
                default=None,
            )
            if latest_day and latest_day < cutoff:
                base, in_window = _partition(bars, latest_day, date_key, close_keys)
        if base is None and in_window:
            base = in_window[0][1]
        if not in_window or not base:
            return []
        return [{"date": d, "pct": round((c / base - 1) * 100, 2)} for d, c in in_window]

    async def _fetch_daily(symbol: str) -> list:
        data = await asyncio.to_thread(
            get_historical_prices, symbol, from_date=from_date, to_date=to_date,
        )
        if not isinstance(data, dict) or "prices" not in data:
            return []
        return _normalize(list(reversed(data["prices"])))

    async def _fetch(symbol: str) -> list:
        try:
            if interval:
                raw = await asyncio.to_thread(
                    fmp, f"/historical-chart/{interval}/{symbol}",
                    {"from": from_date, "to": to_date, "extended": "true"},
                )
                if isinstance(raw, list) and raw:
                    normalized = _normalize(list(reversed(raw)))
                    if normalized:
                        return normalized
                # Intraday unavailable (empty response / API tier) — fall back to daily.
            return await _fetch_daily(symbol)
        except Exception:
            return []

    series = await asyncio.gather(*(_fetch(s) for s in ticker_list))
    return dict(zip(ticker_list, series))


# ---------------------------------------------------------------------------
# 2. Real-time quote for a single symbol
# ---------------------------------------------------------------------------

@router.get("/quote/{symbol}")
async def get_quote(symbol: str):
    """Return real-time quote data for a single symbol, or 404 if not found."""
    sym = symbol.upper()
    from skills.financial_modeling_prep.scripts.market.quote import get_quote_snapshot

    try:
        data = await asyncio.to_thread(get_quote_snapshot, sym)
    except Exception:
        raise HTTPException(status_code=502, detail="Failed to fetch quote")

    if isinstance(data, list) and len(data) > 0:
        result = data[0]
    elif isinstance(data, dict) and data.get("symbol"):
        result = data
    else:
        result = None

    if result:
        result["marketSession"] = _market_session()
        return result

    # Fallback: try profile endpoint which also has price
    try:
        from skills.financial_modeling_prep.scripts.company.profile import get_profile
        profile = await asyncio.to_thread(get_profile, sym)
        if isinstance(profile, list) and profile:
            profile = profile[0]
        if isinstance(profile, dict) and profile.get("price"):
            result = {
                "symbol": sym,
                "name": profile.get("companyName", ""),
                "price": profile.get("price", 0),
                "change": profile.get("changes", 0),
                "changesPercentage": round((profile.get("changes", 0) / (profile.get("price", 1) - profile.get("changes", 0))) * 100, 2) if profile.get("price") else 0,
                "marketCap": profile.get("mktCap", 0),
                "volume": profile.get("volAvg", 0),
                "exchange": profile.get("exchangeShortName", ""),
            }
            return result
    except Exception:
        pass

    raise HTTPException(status_code=404, detail=f"No quote found for {sym}")


# ---------------------------------------------------------------------------
# 3. Company profile
# ---------------------------------------------------------------------------

@router.get("/profile/{symbol}")
async def get_company_profile(symbol: str):
    """Return company profile (sector, market cap, description, CEO, etc.)."""
    sym = symbol.upper()
    from skills.financial_modeling_prep.scripts.company.profile import get_profile

    try:
        data = await asyncio.to_thread(get_profile, sym)
    except Exception:
        raise HTTPException(status_code=502, detail="Failed to fetch profile")

    # FMP returns a list for profile as well
    if isinstance(data, list) and len(data) > 0:
        return data[0]
    if isinstance(data, dict):
        return data
    raise HTTPException(status_code=404, detail=f"No profile found for {sym}")


# ---------------------------------------------------------------------------
# 4. Stock search
# ---------------------------------------------------------------------------

@router.get("/search")
async def search_stocks(q: str = Query(..., min_length=1), limit: int = 10):
    """Search companies by name or ticker symbol."""
    from skills.financial_modeling_prep.scripts.search.search import search

    try:
        data = await asyncio.to_thread(search, q, limit=limit)
    except Exception:
        data = []

    # call_fmp_api unwraps single-item lists to a bare dict — normalize back
    if isinstance(data, dict) and "symbol" in data:
        results = [data]
    elif isinstance(data, list):
        results = data
    else:
        results = []
    query_upper = q.strip().upper()

    # If query looks like an exact ticker, check if it's already in results
    # If not, try a direct quote lookup and prepend it
    if query_upper.isalpha() and len(query_upper) <= 6:
        already_found = any(
            r.get("symbol", "").upper() == query_upper for r in results
        )
        if not already_found:
            from skills.financial_modeling_prep.scripts.api import fmp

            try:
                quote = await asyncio.to_thread(fmp, f"/quote/{query_upper}")
                if isinstance(quote, list) and quote:
                    item = quote[0]
                    results.insert(0, {
                        "symbol": item.get("symbol", query_upper),
                        "name": item.get("name", ""),
                        "exchangeShortName": item.get("exchange", ""),
                    })
            except Exception:
                pass

    return results


# ---------------------------------------------------------------------------
# 5. Market movers (gainers, losers, most active)
# ---------------------------------------------------------------------------

@router.get("/movers")
async def get_market_movers():
    """Return today's top gainers, losers, and most active stocks (price > $5, max 10 each)."""
    from skills.financial_modeling_prep.scripts.market.gainers import get_gainers, get_losers, get_actives

    def _filter(items):
        if not isinstance(items, list):
            return []
        return [i for i in items if (i.get("price") or 0) > 5][:10]

    try:
        gainers, losers, actives = await asyncio.gather(
            asyncio.to_thread(get_gainers),
            asyncio.to_thread(get_losers),
            asyncio.to_thread(get_actives),
        )
    except Exception:
        return {"gainers": [], "losers": [], "actives": []}

    result = {
        "gainers": _filter(gainers),
        "losers": _filter(losers),
        "actives": _filter(actives),
    }
    return result


# ---------------------------------------------------------------------------
# 6. Stock news for a symbol
# ---------------------------------------------------------------------------

@router.get("/news/{symbol}")
async def get_stock_news(symbol: str, limit: int = 10):
    """Return recent news articles for a given stock symbol.

    For symbols (often ETFs) where FMP has no ticker-specific articles,
    fall back to general market news so the UI isn't blank.
    """
    from skills.financial_modeling_prep.scripts.api import fmp

    try:
        data = await asyncio.to_thread(fmp, f"/stock_news?tickers={symbol.upper()}&limit={limit}")
    except Exception:
        data = []

    if not isinstance(data, list):
        data = []

    if not data:
        try:
            data = await asyncio.to_thread(fmp, f"/stock_news?limit={limit}")
        except Exception:
            data = []
        if not isinstance(data, list):
            data = []

    return data


# ---------------------------------------------------------------------------
# 6b. Stock peers (related tickers)
# ---------------------------------------------------------------------------

@router.get("/peers/{symbol}")
async def get_stock_peers_endpoint(symbol: str, limit: int = 6):
    """Return peer tickers with name, price, and market cap (FMP stable)."""
    from skills.financial_modeling_prep.scripts.peers.stock_peers import get_stock_peers_detailed

    try:
        peers = await asyncio.to_thread(get_stock_peers_detailed, symbol.upper())
    except Exception:
        return []

    if not isinstance(peers, list):
        return []

    return [
        {
            "symbol": p.get("symbol"),
            "name": p.get("companyName"),
            "price": p.get("price"),
            "marketCap": p.get("mktCap"),
        }
        for p in peers
        if isinstance(p, dict) and p.get("symbol")
    ][:limit]


# ---------------------------------------------------------------------------
# 7. Batch quotes (multiple symbols in one call)
# ---------------------------------------------------------------------------

@router.get("/batch-quotes")
async def get_batch_quotes(symbols: str = Query(..., description="Comma-separated tickers, e.g. AAPL,MSFT,GOOGL")):
    """Return real-time quotes for multiple symbols at once."""
    cleaned = ",".join(s.strip().upper() for s in symbols.split(",") if s.strip())
    if not cleaned:
        raise HTTPException(status_code=400, detail="Provide at least one symbol")

    from skills.financial_modeling_prep.scripts.market.quote import get_quote_snapshot

    try:
        data = await asyncio.to_thread(get_quote_snapshot, cleaned)
    except Exception:
        return []

    return data if isinstance(data, list) else []


# ---------------------------------------------------------------------------
# 8. Earnings calendar
# ---------------------------------------------------------------------------

@router.get("/earnings")
async def get_earnings_calendar_endpoint(
    from_date: str = None,
    to_date: str = None,
    market: str = "us",
):
    """Return earnings calendar. Accepts optional from/to date params (YYYY-MM-DD) and market (us/india)."""
    from skills.financial_modeling_prep.scripts.earnings.earnings_calendar import get_earnings_calendar
    from datetime import datetime, timedelta

    if not from_date:
        from_date = datetime.now().strftime("%Y-%m-%d")
    if not to_date:
        to_date = (datetime.strptime(from_date, "%Y-%m-%d") + timedelta(days=7)).strftime("%Y-%m-%d")

    try:
        data = await asyncio.to_thread(get_earnings_calendar, from_date, to_date)
    except Exception:
        return []

    if not isinstance(data, list):
        return []

    import re
    if market == "india":
        ticker_re = re.compile(r'^[A-Z0-9]+\.(NS|BO)$')
    else:
        ticker_re = re.compile(r'^[A-Z]{1,4}(-[A-Z])?$')

    filtered = [
        {
            "symbol": e.get("symbol"),
            "name": e.get("name", ""),
            "date": e.get("date"),
            "time": e.get("time"),
            "eps": e.get("eps"),
            "epsEstimated": e.get("epsEstimated"),
            "revenue": e.get("revenue"),
            "revenueEstimated": e.get("revenueEstimated"),
        }
        for e in data
        if (e.get("epsEstimated") is not None or e.get("eps") is not None)
        and ticker_re.match(e.get("symbol") or "")
    ]

    filtered.sort(key=lambda x: (x["date"], -(x.get("revenue") or x.get("revenueEstimated") or 0)))
    return filtered


# ---------------------------------------------------------------------------
# 8b. Batch quotes
# ---------------------------------------------------------------------------

@router.get("/batch-quote")
async def get_batch_quote(symbols: str):
    """Return quotes for comma-separated symbols."""
    from skills.financial_modeling_prep.scripts.api import fmp

    syms = symbols.upper().strip()
    if not syms:
        return []

    try:
        data = await asyncio.to_thread(fmp, f"/quote/{syms}")
    except Exception:
        return []

    if not isinstance(data, list):
        return []

    return [
        {
            "symbol": q.get("symbol"),
            "name": q.get("name", ""),
            "price": q.get("price"),
            "change": q.get("change"),
            "changesPercentage": q.get("changesPercentage"),
            "previousClose": q.get("previousClose"),
            "marketCap": q.get("marketCap"),
        }
        for q in data
    ]


# ---------------------------------------------------------------------------
# 9. General market news
# ---------------------------------------------------------------------------

# Major NSE constituents used to source India-specific headlines, since FMP's
# general news feed is US-centric and doesn't filter by country.
INDIA_NEWS_TICKERS = [
    "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", "ICICIBANK.NS",
    "HINDUNILVR.NS", "SBIN.NS", "BHARTIARTL.NS", "ITC.NS", "KOTAKBANK.NS",
    "LT.NS", "AXISBANK.NS", "BAJFINANCE.NS", "ASIANPAINT.NS", "MARUTI.NS",
]


@router.get("/general-news")
async def get_general_news(limit: int = 10, market: str = "us"):
    """Return general stock market news.

    For India, FMP has no country-level general feed, so we query news for a
    basket of major NSE tickers and merge the results.
    """
    from skills.financial_modeling_prep.scripts.api import fmp

    try:
        if market == "india":
            tickers = ",".join(INDIA_NEWS_TICKERS)
            data = await asyncio.to_thread(fmp, f"/stock_news?tickers={tickers}&limit={limit}")
        else:
            data = await asyncio.to_thread(fmp, f"/stock_news?limit={limit}")
    except Exception:
        return []

    if not isinstance(data, list):
        return []

    # FMP returns multi-ticker results grouped by ticker; sort newest-first so
    # the merged India feed reads chronologically like the US feed.
    if market == "india":
        data.sort(key=lambda n: n.get("publishedDate") or "", reverse=True)
        data = data[:limit]

    return [
        {
            "title": n.get("title"),
            "url": n.get("url"),
            "image": n.get("image"),
            "publishedDate": n.get("publishedDate"),
            "site": n.get("site"),
            "symbol": n.get("symbol"),
            "text": (n.get("text") or "")[:200],
        }
        for n in data
    ]


# ---------------------------------------------------------------------------
# 10. Analyst consensus / price targets
# ---------------------------------------------------------------------------

@router.get("/analyst/{symbol}")
async def get_analyst_data(symbol: str):
    sym = symbol.upper()
    from skills.financial_modeling_prep.scripts.analyst.price_target import (
        get_price_target_consensus,
    )
    from skills.financial_modeling_prep.scripts.api import fmp

    try:
        consensus, grades = await asyncio.gather(
            asyncio.to_thread(get_price_target_consensus, sym),
            asyncio.to_thread(fmp, f"/grade/{sym}", {"limit": 100}),
        )
    except Exception:
        return {"consensus": None, "grades": None}

    grade_summary = None
    if isinstance(grades, list) and grades:
        counts = {"Buy": 0, "Neutral": 0, "Sell": 0}
        for g in grades:
            rec = (g.get("newGrade") or "").lower()
            if any(w in rec for w in ("buy", "overweight", "outperform", "strong buy")):
                counts["Buy"] += 1
            elif any(w in rec for w in ("sell", "underweight", "underperform")):
                counts["Sell"] += 1
            else:
                counts["Neutral"] += 1
        total = sum(counts.values())
        if total > 0:
            top = max(counts, key=lambda k: counts[k])
            grade_summary = {
                "buy": counts["Buy"],
                "neutral": counts["Neutral"],
                "sell": counts["Sell"],
                "total": total,
                "consensus": top,
            }

    cons = None
    if isinstance(consensus, list) and consensus:
        cons = consensus[0]
    elif isinstance(consensus, dict) and consensus:
        cons = consensus

    raw_grades = None
    if isinstance(grades, list) and grades:
        raw_grades = [
            {
                "firm": g.get("gradingCompany", ""),
                "analyst": g.get("analyst", ""),
                "rating": g.get("newGrade", ""),
                "previous": g.get("previousGrade", ""),
                "date": g.get("date", ""),
                "action": g.get("action", ""),
            }
            for g in grades[:30]
        ]

    return {"consensus": cons, "grades": grade_summary, "rawGrades": raw_grades}


# ---------------------------------------------------------------------------
# 11. Historical earnings (actual vs estimated)
# ---------------------------------------------------------------------------

@router.get("/earnings-history/{symbol}")
async def get_earnings_history(symbol: str, limit: int = 12):
    sym = symbol.upper()
    from skills.financial_modeling_prep.scripts.earnings.earnings_calendar import (
        get_historical_earnings,
    )

    try:
        data = await asyncio.to_thread(get_historical_earnings, sym)
    except Exception:
        return []

    if not isinstance(data, list):
        return []

    items = sorted(data, key=lambda x: x.get("date", ""))[-limit:]
    return [
        {
            "date": e.get("date"),
            "eps": e.get("eps"),
            "epsEstimated": e.get("epsEstimated"),
            "revenue": e.get("revenue"),
            "revenueEstimated": e.get("revenueEstimated"),
            "fiscalDateEnding": e.get("fiscalDateEnding"),
            "time": e.get("time"),
        }
        for e in items
    ]


# ---------------------------------------------------------------------------
# 12. Earnings transcript
# ---------------------------------------------------------------------------

@router.get("/earnings-transcript/{symbol}")
async def get_earnings_transcript(symbol: str, quarter: int = 4, year: int = 2025):
    sym = symbol.upper()
    from skills.financial_modeling_prep.scripts.api import fmp

    try:
        data = await asyncio.to_thread(
            fmp, f"/earning_call_transcript/{sym}", {"quarter": quarter, "year": year}
        )
    except Exception:
        return {"content": None}

    if isinstance(data, dict) and data.get("content"):
        return {"date": data.get("date"), "content": data["content"], "quarter": quarter, "year": year}
    if isinstance(data, list) and data:
        item = data[0]
        return {"date": item.get("date"), "content": item.get("content"), "quarter": quarter, "year": year}
    return {"content": None}


# ---------------------------------------------------------------------------
# 13. SEC filings
# ---------------------------------------------------------------------------

@router.get("/sec-filings/{symbol}")
async def get_sec_filings(symbol: str, type: str = None, limit: int = 20):
    sym = symbol.upper()
    from skills.financial_modeling_prep.scripts.api import fmp

    params = {"limit": limit}
    if type:
        params["type"] = type

    try:
        data = await asyncio.to_thread(fmp, f"/sec_filings/{sym}", params)
    except Exception:
        return []

    if not isinstance(data, list):
        return []

    return [
        {
            "fillingDate": e.get("fillingDate"),
            "type": e.get("type"),
            "link": e.get("link"),
            "finalLink": e.get("finalLink"),
        }
        for e in data
    ][:limit]


# ---------------------------------------------------------------------------
# 14. Financials — income statement, balance sheet, cash flow, key metrics, ratios
# ---------------------------------------------------------------------------

@router.get("/financials/{symbol}")
async def get_financials(
    symbol: str,
    statement: str = Query("income-statement", regex="^(key-stats|income-statement|balance-sheet|cash-flow|ratios)$"),
    period: str = Query("annual", regex="^(annual|quarter|ttm)$"),
    limit: int = 6,
):
    sym = symbol.upper()

    from skills.financial_modeling_prep.scripts.financials.income_statement import get_income_statement
    from skills.financial_modeling_prep.scripts.financials.balance_sheet import get_balance_sheet
    from skills.financial_modeling_prep.scripts.financials.cash_flow import get_cash_flow
    from skills.financial_modeling_prep.scripts.financials.key_metrics import get_key_metrics, get_key_metrics_ttm
    from skills.financial_modeling_prep.scripts.financials.ratios import get_ratios
    from skills.financial_modeling_prep.scripts.api import fmp

    def _merge_by_date(*sources):
        merged = {}
        for src in sources:
            if not isinstance(src, list):
                continue
            for item in src:
                d = item.get("date", "")
                if d not in merged:
                    merged[d] = {}
                merged[d].update(item)
        return sorted(merged.values(), key=lambda x: x.get("date", ""))

    # TTM = trailing 4 quarters shown individually
    actual_period = "quarter" if period == "ttm" else period
    actual_limit = 4 if period == "ttm" else limit

    # --- key-stats: merge income + cash flow + balance sheet + key metrics ---
    if statement == "key-stats":
        try:
            inc, cf, bs, km = await asyncio.gather(
                asyncio.to_thread(get_income_statement, sym, actual_period, actual_limit),
                asyncio.to_thread(get_cash_flow, sym, actual_period, actual_limit),
                asyncio.to_thread(get_balance_sheet, sym, actual_period, actual_limit),
                asyncio.to_thread(get_key_metrics, sym, actual_period, actual_limit),
            )
            return _merge_by_date(inc, cf, bs, km)
        except Exception:
            return []

    # --- Standard annual/quarter/ttm ---
    fetchers = {
        "income-statement": lambda: get_income_statement(sym, actual_period, actual_limit),
        "balance-sheet": lambda: get_balance_sheet(sym, actual_period, actual_limit),
        "cash-flow": lambda: get_cash_flow(sym, actual_period, actual_limit),
        "ratios": lambda: get_ratios(sym, actual_period, actual_limit),
    }

    try:
        data = await asyncio.to_thread(fetchers[statement])
    except Exception:
        return []

    return data if isinstance(data, list) else []


# ---------------------------------------------------------------------------
# 15. SEC citation deep-link resolver
# ---------------------------------------------------------------------------

@router.get("/sec-citation")
async def get_sec_citation(
    filing_url: str = Query(..., description="The finalLink URL to the iXBRL filing"),
    field: str = Query(..., description="FMP camelCase field name"),
):
    if not filing_url.startswith("https://www.sec.gov/"):
        raise HTTPException(status_code=400, detail="filing_url must be an SEC EDGAR URL")

    from skills.financial_modeling_prep.scripts.sec_citation import resolve_anchor

    try:
        result = await asyncio.to_thread(resolve_anchor, filing_url, field)
    except Exception:
        return {"anchor_id": None, "url": filing_url}

    if result is None:
        return {"anchor_id": None, "url": filing_url}

    return result
