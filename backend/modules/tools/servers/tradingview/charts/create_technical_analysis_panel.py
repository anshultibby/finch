"""Generate a technical analysis recommendations panel"""
from ._embed import generate_technical_analysis_widget


def create_technical_analysis_panel(
    symbol: str,
    exchange: str = "",
    interval: str = "1d",
    theme: str = "dark"
) -> dict:
    """
    Generate a technical analysis recommendations panel
    
    Shows buy/sell/neutral signals from multiple indicators in a visual gauge.
    Different from create_chart_for_chat - this shows indicator signals, not price charts.
    
    Args:
        symbol: Ticker symbol - TradingView auto-detects exchange
        exchange: Exchange (optional)
        interval: Timeframe (1m, 5m, 15m, 1h, 4h, 1d, 1W, 1M)
        theme: "dark" or "light"
        
    Returns:
        dict with html, filename, description
    """
    
    widget = generate_technical_analysis_widget(
        symbol=symbol,
        exchange=exchange if exchange else "",
        interval=interval,
        theme=theme,
        width="100%",
        height="500"
    )
    
    bg_color = "#131722" if theme == "dark" else "#ffffff"
    
    html_page = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{symbol} - Technical Analysis</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        html, body {{ height: 100%; width: 100%; overflow: hidden; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            background: {bg_color};
            display: flex;
            justify-content: center;
            align-items: flex-start;
            padding: 10px;
        }}
        .panel-container {{
            width: 100%;
            max-width: 500px;
        }}
    </style>
</head>
<body>
    <div class="panel-container">
        {widget['html']}
    </div>
</body>
</html>"""
    
    filename = f"{symbol}_technical_analysis_{interval}.html"
    description = f"{symbol} technical analysis recommendations ({interval} timeframe)"
    
    return {
        "html": html_page,
        "filename": filename,
        "symbol": symbol,
        "interval": interval,
        "description": description
    }

