"""Build a direct index portfolio from an ETF's constituents."""
from .etf_constituents import get_etf_holdings
from skills.financial_modeling_prep.scripts.market.quote import get_quote_snapshot
from skills.financial_modeling_prep.scripts.market.historical_prices import get_historical_prices, get_batch_historical_prices
from typing import List, Dict, Any, Optional


def build_direct_index(
    etf_symbol: str,
    capital: float,
    as_of_date: Optional[str] = None,
    min_weight_pct: float = 0.05,
    min_shares: float = 1,
    fractional: bool = False,
) -> Dict[str, Any]:
    """
    Build a market-cap-weighted direct index portfolio that exactly replicates an ETF.

    Every constituent is held at its true ETF weight. There is no top-N trimming —
    partial replication defeats the purpose (it changes the exposure, not just scales it).
    The only positions skipped are those below min_weight_pct, which are genuinely too
    small to buy a single share at reasonable capital levels.

    Args:
        etf_symbol:     ETF to replicate (e.g., 'QQQ', 'SPY', 'VTI')
        capital:        Total dollars to invest
        as_of_date:     Date to price the portfolio (YYYY-MM-DD). REQUIRED for any
                        historical analysis. If None, uses today's live prices.
                        For "what if I had invested on Jan 1 2025?", pass '2025-01-02'
                        (first trading day). Using today's prices for a historical
                        comparison produces completely wrong initial allocations.
        fractional:     Allow fractional shares (default False = whole shares only).
                        Set True for simulations and backtests — eliminates rounding
                        cash drag and keeps the direct index tracking within < 0.1% of
                        the ETF. Set False for live trading (most brokers require whole
                        shares; Alpaca supports fractional for most US stocks).
        min_weight_pct: Skip constituents whose ETF weight is below this threshold.
                        Default 0.05% — eliminates micro-positions that would require
                        fractional shares or result in $0 allocated. The skipped weight
                        stays as cash and is reported in cash_remainder.
        min_shares:     Minimum shares per position. Default 1.
                        If fractional=True, this can be a float (e.g. 0.001).

    Returns:
        dict with:
            etf:             ETF symbol
            as_of_date:      Date prices were sourced from (None = live)
            capital:         Total capital provided
            n_holdings:      Number of positions actually purchased
            coverage_pct:    % of ETF weight captured by held positions (should be ~99%+)
            deployed_capital: Capital invested in stock positions
            cash_remainder:  Uninvested cash (from whole-share rounding + skipped micro-weights)
            positions:       List of dicts per position:
                               symbol, name, etf_weight_pct, target_value,
                               shares, price, actual_value
            skipped:         List of tickers skipped (below min_weight_pct or no price)
            notes:           Informational strings

    How to use for "what if I had direct indexed instead of holding QQQ?":
        portfolio = build_direct_index('QQQ', capital=100_000, as_of_date='2025-01-02')
        # Prices are sourced from Jan 2 2025 — the actual purchase prices on that date.
        # coverage_pct should be 99%+. cash_remainder is minimal.
        # Simulate daily P&L by applying each stock's historical daily return
        # to its actual_value. Sum across constituents = direct index portfolio value.
        # This should track QQQ within ~0.1-0.3% annually before TLH.
        # The ONLY source of outperformance vs QQQ is TLH alpha.
    """
    notes = []
    skipped = []

    # 1. Get all ETF constituents
    holdings = get_etf_holdings(etf_symbol)
    if isinstance(holdings, dict) and 'error' in holdings:
        return holdings
    if not holdings:
        return {'error': f'No holdings found for {etf_symbol}'}

    # 2. Sort by weight, compute total (should sum to ~100)
    holdings = sorted(holdings, key=lambda h: float(h.get('weightPercentage') or 0), reverse=True)
    total_weight = sum(float(h.get('weightPercentage') or 0) for h in holdings)
    if total_weight == 0:
        return {'error': 'ETF holdings have zero total weight'}

    # 3. Fetch prices — historical if as_of_date provided, live otherwise
    symbols = [h['asset'] for h in holdings if h.get('asset')]
    price_map: Dict[str, float] = {}

    if as_of_date:
        notes.append(f'Prices sourced from historical data on or before {as_of_date}.')
        # Use a 5-day window ending on as_of_date to handle weekends/holidays
        from datetime import date, timedelta
        d = date.fromisoformat(as_of_date)
        window_start = (d - timedelta(days=5)).isoformat()
        # Batch fetch — ~100 symbols in 4 requests instead of 100
        batch_results = get_batch_historical_prices(symbols, from_date=window_start, to_date=as_of_date)
        for sym, hist in batch_results.items():
            if hist.get('prices'):
                price_map[sym] = float(hist['prices'][0]['close'])
    else:
        notes.append('Prices sourced from live quotes (today). Pass as_of_date for historical analysis.')
        BATCH = 50
        for i in range(0, len(symbols), BATCH):
            batch = symbols[i:i + BATCH]
            quotes = get_quote_snapshot(','.join(batch))
            if isinstance(quotes, list):
                for q in quotes:
                    if q.get('symbol') and q.get('price'):
                        price_map[q['symbol']] = float(q['price'])

    # 4. Build positions using true ETF weights
    positions = []
    allocated = 0.0
    covered_weight = 0.0

    for h in holdings:
        symbol = h.get('asset', '').upper()
        if not symbol:
            continue

        raw_weight = float(h.get('weightPercentage') or 0)
        etf_weight_pct = (raw_weight / total_weight) * 100  # normalize to 100%

        if etf_weight_pct < min_weight_pct:
            skipped.append({'symbol': symbol, 'reason': f'weight {etf_weight_pct:.4f}% below {min_weight_pct}%'})
            continue

        price = price_map.get(symbol)
        if not price:
            skipped.append({'symbol': symbol, 'reason': 'no price data'})
            continue

        target_value = capital * (etf_weight_pct / 100)
        if fractional:
            shares = round(max(min_shares, target_value / price), 6)
            actual_value = shares * price  # ≈ target_value exactly
        else:
            shares = max(min_shares, int(target_value / price))
            actual_value = shares * price
        allocated += actual_value
        covered_weight += etf_weight_pct

        positions.append({
            'symbol': symbol,
            'name': h.get('name', ''),
            'etf_weight_pct': round(etf_weight_pct, 4),
            'target_value': round(target_value, 2),
            'shares': shares,
            'price': price,
            'actual_value': round(actual_value, 2),
        })

    cash_remainder = round(capital - allocated, 2)
    coverage_pct = round(covered_weight, 2)

    if coverage_pct < 95:
        notes.append(
            f'WARNING: coverage is only {coverage_pct:.1f}% of ETF weight. '
            f'This portfolio will diverge from {etf_symbol} returns. '
            f'Consider lowering min_weight_pct or checking for missing price data.'
        )
    else:
        notes.append(
            f'Coverage: {coverage_pct:.2f}% of {etf_symbol} weight. '
            f'Pre-TLH returns should track {etf_symbol} within ~0.1-0.5% annually.'
        )

    return {
        'etf': etf_symbol.upper(),
        'as_of_date': as_of_date or 'live',
        'capital': capital,
        'n_holdings': len(positions),
        'coverage_pct': coverage_pct,
        'deployed_capital': round(allocated, 2),
        'cash_remainder': cash_remainder,
        'positions': positions,
        'skipped': skipped,
        'notes': notes,
    }


def diff_direct_index(
    etf_symbol: str,
    capital: float,
    current_positions: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Given an existing direct index portfolio, compute rebalance trades needed
    to stay aligned with current ETF weights and flag TLH candidates.

    Args:
        etf_symbol:         ETF being replicated
        capital:            Total portfolio value to target
        current_positions:  List of dicts: {symbol, shares, cost_basis_per_share, current_price}

    Returns:
        dict with:
            buys:           positions to buy/increase
            sells:          positions to sell/reduce
            holds:          positions within 5% of target (no trade needed)
            tlh_candidates: subset of sells where current_price < cost_basis_per_share
    """
    target = build_direct_index(etf_symbol, capital)
    if 'error' in target:
        return target

    target_map = {p['symbol']: p for p in target['positions']}
    current_map = {p['symbol']: p for p in current_positions}

    buys, sells, holds, tlh_candidates = [], [], [], []

    for symbol, cur in current_map.items():
        cur_value = cur['shares'] * cur['current_price']
        tgt = target_map.get(symbol)

        if tgt is None:
            # Dropped from index — full sell
            loss = (cur['current_price'] - cur['cost_basis_per_share']) * cur['shares']
            entry = {**cur, 'action': 'SELL_ALL', 'reason': 'Not in target index',
                     'unrealized_pnl': round(loss, 2)}
            sells.append(entry)
            if cur['current_price'] < cur['cost_basis_per_share']:
                tlh_candidates.append(entry)
        else:
            diff_value = cur_value - tgt['target_value']
            diff_pct = diff_value / tgt['target_value'] * 100 if tgt['target_value'] else 0

            if abs(diff_pct) < 5:
                holds.append({**cur, 'target_value': tgt['target_value'], 'drift_pct': round(diff_pct, 2)})
            elif diff_value > 0:
                shares_to_sell = int(diff_value / cur['current_price'])
                if shares_to_sell > 0:
                    loss = (cur['current_price'] - cur['cost_basis_per_share']) * shares_to_sell
                    entry = {**cur, 'action': 'SELL', 'shares_to_trade': shares_to_sell,
                             'target_value': tgt['target_value'], 'drift_pct': round(diff_pct, 2),
                             'unrealized_pnl': round(loss, 2)}
                    sells.append(entry)
                    if cur['current_price'] < cur['cost_basis_per_share']:
                        tlh_candidates.append(entry)
            else:
                shares_to_buy = int(abs(diff_value) / cur['current_price'])
                if shares_to_buy > 0:
                    buys.append({**cur, 'action': 'BUY', 'shares_to_trade': shares_to_buy,
                                 'target_value': tgt['target_value'], 'drift_pct': round(diff_pct, 2)})

    # New positions not yet held
    for symbol, tgt in target_map.items():
        if symbol not in current_map:
            buys.append({
                'symbol': symbol, 'name': tgt['name'], 'action': 'BUY_NEW',
                'shares_to_trade': tgt['shares'], 'price': tgt['price'],
                'target_value': tgt['target_value'], 'etf_weight_pct': tgt['etf_weight_pct'],
            })

    return {
        'etf': etf_symbol.upper(),
        'buys': buys,
        'sells': sells,
        'holds': holds,
        'tlh_candidates': tlh_candidates,
    }
