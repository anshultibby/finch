# API Servers

Progressive disclosure for external APIs. Each tool is a Python file with clean docstrings.

## Discovery Pattern

**1. List categories:**
```python
import os
os.listdir('servers/fmp')  # ['company', 'financials', 'market', 'insider', ...]
```

**2. List tools in category:**
```python
os.listdir('servers/fmp/company')  # ['profile.py', 'executives.py']
```

**3. Read tool to understand it:**
```python
with open('servers/fmp/company/profile.py') as f:
    print(f.read())  # See docstring with args and return fields
```

**4. Import and use:**
```python
from servers.fmp.company.profile import get_profile
profile = get_profile('AAPL')
```

## Available Servers

- **fmp/** - Financial Modeling Prep (stocks, financials, market data)
- **polygon/** - Polygon.io (historical prices, quotes)
- **reddit/** - Reddit sentiment (trending stocks)
- **snaptrade/** - SnapTrade (secure portfolio access via OAuth)
- **tradingview/** - TradingView (technical analysis, charts)

## Why This Works

- **Progressive disclosure**: Don't load all tools upfront, discover as needed
- **Token efficient**: Only read files you actually need
- **Self-documenting**: Python docstrings are the documentation
- **Easy to extend**: Add new tool = add new .py file
