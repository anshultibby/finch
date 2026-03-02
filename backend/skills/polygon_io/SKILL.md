---
name: polygon_io
description: Stock market data from Polygon.io. Real-time and historical prices, intraday bars, company fundamentals, and market snapshots for US equities.
homepage: https://polygon.io
metadata:
  emoji: "📊"
  category: stock_data
  is_system: true
  requires:
    env:
      - POLYGON_API_KEY
    bins: []
---

# Polygon.io Skill

Real-time and historical stock market data from Polygon.io.

## Import Pattern

```python
from skills.polygon_io.scripts.market.intraday import get_intraday_bars, get_today_bars
from skills.polygon_io.scripts.market.historical_prices import get_historical_prices
from skills.polygon_io.scripts.market.quote import get_last_trade, get_last_quote, get_snapshot
```

## Intraday Bars

Get minute-by-minute price data:

```python
from skills.polygon_io.scripts.market.intraday import get_intraday_bars, get_today_bars
from datetime import datetime

# Get today's bars (1-minute)
bars = get_today_bars(symbol="AAPL", timespan="minute")
for bar in bars:
    print(f"{bar['timestamp']}: Open ${bar['open']}, High ${bar['high']}, Low ${bar['low']}, Close ${bar['close']}, Vol {bar['volume']}")

# Get historical intraday bars
bars = get_intraday_bars(
    symbol="TSLA",
    from_datetime="2026-01-15T09:30:00",
    to_datetime="2026-01-15T16:00:00",
    timespan="5m"  # 5-minute bars
)
```

## Historical Daily/Weekly/Monthly Prices

```python
from skills.polygon_io.scripts.market.historical_prices import get_historical_prices

# Get daily prices for 1 year
prices = get_historical_prices(
    symbol="NVDA",
    from_date="2025-01-01",
    to_date="2026-01-01",
    timespan="day"  # "day", "week", or "month"
)

# Calculate simple moving average
closes = [bar['close'] for bar in prices]
sma_20 = sum(closes[-20:]) / 20
print(f"20-day SMA: ${sma_20:.2f}")
```

## Real-time Quotes

```python
from skills.polygon_io.scripts.market.quote import get_last_trade, get_last_quote, get_snapshot

# Last trade info
trade = get_last_trade(symbol="MSFT")
print(f"Last trade: ${trade['price']} x {trade['size']} at {trade['timestamp']}")

# Current bid/ask
quote = get_last_quote(symbol="MSFT")
print(f"Bid: ${quote['bid']} x {quote['bid_size']}, Ask: ${quote['ask']} x {quote['ask_size']}")

# Full snapshot (price, stats, daily info)
snapshot = get_snapshot(symbol="MSFT")
print(f"Day open: ${snapshot['open']}, High: ${snapshot['high']}, Low: ${snapshot['low']}")
print(f"Volume: {snapshot['volume']}, VWAP: ${snapshot['vwap']}")
```

## Common Workflows

### Screen Stocks by Price Movement

```python
# Get gainers/losers (requires different endpoint - use financial_modeling_prep skill)
# Then get detailed price action from Polygon
for symbol in ["AAPL", "NVDA", "TSLA"]:
    snapshot = get_snapshot(symbol=symbol)
    change_pct = (snapshot['price'] - snapshot['prev_close']) / snapshot['prev_close'] * 100
    print(f"{symbol}: ${snapshot['price']} ({change_pct:+.2f}%)")
```

### Backtest a Strategy

```python
# Get historical data
prices = get_historical_prices(symbol="SPY", from_date="2020-01-01", to_date="2026-01-01", timespan="day")

# Calculate signals and backtest
# (see strategy skill for backtesting patterns)
```

### Monitor Intraday Trends

```python
# Get today's 5-minute bars
bars = get_today_bars(symbol="QQQ", timespan="5m")

# Find trend: compare first half to second half of day
mid = len(bars) // 2
first_half = sum(b['close'] for b in bars[:mid]) / mid
second_half = sum(b['close'] for b in bars[mid:]) / (len(bars) - mid)

if second_half > first_half * 1.01:
    print("Trending higher in afternoon")
elif second_half < first_half * 0.99:
    print("Trending lower in afternoon")
else:
    print("Sideways action")
```

## Error Handling

Polygon returns empty lists or error dicts on failure:

```python
result = get_last_trade(symbol="INVALID")
if isinstance(result, dict) and 'error' in result:
    print(f"Error: {result['error']}")
```

## Models Reference

See `polygon_io/models.py` for complete Pydantic models:
- `PolygonBar` - OHLCV bar data
- `PolygonTrade` - Last trade details
- `PolygonQuote` - Bid/ask data
- `PolygonSnapshot` - Full market snapshot

## When to Use This Skill

- User asks for a stock's current price, intraday chart, or quote
- User wants historical OHLCV data for backtesting or charting
- User asks about today's price action, volume, or VWAP
- User wants to compare intraday performance across multiple stocks
- Combine with `financial_modeling_prep` for fundamentals and with `tradingview` for technical signals
