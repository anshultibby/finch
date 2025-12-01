"""
Simple integration test for strategy tools
Tests that the tools are properly defined and can be called
"""
import asyncio
import inspect
from modules.tools import tool_registry
from modules.agent.context import AgentContext
from unittest.mock import Mock

# Import definitions to trigger tool registration
import modules.tools.definitions


def test_strategy_tools_registered():
    """Test that all strategy tools are registered"""
    strategy_tools = [
        'create_trading_strategy',
        'backtest_strategy',
        'list_user_strategies',
        'compare_strategies'
    ]
    
    for tool_name in strategy_tools:
        tool = tool_registry.get_tool(tool_name)
        assert tool is not None, f"Tool {tool_name} not registered"
        assert tool.category == "strategy", f"Tool {tool_name} has wrong category"
        print(f"✓ {tool_name} registered correctly")


def test_create_trading_strategy_schema():
    """Test create_trading_strategy has correct schema"""
    tool = tool_registry.get_tool('create_trading_strategy')
    assert tool is not None
    
    # Get OpenAI schema
    schema = tool.to_openai_schema()
    
    # Verify structure
    assert schema["type"] == "function"
    assert "function" in schema
    assert schema["function"]["name"] == "create_trading_strategy"
    assert "description" in schema["function"]
    assert "parameters" in schema["function"]
    
    # Verify parameters
    params = schema["function"]["parameters"]
    assert params["type"] == "object"
    assert "properties" in params
    assert "required" in params
    
    # Check required parameters
    assert "strategy_description" in params["properties"]
    assert "strategy_name" in params["properties"]
    assert "strategy_description" in params["required"]
    assert "strategy_name" in params["required"]
    
    # Verify context is NOT in schema (it's hidden from LLM)
    assert "context" not in params["properties"]
    
    print("✓ create_trading_strategy schema is correct")
    print(f"  - Parameters: {list(params['properties'].keys())}")
    print(f"  - Required: {params['required']}")


def test_backtest_strategy_schema():
    """Test backtest_strategy has correct schema"""
    tool = tool_registry.get_tool('backtest_strategy')
    assert tool is not None
    
    schema = tool.to_openai_schema()
    params = schema["function"]["parameters"]
    
    # Check parameters
    assert "strategy_id" in params["properties"]
    assert "start_date" in params["properties"]
    assert "end_date" in params["properties"]
    assert "initial_capital" in params["properties"]
    
    # Only strategy_id should be required
    assert "strategy_id" in params["required"]
    assert "start_date" not in params["required"]  # Optional with default
    assert "end_date" not in params["required"]  # Optional with default
    
    print("✓ backtest_strategy schema is correct")
    print(f"  - Parameters: {list(params['properties'].keys())}")


def test_list_user_strategies_schema():
    """Test list_user_strategies has correct schema"""
    tool = tool_registry.get_tool('list_user_strategies')
    assert tool is not None
    
    schema = tool.to_openai_schema()
    params = schema["function"]["parameters"]
    
    # Check parameters
    assert "active_only" in params["properties"]
    assert params["properties"]["active_only"]["type"] == "boolean"
    
    # active_only should be optional (has default)
    assert "active_only" not in params["required"]
    
    print("✓ list_user_strategies schema is correct")


def test_compare_strategies_schema():
    """Test compare_strategies has correct schema"""
    tool = tool_registry.get_tool('compare_strategies')
    assert tool is not None
    
    schema = tool.to_openai_schema()
    params = schema["function"]["parameters"]
    
    # This tool has no required parameters (only context which is hidden)
    # So properties should be empty or minimal
    assert params["type"] == "object"
    
    print("✓ compare_strategies schema is correct")


def test_tool_signatures():
    """Test that all strategy tools have correct function signatures"""
    strategy_tools = [
        'create_trading_strategy',
        'backtest_strategy',
        'list_user_strategies',
        'compare_strategies'
    ]
    
    for tool_name in strategy_tools:
        tool = tool_registry.get_tool(tool_name)
        
        # Get function signature
        sig = inspect.signature(tool.handler)
        
        # Check for context parameter
        assert 'context' in sig.parameters, f"{tool_name} missing context parameter"
        
        # Verify context is of type AgentContext
        context_param = sig.parameters['context']
        assert context_param.annotation == AgentContext, f"{tool_name} context has wrong type annotation"
        
        # Verify all parameters are keyword-only
        keyword_only_params = [
            p for p in sig.parameters.values()
            if p.kind == inspect.Parameter.KEYWORD_ONLY
        ]
        assert len(keyword_only_params) > 0, f"{tool_name} must have keyword-only parameters"
        
        print(f"✓ {tool_name} has correct signature")


def test_tool_async_generators():
    """Test that tools that should be async generators are properly defined"""
    # These tools should be async generators (they yield SSE events)
    async_gen_tools = ['create_trading_strategy', 'backtest_strategy']
    
    for tool_name in async_gen_tools:
        tool = tool_registry.get_tool(tool_name)
        
        # Check that tool is marked as async
        assert tool.is_async, f"{tool_name} should be async"
        
        # Check that handler is an async generator function
        assert inspect.isasyncgenfunction(tool.handler), f"{tool_name} should be async generator"
        
        print(f"✓ {tool_name} is async generator")


def test_tool_sync_functions():
    """Test that tools that should be sync are properly defined"""
    # These tools are synchronous
    sync_tools = ['list_user_strategies', 'compare_strategies']
    
    for tool_name in sync_tools:
        tool = tool_registry.get_tool(tool_name)
        
        # Check that tool is NOT marked as async
        assert not tool.is_async, f"{tool_name} should be sync"
        
        print(f"✓ {tool_name} is synchronous")


async def test_tool_call_format():
    """Test that tools can be called with proper argument format"""
    # Create mock context
    mock_context = Mock(spec=AgentContext)
    mock_context.user_id = "test_user"
    mock_context.chat_id = "test_chat"
    mock_context.db = Mock()
    
    # Test that we can call the tool with the expected format
    # This tests the actual calling convention
    tool = tool_registry.get_tool('list_user_strategies')
    
    # Mock the CRUD function
    from unittest.mock import patch
    with patch('crud.strategy.get_user_strategies') as mock_get:
        mock_get.return_value = []
        
        # Call tool with keyword arguments
        try:
            result = tool.handler(context=mock_context, active_only=True)
            assert isinstance(result, dict)
            assert "success" in result
            print("✓ list_user_strategies can be called with correct format")
        except Exception as e:
            print(f"✗ Error calling list_user_strategies: {e}")
            raise


def print_all_tool_schemas():
    """Print all strategy tool schemas for inspection"""
    import json
    
    strategy_tools = [
        'create_trading_strategy',
        'backtest_strategy',
        'list_user_strategies',
        'compare_strategies'
    ]
    
    print("\n" + "="*80)
    print("STRATEGY TOOL SCHEMAS (for LLM)")
    print("="*80)
    
    for tool_name in strategy_tools:
        tool = tool_registry.get_tool(tool_name)
        schema = tool.to_openai_schema()
        
        print(f"\n{tool_name}:")
        print(json.dumps(schema, indent=2))
        print("-"*80)


if __name__ == "__main__":
    print("Testing Strategy Tools\n")
    
    # Run all tests
    test_strategy_tools_registered()
    print()
    
    test_create_trading_strategy_schema()
    print()
    
    test_backtest_strategy_schema()
    print()
    
    test_list_user_strategies_schema()
    print()
    
    test_compare_strategies_schema()
    print()
    
    test_tool_signatures()
    print()
    
    test_tool_async_generators()
    print()
    
    test_tool_sync_functions()
    print()
    
    # Skip this test - it requires database setup
    # asyncio.run(test_tool_call_format())
    # print()
    
    # Print all schemas for inspection
    print_all_tool_schemas()
    
    print("\n✅ All tests passed!")

