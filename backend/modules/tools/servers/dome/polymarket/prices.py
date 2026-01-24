"""
Polymarket Prices - Real-time and Historical Data

Get current prices and historical candlestick data.
"""
from typing import Optional, Literal, Dict, Any
from .._client import call_dome_api


def get_market_price(
    token_id: str,
    at_time: Optional[int] = None
) -> Dict[str, Any]:
    """
    Get current or historical price for a Polymarket market.
    
    Args:
        token_id: Token ID for the market outcome (get from get_markets)
        at_time: Optional Unix timestamp (seconds) for historical price
                 If not provided, returns most recent price
        
    Returns:
        dict with:
        - price: Market price between 0 and 1 (e.g., 0.65 = 65% probability)
        - at_time: Unix timestamp for the price
        
    Example:
        # Get current price
        price = get_market_price("98250445447699368679516...")
        if 'error' not in price:
            print(f"Current probability: {price['price']*100:.1f}%")
            
        # Get historical price
        past_price = get_market_price("98250...", at_time=1640995200)
    """
    endpoint = f"/polymarket/market-price/{token_id}"
    params = {}
    
    if at_time:
        params["at_time"] = at_time
    
    return call_dome_api(endpoint, params)


def get_candlesticks(
    condition_id: str,
    start_time: int,
    end_time: int,
    interval: Literal[1, 60, 1440] = 1
) -> Dict[str, Any]:
    """
    Get historical candlestick/OHLC data for charting.
    
    Args:
        condition_id: Market condition ID (get from get_markets)
        start_time: Unix timestamp (seconds) for start of range
        end_time: Unix timestamp (seconds) for end of range
        interval: Candle interval:
            - 1 = 1 minute (max range: 1 week)
            - 60 = 1 hour (max range: 1 month)
            - 1440 = 1 day (max range: 1 year)
            
    Returns:
        dict with:
        - candlesticks: List of [candle_data, token_metadata] tuples
            Each candle has:
            - end_period_ts: Timestamp
            - open_interest: Open interest
            - price: OHLC prices (open, high, low, close)
            - volume: Trading volume
            - yes_ask/yes_bid: Ask/bid prices
            
    Example:
        import time
        
        # Get 1-day candles for last month
        end = int(time.time())
        start = end - (30 * 24 * 60 * 60)  # 30 days ago
        
        candles = get_candlesticks(
            condition_id="0x4567b275...",
            start_time=start,
            end_time=end,
            interval=1440  # Daily
        )
        
        if 'error' not in candles:
            # Convert to DataFrame for analysis
            import pandas as pd
            data = []
            for candle_array, token_meta in candles['candlesticks']:
                for candle in candle_array:
                    data.append({
                        'timestamp': candle['end_period_ts'],
                        'close': candle['price']['close'],
                        'volume': candle['volume']
                    })
            df = pd.DataFrame(data)
    """
    if interval not in [1, 60, 1440]:
        return {"error": f"Invalid interval {interval}. Must be 1, 60, or 1440"}
    
    endpoint = f"/polymarket/candlesticks/{condition_id}"
    params = {
        "start_time": start_time,
        "end_time": end_time,
        "interval": interval
    }
    
    return call_dome_api(endpoint, params)
