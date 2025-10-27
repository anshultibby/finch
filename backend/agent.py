from typing import List, Dict, Any, Optional
from litellm import completion
import json
from config import Config
from modules.robinhood_tools import robinhood_tools, ROBINHOOD_TOOL_DEFINITIONS


class ChatAgent:
    """
    AI Agent for portfolio chatbot using LiteLLM with tool calling support
    """
    
    def __init__(self):
        self.model = Config.OPENAI_MODEL
        # LiteLLM automatically uses API keys from environment variables
        
        self.system_prompt = """You are Finch, an intelligent portfolio assistant chatbot that helps users manage their Robinhood investments.

CRITICAL RULES FOR TOOL USAGE:

1. When user asks about portfolio/stocks/holdings:
   → IMMEDIATELY call get_portfolio tool
   → Do NOT ask for login first

2. If get_portfolio returns needs_auth=true:
   → Call request_robinhood_login to show login form
   → Tell user to login

3. IMPORTANT: After you see "Successfully connected to Robinhood" message:
   → Check conversation history for what user originally wanted
   → If they asked for portfolio data, IMMEDIATELY call get_portfolio again
   → Do NOT wait for user to ask again
   
4. Context awareness:
   → Remember what user wanted before login
   → After successful login, automatically fulfill their original request
   
EXAMPLE FLOW:
Turn 1:
  User: "what stocks do I own?"
  You: [call get_portfolio] → needs_auth
  You: [call request_robinhood_login]
  You: "Please login..."

Turn 2:
  User: [logs in via modal]
  Assistant: "Successfully connected to Robinhood!"
  You: [see user originally wanted portfolio]
  You: [call get_portfolio immediately]
  You: "Here are your holdings: ..."

ALWAYS complete the original request after successful login. DO NOT make user ask twice.

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
            
            # Check if user has an active Robinhood session
            has_session = robinhood_tools.has_active_session(session_id) if session_id else False
            
            # Build system prompt with authentication status and context
            auth_status_note = ""
            if has_session:
                auth_status_note = "\n\n[SYSTEM INFO: User IS logged into Robinhood.]"
            else:
                auth_status_note = "\n\n[SYSTEM INFO: User is NOT logged in.]"
            
            # Check if user just logged in (successful login in recent history)
            just_logged_in = False
            for msg in reversed(chat_history[-3:]):  # Check last 3 messages
                if msg.get("role") == "assistant" and "Successfully connected to Robinhood" in msg.get("content", ""):
                    just_logged_in = True
                    print(f"🔍 Detected recent successful login!", flush=True)
                    break
            
            if just_logged_in and has_session:
                auth_status_note += "\n[ACTION REQUIRED: User just logged in successfully. Check conversation history for their original request (likely portfolio/holdings) and fulfill it NOW by calling get_portfolio.]"
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
            
            # Always add tools - the tools will check session status internally
            api_params["tools"] = ROBINHOOD_TOOL_DEFINITIONS
            
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
            return response.choices[0].message.content, False, storable_messages
            
        except Exception as e:
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
                
                # Add tool result to messages
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": json.dumps(tool_result)
                })
            
            # Get final response from LLM with tool results
            final_response = completion(
                model=self.model,
                messages=messages,
                api_key=Config.OPENAI_API_KEY,
                tools=ROBINHOOD_TOOL_DEFINITIONS
            )
            
            return final_response.choices[0].message.content, needs_auth
            
        except Exception as e:
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
        
        if function_name == "request_robinhood_login":
            # Return a special response that tells the frontend to show login UI
            return {
                "success": True,
                "needs_auth": True,
                "message": "Please provide your Robinhood username and password to continue.",
                "action_required": "show_login_form"
            }
        
        elif function_name == "get_portfolio":
            print(f"📊 get_portfolio tool called for session: {session_id}", flush=True)
            # Check if we have an active session
            has_session = robinhood_tools.has_active_session(session_id)
            
            if not has_session:
                print(f"❌ No active session, returning needs_auth", flush=True)
                return {
                    "success": False,
                    "needs_auth": True,
                    "message": "You need to log in to Robinhood first. Please provide your credentials."
                }
            
            print(f"✅ Active session found, calling robinhood_tools.get_portfolio", flush=True)
            # Execute tool with stored session
            result = robinhood_tools.get_portfolio(session_id=session_id)
            print(f"📊 Portfolio result: {result}", flush=True)
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

