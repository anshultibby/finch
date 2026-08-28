"""
Reddit - Social Sentiment & Community Reading

CAPABILITIES:
- Get trending stock tickers from Reddit (aggregate mentions + sentiment, via ApeWisdom)
- Search a specific community and read its actual posts/threads (official Reddit API)

KEY MODULES:
- get_trending_stocks: Top mentioned tickers with sentiment scores (ApeWisdom, keyless)
- reddit_api: search_community / get_community_posts / read_thread — real post & comment
  TEXT from the official Reddit Data API (needs REDDIT_CLIENT_ID/SECRET). Use this to feed
  the strategy_distiller with a community's own words.

USAGE PATTERN:
Trending = quick aggregate sentiment. reddit_api = read what a community actually says.
Fetch live, use, discard — do not persist a corpus (see docs/community-strategies-research.md §1a).
"""

from .get_trending_stocks import get_trending_stocks
from .reddit_api import search_community, get_community_posts, read_thread, active_backend

__all__ = ['get_trending_stocks', 'search_community', 'get_community_posts', 'read_thread', 'active_backend']

