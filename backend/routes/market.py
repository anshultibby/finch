"""
Market data API — public endpoints for quotes, profiles, search, movers, news, and historical prices.
All FMP calls are synchronous, so we use asyncio.to_thread() to avoid blocking the event loop.
FMP responses are cached at the fmp() call layer (see scripts/api.py).
"""
import asyncio
from fastapi import APIRouter, HTTPException, Query
from datetime import date, timedelta

router = APIRouter(prefix="/market", tags=["market"])


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
                iso = d.replace(" ", "T") if " " in d else d
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
        return data[0]
    if isinstance(data, dict) and data.get("symbol"):
        return data

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
        return []

    return data if isinstance(data, list) else []


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
async def get_earnings_calendar_endpoint():
    """Return upcoming earnings for the next 7 days."""
    from skills.financial_modeling_prep.scripts.earnings.earnings_calendar import get_earnings_calendar
    from datetime import datetime, timedelta

    today = datetime.now().strftime("%Y-%m-%d")
    end = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")

    try:
        data = await asyncio.to_thread(get_earnings_calendar, today, end)
    except Exception:
        return []

    if not isinstance(data, list):
        return []

    result = [
        {
            "symbol": e.get("symbol"),
            "date": e.get("date"),
            "time": e.get("time"),
            "epsEstimated": e.get("epsEstimated"),
            "revenueEstimated": e.get("revenueEstimated"),
        }
        for e in data
        if e.get("epsEstimated") is not None
    ][:20]
    return result


# ---------------------------------------------------------------------------
# 9. General market news
# ---------------------------------------------------------------------------

@router.get("/general-news")
async def get_general_news(limit: int = 10):
    """Return general stock market news."""
    from skills.financial_modeling_prep.scripts.api import fmp

    try:
        data = await asyncio.to_thread(fmp, f"/stock_news?limit={limit}")
    except Exception:
        return []

    if not isinstance(data, list):
        return []

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
