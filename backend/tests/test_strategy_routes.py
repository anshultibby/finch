"""
Tests for Strategy API Routes

Tests the FastAPI endpoints for strategy management
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, date

from main import app
from models.strategy_v2 import (
    TradingStrategyV2, StrategyRule, DataSource, CandidateSource,
    RiskParameters, StrategyPosition, StrategyBudget, StrategyExecutionResult,
    StrategyDecision
)


client = TestClient(app)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def mock_strategy():
    """Mock strategy for testing"""
    return TradingStrategyV2(
        id="strategy-123",
        user_id="user-456",
        name="Test Strategy",
        description="A test strategy",
        candidate_source=CandidateSource(type="universe", universe="sp500"),
        screening_rules=[
            StrategyRule(
                order=1,
                description="Test rule",
                data_sources=[],
                decision_logic="Test logic",
                weight=1.0
            )
        ],
        management_rules=[],
        risk_parameters=RiskParameters(),
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
        is_active=True
    )


@pytest.fixture
def mock_budget():
    """Mock budget for testing"""
    return StrategyBudget(
        strategy_id="strategy-123",
        user_id="user-456",
        total_budget=1000.0,
        cash_available=500.0,
        position_value=500.0,
        updated_at=datetime.utcnow()
    )


@pytest.fixture
def mock_execution_result(mock_strategy, mock_budget):
    """Mock execution result"""
    return StrategyExecutionResult(
        strategy_id=mock_strategy.id,
        strategy_name=mock_strategy.name,
        timestamp=datetime.utcnow(),
        screening_decisions=[
            StrategyDecision(
                strategy_id=mock_strategy.id,
                ticker="AAPL",
                action="BUY",
                confidence=85.0,
                reasoning="Strong fundamentals",
                rule_results=[],
                data_snapshot={},
                current_price=150.0
            )
        ],
        management_decisions=[],
        budget=mock_budget,
        positions=[]
    )


# ============================================================================
# API Route Tests
# ============================================================================

class TestGetStrategies:
    """Test GET /api/strategies/{user_id}"""
    
    def test_get_user_strategies_success(self, mock_strategy):
        """Test successfully getting user strategies"""
        with patch('routes.strategies.get_user_strategies') as mock_get:
            mock_get.return_value = [mock_strategy]
            
            response = client.get("/api/strategies/user-456?active_only=true")
            
            assert response.status_code == 200
            data = response.json()
            assert len(data) == 1
            assert data[0]["id"] == "strategy-123"
            assert data[0]["name"] == "Test Strategy"
            assert data[0]["user_id"] == "user-456"
    
    def test_get_user_strategies_empty(self):
        """Test getting strategies when user has none"""
        with patch('routes.strategies.get_user_strategies') as mock_get:
            mock_get.return_value = []
            
            response = client.get("/api/strategies/user-456")
            
            assert response.status_code == 200
            assert response.json() == []
    
    def test_get_user_strategies_error(self):
        """Test error handling when fetching strategies"""
        with patch('routes.strategies.get_user_strategies') as mock_get:
            mock_get.side_effect = Exception("Database error")
            
            response = client.get("/api/strategies/user-456")
            
            assert response.status_code == 500


class TestGetStrategyById:
    """Test GET /api/strategies/{user_id}/{strategy_id}"""
    
    def test_get_strategy_success(self, mock_strategy):
        """Test successfully getting a specific strategy"""
        with patch('routes.strategies.get_strategy') as mock_get:
            mock_get.return_value = mock_strategy
            
            response = client.get("/api/strategies/user-456/strategy-123")
            
            assert response.status_code == 200
            data = response.json()
            assert data["id"] == "strategy-123"
            assert data["name"] == "Test Strategy"
    
    def test_get_strategy_not_found(self):
        """Test getting a strategy that doesn't exist"""
        with patch('routes.strategies.get_strategy') as mock_get:
            mock_get.return_value = None
            
            response = client.get("/api/strategies/user-456/nonexistent")
            
            assert response.status_code == 404
            assert "not found" in response.json()["detail"].lower()
    
    def test_get_strategy_wrong_user(self, mock_strategy):
        """Test getting a strategy that belongs to another user"""
        with patch('routes.strategies.get_strategy') as mock_get:
            mock_get.return_value = mock_strategy
            
            # Request with wrong user_id
            response = client.get("/api/strategies/different-user/strategy-123")
            
            assert response.status_code == 403
            assert "denied" in response.json()["detail"].lower()


class TestExecuteStrategy:
    """Test POST /api/strategies/{user_id}/{strategy_id}/execute"""
    
    def test_execute_strategy_success(self, mock_strategy, mock_budget, mock_execution_result):
        """Test successfully executing a strategy"""
        with patch('routes.strategies.get_strategy') as mock_get_strategy:
            with patch('routes.strategies.get_budget') as mock_get_budget:
                with patch('routes.strategies.get_positions') as mock_get_positions:
                    with patch('routes.strategies.strategy_executor.screen_candidate', new_callable=AsyncMock) as mock_screen:
                        # Setup mocks
                        mock_get_strategy.return_value = mock_strategy
                        mock_get_budget.return_value = mock_budget
                        mock_get_positions.return_value = []
                        
                        mock_screen.return_value = StrategyDecision(
                            strategy_id=mock_strategy.id,
                            ticker="AAPL",
                            action="BUY",
                            confidence=85.0,
                            reasoning="Strong fundamentals",
                            rule_results=[],
                            data_snapshot={},
                            current_price=150.0
                        )
                        
                        response = client.post("/api/strategies/user-456/strategy-123/execute")
                        
                        assert response.status_code == 200
                        data = response.json()
                        assert data["strategy_id"] == "strategy-123"
                        assert "screening_decisions" in data
                        assert "budget" in data
    
    def test_execute_strategy_not_found(self):
        """Test executing a non-existent strategy"""
        with patch('routes.strategies.get_strategy') as mock_get:
            mock_get.return_value = None
            
            response = client.post("/api/strategies/user-456/nonexistent/execute")
            
            assert response.status_code == 404
    
    def test_execute_inactive_strategy(self, mock_strategy):
        """Test executing an inactive strategy"""
        inactive_strategy = mock_strategy.model_copy()
        inactive_strategy.is_active = False
        
        with patch('routes.strategies.get_strategy') as mock_get:
            mock_get.return_value = inactive_strategy
            
            response = client.post("/api/strategies/user-456/strategy-123/execute")
            
            assert response.status_code == 400
            assert "not active" in response.json()["detail"].lower()
    
    def test_execute_strategy_no_budget(self, mock_strategy):
        """Test executing a strategy without initialized budget"""
        with patch('routes.strategies.get_strategy') as mock_get_strategy:
            with patch('routes.strategies.get_budget') as mock_get_budget:
                mock_get_strategy.return_value = mock_strategy
                mock_get_budget.return_value = None  # No budget
                
                response = client.post("/api/strategies/user-456/strategy-123/execute")
                
                assert response.status_code == 400
                assert "budget" in response.json()["detail"].lower()
    
    def test_execute_strategy_wrong_user(self, mock_strategy):
        """Test executing a strategy that belongs to another user"""
        with patch('routes.strategies.get_strategy') as mock_get:
            mock_get.return_value = mock_strategy
            
            response = client.post("/api/strategies/different-user/strategy-123/execute")
            
            assert response.status_code == 403


# ============================================================================
# Response Model Tests
# ============================================================================

class TestResponseModels:
    """Test that API responses match expected models"""
    
    def test_strategy_response_structure(self, mock_strategy):
        """Test that strategy response has all required fields"""
        with patch('routes.strategies.get_user_strategies') as mock_get:
            mock_get.return_value = [mock_strategy]
            
            response = client.get("/api/strategies/user-456")
            
            assert response.status_code == 200
            data = response.json()[0]
            
            # Check all required fields
            required_fields = [
                "id", "user_id", "name", "description",
                "candidate_source", "screening_rules", "management_rules",
                "risk_parameters", "created_at", "updated_at", "is_active"
            ]
            for field in required_fields:
                assert field in data
    
    def test_execution_result_structure(self, mock_strategy, mock_budget):
        """Test that execution result has all required fields"""
        with patch('routes.strategies.get_strategy') as mock_get_strategy:
            with patch('routes.strategies.get_budget') as mock_get_budget:
                with patch('routes.strategies.get_positions') as mock_get_positions:
                    with patch('routes.strategies.strategy_executor.screen_candidate', new_callable=AsyncMock) as mock_screen:
                        mock_get_strategy.return_value = mock_strategy
                        mock_get_budget.return_value = mock_budget
                        mock_get_positions.return_value = []
                        
                        mock_screen.return_value = StrategyDecision(
                            strategy_id=mock_strategy.id,
                            ticker="AAPL",
                            action="BUY",
                            confidence=85.0,
                            reasoning="Test",
                            rule_results=[],
                            data_snapshot={},
                            current_price=150.0
                        )
                        
                        response = client.post("/api/strategies/user-456/strategy-123/execute")
                        
                        assert response.status_code == 200
                        data = response.json()
                        
                        # Check all required fields
                        required_fields = [
                            "strategy_id", "strategy_name", "timestamp",
                            "screening_decisions", "management_decisions",
                            "budget", "positions"
                        ]
                        for field in required_fields:
                            assert field in data


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

