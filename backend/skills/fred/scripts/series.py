"""
FRED data series — observations, latest values, and search.

KEY_SERIES maps the macro indicators that move markets to their FRED ids, so
agents don't have to guess ids. Anything else: search_series() first.
"""
from typing import Optional, Dict, Any, List
from ._client import fred

# The market-moving core. id → (description, units note)
KEY_SERIES: Dict[str, str] = {
    "CPIAUCSL":  "CPI, all items (index; % change = inflation print)",
    "CPILFESL":  "Core CPI, ex food & energy (index)",
    "PCEPILFE":  "Core PCE price index — the Fed's preferred gauge",
    "PAYEMS":    "Nonfarm payrolls, thousands (NFP — monthly change is the print)",
    "UNRATE":    "Unemployment rate, %",
    "ICSA":      "Initial jobless claims, weekly",
    "GDPC1":     "Real GDP, quarterly annualized",
    "RSAFS":     "Retail sales, monthly",
    "FEDFUNDS":  "Effective fed funds rate, %",
    "DFEDTARU":  "Fed funds target range, upper bound, % (moves at FOMC)",
    "DGS2":      "2-year Treasury yield, % (daily)",
    "DGS10":     "10-year Treasury yield, % (daily)",
    "T10Y2Y":    "10y–2y spread, % (daily; curve inversion)",
    "VIXCLS":    "VIX close (daily)",
}


def get_series(series_id: str, limit: int = 100, start: Optional[str] = None,
               end: Optional[str] = None, units: Optional[str] = None) -> Dict[str, Any]:
    """
    Observations for a series, newest LAST.
      units: None=levels, "pch"=% change, "pc1"=% change vs year ago (use "pc1"
             on CPIAUCSL/CPILFESL/PCEPILFE to get the headline inflation rate).
    Returns {"series_id", "observations": [{"date", "value": float|None}, ...]}.
    """
    params: Dict[str, Any] = {"series_id": series_id, "limit": limit,
                              "sort_order": "desc"}
    if start:
        params["observation_start"] = start
    if end:
        params["observation_end"] = end
    if units:
        params["units"] = units
    resp = fred("series/observations", **params)
    if "error" in resp:
        return resp
    obs = [{"date": o["date"],
            "value": float(o["value"]) if o["value"] not in (".", "") else None}
           for o in resp.get("observations", [])]
    obs.reverse()  # oldest → newest
    return {"series_id": series_id.upper(), "observations": obs}


def latest(series_id: str, units: Optional[str] = None) -> Dict[str, Any]:
    """Most recent non-null observation: {"series_id", "date", "value"}."""
    resp = get_series(series_id, limit=5, units=units)
    if "error" in resp:
        return resp
    for o in reversed(resp["observations"]):
        if o["value"] is not None:
            return {"series_id": resp["series_id"], **o}
    return {"error": f"no recent data for {series_id}"}


def search_series(text: str, limit: int = 10) -> List[Dict[str, str]]:
    """Find series ids by keyword. Returns [{"id", "title", "frequency", "units"}]."""
    resp = fred("series/search", search_text=text, limit=limit,
                order_by="popularity", sort_order="desc")
    if "error" in resp:
        return [resp]
    return [{"id": s["id"], "title": s["title"], "frequency": s["frequency_short"],
             "units": s["units_short"]} for s in resp.get("seriess", [])]


def macro_snapshot() -> Dict[str, Any]:
    """One-call macro picture: latest value for each KEY_SERIES (inflation
    series returned as % vs year ago). ~14 API calls."""
    out = {}
    for sid, desc in KEY_SERIES.items():
        units = "pc1" if sid in ("CPIAUCSL", "CPILFESL", "PCEPILFE") else None
        v = latest(sid, units=units)
        out[sid] = {**v, "what": desc} if "error" not in v else {"error": v["error"], "what": desc}
    return out
