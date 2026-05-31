"""
Screener service — runs a ScreenSpec against FMP's /stock-screener and returns
normalized rows. Pure logic (no FastAPI deps) so it can be unit-tested and also
called directly by the agent tool.
"""
from typing import List
from schemas.screener import ScreenSpec, ScreenRow

# Map our sortBy keys to the FMP row fields.
_SORT_FIELD = {
    "marketCap": "marketCap",
    "price": "price",
    "beta": "beta",
    "volume": "volume",
    "dividend": "lastAnnualDividend",
    "companyName": "companyName",
}


_MAJOR_US = {"NASDAQ", "NYSE", "AMEX", "NYSEARCA", "BATS", "CBOE"}


def _listing_score(row: dict) -> int:
    """Prefer the primary US listing of a company over foreign cross-listings
    (e.g. MRK over OQAH.L / 6MK.DE)."""
    sym = row.get("symbol") or ""
    exch = (row.get("exchangeShortName") or "").upper()
    score = 0
    if "." not in sym:
        score += 2
    if exch in _MAJOR_US:
        score += 1
    return score


def _dedupe_listings(rows: list) -> list:
    """Collapse same-company cross-listings, keeping the best (US-primary) one."""
    best: dict = {}
    order: list = []
    for r in rows:
        name = (r.get("companyName") or r.get("symbol") or "").strip().lower()
        if not name:
            continue
        if name not in best:
            order.append(name)
            best[name] = r
        elif _listing_score(r) > _listing_score(best[name]):
            best[name] = r
    return [best[n] for n in order]


def _spec_to_fmp_params(spec: ScreenSpec) -> dict:
    """Build FMP /stock-screener query params from the spec's filters."""
    f = spec.filters
    params: dict = {}
    for field, value in f.model_dump(exclude_none=True).items():
        # FMP expects bools as lowercase strings.
        if isinstance(value, bool):
            params[field] = "true" if value else "false"
        else:
            params[field] = value
    # Over-fetch so we can sort/limit ourselves deterministically.
    params["limit"] = max(spec.limit * 4, 100)
    return params


def run_screen(spec: ScreenSpec) -> List[ScreenRow]:
    """Execute a screen and return sorted, limited, normalized rows."""
    # Imported lazily so the module can be imported without FMP configured.
    from skills.financial_modeling_prep.scripts.api import fmp

    raw = fmp("/stock-screener", _spec_to_fmp_params(spec))
    if not isinstance(raw, list):
        return []

    # For US screens (the default), keep only major US exchanges so foreign
    # cross-listings and KOSDAQ/LSE tickers with junk data don't leak in.
    if (spec.filters.country or "US") == "US":
        raw = [r for r in raw if (r.get("exchangeShortName") or "").upper() in _MAJOR_US]

    raw = _dedupe_listings(raw)

    sort_field = _SORT_FIELD.get(spec.sortBy, "marketCap")
    reverse = spec.sortDir == "desc"

    def _norm(v):
        return v.lower() if isinstance(v, str) else v

    # Partition so rows missing the sort field always land at the end,
    # independent of sort direction.
    present = [r for r in raw if r.get(sort_field) is not None]
    missing = [r for r in raw if r.get(sort_field) is None]
    present.sort(key=lambda r: _norm(r.get(sort_field)), reverse=reverse)
    rows = (present + missing)[: spec.limit]

    return [
        ScreenRow(
            symbol=r.get("symbol"),
            companyName=r.get("companyName"),
            marketCap=r.get("marketCap"),
            sector=r.get("sector"),
            industry=r.get("industry"),
            beta=r.get("beta"),
            price=r.get("price"),
            lastAnnualDividend=r.get("lastAnnualDividend"),
            volume=r.get("volume"),
            exchangeShortName=r.get("exchangeShortName"),
            isEtf=r.get("isEtf"),
        )
        for r in rows
        if r.get("symbol")
    ]
