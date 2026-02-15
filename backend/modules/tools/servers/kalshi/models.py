"""
Pydantic models for Kalshi API (prediction market trading).

These models provide:
1. Clear documentation of response structure
2. Type safety and validation
3. IDE autocomplete support
4. Self-documenting code for the LLM agent
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Literal


# ============================================================================
# PORTFOLIO MODELS
# ============================================================================

class GetBalanceOutput(BaseModel):
    """
    Response from get_kalshi_balance()
    
    Example usage:
        from servers.kalshi.portfolio import get_kalshi_balance
        result = get_kalshi_balance()
        
        if 'error' not in result:
            output = GetBalanceOutput(**result)
            print(f"Balance: ${output.balance:.2f}")
    """
    balance: float = Field(description="Account balance in dollars")
    portfolio_value: float = Field(description="Portfolio value in dollars")


class Position(BaseModel):
    """Single Kalshi position"""
    ticker: str = Field(description="Market ticker (e.g., KXBTC-24DEC31-T100000)")
    position: int = Field(description="Number of contracts held")
    market_exposure: float = Field(description="Market exposure in dollars")
    fees_paid: Optional[float] = Field(default=None, description="Total fees paid")
    realized_pnl: Optional[float] = Field(default=None, description="Realized P&L")
    total_cost: Optional[float] = Field(default=None, description="Total cost basis")


class GetPositionsInput(BaseModel):
    """Input parameters for get_kalshi_positions()"""
    limit: int = Field(default=100, ge=1, description="Max positions to return")


class GetPositionsOutput(BaseModel):
    """
    Response from get_kalshi_positions()
    
    Example usage:
        from servers.kalshi.portfolio import get_kalshi_positions
        result = get_kalshi_positions(limit=50)
        
        if 'error' not in result:
            output = GetPositionsOutput(**result)
            for pos in output.positions:
                print(f"{pos.ticker}: {pos.position} contracts")
    """
    positions: List[Position] = Field(description="List of positions")
    count: int = Field(description="Number of positions")


class PortfolioSummary(BaseModel):
    """Complete portfolio summary"""
    balance: float = Field(description="Cash balance")
    portfolio_value: float = Field(description="Total portfolio value")
    positions: List[Position] = Field(description="All positions")
    total_market_exposure: float = Field(description="Total market exposure")


class GetPortfolioOutput(BaseModel):
    """
    Response from get_kalshi_portfolio()
    
    Example usage:
        from servers.kalshi.portfolio import get_kalshi_portfolio
        result = get_kalshi_portfolio()
        
        if 'error' not in result:
            output = GetPortfolioOutput(**result)
            print(f"Balance: ${output.balance:.2f}")
            print(f"Total exposure: ${output.total_market_exposure:.2f}")
    """
    balance: float = Field(description="Cash balance")
    portfolio_value: float = Field(description="Total portfolio value")
    positions: List[Position] = Field(description="All positions")
    total_market_exposure: float = Field(description="Total market exposure")


# ============================================================================
# MARKETS MODELS
# ============================================================================

class Event(BaseModel):
    """Kalshi event (groups related markets)"""
    event_ticker: str = Field(description="Event ticker")
    title: str = Field(description="Event title")
    series_ticker: Optional[str] = Field(default=None, description="Series ticker")
    category: Optional[str] = Field(default=None, description="Category")
    sub_title: Optional[str] = Field(default=None, description="Sub-title")
    mutually_exclusive: bool = Field(description="Whether outcomes are mutually exclusive")
    strike_date: Optional[str] = Field(default=None, description="Strike date")


class GetEventsInput(BaseModel):
    """Input parameters for get_kalshi_events()"""
    limit: int = Field(default=100, ge=1, description="Max events to return")
    status: Optional[Literal["open", "closed", "settled"]] = Field(
        default=None,
        description="Filter by status"
    )
    series_ticker: Optional[str] = Field(default=None, description="Filter by series")


class GetEventsOutput(BaseModel):
    """
    Response from get_kalshi_events()
    
    Example usage:
        from servers.kalshi.markets import get_kalshi_events
        params = GetEventsInput(limit=50, status="open")
        result = get_kalshi_events(**params.model_dump())
        
        if 'error' not in result:
            output = GetEventsOutput(**result)
            for event in output.events:
                print(f"{event.event_ticker}: {event.title}")
    """
    events: List[Event] = Field(description="List of events")
    count: int = Field(description="Number of events")


class MarketDetails(BaseModel):
    """Detailed market information"""
    ticker: str = Field(description="Market ticker")
    event_ticker: str = Field(description="Event ticker")
    title: str = Field(description="Market title")
    subtitle: Optional[str] = Field(default=None, description="Market subtitle")
    yes_bid: Optional[int] = Field(default=None, description="Yes bid price (cents)")
    yes_ask: Optional[int] = Field(default=None, description="Yes ask price (cents)")
    no_bid: Optional[int] = Field(default=None, description="No bid price (cents)")
    no_ask: Optional[int] = Field(default=None, description="No ask price (cents)")
    last_price: Optional[int] = Field(default=None, description="Last trade price (cents)")
    volume: Optional[int] = Field(default=None, description="24h volume")
    open_interest: Optional[int] = Field(default=None, description="Open interest")
    liquidity: Optional[int] = Field(default=None, description="Liquidity")
    status: str = Field(description="Market status")
    can_close_early: bool = Field(description="Whether market can close early")
    expiration_time: Optional[str] = Field(default=None, description="Expiration timestamp")
    close_time: Optional[str] = Field(default=None, description="Close timestamp")
    settlement_value: Optional[str] = Field(default=None, description="Settlement value")


class GetMarketInput(BaseModel):
    """Input parameters for get_kalshi_market()"""
    ticker: str = Field(description="Market ticker (e.g., KXBTC-24DEC31-T100000)")


class GetMarketOutput(BaseModel):
    """
    Response from get_kalshi_market()
    
    Example usage:
        from servers.kalshi.markets import get_kalshi_market
        params = GetMarketInput(ticker="KXBTC-24DEC31-T100000")
        result = get_kalshi_market(**params.model_dump())
        
        if 'error' not in result:
            output = GetMarketOutput(**result)
            print(f"Yes: {output.yes_bid}-{output.yes_ask}")
            print(f"No: {output.no_bid}-{output.no_ask}")
    """
    ticker: str
    event_ticker: str
    title: str
    subtitle: Optional[str] = None
    yes_bid: Optional[int] = None
    yes_ask: Optional[int] = None
    no_bid: Optional[int] = None
    no_ask: Optional[int] = None
    last_price: Optional[int] = None
    volume: Optional[int] = None
    open_interest: Optional[int] = None
    status: str


# ============================================================================
# TRADING MODELS
# ============================================================================

class PlaceOrderInput(BaseModel):
    """Input parameters for place_kalshi_order()"""
    ticker: str = Field(description="Market ticker")
    side: Literal["yes", "no"] = Field(description="Order side: 'yes' or 'no'")
    action: Literal["buy", "sell"] = Field(description="Order action: 'buy' or 'sell'")
    count: int = Field(ge=1, description="Number of contracts")
    yes_price: Optional[int] = Field(
        default=None,
        ge=1,
        le=99,
        description="Limit price for YES in cents (1-99)"
    )
    no_price: Optional[int] = Field(
        default=None,
        ge=1,
        le=99,
        description="Limit price for NO in cents (1-99)"
    )
    expiration_ts: Optional[int] = Field(
        default=None,
        description="Order expiration Unix timestamp (optional)"
    )


class OrderResponse(BaseModel):
    """Response from placing an order"""
    order_id: str = Field(description="Unique order ID")
    ticker: str = Field(description="Market ticker")
    side: str = Field(description="Order side")
    action: str = Field(description="Order action")
    count: int = Field(description="Number of contracts")
    yes_price: Optional[int] = Field(default=None, description="YES price in cents")
    no_price: Optional[int] = Field(default=None, description="NO price in cents")
    status: str = Field(description="Order status")
    created_time: Optional[str] = Field(default=None, description="Creation timestamp")


class PlaceOrderOutput(BaseModel):
    """
    Response from place_kalshi_order()
    
    Example usage:
        from servers.kalshi.trading import place_kalshi_order
        params = PlaceOrderInput(
            ticker="KXBTC-24DEC31-T100000",
            side="yes",
            action="buy",
            count=10,
            yes_price=65
        )
        result = place_kalshi_order(**params.model_dump())
        
        if 'error' not in result:
            output = PlaceOrderOutput(**result)
            print(f"Order placed: {output.order_id}")
    """
    order_id: str
    ticker: str
    side: str
    action: str
    count: int
    yes_price: Optional[int] = None
    no_price: Optional[int] = None
    status: str
    created_time: Optional[str] = None


class Order(BaseModel):
    """Single order"""
    order_id: str = Field(description="Order ID")
    ticker: str = Field(description="Market ticker")
    side: str = Field(description="Order side")
    action: str = Field(description="Order action")
    count: int = Field(description="Number of contracts")
    yes_price: Optional[int] = Field(default=None, description="YES price in cents")
    no_price: Optional[int] = Field(default=None, description="NO price in cents")
    status: str = Field(description="Order status")
    created_time: Optional[str] = Field(default=None, description="Creation time")


class GetOrdersOutput(BaseModel):
    """Response from get_kalshi_orders()"""
    orders: List[Order] = Field(description="List of orders")
    count: int = Field(description="Number of orders")


class CancelOrderInput(BaseModel):
    """Input parameters for cancel_kalshi_order()"""
    order_id: str = Field(description="Order ID to cancel")


class CancelOrderOutput(BaseModel):
    """Response from cancel_kalshi_order()"""
    order_id: str = Field(description="Cancelled order ID")
    status: str = Field(description="New order status (should be 'cancelled')")
