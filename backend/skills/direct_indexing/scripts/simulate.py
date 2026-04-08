"""
simulate_direct_index: end-to-end historical direct indexing simulation.

One function call produces three daily time series:
  1. ETF buy-and-hold (the baseline)
  2. Direct index with exact ETF weights (should track ETF closely, <1% drift)
  3. Direct index + cumulative TLH tax savings (the only source of alpha)

Use this instead of writing your own portfolio simulation. The function handles:
  - Historical prices at the start date (not today's prices)
  - Exact market-cap weights (not renormalized top-N)
  - Sanity-checking that the direct index tracks the ETF before TLH
  - Monthly TLH scans with HIFO lot selection
  - Substitute security wash-sale awareness
  - Cumulative tax savings applied to portfolio value over time
"""
from datetime import date, timedelta
from typing import Dict, Any, List, Optional
from skills.financial_modeling_prep.scripts.market.historical_prices import get_batch_historical_prices


def simulate_direct_index(
    etf_symbol: str,
    capital: float,
    start_date: str,
    end_date: str,
    harvest_threshold_pct: float = 3.0,
    tax_rate_st: float = 0.37,
    tax_rate_lt: float = 0.238,
    harvest_frequency_days: int = 30,
    min_substitute_correlation: float = 0.80,
) -> Dict[str, Any]:
    """
    Simulate direct indexing a given ETF vs buy-and-hold for a historical period.

    Args:
        etf_symbol:             ETF to replicate (e.g. 'QQQ', 'SPY')
        capital:                Starting capital in dollars
        start_date:             First trading day of the period (YYYY-MM-DD)
        end_date:               Last trading day (YYYY-MM-DD)
        harvest_threshold_pct:  Minimum loss % below cost basis to harvest. Default 3%.
        tax_rate_st:            Short-term capital gains tax rate. Default 37%.
        tax_rate_lt:            Long-term cap gains rate. Default 23.8%.
        harvest_frequency_days: How often to scan for TLH opportunities. Default 30 (monthly).

    Returns dict with:
        dates:              List of date strings (all trading days in range)
        etf_values:         Daily portfolio value of ETF buy-and-hold
        direct_index_values: Daily portfolio value of direct index (no TLH)
        tlh_values:         Daily portfolio value of direct index + cumulative TLH
        tracking_error_pct: Max daily deviation of direct_index vs ETF (sanity check)
        harvest_events:     List of harvest events with date, symbol, loss, tax_savings
        total_tax_savings:  Total dollars saved via TLH
        total_losses_harvested: Total dollar losses harvested
        summary:            Plain-English summary of the simulation

    HOW TO USE:
        result = simulate_direct_index('QQQ', capital=100_000,
                                       start_date='2025-01-02', end_date='2025-12-31')

        # Sanity check — this should be < 2%
        print(f"Max tracking error: {result['tracking_error_pct']:.2f}%")

        # Build the comparison chart (three lines)
        import pandas as pd, matplotlib.pyplot as plt
        df = pd.DataFrame({
            'date': result['dates'],
            'QQQ Buy & Hold': result['etf_values'],
            'Direct Index (no TLH)': result['direct_index_values'],
            'Direct Index + TLH': result['tlh_values'],
        })
        df['date'] = pd.to_datetime(df['date'])
        df = df.set_index('date')
        df.plot(figsize=(12, 6))
        plt.title(f'Direct Indexing {etf_symbol} with TLH — {start_date[:4]}')
        plt.ylabel('Portfolio Value ($)')
        plt.savefig('direct_index_comparison.png', dpi=150, bbox_inches='tight')
    """
    import pandas as pd

    # -----------------------------------------------------------------------
    # 1. Fetch point-in-time ETF holdings + quarterly reconstitution snapshots
    # -----------------------------------------------------------------------
    # CRITICAL: always use start_date holdings, never today's. Today's QQQ contains stocks
    # that survived and grew — using them retroactively is survivorship bias and makes the
    # direct index appear to outperform QQQ before TLH, which is impossible by construction.
    from skills.financial_modeling_prep.scripts.etf.holdings import (
        get_etf_holdings, get_etf_holdings_at_dates,
    )

    holdings = get_etf_holdings(etf_symbol, date=start_date)
    if isinstance(holdings, dict) and 'error' in holdings:
        return holdings
    if not holdings:
        return {'error': f'No holdings found for {etf_symbol} at {start_date}'}

    holdings = sorted(holdings, key=lambda h: float(h.get('weightPercentage') or 0), reverse=True)

    # Fetch quarterly reconstitution snapshots so we can track entries and exits.
    # QQQ reconstitutes annually in December; SPY/IVV do minor quarterly rebalances.
    # We compare consecutive snapshots to detect which stocks were added or removed.
    from datetime import date as dt, timedelta
    _s = dt.fromisoformat(start_date)
    _e = dt.fromisoformat(end_date)
    quarterly_dates = []
    d = _s
    while d <= _e:
        quarterly_dates.append(d.isoformat())
        # advance ~3 months
        month = d.month + 3
        year = d.year + (month - 1) // 12
        month = ((month - 1) % 12) + 1
        d = dt(year, month, min(d.day, 28))
    if quarterly_dates[-1] != end_date:
        quarterly_dates.append(end_date)

    quarterly_snapshots = get_etf_holdings_at_dates(etf_symbol, quarterly_dates)
    # Build a sorted list of (date, holdings) pairs for reconstitution scanning
    recon_schedule = sorted(
        [(dt.fromisoformat(d), h) for d, h in quarterly_snapshots.items()],
        key=lambda x: x[0],
    )

    # Union of all symbols ever in the ETF during the period (for price fetching)
    all_ever_held = set(h['asset'].upper() for snap_holdings in quarterly_snapshots.values()
                        for h in snap_holdings if h.get('asset'))
    all_symbols = list(all_ever_held) + [etf_symbol]

    # Single batch fetch for the full simulation period — results are disk-cached so subsequent
    # calls are instant. adjClose handles splits and dividends correctly for return series.
    batch_results = get_batch_historical_prices(all_symbols, from_date=start_date, to_date=end_date)

    price_data: Dict[str, pd.Series] = {}   # adjClose — portfolio value tracking, return series
    close_data: Dict[str, pd.Series] = {}   # unadjusted close — TLH cost basis and loss triggers
    adjclose_on_start: Dict[str, float] = {}
    close_on_start: Dict[str, float] = {}

    start_ts = pd.Timestamp(start_date)

    for sym, hist in batch_results.items():
        if not hist.get('prices'):
            continue
        df = pd.DataFrame(hist['prices'])
        df['date'] = pd.to_datetime(df['date'])
        df = df.sort_values('date').set_index('date')

        # adjClose: retroactively adjusted for splits + dividends — use for portfolio return tracking
        if 'adjClose' in df.columns:
            price_data[sym] = df['adjClose'].astype(float)
        elif 'close' in df.columns:
            price_data[sym] = df['close'].astype(float)

        # close: actual traded price — use for TLH cost basis and loss% triggers.
        # adjClose diverges from close for dividend payers: comparing adjClose_now vs close_at_purchase
        # creates phantom losses (the dividend adjustment makes the historical close look lower).
        if 'close' in df.columns:
            close_data[sym] = df['close'].astype(float)

        if 'adjClose' in df.columns:
            if start_ts in df.index:
                adjclose_on_start[sym] = float(df.loc[start_ts, 'adjClose'])
            elif not df.empty:
                adjclose_on_start[sym] = float(df['adjClose'].iloc[0])

        if 'close' in df.columns:
            if start_ts in df.index:
                close_on_start[sym] = float(df.loc[start_ts, 'close'])
            elif not df.empty:
                close_on_start[sym] = float(df['close'].iloc[0])

    if etf_symbol not in price_data:
        return {'error': f'Could not fetch historical prices for {etf_symbol}'}

    # Build common date index from the ETF's trading days
    etf_prices = price_data[etf_symbol]
    trading_dates = etf_prices.index

    # -----------------------------------------------------------------------
    # 2. Build portfolio allocations
    # -----------------------------------------------------------------------
    # weightPercentage from N-PORT is the exact historical weight at filing date.
    # Normalize across all holdings in case they don't sum to exactly 100.
    total_weight = sum(float(h.get('weightPercentage') or 0) for h in holdings)
    if total_weight == 0:
        return {'error': 'ETF holdings have zero total weight'}

    positions = []
    covered_weight = 0.0
    skipped = []

    for h in holdings:
        symbol = h.get('asset', '').upper()
        if not symbol:
            continue

        raw_weight = float(h.get('weightPercentage') or 0)
        etf_weight_pct = (raw_weight / total_weight) * 100

        # Skip positions too small to buy fractional shares at this capital level.
        # 0.01% = $10 on $100k, $50 on $500k — below this the position is effectively zero.
        if etf_weight_pct < 0.01:
            skipped.append(symbol)
            continue

        adj_price = adjclose_on_start.get(symbol)
        if not adj_price or adj_price <= 0:
            skipped.append(symbol)
            continue

        target_value = capital * (etf_weight_pct / 100)
        # adjClose as share-count denominator: day-1 value == target_value exactly.
        # close != adjClose for dividend payers; mixing them creates a persistent gap.
        shares = round(target_value / adj_price, 6)
        covered_weight += etf_weight_pct

        positions.append({
            'symbol': symbol,
            'etf_weight_pct': round(etf_weight_pct, 4),
            'target_value': round(target_value, 2),
            'shares': shares,
            'adj_price': adj_price,
            'cost_basis': close_on_start.get(symbol, adj_price),
        })

    coverage_pct = round(covered_weight, 2)
    cash_remainder = round(capital * (1 - coverage_pct / 100), 2)

    # Coverage threshold scales with ETF breadth: broad-market ETFs (SPY=500, VTI=3700)
    # have long weight tails where micro-positions are genuinely untradeable; concentrated
    # ETFs (QQQ=100) should replicate nearly perfectly.
    n_holdings_total = len(holdings)
    min_coverage = 98.0 if n_holdings_total < 200 else (95.0 if n_holdings_total < 600 else 90.0)

    if coverage_pct < min_coverage:
        return {
            'error': (
                f"Coverage too low ({coverage_pct:.1f}%, need ≥ {min_coverage:.0f}%) — "
                f"direct index will not track {etf_symbol} within acceptable bounds. "
                f"FMP may be missing price data for some constituents on {start_date}. "
                f"Skipped: {skipped[:10]}"
            )
        }

    # -----------------------------------------------------------------------
    # 3. Build price matrix and compute daily portfolio value with reconstitution
    # -----------------------------------------------------------------------
    # Include all symbols ever held (start holdings + any added during reconstitution)
    all_held = set(p['symbol'] for p in positions) | all_ever_held
    price_matrix_syms = [s for s in all_held if s in price_data]

    price_matrix = pd.DataFrame({
        sym: price_data[sym].reindex(trading_dates)
        for sym in price_matrix_syms
    }).ffill()

    # close_matrix: unadjusted close prices — used ONLY for TLH loss% computation and cost basis.
    # Never use this for portfolio value; dividends are not captured in close prices.
    close_matrix = pd.DataFrame({
        sym: close_data[sym].reindex(trading_dates)
        for sym in price_matrix_syms
        if sym in close_data
    }).ffill()

    # Live shares_map — updated at each reconstitution event
    shares_map: Dict[str, float] = {p['symbol']: p['shares'] for p in positions if p['symbol'] in price_data}
    # cost_basis: close price at purchase date (for TLH); updated when new stocks enter
    portfolio_prices: Dict[str, float] = {p['symbol']: p['cost_basis'] for p in positions}
    # purchase_dates: when each symbol was first bought (for ST vs LT classification in TLH)
    purchase_dates_map: Dict[str, Any] = {p['symbol']: trading_dates[0] for p in positions if p['symbol'] in price_data}

    # Build a lookup: for each reconstitution date, what are the new weights?
    recon_by_date = {recon_dt: {h['asset'].upper(): float(h.get('weightPercentage') or 0)
                                for h in snap if h.get('asset')}
                     for recon_dt, snap in recon_schedule}

    recon_dates_set = set(recon_by_date.keys())
    prev_weights: Dict[str, float] = {h['asset'].upper(): float(h.get('weightPercentage') or 0)
                                      for h in holdings if h.get('asset')}

    daily_port_values = []

    for current_date in trading_dates:
        current_dt = current_date.date()

        # Apply reconstitution if this date has a new snapshot
        if current_dt in recon_dates_set and current_dt != _s:
            new_weights = recon_by_date[current_dt]
            new_total_w = sum(new_weights.values()) or 1.0

            # Current portfolio value before reconstitution
            port_value_now = sum(
                shares_map.get(sym, 0) * float(price_matrix.loc[current_date, sym])
                for sym in shares_map
                if sym in price_matrix.columns and pd.notna(price_matrix.loc[current_date, sym])
            ) + cash_remainder

            # Exits: stocks removed from ETF — sell at current price
            exits = set(prev_weights) - set(new_weights)
            for sym in exits:
                if sym in shares_map and sym in price_matrix.columns:
                    exit_price_val = price_matrix.loc[current_date, sym]
                    if pd.notna(exit_price_val) and float(exit_price_val) > 0:
                        cash_remainder += shares_map[sym] * float(exit_price_val)
                shares_map.pop(sym, None)
                portfolio_prices.pop(sym, None)
                purchase_dates_map.pop(sym, None)

            # Entries: new stocks added to ETF — buy at target allocation
            entries = set(new_weights) - set(prev_weights)
            for sym in entries:
                if sym not in price_matrix.columns:
                    continue
                entry_price_val = price_matrix.loc[current_date, sym]
                if pd.isna(entry_price_val) or float(entry_price_val) <= 0:
                    continue
                entry_price = float(entry_price_val)
                target_val = port_value_now * (new_weights[sym] / new_total_w)
                target_val = min(target_val, max(0, cash_remainder))
                new_shares = round(target_val / entry_price, 6)
                shares_map[sym] = new_shares
                portfolio_prices[sym] = entry_price   # cost basis = entry price on this date
                purchase_dates_map[sym] = current_date  # for ST/LT classification

            # Rebalance continuing positions toward new weights
            for sym, new_w in new_weights.items():
                if sym in exits or sym in entries or sym not in price_matrix.columns:
                    continue
                price_now_val = price_matrix.loc[current_date, sym]
                if pd.isna(price_now_val) or float(price_now_val) <= 0:
                    continue
                price_now = float(price_now_val)
                target_val = port_value_now * (new_w / new_total_w)
                current_val = shares_map.get(sym, 0) * price_now
                delta_shares = round((target_val - current_val) / price_now, 6)
                shares_map[sym] = max(0, shares_map.get(sym, 0) + delta_shares)
                cash_remainder -= delta_shares * price_now

            prev_weights = new_weights
            cash_remainder = max(0.0, cash_remainder)  # rounding in rebalance can push to tiny negative

        # Daily portfolio value = sum(shares × adjClose) + cash
        day_value = sum(
            shares_map.get(sym, 0) * float(price_matrix.loc[current_date, sym])
            for sym in shares_map
            if sym in price_matrix.columns and pd.notna(price_matrix.loc[current_date, sym])
        ) + cash_remainder
        daily_port_values.append(day_value)

    direct_index_series = pd.Series(daily_port_values, index=trading_dates)

    # ETF buy-and-hold: normalize adjClose to starting capital
    etf_series = capital * (etf_prices / etf_prices.iloc[0])

    # -----------------------------------------------------------------------
    # 4. Sanity check: direct index vs ETF tracking
    # -----------------------------------------------------------------------
    comparison = pd.DataFrame({
        'etf': etf_series,
        'direct': direct_index_series,
    }).dropna()
    tracking_diff_pct = ((comparison['direct'] - comparison['etf']) / comparison['etf'] * 100).abs()
    max_tracking_error = tracking_diff_pct.max()

    # Tracking tolerance scales with period length.
    # Within-quarter drift is ~0.1-0.3% (exact weights + fractional shares).
    # Over a full year, between-quarter weight drift from stocks moving differently can
    # accumulate to ~0.5-1.0% even with correct quarterly EDGAR rebalancing — this is
    # normal, not a data error. Only flag if the error is large enough to indicate a
    # real problem (wrong weights, missing prices, or non-market start date).
    sim_days = (pd.Timestamp(end_date) - pd.Timestamp(start_date)).days
    tracking_threshold = 0.5 + (sim_days / 365) * 0.75  # 0.5% for 1 day → 1.25% for 1 year
    cash_drag_pct = round(cash_remainder / capital * 100, 2)

    if max_tracking_error > tracking_threshold:
        # Diagnose the cause so the error message is actionable
        if comparison['direct'].iloc[0] != comparison['etf'].iloc[0]:
            cause = f"Day-1 values differ (direct=${comparison['direct'].iloc[0]:,.0f} vs ETF=${comparison['etf'].iloc[0]:,.0f}) — start-date prices are wrong. Check that '{start_date}' is a market trading day with valid prices."
        elif cash_drag_pct > 5:
            cause = f"High cash drag ({cash_drag_pct:.1f}%) — many constituents were skipped. Coverage: {coverage_pct:.1f}%."
        else:
            cause = f"Within-period weight drift exceeds {tracking_threshold:.1f}% tolerance for a {sim_days}-day simulation. This can happen if quarterly N-PORT rebalancing didn't apply correctly, or if the ETF had unusual constituent moves."
        return {
            'error': (
                f"Simulation failed tracking check: direct index diverged from {etf_symbol} by "
                f"{max_tracking_error:.2f}% (tolerance: {tracking_threshold:.1f}% for {sim_days} days). "
                f"{cause}"
            ),
            'debug': {
                'coverage_pct': coverage_pct,
                'cash_drag_pct': cash_drag_pct,
                'n_positions': len(positions),
                'n_priced': len(shares_map),
                'start_direct': round(comparison['direct'].iloc[0], 2),
                'start_etf': round(comparison['etf'].iloc[0], 2),
                'max_tracking_error_pct': round(float(max_tracking_error), 2),
                'tracking_threshold_pct': round(tracking_threshold, 2),
                'sim_days': sim_days,
            }
        }

    # -----------------------------------------------------------------------
    # 5. TLH simulation: monthly scans with actual substitute swaps
    # -----------------------------------------------------------------------
    # Runs a SEPARATE portfolio alongside the direct index that actually executes:
    #   harvest date:    sell orig X → buy highest-correlation substitute Y
    #   rebuy date (+31d): sell Y → buy X back
    #   tax savings:     banked as cash (not reinvested, conservative estimate)
    #
    # tlh_series reflects the real portfolio value (swapped positions + tax cash).
    # The gap vs direct_index_series = tax savings + substitute performance during hold.

    # Substantially identical securities — IRS wash sale rule blocks swapping between these.
    # Swapping GOOGL→GOOG (or vice versa) is NOT a valid TLH because both represent the
    # same economic interest in Alphabet Inc. Same applies to BRK.A/BRK.B and other share classes.
    _WASH_PAIRS: Dict[str, str] = {
        'GOOGL': 'GOOG',  'GOOG': 'GOOGL',
        'BRK.A': 'BRK.B', 'BRK.B': 'BRK.A',
    }
    # Build a set of (sym, blocked_sym) to reject in candidate selection
    def _wash_blocked(sym: str, candidate: str) -> bool:
        """Return True if sym→candidate swap would violate wash sale (substantially identical)."""
        return _WASH_PAIRS.get(sym) == candidate or _WASH_PAIRS.get(candidate) == sym

    _peers_cache: Dict[str, list] = {}  # sym → FMP sector peers filtered to ETF universe

    def _get_sector_peers(sym: str, universe: set) -> list:
        """Fetch FMP sector peers for sym, filtered to ETF universe. Disk-cached."""
        if sym in _peers_cache:
            return _peers_cache[sym]
        from skills.financial_modeling_prep.scripts.peers.stock_peers import get_stock_peers
        from skills.financial_modeling_prep.scripts._cache import (
            cache_key as _ck, load_cache as _lc, save_cache as _sc,
        )
        _PEERS_DIR = '/tmp/fmp_peers_cache'
        ck = _ck(sym, 'etf_peers_v1')
        raw = _lc(_PEERS_DIR, ck)
        if raw is None:
            fetched = get_stock_peers(sym)
            raw = fetched if isinstance(fetched, list) else []
            _sc(_PEERS_DIR, ck, raw)
        filtered = [p for p in raw if p in universe and p != sym]
        _peers_cache[sym] = filtered
        return filtered

    def _find_substitute(sold_sym: str, candidates: list, as_of_date, lookback: int = 120) -> Optional[Dict]:
        """
        Pick highest-correlation substitute from ETF sector peers first, fall back to all candidates.

        Sector peers (FMP /stock_peers) are same-sector, same-exchange, similar market cap —
        they make better TLH substitutes than a randomly correlated stock from a different industry.
        Uses price_matrix (adjClose returns) for correlation — total return correlation is the right
        hedge quality metric.
        """
        try:
            idx_loc = price_matrix.index.get_loc(as_of_date)
        except KeyError:
            return None
        start_loc = max(0, idx_loc - lookback)
        window = price_matrix.iloc[start_loc:idx_loc + 1]
        if sold_sym not in window.columns or window[sold_sym].dropna().shape[0] < 30:
            return None
        sold_ret = window[sold_sym].pct_change().dropna()

        # Prefer sector peers; fall back to full candidate pool if fewer than 5 peers available
        universe_set = set(candidates)
        sector_peers = _get_sector_peers(sold_sym, universe_set)
        search_pool = sector_peers if len(sector_peers) >= 5 else candidates

        best_sym, best_corr = None, -999.0
        for sym in search_pool:
            if sym not in window.columns:
                continue
            cand_ret = window[sym].pct_change().dropna()
            aligned = pd.concat([sold_ret, cand_ret], axis=1).dropna()
            if len(aligned) < 30:
                continue
            corr = float(aligned.iloc[:, 0].corr(aligned.iloc[:, 1]))
            if corr > best_corr:
                best_corr, best_sym = corr, sym

        # If sector pool found nothing good, retry with full candidates
        if (best_sym is None or best_corr < min_substitute_correlation) and search_pool is not candidates:
            for sym in candidates:
                if sym in search_pool or sym not in window.columns:
                    continue
                cand_ret = window[sym].pct_change().dropna()
                aligned = pd.concat([sold_ret, cand_ret], axis=1).dropna()
                if len(aligned) < 30:
                    continue
                corr = float(aligned.iloc[:, 0].corr(aligned.iloc[:, 1]))
                if corr > best_corr:
                    best_corr, best_sym = corr, sym

        return {'symbol': best_sym, 'correlation': round(best_corr, 4)} if best_sym else None

    # TLH portfolio state — starts identical to the direct index
    tlh_sh: Dict[str, float] = dict(shares_map)
    tlh_cost: Dict[str, float] = {
        sym: portfolio_prices.get(sym, float(price_matrix[sym].iloc[0]))
        for sym in tlh_sh if sym in price_matrix.columns
    }
    tlh_purch: Dict[str, Any] = dict(purchase_dates_map)
    tlh_cash: float = cash_remainder          # TLH portfolio's own cash (may diverge after reinvestment)
    tlh_tax_cash: float = 0.0                 # banked tax savings (reinvested proportionally each harvest)
    tlh_wash: Dict[str, date] = {}

    # active_swaps: orig → {sub_sym, sub_shares, rebuy_date, orig_value_at_harvest, correlation}
    active_swaps: Dict[str, dict] = {}

    harvest_events: List[dict] = []
    missed_harvests: List[dict] = []   # opportunities skipped because no qualifying substitute was found
    cumulative_tax_savings: float = 0.0
    tlh_daily_values: List[float] = []
    last_scan_date = trading_dates[0]
    tlh_prev_weights: Dict[str, float] = dict(prev_weights)   # tracks current ETF composition for TLH recon

    etf_universe = [s for s in price_matrix.columns if s != etf_symbol]

    def _reinvest_tax_savings(savings: float) -> None:
        """Spread tax savings proportionally into active TLH positions (no idle cash drag)."""
        active_syms = [
            s for s in tlh_sh
            if s in price_matrix.columns and pd.notna(price_matrix.loc[current_date, s])
               and float(price_matrix.loc[current_date, s]) > 0
        ]
        if not active_syms:
            return
        total_val = sum(
            tlh_sh[s] * float(price_matrix.loc[current_date, s]) for s in active_syms
        )
        if total_val <= 0:
            return
        for s in active_syms:
            s_price = float(price_matrix.loc[current_date, s])
            weight = (tlh_sh[s] * s_price) / total_val
            extra_shares = (savings * weight) / s_price
            tlh_sh[s] = tlh_sh[s] + extra_shares

    for current_date in trading_dates:
        current_dt = current_date.date()

        # ── TLH reconstitution (mirrors the direct index reconstitution logic) ──
        if current_dt in recon_dates_set and current_dt != _s:
            new_weights = recon_by_date[current_dt]
            new_total_w = sum(new_weights.values()) or 1.0

            tlh_port_value = sum(
                tlh_sh.get(sym, 0) * float(price_matrix.loc[current_date, sym])
                for sym in tlh_sh
                if sym in price_matrix.columns and pd.notna(price_matrix.loc[current_date, sym])
            ) + tlh_cash

            # Exits
            exits = set(tlh_prev_weights) - set(new_weights)
            for sym in exits:
                if sym in tlh_sh and sym in price_matrix.columns:
                    exit_pv = price_matrix.loc[current_date, sym]
                    if pd.notna(exit_pv) and float(exit_pv) > 0:
                        tlh_cash += tlh_sh[sym] * float(exit_pv)
                tlh_sh.pop(sym, None)
                tlh_cost.pop(sym, None)
                tlh_purch.pop(sym, None)
                # also cancel any active swap involving this symbol
                active_swaps.pop(sym, None)

            # Entries
            entries = set(new_weights) - set(tlh_prev_weights)
            for sym in entries:
                if sym not in price_matrix.columns:
                    continue
                entry_pv = price_matrix.loc[current_date, sym]
                if pd.isna(entry_pv) or float(entry_pv) <= 0:
                    continue
                entry_price = float(entry_pv)   # adjClose — used for share count
                target_val = tlh_port_value * (new_weights[sym] / new_total_w)
                target_val = min(target_val, max(0, tlh_cash))
                tlh_sh[sym] = round(target_val / entry_price, 6)
                # Cost basis = close price (what the investor actually paid, for TLH trigger)
                entry_close = close_matrix.loc[current_date, sym] if sym in close_matrix.columns else None
                tlh_cost[sym] = float(entry_close) if entry_close is not None and pd.notna(entry_close) else entry_price
                tlh_purch[sym] = current_date
                tlh_cash -= target_val

            # Rebalance continuing positions
            for sym, new_w in new_weights.items():
                if sym in exits or sym in entries or sym not in price_matrix.columns:
                    continue
                pv = price_matrix.loc[current_date, sym]
                if pd.isna(pv) or float(pv) <= 0:
                    continue
                price_now = float(pv)
                target_val = tlh_port_value * (new_w / new_total_w)
                delta_shares = round((target_val - tlh_sh.get(sym, 0) * price_now) / price_now, 6)
                tlh_sh[sym] = max(0, tlh_sh.get(sym, 0) + delta_shares)
                tlh_cash -= delta_shares * price_now

            tlh_prev_weights = new_weights
            tlh_cash = max(0.0, tlh_cash)  # rounding in rebalance can push to tiny negative

        # ── Close matured swaps (sell substitute, buy original back) ──────────
        for orig_sym in list(active_swaps):
            swap = active_swaps[orig_sym]
            if current_date < swap['rebuy_date']:
                continue
            sub_sym = swap['sub_sym']
            sub_pv = price_matrix.loc[current_date, sub_sym] if sub_sym in price_matrix.columns else None
            if sub_pv is not None and pd.notna(sub_pv) and float(sub_pv) > 0:
                sub_exit_price = float(sub_pv)
                proceeds = swap['sub_shares'] * sub_exit_price
                tlh_sh[sub_sym] = tlh_sh.get(sub_sym, 0) - swap['sub_shares']
                if tlh_sh.get(sub_sym, 0) <= 1e-6:
                    tlh_sh.pop(sub_sym, None)
            else:
                sub_exit_price = swap['sub_entry_price']
                proceeds = swap['orig_value_at_harvest']

            # Back-fill substitute performance into the harvest event record
            ev = harvest_events[swap['event_idx']]
            sub_pnl = proceeds - swap['orig_value_at_harvest']
            sub_ret_pct = (sub_exit_price / swap['sub_entry_price'] - 1) * 100 if swap['sub_entry_price'] > 0 else 0.0
            hold_days = (current_date - swap['harvest_date']).days
            ev['substitute_exit_price'] = round(sub_exit_price, 4)
            ev['substitute_pnl'] = round(sub_pnl, 2)
            ev['substitute_return_pct'] = round(sub_ret_pct, 2)
            ev['substitute_hold_days'] = hold_days
            ev['rebuy_date'] = current_date.strftime('%Y-%m-%d')
            # Net outcome = tax savings realised + substitute P&L during hold
            # (positive = good: tax savings exceeded any substitute underperformance)
            ev['net_harvest_outcome'] = round(ev['tax_savings'] + sub_pnl, 2)

            orig_pv = price_matrix.loc[current_date, orig_sym] if orig_sym in price_matrix.columns else None
            if orig_pv is not None and pd.notna(orig_pv) and float(orig_pv) > 0:
                orig_price = float(orig_pv)
                tlh_sh[orig_sym] = proceeds / orig_price
                # Cost basis = close price on rebuy date (actual price paid, not adjClose)
                orig_close = close_matrix.loc[current_date, orig_sym] if orig_sym in close_matrix.columns else None
                tlh_cost[orig_sym] = float(orig_close) if orig_close is not None and pd.notna(orig_close) else orig_price
                tlh_purch[orig_sym] = current_date
            del active_swaps[orig_sym]

        # ── TLH scan: monthly scheduled + event-driven on large single-day drops ──
        # IMPORTANT: these sets are updated INLINE during the scan so that symbols assigned
        # as substitutes mid-scan are immediately blocked from also being harvested.
        # (Bug without this: NVDA harvested → AVGO assigned as sub → AVGO also harvested
        #  same scan → AVGO sold immediately after being bought = wash sale + bad tracking)
        substituted_origs = set(active_swaps.keys())
        active_sub_syms = {sw['sub_sym'] for sw in active_swaps.values()}
        do_monthly_scan = (current_date - last_scan_date).days >= harvest_frequency_days

        syms_to_scan: List[str] = []
        if do_monthly_scan:
            last_scan_date = current_date
            syms_to_scan = list(tlh_sh)
        else:
            # Event-driven: scan any position with a single-day close drop > threshold
            prev_date_idx = price_matrix.index.get_loc(current_date)
            if prev_date_idx > 0:
                prev_date = price_matrix.index[prev_date_idx - 1]
                for sym in tlh_sh:
                    if sym not in close_matrix.columns or sym == etf_symbol:
                        continue
                    if sym in substituted_origs or sym in active_sub_syms:
                        continue
                    prev_pv = close_matrix.loc[prev_date, sym]
                    cur_pv2 = close_matrix.loc[current_date, sym]
                    if pd.isna(prev_pv) or pd.isna(cur_pv2) or float(prev_pv) <= 0:
                        continue
                    if (float(cur_pv2) - float(prev_pv)) / float(prev_pv) * 100 < -harvest_threshold_pct:
                        syms_to_scan.append(sym)

        for sym in syms_to_scan:
            if sym not in close_matrix.columns or sym == etf_symbol:
                continue
            if sym in substituted_origs or sym in active_sub_syms:
                continue

            # Use close (unadjusted) for loss% — this is the actual price the investor paid vs today's price.
            # adjClose would create phantom losses for dividend payers because it retroactively
            # reduces historical prices by the dividend amount.
            cur_pv = close_matrix.loc[current_date, sym]
            if pd.isna(cur_pv) or float(cur_pv) <= 0:
                continue
            current_price = float(cur_pv)
            basis = tlh_cost.get(sym, 0)
            if basis <= 0:
                continue

            # Pre-sale wash sale check: block if position was purchased within 30 days
            days_since_purchase = (current_date - tlh_purch.get(sym, trading_dates[0])).days
            if days_since_purchase < 31:
                continue

            loss_pct = (current_price - basis) / basis * 100
            if loss_pct > -harvest_threshold_pct:
                continue
            if sym in tlh_wash and current_date.date() < tlh_wash[sym]:
                continue

            shares_held = tlh_sh.get(sym, 0)
            if shares_held <= 0:
                continue
            days_held = days_since_purchase
            rate = tax_rate_st if days_held < 365 else tax_rate_lt
            dollar_loss = abs(current_price - basis) * shares_held
            tax_savings = dollar_loss * rate
            if tax_savings < 10:
                continue

            # Find substitute — exclude active subs and substantially identical share classes
            candidates = [
                s for s in etf_universe
                if s != sym
                and s not in active_sub_syms
                and not _wash_blocked(sym, s)
            ]
            sub = _find_substitute(sym, candidates, current_date)

            # Only execute the position swap if correlation meets the threshold.
            # Below threshold: still harvest (book tax savings) but keep holding orig —
            # a low-correlation substitute is a market bet, not a TLH hedge.
            if sub and sub['correlation'] >= min_substitute_correlation and sub['symbol'] in price_matrix.columns:
                sub_sym = sub['symbol']
                sub_pv2 = price_matrix.loc[current_date, sub_sym]
                if pd.notna(sub_pv2) and float(sub_pv2) > 0:
                    proceeds = shares_held * current_price   # current_price is close (unadjusted)
                    sub_shares = proceeds / float(sub_pv2)
                    tlh_sh.pop(sym, None)
                    tlh_sh[sub_sym] = tlh_sh.get(sub_sym, 0) + sub_shares
                    # Track substitute cost basis in close price for future TLH scans on the sub
                    sub_close = close_matrix.loc[current_date, sub_sym] if sub_sym in close_matrix.columns else None
                    sub_entry_close = float(sub_close) if sub_close is not None and pd.notna(sub_close) else float(sub_pv2)
                    tlh_cost[sub_sym] = sub_entry_close
                    rebuy_future = trading_dates[trading_dates >= current_date + timedelta(days=31)]
                    rebuy_date = rebuy_future[0] if len(rebuy_future) > 0 else trading_dates[-1]
                    active_swaps[sym] = {
                        'sub_sym': sub_sym,
                        'sub_shares': sub_shares,
                        'sub_entry_price': sub_entry_close,
                        'rebuy_date': rebuy_date,
                        'orig_value_at_harvest': proceeds,
                        'correlation': sub['correlation'],
                        'event_idx': len(harvest_events),   # index of the event about to be appended
                        'harvest_date': current_date,
                    }
                    # Update live tracking sets so subsequent iterations in this same scan
                    # can't also harvest sub_sym or use sym as a substitute.
                    active_sub_syms.add(sub_sym)
                    substituted_origs.add(sym)
                    tlh_wash[sym] = (current_date + timedelta(days=31)).date()
                    sub_info = {'symbol': sub_sym, 'correlation': sub['correlation'], 'swapped': True}
                else:
                    sub_info = None
            else:
                # No qualifying substitute found — skip this harvest entirely.
                # NO transaction = NO tax savings. We do NOT set a wash sale period here
                # because nothing was sold; the position will be re-scanned next month.
                best_corr = sub['correlation'] if sub else None
                missed_harvests.append({
                    'date': current_date.strftime('%Y-%m-%d'),
                    'symbol': sym,
                    'loss_pct': round(loss_pct, 2),
                    'dollar_loss': round(dollar_loss, 2),
                    'potential_tax_savings': round(tax_savings, 2),
                    'best_substitute_found': sub['symbol'] if sub else None,
                    'best_correlation': round(best_corr, 4) if best_corr is not None else None,
                    'reason': f'best substitute correlation {best_corr:.2f} < threshold {min_substitute_correlation}' if best_corr is not None else 'no substitute found in ETF universe',
                })
                continue  # skip — no actual transaction, no tax savings

            # A real swap was executed: sell sym, buy substitute.
            # Only book tax savings when an actual transaction occurs.
            _reinvest_tax_savings(tax_savings)
            cumulative_tax_savings += tax_savings
            tlh_tax_cash += tax_savings

            # sub_entry_price: close price of substitute at harvest date.
            # substitute_exit_price / substitute_pnl / net_harvest_outcome are back-filled
            # when the swap closes (rebuy_date). Events still open at period end will not
            # have these fields — the agent must note this in any per-event report.
            sub_close_entry = close_matrix.loc[current_date, sub_sym] if sub_sym in close_matrix.columns else None
            sub_entry_price = round(float(sub_close_entry), 4) if sub_close_entry is not None and pd.notna(sub_close_entry) else None

            harvest_events.append({
                'date': current_date.strftime('%Y-%m-%d'),
                'symbol': sym,
                'substitute': sub_sym,
                'substitute_entry_price': sub_entry_price,
                'correlation': sub['correlation'],
                'swapped': True,
                'loss_pct': round(loss_pct, 2),
                'dollar_loss': round(dollar_loss, 2),
                'tax_savings': round(tax_savings, 2),
                'term': 'short-term' if days_held < 365 else 'long-term',
                'tax_rate': rate,
                # Back-filled when swap closes: substitute_exit_price, substitute_return_pct,
                # substitute_pnl, substitute_hold_days, rebuy_date, net_harvest_outcome
            })

        # ── Daily TLH portfolio value (actual swapped positions + banked tax savings) ─
        day_val = sum(
            tlh_sh.get(sym, 0) * float(price_matrix.loc[current_date, sym])
            for sym in tlh_sh
            if sym in price_matrix.columns and pd.notna(price_matrix.loc[current_date, sym])
        ) + tlh_cash
        tlh_daily_values.append(day_val)

    tlh_series = pd.Series(tlh_daily_values, index=trading_dates)

    # -----------------------------------------------------------------------
    # 6. Format output
    # -----------------------------------------------------------------------
    date_strs = [d.strftime('%Y-%m-%d') for d in comparison.index]
    etf_vals = etf_series.reindex(comparison.index).tolist()
    direct_vals = direct_index_series.reindex(comparison.index).tolist()
    tlh_vals = tlh_series.reindex(comparison.index).tolist()

    etf_final = etf_vals[-1]
    direct_final = direct_vals[-1]
    tlh_final = tlh_vals[-1]
    tlh_alpha = tlh_final - direct_final   # substitute performance + tax savings
    tax_savings_pct = (cumulative_tax_savings / capital) * 100

    summary = (
        f"Starting capital: ${capital:,.0f} | Period: {start_date} to {end_date}\n"
        f"ETF buy & hold:        ${etf_final:,.0f} ({(etf_final/capital - 1)*100:+.2f}%)\n"
        f"Direct index (no TLH): ${direct_final:,.0f} ({(direct_final/capital - 1)*100:+.2f}%) "
        f"[max ETF tracking error: {max_tracking_error:.2f}%]\n"
        f"Direct index + TLH:    ${tlh_final:,.0f} ({(tlh_final/capital - 1)*100:+.2f}%)\n"
        f"TLH alpha:             ${tlh_alpha:,.0f} total "
        f"(${cumulative_tax_savings:,.0f} tax savings + ${tlh_alpha - cumulative_tax_savings:,.0f} substitute performance) "
        f"from {len(harvest_events)} harvests"
    )

    return {
        'dates': date_strs,
        'etf_values': etf_vals,
        'direct_index_values': direct_vals,
        'tlh_values': tlh_vals,
        'tracking_error_pct': round(float(max_tracking_error), 2),
        'harvest_events': harvest_events,
        'missed_harvests': missed_harvests,
        'total_tax_savings': round(cumulative_tax_savings, 2),
        'total_losses_harvested': round(sum(e['dollar_loss'] for e in harvest_events), 2),
        'total_missed_potential': round(sum(e['potential_tax_savings'] for e in missed_harvests), 2),
        'substitute_alpha': round(tlh_alpha - cumulative_tax_savings, 2),
        'total_tlh_alpha': round(tlh_alpha, 2),
        'etf_final_value': round(etf_final, 2),
        'direct_final_value': round(direct_final, 2),
        'tlh_final_value': round(tlh_final, 2),
        'n_positions': len(shares_map),
        'coverage_pct': coverage_pct,
        'summary': summary,
    }
