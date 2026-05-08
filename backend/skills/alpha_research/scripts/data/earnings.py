"""
Earnings data building blocks.

Functions that enrich raw earnings data with context the agent needs
to reason about opportunities: surprise magnitude, price drift since,
insider activity around the event, analyst coverage.

No scoring or signal classification — the agent decides what matters.
"""
from datetime import datetime, timedelta


def get_recent_surprises(lookback_days: int = 30, min_surprise_pct: float = 0.0):
    """
    Get recent earnings with surprise data and post-earnings price drift.

    Args:
        lookback_days: How far back to look
        min_surprise_pct: Filter by minimum absolute surprise % (0 = all)

    Returns:
        list of dicts: symbol, date, eps_actual, eps_estimated, surprise_pct,
        revenue_actual, revenue_estimated, revenue_surprise_pct,
        days_since, drift_pct (price change since earnings)
    """
    from skills.financial_modeling_prep.scripts.earnings.earnings_calendar import get_earnings_calendar
    from skills.financial_modeling_prep.scripts.market.historical_prices import get_historical_prices

    today = datetime.now()
    from_date = (today - timedelta(days=lookback_days)).strftime("%Y-%m-%d")
    to_date = today.strftime("%Y-%m-%d")

    earnings = get_earnings_calendar(from_date=from_date, to_date=to_date)
    if not earnings or isinstance(earnings, dict) and "error" in earnings:
        return []

    results = []
    for e in earnings:
        eps_actual = e.get("eps")
        eps_est = e.get("epsEstimated")
        symbol = e.get("symbol", "")
        earn_date = e.get("date", "")
        if eps_actual is None or eps_est is None or not symbol or not earn_date:
            continue

        surprise_pct = _surprise(eps_actual, eps_est)
        if abs(surprise_pct) < min_surprise_pct:
            continue

        rev_actual = e.get("revenue")
        rev_est = e.get("revenueEstimated")
        rev_surprise = _surprise(rev_actual, rev_est) if rev_actual and rev_est else None

        days_since = (today - datetime.strptime(earn_date, "%Y-%m-%d")).days
        drift_pct = _price_change(symbol, earn_date, to_date)

        results.append({
            "symbol": symbol,
            "date": earn_date,
            "eps_actual": eps_actual,
            "eps_estimated": eps_est,
            "surprise_pct": round(surprise_pct, 2),
            "revenue_actual": rev_actual,
            "revenue_estimated": rev_est,
            "revenue_surprise_pct": round(rev_surprise, 2) if rev_surprise is not None else None,
            "days_since": days_since,
            "drift_pct": round(drift_pct, 2) if drift_pct is not None else None,
        })

    return sorted(results, key=lambda x: abs(x["surprise_pct"]), reverse=True)


def get_upcoming_earnings(days_ahead: int = 14):
    """
    Get upcoming earnings calendar.

    Returns:
        list of dicts: symbol, date, eps_estimated, revenue_estimated, time (bmo/amc)
    """
    from skills.financial_modeling_prep.scripts.earnings.earnings_calendar import get_earnings_calendar

    today = datetime.now()
    from_date = today.strftime("%Y-%m-%d")
    to_date = (today + timedelta(days=days_ahead)).strftime("%Y-%m-%d")

    earnings = get_earnings_calendar(from_date=from_date, to_date=to_date)
    if not earnings or isinstance(earnings, dict) and "error" in earnings:
        return []
    return earnings


def get_earnings_history(symbol: str):
    """
    Get historical earnings for a stock — actual vs estimated over time.
    Useful for understanding a company's beat/miss pattern.

    Returns:
        list of dicts from FMP: date, eps, epsEstimated, revenue, revenueEstimated
    """
    from skills.financial_modeling_prep.scripts.earnings.earnings_calendar import get_historical_earnings
    return get_historical_earnings(symbol)


def get_insider_activity(symbol: str, days_around_earnings: int = 90):
    """
    Get insider trading activity for a stock, split into pre and post
    most recent earnings for context.

    Args:
        symbol: Stock ticker
        days_around_earnings: Window to look for insider trades before earnings

    Returns:
        dict: all_trades (raw list), pre_earnings (trades before last earnings),
        post_earnings (trades after), net_shares_pre, net_shares_post,
        last_earnings_date
    """
    from skills.financial_modeling_prep.scripts.insider.insider_trading import get_insider_trading
    from skills.financial_modeling_prep.scripts.earnings.earnings_calendar import get_historical_earnings

    trades = get_insider_trading(symbol=symbol, limit=100)
    if not trades or isinstance(trades, dict) and "error" in trades:
        return {"all_trades": [], "pre_earnings": [], "post_earnings": []}

    hist = get_historical_earnings(symbol)
    if not hist or isinstance(hist, dict) and "error" in hist:
        return {"all_trades": trades, "pre_earnings": [], "post_earnings": []}

    last_earn_date = None
    if isinstance(hist, list) and hist:
        last_earn_date = hist[0].get("date")

    if not last_earn_date:
        return {"all_trades": trades, "pre_earnings": [], "post_earnings": []}

    earn_dt = datetime.strptime(last_earn_date, "%Y-%m-%d")
    window_start = earn_dt - timedelta(days=days_around_earnings)

    pre, post = [], []
    for t in trades:
        tx_date = t.get("transactionDate", "")
        if not tx_date:
            continue
        try:
            tx_dt = datetime.strptime(tx_date, "%Y-%m-%d")
        except ValueError:
            continue
        if window_start <= tx_dt < earn_dt:
            pre.append(t)
        elif tx_dt >= earn_dt:
            post.append(t)

    return {
        "all_trades": trades,
        "pre_earnings": pre,
        "post_earnings": post,
        "net_shares_pre": _net_shares(pre),
        "net_shares_post": _net_shares(post),
        "last_earnings_date": last_earn_date,
    }


def enrich_with_profile(symbols: list):
    """
    Enrich a list of symbols with company profile data: market cap,
    sector, analyst coverage.

    Returns:
        dict keyed by symbol: market_cap_b, sector, industry, company_name,
        analyst_count, pe_ratio
    """
    from skills.financial_modeling_prep.scripts.company.profile import get_profile
    from skills.financial_modeling_prep.scripts.analyst.price_target import get_price_target_consensus

    profiles = {}
    for symbol in symbols:
        p = get_profile(symbol)
        if not p or isinstance(p, dict) and "error" in p:
            continue

        consensus = get_price_target_consensus(symbol)
        analyst_count = 0
        if consensus and not (isinstance(consensus, dict) and "error" in consensus):
            analyst_count = consensus.get("numberOfAnalysts", 0) or 0

        mkt_cap = p.get("mktCap", 0) or 0
        profiles[symbol] = {
            "company_name": p.get("companyName", symbol),
            "market_cap_b": round(mkt_cap / 1e9, 2),
            "sector": p.get("sector"),
            "industry": p.get("industry"),
            "analyst_count": analyst_count,
            "pe_ratio": p.get("peRatio"),
        }

    return profiles


def _surprise(actual, estimated):
    if estimated == 0:
        return 100.0 if actual > 0 else -100.0 if actual < 0 else 0.0
    return ((actual - estimated) / abs(estimated)) * 100


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


def _net_shares(trades):
    net = 0
    for t in trades:
        tx_type = t.get("transactionType", "")
        shares = t.get("securitiesTransacted", 0) or 0
        if tx_type in ("P", "P-Purchase"):
            net += shares
        elif tx_type in ("S", "S-Sale"):
            net -= shares
    return net
