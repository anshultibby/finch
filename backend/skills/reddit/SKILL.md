---
name: reddit
description: Reddit sentiment + community reading. Trending ticker mentions/sentiment, and search/read a specific community's actual posts & threads via the official Reddit API.
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

Two capabilities:
1. **Trending sentiment** (`get_trending_stocks`) — aggregate ticker mentions + sentiment
   via ApeWisdom. Keyless, no credentials needed.
2. **Community reading** (`reddit_api`) — search a subreddit and read its actual posts and
   comment threads via the **official Reddit Data API**. This is what feeds the
   `strategy_distiller` a community's own words. Needs `REDDIT_CLIENT_ID` /
   `REDDIT_CLIENT_SECRET` (register a *script* app at https://reddit.com/prefs/apps and set
   both in `backend/.env`). Free for non-commercial use at ~100 queries/min.

Ingestion posture: fetch live, use, discard — do **not** persist a redistributable corpus
(see `docs/community-strategies-research.md` §1a).

## Import Pattern

```python
from skills.reddit.scripts.get_trending_stocks import get_trending_stocks
from skills.reddit.scripts.reddit_api import search_community, get_community_posts, read_thread
```

## Community Reading (official Reddit API)

```python
from skills.reddit.scripts.reddit_api import search_community, get_community_posts, read_thread

# Search within a community
posts = search_community("thetagang", "wheel strategy rules", sort="top", time_filter="year", limit=25)

# Pull a community's top posts
top = get_community_posts("thetagang", sort="top", time_filter="month", limit=25)

# Read a full thread (post + top comments) — post_id is the 'id' from a result above
thread = read_thread(posts[0]["id"])
for c in thread["comments"][:10]:
    print(c["author"], c["score"], c["body"][:200])
```

Each post dict: `id, title, author, selftext, score, num_comments, created_utc, flair, permalink`.
`read_thread` adds `comments` (`author/body/score`). Listings cap at 1000 results.

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
