"""
Test SnapTrade transaction fetching and sync functionality
"""
import pytest
import asyncio
from datetime import datetime, timedelta
from modules.tools.clients.snaptrade import snaptrade_tools
from services.transaction_sync import transaction_sync_service
from crud.snaptrade_user import get_user_by_id as get_snaptrade_user
from database import SessionLocal


def test_snaptrade_activities_api():
    """
    Test 1: Verify SnapTrade activities API works
    This tests the raw API call to fetch transactions
    """
    print("\n=== TEST 1: SnapTrade Activities API ===")
    
    # Get a real user from DB
    db = SessionLocal()
    
    # TODO: Replace with actual user_id from your DB
    # You can find this by querying: SELECT user_id FROM snaptrade_users WHERE is_connected = true LIMIT 1;
    test_user_id = "YOUR_USER_ID_HERE"  # Replace this!
    
    snaptrade_user = get_snaptrade_user(db, test_user_id)
    
    if not snaptrade_user:
        print(f"❌ User {test_user_id} not found in database")
        print("💡 Update test_user_id with a real user from snaptrade_users table")
        db.close()
        return
    
    if not snaptrade_user.is_connected:
        print(f"❌ User {test_user_id} is not connected to SnapTrade")
        db.close()
        return
    
    print(f"✅ Found user: {test_user_id}")
    print(f"   SnapTrade User ID: {snaptrade_user.snaptrade_user_id}")
    print(f"   Is Connected: {snaptrade_user.is_connected}")
    
    try:
        # Get user's accounts
        print("\n📋 Fetching accounts...")
        accounts_response = snaptrade_tools.client.account_information.list_user_accounts(
            user_id=test_user_id,
            user_secret=snaptrade_user.snaptrade_user_secret
        )
        
        accounts = accounts_response.body if hasattr(accounts_response, 'body') else accounts_response
        print(f"✅ Found {len(accounts)} account(s)")
        
        if not accounts:
            print("⚠️  No accounts found - user may not have connected a brokerage yet")
            db.close()
            return
        
        # Test fetching activities for first account
        account = accounts[0]
        account_id = account.get('id')
        account_name = account.get('name', 'Unknown')
        
        print(f"\n📊 Testing account: {account_name} (ID: {account_id})")
        
        # Fetch activities for last 1 year
        end_date = datetime.now()
        start_date = end_date - timedelta(days=365)
        
        print(f"   Date range: {start_date.date()} to {end_date.date()}")
        
        activities_response = snaptrade_tools.client.transactions_and_reporting.get_activities(
            user_id=test_user_id,
            user_secret=snaptrade_user.snaptrade_user_secret,
            account_id=account_id,
            start_date=start_date.strftime("%Y-%m-%d"),
            end_date=end_date.strftime("%Y-%m-%d")
        )
        
        activities = activities_response.body if hasattr(activities_response, 'body') else activities_response
        
        print(f"\n✅ SUCCESS! Fetched {len(activities)} activities")
        
        if len(activities) > 0:
            print("\n📝 Sample activities:")
            
            # Group by type
            by_type = {}
            for activity in activities:
                activity_type = activity.get('type', 'UNKNOWN')
                by_type[activity_type] = by_type.get(activity_type, 0) + 1
            
            print("\nActivity breakdown:")
            for activity_type, count in sorted(by_type.items()):
                print(f"   {activity_type}: {count}")
            
            # Show first 3 activities
            print("\nFirst 3 activities:")
            for i, activity in enumerate(activities[:3]):
                print(f"\n   Activity {i+1}:")
                print(f"      Type: {activity.get('type')}")
                print(f"      Symbol: {activity.get('symbol', 'N/A')}")
                print(f"      Date: {activity.get('trade_date', activity.get('date'))}")
                print(f"      Quantity: {activity.get('units', 'N/A')}")
                print(f"      Price: {activity.get('price', 'N/A')}")
                print(f"      Amount: {activity.get('amount', 'N/A')}")
                
                # Check if this is a stock or other asset type
                security_type = activity.get('type', '').upper()
                if security_type in ["OPTION", "CRYPTO", "FUTURE", "FOREX"]:
                    print(f"      ⚠️  Non-stock transaction (will be skipped in MVP)")
        else:
            print("\n⚠️  No activities found in the last year")
            print("   This could mean:")
            print("   - The account has no trading history")
            print("   - The brokerage hasn't synced data yet")
            print("   - Date range is outside of available data")
        
    except Exception as e:
        print(f"\n❌ ERROR calling SnapTrade API:")
        print(f"   {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
    
    finally:
        db.close()


async def test_transaction_sync_service():
    """
    Test 2: Verify transaction sync service works
    This tests our service layer that parses and stores transactions
    """
    print("\n\n=== TEST 2: Transaction Sync Service ===")
    
    # TODO: Replace with actual user_id
    test_user_id = "YOUR_USER_ID_HERE"  # Replace this!
    
    print(f"Testing sync for user: {test_user_id}")
    
    try:
        result = await transaction_sync_service.sync_user_transactions(
            user_id=test_user_id,
            start_date=datetime.now() - timedelta(days=365),
            end_date=datetime.now()
        )
        
        print(f"\n✅ Sync completed!")
        print(f"   Success: {result.get('success')}")
        print(f"   Message: {result.get('message')}")
        print(f"   Transactions fetched: {result.get('transactions_fetched', 0)}")
        print(f"   Transactions inserted: {result.get('transactions_inserted', 0)}")
        print(f"   Transactions updated: {result.get('transactions_updated', 0)}")
        print(f"   Accounts synced: {result.get('accounts_synced', 0)}")
        
        if not result.get('success'):
            print(f"\n⚠️  Sync failed: {result.get('message')}")
        
        # Now check if transactions were actually stored
        from crud import transactions as tx_crud
        db = SessionLocal()
        
        transactions = tx_crud.get_transactions(db, test_user_id, limit=10)
        print(f"\n📊 Transactions in database: {len(transactions)}")
        
        if len(transactions) > 0:
            print("\nFirst 3 transactions:")
            for i, tx in enumerate(transactions[:3]):
                print(f"\n   Transaction {i+1}:")
                print(f"      ID: {tx.id}")
                print(f"      Symbol: {tx.symbol}")
                print(f"      Type: {tx.transaction_type}")
                print(f"      Date: {tx.transaction_date}")
                print(f"      Quantity: {tx.data.get('quantity')}")
                print(f"      Price: {tx.data.get('price')}")
                print(f"      Total: {tx.data.get('total_amount')}")
        
        db.close()
        
    except Exception as e:
        print(f"\n❌ ERROR in sync service:")
        print(f"   {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()


def test_activity_parsing():
    """
    Test 3: Verify activity parsing logic
    This tests that we correctly parse SnapTrade activity objects
    """
    print("\n\n=== TEST 3: Activity Parsing ===")
    
    # Sample SnapTrade activity (stock buy)
    sample_stock_buy = {
        "id": "test_123",
        "type": "BUY",
        "symbol": "AAPL",
        "units": 10,
        "price": 150.50,
        "amount": -1505.00,
        "fee": 0,
        "currency": "USD",
        "trade_date": "2024-01-15T14:30:00Z",
        "settlement_date": "2024-01-17T00:00:00Z",
        "description": "Bought 10 shares of AAPL"
    }
    
    # Sample option trade (should be skipped in MVP)
    sample_option = {
        "id": "test_456",
        "type": "OPTION",
        "symbol": "TSLA",
        "units": 1,
        "price": 500.00,
        "amount": -500.00,
        "trade_date": "2024-01-15T14:30:00Z"
    }
    
    print("\n1. Testing stock transaction parsing:")
    parsed_stock = transaction_sync_service._parse_snaptrade_activity(sample_stock_buy)
    
    if parsed_stock:
        print(f"   ✅ Stock transaction parsed successfully")
        print(f"      Symbol: {parsed_stock['symbol']}")
        print(f"      Type: {parsed_stock['transaction_type']}")
        print(f"      Date: {parsed_stock['transaction_date']}")
        print(f"      Data: {parsed_stock['data']}")
    else:
        print(f"   ❌ Failed to parse stock transaction")
    
    print("\n2. Testing option transaction parsing (should be skipped):")
    parsed_option = transaction_sync_service._parse_snaptrade_activity(sample_option)
    
    if parsed_option is None:
        print(f"   ✅ Option transaction correctly skipped (MVP limitation)")
    else:
        print(f"   ⚠️  Option transaction was parsed (should be skipped in MVP)")


def run_all_tests():
    """Run all tests"""
    print("="*60)
    print("SNAPTRADE TRANSACTION SYNC TESTS")
    print("="*60)
    
    # Test 1: Raw API
    test_snaptrade_activities_api()
    
    # Test 2: Sync service (async)
    asyncio.run(test_transaction_sync_service())
    
    # Test 3: Parsing logic
    test_activity_parsing()
    
    print("\n" + "="*60)
    print("TESTS COMPLETE")
    print("="*60)


if __name__ == "__main__":
    # Instructions
    print("""
    ╔════════════════════════════════════════════════════════════╗
    ║  BEFORE RUNNING: Update test_user_id in the test functions ║
    ║                                                             ║
    ║  Find a user ID by running:                                 ║
    ║  SELECT user_id FROM snaptrade_users                        ║
    ║  WHERE is_connected = true LIMIT 1;                         ║
    ╚════════════════════════════════════════════════════════════╝
    """)
    
    run_all_tests()

