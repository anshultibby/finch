"""
Generate servers directory tree for LLM context.

Used in both:
1. Tool description (so LLM knows what APIs are available)
2. Code execution (so LLM sees the actual mounted filesystem)
"""
import os
from pathlib import Path
from typing import Optional


def get_servers_dir() -> Path:
    """Get the path to the servers directory."""
    return Path(__file__).parent / "servers"


def generate_servers_tree(base_dir: Optional[Path] = None) -> str:
    """
    Generate a tree representation of the servers directory.
    
    Args:
        base_dir: Base directory containing servers/. If None, uses the default location.
        
    Returns:
        String representation of the file tree with import paths.
    """
    if base_dir is None:
        servers_dir = get_servers_dir()
    else:
        servers_dir = base_dir / "servers"
    
    if not servers_dir.exists():
        return "servers/ directory not found"
    
    lines = ["servers/"]
    
    # Get all server directories (skip __pycache__, hidden files)
    server_dirs = sorted([
        d for d in servers_dir.iterdir() 
        if d.is_dir() and not d.name.startswith('_') and not d.name.startswith('.')
    ])
    
    for i, server_dir in enumerate(server_dirs):
        is_last_server = (i == len(server_dirs) - 1)
        prefix = "└── " if is_last_server else "├── "
        lines.append(f"{prefix}{server_dir.name}/")
        
        # Build tree for this server
        _add_directory_contents(
            server_dir, 
            lines, 
            "    " if is_last_server else "│   ",
            server_dir.name
        )
    
    return "\n".join(lines)


def _add_directory_contents(
    directory: Path, 
    lines: list, 
    prefix: str,
    import_prefix: str
):
    """Recursively add directory contents to the tree."""
    # Get all items, filter out __pycache__, hidden, and internal files
    items = sorted([
        item for item in directory.iterdir()
        if not item.name.startswith('_') 
        and not item.name.startswith('.')
        and item.name != '__pycache__'
    ])
    
    # Separate directories and Python files
    dirs = [item for item in items if item.is_dir()]
    py_files = [item for item in items if item.is_file() and item.suffix == '.py']
    
    all_items = dirs + py_files
    
    for i, item in enumerate(all_items):
        is_last = (i == len(all_items) - 1)
        connector = "└── " if is_last else "├── "
        
        if item.is_dir():
            lines.append(f"{prefix}{connector}{item.name}/")
            new_prefix = prefix + ("    " if is_last else "│   ")
            new_import = f"{import_prefix}.{item.name}"
            _add_directory_contents(item, lines, new_prefix, new_import)
        else:
            # Python file - show the import path
            module_name = item.stem
            import_path = f"servers.{import_prefix}.{module_name}"
            lines.append(f"{prefix}{connector}{item.name:<30} # from {import_path} import ...")


def generate_servers_description() -> str:
    """
    Generate the full servers description for tool context.
    
    Returns a formatted string with:
    - The file tree
    - Usage examples
    - Important rules
    """
    tree = generate_servers_tree()
    
    description = """
**🔌 API SERVERS - Available APIs**

The following APIs are available as importable Python modules:

```
""" + tree + """
```

**Usage Examples:**

```python
# Intraday bars (Polygon.io) - for backtesting/strategies
from servers.polygon_io.market.intraday import get_intraday_bars
response = get_intraday_bars(
    symbol='NVDA',              # Stock ticker (required)
    from_datetime='2024-12-01', # Start date YYYY-MM-DD (required)
    to_datetime='2024-12-31',   # End date YYYY-MM-DD (required)
    timespan='15min'            # '1min', '5min', '15min', '30min', '1hour'
)
# ALWAYS check for errors before accessing data!
if 'error' in response:
    print(f"Error: {response['error']}")
else:
    df = pd.DataFrame(response['bars'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')

# Historical daily prices (Polygon.io)
from servers.polygon_io.market.historical_prices import get_historical_prices
response = get_historical_prices(
    symbol='AAPL',              # Stock ticker (required)
    from_date='2024-01-01',     # Start date YYYY-MM-DD (required)
    to_date='2024-12-31',       # End date YYYY-MM-DD (required)
    timespan='day'              # 'day', 'week', 'month' (default='day')
)
if 'error' in response:
    print(f"Error: {response['error']}")
else:
    df = pd.DataFrame(response['bars'])

# Quote snapshot with fundamentals (FMP)
from servers.financial_modeling_prep.market.quote import get_quote_snapshot
quotes = get_quote_snapshot('AAPL')  # Returns LIST even for single stock!
quote = quotes[0]  # Access first result
print(f"{quote['symbol']}: ${quote['price']} | PE: {quote['pe']}")

# Market gainers (FMP) - filter for liquid stocks!
from servers.financial_modeling_prep.market.gainers import get_gainers
gainers = get_gainers()
liquid = [g for g in gainers if g.get('price', 0) > 10]

# Company profile (FMP)
from servers.financial_modeling_prep.company.profile import get_profile
profile = get_profile('AAPL')
```

**⚠️ COMMON MISTAKES TO AVOID:**
- ALL Polygon price functions use `symbol=` not `ticker=`:
  - `get_historical_prices(symbol='AAPL', ...)` ✓
  - `get_intraday_bars(symbol='NVDA', ...)` ✓
  - `get_historical_prices(ticker='AAPL', ...)` ✗ WRONG!
- **ALWAYS check for errors before accessing data:**
  ```python
  response = get_historical_prices(symbol='AAPL', ...)
  if 'error' in response:
      print(f"Error: {response['error']}")  # Handle error!
  else:
      df = pd.DataFrame(response['bars'])  # Safe to access
  ```
- `get_quote_snapshot()` returns a LIST, use `quotes[0]` for single stock
- Response from price APIs is a dict with `'bars'` key, not a list directly
- Always convert timestamp: `pd.to_datetime(df['timestamp'], unit='ms')`

**When to use which API:**
- `polygon_io.market.intraday` → Intraday bars (1min to 1hour)
- `polygon_io.market.historical_prices` → Daily/weekly/monthly bars
- `financial_modeling_prep.market.quote` → Quote with PE, market cap, EPS
- `financial_modeling_prep.market.gainers` → Market movers (filter for liquidity!)
- `kalshi.portfolio` → Kalshi prediction market balance & positions
- `kalshi.markets` → Kalshi events and market data

**🎰 KALSHI (Prediction Markets):**
```python
# Requires user to have saved Kalshi API credentials in Settings > API Keys

# Get account balance
from servers.kalshi.portfolio import get_kalshi_balance
balance = get_kalshi_balance()
if 'error' not in balance:
    print(f"Kalshi balance: ${balance['balance']:.2f}")

# Get portfolio (balance + positions)
from servers.kalshi.portfolio import get_kalshi_portfolio
portfolio = get_kalshi_portfolio()
if 'error' not in portfolio:
    print(f"Balance: ${portfolio['balance']:.2f}")
    for pos in portfolio['positions']:
        print(f"  {pos['ticker']}: {pos['count']} contracts")

# Get open prediction market events
from servers.kalshi.markets import get_kalshi_events
events = get_kalshi_events(limit=10, status="open")
if 'error' not in events:
    for event in events['events']:
        print(f"{event['ticker']}: {event['title']}")

# Get specific market details
from servers.kalshi.markets import get_kalshi_market
market = get_kalshi_market("KXBTC-24DEC31-T100000")
```

**🎲 DOME API (Prediction Markets via Dome):**
```python
# Alternative API for accessing prediction markets with better rate limits
# Dome API Key: Free tier = 1 request per second (automatically rate limited)

# Search Polymarket markets
from servers.dome.polymarket.markets import get_markets
markets = get_markets(tags=['crypto'], limit=10)
if 'error' not in markets:
    for m in markets['markets']:
        print(f"{m['title']}: ${m['volume']:,.0f} volume")

# Get Polymarket market prices
from servers.dome.polymarket.prices import get_market_price, get_candlesticks
price = get_market_price(token_id="98250445447699368679516...")
if 'error' not in price:
    print(f"Probability: {price['price']*100:.1f}%")

# Get historical candlestick data (for charting)
import time
end = int(time.time())
start = end - (7 * 24 * 60 * 60)  # 1 week ago
candles = get_candlesticks(
    condition_id="0x4567b275...",
    start_time=start,
    end_time=end,
    interval=1440  # Daily candles
)

# Track trade history
from servers.dome.polymarket.trading import get_trade_history
trades = get_trade_history(condition_id="0x4567...", limit=50)
# Or track specific wallet: trades = get_trade_history(maker_address="0xabc...")

# Monitor wallet positions & P&L
from servers.dome.polymarket.wallet import get_wallet, get_wallet_pnl
wallet = get_wallet("0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb")
pnl = get_wallet_pnl("0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb")
if 'error' not in pnl:
    print(f"Total P&L: ${pnl['total_pnl']:,.2f}, Win rate: {pnl['win_rate']*100:.1f}%")

# Search Kalshi markets via Dome
from servers.dome.kalshi.markets import get_markets as get_kalshi_markets
markets = get_kalshi_markets(series_ticker='FED', status='active')

# Find matching markets across platforms (arbitrage opportunities)
from servers.dome.matching.sports import get_sports_matching_markets, get_sport_by_date
matches = get_sports_matching_markets(sport='NBA', limit=20)
# Or get markets for specific date:
matches = get_sport_by_date(sport='NBA', date='2024-12-25')
```

**⚠️ RATE LIMITING:**
- Dome API free tier: 1 request per second (handled automatically)
- The client will automatically wait between requests
- For multiple requests, they'll be queued and executed sequentially
"""
    return description


if __name__ == "__main__":
    # Test the tree generation
    print(generate_servers_tree())
    print("\n" + "="*60 + "\n")
    print(generate_servers_description())

