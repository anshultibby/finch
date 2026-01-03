"""
LLM Handler - Clean LLM API interaction with optional logging

Wraps litellm's acompletion to add:
- OpenTelemetry tracing for performance monitoring
- Optional debug logging (via DebugLogger)
- Optional chat logging (via ChatLogger)
- Streaming support with response accumulation
- Session-level usage tracking with cost calculation
"""
from typing import Dict, Any, Optional, AsyncGenerator
from pydantic import BaseModel, Field
from litellm import acompletion
import time
import json
from datetime import datetime
from pathlib import Path

from config import Config
from utils.logger import get_logger
from utils.tracing import get_tracer, add_span_attributes, add_span_event, record_exception
from .chat_logger import ChatLogger, get_chat_log_dir

logger = get_logger(__name__)
tracer = get_tracer(__name__)


# Pricing per million tokens (as of Dec 2024)
# Format: {model_prefix: {"input": price, "output": price, "cache_read": price, "cache_write": price}}
MODEL_PRICING = {
    # Claude 4 models (Sonnet 4.5 and Opus 4.5)
    "claude-sonnet-4-5": {"input": 3.0, "output": 15.0, "cache_read": 0.30, "cache_write": 3.75},
    "claude-opus-4-5": {"input": 15.0, "output": 75.0, "cache_read": 1.50, "cache_write": 18.75},
    # Claude 4 models (Sonnet 4 and Opus 4)
    "claude-sonnet-4": {"input": 3.0, "output": 15.0, "cache_read": 0.30, "cache_write": 3.75},
    "claude-opus-4": {"input": 15.0, "output": 75.0, "cache_read": 1.50, "cache_write": 18.75},
    # Claude 3.5 models
    "claude-3-5-sonnet": {"input": 3.0, "output": 15.0, "cache_read": 0.30, "cache_write": 3.75},
    "claude-3-5-haiku": {"input": 0.80, "output": 4.0, "cache_read": 0.08, "cache_write": 1.0},
    "claude-3-opus": {"input": 15.0, "output": 75.0, "cache_read": 1.50, "cache_write": 18.75},
    # OpenAI models
    "gpt-4o": {"input": 2.50, "output": 10.0, "cache_read": 1.25, "cache_write": 2.50},
    "gpt-4o-mini": {"input": 0.15, "output": 0.60, "cache_read": 0.075, "cache_write": 0.15},
    "o1": {"input": 15.0, "output": 60.0, "cache_read": 7.50, "cache_write": 15.0},
    "o3-mini": {"input": 1.10, "output": 4.40, "cache_read": 0.55, "cache_write": 1.10},
    "gpt-5": {"input": 2.0, "output": 8.0, "cache_read": 1.0, "cache_write": 2.0},  # Estimated
}


def _get_model_pricing(model: str) -> Dict[str, float]:
    """Get pricing for a model by matching prefix."""
    model_lower = model.lower()
    for prefix, pricing in MODEL_PRICING.items():
        if model_lower.startswith(prefix):
            return pricing
    # Default fallback pricing
    return {"input": 3.0, "output": 15.0, "cache_read": 0.30, "cache_write": 3.75}


class UsageStats(BaseModel):
    """Token usage statistics for a single LLM call."""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    cache_read_tokens: int = 0
    cache_creation_tokens: int = 0
    
    @property
    def uncached_input_tokens(self) -> int:
        """Input tokens that were NOT from cache."""
        return self.prompt_tokens - self.cache_read_tokens


class UsageTracker(BaseModel):
    """
    Tracks cumulative token usage across multiple LLM calls in a session.
    
    Calculates costs based on model pricing at the end of the session.
    """
    model: str = ""
    total_prompt_tokens: int = 0
    total_completion_tokens: int = 0
    total_cache_read_tokens: int = 0
    total_cache_creation_tokens: int = 0
    llm_call_count: int = 0
    
    def add_usage(self, usage_info: Any):
        """Add usage from an LLM response to cumulative totals."""
        if not usage_info:
            return
        
        self.llm_call_count += 1
        self.total_prompt_tokens += getattr(usage_info, 'prompt_tokens', 0)
        self.total_completion_tokens += getattr(usage_info, 'completion_tokens', 0)
        self.total_cache_read_tokens += getattr(usage_info, 'cache_read_input_tokens', 0)
        self.total_cache_creation_tokens += getattr(usage_info, 'cache_creation_input_tokens', 0)
    
    @property
    def uncached_input_tokens(self) -> int:
        """Total input tokens that were NOT from cache."""
        return self.total_prompt_tokens - self.total_cache_read_tokens
    
    def calculate_cost(self) -> Dict[str, float]:
        """
        Calculate the total cost based on token usage and model pricing.
        
        Returns dict with breakdown:
        - input_cost: Cost of uncached input tokens
        - cache_read_cost: Cost of cached input tokens (90% cheaper)
        - cache_write_cost: Cost of cache creation tokens (25% more expensive)
        - output_cost: Cost of completion tokens
        - total_cost: Sum of all costs
        - savings: How much was saved by caching
        """
        pricing = _get_model_pricing(self.model)
        
        # Calculate costs (pricing is per million tokens)
        uncached_input = self.uncached_input_tokens
        
        input_cost = (uncached_input / 1_000_000) * pricing["input"]
        cache_read_cost = (self.total_cache_read_tokens / 1_000_000) * pricing["cache_read"]
        cache_write_cost = (self.total_cache_creation_tokens / 1_000_000) * pricing["cache_write"]
        output_cost = (self.total_completion_tokens / 1_000_000) * pricing["output"]
        
        total_cost = input_cost + cache_read_cost + cache_write_cost + output_cost
        
        # Calculate savings (what it would have cost without caching)
        cost_without_cache = (self.total_prompt_tokens / 1_000_000) * pricing["input"]
        actual_input_cost = input_cost + cache_read_cost
        savings = cost_without_cache - actual_input_cost
        
        return {
            "input_cost": input_cost,
            "cache_read_cost": cache_read_cost,
            "cache_write_cost": cache_write_cost,
            "output_cost": output_cost,
            "total_cost": total_cost,
            "savings": savings
        }
    
    def log_summary(self):
        """Log a summary of the session's token usage and costs."""
        if self.llm_call_count == 0:
            return
        
        costs = self.calculate_cost()
        
        logger.info("=" * 60)
        logger.info("📊 SESSION USAGE SUMMARY")
        logger.info("=" * 60)
        logger.info(f"  Model: {self.model}")
        logger.info(f"  LLM Calls: {self.llm_call_count}")
        logger.info("-" * 40)
        logger.info("  TOKEN BREAKDOWN:")
        logger.info(f"    📥 Total Input: {self.total_prompt_tokens:,} tokens")
        logger.info(f"       ├─ Uncached: {self.uncached_input_tokens:,}")
        logger.info(f"       └─ From Cache: {self.total_cache_read_tokens:,}")
        logger.info(f"    📤 Output: {self.total_completion_tokens:,} tokens")
        logger.info(f"    ✏️  Cache Written: {self.total_cache_creation_tokens:,} tokens")
        logger.info("-" * 40)
        logger.info("  COST BREAKDOWN:")
        logger.info(f"    Input (uncached): ${costs['input_cost']:.4f}")
        logger.info(f"    Cache reads:      ${costs['cache_read_cost']:.4f}")
        logger.info(f"    Cache writes:     ${costs['cache_write_cost']:.4f}")
        logger.info(f"    Output:           ${costs['output_cost']:.4f}")
        logger.info("-" * 40)
        logger.info(f"  💰 TOTAL COST: ${costs['total_cost']:.4f}")
        if costs['savings'] > 0:
            logger.info(f"  💚 CACHE SAVINGS: ${costs['savings']:.4f}")
        logger.info("=" * 60)


# Token breakdown removed - we now rely only on actual API response data


class LLMHandler:
    """
    Clean LLM API handler with separated logging concerns.
    
    Responsibilities:
    - LLM API calls (via litellm)
    - Streaming support
    - OpenTelemetry tracing
    - Session-level usage tracking with cost calculation
    - Delegates logging to ChatLogger and DebugLogger
    """
    
    # Class-level storage for usage trackers by chat_id
    # This allows tracking across multiple LLMHandler instances in the same session
    _usage_trackers: Dict[str, UsageTracker] = {}
    
    def __init__(self, user_id: Optional[str] = None, chat_id: Optional[str] = None):
        """
        Initialize LLM handler.
        
        Args:
            user_id: User ID for organizing logs
            chat_id: Chat ID for organizing chat logs
        """
        self.user_id = user_id or "unknown"
        self.chat_id = chat_id or "unknown"
        
        # Initialize chat logger based on config
        backend_dir = Path(__file__).parent.parent.parent
        
        # Single logging system: ChatLogger (conversation tracking with full context)
        # Only create when DEBUG_CHAT_LOGS is enabled
        if Config.DEBUG_CHAT_LOGS:
            chat_log_dir = get_chat_log_dir(self.chat_id, backend_dir)
            # Don't create directory yet - ChatLogger will create it when logging first turn
            self.chat_logger = ChatLogger(self.user_id, self.chat_id, chat_log_dir)
            logger.info(f"Chat logging enabled: {chat_log_dir}")
        else:
            self.chat_logger = None
    
    def _get_usage_tracker(self, model: str) -> UsageTracker:
        """Get or create a usage tracker for this chat session."""
        if self.chat_id not in LLMHandler._usage_trackers:
            LLMHandler._usage_trackers[self.chat_id] = UsageTracker(model=model)
        tracker = LLMHandler._usage_trackers[self.chat_id]
        # Update model in case it changed
        tracker.model = model
        return tracker
    
    @classmethod
    def finalize_session(cls, chat_id: str):
        """
        Finalize a chat session - log usage summary and clean up.
        
        Call this at the end of a chat turn to get the cost summary.
        """
        if chat_id in cls._usage_trackers:
            tracker = cls._usage_trackers[chat_id]
            tracker.log_summary()
            del cls._usage_trackers[chat_id]
    
    @classmethod
    def get_session_usage(cls, chat_id: str) -> Optional[UsageTracker]:
        """Get the current usage tracker for a session (if any)."""
        return cls._usage_trackers.get(chat_id)
    
    async def acompletion(self, **kwargs) -> Any:
        """
        Call LiteLLM's acompletion with tracing and logging.
        
        Args:
            **kwargs: All arguments passed to litellm.acompletion
            
        Returns:
            LiteLLM completion response (streaming or non-streaming)
        """
        # Extract metadata
        model = kwargs.get("model", "unknown")
        is_streaming = kwargs.get("stream", False)
        message_count = len(kwargs.get("messages", []))
        
        # Start tracing
        with tracer.start_as_current_span(f"llm.call") as span:
            add_span_attributes({
                "llm.model": model,
                "llm.streaming": is_streaming,
                "llm.message_count": message_count,
                "user.id": self.user_id,
                "chat.id": self.chat_id
            })
            
            # Timestamp for logging
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            try:
                # Make LLM call
                response = await acompletion(**kwargs)
                
                # Handle streaming vs non-streaming
                if is_streaming:
                    return self._handle_streaming(response, kwargs, timestamp)
                else:
                    return self._handle_non_streaming(response, kwargs, timestamp)
                    
            except Exception as e:
                record_exception(e)
                logger.error(f"LLM call failed: {e}")
                raise
    
    def _handle_non_streaming(self, response: Any, kwargs: Dict[str, Any], timestamp: str) -> Any:
        """Handle non-streaming response with logging"""
        # Chat log (if enabled)
        if self.chat_logger and hasattr(response, "choices") and response.choices:
            self._log_chat_turn_non_streaming(kwargs, response)
        
        return response
    
    async def _handle_streaming(self, stream: AsyncGenerator, kwargs: Dict[str, Any], timestamp: str) -> AsyncGenerator:
        """Handle streaming response with accumulation and logging"""
        start_time = time.time()
        first_chunk_time = None
        chunk_count = 0
        
        # Accumulate for logging (only accumulate response data, not raw chunks)
        accumulated_response = {
            "content": "",
            "reasoning_content": "",
            "tool_calls": {},
            "finish_reason": None
        }
        usage_info = None
        chunk_buffer = []  # Buffer last chunks for debug logging
        
        async for chunk in stream:
            chunk_count += 1
            chunk_buffer.append(chunk)
            if len(chunk_buffer) > 5:
                chunk_buffer.pop(0)  # Keep only last 5 chunks
            
            # Track TTFB
            if first_chunk_time is None:
                first_chunk_time = time.time()
                ttfb_ms = (first_chunk_time - start_time) * 1000
                add_span_event("First chunk received", {"ttfb_ms": ttfb_ms})
                logger.info(f"⏱️  TTFB: {ttfb_ms:.0f}ms (time to first token)")
            
            
            # Capture usage info (comes in final chunk for Claude)
            if hasattr(chunk, 'usage') and chunk.usage:
                usage_info = chunk.usage
            
            # Yield immediately for real-time streaming
            yield chunk
            
            # Accumulate for logging (extract data, don't store raw chunks)
            if self.chat_logger:
                self._accumulate_chunk(chunk, accumulated_response)
        
        # After stream completes, do logging
        duration_ms = (time.time() - start_time) * 1000
        add_span_attributes({
            "llm.duration_ms": duration_ms,
            "llm.chunk_count": chunk_count
        })
        
        # Extract usage from last chunk if not already captured
        if not usage_info and chunk_buffer:
            last_chunk = chunk_buffer[-1]
            if hasattr(last_chunk, 'usage') and last_chunk.usage:
                usage_info = last_chunk.usage
        
        # Log usage stats
        model = kwargs.get("model", "unknown")
        if usage_info:
            self._log_usage_stats(usage_info, duration_ms, first_chunk_time, start_time, model=model)
        
        # Chat logging
        if self.chat_logger:
            self._log_chat_turn_streaming(kwargs, accumulated_response, usage_info)
        
        logger.info(f"✅ LLM stream completed in {duration_ms/1000:.1f}s ({chunk_count} chunks)")
    
    def _accumulate_chunk(self, chunk: Any, accumulated: Dict[str, Any]):
        """Accumulate streaming chunk into response dict"""
        if not hasattr(chunk, "choices") or not chunk.choices:
            return
        
        choice = chunk.choices[0]
        delta = choice.delta
        
        # Accumulate content
        if hasattr(delta, "content") and delta.content:
            accumulated["content"] += delta.content
        
        # Accumulate reasoning (o1/o3 models)
        if hasattr(delta, "reasoning_content") and delta.reasoning_content:
            accumulated["reasoning_content"] += delta.reasoning_content
        
        # Accumulate tool calls
        if hasattr(delta, "tool_calls") and delta.tool_calls:
            for tc_delta in delta.tool_calls:
                idx = tc_delta.index
                if idx not in accumulated["tool_calls"]:
                    accumulated["tool_calls"][idx] = {
                        "id": "",
                        "type": "function",
                        "function": {"name": "", "arguments": ""}
                    }
                
                if tc_delta.id:
                    accumulated["tool_calls"][idx]["id"] = tc_delta.id
                
                if hasattr(tc_delta, "function") and tc_delta.function:
                    if hasattr(tc_delta.function, "name") and tc_delta.function.name:
                        accumulated["tool_calls"][idx]["function"]["name"] = tc_delta.function.name
                    if hasattr(tc_delta.function, "arguments") and tc_delta.function.arguments:
                        accumulated["tool_calls"][idx]["function"]["arguments"] += tc_delta.function.arguments
        
        # Capture finish reason
        if hasattr(choice, "finish_reason") and choice.finish_reason:
            accumulated["finish_reason"] = choice.finish_reason
    
    def _log_usage_stats(self, usage_info: Any, duration_ms: float = 0, first_chunk_time: float = None, start_time: float = None, model: str = "unknown"):
        """Log token usage and cache statistics, and add to session tracker."""
        prompt_tokens = getattr(usage_info, 'prompt_tokens', 0)
        completion_tokens = getattr(usage_info, 'completion_tokens', 0)
        cache_creation = getattr(usage_info, 'cache_creation_input_tokens', 0)
        cache_read = getattr(usage_info, 'cache_read_input_tokens', 0)
        
        # Add to session usage tracker
        tracker = self._get_usage_tracker(model)
        tracker.add_usage(usage_info)
        
        add_span_attributes({
            "llm.tokens.prompt": prompt_tokens,
            "llm.tokens.completion": completion_tokens,
            "llm.tokens.total": prompt_tokens + completion_tokens
        })
        
        # Calculate generation speed
        if completion_tokens > 0 and first_chunk_time and start_time:
            generation_time_ms = (time.time() - first_chunk_time) * 1000
            if generation_time_ms > 0:
                tokens_per_sec = completion_tokens / (generation_time_ms / 1000)
                logger.info(f"🚀 Generation speed: {tokens_per_sec:.0f} tokens/sec ({completion_tokens} tokens in {generation_time_ms/1000:.1f}s)")
        
        if cache_creation > 0 or cache_read > 0:
            add_span_attributes({
                "llm.cache.creation_tokens": cache_creation,
                "llm.cache.read_tokens": cache_read
            })
            
            # Calculate cache metrics
            # Note: prompt_tokens already includes cache_read tokens according to Anthropic API
            total_input_tokens = prompt_tokens  # This is the total
            new_input_tokens = prompt_tokens - cache_read  # Actually new/uncached
            cache_percentage = (cache_read / total_input_tokens * 100) if total_input_tokens > 0 else 0
            
            # Calculate actual cost savings (cache reads cost 10% of normal)
            cost_without_cache = total_input_tokens * 1.0
            cost_with_cache = new_input_tokens * 1.0 + cache_read * 0.1
            cost_savings_pct = ((cost_without_cache - cost_with_cache) / cost_without_cache * 100) if cost_without_cache > 0 else 0
            
            logger.info(f"💾 CACHE STATS:")
            logger.info(f"  📥 New input tokens: {new_input_tokens:,} (uncached)")
            logger.info(f"  📖 Cache read: {cache_read:,} tokens ({cache_percentage:.1f}% of total)")
            logger.info(f"  📊 Total input: {total_input_tokens:,} tokens")
            logger.info(f"  📤 Output tokens: {completion_tokens:,} (generated)")
            logger.info(f"  ✏️  Cache write: {cache_creation:,} tokens")
            logger.info(f"  💰 Cost savings: {cost_savings_pct:.1f}% (cache reads are 90% cheaper)")
            
            # Log cache growth
            if cache_creation > 0:
                logger.info(f"  📈 Cache grew by {cache_creation:,} tokens this turn")
            
            # Explain why new_input != cache_creation (helpful for understanding)
            if new_input_tokens > cache_creation:
                uncached_sent = new_input_tokens - cache_creation
                logger.debug(f"  ℹ️  {uncached_sent:,} new tokens sent but not cached (no cache_control breakpoint)")
    
    def _log_chat_turn_non_streaming(self, kwargs: Dict[str, Any], response: Any):
        """Log non-streaming chat turn"""
        if not self.chat_logger:
            return
        
        # Build assistant response
        message = response.choices[0].message
        assistant_response = {
            "role": "assistant",
            "content": message.content or ""
        }
        
        # Add tool calls if present
        if hasattr(message, "tool_calls") and message.tool_calls:
            assistant_response["tool_calls"] = [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments
                    }
                }
                for tc in message.tool_calls
            ]
        
        # Build full conversation including this response
        messages = kwargs.get("messages", []) + [assistant_response]
        
        # Build usage data with cache stats
        usage_data = self._build_usage_data(response.usage) if hasattr(response, 'usage') else None
        
        # Save current conversation state
        self.chat_logger.log_conversation(
            messages=messages,
            usage_data=usage_data,
            model=kwargs.get("model", "unknown"),
            system_prompt=kwargs.get("system"),  # Claude format
            tools=kwargs.get("tools")  # Tool schemas
        )
    
    def _log_chat_turn_streaming(self, kwargs: Dict[str, Any], accumulated: Dict[str, Any], usage_info: Any):
        """Log streaming chat turn"""
        if not self.chat_logger:
            return
        
        # Build assistant response from accumulated streaming data
        assistant_response = {
            "role": "assistant",
            "content": accumulated["content"]
        }
        
        if accumulated["reasoning_content"]:
            assistant_response["reasoning_content"] = accumulated["reasoning_content"]
        
        # Convert tool_calls dict to list
        tool_calls_list = [
            tc for tc in accumulated["tool_calls"].values()
            if tc.get("id")
        ]
        if tool_calls_list:
            assistant_response["tool_calls"] = tool_calls_list
        
        # Build full conversation including this response
        messages = kwargs.get("messages", []) + [assistant_response]
        
        # Build usage data with cache stats
        usage_data = self._build_usage_data(usage_info) if usage_info else None
        
        # Save current conversation state
        self.chat_logger.log_conversation(
            messages=messages,
            usage_data=usage_data,
            model=kwargs.get("model", "unknown"),
            system_prompt=kwargs.get("system"),  # Claude format
            tools=kwargs.get("tools")  # Tool schemas
        )
    
    @staticmethod
    def _build_usage_data(usage_info: Any) -> Dict[str, Any]:
        """Build usage data dict from usage info"""
        usage_data = {
            "prompt_tokens": getattr(usage_info, 'prompt_tokens', 0),
            "completion_tokens": getattr(usage_info, 'completion_tokens', 0),
            "total_tokens": getattr(usage_info, 'total_tokens', 0)
        }
        
        # Add cache statistics (Claude)
        cache_creation = getattr(usage_info, 'cache_creation_input_tokens', 0)
        cache_read = getattr(usage_info, 'cache_read_input_tokens', 0)
        
        if cache_creation > 0 or cache_read > 0:
            usage_data["cache"] = {
                "creation_tokens": cache_creation,
                "read_tokens": cache_read,
                "cache_hit": cache_read > 0,
                "savings_estimate": f"~90% on {cache_read:,} tokens" if cache_read > 0 else None
            }
        
        return usage_data
