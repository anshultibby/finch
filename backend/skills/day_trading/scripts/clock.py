"""
Market session clock — the single source of truth for "what time is it on Wall St".

Every decision the day-trading agent makes is window-dependent (opening range,
lunch chop, the close), and automations fire on UTC schedules from a UTC sandbox,
so NEVER use datetime.now() bare or assume the server is in ET. Use session().

DST-safe (zoneinfo, with a manual US-rule fallback) and NYSE-holiday-aware.
"""
from datetime import datetime, date, time, timedelta, timezone
from typing import Optional, Dict, Any

try:
    from zoneinfo import ZoneInfo
    _ET = ZoneInfo("America/New_York")
except Exception:  # tzdata missing in a minimal image — fall back to manual rule
    _ET = None

# NYSE full holidays (update yearly; a wrong miss just means a no-op run).
NYSE_HOLIDAYS = {
    # 2025
    "2025-01-01", "2025-01-20", "2025-02-17", "2025-04-18", "2025-05-26",
    "2025-06-19", "2025-07-04", "2025-09-01", "2025-11-27", "2025-12-25",
    # 2026
    "2026-01-01", "2026-01-19", "2026-02-16", "2026-04-03", "2026-05-25",
    "2026-06-19", "2026-07-03", "2026-09-07", "2026-11-26", "2026-12-25",
    # 2027
    "2027-01-01", "2027-01-18", "2027-02-15", "2027-03-26", "2027-05-31",
    "2027-06-18", "2027-07-05", "2027-09-06", "2027-11-25", "2027-12-24",
}
# 13:00 ET early closes
NYSE_EARLY_CLOSES = {
    "2025-07-03", "2025-11-28", "2025-12-24",
    "2026-11-27", "2026-12-24",
    "2027-11-26",
}


def _second_sunday(year: int, month: int) -> date:
    d = date(year, month, 1)
    first_sunday = d + timedelta(days=(6 - d.weekday()) % 7)
    return first_sunday + timedelta(days=7)


def _first_sunday(year: int, month: int) -> date:
    d = date(year, month, 1)
    return d + timedelta(days=(6 - d.weekday()) % 7)


def _et_offset(utc_dt: datetime) -> timedelta:
    """US Eastern offset for a UTC moment, by the post-2007 DST rule."""
    y = utc_dt.year
    # DST runs 2nd Sunday of March 07:00 UTC → 1st Sunday of Nov 06:00 UTC
    start = datetime.combine(_second_sunday(y, 3), time(7, 0), tzinfo=timezone.utc)
    end = datetime.combine(_first_sunday(y, 11), time(6, 0), tzinfo=timezone.utc)
    return timedelta(hours=-4) if start <= utc_dt < end else timedelta(hours=-5)


def now_et() -> datetime:
    """Current time in US Eastern (timezone-aware)."""
    utc = datetime.now(timezone.utc)
    if _ET is not None:
        return utc.astimezone(_ET)
    return (utc + _et_offset(utc)).replace(tzinfo=timezone(_et_offset(utc)))


def to_et(ts_ms: int) -> datetime:
    """Unix-ms timestamp (polygon bar format) → ET datetime."""
    utc = datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc)
    if _ET is not None:
        return utc.astimezone(_ET)
    return (utc + _et_offset(utc)).replace(tzinfo=timezone(_et_offset(utc)))


def is_trading_day(d: Optional[date] = None) -> bool:
    d = d or now_et().date()
    return d.weekday() < 5 and d.isoformat() not in NYSE_HOLIDAYS


def close_time(d: Optional[date] = None) -> time:
    d = d or now_et().date()
    return time(13, 0) if d.isoformat() in NYSE_EARLY_CLOSES else time(16, 0)


def session(now: Optional[datetime] = None) -> Dict[str, Any]:
    """
    The one call every automation should make FIRST.

    Returns:
        {
          "et": "2026-06-10T09:41:12-04:00",
          "date": "2026-06-10",
          "trading_day": True,
          "phase": "opening",       # premarket | opening | morning | lunch |
                                    # afternoon | power_hour | closed
          "minutes_since_open": 11.2 | None,
          "minutes_to_close": 378.8 | None,
          "early_close": False,
        }

    Phases (ET): premarket <09:30 · opening 09:30–10:30 · morning 10:30–11:30 ·
    lunch 11:30–14:00 (lowest edge — don't initiate) · afternoon 14:00–15:00 ·
    power_hour 15:00–close. Non-trading day or outside hours → "closed".
    """
    et = now or now_et()
    d = et.date()
    open_dt = et.replace(hour=9, minute=30, second=0, microsecond=0)
    c = close_time(d)
    close_dt = et.replace(hour=c.hour, minute=c.minute, second=0, microsecond=0)

    trading = is_trading_day(d)
    phase = "closed"
    mins_open = mins_close = None
    if trading:
        if et < open_dt:
            phase = "premarket"
        elif et >= close_dt:
            phase = "closed"
        else:
            mins_open = (et - open_dt).total_seconds() / 60
            mins_close = (close_dt - et).total_seconds() / 60
            hhmm = et.hour * 60 + et.minute
            if hhmm < 10 * 60 + 30:
                phase = "opening"
            elif hhmm < 11 * 60 + 30:
                phase = "morning"
            elif hhmm < 14 * 60:
                phase = "lunch"
            elif hhmm < 15 * 60:
                phase = "afternoon"
            else:
                phase = "power_hour"

    return {
        "et": et.isoformat(),
        "date": d.isoformat(),
        "trading_day": trading,
        "phase": phase,
        "minutes_since_open": round(mins_open, 1) if mins_open is not None else None,
        "minutes_to_close": round(mins_close, 1) if mins_close is not None else None,
        "early_close": d.isoformat() in NYSE_EARLY_CLOSES,
    }


def rth_only(bars: list, d: Optional[date] = None) -> list:
    """
    Filter polygon bars (unix-ms `timestamp`) to regular trading hours of one ET
    day. Polygon minute aggs INCLUDE premarket/after-hours — never compute an
    opening range, VWAP, or RVOL without this filter.
    """
    out = []
    for b in bars:
        et = to_et(int(b["timestamp"]))
        if d is not None and et.date() != d:
            continue
        hhmm = et.hour * 60 + et.minute
        if 9 * 60 + 30 <= hhmm < close_time(et.date()).hour * 60 + close_time(et.date()).minute:
            out.append(b)
    return out


def group_rth_by_day(bars: list) -> Dict[str, list]:
    """RTH bars grouped by ET date string — for multi-day RVOL baselines."""
    by_day: Dict[str, list] = {}
    for b in bars:
        et = to_et(int(b["timestamp"]))
        hhmm = et.hour * 60 + et.minute
        c = close_time(et.date())
        if 9 * 60 + 30 <= hhmm < c.hour * 60 + c.minute:
            by_day.setdefault(et.date().isoformat(), []).append(b)
    return by_day
