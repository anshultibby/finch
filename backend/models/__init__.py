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
    "Portfolio"
]

