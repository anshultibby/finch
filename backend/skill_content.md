# Polymarket Top Traders & Kalshi Arbitrage

This skill helps you find top-performing traders on Polymarket and identify corresponding opportunities on Kalshi for arbitrage or copy trading.

## Overview

**When to use this skill:**
- User asks about finding profitable wallets to copy trade
- User wants to analyze successful prediction market traders
- User is looking for cross-platform arbitrage between Polymarket and Kalshi
- User wants to understand what markets top traders are betting on

## Step 1: Find High-Volume Polymarket Markets

Top traders congregate in high-volume markets. Start by identifying active markets:

```python
from servers.dome.polymarket.markets import get_markets
from servers.dome.models import GetMarketsInput

# Get high-volume markets (top traders trade here)
result = get_markets(GetMarketsInput(
    min_volume=1000000,  # $1M+ volume markets
    status='open',
    limit=20
))

for market in result.markets:
    print(f"{market.market_slug}: Volume=${market.volume_total:,.0f}, Title={market.title}")
```

**Key fields to note:**
- `market_slug` - Used for all subsequent queries
- `condition_id` - Unique market identifier
- `side_a.id` / `side_b.id` - Token IDs for Yes/No outcomes
- `volume_total` - Higher volume = more trader activity

## Step 2: Get Market Trade History to Identify Active Wallets

Once you have high-volume markets, get recent trades to find active wallets:

```python
from servers.dome.polymarket.trading import get_orders
from servers.dome.models import GetOrdersInput

# Get recent trades for a specific market
result = get_orders(GetOrdersInput(
    market_slug='bitcoin-100k',  # Example: Bitcoin $100k market
    limit=100
))

# Extract unique wallet addresses from trades
wallets = set()
for order in result.orders:
    wallets.add(order.user)  # Maker wallet
    wallets.add(order.taker)  # Taker wallet

print(f"Found {len(wallets)} unique wallets trading in this market")
```

## Step 3: Analyze Wallet P&L to Find Top Performers

For each promising wallet, check their realized P&L:

```python
from servers.dome.polymarket.wallet import get_wallet_pnl, get_wallet_info
from servers.dome.models import GetWalletPnLInput, GetWalletInfoInput

wallet_address = '0x...'  # Wallet from trade history

# First get wallet info (converts EOA to proxy if needed)
info = get_wallet_info(GetWalletInfoInput(wallet_address=wallet_address))
proxy_address = info.proxy  # Most APIs need proxy address

# Get P&L over last 30 days
import time
end_time = int(time.time())
start_time = end_time - (30 * 24 * 60 * 60)  # 30 days ago

pnl_result = get_wallet_pnl(GetWalletPnLInput(
    wallet_address=proxy_address,
    granularity='day',
    start_time=start_time,
    end_time=end_time
))

print(f"Wallet: {wallet_address}")
print(f"30-day realized P&L: ${pnl_result.total_pnl:,.2f}")

# View daily breakdown
for point in pnl_result.pnl_over_time:
    print(f"  Day: {point.timestamp}, P&L: ${point.pnl_to_date:,.2f}")
```

**Top Trader Criteria:**
- Positive realized P&L over 30+ days
- Consistent trading activity (not just one lucky trade)
- Trading volume > $10K (indicates serious trader)

## Step 4: Analyze Top Trader Positions

Get current positions of high-performing wallets:

```python
from servers.dome.polymarket.wallet import get_positions
from servers.dome.models import GetPositionsInput

positions = get_positions(GetPositionsInput(
    wallet_address=proxy_address,
    limit=50
))

print(f"\nCurrent positions for top trader:")
for pos in positions.positions:
    print(f"  - {pos.title[:60]}...")
    print(f"    Market: {pos.market_slug}")
    print(f"    Position: {pos.shares_normalized:,.2f} shares {pos.label}")
    print(f"    Condition ID: {pos.condition_id}")
    print()
```

## Step 5: Find Corresponding Kalshi Markets

For each Polymarket position, search for the equivalent market on Kalshi:

```python
from servers.dome.kalshi.markets import get_markets as get_kalshi_markets
from servers.dome.models import GetKalshiMarketsInput

# Extract keywords from Polymarket market title
keywords = ['bitcoin', '100k', '2024']  # Example keywords

# Search Kalshi for matching markets
kalshi_result = get_kalshi_markets(GetKalshiMarketsInput(
    search=' '.join(keywords),
    status='open',
    limit=10
))

print(f"\nKalshi markets matching Polymarket position:")
for market in kalshi_result.markets:
    print(f"  - {market.title}")
    print(f"    Ticker: {market.event_ticker}")
    print(f"    Yes bid: {market.yes_bid}¢, Yes ask: {market.yes_ask}¢")
    print()
```

## Step 6: Calculate Arbitrage Opportunity

Compare prices between Polymarket and Kalshi:

```python
from servers.dome.polymarket.prices import get_market_price
from servers.dome.models import GetMarketPriceInput, GetKalshiMarketPriceInput
from servers.dome.kalshi.markets import get_market_price as get_kalshi_price

# Polymarket price (0-1 probability)
pm_result = get_market_price(GetMarketPriceInput(
    token_id=pos.token_id  # From position
))
pm_price = pm_result.price  # e.g., 0.65 = 65%

# Kalshi price (in cents, 0-100)
kalshi_result = get_kalshi_price(GetKalshiMarketPriceInput(
    ticker=kalshi_market.event_ticker
))
kalshi_price = kalshi_result.price / 100  # Convert to 0-1

# Calculate spread
spread = abs(pm_price - kalshi_price)
print(f"\nArbitrage Analysis:")
print(f"  Polymarket: {pm_price:.2%}")
print(f"  Kalshi: {kalshi_price:.2%}")
print(f"  Spread: {spread:.2%}")

if spread > 0.05:  # 5% threshold
    print(f"  ⚠️ Arbitrage opportunity detected!")
    if pm_price > kalshi_price:
        print(f"  → Sell on Polymarket, Buy on Kalshi")
    else:
        print(f"  → Buy on Polymarket, Sell on Kalshi")
```

## Step 7: Get Detailed Trade History

For copy trading analysis, get complete trade history:

```python
from servers.dome.polymarket.wallet import get_wallet_trades
from servers.dome.models import GetWalletTradesInput

# Get all trades for the last 30 days
trades = get_wallet_trades(GetWalletTradesInput(
    wallet_address=proxy_address,
    start_time=start_time,
    end_time=end_time,
    limit=100
))

print(f"\nTrade History (Last 30 days):")
for trade in trades.orders:
    print(f"  {trade.timestamp}: {trade.side} {trade.shares_normalized:.2f} shares @ {trade.price:.2%}")
    print(f"    Market: {trade.title[:50]}...")
    print(f"    Token: {trade.token_label}")
    print()
```

## Complete Workflow Example

Here's a complete script to find top traders and arbitrage:

```python
import time
from servers.dome.polymarket.markets import get_markets
from servers.dome.polymarket.trading import get_orders
from servers.dome.polymarket.wallet import get_wallet_pnl, get_wallet_info, get_positions
from servers.dome.kalshi.markets import get_markets as get_kalshi_markets, get_market_price as get_kalshi_price
from servers.dome.models import *

# 1. Get high-volume markets
markets = get_markets(GetMarketsInput(min_volume=500000, limit=10))

# 2. For each market, get trades and find wallets
for market in markets.markets[:3]:  # Top 3 markets
    print(f"\n=== Analyzing {market.title} ===")
    
    # Get recent trades
    orders = get_orders(GetOrdersInput(market_slug=market.market_slug, limit=50))
    wallets = list(set(o.user for o in orders.orders))[:5]  # Sample 5 wallets
    
    # 3. Check P&L for each wallet
    for wallet in wallets:
        try:
            info = get_wallet_info(GetWalletInfoInput(wallet_address=wallet))
            pnl = get_wallet_pnl(GetWalletPnLInput(
                wallet_address=info.proxy,
                granularity='month',
                start_time=int(time.time()) - 90*24*60*60
            ))
            
            if pnl.total_pnl > 10000:  # $10K+ profit
                print(f"\n🔥 Top Trader Found!")
                print(f"   Wallet: {wallet}")
                print(f"   90-day P&L: ${pnl.total_pnl:,.2f}")
                
                # Get positions
                positions = get_positions(GetPositionsInput(wallet_address=info.proxy))
                
                # 4. Find Kalshi equivalents
                for pos in positions.positions[:3]:
                    kalshi = get_kalshi_markets(GetKalshiMarketsInput(
                        search=pos.title[:30],
                        limit=3
                    ))
                    if kalshi.markets:
                        print(f"   Kalshi match: {kalshi.markets[0].event_ticker}")
                        
        except Exception as e:
            continue
```

## Key API References

**DOME Polymarket:**
- `servers.dome.polymarket.markets.get_markets` - Browse markets
- `servers.dome.polymarket.trading.get_orders` - Get market trades
- `servers.dome.polymarket.wallet.get_wallet_pnl` - Check trader performance
- `servers.dome.polymarket.wallet.get_positions` - Current holdings
- `servers.dome.polymarket.wallet.get_wallet_trades` - Trade history
- `servers.dome.polymarket.prices.get_market_price` - Current prices

**DOME Kalshi:**
- `servers.dome.kalshi.markets.get_markets` - Search Kalshi markets
- `servers.dome.kalshi.markets.get_market_price` - Get Kalshi prices

**Models:** Import from `servers.dome.models`

## Testing Recommendations

Always test your analysis before recommending trades:

1. **Verify P&L calculation:** Compare `get_wallet_pnl` with `get_wallet_trades` to ensure consistency
2. **Check price accuracy:** Compare `get_market_price` on both platforms before calculating spreads
3. **Validate wallet activity:** Ensure wallets have >10 trades (not just lucky winners)
4. **Cross-check markets:** Verify Kalshi markets match Polymarket questions exactly
5. **Test with small amounts:** Recommend paper trading or small positions first

## Important Notes

- DOME API rate limit: 1 request per second (built into client)
- P&L is **realized only** (sells/redeems), not unrealized positions
- Kalshi prices are in cents (divide by 100 to compare with Polymarket 0-1 scale)
- Always use **proxy addresses** for wallet APIs (not EOA)
- Some markets may not have Kalshi equivalents - focus on popular categories (politics, crypto, sports)
