"""
Build portfolio value history from SnapTrade activities + FMP daily prices.

equity[day] = sum(holdings[sym] * close_price[sym]) + cash[day]

- Holdings replayed from activities (buys, sells, splits, option events)
- Validated against SnapTrade's current positions; correction applied retroactively
- Cash anchored to SnapTrade's current cash, adjusted by cumulative activity amounts
- Daily resolution only (end-of-day close prices)
- Incremental: reuses cached equity series and resumes from cached holdings state
"""

from typing import Dict, Any, List, Optional, Tuple
from datetime import date, timedelta
from collections import defaultdict
import time as _time

_activities_cache: Dict[Tuple[str, str], Tuple[float, List[dict]]] = {}
_price_cache: Dict[str, Dict[str, float]] = {}
_split_cache: Dict[str, List[dict]] = {}
_CACHE_TTL = 300
_INCREMENTAL_OVERLAP = 3

# Activity types where 'units' does NOT represent share count changes
_SKIP_UNITS = {'FEE', 'INTEREST', 'CONTRIBUTION', 'WITHDRAWAL', 'DIVIDEND'}


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
    cached_equity: Optional[List[dict]] = None,
    cached_holdings: Optional[Dict[str, float]] = None,
    cached_cash: Optional[float] = None,
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

    # ── 1. Accounts, balance, cash, current positions ──
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

    # ── 2. Determine incremental vs full rebuild ──
    use_incremental = (
        not full_rebuild
        and cached_equity
        and cached_holdings
        and cached_cash is not None
        and len(cached_equity) >= 2
    )

    if use_incremental:
        cache_cutoff = cached_equity[-1]["date"]
        resume_date = (date.fromisoformat(cache_cutoff) - timedelta(days=_INCREMENTAL_OVERLAP)).isoformat()
        print(f"⚡ Incremental build from {resume_date} (cached {len(cached_equity)} days through {cache_cutoff})", flush=True)
        activity_start = resume_date
    else:
        activity_start = start_date or (date.today() - timedelta(days=365)).isoformat()
        print(f"🔄 Full rebuild from {activity_start}", flush=True)

    # ── 3. Fetch activities ──
    cache_key = (user_id, account_id or "all")
    cached = _activities_cache.get(cache_key)
    if cached and (_time.time() - cached[0]) < _CACHE_TTL:
        all_activities = list(cached[1])
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
    print(f"📋 {len(all_activities)} activities", flush=True)

    if not all_activities and not use_incremental:
        return {"success": False, "error": "No activities."}

    # ── 4. Fetch splits for traded symbols ──
    traded_symbols = {a["symbol"] for a in all_activities if a["symbol"]}
    new_splits = [s for s in traded_symbols if s not in _split_cache]
    if new_splits:
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
            except Exception:
                return (sym, [])

        with ThreadPoolExecutor(max_workers=20) as pool:
            for sym, splits in pool.map(_fetch_split, new_splits):
                _split_cache[sym] = splits

    for sym, splits in _split_cache.items():
        for s in splits:
            if s["date"] >= activity_start:
                all_activities.append({
                    "account_id": "", "type": "_SPLIT", "symbol": sym,
                    "date": s["date"], "units": 0, "amount": 0, "price": 0,
                    "split_ratio": s["ratio"],
                })

    all_activities.sort(key=lambda a: a["date"])

    # ── 5. Replay activities day by day ──
    if use_incremental:
        holdings = defaultdict(float, cached_holdings)
        cumulative_cash = cached_cash
        first_date = date.fromisoformat(activity_start)
    else:
        holdings: Dict[str, float] = defaultdict(float)
        cumulative_cash = 0.0
        first_date = date.fromisoformat(all_activities[0]["date"]) if all_activities else date.today()

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
                holdings[sym] = holdings[sym] * a["split_ratio"]
            elif sym and a.get("units") and atype not in _SKIP_UNITS:
                holdings[sym] += a["units"]
                if abs(holdings[sym]) < 0.01:
                    del holdings[sym]

            cumulative_cash += a.get("amount", 0)

        if current.weekday() < 5:
            clean = {s: q for s, q in holdings.items() if q > 0.01}
            daily_state.append((d, dict(clean), cumulative_cash))

        current += timedelta(days=1)

    if not daily_state:
        return {"success": False, "error": "No market days computed."}

    # ── 6. Correct holdings: snap to actual positions ──
    replayed_final = daily_state[-1][1]
    valid_symbols = set(actual_positions.keys())

    # Compute per-symbol correction (actual - replayed)
    correction: Dict[str, float] = {}
    all_syms = set(list(replayed_final.keys()) + list(actual_positions.keys()))
    for sym in all_syms:
        replayed_qty = replayed_final.get(sym, 0)
        actual_qty = actual_positions.get(sym, 0)
        delta = actual_qty - replayed_qty
        if abs(delta) > 0.1:
            correction[sym] = delta
            print(f"⚠️ {sym}: replayed={replayed_qty:.2f} actual={actual_qty:.2f} correction={delta:+.2f}", flush=True)

    # Remove phantoms (replayed > 0 but actual = 0) from all days
    phantoms = {sym for sym, delta in correction.items() if actual_positions.get(sym, 0) < 0.01}

    # Apply corrections retroactively to all days
    if correction:
        corrected_state = []
        for d, h, cc in daily_state:
            corrected = dict(h)
            for sym in phantoms:
                corrected.pop(sym, None)
            for sym, delta in correction.items():
                if sym in phantoms:
                    continue
                corrected[sym] = corrected.get(sym, 0) + delta
                if corrected[sym] < 0.01:
                    corrected.pop(sym, None)
            corrected_state.append((d, corrected, cc))
        daily_state = corrected_state

    print(f"📊 {len(daily_state)} market days, {len(valid_symbols)} active positions, {len(correction)} corrections", flush=True)

    # ── 7. Fetch daily close prices ──
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
        print(f"📊 Fetching daily prices: {len(to_fetch)}/{len(symbol_ranges)} symbols...", flush=True)

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
            except Exception:
                return (sym, {})

        with ThreadPoolExecutor(max_workers=20) as pool:
            for sym, prices in pool.map(_fetch_price, to_fetch.items()):
                if prices:
                    _price_cache.setdefault(sym, {}).update(prices)
        print(f"✅ Prices fetched in {time.time()-t1:.1f}s", flush=True)

    # ── 8. Build equity series ──
    today_cum = daily_state[-1][2]

    new_equity = []
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
            if price is not None:
                stock_value += qty * price

        cash_on_day = cash_balance - (today_cum - cum_cash)
        total = stock_value + cash_on_day
        if total > 0:
            new_equity.append({"date": d, "value": round(total, 2)})

    # Merge with cached equity for incremental builds
    if use_incremental and cached_equity:
        cutoff = new_equity[0]["date"] if new_equity else cached_equity[-1]["date"]
        kept = [p for p in cached_equity if p["date"] < cutoff]
        equity_series = kept + new_equity
        print(f"⚡ Merged: {len(kept)} cached + {len(new_equity)} new = {len(equity_series)} total days", flush=True)
    else:
        equity_series = new_equity

    if equity_series and actual_balance > 0:
        last_computed = equity_series[-1]["value"]
        drift = abs(last_computed - actual_balance) / actual_balance
        print(f"📊 Final: ${last_computed:,.2f} vs actual ${actual_balance:,.2f} (drift={drift:.1%})", flush=True)

    final_holdings = daily_state[-1][1]
    final_cash = daily_state[-1][2]

    print(f"⏱️ Done in {time.time()-t0:.1f}s — {len(equity_series)} daily points", flush=True)

    return {
        "success": True,
        "equity_series": equity_series,
        "intraday_series": [],
        "symbols_used": sorted(symbol_ranges.keys()),
        "activities_count": len(all_activities),
        "snapshots_saved": 0,
        "date_range": {
            "from": equity_series[0]["date"] if equity_series else None,
            "to": equity_series[-1]["date"] if equity_series else None,
        },
        "holdings_state": final_holdings,
        "cash_state": final_cash,
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
