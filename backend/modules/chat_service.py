"""
Chat service for managing chat sessions and interactions
"""
from typing import List, AsyncGenerator, Dict, Any
import os
import json
import asyncio
from datetime import datetime, timezone
from .agent.agent_config import create_agent
from .agent.llm_handler import LLMHandler
from core.config import Config
from .context_manager import context_manager
from core.database import get_db_session
from modules.agent.context import AgentContext, generate_agent_id, register_context, unregister_context
from schemas.chat_history import ChatHistory
from crud import chat_async
from utils.logger import get_logger
from utils.tracing import get_tracer
from modules.tools import tool_registry

logger = get_logger(__name__)
tracer = get_tracer(__name__)


class ChatService:
    """Service for handling chat operations"""
    
    def __init__(self):
        # Don't create a shared agent instance - create one per request
        # to avoid state conflicts with concurrent requests
        pass
    
    async def send_message_stream(
        self,
        message: str,
        chat_id: str,
        user_id: str,
        images: List[Dict[str, str]] = None,
        skill_ids: List[str] = None
    ) -> AsyncGenerator[str, None]:
        """
        Send a message and stream SSE events as they happen.
        
        Messages are saved INCREMENTALLY as they complete during streaming.
        This ensures that if the stream is interrupted (user sends new message),
        completed work is preserved in the database.
        
        Args:
            message: User message content
            chat_id: Chat identifier
            user_id: User identifier (for SnapTrade tools)
            images: Optional list of image attachments [{"data": base64, "media_type": "image/png"}]
            
        Yields:
            SSE formatted strings (event: <type>\\ndata: <json>\\n\\n)
        """
        # OpenTelemetry will automatically trace database and HTTP calls
        # We just add high-level spans for business logic
        with tracer.start_as_current_span("chat_turn"):
            logger.info(f"Starting chat turn for user {user_id}")
            
            # Create single DB session for entire request lifecycle
            # This prevents connection pool exhaustion by reusing one connection
            async with get_db_session() as db:
                # Mark chat as processing in database
                await chat_async.set_chat_processing(db, chat_id, is_processing=True)
                
                # Check if user has credits before processing
                from services.credits import CreditsService
                user_credits = await CreditsService.get_user_credits(db, user_id)
                
                if user_credits is not None and user_credits <= 0:
                    # User has no credits - send error and stop
                    from schemas.sse import SSEEvent
                    logger.warning(f"User {user_id} has insufficient credits: {user_credits}")
                    await chat_async.set_chat_processing(db, chat_id, is_processing=False)
                    yield SSEEvent(
                        event="error",
                        data={"error": "Insufficient credits. Please contact support to add more credits."}
                    ).to_sse_format()
                    yield SSEEvent(event="done", data={}).to_sse_format()
                    return

                # Check daily spend cap
                allowed, remaining_today = await CreditsService.check_daily_cap(db, user_id)
                if not allowed:
                    from schemas.sse import SSEEvent
                    logger.warning(f"User {user_id} hit daily credit cap")
                    await chat_async.set_chat_processing(db, chat_id, is_processing=False)
                    yield SSEEvent(
                        event="error",
                        data={"error": "Daily limit reached ($1/day). Resets at midnight UTC."}
                    ).to_sse_format()
                    yield SSEEvent(event="done", data={}).to_sse_format()
                    return
                
                # Send immediate acknowledgment so frontend knows connection is alive
                from schemas.sse import SSEEvent, ThinkingEvent
                yield SSEEvent(
                    event="thinking",
                    data=ThinkingEvent(message="Processing your message...").model_dump()
                ).to_sse_format()
                
                # STEP 1: Load history and save user message
                db_chat = await chat_async.get_chat(db, chat_id)
                if not db_chat:
                    await chat_async.create_chat(db, chat_id, user_id)
                
                # Load chat history using ChatHistory model
                db_messages = await chat_async.get_chat_messages(db, chat_id)
                
                # Clean up incomplete tool call sequences (Anthropic requirement)
                removed_count = await chat_async.cleanup_incomplete_tool_sequences(db, chat_id)
                if removed_count > 0:
                    logger.warning(f"Removed {removed_count} incomplete tool message(s) from history")
                    db_messages = await chat_async.get_chat_messages(db, chat_id)
                
                history = ChatHistory.from_db_messages(db_messages, chat_id, user_id)
                
                # Save user message FIRST before streaming (to both DB and conversation log)
                current_sequence = await chat_async.get_next_sequence(db, chat_id)
                await chat_async.create_message(
                    db=db,
                    chat_id=chat_id,
                    role="user",
                    content=message,
                    sequence=current_sequence
                )
                current_sequence += 1
                
                # Also log user message to conversation file for complete history
                if Config.DEBUG_CHAT_LOGS:
                    llm_handler = LLMHandler(user_id=user_id, chat_id=chat_id, agent_type="agent")
                    if llm_handler.chat_logger:
                        llm_handler.chat_logger.add_message({
                            "role": "user",
                            "content": message
                        })
            
                # STEP 2: Process message and save incrementally
                context = context_manager.get_all_context(user_id)
                
                # Create cancel event for this execution
                cancel_event = asyncio.Event()
                
                agent_context = AgentContext(
                    agent_id=generate_agent_id(),  # Unique ID for this master agent instance
                    user_id=user_id,
                    chat_id=chat_id,
                    skill_ids=skill_ids,
                    data=context,
                    cancel_event=cancel_event
                )
                
                # Register this context and cancel any previous active one
                previous_context = register_context(chat_id, agent_context)
                if previous_context is not None:
                    logger.info(f"🛑 Cancelling previous agent execution for chat {chat_id}")
                    previous_context.cancel()
                
                agent = await create_agent(agent_context, user_id=user_id, skill_ids=skill_ids)
                
                # Prepend current datetime so the LLM is always aware of the current time
                now = datetime.now(timezone.utc).strftime("%A, %B %d, %Y %H:%M UTC")
                message_with_datetime = f"[Current date/time: {now}]\n\n{message}"
                
                # Add user message to history (with optional images for multimodal)
                history.add_user_message(message_with_datetime, images=images)
                
                # Track pending assistant message (with tool calls) until tools_end arrives
                pending_assistant_msg = None
                
                # Stream events from agent and save completed messages immediately as they arrive.
                # Saving inside the loop (not after) means progress is persisted even if the
                # client disconnects mid-stream.
                with tracer.start_as_current_span("agent_processing"):
                    async for event in agent.process_message_stream(
                        message=message_with_datetime,
                        chat_history=history,
                        history_limit=Config.CHAT_HISTORY_LIMIT
                    ):
                        # YIELD EVENT FIRST for real-time streaming
                        yield event.to_sse_format()
                        
                        if event.event == "tool_call_start":
                            logger.info(f"🚀 Yielding tool_call_start event to client: {event.data}")
                        
                        if event.event == "message_end":
                            tool_calls = event.data.get("tool_calls")
                            content = event.data.get("content", "")
                            
                            if tool_calls:
                                # Hold the assistant message until tools_end so we can attach
                                # tool_results metadata to it in a single DB write.
                                logger.info(f"📝 message_end with {len(tool_calls)} tool calls - holding for tools_end")
                                pending_assistant_msg = {
                                    "content": content,
                                    "tool_calls": tool_calls
                                }
                            else:
                                # Final assistant message with no tool calls — save immediately.
                                try:
                                    seq = current_sequence
                                    current_sequence += 1
                                    await chat_async.create_message(
                                        db=db,
                                        chat_id=chat_id,
                                        role="assistant",
                                        content=content,
                                        sequence=seq
                                    )
                                    logger.info(f"💾 Saved final assistant message (seq={seq})")
                                except Exception as e:
                                    logger.error(f"Failed to save final assistant message: {e}")
                                    try:
                                        await db.rollback()
                                    except Exception:
                                        pass

                        elif event.event == "tools_end":
                            tool_messages = event.data.get("tool_messages", [])
                            execution_results = event.data.get("execution_results", [])
                            
                            logger.info(f"🔧 tools_end - pending_assistant_msg={'SET' if pending_assistant_msg else 'NONE'}, {len(tool_messages)} tool messages")
                            
                            if not pending_assistant_msg and tool_messages:
                                logger.error(f"🚨 BUG: tools_end has {len(tool_messages)} tool results but no pending_assistant_msg!")

                            # Storage-time hard cap: prevent oversized tool results
                            # from bloating the DB and consuming the entire context
                            # window on subsequent loads.
                            max_chars = Config.STORAGE_MAX_TOOL_RESULT_CHARS
                            for tm in tool_messages:
                                tc = tm.get("content", "")
                                if isinstance(tc, str) and len(tc) > max_chars:
                                    tm["content"] = tc[:max_chars] + f"\n... [truncated at {max_chars:,} chars, {len(tc):,} total]"
                            
                            if Config.DEBUG_CHAT_LOGS:
                                llm_handler = LLMHandler(user_id=user_id, chat_id=chat_id, agent_type="agent")
                                if llm_handler.chat_logger:
                                    llm_handler.log_tool_results(tool_messages)
                            
                            # Build tool_results dict keyed by tool_call_id
                            tool_results = {}
                            for exec_result in execution_results:
                                tool_call_id = exec_result.get("tool_call_id")
                                if tool_call_id:
                                    result_data = exec_result.get("result_data", {})
                                    tool_results[tool_call_id] = {
                                        "status": exec_result.get("status", "completed"),
                                        "error": exec_result.get("error"),
                                        "result_summary": result_data.get("message") if isinstance(result_data, dict) else None,
                                    }
                                    if isinstance(result_data, dict):
                                        stdout = result_data.get("stdout")
                                        stderr = result_data.get("stderr")
                                        if stdout is not None or stderr is not None:
                                            tool_results[tool_call_id]["code_output"] = {
                                                "stdout": stdout or "",
                                                "stderr": stderr or ""
                                            }
                            
                            # Save assistant message + tool results immediately
                            if pending_assistant_msg:
                                try:
                                    seq = current_sequence
                                    current_sequence += 1 + len(tool_messages)
                                    
                                    await chat_async.create_message(
                                        db=db,
                                        chat_id=chat_id,
                                        role="assistant",
                                        content=pending_assistant_msg["content"],
                                        sequence=seq,
                                        tool_calls=pending_assistant_msg["tool_calls"],
                                        tool_results=tool_results if tool_results else None
                                    )
                                    logger.info(f"💾 Saved assistant message with {len(pending_assistant_msg['tool_calls'])} tool calls (seq={seq})")
                                    seq += 1
                                    
                                    for tool_msg in tool_messages:
                                        msg_content = tool_msg.get("content", "")
                                        if isinstance(msg_content, list):
                                            msg_content = json.dumps(msg_content)
                                        
                                        await chat_async.create_message(
                                            db=db,
                                            chat_id=chat_id,
                                            role="tool",
                                            content=msg_content,
                                            sequence=seq,
                                            tool_call_id=tool_msg.get("tool_call_id"),
                                            name=tool_msg.get("name")
                                        )
                                        seq += 1
                                    
                                    if tool_messages:
                                        logger.info(f"💾 Saved {len(tool_messages)} tool result messages")
                                except Exception as e:
                                    logger.error(f"Failed to save tools_end batch: {e}")
                                    try:
                                        await db.rollback()
                                    except Exception:
                                        pass

                            pending_assistant_msg = None
                
                # Log session usage summary (token counts and costs)
                # Also deduct credits based on actual token usage
                usage_tracker = LLMHandler.get_session_usage(chat_id)
                if usage_tracker and usage_tracker.llm_call_count > 0:
                    # Calculate and deduct credits
                    from services.credits import calculate_credits_for_llm_call
                    
                    credits_to_deduct = calculate_credits_for_llm_call(
                        model=usage_tracker.model,
                        prompt_tokens=usage_tracker.total_prompt_tokens,
                        completion_tokens=usage_tracker.total_completion_tokens,
                        cache_read_tokens=usage_tracker.total_cache_read_tokens,
                        cache_creation_tokens=usage_tracker.total_cache_creation_tokens
                    )
                    
                    # Deduct credits using the same DB session
                    from services.credits import CreditsService
                    
                    # Build metadata for transaction
                    costs = usage_tracker.calculate_cost()
                    metadata = {
                        "model": usage_tracker.model,
                        "prompt_tokens": usage_tracker.total_prompt_tokens,
                        "completion_tokens": usage_tracker.total_completion_tokens,
                        "cache_read_tokens": usage_tracker.total_cache_read_tokens,
                        "cache_creation_tokens": usage_tracker.total_cache_creation_tokens,
                        "llm_calls": usage_tracker.llm_call_count,
                        "usd_cost": costs["total_cost"],
                        "premium_rate": 1.2
                    }
                    
                    success = await CreditsService.deduct_credits(
                        db=db,
                        user_id=user_id,
                        credits=credits_to_deduct,
                        transaction_type="chat_turn",
                        description=f"Chat turn ({usage_tracker.llm_call_count} LLM calls, {usage_tracker.total_prompt_tokens + usage_tracker.total_completion_tokens:,} tokens)",
                        chat_id=chat_id,
                        metadata=metadata
                    )
                    
                    if success:
                        logger.info(f"💳 Deducted {credits_to_deduct} credits (${costs['total_cost']:.4f} + 20% premium)")
                    else:
                        logger.warning(f"⚠️  Failed to deduct {credits_to_deduct} credits - insufficient balance or user not found")
                
                LLMHandler.finalize_session(chat_id)

                # Run compaction if the history has grown too large, or if the
                # session pruner signaled overflow (early compaction cascade).
                from .agent.compactor import maybe_compact
                force_compact = getattr(agent, '_needs_early_compaction', False)
                try:
                    if force_compact:
                        logger.info(f"Early compaction triggered by session pruner overflow for chat {chat_id}")
                    await maybe_compact(chat_id, user_id, db, skill_ids=skill_ids, force=force_compact)
                except Exception as e:
                    logger.warning(f"Compaction check failed (non-fatal): {e}")
                
                # Unregister this context (only if we're still the active one)
                unregister_context(chat_id, agent_context)

                # Send email notification if user requested it
                from services.notification_registry import pop_email_notification
                notify_email = pop_email_notification(chat_id)
                if notify_email:
                    try:
                        from services.notifications import send_chat_complete_email
                        chat_title = (await chat_async.get_chat(db, chat_id))
                        title = chat_title.title if chat_title and chat_title.title else "Your analysis"
                        app_base_url = os.environ.get("APP_BASE_URL", "http://localhost:3000")
                        chat_url = f"{app_base_url}/chat/{chat_id}"
                        await send_chat_complete_email(notify_email, title, chat_url)
                    except Exception as e:
                        logger.warning(f"Failed to send chat complete email: {e}")

                # Mark chat as no longer processing in database
                await chat_async.set_chat_processing(db, chat_id, is_processing=False)
                
                logger.info("Chat turn complete - all messages saved incrementally")
    
    async def get_chat_history(self, chat_id: str, db=None) -> List[dict]:
        """Get chat history for a chat, including tool calls (OpenAI format)"""
        if db is None:
            async with get_db_session() as db:
                messages = await chat_async.get_chat_messages(db, chat_id)
                history = ChatHistory.from_db_messages(messages, chat_id, user_id=None)
                return history.to_openai_format()
        else:
            messages = await chat_async.get_chat_messages(db, chat_id)
            history = ChatHistory.from_db_messages(messages, chat_id, user_id=None)
            return history.to_openai_format()
    
    async def clear_chat(self, chat_id: str, db=None) -> bool:
        """Clear chat history for a chat"""
        if db is None:
            async with get_db_session() as db:
                count = await chat_async.clear_chat_messages(db, chat_id)
                return count > 0
        else:
            count = await chat_async.clear_chat_messages(db, chat_id)
            return count > 0
    
    async def chat_exists(self, chat_id: str, db=None) -> bool:
        """Check if chat exists"""
        if db is None:
            async with get_db_session() as db:
                return await chat_async.get_chat(db, chat_id) is not None
        else:
            return await chat_async.get_chat(db, chat_id) is not None
    
    async def get_user_chats(self, user_id: str, limit: int = 50, db=None) -> List[dict]:
        """Get all chats for a user with last message preview (single optimized query)"""
        if db is None:
            async with get_db_session() as db:
                # Use optimized function that gets chats and previews in a single query
                return await chat_async.get_user_chats_with_preview(db, user_id, limit)
        else:
            return await chat_async.get_user_chats_with_preview(db, user_id, limit)
    
    async def is_chat_processing(self, chat_id: str, db=None) -> bool:
        """
        Check if a chat is currently being processed.
        Used for reconnection logic to determine if streaming should resume.
        
        Returns:
            True if the chat is currently being processed, False otherwise
        """
        if db is None:
            async with get_db_session() as db:
                return await chat_async.is_chat_processing(db, chat_id)
        else:
            return await chat_async.is_chat_processing(db, chat_id)
    
    async def get_chat_history_for_display(self, chat_id: str, db=None) -> Dict[str, Any]:
        """
        Get chat history formatted for UI display.
        
        SIMPLE: Each message has content and optional tool_calls attached directly.
        Frontend just renders messages in order.
        """
        if db is None:
            async with get_db_session() as db:
                return await self._get_chat_history_for_display_impl(db, chat_id)
        else:
            return await self._get_chat_history_for_display_impl(db, chat_id)
    
    async def _get_chat_history_for_display_impl(self, db, chat_id: str) -> Dict[str, Any]:
        """Internal implementation of get_chat_history_for_display"""
        messages = await chat_async.get_chat_messages(db, chat_id)
        
        if not messages:
            return {"messages": []}
        
        display_messages = []
        
        for msg in messages:
            # User messages
            if msg.role == "user":
                display_messages.append({
                    "role": "user",
                    "content": msg.content,
                    "timestamp": msg.timestamp.isoformat() if msg.timestamp else None
                })
            
            # Assistant messages
            elif msg.role == "assistant":
                # Parse tool_calls if present
                tool_calls = []
                # Get stored tool_results for this message (keyed by tool_call_id)
                tool_results = msg.tool_results or {}
                
                if msg.tool_calls:
                    for tc in msg.tool_calls:
                        tool_name = tc.get("function", {}).get("name")
                        tool_call_id = tc.get("id")
                        
                        # Skip hidden tools
                        tool_obj = tool_registry.get_tool(tool_name)
                        if tool_obj and tool_obj.hidden_from_ui:
                            continue
                        
                        # Parse arguments
                        try:
                            args_str = tc.get("function", {}).get("arguments", "{}")
                            # Handle both string and dict formats
                            if isinstance(args_str, str):
                                args = json.loads(args_str) if args_str else {}
                            elif isinstance(args_str, dict):
                                args = args_str
                            else:
                                args = {}
                            
                            # Use statusMessage to match ToolCallStatus interface
                            # Fall back to tool_name if no user_description provided
                            status_message = args.get("user_description") or tool_name
                            
                            # Get stored execution result for this tool call
                            stored_result = tool_results.get(tool_call_id, {})
                            
                            tool_call_data = {
                                "tool_call_id": tool_call_id,
                                "tool_name": tool_name,
                                "statusMessage": status_message,
                                "arguments": args,  # Include arguments for filename extraction
                                "status": stored_result.get("status", "completed"),
                                "error": stored_result.get("error"),
                                "result_summary": stored_result.get("result_summary"),
                            }
                            
                            # Include code_output if present (for execute_code tool)
                            if "code_output" in stored_result:
                                tool_call_data["code_output"] = stored_result["code_output"]
                            
                            tool_calls.append(tool_call_data)
                        except Exception as e:
                            logger.warning(f"Failed to parse tool call {tool_name}: {e}")
                            logger.exception(e)
                
                # Only add message if it has content or tool_calls
                if msg.content or tool_calls:
                    display_messages.append({
                        "role": "assistant",
                        "content": msg.content or "",
                        "timestamp": msg.timestamp.isoformat() if msg.timestamp else None,
                        "tool_calls": tool_calls if tool_calls else None
                    })
            
            # Skip internal messages
            elif msg.role in ("tool", "compaction"):
                continue
        
        return {"messages": display_messages}

