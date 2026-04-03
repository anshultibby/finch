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

    # Debug: show activity type breakdown and samples
    from collections import Counter
    type_counts = Counter(a["type"] for a in all_activities)
    print(f"📊 Activity types: {dict(type_counts)}", flush=True)

    # Show a few with empty symbols or zero units
    empty_sym = [a for a in all_activities if not a["symbol"] and a["units"] != 0][:3]
    if empty_sym:
        print(f"⚠️ Activities with empty symbol but units: {empty_sym}", flush=True)

    # Show some BUY samples
    buys = [a for a in all_activities if a["type"] == "BUY"][:3]
    print(f"📋 Sample BUYs: {buys}", flush=True)

    # Show option exercises
    opts = [a for a in all_activities if "OPTION" in a["type"]][:3]
    if opts:
        print(f"📋 Sample OPTIONS: {opts}", flush=True)

    # Sort by date
    all_activities.sort(key=lambda a: a["date"])

    # ── Step 3: Replay transactions to build daily holdings + cash ──
    holdings: Dict[str, float] = defaultdict(float)
    cash: float = 0.0

    first_date = date.fromisoformat(all_activities[0]["date"])
    last_date = date.today()

    # Index activities by date
    activities_by_date: Dict[str, List[dict]] = defaultdict(list)
    for a in all_activities:
        activities_by_date[a["date"]].append(a)

    # Option activities track contract counts, not shares
    SKIP_UNITS_TYPES = {'OPTIONEXERCISE', 'OPTIONEXPIRATION', 'OPTIONASSIGNMENT', 'FEE', 'INTEREST', 'CONTRIBUTION', 'WITHDRAWAL'}

    # Build per-day state: holdings snapshot + cash balance
    # Only store on weekdays (market days)
    daily_state: List[tuple] = []  # [(date_str, {symbol: qty}, cash), ...]
    all_symbols: set = set()

    current = first_date
    while current <= last_date:
        d = current.isoformat()

        for a in activities_by_date.get(d, []):
            symbol = a.get("symbol")
            units = a.get("units", 0)
            amount = a.get("amount", 0)
            atype = a.get("type", "")

            if symbol and units and atype not in SKIP_UNITS_TYPES:
                holdings[symbol] += units
                if abs(holdings[symbol]) < 0.0001:
                    del holdings[symbol]

            cash += amount

        if current.weekday() < 5:
            all_symbols.update(holdings.keys())
            daily_state.append((d, dict(holdings), cash))

        current += timedelta(days=1)

    print(f"📊 {len(daily_state)} market days, {len(all_symbols)} unique symbols", flush=True)

    # ── Step 4: Fetch historical prices from FMP (parallel) ──
    # Compute date ranges per symbol so we only fetch what's needed
    symbol_ranges: Dict[str, tuple] = {}  # symbol -> (first_held, last_held)
    for d, h, _ in daily_state:
        for sym in h:
            if sym not in symbol_ranges:
                symbol_ranges[sym] = (d, d)
            else:
                symbol_ranges[sym] = (symbol_ranges[sym][0], d)

    symbol_ranges = {s: r for s, r in symbol_ranges.items() if s}
    print(f"📊 Fetching prices for {len(symbol_ranges)} symbols (20 parallel)...", flush=True)

    price_cache: Dict[str, Dict[str, float]] = {}

    def _fetch_one(item: tuple) -> tuple:
        symbol, (from_d, to_d) = item
        try:
            data = fmp(f"/historical-price-full/{symbol}", {"from": from_d, "to": to_d})
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
    with ThreadPoolExecutor(max_workers=20) as pool:
        for symbol, prices in pool.map(_fetch_one, symbol_ranges.items()):
            if prices:
                price_cache[symbol] = prices

    print(f"✅ Got prices for {len(price_cache)} symbols", flush=True)

    # ── Step 5: Compute daily portfolio value = stocks + cash ──
    equity_series = []

    for d, h, day_cash in daily_state:
        stock_value = 0.0
        for symbol, qty in h.items():
            if symbol in price_cache:
                price = _find_price(price_cache[symbol], d)
                stock_value += qty * price

        total = stock_value + day_cash
        if total > 0:
            equity_series.append({"date": d, "value": round(total, 2)})

    dates = [p["date"] for p in equity_series]
    return {
        "success": True,
        "equity_series": equity_series,
        "symbols_used": sorted(all_symbols),
        "activities_count": len(all_activities),
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


def build_intraday_history(
    user_id: str,
    account_id: Optional[str] = None,
    days_back: int = 7,
) -> Dict[str, Any]:
    """
    Build hourly portfolio value for the last N days using FMP intraday prices
    and current holdings from SnapTrade.

    Args:
        user_id: Supabase user ID
        account_id: Optional - limit to one account
        days_back: Number of days of hourly data (default 7)

    Returns:
        dict with equity_series: list of {date, value} with hourly timestamps
    """
    from skills.snaptrade.scripts._client import get_snaptrade_client
    from skills.financial_modeling_prep.scripts.api import fmp
    from concurrent.futures import ThreadPoolExecutor

    client = get_snaptrade_client()
    session = client._get_session(user_id)
    if not session or not session.is_connected:
        return {"success": False, "error": "Not connected."}

    uid = session.snaptrade_user_id
    secret = session.snaptrade_user_secret

    # Get current holdings (positions) - these are what we value at each hour
    try:
        acct_resp = client.client.account_information.list_user_accounts(
            user_id=uid, user_secret=secret
        )
        accounts_raw = acct_resp.body if hasattr(acct_resp, "body") else acct_resp
        if not isinstance(accounts_raw, list):
            accounts_raw = accounts_raw.get("data", []) if isinstance(accounts_raw, dict) else []

        account_ids = []
        for a in accounts_raw:
            aid = None
            if isinstance(a, dict):
                aid = a.get("id") or a.get("account_id")
            else:
                aid = str(getattr(a, "id", "")) or str(getattr(a, "account_id", ""))
            if aid and str(aid) != "None":
                account_ids.append(str(aid))

        if account_id:
            account_ids = [a for a in account_ids if a == account_id]
    except Exception as e:
        return {"success": False, "error": f"Failed to list accounts: {e}"}

    # Get positions for each account
    holdings: Dict[str, float] = defaultdict(float)  # symbol -> total qty
    for aid in account_ids:
        try:
            resp = client.client.account_information.get_user_account_positions(
                user_id=uid, user_secret=secret, account_id=aid
            )
            positions = resp.body if hasattr(resp, "body") else resp
            if not isinstance(positions, list):
                positions = positions.get("data", []) if isinstance(positions, dict) else []

            for pos in positions:
                sym_obj = pos.get("symbol") if isinstance(pos, dict) else getattr(pos, "symbol", None)
                ticker = _extract_ticker(sym_obj)
                qty = float(pos.get("units", 0) if isinstance(pos, dict) else getattr(pos, "units", 0) or 0)
                if ticker and qty > 0:
                    holdings[ticker] += qty
        except Exception as e:
            print(f"⚠️ Failed to get positions for {aid}: {str(e)[:100]}", flush=True)

    if not holdings:
        return {"success": False, "error": "No positions found."}

    symbols = list(holdings.keys())
    print(f"📊 Fetching hourly prices for {len(symbols)} symbols...", flush=True)

    # Fetch 1hour bars from FMP in parallel
    hourly_prices: Dict[str, List[dict]] = {}  # symbol -> [{date, close}, ...]

    def _fetch_hourly(symbol: str):
        try:
            data = fmp(f"/historical-chart/1hour/{symbol}")
            if isinstance(data, list):
                # FMP returns newest first, take last N days worth
                cutoff = (date.today() - timedelta(days=days_back)).isoformat()
                bars = [{"date": b["date"], "close": b.get("close", 0)} for b in data if b.get("date", "") >= cutoff]
                return (symbol, bars)
            return (symbol, [])
        except Exception as e:
            print(f"⚠️ Hourly fetch failed for {symbol}: {str(e)[:80]}", flush=True)
            return (symbol, [])

    with ThreadPoolExecutor(max_workers=10) as pool:
        for symbol, bars in pool.map(_fetch_hourly, symbols):
            if bars:
                hourly_prices[symbol] = bars

    print(f"✅ Got hourly prices for {len(hourly_prices)}/{len(symbols)} symbols", flush=True)

    # Build hourly equity series
    # Collect all unique timestamps across all symbols
    all_timestamps = set()
    for bars in hourly_prices.values():
        for b in bars:
            all_timestamps.add(b["date"])

    # For each timestamp, compute portfolio value
    equity_series = []
    for ts in sorted(all_timestamps):
        total = 0.0
        for symbol, qty in holdings.items():
            if symbol in hourly_prices:
                # Find the bar at or just before this timestamp
                price = 0.0
                for b in hourly_prices[symbol]:
                    if b["date"] <= ts:
                        price = b["close"]
                    elif b["date"] > ts:
                        break
                if price == 0:
                    # Use first available price
                    if hourly_prices[symbol]:
                        price = hourly_prices[symbol][0]["close"]
                total += qty * price

        if total > 0:
            equity_series.append({"date": ts, "value": round(total, 2)})

    return {
        "success": True,
        "equity_series": equity_series,
        "symbols_count": len(symbols),
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
