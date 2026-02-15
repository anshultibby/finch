# API Servers - Complete Function Reference

## servers/dome/
**Prediction market data (Polymarket & Kalshi) - READ ONLY**

### polymarket/wallet.py
- `get_wallet_info(address: str)` - Basic wallet info
- `get_positions(address: str)` - Current positions with P&L
- `get_wallet_pnl(address: str, start_date: str, end_date: str)` - Historical P&L
- `get_wallet_activity(address: str, limit: int)` - Recent activity/transactions
- `get_wallet_trades(address: str, market_id: str)` - Trades for specific market

### polymarket/markets.py
- `get_markets(search: str, status: str, limit: int)` - Search/browse markets

### polymarket/prices.py
- `get_market_price(condition_id: str, token_id: str)` - Current price
- `get_candlesticks(condition_id: str, token_id: str, interval: str)` - OHLCV data

### polymarket/trading.py
- `get_orders(condition_id: str)` - Order book for market
- `get_trade_history(condition_id: str, limit: int)` - Recent trades

### polymarket/clob_client.py
- `get_clob_client()` - Low-level CLOB client
- `get_markets_clob()` - All markets via CLOB
- `get_orderbook(condition_id: str, token_id: str)` - Full order book
- `get_market_price(condition_id: str, token_id: str)` - Price via CLOB
- `get_user_orders(address: str)` - User's open orders
- `get_user_trades(address: str, limit: int)` - User's trade history

### kalshi/markets.py
- `get_markets(search: str, status: str, limit: int)` - Search Kalshi markets
- `get_market_price(ticker: str)` - Current Kalshi market price

### matching/sports.py
- `get_sports_matching_markets(sport: str, date: str)` - Find matching markets across platforms
- `get_sport_by_date(sport: str, date: str)` - Sports events on date
- `find_arbitrage_opportunities(sport: str)` - Cross-platform arbitrage

**Models:** `servers/dome/models.py`

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

**Models:** `servers/polygon_io/models.py`

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

**Models:** `servers/financial_modeling_prep/models.py`

---

## servers/kalshi/
**Kalshi trading (authenticated) - REQUIRES API KEYS**

### portfolio.py
- `get_kalshi_balance()` - Account balance
- `get_kalshi_positions(limit: int)` - Open positions
- `get_kalshi_portfolio()` - Full portfolio state

### markets.py
- `get_kalshi_events(limit: int, status: str)` - Browse events
- `get_kalshi_market(ticker: str)` - Market details with pricing

### trading.py
- `place_kalshi_order(ticker: str, side: str, action: str, count: int, price: int)` - Place order
- `get_kalshi_orders()` - View open orders
- `cancel_kalshi_order(order_id: str)` - Cancel order

**Models:** `servers/kalshi/models.py`

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

Always check for `'error'` key in responses before using data.

Use Pydantic models from `servers/<server>/models.py` for type safety.

See `servers/<server>/AGENTS.md` for detailed parameter docs and examples.
