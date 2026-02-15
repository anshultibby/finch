"""
Pydantic models for Dome API (Polymarket & Kalshi prediction markets).

These models provide:
1. Clear documentation of response structure
2. Type safety and validation
3. IDE autocomplete support
4. Self-documenting code for the LLM agent
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Literal, Dict, Any


# ============================================================================
# POLYMARKET WALLET MODELS
# ============================================================================

class Position(BaseModel):
    """Single position in a prediction market"""
    wallet: str = Field(description="Wallet address holding this position")
    token_id: str = Field(description="Token ID for this outcome")
    condition_id: str = Field(description="Condition ID for the market")
    title: str = Field(description="Market question/title")
    shares: int = Field(description="Raw shares (divide by 1e6 for normalized)")
    shares_normalized: float = Field(description="Position size in shares")
    redeemable: bool = Field(description="Whether position can be redeemed")
    market_slug: str = Field(description="Market identifier (URL-safe)")
    event_slug: Optional[str] = Field(default=None, description="Event identifier")
    label: str = Field(description="Outcome label: 'Yes' or 'No'")
    winning_outcome: Optional[str] = Field(default=None, description="Winning outcome if resolved")
    market_status: str = Field(description="Market status: 'open' or 'closed'")


class Pagination(BaseModel):
    """Pagination metadata"""
    limit: int = Field(description="Max items per page")
    count: Optional[int] = Field(default=None, description="Total count if available")
    has_more: bool = Field(description="Whether more results exist")
    pagination_key: Optional[str] = Field(default=None, description="Key for next page")


class GetPositionsInput(BaseModel):
    """Input parameters for get_positions()"""
    wallet_address: str = Field(description="Proxy wallet address (0x...)")
    limit: int = Field(default=100, ge=1, le=100, description="Max positions to return")
    pagination_key: Optional[str] = Field(default=None, description="Pagination cursor")


class GetPositionsOutput(BaseModel):
    """
    Response from get_positions()
    
    Example usage:
        from servers.dome.polymarket.wallet import get_positions
        params = GetPositionsInput(wallet_address="0x742d35...", limit=50)
        result = get_positions(**params.model_dump())
        
        if 'error' not in result:
            output = GetPositionsOutput(**result)
            for pos in output.positions:
                print(f"{pos.title}: {pos.shares_normalized} {pos.label}")
    """
    wallet_address: str = Field(description="Wallet address queried")
    positions: List[Position] = Field(description="List of active positions")
    pagination: Pagination = Field(description="Pagination info")


class PnLDataPoint(BaseModel):
    """Single P&L data point"""
    timestamp: int = Field(description="Unix timestamp (seconds)")
    pnl_to_date: float = Field(description="Cumulative realized P&L up to this point (USD)")


class GetWalletPnLInput(BaseModel):
    """Input parameters for get_wallet_pnl()"""
    wallet_address: str = Field(description="Proxy wallet address (0x...)")
    granularity: Literal["day", "week", "month", "year", "all"] = Field(
        default="day",
        description="Time granularity for P&L data"
    )
    start_time: Optional[int] = Field(default=None, description="Unix timestamp start (seconds)")
    end_time: Optional[int] = Field(default=None, description="Unix timestamp end (seconds)")


class GetWalletPnLOutput(BaseModel):
    """
    Response from get_wallet_pnl()
    
    NOTE: Returns REALIZED P&L only (from sells/redeems), not unrealized.
    
    Example usage:
        from servers.dome.polymarket.wallet import get_wallet_pnl
        params = GetWalletPnLInput(wallet_address="0x742d35...", granularity="day")
        result = get_wallet_pnl(**params.model_dump())
        
        if 'error' not in result:
            output = GetWalletPnLOutput(**result)
            latest = output.pnl_over_time[-1]
            print(f"Total realized P&L: ${latest.pnl_to_date:,.2f}")
    """
    granularity: str = Field(description="Granularity used")
    start_time: int = Field(description="Start timestamp")
    end_time: int = Field(description="End timestamp")
    wallet_address: str = Field(description="Wallet address")
    pnl_over_time: List[PnLDataPoint] = Field(description="P&L history")


class Activity(BaseModel):
    """Single activity record (SPLIT, MERGE, or REDEEM)"""
    token_id: str = Field(description="Token ID")
    side: Literal["SPLIT", "MERGE", "REDEEM"] = Field(description="Activity type")
    market_slug: str = Field(description="Market identifier")
    condition_id: str = Field(description="Condition ID")
    shares: int = Field(description="Raw shares")
    shares_normalized: float = Field(description="Normalized shares")
    price: float = Field(description="Price at time of activity (1 for redeems)")
    tx_hash: str = Field(description="Transaction hash")
    title: str = Field(description="Market title")
    timestamp: int = Field(description="Unix timestamp (seconds)")
    user: str = Field(description="User wallet address")


class GetWalletActivityInput(BaseModel):
    """Input parameters for get_wallet_activity()"""
    wallet_address: str = Field(description="Proxy wallet address (0x...)")
    start_time: Optional[int] = Field(default=None, description="Unix timestamp start")
    end_time: Optional[int] = Field(default=None, description="Unix timestamp end")
    market_slug: Optional[str] = Field(default=None, description="Filter by market")
    condition_id: Optional[str] = Field(default=None, description="Filter by condition ID")
    limit: int = Field(default=100, ge=1, le=1000, description="Max activities to return")
    pagination_key: Optional[str] = Field(default=None, description="Pagination cursor")


class GetWalletActivityOutput(BaseModel):
    """
    Response from get_wallet_activity()
    
    NOTE: Returns SPLITS, MERGES, and REDEEMS only - NOT BUY/SELL trades.
    For BUY/SELL trades, use get_wallet_trades() instead.
    """
    activities: List[Activity] = Field(description="List of activities")
    pagination: Pagination = Field(description="Pagination info")


class Order(BaseModel):
    """Single executed order (BUY or SELL)"""
    token_id: str = Field(description="Token ID")
    token_label: str = Field(description="'Yes' or 'No'")
    side: Literal["BUY", "SELL"] = Field(description="Order side")
    market_slug: str = Field(description="Market identifier")
    condition_id: str = Field(description="Condition ID")
    shares_normalized: float = Field(description="Normalized share amount")
    price: float = Field(description="Execution price (0-1)")
    tx_hash: str = Field(description="Transaction hash")
    title: str = Field(description="Market title")
    timestamp: int = Field(description="Unix timestamp of execution")
    user: str = Field(description="Maker wallet address")
    taker: str = Field(description="Taker wallet address")


class GetWalletTradesInput(BaseModel):
    """Input parameters for get_wallet_trades()"""
    wallet_address: str = Field(description="Wallet address (0x...)")
    start_time: Optional[int] = Field(default=None, description="Unix timestamp start")
    end_time: Optional[int] = Field(default=None, description="Unix timestamp end")
    market_slug: Optional[str] = Field(default=None, description="Filter by market")
    condition_id: Optional[str] = Field(default=None, description="Filter by condition ID")
    token_id: Optional[str] = Field(default=None, description="Filter by token ID")
    limit: int = Field(default=100, ge=1, le=1000, description="Max trades to return")
    pagination_key: Optional[str] = Field(default=None, description="Pagination cursor")


class GetWalletTradesOutput(BaseModel):
    """
    Response from get_wallet_trades()
    
    Example usage:
        from servers.dome.polymarket.wallet import get_wallet_trades
        params = GetWalletTradesInput(wallet_address="0x6a72...", limit=100)
        result = get_wallet_trades(**params.model_dump())
        
        if 'error' not in result:
            output = GetWalletTradesOutput(**result)
            for order in output.orders:
                print(f"{order.side} {order.shares_normalized:.2f} @ ${order.price:.2f}")
    """
    orders: List[Order] = Field(description="List of executed orders")
    pagination: Pagination = Field(description="Pagination info")


# ============================================================================
# POLYMARKET MARKETS MODELS
# ============================================================================

class MarketSide(BaseModel):
    """Single outcome side (Yes or No)"""
    id: str = Field(description="Token ID for this outcome")
    label: str = Field(description="Outcome label: 'Yes' or 'No'")


class Market(BaseModel):
    """Single prediction market"""
    market_slug: str = Field(description="Market identifier (URL-safe)")
    event_slug: Optional[str] = Field(default=None, description="Event identifier")
    condition_id: str = Field(description="Market condition ID (0x...)")
    title: str = Field(description="Market question")
    description: Optional[str] = Field(default=None, description="Full description")
    tags: List[str] = Field(default=[], description="Market tags (e.g., ['crypto', 'politics'])")
    volume_1_week: Optional[float] = Field(default=None, description="7-day trading volume (USD)")
    volume_1_month: Optional[float] = Field(default=None, description="30-day trading volume (USD)")
    volume_1_year: Optional[float] = Field(default=None, description="1-year trading volume (USD)")
    volume_total: float = Field(description="Total trading volume (USD)")
    status: str = Field(description="Market status: 'open' or 'closed'")
    start_time: Optional[int] = Field(default=None, description="Unix timestamp")
    end_time: Optional[int] = Field(default=None, description="Unix timestamp")
    completed_time: Optional[int] = Field(default=None, description="Unix timestamp")
    close_time: Optional[int] = Field(default=None, description="Unix timestamp")
    side_a: MarketSide = Field(description="First outcome (usually Yes)")
    side_b: MarketSide = Field(description="Second outcome (usually No)")
    winning_side: Optional[str] = Field(default=None, description="'side_a' or 'side_b' if resolved")
    image: Optional[str] = Field(default=None, description="Market image URL")
    resolution_source: Optional[str] = Field(default=None, description="Resolution source URL")


class GetMarketsInput(BaseModel):
    """Input parameters for get_markets()"""
    market_slug: Optional[List[str]] = Field(default=None, description="Filter by market slug(s)")
    event_slug: Optional[List[str]] = Field(default=None, description="Filter by event slug(s)")
    condition_id: Optional[List[str]] = Field(default=None, description="Filter by condition ID(s)")
    token_id: Optional[List[str]] = Field(default=None, description="Filter by token ID(s)")
    tags: Optional[List[str]] = Field(default=None, description="Filter by tags")
    search: Optional[str] = Field(default=None, description="Search keywords")
    status: Optional[str] = Field(default=None, description="Filter by status: 'open' or 'closed'")
    min_volume: Optional[float] = Field(default=None, description="Minimum trading volume (USD)")
    start_time: Optional[int] = Field(default=None, description="Filter markets from timestamp")
    end_time: Optional[int] = Field(default=None, description="Filter markets until timestamp")
    limit: int = Field(default=10, ge=1, le=100, description="Max markets to return")
    pagination_key: Optional[str] = Field(default=None, description="Pagination cursor")


class GetMarketsOutput(BaseModel):
    """
    Response from get_markets()
    
    Example usage:
        from servers.dome.polymarket.markets import get_markets
        params = GetMarketsInput(tags=['crypto'], status='open', limit=20)
        result = get_markets(**params.model_dump())
        
        if 'error' not in result:
            output = GetMarketsOutput(**result)
            for m in output.markets:
                print(f"{m.title}: ${m.volume_total:,.0f} volume")
                print(f"  {m.side_a.label}: token {m.side_a.id}")
    """
    markets: List[Market] = Field(description="List of markets")
    pagination: Dict[str, Any] = Field(description="Pagination info")


# ============================================================================
# POLYMARKET PRICES MODELS
# ============================================================================

class GetMarketPriceInput(BaseModel):
    """Input parameters for get_market_price()"""
    token_id: str = Field(description="Token ID (outcome)")


class GetMarketPriceOutput(BaseModel):
    """Response from get_market_price()"""
    token_id: str = Field(description="Token ID")
    price: float = Field(description="Current price (0-1 probability)")
    timestamp: int = Field(description="Unix timestamp")


class Candle(BaseModel):
    """Single candlestick data point"""
    timestamp: int = Field(description="Unix timestamp")
    open: float = Field(description="Opening price")
    high: float = Field(description="Highest price")
    low: float = Field(description="Lowest price")
    close: float = Field(description="Closing price")
    volume: float = Field(description="Trading volume")


class GetCandlesticksInput(BaseModel):
    """Input parameters for get_candlesticks()"""
    condition_id: str = Field(description="Condition ID (0x...)")
    start_time: int = Field(description="Unix timestamp start")
    end_time: int = Field(description="Unix timestamp end")
    interval: int = Field(default=1440, description="Interval in minutes (e.g., 1440 = daily)")


class TokenCandlesticks(BaseModel):
    """Candlesticks for one token"""
    token_id: str = Field(description="Token ID")
    label: str = Field(description="Outcome label")
    candles: List[Candle] = Field(description="Candlestick data")


class GetCandlesticksOutput(BaseModel):
    """Response from get_candlesticks()"""
    condition_id: str = Field(description="Condition ID")
    candlesticks: List[TokenCandlesticks] = Field(description="Candlesticks for each outcome")
