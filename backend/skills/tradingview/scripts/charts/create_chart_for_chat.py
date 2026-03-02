"""Generate a TradingView chart ready for chat embedding"""
from typing import List
from ._embed import generate_chart_widget


def create_chart_for_chat(
    symbol: str,
    exchange: str = "",
    interval: str = "1d",
    indicators: List[str] = None,
    theme: str = "dark"
) -> dict:
    """
    Generate a TradingView chart ready for chat embedding
    
    This creates a complete HTML file with the TradingView chart widget.
    The AI should save this to a file and reference it with [file:chart.html]
    
    Args:
        symbol: Ticker symbol (e.g., 'AAPL', 'TSLA', 'ANF')
            Can also include exchange: 'NYSE:ANF', 'NASDAQ:AAPL'
        exchange: Exchange (optional - TradingView auto-detects if not provided)
            Examples: NASDAQ, NYSE, AMEX, BINANCE, COINBASE
        interval: Timeframe (1m, 5m, 15m, 1h, 4h, 1d, 1w)
        indicators: List of indicators to show
            Options: ['RSI', 'MACD', 'BB', 'EMA', 'SMA', 'Volume', 'Bollinger', 'Stochastic', 'ATR']
        theme: "dark" or "light"
        
    Returns:
        dict with:
            - html: Complete HTML page with chart
            - filename: Suggested filename
            - description: Human-readable description
    """
    
    # Map simple indicator names to TradingView study IDs
    study_map = {
        'RSI': 'RSI@tv-basicstudies',
        'MACD': 'MACD@tv-basicstudies',
        'BB': 'BB@tv-basicstudies',
        'EMA': 'EMA@tv-basicstudies',
        'SMA': 'MASimple@tv-basicstudies',
        'Volume': 'Volume@tv-basicstudies',
        'Bollinger': 'BB@tv-basicstudies',
        'Stochastic': 'Stochastic@tv-basicstudies',
        'ATR': 'ATR@tv-basicstudies'
    }
    
    # Convert indicator names to TradingView studies
    studies = None
    if indicators:
        studies = [study_map.get(ind, ind) for ind in indicators]
    
    # Generate the widget (pass exchange only if specified)
    widget = generate_chart_widget(
        symbol=symbol,
        exchange=exchange if exchange else "",
        interval=interval,
        theme=theme,
        width="100%",
        height=600,
        studies=studies,
        hide_side_toolbar=False,
        allow_symbol_change=True,
        save_image=True
    )
    
    bg_color = "#131722" if theme == "dark" else "#ffffff"
    
    # Create complete HTML page
    html_page = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{symbol} - TradingView Chart</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        html, body {{ height: 100%; width: 100%; overflow: hidden; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            background: {bg_color};
        }}
        .chart-container {{
            width: 100%;
            height: 100%;
        }}
        .tradingview-widget-container {{
            height: 100% !important;
        }}
    </style>
</head>
<body>
    <div class="chart-container">
        {widget['html']}
    </div>
</body>
</html>"""
    
    # Generate filename
    indicator_suffix = "_".join(indicators[:3]) if indicators else "chart"
    filename = f"{symbol}_{interval}_{indicator_suffix}.html"
    
    # Human-readable description
    indicators_text = ", ".join(indicators) if indicators else "price action"
    description = f"{symbol} chart ({interval} timeframe) with {indicators_text}"
    
    return {
        "html": html_page,
        "filename": filename,
        "symbol": symbol,
        "interval": interval,
        "description": description
    }
