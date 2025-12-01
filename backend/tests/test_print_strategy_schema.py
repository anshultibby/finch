"""
Print the exact OpenAI schema for strategy tools
"""
import json
import sys
sys.path.insert(0, '.')

from modules.tools import tool_registry
import modules.tools.definitions  # Trigger registration

def print_tool_schema(tool_name):
    """Print the OpenAI schema for a specific tool"""
    tool = tool_registry.get_tool(tool_name)
    
    if not tool:
        print(f"❌ Tool '{tool_name}' not found!")
        return
    
    schema = tool.to_openai_schema()
    
    print(f"\n{'='*80}")
    print(f"TOOL: {tool_name}")
    print(f"{'='*80}")
    print(json.dumps(schema, indent=2))
    print(f"{'='*80}\n")
    
    # Extract and show key info
    params = schema['function']['parameters']
    print(f"📋 Parameter Summary:")
    print(f"  Required: {params.get('required', [])}")
    print(f"  Properties: {list(params.get('properties', {}).keys())}")
    
    for prop_name, prop_info in params.get('properties', {}).items():
        print(f"\n  {prop_name}:")
        print(f"    Type: {prop_info.get('type')}")
        print(f"    Description: {prop_info.get('description', 'N/A')[:100]}...")
    
    print("\n")


if __name__ == "__main__":
    print("\n" + "="*80)
    print("ALL TOOL SCHEMAS - Sent to LLM")
    print("="*80)
    
    # Get all registered tools
    all_tools = tool_registry.list_tools()
    
    print(f"\n📊 Total tools registered: {len(all_tools)}\n")
    
    # Group by category
    by_category = {}
    for tool in all_tools:
        category = tool.category or 'uncategorized'
        if category not in by_category:
            by_category[category] = []
        by_category[category].append(tool.name)
    
    print("Tools by category:")
    for category, tools in sorted(by_category.items()):
        print(f"  {category}: {', '.join(tools)}")
    
    print("\n" + "="*80 + "\n")
    
    # Print each tool schema
    for tool in all_tools:
        print_tool_schema(tool.name)
    
    # Show example of correct call format
    print("\n" + "="*80)
    print("CORRECT CALL FORMAT EXAMPLES")
    print("="*80)
    
    print("""
For create_trading_strategy:
{
  "name": "create_trading_strategy",
  "arguments": {
    "strategy_name": "Insider + RSI Oversold",
    "strategy_description": "Buy stocks when 3 or more insiders buy over $500K total in the last 30 days AND the stock's RSI is below 30. Exit when RSI goes above 70 OR if the stock drops 12% (stop loss) OR after 60 days."
  }
}

WRONG (what the LLM is currently doing):
{
  "name": "create_trading_strategy",
  "arguments": {
    "params": "{...complex nested JSON...}"
  }
}
    """)

