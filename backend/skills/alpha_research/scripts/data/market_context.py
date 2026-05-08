"""
Market context building blocks.

Functions that provide broader context for trade decisions:
cross-asset regime snapshot, peer price reactions, IV context.

No scoring or classification — just data for the agent to reason about.
"""
from datetime import datetime, timedelta


def get_cross_asset_snapshot():
    """
    Get current cross-asset data points relevant to equity risk assessment.

    Returns VIX level, credit spread proxy (HYG vs LQD), dollar trend (UUP),
    yield curve proxy (TLT vs SHY), and recent trends for each.

    Returns:
        dict with asset-level data: vix, credit, dollar, yield_curve,
        each containing latest price and 30-day trend_pct
    """
    from skills.financial_modeling_prep.scripts.market.historical_prices import get_historical_prices

    today = datetime.now()
    from_date = (today - timedelta(days=60)).strftime("%Y-%m-%d")
    to_date = today.strftime("%Y-%m-%d")

    assets = {
        "vix": "^VIX",
        "hyg": "HYG",
        "lqd": "LQD",
        "dollar": "UUP",
        "long_bonds": "TLT",
        "short_bonds": "SHY",
        "sp500": "SPY",
        "oil": "USO",
        "gold": "GLD",
    }

    snapshot = {}
    for label, symbol in assets.items():
        data = _get_trend(symbol, from_date, to_date)
        snapshot[label] = data if data else {"latest": None, "trend_30d_pct": None}

    return snapshot


def get_peer_reactions(symbol: str, since_date: str):
    """
    Get price changes of a stock's peers since a given date.
    Useful for seeing which related companies have or haven't
    reacted to news from the source company.

    Args:
        symbol: Source stock ticker
        since_date: Date to measure from (YYYY-MM-DD)

    Returns:
        list of dicts: symbol, company_name, sector, price_change_pct, market_cap_b
    """
    from skills.financial_modeling_prep.scripts.peers.stock_peers import get_stock_peers
    from skills.financial_modeling_prep.scripts.company.profile import get_profile

    peers = get_stock_peers(symbol)
    if not peers or isinstance(peers, dict) and "error" in peers:
        return []

    peer_symbols = []
    if isinstance(peers, list):
        for p in peers:
            if isinstance(p, dict):
                peer_symbols.extend(p.get("peersList", []))
            elif isinstance(p, str):
                peer_symbols.append(p)
    elif isinstance(peers, dict):
        peer_symbols = peers.get("peersList", [])

    peer_symbols = [s for s in peer_symbols if s != symbol][:20]
    today = datetime.now().strftime("%Y-%m-%d")

    results = []
    for peer in peer_symbols:
        change = _price_change(peer, since_date, today)
        profile = get_profile(peer)
        name, sector, mkt_cap_b = peer, None, None
        if profile and not (isinstance(profile, dict) and "error" in profile):
            name = profile.get("companyName", peer)
            sector = profile.get("sector")
            mkt_cap = profile.get("mktCap", 0) or 0
            mkt_cap_b = round(mkt_cap / 1e9, 2)

        results.append({
            "symbol": peer,
            "company_name": name,
            "sector": sector,
            "price_change_pct": round(change, 2) if change is not None else None,
            "market_cap_b": mkt_cap_b,
        })

    return sorted(results, key=lambda x: abs(x["price_change_pct"] or 0))


def get_iv_context(symbol: str):
    """
    Get IV context for a stock: current IV rank, vol risk premium,
    implied earnings move, historical vol metrics.

    Returns:
        dict: iv_rank_1y, current_iv, iv30d, realized_vol_20d,
        vol_risk_premium, implied_earnings_move, contango
        Returns None if ORATS is unavailable.
    """
    try:
        from skills.orats.scripts.options import get_iv_rank, get_summary
    except ImportError:
        return None

    result = {}

    summary = get_summary(symbol)
    if summary and not (isinstance(summary, dict) and "error" in summary):
        result["iv30d"] = summary.get("iv30d")
        result["iv60d"] = summary.get("iv60d")
        result["realized_vol_20d"] = summary.get("orHv20d")
        result["implied_earnings_move"] = summary.get("impliedMove") or summary.get("impliedEarningsMove")
        result["contango"] = summary.get("contango")

        iv30 = summary.get("iv30d")
        hv20 = summary.get("orHv20d") or summary.get("hv20d")
        if iv30 and hv20:
            result["vol_risk_premium"] = round(iv30 - hv20, 4)

    iv_data = get_iv_rank(symbol)
    if iv_data and not (isinstance(iv_data, dict) and "error" in iv_data):
        history = iv_data.get("history", [])
        if history:
            latest = history[-1]
            result["iv_rank_1y"] = latest.get("ivRank1y") or latest.get("ivPct1y")
            result["current_iv"] = latest.get("iv")

    return result if result else None


def get_historical_moves_around_earnings(symbol: str, n_quarters: int = 8):
    """
    Get actual price moves around past earnings events.
    Useful for comparing implied vs realized earnings moves.

    Args:
        symbol: Stock ticker
        n_quarters: How many past earnings to check

    Returns:
        list of dicts: earnings_date, move_pct (close-to-close around earnings)
    """
    from skills.financial_modeling_prep.scripts.earnings.earnings_calendar import get_historical_earnings
    from skills.financial_modeling_prep.scripts.market.historical_prices import get_historical_prices

    hist = get_historical_earnings(symbol)
    if not hist or isinstance(hist, dict) and "error" in hist:
        return []

    recent = hist[:n_quarters] if isinstance(hist, list) else []
    moves = []

    for e in recent:
        earn_date = e.get("date")
        if not earn_date:
            continue

        dt = datetime.strptime(earn_date, "%Y-%m-%d")
        start = (dt - timedelta(days=2)).strftime("%Y-%m-%d")
        end = (dt + timedelta(days=2)).strftime("%Y-%m-%d")

        prices = get_historical_prices(symbol, from_date=start, to_date=end)
        if not prices or isinstance(prices, dict) and "error" in prices or len(prices) < 2:
            continue

        s = sorted(prices, key=lambda p: p.get("date", ""))
        pre, post = None, None
        for p in s:
            if p.get("date", "") <= earn_date:
                pre = p.get("close")
            elif post is None:
                post = p.get("close")

        if pre and post and pre > 0:
            moves.append({
                "earnings_date": earn_date,
                "move_pct": round(abs((post - pre) / pre) * 100, 2),
                "direction": "up" if post > pre else "down",
                "eps_actual": e.get("eps"),
                "eps_estimated": e.get("epsEstimated"),
            })

    return moves


def _get_trend(symbol, from_date, to_date):
    from skills.financial_modeling_prep.scripts.market.historical_prices import get_historical_prices

    prices = get_historical_prices(symbol, from_date=from_date, to_date=to_date)
    if not prices or isinstance(prices, dict) and "error" in prices or len(prices) < 2:
        return None

    s = sorted(prices, key=lambda p: p.get("date", ""))
    latest = s[-1].get("close")
    month_ago_idx = max(0, len(s) - 22)
    month_ago = s[month_ago_idx].get("close")

    if latest and month_ago and month_ago > 0:
        return {
            "latest": latest,
            "trend_30d_pct": round(((latest - month_ago) / month_ago) * 100, 2),
        }
    return None


def _price_change(symbol, from_date, to_date):
    from skills.financial_modeling_prep.scripts.market.historical_prices import get_historical_prices

    start = (datetime.strptime(from_date, "%Y-%m-%d") - timedelta(days=1)).strftime("%Y-%m-%d")
    prices = get_historical_prices(symbol, from_date=start, to_date=to_date)
    if not prices or isinstance(prices, dict) and "error" in prices or len(prices) < 2:
        return None
    s = sorted(prices, key=lambda p: p.get("date", ""))
    pre, cur = s[0].get("close"), s[-1].get("close")
    if pre and cur and pre > 0:
        return ((cur - pre) / pre) * 100
    return None
