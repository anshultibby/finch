"""
Generate and save TradingView charts for chat embedding

This module creates HTML chart files that can be embedded in the chat interface.
The AI can call these functions to show charts to users.
"""
from typing import List, Optional
from .embed import (
    generate_chart_widget,
    generate_mini_chart,
    generate_symbol_overview,
    generate_technical_analysis_widget,
    generate_multi_chart_layout
)


def create_chart_for_chat(
    symbol: str,
    exchange: str = "NASDAQ",
    interval: str = "1d",
    indicators: List[str] = None,
    theme: str = "dark"
) -> dict:
    """
    Generate a TradingView chart ready for chat embedding
    
    This creates a complete HTML file with the TradingView chart widget.
    The AI should save this to a file and reference it with [file:chart.html]
    
    Args:
        symbol: Ticker symbol (e.g., 'AAPL', 'TSLA')
        exchange: Exchange (NASDAQ, NYSE, etc)
        interval: Timeframe (1m, 5m, 15m, 1h, 4h, 1d, 1w)
        indicators: List of indicators to show
            Options: ['RSI', 'MACD', 'BB', 'EMA', 'SMA', 'Volume']
        theme: "dark" or "light"
        
    Returns:
        dict with:
            - html: Complete HTML page with chart
            - filename: Suggested filename
            - description: Human-readable description
            
    Usage (in AI code):
        ```python
        from servers.tradingview.charts.generate import create_chart_for_chat
        
        # Generate chart
        chart = create_chart_for_chat('AAPL', interval='1d', indicators=['RSI', 'MACD'])
        
        # Save to chat files (AI will do this via write_chat_file tool)
        # Then mention it: "Here's the chart: [file:AAPL_chart.html]"
        ```
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
    
    # Generate the widget
    widget = generate_chart_widget(
        symbol=symbol,
        exchange=exchange,
        interval=interval,
        theme=theme,
        width="100%",
        height=600,
        studies=studies,
        hide_side_toolbar=False,
        allow_symbol_change=True,
        save_image=True
    )
    
    # Create complete HTML page
    html_page = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{symbol} - TradingView Chart</title>
    <style>
        body {{
            margin: 0;
            padding: 0;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            background: {"#131722" if theme == "dark" else "#ffffff"};
        }}
        .chart-container {{
            width: 100%;
            height: 100vh;
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


def create_technical_analysis_panel(
    symbol: str,
    exchange: str = "NASDAQ",
    interval: str = "1d",
    theme: str = "dark"
) -> dict:
    """
    Generate a technical analysis recommendations panel
    
    Shows buy/sell/neutral signals from multiple indicators
    
    Args:
        symbol: Ticker symbol
        exchange: Exchange
        interval: Timeframe
        theme: "dark" or "light"
        
    Returns:
        dict with html, filename, description
    """
    
    widget = generate_technical_analysis_widget(
        symbol=symbol,
        exchange=exchange,
        interval=interval,
        theme=theme,
        width="100%",
        height="500"
    )
    
    html_page = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{symbol} - Technical Analysis</title>
    <style>
        body {{
            margin: 0;
            padding: 20px;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            background: {"#131722" if theme == "dark" else "#ffffff"};
        }}
        .panel-container {{
            max-width: 500px;
            margin: 0 auto;
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


def create_watchlist_dashboard(
    symbols: List[str],
    exchange: str = "NASDAQ",
    theme: str = "dark"
) -> dict:
    """
    Generate a multi-chart watchlist dashboard
    
    Args:
        symbols: List of ticker symbols (max 6 recommended)
        exchange: Exchange
        theme: "dark" or "light"
        
    Returns:
        dict with html, filename, description
    """
    
    # Determine grid layout
    num_symbols = len(symbols)
    columns = 2 if num_symbols <= 4 else 3
    
    widget = generate_multi_chart_layout(
        symbols=symbols,
        exchange=exchange,
        interval="D",
        theme=theme,
        columns=columns
    )
    
    html_page = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Watchlist Dashboard</title>
    <style>
        body {{
            margin: 0;
            padding: 20px;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            background: {"#131722" if theme == "dark" else "#ffffff"};
        }}
        .dashboard-container {{
            max-width: 1400px;
            margin: 0 auto;
        }}
        h1 {{
            color: {"#d1d4dc" if theme == "dark" else "#131722"};
            text-align: center;
            margin-bottom: 20px;
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

