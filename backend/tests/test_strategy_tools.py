"""
Test strategy creation and backtesting tools
"""
import pytest
import asyncio
import json
from datetime import date, datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock

from modules.agent.context import AgentContext
from modules.tools.definitions import (
    create_trading_strategy,
    backtest_strategy,
    list_user_strategies,
    compare_strategies
)
from models.strategy import TradingStrategy, StrategyBacktest
from models.sse import SSEEvent


@pytest.fixture
def mock_context():
    """Create a mock AgentContext"""
    context = Mock(spec=AgentContext)
    context.user_id = "test_user_123"
    context.chat_id = "test_chat_456"
    context.db = Mock()
    return context


@pytest.fixture
def sample_strategy():
    """Create a sample trading strategy"""
    from models.strategy import (
        TradingStrategy, DataRequirement, Condition, RiskParameters
    )
    
    return TradingStrategy(
        id="strategy_123",
        user_id="test_user_123",
        name="Insider + RSI Oversold",
        description="Buy when insiders are buying and RSI is oversold",
        natural_language_input="Buy when 3+ insiders buy over $500K in 30 days AND RSI < 30",
        timeframe="short_term",
        data_requirements=[
            DataRequirement(
                source="fmp",
                data_type="insider_trading",
                parameters={"days": 30}
            ),
            DataRequirement(
                source="calculated",
                data_type="rsi",
                parameters={"period": 14}
            )
        ],
        entry_conditions=[
            Condition(
                field="insider_buy_count",
                operator="gte",
                value=3,
                description="At least 3 insider buys"
            ),
            Condition(
                field="insider_buy_amount",
                operator="gt",
                value=500000,
                description="Total insider buying over $500K"
            ),
            Condition(
                field="rsi",
                operator="lt",
                value=30,
                description="RSI below 30 (oversold)"
            )
        ],
        entry_logic="AND",
        exit_conditions=[
            Condition(
                field="rsi",
                operator="gt",
                value=70,
                description="RSI above 70 (overbought)"
            )
        ],
        exit_logic="OR",
        risk_parameters=RiskParameters(
            stop_loss_pct=12.0,
            take_profit_pct=25.0,
            max_hold_days=60,
            position_size_pct=5.0,
            max_positions=5
        )
    )


class TestCreateTradingStrategy:
    """Test create_trading_strategy tool"""
    
    @pytest.mark.asyncio
    async def test_create_strategy_success(self, mock_context, sample_strategy):
        """Test successful strategy creation"""
        
        # Mock the parser service
        with patch('backend.services.strategy_parser.StrategyParserService') as MockParser, \
             patch('backend.crud.strategy.create_strategy') as mock_create:
            
            # Setup mocks
            mock_parser_instance = MockParser.return_value
            mock_parser_instance.parse_strategy = AsyncMock(return_value=sample_strategy)
            mock_parser_instance.validate_strategy = Mock(return_value={
                "valid": True,
                "issues": []
            })
            mock_create.return_value = Mock()
            
            # Call the tool
            results = []
            async for item in create_trading_strategy(
                context=mock_context,
                strategy_description="Buy when 3+ insiders buy over $500K in 30 days AND RSI < 30",
                strategy_name="Insider + RSI Oversold"
            ):
                results.append(item)
            
            # Verify we got events
            assert len(results) > 0
            
            # Check for status event
            status_events = [r for r in results if isinstance(r, SSEEvent) and r.event == "tool_status"]
            assert len(status_events) > 0
            
            # Check final result
            final_result = results[-1]
            assert isinstance(final_result, dict)
            assert final_result["success"] is True
            assert final_result["strategy_id"] == sample_strategy.id
            assert final_result["strategy_name"] == "Insider + RSI Oversold"
            assert "entry_conditions" in final_result
            assert "exit_conditions" in final_result
            assert "risk_parameters" in final_result
            
            # Verify parser was called correctly
            mock_parser_instance.parse_strategy.assert_called_once_with(
                user_id=mock_context.user_id,
                natural_language_input="Buy when 3+ insiders buy over $500K in 30 days AND RSI < 30"
            )
            
            # Verify validation was called
            mock_parser_instance.validate_strategy.assert_called_once()
            
            # Verify strategy was saved
            mock_create.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_create_strategy_validation_failed(self, mock_context):
        """Test strategy creation with validation failure"""
        
        with patch('backend.services.strategy_parser.StrategyParserService') as MockParser:
            mock_parser_instance = MockParser.return_value
            mock_parser_instance.parse_strategy = AsyncMock(return_value=Mock())
            mock_parser_instance.validate_strategy = Mock(return_value={
                "valid": False,
                "issues": ["Strategy must have at least one entry condition"]
            })
            
            results = []
            async for item in create_trading_strategy(
                context=mock_context,
                strategy_description="Invalid strategy",
                strategy_name="Bad Strategy"
            ):
                results.append(item)
            
            final_result = results[-1]
            assert final_result["success"] is False
            assert "issues" in final_result
    
    @pytest.mark.asyncio
    async def test_create_strategy_parser_error(self, mock_context):
        """Test strategy creation with parser error"""
        
        with patch('backend.services.strategy_parser.StrategyParserService') as MockParser:
            mock_parser_instance = MockParser.return_value
            mock_parser_instance.parse_strategy = AsyncMock(
                side_effect=ValueError("Could not parse strategy")
            )
            
            results = []
            async for item in create_trading_strategy(
                context=mock_context,
                strategy_description="Unclear strategy",
                strategy_name="Test"
            ):
                results.append(item)
            
            final_result = results[-1]
            assert final_result["success"] is False
            assert "error" in final_result


class TestBacktestStrategy:
    """Test backtest_strategy tool"""
    
    @pytest.mark.asyncio
    async def test_backtest_success(self, mock_context, sample_strategy):
        """Test successful backtest"""
        
        from models.strategy import BacktestTrade
        
        # Create mock backtest result
        mock_backtest = StrategyBacktest(
            strategy_id=sample_strategy.id,
            start_date=date(2022, 1, 1),
            end_date=date(2024, 1, 1),
            initial_capital=100000,
            total_trades=25,
            winning_trades=15,
            losing_trades=10,
            win_rate=60.0,
            total_return_pct=34.2,
            total_return_dollars=34200,
            final_equity=134200,
            avg_win_pct=12.5,
            avg_loss_pct=-5.2,
            profit_factor=2.1,
            max_drawdown_pct=8.4,
            sharpe_ratio=1.8,
            best_trade=BacktestTrade(
                ticker="NVDA",
                entry_date=date(2023, 6, 15),
                entry_price=420.0,
                exit_date=date(2023, 7, 20),
                exit_price=595.0,
                shares=10,
                pnl=1750,
                pnl_pct=41.7,
                days_held=35,
                exit_reason="take_profit"
            ),
            worst_trade=BacktestTrade(
                ticker="AMD",
                entry_date=date(2023, 3, 10),
                entry_price=95.0,
                exit_date=date(2023, 3, 25),
                exit_price=83.6,
                shares=15,
                pnl=-171,
                pnl_pct=-12.0,
                days_held=15,
                exit_reason="stop_loss"
            ),
            trades=[],
            equity_curve=[
                {"date": "2022-01-01", "equity": 100000, "cash": 100000, "positions_value": 0},
                {"date": "2024-01-01", "equity": 134200, "cash": 20000, "positions_value": 114200}
            ]
        )
        
        with patch('backend.crud.strategy.get_strategy') as mock_get, \
             patch('backend.crud.strategy.save_backtest') as mock_save, \
             patch('backend.services.strategy_backtest.BacktestEngine') as MockEngine, \
             patch('backend.modules.tools.fmp_client.FMPClient') as MockFMP:
            
            # Setup mocks
            mock_get.return_value = sample_strategy
            mock_engine_instance = MockEngine.return_value
            mock_engine_instance.run_backtest = AsyncMock(return_value=mock_backtest)
            
            # Call the tool
            results = []
            async for item in backtest_strategy(
                context=mock_context,
                strategy_id=sample_strategy.id,
                start_date="2022-01-01",
                end_date="2024-01-01"
            ):
                results.append(item)
            
            # Verify results
            assert len(results) > 0
            
            # Check for status event
            status_events = [r for r in results if isinstance(r, SSEEvent)]
            assert len(status_events) > 0
            
            # Check final result
            final_result = results[-1]
            assert final_result["success"] is True
            assert final_result["backtest_id"] == mock_backtest.backtest_id
            assert final_result["performance"]["total_trades"] == 25
            assert final_result["performance"]["win_rate"] == 60.0
            assert final_result["performance"]["total_return_pct"] == 34.2
            assert "best_trade" in final_result
            assert "worst_trade" in final_result
            assert final_result["best_trade"]["ticker"] == "NVDA"
            assert final_result["worst_trade"]["ticker"] == "AMD"
            
            # Verify backtest was run
            mock_engine_instance.run_backtest.assert_called_once()
            
            # Verify results were saved
            mock_save.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_backtest_strategy_not_found(self, mock_context):
        """Test backtest with non-existent strategy"""
        
        with patch('backend.crud.strategy.get_strategy') as mock_get:
            mock_get.return_value = None
            
            results = []
            async for item in backtest_strategy(
                context=mock_context,
                strategy_id="nonexistent",
                start_date="2022-01-01",
                end_date="2024-01-01"
            ):
                results.append(item)
            
            final_result = results[-1]
            assert final_result["success"] is False
            assert "not found" in final_result["error"]
    
    @pytest.mark.asyncio
    async def test_backtest_wrong_user(self, mock_context, sample_strategy):
        """Test backtest with wrong user"""
        
        # Change strategy user_id to different user
        wrong_user_strategy = sample_strategy.model_copy()
        wrong_user_strategy.user_id = "different_user"
        
        with patch('backend.crud.strategy.get_strategy') as mock_get:
            mock_get.return_value = wrong_user_strategy
            
            results = []
            async for item in backtest_strategy(
                context=mock_context,
                strategy_id=sample_strategy.id
            ):
                results.append(item)
            
            final_result = results[-1]
            assert final_result["success"] is False
            assert "permission" in final_result["error"]
    
    @pytest.mark.asyncio
    async def test_backtest_default_dates(self, mock_context, sample_strategy):
        """Test backtest with default dates (2 years)"""
        
        mock_backtest = StrategyBacktest(
            strategy_id=sample_strategy.id,
            start_date=date.today() - timedelta(days=730),
            end_date=date.today(),
            initial_capital=100000,
            total_trades=10,
            winning_trades=6,
            losing_trades=4,
            win_rate=60.0,
            total_return_pct=15.0,
            total_return_dollars=15000,
            final_equity=115000,
            avg_win_pct=8.0,
            avg_loss_pct=-4.0,
            profit_factor=2.0,
            max_drawdown_pct=5.0,
            sharpe_ratio=1.5,
            trades=[],
            equity_curve=[]
        )
        
        with patch('backend.crud.strategy.get_strategy') as mock_get, \
             patch('backend.crud.strategy.save_backtest') as mock_save, \
             patch('backend.services.strategy_backtest.BacktestEngine') as MockEngine, \
             patch('backend.modules.tools.fmp_client.FMPClient'):
            
            mock_get.return_value = sample_strategy
            mock_engine_instance = MockEngine.return_value
            mock_engine_instance.run_backtest = AsyncMock(return_value=mock_backtest)
            
            # Call without dates
            results = []
            async for item in backtest_strategy(
                context=mock_context,
                strategy_id=sample_strategy.id
            ):
                results.append(item)
            
            final_result = results[-1]
            assert final_result["success"] is True
            
            # Verify dates are approximately 2 years apart
            period = final_result["period"]
            start = date.fromisoformat(period["start_date"])
            end = date.fromisoformat(period["end_date"])
            days_diff = (end - start).days
            assert 700 <= days_diff <= 750  # ~2 years with some tolerance


class TestListUserStrategies:
    """Test list_user_strategies tool"""
    
    def test_list_strategies_success(self, mock_context, sample_strategy):
        """Test listing user strategies"""
        
        strategies = [sample_strategy]
        
        with patch('backend.crud.strategy.get_user_strategies') as mock_get:
            mock_get.return_value = strategies
            
            result = list_user_strategies(
                context=mock_context,
                active_only=True
            )
            
            assert result["success"] is True
            assert result["count"] == 1
            assert len(result["strategies"]) == 1
            assert result["strategies"][0]["strategy_id"] == sample_strategy.id
            assert result["strategies"][0]["name"] == sample_strategy.name
            
            # Verify CRUD was called correctly
            mock_get.assert_called_once_with(mock_context.db, mock_context.user_id, True)
    
    def test_list_strategies_empty(self, mock_context):
        """Test listing with no strategies"""
        
        with patch('backend.crud.strategy.get_user_strategies') as mock_get:
            mock_get.return_value = []
            
            result = list_user_strategies(
                context=mock_context,
                active_only=True
            )
            
            assert result["success"] is True
            assert result["count"] == 0
            assert len(result["strategies"]) == 0
            assert "haven't created" in result["message"]
    
    def test_list_strategies_include_inactive(self, mock_context, sample_strategy):
        """Test listing including inactive strategies"""
        
        active = sample_strategy
        inactive = sample_strategy.model_copy()
        inactive.id = "strategy_456"
        inactive.is_active = False
        
        with patch('backend.crud.strategy.get_user_strategies') as mock_get:
            mock_get.return_value = [active, inactive]
            
            result = list_user_strategies(
                context=mock_context,
                active_only=False
            )
            
            assert result["count"] == 2
            mock_get.assert_called_once_with(mock_context.db, mock_context.user_id, False)


class TestCompareStrategies:
    """Test compare_strategies tool"""
    
    def test_compare_strategies_success(self, mock_context):
        """Test comparing strategies"""
        
        from models.strategy import StrategyComparison
        
        comparisons = [
            StrategyComparison(
                strategy_id="strat_1",
                strategy_name="Insider + RSI",
                timeframe="short_term",
                signals_generated=15,
                win_rate=65.0,
                actual_return_pct=18.2,
                hypothetical_return_pct=22.5,
                last_signal=datetime(2024, 11, 30),
                is_active=True
            ),
            StrategyComparison(
                strategy_id="strat_2",
                strategy_name="MA Crossover",
                timeframe="medium_term",
                signals_generated=8,
                win_rate=75.0,
                actual_return_pct=14.5,
                hypothetical_return_pct=16.0,
                last_signal=datetime(2024, 11, 28),
                is_active=True
            )
        ]
        
        with patch('backend.crud.strategy.compare_user_strategies') as mock_compare:
            mock_compare.return_value = comparisons
            
            result = compare_strategies(context=mock_context)
            
            assert result["success"] is True
            assert result["count"] == 2
            assert len(result["strategies"]) == 2
            assert result["strategies"][0]["strategy_name"] == "Insider + RSI"
            assert result["strategies"][0]["win_rate"] == 65.0
            
            mock_compare.assert_called_once_with(mock_context.db, mock_context.user_id)
    
    def test_compare_strategies_empty(self, mock_context):
        """Test comparing with no strategies"""
        
        with patch('backend.crud.strategy.compare_user_strategies') as mock_compare:
            mock_compare.return_value = []
            
            result = compare_strategies(context=mock_context)
            
            assert result["success"] is True
            assert result["count"] == 0
            assert "No strategies" in result["message"]


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v", "--tb=short"])

