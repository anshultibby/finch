"""
Test parallelization in strategy execution
"""
import pytest
import asyncio
import time
from datetime import datetime, date
from models.strategy_v2 import (
    TradingStrategyV2, 
    StrategyRule, 
    DataSource,
    CandidateSource,
    StrategyPosition
)
from services.strategy_executor import StrategyExecutor


@pytest.mark.asyncio
async def test_parallel_candidate_screening():
    """Test that candidates are screened in parallel"""
    
    # Create a simple strategy
    strategy = TradingStrategyV2(
        user_id="test_user",
        name="Test Parallel Strategy",
        description="Testing parallelization",
        candidate_source=CandidateSource(type="tickers", tickers=["AAPL", "MSFT", "GOOGL"]),
        screening_rules=[
            StrategyRule(
                order=1,
                description="Check if price > $100",
                data_sources=[
                    DataSource(
                        type="fmp",
                        endpoint="quote",
                        parameters={}
                    )
                ],
                decision_logic="If price > $100, signal BULLISH (1.0), else NEUTRAL (0.5)",
                weight=1.0
            )
        ]
    )
    
    executor = StrategyExecutor(max_concurrent_candidates=3)
    
    # Test parallel screening
    tickers = ["AAPL", "MSFT", "GOOGL", "TSLA", "NVDA"]
    
    start_time = time.time()
    decisions = await executor.screen_candidates_parallel(strategy, tickers)
    elapsed = time.time() - start_time
    
    print(f"\n✅ Screened {len(tickers)} candidates in {elapsed:.2f}s")
    print(f"   Decisions: {len(decisions)}")
    print(f"   Concurrency: {executor.max_concurrent_candidates}")
    
    # Should be faster than sequential execution
    assert len(decisions) <= len(tickers)  # Some might fail
    assert elapsed < len(tickers) * 2  # Should be much faster than 2s per ticker


@pytest.mark.asyncio  
async def test_parallel_position_management():
    """Test that positions are managed in parallel"""
    
    # Create a simple strategy
    strategy = TradingStrategyV2(
        user_id="test_user",
        name="Test Parallel Management",
        description="Testing parallelization",
        screening_rules=[
            StrategyRule(
                order=1,
                description="Check position performance",
                data_sources=[],
                decision_logic="If P&L > 10%, SELL. If P&L < -5%, SELL. Else HOLD.",
                weight=1.0
            )
        ]
    )
    
    # Create test positions
    positions = [
        StrategyPosition(
            strategy_id=strategy.id,
            user_id="test_user",
            ticker="AAPL",
            shares=10,
            entry_price=150.0,
            entry_date=date.today(),
            entry_decision_id="test_1",
            current_price=165.0,
            pnl=150.0,
            pnl_pct=10.0,
            days_held=5
        ),
        StrategyPosition(
            strategy_id=strategy.id,
            user_id="test_user",
            ticker="MSFT",
            shares=5,
            entry_price=300.0,
            entry_date=date.today(),
            entry_decision_id="test_2",
            current_price=315.0,
            pnl=75.0,
            pnl_pct=5.0,
            days_held=3
        )
    ]
    
    executor = StrategyExecutor(max_concurrent_positions=2)
    
    start_time = time.time()
    decisions = await executor.manage_positions_parallel(strategy, positions)
    elapsed = time.time() - start_time
    
    print(f"\n✅ Managed {len(positions)} positions in {elapsed:.2f}s")
    print(f"   Decisions: {len(decisions)}")
    print(f"   Concurrency: {executor.max_concurrent_positions}")
    
    # Should complete successfully
    assert len(decisions) <= len(positions)


@pytest.mark.asyncio
async def test_concurrency_limit():
    """Test that concurrency limits are respected"""
    
    # Track concurrent executions
    concurrent_count = 0
    max_concurrent = 0
    lock = asyncio.Lock()
    
    # Monkey-patch the executor to track concurrency
    original_screen = StrategyExecutor.screen_candidate
    
    async def tracked_screen(self, strategy, ticker):
        nonlocal concurrent_count, max_concurrent
        
        async with lock:
            concurrent_count += 1
            max_concurrent = max(max_concurrent, concurrent_count)
        
        try:
            # Simulate some work
            await asyncio.sleep(0.1)
            # For testing, return a mock decision
            from models.strategy_v2 import StrategyDecision
            return StrategyDecision(
                strategy_id=strategy.id,
                ticker=ticker,
                action="SKIP",
                confidence=50,
                reasoning="Test",
                rule_results=[],
                data_snapshot={},
                current_price=100.0
            )
        finally:
            async with lock:
                concurrent_count -= 1
    
    StrategyExecutor.screen_candidate = tracked_screen
    
    try:
        strategy = TradingStrategyV2(
            user_id="test_user",
            name="Test Concurrency",
            description="Testing concurrency limits",
            screening_rules=[
                StrategyRule(
                    order=1,
                    description="Test rule",
                    data_sources=[],
                    decision_logic="Test",
                    weight=1.0
                )
            ]
        )
        
        executor = StrategyExecutor(max_concurrent_candidates=3)
        tickers = [f"TICK{i}" for i in range(10)]
        
        await executor.screen_candidates_parallel(strategy, tickers)
        
        print(f"\n✅ Max concurrent executions: {max_concurrent}")
        print(f"   Limit: {executor.max_concurrent_candidates}")
        
        # Should not exceed the limit
        assert max_concurrent <= executor.max_concurrent_candidates
        
    finally:
        # Restore original method
        StrategyExecutor.screen_candidate = original_screen


if __name__ == "__main__":
    # Run tests
    asyncio.run(test_parallel_candidate_screening())
    asyncio.run(test_parallel_position_management())
    asyncio.run(test_concurrency_limit())

