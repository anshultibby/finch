"""
Trade setups — the research-backed signals, composed from indicators.py.

Each function takes data (OHLCV bars and/or scalar inputs) and returns a plain
dict describing whether a setup is present and the levels to trade it. They make
NO network calls and place NO orders — fetch bars with the polygon_io skill, pass
them in, and route any resulting trade through the robinhood review→approve loop.

See SKILL.md for the citation behind each setup and its known win rate / payoff.
"""
from typing import List, Dict, Optional, Literal
from .indicators import (
    opening_range, vwap, atr, rsi, sma, relative_volume,
)


def orb_signal(bars: List[Dict], or_minutes: int = 5,
               atr_bars: Optional[List[Dict]] = None,
               stop_atr_mult: float = 0.10) -> dict:
    """
    5-minute Opening Range Breakout (Zarattini, Barbon & Aziz 2024).

    Direction is set by the first bar: if it closed up, only longs (break of the
    OR high); if down, only shorts (break of the OR low). Enter on a STOP order at
    the OR boundary. Stop = a fraction of the 14-day ATR beyond entry (default
    0.10x); exit the rest at the close (EOD time stop). Asymmetric by design:
    ~17% win rate but large winners → Sharpe ~2.4 on stocks-in-play.

    Args:
        bars: today's 1- or 5-min bars from the 09:30 open onward
        or_minutes: opening range length (5 is the tested optimum)
        atr_bars: daily bars for ATR(14); if None, stop falls back to the opposite
                  end of the opening range
        stop_atr_mult: ATR fraction for the stop distance
    """
    rng = opening_range(bars, or_minutes)
    if not rng:
        return {"setup": "orb", "signal": None, "reason": "no opening range yet"}
    or_high, or_low = rng
    first = bars[0]
    direction = "long" if float(first["close"]) >= float(first["open"]) else "short"

    # Has price broken the range after the opening window?
    window_end_ts = int(bars[0]["timestamp"]) + or_minutes * 60 * 1000
    post = [b for b in bars if int(b["timestamp"]) >= window_end_ts]
    if not post:
        return {"setup": "orb", "signal": None, "or_high": or_high, "or_low": or_low,
                "reason": "opening range still forming"}
    last = float(post[-1]["close"])

    a = atr(atr_bars, 14) if atr_bars else None
    if direction == "long":
        triggered = any(float(b["high"]) > or_high for b in post)
        entry = or_high
        stop = (entry - stop_atr_mult * a) if a else or_low
    else:
        triggered = any(float(b["low"]) < or_low for b in post)
        entry = or_low
        stop = (entry + stop_atr_mult * a) if a else or_high

    return {
        "setup": "orb",
        "signal": direction if triggered else None,
        "direction": direction,
        "entry": round(entry, 4),
        "stop": round(stop, 4),
        "or_high": round(or_high, 4),
        "or_low": round(or_low, 4),
        "last": round(last, 4),
        "atr14": round(a, 4) if a else None,
        "reason": (f"{direction} breakout confirmed" if triggered
                   else "no breakout of the opening range yet"),
    }


def stocks_in_play(candidates: List[Dict], top_n: int = 20,
                   min_price: float = 5.0, min_atr: float = 0.50,
                   min_rvol: float = 1.0) -> List[Dict]:
    """
    Rank the day's "stocks in play" — the universe filter that makes ORB work.

    Pass a list of dicts, one per liquid symbol, already populated from market
    data (e.g. polygon_io):

        {"symbol": "NVDA", "price": 120.0, "atr14": 3.2,
         "open_volume": 5_000_000, "prior_open_volumes": [..14 values..]}

    Keeps names with price > min_price, ATR > min_atr, and relative volume >
    min_rvol, then returns the top_n by relative volume (descending). RVOL is
    today's opening volume vs the prior-14-day average opening volume.
    """
    ranked = []
    for c in candidates:
        rvol = relative_volume(c.get("open_volume", 0), c.get("prior_open_volumes", []))
        if rvol is None:
            continue
        if c.get("price", 0) <= min_price:
            continue
        if c.get("atr14", 0) <= min_atr:
            continue
        if rvol <= min_rvol:
            continue
        ranked.append({**c, "rvol": round(rvol, 2)})
    ranked.sort(key=lambda x: x["rvol"], reverse=True)
    return ranked[:top_n]


def vwap_signal(bars: List[Dict], trend_bias: Optional[Literal["long", "short"]] = None) -> dict:
    """
    VWAP reclaim / pullback (institutional benchmark, ~60-70% of US volume).

    Long bias: price is above VWAP (uptrend). The low-risk entry is a pullback
    toward VWAP that holds, with the stop just below the pullback low (NOT on
    VWAP — wicks knock you out). Short bias is the mirror. Best in the first hour;
    requires volume on the move (confirm with relative_volume / rising volume).

    Returns the current relationship to VWAP and a candidate stop level. Pass
    `trend_bias` to only act with the higher-timeframe trend.
    """
    v = vwap(bars)
    if v is None or len(bars) < 3:
        return {"setup": "vwap", "signal": None, "reason": "not enough bars"}
    last = float(bars[-1]["close"])
    above = last > v
    recent_low = min(float(b["low"]) for b in bars[-3:])
    recent_high = max(float(b["high"]) for b in bars[-3:])

    signal = None
    reason = "no clean VWAP setup"
    if above and trend_bias in (None, "long"):
        signal = "long"
        reason = "price holding above VWAP — buy pullbacks that hold the line"
        stop = recent_low
    elif (not above) and trend_bias in (None, "short"):
        signal = "short"
        reason = "price below VWAP — short rallies that fail into the line"
        stop = recent_high
    else:
        stop = recent_low if above else recent_high

    return {
        "setup": "vwap",
        "signal": signal,
        "vwap": round(v, 4),
        "last": round(last, 4),
        "above_vwap": above,
        "entry": round(last, 4),
        "stop": round(stop, 4),
        "reason": reason,
    }


def connors_rsi2_signal(daily_closes: List[float]) -> dict:
    """
    Connors RSI(2) mean reversion — a *swing* edge (1-5 day hold), not intraday,
    but the most reproducible short-term long signal (win rate >75% on indices in
    Connors & Alvarez's backtests). Best on broad ETFs (SPY/QQQ), weaker on
    single names.

    Rules: only longs when close > 200-day SMA (trend filter); buy when RSI(2) < 10
    (stronger edge < 5); exit when close > 5-day SMA. Connors found fixed stops
    HURT net performance — control risk with position size and the ETF trend
    filter instead, and still cap catastrophe risk on live single names.
    """
    if len(daily_closes) < 201:
        return {"setup": "connors_rsi2", "signal": None, "reason": "need ~200 daily closes"}
    sma200 = sma(daily_closes, 200)
    sma5 = sma(daily_closes, 5)
    r2 = rsi(daily_closes, 2)
    last = daily_closes[-1]
    in_uptrend = last > sma200
    entry = in_uptrend and r2 is not None and r2 < 10
    exit_long = last > sma5
    return {
        "setup": "connors_rsi2",
        "signal": "long" if entry else None,
        "rsi2": round(r2, 2) if r2 is not None else None,
        "above_200sma": in_uptrend,
        "exit_above_5sma": exit_long,
        "reason": ("oversold pullback in an uptrend — entry" if entry
                   else "no entry (need close>200SMA and RSI2<10)"),
    }
