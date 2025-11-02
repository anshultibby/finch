"""
Main ChatAgent class - refactored to use BaseAgent
"""
from typing import List, Dict, Any, Optional, AsyncGenerator
from datetime import datetime

from config import Config
from modules.snaptrade_tools import snaptrade_tools
from modules.tools import tool_registry
from .context import AgentContext
from models.sse import (
    SSEEvent,
    ToolCallStartEvent,
    ToolCallCompleteEvent,
    ThinkingEvent,
    AssistantMessageEvent,
    DoneEvent,
    ErrorEvent
)

from .prompts import (
    FINCH_SYSTEM_PROMPT,
    AUTH_STATUS_CONNECTED,
    AUTH_STATUS_NOT_CONNECTED
)
from .base_agent import BaseAgent
from .llm_config import LLMConfig
from .message_processor import (
    clean_incomplete_tool_calls,
    reconstruct_message_for_api,
    track_pending_tool_calls
)

# Import tool_definitions to register all tools
import modules.tool_definitions  # This will auto-register all tools


class ChatAgent(BaseAgent):
    """
    Main user-facing chat agent.
    Inherits from BaseAgent and provides SSE streaming for frontend.
    """
    
    def get_model(self) -> str:
        """Use configured OpenAI model"""
        return Config.OPENAI_MODEL
    
    def get_tool_names(self) -> Optional[List[str]]:
        """
        Main agent uses high-level tools and delegates to specialized agents.
        Individual FMP tools are excluded - use analyze_financials instead.
        """
        return [
            # Portfolio tools
            'get_portfolio',
            'request_brokerage_connection',
            
            # Reddit sentiment
            'get_reddit_trending_stocks',
            'get_reddit_ticker_sentiment',
            'compare_reddit_sentiment',
            
            # Financial analysis (delegated to FMP agent)
            # Note: get_fmp_data (universal FMP tool including insider trading)
            # is NOT included here - main agent delegates via analyze_financials instead
            'analyze_financials',
            
            # Visualization (delegated to plotting agent)
            'create_plot'
        ]
    
    def get_system_prompt(self, user_id: Optional[str] = None, **kwargs) -> str:
        """
        Build system prompt with auth status
        
        Args:
            user_id: Used to check auth status
        """
        # Check connection status
        has_connection = snaptrade_tools.has_active_connection(user_id) if user_id else False
        
        # Build system prompt
        system_prompt = FINCH_SYSTEM_PROMPT
        system_prompt += AUTH_STATUS_CONNECTED if has_connection else AUTH_STATUS_NOT_CONNECTED
        
        # Add tool descriptions
        tool_descriptions = tool_registry.get_tool_descriptions_for_prompt()
        system_prompt += f"\n\n{tool_descriptions}"
        
        return system_prompt
    
    async def process_message_stream(
        self,
        message: str,
        chat_history: List[Dict[str, Any]],
        agent_context: AgentContext  # Always required
    ) -> AsyncGenerator[SSEEvent, None]:
        """
        Stream chat responses using BaseAgent with SSE callbacks
        
        Args:
            message: User message
            chat_history: Previous messages
            agent_context: AgentContext with user_id, chat_id, resource_manager
        """
        needs_auth = [False]  # Mutable to capture in closures
        
        try:
            print(f"\n{'='*80}", flush=True)
            print(f"📨 STREAMING MESSAGE for user: {agent_context.user_id}", flush=True)
            print(f"📨 Current message: {message}", flush=True)
            print(f"{'='*80}\n", flush=True)
            
            # Build initial messages
            initial_messages = self._build_messages_for_api(
                message, chat_history, agent_context
            )
            
            # Define SSE callbacks
            async def on_content_delta(delta: str):
                """Yield SSE event for text delta"""
                yield SSEEvent(
                    event="assistant_message_delta",
                    data={"delta": delta}
                )
            
            async def on_tool_call_start(info: Dict[str, Any]):
                """Yield SSE event for tool call start"""
                yield SSEEvent(
                    event="tool_call_start",
                    data=ToolCallStartEvent(
                        tool_call_id=info["tool_call_id"],
                        tool_name=info["tool_name"],
                        arguments=info["arguments"],
                        timestamp=datetime.now().isoformat()
                    ).model_dump()
                )
            
            async def on_tool_call_complete(info: Dict[str, Any]):
                """Yield SSE event for tool call complete"""
                result = info["result"]
                if result.get("needs_auth"):
                    needs_auth[0] = True
                
                yield SSEEvent(
                    event="tool_call_complete",
                    data=ToolCallCompleteEvent(
                        tool_call_id=info["tool_call_id"],
                        tool_name=info["tool_name"],
                        status="completed",
                        timestamp=datetime.now().isoformat()
                    ).model_dump()
                )
            
            async def on_thinking():
                """Yield SSE event for thinking indicator"""
                yield SSEEvent(
                    event="thinking",
                    data=ThinkingEvent(message="Analyzing results...").model_dump()
                )
            
            # Create LLM configuration
            llm_config = LLMConfig.from_config(stream=True)
            
            # Use BaseAgent's streaming loop
            async for event in self.run_tool_loop_streaming(
                initial_messages=initial_messages,
                context=agent_context,
                max_iterations=10,
                llm_config=llm_config,
                on_content_delta=on_content_delta,
                on_tool_call_start=on_tool_call_start,
                on_tool_call_complete=on_tool_call_complete,
                on_thinking=on_thinking
            ):
                # Forward all events from BaseAgent
                yield event
            
            # Yield final assistant message (after streaming completes)
            new_messages = self.get_new_messages()
            if new_messages:
                last_message = new_messages[-1]
                if last_message.get("role") == "assistant":
                    content = last_message.get("content", "")
                    yield SSEEvent(
                        event="assistant_message",
                        data=AssistantMessageEvent(
                            content=content,
                            timestamp=datetime.now().isoformat(),
                            needs_auth=needs_auth[0]
                        ).model_dump()
                    )
            
            # Done
            yield SSEEvent(
                event="done",
                data=DoneEvent().model_dump()
            )
            
        except Exception as e:
            print(f"❌ Error: {str(e)}", flush=True)
            import traceback
            print(f"❌ Traceback: {traceback.format_exc()}", flush=True)
            
            yield SSEEvent(
                event="error",
                data=ErrorEvent(error=str(e), details=traceback.format_exc()).model_dump()
            )
    
    def _build_messages_for_api(
        self,
        message: str,
        chat_history: List[Dict[str, Any]],
        agent_context: AgentContext
    ) -> List[Dict[str, Any]]:
        """Build message list for LLM API"""
        # Use BaseAgent's build_messages with system prompt
        messages = self.build_messages(
            user_message=message,
            chat_history=chat_history,
            user_id=agent_context.user_id,  # Passed to get_system_prompt
            resource_manager=agent_context.resource_manager  # Passed for resource section
        )
        
        # Clean incomplete tool calls from history
        pending = track_pending_tool_calls(messages)
        if pending:
            messages = clean_incomplete_tool_calls(messages, pending)
        
        return messages

