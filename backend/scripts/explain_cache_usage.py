#!/usr/bin/env python3
"""
Explain cache usage from conversation logs.

Shows how cache works and why new_input_tokens != cache_creation_tokens
"""
import json
from pathlib import Path

def analyze_conversation(conv_file: Path):
    """Analyze cache usage in a conversation"""
    with open(conv_file) as f:
        data = json.load(f)
    
    cache_summary = data.get("cache_summary", {})
    if not cache_summary:
        print("❌ No cache summary found")
        return
    
    print("=" * 80)
    print(f"📊 Cache Analysis: {conv_file.parent.name}")
    print("=" * 80)
    
    # Explain the metrics
    print("\n📖 UNDERSTANDING THE METRICS:\n")
    print("1. NEW INPUT TOKENS:")
    print("   = Everything sent that wasn't already cached")
    print("   = User's new message + any uncached context + tool results")
    print()
    print("2. CACHE CREATION TOKENS:")
    print("   = NEW content being added to the cache this turn")
    print("   = Only includes content marked with cache_control breakpoints")
    print()
    print("3. CACHE READ TOKENS:")
    print("   = Content retrieved from cache (90% cheaper)")
    print("   = System prompt + tools + previously cached messages")
    print()
    print("💡 WHY DIFFERENT?")
    print("   Not all new input gets cached! Only ~last 2 messages have cache")
    print("   breakpoints, so most conversation history is sent as 'new input'")
    print("   but doesn't get added to the cache.")
    print()
    
    # Show turn-by-turn breakdown
    history = cache_summary.get("history", [])
    if history:
        print("\n📈 TURN-BY-TURN BREAKDOWN:\n")
        print(f"{'Turn':<6} {'New In':<10} {'Cached':<10} {'Cache Write':<12} {'Cache %':<10} {'Savings':<10}")
        print("-" * 80)
        
        for entry in history:
            turn = entry["turn"]
            new_in = entry["new_input_tokens"]
            cached = entry["cache_read_tokens"]
            cache_write = entry["cache_creation_tokens"]
            cache_pct = entry["cache_hit_rate"]
            savings = entry["cost_savings"]
            
            print(f"{turn:<6} {new_in:<10,} {cached:<10,} {cache_write:<12,} {cache_pct:<10} {savings:<10}")
        
        # Explain what's happening
        print("\n🔍 WHAT'S HAPPENING:\n")
        if len(history) > 1:
            turn1 = history[0]
            turn2 = history[1]
            
            print(f"Turn 1 (Cold Start):")
            print(f"  - Created {turn1['cache_creation_tokens']:,} token cache (system + tools + last 2 msgs)")
            print(f"  - Everything was 'new input' (no cache yet)")
            print()
            print(f"Turn 2 (Cache Working):")
            print(f"  - Read {turn2['cache_read_tokens']:,} from cache (system + tools + some msgs)")
            print(f"  - Sent {turn2['new_input_tokens']:,} new tokens (user msg + uncached msgs)")
            print(f"  - Added {turn2['cache_creation_tokens']:,} to cache (ONLY new msg with breakpoint)")
            print()
            print(f"❓ Why is new_input ({turn2['new_input_tokens']:,}) > cache_write ({turn2['cache_creation_tokens']:,})?")
            print(f"   Because {turn2['new_input_tokens'] - turn2['cache_creation_tokens']:,} tokens were sent as 'new'")
            print(f"   but DON'T have cache_control breakpoints (older messages in conversation)")
            print()
        
        # Show potential improvement
        cumulative = cache_summary.get("cumulative", {})
        current_savings = float(cumulative.get("avg_cost_savings", "0%").rstrip('%'))
        
        print("\n💰 COST ANALYSIS:\n")
        print(f"Current average savings: {current_savings:.1f}%")
        print()
        print("🚀 OPTIMIZATION OPPORTUNITY:")
        print("   With better cache strategy (caching more history):")
        print("   - Could cache older messages instead of re-sending as 'new input'")
        print("   - Target: 85-90% cache hit rate (vs current ~75-85%)")
        print("   - Estimated additional savings: 10-15% on input tokens")
        print()

if __name__ == "__main__":
    # Analyze the conversation in context
    conv_file = Path(__file__).parent.parent / "chat_logs/20251210/141519_ccff8418-82f4-4661-b384-043ed244ebba/conversation.json"
    
    if conv_file.exists():
        analyze_conversation(conv_file)
    else:
        print(f"❌ Conversation file not found: {conv_file}")
