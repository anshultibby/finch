"""
Service for syncing transactions from SnapTrade
"""
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from decimal import Decimal
import asyncio
from database import SessionLocal
from crud import transactions as tx_crud
from crud.snaptrade_user import get_user_by_id as get_snaptrade_user
from modules.tools.clients.snaptrade import snaptrade_tools
from utils.logger import get_logger

logger = get_logger(__name__)


class TransactionSyncService:
    """Handles syncing transactions from SnapTrade to local database"""
    
    def __init__(self):
        # Cache last sync time per user to avoid excessive syncing
        self._last_sync_time = {}
        self._sync_cooldown_seconds = 300  # 5 minutes default
        self._background_sync_enabled = True  # Enable background syncs
    
    def _should_sync(self, user_id: str, force_resync: bool) -> bool:
        """Check if we should sync based on last sync time"""
        if force_resync:
            return True
        
        last_sync = self._last_sync_time.get(user_id)
        
        # If not in cache, check database for recent sync
        if not last_sync:
            db = SessionLocal()
            try:
                latest_job = tx_crud.get_latest_sync_job(db, user_id)
                if latest_job and latest_job.status == "completed" and latest_job.completed_at:
                    # Initialize cache from DB
                    self._last_sync_time[user_id] = latest_job.completed_at
                    last_sync = latest_job.completed_at
                else:
                    return True  # No recent sync, do it
            finally:
                db.close()
        
        if not last_sync:
            return True
        
        # Check if enough time has passed
        time_since_sync = (datetime.now() - last_sync).total_seconds()
        return time_since_sync >= self._sync_cooldown_seconds
    
    async def sync_user_transactions(
        self,
        user_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        force_resync: bool = False,
        background_sync: bool = True  # New param
    ) -> Dict[str, Any]:
        """
        Sync all transactions for a user from SnapTrade
        
        Args:
            user_id: User ID
            start_date: Optional start date (defaults to 1 year ago)
            end_date: Optional end date (defaults to today)
            force_resync: If True, re-fetch even if already synced
            
        Returns:
            Dictionary with sync results
        """
        # Get info about last sync
        db_for_check = SessionLocal()
        latest_job = tx_crud.get_latest_sync_job(db_for_check, user_id)
        db_for_check.close()
        
        # Calculate staleness
        last_sync_time = self._last_sync_time.get(user_id)
        if not last_sync_time and latest_job and latest_job.completed_at:
            last_sync_time = latest_job.completed_at
            self._last_sync_time[user_id] = last_sync_time
        
        staleness_seconds = int((datetime.now() - last_sync_time).total_seconds()) if last_sync_time else None
        
        # Check if we should sync (throttle)
        should_sync = self._should_sync(user_id, force_resync)
        
        if not should_sync:
            # Within cooldown - return cached data
            cooldown_remaining = int(self._sync_cooldown_seconds - staleness_seconds) if staleness_seconds else 0
            logger.info(f"⏭️  Using cached data for {user_id} - last synced {staleness_seconds}s ago (cooldown: {cooldown_remaining}s remaining)")
            
            if latest_job:
                return {
                    "success": True,
                    "message": f"Using data from {staleness_seconds}s ago",
                    "transactions_fetched": latest_job.data.get("transactions_fetched", 0),
                    "transactions_inserted": latest_job.data.get("transactions_inserted", 0),
                    "transactions_updated": latest_job.data.get("transactions_updated", 0),
                    "accounts_synced": latest_job.data.get("accounts_synced", 0),
                    "cached": True,
                    "last_synced_at": last_sync_time.isoformat() if last_sync_time else None,
                    "staleness_seconds": staleness_seconds
                }
        
        elif background_sync and self._background_sync_enabled and staleness_seconds and staleness_seconds < 3600:
            # Outside cooldown but data is recent (< 1 hour) - return cached and trigger background sync
            logger.info(f"🔄 Returning cached data and triggering background sync for {user_id}")
            
            # Trigger background sync (fire and forget)
            asyncio.create_task(self._background_sync(user_id, start_date, end_date))
            
            if latest_job:
                return {
                    "success": True,
                    "message": f"Using data from {staleness_seconds}s ago (updating in background)",
                    "transactions_fetched": latest_job.data.get("transactions_fetched", 0),
                    "transactions_inserted": latest_job.data.get("transactions_inserted", 0),
                    "transactions_updated": latest_job.data.get("transactions_updated", 0),
                    "accounts_synced": latest_job.data.get("accounts_synced", 0),
                    "cached": True,
                    "background_sync": True,
                    "last_synced_at": last_sync_time.isoformat() if last_sync_time else None,
                    "staleness_seconds": staleness_seconds
                }
        
        # Need fresh sync (data is very old or force requested)
        logger.info(f"🔄 Starting foreground sync for {user_id} (force={force_resync}, staleness={staleness_seconds}s)")
        
        db = SessionLocal()
        
        try:
            # Create sync job
            job = tx_crud.create_sync_job(
                db,
                user_id=user_id,
                status="running",
                data={
                    "start_date": start_date.isoformat() if start_date else None,
                    "end_date": end_date.isoformat() if end_date else None,
                    "force_resync": force_resync,
                    "started_at": datetime.now().isoformat()
                }
            )
            
            # Get user's SnapTrade connection
            snaptrade_user = get_snaptrade_user(db, user_id)
            if not snaptrade_user or not snaptrade_user.is_connected:
                tx_crud.update_sync_job(
                    db,
                    str(job.id),
                    status="failed",
                    data={**job.data, "error": "No active brokerage connection"},
                    completed_at=datetime.now()
                )
                return {
                    "success": False,
                    "message": "No active brokerage connection. Please connect a brokerage first."
                }
            
            # Default to last year if no start date
            if not start_date:
                start_date = datetime.now() - timedelta(days=365)
            if not end_date:
                end_date = datetime.now()
            
            # Get all accounts for this user
            accounts = await self._get_user_accounts(
                user_id,
                snaptrade_user.snaptrade_user_secret
            )
            
            if not accounts:
                tx_crud.update_sync_job(
                    db,
                    str(job.id),
                    status="completed",
                    data={**job.data, "accounts_synced": 0, "message": "No accounts found"},
                    completed_at=datetime.now()
                )
                return {
                    "success": True,
                    "message": "No accounts found to sync",
                    "transactions_fetched": 0,
                    "transactions_inserted": 0,
                    "transactions_updated": 0,
                    "accounts_synced": 0
                }
            
            total_fetched = 0
            total_inserted = 0
            total_updated = 0
            
            # Sync each account
            for account in accounts:
                logger.info(f"Syncing account {account.get('id')} for user {user_id}")
                result = await self._sync_account_transactions(
                    user_id=user_id,
                    user_secret=snaptrade_user.snaptrade_user_secret,
                    account_id=account.get("id"),
                    start_date=start_date,
                    end_date=end_date
                )
                total_fetched += result["fetched"]
                total_inserted += result["inserted"]
                total_updated += result["updated"]
            
            # Update sync job as completed
            tx_crud.update_sync_job(
                db,
                str(job.id),
                status="completed",
                data={
                    **job.data,
                    "transactions_fetched": total_fetched,
                    "transactions_inserted": total_inserted,
                    "transactions_updated": total_updated,
                    "accounts_synced": len(accounts)
                },
                completed_at=datetime.now()
            )
            
            # Update last sync time cache
            self._last_sync_time[user_id] = datetime.now()
            
            logger.info(f"Sync completed for user {user_id}: {total_inserted} inserted, {total_updated} updated")
            
            return {
                "success": True,
                "message": f"Successfully synced {total_fetched} transactions",
                "transactions_fetched": total_fetched,
                "transactions_inserted": total_inserted,
                "transactions_updated": total_updated,
                "accounts_synced": len(accounts),
                "cached": False,
                "last_synced_at": datetime.now().isoformat(),
                "staleness_seconds": 0
            }
            
        except Exception as e:
            logger.error(f"Error syncing transactions for user {user_id}: {str(e)}", exc_info=True)
            
            # Update sync job as failed
            if 'job' in locals():
                tx_crud.update_sync_job(
                    db,
                    str(job.id),
                    status="failed",
                    data={**job.data, "error": str(e)},
                    completed_at=datetime.now()
                )
            
            return {
                "success": False,
                "message": f"Sync failed: {str(e)}"
            }
        finally:
            db.close()
    
    async def _background_sync(
        self,
        user_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ):
        """Background sync - runs async, updates cache when done"""
        try:
            logger.info(f"🔄 Background sync started for {user_id}")
            # Call the main sync with background_sync=False to avoid recursion
            result = await self.sync_user_transactions(
                user_id, 
                start_date, 
                end_date, 
                force_resync=True,  # Force to actually sync
                background_sync=False  # Prevent nested background syncs
            )
            logger.info(f"✅ Background sync completed for {user_id}: {result.get('transactions_inserted', 0)} new, {result.get('transactions_updated', 0)} updated")
        except Exception as e:
            logger.error(f"❌ Background sync failed for {user_id}: {e}")
    
    async def _get_user_accounts(
        self,
        user_id: str,
        user_secret: str
    ) -> List[Dict[str, Any]]:
        """Get all accounts for a user from SnapTrade"""
        try:
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: snaptrade_tools.client.account_information.list_user_accounts(
                    user_id=user_id,
                    user_secret=user_secret
                )
            )
            
            # Extract account data
            accounts = response.body if hasattr(response, 'body') else response
            return accounts or []
            
        except Exception as e:
            logger.error(f"Error fetching accounts for user {user_id}: {str(e)}")
            return []
    
    async def _sync_account_transactions(
        self,
        user_id: str,
        user_secret: str,
        account_id: str,
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, int]:
        """Sync transactions for a specific account"""
        
        try:
            # Call SnapTrade activities API (NEW API)
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: snaptrade_tools.client.account_information.get_account_activities(
                    user_id=user_id,
                    user_secret=user_secret,
                    account_id=account_id,
                    start_date=start_date.date(),  # Pass date object, not string
                    end_date=end_date.date()
                )
            )
            
            # New API returns {data: [...], pagination: {...}}
            result = response.body if hasattr(response, 'body') else response
            activities = result.get('data', []) if isinstance(result, dict) else result
            
            if not activities:
                return {"fetched": 0, "inserted": 0, "updated": 0}
            
            fetched = len(activities)
            inserted = 0
            updated = 0
            
            db = SessionLocal()
            try:
                for activity in activities:
                    # Parse activity into transaction data
                    tx_data = self._parse_snaptrade_activity(activity)
                    
                    # Skip if not a stock transaction (MVP limitation)
                    if tx_data is None:
                        continue
                    
                    # Upsert transaction
                    _, is_new = tx_crud.upsert_transaction(
                        db,
                        user_id=user_id,
                        account_id=account_id,
                        symbol=tx_data["symbol"],
                        transaction_type=tx_data["transaction_type"],
                        transaction_date=tx_data["transaction_date"],
                        data=tx_data["data"],
                        external_id=tx_data.get("external_id")
                    )
                    
                    if is_new:
                        inserted += 1
                    else:
                        updated += 1
                
            finally:
                db.close()
            
            return {
                "fetched": fetched,
                "inserted": inserted,
                "updated": updated
            }
            
        except Exception as e:
            logger.error(f"Error syncing account {account_id}: {str(e)}", exc_info=True)
            return {"fetched": 0, "inserted": 0, "updated": 0}
    
    def _parse_snaptrade_activity(
        self,
        activity: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Parse SnapTrade activity into transaction format
        
        Returns None if activity should be skipped (e.g., options trades in MVP)
        """
        
        # NEW API: symbol is an object, not a string
        symbol_obj = activity.get("symbol")
        
        # Skip if no symbol (e.g., CONTRIBUTION, WITHDRAWAL, FEE without symbol)
        if not symbol_obj or symbol_obj is None:
            activity_type = activity.get("type", "").upper()
            # These are valid non-stock transactions
            if activity_type in ["CONTRIBUTION", "WITHDRAWAL", "FEE", "INTEREST"]:
                logger.debug(f"⚠️ Skipping non-stock transaction: {activity_type}")
            return None
        
        # Extract symbol string
        symbol = symbol_obj.get("symbol", "").strip() if isinstance(symbol_obj, dict) else str(symbol_obj).strip()
        if not symbol:
            logger.debug(f"⚠️ Skipping transaction with no symbol")
            return None
        
        # MVP: Skip options
        option_symbol = activity.get("option_symbol")
        if option_symbol:
            logger.debug(f"⚠️ Skipping option transaction: {symbol}")
            return None
        
        # Check security type
        if symbol_obj and isinstance(symbol_obj, dict):
            security_type_obj = symbol_obj.get("type", {})
            security_type_code = security_type_obj.get("code", "").upper() if isinstance(security_type_obj, dict) else ""
            # Skip if not common stock
            if security_type_code and security_type_code not in ["CS", "COMMON STOCK", ""]:
                logger.debug(f"⚠️ Skipping non-stock security: {security_type_code}")
                return None
        
        # Map SnapTrade activity types to our types
        type_mapping = {
            "BUY": "BUY",
            "SELL": "SELL",
            "DIVIDEND": "DIVIDEND",
            "DIV": "DIVIDEND",
            "FEE": "FEE",
            "DEPOSIT": "TRANSFER",
            "WITHDRAWAL": "TRANSFER",
            "CONTRIBUTION": "TRANSFER",
            "SPLIT": "SPLIT",
            "INTEREST": "INTEREST"
        }
        
        activity_type = activity.get("type", "").upper()
        transaction_type = type_mapping.get(activity_type, "TRANSFER")
        
        # Parse dates (NEW API uses ISO format with Z)
        trade_date_str = activity.get("trade_date")
        if not trade_date_str:
            logger.warning(f"⚠️ Activity missing trade_date: {activity.get('id')}")
            return None
        
        try:
            trade_date = datetime.fromisoformat(trade_date_str.replace("Z", "+00:00"))
        except Exception as e:
            logger.error(f"Error parsing trade_date '{trade_date_str}': {e}")
            return None
        
        settlement_date = None
        if activity.get("settlement_date"):
            try:
                settlement_date = datetime.fromisoformat(
                    activity["settlement_date"].replace("Z", "+00:00")
                )
            except:
                pass
        
        # Extract currency (NEW API: currency is an object)
        currency_obj = activity.get("currency", {})
        currency = currency_obj.get("code", "USD") if isinstance(currency_obj, dict) else "USD"
        
        # Build transaction data (what goes in the JSONB field)
        data = {
            "quantity": float(activity.get("units", 0)),
            "price": float(activity.get("price")) if activity.get("price") else None,
            "fee": float(activity.get("fee", 0)),
            "total_amount": float(activity.get("amount", 0)),
            "asset_type": "STOCK",
            "settlement_date": settlement_date.isoformat() if settlement_date else None,
            "description": activity.get("description", ""),
            "currency": currency,
            "institution": activity.get("institution", ""),
            "raw_data": activity  # Store full SnapTrade response
        }
        
        return {
            "symbol": symbol,
            "transaction_type": transaction_type,
            "transaction_date": trade_date,
            "external_id": activity.get("id", ""),
            "data": data
        }


# Global instance
transaction_sync_service = TransactionSyncService()

