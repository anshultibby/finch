"""
Minimal test case to reproduce multi-turn conversation error with Claude
"""
import asyncio
import json
from database import AsyncSessionLocal
from models.chat_history import ChatHistory
from crud import chat_async

async def test_chat(chat_id: str):
    """Test loading and formatting messages for a multi-turn conversation"""
    async with AsyncSessionLocal() as db:
        # Load messages from database
        db_messages = await chat_async.get_chat_messages(db, chat_id)
        print(f"\n=== Database has {len(db_messages)} messages ===\n")
        
        # Show first 15 messages from DB
        for i, msg in enumerate(db_messages[:15]):
            print(f"DB Message {i} (seq={msg.sequence}):")
            print(f"  Role: {msg.role}")
            print(f"  Content length: {len(msg.content) if msg.content else 0}")
            print(f"  Has tool_calls: {bool(msg.tool_calls)}")
            if msg.tool_calls:
                print(f"    Tool call IDs: {[tc['id'] for tc in msg.tool_calls]}")
            print(f"  Tool call ID: {msg.tool_call_id or 'None'}")
            print()
        
        # Load into ChatHistory
        history = ChatHistory.from_db_messages(db_messages, chat_id, user_id="test")
        print(f"\n=== ChatHistory has {len(history.messages)} messages ===\n")
        
        # Show first 15 messages from ChatHistory
        for i, msg in enumerate(history.messages[:15]):
            print(f"History Message {i} (seq={msg.sequence}):")
            print(f"  Role: {msg.role}")
            print(f"  Content length: {len(msg.content) if msg.content and isinstance(msg.content, str) else 0}")
            print(f"  Has tool_calls: {bool(msg.tool_calls)}")
            if msg.tool_calls:
                print(f"    Tool call IDs: {[tc.id for tc in msg.tool_calls]}")
            print(f"  Tool call ID: {msg.tool_call_id or 'None'}")
            print()
        
        # Convert to OpenAI format
        openai_msgs = history.to_openai_format()
        print(f"\n=== OpenAI format has {len(openai_msgs)} messages ===\n")
        
        # Show first 5 messages in detail
        for i, msg in enumerate(openai_msgs[:5]):
            print(f"OpenAI Message {i}:")
            print(f"  Role: {msg['role']}")
            
            # Check content structure
            content = msg.get('content')
            if isinstance(content, list):
                print(f"  Content is list with {len(content)} blocks:")
                for j, block in enumerate(content):
                    print(f"    Block {j}: type={block.get('type')}")
                    if block.get('type') == 'tool_result':
                        print(f"      tool_use_id: {block.get('tool_use_id')}")
            elif isinstance(content, str):
                print(f"  Content is string: {content[:100]}...")
            else:
                print(f"  Content: {content}")
            
            # Check for tool_calls
            if msg.get('tool_calls'):
                print(f"  Has tool_calls: {len(msg['tool_calls'])}")
                for tc in msg['tool_calls']:
                    print(f"    - {tc['id']}: {tc['function']['name']}")
            
            # Check for tool_call_id
            if msg.get('tool_call_id'):
                print(f"  Tool call ID: {msg['tool_call_id']}")
            
            print()

if __name__ == "__main__":
    # Use the chat ID from the error
    chat_id = "7292a8ad-b411-40e3-b3dc-93e09fba83c9"
    asyncio.run(test_chat(chat_id))

