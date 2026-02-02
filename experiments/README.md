# Experiments Folder

This folder contains exploration scripts, tests, and demos for various features.

## Dome Matching Markets

Scripts for exploring and testing the Dome API matching markets functionality:

### Main Demo
- **`demo_dome_matching.py`** - Interactive comprehensive demo
  - Shows all matching market functionality
  - Demonstrates querying by sport/date, slug, and ticker
  - Optional arbitrage detection demo
  
### Exploration & Testing
- **`explore_dome_matching.py`** - Detailed API exploration
  - Tests all matching endpoints
  - Shows actual API response structures
  - Useful for understanding the API behavior
  
- **`test_matching_updated.py`** - Unit tests for matching functions
  - Tests sport/date queries
  - Tests slug/ticker queries
  - Validates response structures
  
- **`test_arbitrage_finder.py`** - Arbitrage detection tests
  - Tests the arbitrage opportunity finder
  - Shows how to use arbitrage detection
  
- **`test_imports.py`** - Module import verification
  - Ensures all imports work correctly
  - Validates module structure

## Running Scripts

All scripts should be run with the backend virtual environment:

```bash
# From project root
backend/venv/bin/python experiments/<script_name>.py
```

### Examples

```bash
# Interactive demo (recommended)
backend/venv/bin/python experiments/demo_dome_matching.py

# Full exploration
backend/venv/bin/python experiments/explore_dome_matching.py

# Quick tests
backend/venv/bin/python experiments/test_matching_updated.py
```

## Requirements

- `DOME_API_KEY` must be set in `backend/.env`
- Scripts automatically load environment variables
- Rate limiting: 1 request/second (free tier)

## Documentation

See parent directory for full documentation:
- `../DOME_MATCHING_README.md` - Quick start guide
- `../DOME_MATCHING_IMPLEMENTATION.md` - Complete technical docs
