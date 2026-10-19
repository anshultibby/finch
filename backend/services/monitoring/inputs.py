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


async def symbols_by_user(require_device: bool = True) -> Dict[str, Dict[str, set]]:
    """user_id -> {"owned": {...}, "watched": {...}} for recently-active users.

    Owned symbols come from the last PortfolioHoldingsCache row even if stale —
    only the symbol list is needed, and this avoids hammering SnapTrade.
    `require_device` limits to users with a push token (the market monitor only
    exists to push); the events watch also writes to the ledger, so it doesn't.
    A registered device alone isn't evidence of a live user, so activity is
    always required too.
    """
    from models.brokerage import PortfolioHoldingsCache
    from models.user import DeviceToken
    from services.insight_model import filter_active_users

    async with get_db_session() as db:
        if require_device:
            rows = await db.execute(select(DeviceToken.user_id).distinct())
            candidates = {r[0] for r in rows.all()}
        else:
            w = await db.execute(select(UserWatchlist.user_id).distinct())
            h = await db.execute(select(PortfolioHoldingsCache.user_id).distinct())
            candidates = {r[0] for r in w.all()} | {r[0] for r in h.all()}
    user_ids = await filter_active_users(candidates)
    if not user_ids:
        return {}

    out: Dict[str, Dict[str, set]] = {uid: {"owned": set(), "watched": set()} for uid in user_ids}
    async with get_db_session() as db:
        rows = await db.execute(
            select(UserWatchlist.user_id, UserWatchlist.symbol).where(UserWatchlist.user_id.in_(user_ids))
        )
        for uid, sym in rows.all():
            out[uid]["watched"].add(sym.upper())
        rows = await db.execute(
            select(PortfolioHoldingsCache.user_id, PortfolioHoldingsCache.portfolio_data)
            .where(PortfolioHoldingsCache.user_id.in_(user_ids))
        )
        for uid, data in rows.all():
            out[uid]["owned"].update(symbols_from_portfolio_data(data))
    for v in out.values():
        v["watched"] -= v["owned"]
    return {uid: v for uid, v in out.items() if v["owned"] or v["watched"]}


async def owned_symbols(user_id: str) -> List[str]:
    """Symbols the user holds, from the last cached SnapTrade sync (no live call).
    Empty when they haven't connected a brokerage."""
    from models.brokerage import PortfolioHoldingsCache

    async with get_db_session() as db:
        rows = await db.execute(
            select(PortfolioHoldingsCache.portfolio_data).where(PortfolioHoldingsCache.user_id == user_id)
        )
        owned: set = set()
        for (data,) in rows.all():
            owned.update(symbols_from_portfolio_data(data))
    return sorted(owned)
