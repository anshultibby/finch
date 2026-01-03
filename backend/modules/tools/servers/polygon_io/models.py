"""
Pydantic models for Polygon.io API responses.

These models provide:
1. Clear documentation of response structure
2. Type safety and validation
3. IDE autocomplete support
4. Self-documenting code for the LLM agent
"""
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime


class Bar(BaseModel):
    """Single OHLCV price bar"""
    timestamp: int = Field(description="Unix timestamp in milliseconds")
    date: str = Field(description="Human-readable date (YYYY-MM-DD HH:MM:SS)")
    open: float = Field(description="Opening price")
    high: float = Field(description="Highest price")
    low: float = Field(description="Lowest price")
    close: float = Field(description="Closing price")
    volume: float = Field(description="Trading volume")
    vwap: Optional[float] = Field(default=None, description="Volume-weighted average price")
    trades: Optional[int] = Field(default=None, description="Number of trades")


class IntradayBarsResponse(BaseModel):
    """
    Response from get_intraday_bars()
    
    Example usage:
        # IMPORTANT: Use symbol= (not ticker=), check for errors!
        response = get_intraday_bars(symbol='NVDA', from_datetime='2024-01-01', to_datetime='2024-01-31', timespan='15min')
        if 'error' in response:
            print(f"Error: {response['error']}")
        else:
            bars = response['bars']  # Data is in 'bars' key!
            df = pd.DataFrame(bars)
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    """
    symbol: str = Field(description="Stock ticker symbol (uppercase)")
    from_: str = Field(alias="from", description="Start date/datetime")
    to: str = Field(description="End date/datetime")
    timespan: str = Field(description="Bar size: '1min', '5min', '15min', '30min', '1hour'")
    count: int = Field(description="Number of bars returned")
    bars: List[Bar] = Field(description="List of OHLCV bars")
    
    class Config:
        populate_by_name = True


class HistoricalPricesResponse(BaseModel):
    """
    Response from get_historical_prices()
    
    Example usage:
        # IMPORTANT: Use symbol= (not ticker=), check for errors!
        response = get_historical_prices(symbol='AAPL', from_date='2024-01-01', to_date='2024-12-31')
        if 'error' in response:
            print(f"Error: {response['error']}")
        else:
            bars = response['bars']  # Data is in 'bars' key!
            df = pd.DataFrame(bars)
    """
    symbol: str = Field(description="Stock ticker symbol (uppercase)")
    from_: str = Field(alias="from", description="Start date")
    to: str = Field(description="End date")
    timespan: str = Field(description="Bar size (e.g., '1 day', '5 minute')")
    count: int = Field(description="Number of bars returned")
    bars: List[Bar] = Field(description="List of OHLCV bars")
    
    class Config:
        populate_by_name = True


class LastTradeResponse(BaseModel):
    """Response from get_last_trade()"""
    symbol: str = Field(description="Stock ticker symbol")
    price: float = Field(description="Last trade price")
    size: int = Field(description="Trade size (shares)")
    exchange: int = Field(description="Exchange ID")
    timestamp: int = Field(description="Unix timestamp in nanoseconds")
    conditions: List[int] = Field(default=[], description="Trade condition codes")


class LastQuoteResponse(BaseModel):
    """Response from get_last_quote()"""
    symbol: str = Field(description="Stock ticker symbol")
    bid_price: float = Field(description="Best bid price")
    bid_size: int = Field(description="Bid size")
    ask_price: float = Field(description="Best ask price")
    ask_size: int = Field(description="Ask size")
    timestamp: int = Field(description="Unix timestamp")


class SnapshotResponse(BaseModel):
    """Response from get_snapshot()"""
    symbol: str = Field(description="Stock ticker symbol")
    price: Optional[float] = Field(description="Current/last trade price")
    change: Optional[float] = Field(description="Price change from previous close")
    change_percent: Optional[float] = Field(description="Percent change from previous close")
    open: Optional[float] = Field(description="Today's open price")
    high: Optional[float] = Field(description="Today's high price")
    low: Optional[float] = Field(description="Today's low price")
    close: Optional[float] = Field(description="Today's close/current price")
    volume: Optional[float] = Field(description="Today's volume")
    vwap: Optional[float] = Field(description="Volume-weighted average price")
    prev_close: Optional[float] = Field(description="Previous day's close")
    prev_volume: Optional[float] = Field(description="Previous day's volume")

