"""
Seed a couple of real widgets for a user — QA fixtures and the first shareable
topical widgets. Run AFTER `alembic upgrade head` (needs the widgets table).

Usage:
    python -m scripts.seed_widgets --user <user_id> [--publish]
"""
import argparse
import asyncio

from core.database import get_db_session
from crud import widget as crud
from schemas.widget import WidgetSpec

HORMUZ = {
    "title": "Strait of Hormuz Tracker",
    "description": "Oil benchmarks, closure odds, tanker & defense names, and live headlines.",
    "emoji": "🛢️",
    "tags": ["oil", "geopolitics", "energy"],
    "spec": {
        "spec_version": 1,
        "tiles": [
            {"id": "oil", "type": "chart", "title": "Brent vs WTI", "size": "lg",
             "query": {"source": "series", "symbols": [{"symbol": "BZUSD", "label": "Brent"}, {"symbol": "CLUSD", "label": "WTI"}], "range": "3M"},
             "options": {"chart_type": "line"}},
            {"id": "brent", "type": "stat", "title": "Brent", "size": "sm",
             "query": {"source": "quote", "symbols": ["BZUSD"]}},
            {"id": "tankers", "type": "chart", "title": "Tankers & defense (indexed)", "size": "md",
             "query": {"source": "series", "symbols": [{"symbol": "FRO"}, {"symbol": "STNG"}, {"symbol": "LMT"}, {"symbol": "RTX"}], "range": "1M"},
             "transforms": [{"op": "normalize", "base": 100}]},
            {"id": "movers", "type": "table", "title": "Related names", "size": "md",
             "query": {"source": "quote", "symbols": ["FRO", "STNG", "TNK", "LMT", "RTX", "NOC", "XOM", "OXY"]},
             "transforms": [{"op": "sort", "by": "change_pct", "desc": True}]},
            {"id": "news", "type": "news", "title": "Latest", "size": "md",
             "query": {"source": "news", "query": "Strait of Hormuz oil", "limit": 8}},
            {"id": "context", "type": "text", "size": "full",
             "query": {"source": "inline", "shape": "markdown",
                       "data": "**Why this matters:** roughly 20% of global oil supply transits the Strait of Hormuz. Escalation shows up first in the Brent–WTI spread, tanker rates, and defense names."}},
        ],
        "refresh": {"interval_seconds": 60},
    },
}

GOLD_BTC = {
    "title": "Gold vs Bitcoin",
    "description": "The two 'debasement' trades, indexed to 100 this year.",
    "emoji": "🪙",
    "tags": ["gold", "bitcoin", "macro"],
    "spec": {
        "spec_version": 1,
        "tiles": [
            {"id": "cmp", "type": "chart", "title": "Gold vs Bitcoin (indexed, YTD)", "size": "lg",
             "query": {"source": "series", "symbols": [{"symbol": "GCUSD", "label": "Gold"}, {"symbol": "BTCUSD", "label": "Bitcoin"}], "range": "YTD"},
             "transforms": [{"op": "normalize", "base": 100}]},
            {"id": "gold", "type": "stat", "title": "Gold", "size": "sm",
             "query": {"source": "quote", "symbols": ["GCUSD"]}},
            {"id": "btc", "type": "stat", "title": "Bitcoin", "size": "sm",
             "query": {"source": "quote", "symbols": ["BTCUSD"]}},
        ],
        "refresh": {"interval_seconds": 60},
    },
}


async def seed(user_id: str, publish: bool) -> None:
    async with get_db_session() as db:
        for payload in (HORMUZ, GOLD_BTC):
            spec = WidgetSpec(**payload["spec"])
            w = await crud.create_widget(
                db, user_id,
                title=payload["title"], spec=spec, description=payload["description"],
                emoji=payload["emoji"], tags=payload["tags"],
            )
            if publish:
                w = await crud.publish_widget(db, w)
            print(f"  ✓ {w.title}  id={w.id}  slug={w.slug or '(private)'}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--user", required=True, help="user_id to own the seed widgets")
    ap.add_argument("--publish", action="store_true", help="publish them (mint public slugs)")
    args = ap.parse_args()
    asyncio.run(seed(args.user, args.publish))


if __name__ == "__main__":
    main()
