# Dome API

Polymarket & Kalshi prediction market data. Rate: 1 req/sec.

## API Design

All functions accept a single Pydantic input model and return a Pydantic output model.
Errors are raised as `DomeAPIError` exceptions.

Import models from `servers.dome.models`. See models.py for complete schemas and available attributes.

## Functions

### polymarket.wallet

- `get_wallet_info(GetWalletInfoInput)` → `GetWalletInfoOutput`
- `get_positions(GetPositionsInput)` → `GetPositionsOutput`
- `get_wallet_trades(GetWalletTradesInput)` → `GetWalletTradesOutput`
- `get_wallet_pnl(GetWalletPnLInput)` → `GetWalletPnLOutput`
- `get_wallet_activity(GetWalletActivityInput)` → `GetWalletActivityOutput`

### polymarket.markets

- `get_markets(GetMarketsInput)` → `GetMarketsOutput`

### polymarket.prices

- `get_market_price(GetMarketPriceInput)` → `GetMarketPriceOutput`
- `get_candlesticks(GetCandlesticksInput)` → `GetCandlesticksOutput`

### polymarket.trading

- `get_orders(GetOrdersInput)` → `GetOrdersOutput`

### kalshi.markets

- `get_markets(GetKalshiMarketsInput)` → `GetKalshiMarketsOutput`
- `get_market_price(GetKalshiMarketPriceInput)` → `GetKalshiMarketPriceOutput`

All input/output models available in `servers.dome.models`

## Identifiers

- **wallet_address**: 0x... (proxy address - use this for most wallet APIs)
- **eoa**: 0x... (externally owned account - original wallet address)
- **proxy**: 0x... (proxy wallet address - required for Polymarket trading)
- **condition_id**: 0x... (market identifier)
- **token_id**: numeric string (outcome identifier)
- **market_slug**: URL-safe name (e.g., "bitcoin-100k")

## Wallet Address Types

Polymarket uses two types of addresses:
- **EOA (Externally Owned Account)**: Your original wallet address
- **Proxy**: A proxy contract address used for trading

Most wallet APIs (`get_positions`, `get_wallet_pnl`, `get_wallet_trades`, etc.) expect the **proxy** address.

Use `get_wallet_info()` to get both addresses (automatically detects if input is EOA or proxy).
The function returns both `result.eoa` and `result.proxy` attributes.
