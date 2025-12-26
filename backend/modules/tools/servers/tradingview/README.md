# TradingView Server

Technical analysis and charting data from TradingView for AI-powered trading decisions.

## Overview

This server provides access to TradingView's technical analysis indicators, helping users:
- Analyze stocks/assets with 30+ technical indicators
- Get buy/sell/neutral recommendations
- Detect chart patterns (Bollinger squeeze, RSI divergence, MACD crossovers)
- Compare trends across multiple timeframes
- Make informed trading decisions with AI assistance

## Quick Start

```python
from servers.tradingview.api import get_technical_analysis
from servers.tradingview.analysis.technical_indicators import get_recommendation
from servers.tradingview.analysis.chart_patterns import detect_bollinger_squeeze

# Get full technical analysis
analysis = get_technical_analysis('AAPL', 'NASDAQ', '1d')

# Get quick recommendation
rec = get_recommendation('TSLA', 'NASDAQ', '4h')

# Check for Bollinger squeeze (breakout setup)
squeeze = detect_bollinger_squeeze('MSFT', 'NASDAQ', '1d')
```

## Available Tools

### Core API (`api.py`)

**`get_technical_analysis(symbol, exchange, interval, screener)`**
- Complete technical analysis for any symbol
- Returns: indicators, oscillators, moving averages, recommendation
- Example: `get_technical_analysis('AAPL', 'NASDAQ', '1d', 'america')`

**`get_multi_timeframe_analysis(symbol, exchange, screener, intervals)`**
- Analyze across multiple timeframes simultaneously
- Default intervals: ['15m', '1h', '4h', '1d']
- Example: `get_multi_timeframe_analysis('TSLA', intervals=['1h', '4h', '1d'])`

### Technical Indicators (`analysis/technical_indicators.py`)

**`get_indicators(symbol, exchange, interval)`**
- All technical indicators: RSI, MACD, ADX, CCI, Stochastic, etc.

**`get_oscillators(symbol, exchange, interval)`**
- Oscillator-only indicators (overbought/oversold signals)

**`get_moving_averages(symbol, exchange, interval)`**
- Moving averages: SMA10/20/50/100/200, EMA10/20/50/100/200

**`get_recommendation(symbol, exchange, interval)`**
- Overall buy/sell/neutral recommendation based on all indicators

### Multi-Timeframe Analysis (`analysis/multi_timeframe.py`)

**`compare_timeframes(symbol, exchange, intervals)`**
- Compare analysis across different timeframes
- Identify trend alignment or divergence
- Example use cases:
  - Scalping: `['1m', '5m', '15m']`
  - Day trading: `['15m', '1h', '4h']`
  - Swing trading: `['4h', '1d', '1w']`

**`get_trend_alignment(symbol, exchange)`**
- Check if trends align across timeframes (confluence)
- Returns: STRONG_BULLISH, BULLISH, NEUTRAL, BEARISH, STRONG_BEARISH

### Chart Patterns (`analysis/chart_patterns.py`)

**`detect_bollinger_squeeze(symbol, exchange, interval)`**
- Detect Bollinger Band squeeze (pre-breakout setup)
- Returns: squeeze status, band width, price position

**`check_rsi_divergence(symbol, exchange, interval)`**
- Check RSI for overbought (>70) or oversold (<30) conditions
- Returns: RSI value, condition, signal

**`check_macd_crossover(symbol, exchange, interval)`**
- Check MACD crossover status (bullish/bearish)
- Returns: MACD values, crossover type, interpretation

## Parameters

### Exchanges
- **Stocks**: `NASDAQ`, `NYSE`, `AMEX`
- **Crypto** (optional): `BINANCE`, `KUCOIN`

### Intervals
- **Intraday**: `1m`, `5m`, `15m`, `30m`, `1h`, `2h`, `4h`
- **Daily+**: `1d`, `1w`, `1M`

### Screeners
- `america` - US stocks (NASDAQ, NYSE, AMEX)
- `crypto` - Cryptocurrency markets

## Common Use Cases

### 1. Quick Stock Analysis
```python
from servers.tradingview.analysis.technical_indicators import get_recommendation

# Get AI trading recommendation
rec = get_recommendation('AAPL', 'NASDAQ', '1d')
# Returns: {"recommendation": "STRONG_BUY", "buy": 15, "sell": 3, "neutral": 8}
```

### 2. Entry Point Detection
```python
from servers.tradingview.analysis.chart_patterns import (
    detect_bollinger_squeeze,
    check_rsi_divergence
)

# Check for breakout setup
squeeze = detect_bollinger_squeeze('TSLA', 'NASDAQ', '1d')
if squeeze['is_squeeze']:
    print(f"Potential breakout setup on {squeeze['symbol']}")

# Check for oversold bounce
rsi = check_rsi_divergence('MSFT', 'NASDAQ', '4h')
if rsi['condition'] == 'OVERSOLD':
    print(f"Potential buy opportunity: RSI at {rsi['rsi']}")
```

### 3. Multi-Timeframe Confirmation
```python
from servers.tradingview.analysis.multi_timeframe import get_trend_alignment

# Check if all timeframes agree
alignment = get_trend_alignment('GOOGL', 'NASDAQ')
if alignment['alignment'] == 'STRONG_BULLISH':
    print(f"{alignment['bullish_timeframes']}/4 timeframes bullish")
```

### 4. Full Technical Dashboard
```python
from servers.tradingview.api import get_technical_analysis

# Get everything in one call
analysis = get_technical_analysis('NVDA', 'NASDAQ', '1d')

print(f"Recommendation: {analysis['summary']['recommendation']}")
print(f"RSI: {analysis['indicators']['RSI']}")
print(f"MACD: {analysis['indicators']['MACD.macd']}")
print(f"Price: {analysis['indicators']['close']}")
```

## Technical Indicators Explained

### Trend Indicators
- **SMA/EMA**: Moving averages (trend direction)
- **MACD**: Moving Average Convergence Divergence (momentum & trend)
- **ADX**: Average Directional Index (trend strength)

### Momentum Oscillators
- **RSI**: Relative Strength Index (overbought/oversold, 0-100)
- **Stochastic**: Momentum oscillator (overbought/oversold)
- **CCI**: Commodity Channel Index (trend changes)
- **Williams %R**: Momentum indicator

### Volatility Indicators
- **Bollinger Bands**: Price volatility and squeeze detection
- **ATR**: Average True Range (volatility measurement)

### Volume Indicators
- **Volume**: Trading volume analysis
- **OBV**: On-Balance Volume (buying/selling pressure)

## Chart Embedding (`charts/generate.py`)

Generate embeddable TradingView charts for the chat interface:

**`create_chart_for_chat(symbol, exchange, interval, indicators, theme)`**
- Generate interactive chart ready for chat embedding
- Returns HTML that can be saved as a file
- Usage: Save as `.html` file, then reference with `[file:chart.html]`

**`create_technical_analysis_panel(symbol, exchange, interval, theme)`**
- Generate technical analysis recommendations widget
- Shows buy/sell/neutral signals

**`create_watchlist_dashboard(symbols, exchange, theme)`**
- Generate multi-chart grid for watchlist
- Up to 6 symbols in 2-3 column layout

### How AI Embeds Charts

```python
from servers.tradingview.charts.generate import create_chart_for_chat

# 1. Generate chart HTML
chart = create_chart_for_chat(
    'AAPL', 
    interval='1d',
    indicators=['RSI', 'MACD', 'BB']
)

# 2. Save to chat files (AI uses write_chat_file tool)
# write_chat_file(filename=chart['filename'], content=chart['html'])

# 3. Reference in message
# "Here's the AAPL chart with RSI, MACD, and Bollinger Bands: [file:AAPL_1d_RSI_MACD_BB.html]"
```

The frontend will render this as an interactive TradingView chart!

## AI Trading Assistant Integration

The AI can help users by:
1. **Analyzing charts**: "Analyze AAPL's technical indicators on the daily chart"
2. **Finding setups**: "Find stocks with Bollinger Band squeeze on 4h timeframe"
3. **Confirming trends**: "Check if TSLA is bullish across all timeframes"
4. **Entry/exit timing**: "Is NVDA oversold? Should I buy?"
5. **Creating visualizations**: "Show me MSFT chart with RSI and MACD"

## Example AI Conversations

**User**: "Analyze Tesla's technicals"
**AI**: *Calls `get_technical_analysis('TSLA', 'NASDAQ', '1d')` and plots key indicators*

**User**: "Is there a good entry point on Apple?"
**AI**: *Checks RSI, Bollinger Bands, and multi-timeframe alignment, then provides recommendation*

**User**: "Find me a stock ready to break out"
**AI**: *Scans watchlist for Bollinger squeezes and provides candidates*

## Progressive Disclosure

This server follows the progressive disclosure pattern:
1. Agent discovers tools by exploring `servers/tradingview/`
2. Reads tool docstrings to understand functionality
3. Uses only what's needed for the user's request
4. Combines tools for complex analysis

## Error Handling

All tools return `{"error": "message"}` on failure. Check for error key before processing results.

```python
result = get_recommendation('INVALID', 'NASDAQ', '1d')
if 'error' in result:
    print(f"Failed: {result['error']}")
```

