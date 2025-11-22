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
from .sse import (
    SSEEvent,
    ToolCallStartEvent,
    ToolCallCompleteEvent,
    ThinkingEvent,
    AssistantMessageEvent,
    DoneEvent,
    ErrorEvent,
    OptionButton,
    OptionsEvent,
    ToolStatusEvent,
    ToolProgressEvent,
    ToolLogEvent,
    LLMStartEvent,
    LLMEndEvent,
    ToolsEndEvent
)
from .chat_history import (
    ChatHistory,
    ChatMessage as HistoryChatMessage,
    ToolCall,
    ChatTurn
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
    "ToolCallInfo",
    "SSEEvent",
    "ToolCallStartEvent",
    "ToolCallCompleteEvent",
    "ThinkingEvent",
    "AssistantMessageEvent",
    "DoneEvent",
    "ErrorEvent",
    "OptionButton",
    "OptionsEvent",
    "ToolStatusEvent",
    "ToolProgressEvent",
    "ToolLogEvent",
    "LLMStartEvent",
    "LLMEndEvent",
    "ToolsEndEvent",
    "ChatHistory",
    "HistoryChatMessage",
    "ToolCall",
    "ChatTurn"
]

