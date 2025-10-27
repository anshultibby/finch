"""
Test script for analyzing buy transactions from insider trading data
This test fetches 100 buy transactions and analyzes the output size
"""
import asyncio
import sys
import json
from datetime import datetime
from modules.insider_trading_tools import insider_trading_tools


async def test_last_100_buy_transactions():
    """
    Test fetching the last 100 buy transactions (P-Purchase) from insider trades
    This will help analyze why the content size is so large
    """
    print("\n" + "="*80)
    print("TEST: Last 100 Buy Transactions (P-Purchase)")
    print("="*80)
    print(f"⏰ Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    # Use search_insider_trades with transaction_type filter for purchases
    result = await insider_trading_tools.search_insider_trades(
        transaction_type="P-Purchase",
        limit=100,
        page=0
    )
    
    if not result.get("success"):
        print(f"❌ Failed: {result.get('message')}")
        return False
    
    # Parse CSV data
    trades_csv = result.get("trades_csv", "")
    if not trades_csv:
        print(f"❌ No CSV data returned")
        return False
    
    # Convert CSV to list of dicts for analysis
    import csv
    from io import StringIO
    csv_reader = csv.DictReader(StringIO(trades_csv))
    trades = list(csv_reader)
    
    print(f"✅ Successfully fetched {len(trades)} buy transactions\n")
    
    # Analyze the output size
    print("="*80)
    print("OUTPUT SIZE ANALYSIS")
    print("="*80)
    
    # Convert to JSON to measure size
    result_json = json.dumps(result, indent=2)
    result_json_compact = json.dumps(result)
    
    size_formatted = len(result_json)
    size_compact = len(result_json_compact)
    
    print(f"📊 Size Statistics:")
    print(f"   - Formatted JSON: {size_formatted:,} characters ({size_formatted/1024:.2f} KB)")
    print(f"   - Compact JSON: {size_compact:,} characters ({size_compact/1024:.2f} KB)")
    print(f"   - Number of trades: {len(trades)}")
    print(f"   - Avg size per trade: {size_compact/max(len(trades), 1):.0f} characters")
    
    # Analyze CSV structure
    if trades:
        print(f"\n{'='*80}")
        print("CSV DATA STRUCTURE")
        print("="*80)
        
        # Show first few lines of CSV
        csv_lines = trades_csv.split('\n')
        print(f"CSV header: {csv_lines[0]}")
        print(f"Sample row: {csv_lines[1] if len(csv_lines) > 1 else 'N/A'}")
        print(f"\nCSV size: {len(trades_csv):,} characters")
        print(f"Avg size per row: {len(trades_csv)/max(len(trades), 1):.0f} characters")
        
        sample_trade = trades[0]
        print(f"\n{'='*80}")
        print("SAMPLE TRADE DATA (parsed from CSV)")
        print("="*80)
        
        for key, value in sample_trade.items():
            if isinstance(value, str) and len(str(value)) > 100:
                print(f"  {key}: {str(value)[:100]}... (truncated, full length: {len(str(value))})")
            else:
                print(f"  {key}: {value}")
    
    # Show summary statistics
    print(f"\n{'='*80}")
    print("TRADE SUMMARY STATISTICS")
    print("="*80)
    
    # Extract symbols from CSV (note: CSV has different field names from to_df_row)
    # The CSV has columns like: date, insider, position, type, shares, price
    # We need to parse the original result to get symbols since they're not in the compact CSV
    symbols = {}
    # For now, skip symbol analysis since CSV doesn't include it
    
    print(f"\n📈 Note: Symbol information not in compact CSV format")
    print(f"   Total trades: {len(trades)}")
    
    # Analyze transaction amounts (from CSV 'shares' column)
    print(f"\n💰 Transaction Size Analysis:")
    shares_list = []
    for trade in trades:
        shares_str = trade.get('shares', '0')
        try:
            shares = float(shares_str) if shares_str != 'N/A' else 0
            if shares > 0:
                shares_list.append(shares)
        except:
            pass
    
    if shares_list:
        avg_shares = sum(shares_list) / len(shares_list)
        max_shares = max(shares_list)
        min_shares = min(shares_list)
        
        print(f"   Average shares: {avg_shares:,.0f}")
        print(f"   Max shares: {max_shares:,.0f}")
        print(f"   Min shares: {min_shares:,.0f}")
    
    # Analyze prices (from CSV 'price' column)
    prices = []
    for trade in trades:
        price_str = trade.get('price', '0')
        try:
            price = float(price_str) if price_str != 'N/A' else 0
            if price > 0:
                prices.append(price)
        except:
            pass
    
    if prices:
        avg_price = sum(prices) / len(prices)
        max_price = max(prices)
        min_price = min(prices)
        
        print(f"\n💵 Price Analysis:")
        print(f"   Average price: ${avg_price:,.2f}")
        print(f"   Max price: ${max_price:,.2f}")
        print(f"   Min price: ${min_price:,.2f}")
    
    # Show CSV vs old format comparison
    print(f"\n{'='*80}")
    print("SIZE COMPARISON: CSV vs OLD SPLIT FORMAT")
    print("="*80)
    
    # Estimate old format size (was ~669 chars per trade for 16 fields)
    old_format_estimate = len(trades) * 669
    csv_size = len(trades_csv)
    savings = old_format_estimate - csv_size
    savings_pct = (savings / old_format_estimate * 100) if old_format_estimate > 0 else 0
    
    print(f"\n📊 Size Comparison:")
    print(f"   Old split format (estimated): {old_format_estimate:,} chars")
    print(f"   New CSV format: {csv_size:,} chars")
    print(f"   Savings: {savings:,} chars ({savings_pct:.1f}% reduction)")
    print(f"   Old format had 16 fields, CSV has 6 essential fields")
    
    # Write full output to file for inspection
    output_file = "/Users/anshul/code/finch/backend/tests/buy_transactions_output.json"
    with open(output_file, 'w') as f:
        json.dump(result, f, indent=2)
    
    print(f"\n{'='*80}")
    print(f"✅ Full output saved to: {output_file}")
    print(f"   File size: {size_formatted/1024:.2f} KB")
    print("="*80)
    
    return True


async def main():
    """Main test runner"""
    try:
        success = await test_last_100_buy_transactions()
        
        print(f"\n{'='*80}")
        print("TEST COMPLETE")
        print("="*80)
        
        if success:
            print("✅ Test passed successfully!")
            return 0
        else:
            print("❌ Test failed!")
            return 1
            
    except Exception as e:
        print(f"\n❌ Test crashed with error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)

