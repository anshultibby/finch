# Dome API

Polymarket & Kalshi prediction market data. Rate: 1 req/sec.

## Functions

### polymarket.wallet

- `get_positions(wallet_address, limit=100)` → positions list
- `get_wallet_trades(wallet_address, limit=100)` → BUY/SELL orders
- `get_wallet_pnl(wallet_address, granularity)` → realized P&L history
  - granularity: "day", "week", "month", "year", "all"
- `get_wallet_activity(wallet_address, limit=100)` → SPLIT/MERGE/REDEEM (not trades)

### polymarket.markets

- `get_markets(tags=None, search=None, status=None, limit=10)` → markets list
  - tags: ['crypto', 'politics', 'sports']
  - status: 'open' or 'closed'

### polymarket.prices

- `get_market_price(token_id)` → current price
- `get_candlesticks(condition_id, start_time, end_time, interval=1440)` → OHLCV data
  - interval: minutes (1440=daily, 60=hourly)

### kalshi.markets

- `get_kalshi_events(limit=100)` → events list
- `get_kalshi_market(ticker)` → market details with prices

### matching.sports

- `find_arbitrage_opportunities(sport, date)` → cross-platform arb ops

## Models

```python
from servers.dome.models import (
    GetPositionsInput, GetPositionsOutput,
    GetWalletTradesInput, GetWalletTradesOutput,
    GetWalletPnLInput, GetWalletPnLOutput,
    GetMarketsInput, GetMarketsOutput,
    GetMarketPriceInput, GetMarketPriceOutput,
    GetCandlesticksInput, GetCandlesticksOutput
)
```

## Identifiers

- **wallet_address**: 0x... (use proxy address)
- **condition_id**: 0x... (market identifier)
- **token_id**: numeric string (outcome identifier)
- **market_slug**: URL-safe name (e.g., "bitcoin-100k")
