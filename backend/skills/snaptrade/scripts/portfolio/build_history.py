"""
Build portfolio value history from SnapTrade activities + FMP historical prices.

Reconstructs daily portfolio value by:
1. Fetching all account activities (buys, sells, dividends, etc.) from SnapTrade
2. Replaying transactions to build a day-by-day holdings map
3. Fetching historical close prices from FMP for each symbol held
4. Computing portfolio value = sum(holdings * price) for each day
5. Saving results to portfolio_snapshots table

Works for any user with connected SnapTrade accounts.

Example:
    from skills.snaptrade.scripts.portfolio.build_history import build_portfolio_history
    result = build_portfolio_history('user-uuid-123')
    print(result['equity_series'][:5])
"""

from typing import Dict, Any, List, Optional
from datetime import date, timedelta
from collections import defaultdict


def build_portfolio_history(
    user_id: str,
    account_id: Optional[str] = None,
    start_date: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Reconstruct daily portfolio value history for a user.

    Args:
        user_id: Supabase user ID
        account_id: Optional - limit to one account (default: all accounts)
        start_date: Optional - earliest date to compute from (default: first activity)

    Returns:
        dict with:
            - success (bool)
            - equity_series: list of {date, value} dicts
            - symbols_used: list of symbols that were held
            - activities_count: number of activities processed
            - snapshots_saved: number of new snapshots saved to DB
    """
    from skills.snaptrade.scripts._client import get_snaptrade_client
    from skills.financial_modeling_prep.scripts.api import fmp
    from core.database import SessionLocal
    from models.brokerage import PortfolioSnapshot
    from sqlalchemy import and_
    import uuid

    client = get_snaptrade_client()
    session = client._get_session(user_id)
    if not session or not session.is_connected:
        return {"success": False, "error": "Not connected to any brokerage."}

    uid = session.snaptrade_user_id
    secret = session.snaptrade_user_secret

    # ── Step 1: Get accounts ──
    try:
        acct_resp = client.client.account_information.list_user_accounts(
            user_id=uid, user_secret=secret
        )
        accounts_raw = acct_resp.body if hasattr(acct_resp, "body") else acct_resp
        if not isinstance(accounts_raw, list):
            accounts_raw = accounts_raw.get("data", []) if isinstance(accounts_raw, dict) else []

        # Extract account IDs reliably
        account_ids = []
        for a in accounts_raw:
            aid = None
            if isinstance(a, dict):
                aid = a.get("id") or a.get("account_id") or a.get("brokerage_authorization", {}).get("id")
            else:
                # SDK model object - try common attribute patterns
                for attr in ["id", "account_id"]:
                    val = getattr(a, attr, None)
                    if val and str(val) and str(val) != "None":
                        aid = str(val)
                        break
                if not aid:
                    # Try dict-like access
                    try:
                        aid = a["id"]
                    except (KeyError, TypeError):
                        pass
            if aid:
                account_ids.append(str(aid))

        print(f"📋 Found {len(account_ids)} accounts: {account_ids}", flush=True)
    except Exception as e:
        return {"success": False, "error": f"Failed to list accounts: {e}"}

    if account_id:
        account_ids = [a for a in account_ids if a == account_id]

    if not account_ids:
        return {"success": False, "error": "No accounts found."}

    # ── Step 2: Fetch all activities across accounts ──
    all_activities = []
    for aid in account_ids:
        try:
            offset = 0
            while True:
                resp = client.client.account_information.get_account_activities(
                    user_id=uid, user_secret=secret, account_id=aid,
                    start_date=start_date or "2020-01-01",
                    end_date=date.today().isoformat(),
                    offset=offset, limit=1000,
                )
                data = resp.body if hasattr(resp, "body") else resp

                items = data if isinstance(data, list) else data.get("data", [])
                if not items:
                    break

                for item in items:
                    activity = _parse_activity(item, aid)
                    if activity:
                        all_activities.append(activity)

                if len(items) < 1000:
                    break
                offset += 1000

            print(f"📋 Fetched activities for account {aid}: {len([a for a in all_activities if a['account_id'] == aid])}", flush=True)
        except Exception as e:
            print(f"⚠️ Failed to fetch activities for {aid}: {str(e)[:200]}", flush=True)

    if not all_activities:
        return {"success": False, "error": "No activities found."}

    # Sort by date
    all_activities.sort(key=lambda a: a["date"])

    # ── Step 3: Replay transactions to build daily holdings ──
    # holdings[symbol] = quantity on each day
    holdings: Dict[str, float] = defaultdict(float)
    cash: float = 0.0
    daily_holdings: Dict[str, Dict[str, float]] = {}  # date -> {symbol: qty}

    first_date = date.fromisoformat(all_activities[0]["date"])
    last_date = date.today()

    # Index activities by date
    activities_by_date: Dict[str, List[dict]] = defaultdict(list)
    for a in all_activities:
        activities_by_date[a["date"]].append(a)

    # Walk through each day
    current = first_date
    while current <= last_date:
        d = current.isoformat()
        for a in activities_by_date.get(d, []):
            symbol = a.get("symbol")
            units = a.get("units", 0)
            amount = a.get("amount", 0)

            if symbol and units:
                holdings[symbol] += units
                # Clean up zero/tiny positions
                if abs(holdings[symbol]) < 0.0001:
                    del holdings[symbol]

            cash += amount

        # Save snapshot of holdings for this day (only on market days, skip weekends)
        if current.weekday() < 5:  # Mon-Fri
            daily_holdings[d] = dict(holdings)

        current += timedelta(days=1)

    # ── Step 4: Fetch historical prices from FMP (parallel) ──
    all_symbols = set()
    for h in daily_holdings.values():
        all_symbols.update(h.keys())

    all_symbols = {s for s in all_symbols if s}  # remove empty
    print(f"📊 Fetching prices for {len(all_symbols)} symbols (parallel)...", flush=True)

    # price_cache[symbol][date_str] = close_price
    price_cache: Dict[str, Dict[str, float]] = {}

    def _fetch_one(symbol: str) -> tuple:
        try:
            data = fmp(f"/historical-price-full/{symbol}", {"from": first_date.isoformat(), "to": last_date.isoformat()})
            prices = {}
            if isinstance(data, dict) and "historical" in data:
                for bar in data["historical"]:
                    prices[bar["date"]] = bar.get("adjClose") or bar.get("close", 0)
            elif isinstance(data, list):
                for bar in data:
                    if "date" in bar:
                        prices[bar["date"]] = bar.get("adjClose") or bar.get("close", 0)
            return (symbol, prices)
        except Exception as e:
            print(f"⚠️ Price fetch failed for {symbol}: {str(e)[:100]}", flush=True)
            return (symbol, {})

    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=10) as pool:
        results = pool.map(_fetch_one, all_symbols)
        for symbol, prices in results:
            if prices:
                price_cache[symbol] = prices

    print(f"✅ Got prices for {len(price_cache)} symbols", flush=True)

    # ── Step 5: Compute daily portfolio value ──
    equity_series = []
    dates = sorted(daily_holdings.keys())

    for d in dates:
        h = daily_holdings[d]
        total = 0.0
        for symbol, qty in h.items():
            if symbol in price_cache:
                # Find closest price (exact date or most recent before)
                price = _find_price(price_cache[symbol], d)
                total += qty * price
        # Include cash
        # total += cash  # Cash is complex to track accurately, skip for now

        if total > 0:
            equity_series.append({"date": d, "value": round(total, 2)})

    # ── Step 6: Save to portfolio_snapshots ──
    # Use a composite key in JSONB: account_id stored in data so we can filter
    snapshot_account_key = account_id or "all"
    db = SessionLocal()
    saved = 0
    try:
        # Get existing snapshot dates for this account to avoid duplicates
        from sqlalchemy import cast, String
        existing = db.query(PortfolioSnapshot.snapshot_date, PortfolioSnapshot.data).filter(
            PortfolioSnapshot.user_id == user_id
        ).all()
        existing_dates = {str(s.snapshot_date) for s in existing if (s.data or {}).get("account_id", "all") == snapshot_account_key}

        for point in equity_series:
            if point["date"] not in existing_dates:
                snapshot = PortfolioSnapshot(
                    id=uuid.uuid4(),
                    user_id=user_id,
                    snapshot_date=date.fromisoformat(point["date"]),
                    data={"total_value": point["value"], "account_id": snapshot_account_key}
                )
                db.add(snapshot)
                saved += 1

        if saved > 0:
            db.commit()
            print(f"💾 Saved {saved} new portfolio snapshots", flush=True)
    finally:
        db.close()

    return {
        "success": True,
        "equity_series": equity_series,
        "symbols_used": sorted(all_symbols),
        "activities_count": len(all_activities),
        "snapshots_saved": saved,
        "date_range": {"from": dates[0] if dates else None, "to": dates[-1] if dates else None},
    }


def _extract_ticker(symbol_obj) -> str:
    """Extract ticker string from SnapTrade's nested symbol objects."""
    if not symbol_obj:
        return ""
    if isinstance(symbol_obj, str):
        return symbol_obj

    # SDK model object or dict - dig through nesting
    # Pattern: activity.symbol -> UniversalSymbol with .symbol -> SecurityExchange with .symbol (ticker)
    # Or: activity.symbol -> dict with 'symbol' key -> dict with 'symbol' key (ticker string)
    obj = symbol_obj
    for _ in range(3):  # max 3 levels of nesting
        if isinstance(obj, str):
            return obj
        if isinstance(obj, dict):
            # Try 'symbol' key first, then 'ticker'
            inner = obj.get("symbol") or obj.get("ticker") or obj.get("id", "")
            if isinstance(inner, str):
                return inner
            obj = inner
            continue
        # SDK object - try attributes
        inner = getattr(obj, "symbol", None) or getattr(obj, "ticker", None)
        if inner is None:
            return str(obj) if obj else ""
        if isinstance(inner, str):
            return inner
        obj = inner

    return str(obj) if obj else ""


def _parse_activity(item: Any, account_id: str) -> Optional[dict]:
    """Parse a SnapTrade activity into a normalized dict."""
    if isinstance(item, dict):
        symbol = _extract_ticker(item.get("symbol"))
        trade_date = item.get("trade_date") or item.get("settlement_date") or item.get("date", "")
        if isinstance(trade_date, str) and "T" in trade_date:
            trade_date = trade_date.split("T")[0]
        return {
            "account_id": account_id,
            "type": item.get("type", ""),
            "symbol": symbol,
            "date": str(trade_date),
            "units": float(item.get("units", 0) or 0),
            "amount": float(item.get("amount", 0) or 0),
            "price": float(item.get("price", 0) or 0),
        }
    else:
        symbol = _extract_ticker(getattr(item, "symbol", None))
        trade_date = getattr(item, "trade_date", None) or getattr(item, "settlement_date", None) or getattr(item, "date", "")
        trade_date = str(trade_date)
        if "T" in trade_date:
            trade_date = trade_date.split("T")[0]
        return {
            "account_id": account_id,
            "type": str(getattr(item, "type", "")),
            "symbol": symbol,
            "date": trade_date,
            "units": float(getattr(item, "units", 0) or 0),
            "amount": float(getattr(item, "amount", 0) or 0),
            "price": float(getattr(item, "price", 0) or 0),
        }


def _find_price(prices: Dict[str, float], target_date: str) -> float:
    """Find exact price or most recent price before the target date."""
    if target_date in prices:
        return prices[target_date]

    # Walk backwards up to 7 days to find most recent price
    d = date.fromisoformat(target_date)
    for i in range(1, 8):
        prev = (d - timedelta(days=i)).isoformat()
        if prev in prices:
            return prices[prev]

    return 0.0
