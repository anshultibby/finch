"""
Direct indexing decision model — runs scenario variations and returns a structured recommendation.

The Finch agent uses this instead of calling simulate_direct_index directly, because:
  - It runs multiple parameter variations in one call (reusing cached prices)
  - It computes break-even analysis against typical DI management fees
  - It returns a RECOMMEND/MARGINAL/SKIP decision with plain-English reasoning

Typical agent usage:
    from skills.direct_indexing.scripts.model import run_direct_index_model
    result = run_direct_index_model(
        etf_symbol='QQQ',
        capital=500_000,
        tax_rate_st=0.503,   # California combined rate
        tax_rate_lt=0.371,
        start_date='2024-01-02',
        end_date='2024-12-31',
    )
    print(result['recommendation'])   # 'RECOMMEND' / 'MARGINAL' / 'SKIP'
    print(result['summary'])          # full narrative
"""
from typing import Dict, Any, List, Optional
from .simulate import simulate_direct_index


# Typical annual DI management fee tiers (% of AUM)
_FEE_TIERS = {
    'low':    0.15,   # Fidelity / Vanguard passive DI
    'mid':    0.25,   # Wealthfront / Betterment
    'high':   0.40,   # Parametric / traditional wealth mgmt
}

# Harvest threshold variants to test sensitivity
_THRESHOLD_VARIANTS = [1.0, 3.0, 5.0]


def run_direct_index_model(
    etf_symbol: str,
    capital: float,
    start_date: str,
    end_date: str,
    tax_rate_st: float = 0.37,
    tax_rate_lt: float = 0.238,
    harvest_frequency_days: int = 30,
    min_substitute_correlation: float = 0.80,
    di_fee_pct: Optional[float] = None,   # annual DI management fee to evaluate against; None = evaluate all tiers
) -> Dict[str, Any]:
    """
    Run the direct indexing simulation across multiple harvest-threshold scenarios
    and return a structured recommendation.

    The base simulation uses harvest_threshold_pct=3.0 (industry standard). Sensitivity
    variants at 1% and 5% show how aggressive vs conservative harvesting affects results.
    All variants reuse the same cached price data so only the first call is slow.

    Args:
        etf_symbol:               ETF to replicate ('QQQ', 'SPY', etc.)
        capital:                  Starting capital in dollars
        start_date:               First trading day (YYYY-MM-DD)
        end_date:                 Last trading day (YYYY-MM-DD)
        tax_rate_st:              Short-term capital gains rate (combined fed+state).
                                  CA=0.503, NYC=0.479, TX/FL=0.370
        tax_rate_lt:              Long-term capital gains rate.
                                  CA=0.371, NYC=0.347, TX/FL=0.238
        harvest_frequency_days:   Scan frequency in days (default 30 = monthly)
        min_substitute_correlation: Min R² for substitute swap (default 0.80)
        di_fee_pct:               Annual DI management fee % to break-even against.
                                  If None, evaluates against low/mid/high fee tiers.

    Returns dict with:
        recommendation:         'RECOMMEND' | 'MARGINAL' | 'SKIP'
        base:                   Full result from simulate_direct_index (threshold=3%)
        scenarios:              List of scenario dicts (one per threshold variant)
        annualized_yield_pct:   Annualized TLH yield as % of capital (base scenario)
        break_even_fee_pct:     Max annual DI fee this yield can support
        fee_analysis:           {fee_label: {fee_pct, net_benefit, verdict}}
        summary:                Multi-line narrative for the agent to present to the user
        error:                  Present only if base simulation failed
    """
    import pandas as pd
    from datetime import date as dt

    sim_days = (pd.Timestamp(end_date) - pd.Timestamp(start_date)).days
    years = max(sim_days / 365, 1 / 365)

    # ── Base simulation (3% threshold — industry standard) ──────────────────
    base = simulate_direct_index(
        etf_symbol=etf_symbol,
        capital=capital,
        start_date=start_date,
        end_date=end_date,
        harvest_threshold_pct=3.0,
        tax_rate_st=tax_rate_st,
        tax_rate_lt=tax_rate_lt,
        harvest_frequency_days=harvest_frequency_days,
        min_substitute_correlation=min_substitute_correlation,
    )
    if 'error' in base:
        return {'error': base['error'], 'recommendation': 'UNKNOWN', 'summary': base['error']}

    # ── Sensitivity variants (1% and 5% thresholds) ─────────────────────────
    scenarios: List[Dict] = []
    for thresh in _THRESHOLD_VARIANTS:
        label = f'threshold_{thresh:.0f}pct'
        if thresh == 3.0:
            # Reuse the base run
            sim = base
        else:
            sim = simulate_direct_index(
                etf_symbol=etf_symbol,
                capital=capital,
                start_date=start_date,
                end_date=end_date,
                harvest_threshold_pct=thresh,
                tax_rate_st=tax_rate_st,
                tax_rate_lt=tax_rate_lt,
                harvest_frequency_days=harvest_frequency_days,
                min_substitute_correlation=min_substitute_correlation,
            )
        if 'error' in sim:
            continue
        ann_yield = (sim['total_tax_savings'] / capital) * (365 / sim_days) * 100
        scenarios.append({
            'label': label,
            'harvest_threshold_pct': thresh,
            'total_tax_savings': sim['total_tax_savings'],
            'n_harvests': len(sim['harvest_events']),
            'annualized_yield_pct': round(ann_yield, 2),
            'tracking_error_pct': sim['tracking_error_pct'],
            'tlh_final_value': sim['tlh_final_value'],
            'etf_final_value': sim['etf_final_value'],
        })

    # ── Annualized yield from base ───────────────────────────────────────────
    ann_yield_base = (base['total_tax_savings'] / capital) * (365 / sim_days) * 100
    # Break-even fee: annualized yield minus a small tracking cost buffer (0.05%)
    break_even_fee = max(0.0, ann_yield_base - 0.05)

    # ── Fee analysis ─────────────────────────────────────────────────────────
    tiers = {di_fee_pct: 'custom'} if di_fee_pct is not None else {v: k for k, v in _FEE_TIERS.items()}
    fee_analysis: Dict[str, Dict] = {}
    for fee, label in tiers.items():
        annual_fee_dollars = capital * (fee / 100)
        # Net benefit = annualized tax savings minus annual fee cost
        annual_savings = base['total_tax_savings'] / years
        net_annual = annual_savings - annual_fee_dollars
        verdict = 'worthwhile' if net_annual > 0 else 'not worthwhile'
        fee_analysis[label] = {
            'fee_pct': fee,
            'annual_fee_dollars': round(annual_fee_dollars, 0),
            'annual_savings_dollars': round(annual_savings, 0),
            'net_annual_dollars': round(net_annual, 0),
            'verdict': verdict,
        }

    # ── Recommendation ───────────────────────────────────────────────────────
    if ann_yield_base >= _FEE_TIERS['high'] + 0.10:
        recommendation = 'RECOMMEND'
    elif ann_yield_base >= _FEE_TIERS['low']:
        recommendation = 'MARGINAL'
    else:
        recommendation = 'SKIP'

    # ── Build summary narrative ──────────────────────────────────────────────
    etf_ret = (base['etf_final_value'] / capital - 1) * 100
    di_ret  = (base['direct_final_value'] / capital - 1) * 100
    tlh_ret = (base['tlh_final_value'] / capital - 1) * 100
    period_label = f"{start_date} to {end_date} ({sim_days} days)"

    scenario_lines = []
    for s in scenarios:
        scenario_lines.append(
            f"  Harvest >{s['harvest_threshold_pct']:.0f}%:  "
            f"${s['total_tax_savings']:,.0f} saved ({s['annualized_yield_pct']:.2f}% annualized), "
            f"{s['n_harvests']} harvests"
        )

    fee_lines = []
    for label, fa in fee_analysis.items():
        fee_lines.append(
            f"  {label.capitalize()} fee ({fa['fee_pct']:.2f}%):  "
            f"${fa['annual_fee_dollars']:,.0f}/yr cost vs ${fa['annual_savings_dollars']:,.0f}/yr savings "
            f"→ ${fa['net_annual_dollars']:+,.0f}/yr net  [{fa['verdict']}]"
        )

    rec_text = {
        'RECOMMEND': 'Direct indexing is clearly beneficial at this tax rate and capital level.',
        'MARGINAL':  'Direct indexing may be worthwhile at lower fee tiers, but margins are thin.',
        'SKIP':      'TLH yield is too low to justify direct indexing management fees.',
    }[recommendation]

    summary_lines = [
        f"Direct Indexing Model: {etf_symbol} | ${capital:,.0f} capital | {period_label}",
        f"Tax rates: {tax_rate_st*100:.1f}% ST / {tax_rate_lt*100:.1f}% LT",
        "",
        f"Returns:",
        f"  ETF buy & hold:        {etf_ret:+.2f}%",
        f"  Direct index (no TLH): {di_ret:+.2f}%  [tracking error: {base['tracking_error_pct']:.2f}%]",
        f"  Direct index + TLH:    {tlh_ret:+.2f}%",
        "",
        f"TLH yield: {ann_yield_base:.2f}% annualized  |  break-even fee: {break_even_fee:.2f}%",
        "",
        "Harvest threshold sensitivity:",
        *scenario_lines,
        "",
        "Fee break-even analysis:",
        *fee_lines,
        "",
        f"RECOMMENDATION: {recommendation}",
        rec_text,
    ]
    summary = "\n".join(summary_lines)

    return {
        'recommendation': recommendation,
        'base': base,
        'scenarios': scenarios,
        'annualized_yield_pct': round(ann_yield_base, 2),
        'break_even_fee_pct': round(break_even_fee, 2),
        'fee_analysis': fee_analysis,
        'summary': summary,
        'etf_symbol': etf_symbol,
        'capital': capital,
        'start_date': start_date,
        'end_date': end_date,
        'tax_rate_st': tax_rate_st,
        'tax_rate_lt': tax_rate_lt,
        'sim_days': sim_days,
    }
