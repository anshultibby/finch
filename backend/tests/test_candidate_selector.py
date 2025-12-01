"""
Test Candidate Selector - LLM-powered candidate selection
"""
import pytest
import asyncio
from models.strategy_v2 import TradingStrategyV2, StrategyRule, CandidateSource, DataSource
from services.candidate_selector import CandidateSelector


@pytest.fixture
def momentum_strategy():
    """Sample momentum strategy"""
    return TradingStrategyV2(
        user_id="test-user",
        name="Momentum Tech Strategy",
        description="Buy high-momentum technology stocks with strong earnings growth",
        candidate_source=CandidateSource(
            type="universe",
            universe="nasdaq100",
            sector="Technology"
        ),
        screening_rules=[
            StrategyRule(
                order=1,
                description="Check if revenue growth > 20% YoY",
                data_sources=[
                    DataSource(type="fmp", endpoint="income-statement", parameters={"period": "annual", "limit": 2})
                ],
                decision_logic="If revenue growth > 20%, CONTINUE. Otherwise SKIP.",
                weight=0.4
            ),
            StrategyRule(
                order=2,
                description="Check if stock has positive momentum (price > 50-day MA)",
                data_sources=[
                    DataSource(type="fmp", endpoint="quote", parameters={})
                ],
                decision_logic="If price is above 50-day moving average, BUY. Otherwise SKIP.",
                weight=0.6
            )
        ]
    )


@pytest.fixture
def value_strategy():
    """Sample value strategy"""
    return TradingStrategyV2(
        user_id="test-user",
        name="Value Healthcare Strategy",
        description="Find undervalued healthcare companies with low P/E ratios",
        candidate_source=CandidateSource(
            type="universe",
            universe="sp500",
            sector="Healthcare"
        ),
        screening_rules=[
            StrategyRule(
                order=1,
                description="Check if P/E ratio < 15",
                data_sources=[
                    DataSource(type="fmp", endpoint="key-metrics", parameters={"period": "annual", "limit": 1})
                ],
                decision_logic="If P/E ratio < 15, CONTINUE. Otherwise SKIP.",
                weight=0.5
            ),
            StrategyRule(
                order=2,
                description="Check if debt-to-equity < 1.0",
                data_sources=[
                    DataSource(type="fmp", endpoint="ratios", parameters={"period": "annual", "limit": 1})
                ],
                decision_logic="If debt-to-equity < 1.0, BUY. Otherwise SKIP.",
                weight=0.5
            )
        ]
    )


@pytest.fixture
def custom_tickers_strategy():
    """Strategy with custom tickers"""
    return TradingStrategyV2(
        user_id="test-user",
        name="Custom Watchlist",
        description="Screen my custom watchlist",
        candidate_source=CandidateSource(
            type="custom",
            tickers=["AAPL", "MSFT", "GOOGL", "NVDA", "META"]
        ),
        screening_rules=[
            StrategyRule(
                order=1,
                description="Basic momentum check",
                data_sources=[DataSource(type="fmp", endpoint="quote", parameters={})],
                decision_logic="If price > 50-day MA, BUY. Otherwise SKIP.",
                weight=1.0
            )
        ]
    )


@pytest.mark.asyncio
@pytest.mark.real_api
async def test_select_candidates_momentum_strategy(momentum_strategy):
    """Test LLM selects appropriate candidates for momentum strategy"""
    selector = CandidateSelector()
    
    candidates = await selector.select_candidates(momentum_strategy, max_candidates=10)
    
    print("\n" + "="*80)
    print(f"MOMENTUM STRATEGY: {momentum_strategy.name}")
    print(f"Description: {momentum_strategy.description}")
    print("-"*80)
    print(f"Selected Candidates ({len(candidates)}):")
    for ticker in candidates:
        print(f"  - {ticker}")
    print("="*80)
    
    # Assertions
    assert len(candidates) <= 10, "Should return max 10 candidates"
    assert len(candidates) > 0, "Should return at least 1 candidate"
    assert all(isinstance(t, str) for t in candidates), "All candidates should be ticker strings"


@pytest.mark.asyncio
@pytest.mark.real_api
async def test_select_candidates_value_strategy(value_strategy):
    """Test LLM selects appropriate candidates for value strategy"""
    selector = CandidateSelector()
    
    candidates = await selector.select_candidates(value_strategy, max_candidates=10)
    
    print("\n" + "="*80)
    print(f"VALUE STRATEGY: {value_strategy.name}")
    print(f"Description: {value_strategy.description}")
    print("-"*80)
    print(f"Selected Candidates ({len(candidates)}):")
    for ticker in candidates:
        print(f"  - {ticker}")
    print("="*80)
    
    # Assertions
    assert len(candidates) <= 10, "Should return max 10 candidates"
    assert len(candidates) > 0, "Should return at least 1 candidate"


@pytest.mark.asyncio
async def test_select_candidates_custom_tickers(custom_tickers_strategy):
    """Test custom tickers are used directly (no LLM call)"""
    selector = CandidateSelector()
    
    candidates = await selector.select_candidates(custom_tickers_strategy, max_candidates=10)
    
    print("\n" + "="*80)
    print(f"CUSTOM STRATEGY: {custom_tickers_strategy.name}")
    print("-"*80)
    print(f"Selected Candidates ({len(candidates)}):")
    for ticker in candidates:
        print(f"  - {ticker}")
    print("="*80)
    
    # Should use custom tickers directly
    assert candidates == custom_tickers_strategy.candidate_source.tickers
    assert len(candidates) == 5


@pytest.mark.asyncio
@pytest.mark.real_api
async def test_parallel_selection():
    """Test multiple strategies can select candidates in parallel"""
    selector = CandidateSelector()
    
    strategies = [
        TradingStrategyV2(
            user_id="test",
            name=f"Strategy {i}",
            description=f"Test strategy {i}",
            candidate_source=CandidateSource(type="universe", universe="sp500"),
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
        for i in range(3)
    ]
    
    # Select candidates for all strategies in parallel
    tasks = [
        selector.select_candidates(strategy, max_candidates=5)
        for strategy in strategies
    ]
    
    results = await asyncio.gather(*tasks)
    
    print("\n" + "="*80)
    print("PARALLEL SELECTION TEST")
    print("-"*80)
    for i, candidates in enumerate(results):
        print(f"Strategy {i}: {len(candidates)} candidates - {candidates}")
    print("="*80)
    
    assert len(results) == 3
    assert all(len(c) <= 5 for c in results)


@pytest.mark.asyncio
@pytest.mark.real_api
async def test_context_gathering():
    """Test that context data is gathered properly"""
    selector = CandidateSelector()
    
    strategy = TradingStrategyV2(
        user_id="test",
        name="Test",
        description="Test strategy",
        candidate_source=CandidateSource(type="universe", universe="sp500"),
        screening_rules=[
            StrategyRule(
                order=1,
                description="Test",
                data_sources=[],
                decision_logic="Test",
                weight=1.0
            )
        ]
    )
    
    context = await selector._gather_context_data(strategy)
    
    print("\n" + "="*80)
    print("CONTEXT DATA")
    print("-"*80)
    print(f"Market Movers: {list(context.get('market_movers', {}).keys()) if context.get('market_movers') else 'None'}")
    print(f"Sector Performance: {'Available' if context.get('sector_performance') else 'None'}")
    print(f"Recent News: {len(context.get('recent_news', [])) if context.get('recent_news') else 0} items")
    print("="*80)
    
    # Context should have these keys (may be None if API fails)
    assert "market_movers" in context
    assert "sector_performance" in context
    assert "recent_news" in context


if __name__ == "__main__":
    # Run a quick test
    async def quick_test():
        strategy = TradingStrategyV2(
            user_id="test",
            name="Quick Momentum Test",
            description="Find high-growth tech stocks with strong momentum",
            candidate_source=CandidateSource(
                type="universe",
                universe="nasdaq100",
                sector="Technology"
            ),
            screening_rules=[
                StrategyRule(
                    order=1,
                    description="Check revenue growth",
                    data_sources=[],
                    decision_logic="High revenue growth",
                    weight=1.0
                )
            ]
        )
        
        selector = CandidateSelector()
        candidates = await selector.select_candidates(strategy)
        
        print(f"\nSelected candidates: {candidates}")
    
    asyncio.run(quick_test())

