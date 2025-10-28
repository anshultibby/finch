# Tool Call and Function Result Storage Implementation

## Overview
Enhanced the chat message storage system to properly store tool calls and function results following OpenAI's Chat API format, with foreign key references to the resources table and latency tracking for assistant responses.

## Database Schema Changes

### Migration: `007_add_tool_call_columns.py`

Added four new columns to the `chat_messages` table:

1. **`tool_calls`** (JSONB, nullable)
   - For `assistant` role messages that invoke tools
   - Stores array of tool call objects with id, type, and function details

2. **`tool_call_id`** (String, nullable, indexed)
   - For `tool` role messages (function results)
   - Links back to the specific tool call that was executed

3. **`name`** (String, nullable)
   - For `tool` role messages
   - Stores the tool/function name

4. **`latency_ms`** (Integer, nullable)
   - For `assistant` role messages
   - Tracks response time in milliseconds

## Message Roles (OpenAI Format)

Following OpenAI's Chat API convention:

### `user`
- User input messages
- **Fields**: `content`

### `assistant`
- AI responses
- **Fields**: `content`, optionally `tool_calls`, `latency_ms`

### `tool`
- Tool/function execution results
- **Fields**: `content`, `tool_call_id`, `name`, `resource_id` (FK)

## Database Model (`models/db.py`)

```python
class ChatMessage(Base):
    # Core fields
    role = Column(String, nullable=False)  # 'user', 'assistant', or 'tool'
    content = Column(Text, nullable=False)
    
    # Assistant message fields
    tool_calls = Column(JSONB, nullable=True)
    latency_ms = Column(Integer, nullable=True)
    
    # Tool result fields
    tool_call_id = Column(String, nullable=True, index=True)
    name = Column(String, nullable=True)
    resource_id = Column(String, nullable=True, index=True)  # FK to resources
```

## CRUD Operations (`crud/chat.py`)

Updated `create_message()` to accept all new parameters:
- `tool_calls`: JSONB array for assistant messages
- `tool_call_id`: String for tool messages
- `name`: Tool name for tool messages
- `latency_ms`: Response time for assistant messages

## Chat Service (`modules/chat_service.py`)

### Storing Messages
- **Tracks latency**: Measures time from request start to assistant response completion
- **Links tool results to resources**: Uses `tool_call_to_resource` map to connect function results with their resource records
- **Proper column mapping**: Extracts OpenAI format fields and maps them to database columns

### Retrieving Messages
- **Reconstructs OpenAI format**: Reads from database columns and rebuilds proper message structure
- **Includes metadata**: Returns `latency_ms` for assistant messages, `resource_id` for tool messages
- Works in both `send_message()` and `send_message_stream()` methods

## Pydantic Models (`models/chat.py`)

### `Message` Model
Represents messages in chat history with proper typing:

```python
class Message(BaseModel):
    role: Literal["user", "assistant", "tool"]
    content: str
    timestamp: str
    
    # Assistant fields
    tool_calls: Optional[List[Dict[str, Any]]] = None
    latency_ms: Optional[int] = None
    
    # Tool result fields
    tool_call_id: Optional[str] = None
    name: Optional[str] = None
    resource_id: Optional[str] = None
```

### `ToolCall` Model
Structure for tool calls in assistant messages:

```python
class ToolCall(BaseModel):
    id: str
    type: str = "function"
    function: Dict[str, Any]  # Contains 'name' and 'arguments'
```

## Benefits

1. **OpenAI Compatibility**: Message format matches OpenAI's Chat API exactly
2. **Resource Linking**: Function results are properly linked to resource records via FK
3. **Performance Tracking**: Latency metrics stored for each assistant response
4. **Proper Storage**: No more JSON serialization hacks - each field has its own column
5. **Query Efficiency**: Indexed columns for fast lookups by `tool_call_id`
6. **Chat History Completeness**: Full conversation context including tool invocations and results

## Migration Command

```bash
cd backend
source venv/bin/activate
alembic upgrade head
```

## Example Message Flow

1. **User message**
   ```json
   {
     "role": "user",
     "content": "What stocks do I own?"
   }
   ```

2. **Assistant with tool call**
   ```json
   {
     "role": "assistant",
     "content": "",
     "tool_calls": [{
       "id": "call_abc123",
       "type": "function",
       "function": {"name": "get_portfolio", "arguments": "{}"}
     }],
     "latency_ms": 1234
   }
   ```

3. **Tool result**
   ```json
   {
     "role": "tool",
     "tool_call_id": "call_abc123",
     "name": "get_portfolio",
     "content": "{...result...}",
     "resource_id": "res_xyz789"
   }
   ```

4. **Final assistant response**
   ```json
   {
     "role": "assistant",
     "content": "You own 5 stocks...",
     "latency_ms": 856
   }
   ```

## Files Modified

- `backend/alembic/versions/007_add_tool_call_columns.py` (new)
- `backend/models/db.py`
- `backend/models/chat.py`
- `backend/crud/chat.py`
- `backend/modules/chat_service.py`

