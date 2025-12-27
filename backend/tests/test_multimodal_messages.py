"""
Test multimodal message handling - ensures cache_control is never persisted to DB
and list format is used consistently throughout the codebase.
"""
import pytest
import json
import copy
from models.chat_history import ChatHistory, ChatMessage
from modules.agent.llm_stream import _add_cache_control_to_messages, _deep_copy_message


class TestCacheControlNotPersisted:
    """Ensure cache_control is added dynamically and never saved to DB."""
    
    def test_add_cache_control_does_not_mutate_original(self):
        """_add_cache_control_to_messages should not mutate the original messages."""
        original_messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"},
            {"role": "user", "content": [{"type": "text", "text": "How are you?"}]},
        ]
        
        # Deep copy to compare later
        original_copy = copy.deepcopy(original_messages)
        
        # Add cache control
        modified = _add_cache_control_to_messages(original_messages)
        
        # Original should be unchanged
        assert original_messages == original_copy, "Original messages were mutated!"
        
        # Modified should have cache_control on last message
        last_content = modified[-1]["content"]
        assert isinstance(last_content, list)
        assert "cache_control" in last_content[-1]
    
    def test_add_cache_control_to_list_content_does_not_mutate(self):
        """List content should not be mutated when adding cache_control."""
        tool_message = {
            "role": "tool",
            "tool_call_id": "test123",
            "name": "execute_code",
            "content": [{"type": "text", "text": '{"success": true}'}]
        }
        
        messages = [
            {"role": "user", "content": "Run some code"},
            {"role": "assistant", "content": "", "tool_calls": [{"id": "test123", "type": "function", "function": {"name": "execute_code", "arguments": "{}"}}]},
            tool_message,
        ]
        
        original_tool_content = copy.deepcopy(tool_message["content"])
        
        # Add cache control
        modified = _add_cache_control_to_messages(messages)
        
        # Original tool message content should be unchanged
        assert tool_message["content"] == original_tool_content
        assert "cache_control" not in tool_message["content"][0]
    
    def test_tool_message_in_multi_turn_not_mutated(self):
        """
        Simulate the exact bug scenario: tool messages added to conversation,
        then cache control added for LLM call. Original should stay clean.
        """
        # This is what happens in base_agent.py run_tool_loop_streaming
        messages = [
            {"role": "user", "content": "What is TSLA price?"},
        ]
        
        # Assistant responds with tool call
        assistant_msg = {
            "role": "assistant",
            "content": "",
            "tool_calls": [{
                "id": "toolu_123",
                "type": "function",
                "function": {"name": "execute_code", "arguments": "{}"}
            }]
        }
        messages.append(assistant_msg)
        
        # Tool result comes back (from executor) - using list format
        tool_msg = {
            "role": "tool",
            "tool_call_id": "toolu_123",
            "name": "execute_code",
            "content": [{"type": "text", "text": '{"success": true, "stdout": "$475.19"}'}]
        }
        messages.append(tool_msg)
        
        # Now LLM is called again - cache control is added
        llm_messages = _add_cache_control_to_messages(messages)
        
        # The original tool message should NOT have cache_control
        assert "cache_control" not in messages[2]["content"][0], \
            "Original tool message was mutated with cache_control!"
        
        # But the copy sent to LLM should have it
        assert "cache_control" in llm_messages[2]["content"][0]


class TestMultimodalToolMessages:
    """Test that tool messages use list format consistently."""
    
    def test_to_openai_format_preserves_list_content(self):
        """List content should be preserved in OpenAI format."""
        msg = ChatMessage(
            role="tool",
            tool_call_id="test123",
            name="execute_code",
            content=[{"type": "text", "text": '{"success": true}'}]
        )
        
        openai_format = msg.to_openai_format()
        
        assert openai_format["role"] == "tool"
        assert openai_format["tool_call_id"] == "test123"
        assert isinstance(openai_format["content"], list)
        assert openai_format["content"][0]["type"] == "text"
    
    def test_chat_history_to_openai_format_with_tool_messages(self):
        """Full conversation with tool messages should maintain list format."""
        history = ChatHistory()
        history.add_user_message("Run some code")
        history.add_message(ChatMessage(
            role="assistant",
            content="",
            tool_calls=[{
                "id": "test123",
                "type": "function", 
                "function": {"name": "execute_code", "arguments": "{}"}
            }]
        ))
        history.add_message(ChatMessage(
            role="tool",
            tool_call_id="test123",
            name="execute_code",
            content=[{"type": "text", "text": '{"success": true}'}]
        ))
        history.add_message(ChatMessage(
            role="assistant",
            content="Code executed successfully!"
        ))
        
        openai_messages = history.to_openai_format()
        
        # Tool message should have list content
        tool_msg = openai_messages[2]
        assert tool_msg["role"] == "tool"
        assert isinstance(tool_msg["content"], list)


class TestHistoryLimitPreservesToolPairs:
    """Test that history limiting doesn't break tool call/result pairs."""
    
    def test_limit_does_not_orphan_tool_results(self):
        """
        When limiting history, tool results must have their corresponding
        assistant message with tool_calls included.
        
        This was the root cause of the Anthropic API error:
        "unexpected tool_use_id found in tool_result blocks"
        """
        history = ChatHistory()
        
        # Build a conversation with multiple tool uses
        history.add_user_message("First question")
        history.add_message(ChatMessage(role="assistant", content="First answer"))
        
        history.add_user_message("Run code")
        history.add_message(ChatMessage(
            role="assistant",
            content="",
            tool_calls=[{"id": "tool1", "type": "function", "function": {"name": "execute_code", "arguments": "{}"}}]
        ))
        history.add_message(ChatMessage(
            role="tool",
            tool_call_id="tool1",
            name="execute_code",
            content=[{"type": "text", "text": "result1"}]
        ))
        history.add_message(ChatMessage(role="assistant", content="Code done!"))
        
        history.add_user_message("Another question")
        history.add_message(ChatMessage(role="assistant", content="Another answer"))
        
        # Total: 8 messages
        # If we limit to 3, naive slicing would give: [tool_result, assistant, user]
        # which is INVALID because tool_result has no preceding tool_use
        
        messages = history.to_openai_format(limit=3)
        
        # Verify no orphaned tool results
        for i, msg in enumerate(messages):
            if msg["role"] == "tool":
                # There must be a preceding assistant message with matching tool_call
                tool_call_id = msg["tool_call_id"]
                found_tool_use = False
                for j in range(i):
                    prev = messages[j]
                    if prev["role"] == "assistant" and prev.get("tool_calls"):
                        for tc in prev["tool_calls"]:
                            if tc["id"] == tool_call_id:
                                found_tool_use = True
                                break
                assert found_tool_use, f"Tool result {tool_call_id} has no preceding tool_use!"
    
    def test_limit_starts_from_safe_boundary(self):
        """Limiting should start from a user message or clean assistant message."""
        history = ChatHistory()
        
        history.add_user_message("Q1")
        history.add_message(ChatMessage(role="assistant", content="A1"))
        history.add_user_message("Q2")
        history.add_message(ChatMessage(
            role="assistant",
            content="",
            tool_calls=[{"id": "t1", "type": "function", "function": {"name": "test", "arguments": "{}"}}]
        ))
        history.add_message(ChatMessage(role="tool", tool_call_id="t1", name="test", content="result"))
        history.add_message(ChatMessage(role="assistant", content="A2"))
        
        # Limit to 4 - should include from Q2 onwards (not start from tool result)
        messages = history.to_openai_format(limit=4)
        
        # First message should be user or clean assistant, never tool
        assert messages[0]["role"] in ("user", "assistant")
        if messages[0]["role"] == "assistant":
            assert "tool_calls" not in messages[0] or not messages[0]["tool_calls"]


class TestDeepCopyMessage:
    """Test _deep_copy_message utility."""
    
    def test_deep_copy_nested_content(self):
        """Deep copy should handle nested structures."""
        msg = {
            "role": "tool",
            "content": [
                {"type": "text", "text": "test"},
                {"type": "image", "source": {"type": "base64", "data": "abc"}}
            ]
        }
        
        copied = _deep_copy_message(msg)
        
        # Modify the copy
        copied["content"][0]["text"] = "modified"
        copied["content"][1]["source"]["data"] = "xyz"
        
        # Original should be unchanged
        assert msg["content"][0]["text"] == "test"
        assert msg["content"][1]["source"]["data"] == "abc"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

