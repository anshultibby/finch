from typing import List, Dict, Any, Optional
from litellm import completion
import json
from config import Config
from modules.snaptrade_tools import snaptrade_tools, SNAPTRADE_TOOL_DEFINITIONS
from modules.apewisdom_tools import apewisdom_tools, APEWISDOM_TOOL_DEFINITIONS
from modules.insider_trading_tools import insider_trading_tools, INSIDER_TRADING_TOOL_DEFINITIONS


class ChatAgent:
    """
    AI Agent for portfolio chatbot using LiteLLM with tool calling support
    """
    
    def __init__(self):
        self.model = Config.OPENAI_MODEL
        # LiteLLM automatically uses API keys from environment variables
        
        self.system_prompt = """You are Finch, an intelligent portfolio assistant chatbot that helps users manage their brokerage investments through SnapTrade and track market sentiment from Reddit.

CRITICAL RULES FOR TOOL USAGE:

1. When user asks about portfolio/stocks/holdings:
   → IMMEDIATELY call get_portfolio tool
   → Do NOT ask for connection first

2. If get_portfolio returns needs_auth=true:
   → Call request_brokerage_connection to prompt user to connect
   → Tell user to connect their brokerage account

3. IMPORTANT: After you see "Successfully connected" message:
   → Check conversation history for what user originally wanted
   → If they asked for portfolio data, IMMEDIATELY call get_portfolio again
   → Do NOT wait for user to ask again
   
4. Context awareness:
   → Remember what user wanted before connection
   → After successful connection, automatically fulfill their original request

5. Reddit sentiment tools:
   → When user asks about trending stocks, what's popular on Reddit, meme stocks, or wallstreetbets: use get_reddit_trending_stocks
   → When user asks about Reddit sentiment for specific tickers: use get_reddit_ticker_sentiment or compare_reddit_sentiment
   → These tools work independently and don't require brokerage connection

6. Insider trading tools:
   → When user asks about Senate/House/congressional trades: use get_recent_senate_trades or get_recent_house_trades
   → When user asks about insider trading, insider buying/selling, or Form 4 filings: use get_recent_insider_trades
   → When user asks about insider activity for a specific stock: use search_ticker_insider_activity
   → When user asks about insider activity in their portfolio: FIRST call get_portfolio to get tickers, THEN call get_portfolio_insider_activity with those tickers
   → IMPORTANT: When calling get_portfolio_insider_activity, be smart about ticker selection:
     * If user has many holdings (>10), focus on their largest positions or most significant holdings
     * For ETFs (SPY, QQQ, etc), skip them - only include individual stocks
     * Maximum 15-20 tickers per call to avoid overload
     * You can see position values in the portfolio data - prioritize by value
   → API FAILURE HANDLING: If Senate/House endpoints return errors (API limits, payment required), gracefully inform the user and offer alternatives:
     * "Senate/House data temporarily unavailable, but I can show you corporate insider trades for your holdings"
     * Still provide valuable insights using available data sources
   → These tools work independently and don't require brokerage connection (except get_portfolio_insider_activity which needs portfolio data first)
   
EXAMPLE FLOW:
Turn 1:
  User: "what stocks do I own?"
  You: [call get_portfolio] → needs_auth
  You: [call request_brokerage_connection]
  You: "Please connect your brokerage account..."

Turn 2:
  User: [connects via OAuth]
  Assistant: "Successfully connected!"
  You: [see user originally wanted portfolio]
  You: [call get_portfolio immediately]
  You: "Here are your holdings: ..."

Turn 3:
  User: "what's trending on Reddit?"
  You: [call get_reddit_trending_stocks]
  You: "Here are the top trending stocks on Reddit..."

Turn 4:
  User: "what insider activity is happening in my portfolio?"
  You: [call get_portfolio] → get tickers and values
  You: [filter to top individual stocks, exclude ETFs like SPY/QQQ]
  You: [call get_portfolio_insider_activity with filtered tickers (max 15-20)]
  You: "Here's the insider activity in your top portfolio holdings..."

ALWAYS complete the original request after successful connection. DO NOT make user ask twice.

Be friendly and professional in your responses."""
    
    async def process_message(
        self, 
        message: str, 
        chat_history: List[Dict[str, Any]],
        context: Optional[Dict[str, Any]] = None,
        session_id: Optional[str] = None
    ) -> tuple[str, bool, List[Dict[str, Any]]]:
        """
        Process a user message and return the agent's response
        Context variables (like credentials) are passed to tools but NOT visible to the LLM
        
        Returns:
            Tuple of (response_text, needs_auth, full_conversation_history)
        """
        context = context or {}
        
        try:
            print(f"\n{'='*80}", flush=True)
            print(f"📨 PROCESSING MESSAGE for session: {session_id}", flush=True)
            print(f"📨 Current message: {message}", flush=True)
            print(f"📨 Chat history length: {len(chat_history)}", flush=True)
            print(f"📨 Full chat history:", flush=True)
            for i, msg in enumerate(chat_history):
                role = msg.get('role', 'unknown')
                content = msg.get('content', '')
                
                # Better labeling
                if role == 'tool':
                    label = "🔧 function result"
                    tool_call_id = msg.get('tool_call_id', '')
                    print(f"  [{i}] {label} (id={tool_call_id}):", flush=True)
                    print(f"      {content}", flush=True)
                elif role == 'assistant' and 'tool_calls' in msg:
                    label = "🤖 assistant (calling tools)"
                    tool_names = [tc.get('function', {}).get('name', 'unknown') for tc in msg.get('tool_calls', [])]
                    print(f"  [{i}] {label}: {tool_names}", flush=True)
                    if content:
                        print(f"      message: {content}", flush=True)
                else:
                    label = f"{'👤' if role == 'user' else '🤖'} {role}"
                    print(f"  [{i}] {label}:", flush=True)
                    print(f"      {content}", flush=True)
                print()  # Empty line between messages
            print(f"{'='*80}\n", flush=True)
            
            # Check if user has an active brokerage connection
            has_connection = snaptrade_tools.has_active_connection(session_id) if session_id else False
            
            # Build system prompt with authentication status and context
            auth_status_note = ""
            if has_connection:
                auth_status_note = "\n\n[SYSTEM INFO: User IS connected to their brokerage.]"
            else:
                auth_status_note = "\n\n[SYSTEM INFO: User is NOT connected to any brokerage.]"
            
            # Check if user just connected (successful connection in recent history)
            just_connected = False
            for msg in reversed(chat_history[-3:]):  # Check last 3 messages
                if msg.get("role") == "assistant" and "Successfully connected" in msg.get("content", ""):
                    just_connected = True
                    print(f"🔍 Detected recent successful connection!", flush=True)
                    break
            
            if just_connected and has_connection:
                auth_status_note += "\n[ACTION REQUIRED: User just connected successfully. Check conversation history for their original request (likely portfolio/holdings) and fulfill it NOW by calling get_portfolio.]"
                print(f"🎯 ACTION REQUIRED: Agent should call get_portfolio now", flush=True)
            
            full_system_prompt = self.system_prompt + auth_status_note
            print(f"\n📝 System prompt additions:", flush=True)
            print(f"{auth_status_note}\n", flush=True)
            
            # Convert chat history to standard format
            messages = [{"role": "system", "content": full_system_prompt}]
            
            for msg in chat_history[:-1]:  # Exclude the last message (current user message)
                if msg["role"] in ["user", "assistant", "tool"]:
                    # Reconstruct message for API
                    api_msg = {
                        "role": msg["role"],
                        "content": msg.get("content", "")
                    }
                    
                    # Preserve tool calls for assistant messages
                    if msg["role"] == "assistant" and "tool_calls" in msg:
                        api_msg["tool_calls"] = msg["tool_calls"]
                    
                    # Preserve tool call ID for tool responses
                    if msg["role"] == "tool" and "tool_call_id" in msg:
                        api_msg["tool_call_id"] = msg["tool_call_id"]
                        if "name" in msg:
                            api_msg["name"] = msg["name"]
                    
                    messages.append(api_msg)
            
            # Add current message
            messages.append({
                "role": "user",
                "content": message
            })
            
            # Prepare API call parameters
            api_params = {
                "model": self.model,
                "messages": messages,
                "api_key": Config.OPENAI_API_KEY
            }
            
            # Always add tools - the tools will check connection status internally
            api_params["tools"] = SNAPTRADE_TOOL_DEFINITIONS + APEWISDOM_TOOL_DEFINITIONS + INSIDER_TRADING_TOOL_DEFINITIONS
            
            # Call LLM via LiteLLM
            response = completion(**api_params)
            
            # Check if the model wants to call a tool
            if hasattr(response.choices[0].message, 'tool_calls') and response.choices[0].message.tool_calls:
                final_response, needs_auth = await self._handle_tool_calls(
                    response, 
                    messages, 
                    context, 
                    session_id
                )
                # Convert messages to storable format (remove system message, add timestamps)
                storable_messages = self._convert_to_storable_history(messages)
                return final_response, needs_auth, storable_messages
            
            # Extract text response
            storable_messages = self._convert_to_storable_history(messages)
            response_content = response.choices[0].message.content
            if response_content is None:
                print(f"⚠️ LLM returned None content, using fallback message", flush=True)
                response_content = "I'm not sure how to respond to that. Could you please rephrase your question?"
            return response_content, False, storable_messages
            
        except Exception as e:
            error_msg = f"Error in process_message: {str(e)}"
            print(f"❌ {error_msg}", flush=True)
            import traceback
            print(f"❌ Traceback: {traceback.format_exc()}", flush=True)
            return f"I apologize, but I encountered an error: {str(e)}", False, []
    
    async def _handle_tool_calls(
        self,
        initial_response: Any,
        messages: List[Dict[str, Any]],
        context: Dict[str, Any],
        session_id: str
    ) -> tuple[str, bool]:
        """
        Handle tool calls from the LLM
        Execute tools with context variables (credentials) that aren't visible to LLM
        
        Returns:
            Tuple of (response_text, needs_auth)
        """
        needs_auth = False
        
        try:
            # Add assistant's tool call message to history
            messages.append({
                "role": "assistant",
                "content": initial_response.choices[0].message.content or "",
                "tool_calls": [
                    {
                        "id": tool_call.id,
                        "type": "function",
                        "function": {
                            "name": tool_call.function.name,
                            "arguments": tool_call.function.arguments
                        }
                    }
                    for tool_call in initial_response.choices[0].message.tool_calls
                ]
            })
            
            # Execute each tool call
            for tool_call in initial_response.choices[0].message.tool_calls:
                function_name = tool_call.function.name
                function_args = json.loads(tool_call.function.arguments)
                
                # Execute the tool with context (credentials)
                tool_result = await self._execute_tool(
                    function_name,
                    function_args,
                    context,
                    session_id
                )
                
                # Check if authentication is needed
                if tool_result.get("needs_auth") or tool_result.get("action_required") == "show_login_form":
                    needs_auth = True
                
                # Truncate large tool results to avoid overwhelming the LLM
                try:
                    tool_result_str = json.dumps(tool_result)
                except Exception as json_err:
                    print(f"❌ Error serializing tool result to JSON: {json_err}", flush=True)
                    tool_result_str = json.dumps({
                        "success": False,
                        "error": f"Failed to serialize tool result: {str(json_err)}"
                    })
                
                max_size = 50000  # 50KB limit per tool response
                
                if len(tool_result_str) > max_size:
                    print(f"⚠️ Tool result too large ({len(tool_result_str)} bytes), truncating to {max_size} bytes", flush=True)
                    
                    # Try to intelligently truncate portfolio_activity data
                    if "portfolio_activity" in tool_result and isinstance(tool_result["portfolio_activity"], dict):
                        original_count = len(tool_result["portfolio_activity"])
                        # Keep only top 10 tickers by activity
                        truncated_activity = dict(list(tool_result["portfolio_activity"].items())[:10])
                        tool_result["portfolio_activity"] = truncated_activity
                        tool_result["_truncated"] = f"Showing top 10 of {original_count} tickers with activity"
                        print(f"📊 Truncated portfolio activity from {original_count} to 10 tickers", flush=True)
                        tool_result_str = json.dumps(tool_result)
                    
                    # If still too large, hard truncate
                    if len(tool_result_str) > max_size:
                        tool_result_str = tool_result_str[:max_size] + '... [TRUNCATED]"}'
                        print(f"⚠️ Hard truncated to {max_size} bytes", flush=True)
                
                # Add tool result to messages
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": tool_result_str
                })
            
            # Get final response from LLM with tool results
            final_response = completion(
                model=self.model,
                messages=messages,
                api_key=Config.OPENAI_API_KEY,
                tools=SNAPTRADE_TOOL_DEFINITIONS + APEWISDOM_TOOL_DEFINITIONS + INSIDER_TRADING_TOOL_DEFINITIONS
            )
            
            response_content = final_response.choices[0].message.content
            if response_content is None:
                print(f"⚠️ LLM returned None content, using fallback message", flush=True)
                response_content = "I encountered an issue processing that request. Please try again."
            
            return response_content, needs_auth
            
        except Exception as e:
            error_msg = f"Error in tool processing: {str(e)}"
            print(f"❌ {error_msg}", flush=True)
            import traceback
            print(f"❌ Traceback: {traceback.format_exc()}", flush=True)
            return f"I encountered an error while processing tools: {str(e)}", False
    
    async def _execute_tool(
        self,
        function_name: str,
        function_args: Dict[str, Any],
        context: Dict[str, Any],
        session_id: str
    ) -> Dict[str, Any]:
        """
        Execute a tool with context variables (credentials from context, not LLM)
        """
        print(f"🔧 Executing tool: {function_name} for session: {session_id}", flush=True)
        
        if function_name == "request_brokerage_connection":
            # Return a special response that tells the frontend to show connection UI
            return {
                "success": True,
                "needs_auth": True,
                "message": "Please connect your brokerage account through SnapTrade to continue.",
                "action_required": "show_connection_modal"
            }
        
        elif function_name == "get_portfolio":
            print(f"📊 get_portfolio tool called for session: {session_id}", flush=True)
            # Check if we have an active connection
            has_connection = snaptrade_tools.has_active_connection(session_id)
            
            if not has_connection:
                print(f"❌ No active connection, returning needs_auth", flush=True)
                return {
                    "success": False,
                    "needs_auth": True,
                    "message": "You need to connect your brokerage account first."
                }
            
            print(f"✅ Active connection found, calling snaptrade_tools.get_portfolio", flush=True)
            # Execute tool with stored connection
            result = snaptrade_tools.get_portfolio(session_id=session_id)
            print(f"📊 Portfolio result: {result}", flush=True)
            return result
        
        elif function_name == "get_reddit_trending_stocks":
            print(f"📊 get_reddit_trending_stocks tool called", flush=True)
            limit = function_args.get("limit", 10)
            result = await apewisdom_tools.get_trending_stocks(limit=limit)
            print(f"📊 Reddit trending result: {result}", flush=True)
            return result
        
        elif function_name == "get_reddit_ticker_sentiment":
            print(f"📊 get_reddit_ticker_sentiment tool called", flush=True)
            ticker = function_args.get("ticker", "")
            result = await apewisdom_tools.get_ticker_sentiment(ticker=ticker)
            print(f"📊 Reddit ticker sentiment result: {result}", flush=True)
            return result
        
        elif function_name == "compare_reddit_sentiment":
            print(f"📊 compare_reddit_sentiment tool called", flush=True)
            tickers = function_args.get("tickers", [])
            result = await apewisdom_tools.compare_tickers_sentiment(tickers=tickers)
            print(f"📊 Reddit comparison result: {result}", flush=True)
            return result
        
        elif function_name == "get_recent_senate_trades":
            print(f"🏛️ get_recent_senate_trades tool called", flush=True)
            limit = function_args.get("limit", 50)
            result = await insider_trading_tools.get_recent_senate_trades(limit=limit)
            
            # Log summary instead of full result
            if result.get("success"):
                print(f"🏛️ Senate trades: Found {result.get('total_count', 0)} trades", flush=True)
            else:
                print(f"🏛️ Senate trades failed: {result.get('message')}", flush=True)
            
            return result
        
        elif function_name == "get_recent_house_trades":
            print(f"🏛️ get_recent_house_trades tool called", flush=True)
            limit = function_args.get("limit", 50)
            result = await insider_trading_tools.get_recent_house_trades(limit=limit)
            
            # Log summary instead of full result
            if result.get("success"):
                print(f"🏛️ House trades: Found {result.get('total_count', 0)} trades", flush=True)
            else:
                print(f"🏛️ House trades failed: {result.get('message')}", flush=True)
            
            return result
        
        elif function_name == "get_recent_insider_trades":
            print(f"💼 get_recent_insider_trades tool called", flush=True)
            limit = function_args.get("limit", 100)
            result = await insider_trading_tools.get_recent_insider_trades(limit=limit)
            
            # Log summary instead of full result
            if result.get("success"):
                print(f"💼 Insider trades: Found {result.get('total_count', 0)} trades", flush=True)
            else:
                print(f"💼 Insider trades failed: {result.get('message')}", flush=True)
            
            return result
        
        elif function_name == "search_ticker_insider_activity":
            print(f"🔍 search_ticker_insider_activity tool called", flush=True)
            ticker = function_args.get("ticker", "")
            limit = function_args.get("limit", 50)
            result = await insider_trading_tools.search_ticker_insider_activity(ticker=ticker, limit=limit)
            
            # Log summary instead of full result
            if result.get("success"):
                summary = result.get('summary', {})
                print(f"🔍 {ticker}: {summary.get('total_trades', 0)} trades ({summary.get('purchases', 0)} buys, {summary.get('sales', 0)} sells)", flush=True)
            else:
                print(f"🔍 {ticker} search failed: {result.get('message')}", flush=True)
            
            return result
        
        elif function_name == "get_portfolio_insider_activity":
            print(f"📊 get_portfolio_insider_activity tool called", flush=True)
            tickers = function_args.get("tickers", [])
            days_back = function_args.get("days_back", 90)  # Increased default to 90 days for better coverage
            
            # Limit to max 20 tickers to avoid overwhelming API/response
            if len(tickers) > 20:
                print(f"⚠️ Limiting tickers from {len(tickers)} to 20 to avoid overload", flush=True)
                tickers = tickers[:20]
            
            result = await insider_trading_tools.get_portfolio_insider_activity(tickers=tickers, days_back=days_back)
            
            # Don't print full result (too large), just summary
            if result.get("success"):
                print(f"📊 Portfolio insider activity: Found activity in {len(result.get('tickers_with_activity', []))} tickers", flush=True)
            else:
                print(f"📊 Portfolio insider activity result: {result.get('message')}", flush=True)
            
            return result
        
        elif function_name == "get_insider_trading_statistics":
            print(f"📊 get_insider_trading_statistics tool called", flush=True)
            symbol = function_args.get("symbol", "")
            result = await insider_trading_tools.get_insider_trading_statistics(symbol=symbol)
            
            if result.get("success"):
                summary = result.get('summary', {})
                print(f"📊 {symbol} statistics: {summary.get('total_quarters', 0)} quarters analyzed", flush=True)
            else:
                print(f"📊 {symbol} statistics failed: {result.get('message')}", flush=True)
            
            return result
        
        elif function_name == "search_insider_trades":
            print(f"🔍 search_insider_trades tool called", flush=True)
            symbol = function_args.get("symbol")
            reporting_cik = function_args.get("reporting_cik")
            company_cik = function_args.get("company_cik")
            transaction_type = function_args.get("transaction_type")
            limit = function_args.get("limit", 50)
            page = function_args.get("page", 0)
            
            result = await insider_trading_tools.search_insider_trades(
                symbol=symbol,
                reporting_cik=reporting_cik,
                company_cik=company_cik,
                transaction_type=transaction_type,
                limit=limit,
                page=page
            )
            
            if result.get("success"):
                print(f"🔍 Search found {result.get('total_count', 0)} trades", flush=True)
            else:
                print(f"🔍 Search failed: {result.get('message')}", flush=True)
            
            return result
        
        return {
            "success": False,
            "message": f"Unknown tool: {function_name}"
        }
    
    def _convert_to_storable_history(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Convert API messages to storable chat history format
        - Remove system messages
        - Add timestamps
        - Keep tool_calls and tool results for context
        """
        from datetime import datetime
        storable = []
        timestamp = datetime.now().isoformat()
        
        for msg in messages:
            if msg["role"] == "system":
                continue  # Don't store system messages
                
            storable_msg = {
                "role": msg["role"],
                "content": msg.get("content", ""),
                "timestamp": timestamp
            }
            
            # Preserve tool calls
            if "tool_calls" in msg:
                storable_msg["tool_calls"] = msg["tool_calls"]
            
            # Preserve tool call ID for tool responses
            if msg["role"] == "tool" and "tool_call_id" in msg:
                storable_msg["tool_call_id"] = msg["tool_call_id"]
                storable_msg["name"] = msg.get("name", "")
            
            storable.append(storable_msg)
        
        return storable
    
    def add_tool(self, tool_definition: Dict[str, Any]):
        """
        Add a tool definition for the agent to use
        This will be used when integrating Robinhood API
        """
        pass  # To be implemented with tool calling

