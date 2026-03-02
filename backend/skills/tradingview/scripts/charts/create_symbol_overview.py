"""Generate a symbol overview widget with price, stats, and chart"""
from ._embed import generate_symbol_overview


def create_symbol_overview(
    symbol: str,
    exchange: str = "",
    theme: str = "dark"
) -> dict:
    """
    Generate a symbol overview widget with price, stats, and chart
    
    Shows current price, change %, volume, market cap in a compact widget.
    Good for quick symbol summaries.
    
    Args:
        symbol: Ticker symbol - TradingView auto-detects exchange
        exchange: Exchange (optional)
        theme: "dark" or "light"
        
    Returns:
        dict with html, filename, description
    """
    
    widget = generate_symbol_overview(
        symbol=symbol,
        exchange=exchange if exchange else "",
        width="100%",
        height="500",
        theme=theme,
        show_chart=True
    )
    
    bg_color = "#131722" if theme == "dark" else "#ffffff"
    
    html_page = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{symbol} - Overview</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        html, body {{ height: 100%; width: 100%; overflow: hidden; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            background: {bg_color};
        }}
        .overview-container {{
            width: 100%;
            height: 100%;
        }}
    </style>
</head>
<body>
    <div class="overview-container">
        {widget['html']}
    </div>
</body>
</html>"""
    
    filename = f"{symbol}_overview.html"
    description = f"{symbol} overview with price, change, and chart"
    
    return {
        "html": html_page,
        "filename": filename,
        "symbol": symbol,
        "description": description
    }

