"""ORATS options data — current chain, historical metrics, IV rank."""
from ._client import call_orats


def get_options_chain(ticker: str) -> dict:
    """
    Get the current end-of-day options chain for a ticker with full Greeks.

    Returns one record per (strike, expiry) pair captured ~14 min before close.

    Fields include: strike, expirDate, dte, delta, gamma, theta, vega, rho, phi,
    callBidPrice, callAskPrice, putBidPrice, putAskPrice, callMidIv, smvVol,
    callVolume, putVolume, callOpenInterest, putOpenInterest, stockPrice.

    Args:
        ticker: Stock symbol, e.g. 'AAPL'

    Returns:
        dict with keys:
            ticker   – symbol
            date     – trade date of snapshot
            strikes  – list of strike records (sorted by expiry then strike)

    Example:
        chain = get_options_chain('AAPL')
        # Filter to 30-45 DTE calls
        calls = [s for s in chain['strikes'] if 30 <= s['dte'] <= 45 and s['delta'] > 0]
    """
    try:
        data = call_orats("strikes", {"ticker": ticker})
        if not data:
            return {"error": f"No chain data for {ticker}"}
        return {
            "ticker": ticker,
            "date": data[0].get("tradeDate"),
            "strikes": data,
        }
    except Exception as e:
        return {"error": str(e)}


def get_iv_rank(ticker: str, from_date: str = None, to_date: str = None) -> dict:
    """
    Get IV rank and IV percentile history for a ticker (back to 2007).

    Args:
        ticker:    Stock symbol, e.g. 'AAPL'
        from_date: Start date 'YYYY-MM-DD' (optional, defaults to full history)
        to_date:   End date   'YYYY-MM-DD' (optional)

    Returns:
        dict with keys:
            ticker  – symbol
            history – list of dicts, each with:
                        tradeDate, iv, ivRank1m, ivPct1m, ivRank1y, ivPct1y

    Example:
        ivr = get_iv_rank('AAPL', from_date='2023-01-01', to_date='2023-12-31')
        df = pd.DataFrame(ivr['history'])
        # Find days where IV rank was above 50 (elevated vol)
        high_iv = df[df['ivRank1y'] > 50]
    """
    try:
        params = {"ticker": ticker}
        if from_date:
            params["tradeDateStart"] = from_date
        if to_date:
            params["tradeDateEnd"] = to_date
        data = call_orats("hist/ivrank", params)
        if not data:
            return {"error": f"No IV rank data for {ticker}"}
        return {"ticker": ticker, "history": data}
    except Exception as e:
        return {"error": str(e)}


def get_historical_metrics(ticker: str, from_date: str = None, to_date: str = None) -> dict:
    """
    Get rich historical options metrics for a ticker (back to 2007).

    Includes 200+ fields: realized vol, IV term structure, skew/slope, contango,
    earnings data, IV percentiles, vol forecasts, and more.

    Key fields: tradeDate, pxAtmIv, iv20d, iv30d, iv60d, iv90d, iv6m, iv1y,
    ivPctile1m, ivPctile1y, slope, contango, orHv20d, orHv60d, nextErn,
    absAvgErnMv, impliedEarningsMove, beta1y, correlSpy1y.

    Args:
        ticker:    Stock symbol, e.g. 'AAPL'
        from_date: Start date 'YYYY-MM-DD' (optional)
        to_date:   End date   'YYYY-MM-DD' (optional)

    Returns:
        dict with keys:
            ticker  – symbol
            history – list of daily metric records

    Example:
        metrics = get_historical_metrics('AAPL', from_date='2022-01-01', to_date='2024-01-01')
        df = pd.DataFrame(metrics['history'])
        df['tradeDate'] = pd.to_datetime(df['tradeDate'])
        # Backtest: enter when IV percentile > 80 and contango > 0
        signals = df[(df['ivPctile1y'] > 80) & (df['contango'] > 0)]
    """
    try:
        params = {"ticker": ticker}
        if from_date:
            params["tradeDateStart"] = from_date
        if to_date:
            params["tradeDateEnd"] = to_date
        data = call_orats("hist/cores", params)
        if not data:
            return {"error": f"No historical metrics for {ticker}"}
        return {"ticker": ticker, "history": data}
    except Exception as e:
        return {"error": str(e)}


def get_iv_surface(ticker: str) -> dict:
    """
    Get the current implied volatility surface (term structure) for a ticker.

    Returns IV at standardized delta/DTE grid points — useful for understanding
    the shape of the vol surface (skew, term structure, contango).

    Args:
        ticker: Stock symbol, e.g. 'AAPL'

    Returns:
        dict with keys:
            ticker  – symbol
            date    – trade date
            surface – list of surface points with fields:
                        expirDate, dte, delta, impliedVol, smoothedVol, fittedVol

    Example:
        surface = get_iv_surface('AAPL')
        # Find the 30-DTE ATM vol
        atm_30 = next((p for p in surface['surface'] if p['dte'] == 30), None)
    """
    try:
        data = call_orats("monies/implied", {"ticker": ticker})
        if not data:
            return {"error": f"No IV surface data for {ticker}"}
        return {
            "ticker": ticker,
            "date": data[0].get("tradeDate"),
            "surface": data,
        }
    except Exception as e:
        return {"error": str(e)}


def get_summary(ticker: str) -> dict:
    """
    Get current options summary metrics for a ticker.

    Includes IV term structure (iv10d through iv1y), skew at multiple deltas,
    forward vol, contango, borrow rate, implied earnings move, and more.

    Args:
        ticker: Stock symbol, e.g. 'AAPL'

    Returns:
        dict: Single record with all summary fields for today.

    Example:
        summary = get_summary('AAPL')
        print(f"30d IV: {summary.get('iv30d')}, IV rank: {summary.get('ivRank1y')}")
        print(f"Implied earnings move: {summary.get('impliedEarningsMove')}")
    """
    try:
        data = call_orats("summaries", {"ticker": ticker})
        if not data:
            return {"error": f"No summary data for {ticker}"}
        return data[0]
    except Exception as e:
        return {"error": str(e)}
