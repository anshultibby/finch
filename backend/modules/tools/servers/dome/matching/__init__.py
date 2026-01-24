"""
Cross-platform Market Matching

Find the same events across Polymarket and Kalshi.
Useful for arbitrage and price comparison.
"""
from .sports import get_sports_matching_markets, get_sport_by_date

__all__ = ['get_sports_matching_markets', 'get_sport_by_date']
