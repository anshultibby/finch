"""
Chat service for managing chat sessions and interactions
"""
from typing import List, Any, Optional, Dict
from datetime import datetime
import json
import uuid
from agent import ChatAgent
from .context_manager import context_manager
from database import SessionLocal
from crud import chat as chat_crud
from crud import resource as resource_crud


class ChatService:
    """Service for handling chat operations"""
    
    def __init__(self):
        self.agent = ChatAgent()
    
    async def send_message(
        self, 
        message: str, 
        chat_id: str,
        user_id: str
    ) -> tuple[str, str, bool, List[Dict[str, Any]]]:
        """
        Send a message and get agent response
        
        Args:
            message: User message content
            chat_id: Chat identifier
            user_id: User identifier (for SnapTrade tools)
            
        Returns:
            Tuple of (response, timestamp, needs_auth, tool_calls_info)
        """
        db = SessionLocal()
        try:
            # Ensure chat exists
            db_chat = chat_crud.get_chat(db, chat_id)
            if not db_chat:
                # Create new chat
                chat_crud.create_chat(db, chat_id, user_id)
            
            # Get existing chat history and deserialize
            db_messages = chat_crud.get_chat_messages(db, chat_id)
            chat_history = []
            for msg in db_messages:
                # Deserialize content if it's JSON (for tool messages)
                content = msg.content
                try:
                    parsed_content = json.loads(content)
                    # If it successfully parses as JSON, it might be tool data
                    if isinstance(parsed_content, dict):
                        message_dict = {
                            "role": msg.role,
                            "content": parsed_content.get("content", ""),
                            "timestamp": msg.timestamp.isoformat()
                        }
                        # Add tool-specific fields if present
                        if "tool_calls" in parsed_content:
                            message_dict["tool_calls"] = parsed_content["tool_calls"]
                        if "tool_call_id" in parsed_content:
                            message_dict["tool_call_id"] = parsed_content["tool_call_id"]
                            message_dict["name"] = parsed_content.get("name", "")
                        chat_history.append(message_dict)
                    else:
                        # Plain text content
                        chat_history.append({
                            "role": msg.role,
                            "content": content,
                            "timestamp": msg.timestamp.isoformat()
                        })
                except (json.JSONDecodeError, TypeError):
                    # Not JSON, treat as plain text
                    chat_history.append({
                        "role": msg.role,
                        "content": content,
                        "timestamp": msg.timestamp.isoformat()
                    })
            
            # Get context for this user (using user_id for SnapTrade)
            context = context_manager.get_all_context(user_id)
            
            # Get agent response with full conversation including tool calls
            response, needs_auth, full_messages, tool_calls_info = await self.agent.process_message(
                message=message,
                chat_history=chat_history,
                context=context,
                session_id=user_id  # Pass user_id as session_id for tools
            )
            
            # Store ALL new messages including user message, tool calls, and assistant responses
            # full_messages contains the complete conversation including what we just processed
            # We need to store only the NEW messages (after the existing history)
            start_index = len(db_messages)
            sequence = start_index
            
            # Map tool_call_id to resource_id for linking messages to resources
            tool_call_to_resource = {}
            
            # Create resources for each successful tool call
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
                    
                    # Update tool_call_info with resource_id for frontend
                    tool_call_info["resource_id"] = resource.id
            
            final_timestamp = None
            for msg in full_messages[start_index:]:
                # Serialize content based on message type
                if msg["role"] == "tool" or "tool_calls" in msg:
                    # Store complex messages as JSON
                    content_to_store = json.dumps({
                        "content": msg.get("content", ""),
                        "tool_calls": msg.get("tool_calls"),
                        "tool_call_id": msg.get("tool_call_id"),
                        "name": msg.get("name")
                    })
                else:
                    # Store simple text messages as-is
                    content_to_store = msg.get("content", "")
                
                # Link tool response messages to resources
                resource_id = None
                if msg["role"] == "tool" and msg.get("tool_call_id"):
                    resource_id = tool_call_to_resource.get(msg["tool_call_id"])
                
                stored_msg = chat_crud.create_message(
                    db, chat_id, msg["role"], content_to_store, sequence, resource_id
                )
                sequence += 1
                final_timestamp = stored_msg.timestamp.isoformat()
            
            return response, final_timestamp or datetime.now().isoformat(), needs_auth, tool_calls_info
            
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
        """Get chat history for a chat, including tool calls"""
        db = SessionLocal()
        try:
            messages = chat_crud.get_chat_messages(db, chat_id)
            history = []
            for msg in messages:
                # Try to deserialize JSON content (for tool messages)
                try:
                    parsed_content = json.loads(msg.content)
                    if isinstance(parsed_content, dict):
                        # Reconstruct the full message with tool data
                        message_dict = {
                            "role": msg.role,
                            "content": parsed_content.get("content", ""),
                            "timestamp": msg.timestamp.isoformat()
                        }
                        # Add tool-specific fields if present
                        if parsed_content.get("tool_calls"):
                            message_dict["tool_calls"] = parsed_content["tool_calls"]
                        if parsed_content.get("tool_call_id"):
                            message_dict["tool_call_id"] = parsed_content["tool_call_id"]
                            message_dict["name"] = parsed_content.get("name", "")
                        history.append(message_dict)
                    else:
                        # Plain text that happened to be JSON
                        history.append({
                            "role": msg.role,
                            "content": msg.content,
                            "timestamp": msg.timestamp.isoformat()
                        })
                except (json.JSONDecodeError, TypeError):
                    # Not JSON, plain text message
                    history.append({
                        "role": msg.role,
                        "content": msg.content,
                        "timestamp": msg.timestamp.isoformat()
                    })
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

