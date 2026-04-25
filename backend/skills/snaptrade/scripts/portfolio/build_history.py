"""
Build portfolio value history from SnapTrade activities + FMP prices.

equity[day] = sum(holdings[sym] * price[sym]) + cash[day]

- Holdings replayed from activities (buys/sells/splits)
- Validated against SnapTrade's current positions to remove phantom holdings
- Cash anchored to SnapTrade's current cash, adjusted by activity amounts
- Daily resolution for full history, hourly for last 7 days
"""

from typing import Dict, Any, List, Optional, Tuple
from datetime import date, timedelta
from collections import defaultdict
import time as _time

_activities_cache: Dict[Tuple[str, str], Tuple[float, List[dict]]] = {}
_price_cache: Dict[str, Dict[str, float]] = {}
_split_cache: Dict[str, List[dict]] = {}
_CACHE_TTL = 300


def clear_caches():
    _activities_cache.clear()
    _price_cache.clear()
    _split_cache.clear()


def build_portfolio_history(
    user_id: str,
    account_id: Optional[str] = None,
    start_date: Optional[str] = None,
    full_rebuild: bool = False,
    creds: Optional[tuple] = None,
) -> Dict[str, Any]:
    from skills.snaptrade.scripts._client import get_snaptrade_client
    from skills.financial_modeling_prep.scripts.api import fmp
    from concurrent.futures import ThreadPoolExecutor
    import time

    t0 = time.time()
    client = get_snaptrade_client()
    if creds:
        uid, secret = creds
    else:
        session = client._get_session(user_id)
        if not session or not session.is_connected:
            return {"success": False, "error": "Not connected."}
        uid = session.snaptrade_user_id
        secret = session.snaptrade_user_secret

    # ── 1. Accounts + balance + cash + current positions ──
    acct_resp = client.client.account_information.list_user_accounts(user_id=uid, user_secret=secret)
    accounts_raw = acct_resp.body if hasattr(acct_resp, "body") else acct_resp
    if not isinstance(accounts_raw, list):
        accounts_raw = []

    account_ids = []
    actual_balance = 0.0
    for a in accounts_raw:
        aid = str(getattr(a, "id", "") if not isinstance(a, dict) else a.get("id", ""))
        if not aid or aid == "None":
            continue
        if account_id and aid != account_id:
            continue
        account_ids.append(aid)
        bal = getattr(a, "balance", None) if not isinstance(a, dict) else a.get("balance")
        if bal:
            total = getattr(bal, "total", bal) if not isinstance(bal, dict) else bal.get("total", bal)
            try:
                if hasattr(total, "amount"):
                    actual_balance += float(total.amount)
                elif isinstance(total, dict):
                    actual_balance += float(total.get("amount", 0))
                elif isinstance(total, (int, float)):
                    actual_balance += float(total)
            except (ValueError, TypeError):
                pass

    if not account_ids:
        return {"success": False, "error": "No accounts."}

    # Get cash balance from SnapTrade
    cash_balance = 0.0
    for aid in account_ids:
        try:
            resp = client.client.account_information.get_user_account_balance(
                user_id=uid, user_secret=secret, account_id=aid
            )
            data = resp.body if hasattr(resp, "body") else resp
            bals = data if isinstance(data, list) else [data]
            for b in bals:
                if isinstance(b, dict):
                    cash_balance += float(b.get("cash", 0) or 0)
                else:
                    cash_balance += float(getattr(b, "cash", 0) or 0)
        except Exception as e:
            print(f"⚠️ Balance fetch failed for {aid}: {str(e)[:80]}", flush=True)

    # Get current positions from SnapTrade (ground truth for today's holdings)
    actual_positions: Dict[str, float] = defaultdict(float)
    for aid in account_ids:
        try:
            resp = client.client.account_information.get_user_account_positions(
                user_id=uid, user_secret=secret, account_id=aid
            )
            pos = resp.body if hasattr(resp, "body") else resp
            if not isinstance(pos, list):
                pos = pos.get("data", []) if isinstance(pos, dict) else []
            for p in pos:
                t = _extract_ticker(p.get("symbol") if isinstance(p, dict) else getattr(p, "symbol", None))
                q = float(p.get("units", 0) if isinstance(p, dict) else getattr(p, "units", 0) or 0)
                if t and q > 0:
                    actual_positions[t] += q
        except Exception:
            pass

    print(f"📋 {len(account_ids)} accounts, balance=${actual_balance:,.2f}, cash=${cash_balance:,.2f}, {len(actual_positions)} positions", flush=True)

    # ── 2. Fetch activities ──
    # Default to 1 year of history for portfolio view
    activity_start = start_date or (date.today() - timedelta(days=365)).isoformat()
    cache_key = (user_id, account_id or "all")
    cached = _activities_cache.get(cache_key)
    if cached and (_time.time() - cached[0]) < _CACHE_TTL:
        all_activities = list(cached[1])
        print(f"📋 Cached: {len(all_activities)} activities", flush=True)
    else:
        all_activities = []
        for aid in account_ids:
            try:
                offset = 0
                while True:
                    resp = client.client.account_information.get_account_activities(
                        user_id=uid, user_secret=secret, account_id=aid,
                        start_date=activity_start,
                        end_date=date.today().isoformat(),
                        offset=offset, limit=1000,
                    )
                    data = resp.body if hasattr(resp, "body") else resp
                    items = data if isinstance(data, list) else data.get("data", [])
                    if not items:
                        break
                    for item in items:
                        a = _parse_activity(item, aid)
                        if a:
                            all_activities.append(a)
                    if len(items) < 1000:
                        break
                    offset += 1000
            except Exception as e:
                print(f"⚠️ Activities failed for {aid}: {str(e)[:100]}", flush=True)
        if all_activities:
            _activities_cache[cache_key] = (_time.time(), list(all_activities))
        print(f"📋 Fetched {len(all_activities)} activities in {time.time()-t0:.1f}s", flush=True)

    if not all_activities:
        return {"success": False, "error": "No activities."}

    # ── 3. Fetch splits for traded symbols ──
    traded_symbols = {a["symbol"] for a in all_activities if a["symbol"]}
    new_splits = [s for s in traded_symbols if s not in _split_cache]
    if new_splits:
        print(f"📊 Fetching splits for {len(new_splits)} symbols...", flush=True)

        def _fetch_split(sym):
            try:
                data = fmp(f"/historical-price-full/stock_split/{sym}")
                hist = data.get("historical", []) if isinstance(data, dict) else []
                splits = []
                for s in hist:
                    n = float(s.get("numerator", 1))
                    d = float(s.get("denominator", 1))
                    if n > 0 and d > 0 and n != d:
                        splits.append({"date": s["date"], "ratio": n / d})
                return (sym, splits)
            except:
                return (sym, [])

        with ThreadPoolExecutor(max_workers=20) as pool:
            for sym, splits in pool.map(_fetch_split, new_splits):
                _split_cache[sym] = splits

    # Only inject splits within our date range
    for sym, splits in _split_cache.items():
        for s in splits:
            if s["date"] >= activity_start:
                all_activities.append({
                    "account_id": "", "type": "_SPLIT", "symbol": sym,
                    "date": s["date"], "units": 0, "amount": 0, "price": 0,
                    "split_ratio": s["ratio"],
                })

    all_activities.sort(key=lambda a: a["date"])

    # ── 4. Replay activities day by day ──
    SKIP_UNITS = {'OPTIONEXERCISE', 'OPTIONEXPIRATION', 'FEE', 'INTEREST', 'CONTRIBUTION', 'WITHDRAWAL'}

    # Start with actual positions and work backward to set initial holdings
    # at start_date. We do this by replaying activities FORWARD from start_date
    # using SnapTrade positions as a validation anchor.
    holdings: Dict[str, float] = defaultdict(float)
    cumulative_cash = 0.0
    first_date = date.fromisoformat(all_activities[0]["date"])
    last_date = date.today()

    activities_by_date: Dict[str, List[dict]] = defaultdict(list)
    for a in all_activities:
        activities_by_date[a["date"]].append(a)

    daily_state: List[Tuple[str, Dict[str, float], float]] = []

    current = first_date
    while current <= last_date:
        d = current.isoformat()
        for a in activities_by_date.get(d, []):
            sym = a.get("symbol")
            atype = a.get("type", "")

            if atype == "_SPLIT" and sym and sym in holdings and holdings[sym] > 0:
                old_qty = holdings[sym]
                holdings[sym] = old_qty * a["split_ratio"]
            elif sym and a.get("units") and atype not in SKIP_UNITS:
                holdings[sym] += a["units"]
                if abs(holdings[sym]) < 0.01:
                    del holdings[sym]

            cumulative_cash += a.get("amount", 0)

        if current.weekday() < 5:
            clean = {s: q for s, q in holdings.items() if q > 0.01}
            daily_state.append((d, dict(clean), cumulative_cash))

        current += timedelta(days=1)

    # ── 4b. Validate replayed holdings against SnapTrade positions ──
    # Remove phantom holdings (mergers, acquisitions, delistings)
    replayed_holdings = daily_state[-1][1] if daily_state else {}
    valid_symbols = set(actual_positions.keys())
    phantom = {s for s in replayed_holdings if s not in valid_symbols}
    if phantom:
        print(f"🧹 Removing {len(phantom)} phantom holdings not in SnapTrade: {sorted(phantom)}", flush=True)
        # Remove phantoms from all daily states
        daily_state = [
            (d, {s: q for s, q in h.items() if s not in phantom}, cc)
            for d, h, cc in daily_state
        ]

    # Log holdings comparison
    for sym in sorted(valid_symbols):
        replayed = replayed_holdings.get(sym, 0)
        actual = actual_positions[sym]
        if abs(replayed - actual) > 0.1:
            print(f"⚠️ Holdings mismatch: {sym} replayed={replayed:.2f} vs actual={actual:.2f}", flush=True)

    print(f"📊 {len(daily_state)} market days, {len(valid_symbols)} active positions", flush=True)

    # ── 5. Fetch prices ──
    # Only fetch for symbols actually in holdings, and only for the date range held
    symbol_ranges: Dict[str, tuple] = {}
    for d, h, _ in daily_state:
        for sym in h:
            if sym not in symbol_ranges:
                symbol_ranges[sym] = (d, d)
            else:
                symbol_ranges[sym] = (symbol_ranges[sym][0], d)
    symbol_ranges = {s: r for s, r in symbol_ranges.items() if s}

    to_fetch = {}
    for sym, (from_d, to_d) in symbol_ranges.items():
        if sym not in _price_cache:
            to_fetch[sym] = (from_d, to_d)
        elif to_d > max(_price_cache[sym].keys(), default=""):
            to_fetch[sym] = (max(_price_cache[sym].keys()), to_d)

    if to_fetch:
        t1 = time.time()
        print(f"📊 Daily prices: {len(to_fetch)}/{len(symbol_ranges)} symbols...", flush=True)

        def _fetch_price(item):
            sym, (fd, td) = item
            try:
                data = fmp(f"/historical-price-full/{sym}", {"from": fd, "to": td})
                prices = {}
                hist = data.get("historical", []) if isinstance(data, dict) else (data if isinstance(data, list) else [])
                for bar in hist:
                    if "date" in bar:
                        prices[bar["date"]] = bar.get("close", 0)
                return (sym, prices)
            except:
                return (sym, {})

        with ThreadPoolExecutor(max_workers=20) as pool:
            for sym, prices in pool.map(_fetch_price, to_fetch.items()):
                if prices:
                    _price_cache.setdefault(sym, {}).update(prices)
        print(f"✅ Daily prices in {time.time()-t1:.1f}s", flush=True)

    # Hourly prices for last 7 days
    current_holdings = daily_state[-1][1] if daily_state else {}
    intraday_cutoff = (date.today() - timedelta(days=10)).isoformat()
    hourly_cache: Dict[str, List[dict]] = {}

    if current_holdings:
        t2 = time.time()

        def _fetch_hourly(sym):
            try:
                data = fmp(f"/historical-chart/1hour/{sym}", {"from": intraday_cutoff, "to": date.today().isoformat()})
                if not isinstance(data, list):
                    return (sym, [])
                return (sym, [{"date": b["date"], "close": b.get("close", 0)} for b in data if b.get("date", "") >= intraday_cutoff])
            except:
                return (sym, [])

        with ThreadPoolExecutor(max_workers=10) as pool:
            for sym, bars in pool.map(_fetch_hourly, current_holdings.keys()):
                if bars:
                    hourly_cache[sym] = sorted(bars, key=lambda b: b["date"])
        print(f"✅ Hourly prices in {time.time()-t2:.1f}s ({len(hourly_cache)} symbols)", flush=True)

    # ── 6. Build equity series ──
    today_cum = daily_state[-1][2] if daily_state else 0
    missing_prices: Dict[str, List[str]] = defaultdict(list)

    equity_series = []
    for d, h, cum_cash in daily_state:
        stock_value = 0.0
        for sym, qty in h.items():
            prices = _price_cache.get(sym, {})
            price = prices.get(d)
            if price is None:
                dt = date.fromisoformat(d)
                for i in range(1, 4):
                    p = (dt - timedelta(days=i)).isoformat()
                    if p in prices:
                        price = prices[p]
                        break
            if price is None:
                missing_prices[sym].append(d)
            else:
                stock_value += qty * price

        cash_on_day = cash_balance - (today_cum - cum_cash)
        total = stock_value + cash_on_day
        if total > 0:
            equity_series.append({"date": d, "value": round(total, 2)})

    if missing_prices:
        for sym, dates in missing_prices.items():
            print(f"⚠️ MISSING PRICES: {sym} — {len(dates)} days (e.g. {dates[:3]})", flush=True)

    # Hourly series for last 7 days
    intraday_series = []
    if hourly_cache and current_holdings:
        all_ts = sorted({b["date"] for bars in hourly_cache.values() for b in bars})
        week_ago = (date.today() - timedelta(days=7)).isoformat()
        all_ts = [ts for ts in all_ts if ts >= week_ago]

        for ts in all_ts:
            stock_value = 0.0
            for sym, qty in current_holdings.items():
                price = 0
                for b in hourly_cache.get(sym, []):
                    if b["date"] <= ts:
                        price = b["close"]
                    else:
                        break
                stock_value += qty * price
            if stock_value > 0:
                total = stock_value + cash_balance
                intraday_series.append({"date": ts, "value": round(total, 2)})

    if equity_series and actual_balance > 0:
        print(f"📊 Last daily=${equity_series[-1]['value']:,.2f} vs actual=${actual_balance:,.2f}", flush=True)

    print(f"⏱️ Done: {time.time()-t0:.1f}s, {len(equity_series)} daily + {len(intraday_series)} hourly pts", flush=True)

    return {
        "success": True,
        "equity_series": equity_series,
        "intraday_series": intraday_series,
        "symbols_used": sorted(symbol_ranges.keys()),
        "activities_count": len(all_activities),
        "snapshots_saved": 0,
        "date_range": {
            "from": equity_series[0]["date"] if equity_series else None,
            "to": equity_series[-1]["date"] if equity_series else None,
        },
    }


def _extract_ticker(obj) -> str:
    if not obj:
        return ""
    if isinstance(obj, str):
        return obj
    for _ in range(3):
        if isinstance(obj, str):
            return obj
        if isinstance(obj, dict):
            inner = obj.get("symbol") or obj.get("ticker") or obj.get("id", "")
            if isinstance(inner, str):
                return inner
            obj = inner
            continue
        inner = getattr(obj, "symbol", None) or getattr(obj, "ticker", None)
        if inner is None:
            return ""
        if isinstance(inner, str):
            return inner
        obj = inner
    return ""


def _parse_activity(item, account_id: str) -> Optional[dict]:
    if isinstance(item, dict):
        sym = _extract_ticker(item.get("symbol"))
        td = str(item.get("trade_date") or item.get("settlement_date") or item.get("date", ""))
        if "T" in td:
            td = td.split("T")[0]
        return {"account_id": account_id, "type": item.get("type", ""), "symbol": sym, "date": td,
                "units": float(item.get("units", 0) or 0), "amount": float(item.get("amount", 0) or 0),
                "price": float(item.get("price", 0) or 0)}
    sym = _extract_ticker(getattr(item, "symbol", None))
    td = str(getattr(item, "trade_date", None) or getattr(item, "settlement_date", None) or getattr(item, "date", ""))
    if "T" in td:
        td = td.split("T")[0]
    return {"account_id": account_id, "type": str(getattr(item, "type", "")), "symbol": sym, "date": td,
            "units": float(getattr(item, "units", 0) or 0), "amount": float(getattr(item, "amount", 0) or 0),
            "price": float(getattr(item, "price", 0) or 0)}
