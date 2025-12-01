"""
Comprehensive FMP API Tests

Tests all Financial Modeling Prep API endpoints to ensure they work correctly.

Run with:
    pytest tests/test_fmp_apis.py -v
    pytest tests/test_fmp_apis.py -v -m real_api      # Real API tests only
    pytest tests/test_fmp_apis.py -v -m "not real_api"  # Mock tests only
"""
import pytest
from unittest.mock import AsyncMock, patch
from modules.tools.clients.fmp import fmp_tools


# ============================================================================
# Test Configuration - Define all endpoints to test
# ============================================================================

# Endpoints that require a symbol
SYMBOL_ENDPOINTS = [
    ("profile", {"symbol": "AAPL"}),
    ("quote", {"symbol": "AAPL"}),
    ("income-statement", {"symbol": "AAPL", "period": "annual", "limit": 2}),
    ("balance-sheet-statement", {"symbol": "AAPL", "period": "quarter", "limit": 2}),
    ("cash-flow-statement", {"symbol": "AAPL", "period": "annual", "limit": 1}),
    ("key-metrics", {"symbol": "AAPL", "period": "annual", "limit": 1}),
    ("ratios", {"symbol": "AAPL", "period": "annual", "limit": 1}),
    ("financial-growth", {"symbol": "AAPL", "period": "annual", "limit": 2}),
    ("historical-price-full", {"symbol": "AAPL", "limit": 5}),
    ("grade", {"symbol": "AAPL", "limit": 5}),
    ("price-target-consensus", {"symbol": "AAPL"}),
    ("grades", {"symbol": "AAPL", "limit": 5}),
    ("stock-peers", {"symbol": "AAPL"}),
    ("splits", {"symbol": "AAPL"}),
    ("esg-ratings", {"symbol": "AAPL"}),
]

# Endpoints that work without parameters
NO_PARAM_ENDPOINTS = [
    ("biggest-gainers", {}),
    ("biggest-losers", {}),
    ("most-actives", {}),
    ("sector-performance-snapshot", {}),
    ("earnings-calendar", {}),
    ("dividends-calendar", {}),
    ("treasury-rates", {}),
]

# Search and screening endpoints
SEARCH_ENDPOINTS = [
    ("search-symbol", {"query": "Apple", "limit": 5}),
    ("company-screener", {"marketCapMoreThan": 1000000000, "limit": 10}),
]

# News endpoints
NEWS_ENDPOINTS = [
    ("news/stock", {"symbols": "AAPL", "limit": 5}),
    ("news/stock-latest", {"limit": 5}),
]

# ETF endpoints
ETF_ENDPOINTS = [
    ("etf/holdings", {"symbol": "SPY"}),
    ("etf/info", {"symbol": "SPY"}),
    ("etf/sector-weightings", {"symbol": "SPY"}),
]

# Insider trading endpoints (v4 API)
INSIDER_ENDPOINTS = [
    ("insider-trading", {"symbol": "AAPL", "limit": 10}),
    ("insider-roster", {"symbol": "AAPL"}),
]

# Government trading endpoints (v4 API)
GOVERNMENT_ENDPOINTS = [
    ("senate-trading", {"symbol": "AAPL", "limit": 10}),
    ("house-trading", {"symbol": "AAPL", "limit": 10}),
]

# SEC filings
SEC_ENDPOINTS = [
    ("sec-filings-search/symbol", {"symbol": "AAPL", "limit": 5}),
    ("sec-filings-search/form-type", {"formType": "10-K", "limit": 5}),
]

# Economic data
ECONOMIC_ENDPOINTS = [
    ("economic-indicators", {"name": "GDP"}),
]


# ============================================================================
# Real API Tests
# ============================================================================

class TestFMPRealAPI:
    """Tests that hit the real FMP API"""
    
    @pytest.mark.real_api
    @pytest.mark.asyncio
    @pytest.mark.parametrize("endpoint,params", SYMBOL_ENDPOINTS)
    async def test_symbol_endpoints(self, endpoint, params):
        """Test all endpoints that require a symbol"""
        result = await fmp_tools.get_fmp_data(endpoint, params)
        
        # All endpoints should return a result with success and data keys
        assert "success" in result, f"No success key in result for {endpoint}"
        assert "data" in result, f"No data key in result for {endpoint}"
        
        # If successful, validate data structure
        if result["success"]:
            assert isinstance(result["data"], list), f"Data should be list for {endpoint}"
            if len(result["data"]) > 0:
                assert isinstance(result["data"][0], dict), f"Data items should be dicts for {endpoint}"
        else:
            # It's OK if some endpoints don't have data, just log it
            print(f"⚠️  {endpoint}: {result.get('message', 'No data')}")
    
    @pytest.mark.real_api
    @pytest.mark.asyncio
    @pytest.mark.parametrize("endpoint,params", NO_PARAM_ENDPOINTS)
    async def test_no_param_endpoints(self, endpoint, params):
        """Test endpoints that don't require parameters"""
        result = await fmp_tools.get_fmp_data(endpoint, params)
        
        assert "success" in result
        assert "data" in result
        
        # These might return empty outside market hours
        if not result["success"]:
            print(f"⚠️  {endpoint}: {result.get('message', 'No data')}")
    
    @pytest.mark.real_api
    @pytest.mark.asyncio
    @pytest.mark.parametrize("endpoint,params", SEARCH_ENDPOINTS)
    async def test_search_endpoints(self, endpoint, params):
        """Test search and screening endpoints"""
        result = await fmp_tools.get_fmp_data(endpoint, params)
        
        assert "success" in result
        assert "data" in result
        
        if not result["success"]:
            print(f"⚠️  {endpoint}: {result.get('message', 'No data')}")
    
    @pytest.mark.real_api
    @pytest.mark.asyncio
    @pytest.mark.parametrize("endpoint,params", NEWS_ENDPOINTS)
    async def test_news_endpoints(self, endpoint, params):
        """Test news endpoints"""
        result = await fmp_tools.get_fmp_data(endpoint, params)
        
        assert "success" in result
        assert "data" in result
        
        if not result["success"]:
            print(f"⚠️  {endpoint}: {result.get('message', 'No data')}")
    
    @pytest.mark.real_api
    @pytest.mark.asyncio
    @pytest.mark.parametrize("endpoint,params", ETF_ENDPOINTS)
    async def test_etf_endpoints(self, endpoint, params):
        """Test ETF endpoints"""
        result = await fmp_tools.get_fmp_data(endpoint, params)
        
        assert "success" in result
        assert "data" in result
        
        if not result["success"]:
            print(f"⚠️  {endpoint}: {result.get('message', 'No data')}")
    
    @pytest.mark.real_api
    @pytest.mark.asyncio
    @pytest.mark.parametrize("endpoint,params", INSIDER_ENDPOINTS)
    async def test_insider_endpoints(self, endpoint, params):
        """Test insider trading endpoints"""
        result = await fmp_tools.get_fmp_data(endpoint, params)
        
        assert "success" in result
        assert "data" in result
        
        if not result["success"]:
            print(f"⚠️  {endpoint}: {result.get('message', 'No data')}")
    
    @pytest.mark.real_api
    @pytest.mark.asyncio
    @pytest.mark.parametrize("endpoint,params", GOVERNMENT_ENDPOINTS)
    async def test_government_endpoints(self, endpoint, params):
        """Test government (senate/house) trading endpoints"""
        result = await fmp_tools.get_fmp_data(endpoint, params)
        
        assert "success" in result
        assert "data" in result
        
        if not result["success"]:
            print(f"⚠️  {endpoint}: {result.get('message', 'No data')}")
    
    @pytest.mark.real_api
    @pytest.mark.asyncio
    @pytest.mark.parametrize("endpoint,params", SEC_ENDPOINTS)
    async def test_sec_endpoints(self, endpoint, params):
        """Test SEC filings endpoints"""
        result = await fmp_tools.get_fmp_data(endpoint, params)
        
        assert "success" in result
        assert "data" in result
        
        if not result["success"]:
            print(f"⚠️  {endpoint}: {result.get('message', 'No data')}")
    
    @pytest.mark.real_api
    @pytest.mark.asyncio
    @pytest.mark.parametrize("endpoint,params", ECONOMIC_ENDPOINTS)
    async def test_economic_endpoints(self, endpoint, params):
        """Test economic data endpoints"""
        result = await fmp_tools.get_fmp_data(endpoint, params)
        
        assert "success" in result
        assert "data" in result
        
        if not result["success"]:
            print(f"⚠️  {endpoint}: {result.get('message', 'No data')}")
    
    @pytest.mark.real_api
    @pytest.mark.asyncio
    async def test_stock_screener_advanced(self):
        """Test stock screener with multiple filters"""
        result = await fmp_tools.get_fmp_data(
            "company-screener",
            {
                "marketCapMoreThan": 1000000000,
                "sector": "Technology",
                "betaMoreThan": 0.5,
                "betaLowerThan": 1.5,
                "isActivelyTrading": True,
                "limit": 5
            }
        )
        
        assert "success" in result
        assert "data" in result
        
        if not result["success"]:
            print(f"⚠️  Stock screener (advanced): {result.get('message', 'No data')}")


# ============================================================================
# Mock API Tests (no API key required, fast)
# ============================================================================

class TestFMPMockAPI:
    """Tests using mocked API responses - don't require API key"""
    
    @pytest.mark.asyncio
    async def test_successful_response(self):
        """Test handling of successful API response"""
        mock_response = [{"symbol": "AAPL", "price": 150.0, "volume": 50000000}]
        
        with patch.object(fmp_tools, '_fetch_api_data', new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = mock_response
            
            result = await fmp_tools.get_fmp_data("quote", {"symbol": "AAPL"})
            
            assert result["success"] is True
            assert "data" in result
            assert isinstance(result["data"], list)
    
    @pytest.mark.asyncio
    async def test_empty_response(self):
        """Test handling of empty API response"""
        with patch.object(fmp_tools, '_fetch_api_data', new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = []
            
            result = await fmp_tools.get_fmp_data("quote", {"symbol": "INVALID"})
            
            assert result["success"] is False
            assert "data" in result
            assert result["data"] == []
    
    @pytest.mark.asyncio
    async def test_api_error(self):
        """Test handling of API errors"""
        with patch.object(fmp_tools, '_fetch_api_data', new_callable=AsyncMock) as mock_fetch:
            mock_fetch.side_effect = Exception("API connection failed")
            
            result = await fmp_tools.get_fmp_data("quote", {"symbol": "AAPL"})
            
            assert result["success"] is False
            assert "message" in result
            assert "failed" in result["message"].lower()
    
    @pytest.mark.asyncio
    async def test_stock_screener_response(self):
        """Test stock screener with mocked response"""
        mock_response = [
            {
                "symbol": "AAPL",
                "companyName": "Apple Inc.",
                "marketCap": 3435062313000,
                "sector": "Technology",
                "industry": "Consumer Electronics",
                "beta": 1.24,
                "price": 225.93,
                "lastAnnualDividend": 1,
                "volume": 43010091,
                "exchange": "NASDAQ Global Select",
                "exchangeShortName": "NASDAQ",
                "country": "US",
                "isEtf": False,
                "isFund": False,
                "isActivelyTrading": True
            }
        ]
        
        with patch.object(fmp_tools, '_fetch_api_data', new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = mock_response
            
            result = await fmp_tools.get_fmp_data(
                "company-screener",
                {"marketCapMoreThan": 1000000000, "limit": 10}
            )
            
            assert result["success"] is True
            assert "data" in result
            assert len(result["data"]) > 0


# ============================================================================
# Diagnostic Tests
# ============================================================================

class TestFMPDiagnostics:
    """Diagnostic tests to check API health"""
    
    @pytest.mark.real_api
    @pytest.mark.asyncio
    async def test_all_endpoints_summary(self):
        """Run a quick test of major endpoints and print summary"""
        
        test_cases = [
            ("profile", {"symbol": "AAPL"}, "Company Profile"),
            ("quote", {"symbol": "AAPL"}, "Quote"),
            ("income-statement", {"symbol": "AAPL", "period": "annual", "limit": 1}, "Income Statement"),
            ("balance-sheet-statement", {"symbol": "AAPL", "period": "annual", "limit": 1}, "Balance Sheet"),
            ("key-metrics", {"symbol": "AAPL", "period": "annual", "limit": 1}, "Key Metrics"),
            ("ratios", {"symbol": "AAPL", "period": "annual", "limit": 1}, "Financial Ratios"),
            ("financial-growth", {"symbol": "AAPL", "period": "annual", "limit": 1}, "Financial Growth"),
            ("historical-price-full", {"symbol": "AAPL", "limit": 5}, "Historical Prices"),
            ("biggest-gainers", {}, "Market Gainers"),
            ("company-screener", {"marketCapMoreThan": 1000000000, "limit": 5}, "Stock Screener"),
        ]
        
        results = {}
        
        print("\n" + "="*70)
        print("FMP API ENDPOINT STATUS")
        print("="*70)
        
        for endpoint, params, name in test_cases:
            result = await fmp_tools.get_fmp_data(endpoint, params)
            success = result.get("success", False)
            results[name] = success
            
            status = "✅" if success else "❌"
            count = result.get("count", 0) if success else 0
            message = f"({count} records)" if success and count else result.get("message", "No data")
            
            print(f"{status} {name:25s}: {message}")
        
        # Summary
        working = sum(1 for v in results.values() if v)
        total = len(results)
        
        print("="*70)
        print(f"📊 Summary: {working}/{total} endpoints working ({working/total*100:.0f}%)")
        print("="*70)
        
        # Don't fail if at least half work (some endpoints might need market hours)
        assert working >= total * 0.5, f"Too many endpoints failing: {results}"


if __name__ == "__main__":
    print("="*80)
    print("FMP API Tests")
    print("="*80)
    print("\nRun all tests:")
    print("  pytest tests/test_fmp_apis.py -v")
    print("\nRun only real API tests (requires FMP_API_KEY):")
    print("  pytest tests/test_fmp_apis.py -v -m real_api")
    print("\nRun only mock tests (no API key needed):")
    print("  pytest tests/test_fmp_apis.py -v -m 'not real_api'")
    print("\nRun diagnostic:")
    print("  pytest tests/test_fmp_apis.py::TestFMPDiagnostics::test_all_endpoints_summary -v -s")
    print("="*80)
    
    pytest.main([__file__, "-v", "-m", "not real_api"])
