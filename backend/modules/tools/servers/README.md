# API Servers

Progressive disclosure for external APIs. Each tool is a Python file with clean docstrings.

## Available Servers

- **financial_modeling_prep/** - Financial Modeling Prep (stocks, financials, market data)
- **polygon_io/** - Polygon.io (historical prices, quotes)
- **reddit/** - Reddit sentiment (trending stocks)
- **snaptrade/** - SnapTrade (secure portfolio access via OAuth)
- **tradingview/** - TradingView (technical analysis, interactive charts)

**Note:** Web search and scraping are now first-order tools (`web_search`, `news_search`, `scrape_url`).

## Quick Reference

### Intraday Price Data (for backtesting/strategies)

```python
from servers.polygon_io.market.intraday import get_intraday_bars

response = get_intraday_bars(
    symbol='NVDA',              # Stock ticker (required)
    from_datetime='2024-12-01', # Start date YYYY-MM-DD (required)
    to_datetime='2024-12-31',   # End date YYYY-MM-DD (required)
    timespan='15min'            # '1min', '5min', '15min', '30min', '1hour'
)

# Response structure:
# {
#     'symbol': 'NVDA',
#     'from': '2024-12-01',
#     'to': '2024-12-31',
#     'timespan': '15min',
#     'count': 1234,
#     'bars': [
#         {'timestamp': 1704067200000, 'date': '2024-12-01 09:30:00',
#          'open': 495.0, 'high': 496.5, 'low': 494.2, 'close': 495.8,
#          'volume': 123456, 'vwap': 495.5, 'trades': 1234},
#         ...
#     ]
# }

# Convert to DataFrame:
import pandas as pd
df = pd.DataFrame(response['bars'])
df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
```

### Historical Daily Prices

```python
from servers.polygon_io.market.historical_prices import get_historical_prices

response = get_historical_prices(
    symbol='AAPL',              # Stock ticker (required)
    from_date='2024-01-01',     # Start date YYYY-MM-DD (required)
    to_date='2024-12-31',       # End date YYYY-MM-DD (required)
    timespan='day',             # 'day', 'week', 'month' (default='day')
    multiplier=1                # Timespan multiplier (default=1)
)

df = pd.DataFrame(response['bars'])
```

### Stock Quote with Fundamentals (FMP)

```python
from servers.financial_modeling_prep.market.quote import get_quote_snapshot

# IMPORTANT: Returns a LIST even for single stock!
quotes = get_quote_snapshot('AAPL')
quote = quotes[0]  # Access first result

# Available fields:
# symbol, name, price, change, changesPercentage,
# dayLow, dayHigh, yearLow, yearHigh, volume, avgVolume,
# marketCap, pe, eps, open, previousClose, exchange
```

### Market Movers

```python
from servers.financial_modeling_prep.market.gainers import get_gainers, get_losers, get_actives

gainers = get_gainers()

# IMPORTANT: Filter for liquid stocks!
liquid_gainers = [g for g in gainers 
                  if g.get('price', 0) > 10 
                  and g.get('volume', 0) > 1000000]
```

### Company Profile

```python
from servers.financial_modeling_prep.company.profile import get_profile
profile = get_profile('AAPL')
```

### TradingView Charts

```python
from servers.tradingview.charts.generate import create_chart_for_chat
chart = create_chart_for_chat('AAPL', interval='1d', indicators=['RSI', 'MACD'])
# Save chart['html'] to file, reference with [file:AAPL_chart.html]
```

## ⚠️ Common Mistakes to Avoid

1. **Wrong parameter name**: Use `symbol=` not `ticker=` for all Polygon functions
2. **Not checking for errors**: ALWAYS check `if 'error' in response` before accessing data:
   ```python
   response = get_historical_prices(symbol='AAPL', ...)
   if 'error' in response:
       print(f"Error: {response['error']}")  # Handle error!
   else:
       df = pd.DataFrame(response['bars'])  # Safe to access
   ```
3. **Expecting list, getting dict**: Price APIs return `{'bars': [...]}`, not a list directly
4. **Forgetting to access list**: `get_quote_snapshot()` returns a LIST, use `quotes[0]`
5. **Timestamp conversion**: Always do `pd.to_datetime(df['timestamp'], unit='ms')`
6. **Not filtering gainers**: Raw gainers include penny stocks - always filter by price/volume

## When to Use Which API

| Need | Use |
|------|-----|
| Intraday bars (1min-1hour) | `polygon_io.market.intraday.get_intraday_bars()` |
| Daily/weekly/monthly bars | `polygon_io.market.historical_prices.get_historical_prices()` |
| Quote with PE, market cap | `financial_modeling_prep.market.quote.get_quote_snapshot()` |
| Market gainers/losers | `financial_modeling_prep.market.gainers.get_gainers()` |
| Company fundamentals | `financial_modeling_prep.company.profile.get_profile()` |
| Interactive charts | `tradingview.charts.generate.create_chart_for_chat()` |
