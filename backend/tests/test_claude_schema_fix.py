"""
Test Claude/Anthropic JSON Schema Compatibility

Tests to verify:
1. Pydantic model schemas are properly cleaned for Claude
2. response_format is not used with Claude models
3. No $ref, $defs, or other incompatible fields in schemas
"""
import pytest
import json
from typing import List, Dict, Any
from pydantic import BaseModel, Field

# Import the schema generation functions
from modules.tools.decorator import _resolve_refs, _clean_schema_for_claude, _get_pydantic_schema


# Sample Pydantic models similar to strategy tools
class NestedDataSource(BaseModel):
    """Nested model to test $ref resolution"""
    type: str
    endpoint: str
    parameters: Dict[str, Any] = Field(default_factory=dict)


class StrategyRule(BaseModel):
    """Model with nested references"""
    order: int
    description: str
    data_sources: List[NestedDataSource] = Field(default_factory=list)
    decision_logic: str
    weight: float = 1.0


class ComplexParams(BaseModel):
    """Top-level model with multiple nested models"""
    name: str
    description: str
    rules: List[StrategyRule]


# ============================================================================
# Schema Cleaning Tests
# ============================================================================

def test_clean_schema_removes_incompatible_fields():
    """Test that _clean_schema_for_claude removes fields incompatible with Anthropic"""
    schema_with_bad_fields = {
        "type": "object",
        "$schema": "http://json-schema.org/draft-07/schema#",
        "title": "MyModel",
        "$defs": {
            "NestedModel": {"type": "object"}
        },
        "properties": {
            "field1": {"type": "string"},
            "field2": {"type": "integer", "title": "Field 2"}
        },
        "additionalProperties": False,
        "required": ["field1"]
    }
    
    cleaned = _clean_schema_for_claude(schema_with_bad_fields)
    
    # Check that bad fields are removed
    assert "$schema" not in cleaned
    assert "title" not in cleaned
    assert "$defs" not in cleaned
    assert "additionalProperties" not in cleaned
    
    # Check that good fields remain
    assert cleaned["type"] == "object"
    assert "properties" in cleaned
    assert "required" in cleaned
    assert cleaned["properties"]["field1"]["type"] == "string"


def test_clean_schema_recursive():
    """Test that cleaning works recursively on nested objects"""
    schema = {
        "type": "object",
        "title": "Root",
        "properties": {
            "nested": {
                "type": "object",
                "title": "Nested",
                "additionalProperties": True,
                "properties": {
                    "deep": {
                        "type": "string",
                        "title": "Deep"
                    }
                }
            }
        }
    }
    
    cleaned = _clean_schema_for_claude(schema)
    
    # Root level cleaned
    assert "title" not in cleaned
    
    # Nested level cleaned
    assert "title" not in cleaned["properties"]["nested"]
    assert "additionalProperties" not in cleaned["properties"]["nested"]
    
    # Deep level cleaned
    assert "title" not in cleaned["properties"]["nested"]["properties"]["deep"]


# ============================================================================
# $ref Resolution Tests
# ============================================================================

def test_resolve_refs_simple():
    """Test basic $ref resolution"""
    defs = {
        "SimpleType": {
            "type": "object",
            "properties": {
                "name": {"type": "string"}
            },
            "required": ["name"]
        }
    }
    
    schema = {
        "type": "object",
        "properties": {
            "item": {"$ref": "#/$defs/SimpleType"}
        }
    }
    
    resolved = _resolve_refs(schema, defs)
    
    # Check that $ref is replaced with actual definition
    assert "$ref" not in str(resolved)
    assert resolved["properties"]["item"]["type"] == "object"
    assert "name" in resolved["properties"]["item"]["properties"]


def test_resolve_refs_in_arrays():
    """Test $ref resolution in array items"""
    defs = {
        "Item": {
            "type": "object",
            "properties": {
                "id": {"type": "integer"}
            }
        }
    }
    
    schema = {
        "type": "object",
        "properties": {
            "items": {
                "type": "array",
                "items": {"$ref": "#/$defs/Item"}
            }
        }
    }
    
    resolved = _resolve_refs(schema, defs)
    
    # Check that array items $ref is resolved
    assert "$ref" not in str(resolved)
    assert resolved["properties"]["items"]["items"]["type"] == "object"
    assert "id" in resolved["properties"]["items"]["items"]["properties"]


def test_resolve_refs_nested():
    """Test nested $ref resolution (model referencing another model)"""
    defs = {
        "Address": {
            "type": "object",
            "properties": {
                "street": {"type": "string"},
                "city": {"type": "string"}
            }
        },
        "Person": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "address": {"$ref": "#/$defs/Address"}
            }
        }
    }
    
    schema = {
        "type": "object",
        "properties": {
            "person": {"$ref": "#/$defs/Person"}
        }
    }
    
    resolved = _resolve_refs(schema, defs)
    
    # Check that all $refs are resolved
    resolved_str = str(resolved)
    assert "$ref" not in resolved_str
    
    # Check structure is preserved
    assert resolved["properties"]["person"]["type"] == "object"
    assert "address" in resolved["properties"]["person"]["properties"]
    assert resolved["properties"]["person"]["properties"]["address"]["type"] == "object"
    assert "street" in resolved["properties"]["person"]["properties"]["address"]["properties"]


# ============================================================================
# Pydantic Model Schema Generation Tests
# ============================================================================

def test_pydantic_schema_no_refs():
    """Test that _get_pydantic_schema returns clean schemas without $refs"""
    schema = _get_pydantic_schema(NestedDataSource)
    
    assert schema is not None
    assert schema["type"] == "object"
    assert "properties" in schema
    assert "required" in schema
    
    # Check no bad fields in actual schema structure (not in string descriptions)
    def has_ref_keys(obj):
        """Recursively check if object has $ref or $defs keys"""
        if isinstance(obj, dict):
            if "$ref" in obj or "$defs" in obj:
                return True
            return any(has_ref_keys(v) for v in obj.values())
        elif isinstance(obj, list):
            return any(has_ref_keys(item) for item in obj)
        return False
    
    assert not has_ref_keys(schema), "Schema contains $ref or $defs keys"
    assert "title" not in schema


def test_pydantic_schema_with_nested_models():
    """Test complex Pydantic model with nested models"""
    schema = _get_pydantic_schema(ComplexParams)
    
    assert schema is not None
    assert schema["type"] == "object"
    
    # Check schema structure has no $ref or $defs keys (using helper from previous test)
    def has_ref_keys(obj):
        """Recursively check if object has $ref or $defs keys"""
        if isinstance(obj, dict):
            if "$ref" in obj or "$defs" in obj:
                return True
            return any(has_ref_keys(v) for v in obj.values())
        elif isinstance(obj, list):
            return any(has_ref_keys(item) for item in obj)
        return False
    
    assert not has_ref_keys(schema), "Schema contains $ref or $defs keys"
    
    # Check nested structure is inlined
    assert "rules" in schema["properties"]
    rules_schema = schema["properties"]["rules"]
    assert rules_schema["type"] == "array"
    assert "items" in rules_schema
    
    # Check items schema is inlined (not a reference)
    items_schema = rules_schema["items"]
    assert items_schema["type"] == "object"
    assert "properties" in items_schema
    assert "data_sources" in items_schema["properties"]


def test_pydantic_schema_deeply_nested():
    """Test that deeply nested models are properly resolved"""
    schema = _get_pydantic_schema(ComplexParams)
    
    # Navigate to deeply nested structure
    rules_items = schema["properties"]["rules"]["items"]
    data_sources = rules_items["properties"]["data_sources"]
    data_sources_items = data_sources["items"]
    
    # Check that even deep nesting has no references
    assert data_sources_items["type"] == "object"
    assert "properties" in data_sources_items
    assert "type" in data_sources_items["properties"]
    assert "endpoint" in data_sources_items["properties"]
    assert "parameters" in data_sources_items["properties"]
    
    # Ensure no $ref keys anywhere in the deep structure
    def has_ref_keys(obj):
        """Recursively check if object has $ref or $defs keys"""
        if isinstance(obj, dict):
            if "$ref" in obj or "$defs" in obj:
                return True
            return any(has_ref_keys(v) for v in obj.values())
        elif isinstance(obj, list):
            return any(has_ref_keys(item) for item in obj)
        return False
    
    assert not has_ref_keys(data_sources_items), "Deep structure contains $ref or $defs keys"


# ============================================================================
# Integration Test: Full Tool Schema
# ============================================================================

def test_full_tool_schema_generation():
    """Test that actual tool schemas are Claude-compatible"""
    from modules.tools.registry import tool_registry
    
    # Get a tool that uses Pydantic models (create_trading_strategy)
    tool = tool_registry.get_tool('create_trading_strategy')
    
    if tool:
        # Get OpenAI schema format
        openai_schema = tool.to_openai_schema()
        
        # Convert to JSON to check for invalid fields
        schema_json = json.dumps(openai_schema)
        
        # Verify no incompatible fields
        assert "$ref" not in schema_json, "Schema contains $ref references"
        assert "$defs" not in schema_json, "Schema contains $defs definitions"
        
        # Verify basic structure
        assert openai_schema["type"] == "function"
        assert "function" in openai_schema
        assert "parameters" in openai_schema["function"]
        
        parameters = openai_schema["function"]["parameters"]
        assert parameters["type"] == "object"
        assert "properties" in parameters
        assert "required" in parameters
        
        print(f"✅ Tool '{tool.name}' schema is Claude-compatible")
    else:
        pytest.skip("create_trading_strategy tool not found")


# ============================================================================
# Strategy Executor Response Format Test
# ============================================================================

def test_strategy_executor_no_response_format_for_claude():
    """Test that strategy_executor doesn't use response_format with Claude"""
    from services.strategy_executor import StrategyExecutor
    from modules.agent.llm_config import LLMConfig
    from unittest.mock import Mock, patch, AsyncMock
    
    executor = StrategyExecutor()
    
    # Mock LLMConfig to return Claude model
    with patch('services.strategy_executor.LLMConfig.from_config') as mock_config:
        mock_llm_config = Mock()
        mock_llm_config.model = "claude-3-5-sonnet-20241022"
        mock_config.return_value = mock_llm_config
        
        # Mock LLM handler
        with patch.object(executor.llm_handler, 'acompletion', new_callable=AsyncMock) as mock_acompletion:
            mock_response = Mock()
            mock_response.choices = [Mock()]
            mock_response.choices[0].message.content = json.dumps({
                "action": "CONTINUE",
                "signal": "NEUTRAL",
                "signal_value": 0.5,
                "reasoning": "Test",
                "confidence": 50
            })
            mock_acompletion.return_value = mock_response
            
            # Create a mock rule
            from models.strategy_v2 import StrategyRule
            rule = StrategyRule(
                order=1,
                description="Test rule",
                data_sources=[],
                decision_logic="Test logic",
                weight=1.0
            )
            
            # Execute the rule
            import asyncio
            result = asyncio.run(executor._execute_rule(
                rule=rule,
                ticker="AAPL",
                all_data={},
                context={"mode": "screening", "strategy_name": "Test", "position": None}
            ))
            
            # Check that acompletion was called
            assert mock_acompletion.called
            
            # Get the kwargs passed to acompletion
            call_kwargs = mock_acompletion.call_args[1]
            
            # Verify response_format is NOT in kwargs for Claude
            assert "response_format" not in call_kwargs, \
                "response_format should not be used with Claude models"
            
            print("✅ Strategy executor correctly avoids response_format for Claude")


def test_strategy_executor_uses_response_format_for_openai():
    """Test that strategy_executor DOES use response_format with OpenAI"""
    from services.strategy_executor import StrategyExecutor
    from modules.agent.llm_config import LLMConfig
    from unittest.mock import Mock, patch, AsyncMock
    
    executor = StrategyExecutor()
    
    # Mock LLMConfig to return OpenAI model
    with patch('services.strategy_executor.LLMConfig.from_config') as mock_config:
        mock_llm_config = Mock()
        mock_llm_config.model = "gpt-4o"
        mock_config.return_value = mock_llm_config
        
        # Mock LLM handler
        with patch.object(executor.llm_handler, 'acompletion', new_callable=AsyncMock) as mock_acompletion:
            mock_response = Mock()
            mock_response.choices = [Mock()]
            mock_response.choices[0].message.content = json.dumps({
                "action": "CONTINUE",
                "signal": "NEUTRAL",
                "signal_value": 0.5,
                "reasoning": "Test",
                "confidence": 50
            })
            mock_acompletion.return_value = mock_response
            
            # Create a mock rule
            from models.strategy_v2 import StrategyRule
            rule = StrategyRule(
                order=1,
                description="Test rule",
                data_sources=[],
                decision_logic="Test logic",
                weight=1.0
            )
            
            # Execute the rule
            import asyncio
            result = asyncio.run(executor._execute_rule(
                rule=rule,
                ticker="AAPL",
                all_data={},
                context={"mode": "screening", "strategy_name": "Test", "position": None}
            ))
            
            # Check that acompletion was called
            assert mock_acompletion.called
            
            # Get the kwargs passed to acompletion
            call_kwargs = mock_acompletion.call_args[1]
            
            # Verify response_format IS in kwargs for OpenAI
            assert "response_format" in call_kwargs, \
                "response_format should be used with OpenAI models"
            assert call_kwargs["response_format"] == {"type": "json_object"}
            
            print("✅ Strategy executor correctly uses response_format for OpenAI")


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "-s"])

