# ChatHistory Model Usage Guide

## Overview

The new `ChatHistory` model provides a type-safe, clean abstraction for managing conversation state throughout the codebase.

## Benefits

✅ **Type Safety** - No more `List[Dict[str, Any]]`  
✅ **Clean API** - Intuitive methods for common operations  
✅ **Easy Serialization** - Convert to/from DB and OpenAI formats  
✅ **Aggregation** - Built-in methods for analyzing conversations  
✅ **Better Logging** - Structured turn-based logging

## Before & After

### Before (Raw Dictionaries)

```python
# chat_service.py - BEFORE
async def send_message_stream(...):
    # Load from DB - manual reconstruction
    db_messages = await chat_async.get_chat_messages(db, chat_id)
    chat_history = []
    for msg in db_messages:
        message_dict = {
            "role": msg.role,
            "content": msg.content,
            "timestamp": msg.timestamp.isoformat()
        }
        if msg.role == "assistant" and msg.tool_calls:
            message_dict["tool_calls"] = msg.tool_calls
        if msg.role == "tool":
            if msg.tool_call_id:
                message_dict["tool_call_id"] = msg.tool_call_id
            if msg.name:
                message_dict["name"] = msg.name
        chat_history.append(message_dict)
    
    # Use in agent
    async for event in agent.process_message_stream(
        message=message,
        chat_history=chat_history,  # List[Dict]
        agent_context=agent_context
    ):
        yield event
    
    # Save to DB - manual extraction
    new_messages = agent.get_new_messages()
    for msg in new_messages:
        role = msg["role"]
        content = msg.get("content", "")
        tool_calls = msg.get("tool_calls") if role == "assistant" else None
        # ... more extraction logic ...
        await chat_async.create_message(db, chat_id, role, content, ...)
```

### After (Type-Safe ChatHistory)

```python
# chat_service.py - AFTER
from models import ChatHistory

async def send_message_stream(...):
    # Load from DB - clean constructor
    db_messages = await chat_async.get_chat_messages(db, chat_id)
    history = ChatHistory.from_db_messages(db_messages, chat_id, user_id)
    
    # Add new user message
    history.add_user_message(message)
    
    # Use in agent (pass ChatHistory or convert to OpenAI format)
    async for event in agent.process_message_stream(
        message=message,
        chat_history=history.to_openai_format(),  # Clean conversion
        agent_context=agent_context
    ):
        yield event
    
    # Save to DB - clean iteration
    new_messages = agent.get_new_messages()
    for msg in new_messages:
        db_format = msg.to_db_format()  # Everything converted properly
        await chat_async.create_message(db, chat_id, **db_format)
```

## API Reference

### ChatMessage

Individual message with full type safety:

```python
from models.chat_history import ChatMessage, ToolCall

# User message
user_msg = ChatMessage(role="user", content="Hello!")

# Assistant message with tool calls
assistant_msg = ChatMessage(
    role="assistant",
    content="Let me check your portfolio",
    tool_calls=[
        ToolCall(
            id="call_123",
            type="function",
            function={"name": "get_portfolio", "arguments": "{}"}
        )
    ]
)

# Tool result
tool_msg = ChatMessage(
    role="tool",
    content='{"holdings": [...]}',
    tool_call_id="call_123",
    name="get_portfolio",
    resource_id="res_456"  # Optional: link to resource
)

# Convert to different formats
openai_dict = user_msg.to_openai_format()  # For LLM API
db_dict = user_msg.to_db_format()  # For database storage
```

### ChatHistory

Conversation history management:

```python
from models import ChatHistory

# Create new history
history = ChatHistory(chat_id="chat_123", user_id="user_456")

# Add messages
history.add_system_message("You are a helpful assistant")
history.add_user_message("What's in my portfolio?")
history.add_assistant_message(
    content="Let me check",
    tool_calls=[...]
)
history.add_tool_message(
    content='{"holdings": [...]}',
    tool_call_id="call_123",
    name="get_portfolio"
)

# Query history
last_user = history.get_last_user_message()
assistant_msgs = history.get_messages_by_role("assistant")
counts = history.count_by_role()  # {"user": 1, "assistant": 1, ...}

# Convert for different uses
openai_msgs = history.to_openai_format()  # For LLM API
db_msgs = history.to_db_format()  # For database
new_msgs = history.get_new_messages(start_index=5)  # Messages after index 5

# Load from database
db_messages = await chat_async.get_chat_messages(db, chat_id)
history = ChatHistory.from_db_messages(db_messages, chat_id, user_id)

# Load from dicts
dict_messages = [{"role": "user", "content": "hi"}, ...]
history = ChatHistory.from_dicts(dict_messages, chat_id, user_id)
```

### ChatTurn

Represents a complete conversation turn (useful for logging):

```python
from models.chat_history import ChatTurn

turn = ChatTurn(
    turn_number=1,
    user_message=user_msg,
    assistant_messages=[assistant_msg1, assistant_msg2],
    tool_messages=[tool_msg1, tool_msg2],
    duration_ms=1250.5
)

# Get log format
log_data = turn.to_log_format()
# {
#     "turn_number": 1,
#     "timestamp": "2024-01-01T12:00:00",
#     "duration_ms": 1250.5,
#     "user_message": "What's in my portfolio?",
#     "assistant_messages": [...],
#     "tool_calls": [...]
# }

# Get final response
final = turn.get_final_response()  # Last assistant message without tool calls
```

## Refactoring Guide

### Step 1: Update chat_service.py

```python
# Old
chat_history = []
for msg in db_messages:
    message_dict = {
        "role": msg.role,
        "content": msg.content,
        # ... manual reconstruction
    }
    chat_history.append(message_dict)

# New
history = ChatHistory.from_db_messages(db_messages, chat_id, user_id)
history.add_user_message(message)
chat_history = history.to_openai_format()
```

### Step 2: Update base_agent.py

The agent can work with either format:

```python
# Option A: Keep using List[Dict] internally (minimal change)
def build_messages(
    self,
    user_message: str,
    chat_history: List[Dict[str, Any]],
    **kwargs
) -> List[Dict[str, Any]]:
    # Works as-is

# Option B: Accept ChatHistory (better type safety)
def build_messages(
    self,
    user_message: str,
    chat_history: ChatHistory,
    **kwargs
) -> List[Dict[str, Any]]:
    messages = [{"role": "system", "content": self.get_system_prompt(**kwargs)}]
    messages.extend(chat_history.to_openai_format())
    messages.append({"role": "user", "content": user_message})
    return messages
```

### Step 3: Update message tracking

```python
# Old - BaseAgent
def get_new_messages(self) -> List[Dict[str, Any]]:
    return self._last_messages[self._initial_messages_len:]

# New - Can return ChatMessage objects or dicts
def get_new_messages(self) -> List[ChatMessage]:
    raw_messages = self._last_messages[self._initial_messages_len:]
    return [ChatMessage.from_dict(msg) for msg in raw_messages]
```

### Step 4: Simplify DB operations

```python
# Old
for msg in new_messages:
    role = msg["role"]
    content = msg.get("content", "")
    tool_calls = msg.get("tool_calls") if role == "assistant" else None
    tool_call_id = msg.get("tool_call_id") if role == "tool" else None
    name = msg.get("name") if role == "tool" else None
    
    await chat_async.create_message(
        db=db,
        chat_id=chat_id,
        role=role,
        content=content,
        sequence=sequence,
        tool_calls=tool_calls,
        tool_call_id=tool_call_id,
        name=name
    )

# New
for msg in new_messages:
    db_data = msg.to_db_format()
    await chat_async.create_message(db=db, chat_id=chat_id, **db_data)
```

## Advanced Usage

### Analyzing Conversations

```python
# Get tool usage statistics
history = ChatHistory.from_db_messages(db_messages, chat_id, user_id)

# Count messages
counts = history.count_by_role()
print(f"User sent {counts['user']} messages")
print(f"Assistant used {counts['tool']} tools")

# Get tool calls with results
tool_pairs = history.get_tool_calls_with_results()
for pair in tool_pairs:
    tool_call = pair["tool_call"]
    result = pair["result"]
    print(f"Tool: {tool_call.function['name']}")
    print(f"Resource: {result.resource_id}")
```

### Streaming with Turns

```python
# Track turns for better logging
current_turn = 1
turn_start = time.time()

history = ChatHistory(chat_id=chat_id, user_id=user_id)
user_msg = ChatMessage(role="user", content=message)
history.add_message(user_msg)

# Process with agent
initial_len = len(history)
async for event in agent.process_message_stream(...):
    yield event

# Create turn object for logging
new_messages = history.get_new_messages(initial_len)
turn = ChatTurn(
    turn_number=current_turn,
    user_message=user_msg,
    assistant_messages=[m for m in new_messages if m.role == "assistant"],
    tool_messages=[m for m in new_messages if m.role == "tool"],
    duration_ms=(time.time() - turn_start) * 1000
)

# Log turn
logger.info(f"Turn {current_turn}: {turn.to_log_format()}")
```

### Resource Tracking

```python
# Track which tool calls created resources
history = ChatHistory.from_db_messages(db_messages, chat_id, user_id)

# Get all tool messages with resources
tool_messages = history.get_messages_by_role("tool")
resources_created = [
    {
        "tool": msg.name,
        "resource_id": msg.resource_id,
        "tool_call_id": msg.tool_call_id
    }
    for msg in tool_messages
    if msg.resource_id
]

print(f"Created {len(resources_created)} resources this conversation")
```

## Migration Checklist

- [ ] Update `chat_service.py` to use `ChatHistory`
- [ ] Update `base_agent.py` to accept/return `ChatMessage` objects
- [ ] Update `chat_agent.py` message handling
- [ ] Update `llm_handler.py` chat logging to use `ChatTurn`
- [ ] Update tests to use new models
- [ ] Add type hints throughout using new models
- [ ] Update documentation

## Benefits Summary

1. **Type Safety**: IDE autocomplete and type checking
2. **Less Code**: No more manual dict construction
3. **Cleaner API**: Intuitive methods like `add_user_message()`
4. **Easy Conversion**: `to_openai_format()`, `to_db_format()`
5. **Better Logging**: `ChatTurn` for structured turn logging
6. **Analysis**: Built-in methods for conversation analysis
7. **Validation**: Pydantic validates all data automatically

