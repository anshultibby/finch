#!/usr/bin/env python3
"""
Analyze cache usage from conversation logs

Usage:
    python analyze_cache_usage.py <path_to_conversation.json>
"""
import sys
import json
from pathlib import Path
from typing import Dict, Any, List


def analyze_cache_usage(conversation_file: Path):
    """Analyze and visualize cache usage from a conversation log"""
    with open(conversation_file) as f:
        data = json.load(f)
    
    print("=" * 80)
    print(f"CACHE ANALYSIS: {conversation_file.parent.name}")
    print("=" * 80)
    print()
    
    # Basic info
    print(f"Model: {data.get('model', 'unknown')}")
    print(f"Total messages: {data.get('message_count', 0)}")
    print(f"Last updated: {data.get('updated_at', 'unknown')}")
    print()
    
    # Cache summary
    cache_summary = data.get("cache_summary")
    if not cache_summary:
        print("⚠️  No cache summary found in this conversation")
        return
    
    this_turn = cache_summary.get("this_turn", {})
    cumulative = cache_summary.get("cumulative", {})
    history = cache_summary.get("history", [])
    
    print("LATEST TURN CACHE STATS:")
    print(f"  📖 Read from cache: {this_turn.get('read_tokens', 0):,} tokens")
    print(f"  ✏️  Wrote to cache: {this_turn.get('creation_tokens', 0):,} tokens")
    print(f"  📊 Cache efficiency: {this_turn.get('cache_efficiency', '0%')}")
    print(f"  {'✅' if this_turn.get('cache_hit') else '❌'} Cache hit: {this_turn.get('cache_hit', False)}")
    print()
    
    print("CUMULATIVE STATS:")
    print(f"  📦 Total cache size: {cumulative.get('total_cache_size', 0):,} tokens")
    print(f"  📖 Total tokens read: {cumulative.get('total_tokens_read', 0):,} tokens")
    print(f"  📊 Avg efficiency: {cumulative.get('avg_cache_efficiency', '0%')}")
    print()
    
    if len(history) > 1:
        print("CACHE GROWTH OVER TIME:")
        print()
        print(f"{'Turn':<6} {'Messages':<10} {'Created':<12} {'Read':<12} {'Cumulative':<15} {'Hit':<6}")
        print("-" * 80)
        
        cumulative_size = 0
        for entry in history:
            cumulative_size += entry.get("creation_tokens", 0)
            print(
                f"{entry.get('turn', 0):<6} "
                f"{entry.get('message_count', 0):<10} "
                f"{entry.get('creation_tokens', 0):>10,}  "
                f"{entry.get('read_tokens', 0):>10,}  "
                f"{cumulative_size:>13,}  "
                f"{'✅' if entry.get('cache_hit') else '❌':<6}"
            )
        print()
        
        # Analysis
        print("CACHE GROWTH ANALYSIS:")
        if len(history) >= 2:
            # Check if cache is growing appropriately
            creation_tokens = [e.get("creation_tokens", 0) for e in history]
            read_tokens = [e.get("read_tokens", 0) for e in history]
            
            avg_creation = sum(creation_tokens) / len(creation_tokens)
            avg_read = sum(read_tokens) / len(read_tokens)
            
            print(f"  📈 Avg cache creation per turn: {avg_creation:,.0f} tokens")
            print(f"  📖 Avg cache read per turn: {avg_read:,.0f} tokens")
            print()
            
            # Check if cache is growing efficiently
            if avg_read > avg_creation * 2:
                print("  ✅ EXCELLENT: Cache is being reused more than it's growing!")
            elif avg_read > avg_creation:
                print("  ✅ GOOD: Cache reads exceed new cache creation")
            elif avg_creation > 0:
                print("  ⚠️  SUBOPTIMAL: Cache growing faster than it's being reused")
                print("     Consider adding more cache breakpoints or adjusting placement")
            
            # Check for increasing cache reads over time
            if len(read_tokens) >= 3:
                recent_avg = sum(read_tokens[-3:]) / 3
                early_avg = sum(read_tokens[:3]) / 3 if len(read_tokens) >= 3 else read_tokens[0]
                
                if recent_avg > early_avg * 1.5:
                    print("  ✅ Cache reads are growing over time (good!)")
                elif recent_avg < early_avg:
                    print("  ⚠️  Cache reads decreasing (may indicate cache breakpoint issues)")
    
    print()
    print("=" * 80)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python analyze_cache_usage.py <path_to_conversation.json>")
        sys.exit(1)
    
    conv_file = Path(sys.argv[1])
    if not conv_file.exists():
        print(f"Error: File not found: {conv_file}")
        sys.exit(1)
    
    analyze_cache_usage(conv_file)
