"""
Demo: Direct API Access Pattern in Code Execution

This shows how the new pattern works - code can directly call APIs
without data flowing through the LLM context.
"""

# This is what gets auto-imported in every execute_code call
from finch_runtime import fmp, reddit, fetch_multiple_stocks, combine_financial_data

print("=" * 70)
print("DIRECT API ACCESS DEMO")
print("=" * 70)

# Example 1: Get quote for single stock
print("\n1. Single stock quote:")
quote = fmp.get_quote('AAPL')
if quote:
    print(f"   AAPL: ${quote['price']:.2f} ({quote['changesPercentage']:+.2f}%)")

# Example 2: Batch fetch multiple stocks
print("\n2. Batch fetch (5 stocks):")
tickers = ['AAPL', 'MSFT', 'GOOGL', 'NVDA', 'TSLA']
quotes = fetch_multiple_stocks(tickers, 'quote')
for ticker, quote in quotes.items():
    print(f"   {ticker}: ${quote['price']:.2f}")

# Example 3: Reddit sentiment + fundamentals
print("\n3. Reddit trending + fundamentals screening:")
trending = reddit.get_trending(limit=10)
if trending:
    print(f"   Found {len(trending)} trending stocks on Reddit")
    
    # Filter by P/E ratio
    good_picks = []
    for stock in trending[:5]:  # Check top 5
        ticker = stock['ticker']
        metrics = fmp.get_key_metrics(ticker, limit=1)
        if metrics and len(metrics) > 0:
            pe = metrics[0].get('peRatio', 999)
            if pe < 25:
                good_picks.append({
                    'ticker': ticker,
                    'mentions': stock['mentions'],
                    'pe': pe
                })
    
    print(f"   {len(good_picks)} have P/E < 25:")
    for pick in good_picks:
        print(f"   - {pick['ticker']}: {pick['mentions']} mentions, P/E={pick['pe']:.1f}")

# Example 4: Insider trading analysis
print("\n4. Insider trading (last 100 transactions):")
trades = fmp.get_insider_trading('NVDA', limit=100)
if trades:
    purchases = [t for t in trades if 'Purchase' in t.get('transactionType', '')]
    sales = [t for t in trades if 'Sale' in t.get('transactionType', '')]
    print(f"   NVDA: {len(purchases)} purchases, {len(sales)} sales")
    
    # Calculate total value
    buy_value = sum(t.get('securitiesTransacted', 0) * t.get('price', 0) for t in purchases)
    print(f"   Total insider buying: ${buy_value/1e6:.1f}M")

# Example 5: Comprehensive financial data
print("\n5. Combined financial data:")
financials = combine_financial_data('TSLA')
if financials['quote'] and financials['metrics']:
    print(f"   TSLA:")
    print(f"   - Price: ${financials['quote']['price']:.2f}")
    if financials['metrics']:
        print(f"   - P/E Ratio: {financials['metrics'][0].get('peRatio', 'N/A')}")
        print(f"   - Market Cap: ${financials['metrics'][0].get('marketCap', 0)/1e9:.1f}B")

print("\n" + "=" * 70)
print("✓ All API calls happened in code - no data through LLM context!")
print("=" * 70)

