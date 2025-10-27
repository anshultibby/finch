# Backend Tests

This directory contains test scripts for the Finch backend services.

## Running Tests

### All Insider Trading Tests
```bash
cd backend
python -m tests.test_insider_trading
```

### Buy Transactions Analysis Test
```bash
cd backend
python -m tests.test_buy_transactions
```

## Test Files

- `test_insider_trading.py` - Comprehensive tests for insider trading API functionality
  - Senate trades
  - House trades  
  - Corporate insider trades
  - Ticker-specific activity
  - Portfolio analysis

- `test_buy_transactions.py` - Analyzes the last 100 buy transactions
  - Fetches P-Purchase type transactions
  - Analyzes output size and content
  - Generates detailed statistics
  - Saves full output to `buy_transactions_output.json`

## Output Files

Test output files are saved in this directory:
- `buy_transactions_output.json` - Full JSON output from buy transactions test

