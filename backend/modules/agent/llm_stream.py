"""
Standalone LLM streaming functions - clean separation from agent logic
"""
from typing import List, Dict, Any, Optional, AsyncGenerator, Callable
from models.sse import SSEEvent, LLMStartEvent, LLMEndEvent, AssistantMessageDeltaEvent
from .llm_handler import LLMHandler
from .llm_config import LLMConfig
from utils.logger import get_logger

logger = get_logger(__name__)


async def stream_llm_response(
    messages: List[Dict[str, Any]],
    tools: List[Dict[str, Any]],
    llm_config: LLMConfig,
    user_id: str,
    on_content_delta: Optional[Callable[[str], AsyncGenerator[SSEEvent, None]]] = None
) -> AsyncGenerator[SSEEvent, None]:
    """
    Stream LLM response and yield SSE events.
    
    Args:
        messages: Messages to send to LLM
        tools: Available tools
        llm_config: LLM configuration
        user_id: User ID for logging
        on_content_delta: Optional callback for content deltas
        
    Yields:
        SSEEvent objects (llm_start, content deltas, llm_end)
    """
    # Emit start event
    yield SSEEvent(
        event="llm_start",
        data=LLMStartEvent(message_count=len(messages)).model_dump()
    )
    
    # Create LLM handler
    llm_handler = LLMHandler(user_id=user_id)
    
    # Build kwargs for LiteLLM
    llm_kwargs = llm_config.to_litellm_kwargs()
    llm_kwargs["messages"] = messages
    llm_kwargs["tools"] = tools if tools else None
    llm_kwargs["tool_choice"] = "auto" if tools else None
    llm_kwargs["stream"] = True
    if "stream_options" not in llm_kwargs:
        llm_kwargs["stream_options"] = {"include_usage": False}
    
    # Stream response
    stream_response = await llm_handler.acompletion(**llm_kwargs)
    
    # Accumulate response
    content = ""
    tool_calls = []
    reasoning_content = ""
    
    # Process stream
    async for chunk in stream_response:
        if not hasattr(chunk, 'choices') or not chunk.choices:
            continue
            
        delta = chunk.choices[0].delta
        
        # Handle reasoning content (o1/o3 models)
        if hasattr(delta, 'reasoning_content') and delta.reasoning_content:
            reasoning_content += delta.reasoning_content
            yield SSEEvent(
                event="assistant_message_delta",
                data=AssistantMessageDeltaEvent(delta=delta.reasoning_content).model_dump()
            )
            if on_content_delta:
                async for event in on_content_delta(delta.reasoning_content):
                    yield event
        
        # Handle regular content
        if hasattr(delta, 'content') and delta.content:
            content += delta.content
            yield SSEEvent(
                event="assistant_message_delta",
                data=AssistantMessageDeltaEvent(delta=delta.content).model_dump()
            )
            if on_content_delta:
                async for event in on_content_delta(delta.content):
                    yield event
        
        # Accumulate tool calls
        if hasattr(delta, 'tool_calls') and delta.tool_calls:
            for tc in delta.tool_calls:
                idx = tc.index
                while len(tool_calls) <= idx:
                    tool_calls.append({
                        "id": "",
                        "type": "function",
                        "function": {"name": "", "arguments": ""}
                    })
                if tc.id:
                    tool_calls[idx]["id"] = tc.id
                if hasattr(tc, 'function') and tc.function:
                    if tc.function.name:
                        tool_calls[idx]["function"]["name"] = tc.function.name
                    if tc.function.arguments:
                        tool_calls[idx]["function"]["arguments"] += tc.function.arguments
    
    # Emit end event
    yield SSEEvent(
        event="llm_end",
        data=LLMEndEvent(
            content=content,
            tool_calls=tool_calls
        ).model_dump()
    )

