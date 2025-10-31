"""
Chat service for managing chat sessions and interactions
"""
from typing import List, Any, Optional, Dict, AsyncGenerator
from datetime import datetime
import json
import uuid
import io
import pandas as pd
from .agent import ChatAgent
from .context_manager import context_manager
from database import SessionLocal
from crud import chat as chat_crud
from crud import resource as resource_crud
from models.sse import SSEEvent, ToolCallCompleteEvent


class ChatService:
    """Service for handling chat operations"""
    
    def __init__(self):
        self.agent = ChatAgent()
    
    async def send_message_stream(
        self, 
        message: str, 
        chat_id: str,
        user_id: str
    ) -> AsyncGenerator[str, None]:
        """
        Send a message and stream SSE events as they happen
        
        Args:
            message: User message content
            chat_id: Chat identifier
            user_id: User identifier (for SnapTrade tools)
            
        Yields:
            SSE formatted strings (event: <type>\\ndata: <json>\\n\\n)
        """
        db = SessionLocal()
        try:
            # Ensure chat exists
            db_chat = chat_crud.get_chat(db, chat_id)
            if not db_chat:
                # Create new chat
                chat_crud.create_chat(db, chat_id, user_id)
            
            # Get existing chat history
            db_messages = chat_crud.get_chat_messages(db, chat_id)
            chat_history = []
            for msg in db_messages:
                # Reconstruct message from database columns (OpenAI format)
                message_dict = {
                    "role": msg.role,
                    "content": msg.content,
                    "timestamp": msg.timestamp.isoformat()
                }
                
                # Add tool_calls for assistant messages that call tools
                if msg.role == "assistant" and msg.tool_calls:
                    message_dict["tool_calls"] = msg.tool_calls
                
                # Add tool result metadata for tool role messages
                if msg.role == "tool":
                    if msg.tool_call_id:
                        message_dict["tool_call_id"] = msg.tool_call_id
                    if msg.name:
                        message_dict["name"] = msg.name
                    if msg.resource_id:
                        message_dict["resource_id"] = msg.resource_id
                
                chat_history.append(message_dict)
            
            # Get context for this user (using user_id for SnapTrade)
            context = context_manager.get_all_context(user_id)
            
            # Save user message FIRST before streaming
            start_sequence = len(db_messages)
            chat_crud.create_message(
                db=db,
                chat_id=chat_id,
                role="user",
                content=message,
                sequence=start_sequence
            )
            print(f"💾 Saved user message to database", flush=True)
            
            # Stream events from agent
            async for event in self.agent.process_message_stream(
                message=message,
                chat_history=chat_history,
                context=context,
                session_id=user_id
            ):
                # Yield the SSE formatted event
                yield event.to_sse_format()
            
            # After streaming, get new messages (assistant + tool responses) and save to database
            new_messages = self.agent.get_new_messages()
            print(f"💾 Saving {len(new_messages)} messages to database...", flush=True)
            
            # Get tool call information for resource creation
            tool_calls_info = self.agent.get_tool_calls_info()
            
            # Create resources for each successful tool call
            tool_call_to_resource = {}
            for tool_call_info in tool_calls_info:
                if tool_call_info["status"] == "completed" and tool_call_info.get("result_data"):
                    result_data = tool_call_info["result_data"]
                    
                    # Determine resource type and title based on tool name
                    resource_type, title = self._get_resource_metadata(
                        tool_call_info["tool_name"],
                        tool_call_info.get("arguments", {}),
                        result_data
                    )
                    
                    # Extract core table data from wrapped structures
                    table_data = self._extract_table_data(result_data)
                    
                    # Create resource
                    resource = resource_crud.create_resource(
                        db=db,
                        chat_id=chat_id,
                        user_id=user_id,
                        tool_name=tool_call_info["tool_name"],
                        resource_type=resource_type,
                        title=title,
                        data=table_data,
                        resource_metadata={
                            "parameters": tool_call_info.get("arguments", {}),
                            "tool_call_id": tool_call_info["tool_call_id"],
                            "original_success": result_data.get("success"),
                            "data_source": result_data.get("data_source"),
                            "total_count": result_data.get("total_count") or result_data.get("total_tickers")
                        }
                    )
                    
                    # Map tool_call_id to resource_id
                    tool_call_to_resource[tool_call_info["tool_call_id"]] = resource.id
                    print(f"📊 Created resource {resource.id} for tool call {tool_call_info['tool_call_id']}", flush=True)
            
            # Save messages with proper sequencing (start after user message)
            sequence = start_sequence + 1
            
            for msg in new_messages:
                role = msg["role"]
                content = msg.get("content", "")
                tool_calls = msg.get("tool_calls") if role == "assistant" else None
                tool_call_id = msg.get("tool_call_id") if role == "tool" else None
                name = msg.get("name") if role == "tool" else None
                
                # Link tool result messages to resources
                resource_id = None
                if role == "tool" and tool_call_id:
                    resource_id = tool_call_to_resource.get(tool_call_id)
                
                chat_crud.create_message(
                    db=db,
                    chat_id=chat_id,
                    role=role,
                    content=content,
                    sequence=sequence,
                    resource_id=resource_id,
                    tool_calls=tool_calls,
                    tool_call_id=tool_call_id,
                    name=name
                )
                sequence += 1
            
            print(f"✅ Saved conversation history", flush=True)
            
        finally:
            db.close()
    
    def _extract_table_data(self, result_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract core table data from wrapped API responses
        Converts nested structures to flat arrays for better table display
        
        Returns:
            Simplified data structure optimized for table display
        """
        # If it's already a simple array, return as-is
        if isinstance(result_data, list):
            return {"data": result_data}
        
        # Handle CSV-formatted portfolio holdings (efficient format)
        if "holdings_csv" in result_data and isinstance(result_data["holdings_csv"], str):
            try:
                # Parse CSV string to DataFrame
                df = pd.read_csv(io.StringIO(result_data["holdings_csv"]))
                # Convert to list of dicts for JSON serialization
                holdings_array = df.to_dict('records')
                return {"data": holdings_array}
            except Exception as e:
                print(f"⚠️ Error parsing CSV portfolio data: {e}", flush=True)
                # Fall back to returning full result
                return result_data
        
        # Extract the main data array from common wrapper structures
        if "mentions" in result_data and isinstance(result_data["mentions"], list):
            return {"data": result_data["mentions"]}
        elif "trades" in result_data and isinstance(result_data["trades"], list):
            return {"data": result_data["trades"]}
        elif "holdings" in result_data and isinstance(result_data["holdings"], list):
            return {"data": result_data["holdings"]}
        elif "positions" in result_data and isinstance(result_data["positions"], list):
            return {"data": result_data["positions"]}
        elif "portfolio_activity" in result_data:
            # Flatten portfolio insider activity
            activities = []
            for ticker, activity_list in result_data.get("portfolio_activity", {}).items():
                for activity in activity_list:
                    activities.append({"ticker": ticker, **activity})
            return {"data": activities}
        elif "results" in result_data and isinstance(result_data["results"], list):
            return {"data": result_data["results"]}
        
        # If no recognizable array structure, return the whole thing
        return result_data
    
    def _get_resource_metadata(
        self, 
        tool_name: str, 
        arguments: Dict[str, Any],
        result_data: Dict[str, Any]
    ) -> tuple[str, str]:
        """
        Determine resource type and title based on tool name and results
        
        Returns:
            Tuple of (resource_type, title)
        """
        if tool_name == "get_portfolio":
            return "portfolio", "Portfolio Holdings"
        elif tool_name == "get_reddit_trending_stocks":
            limit = arguments.get("limit", 10)
            return "reddit_trends", f"Top {limit} Trending Stocks on Reddit"
        elif tool_name == "get_reddit_ticker_sentiment":
            ticker = arguments.get("ticker", "").upper()
            return "reddit_sentiment", f"Reddit Sentiment for {ticker}"
        elif tool_name == "compare_reddit_sentiment":
            tickers = arguments.get("tickers", [])
            return "reddit_comparison", f"Reddit Comparison: {', '.join(tickers)}"
        elif tool_name == "get_recent_senate_trades":
            limit = arguments.get("limit", 50)
            return "senate_trades", f"Recent Senate Trades (Last {limit})"
        elif tool_name == "get_recent_house_trades":
            limit = arguments.get("limit", 50)
            return "house_trades", f"Recent House Trades (Last {limit})"
        elif tool_name == "get_recent_insider_trades":
            limit = arguments.get("limit", 100)
            return "insider_trades", f"Recent Insider Trades (Last {limit})"
        elif tool_name == "search_ticker_insider_activity":
            ticker = arguments.get("ticker", "").upper()
            return "ticker_insider_activity", f"Insider Activity: {ticker}"
        elif tool_name == "get_portfolio_insider_activity":
            return "portfolio_insider_activity", "Insider Activity in Portfolio"
        elif tool_name == "get_insider_trading_statistics":
            symbol = arguments.get("symbol", "").upper()
            return "insider_statistics", f"Insider Statistics: {symbol}"
        elif tool_name == "search_insider_trades":
            symbol = arguments.get("symbol", "").upper() if arguments.get("symbol") else "Multiple"
            return "insider_search", f"Insider Trades Search: {symbol}"
        else:
            return "other", tool_name.replace("_", " ").title()
    
    def get_chat_history(self, chat_id: str) -> List[dict]:
        """Get chat history for a chat, including tool calls (OpenAI format)"""
        db = SessionLocal()
        try:
            messages = chat_crud.get_chat_messages(db, chat_id)
            history = []
            for msg in messages:
                # Reconstruct message from database columns (OpenAI format)
                message_dict = {
                    "role": msg.role,
                    "content": msg.content,
                    "timestamp": msg.timestamp.isoformat()
                }
                
                # Add tool_calls for assistant messages
                if msg.role == "assistant":
                    if msg.tool_calls:
                        message_dict["tool_calls"] = msg.tool_calls
                    if msg.latency_ms is not None:
                        message_dict["latency_ms"] = msg.latency_ms
                
                # Add tool result metadata for tool role messages
                if msg.role == "tool":
                    if msg.tool_call_id:
                        message_dict["tool_call_id"] = msg.tool_call_id
                    if msg.name:
                        message_dict["name"] = msg.name
                    if msg.resource_id:
                        message_dict["resource_id"] = msg.resource_id
                
                history.append(message_dict)
            return history
        finally:
            db.close()
    
    def clear_chat(self, chat_id: str) -> bool:
        """Clear chat history for a chat"""
        db = SessionLocal()
        try:
            count = chat_crud.clear_chat_messages(db, chat_id)
            return count > 0
        finally:
            db.close()
    
    def chat_exists(self, chat_id: str) -> bool:
        """Check if chat exists"""
        db = SessionLocal()
        try:
            return chat_crud.get_chat(db, chat_id) is not None
        finally:
            db.close()
    
    def get_user_chats(self, user_id: str, limit: int = 50) -> List[dict]:
        """Get all chats for a user"""
        db = SessionLocal()
        try:
            chats = chat_crud.get_user_chats(db, user_id, limit)
            return [
                {
                    "chat_id": chat.chat_id,
                    "title": chat.title,
                    "created_at": chat.created_at.isoformat(),
                    "updated_at": chat.updated_at.isoformat()
                }
                for chat in chats
            ]
        finally:
            db.close()

