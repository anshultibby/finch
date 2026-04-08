"""
Charts for direct indexing and TLH visualization.

Functions:
    plot_tlh_plan(plan)         — correlation quality chart for a TLH plan
    plot_simulation(result)     — three-line ETF vs direct index vs TLH comparison
"""
from typing import Dict, Any


def plot_tlh_plan(
    plan: Dict[str, Any],
    output_path: str = 'tlh_plan.png',
    max_opportunities: int = 30,
) -> str:
    """
    Visualize a TLH plan as a horizontal bar chart showing each harvest opportunity
    with its substitute and correlation quality.

    Each bar represents one opportunity:
      - Length = correlation (0 → 1)
      - Color = match quality: green (≥0.85), orange (0.70–0.85), red (<0.70)
      - Left label: "SOLD → SUBSTITUTE"
      - Right annotation: tax savings + recommendation

    Opportunities are sorted by tax savings (largest first).
    Above the chart: total savings and number of harvests.

    Args:
        plan:               Output of build_tlh_plan()
        output_path:        Where to save the PNG
        max_opportunities:  Cap displayed rows (show top N by tax savings)

    Returns:
        output_path (for display via show_image)
    """
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches
    import numpy as np

    opportunities = plan.get('harvest_opportunities', [])
    if not opportunities:
        raise ValueError('No harvest opportunities in plan — nothing to chart')

    # Sort by tax savings descending, cap at max_opportunities
    opps = sorted(opportunities, key=lambda o: -o.get('estimated_tax_savings', 0))
    opps = opps[:max_opportunities]

    n = len(opps)
    fig_height = max(4, n * 0.45 + 2)
    fig, ax = plt.subplots(figsize=(11, fig_height))

    y_positions = np.arange(n)

    for i, opp in enumerate(opps):
        sub = opp.get('substitute', {})
        corr = sub.get('correlation')
        rec = opp.get('recommendation', 'HARVEST')
        savings = opp.get('estimated_tax_savings', 0)
        symbol = opp['symbol']
        sub_sym = sub.get('symbol', '?')
        term = opp.get('term', '')

        # Bar color by correlation quality
        if corr is None:
            color = '#aaaaaa'   # gray — no correlation data (ETF fallback)
            bar_val = 0.70      # display at 0.70 placeholder
        elif corr >= 0.85:
            color = '#2ecc71'   # green
            bar_val = corr
        elif corr >= 0.70:
            color = '#f39c12'   # orange
            bar_val = corr
        else:
            color = '#e74c3c'   # red
            bar_val = corr

        # Dim SKIP opportunities
        alpha = 0.5 if rec == 'SKIP' else 0.85

        ax.barh(i, bar_val, color=color, alpha=alpha, height=0.6, left=0)

        # Correlation label inside bar
        corr_label = f'R={corr:.2f}' if corr is not None else 'ETF'
        ax.text(
            max(bar_val - 0.02, 0.02), i,
            corr_label,
            va='center', ha='right', fontsize=8, color='white', fontweight='bold',
        )

        # Right: tax savings + rec badge
        rec_color = {'HARVEST': '#27ae60', 'BORDERLINE': '#e67e22', 'SKIP': '#c0392b'}.get(rec, '#888')
        ax.text(
            1.02, i,
            f'${savings:,.0f}  [{rec}]',
            va='center', ha='left', fontsize=8.5,
            color=rec_color, fontweight='bold' if rec == 'HARVEST' else 'normal',
        )

    # Y-axis labels: "NVDA → AMD  (short-term)"
    labels = []
    for opp in opps:
        sub = opp.get('substitute', {})
        term_tag = ' ST' if opp.get('is_short_term') else ' LT'
        labels.append(f"{opp['symbol']} → {sub.get('symbol', '?')}{term_tag}")

    ax.set_yticks(y_positions)
    ax.set_yticklabels(labels, fontsize=9)
    ax.invert_yaxis()

    ax.set_xlim(0, 1)
    ax.set_xlabel('Substitute Correlation (R)', fontsize=10)
    ax.axvline(0.85, color='#2ecc71', linestyle='--', linewidth=1, alpha=0.6, label='R=0.85 threshold')
    ax.axvline(0.70, color='#f39c12', linestyle='--', linewidth=1, alpha=0.6, label='R=0.70 threshold')

    # Summary title
    total_savings = plan.get('total_estimated_tax_savings', 0)
    total_losses = plan.get('total_losses_to_harvest', 0)
    harvest_count = len([o for o in opportunities if o.get('recommendation') == 'HARVEST'])
    shown_note = f' (top {max_opportunities} shown)' if len(opportunities) > max_opportunities else ''
    ax.set_title(
        f'TLH Plan — {harvest_count} HARVEST opportunities{shown_note}\n'
        f'Total losses: ${total_losses:,.0f}  |  Estimated tax savings: ${total_savings:,.0f}',
        fontsize=11, fontweight='bold', pad=12,
    )

    # Legend
    legend_patches = [
        mpatches.Patch(color='#2ecc71', label='Strong match  R ≥ 0.85'),
        mpatches.Patch(color='#f39c12', label='Moderate match  0.70–0.85'),
        mpatches.Patch(color='#e74c3c', label='Weak match  R < 0.70'),
        mpatches.Patch(color='#aaaaaa', label='ETF substitute (no R data)'),
    ]
    ax.legend(handles=legend_patches, loc='lower right', fontsize=8, framealpha=0.8)

    # Warnings
    warnings = plan.get('warnings', [])
    if warnings:
        warning_text = f'⚠ {len(warnings)} position(s) with warnings — check plan[\'warnings\']'
        fig.text(0.5, 0.01, warning_text, ha='center', fontsize=8, color='#c0392b')

    plt.tight_layout(rect=[0, 0.03, 1, 1])
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()
    return output_path


def plot_simulation(
    result: Dict[str, Any],
    output_path: str = 'direct_index_comparison.png',
) -> str:
    """
    Three-line comparison chart from simulate_direct_index output:
      1. ETF buy & hold (baseline)
      2. Direct index, no TLH (should nearly overlap with ETF)
      3. Direct index + cumulative TLH savings (the alpha)

    Green shading between lines 2 and 3 shows the TLH benefit accumulating over time.
    Harvest events are marked as small triangles on line 3.

    Args:
        result:       Output of simulate_direct_index()
        output_path:  Where to save the PNG

    Returns:
        output_path
    """
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    import pandas as pd

    dates = pd.to_datetime(result['dates'])
    etf_vals = result['etf_values']
    direct_vals = result['direct_index_values']
    tlh_vals = result['tlh_values']
    harvest_events = result.get('harvest_events', [])
    total_savings = result.get('total_tax_savings', 0)
    tracking_err = result.get('tracking_error_pct', 0)

    fig, ax = plt.subplots(figsize=(13, 6))

    ax.plot(dates, etf_vals,    color='steelblue',  linewidth=2,   label='ETF Buy & Hold')
    ax.plot(dates, direct_vals, color='#888888',    linewidth=1.5, linestyle='--',
            label=f'Direct Index, no TLH  (tracking error: {tracking_err:.2f}%)')
    ax.plot(dates, tlh_vals,    color='#27ae60',    linewidth=2.5,
            label=f'Direct Index + TLH  (+${total_savings:,.0f})')

    ax.fill_between(dates, direct_vals, tlh_vals, alpha=0.15, color='#27ae60', label='TLH alpha')

    # Mark harvest events as small triangles on the TLH line
    if harvest_events:
        harvest_dates = pd.to_datetime([e['date'] for e in harvest_events])
        # Interpolate TLH values at harvest dates
        tlh_series = pd.Series(tlh_vals, index=dates)
        for hd in harvest_dates:
            nearest = tlh_series.index[tlh_series.index.get_indexer([hd], method='nearest')[0]]
            ax.plot(nearest, tlh_series[nearest], marker='^', color='#27ae60',
                    markersize=6, alpha=0.7, zorder=5)

    ax.axhline(result.get('etf_values', [0])[0], color='gray', linestyle=':', alpha=0.4,
               label='Starting capital')

    ax.set_xlabel('Date', fontsize=11)
    ax.set_ylabel('Portfolio Value ($)', fontsize=11)
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f'${x:,.0f}'))
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%b %Y'))
    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=2))
    plt.xticks(rotation=30)

    etf_final = etf_vals[-1]
    tlh_final = tlh_vals[-1]
    capital = result.get('etf_values', [0])[0]
    n_harvests = len(harvest_events)
    ax.set_title(
        f'Direct Indexing vs ETF — {result["dates"][0][:4]}\n'
        f'ETF: {(etf_final/capital - 1)*100:+.1f}%  |  '
        f'Direct Index + TLH: {(tlh_final/capital - 1)*100:+.1f}%  |  '
        f'{n_harvests} harvests  |  Tax savings: ${total_savings:,.0f}',
        fontsize=11, fontweight='bold',
    )
    ax.legend(fontsize=9, loc='upper left')

    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()
    return output_path
