"""
Portfolio analytics — computes allocation, concentration, weighted beta, and
dividend income from a list of holdings, enriching each with FMP fundamentals.
Pure logic so it's unit-testable and callable from the agent tool.
"""
from typing import List, Dict
from schemas.portfolio_analytics import (
    Holding, AnalyticsView, Allocation, TopHolding,
)


def _enrich(symbols: List[str]) -> Dict[str, dict]:
    """Fetch sector/beta/lastDiv/price per symbol (FMP profile, cached)."""
    from skills.financial_modeling_prep.scripts.api import fmp
    out: Dict[str, dict] = {}
    for sym in symbols:
        try:
            r = fmp(f"/profile/{sym}")
            d = r[0] if isinstance(r, list) and r else (r if isinstance(r, dict) else {})
            if d and not d.get("error"):
                out[sym] = d
        except Exception:
            continue
    return out


def analyze(holdings: List[Holding]) -> AnalyticsView:
    # Collapse duplicate symbols (same ticker across accounts).
    merged: Dict[str, float] = {}
    for h in holdings:
        if h.symbol and h.value:
            merged[h.symbol.upper()] = merged.get(h.symbol.upper(), 0.0) + float(h.value)

    total = sum(merged.values()) or 1.0
    profiles = _enrich(list(merged.keys()))

    # Sector allocation
    sector_val: Dict[str, float] = {}
    for sym, val in merged.items():
        sector = (profiles.get(sym, {}) or {}).get("sector") or "Unknown"
        sector_val[sector] = sector_val.get(sector, 0.0) + val
    sector_allocation = [
        Allocation(label=s, value=v, weight=v / total)
        for s, v in sorted(sector_val.items(), key=lambda kv: kv[1], reverse=True)
    ]

    # Top holdings
    ranked = sorted(merged.items(), key=lambda kv: kv[1], reverse=True)
    top_holdings = [
        TopHolding(
            symbol=sym, value=val, weight=val / total,
            sector=(profiles.get(sym, {}) or {}).get("sector"),
            beta=(profiles.get(sym, {}) or {}).get("beta"),
        )
        for sym, val in ranked[:10]
    ]
    top5_concentration = sum(v for _, v in ranked[:5]) / total
    largest = (ranked[0][1] / total) if ranked else 0.0

    # Weighted beta (over holdings we have a beta for; renormalized)
    beta_num = 0.0
    beta_weight = 0.0
    div_income = 0.0
    enriched = 0
    for sym, val in merged.items():
        p = profiles.get(sym)
        if not p:
            continue
        enriched += 1
        beta = p.get("beta")
        if isinstance(beta, (int, float)):
            beta_num += (val / total) * beta
            beta_weight += val / total
        last_div = p.get("lastDiv") or 0
        price = p.get("price") or 0
        if last_div and price:
            div_income += val * (last_div / price)

    weighted_beta = (beta_num / beta_weight) if beta_weight > 0 else None

    return AnalyticsView(
        total_value=total if merged else 0.0,
        holding_count=len(merged),
        sector_allocation=sector_allocation,
        top_holdings=top_holdings,
        top5_concentration=top5_concentration,
        largest_position_weight=largest,
        weighted_beta=round(weighted_beta, 2) if weighted_beta is not None else None,
        annual_dividend_income=round(div_income, 2),
        dividend_yield=(div_income / total) if total else 0.0,
        enriched_count=enriched,
    )
