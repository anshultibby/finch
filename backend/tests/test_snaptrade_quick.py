"""
Quick test to fetch SnapTrade activities for debugging
Run this to see what's actually being returned from the API
"""
import sys
from datetime import datetime, timedelta
from crud.snaptrade_user import get_user_by_id as get_snaptrade_user
from modules.tools.clients.snaptrade import snaptrade_tools
from database import SessionLocal


def quick_test_activities(user_id: str):
    """Quick test to see SnapTrade activities for a user"""
    
    print(f"\n🔍 Testing SnapTrade Activities API for user: {user_id}")
    print("="*60)
    
    db = SessionLocal()
    
    try:
        # Get user
        snaptrade_user = get_snaptrade_user(db, user_id)
        
        if not snaptrade_user:
            print(f"❌ User not found in database")
            return
        
        if not snaptrade_user.is_connected:
            print(f"❌ User not connected to SnapTrade")
            return
        
        print(f"✅ User found and connected")
        
        # Get accounts
        print(f"\n📋 Fetching accounts...")
        accounts_response = snaptrade_tools.client.account_information.list_user_accounts(
            user_id=user_id,
            user_secret=snaptrade_user.snaptrade_user_secret
        )
        
        accounts = accounts_response.body if hasattr(accounts_response, 'body') else accounts_response
        print(f"   Found {len(accounts)} account(s)")
        
        # Test each account
        for i, account in enumerate(accounts):
            account_id = account.get('id')
            account_name = account.get('name', 'Unknown')
            broker = account.get('brokerage_authorization', {}).get('name', 'Unknown')
            
            print(f"\n📊 Account {i+1}: {account_name} ({broker})")
            print(f"   Account ID: {account_id}")
            
            # Try different date ranges
            test_ranges = [
                ("Last 30 days", 30),
                ("Last 90 days", 90),
                ("Last 1 year", 365),
                ("Last 2 years", 730),
            ]
            
            for range_name, days in test_ranges:
                end_date = datetime.now()
                start_date = end_date - timedelta(days=days)
                
                print(f"\n   Testing {range_name} ({start_date.date()} to {end_date.date()})...")
                
                try:
                    activities_response = snaptrade_tools.client.transactions_and_reporting.get_activities(
                        user_id=user_id,
                        user_secret=snaptrade_user.snaptrade_user_secret,
                        account_id=account_id,
                        start_date=start_date.strftime("%Y-%m-%d"),
                        end_date=end_date.strftime("%Y-%m-%d")
                    )
                    
                    activities = activities_response.body if hasattr(activities_response, 'body') else activities_response
                    
                    print(f"      ✅ {len(activities)} activities found")
                    
                    if len(activities) > 0:
                        # Group by type
                        by_type = {}
                        for activity in activities:
                            activity_type = activity.get('type', 'UNKNOWN')
                            by_type[activity_type] = by_type.get(activity_type, 0) + 1
                        
                        print(f"      Breakdown:")
                        for activity_type, count in sorted(by_type.items()):
                            print(f"         {activity_type}: {count}")
                        
                        # Show a few examples
                        print(f"\n      Sample activities:")
                        for j, activity in enumerate(activities[:5]):
                            print(f"\n         [{j+1}] {activity.get('type')} - {activity.get('symbol', 'N/A')}")
                            print(f"             Date: {activity.get('trade_date', activity.get('date'))}")
                            print(f"             Qty: {activity.get('units', 'N/A')}, Price: {activity.get('price', 'N/A')}")
                            print(f"             Amount: {activity.get('amount', 'N/A')}")
                        
                        # Found data, no need to test longer ranges
                        break
                    
                except Exception as e:
                    print(f"      ❌ Error: {str(e)}")
                    continue
            
            print()
    
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
    
    finally:
        db.close()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("\n❌ Usage: python test_snaptrade_quick.py <user_id>")
        print("\nTo find a user ID, run this SQL query:")
        print("  SELECT user_id FROM snaptrade_users WHERE is_connected = true LIMIT 1;")
        print("\nOr check your frontend - the user ID is shown in the browser console")
        sys.exit(1)
    
    user_id = sys.argv[1]
    quick_test_activities(user_id)

