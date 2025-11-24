#!/usr/bin/env python3
"""Test that all imports work correctly"""

print("Testing imports...")

# Test 1: Import AgentContext
print("1. Importing AgentContext...")
from modules.agent.context import AgentContext
print("   ✓ AgentContext imported")

# Test 2: Import tools models
print("2. Importing Tool from models...")
from modules.tools.models import Tool
print("   ✓ Tool imported")

# Test 3: Import registry
print("3. Importing ToolRegistry...")
from modules.tools.registry import ToolRegistry, tool_registry
print("   ✓ ToolRegistry imported")

# Test 4: Import runner
print("4. Importing ToolRunner...")
from modules.tools.runner import ToolRunner, tool_runner
print("   ✓ ToolRunner imported")

# Test 5: Import base_agent
print("5. Importing BaseAgent...")
from modules.agent.base_agent import BaseAgent
print("   ✓ BaseAgent imported")

# Test 6: Import ChatService
print("6. Importing ChatService...")
from modules.chat_service import ChatService
print("   ✓ ChatService imported")

# Test 7: Import routes
print("7. Importing routes...")
from routes import chat_router, snaptrade_router, resources_router
print("   ✓ Routes imported")

print("\n✓ All imports successful!")

