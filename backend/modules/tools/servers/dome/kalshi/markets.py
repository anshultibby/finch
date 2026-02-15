"""
Kalshi Markets - Search and Pricing

Access Kalshi prediction markets via Dome API (read-only).
"""
from .._client import call_dome_api
from ..models import GetKalshiMarketsInput, GetKalshiMarketsOutput, GetKalshiMarketPriceInput, GetKalshiMarketPriceOutput


def get_markets(input: GetKalshiMarketsInput) -> GetKalshiMarketsOutput:
    """
    Search Kalshi prediction markets.
    
    Args:
        input: GetKalshiMarketsInput with filters
        
    Returns:
        GetKalshiMarketsOutput with markets list and pagination
        
    Example:
        from servers.dome.models import GetKalshiMarketsInput
        markets = get_markets(GetKalshiMarketsInput(
            series_ticker='FED',
            status='active'
        ))
        for m in markets.markets:
            print(f"{m.ticker}: {m.title}")
    """
    params = input.model_dump(exclude_none=True)
    result = call_dome_api("/kalshi/markets", params)
    return GetKalshiMarketsOutput(**result)


def get_market_price(input: GetKalshiMarketPriceInput) -> GetKalshiMarketPriceOutput:
    """
    Get current or historical price for a Kalshi market.
    
    Args:
        input: GetKalshiMarketPriceInput with ticker and optional at_time
        
    Returns:
        GetKalshiMarketPriceOutput with price and timestamp
        
    Example:
        from servers.dome.models import GetKalshiMarketPriceInput
        price = get_market_price(GetKalshiMarketPriceInput(ticker="FED-24FEB28-T4.75"))
        print(f"Current price: {price.price}¢")
    """
    endpoint = f"/kalshi/market-price/{input.ticker}"
    params = input.model_dump(exclude={"ticker"}, exclude_none=True)
    result = call_dome_api(endpoint, params)
    return GetKalshiMarketPriceOutput(**result)
