"""
Custom ETF Builder - Example Usage

This script demonstrates how to use the custom ETF builder tool.
Run this to test the feature or see example usage.

Usage:
    python -m modules.tools.examples.etf_builder_example
"""
import asyncio
import os
from modules.tools.etf_builder_tools import BuildCustomETFParams, build_custom_etf
from modules.agent.context import AgentContext


async def example_equal_weight_etf():
    """Example: Build an equal-weight tech ETF"""
    print("\n" + "="*60)
    print("EXAMPLE 1: Equal-Weight Tech ETF")
    print("="*60)
    
    # Create agent context (minimal for testing)
    context = AgentContext(
        user_id="test_user",
        chat_id="test_chat",
        data={}
    )
    
    # Build equal-weight ETF with big tech stocks
    params = BuildCustomETFParams(
        tickers=["AAPL", "MSFT", "GOOGL", "META", "NVDA"],
        weighting_method="equal_weight",
        name="Big Tech Equal Weight ETF"
    )
    
    print(f"\n📊 Building ETF with {len(params.tickers)} stocks...")
    print(f"   Weighting: {params.weighting_method}")
    print(f"   Tickers: {', '.join(params.tickers)}")
    
    # Call the tool
    result = None
    async for event in build_custom_etf(params=params, context=context):
        # Handle SSE events
        if hasattr(event, 'event'):
            print(f"   Status: {event.data.get('message', 'Processing...')}")
        else:
            # Final result
            result = event
    
    if result and result.get("success"):
        print("\nETF Built Successfully!\n")
        print(f"Name: {result['etf_name']}")
        print(f"Total Stocks: {result['total_stocks']}")
        print(f"Weighting Method: {result['weighting_method']}")
        
        print("\n📈 Allocation:")
        print("-" * 70)
        print(f"{'Ticker':<8} {'Name':<30} {'Weight':<10} {'Price':<12} {'Mkt Cap'}")
        print("-" * 70)
        
        for comp in result['components']:
            name = comp['name'][:28]  # Truncate long names
            weight = f"{comp['weight']*100:.2f}%"
            price = f"${comp['price']:.2f}"
            mkt_cap = f"${comp['market_cap']/1e9:.1f}B"
            print(f"{comp['ticker']:<8} {name:<30} {weight:<10} {price:<12} {mkt_cap}")
        
        print("-" * 70)
        print(f"\n💡 Top Holding: {result['summary']['top_holding']} ({result['summary']['top_weight']})")
        print(f"💰 Total Market Cap: ${result['summary']['total_market_cap']/1e12:.2f}T")
    else:
        print(f"\n❌ Failed: {result.get('error', 'Unknown error')}")


async def example_market_cap_etf():
    """Example: Build a market-cap weighted ETF"""
    print("\n" + "="*60)
    print("EXAMPLE 2: Market-Cap Weighted ETF")
    print("="*60)
    
    context = AgentContext(
        user_id="test_user",
        chat_id="test_chat",
        data={}
    )
    
    # Same stocks, but market-cap weighted
    params = BuildCustomETFParams(
        tickers=["AAPL", "MSFT", "GOOGL", "META", "NVDA"],
        weighting_method="market_cap",
        name="Big Tech Market Cap ETF"
    )
    
    print(f"\n📊 Building ETF with {len(params.tickers)} stocks...")
    print(f"   Weighting: {params.weighting_method}")
    print(f"   Tickers: {', '.join(params.tickers)}")
    
    result = None
    async for event in build_custom_etf(params=params, context=context):
        if hasattr(event, 'event'):
            print(f"   Status: {event.data.get('message', 'Processing...')}")
        else:
            result = event
    
    if result and result.get("success"):
        print("\nETF Built Successfully!\n")
        print(f"Name: {result['etf_name']}")
        print(f"Total Stocks: {result['total_stocks']}")
        print(f"Weighting Method: {result['weighting_method']}")
        
        print("\n📈 Allocation (sorted by weight):")
        print("-" * 70)
        print(f"{'Ticker':<8} {'Name':<30} {'Weight':<10} {'Price':<12} {'Mkt Cap'}")
        print("-" * 70)
        
        for comp in result['components']:
            name = comp['name'][:28]
            weight = f"{comp['weight']*100:.2f}%"
            price = f"${comp['price']:.2f}"
            mkt_cap = f"${comp['market_cap']/1e9:.1f}B"
            print(f"{comp['ticker']:<8} {name:<30} {weight:<10} {price:<12} {mkt_cap}")
        
        print("-" * 70)
        print(f"\n💡 Top Holding: {result['summary']['top_holding']} ({result['summary']['top_weight']})")
        print(f"💰 Total Market Cap: ${result['summary']['total_market_cap']/1e12:.2f}T")
        
        print("\n📊 Notice: Market-cap weighting gives larger companies higher allocation")
        print("   compared to equal-weight where each stock gets 20%.")


async def example_with_invalid_tickers():
    """Example: Handle invalid tickers gracefully"""
    print("\n" + "="*60)
    print("EXAMPLE 3: Error Handling (Invalid Tickers)")
    print("="*60)
    
    context = AgentContext(
        user_id="test_user",
        chat_id="test_chat",
        data={}
    )
    
    # Mix of valid and invalid tickers
    params = BuildCustomETFParams(
        tickers=["AAPL", "INVALID", "MSFT", "FAKE123", "GOOGL"],
        weighting_method="equal_weight",
        name="Test ETF with Invalid Tickers"
    )
    
    print(f"\n📊 Building ETF with {len(params.tickers)} stocks...")
    print(f"   Tickers: {', '.join(params.tickers)}")
    print(f"   (Note: INVALID and FAKE123 are not real tickers)")
    
    result = None
    async for event in build_custom_etf(params=params, context=context):
        if hasattr(event, 'event'):
            print(f"   Status: {event.data.get('message', 'Processing...')}")
        else:
            result = event
    
    if result and result.get("success"):
        print("\nETF Built Successfully (with warnings)!\n")
        print(f"Total Valid Stocks: {result['total_stocks']}")
        
        if result.get('failed_tickers'):
            print(f"⚠️  Failed Tickers: {', '.join(result['failed_tickers'])}")
        
        print("\n📈 Final Allocation:")
        print("-" * 70)
        print(f"{'Ticker':<8} {'Name':<30} {'Weight':<10}")
        print("-" * 70)
        
        for comp in result['components']:
            name = comp['name'][:28]
            weight = f"{comp['weight']*100:.2f}%"
            print(f"{comp['ticker']:<8} {name:<30} {weight:<10}")
        
        print("-" * 70)
        print("\n💡 The tool successfully built an ETF with valid tickers only.")
    else:
        print(f"\n❌ Failed: {result.get('error', 'Unknown error')}")


async def main():
    """Run all examples"""
    print("\n" + "="*70)
    print("  CUSTOM ETF BUILDER - EXAMPLE DEMONSTRATIONS")
    print("="*70)
    
    # Check for API key
    if not os.getenv("FMP_API_KEY"):
        print("\n⚠️  Warning: FMP_API_KEY not set in environment")
        print("   Set it with: export FMP_API_KEY='your-key-here'")
        print("   Proceeding anyway (may fail)...\n")
    
    # Run examples
    await example_equal_weight_etf()
    await asyncio.sleep(1)  # Small delay between examples
    
    await example_market_cap_etf()
    await asyncio.sleep(1)
    
    await example_with_invalid_tickers()
    
    print("\n" + "="*70)
    print("  EXAMPLES COMPLETE")
    print("="*70)
    print("\n💡 Next Steps:")
    print("   1. Try different ticker combinations")
    print("   2. Compare equal_weight vs market_cap strategies")
    print("   3. Use the agent to screen stocks first, then build ETFs")
    print("   4. Generate backtest code to see historical performance")
    print("   5. Visualize results with create_chart")
    print("\n")


if __name__ == "__main__":
    asyncio.run(main())

