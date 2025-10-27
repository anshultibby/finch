"""
Test script for insider trading tools
Tests both API connectivity and data parsing
"""
import asyncio
import sys
from datetime import datetime
from modules.insider_trading_tools import insider_trading_tools

async def test_recent_senate_trades():
    """Test fetching recent Senate trades"""
    print("\n" + "="*80)
    print("TEST 1: Recent Senate Trades")
    print("="*80)
    
    result = await insider_trading_tools.get_recent_senate_trades(limit=5)
    
    if result.get("success"):
        trades = result.get("trades", [])
        print(f"✅ Success! Found {len(trades)} Senate trades")
        
        if trades:
            print("\nSample trade:")
            trade = trades[0]
            print(f"  Senator: {trade.get('firstName')} {trade.get('lastName')}")
            print(f"  Symbol: {trade.get('symbol')}")
            print(f"  Type: {trade.get('type')}")
            print(f"  Amount: {trade.get('amount')}")
            print(f"  Date: {trade.get('transactionDate') or trade.get('disclosureDate')}")
    else:
        print(f"❌ Failed: {result.get('message')}")
    
    return result.get("success")


async def test_recent_house_trades():
    """Test fetching recent House trades"""
    print("\n" + "="*80)
    print("TEST 2: Recent House Trades")
    print("="*80)
    
    result = await insider_trading_tools.get_recent_house_trades(limit=5)
    
    if result.get("success"):
        trades = result.get("trades", [])
        print(f"✅ Success! Found {len(trades)} House trades")
        
        if trades:
            print("\nSample trade:")
            trade = trades[0]
            print(f"  Representative: {trade.get('firstName')} {trade.get('lastName')}")
            print(f"  Symbol: {trade.get('symbol')}")
            print(f"  Type: {trade.get('type')}")
            print(f"  Amount: {trade.get('amount')}")
            print(f"  Date: {trade.get('transactionDate') or trade.get('disclosureDate')}")
    else:
        print(f"❌ Failed: {result.get('message')}")
    
    return result.get("success")


async def test_recent_insider_trades():
    """Test fetching recent corporate insider trades"""
    print("\n" + "="*80)
    print("TEST 3: Recent Corporate Insider Trades")
    print("="*80)
    
    result = await insider_trading_tools.get_recent_insider_trades(limit=5)
    
    if result.get("success"):
        trades = result.get("trades", [])
        print(f"✅ Success! Found {len(trades)} insider trades")
        
        if trades:
            print("\nSample trade:")
            trade = trades[0]
            print(f"  Insider: {trade.get('reporting_name')}")
            print(f"  Position: {trade.get('type_of_owner')}")
            print(f"  Symbol: {trade.get('symbol')}")
            print(f"  Type: {trade.get('transaction_type')}")
            print(f"  Shares: {trade.get('securities_transacted')}")
            print(f"  Price: ${trade.get('price')}")
            print(f"  Date: {trade.get('transaction_date') or trade.get('filing_date')}")
    else:
        print(f"❌ Failed: {result.get('message')}")
    
    return result.get("success")


async def test_ticker_insider_activity():
    """Test fetching insider activity for specific tickers"""
    print("\n" + "="*80)
    print("TEST 4: Ticker-Specific Insider Activity")
    print("="*80)
    
    test_tickers = ["HOOD", "RDDT", "TWLO"]
    
    for ticker in test_tickers:
        print(f"\n🔍 Testing {ticker}...")
        result = await insider_trading_tools.search_ticker_insider_activity(ticker, limit=10)
        
        if result.get("success"):
            trades = result.get("trades", [])
            summary = result.get("summary", {})
            
            print(f"  ✅ Found {summary.get('total_trades', 0)} trades")
            print(f"     Purchases: {summary.get('purchases', 0)}")
            print(f"     Sales: {summary.get('sales', 0)}")
            print(f"     Congressional: {summary.get('congressional_trades', 0)}")
            print(f"     Corporate: {summary.get('corporate_insider_trades', 0)}")
            
            if trades:
                recent = trades[0]
                print(f"     Most recent: {recent.get('transaction_type') or recent.get('type')} on {recent.get('transaction_date') or recent.get('filing_date')}")
        else:
            print(f"  ℹ️  {result.get('message')}")
    
    return True


async def test_portfolio_insider_activity():
    """Test fetching insider activity for a portfolio of stocks"""
    print("\n" + "="*80)
    print("TEST 5: Portfolio Insider Activity (Last 90 Days)")
    print("="*80)
    
    portfolio_tickers = ["HOOD", "RDDT", "TWLO", "RBLX", "U"]
    
    result = await insider_trading_tools.get_portfolio_insider_activity(
        tickers=portfolio_tickers,
        days_back=90
    )
    
    if result.get("success"):
        activity = result.get("portfolio_activity", {})
        tickers_with_activity = result.get("tickers_with_activity", [])
        
        print(f"✅ Success! Found activity in {len(tickers_with_activity)} of {len(portfolio_tickers)} tickers")
        
        for ticker in tickers_with_activity[:3]:  # Show top 3
            ticker_data = activity.get(ticker, {})
            print(f"\n  📊 {ticker}:")
            print(f"     Total trades: {ticker_data.get('total_trades')}")
            print(f"     Purchases: {ticker_data.get('purchases')}")
            print(f"     Sales: {ticker_data.get('sales')}")
            print(f"     Sentiment: {ticker_data.get('sentiment')}")
            
            # Show DataFrame structure
            trades_df = ticker_data.get('trades_df', {})
            if trades_df:
                columns = trades_df.get('columns', [])
                data = trades_df.get('data', [])
                print(f"     Recent trades (DataFrame with {len(data)} rows):")
                print(f"     Columns: {columns}")
                if data:
                    print(f"     Latest: {data[0]}")
    else:
        print(f"❌ Failed: {result.get('message')}")
    
    return result.get("success")


async def run_all_tests():
    """Run all tests"""
    print("\n🧪 INSIDER TRADING API TESTS")
    print(f"⏰ Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    results = []
    
    # Test 1: Senate
    try:
        results.append(("Senate Trades", await test_recent_senate_trades()))
    except Exception as e:
        print(f"❌ Senate test crashed: {e}")
        results.append(("Senate Trades", False))
    
    # Test 2: House
    try:
        results.append(("House Trades", await test_recent_house_trades()))
    except Exception as e:
        print(f"❌ House test crashed: {e}")
        results.append(("House Trades", False))
    
    # Test 3: Insider Trades
    try:
        results.append(("Insider Trades", await test_recent_insider_trades()))
    except Exception as e:
        print(f"❌ Insider trades test crashed: {e}")
        results.append(("Insider Trades", False))
    
    # Test 4: Ticker-specific
    try:
        results.append(("Ticker Activity", await test_ticker_insider_activity()))
    except Exception as e:
        print(f"❌ Ticker activity test crashed: {e}")
        results.append(("Ticker Activity", False))
    
    # Test 5: Portfolio
    try:
        results.append(("Portfolio Activity", await test_portfolio_insider_activity()))
    except Exception as e:
        print(f"❌ Portfolio activity test crashed: {e}")
        import traceback
        traceback.print_exc()
        results.append(("Portfolio Activity", False))
    
    # Summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    
    for test_name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} - {test_name}")
    
    passed_count = sum(1 for _, p in results if p)
    total_count = len(results)
    
    print(f"\n🎯 Results: {passed_count}/{total_count} tests passed")
    
    if passed_count == total_count:
        print("🎉 All tests passed!")
        return 0
    else:
        print("⚠️  Some tests failed")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(run_all_tests())
    sys.exit(exit_code)

