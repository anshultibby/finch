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

## Common Workflows

### Early Trend Detection

```python
def detect_emerging_trends(min_mentions=50, sentiment_threshold=0.3):
    """Find stocks gaining momentum on Reddit"""
    
    trending = get_trending_stocks(limit=50)
    
    emerging = []
    for stock in trending['trending']:
        if stock['mentions'] >= min_mentions and stock['sentiment_score'] >= sentiment_threshold:
            emerging.append({
                'symbol': stock['symbol'],
                'mentions': stock['mentions'],
                'sentiment': stock['sentiment_score'],
                'subreddits': stock['subreddits']
            })
    
    # Sort by combined score
    emerging.sort(key=lambda x: x['mentions'] * x['sentiment'], reverse=True)
    
    return emerging

# Usage
trends = detect_emerging_trends()
print("🔥 Emerging trends:")
for t in trends[:10]:
    print(f"  {t['symbol']}: {t['mentions']} mentions, {t['sentiment']:+.2f} sentiment")
```

### Contrarian Signals

```python
def find_contrarian_opportunities():
    """Find stocks with high negative sentiment (potential bounce)"""
    
    trending = get_trending_stocks(limit=50)
    
    contrarian = []
    for stock in trending['trending']:
        # High mentions but negative sentiment = potential oversold
        if stock['mentions'] >= 100 and stock['sentiment_score'] < -0.3:
            contrarian.append({
                'symbol': stock['symbol'],
                'mentions': stock['mentions'],
                'sentiment': stock['sentiment_score'],
                'signal': 'potential_oversold'
            })
    
    return contrarian

opportunities = find_contrarian_opportunities()
for opp in opportunities:
    print(f"📉 {opp['symbol']}: High negative buzz ({opp['sentiment']:+.2f}) - potential bounce?")
```

### Sentiment Correlation

```python
def analyze_sentiment_vs_price(symbols):
    """Compare Reddit sentiment to recent price action"""
    
    from skills.polygon_io.scripts.market.quote import get_snapshot
    from skills.reddit.scripts.get_trending_stocks import get_trending_stocks
    
    trending = get_trending_stocks(limit=100)
    trending_dict = {s['symbol']: s for s in trending['trending']}
    
    analysis = []
    for symbol in symbols:
        if symbol not in trending_dict:
            continue
        
        stock_data = trending_dict[symbol]
        snapshot = get_snapshot(symbol=symbol)
        
        # Calculate price change
        if 'error' not in snapshot:
            change_pct = (snapshot['price'] - snapshot['prev_close']) / snapshot['prev_close'] * 100
            
            analysis.append({
                'symbol': symbol,
                'sentiment': stock_data['sentiment_score'],
                'mentions': stock_data['mentions'],
                'price_change': change_pct,
                'alignment': 'aligned' if (stock_data['sentiment_score'] > 0 and change_pct > 0) or (stock_data['sentiment_score'] < 0 and change_pct < 0) else 'divergent'
            })
    
    return analysis

# Usage
results = analyze_sentiment_vs_price(["GME", "AMC", "TSLA", "NVDA"])
for r in results:
    emoji = "✅" if r['alignment'] == 'aligned' else "⚠️"
    print(f"{emoji} {r['symbol']}: Sentiment {r['sentiment']:+.2f}, Price {r['price_change']:+.1f}%")
```

### Hype Cycle Detection

```python
def detect_hype_cycles():
    """Identify stocks with unusually high mention volume"""
    
    trending = get_trending_stocks(limit=30)
    
    # Find outliers (top 10% mention counts)
    mentions = [s['mentions'] for s in trending['trending']]
    threshold = sorted(mentions, reverse=True)[int(len(mentions) * 0.1)]
    
    hype_stocks = [
        s for s in trending['trending']
        if s['mentions'] >= threshold
    ]
    
    print("🔥 High hype stocks (may indicate news/event):")
    for s in hype_stocks:
        emoji = "🟢" if s['sentiment_score'] > 0.2 else "🔴" if s['sentiment_score'] < -0.2 else "⚪"
        print(f"  {emoji} {s['symbol']}: {s['mentions']} mentions")
    
    return hype_stocks
```

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

## Sentiment Methodology

- **Natural Language Processing** on post titles and comments
- **Weighted by engagement** (upvotes, comments, awards)
- **Time-decayed** (recent discussions weighted higher)
- **Filtered** for spam and bot accounts

## Common Patterns

| Pattern | Description | Signal |
|---------|-------------|--------|
| Surge in mentions + positive | Organic interest building | Bullish |
| High mentions + negative | Backlash, sell-off, or controversy | Bearish |
| Low mentions but very positive | Quiet accumulation | Watchlist |
| Meme stock behavior | GME/AMC style pump | High volatility |

## Notes

- Data updates every 15-30 minutes
- Historical data not available (current snapshot only)
- Combine with price/volume analysis for confirmation
- Meme stocks can have extreme sentiment swings
- Not investment advice - use as one input among many

## When to Use This Skill

- User asks what's trending on Reddit or WallStreetBets
- User wants social sentiment for a stock before trading
- User asks "is Reddit bullish or bearish on X"
- User wants to detect meme stock momentum early
- Combine with `polygon_io` to correlate sentiment with price action
