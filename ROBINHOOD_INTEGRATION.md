# Robinhood Integration Guide

## 🎯 Overview

Your Finch chatbot now has **secure Robinhood integration** with tool calling! The AI can fetch real portfolio data while keeping credentials safe.

## 🔐 Architecture: Context Variables

### **What are Context Variables?**

Context variables are **session-specific data** that:
- ✅ Are passed to tools for execution
- ✅ Are NOT visible to the LLM
- ✅ Store sensitive data like credentials
- ✅ Persist per session

### **How It Works**

```
User → Frontend → API → Context Manager → Agent → LLM
                           ↓                    ↑
                      Credentials          Tool Call
                           ↓                    ↓
                    Robinhood Tool ← Execute with Credentials
```

**Key Security Feature:** The LLM never sees the credentials - they're injected by the tool execution layer!

## 📋 API Endpoints

### 1. **Set Robinhood Credentials**

```http
POST /robinhood/credentials
Content-Type: application/json

{
  "username": "your_robinhood_username",
  "password": "your_robinhood_password",
  "session_id": "user_session_id"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Robinhood credentials set successfully",
  "has_credentials": true
}
```

### 2. **Check if Credentials are Set**

```http
GET /robinhood/credentials/{session_id}
```

**Response:**
```json
{
  "success": true,
  "message": "Credentials are set",
  "has_credentials": true
}
```

### 3. **Delete Credentials**

```http
DELETE /robinhood/credentials/{session_id}
```

## 🛠️ Available Tools

### **get_portfolio**

Fetches the user's current Robinhood portfolio holdings.

**LLM sees this tool definition:**
```json
{
  "name": "get_portfolio",
  "description": "Get the user's current Robinhood portfolio holdings including stocks, quantities, current prices, and total equity",
  "parameters": {}
}
```

**Notice:** No credential parameters! They come from context.

**Tool returns:**
```json
{
  "success": true,
  "holdings": {
    "AAPL": {
      "name": "Apple Inc",
      "quantity": 10.0,
      "price": 150.25,
      "equity": 1502.50,
      "percent_change": 2.5,
      "average_buy_price": 145.00
    }
  },
  "total_equity": 1502.50,
  "holdings_count": 1
}
```

## 🚀 Usage Flow

### **Step 1: User Sets Credentials**

Frontend calls:
```javascript
await fetch('http://localhost:8000/robinhood/credentials', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    username: 'user@example.com',
    password: 'password123',
    session_id: sessionId
  })
});
```

Credentials are stored in context for this session.

### **Step 2: User Asks About Portfolio**

User: "What stocks do I own?"

### **Step 3: Agent Processes**

1. Agent receives message
2. Checks if credentials exist in context
3. If yes, adds `get_portfolio` tool to LLM API call
4. LLM decides to call `get_portfolio`
5. Agent executes tool with credentials from context (not from LLM!)
6. Tool logs into Robinhood and fetches portfolio
7. Agent sends tool result back to LLM
8. LLM generates natural language response

User sees: "You own 10 shares of Apple (AAPL) worth $1,502.50. Your average buy price was $145..."

## 🔒 Security Features

### **Context Variables**
- Stored per session
- Never sent to LLM
- Only accessed by tool execution layer
- Automatically cleared when session ends

### **Best Practices for Production**

1. **Encrypt credentials at rest**
   ```python
   from cryptography.fernet import Fernet
   
   # Encrypt before storing
   encrypted = cipher.encrypt(password.encode())
   context_manager.set_context(session_id, "robinhood_password", encrypted)
   ```

2. **Use database instead of in-memory**
   - Currently uses `Dict` in memory
   - Replace with Redis or database for persistence

3. **Add session expiration**
   ```python
   context_manager.set_context(session_id, "expires_at", time.time() + 3600)
   ```

4. **Use OAuth instead of passwords**
   - Robinhood doesn't officially support OAuth
   - Consider using API keys when available

## 📊 Backend Structure

```
backend/
├── modules/
│   ├── context_manager.py     # Context variable storage
│   ├── robinhood_tools.py     # Tool implementations
│   └── chat_service.py        # Orchestration
├── routes/
│   ├── robinhood.py          # Credential endpoints
│   └── chat.py               # Chat endpoints
├── models/
│   └── robinhood.py          # Pydantic models
└── agent.py                  # Tool calling logic
```

## 🧪 Testing

### **Test with cURL**

```bash
# 1. Set credentials
curl -X POST http://localhost:8000/robinhood/credentials \
  -H "Content-Type: application/json" \
  -d '{
    "username": "your_username",
    "password": "your_password",
    "session_id": "test_session"
  }'

# 2. Check credentials
curl http://localhost:8000/robinhood/credentials/test_session

# 3. Chat
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What stocks do I own?",
    "session_id": "test_session"
  }'
```

## ➕ Adding More Tools

To add more Robinhood tools:

### **1. Add tool definition** (`modules/robinhood_tools.py`)

```python
{
    "type": "function",
    "function": {
        "name": "get_stock_quote",
        "description": "Get current stock price and quote data",
        "parameters": {
            "type": "object",
            "properties": {
                "symbol": {
                    "type": "string",
                    "description": "Stock ticker symbol"
                }
            },
            "required": ["symbol"]
        }
    }
}
```

### **2. Implement tool** (`modules/robinhood_tools.py`)

```python
def get_stock_quote(self, symbol: str, username: str, password: str, session_id: str):
    # Login if needed
    if session_id not in self._logged_in_sessions:
        self.login(username, password, session_id)
    
    # Get quote
    quote = rh.get_latest_price(symbol)[0]
    return {"success": True, "symbol": symbol, "price": float(quote)}
```

### **3. Add to agent** (`agent.py`)

```python
elif function_name == "get_stock_quote":
    symbol = function_args.get("symbol")
    result = robinhood_tools.get_stock_quote(
        symbol=symbol,
        username=context.get("robinhood_username"),
        password=context.get("robinhood_password"),
        session_id=session_id
    )
    return result
```

## 🎓 Key Concepts

1. **Tools are functions** the LLM can call
2. **Context variables** provide data without showing it to LLM
3. **Tool execution layer** bridges LLM decisions with real API calls
4. **Session-based** credentials for multi-user support

## 🚀 Next Steps

1. Update frontend to collect credentials
2. Add credential input UI
3. Test with real Robinhood account
4. Add more tools (buy/sell, quotes, history)
5. Implement encryption for production
6. Add error handling and retries

---

**Your chatbot can now securely access real portfolio data!** 🎉

