"""
Widget data service — resolves a widget spec's tiles into render-ready data
payloads (the shapes in docs/widgets/spec.md §2.6).

Cost control (the whole reason this is server-side): raw source fetches are
cached in a module-level dict keyed by (source, params) with per-source TTLs and
per-key single-flight locks — the exact pattern as services/move_explainer.py.
Fifty widgets that all reference AAPL share one cached quote; N viewers polling a
public page share one upstream fetch. Transforms run AFTER the cache so that,
e.g., two tiles that both `series` AAPL but normalize differently still hit one
fetch.

Personal bindings (user_portfolio / user_watchlist) are per-viewer and bypass
the shared cache; with viewer_user_id=None (public page) they return an "empty"
shape that the renderer turns into a "connect your portfolio" CTA.
"""
import asyncio
import json
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import httpx

from utils.logger import get_logger

logger = get_logger(__name__)

# ── cache ──────────────────────────────────────────────────────────────────
_TTL_BY_SOURCE = {
    "quote": 60,
    "kalshi": 60,
    "series": 300,
    "news": 300,
    "fred": 3600,
}
_cache: Dict[str, Dict[str, Any]] = {}
_locks: Dict[str, asyncio.Lock] = {}

KALSHI_MARKET_URL = "https://api.elections.kalshi.com/trade-api/v2/markets/{ticker}"

# Where each tile's numbers come from, so a viewer can double-check the source.
SRC_FMP = {"label": "Financial Modeling Prep", "url": "https://site.financialmodelingprep.com"}
SRC_FRED = {"label": "FRED · St. Louis Fed", "url": "https://fred.stlouisfed.org"}
SRC_KALSHI = {"label": "Kalshi", "url": "https://kalshi.com"}
SRC_INLINE = {"label": "Computed in-app (snapshot)"}
SRC_PORTFOLIO = {"label": "Your connected accounts"}
SRC_WATCHLIST = {"label": "Your watchlist"}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _cache_key(source: str, params: dict) -> str:
    return f"{source}|{json.dumps(params, sort_keys=True, default=str)}"


async def _cached(source: str, params: dict, fetch):
    """Double-checked-locking single-flight cache around an async `fetch`."""
    ttl = _TTL_BY_SOURCE.get(source, 60)
    key = _cache_key(source, params)

    entry = _cache.get(key)
    if entry and (time.monotonic() - entry["at"]) < ttl:
        return entry["data"]

    lock = _locks.setdefault(key, asyncio.Lock())
    async with lock:
        entry = _cache.get(key)
        if entry and (time.monotonic() - entry["at"]) < ttl:
            return entry["data"]
        data = await fetch()
        _cache[key] = {"at": time.monotonic(), "data": data}
        if len(_cache) > 500:
            for k, _ in sorted(_cache.items(), key=lambda kv: kv[1]["at"])[:100]:
                _cache.pop(k, None)
        return data


# ── range helpers ──────────────────────────────────────────────────────────
def _range_to_days(rng: str) -> int:
    if rng == "YTD":
        return (_now() - datetime(_now().year, 1, 1, tzinfo=timezone.utc)).days + 1
    return {
        "1D": 2, "5D": 6, "1M": 31, "3M": 93, "6M": 186, "1Y": 366, "5Y": 1830,
    }.get(rng, 93)


def _downsample(points: List[dict], cap: int = 400) -> List[dict]:
    if len(points) <= cap:
        return points
    step = len(points) / cap
    return [points[int(i * step)] for i in range(cap)]


# ── fetchers (return the shape payloads) ────────────────────────────────────
async def _fetch_quote_table(symbols: List[str]) -> dict:
    from skills.financial_modeling_prep.scripts.market.quote import get_quote_snapshot

    data = await asyncio.to_thread(get_quote_snapshot, ",".join(symbols))
    if isinstance(data, dict):
        data = [data] if data.get("symbol") else []
    rows = []
    for q in data or []:
        if not isinstance(q, dict) or not q.get("symbol"):
            continue
        rows.append([
            q.get("symbol"),
            q.get("name") or q.get("symbol"),
            q.get("price"),
            round(float(q["change"]), 2) if q.get("change") is not None else None,
            round(float(q["changesPercentage"]), 2) if q.get("changesPercentage") is not None else None,
        ])
    return {
        "shape": "table",
        "columns": ["symbol", "name", "price", "change", "change_pct"],
        "rows": rows,
        "source": SRC_FMP,
        "asof": _now().isoformat(),
    }


async def _fetch_quote_number(symbol: str) -> dict:
    from skills.financial_modeling_prep.scripts.market.quote import get_quote_snapshot

    data = await asyncio.to_thread(get_quote_snapshot, symbol)
    q = data[0] if isinstance(data, list) and data else (data if isinstance(data, dict) else {})
    price = q.get("price")
    change = q.get("change")
    change_pct = q.get("changesPercentage")
    return {
        "shape": "number",
        "label": q.get("name") or symbol,
        "value": price,
        "delta": round(float(change), 2) if change is not None else None,
        "delta_pct": round(float(change_pct), 2) if change_pct is not None else None,
        "source": SRC_FMP,
        "asof": _now().isoformat(),
    }


async def _fetch_series(symbols: List[dict], rng: str) -> dict:
    from skills.financial_modeling_prep.scripts.market.historical_prices import (
        get_batch_historical_prices,
    )

    days = _range_to_days(rng)
    to_date = _now().date().isoformat()
    from_date = (_now().date() - timedelta(days=days)).isoformat()
    syms = [s["symbol"] for s in symbols]
    batch = await asyncio.to_thread(get_batch_historical_prices, syms, from_date, to_date)

    series = []
    for s in symbols:
        sym = s["symbol"]
        label = s.get("label") or sym
        prices = (batch.get(sym) or {}).get("prices", [])
        # FMP returns newest-first; we want oldest→newest for charting.
        pts = [
            {"t": p["date"], "v": p.get("close")}
            for p in reversed(prices)
            if p.get("close") is not None
        ]
        series.append({"label": label, "points": _downsample(pts)})
    return {"shape": "series", "series": series, "source": SRC_FMP, "asof": _now().isoformat()}


async def _fetch_news(query: Optional[str], symbols: Optional[List[str]], limit: int) -> dict:
    from skills.financial_modeling_prep.scripts.api import fmp

    items: List[dict] = []
    if symbols:
        data = await asyncio.to_thread(fmp, f"/stock_news?tickers={','.join(symbols)}&limit={limit}")
        raw = data if isinstance(data, list) else []
    else:
        # Thematic query: pull the latest news and keyword-filter by title/text.
        # (/general_news is empty on our FMP plan; /stock_news carries the feed.)
        data = await asyncio.to_thread(fmp, "/stock_news?limit=100")
        raw = data if isinstance(data, list) else []
        if query:
            terms = [t for t in query.lower().split() if len(t) > 2]
            filtered = [
                n for n in raw
                if isinstance(n, dict) and any(
                    t in (n.get("title", "") + " " + n.get("text", "")).lower() for t in terms
                )
            ]
            raw = filtered or raw  # fall back to latest if nothing matches

    for n in raw[:limit]:
        if not isinstance(n, dict) or not n.get("title"):
            continue
        items.append({
            "title": n.get("title"),
            "url": n.get("url"),
            "source": n.get("site") or n.get("publisher"),
            "published_at": n.get("publishedDate"),
            "image": n.get("image"),
        })
    return {"shape": "news", "items": items, "source": SRC_FMP, "asof": _now().isoformat()}


async def _fetch_kalshi(ticker: str) -> dict:
    url = KALSHI_MARKET_URL.format(ticker=ticker)
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        market = resp.json().get("market", {})
    last = market.get("last_price")
    yes_bid, yes_ask = market.get("yes_bid"), market.get("yes_ask")
    if last is not None:
        prob = last / 100.0
    elif yes_bid is not None and yes_ask is not None:
        prob = (yes_bid + yes_ask) / 200.0
    else:
        prob = None
    series_ticker = ticker.split("-")[0] if ticker else ""
    return {
        "shape": "odds",
        "prob": prob,
        "title": market.get("title") or market.get("subtitle") or ticker,
        "close_date": market.get("close_time"),
        "history": [],  # per-candle history is a v2 add
        "source": {"label": "Kalshi", "url": f"https://kalshi.com/markets/{series_ticker}" if series_ticker else "https://kalshi.com"},
        "asof": _now().isoformat(),
    }


async def _fetch_fred(series_id: str, rng: Optional[str]) -> dict:
    from skills.fred.scripts.series import get_series

    days = _range_to_days(rng or "1Y")
    start = (_now().date() - timedelta(days=days)).isoformat()
    data = await asyncio.to_thread(get_series, series_id, 5000, start)
    obs = data.get("observations", []) if isinstance(data, dict) else []
    pts = [{"t": o["date"], "v": o["value"]} for o in obs if o.get("value") is not None]
    return {
        "shape": "series",
        "series": [{"label": series_id.upper(), "points": _downsample(pts)}],
        "source": {"label": "FRED · St. Louis Fed", "url": f"https://fred.stlouisfed.org/series/{series_id.upper()}"},
        "asof": _now().isoformat(),
    }


# ── personal bindings (per-viewer, not shared-cached) ───────────────────────
_EMPTY_BINDING = {"shape": "empty", "reason": "connect_portfolio"}


async def _fetch_portfolio_table(viewer_user_id: Optional[str]) -> dict:
    if not viewer_user_id:
        return dict(_EMPTY_BINDING)
    from modules.tools.clients import snaptrade_tools
    from services.portfolio_digest import _parse_holdings, _batch_quotes

    try:
        portfolio = await snaptrade_tools.get_portfolio(viewer_user_id)
    except Exception:
        logger.exception("widget: portfolio fetch failed for %s", viewer_user_id)
        return dict(_EMPTY_BINDING)
    if not portfolio.get("success"):
        return dict(_EMPTY_BINDING)
    holdings = _parse_holdings(portfolio.get("holdings_csv", ""))
    if not holdings:
        return dict(_EMPTY_BINDING)

    quotes = await _batch_quotes([h["symbol"] for h in holdings])
    rows = []
    for h in holdings:
        q = quotes.get(h["symbol"], {})
        rows.append([
            h["symbol"],
            round(h["value"], 2),
            round(float(q["changesPercentage"]), 2) if q.get("changesPercentage") is not None else None,
        ])
    return {
        "shape": "table",
        "columns": ["symbol", "value", "change_pct"],
        "rows": rows,
        "source": SRC_PORTFOLIO,
        "asof": _now().isoformat(),
    }


async def _fetch_watchlist_table(viewer_user_id: Optional[str]) -> dict:
    if not viewer_user_id:
        return dict(_EMPTY_BINDING)
    from services.portfolio_digest import _watchlist_symbols

    symbols = await _watchlist_symbols(viewer_user_id)
    if not symbols:
        return {"shape": "empty", "reason": "empty_watchlist"}
    return await _fetch_quote_table(symbols[:30])


# ── inline (frozen snapshot) ────────────────────────────────────────────────
def _inline_payload(query: dict) -> dict:
    shape = query.get("shape")
    data = query.get("data")
    asof = query.get("asof") or _now().isoformat()
    if shape == "markdown":
        return {"shape": "markdown", "text": data if isinstance(data, str) else str(data), "source": SRC_INLINE, "asof": asof}
    if shape == "number":
        return {"shape": "number", **(data if isinstance(data, dict) else {"value": data}), "source": SRC_INLINE, "asof": asof}
    if shape == "series":
        return {"shape": "series", "series": data, "source": SRC_INLINE, "asof": asof}
    if shape == "table":
        payload = {"shape": "table", "source": SRC_INLINE, "asof": asof}
        payload.update(data if isinstance(data, dict) else {"rows": data, "columns": []})
        return payload
    return {"shape": "error", "message": f"unknown inline shape '{shape}'"}


# ── transforms (post-fetch, in-process) ─────────────────────────────────────
def _first_nonnull(points: List[dict]) -> Optional[float]:
    for p in points:
        if p.get("v") is not None:
            return p["v"]
    return None


def _apply_transform(payload: dict, tf: dict) -> dict:
    op = tf.get("op")
    shape = payload.get("shape")

    if op in ("normalize", "pct_change") and shape == "series":
        base = tf.get("base", 100.0)
        out_series = []
        for s in payload.get("series", []):
            v0 = _first_nonnull(s.get("points", []))
            pts = []
            for p in s["points"]:
                v = p.get("v")
                if v is None or not v0:
                    pts.append({"t": p["t"], "v": None})
                elif op == "normalize":
                    pts.append({"t": p["t"], "v": round(v / v0 * base, 3)})
                else:  # pct_change
                    pts.append({"t": p["t"], "v": round((v / v0 - 1) * 100, 3)})
            out_series.append({"label": s["label"], "points": pts})
        return {**payload, "series": out_series}

    if op in ("spread", "ratio") and shape == "series":
        by_label = {s["label"]: s for s in payload.get("series", [])}
        a, b = by_label.get(tf.get("a")), by_label.get(tf.get("b"))
        if not a or not b:
            return {"shape": "error", "message": f"{op}: series '{tf.get('a')}' or '{tf.get('b')}' not found"}
        b_map = {p["t"]: p.get("v") for p in b["points"]}
        pts = []
        for p in a["points"]:
            va, vb = p.get("v"), b_map.get(p["t"])
            if va is None or vb is None or (op == "ratio" and not vb):
                pts.append({"t": p["t"], "v": None})
            else:
                pts.append({"t": p["t"], "v": round(va - vb if op == "spread" else va / vb, 4)})
        label = f"{tf['a']}{'−' if op == 'spread' else '/'}{tf['b']}"
        return {**payload, "series": [{"label": label, "points": pts}]}

    if op == "sort" and shape == "table":
        cols = payload.get("columns", [])
        by = tf.get("by")
        if by in cols:
            idx = cols.index(by)
            rows = payload.get("rows", [])
            # Nulls always sort last, regardless of direction (so `reverse`
            # doesn't flip them to the top).
            present = sorted(
                (r for r in rows if r[idx] is not None),
                key=lambda r: r[idx],
                reverse=tf.get("desc", True),
            )
            missing = [r for r in rows if r[idx] is None]
            return {**payload, "rows": [*present, *missing]}
        return payload

    if op == "limit":
        n = tf.get("n", 10)
        if shape == "table":
            return {**payload, "rows": payload.get("rows", [])[:n]}
        if shape == "news":
            return {**payload, "items": payload.get("items", [])[:n]}
    return payload


# ── tile resolution ─────────────────────────────────────────────────────────
async def _resolve_query(query: dict, viewer_user_id: Optional[str]) -> dict:
    source = query.get("source")

    if source == "inline":
        return _inline_payload(query)
    if source == "user_portfolio":
        return await _fetch_portfolio_table(viewer_user_id)
    if source == "user_watchlist":
        return await _fetch_watchlist_table(viewer_user_id)

    if source == "quote":
        symbols = query.get("symbols", [])
        params = {"symbols": symbols}
        # A single-symbol quote tile is usually a `stat`; return a number shape.
        if len(symbols) == 1:
            return await _cached("quote", {"n": symbols[0]}, lambda: _fetch_quote_number(symbols[0]))
        return await _cached("quote", params, lambda: _fetch_quote_table(symbols))
    if source == "series":
        symbols = query.get("symbols", [])
        rng = query.get("range", "3M")
        return await _cached("series", {"s": symbols, "r": rng}, lambda: _fetch_series(symbols, rng))
    if source == "news":
        q, syms, limit = query.get("query"), query.get("symbols"), query.get("limit", 8)
        return await _cached("news", {"q": q, "s": syms, "l": limit}, lambda: _fetch_news(q, syms, limit))
    if source == "kalshi":
        ticker = query.get("ticker")
        return await _cached("kalshi", {"t": ticker}, lambda: _fetch_kalshi(ticker))
    if source == "fred":
        sid, rng = query.get("series_id"), query.get("range")
        return await _cached("fred", {"s": sid, "r": rng}, lambda: _fetch_fred(sid, rng))

    return {"shape": "error", "message": f"unknown source '{source}'"}


async def _resolve_tile(tile: dict, viewer_user_id: Optional[str]) -> dict:
    query = tile.get("query")
    if not query:
        # Self-contained tile (e.g. a chart_spec figure with data baked in) —
        # nothing to fetch. The renderer uses tile.options directly.
        return {"shape": "static"}
    payload = await _resolve_query(query, viewer_user_id)
    if payload.get("shape") in ("error", "empty"):
        return payload
    for tf in tile.get("transforms") or []:
        payload = _apply_transform(payload, tf)
        if payload.get("shape") == "error":
            break
    return payload


async def resolve_widget_data(
    spec: dict, viewer_user_id: Optional[str] = None
) -> Dict[str, Any]:
    """Resolve every tile to its data payload. One bad tile becomes an `error`
    shape; it never blanks the whole widget."""
    tiles = spec.get("tiles", [])
    results = await asyncio.gather(
        *(_resolve_tile(t, viewer_user_id) for t in tiles),
        return_exceptions=True,
    )
    out: Dict[str, Any] = {}
    for tile, res in zip(tiles, results):
        if isinstance(res, Exception):
            logger.warning("widget tile '%s' failed: %s", tile.get("id"), res)
            out[tile["id"]] = {"shape": "error", "message": str(res)}
        else:
            out[tile["id"]] = res
    return out
