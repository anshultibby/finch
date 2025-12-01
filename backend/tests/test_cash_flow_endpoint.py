"""Test cash flow endpoint mapping fix"""
import pytest
import asyncio
from services.data_fetcher import DataFetcherService
from models.strategy_v2 import DataSource


@pytest.mark.asyncio
async def test_cash_flow_endpoint():
    """Test that cash-flow-statement endpoint is properly mapped"""
    fetcher = DataFetcherService()
    
    # Test with full endpoint name (the one that was failing)
    source = DataSource(
        type="fmp",
        endpoint="cash-flow-statement",
        parameters={"period": "annual", "limit": 2}
    )
    
    result = await fetcher.fetch_data(source, "AAPL")
    
    # Should succeed (not get "endpoint not implemented" error)
    assert "error" not in result or result["error"] != "Endpoint not implemented: cash-flow-statement"
    print(f"✅ cash-flow-statement endpoint: {result.get('success', False)}")
    
    # Test with short name (should still work)
    source2 = DataSource(
        type="fmp",
        endpoint="cash-flow",
        parameters={"period": "annual", "limit": 2}
    )
    
    result2 = await fetcher.fetch_data(source2, "AAPL")
    
    # Should succeed
    assert "error" not in result2 or result2["error"] != "Endpoint not implemented: cash-flow"
    print(f"✅ cash-flow endpoint: {result2.get('success', False)}")


@pytest.mark.asyncio
async def test_balance_sheet_endpoint():
    """Test that balance-sheet-statement endpoint is also properly mapped"""
    fetcher = DataFetcherService()
    
    # Test with full endpoint name
    source = DataSource(
        type="fmp",
        endpoint="balance-sheet-statement",
        parameters={"period": "annual", "limit": 2}
    )
    
    result = await fetcher.fetch_data(source, "AAPL")
    
    # Should succeed
    assert "error" not in result or result["error"] != "Endpoint not implemented: balance-sheet-statement"
    print(f"✅ balance-sheet-statement endpoint: {result.get('success', False)}")
    
    # Test with short name
    source2 = DataSource(
        type="fmp",
        endpoint="balance-sheet",
        parameters={"period": "annual", "limit": 2}
    )
    
    result2 = await fetcher.fetch_data(source2, "AAPL")
    
    # Should succeed
    assert "error" not in result2 or result2["error"] != "Endpoint not implemented: balance-sheet"
    print(f"✅ balance-sheet endpoint: {result2.get('success', False)}")


if __name__ == "__main__":
    # Run the tests
    asyncio.run(test_cash_flow_endpoint())
    asyncio.run(test_balance_sheet_endpoint())
    print("\n✅ All endpoint mapping tests passed!")

