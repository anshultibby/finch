---
name: reddit
description: Social sentiment analysis from Reddit. Track trending stock mentions, sentiment scores, and discussion volume across subreddits.
homepage: https://reddit.com
metadata:
  emoji: "👾"
  category: sentiment
  is_system: true
  requires:
    env:
      - REDDIT_CLIENT_ID
      - REDDIT_CLIENT_SECRET
    bins: []
---

# Reddit Skill

Social sentiment analysis from Reddit discussions.

## Import Pattern

```python
from skills.reddit.scripts.get_trending_stocks import get_trending_stocks
```

## Get Trending Stocks

```python
from skills.reddit.scripts.get_trending_stocks import get_trending_stocks

# Get trending stocks with sentiment
trending = get_trending_stocks(limit=20)

for stock in trending['trending']:
    print(f"\n{stock['symbol']}: {stock['mentions']} mentions")
    print(f"  Sentiment: {stock['sentiment_score']:.2f} ({stock['sentiment_label']})")
    print(f"  Top subreddits: {', '.join(stock['subreddits'][:3])}")
    if stock['sample_titles']:
        print(f"  Example: \"{stock['sample_titles'][0]}\"")
```

## Sentiment Scoring

Sentiment is scored from -1.0 to +1.0:
- `> 0.2`: Bullish (positive discussions)
- `-0.2 to 0.2`: Neutral (mixed or factual)
- `< -0.2`: Bearish (negative discussions)

## Subreddit Sources

Data is aggregated from:
- r/wallstreetbets
- r/stocks
- r/investing
- r/pennystocks
- r/options
- r/securityanalysis
- r/daytrading
- r/algotrading

## When to Use This Skill

- User asks what's trending on Reddit or WallStreetBets
- User wants social sentiment for a stock before trading
- User asks "is Reddit bullish or bearish on X"
- User wants to detect meme stock momentum early
