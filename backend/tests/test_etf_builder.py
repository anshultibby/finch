"""
Tests for Custom ETF Builder

Tests the build_custom_etf tool and integration with other tools.
"""
import pytest
from modules.agent.context import AgentContext
from modules.tools.implementations.etf_builder import BuildCustomETFParams, build_custom_etf_impl as build_custom_etf


class TestETFBuilder:
    """Test suite for ETF builder tool"""
    
    @pytest.fixture
    def agent_context(self):
        """Create a test agent context"""
        return AgentContext(
            agent_id="test_agent",
            user_id="test_user",
            chat_id="test_chat",
            data={}
        )
    
    @pytest.mark.asyncio
    async def test_market_cap_etf(self, agent_context):
        """Test building a market-cap weighted ETF"""
        params = BuildCustomETFParams(
            tickers=["AAPL", "MSFT", "GOOGL"],
            weighting_method="market_cap",
            name="Test Market Cap ETF"
        )
        
        result = None
        async for event in build_custom_etf(params=params, context=agent_context):
            if not hasattr(event, 'event'):
                result = event
        
        assert result is not None
        assert result["success"] is True
        assert result["weighting_method"] == "market_cap"
        
        # Check that weights sum to approximately 1.0
        total_weight = sum(c["weight"] for c in result["components"])
        assert abs(total_weight - 1.0) < 0.01
        
        # Check that weights are different (not equal)
        weights = [c["weight"] for c in result["components"]]
        assert len(set(weights)) > 1  # Not all weights are the same
    
    @pytest.mark.asyncio
    async def test_invalid_tickers(self, agent_context):
        """Test handling of invalid tickers"""
        params = BuildCustomETFParams(
            tickers=["AAPL", "INVALID_TICKER", "MSFT"],
            weighting_method="market_cap",
            name="Test ETF with Invalid"
        )
        
        result = None
        async for event in build_custom_etf(params=params, context=agent_context):
            if not hasattr(event, 'event'):
                result = event
        
        assert result is not None
        # Should succeed with valid tickers
        assert result["success"] is True
        # Should report failed tickers
        assert "failed_tickers" in result
        assert "INVALID_TICKER" in result.get("failed_tickers", [])
        # Should have 2 valid stocks
        assert result["total_stocks"] == 2
    
    @pytest.mark.asyncio
    async def test_single_stock(self, agent_context):
        """Test building ETF with single stock"""
        params = BuildCustomETFParams(
            tickers=["AAPL"],
            weighting_method="market_cap",
            name="Single Stock ETF"
        )
        
        result = None
        async for event in build_custom_etf(params=params, context=agent_context):
            if not hasattr(event, 'event'):
                result = event
        
        assert result is not None
        assert result["success"] is True
        assert result["total_stocks"] == 1
        # Single stock should have 100% weight
        assert abs(result["components"][0]["weight"] - 1.0) < 0.01
    
    @pytest.mark.asyncio
    async def test_component_structure(self, agent_context):
        """Test that component structure is correct"""
        params = BuildCustomETFParams(
            tickers=["AAPL", "MSFT"],
            weighting_method="market_cap",
            name="Test Structure"
        )
        
        result = None
        async for event in build_custom_etf(params=params, context=agent_context):
            if not hasattr(event, 'event'):
                result = event
        
        assert result is not None
        assert result["success"] is True
        
        # Check component structure
        for component in result["components"]:
            assert "ticker" in component
            assert "name" in component
            assert "weight" in component
            assert "price" in component
            assert "market_cap" in component
            
            # Validate types
            assert isinstance(component["ticker"], str)
            assert isinstance(component["name"], str)
            assert isinstance(component["weight"], float)
            assert isinstance(component["price"], (int, float))
            assert isinstance(component["market_cap"], (int, float))
            
            # Validate values
            assert component["weight"] > 0
            assert component["weight"] <= 1
            assert component["price"] > 0
            assert component["market_cap"] > 0
    
    @pytest.mark.asyncio
    async def test_summary_data(self, agent_context):
        """Test that summary data is correct"""
        params = BuildCustomETFParams(
            tickers=["AAPL", "MSFT", "GOOGL"],
            weighting_method="market_cap",
            name="Test Summary"
        )
        
        result = None
        async for event in build_custom_etf(params=params, context=agent_context):
            if not hasattr(event, 'event'):
                result = event
        
        assert result is not None
        assert result["success"] is True
        assert "summary" in result
        
        summary = result["summary"]
        assert "top_holding" in summary
        assert "top_weight" in summary
        assert "total_market_cap" in summary
        
        # Top holding should be one of the tickers
        assert summary["top_holding"] in ["AAPL", "MSFT", "GOOGL"]
        
        # Total market cap should be sum of components
        expected_total = sum(c["market_cap"] for c in result["components"])
        assert abs(summary["total_market_cap"] - expected_total) < 1000


class TestETFBuilderIntegration:
    """Integration tests with other tools"""
    
    def test_tool_registration(self):
        """Test that build_custom_etf is registered"""
        from modules.tools import tool_registry
        
        tool = tool_registry.get_tool("build_custom_etf")
        assert tool is not None
        assert tool.name == "build_custom_etf"
        assert tool.category == "analysis"
    
    def test_tool_in_agent_config(self):
        """Test that tool is in agent config"""
        from modules.agent.agent_config import MAIN_AGENT_TOOLS
        
        assert "build_custom_etf" in MAIN_AGENT_TOOLS
    
    def test_params_validation(self):
        """Test Pydantic validation"""
        # Valid params
        params = BuildCustomETFParams(
            tickers=["AAPL", "MSFT"],
            weighting_method="market_cap"
        )
        assert params.tickers == ["AAPL", "MSFT"]
        assert params.weighting_method == "market_cap"
        
        # Invalid weighting method should fail (equal_weight is no longer supported)
        with pytest.raises(Exception):  # Pydantic ValidationError
            BuildCustomETFParams(
                tickers=["AAPL"],
                weighting_method="equal_weight"
            )
        
        # Empty tickers list should fail
        with pytest.raises(Exception):  # Pydantic ValidationError
            BuildCustomETFParams(
                tickers=[],
                weighting_method="market_cap"
            )


# Run tests with: pytest tests/test_etf_builder.py -v
# Run with coverage: pytest tests/test_etf_builder.py --cov=modules.tools.implementations.etf_builder

