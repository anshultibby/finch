"""
Agent-specific tracing utilities - clean abstractions for instrumentation

This separates instrumentation from business logic, making the core agent loop cleaner.
"""
from typing import Dict, Any, Optional, List
from contextlib import asynccontextmanager
import time
from utils.tracing import get_tracer, add_span_attributes, add_span_event, record_exception
from utils.logger import get_logger

logger = get_logger(__name__)
tracer = get_tracer(__name__)


class AgentTracer:
    """
    Clean tracing abstraction for agent operations.
    
    Usage:
        tracer = AgentTracer(agent_name="ChatAgent", user_id=user_id, chat_id=chat_id)
        
        with tracer.interaction(max_iterations=10):
            for turn in range(1, max_iterations):
                with tracer.turn(turn, message_count=len(messages)):
                    # Do work
                    tracer.record_tool_calls(tool_calls)
    """
    
    def __init__(self, agent_name: str, user_id: str, chat_id: Optional[str] = None, model: str = "gpt-4"):
        self.agent_name = agent_name
        self.user_id = user_id
        self.chat_id = chat_id
        self.model = model
        self._turn_start_time = None
    
    @asynccontextmanager
    async def interaction(self, max_iterations: int):
        """Trace an entire agent interaction (all turns)"""
        with tracer.start_as_current_span(f"agent.{self.agent_name}.interaction"):
            add_span_attributes({
                "agent.name": self.agent_name,
                "agent.model": self.model,
                "agent.max_iterations": max_iterations,
                "user.id": self.user_id,
                "chat.id": self.chat_id or "unknown"
            })
            try:
                yield
                # Mark as completed if no exception
                add_span_attributes({"agent.completed": True})
            except Exception as e:
                add_span_attributes({
                    "agent.error": True,
                    "agent.error_message": str(e)
                })
                record_exception(e)
                raise
    
    @asynccontextmanager
    async def turn(self, turn_number: int, message_count: int):
        """Trace a single agent turn (one LLM call + tool execution cycle)"""
        with tracer.start_as_current_span(f"agent.turn.{turn_number}"):
            self._turn_start_time = time.time()
            
            add_span_attributes({
                "agent.turn": turn_number,
                "agent.message_count": message_count
            })
            add_span_event(f"Turn {turn_number} started", {
                "message_count": message_count
            })
            
            try:
                yield
            finally:
                if self._turn_start_time:
                    duration_ms = (time.time() - self._turn_start_time) * 1000
                    add_span_attributes({"agent.turn_duration_ms": duration_ms})
                    add_span_event(f"Turn {turn_number} completed", {
                        "duration_ms": duration_ms
                    })
    
    def record_tools_available(self, tool_count: int):
        """Record how many tools are available"""
        add_span_attributes({"agent.tool_count": tool_count})
    
    def record_tool_calls_requested(self, tool_calls: List[Dict[str, Any]]):
        """Record that LLM requested tool calls"""
        add_span_attributes({
            "agent.tool_calls_requested": len(tool_calls)
        })
        add_span_event("Tool calls requested", {
            "tool_count": len(tool_calls),
            "tools": [tc["function"]["name"] for tc in tool_calls]
        })
    
    def record_final_turn(self, turn_number: int, content_length: int):
        """Record that this is the final turn (no more tool calls)"""
        if self._turn_start_time:
            duration_ms = (time.time() - self._turn_start_time) * 1000
            add_span_attributes({
                "agent.turn_duration_ms": duration_ms,
                "agent.final_turn": True,
                "agent.total_turns": turn_number,
                "agent.completed": True
            })
            add_span_event("Final turn completed (no tool calls)", {
                "duration_ms": duration_ms,
                "content_length": content_length
            })


@asynccontextmanager
async def trace_agent_interaction(
    agent_name: str,
    user_id: str,
    chat_id: Optional[str] = None,
    model: str = "gpt-4",
    max_iterations: int = 10
):
    """
    Simplified context manager for tracing agent interactions.
    
    Usage:
        async with trace_agent_interaction("ChatAgent", user_id, chat_id) as tracer:
            for turn in range(1, max_iterations):
                async with tracer.turn(turn, len(messages)):
                    # Do work
                    tracer.record_tool_calls(tool_calls)
    """
    agent_tracer = AgentTracer(agent_name, user_id, chat_id, model)
    async with agent_tracer.interaction(max_iterations):
        yield agent_tracer


class TracedAgentMixin:
    """
    Mixin that adds clean tracing to agent classes.
    
    Usage:
        class MyAgent(TracedAgentMixin, BaseAgent):
            def get_model(self) -> str:
                return "gpt-4"
    """
    
    def _create_tracer(self, user_id: str, chat_id: Optional[str] = None) -> AgentTracer:
        """Create a tracer for this agent instance"""
        agent_name = self.__class__.__name__
        model = self.get_model() if hasattr(self, 'get_model') else "unknown"
        return AgentTracer(agent_name, user_id, chat_id, model)

