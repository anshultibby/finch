"""TradingView Chart Embedding - Generate embeddable chart widgets"""
from typing import Optional, List


def generate_chart_widget(
    symbol: str,
    exchange: str = "NASDAQ",
    interval: str = "D",
    theme: str = "dark",
    width: str = "100%",
    height: int = 500,
    studies: List[str] = None,
    hide_side_toolbar: bool = False,
    allow_symbol_change: bool = True,
    save_image: bool = True
):
    """
    Generate TradingView advanced chart widget HTML
    
    Args:
        symbol: Ticker symbol (e.g., 'AAPL', 'TSLA')
        exchange: Exchange (NASDAQ, NYSE, BINANCE, etc)
        interval: Timeframe (1, 3, 5, 15, 30, 60, 120, 180, D, W, M)
        theme: "dark" or "light"
        width: Chart width (e.g., "100%", "800px")
        height: Chart height in pixels
        studies: List of technical indicators to display
            Options: ["RSI@tv-basicstudies", "MACD@tv-basicstudies", 
                     "BB@tv-basicstudies", "EMA@tv-basicstudies", etc]
        hide_side_toolbar: Hide the side toolbar
        allow_symbol_change: Allow users to change symbol
        save_image: Allow saving chart as image
        
    Returns:
        dict: HTML code and iframe code for embedding
    """
    
    # Map interval format
    interval_map = {
        "1m": "1", "3m": "3", "5m": "5", "15m": "15", 
        "30m": "30", "1h": "60", "2h": "120", "4h": "240",
        "1d": "D", "1w": "W", "1M": "M"
    }
    tv_interval = interval_map.get(interval, interval)
    
    # Build studies parameter
    studies_param = ""
    if studies:
        studies_param = f'"studies": {studies},'
    
    # Generate the widget HTML
    html = f'''
<!-- TradingView Widget BEGIN -->
<div class="tradingview-widget-container" style="height:{height}px;width:{width}">
  <div id="tradingview_chart" style="height:calc(100% - 32px);width:100%"></div>
  <div class="tradingview-widget-copyright">
    <a href="https://www.tradingview.com/" rel="noopener nofollow" target="_blank">
      <span class="blue-text">Track all markets on TradingView</span>
    </a>
  </div>
  <script type="text/javascript" src="https://s3.tradingview.com/tv.js"></script>
  <script type="text/javascript">
  new TradingView.widget({{
    "width": "{width}",
    "height": {height},
    "symbol": "{exchange}:{symbol}",
    "interval": "{tv_interval}",
    "timezone": "Etc/UTC",
    "theme": "{theme}",
    "style": "1",
    "locale": "en",
    "toolbar_bg": "#f1f3f6",
    "enable_publishing": false,
    "hide_side_toolbar": {str(hide_side_toolbar).lower()},
    "allow_symbol_change": {str(allow_symbol_change).lower()},
    "save_image": {str(save_image).lower()},
    {studies_param}
    "container_id": "tradingview_chart"
  }});
  </script>
</div>
<!-- TradingView Widget END -->
'''
    
    return {
        "symbol": f"{exchange}:{symbol}",
        "interval": tv_interval,
        "html": html.strip(),
        "type": "advanced_chart"
    }


def generate_mini_chart(
    symbol: str,
    exchange: str = "NASDAQ",
    width: str = "350",
    height: str = "220",
    theme: str = "dark"
):
    """
    Generate compact mini chart widget (smaller, for quick views)
    
    Args:
        symbol: Ticker symbol
        exchange: Exchange
        width: Width in pixels
        height: Height in pixels
        theme: "dark" or "light"
        
    Returns:
        dict: HTML for mini chart
    """
    
    html = f'''
<!-- TradingView Widget BEGIN -->
<div class="tradingview-widget-container">
  <div class="tradingview-widget-container__widget"></div>
  <script type="text/javascript" src="https://s3.tradingview.com/external-embedding/embed-widget-mini-symbol-overview.js" async>
  {{
    "symbol": "{exchange}:{symbol}",
    "width": "{width}",
    "height": "{height}",
    "locale": "en",
    "dateRange": "12M",
    "colorTheme": "{theme}",
    "isTransparent": false,
    "autosize": false,
    "largeChartUrl": ""
  }}
  </script>
</div>
<!-- TradingView Widget END -->
'''
    
    return {
        "symbol": f"{exchange}:{symbol}",
        "html": html.strip(),
        "type": "mini_chart"
    }


def generate_symbol_overview(
    symbol: str,
    exchange: str = "NASDAQ",
    width: str = "1000",
    height: str = "400",
    theme: str = "dark",
    show_chart: bool = True
):
    """
    Generate symbol overview widget (price + stats + chart)
    
    Includes: current price, change %, volume, market cap, and chart
    
    Args:
        symbol: Ticker symbol
        exchange: Exchange
        width: Width in pixels or percentage
        height: Height in pixels
        theme: "dark" or "light"
        show_chart: Show price chart
        
    Returns:
        dict: HTML for symbol overview
    """
    
    html = f'''
<!-- TradingView Widget BEGIN -->
<div class="tradingview-widget-container">
  <div class="tradingview-widget-container__widget"></div>
  <script type="text/javascript" src="https://s3.tradingview.com/external-embedding/embed-widget-symbol-overview.js" async>
  {{
    "symbols": [
      ["{exchange}:{symbol}"]
    ],
    "chartOnly": {str(not show_chart).lower()},
    "width": "{width}",
    "height": "{height}",
    "locale": "en",
    "colorTheme": "{theme}",
    "autosize": false,
    "showVolume": true,
    "showMA": false,
    "hideDateRanges": false,
    "hideMarketStatus": false,
    "hideSymbolLogo": false,
    "scalePosition": "right",
    "scaleMode": "Normal",
    "fontFamily": "-apple-system, BlinkMacSystemFont, Trebuchet MS, Roboto, Ubuntu, sans-serif",
    "fontSize": "10",
    "noTimeScale": false,
    "valuesTracking": "1",
    "changeMode": "price-and-percent",
    "chartType": "area"
  }}
  </script>
</div>
<!-- TradingView Widget END -->
'''
    
    return {
        "symbol": f"{exchange}:{symbol}",
        "html": html.strip(),
        "type": "symbol_overview"
    }


def generate_technical_analysis_widget(
    symbol: str,
    exchange: str = "NASDAQ",
    interval: str = "1d",
    width: str = "425",
    height: str = "450",
    theme: str = "dark"
):
    """
    Generate technical analysis widget (shows recommendations)
    
    Displays buy/sell/neutral signals from multiple indicators
    
    Args:
        symbol: Ticker symbol
        exchange: Exchange
        interval: Timeframe (1m, 5m, 15m, 1h, 4h, 1d, 1W, 1M)
        width: Width in pixels
        height: Height in pixels
        theme: "dark" or "light"
        
    Returns:
        dict: HTML for technical analysis widget
    """
    
    html = f'''
<!-- TradingView Widget BEGIN -->
<div class="tradingview-widget-container">
  <div class="tradingview-widget-container__widget"></div>
  <script type="text/javascript" src="https://s3.tradingview.com/external-embedding/embed-widget-technical-analysis.js" async>
  {{
    "interval": "{interval}",
    "width": "{width}",
    "isTransparent": false,
    "height": "{height}",
    "symbol": "{exchange}:{symbol}",
    "showIntervalTabs": true,
    "locale": "en",
    "colorTheme": "{theme}"
  }}
  </script>
</div>
<!-- TradingView Widget END -->
'''
    
    return {
        "symbol": f"{exchange}:{symbol}",
        "interval": interval,
        "html": html.strip(),
        "type": "technical_analysis_widget"
    }


def generate_multi_chart_layout(
    symbols: List[str],
    exchange: str = "NASDAQ",
    interval: str = "D",
    theme: str = "dark",
    columns: int = 2
):
    """
    Generate multi-chart grid layout
    
    Args:
        symbols: List of ticker symbols (e.g., ['AAPL', 'TSLA', 'MSFT', 'NVDA'])
        exchange: Exchange
        interval: Timeframe
        theme: "dark" or "light"
        columns: Number of columns in grid
        
    Returns:
        dict: HTML for multi-chart grid
    """
    
    chart_width = f"{100 // columns}%"
    charts = []
    
    for symbol in symbols:
        chart = generate_mini_chart(symbol, exchange, "100%", "250", theme)
        charts.append(chart["html"])
    
    grid_html = f'''
<div style="display: grid; grid-template-columns: repeat({columns}, 1fr); gap: 10px; width: 100%;">
    {"".join(f'<div>{chart}</div>' for chart in charts)}
</div>
'''
    
    return {
        "symbols": [f"{exchange}:{s}" for s in symbols],
        "html": grid_html.strip(),
        "type": "multi_chart_grid"
    }

