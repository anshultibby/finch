"""
Reddit - Social Sentiment & Trending Stocks

CAPABILITIES:
- Get trending stock tickers from Reddit (r/wallstreetbets, r/stocks, etc)
- Sentiment analysis and mention counts
- Track retail investor interest in stocks

KEY MODULES:
- get_trending_stocks: Top mentioned tickers with sentiment scores

USAGE PATTERN:
Data via ApeWisdom API. Returns list of tickers with mention counts and sentiment.
Useful for gauging retail sentiment and identifying meme stock momentum.
"""

from .get_trending_stocks import get_trending_stocks

__all__ = ['get_trending_stocks']

