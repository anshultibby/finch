"""
Polymarket Prices - Real-time and Historical Data

Get current prices and historical candlestick data.
"""
from typing import Literal
from .._client import call_dome_api, DomeAPIError
from ..models import GetMarketPriceInput, GetMarketPriceOutput, GetCandlesticksInput, GetCandlesticksOutput


def get_market_price(input: GetMarketPriceInput) -> GetMarketPriceOutput:
    """
    Get current or historical price for a Polymarket market.
    
    Args:
        input: GetMarketPriceInput with token_id and optional at_time
        
    Returns:
        GetMarketPriceOutput with price and timestamp
        
    Example:
        from servers.dome.models import GetMarketPriceInput
        price = get_market_price(GetMarketPriceInput(token_id="98250445..."))
        print(f"Current probability: {price.price*100:.1f}%")
    """
    endpoint = f"/polymarket/market-price/{input.token_id}"
    params = input.model_dump(exclude={"token_id"}, exclude_none=True)
    result = call_dome_api(endpoint, params)
    return GetMarketPriceOutput(**result)


def get_candlesticks(input: GetCandlesticksInput) -> GetCandlesticksOutput:
    """
    Get historical candlestick/OHLC data for charting.
    
    Args:
        input: GetCandlesticksInput with condition_id, time range, and interval
        
    Returns:
        GetCandlesticksOutput with candlestick data
        
    Example:
        import time
        from servers.dome.models import GetCandlesticksInput
        
        end = int(time.time())
        start = end - (30 * 24 * 60 * 60)
        
        candles = get_candlesticks(GetCandlesticksInput(
            condition_id="0x4567b275...",
            start_time=start,
            end_time=end,
            interval=1440
        ))
        
        for token_candles in candles.candlesticks:
            print(f"{token_candles.label}: {len(token_candles.candles)} candles")
    """
    if input.interval not in [1, 60, 1440]:
        raise DomeAPIError(f"Invalid interval {input.interval}. Must be 1, 60, or 1440")
    
    endpoint = f"/polymarket/candlesticks/{input.condition_id}"
    params = input.model_dump(exclude={"condition_id"})
    result = call_dome_api(endpoint, params)
    return GetCandlesticksOutput(**result)
