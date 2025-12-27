"""Quick test to verify MessageEndEvent includes tool_calls"""
from models.sse import MessageEndEvent

def test_message_end_event_includes_tool_calls():
    """MessageEndEvent must include tool_calls in model_dump output"""
    tool_calls = [{"id": "test123", "type": "function", "function": {"name": "test", "arguments": "{}"}}]
    
    event = MessageEndEvent(content="", tool_calls=tool_calls)
    data = event.model_dump()
    
    assert "tool_calls" in data, "tool_calls missing from MessageEndEvent!"
    assert data["tool_calls"] == tool_calls, "tool_calls not preserved!"
    print("✅ MessageEndEvent correctly includes tool_calls")

def test_message_end_event_without_tool_calls():
    """MessageEndEvent should work without tool_calls too"""
    event = MessageEndEvent(content="Hello")
    data = event.model_dump()
    
    assert data["content"] == "Hello"
    assert data["tool_calls"] is None
    print("✅ MessageEndEvent works without tool_calls")

if __name__ == "__main__":
    test_message_end_event_includes_tool_calls()
    test_message_end_event_without_tool_calls()
    print("\n🎉 All tests passed!")

