"""
Polymarket — read-only HTTP helpers for Gamma, CLOB, and Data APIs.

No credentials required. All responses are raw JSON.
Prices are floats in [0, 1] (0.515 = 51.5¢).
"""
from .polymarket import gamma, clob, data, get_sport_events, parse_outcomes

__all__ = ["gamma", "clob", "data", "get_sport_events", "parse_outcomes"]
