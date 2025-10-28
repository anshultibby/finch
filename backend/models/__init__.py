"""
Pydantic models for Finch API
"""
from .chat import ChatMessage, ChatResponse, Message
from .snaptrade import (
    SnapTradeConnectionRequest,
    SnapTradeConnectionResponse,
    SnapTradeCallbackRequest,
    SnapTradeStatusResponse,
    SnapTradePositionResponse,
    SnapTradeAccountResponse,
    Position,
    Account,
    AggregatedHolding,
    Portfolio
)
from .apewisdom import (
    StockMention,
    RedditSentiment,
    TickerDetails,
    TrendingStocksResponse
)
from .insider_trading import (
    SenateTrade,
    HouseTrade,
    InsiderTrade,
    CongressionalActivity,
    InsiderTradingResponse
)
from .resource import (
    ResourceResponse,
    ResourceMetadata,
    ToolCallStatus,
    ToolCallInfo
)

__all__ = [
    "ChatMessage", 
    "ChatResponse", 
    "Message",
    "SnapTradeConnectionRequest",
    "SnapTradeConnectionResponse",
    "SnapTradeCallbackRequest",
    "SnapTradeStatusResponse",
    "Position",
    "Account",
    "AggregatedHolding",
    "Portfolio",
    "StockMention",
    "RedditSentiment",
    "TickerDetails",
    "TrendingStocksResponse",
    "SenateTrade",
    "HouseTrade",
    "InsiderTrade",
    "CongressionalActivity",
    "InsiderTradingResponse",
    "ResourceResponse",
    "ResourceMetadata",
    "ToolCallStatus",
    "ToolCallInfo"
]

