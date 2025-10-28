# Agent Refactor Plan

## Current State
- **agent.py**: 1069 lines, single monolithic file
- Hard to read, test, and maintain

## New Structure

```
backend/
  agent/
    __init__.py               # Public exports
    chat_agent.py             # Main agent class (< 300 lines)
    prompts.py                # System prompts ✅ DONE
    tool_executor.py          # Tool execution ✅ DONE
    stream_handler.py         # Streaming helpers
    response_builder.py       # Mock response builders
    message_processor.py      # History cleaning & validation
```

## Files Created

### ✅ agent/prompts.py (103 lines)
- `FINCH_SYSTEM_PROMPT`: Main system prompt
- `build_system_prompt()`: Dynamic context builder

### ✅ agent/tool_executor.py (183 lines)
- `execute_tool()`: Clean tool dispatcher
- No switch statement bloat
- One function per tool with logging

## Benefits

### 1. **Readability**
- Each file has single responsibility
- Easy to find specific logic
- Clear module boundaries

### 2. **Maintainability**
- Change prompts without touching agent logic
- Add tools without modifying core code
- Test components independently

### 3. **Code Quality**
- Smaller files (< 300 lines each)
- Better organization
- Easier code reviews

### 4. **Testing**
- Unit test each module separately
- Mock dependencies cleanly
- Fast, focused tests

## Next Steps

1. Create `response_builder.py` - Mock response object builders
2. Create `stream_handler.py` - Streaming accumulation logic
3. Create `message_processor.py` - History validation
4. Rewrite `chat_agent.py` - Main class using all modules
5. Update imports in `main.py`
6. Delete old `agent.py`

## Migration Strategy

### Phase 1: Create new modules (✅ Done for 2/6)
- Keep old agent.py working
- Build new structure alongside

### Phase 2: Build new chat_agent.py
- Import from new modules
- Keep same public API
- Internal refactor only

### Phase 3: Update imports
- Change `from agent import ChatAgent`
- To `from agent import ChatAgent` (same!)
- No changes to calling code needed

### Phase 4: Cleanup
- Delete old agent.py
- Run tests
- Celebrate! 🎉

## File Size Comparison

| File | Before | After |
|------|--------|-------|
| agent.py | 1069 lines | DELETED |
| agent/chat_agent.py | N/A | ~250 lines |
| agent/prompts.py | N/A | 103 lines |
| agent/tool_executor.py | N/A | 183 lines |
| agent/stream_handler.py | N/A | ~100 lines |
| agent/response_builder.py | N/A | ~60 lines |
| agent/message_processor.py | N/A | ~80 lines |
| **Total** | **1069 lines** | **~776 lines** (27% reduction) |

Plus better organization and testability!

## Design Principles

1. **Single Responsibility**: Each module does ONE thing well
2. **DRY**: No duplication between streaming/non-streaming
3. **Clean Interfaces**: Simple function signatures
4. **Type Hints**: Full typing for better IDE support
5. **Logging**: Consistent, informative logs
6. **Error Handling**: Graceful degradation

## Status

- [x] Create agent/ directory
- [x] Create prompts.py
- [x] Create tool_executor.py
- [ ] Create response_builder.py
- [ ] Create stream_handler.py
- [ ] Create message_processor.py
- [ ] Create chat_agent.py
- [ ] Update imports
- [ ] Delete old agent.py
- [ ] Test everything

