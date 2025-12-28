# API Servers

Progressive disclosure for external APIs. Each tool is a Python file with clean docstrings.

## Available Servers

- **financial_modeling_prep/** - Financial Modeling Prep (stocks, financials, market data)
- **polygon_io/** - Polygon.io (historical prices, quotes)
- **reddit/** - Reddit sentiment (trending stocks)
- **snaptrade/** - SnapTrade (secure portfolio access via OAuth)
- **tradingview/** - TradingView (technical analysis, interactive charts)

**Note:** Web search and scraping are now first-order tools (`web_search`, `news_search`, `scrape_url`).

## Usage

```python
# Historical prices
from servers.polygon_io.market.historical_prices import get_historical_prices
prices = get_historical_prices('AAPL', '2024-01-01', '2024-12-31')

# Company profile
from servers.financial_modeling_prep.company.profile import get_profile
profile = get_profile('AAPL')

# TradingView chart (save as HTML, embed in chat)
from servers.tradingview.charts.generate import create_chart_for_chat
chart = create_chart_for_chat('AAPL', interval='1d', indicators=['RSI', 'MACD'])
# Save chart['html'] to file, reference with [file:AAPL_chart.html]
```

## Guidelines
1. If you need current information or research, use the `web_search` or `news_search` tools directly.
2. Use `scrape_url` to read full content from search results.
