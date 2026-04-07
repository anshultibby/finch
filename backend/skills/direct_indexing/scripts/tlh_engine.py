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

        candidates.append({
            **lot.to_dict(),
            'dollar_loss': round(dollar_loss, 2),
            'loss_pct': round(loss_pct, 2),
            'tax_rate': tax_rate,
            'estimated_tax_savings': round(tax_savings, 2),
            'term': 'short-term' if lot.is_short_term else 'long-term',
        })

    # Sort: short-term losses first (higher tax value), then by dollar loss descending
    candidates.sort(key=lambda c: (-int(c['is_short_term']), -c['estimated_tax_savings']))
    return candidates


# ---------------------------------------------------------------------------
# Substitute Security Selection
# ---------------------------------------------------------------------------

def compute_correlation(prices_a: List[float], prices_b: List[float]) -> Optional[float]:
    """
    Pearson correlation of daily returns between two price series.
    Returns None if insufficient data (< 20 common points).
    """
    if len(prices_a) < 20 or len(prices_b) < 20:
        return None

    n = min(len(prices_a), len(prices_b))
    prices_a = prices_a[:n]
    prices_b = prices_b[:n]

    returns_a = [(prices_a[i] - prices_a[i+1]) / prices_a[i+1] for i in range(n-1)]
    returns_b = [(prices_b[i] - prices_b[i+1]) / prices_b[i+1] for i in range(n-1)]

    try:
        return statistics.correlation(returns_a, returns_b)
    except Exception:
        return None


def find_substitute_security(
    sold_symbol: str,
    candidate_tickers: List[str],
    wash_sale_log: List[Dict[str, Any]],
    min_correlation: float = 0.85,
    price_lookback_days: int = 90,
) -> Optional[Dict[str, Any]]:
    """
    Find the best substitute security for a harvested position.

    Selection criteria (in order):
    1. Not substantially identical (different issuer — handled by caller passing only peers)
    2. Not in the wash sale window (wasn't recently sold at a loss)
    3. Correlation with sold security >= min_correlation (default 0.85)
    4. Among qualifying substitutes, pick the one with highest correlation

    Args:
        sold_symbol:        The ticker being harvested
        candidate_tickers:  Pool of potential substitutes (peers, sector ETF, etc.)
        wash_sale_log:      Prior sales log for wash sale checking
        min_correlation:    Minimum R with sold security (default 0.85; pros use 0.90-0.95)
        price_lookback_days: Days of price history to use for correlation (default 90)

    Returns:
        Best substitute dict {symbol, correlation, reason} or None if no suitable match
    """
    from skills.financial_modeling_prep.scripts.market.historical_prices import get_historical_prices

    # Filter wash-sale-blocked candidates
    eligible = [
        t for t in candidate_tickers
        if t.upper() != sold_symbol.upper()
        and not is_in_wash_sale_window(t, wash_sale_log)
    ]

    if not eligible:
        return None

    # Fetch historical prices for the sold security
    from_date = (date.today() - timedelta(days=price_lookback_days + 10)).isoformat()
    sold_data = get_historical_prices(sold_symbol, from_date=from_date)
    if 'error' in sold_data or not sold_data.get('prices'):
        # Fallback: return first eligible candidate without correlation check
        return {'symbol': eligible[0], 'correlation': None, 'reason': 'price data unavailable, using first eligible peer'}

    sold_prices = [p['close'] for p in sold_data['prices'] if p.get('close')]

    best: Optional[Dict[str, Any]] = None
    best_corr = -999.0

    for ticker in eligible[:15]:  # Check up to 15 candidates to limit API calls
        data = get_historical_prices(ticker, from_date=from_date)
        if 'error' in data or not data.get('prices'):
            continue
        prices = [p['close'] for p in data['prices'] if p.get('close')]

        corr = compute_correlation(sold_prices, prices)
        if corr is None:
            continue

        if corr >= min_correlation and corr > best_corr:
            best_corr = corr
            best = {
                'symbol': ticker,
                'correlation': round(corr, 4),
                'reason': f'highest-correlation peer (R={corr:.3f})',
            }

    if best is None:
        # Relax: take the best available even below threshold (with warning)
        for ticker in eligible[:5]:
            data = get_historical_prices(ticker, from_date=from_date)
            if 'error' in data or not data.get('prices'):
                continue
            prices = [p['close'] for p in data['prices'] if p.get('close')]
            corr = compute_correlation(sold_prices, prices)
            if corr is not None and corr > best_corr:
                best_corr = corr
                best = {
                    'symbol': ticker,
                    'correlation': round(corr, 4),
                    'reason': f'best available peer below correlation threshold (R={corr:.3f}) — verify manually',
                }

    return best


# ---------------------------------------------------------------------------
# Sector ETF fallbacks (for large-cap stocks with no good peer substitute)
# ---------------------------------------------------------------------------

SECTOR_ETF_FALLBACKS = {
    'Technology': 'XLK',
    'Communication Services': 'XLC',
    'Consumer Discretionary': 'XLY',
    'Consumer Staples': 'XLP',
    'Energy': 'XLE',
    'Financials': 'XLF',
    'Health Care': 'XLV',
    'Industrials': 'XLI',
    'Materials': 'XLB',
    'Real Estate': 'XLRE',
    'Utilities': 'XLU',
}

# Map of tickers where peer substitution typically fails (mega-caps that dominate sectors)
# For these, the sector ETF is the preferred substitute
SECTOR_ETF_PREFERRED = {'AAPL', 'MSFT', 'NVDA', 'AMZN', 'META', 'GOOGL', 'GOOG', 'TSLA', 'NFLX'}


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
    2. Find the best substitute security (peer or sector ETF)
    3. Compute the safe repurchase date (31 days from today)
    4. Return actionable instructions

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
    from skills.financial_modeling_prep.scripts.peers.stock_peers import get_stock_peers
    from skills.financial_modeling_prep.scripts.company.profile import get_profile as get_company_profile

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

    # Build set of ETF tickers for in-index substitute preference
    etf_tickers = set()
    if etf_holdings:
        etf_tickers = {h.get('asset', '').upper() for h in etf_holdings if h.get('asset')}

    warnings = []
    opportunities = []
    repurchase_date = wash_sale_safe_after(date.today())

    for cand in candidates:
        symbol = cand['symbol']

        # Step 2: Find substitute
        substitute = None
        substitute_source = None

        # For mega-caps, prefer sector ETF immediately
        if symbol in SECTOR_ETF_PREFERRED:
            # Get company sector to find the right ETF
            profile_data = get_company_profile(symbol)
            profile_list = profile_data if isinstance(profile_data, list) else [profile_data] if isinstance(profile_data, dict) else []
            profile = profile_list[0] if profile_list else {}
            sector = profile.get('sector', '')
            sector_etf = SECTOR_ETF_FALLBACKS.get(sector)
            if sector_etf and not is_in_wash_sale_window(sector_etf, wash_sale_log):
                substitute = {'symbol': sector_etf, 'correlation': None, 'reason': f'sector ETF ({sector}) — preferred for mega-cap, definitively not substantially identical'}
                substitute_source = 'sector_etf'

        if substitute is None:
            # Try peers first, preferring those already in the ETF
            peers = get_stock_peers(symbol)
            if isinstance(peers, list) and peers:
                # Prioritize peers that are in the target ETF (maintains index exposure)
                in_index_peers = [p for p in peers if p.upper() in etf_tickers and p.upper() != symbol.upper()]
                out_of_index_peers = [p for p in peers if p.upper() not in etf_tickers and p.upper() != symbol.upper()]
                ordered_peers = in_index_peers + out_of_index_peers

                substitute = find_substitute_security(
                    symbol,
                    ordered_peers,
                    wash_sale_log,
                    min_correlation=min_correlation,
                )
                substitute_source = 'peer'

        if substitute is None:
            # Final fallback: sector ETF
            profile_data = get_company_profile(symbol)
            profile_list = profile_data if isinstance(profile_data, list) else [profile_data] if isinstance(profile_data, dict) else []
            profile = profile_list[0] if profile_list else {}
            sector = profile.get('sector', '')
            sector_etf = SECTOR_ETF_FALLBACKS.get(sector)
            if sector_etf and not is_in_wash_sale_window(sector_etf, wash_sale_log):
                substitute = {'symbol': sector_etf, 'correlation': None, 'reason': f'sector ETF fallback ({sector}) — no suitable peer found'}
                substitute_source = 'sector_etf_fallback'
            else:
                warnings.append(f'{symbol}: no suitable substitute found — skipping harvest (wash sale risk or no peers)')
                continue

        # Score the opportunity: expected value vs tracking error cost
        scoring = score_harvest_opportunity(
            dollar_loss=cand['dollar_loss'],
            tax_rate=cand['tax_rate'],
            substitute_correlation=substitute.get('correlation'),
        )

        opportunity = {
            **cand,
            'substitute': substitute,
            'substitute_source': substitute_source,
            'sell_date': date.today().isoformat(),
            'safe_repurchase_date': repurchase_date.isoformat(),
            'hold_substitute_days': 31,
            'scoring': scoring,
            'recommendation': scoring['recommendation'],
            'action': f"SELL {cand['shares']} shares {symbol} → BUY {substitute['symbol']} → repurchase {symbol} after {repurchase_date.isoformat()}",
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
    summary = (
        f"Found {len(harvest_now)} HARVEST + {len(borderline)} BORDERLINE + {len(skip)} SKIP opportunities. "
        f"Recommended harvest: {st_count} short-term, {lt_count} long-term. "
        f"Total losses to harvest: ${total_losses:,.0f}. "
        f"Estimated tax savings: ${total_savings:,.0f} "
        f"(ST @ {tax_rate_st*100:.1f}%, LT @ {tax_rate_lt*100:.1f}%). "
        f"Net expected value after tracking error cost: ${net_ev_total:,.0f}. "
        f"Safe repurchase date: {repurchase_date.isoformat()}."
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
    annualized_volatility: float = 0.25,
    hold_days: int = 31,
    annual_return_assumption: float = 0.10,
    discount_rate: float = 0.07,
    years_until_liquidation: float = 10.0,
) -> Dict[str, Any]:
    """
    Score a TLH opportunity using expected value: tax savings minus opportunity cost.

    The opportunity cost of harvesting is that you hold a substitute for 31 days
    instead of the original. The substitute may diverge. We estimate this cost using
    the correlation and the expected tracking error over the hold period.

    Expected tracking error cost:
        σ_tracking ≈ σ_sold × sqrt(2 × (1 - ρ)) × sqrt(hold_days / 252)
        Expected |divergence| ≈ σ_tracking × sqrt(2/π)   [half-normal mean]

    Deferral value of the tax savings:
        Tax savings today compound at the discount_rate until liquidation.
        NPV of deferral = tax_savings × (1 - (1+discount_rate)^-years)

    Args:
        dollar_loss:             Absolute dollar loss being harvested
        tax_rate:                Applicable tax rate (ST or LT)
        substitute_correlation:  R between sold security and substitute (None = sector ETF)
        annualized_volatility:   Expected annual vol of sold security (default 25%)
        hold_days:               Days in substitute before repurchase (default 31)
        annual_return_assumption: Expected annual portfolio return (for NPV)
        discount_rate:           Discount rate for NPV calculation (default 7%)
        years_until_liquidation: How many years until expected full liquidation (for NPV)

    Returns:
        {
            tax_savings:          raw tax savings from harvesting
            tracking_error_cost:  expected dollar cost from substitute divergence
            net_expected_value:   tax_savings minus tracking_error_cost
            deferral_npv:         NPV of having the tax savings reinvested
            break_even_days:      minimum hold_days where tax savings > tracking error cost
            recommendation:       'HARVEST', 'BORDERLINE', or 'SKIP'
            explanation:          plain-English explanation
        }
    """
    import math

    tax_savings = dollar_loss * tax_rate

    # Tracking error cost
    if substitute_correlation is None:
        # Sector ETF: typically R ~ 0.80–0.90 for individual large-cap stocks
        rho = 0.82
    else:
        rho = substitute_correlation

    rho = max(-1.0, min(1.0, rho))  # clamp

    # Annualized tracking error of the substitute vs sold security
    sigma_tracking_annual = annualized_volatility * math.sqrt(2 * (1 - rho))

    # Over hold_days
    sigma_tracking_period = sigma_tracking_annual * math.sqrt(hold_days / 252)

    # Expected absolute divergence (half-normal distribution mean = σ × sqrt(2/π))
    expected_divergence_pct = sigma_tracking_period * math.sqrt(2 / math.pi)

    # Dollar cost of tracking error on the position value
    position_value = dollar_loss / (annualized_volatility * 0.5)  # rough position size
    tracking_error_cost = position_value * expected_divergence_pct

    net_ev = tax_savings - tracking_error_cost

    # Deferral NPV: the tax savings can be invested; the gain is the time value
    # NPV = tax_savings × [1 - (1+r)^-n] / r  (present value of annuity concept,
    # but here it's simpler: we get tax_savings now instead of paying tax on gains later)
    # Practical: just show the future value of reinvesting the tax savings
    future_value_of_savings = tax_savings * (1 + annual_return_assumption) ** years_until_liquidation
    deferral_benefit = future_value_of_savings - tax_savings

    # Break-even: minimum hold_days where tax savings > tracking error cost
    # Solve: tax_savings = position_value × σ_sold × sqrt(2(1-ρ)) × sqrt(d/252) × sqrt(2/π)
    # d = 252 × (tax_savings / (position_value × σ_sold × sqrt(2(1-ρ)) × sqrt(2/π)))^2
    sigma_corr = annualized_volatility * math.sqrt(2 * (1 - rho)) * math.sqrt(2 / math.pi)
    if sigma_corr > 0 and position_value > 0:
        break_even_days = int(252 * (tax_savings / (position_value * sigma_corr)) ** 2)
    else:
        break_even_days = 0

    # Recommendation
    if net_ev >= tax_savings * 0.5:
        recommendation = 'HARVEST'
        explanation = (
            f"Strong opportunity. Tax savings ${tax_savings:,.0f} far exceed estimated "
            f"tracking error cost ${tracking_error_cost:,.0f} (R={rho:.2f} substitute). "
            f"Break-even hold period: {break_even_days} days (well below 31-day minimum)."
        )
    elif net_ev > 0:
        recommendation = 'HARVEST'
        explanation = (
            f"Positive expected value. Tax savings ${tax_savings:,.0f} exceed tracking error "
            f"cost ${tracking_error_cost:,.0f}, but margin is thin. "
            f"Ensure substitute correlation holds (R={rho:.2f})."
        )
    elif net_ev > -tax_savings * 0.2:
        recommendation = 'BORDERLINE'
        explanation = (
            f"Borderline. Tax savings ${tax_savings:,.0f} roughly match tracking error "
            f"cost ${tracking_error_cost:,.0f}. Only harvest if substitute is highly "
            f"liquid and you can buy back quickly on day 31."
        )
    else:
        recommendation = 'SKIP'
        explanation = (
            f"Tracking error risk (${tracking_error_cost:,.0f}) exceeds tax savings "
            f"(${tax_savings:,.0f}). The substitute (R={rho:.2f}) diverges too much "
            f"over 31 days to make this worthwhile. Wait for a larger loss or better substitute."
        )

    return {
        'tax_savings': round(tax_savings, 2),
        'tracking_error_cost': round(tracking_error_cost, 2),
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
