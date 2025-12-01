"""
Tests for Strategy Management System (V2)

Tests the complete flow:
- API routes for listing and executing strategies
- Strategy executor (screening and management)
- Data fetcher service
- JSON parsing from LLM responses
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, date
import json

from models.strategy_v2 import (
    TradingStrategyV2, StrategyRule, DataSource, CandidateSource, 
    RiskParameters, StrategyPosition, StrategyBudget, StrategyExecutionResult
)
from services.strategy_executor import StrategyExecutor
from services.data_fetcher import DataFetcherService


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def sample_strategy():
    """Create a sample strategy for testing"""
    return TradingStrategyV2(
        id="test-strategy-123",
        user_id="test-user-456",
        name="Test Momentum Strategy",
        description="A test strategy for momentum trading",
        candidate_source=CandidateSource(
            type="universe",
            universe="sp500"
        ),
        screening_rules=[
            StrategyRule(
                order=1,
                description="Check revenue growth",
                data_sources=[
                    DataSource(
                        type="fmp",
                        endpoint="financial-growth",
                        parameters={"period": "annual", "limit": 2}
                    )
                ],
                decision_logic="If revenue growth > 20%, BULLISH. Otherwise NEUTRAL.",
                weight=0.7
            ),
            StrategyRule(
                order=2,
                description="Check profitability",
                data_sources=[
                    DataSource(
                        type="fmp",
                        endpoint="key-metrics",
                        parameters={"period": "annual", "limit": 1}
                    )
                ],
                decision_logic="If ROE > 15%, BULLISH. Otherwise BEARISH.",
                weight=0.3
            )
        ],
        management_rules=[
            StrategyRule(
                order=1,
                description="Exit on profit/loss targets",
                data_sources=[],
                decision_logic="If P&L >= 25%, SELL (profit). If P&L <= -10%, SELL (loss). Otherwise HOLD.",
                weight=1.0
            )
        ],
        risk_parameters=RiskParameters(
            position_size_pct=20.0,
            max_positions=5,
            stop_loss_pct=10.0,
            take_profit_pct=25.0
        )
    )


@pytest.fixture
def sample_position():
    """Create a sample position for testing"""
    return StrategyPosition(
        position_id="pos-123",
        strategy_id="test-strategy-123",
        user_id="test-user-456",
        ticker="AAPL",
        shares=10.0,
        entry_price=150.0,
        entry_date=date(2024, 1, 1),
        entry_decision_id="decision-123",
        current_price=165.0,
        current_value=1650.0,
        pnl=150.0,
        pnl_pct=10.0,
        days_held=30,
        is_open=True,
        created_at=datetime(2024, 1, 1),
        updated_at=datetime.utcnow()
    )


@pytest.fixture
def sample_budget():
    """Create a sample budget for testing"""
    return StrategyBudget(
        strategy_id="test-strategy-123",
        user_id="test-user-456",
        total_budget=1000.0,
        cash_available=500.0,
        position_value=500.0,
        updated_at=datetime.utcnow()
    )


# ============================================================================
# JSON Extraction Tests
# ============================================================================

class TestJSONExtraction:
    """Test JSON extraction from various LLM response formats"""
    
    def test_direct_json(self):
        """Test parsing direct JSON response"""
        executor = StrategyExecutor()
        
        response = '{"action": "BUY", "signal": "BULLISH", "signal_value": 0.8, "reasoning": "Good metrics", "confidence": 85}'
        result = executor._extract_json(response)
        
        assert result["action"] == "BUY"
        assert result["signal"] == "BULLISH"
        assert result["signal_value"] == 0.8
        assert result["confidence"] == 85
    
    def test_json_in_markdown_json_block(self):
        """Test parsing JSON from ```json block"""
        executor = StrategyExecutor()
        
        response = '''```json
{
    "action": "SELL",
    "signal": "BEARISH",
    "signal_value": 0.2,
    "reasoning": "Poor fundamentals",
    "confidence": 75
}
```'''
        result = executor._extract_json(response)
        
        assert result["action"] == "SELL"
        assert result["signal"] == "BEARISH"
        assert result["confidence"] == 75
    
    def test_json_in_generic_code_block(self):
        """Test parsing JSON from generic ``` block"""
        executor = StrategyExecutor()
        
        response = '''Here's my analysis:
```
{
    "action": "HOLD",
    "signal": "NEUTRAL",
    "signal_value": 0.5,
    "reasoning": "Mixed signals",
    "confidence": 60
}
```
That's my recommendation.'''
        result = executor._extract_json(response)
        
        assert result["action"] == "HOLD"
        assert result["signal"] == "NEUTRAL"
        assert result["confidence"] == 60
    
    def test_json_embedded_in_text(self):
        """Test extracting JSON from text with surrounding content"""
        executor = StrategyExecutor()
        
        response = '''Based on my analysis, here is the decision:

{"action": "BUY", "signal": "BULLISH", "signal_value": 0.9, "reasoning": "Strong growth", "confidence": 90}

This is a high-confidence recommendation.'''
        result = executor._extract_json(response)
        
        assert result["action"] == "BUY"
        assert result["confidence"] == 90
    
    def test_empty_response_raises_error(self):
        """Test that empty response raises ValueError"""
        executor = StrategyExecutor()
        
        with pytest.raises(ValueError, match="Empty response"):
            executor._extract_json("")
    
    def test_invalid_json_raises_error(self):
        """Test that invalid JSON raises ValueError"""
        executor = StrategyExecutor()
        
        with pytest.raises(ValueError, match="Could not parse JSON"):
            executor._extract_json("This is just plain text with no JSON")


# ============================================================================
# Data Fetcher Tests
# ============================================================================

class TestDataFetcher:
    """Test data fetching from various sources"""
    
    @pytest.mark.asyncio
    async def test_fetch_fmp_success(self):
        """Test successful FMP data fetch"""
        fetcher = DataFetcherService()
        
        # Mock FMP client
        mock_data = {
            "success": True,
            "data": [
                {"date": "2024-01-01", "revenueGrowth": 0.25, "netIncomeGrowth": 0.30}
            ]
        }
        
        with patch.object(fetcher.fmp_client, 'get_fmp_data', new_callable=AsyncMock) as mock_fmp:
            mock_fmp.return_value = mock_data
            
            source = DataSource(
                type="fmp",
                endpoint="financial-growth",
                parameters={"period": "annual", "limit": 2}
            )
            
            result = await fetcher.fetch_data(source, "AAPL")
            
            assert result["success"] is True
            assert result["source"] == "fmp"
            assert result["endpoint"] == "financial-growth"
            assert "data" in result
            mock_fmp.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_fetch_fmp_error(self):
        """Test FMP data fetch error handling"""
        fetcher = DataFetcherService()
        
        mock_error = {
            "success": False,
            "error": "API rate limit exceeded"
        }
        
        with patch.object(fetcher.fmp_client, 'get_fmp_data', new_callable=AsyncMock) as mock_fmp:
            mock_fmp.return_value = mock_error
            
            source = DataSource(
                type="fmp",
                endpoint="financial-growth",
                parameters={}
            )
            
            result = await fetcher.fetch_data(source, "AAPL")
            
            assert result["success"] is False
            assert "error" in result
    
    @pytest.mark.asyncio
    async def test_fetch_exception_handling(self):
        """Test exception handling in fetch_data"""
        fetcher = DataFetcherService()
        
        # Mock FMP client to raise exception
        with patch.object(fetcher.fmp_client, 'get_fmp_data', new_callable=AsyncMock) as mock_fmp:
            mock_fmp.side_effect = Exception("Network error")
            
            source = DataSource(
                type="fmp",
                endpoint="quote",
                parameters={}
            )
            
            result = await fetcher.fetch_data(source, "AAPL")
            
            assert "error" in result


# ============================================================================
# Strategy Executor Tests
# ============================================================================

class TestStrategyExecutor:
    """Test strategy execution logic"""
    
    @pytest.mark.asyncio
    async def test_screen_candidate_buy_signal(self, sample_strategy):
        """Test screening a candidate that generates BUY signal"""
        executor = StrategyExecutor()
        
        # Mock data fetcher
        mock_growth_data = {
            "success": True,
            "data": [{"revenueGrowth": 0.25, "netIncomeGrowth": 0.30}]
        }
        mock_metrics_data = {
            "success": True,
            "data": [{"roe": 0.20}]
        }
        
        # Mock LLM responses
        mock_llm_responses = [
            # Rule 1 response (revenue growth)
            Mock(choices=[Mock(message=Mock(content='{"action": "CONTINUE", "signal": "BULLISH", "signal_value": 0.9, "reasoning": "Revenue growth 25% exceeds 20% threshold", "confidence": 90}'))]),
            # Rule 2 response (profitability)
            Mock(choices=[Mock(message=Mock(content='{"action": "CONTINUE", "signal": "BULLISH", "signal_value": 0.8, "reasoning": "ROE 20% exceeds 15% threshold", "confidence": 85}'))])
        ]
        
        with patch.object(executor.data_fetcher, 'fetch_data', new_callable=AsyncMock) as mock_fetch:
            with patch.object(executor.llm_handler, 'acompletion', new_callable=AsyncMock) as mock_llm:
                # Setup mocks
                mock_fetch.side_effect = [mock_growth_data, mock_metrics_data]
                mock_llm.side_effect = mock_llm_responses
                
                # Execute screening
                decision = await executor.screen_candidate(sample_strategy, "AAPL")
                
                assert decision.ticker == "AAPL"
                assert decision.action == "BUY"  # Both rules bullish -> BUY
                assert decision.confidence > 0
                assert len(decision.rule_results) == 2
    
    @pytest.mark.asyncio
    async def test_screen_candidate_skip_signal(self, sample_strategy):
        """Test screening a candidate that generates SKIP signal"""
        executor = StrategyExecutor()
        
        # Mock data that will result in SKIP
        mock_growth_data = {
            "success": True,
            "data": [{"revenueGrowth": 0.05}]  # Low growth
        }
        
        mock_llm_response = Mock(
            choices=[Mock(message=Mock(content='{"action": "SKIP", "signal": "BEARISH", "signal_value": 0.2, "reasoning": "Revenue growth only 5%, below 20% threshold", "confidence": 95}'))]
        )
        
        with patch.object(executor.data_fetcher, 'fetch_data', new_callable=AsyncMock) as mock_fetch:
            with patch.object(executor.llm_handler, 'acompletion', new_callable=AsyncMock) as mock_llm:
                mock_fetch.return_value = mock_growth_data
                mock_llm.return_value = mock_llm_response
                
                decision = await executor.screen_candidate(sample_strategy, "AAPL")
                
                assert decision.ticker == "AAPL"
                assert decision.action == "SKIP"
                assert len(decision.rule_results) == 1  # Stopped after first SKIP
    
    @pytest.mark.asyncio
    async def test_manage_position_sell_signal(self, sample_strategy, sample_position):
        """Test managing a position that should be sold"""
        executor = StrategyExecutor()
        
        # Position has 10% P&L, but let's say LLM recommends SELL
        mock_llm_response = Mock(
            choices=[Mock(message=Mock(content='{"action": "SELL", "signal": "BEARISH", "signal_value": 0.3, "reasoning": "P&L at 10%, but recent negative news suggests selling", "confidence": 80}'))]
        )
        
        with patch.object(executor.llm_handler, 'acompletion', new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = mock_llm_response
            
            decision = await executor.manage_position(sample_strategy, sample_position)
            
            assert decision.ticker == "AAPL"
            assert decision.action == "SELL"
            assert decision.position_data is not None
    
    @pytest.mark.asyncio
    async def test_manage_position_hold_signal(self, sample_strategy, sample_position):
        """Test managing a position that should be held"""
        executor = StrategyExecutor()
        
        mock_llm_response = Mock(
            choices=[Mock(message=Mock(content='{"action": "HOLD", "signal": "NEUTRAL", "signal_value": 0.6, "reasoning": "P&L at 10%, fundamentals still strong, hold position", "confidence": 75}'))]
        )
        
        with patch.object(executor.llm_handler, 'acompletion', new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = mock_llm_response
            
            decision = await executor.manage_position(sample_strategy, sample_position)
            
            assert decision.action == "HOLD"
    
    @pytest.mark.asyncio
    async def test_rule_error_handling(self, sample_strategy):
        """Test that rule errors are handled gracefully"""
        executor = StrategyExecutor()
        
        # Mock data fetch to return error (not raise exception)
        # The executor catches exceptions, so we should test the error response path
        mock_error_data = {"success": False, "error": "API error"}
        
        # Mock LLM to raise exception (which should be caught)
        with patch.object(executor.data_fetcher, 'fetch_data', new_callable=AsyncMock) as mock_fetch:
            with patch.object(executor.llm_handler, 'acompletion', new_callable=AsyncMock) as mock_llm:
                mock_fetch.return_value = mock_error_data
                mock_llm.side_effect = Exception("LLM error")
                
                decision = await executor.screen_candidate(sample_strategy, "AAPL")
                
                # Should still return a decision, even if all rules errored
                assert decision is not None
                assert decision.ticker == "AAPL"
                # All rules should have error results
                assert all(r.get("action") == "ERROR" for r in decision.rule_results)


# ============================================================================
# Decision Aggregation Tests
# ============================================================================

class TestDecisionAggregation:
    """Test decision aggregation logic"""
    
    def test_weighted_signal_calculation(self):
        """Test that weighted signals are calculated correctly"""
        executor = StrategyExecutor()
        
        rule_results = [
            {"signal_value": 0.9, "rule_weight": 0.7},  # Bullish with high weight
            {"signal_value": 0.3, "rule_weight": 0.3}   # Bearish with low weight
        ]
        
        # Calculate expected: (0.9 * 0.7 + 0.3 * 0.3) / (0.7 + 0.3) = 0.72
        decision = executor._aggregate_decision(
            strategy_id="test",
            ticker="AAPL",
            rule_results=rule_results,
            all_data={},
            position=None,
            mode="screening"
        )
        
        # With weighted signal 0.72, should be BUY (>= 0.7 threshold)
        assert decision.action == "BUY"
    
    def test_skip_takes_precedence(self):
        """Test that SKIP action takes precedence over other signals"""
        executor = StrategyExecutor()
        
        rule_results = [
            {"action": "CONTINUE", "signal_value": 0.9, "rule_weight": 0.5},
            {"action": "SKIP", "signal_value": 0.2, "rule_weight": 0.5}
        ]
        
        decision = executor._aggregate_decision(
            strategy_id="test",
            ticker="AAPL",
            rule_results=rule_results,
            all_data={},
            position=None,
            mode="screening"
        )
        
        assert decision.action == "SKIP"
    
    def test_management_thresholds(self):
        """Test management mode decision thresholds"""
        executor = StrategyExecutor()
        
        # Test BUY threshold (>= 0.75)
        decision_buy = executor._aggregate_decision(
            strategy_id="test",
            ticker="AAPL",
            rule_results=[{"signal_value": 0.8, "rule_weight": 1.0}],
            all_data={},
            position=None,
            mode="management"
        )
        assert decision_buy.action == "BUY"
        
        # Test HOLD threshold (0.4 to 0.74)
        decision_hold = executor._aggregate_decision(
            strategy_id="test",
            ticker="AAPL",
            rule_results=[{"signal_value": 0.6, "rule_weight": 1.0}],
            all_data={},
            position=None,
            mode="management"
        )
        assert decision_hold.action == "HOLD"
        
        # Test SELL threshold (< 0.4)
        decision_sell = executor._aggregate_decision(
            strategy_id="test",
            ticker="AAPL",
            rule_results=[{"signal_value": 0.3, "rule_weight": 1.0}],
            all_data={},
            position=None,
            mode="management"
        )
        assert decision_sell.action == "SELL"


# ============================================================================
# Integration Tests
# ============================================================================

class TestStrategyIntegration:
    """Integration tests for the complete strategy flow"""
    
    @pytest.mark.asyncio
    async def test_complete_screening_flow(self, sample_strategy):
        """Test the complete flow of screening a candidate"""
        executor = StrategyExecutor()
        
        # Mock successful data and LLM responses
        with patch.object(executor.data_fetcher, 'fetch_data', new_callable=AsyncMock) as mock_fetch:
            with patch.object(executor.llm_handler, 'acompletion', new_callable=AsyncMock) as mock_llm:
                # Setup data
                mock_fetch.side_effect = [
                    {"success": True, "data": [{"revenueGrowth": 0.25}]},
                    {"success": True, "data": [{"roe": 0.20}]}
                ]
                
                # Setup LLM responses
                mock_llm.side_effect = [
                    Mock(choices=[Mock(message=Mock(content='{"action": "CONTINUE", "signal": "BULLISH", "signal_value": 0.9, "reasoning": "Good growth", "confidence": 90}'))]),
                    Mock(choices=[Mock(message=Mock(content='{"action": "CONTINUE", "signal": "BULLISH", "signal_value": 0.8, "reasoning": "Strong ROE", "confidence": 85}'))])
                ]
                
                decision = await executor.screen_candidate(sample_strategy, "AAPL")
                
                # Verify decision structure
                assert decision.ticker == "AAPL"
                assert decision.strategy_id == sample_strategy.id
                assert decision.action in ["BUY", "SKIP"]
                assert 0 <= decision.confidence <= 100
                assert decision.reasoning
                assert len(decision.rule_results) > 0
                assert decision.data_snapshot
                assert decision.timestamp


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

