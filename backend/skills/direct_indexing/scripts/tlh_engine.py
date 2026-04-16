"""
Professional Tax Loss Harvesting Engine

Implements institutional-grade TLH:
- HIFO (Highest In, First Out) lot selection
- Short-term loss prioritization over long-term
- Correlation-based substitute security selection
- 61-day wash sale window tracking (30 before + sale day + 30 after)
- Harvest threshold gate (only harvest when benefit > cost)
- DRIP suppression awareness
"""
from datetime import date, timedelta
from typing import List, Dict, Any, Optional, Tuple
import statistics


# ---------------------------------------------------------------------------
# Types
# ---------------------------------------------------------------------------

class TaxLot:
    """A single cost-basis lot within a position."""
    def __init__(
        self,
        symbol: str,
        shares: float,
        cost_basis_per_share: float,
        purchase_date: date,
        current_price: float,
    ):
        self.symbol = symbol
        self.shares = shares
        self.cost_basis_per_share = cost_basis_per_share
        self.purchase_date = purchase_date
        self.current_price = current_price

    @property
    def is_short_term(self) -> bool:
        """Short-term = held < 1 year (365 days)."""
        return (date.today() - self.purchase_date).days < 365

    @property
    def holding_days(self) -> int:
        return (date.today() - self.purchase_date).days

    @property
    def unrealized_gain_per_share(self) -> float:
        return self.current_price - self.cost_basis_per_share

    @property
    def unrealized_gain_total(self) -> float:
        return self.unrealized_gain_per_share * self.shares

    @property
    def loss_pct(self) -> float:
        """Negative = loss. e.g., -0.15 means 15% below cost basis."""
        if self.cost_basis_per_share == 0:
            return 0.0
        return (self.current_price - self.cost_basis_per_share) / self.cost_basis_per_share

    def to_dict(self) -> Dict[str, Any]:
        return {
            'symbol': self.symbol,
            'shares': round(self.shares, 4),
            'cost_basis_per_share': round(self.cost_basis_per_share, 4),
            'current_price': round(self.current_price, 4),
            'purchase_date': self.purchase_date.isoformat(),
            'holding_days': self.holding_days,
            'is_short_term': self.is_short_term,
            'unrealized_gain_total': round(self.unrealized_gain_total, 2),
            'loss_pct': round(self.loss_pct * 100, 2),
        }


# ---------------------------------------------------------------------------
# Wash Sale Window
# ---------------------------------------------------------------------------

def is_in_wash_sale_window(
    symbol: str,
    wash_sale_log: List[Dict[str, Any]],
    reference_date: Optional[date] = None,
) -> bool:
    """
    Returns True if buying `symbol` on `reference_date` would trigger a wash sale.

    A wash sale occurs if the same (or substantially identical) security was sold
    at a loss within the 30-day window BEFORE or the 30-day window AFTER the
    reference date. For buying, we only need to check: was it sold at a loss
    within the last 30 days, OR is there a planned purchase within 30 days of a
    recent sale?

    In practice, the safe rule is: do not buy a security if it was sold at a loss
    within the last 31 days (the "31-day hold" rule for substitutes).

    Args:
        symbol:         Ticker to check
        wash_sale_log:  List of {symbol, sale_date (YYYY-MM-DD), was_loss: bool}
        reference_date: Date of proposed purchase (defaults to today)

    Returns:
        True if buying this symbol would constitute a wash sale
    """
    if reference_date is None:
        reference_date = date.today()

    for entry in wash_sale_log:
        if entry.get('symbol', '').upper() != symbol.upper():
            continue
        if not entry.get('was_loss', False):
            continue
        sale_date = date.fromisoformat(entry['sale_date'])
        # Within 30 days before or 30 days after the sale is disallowed.
        # When buying, the relevant check is: are we within 30 days AFTER a sale?
        days_since_sale = (reference_date - sale_date).days
        if 0 <= days_since_sale <= 30:
            return True

    return False


def wash_sale_safe_after(sale_date: date) -> date:
    """Returns the first date it is safe to repurchase the harvested security."""
    return sale_date + timedelta(days=31)


# ---------------------------------------------------------------------------
# HIFO Lot Selection
# ---------------------------------------------------------------------------

def hifo_sort(lots: List[TaxLot]) -> List[TaxLot]:
    """
    Sort lots in HIFO order for selling:
    1. Short-term losses first (more valuable: ST rate vs LT rate delta ~17 ppts)
    2. Within ST: highest cost basis first (largest loss)
    3. Then long-term losses, same ordering
    4. Gains last (avoid realizing gains)

    This maximizes after-tax value of every harvest decision.
    """
    def sort_key(lot: TaxLot):
        is_gain = lot.unrealized_gain_total >= 0
        # (is_gain, is_long_term, cost_basis ascending = loss descending)
        return (
            int(is_gain),               # 0 = loss first, 1 = gain last
            int(not lot.is_short_term), # 0 = short-term first, 1 = long-term second
            -lot.cost_basis_per_share,  # highest cost basis first (largest loss)
        )
    return sorted(lots, key=sort_key)


# ---------------------------------------------------------------------------
# Harvest Candidate Detection
# ---------------------------------------------------------------------------

def find_harvest_candidates(
    lots: List[TaxLot],
    threshold_loss_pct: float = 3.0,
    min_dollar_loss: float = 100.0,
    tax_rate_st: float = 0.37,
    tax_rate_lt: float = 0.238,
) -> List[Dict[str, Any]]:
    """
    Find tax lots that are worth harvesting after applying cost-benefit filters.

    Args:
        lots:               All tax lots across the portfolio
        threshold_loss_pct: Only harvest lots > this % below cost basis (default 3%)
                            Frec uses 3%, academic literature uses 5%
        min_dollar_loss:    Minimum unrealized loss in dollars to bother (default $100)
                            Filters noise and avoids high-turnover on tiny positions
        tax_rate_st:        Short-term capital gains rate (default 37% federal)
        tax_rate_lt:        Long-term capital gains rate (default 23.8% = 20% + 3.8% NIIT)

    Returns:
        List of harvest opportunity dicts, sorted by tax_savings descending
    """
    candidates = []

    for lot in lots:
        # Only harvest losses
        if lot.unrealized_gain_total >= 0:
            continue

        # Apply threshold gate
        loss_pct = abs(lot.loss_pct) * 100  # e.g., 15.0 for 15% loss
        if loss_pct < threshold_loss_pct:
            continue

        dollar_loss = abs(lot.unrealized_gain_total)
        if dollar_loss < min_dollar_loss:
            continue

        tax_rate = tax_rate_st if lot.is_short_term else tax_rate_lt
        tax_savings = dollar_loss * tax_rate
        position_value = lot.shares * lot.current_price

        # Days until this lot crosses the 1-year mark and becomes long-term.
        # Negative means it's already long-term.
        days_until_lt = max(0, 365 - lot.holding_days) if lot.is_short_term else 0

        candidates.append({
            **lot.to_dict(),
            'dollar_loss': round(dollar_loss, 2),
            'loss_pct': round(loss_pct, 2),
            'position_value': round(position_value, 2),
            'tax_rate': tax_rate,
            'tax_rate_st': tax_rate_st,
            'tax_rate_lt': tax_rate_lt,
            'estimated_tax_savings': round(tax_savings, 2),
            'term': 'short-term' if lot.is_short_term else 'long-term',
            'days_until_long_term': days_until_lt,
            # Surface if waiting to harvest at LT rate is worth considering.
            # Only relevant when the position is ST and close to the 1-year mark.
            'consider_waiting_for_lt': lot.is_short_term and days_until_lt <= 45,
        })

    # Sort: short-term losses first (higher tax value), then by dollar loss descending
    candidates.sort(key=lambda c: (-int(c['is_short_term']), -c['estimated_tax_savings']))
    return candidates


# ---------------------------------------------------------------------------
# Substitute Security Selection
# ---------------------------------------------------------------------------

def find_substitute_candidates(
    sold_symbol: str,
    universe: Optional[List[str]] = None,
    wash_sale_log: Optional[List[Dict[str, Any]]] = None,
    min_correlation: float = 0.80,
    lookback_days: int = 252,
    top_n: int = 5,
    existing_holdings: Optional[List[str]] = None,
    min_market_cap: int = 0,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Return a ranked list of substitute candidates for `sold_symbol`.

    Use this when the agent needs to reason about tradeoffs — e.g. the top
    candidate by correlation is already a large position in the portfolio, or
    the user has a preference between two similarly-correlated options.

    `find_best_correlated_substitute` (below) wraps this and returns only the
    top pick — use that inside `build_tlh_plan` for automated plans.

    When `universe` is None (default), automatically builds a candidate pool
    from all US stocks above `min_market_cap` ($2B default), narrowed to the
    same sector as `sold_symbol` first. If the sector pool is < 20 stocks,
    falls back to the full market-cap universe.

    Search order:
      1. FMP sector peers intersected with universe — tightest economic match,
         definitively not "substantially identical" to any individual stock.
      2. Full universe — broader fallback.

    Correlation is computed from daily adjClose returns over `lookback_days`.

    Args:
        sold_symbol:       Ticker being harvested.
        universe:          Candidate pool. If None, auto-builds from market-cap screener.
        wash_sale_log:     [{symbol, sale_date, was_loss}] — blocked symbols.
        min_correlation:   Minimum R to include in results (default 0.80).
                           Candidates below this are still returned but flagged.
        lookback_days:     Days of price history for correlation (default 252 = 1 trading year).
        top_n:             Number of candidates to return (default 5).
        existing_holdings: Tickers the user already holds — flagged in results
                           so the agent can factor in concentration risk.
        min_market_cap:    Minimum market cap for auto-built universe (default 0 = no filter).
                           Ignored if `universe` is explicitly provided.

    Returns:
        Tuple of (candidates, sold_returns):
        - candidates: List of up to `top_n` dicts, sorted sector-peers first then by correlation:
          [{symbol, correlation, search_pool, is_sector_peer, below_threshold, already_held,
            wash_sale_risk, wash_sale_safe, returns: {1m, 3m, 6m, 1y}}]
        - sold_returns: {1m, 3m, 6m, 1y} pct changes for the sold symbol itself
        Returns ([], {}) if no price data found.
    """
    from skills.financial_modeling_prep.scripts.market.historical_prices import get_batch_historical_prices

    if wash_sale_log is None:
        wash_sale_log = []

    # Auto-build universe from market-cap screener if not provided
    if universe is None:
        sector = get_symbol_sector(sold_symbol)
        universe = get_tradeable_universe(min_market_cap, sector=sector)
        if len(universe) < 20:
            # Sector too narrow (e.g. rare sector or API gap) — fall back to full universe
            universe = get_tradeable_universe(min_market_cap)

    universe_set = {s.upper() for s in universe}
    held_set = {s.upper() for s in (existing_holdings or [])}
    blocked = {sold_symbol.upper()} | {
        e['symbol'].upper() for e in wash_sale_log
        if is_in_wash_sale_window(e['symbol'], wash_sale_log)
    }

    sector_peer_set = {
        s.upper() for s in _get_peers_fallback(sold_symbol)
        if s.upper() in universe_set and s.upper() not in blocked
    }
    full_eligible = [
        s for s in universe
        if s.upper() not in blocked and s.upper() != sold_symbol.upper()
    ]

    if not full_eligible and not sector_peer_set:
        return [], {}

    # Convert trading days → calendar days (5 trading days per 7 calendar days + buffer)
    calendar_days = int(lookback_days * 7 / 5) + 14
    from_date = (date.today() - timedelta(days=calendar_days)).isoformat()
    to_date = date.today().isoformat()

    all_syms = list({sold_symbol} | sector_peer_set | set(full_eligible))
    batch = get_batch_historical_prices(all_syms, from_date=from_date, to_date=to_date)

    if sold_symbol not in batch or not batch[sold_symbol].get('prices'):
        return [], {}

    def _price_map(prices_list: list) -> dict:
        """Build {date_str: price} map, preferring adjClose and falling back to close."""
        result = {}
        for p in prices_list:
            if not p.get('date'):
                continue
            price = p.get('adjClose') or p.get('close')
            if price:
                result[p['date']] = price
        return result

    sold_map = _price_map(batch[sold_symbol]['prices'])
    if len(sold_map) < 31:
        return [], {}

    sold_dates = sorted(sold_map.keys(), reverse=True)

    def _period_pct(price_map: dict, dates_newest_first: list, n_trading_days: int) -> Optional[float]:
        """Return % change over the last n trading days, or None if insufficient data."""
        if len(dates_newest_first) <= n_trading_days:
            return None
        recent = price_map[dates_newest_first[0]]
        start = price_map[dates_newest_first[n_trading_days]]
        return round((recent / start - 1) * 100, 1) if start else None

    sold_returns = {
        '1m':  _period_pct(sold_map, sold_dates, 22),
        '3m':  _period_pct(sold_map, sold_dates, 66),
        '6m':  _period_pct(sold_map, sold_dates, 132),
        '1y':  _period_pct(sold_map, sold_dates, 252),
    }

    scored = []
    for sym in full_eligible:
        if sym not in batch:
            continue
        cand_map = _price_map(batch[sym]['prices'])

        # Align by date — avoids index drift from trading halts / missing days
        common_dates = sorted(sold_map.keys() & cand_map.keys(), reverse=True)
        if len(common_dates) < 31:
            continue

        # Daily returns on common dates (newest-first order)
        sold_closes = [sold_map[d] for d in common_dates]
        cand_closes = [cand_map[d] for d in common_dates]
        sold_rets = [sold_closes[i] / sold_closes[i + 1] - 1 for i in range(len(common_dates) - 1)]
        cand_rets = [cand_closes[i] / cand_closes[i + 1] - 1 for i in range(len(common_dates) - 1)]

        try:
            corr = statistics.correlation(sold_rets, cand_rets)
        except Exception:
            continue

        wash_risk = classify_substitute_risk(sold_symbol, sym)

        # Correlation quality bands:
        #   STRONG  (≥ 0.85): tight hedge, low tracking error risk
        #   GOOD    (≥ 0.70): acceptable hedge for most situations
        #   WEAK    (≥ 0.40): loose hedge, meaningful tracking error — flag but usable
        #   POOR    (<  0.40): essentially uncorrelated, tracking error likely exceeds tax savings
        #   INVERSE (<  0.00): moves against you during hold — avoid
        if corr >= 0.85:
            corr_quality = 'STRONG'
        elif corr >= 0.70:
            corr_quality = 'GOOD'
        elif corr >= 0.40:
            corr_quality = 'WEAK'
        elif corr >= 0.0:
            corr_quality = 'POOR'
        else:
            corr_quality = 'INVERSE'

        cand_dates = sorted(cand_map.keys(), reverse=True)
        scored.append({
            'symbol': sym,
            'correlation': round(corr, 4),
            'correlation_quality': corr_quality,
            'search_pool': 'sector_peers' if sym.upper() in sector_peer_set else 'universe',
            'is_sector_peer': sym.upper() in sector_peer_set,
            'below_threshold': corr < min_correlation,
            'already_held': sym.upper() in held_set,
            'wash_sale_risk': wash_risk['risk_level'],
            'wash_sale_safe': wash_risk['is_safe'],
            # Compressed price context — lets the LLM reason about recent divergence
            'returns': {
                '1m':  _period_pct(cand_map, cand_dates, 22),
                '3m':  _period_pct(cand_map, cand_dates, 66),
                '6m':  _period_pct(cand_map, cand_dates, 132),
                '1y':  _period_pct(cand_map, cand_dates, 252),
            },
        })

    # Sort: sector peers first (semantically correct), then by correlation.
    scored.sort(key=lambda c: (not c['is_sector_peer'], -c['correlation']))
    return scored[:top_n], sold_returns


def find_best_correlated_substitute(
    sold_symbol: str,
    universe: Optional[List[str]] = None,
    wash_sale_log: Optional[List[Dict[str, Any]]] = None,
    min_correlation: float = 0.80,
    lookback_days: int = 252,
    existing_holdings: Optional[List[str]] = None,
    min_market_cap: int = 0,
) -> Optional[Dict[str, Any]]:
    """
    Return the single best substitute for `sold_symbol`.

    Wraps `find_substitute_candidates` and picks the top result.
    Used by `build_tlh_plan` for automated plans.

    When the agent needs to reason about multiple options (e.g. user already
    holds the top pick), call `find_substitute_candidates` instead.

    `universe` and `wash_sale_log` default to None — when None, the universe
    is built automatically from the $2B+ market-cap screener.

    Returns:
        {symbol, correlation, search_pool, reason, below_threshold} or None.
    """
    candidates, _ = find_substitute_candidates(
        sold_symbol=sold_symbol,
        universe=universe,
        wash_sale_log=wash_sale_log,
        min_correlation=min_correlation,
        lookback_days=lookback_days,
        top_n=5,
        existing_holdings=existing_holdings,
        min_market_cap=min_market_cap,
    )

    if not candidates:
        return None

    # Automated plan preference order:
    # (1) not INVERSE correlation — never pick something that moves against you
    # (2) not already held — avoids silently compounding concentration risk
    # (3) sector peers preferred — same-sector substitutes are semantically correct
    # (4) above min_correlation threshold
    # (5) highest correlation (already sorted, with sector peers first)
    safe = [c for c in candidates if c['correlation_quality'] != 'INVERSE']
    not_held = [c for c in safe if not c['already_held']]
    preferred = [c for c in not_held if not c['below_threshold']]
    # Try sector peers first at each tier
    pick = (
        next((c for c in preferred if c['is_sector_peer']), None)
        or (preferred[0] if preferred else None)
        or next((c for c in not_held if c['is_sector_peer']), None)
        or (not_held[0] if not_held else None)
        or (safe[0] if safe else candidates[0])
    )

    below = pick['below_threshold']
    return {
        'symbol': pick['symbol'],
        'correlation': pick['correlation'],
        'search_pool': pick['search_pool'],
        'reason': (
            f"{'sector peer' if pick['is_sector_peer'] else 'ETF universe'} substitute "
            f"(R={pick['correlation']:.3f})"
            if not below else
            f"best available substitute (R={pick['correlation']:.3f}, below {min_correlation} threshold — "
            f"verify before executing)"
        ),
        'below_threshold': below,
    }


def _get_peers_fallback(symbol: str) -> List[str]:
    """Fetch FMP sector peers for a symbol."""
    try:
        from skills.financial_modeling_prep.scripts.peers.stock_peers import get_stock_peers
        peers = get_stock_peers(symbol)
        return [p for p in peers if isinstance(p, str)] if isinstance(peers, list) else []
    except Exception:
        return []


def get_tradeable_universe(
    min_market_cap: int = 0,
    sector: Optional[str] = None,
    exchange: str = 'NASDAQ,NYSE',
    limit: int = 2000,
    cache_hours: int = 24,
) -> List[str]:
    """
    Return a list of US stock tickers, optionally filtered by market cap and sector.

    This is the default substitute universe for TLH — all exchange-listed US stocks
    on NASDAQ/NYSE, ordered by market cap descending. No minimum market cap by default,
    so mid-cap and small-cap names are included as candidates.

    Results are disk-cached for `cache_hours` (default 24h) to avoid repeat API calls.

    Args:
        min_market_cap:  Minimum market cap in dollars (default 0 = no filter).
                         Pass e.g. 2_000_000_000 to restrict to $2B+ large-caps.
        sector:          Optional FMP sector name to narrow search:
                         'Technology', 'Healthcare', 'Financial Services',
                         'Consumer Cyclical', 'Industrials', 'Energy',
                         'Consumer Defensive', 'Real Estate', 'Communication Services',
                         'Basic Materials', 'Utilities'
        exchange:        Comma-separated exchanges (default 'NASDAQ,NYSE').
        limit:           Max tickers to return (default 2000).
        cache_hours:     How long to cache results (default 24h).

    Returns:
        List of ticker strings, e.g. ['AAPL', 'MSFT', 'NVDA', ...]
    """
    import json
    import os
    import time

    cache_dir = '/tmp/tlh_universe_cache'
    sector_key = sector.replace(' ', '_').lower() if sector else 'all'
    cache_file = os.path.join(cache_dir, f'universe_{sector_key}_{min_market_cap}.json')

    # Return cached result if fresh enough
    if os.path.exists(cache_file):
        try:
            with open(cache_file) as f:
                cached = json.load(f)
            age_hours = (time.time() - cached.get('timestamp', 0)) / 3600
            if age_hours < cache_hours and cached.get('tickers'):
                return cached['tickers']
        except Exception:
            pass

    try:
        from skills.financial_modeling_prep.scripts.peers.stock_screener import screen_stocks

        results = screen_stocks(
            market_cap_more_than=min_market_cap if min_market_cap > 0 else None,
            sector=sector,
            country='US',
            exchange=exchange,
            limit=limit,
        )

        tickers = [r['symbol'] for r in (results or []) if r.get('symbol')]

        os.makedirs(cache_dir, exist_ok=True)
        with open(cache_file, 'w') as f:
            json.dump({'tickers': tickers, 'timestamp': time.time()}, f)

        return tickers
    except Exception:
        return []


def get_symbol_sector(symbol: str) -> Optional[str]:
    """
    Return the FMP sector name for a symbol, or None if unavailable.
    Used to narrow the substitute universe to the same sector first.
    """
    try:
        from skills.financial_modeling_prep.scripts.company.profile import get_profile
        profile = get_profile(symbol)
        if isinstance(profile, list) and profile:
            profile = profile[0]
        return profile.get('sector') if isinstance(profile, dict) else None
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Full TLH Plan
# ---------------------------------------------------------------------------

def build_tlh_plan(
    lots: List[TaxLot],
    wash_sale_log: Optional[List[Dict[str, Any]]] = None,
    etf_holdings: Optional[List[Dict[str, Any]]] = None,
    threshold_loss_pct: float = 3.0,
    min_dollar_loss: float = 100.0,
    tax_rate_st: float = 0.37,
    tax_rate_lt: float = 0.238,
    min_correlation: float = 0.85,
) -> Dict[str, Any]:
    """
    Generate a complete, ranked TLH execution plan for a portfolio.

    For each harvestable lot:
    1. Identify the loss and its tax value
    2. Find the highest-correlated substitute in the ETF constituent universe
    3. Enforce cross-opportunity wash sale safety: a stock cannot be both harvested
       (sold) and used as a substitute (bought) in the same plan
    4. Compute the safe repurchase date (31 days from today)
    5. Return actionable instructions

    Cross-opportunity conflict example:
        AMZN at a loss → substitute is MSFT (highest corr)
        MSFT also at a loss → MSFT is now blocked as a harvest candidate
        because we just bought it as AMZN's substitute. Selling MSFT immediately
        after buying it would disallow the MSFT loss (purchased within 30 days).
        The plan will warn about MSFT and skip it, or find MSFT a different sub.

    Args:
        lots:               All tax lots (use TaxLot objects)
        wash_sale_log:      Prior sales that might trigger wash sales.
                            Format: [{symbol, sale_date: YYYY-MM-DD, was_loss: bool}]
        etf_holdings:       ETF constituent list for finding in-index substitutes.
                            Format: [{'asset': 'MSFT', 'name': ...}, ...]
        threshold_loss_pct: Minimum loss % to harvest (default 3%)
        min_dollar_loss:    Minimum dollar loss to harvest (default $100)
        tax_rate_st:        Short-term gains tax rate (default 37%)
        tax_rate_lt:        Long-term gains tax rate (default 23.8%)
        min_correlation:    Minimum correlation for substitute (default 0.85)

    Returns:
        {
            harvest_opportunities: list of ranked opportunities with substitute info,
            total_losses_available: float,
            total_estimated_tax_savings: float,
            summary: str,
            warnings: list of warning strings,
        }
    """
    if wash_sale_log is None:
        wash_sale_log = []

    # Step 1: Find all harvest candidates (HIFO ordered, threshold filtered)
    candidates = find_harvest_candidates(
        lots,
        threshold_loss_pct=threshold_loss_pct,
        min_dollar_loss=min_dollar_loss,
        tax_rate_st=tax_rate_st,
        tax_rate_lt=tax_rate_lt,
    )

    # Build substitute universe.
    # If etf_holdings provided (legacy), use those tickers.
    # Otherwise auto-build from screener (all NASDAQ/NYSE stocks, ordered by market cap).
    if etf_holdings:
        universe: Optional[List[str]] = [h['asset'].upper() for h in etf_holdings if h.get('asset')]
    else:
        universe = None  # find_best_correlated_substitute will build it per-symbol

    warnings = []
    opportunities = []
    repurchase_date = wash_sale_safe_after(date.today())

    # Track symbols already assigned as substitutes in this plan.
    # A stock being bought as a substitute cannot simultaneously be harvested (sold) —
    # that would create a wash sale on the newly purchased substitute lot.
    # e.g. AMZN loss → buy MSFT; then harvesting MSFT loss → sell MSFT immediately after
    # buying it → the MSFT loss is disallowed (purchased within 30 days of the loss sale).
    assigned_as_substitute: set = set()

    # Also track symbols already scheduled to be sold, so we don't assign them as substitutes.
    scheduled_to_sell: set = set()

    for cand in candidates:
        symbol = cand['symbol']

        # Skip if this symbol was already assigned as a substitute for an earlier harvest.
        # We can't sell it (harvest it) while we're supposed to be holding it as a substitute.
        if symbol in assigned_as_substitute:
            warnings.append(
                f'{symbol}: skipped — already assigned as substitute for another position. '
                f'Cannot harvest and use as substitute simultaneously.'
            )
            continue

        # Build candidate universe excluding:
        # - Stocks we're already selling (buying them back = wash sale on the sold lot)
        # - Stocks already being used as substitutes (can't buy more of what we're holding short-term)
        blocked = scheduled_to_sell | assigned_as_substitute
        candidate_universe = (
            [s for s in universe if s.upper() not in blocked] if universe is not None else None
        )

        # Get top-N substitute candidates — LLM picks the best one
        substitute_candidates, sold_returns = find_substitute_candidates(
            symbol, candidate_universe, wash_sale_log,
            min_correlation=min_correlation, top_n=5,
        )

        if not substitute_candidates:
            warnings.append(f'{symbol}: no substitute found — no price data or all candidates in wash sale window')
            continue

        # Use top candidate for scoring (LLM may override this choice)
        top_sub = substitute_candidates[0]

        if top_sub.get('below_threshold'):
            warnings.append(
                f'{symbol}: best substitute {top_sub["symbol"]} has R={top_sub["correlation"]:.3f} '
                f'(below {min_correlation} threshold) — LLM should review candidates'
            )

        # Register top candidate to block wash-sale conflicts for subsequent positions.
        # LLM may pick a different candidate — if so, those cross-position conflicts are rare
        # and the agent should note them when reviewing.
        assigned_as_substitute.add(top_sub['symbol'].upper())
        scheduled_to_sell.add(symbol.upper())

        # Score using top candidate correlation
        scoring = score_harvest_opportunity(
            dollar_loss=cand['dollar_loss'],
            tax_rate=cand['tax_rate'],
            substitute_correlation=top_sub.get('correlation'),
            position_value=cand.get('position_value'),
            tax_rate_st=tax_rate_st,
        )

        opportunity = {
            **cand,
            # Sold symbol's own returns — LLM uses these to check divergence vs candidates
            'sold_returns': sold_returns,
            # All candidates with price context — LLM picks the substitute
            'substitute_candidates': substitute_candidates,
            'sell_date': date.today().isoformat(),
            'safe_repurchase_date': repurchase_date.isoformat(),
            'hold_substitute_days': 31,
            'scoring': scoring,
            'recommendation': scoring['recommendation'],
        }
        opportunities.append(opportunity)

    # Sort by net expected value descending (best risk-adjusted opportunities first)
    opportunities.sort(key=lambda o: -o['scoring']['net_expected_value'])

    # Separate by recommendation tier
    harvest_now = [o for o in opportunities if o['recommendation'] == 'HARVEST']
    borderline = [o for o in opportunities if o['recommendation'] == 'BORDERLINE']
    skip = [o for o in opportunities if o['recommendation'] == 'SKIP']

    total_losses = sum(o['dollar_loss'] for o in harvest_now + borderline)
    total_savings = sum(o['estimated_tax_savings'] for o in harvest_now + borderline)
    net_ev_total = sum(o['scoring']['net_expected_value'] for o in harvest_now + borderline)

    # Build summary
    st_count = sum(1 for o in harvest_now if o['is_short_term'])
    lt_count = sum(1 for o in harvest_now if not o['is_short_term'])
    total_sub_stgain_tax = sum(o['scoring'].get('substitute_st_gain_tax', 0) for o in harvest_now + borderline)
    wait_for_lt = [o for o in harvest_now + borderline if o.get('consider_waiting_for_lt')]

    summary = (
        f"Found {len(harvest_now)} HARVEST + {len(borderline)} BORDERLINE + {len(skip)} SKIP opportunities. "
        f"Recommended harvest: {st_count} short-term, {lt_count} long-term. "
        f"Total losses to harvest: ${total_losses:,.0f}. "
        f"Gross tax savings: ${total_savings:,.0f} "
        f"(ST @ {tax_rate_st*100:.1f}%, LT @ {tax_rate_lt*100:.1f}%). "
        f"Expected substitute ST gain tax: ${total_sub_stgain_tax:,.0f} "
        f"(substitute positions held <31 days = short-term; taxed at ST rate if they appreciate). "
        f"Net expected value: ${net_ev_total:,.0f}. "
        f"Safe repurchase date: {repurchase_date.isoformat()}."
    )
    if wait_for_lt:
        syms = ', '.join(o['symbol'] for o in wait_for_lt)
        days = min(o['days_until_long_term'] for o in wait_for_lt)
        summary += (
            f" NOTE: {len(wait_for_lt)} position(s) ({syms}) become long-term within 45 days "
            f"(soonest: {days} days). Consider waiting to harvest at the lower LT rate."
        )

    if warnings:
        summary += f" {len(warnings)} position(s) skipped — no safe substitute found."

    return {
        'harvest_opportunities': opportunities,    # all, sorted by net EV
        'harvest_now': harvest_now,                # clear wins
        'borderline': borderline,                  # judgment calls
        'skip': skip,                              # tracking error > tax savings
        'total_losses_to_harvest': round(total_losses, 2),
        'total_estimated_tax_savings': round(total_savings, 2),
        'total_net_expected_value': round(net_ev_total, 2),
        'safe_repurchase_date': repurchase_date.isoformat(),
        'parameters_used': {
            'threshold_loss_pct': threshold_loss_pct,
            'min_dollar_loss': min_dollar_loss,
            'tax_rate_st': tax_rate_st,
            'tax_rate_lt': tax_rate_lt,
            'min_correlation': min_correlation,
        },
        'summary': summary,
        'warnings': warnings,
    }


# ---------------------------------------------------------------------------
# Break-even & Expected Value Scoring (what platforms don't show you)
# ---------------------------------------------------------------------------

def score_harvest_opportunity(
    dollar_loss: float,
    tax_rate: float,
    substitute_correlation: Optional[float],
    position_value: Optional[float] = None,
    tax_rate_st: Optional[float] = None,
    annualized_volatility: float = 0.25,
    hold_days: int = 31,
    annual_return_assumption: float = 0.10,
    discount_rate: float = 0.07,
    years_until_liquidation: float = 10.0,
) -> Dict[str, Any]:
    """
    Score a TLH opportunity: tax savings minus ALL costs.

    Three costs:

    1. Tracking error cost — substitute diverges from original during hold.
       This is symmetric: substitute might outperform OR underperform.

    2. Substitute short-term gain tax — the substitute is held for 31 days,
       which is always short-term. If the substitute appreciates, you owe ST
       tax on that gain when you sell it on day 31 to repurchase the original.
       This is the most commonly ignored cost and can significantly erode
       (or eliminate) the harvest benefit in a rising market.

       Cost = position_value × (annual_return × hold_days/252) × tax_rate_st

    3. Basis step-up cost (informational) — after repurchasing the original
       on day 31, your new cost basis is the repurchase price. If the stock
       recovered during the hold, your basis is now higher than when you sold.
       Future gains will be smaller (or future losses larger). This is NOT
       an additional cost — it's the mechanism by which the tax is deferred
       rather than eliminated.

    Args:
        dollar_loss:              Absolute dollar loss being harvested
        tax_rate:                 Harvest rate: ST rate if short-term lot, LT if long-term
        substitute_correlation:   R between sold security and substitute (None → assume 0.82)
        position_value:           Market value of position (shares × current_price).
                                  If None, estimated from dollar_loss and volatility.
        tax_rate_st:              Short-term cap gains rate — used for substitute ST gain
                                  calculation. Defaults to tax_rate if not provided.
        annualized_volatility:    Expected annual vol of sold security (default 25%)
        hold_days:                Days holding substitute before repurchase (default 31)
        annual_return_assumption: Expected annual portfolio return (default 10%)
        discount_rate:            Discount rate for NPV (default 7%)
        years_until_liquidation:  Years until final portfolio liquidation (for deferral NPV)

    Returns:
        {
            tax_savings, tracking_error_cost, substitute_st_gain_tax,
            total_cost, net_expected_value, deferral_benefit_10yr,
            break_even_hold_days, substitute_correlation_used,
            recommendation, explanation
        }
    """
    import math

    tax_savings = dollar_loss * tax_rate
    st_rate = tax_rate_st if tax_rate_st is not None else tax_rate

    if substitute_correlation is None:
        rho = 0.82
    else:
        rho = max(-1.0, min(1.0, substitute_correlation))

    # Position value — use provided if available, otherwise estimate from loss and vol.
    # The estimate assumes the position dropped ~vol/2 to generate this loss, which is rough.
    pv = position_value if position_value is not None else dollar_loss / max(annualized_volatility * 0.5, 0.01)

    # --- Cost 1: Tracking error ---
    # How much might the substitute diverge from the original during the hold?
    sigma_tracking_annual = annualized_volatility * math.sqrt(max(0, 2 * (1 - rho)))
    sigma_tracking_period = sigma_tracking_annual * math.sqrt(hold_days / 252)
    expected_divergence_pct = sigma_tracking_period * math.sqrt(2 / math.pi)
    tracking_error_cost = pv * expected_divergence_pct

    # --- Cost 2: Substitute short-term gain tax ---
    # The substitute is always held for ≤ hold_days (short-term).
    # If the market rises, we owe ST tax on the substitute's gain when we sell on day 31.
    # This is a real, often-forgotten cost that can significantly erode harvest savings.
    expected_sub_gain_pct = annual_return_assumption * (hold_days / 252)
    expected_sub_gain = pv * expected_sub_gain_pct
    substitute_st_gain_tax = expected_sub_gain * st_rate

    total_cost = tracking_error_cost + substitute_st_gain_tax
    net_ev = tax_savings - total_cost

    # Deferral benefit: reinvest the deferred tax savings
    future_value_of_savings = tax_savings * (1 + annual_return_assumption) ** years_until_liquidation
    deferral_benefit = future_value_of_savings - tax_savings

    # Break-even days (tracking error only — substitute gain is time-invariant)
    sigma_corr = annualized_volatility * math.sqrt(max(0, 2 * (1 - rho))) * math.sqrt(2 / math.pi)
    if sigma_corr > 0 and pv > 0:
        break_even_days = int(252 * (tax_savings / (pv * sigma_corr)) ** 2)
    else:
        break_even_days = 0

    # Recommendation — account for BOTH costs
    if net_ev >= tax_savings * 0.5:
        recommendation = 'HARVEST'
        explanation = (
            f"Strong opportunity. Tax savings ${tax_savings:,.0f} vs total cost "
            f"${total_cost:,.0f} (tracking error ${tracking_error_cost:,.0f} + "
            f"substitute ST gain tax ${substitute_st_gain_tax:,.0f} at {st_rate*100:.1f}%). "
            f"Net EV: ${net_ev:,.0f}."
        )
    elif net_ev > 0:
        recommendation = 'HARVEST'
        explanation = (
            f"Positive EV, but thin margin. Tax savings ${tax_savings:,.0f} vs costs "
            f"${total_cost:,.0f} (incl. ${substitute_st_gain_tax:,.0f} ST gain tax on substitute). "
            f"In a strongly rising market the substitute gain tax could erode this further."
        )
    elif net_ev > -tax_savings * 0.2:
        recommendation = 'BORDERLINE'
        st_gain_pct = (substitute_st_gain_tax / tax_savings * 100) if tax_savings else 0
        explanation = (
            f"Borderline after accounting for substitute ST gain tax. "
            f"The substitute gain tax alone ({st_gain_pct:.0f}% of harvest savings) "
            f"reduces benefit substantially. Only proceed if you expect flat/down market "
            f"during the {hold_days}-day hold, or if you can hold the substitute >1 year "
            f"to convert its gain to long-term."
        )
    else:
        recommendation = 'SKIP'
        explanation = (
            f"Total costs ${total_cost:,.0f} (tracking error ${tracking_error_cost:,.0f} + "
            f"substitute ST gain tax ${substitute_st_gain_tax:,.0f}) exceed tax savings "
            f"${tax_savings:,.0f}. In a rising market this harvest likely costs more than it saves."
        )

    return {
        'tax_savings': round(tax_savings, 2),
        'tracking_error_cost': round(tracking_error_cost, 2),
        'substitute_st_gain_tax': round(substitute_st_gain_tax, 2),
        'total_cost': round(total_cost, 2),
        'net_expected_value': round(net_ev, 2),
        'deferral_benefit_10yr': round(deferral_benefit, 2),
        'break_even_hold_days': break_even_days,
        'substitute_correlation_used': round(rho, 4),
        'recommendation': recommendation,
        'explanation': explanation,
    }


# ---------------------------------------------------------------------------
# Helper: build TaxLot list from raw broker positions
# ---------------------------------------------------------------------------

def lots_from_positions(
    positions: List[Dict[str, Any]],
) -> List[TaxLot]:
    """
    Convert raw broker position dicts into TaxLot objects.

    Input format (per position):
        symbol:               str
        shares:               float
        cost_basis_per_share: float
        current_price:        float
        purchase_date:        str YYYY-MM-DD  (or 'open_date', 'acquired_date')

    If the position has multiple lots, pass each lot as a separate dict.
    If only aggregate position data is available (no per-lot dates), use today - 365
    as a conservative long-term placeholder.
    """
    lots = []
    today = date.today()
    for p in positions:
        symbol = p.get('symbol', '').upper()
        shares = float(p.get('shares', p.get('qty', 0)))
        cost = float(p.get('cost_basis_per_share', p.get('avg_entry_price', 0)))
        price = float(p.get('current_price', 0))

        date_str = p.get('purchase_date') or p.get('open_date') or p.get('acquired_date')
        if date_str:
            try:
                purchase_date = date.fromisoformat(date_str[:10])
            except (ValueError, TypeError):
                purchase_date = today - timedelta(days=400)  # assume long-term
        else:
            purchase_date = today - timedelta(days=400)  # conservative: treat as long-term

        if shares > 0 and cost > 0 and price > 0:
            lots.append(TaxLot(symbol, shares, cost, purchase_date, price))

    return lots


# ===========================================================================
# INSTITUTIONAL-GRADE ADDITIONS
# The functions below are standalone, callable by the agent with specific params.
# They encode IRS §1091 rules, practitioner consensus, and academic research
# (Chaudhuri/Burnham/Lo 2020, Israelov/Lu 2022, Wealthfront/Betterment whitepapers).
# ===========================================================================


# ---------------------------------------------------------------------------
# Tax Profile — user tax situation bundled for clean function signatures
# ---------------------------------------------------------------------------

class TaxProfile:
    """
    User tax situation bundled for clean function signatures.

    Rates are COMBINED (federal + state + NIIT where applicable).
    Always ask the user their state — it changes the analysis significantly.

    Quick construction:
        profile = TaxProfile.for_state('california')
        profile = TaxProfile.for_state('new_york_city', current_year_st_gains=12000)
        profile = TaxProfile(rate_st=0.37, rate_lt=0.238)  # custom rates
    """
    def __init__(
        self,
        rate_st: float = 0.37,
        rate_lt: float = 0.238,
        rate_ordinary: float = 0.37,
        state: str = 'federal_only',
        current_year_st_gains: float = 0.0,
        current_year_lt_gains: float = 0.0,
        loss_carryforward_st: float = 0.0,
        loss_carryforward_lt: float = 0.0,
    ):
        self.rate_st = rate_st
        self.rate_lt = rate_lt
        self.rate_ordinary = rate_ordinary
        self.state = state
        self.current_year_st_gains = current_year_st_gains
        self.current_year_lt_gains = current_year_lt_gains
        self.loss_carryforward_st = loss_carryforward_st
        self.loss_carryforward_lt = loss_carryforward_lt

    @classmethod
    def for_state(cls, state: str, **kwargs) -> 'TaxProfile':
        """Construct with pre-set combined (federal + state) rates."""
        rates = _TAX_RATES_BY_STATE.get(state.lower(), _TAX_RATES_BY_STATE['federal_only'])
        return cls(
            rate_st=rates['st'],
            rate_lt=rates['lt'],
            rate_ordinary=rates['ordinary'],
            state=state,
            **kwargs,
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            'state': self.state,
            'rate_st': self.rate_st,
            'rate_lt': self.rate_lt,
            'rate_ordinary': self.rate_ordinary,
            'current_year_st_gains': self.current_year_st_gains,
            'current_year_lt_gains': self.current_year_lt_gains,
        }


# 2025 combined federal + state capital gains rates
# Federal ST max: 37% + 3.8% NIIT = 40.8%; LT max: 20% + 3.8% NIIT = 23.8%
# We use 37% ST (not 40.8%) as the baseline since NIIT phase-in varies.
_TAX_RATES_BY_STATE: Dict[str, Dict[str, float]] = {
    'federal_only':  {'st': 0.370, 'lt': 0.238, 'ordinary': 0.370},
    'california':    {'st': 0.503, 'lt': 0.371, 'ordinary': 0.503},  # +13.3% state
    'new_york':      {'st': 0.468, 'lt': 0.337, 'ordinary': 0.468},  # +10.9% state
    'new_york_city': {'st': 0.479, 'lt': 0.347, 'ordinary': 0.479},  # +10.9% + 3.88% NYC
    'texas':         {'st': 0.370, 'lt': 0.238, 'ordinary': 0.370},
    'florida':       {'st': 0.370, 'lt': 0.238, 'ordinary': 0.370},
    'illinois':      {'st': 0.419, 'lt': 0.287, 'ordinary': 0.419},  # +4.95% flat
    'massachusetts': {'st': 0.449, 'lt': 0.287, 'ordinary': 0.449},  # +8.97% (inc. surtax)
    'oregon':        {'st': 0.459, 'lt': 0.327, 'ordinary': 0.459},  # +9.9%
    'minnesota':     {'st': 0.443, 'lt': 0.311, 'ordinary': 0.443},  # +9.85%
    'washington':    {'st': 0.370, 'lt': 0.238, 'ordinary': 0.370},  # no income tax
    'colorado':      {'st': 0.414, 'lt': 0.282, 'ordinary': 0.414},  # +4.4% flat
    'georgia':       {'st': 0.419, 'lt': 0.287, 'ordinary': 0.419},  # +5.49%
    'north_carolina':{'st': 0.415, 'lt': 0.283, 'ordinary': 0.415},  # +4.5%
    'virginia':      {'st': 0.422, 'lt': 0.290, 'ordinary': 0.422},  # +5.75%
    'maryland':      {'st': 0.433, 'lt': 0.301, 'ordinary': 0.433},  # +6.25%
}


# ---------------------------------------------------------------------------
# Known substitution pairs — substantially-identical risk ratings
# ---------------------------------------------------------------------------
# IRS §1091 has not explicitly ruled on ETFs, but practitioner consensus:
#   SAME_INDEX:    same underlying index, different issuer → high wash sale risk, AVOID
#   SIMILAR_INDEX: different but related index (e.g. S&P 500 → Total Market) → SAFE
#   SAME_COMPANY:  different share classes of the same corporation → always disallowed
#
# Sources: Wealthfront/Betterment whitepapers, Morningstar, White Coat Investor.

_PAIR_RISK: Dict[frozenset, Dict[str, str]] = {
    # SAME_INDEX — high wash sale risk
    frozenset({'VOO', 'IVV'}):    {'risk': 'SAME_INDEX',    'reason': 'Both track S&P 500, different issuers'},
    frozenset({'VOO', 'SPY'}):    {'risk': 'SAME_INDEX',    'reason': 'Both track S&P 500'},
    frozenset({'IVV', 'SPY'}):    {'risk': 'SAME_INDEX',    'reason': 'Both track S&P 500'},
    frozenset({'VTI', 'ITOT'}):   {'risk': 'SAME_INDEX',    'reason': 'Both track CRSP US Total Market'},
    frozenset({'QQQ', 'QQQM'}):   {'risk': 'SAME_INDEX',    'reason': 'Both track Nasdaq-100'},
    frozenset({'GLD', 'IAU'}):    {'risk': 'SAME_INDEX',    'reason': 'Both track gold spot price'},
    frozenset({'GLD', 'GLDM'}):   {'risk': 'SAME_INDEX',    'reason': 'Both track gold spot price'},
    frozenset({'VXUS', 'IXUS'}):  {'risk': 'SAME_INDEX',    'reason': 'Both track MSCI ACWI ex-US'},
    frozenset({'VEA', 'IEFA'}):   {'risk': 'SAME_INDEX',    'reason': 'Both track MSCI EAFE'},
    frozenset({'VWO', 'IEMG'}):   {'risk': 'SAME_INDEX',    'reason': 'Both track MSCI EM'},
    frozenset({'AGG', 'IUSB'}):   {'risk': 'SAME_INDEX',    'reason': 'Both track Bloomberg US Aggregate'},
    # SAME_COMPANY — always substantially identical
    frozenset({'GOOGL', 'GOOG'}): {'risk': 'SAME_COMPANY',  'reason': 'Class A and Class C shares of Alphabet'},
    frozenset({'BRK.A', 'BRK.B'}):{'risk': 'SAME_COMPANY',  'reason': 'Class A and Class B shares of Berkshire'},
    # SIMILAR_INDEX — safe swaps (different underlying index)
    frozenset({'VOO', 'VTI'}):    {'risk': 'SIMILAR_INDEX', 'reason': 'S&P 500 vs. Total Market — materially different index (adds ~3,000 small/mid-cap stocks)'},
    frozenset({'SPY', 'VTI'}):    {'risk': 'SIMILAR_INDEX', 'reason': 'S&P 500 vs. Total Market'},
    frozenset({'IVV', 'VTI'}):    {'risk': 'SIMILAR_INDEX', 'reason': 'S&P 500 vs. Total Market'},
    frozenset({'VOO', 'SCHB'}):   {'risk': 'SIMILAR_INDEX', 'reason': 'S&P 500 vs. Dow Jones US Broad Market'},
    frozenset({'QQQ', 'VGT'}):    {'risk': 'SIMILAR_INDEX', 'reason': 'Nasdaq-100 vs. Vanguard IT sector — different index'},
    frozenset({'QQQ', 'SCHG'}):   {'risk': 'SIMILAR_INDEX', 'reason': 'Nasdaq-100 vs. Schwab Large-Cap Growth (Dow Jones)'},
    frozenset({'QQQ', 'IWF'}):    {'risk': 'SIMILAR_INDEX', 'reason': 'Nasdaq-100 vs. Russell 1000 Growth'},
    frozenset({'VXUS', 'SCHF'}):  {'risk': 'SIMILAR_INDEX', 'reason': 'Total Intl vs. Schwab Developed Markets'},
    frozenset({'VEA', 'SCHF'}):   {'risk': 'SIMILAR_INDEX', 'reason': 'MSCI EAFE vs. Schwab Developed Markets (Dow Jones)'},
    frozenset({'VWO', 'SCHE'}):   {'risk': 'SIMILAR_INDEX', 'reason': 'MSCI EM vs. Schwab EM (Dow Jones EM) — different index'},
    frozenset({'VNQ', 'SCHH'}):   {'risk': 'SIMILAR_INDEX', 'reason': 'Different REIT indexes'},
    frozenset({'VNQ', 'USRT'}):   {'risk': 'SIMILAR_INDEX', 'reason': 'MSCI US REIT vs. FTSE NAREIT All Equity'},
    frozenset({'AGG', 'BND'}):    {'risk': 'SIMILAR_INDEX', 'reason': 'Bloomberg US Agg vs. Bloomberg US Float Adj — slightly different'},
    frozenset({'SCHP', 'TIP'}):   {'risk': 'SIMILAR_INDEX', 'reason': 'Both TIPS ETFs but different Bloomberg indexes'},
    frozenset({'IWM', 'VB'}):     {'risk': 'SIMILAR_INDEX', 'reason': 'Russell 2000 vs. CRSP US Small Cap — different index'},
    frozenset({'IWM', 'SCHA'}):   {'risk': 'SIMILAR_INDEX', 'reason': 'Russell 2000 vs. Dow Jones US Small-Cap'},
}

# Curated safe substitution recommendations per ticker.
# For individual stocks, use find_best_correlated_substitute() instead.
KNOWN_SUBSTITUTES: Dict[str, List[Dict[str, Any]]] = {
    'SPY':  [{'sub': 'VTI',  'risk': 'SIMILAR_INDEX', 'desc': 'Total US market (CRSP), adds ~3,000 small/mid-cap stocks', 'typical_corr': 0.99},
             {'sub': 'SCHB', 'risk': 'SIMILAR_INDEX', 'desc': 'Dow Jones US Broad Market Index', 'typical_corr': 0.99}],
    'VOO':  [{'sub': 'VTI',  'risk': 'SIMILAR_INDEX', 'desc': 'Total US market — different index, high correlation', 'typical_corr': 0.99},
             {'sub': 'SCHB', 'risk': 'SIMILAR_INDEX', 'desc': 'Schwab Broad Market', 'typical_corr': 0.99}],
    'IVV':  [{'sub': 'VTI',  'risk': 'SIMILAR_INDEX', 'desc': 'Total US market, different index entirely', 'typical_corr': 0.99},
             {'sub': 'SCHB', 'risk': 'SIMILAR_INDEX', 'desc': 'Schwab Broad Market', 'typical_corr': 0.99}],
    'QQQ':  [{'sub': 'SCHG', 'risk': 'SIMILAR_INDEX', 'desc': 'Schwab Large-Cap Growth (Dow Jones) — closest safe alternative', 'typical_corr': 0.97},
             {'sub': 'VGT',  'risk': 'SIMILAR_INDEX', 'desc': 'Vanguard IT sector ETF — high overlap but different index', 'typical_corr': 0.95},
             {'sub': 'IWF',  'risk': 'SIMILAR_INDEX', 'desc': 'iShares Russell 1000 Growth', 'typical_corr': 0.97}],
    'QQQM': [{'sub': 'SCHG', 'risk': 'SIMILAR_INDEX', 'desc': 'Schwab Large-Cap Growth', 'typical_corr': 0.97},
             {'sub': 'VGT',  'risk': 'SIMILAR_INDEX', 'desc': 'Vanguard IT sector', 'typical_corr': 0.95}],
    'VTI':  [{'sub': 'SCHB', 'risk': 'SIMILAR_INDEX', 'desc': 'Dow Jones US Broad Market — virtually identical exposure, different index', 'typical_corr': 0.999}],
    'ITOT': [{'sub': 'SCHB', 'risk': 'SIMILAR_INDEX', 'desc': 'Schwab Broad Market — different index provider', 'typical_corr': 0.999}],
    'VXUS': [{'sub': 'SCHF', 'risk': 'SIMILAR_INDEX', 'desc': 'Schwab Developed Markets, different index', 'typical_corr': 0.98}],
    'VEA':  [{'sub': 'SCHF', 'risk': 'SIMILAR_INDEX', 'desc': 'Schwab Developed Markets (Dow Jones Intl ex-US)', 'typical_corr': 0.99}],
    'EFA':  [{'sub': 'SCHF', 'risk': 'SIMILAR_INDEX', 'desc': 'Schwab Developed Markets', 'typical_corr': 0.99}],
    'VWO':  [{'sub': 'SCHE', 'risk': 'SIMILAR_INDEX', 'desc': 'Schwab EM (Dow Jones EM vs MSCI EM) — different index', 'typical_corr': 0.98}],
    'EEM':  [{'sub': 'SCHE', 'risk': 'SIMILAR_INDEX', 'desc': 'Schwab EM — different index provider', 'typical_corr': 0.97}],
    'IWM':  [{'sub': 'VB',   'risk': 'SIMILAR_INDEX', 'desc': 'Vanguard Small-Cap (CRSP US Small), Russell 2000 vs CRSP', 'typical_corr': 0.98},
             {'sub': 'SCHA', 'risk': 'SIMILAR_INDEX', 'desc': 'Schwab Small-Cap (Dow Jones US Small-Cap)', 'typical_corr': 0.98}],
    'VNQ':  [{'sub': 'SCHH', 'risk': 'SIMILAR_INDEX', 'desc': 'Dow Jones US Select REIT Index', 'typical_corr': 0.98},
             {'sub': 'USRT', 'risk': 'SIMILAR_INDEX', 'desc': 'FTSE NAREIT All Equity REITs', 'typical_corr': 0.98}],
    'GLD':  [{'sub': 'PHYS', 'risk': 'SIMILAR_INDEX', 'desc': 'Sprott Physical Gold Trust — different structure (trust vs ETF)', 'typical_corr': 0.98}],
    'AGG':  [{'sub': 'BND',  'risk': 'SIMILAR_INDEX', 'desc': 'Vanguard Total Bond Market (Bloomberg Float Adj)', 'typical_corr': 0.99},
             {'sub': 'SCHZ', 'risk': 'SIMILAR_INDEX', 'desc': 'Schwab US Aggregate Bond', 'typical_corr': 0.99}],
    'BND':  [{'sub': 'AGG',  'risk': 'SIMILAR_INDEX', 'desc': 'iShares Core US Aggregate Bond', 'typical_corr': 0.99},
             {'sub': 'SCHZ', 'risk': 'SIMILAR_INDEX', 'desc': 'Schwab US Aggregate Bond', 'typical_corr': 0.99}],
    'TIP':  [{'sub': 'SCHP', 'risk': 'SIMILAR_INDEX', 'desc': 'Schwab US TIPS ETF — different Bloomberg index', 'typical_corr': 0.99}],
    'SCHP': [{'sub': 'TIP',  'risk': 'SIMILAR_INDEX', 'desc': 'iShares TIPS Bond ETF — different Bloomberg index', 'typical_corr': 0.99}],
}


# ---------------------------------------------------------------------------
# Wash sale lookback check (pre-sale trap)
# ---------------------------------------------------------------------------

def check_wash_sale_lookback(
    symbol: str,
    purchase_history: List[Dict[str, Any]],
    proposed_sale_date: Optional[date] = None,
) -> Dict[str, Any]:
    """
    Check the wash sale LOOKBACK trap: did the user buy this symbol in the
    30 days BEFORE the proposed sale date?

    This is the commonly missed direction of the wash sale rule. If you:
      - Bought AAPL on Nov 1
      - Sell AAPL at a loss on Nov 20 (19 days later)
    The IRS looks back 30 days from the sale. The Nov 1 purchase falls within
    the lookback window → loss is DISALLOWED, even though you bought first.

    Most common cause: dollar-cost-averaging into a falling position.

    Args:
        symbol:             Ticker to check
        purchase_history:   [{symbol, purchase_date (YYYY-MM-DD), shares}]
                            Use broker transaction history
        proposed_sale_date: Date of proposed sale (defaults to today)

    Returns:
        {
            has_lookback_risk: bool,
            blocking_purchases: list — purchases within the 30-day lookback,
            earliest_safe_sale_date: ISO date string,
            explanation: str,
        }
    """
    if proposed_sale_date is None:
        proposed_sale_date = date.today()

    lookback_start = proposed_sale_date - timedelta(days=30)
    blocking = []

    for entry in purchase_history:
        if entry.get('symbol', '').upper() != symbol.upper():
            continue
        date_str = entry.get('purchase_date') or entry.get('date') or entry.get('acquired_date')
        if not date_str:
            continue
        try:
            pdate = date.fromisoformat(str(date_str)[:10])
        except (ValueError, TypeError):
            continue
        if lookback_start <= pdate <= proposed_sale_date:
            blocking.append({
                'purchase_date': pdate.isoformat(),
                'shares': entry.get('shares', entry.get('qty', '?')),
                'days_before_sale': (proposed_sale_date - pdate).days,
            })

    if not blocking:
        return {
            'has_lookback_risk': False,
            'blocking_purchases': [],
            'earliest_safe_sale_date': proposed_sale_date.isoformat(),
            'explanation': f'No purchases of {symbol} in the 30-day lookback window. Safe to harvest.',
        }

    latest = max(date.fromisoformat(b['purchase_date']) for b in blocking)
    earliest_safe = (latest + timedelta(days=31)).isoformat()
    return {
        'has_lookback_risk': True,
        'blocking_purchases': blocking,
        'earliest_safe_sale_date': earliest_safe,
        'explanation': (
            f'{symbol}: {len(blocking)} purchase(s) within the 30-day lookback window trigger a wash sale. '
            f'Most recent blocking purchase: {latest.isoformat()}. '
            f'Earliest safe sale date: {earliest_safe}. '
            f'Selling before then disallows the loss permanently — it cannot even be deferred.'
        ),
    }


# ---------------------------------------------------------------------------
# Substitute risk classification
# ---------------------------------------------------------------------------

def classify_substitute_risk(symbol_sold: str, symbol_bought: str) -> Dict[str, Any]:
    """
    Classify the wash sale risk of a proposed symbol_sold → symbol_bought swap.

    The IRS has not explicitly ruled on ETF-to-ETF substantially-identical
    determinations, but practitioner consensus (Wealthfront, Betterment,
    Morningstar) treats same-index/different-issuer ETFs as high risk.

    Args:
        symbol_sold:   Ticker being harvested
        symbol_bought: Proposed replacement ticker

    Returns:
        {
            risk_level: 'SAME_COMPANY' | 'SAME_INDEX' | 'SIMILAR_INDEX' | 'UNKNOWN',
            is_safe: bool,
            reason: str,
            recommendation: str,
        }
    """
    key = frozenset({symbol_sold.upper(), symbol_bought.upper()})

    if key in _PAIR_RISK:
        info = _PAIR_RISK[key]
        risk = info['risk']
        is_safe = risk == 'SIMILAR_INDEX'
        rec = (
            'AVOID — substantially identical risk. Use a SIMILAR_INDEX substitute instead.'
            if risk in ('SAME_INDEX', 'SAME_COMPANY')
            else 'SAFE — standard institutional TLH pair with different underlying index.'
        )
        return {'risk_level': risk, 'is_safe': is_safe, 'reason': info['reason'], 'recommendation': rec}

    return {
        'risk_level': 'UNKNOWN',
        'is_safe': True,
        'reason': 'Not in known-pairs database. Different corporations are not substantially identical per IRS regulations.',
        'recommendation': 'Likely safe. Verify if both are ETFs tracking highly similar indexes.',
    }


def get_known_substitutes(symbol: str, exclude_risky: bool = True) -> List[Dict[str, Any]]:
    """
    Return pre-vetted substitution options for a given ETF ticker.

    For individual stocks, this returns an empty list — use
    find_best_correlated_substitute() instead, which computes live correlations.

    Args:
        symbol:        ETF ticker to find substitutes for
        exclude_risky: If True (default), exclude SAME_INDEX pairs

    Returns:
        List of {sub, risk, desc, typical_corr}, best options first.
        Empty list if no pre-vetted substitutes exist for this ticker.

    Example:
        >>> get_known_substitutes('QQQ')
        [{'sub': 'SCHG', 'risk': 'SIMILAR_INDEX', 'desc': '...', 'typical_corr': 0.97}, ...]
    """
    subs = KNOWN_SUBSTITUTES.get(symbol.upper(), [])
    if exclude_risky:
        subs = [s for s in subs if s['risk'] != 'SAME_INDEX']
    return subs


# ---------------------------------------------------------------------------
# Netting order analysis — which losses are most valuable given current gains
# ---------------------------------------------------------------------------

def compute_netting_order(
    candidates: List[Dict[str, Any]],
    tax_profile: TaxProfile,
) -> List[Dict[str, Any]]:
    """
    Re-rank harvest candidates by actual after-tax value given the user's
    current-year realized gains mix.

    IRS netting rules (§1222):
    1. All ST gains/losses net against each other → net STCG or STCL
    2. All LT gains/losses net against each other → net LTCG or LTCL
    3. Net gain + net loss offset each other (with value destruction: a LT loss
       offsetting a ST gain saves only at the LT rate, not the ST rate)

    Bracket arbitrage (permanent wealth gain): harvesting a ST loss to offset
    a ST gain saves at the ST rate (up to 40.8%), while future recovery gains
    (after repurchasing) will be LT gains taxed at ~23.8%. The ~17-ppt
    differential is a permanent, not just deferred, tax saving.

    Args:
        candidates:   Output of find_harvest_candidates() — list of candidate dicts
        tax_profile:  User's TaxProfile with current_year_st_gains / lt_gains set

    Returns:
        Candidates with 'netting_context' field added, re-ranked by effective value.
    """
    remaining_st = tax_profile.current_year_st_gains
    remaining_lt = tax_profile.current_year_lt_gains
    ordinary_cap_remaining = max(0.0, 3000.0 - tax_profile.loss_carryforward_st - tax_profile.loss_carryforward_lt)

    enriched = []
    for cand in candidates:
        loss = cand['dollar_loss']
        is_st = cand['is_short_term']
        arbitrage = 0.0

        if is_st and remaining_st > 0:
            # Best case: ST loss × ST rate + bracket arbitrage
            offset = min(loss, remaining_st)
            effective_rate = tax_profile.rate_st
            arbitrage = offset * (tax_profile.rate_st - tax_profile.rate_lt)
            explanation = (
                f"ST loss offsets ${offset:,.0f} of ST gains at {tax_profile.rate_st*100:.1f}%. "
                f"Bracket arbitrage: ${arbitrage:,.0f} permanent (future recovery gains taxed at "
                f"{tax_profile.rate_lt*100:.1f}% LT rate)."
            )
            remaining_st -= offset

        elif is_st and remaining_lt > 0:
            # ST loss steps down to offset LT gain — loses rate differential
            effective_rate = tax_profile.rate_lt
            explanation = (
                f"No ST gains left — ST loss offsets LT gains at {tax_profile.rate_lt*100:.1f}% "
                f"(not {tax_profile.rate_st*100:.1f}%). No bracket arbitrage."
            )
            remaining_lt -= min(loss, remaining_lt)

        elif not is_st and remaining_lt > 0:
            effective_rate = tax_profile.rate_lt
            explanation = f"LT loss offsets LT gains at {tax_profile.rate_lt*100:.1f}%."
            remaining_lt -= min(loss, remaining_lt)

        elif not is_st and remaining_st > 0:
            # LT loss offsets ST gain — destroys rate value
            effective_rate = tax_profile.rate_lt
            arbitrage = -loss * (tax_profile.rate_st - tax_profile.rate_lt)  # negative
            explanation = (
                f"LT loss offsetting ST gains at {tax_profile.rate_lt*100:.1f}% — "
                f"destroys ${abs(arbitrage):,.0f} in rate value vs. a ST loss offsetting same gains. "
                f"Consider whether to harvest now or wait for position to become ST loss."
            )
            remaining_st -= min(loss, remaining_st)

        elif ordinary_cap_remaining > 0:
            # Offset ordinary income (up to $3,000/year)
            offset = min(loss, ordinary_cap_remaining)
            effective_rate = tax_profile.rate_ordinary
            explanation = (
                f"No capital gains to offset. First ${offset:,.0f} offsets ordinary income at "
                f"{tax_profile.rate_ordinary*100:.1f}% (§1211 $3K cap). Remainder carries forward."
            )
            ordinary_cap_remaining -= offset

        else:
            effective_rate = tax_profile.rate_lt  # best guess for future carryforward use
            explanation = (
                f"No gains or ordinary income available. Loss carries forward (§1212) — "
                f"will offset future gains. Still worth harvesting for the carryforward."
            )

        enriched.append({
            **cand,
            'netting_context': {
                'effective_rate': round(effective_rate, 4),
                'effective_tax_savings': round(loss * effective_rate, 2),
                'bracket_arbitrage': round(arbitrage, 2),
                'netting_explanation': explanation,
            },
        })

    enriched.sort(key=lambda c: -c['netting_context']['effective_tax_savings'])
    return enriched


# ---------------------------------------------------------------------------
# Full institutional tax alpha (immediate + deferral NPV + bracket arbitrage)
# ---------------------------------------------------------------------------

def compute_tax_alpha(
    dollar_loss: float,
    tax_profile: TaxProfile,
    is_short_term: bool = True,
    years_to_liquidation: float = 10.0,
    annual_return: float = 0.08,
) -> Dict[str, Any]:
    """
    Compute the full institutional tax alpha for a harvesting opportunity.

    Three components (Kitces / Wealthfront framework):

    1. Immediate benefit: dollar_loss × applicable rate. Tax not paid this year.

    2. Deferral NPV: the deferred tax compounds as reinvested capital. On final
       liquidation you pay tax again — but on a much larger base. Net gain =
       compounding of the deferred tax float over years_to_liquidation.

    3. Bracket arbitrage (ST losses only, when offsetting ST gains): permanent
       wealth gain from harvesting at the ST rate (up to 40.8%) while future
       repurchase gains will be LT (23.8%). The ~17-ppt differential is NOT
       recovered on liquidation — it's a permanent tax saving.

    This is why short-term losses are more valuable than long-term losses.

    Args:
        dollar_loss:          Absolute dollar loss to harvest
        tax_profile:          User's TaxProfile (state, current gains, rates)
        is_short_term:        Whether this lot is short-term (<1 year)
        years_to_liquidation: Expected years until final portfolio liquidation
        annual_return:        Expected portfolio return for NPV calculation

    Returns:
        {
            immediate_benefit, deferral_npv, bracket_arbitrage,
            total_alpha, alpha_pct_of_loss, niit_component, breakdown
        }
    """
    import math

    harvest_rate = tax_profile.rate_st if is_short_term else tax_profile.rate_lt
    immediate = dollar_loss * harvest_rate

    # Deferral NPV: reinvest the deferred tax at annual_return, pay LT tax on gains at liquidation
    future_value = immediate * (1 + annual_return) ** years_to_liquidation
    tax_on_future_gains = (future_value - immediate) * tax_profile.rate_lt
    deferral_npv = future_value - tax_on_future_gains - immediate

    # Bracket arbitrage: ST loss offsetting ST gain captures permanent rate differential
    bracket_arb = 0.0
    if is_short_term and tax_profile.current_year_st_gains > 0:
        eligible = min(dollar_loss, tax_profile.current_year_st_gains)
        bracket_arb = eligible * (tax_profile.rate_st - tax_profile.rate_lt)

    # NIIT breakout (3.8% is embedded in rate_lt = 0.238 for high earners)
    niit = dollar_loss * 0.038 if tax_profile.rate_lt >= 0.238 else 0.0

    total = immediate + deferral_npv + bracket_arb

    return {
        'immediate_benefit': round(immediate, 2),
        'deferral_npv': round(deferral_npv, 2),
        'bracket_arbitrage': round(bracket_arb, 2),
        'total_alpha': round(total, 2),
        'alpha_pct_of_loss': round(total / dollar_loss * 100, 2) if dollar_loss else 0,
        'niit_component': round(niit, 2),
        'harvest_rate_used': harvest_rate,
        'breakdown': {
            'dollar_loss': round(dollar_loss, 2),
            'term': 'short-term' if is_short_term else 'long-term',
            'harvest_rate': harvest_rate,
            'immediate': round(immediate, 2),
            'deferral_npv': round(deferral_npv, 2),
            'bracket_arb': round(bracket_arb, 2),
            'rate_diff_st_minus_lt': round((tax_profile.rate_st - tax_profile.rate_lt) * 100, 1),
            'reinvested_at': f'{annual_return*100:.0f}% for {years_to_liquidation:.0f}yr',
            'total': round(total, 2),
        },
    }
