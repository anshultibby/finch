"""
Comprehensive test suite for FMP Tools
Tests all endpoints to verify they work correctly
"""
import asyncio
import sys
import os
from datetime import datetime, timedelta

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from modules.tools.clients.fmp import fmp_tools


class TestResults:
    def __init__(self):
        self.passed = []
        self.failed = []
        self.skipped = []
    
    def add_pass(self, test_name):
        self.passed.append(test_name)
        print(f"✅ PASS: {test_name}")
    
    def add_fail(self, test_name, error):
        self.failed.append((test_name, str(error)))
        print(f"❌ FAIL: {test_name} - {error}")
    
    def add_skip(self, test_name, reason):
        self.skipped.append((test_name, reason))
        print(f"⏭️  SKIP: {test_name} - {reason}")
    
    def print_summary(self):
        total = len(self.passed) + len(self.failed) + len(self.skipped)
        print("\n" + "="*70)
        print("TEST SUMMARY")
        print("="*70)
        print(f"Total Tests: {total}")
        print(f"✅ Passed: {len(self.passed)}")
        print(f"❌ Failed: {len(self.failed)}")
        print(f"⏭️  Skipped: {len(self.skipped)}")
        print(f"Success Rate: {len(self.passed)/(total or 1)*100:.1f}%")
        
        if self.failed:
            print("\n" + "="*70)
            print("FAILED TESTS:")
            print("="*70)
            for name, error in self.failed:
                print(f"  {name}: {error}")


results = TestResults()


async def test_company_profile():
    """Test fetching company profile"""
    try:
        result = await fmp_tools.get_company_profile("AAPL")
        assert result.get("success"), "Should return success"
        assert "company_profile" in result, "Should contain company_profile"
        results.add_pass("get_company_profile")
    except Exception as e:
        results.add_fail("get_company_profile", e)


async def test_income_statement():
    """Test fetching income statement"""
    try:
        result = await fmp_tools.get_income_statement("AAPL", period="annual", limit=5)
        assert result.get("success"), "Should return success"
        assert "data_csv" in result, "Should contain CSV data"
        results.add_pass("get_income_statement")
    except Exception as e:
        results.add_fail("get_income_statement", e)


async def test_balance_sheet():
    """Test fetching balance sheet"""
    try:
        result = await fmp_tools.get_balance_sheet("AAPL", period="annual", limit=5)
        assert result.get("success"), "Should return success"
        assert "data_csv" in result, "Should contain CSV data"
        results.add_pass("get_balance_sheet")
    except Exception as e:
        results.add_fail("get_balance_sheet", e)


async def test_cash_flow():
    """Test fetching cash flow statement"""
    try:
        result = await fmp_tools.get_cash_flow_statement("AAPL", period="annual", limit=5)
        assert result.get("success"), "Should return success"
        assert "data_csv" in result, "Should contain CSV data"
        results.add_pass("get_cash_flow_statement")
    except Exception as e:
        results.add_fail("get_cash_flow_statement", e)


async def test_key_metrics():
    """Test fetching key metrics"""
    try:
        result = await fmp_tools.get_key_metrics("AAPL", period="annual", limit=5)
        assert result.get("success"), "Should return success"
        assert "data_csv" in result, "Should contain CSV data"
        results.add_pass("get_key_metrics")
    except Exception as e:
        results.add_fail("get_key_metrics", e)


async def test_financial_ratios():
    """Test fetching financial ratios"""
    try:
        result = await fmp_tools.get_financial_ratios("AAPL", period="annual", limit=5)
        assert result.get("success"), "Should return success"
        assert "data_csv" in result, "Should contain CSV data"
        results.add_pass("get_financial_ratios")
    except Exception as e:
        results.add_fail("get_financial_ratios", e)


async def test_financial_growth():
    """Test fetching financial growth"""
    try:
        result = await fmp_tools.get_financial_growth("AAPL", period="annual", limit=5)
        assert result.get("success"), "Should return success"
        assert "data_csv" in result, "Should contain CSV data"
        results.add_pass("get_financial_growth")
    except Exception as e:
        results.add_fail("get_financial_growth", e)


async def test_quote():
    """Test fetching real-time quote"""
    try:
        result = await fmp_tools.get_quote("AAPL")
        assert result.get("success"), "Should return success"
        assert "quote" in result, "Should contain quote data"
        results.add_pass("get_quote")
    except Exception as e:
        results.add_fail("get_quote", e)


async def test_historical_prices():
    """Test fetching historical prices"""
    try:
        to_date = datetime.now().strftime("%Y-%m-%d")
        from_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
        result = await fmp_tools.get_historical_prices("AAPL", from_date=from_date, to_date=to_date, limit=30)
        assert result.get("success"), "Should return success"
        assert "data_csv" in result, "Should contain CSV data"
        results.add_pass("get_historical_prices")
    except Exception as e:
        results.add_fail("get_historical_prices", e)


async def test_analyst_recommendations():
    """Test fetching analyst recommendations"""
    try:
        result = await fmp_tools.get_analyst_recommendations("AAPL", limit=10)
        assert result.get("success"), "Should return success"
        assert "data_csv" in result, "Should contain CSV data"
        results.add_pass("get_analyst_recommendations")
    except Exception as e:
        results.add_fail("get_analyst_recommendations", e)


async def test_search_symbol():
    """Test symbol search"""
    try:
        result = await fmp_tools.search_symbol("Apple", limit=5)
        assert result.get("success"), "Should return success"
        assert "results" in result, "Should contain results"
        results.add_pass("search_symbol")
    except Exception as e:
        results.add_fail("search_symbol", e)


async def test_stock_screener():
    """Test stock screener"""
    try:
        result = await fmp_tools.stock_screener(
            market_cap_more_than=1000000000,
            limit=10
        )
        assert result.get("success"), "Should return success"
        assert "results" in result, "Should contain results"
        results.add_pass("stock_screener")
    except Exception as e:
        results.add_fail("stock_screener", e)


async def test_market_gainers():
    """Test market gainers"""
    try:
        result = await fmp_tools.get_market_gainers()
        assert result.get("success"), "Should return success"
        assert "gainers" in result, "Should contain gainers"
        results.add_pass("get_market_gainers")
    except Exception as e:
        results.add_fail("get_market_gainers", e)


async def test_market_losers():
    """Test market losers"""
    try:
        result = await fmp_tools.get_market_losers()
        assert result.get("success"), "Should return success"
        assert "losers" in result, "Should contain losers"
        results.add_pass("get_market_losers")
    except Exception as e:
        results.add_fail("get_market_losers", e)


async def test_most_active():
    """Test most active stocks"""
    try:
        result = await fmp_tools.get_most_active()
        assert result.get("success"), "Should return success"
        assert "most_active" in result, "Should contain most_active"
        results.add_pass("get_most_active")
    except Exception as e:
        results.add_fail("get_most_active", e)


async def test_sector_performance():
    """Test sector performance"""
    try:
        result = await fmp_tools.get_sector_performance()
        assert result.get("success"), "Should return success"
        assert "sectors" in result, "Should contain sectors"
        results.add_pass("get_sector_performance")
    except Exception as e:
        results.add_fail("get_sector_performance", e)


async def test_stock_news():
    """Test stock news"""
    try:
        result = await fmp_tools.get_stock_news(symbols=["AAPL"], limit=5)
        assert result.get("success"), "Should return success"
        assert "news" in result, "Should contain news"
        results.add_pass("get_stock_news")
    except Exception as e:
        results.add_fail("get_stock_news", e)


async def test_etf_holdings():
    """Test ETF holdings"""
    try:
        result = await fmp_tools.get_etf_holdings("SPY")
        assert result.get("success"), "Should return success"
        assert "holdings" in result, "Should contain holdings"
        results.add_pass("get_etf_holdings")
    except Exception as e:
        results.add_fail("get_etf_holdings", e)


async def test_etf_info():
    """Test ETF info"""
    try:
        result = await fmp_tools.get_etf_info("SPY")
        assert result.get("success"), "Should return success"
        assert "info" in result, "Should contain info"
        results.add_pass("get_etf_info")
    except Exception as e:
        results.add_fail("get_etf_info", e)


async def test_stock_peers():
    """Test stock peers"""
    try:
        result = await fmp_tools.get_stock_peers("AAPL")
        assert result.get("success"), "Should return success"
        assert "peers" in result, "Should contain peers"
        results.add_pass("get_stock_peers")
    except Exception as e:
        results.add_fail("get_stock_peers", e)


async def test_price_target():
    """Test price target"""
    try:
        result = await fmp_tools.get_price_target("AAPL")
        assert result.get("success"), "Should return success"
        assert "price_target" in result, "Should contain price_target"
        results.add_pass("get_price_target")
    except Exception as e:
        results.add_fail("get_price_target", e)


async def test_earnings_calendar():
    """Test earnings calendar"""
    try:
        result = await fmp_tools.get_earnings_calendar()
        assert result.get("success"), "Should return success"
        assert "earnings" in result, "Should contain earnings"
        results.add_pass("get_earnings_calendar")
    except Exception as e:
        results.add_fail("get_earnings_calendar", e)


async def test_stock_splits():
    """Test stock splits"""
    try:
        result = await fmp_tools.get_stock_splits("AAPL")
        assert result.get("success"), "Should return success"
        assert "splits" in result, "Should contain splits"
        results.add_pass("get_stock_splits")
    except Exception as e:
        results.add_fail("get_stock_splits", e)


async def test_treasury_rates():
    """Test treasury rates"""
    try:
        result = await fmp_tools.get_treasury_rates()
        assert result.get("success"), "Should return success"
        assert "rates" in result, "Should contain rates"
        results.add_pass("get_treasury_rates")
    except Exception as e:
        results.add_fail("get_treasury_rates", e)


async def test_generic_fetch_endpoint():
    """Test the generic fetch_endpoint method"""
    try:
        # Test with quote endpoint
        result = await fmp_tools.fetch_endpoint("quote", {"symbol": "AAPL"}, "quote_data")
        assert result.get("success"), "Should return success"
        assert "quote_data" in result, "Should contain quote_data"
        results.add_pass("fetch_endpoint (generic)")
    except Exception as e:
        results.add_fail("fetch_endpoint (generic)", e)


async def test_invalid_params():
    """Test that invalid params don't break anything"""
    try:
        # Send invalid params - API should ignore them
        result = await fmp_tools.fetch_endpoint("quote", {
            "symbol": "AAPL",
            "invalid_param_xyz": "should_be_ignored",
            "another_bad_param": 12345
        })
        assert result.get("success"), "Should still succeed with invalid params"
        results.add_pass("invalid_params_handling")
    except Exception as e:
        results.add_fail("invalid_params_handling", e)


async def run_all_tests():
    """Run all tests"""
    print("\n" + "="*70)
    print("STARTING FMP TOOLS COMPREHENSIVE TEST SUITE")
    print("="*70 + "\n")
    
    # Check API key
    if not fmp_tools.api_enabled:
        print("❌ FMP_API_KEY not configured. Please set it in your .env file.")
        print("Get your API key from: https://site.financialmodelingprep.com/developer/docs/pricing")
        return
    
    print("✅ API Key configured\n")
    
    # Core financial data tests
    print("\n--- Core Financial Data ---")
    await test_company_profile()
    await test_income_statement()
    await test_balance_sheet()
    await test_cash_flow()
    await test_key_metrics()
    await test_financial_ratios()
    await test_financial_growth()
    
    # Market data tests
    print("\n--- Market Data ---")
    await test_quote()
    await test_historical_prices()
    await test_analyst_recommendations()
    
    # Search & screening tests
    print("\n--- Search & Screening ---")
    await test_search_symbol()
    await test_stock_screener()
    
    # Market movers tests
    print("\n--- Market Movers ---")
    await test_market_gainers()
    await test_market_losers()
    await test_most_active()
    await test_sector_performance()
    
    # News & info tests
    print("\n--- News & Info ---")
    await test_stock_news()
    
    # ETF tests
    print("\n--- ETF Data ---")
    await test_etf_holdings()
    await test_etf_info()
    
    # Comparison tests
    print("\n--- Comparisons ---")
    await test_stock_peers()
    await test_price_target()
    
    # Calendar tests
    print("\n--- Calendar & Events ---")
    await test_earnings_calendar()
    await test_stock_splits()
    
    # Economic data tests
    print("\n--- Economic Data ---")
    await test_treasury_rates()
    
    # Generic endpoint tests
    print("\n--- Generic Methods ---")
    await test_generic_fetch_endpoint()
    await test_invalid_params()
    
    # Close client
    await fmp_tools.close()
    
    # Print summary
    results.print_summary()


if __name__ == "__main__":
    asyncio.run(run_all_tests())

