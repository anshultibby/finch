"""
Day-trading indicators — pure Python, no external dependencies.

Every function takes either a list of floats (prices) or a list of OHLCV "bar"
dicts shaped like the output of polygon_io's get_intraday_bars():

    {"open": float, "high": float, "low": float, "close": float,
     "volume": float, "timestamp": int}  # timestamp = unix ms

These are the building blocks behind the setups in setups.py. They are written
to match the standard (Wilder) definitions used in the research so backtests are
reproducible — see SKILL.md for citations.
"""
from typing import List, Dict, Optional, Tuple


def _closes(bars: List[Dict]) -> List[float]:
    return [float(b["close"]) for b in bars]


def sma(values: List[float], period: int) -> Optional[float]:
    """Simple moving average of the last `period` values. None if too few."""
    if len(values) < period or period <= 0:
        return None
    return sum(values[-period:]) / period


def ema(values: List[float], period: int) -> Optional[float]:
    """Exponential moving average (last value). Seeded with the SMA."""
    if len(values) < period or period <= 0:
        return None
    k = 2 / (period + 1)
    e = sum(values[:period]) / period  # seed with SMA of first `period`
    for v in values[period:]:
        e = v * k + e * (1 - k)
    return e


def rsi(values: List[float], period: int = 14) -> Optional[float]:
    """
    Wilder's RSI of the last value. Use period=2 for the Connors mean-reversion
    setup, period=14 for the classic. Returns 0..100, or None if too few points.
    """
    if len(values) <= period or period <= 0:
        return None
    gains, losses = [], []
    for i in range(1, len(values)):
        ch = values[i] - values[i - 1]
        gains.append(max(ch, 0.0))
        losses.append(max(-ch, 0.0))
    # Seed with simple average of the first `period` changes, then Wilder-smooth.
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    for i in range(period, len(gains)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100.0 - (100.0 / (1.0 + rs))


def atr(bars: List[Dict], period: int = 14) -> Optional[float]:
    """
    Wilder's Average True Range over `period` bars (last value).
    On a daily timeframe this is the volatility unit used for stops & sizing.
    """
    if len(bars) <= period or period <= 0:
        return None
    trs = []
    for i in range(1, len(bars)):
        h, l = float(bars[i]["high"]), float(bars[i]["low"])
        prev_c = float(bars[i - 1]["close"])
        trs.append(max(h - l, abs(h - prev_c), abs(l - prev_c)))
    a = sum(trs[:period]) / period
    for i in range(period, len(trs)):
        a = (a * (period - 1) + trs[i]) / period
    return a


def vwap(bars: List[Dict]) -> Optional[float]:
    """
    Session VWAP (cumulative) through the last bar. Pass only the current
    session's bars — VWAP resets each day at the open. This is the institutional
    benchmark (~60-70% of US volume is algo-executed against VWAP).
    """
    if not bars:
        return None
    cum_pv = cum_v = 0.0
    for b in bars:
        tp = (float(b["high"]) + float(b["low"]) + float(b["close"])) / 3.0
        v = float(b["volume"])
        cum_pv += tp * v
        cum_v += v
    if cum_v == 0:
        return None
    return cum_pv / cum_v


def vwap_series(bars: List[Dict]) -> List[float]:
    """Running session VWAP, one value per bar (for plotting / signal logic)."""
    out, cum_pv, cum_v = [], 0.0, 0.0
    for b in bars:
        tp = (float(b["high"]) + float(b["low"]) + float(b["close"])) / 3.0
        v = float(b["volume"])
        cum_pv += tp * v
        cum_v += v
        out.append(cum_pv / cum_v if cum_v else tp)
    return out


def opening_range(bars: List[Dict], minutes: int = 5) -> Optional[Tuple[float, float]]:
    """
    (high, low) of the opening range — the bars within the first `minutes` of the
    session. Assumes `bars` starts at the 09:30 ET open and carries unix-ms
    `timestamp`s. The 5-minute range is the research-backed default.
    """
    if not bars:
        return None
    start = int(bars[0]["timestamp"])
    window = minutes * 60 * 1000
    hi, lo = float("-inf"), float("inf")
    used = False
    for b in bars:
        if int(b["timestamp"]) < start + window:
            hi = max(hi, float(b["high"]))
            lo = min(lo, float(b["low"]))
            used = True
        else:
            break
    return (hi, lo) if used else None


def relative_volume(today_open_volume: float, prior_open_volumes: List[float]) -> Optional[float]:
    """
    Relative volume (RVOL): today's opening volume divided by the average opening
    volume over prior days. The "stocks in play" filter from Zarattini et al.
    uses the first 5 minutes over the prior 14 days; RVOL > 1 = in play.
    """
    prior = [v for v in prior_open_volumes if v is not None]
    if not prior:
        return None
    avg = sum(prior) / len(prior)
    if avg == 0:
        return None
    return today_open_volume / avg
