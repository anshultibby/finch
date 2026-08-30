"""Input gathering for the monitoring passes: holdings parsing + FMP quotes.

These were previously copy-pasted across portfolio_digest, ledger_review and
market_monitor (three near-identical quote fetchers, three holdings-CSV parsers,
three SPY fetches). One canonical copy each lives here.
"""
import asyncio
import csv
import io
from typing import Dict, List, Optional

from sqlalchemy import select

from core.database import get_db_session
from models.brokerage import UserWatchlist


def parse_holdings(holdings_csv: str) -> List[dict]:
    """Owned positions from a SnapTrade holdings CSV: [{symbol, quantity, value}].

    Drops rows with no symbol or a non-positive value (the shape used by the
    digest + widget tables, which only show holdings worth something).
    """
    holdings = []
    for row in csv.DictReader(io.StringIO(holdings_csv or "")):
        try:
            holdings.append({
                "symbol": (row.get("symbol") or "").upper(),
                "quantity": float(row.get("quantity") or 0),
                "value": float(row.get("value") or 0),
            })
        except (ValueError, TypeError):
            continue
    return [h for h in holdings if h["symbol"] and h["value"] > 0]


def holdings_qty(portfolio_data: dict) -> Dict[str, float]:
    """symbol -> quantity from a cached PortfolioHoldingsCache row (0 if unparseable)."""
    out: Dict[str, float] = {}
    holdings_csv = (portfolio_data or {}).get("holdings_csv") or ""
    try:
        for row in csv.DictReader(io.StringIO(holdings_csv)):
            sym = (row.get("symbol") or "").upper().strip()
            if not sym:
                continue
            try:
                out[sym] = float(row.get("quantity") or 0)
            except (TypeError, ValueError):
                out[sym] = 0.0
    except Exception:
        return {}
    return out


def symbols_from_portfolio_data(portfolio_data: dict) -> List[str]:
    """Just the symbols from a cached holdings row (for callers that ignore qty)."""
    return list(holdings_qty(portfolio_data).keys())


async def watchlist_symbols(user_id: str) -> List[str]:
    async with get_db_session() as db:
        result = await db.execute(
            select(UserWatchlist.symbol).where(UserWatchlist.user_id == user_id).distinct()
        )
        return [s.upper() for (s,) in result.all()]


async def batch_quotes(symbols: List[str], chunk_size: int = 50) -> Dict[str, dict]:
    """FMP /quote for a symbol list, chunked defensively. symbol(upper) -> quote."""
    from skills.financial_modeling_prep.scripts.api import fmp

    quotes: Dict[str, dict] = {}
    for i in range(0, len(symbols), chunk_size):
        chunk = ",".join(symbols[i:i + chunk_size])
        try:
            data = await asyncio.to_thread(fmp, f"/quote/{chunk}")
        except Exception:
            continue
        if isinstance(data, dict):
            data = [data]
        if isinstance(data, list):
            for q in data:
                if isinstance(q, dict) and q.get("symbol"):
                    quotes[q["symbol"].upper()] = q
    return quotes


async def spy_backdrop() -> Optional[dict]:
    """The S&P 500 (SPY) quote used as market context, or None."""
    return (await batch_quotes(["SPY"])).get("SPY")
