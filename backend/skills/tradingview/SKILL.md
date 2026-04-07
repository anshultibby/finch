---
name: tradingview
description: Technical analysis and chart generation from TradingView. Multi-timeframe analysis, trend alignment, and embeddable charts with indicators.
homepage: https://tradingview.com
metadata:
  emoji: "📐"
  category: technical_analysis
  is_system: true
  auto_on: true
  requires:
    env: []
    bins: []
---

# TradingView Skill

Technical analysis, indicators, and chart generation from TradingView.

## Import Pattern

```python
from skills.tradingview.scripts.analysis.get_technical_analysis import get_technical_analysis
from skills.tradingview.scripts.analysis.get_multi_timeframe_analysis import get_multi_timeframe_analysis
from skills.tradingview.scripts.analysis.get_trend_alignment import get_trend_alignment
from skills.tradingview.scripts.analysis.compare_timeframes import compare_timeframes
from skills.tradingview.scripts.charts.create_chart_for_chat import create_chart_for_chat
from skills.tradingview.scripts.charts.create_symbol_overview import create_symbol_overview
from skills.tradingview.scripts.charts.create_technical_analysis_panel import create_technical_analysis_panel
from skills.tradingview.scripts.charts.create_watchlist_dashboard import create_watchlist_dashboard
```

## Technical Analysis

```python
from skills.tradingview.scripts.analysis.get_technical_analysis import get_technical_analysis

# Get full technical analysis for a symbol
ta = get_technical_analysis(symbol="AAPL", screener="america", interval="1D")

print(f"Symbol: {ta['symbol']}")
print(f"Exchange: {ta['exchange']}")
print(f"Interval: {ta['interval']}")
print(f"Overall Recommendation: {ta['recommendation']}")  # BUY, SELL, NEUTRAL

# Oscillator signals
print("\nOscillators:")
for osc in ta['oscillators']:
    print(f"  {osc['name']}: {osc['value']} ({osc['signal']})")

# Moving average signals  
print("\nMoving Averages:")
for ma in ta['moving_averages']:
    print(f"  {ma['name']}: {ma['value']} ({ma['signal']})")
```

## Multi-Timeframe Analysis

```python
from skills.tradingview.scripts.analysis.get_multi_timeframe_analysis import get_multi_timeframe_analysis

# Analyze across multiple timeframes
mtf = get_multi_timeframe_analysis(symbol="NVDA", screener="america")

for timeframe in mtf['timeframes']:
    print(f"{timeframe['interval']}: {timeframe['recommendation']}")
    print(f"  Oscillator: {timeframe['oscillator']}")
    print(f"  MA: {timeframe['ma']}")

# Check for alignment
buy_timeframes = [t for t in mtf['timeframes'] if t['recommendation'] == 'BUY']
sell_timeframes = [t for t in mtf['timeframes'] if t['recommendation'] == 'SELL']

if len(buy_timeframes) >= 3:
    print("🟢 Strong bullish alignment across timeframes")
elif len(sell_timeframes) >= 3:
    print("🔴 Strong bearish alignment across timeframes")
```

## Trend Alignment

```python
from skills.tradingview.scripts.analysis.get_trend_alignment import get_trend_alignment

# Quick trend check across timeframes
alignment = get_trend_alignment(symbol="TSLA", exchange="NASDAQ")

print(f"Trend alignment: {alignment['alignment']}")  # bullish, bearish, mixed
print(f"Timeframes aligned: {alignment['aligned_count']}/{alignment['total_timeframes']}")

for tf in alignment['timeframes']:
    direction = "🟢" if tf['direction'] == 'up' else "🔴" if tf['direction'] == 'down' else "⚪"
    print(f"  {direction} {tf['interval']}: {tf['direction']}")
```

## Compare Specific Timeframes

```python
from skills.tradingview.scripts.analysis.compare_timeframes import compare_timeframes

# Compare only specific timeframes of interest
comparison = compare_timeframes(
    symbol="BTCUSD",
    screener="crypto",
    timeframes=["1h", "4h", "1D"]
)

print(f"Comparing: {comparison['timeframes']}")
print(f"Consensus: {comparison['consensus']}")

for result in comparison['results']:
    print(f"{result['interval']}: {result['recommendation']} (strength: {result['strength']:.2f})")
```

## Chart Generation

### Chart for Chat (Embeddable)

Always save charts to `/home/user/chat_files/` so they appear in the user's Charts tab in the sidebar.

```python
import os
from skills.tradingview.scripts.charts.create_chart_for_chat import create_chart_for_chat

# Create an embeddable chart
chart = create_chart_for_chat(
    symbol="AAPL",
    interval="D",  # Daily
    indicators=["RSI", "MACD"]  # Optional indicators
)

# Save to chat_files so it shows in the Charts tab
os.makedirs("/home/user/chat_files", exist_ok=True)
path = f"/home/user/chat_files/{chart['filename']}"
with open(path, "w") as f:
    f.write(chart["html"])

print(f"Chart saved: {chart['filename']}")
print(f"Description: {chart['description']}")
# Tell the user to check the Charts tab in the sidebar
```

### Symbol Overview Widget

```python
from skills.tradingview.scripts.charts.create_symbol_overview import create_symbol_overview

# Create overview widget for multiple symbols
overview = create_symbol_overview(symbols=["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA"])

print(f"Widget HTML: {overview['html'][:100]}...")
```

### Technical Analysis Panel

```python
from skills.tradingview.scripts.charts.create_technical_analysis_panel import create_technical_analysis_panel

# Create TA panel widget
ta_panel = create_technical_analysis_panel(symbol="NVDA")

print(f"TA Panel HTML: {ta_panel['html'][:100]}...")
```

### Watchlist Dashboard

```python
from skills.tradingview.scripts.charts.create_watchlist_dashboard import create_watchlist_dashboard

# Create watchlist with multiple symbols
dashboard = create_watchlist_dashboard(symbols=["SPY", "QQQ", "IWM", "VIX"])

print(f"Dashboard HTML: {dashboard['html'][:100]}...")
```

## Trading Strategies

### Trend Following

```python
def trend_follow_signal(symbol):
    """Enter when trend aligns bullish across timeframes"""
    alignment = get_trend_alignment(symbol=symbol, exchange="NASDAQ")
    
    if alignment['alignment'] == 'bullish' and alignment['aligned_count'] >= 3:
        # Check individual timeframes for confirmation
        mtf = get_multi_timeframe_analysis(symbol=symbol, screener="america")
        daily = next((t for t in mtf['timeframes'] if t['interval'] == '1D'), None)
        
        if daily and daily['recommendation'] == 'BUY':
            print(f"🟢 Trend follow BUY signal for {symbol}")
            return True
    
    return False
```

### Mean Reversion

```python
def mean_reversion_signal(symbol):
    """Look for oversold conditions with potential reversal"""
    ta = get_technical_analysis(symbol=symbol, screener="america", interval="1D")
    
    # Check if oversold on oscillators but price near support
    rsi = next((o for o in ta['oscillators'] if o['name'] == 'RSI'), None)
    stoch = next((o for o in ta['oscillators'] if o['name'] == 'Stochastic'), None)
    
    if rsi and stoch:
        rsi_value = rsi['value']
        stoch_value = stoch['value']
        
        # Oversold conditions
        if rsi_value < 30 and stoch_value < 20:
            # Check if MAs are turning
            ema50 = next((ma for ma in ta['moving_averages'] if '50' in ma['name']), None)
            if ema50 and ema50['signal'] in ['BUY', 'NEUTRAL']:
                print(f"🟡 Mean reversion candidate: {symbol} (RSI: {rsi_value:.1f})")
                return True
    
    return False
```

### Multi-Timeframe Entry

```python
def multi_tf_entry(symbol):
    """Require alignment across 3 timeframes before entry"""
    comparison = compare_timeframes(
        symbol=symbol,
        screener="america",
        timeframes=["1h", "4h", "1D"]
    )
    
    # All 3 must agree
    recommendations = [r['recommendation'] for r in comparison['results']]
    
    if all(r == 'BUY' for r in recommendations):
        print(f"🟢 Strong multi-TF BUY: {symbol}")
        return 'buy'
    elif all(r == 'SELL' for r in recommendations):
        print(f"🔴 Strong multi-TF SELL: {symbol}")
        return 'sell'
    
    return None
```

## Common Workflows

### Screen for Technical Setups

```python
def screen_technical_setups(symbols):
    setups = []
    
    for symbol in symbols:
        ta = get_technical_analysis(symbol=symbol, screener="america", interval="1D")
        
        # Skip if no data
        if 'error' in ta:
            continue
        
        # Check for strong buy signal
        if ta['recommendation'] == 'BUY':
            alignment = get_trend_alignment(symbol=symbol, exchange="NASDAQ")
            
            if alignment['alignment'] == 'bullish':
                setups.append({
                    'symbol': symbol,
                    'signal': 'BUY',
                    'strength': alignment['aligned_count'],
                    'timeframes': alignment['timeframes']
                })
    
    # Sort by strength
    setups.sort(key=lambda x: x['strength'], reverse=True)
    return setups

# Usage
setups = screen_technical_setups(["AAPL", "MSFT", "NVDA", "TSLA", "AMD"])
for setup in setups[:5]:
    print(f"{setup['symbol']}: {setup['signal']} (strength {setup['strength']}/5)")
```

### Create Analysis Report

```python
def create_analysis_report(symbol):
    """Generate comprehensive TA report"""
    report = []
    
    # Single timeframe analysis
    ta = get_technical_analysis(symbol=symbol, screener="america", interval="1D")
    report.append(f"# Technical Analysis: {symbol}")
    report.append(f"\nOverall: {ta['recommendation']}")
    
    # Multi-timeframe
    mtf = get_multi_timeframe_analysis(symbol=symbol, screener="america")
    report.append("\n## Multi-Timeframe")
    for tf in mtf['timeframes']:
        report.append(f"- {tf['interval']}: {tf['recommendation']}")
    
    # Trend alignment
    alignment = get_trend_alignment(symbol=symbol, exchange="NASDAQ")
    report.append(f"\n## Trend Alignment")
    report.append(f"Overall: {alignment['alignment']}")
    
    # Generate chart
    chart = create_chart_for_chat(symbol=symbol, interval="D")
    report.append(f"\n## Chart")
    report.append(f"Widget: {chart['html'][:50]}...")
    
    return "\n".join(report)
```

## Notes

- Screener values: `"america"` (US stocks), `"crypto"` (crypto), `"forex"` (FX)
- Intervals: `"1m"`, `"5m"`, `"15m"`, `"1h"`, `"4h"`, `"1D"`, `"1W"`, `"1M"`
- Recommendations: `"BUY"`, `"SELL"`, `"NEUTRAL"`, `"STRONG_BUY"`, `"STRONG_SELL"`
- **Always save charts to `/home/user/chat_files/`** — this makes them appear in the Charts tab in the sidebar
- After saving, tell the user the chart is ready and they can view it in the Charts tab

## When to Use This Skill

- User asks for a technical analysis of a stock or crypto
- User wants to know if a stock is in an uptrend, downtrend, or sideways
- User asks for RSI, MACD, moving averages, or other indicators
- User wants an embeddable chart widget in their chat
- User asks "is now a good time to buy X" from a technical perspective
- Combine with `polygon_io` for raw price data and `financial_modeling_prep` for fundamentals
