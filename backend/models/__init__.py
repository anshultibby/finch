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
    MessageEndEvent,
    DoneEvent,
    ErrorEvent,
    OptionButton,
    OptionsEvent,
    ToolStatusEvent,
    ToolProgressEvent,
    ToolLogEvent,
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
from .strategies import (
    StrategyConfig,
    StrategyStats,
    RiskLimits,
    ExecutionData,
    ExecutionAction,
    CreateStrategyRequest,
    UpdateStrategyRequest,
    StrategyResponse,
    StrategyDetailResponse,
    ExecutionResponse,
    ExecutionDetailResponse,
    RunStrategyRequest,
    RunStrategyResponse,
    StrategyInfoForLLM,
)
from .skills import (
    SkillRequest,
    SkillResponse,
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
    "ResourceResponse",
    "ResourceMetadata",
    "ToolCallStatus",
    "ToolCallInfo",
    "SSEEvent",
    "ToolCallStartEvent",
    "ToolCallCompleteEvent",
    "ThinkingEvent",
    "MessageEndEvent",
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
    "FileContent",
    "ChatHistory",
    "HistoryChatMessage",
    "ToolCall",
    "SaveApiKeyRequest",
    "ApiKeyInfo",
    "ApiKeysResponse",
    "ApiKeyResponse",
    "TestApiKeyRequest",
    "TestApiKeyResponse",
    # Strategies
    "StrategyConfig",
    "StrategyStats",
    "RiskLimits",
    "ExecutionData",
    "ExecutionAction",
    "CreateStrategyRequest",
    "UpdateStrategyRequest",
    "StrategyResponse",
    "StrategyDetailResponse",
    "ExecutionResponse",
    "ExecutionDetailResponse",
    "RunStrategyRequest",
    "RunStrategyResponse",
    "StrategyInfoForLLM",
    # Skills
    "SkillRequest",
    "SkillResponse",
]

