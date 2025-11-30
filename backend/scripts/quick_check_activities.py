#!/usr/bin/env python
"""
ONE-LINE TEST: Quickly check if SnapTrade activities API is working

Usage: python quick_check_activities.py <user_id>
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timedelta
from crud.snaptrade_user import get_user_by_id
from modules.tools.clients.snaptrade import snaptrade_tools
from database import SessionLocal


def check(user_id: str):
    db = SessionLocal()
    user = get_user_by_id(db, user_id)
    
    if not user:
        print(f"❌ User {user_id} not found")
        return
    
    if not user.is_connected:
        print(f"❌ User not connected to SnapTrade")
        return
    
    print(f"✅ User connected to SnapTrade")
    
    # Get accounts
    accounts = snaptrade_tools.client.account_information.list_user_accounts(
        user_id=user_id,
        user_secret=user.snaptrade_user_secret
    ).body
    
    print(f"✅ Found {len(accounts)} account(s)\n")
    
    for account in accounts:
        account_id = account.get('id')
        name = account.get('name', 'Unknown')
        
        # Try fetching last 2 years
        end = datetime.now()
        start = end - timedelta(days=730)
        
        print(f"📊 {name} (ID: {account_id[:8]}...)")
        
        try:
            # NEW API: account_information.get_account_activities
            result = snaptrade_tools.client.account_information.get_account_activities(
                user_id=user_id,
                user_secret=user.snaptrade_user_secret,
                account_id=account_id,
                start_date=start.date(),
                end_date=end.date()
            )
            
            # Response is {data: [...], pagination: {...}}
            response_body = result.body if hasattr(result, 'body') else result
            activities = response_body.get('data', []) if isinstance(response_body, dict) else []
            
            print(f"   ✅ {len(activities)} activities in last 2 years")
            
            if activities:
                types = {}
                for a in activities:
                    t = a.get('type', 'UNKNOWN')
                    types[t] = types.get(t, 0) + 1
                
                for t, count in sorted(types.items()):
                    print(f"      {t}: {count}")
                
                # Show most recent
                recent = sorted(activities, key=lambda x: x.get('trade_date', ''), reverse=True)[:3]
                print(f"\n   Most recent:")
                for a in recent:
                    # Symbol is now an object
                    symbol_obj = a.get('symbol', {})
                    symbol = symbol_obj.get('symbol', 'N/A') if isinstance(symbol_obj, dict) else 'N/A'
                    trade_date = a.get('trade_date', '')[:10]
                    print(f"      • {a.get('type')} {symbol} on {trade_date}")
        
        except Exception as e:
            print(f"   ❌ Error: {str(e)}")
        
        print()
    
    db.close()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python quick_check_activities.py <user_id>")
        sys.exit(1)
    
    check(sys.argv[1])

