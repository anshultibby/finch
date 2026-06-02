"""
Typed wrappers over the Indian Stock Market API (indianapi.in) endpoints.

All NSE/BSE-listed Indian equities, mutual funds, IPOs and commodities. Companies
are addressed by NAME (e.g. "MTAR Technologies", "Reliance"), not ticker. Use
``search_industry`` or the company's exact name; the ``/stock`` response echoes
the BSE/NSE codes under ``companyProfile``.

Prices are INR (₹). Timestamps are IST. Import what you need:

    from skills.indian_stocks.scripts.stocks import stock, target_price, quarterly_results
"""
from typing import Any, List, Optional

from ._client import get

# ── Company / stock ──────────────────────────────────────────────────────────


def stock(name: str) -> Any:
    """The big one-call endpoint. Returns the full mosaic for a company:
    companyProfile (+ peerCompanyList, officers, BSE/NSE codes), currentPrice
    (BSE/NSE), financials, keyMetrics (margins, valuation, growth, persharedata,
    financialstrength, mgmtEffectiveness), analystView, recosBar (consensus
    rating), riskMeter, shareholding, stockCorporateActionData (bonus/dividend/
    rights/splits/AGM/board meetings), stockTechnicalData, yearHigh/yearLow.

    This usually answers a whole "analyse this stock after Q4" question in one
    request — reach for the dedicated endpoints below only for extra detail.
    """
    return get("/stock", {"name": name})


def target_price(stock_id: str) -> Any:
    """Analyst consensus price target: Mean/Median/High/Low, NumberOfEstimates,
    StandardDeviation (INR) + historical snapshots. `stock_id` is the company name."""
    return get("/stock_target_price", {"stock_id": stock_id})


def forecasts(
    stock_id: str,
    measure_code: str = "EPS",
    period_type: str = "Annual",
    data_type: str = "Actuals",
    age: str = "Current",
) -> Any:
    """Analyst estimates vs actuals for a measure over time.
    measure_code: EPS | Revenue | NetProfit | EBITDA | ... (per-stock coverage varies)
    period_type:  Annual | Interim
    data_type:    Actuals | Estimates
    age:          Current | OneWeekAgo | OneMonthAgo | ...
    """
    return get(
        "/stock_forecasts",
        {
            "stock_id": stock_id,
            "measure_code": measure_code,
            "period_type": period_type,
            "data_type": data_type,
            "age": age,
        },
    )


def corporate_actions(stock_name: str) -> Any:
    """Board meetings, dividends, splits, bonus, rights, AGM for a company."""
    return get("/corporate_actions", {"stock_name": stock_name})


# ── Financials / history (HEAVY — currently 504 on the free plan) ────────────
# NOTE: As of the free plan these four endpoints return HTTP 504 (server-side
# gateway timeout). Don't rely on them. The good news: stock() already EMBEDS
# what they'd return — financials (18 periods incl. quarterly, with QoQ/YoY
# comparisons), the full shareholding time series, and corporate actions. So for
# the "Q4 result analysis" flow, read it off stock()["financials"] /
# stock()["shareholding"] instead. These wrappers are kept for when the plan is
# upgraded; each retries once.


def quarterly_results(stock_name: str) -> Any:
    """Historical quarterly results. ⚠️ Returns 504 on the free plan — prefer
    ``stock(name)["financials"]`` (18 periods, includes quarterly + QoQ/YoY)."""
    return historical_stats(stock_name, "quarter_results")


def historical_stats(stock_name: str, stats: str) -> Any:
    """Historical fundamentals tables. ⚠️ 504 on the free plan (see module note).
    stats: quarter_results | yoy_results | balancesheet | cashflow | ratios |
           shareholding_pattern_quarterly | shareholding_pattern_yearly"""
    return get("/historical_stats", {"stock_name": stock_name, "stats": stats})


def statement(stock_name: str, stats: str) -> Any:
    """Standardised financial statements. ⚠️ 504 on the free plan.
    stats: profit_loss | balancesheet | cashflow (annual)."""
    return get("/statement", {"stock_name": stock_name, "stats": stats})


def historical_data(stock_name: str, period: str = "1m", filter: str = "price") -> Any:
    """Historical price/volume series. ⚠️ 504 on the free plan (use FMP's
    ``get_historical_prices('<SYM>.NS', ...)`` for Indian price history instead).
    period: 1m | 6m | 1yr | 3yr | 5yr | 10yr | max   filter: price | pe | sm"""
    return get(
        "/historical_data", {"stock_name": stock_name, "period": period, "filter": filter}
    )


def recent_announcements(stock_name: str) -> Any:
    """Recent exchange announcements/filings. ⚠️ 504 on the free plan — use
    ``corporate_actions(stock_name)`` (board meetings) instead."""
    return get("/recent_announcements", {"stock_name": stock_name})


# ── Market overview / discovery ──────────────────────────────────────────────


def trending(exchange: Optional[str] = None) -> Any:
    """Top gainers and losers. Optional exchange: NSE | BSE."""
    return get("/trending", {"exchange": exchange} if exchange else None)


def fifty_two_week_high_low() -> Any:
    """Stocks at 52-week highs/lows for both BSE and NSE."""
    return get("/fetch_52_week_high_low_data")


def nse_most_active() -> Any:
    """Highest-volume NSE stocks."""
    return get("/NSE_most_active")


def bse_most_active() -> Any:
    """Highest-volume BSE stocks."""
    return get("/BSE_most_active")


def price_shockers() -> Any:
    """Stocks with large intraday price swings (BSE + NSE)."""
    return get("/price_shockers")


def search_industry(query: str) -> Any:
    """Find companies by industry/sector keyword (returns ids + names)."""
    return get("/industry_search", {"query": query})


# ── News ─────────────────────────────────────────────────────────────────────


def news(page_no: int = 1, size: int = 20) -> Any:
    """Latest market news headlines (paginated)."""
    return get("/news", {"page_no": page_no, "size": size})


# ── IPO ──────────────────────────────────────────────────────────────────────


def ipo() -> Any:
    """Upcoming, open, and recently listed IPOs with subscription data."""
    return get("/ipo")


# ── Mutual funds ─────────────────────────────────────────────────────────────


def mutual_funds() -> Any:
    """Full MF catalogue by category with NAV and 1/3/5-yr returns."""
    return get("/mutual_funds")


def mutual_fund_details(stock_name: str) -> Any:
    """Details for a specific mutual fund (basic info, returns, holdings)."""
    return get("/mutual_funds_details", {"stock_name": stock_name})


def search_mutual_fund(query: str) -> Any:
    """Find mutual fund schemes by name."""
    return get("/mutual_fund_search", {"query": query})


# ── Commodities ──────────────────────────────────────────────────────────────


def commodities() -> Any:
    """Live MCX commodity futures (gold, silver, crude, etc.)."""
    return get("/commodities")
