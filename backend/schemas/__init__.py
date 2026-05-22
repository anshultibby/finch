"""
Pydantic request/response schemas for the Finch API.

ORM models live in models/. This package contains only Pydantic schemas.
"""
from .chat import ChatMessage
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
from .resource import (
    ResourceResponse,
    ResourceMetadata,
    ToolCallStatus,
    ToolCallInfo
)
from .sse import (
    SSEEvent,
    ThinkingEvent,
    MessageEndEvent,
    DoneEvent,
    ErrorEvent,
    LLMStartEvent,
    LLMEndEvent,
    ToolsEndEvent,
    FileContent
)
from .chat_history import (
    ChatHistory,
    ChatMessage as HistoryChatMessage,
    ToolCall,
)
from .api_keys import (
    SaveApiKeyRequest,
    ApiKeyInfo,
    ApiKeysResponse,
    ApiKeyResponse,
    TestApiKeyRequest,
    TestApiKeyResponse,
)
