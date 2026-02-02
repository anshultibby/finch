#!/usr/bin/env python3
"""Quick test that all imports work correctly"""
import sys
import os

# Add backend to path (we're in experiments/ subfolder)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

print("Testing imports...")

# Test direct imports
from modules.tools.servers.dome.matching import (
    get_sports_matching_markets,
    get_sport_by_date, 
    find_arbitrage_opportunities
)
print("✅ Direct matching imports work")

# Test module imports
from modules.tools.servers import dome
print("✅ Dome module import works")

# Test submodule access
print(f"✅ dome.matching module: {dome.matching}")
print(f"✅ dome.polymarket module: {dome.polymarket}")
print(f"✅ dome.kalshi module: {dome.kalshi}")

# Test function access
print(f"✅ dome.matching.get_sport_by_date: {dome.matching.get_sport_by_date}")
print(f"✅ dome.matching.find_arbitrage_opportunities: {dome.matching.find_arbitrage_opportunities}")

print("\n✅ All imports successful!")
