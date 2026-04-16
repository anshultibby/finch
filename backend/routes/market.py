"""
Lightweight market data endpoint for frontend charts.
Uses FMP historical prices (API key loaded from .env at startup).
"""
from fastapi import APIRouter, HTTPException
from datetime import date, timedelta

router = APIRouter(prefix="/market", tags=["market"])


@router.get("/prices")
async def get_prices(symbols: str, days: int = 365):
    """
    Return normalized daily price series (% change from first close) for up to 5 symbols.

    Query params:
        symbols  – comma-separated tickers, e.g. "AAPL,QQQ"
        days     – lookback in calendar days (default 365)

    Returns:
        { symbol: [{ date, pct }, ...] }
    """
    ticker_list = [s.strip().upper() for s in symbols.split(",") if s.strip()]
    if not ticker_list or len(ticker_list) > 5:
        raise HTTPException(status_code=400, detail="Provide 1–5 comma-separated symbols")

    from_date = (date.today() - timedelta(days=days + 10)).isoformat()
    to_date = date.today().isoformat()

    try:
        from skills.financial_modeling_prep.scripts.market.historical_prices import get_historical_prices
    except ImportError:
        raise HTTPException(status_code=503, detail="Price data module unavailable")

    result: dict = {}
    for symbol in ticker_list:
        try:
            data = get_historical_prices(symbol, from_date=from_date, to_date=to_date)
            if not isinstance(data, dict) or "prices" not in data:
                result[symbol] = []
                continue
            # FMP returns newest-first — reverse to chronological
            prices = list(reversed(data["prices"]))
            if not prices:
                result[symbol] = []
                continue
            base = prices[0].get("adjClose") or prices[0].get("close") or 1
            result[symbol] = [
                {"date": p["date"], "pct": round(((p.get("adjClose") or p.get("close", base)) / base - 1) * 100, 2)}
                for p in prices
            ]
        except Exception:
            result[symbol] = []

    return result
