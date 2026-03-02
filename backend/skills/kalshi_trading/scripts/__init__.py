"""
Kalshi Trading — CFTC-regulated prediction market trading.

Requires Kalshi API credentials (set in Settings > API Keys).
Market prices are in CENTS (0–100). Quantities are integer contracts.

Quick start:
    from skills.kalshi_trading.scripts.kalshi import (
        get_portfolio, get_events, get_market,
        place_order, get_orders, cancel_order,
    )
"""
from .kalshi import (
    get_balance,
    get_positions,
    get_portfolio,
    get_events,
    get_markets,
    get_market,
    get_orderbook,
    place_order,
    get_orders,
    cancel_order,
)

__all__ = [
    "get_balance",
    "get_positions",
    "get_portfolio",
    "get_events",
    "get_markets",
    "get_market",
    "get_orderbook",
    "place_order",
    "get_orders",
    "cancel_order",
]
