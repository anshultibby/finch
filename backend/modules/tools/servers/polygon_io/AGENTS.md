# Polygon.io

Stock market OHLCV data.

## Functions

### market.intraday

- `get_intraday_bars(symbol, from_datetime, to_datetime, timespan='5min')` → bars
  - timespan: '1min', '5min', '15min', '30min', '1hour'
  - dates: 'YYYY-MM-DD' or 'YYYY-MM-DD HH:MM:SS'

### market.historical_prices

- `get_historical_prices(symbol, from_date, to_date, timespan='day')` → bars
  - timespan: 'day', 'week', 'month'

### market.quote

- `get_snapshot(symbol)` → current price, volume, day range
- `get_last_trade(symbol)` → last trade details
- `get_last_quote(symbol)` → bid/ask spread

## Models

```python
from servers.polygon_io.models import (
    IntradayBarsResponse,
    HistoricalPricesResponse,
    SnapshotResponse,
    Bar
)
```

## Notes

- Use `symbol=` parameter (NOT `ticker=`)
- Response has `bars` key containing list of Bar objects
- Timestamps are Unix milliseconds
