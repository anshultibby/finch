"""
Helper utilities for building mock response objects
"""
from typing import List, Dict, Any


class MockToolCall:
    """Mock tool call object matching OpenAI's structure"""
    def __init__(self, tc_data: Dict[str, Any]):
        self.id = tc_data["id"]
        self.type = tc_data.get("type", "function")
        self.function = type('obj', (object,), {
            'name': tc_data["function"]["name"],
            'arguments': tc_data["function"]["arguments"]
        })()


class MockMessage:
    """Mock message object with tool calls"""
    def __init__(self, content: str, tool_calls: List[Dict[str, Any]]):
        self.content = content
        self.tool_calls = [MockToolCall(tc) for tc in tool_calls] if tool_calls else None


class MockResponse:
    """Mock LLM response object"""
    def __init__(self, content: str = "", tool_calls: List[Dict[str, Any]] = None):
        self.choices = [type('obj', (object,), {
            'message': MockMessage(content, tool_calls or [])
        })()]


def build_mock_response_from_stream(
    full_content: str,
    accumulated_tool_calls: List[Dict[str, Any]]
) -> MockResponse:
    """
    Build a mock response object from accumulated stream data
    
    Args:
        full_content: Accumulated text content
        accumulated_tool_calls: List of accumulated tool call dicts
        
    Returns:
        MockResponse object compatible with tool handler
    """
    return MockResponse(full_content, accumulated_tool_calls)

