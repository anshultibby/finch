"""Generate a multi-chart watchlist dashboard"""
from typing import List
from ._embed import generate_multi_chart_layout


def create_watchlist_dashboard(
    symbols: List[str],
    exchange: str = "",
    theme: str = "dark"
) -> dict:
    """
    Generate a multi-chart watchlist dashboard
    
    Creates a grid of mini charts for multiple symbols at once.
    Good for monitoring a portfolio or watchlist.
    
    Args:
        symbols: List of ticker symbols (max 6 recommended) - TradingView auto-detects exchanges
        exchange: Exchange (optional)
        theme: "dark" or "light"
        
    Returns:
        dict with html, filename, description
    """
    
    # Determine grid layout
    num_symbols = len(symbols)
    columns = 2 if num_symbols <= 4 else 3
    
    widget = generate_multi_chart_layout(
        symbols=symbols,
        exchange=exchange if exchange else "",
        interval="D",
        theme=theme,
        columns=columns
    )
    
    bg_color = "#131722" if theme == "dark" else "#ffffff"
    text_color = "#d1d4dc" if theme == "dark" else "#131722"
    
    html_page = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Watchlist Dashboard</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        html, body {{ min-height: 100%; width: 100%; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            background: {bg_color};
            padding: 20px;
        }}
        .dashboard-container {{
            max-width: 1400px;
            margin: 0 auto;
        }}
        h1 {{
            color: {text_color};
            text-align: center;
            margin-bottom: 20px;
            font-size: 1.5rem;
        }}
    </style>
</head>
<body>
    <div class="dashboard-container">
        <h1>📊 Watchlist Dashboard</h1>
        {widget['html']}
    </div>
</body>
</html>"""
    
    filename = "watchlist_dashboard.html"
    description = f"Watchlist dashboard with {len(symbols)} symbols: {', '.join(symbols)}"
    
    return {
        "html": html_page,
        "filename": filename,
        "symbols": symbols,
        "description": description
    }

