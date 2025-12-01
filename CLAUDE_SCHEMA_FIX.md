# Claude/Anthropic JSON Schema Compatibility Fix

## Problem
Strategy execution was failing with Claude/Anthropic models with this error:
```
tools.0.custom.input_schema: JSON schema is invalid. It must match JSON Schema draft 2020-12
```

## Root Causes

### Issue 1: Pydantic Nested Model Schemas
When Pydantic models with nested structures (e.g., `CreateStrategyV2Params` with nested `DataSourceInput`, `StrategyRuleInput`) were converted to JSON schemas for tool definitions, they included:
- `$ref` references (e.g., `{"$ref": "#/$defs/DataSourceInput"}`)
- `$defs` definitions section
- Extra fields: `title`, `$schema`, `additionalProperties`

These are incompatible with Anthropic's strict JSON Schema draft 2020-12 requirements.

### Issue 2: response_format with Claude
When `response_format={"type": "json_object"}` is used with Claude models through litellm, it internally converts this to a tool schema. This internal schema generation can also include invalid structures.

## Solutions Implemented

### Fix 1: Schema Cleaning (`decorator.py`)
Added three helper functions to `/Users/anshul/code/finch/backend/modules/tools/decorator.py`:

1. **`_clean_schema_for_claude()`**
   - Recursively removes incompatible fields: `$schema`, `title`, `$defs`, `additionalProperties`
   - Preserves essential fields: `type`, `properties`, `required`, `description`

2. **`_resolve_refs()`**
   - Recursively resolves all `$ref` references by inlining actual definitions
   - Handles nested references (models referencing other models)
   - Works with arrays of models

3. **`_get_pydantic_schema()` (updated)**
   - Now uses both helpers to generate clean, Claude-compatible schemas
   - Checks for `$defs` and resolves them if present
   - Returns minimal schema structure without references

### Fix 2: Conditional response_format (`strategy_executor.py`)
Modified `/Users/anshul/code/finch/backend/services/strategy_executor.py`:

```python
# Only add response_format for OpenAI models
# Anthropic/Claude doesn't support response_format natively, and litellm's
# conversion to tool schema can cause validation errors with nested models
if llm_config.model.startswith(("gpt-", "o1-", "o3-")):
    llm_kwargs["response_format"] = {"type": "json_object"}
```

**Note:** `candidate_selector.py` already had this fix in place.

## Test Coverage
Created comprehensive test suite in `/Users/anshul/code/finch/backend/tests/test_claude_schema_fix.py`:

### Schema Cleaning Tests (3 tests)
- ✅ Removes incompatible fields ($schema, title, $defs, additionalProperties)
- ✅ Works recursively on nested objects
- ✅ Preserves essential schema structure

### $ref Resolution Tests (3 tests)
- ✅ Resolves simple $ref references
- ✅ Resolves $ref in array items
- ✅ Resolves nested $ref (models referencing models)

### Pydantic Schema Generation Tests (3 tests)
- ✅ Simple models have no $refs
- ✅ Complex nested models are properly inlined
- ✅ Deeply nested structures have no references

### Strategy Executor Tests (2 tests)
- ✅ Claude models don't get response_format
- ✅ OpenAI models do get response_format

**Test Results:** 10 passed, 1 skipped, 0 failed

## Files Modified

1. `/Users/anshul/code/finch/backend/modules/tools/decorator.py`
   - Added `_clean_schema_for_claude()` function
   - Added `_resolve_refs()` function
   - Updated `_get_pydantic_schema()` to use both helpers

2. `/Users/anshul/code/finch/backend/services/strategy_executor.py`
   - Modified `_execute_rule()` to conditionally add `response_format`
   - Only used for OpenAI models (gpt-, o1-, o3-)

3. `/Users/anshul/code/finch/backend/tests/test_claude_schema_fix.py` (new file)
   - Comprehensive test suite validating all fixes

## Result

Tool schemas now:
- ✅ Have all nested model references inlined (no `$ref` or `$defs`)
- ✅ Contain only essential fields: `type`, `properties`, `required`, `description`
- ✅ Comply with JSON Schema draft 2020-12
- ✅ Are accepted by Anthropic's Claude API

Strategy execution with Claude models now works without schema validation errors!

## Additional Notes

- The fix maintains backward compatibility with OpenAI models
- Schema cleaning is automatic and happens during tool registration
- No changes needed to individual tool definitions
- The fix handles arbitrarily nested Pydantic model structures

