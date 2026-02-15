# Polygon.io

Stock market OHLCV data.

## ⚠️ Response Structure

All functions return **dictionaries**. Access data via keys like `result['bars']`, `result['snapshot']`, etc.

## Functions

### market.intraday

- `get_intraday_bars(symbol, from_datetime, to_datetime, timespan='5min')` → dict with `bars` key (list)
  - timespan: '1min', '5min', '15min', '30min', '1hour'
  - dates: 'YYYY-MM-DD' or 'YYYY-MM-DD HH:MM:SS'

### market.historical_prices

- `get_historical_prices(symbol, from_date, to_date, timespan='day')` → dict with `bars` key (list)
  - timespan: 'day', 'week', 'month'

### market.quote

- `get_snapshot(symbol)` → dict with snapshot data
- `get_last_trade(symbol)` → dict with last trade details
- `get_last_quote(symbol)` → dict with bid/ask data

## Models

```python
from servers.polygon_io.models import (
    IntradayBarsResponse,
    HistoricalPricesResponse,
    SnapshotResponse,
    Bar
)
```

## Example Usage

```python
from servers.polygon_io.market.intraday import get_intraday_bars

# Get intraday bars
result = get_intraday_bars(
    symbol="AAPL",
    from_datetime="2024-01-01",
    to_datetime="2024-01-02",
    timespan="5min"
)

if 'error' in result:
    print(f"Error: {result['error']}")
else:
    # Access the bars list via the 'bars' key
    bars = result['bars']  # This is a list of Bar objects
    
    for bar in bars:
        print(f"Time: {bar['timestamp']}, Close: ${bar['close']}")
```

## Notes

- Use `symbol=` parameter (NOT `ticker=`)
- All functions return dicts. Access data via `result['bars']`, etc.
- Timestamps are Unix milliseconds
