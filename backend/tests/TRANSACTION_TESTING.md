# Testing SnapTrade Transaction Fetching

## Problem
The chat showed portfolio positions but no transaction history. These tests help debug why.

## Quick Test (Easiest)

### Step 1: Find Your User ID

**Option A - From Browser Console:**
1. Open frontend (http://localhost:3000)
2. Open browser DevTools (F12)
3. Look for `user_id` in console logs when you log in

**Option B - From Database:**
```bash
cd /Users/anshul/code/finch/backend
source venv/bin/activate

# Connect to database and query
python -c "
from database import SessionLocal
from crud.snaptrade_user import get_snaptrade_user
db = SessionLocal()
users = db.execute('SELECT user_id, is_connected FROM snaptrade_users LIMIT 5').fetchall()
for user in users:
    print(f'User ID: {user[0]}, Connected: {user[1]}')
db.close()
"
```

### Step 2: Run the Quick Test

```bash
cd /Users/anshul/code/finch/backend
./scripts/test_transactions.sh YOUR_USER_ID_HERE
```

This will:
- Check if user is connected
- Fetch all accounts
- Try different date ranges (30d, 90d, 1y, 2y)
- Show you what activities are found
- Break down by transaction type

## Full Test Suite

For comprehensive testing:

```bash
cd /Users/anshul/code/finch/backend
source venv/bin/activate

# Edit the file first to set your user_id
# Open tests/test_transaction_sync.py and replace "YOUR_USER_ID_HERE" with your actual user_id

python tests/test_transaction_sync.py
```

This runs 3 tests:
1. **Raw SnapTrade API** - Tests direct API calls
2. **Sync Service** - Tests our parsing and storage
3. **Activity Parsing** - Tests our logic for filtering/parsing activities

## Expected Output

### If Everything Works:
```
✅ Found user: abc123
✅ Found 2 account(s)
📊 Testing account: Robinhood (ID: xyz)
   Date range: 2023-11-30 to 2024-11-30
✅ SUCCESS! Fetched 156 activities

Activity breakdown:
   BUY: 45
   SELL: 38
   DIVIDEND: 73

First 3 activities:
   Activity 1:
      Type: BUY
      Symbol: AAPL
      Date: 2024-11-15
      Quantity: 10
      Price: 150.50
```

### If No Activities Found:
```
⚠️  No activities found in the last year
   This could mean:
   - The account has no trading history
   - The brokerage hasn't synced data yet
   - Date range is outside of available data
```

### Common Issues:

**Issue 1: "User not connected"**
- User hasn't completed SnapTrade OAuth flow
- Fix: Connect brokerage in frontend

**Issue 2: "No activities found"**
- Possible causes:
  - Brokerage just connected (SnapTrade needs time to sync)
  - All trades are options/crypto (MVP only supports stocks)
  - Account has no trading history
  - Date range is wrong

**Issue 3: Activities found but not stored in DB**
- Check if migration ran: `alembic current`
- Check for errors in sync service logs
- Verify transactions table exists

## Debugging Tips

### 1. Check Raw API Response

Add this to see full activity object:
```python
import json
print(json.dumps(activity, indent=2))
```

### 2. Check What's in Database

```bash
cd /Users/anshul/code/finch/backend
source venv/bin/activate

python -c "
from database import SessionLocal
from crud import transactions as tx_crud

db = SessionLocal()
txs = tx_crud.get_transactions(db, 'YOUR_USER_ID', limit=10)
print(f'Found {len(txs)} transactions in DB')
for tx in txs:
    print(f'{tx.symbol} {tx.transaction_type} on {tx.transaction_date}')
db.close()
"
```

### 3. Check Sync Job Status

```bash
python -c "
from database import SessionLocal
from crud import transactions as tx_crud

db = SessionLocal()
job = tx_crud.get_latest_sync_job(db, 'YOUR_USER_ID')
if job:
    print(f'Status: {job.status}')
    print(f'Data: {job.data}')
else:
    print('No sync jobs found')
db.close()
"
```

## What's Being Tested

### Test 1: SnapTrade API
- ✅ Can we connect to SnapTrade?
- ✅ Can we fetch user's accounts?
- ✅ Can we fetch activities for each account?
- ✅ What date ranges have data?
- ✅ What types of activities exist?

### Test 2: Sync Service
- ✅ Does our service successfully call SnapTrade?
- ✅ Does it parse activities correctly?
- ✅ Does it store them in the database?
- ✅ Does it skip non-stock transactions (options, crypto)?

### Test 3: Parsing Logic
- ✅ Do we correctly parse stock transactions?
- ✅ Do we correctly skip non-stock transactions?
- ✅ Do we handle missing fields gracefully?

## Next Steps After Testing

Once you know what's being returned:

1. **If activities are found**: Check why they're not being parsed/stored
2. **If no activities found**: Check SnapTrade dashboard for sync status
3. **If only options/crypto found**: This is expected (MVP limitation)
4. **If activities stored but not showing in chat**: Check the LLM tools

## Need Help?

Check:
- SnapTrade documentation: https://docs.snaptrade.com/
- `backend/services/transaction_sync.py` - Sync logic
- `backend/crud/transactions.py` - Database operations
- `backend/modules/tools/definitions.py` - LLM tools

