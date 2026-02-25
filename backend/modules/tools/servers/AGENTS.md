# API Servers - Complete Function Reference

## servers/dome/
**Prediction market data (Polymarket & Kalshi) - READ ONLY**

**All functions use Pydantic models for input/output. Import models from `servers.dome.models`. Errors raised as `DomeAPIError`.**

**IMPORTANT**: For wallet functions, most APIs expect the **proxy** wallet address, not the EOA.
Use `get_wallet_info()` to convert between EOA and proxy addresses if needed.

### polymarket/wallet.py
- `get_wallet_info(GetWalletInfoInput)` → `GetWalletInfoOutput`
  - Takes any wallet address and returns both EOA and proxy addresses
  - Automatically detects if input is EOA or proxy
- `get_positions(GetPositionsInput)` → `GetPositionsOutput` 
  - Requires proxy wallet address
- `get_wallet_pnl(GetWalletPnLInput)` → `GetWalletPnLOutput`
  - Requires proxy wallet address
- `get_wallet_activity(GetWalletActivityInput)` → `GetWalletActivityOutput`
  - Requires proxy wallet address
  - Returns SPLIT/MERGE/REDEEM only (not BUY/SELL)
- `get_wallet_trades(GetWalletTradesInput)` → `GetWalletTradesOutput`
  - Requires proxy wallet address
  - Returns BUY/SELL orders

### polymarket/markets.py
- `get_markets(GetMarketsInput)` → `GetMarketsOutput`

### polymarket/prices.py
- `get_market_price(GetMarketPriceInput)` → `GetMarketPriceOutput`
  - Returns `price`, `at_time` (not `timestamp`)
- `get_candlesticks(GetCandlesticksInput)` → `GetCandlesticksOutput`

### polymarket/trading.py
- `get_orders(GetOrdersInput)` → `GetOrdersOutput`
- `get_trade_history(GetOrdersInput)` → `GetOrdersOutput` (deprecated, use get_orders)

### polymarket/clob_client.py
- `get_clob_client()` → ClobClient
- `get_markets_clob()` → dict with `data` key
- `get_orderbook(token_id: str)` → dict with `bids`/`asks`
- `get_market_price(token_id: str, side: str)` → dict with `price`
- `get_user_orders(private_key: str)` → dict with `orders`
- `get_user_trades(private_key: str)` → dict with `trades`

### kalshi/markets.py
- `get_markets(GetKalshiMarketsInput)` → `GetKalshiMarketsOutput`
  - Returns markets with `event_ticker` (not `ticker`), `title`, `yes_bid`, `yes_ask`
- `get_market_price(GetKalshiMarketPriceInput)` → `GetKalshiMarketPriceOutput`

### matching/sports.py
- `get_sports_matching_markets(polymarket_market_slug, kalshi_event_ticker)` → dict
- `get_sport_by_date(sport: str, date: str)` → dict
- `find_arbitrage_opportunities(sport: str, date: str, min_spread: float)` → dict

**Models:** Import from `servers.dome.models`. See models.py for complete response schemas with all available attributes.

---

## servers/polygon_io/
**Stock market data**

### market/intraday.py
- `get_intraday_bars(symbol: str, from_datetime: str, to_datetime: str, timespan: str)` - Minute bars
- `get_today_bars(symbol: str, timespan: str)` - Today's bars

### market/historical_prices.py
- `get_historical_prices(symbol: str, from_date: str, to_date: str, timespan: str)` - Daily/weekly/monthly bars

### market/quote.py
- `get_last_trade(symbol: str)` - Last trade info
- `get_last_quote(symbol: str)` - Last bid/ask
- `get_snapshot(symbol: str)` - Complete snapshot

**Models:** `polygon_io/models.py` (read with `read_chat_file(filename="polygon_io/models.py", from_api_docs=True)`)

---

## servers/financial_modeling_prep/
**Stock fundamentals & ownership**

### company/profile.py
- `get_profile(symbol: str)` - Company profile

### company/executives.py
- `get_executives(symbol: str)` - Executive team

### market/quote.py
- `get_quote_snapshot(symbol: str)` - Real-time quote (returns list)

### market/gainers.py
- `get_gainers()` - Top gainers
- `get_losers()` - Top losers
- `get_actives()` - Most active

### financials/income_statement.py
- `get_income_statement(symbol: str, period: str, limit: int)` - Income statements

### financials/balance_sheet.py
- `get_balance_sheet(symbol: str, period: str, limit: int)` - Balance sheets

### financials/cash_flow.py
- `get_cash_flow(symbol: str, period: str, limit: int)` - Cash flow statements

### financials/key_metrics.py
- `get_key_metrics(symbol: str, period: str, limit: int)` - Key metrics
- `get_key_metrics_ttm(symbol: str)` - Trailing twelve months

### financials/ratios.py
- `get_ratios(symbol: str, period: str, limit: int)` - Financial ratios

### analyst/price_target.py
- `get_price_targets(symbol: str)` - All price targets
- `get_price_target_consensus(symbol: str)` - Consensus target

### insider/insider_roster.py
- `get_insider_roster(symbol: str)` - Officers/directors/owners

### insider/insider_trading.py
- `get_insider_trading(symbol: str, limit: int)` - Recent insider trades

### insider/insider_statistics.py
- `get_insider_statistics(symbol: str)` - Insider trading stats

### insider/senate_trading.py
- `get_senate_trading(symbol: str)` - Senate trades

### insider/house_trading.py
- `get_house_trading(symbol: str)` - House trades

### ownership/institutional_ownership.py
- `get_institutional_ownership(symbol: str, date: str)` - 13F holders
- `get_institutional_ownership_summary(symbol: str, year: int, quarter: int)` - Summary
- `get_institutional_holders_list(limit: int)` - Top holders

### earnings/earnings_calendar.py
- `get_earnings_calendar(from_date: str, to_date: str)` - Upcoming earnings
- `get_historical_earnings(symbol: str)` - Historical earnings

### search/search.py
- `search(query: str, limit: int, exchange: str)` - Search stocks

**Models:** `financial_modeling_prep/models.py` (read with `read_chat_file(filename="financial_modeling_prep/models.py", from_api_docs=True)`)

---

## servers/kalshi/
**Kalshi trading (authenticated) - REQUIRES API KEYS**

**All functions are synchronous (no `await` needed).** They handle async internally.

### portfolio.py
- `get_kalshi_balance()` → `{"balance": float, "portfolio_value": float}` (dollars)
- `get_kalshi_positions(limit: int = 100)` → `{"positions": [...], "count": int}`
- `get_kalshi_portfolio()` → combined balance + positions

### markets.py
- `get_kalshi_events(limit: int = 20, status: str = "open")` → `{"events": [...], "count": int}`
- `get_kalshi_market(ticker: str)` → market details with yes_bid, yes_ask, volume (prices in cents)

### trading.py
- `place_kalshi_order(ticker, side, action, count, order_type="market", price=None)` - Place order
- `get_kalshi_orders(ticker=None, status="resting")` → `{"orders": [...], "count": int}`
- `cancel_kalshi_order(order_id: str)` → `{"order_id": str, "status": "canceled"}`

**Models:** `kalshi/models.py` (read with `read_chat_file(filename="kalshi/models.py", from_api_docs=True)`)

---

## servers/tradingview/
**Technical analysis & charts**

### analysis/get_technical_analysis.py
- `get_technical_analysis(symbol: str, screener: str, interval: str)` - Full TA

### analysis/get_trend_alignment.py
- `get_trend_alignment(symbol: str, exchange: str)` - Multi-timeframe trend check

### analysis/get_multi_timeframe_analysis.py
- `get_multi_timeframe_analysis(symbol: str, screener: str)` - Comprehensive MTF analysis

### analysis/compare_timeframes.py
- `compare_timeframes(symbol: str, screener: str, timeframes: list)` - Compare signals

### charts/create_chart_for_chat.py
- `create_chart_for_chat(symbol: str, interval: str, indicators: list)` - Embeddable chart

### charts/create_symbol_overview.py
- `create_symbol_overview(symbols: list)` - Symbol overview widget

### charts/create_technical_analysis_panel.py
- `create_technical_analysis_panel(symbol: str)` - TA panel widget

### charts/create_watchlist_dashboard.py
- `create_watchlist_dashboard(symbols: list)` - Watchlist dashboard

---

## servers/snaptrade/
**Brokerage accounts (authenticated) - REQUIRES USER AUTH**

### portfolio/request_connection.py
- `request_connection(user_id: str)` - Get OAuth connection link

### portfolio/get_accounts.py
- `get_accounts(user_id: str)` - List connected accounts (async)

### portfolio/get_holdings.py
- `get_holdings(user_id: str)` - All holdings across accounts (async)

---

## servers/reddit/
**Social sentiment**

### get_trending_stocks.py
- `get_trending_stocks(limit: int)` - Top mentioned tickers with sentiment

---

## servers/strategies/
**Automated trading bots**

### deploy_from_files.py
- `deploy_strategy_from_files(**kwargs)` - Deploy strategy from code files
- `inspect_strategy(strategy_id: str, user_id: str)` - View strategy details
- `claim_strategy(strategy_id: str, user_id: str, chat_id: str)` - Claim ownership

### query_strategies.py
- `list_strategies(user_id: str)` - List user's strategies (async)
- `get_strategy_code(user_id: str, strategy_id: str)` - Get strategy code (async)
- `get_top_strategies(limit: int)` - Top performing strategies (async)
- `analyze_strategy_performance(strategy_id: str)` - Performance analysis (async)

### create_strategy.py
- `create_strategy(name: str, thesis: str, platform: str, ...)` - Create new strategy

---

## Usage

Import: `from servers.<server>.<module> import <function>`

**Most functions return Pydantic models directly.** Access data via attributes. Errors are raised as exceptions.

See models.py files for complete response schemas with all available attributes.
