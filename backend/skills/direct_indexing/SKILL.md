---
name: direct_indexing
description: "Use for ANY direct indexing or TLH question. Entry point: run_direct_index_model() — runs scenario variations (1%/3%/5% thresholds) and returns RECOMMEND/MARGINAL/SKIP with fee break-even analysis. For a single simulation: simulate_direct_index(). Both use SEC EDGAR historical weights (not top-N, not renormalized). Writing your own simulation loop is always wrong."
metadata:
  emoji: "📊"
  category: finance
  is_system: true
  auto_on: true
  requires:
    env: []
    bins: []
---

# Direct Indexing Skill

## ⛔ STOP — read before writing any code

**NEVER guess, approximate, or present unverified numbers. Always run the full computation.**

**NEVER do any of the following:**
- Write your own simulation loop
- Use `top_n`, subset holdings, or filter to "top 50"
- Renormalize weights after filtering
- Fetch prices manually and compute returns yourself
- Use `weightPercentage` from FMP directly for historical simulations (FMP returns today's weights, not historical)
- Present estimated tax savings without running the simulation ("roughly 1-2%", "typically $X" — no)
- Invent or extrapolate numbers when the function returns an error — diagnose and fix the error instead

**Why top-N is always wrong:** If you take QQQ's top 50 and renormalize to 100%, you silently exclude the underperformers and overweight the winners. The direct index will appear to beat QQQ *before* any TLH — which is impossible by construction (direct indexing is the same portfolio, just unwrapped). Any pre-TLH outperformance means the simulation is broken.

**The correct call for every direct indexing question:**
```python
from skills.direct_indexing.scripts.model import run_direct_index_model
result = run_direct_index_model('QQQ', capital=100_000, start_date='2025-01-02', end_date='2025-12-31')
print(result['summary'])   # includes RECOMMEND/MARGINAL/SKIP verdict + all scenario numbers
```
That's it. One import, one call. Everything — historical weights from SEC EDGAR, exact prices, full replication, TLH loop, wash sale tracking, sector-peer substitutes, scenario sensitivity, fee break-even — is handled inside.

**Sanity check before presenting results:** `result['base']['tracking_error_pct']` must be < 0.5%. If the direct index (no TLH) return differs from ETF return by more than ~0.5%, the simulation is wrong. Do not present it. Do not explain it away. Fix it.

**Per-harvest substitute tracking is mandatory.** Every harvest event where `swapped=True` must have its substitute performance computed and reported. The fields are filled automatically when the swap closes:
```python
for ev in result['base']['harvest_events']:
    if ev.get('swapped'):
        # These fields are present once the rebuy window has passed:
        print(f"{ev['symbol']} → {ev['substitute']}: "
              f"tax savings ${ev['tax_savings']:,.0f}  |  "
              f"sub return {ev.get('substitute_return_pct', 'open'):+.1f}%  |  "
              f"net outcome ${ev.get('net_harvest_outcome', 'open'):,.0f}")
```
Never summarise TLH results without showing per-event substitute tracking. A harvest that saved $800 in taxes but lost $1,200 on the substitute is a net loss — the agent must compute and display this, not just cite the tax savings number.

---

## Which function to use

| User question | Call |
|---|---|
| "Should I do direct indexing? Is it worth it for me?" | `run_direct_index_model` ← **start here** |
| "What would direct indexing + TLH have made in 2025?" | `run_direct_index_model` or `simulate_direct_index` |
| "What should I harvest right now?" | `build_tlh_plan` |
| "Build me a direct index portfolio" | `build_direct_index` |
| "Is this harvest worth doing?" | `score_harvest_opportunity` |

---

## 0. Decision model — `run_direct_index_model` (recommended entry point)

Use this when the user wants to know whether direct indexing makes sense for them, or wants to compare scenarios. Runs the simulation at three harvest thresholds (1%, 3%, 5%) and returns a `RECOMMEND / MARGINAL / SKIP` verdict with fee break-even analysis.

```python
from skills.direct_indexing.scripts.model import run_direct_index_model

result = run_direct_index_model(
    etf_symbol='QQQ',
    capital=500_000,
    start_date='2024-01-02',
    end_date='2024-12-31',
    tax_rate_st=0.503,   # California: fed 37% + state 13.3%
    tax_rate_lt=0.371,   # California: fed 23.8% + state 13.3%
)

print(result['recommendation'])      # 'RECOMMEND' | 'MARGINAL' | 'SKIP'
print(result['summary'])             # full narrative with scenarios + fee analysis

# Access the base simulation result directly:
base = result['base']
print(base['summary'])               # ETF vs DI vs TLH returns

# Scenario comparison:
for s in result['scenarios']:
    print(f"Threshold {s['harvest_threshold_pct']:.0f}%:  "
          f"${s['total_tax_savings']:,.0f} saved ({s['annualized_yield_pct']:.2f}% annualized)")

# Break-even fee: max annual DI management fee this TLH yield justifies
print(f"Break-even fee: {result['break_even_fee_pct']:.2f}% AUM/yr")
```

**Output: `result['summary']` looks like:**
```
Direct Indexing Model: QQQ | $500,000 capital | 2024-01-02 to 2024-12-31 (364 days)
Tax rates: 50.3% ST / 37.1% LT

Returns:
  ETF buy & hold:        +24.89%
  Direct index (no TLH): +24.71%  [tracking error: 0.31%]
  Direct index + TLH:    +25.84%

TLH yield: 0.95% annualized  |  break-even fee: 0.90%

Harvest threshold sensitivity:
  Harvest >1%:  $6,240 saved (1.25% annualized), 87 harvests
  Harvest >3%:  $4,750 saved (0.95% annualized), 34 harvests
  Harvest >5%:  $3,100 saved (0.62% annualized), 18 harvests

Fee break-even analysis:
  Low fee (0.15%):  $750/yr cost vs $4,750/yr savings → +$4,000/yr net  [worthwhile]
  Mid fee (0.25%):  $1,250/yr cost vs $4,750/yr savings → +$3,500/yr net  [worthwhile]
  High fee (0.40%): $2,000/yr cost vs $4,750/yr savings → +$2,750/yr net  [worthwhile]

RECOMMENDATION: RECOMMEND
Direct indexing is clearly beneficial at this tax rate and capital level.
```

---

## 1. Historical simulation — `simulate_direct_index`

```python
from skills.direct_indexing.scripts.simulate import simulate_direct_index

result = simulate_direct_index(
    etf_symbol='QQQ',
    capital=100_000,
    start_date='2025-01-02',          # first trading day — must be a market day
    end_date='2025-03-31',
    harvest_threshold_pct=3.0,        # harvest losses > 3% below cost basis
    tax_rate_st=0.37,                  # short-term rate (add state: CA=0.503, NYC=0.479)
    tax_rate_lt=0.238,                 # long-term rate
    harvest_frequency_days=30,        # scan monthly
)

# Always check for errors first
if 'error' in result:
    print(result['error'])

print(result['summary'])
# Starting capital: $100,000 | Period: 2025-01-02 to 2025-03-31
# ETF buy & hold:        $92,040 (-7.96%)
# Direct index (no TLH): $92,344 (-7.66%) [max ETF tracking error: 0.33%]
# Direct index + TLH:    $92,377 (-7.62%)
# TLH alpha:             $2,240 from 33 harvests
```

**Result keys:**
- `dates` — list of date strings
- `etf_values`, `direct_index_values`, `tlh_values` — parallel lists of daily portfolio values
- `tracking_error_pct` — max daily deviation of direct index vs ETF (expect < 0.5%)
- `harvest_events` — list of `{date, symbol, loss_pct, dollar_loss, tax_savings, term}`
- `total_tax_savings`, `total_losses_harvested`
- `etf_final_value`, `direct_final_value`, `tlh_final_value`
- `n_positions`, `coverage_pct`

**How it works — data sources (no paid APIs required):**
- **Historical ETF weights**: fetched free from SEC EDGAR N-PORT filings. QQQ's Dec 31 N-PORT gives exact Nasdaq-100 composition — 101 holdings with precise weights — available ~60 days after quarter end.
- **Prices**: FMP batch historical OHLCV, disk-cached so subsequent runs are instant.
- **Tracking**: with exact historical weights and fractional shares, the direct index tracks within ~0.3% of the ETF. If > 0.5%, the function returns an error.

---

## 2. Plot the simulation

```python
from skills.direct_indexing.scripts.charts import plot_simulation

plot_simulation(result, output_path='direct_index_comparison.png')
```

Produces a three-line chart: ETF (blue) vs Direct Index no-TLH (gray dashed) vs Direct Index + TLH (green), with green shading between lines 2 and 3 showing TLH alpha. Harvest events are marked as triangles on line 3.

Or build it manually:
```python
import pandas as pd
import matplotlib.pyplot as plt

df = pd.DataFrame({
    'date': pd.to_datetime(result['dates']),
    'QQQ Buy & Hold': result['etf_values'],
    'Direct Index (no TLH)': result['direct_index_values'],
    'Direct Index + TLH': result['tlh_values'],
}).set_index('date')

fig, ax = plt.subplots(figsize=(13, 6))
ax.plot(df.index, df['QQQ Buy & Hold'], color='steelblue', linewidth=2, label='QQQ Buy & Hold')
ax.plot(df.index, df['Direct Index (no TLH)'], color='gray', linestyle='--', linewidth=1.5, label='Direct Index (no TLH)')
ax.plot(df.index, df['Direct Index + TLH'], color='green', linewidth=2.5,
        label=f"Direct Index + TLH (+${result['total_tax_savings']:,.0f})")
ax.fill_between(df.index, df['Direct Index (no TLH)'], df['Direct Index + TLH'],
                alpha=0.2, color='green')
ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f'${x:,.0f}'))
ax.set_title(f"Direct Indexing {result.get('etf_symbol','QQQ')} with TLH\n"
             f"${result['total_tax_savings']:,.0f} saved from {len(result['harvest_events'])} harvests")
ax.legend(); plt.tight_layout()
plt.savefig('direct_index_comparison.png', dpi=150, bbox_inches='tight')
```

---

## 3. Historical ETF holdings — `get_etf_holdings`

The simulation calls this automatically. Call it directly if you need the holdings for other purposes.

```python
from skills.financial_modeling_prep.scripts.etf.holdings import get_etf_holdings

# Historical — uses SEC EDGAR N-PORT (exact weights, free)
holdings = get_etf_holdings('QQQ', date='2025-01-02')
# Returns Dec 31, 2024 N-PORT filing: 92 holdings with exact weights

# Current — uses FMP (today's composition)
holdings = get_etf_holdings('QQQ')

# Each holding dict:
# {'asset': 'AAPL', 'name': 'Apple Inc.', 'weightPercentage': 9.79,
#  'cusip': '037833100', 'isin': 'US0378331005',
#  'source': 'edgar_nport', 'filing_period': '2024-12-31'}
```

**EDGAR N-PORT coverage**: QQQ and SPY are supported directly. Other ETFs need their CIK looked up dynamically. Filings are available ~60 days after quarter end (Dec 31 data → available ~Feb 28).

---

## 4. TLH plan — `build_tlh_plan`

For users who already have a portfolio and want to know what to harvest *today*:

```python
from skills.direct_indexing.scripts.tlh_engine import TaxLot, lots_from_positions, build_tlh_plan
from skills.financial_modeling_prep.scripts.etf.holdings import get_etf_holdings

# Build lots from broker positions
lots = lots_from_positions([
    {'symbol': 'NVDA', 'shares': 15, 'cost_basis_per_share': 140.00,
     'current_price': 115.00, 'purchase_date': '2025-01-10'},
    {'symbol': 'META', 'shares': 8, 'cost_basis_per_share': 620.00,
     'current_price': 490.00, 'purchase_date': '2025-02-01'},
])

etf_holdings = get_etf_holdings('QQQ')   # universe for substitute selection

plan = build_tlh_plan(
    lots=lots,
    wash_sale_log=[],           # {'symbol': 'X', 'sale_date': 'YYYY-MM-DD', 'was_loss': True}
    etf_holdings=etf_holdings,
    threshold_loss_pct=3.0,
    min_dollar_loss=100.0,
    tax_rate_st=0.37,
    tax_rate_lt=0.238,
    min_correlation=0.85,
)

print(plan['summary'])
for opp in plan['harvest_opportunities']:
    sub = opp['substitute']
    print(f"{opp['symbol']} → {sub['symbol']} (R={sub['correlation']:.2f}): "
          f"${opp['estimated_tax_savings']:,.0f} saved  [{opp['action']}]")
```

**Substitute selection**: picks the highest-correlation stock from the ETF universe (90-day return correlation), excluding wash-sale-blocked tickers and any stock already used as another position's substitute in the same plan.

```python
from skills.direct_indexing.scripts.charts import plot_tlh_plan
plot_tlh_plan(plan, output_path='tlh_plan.png')
# Horizontal bar chart: bar length = correlation, color = green/orange/red by quality
```

---

## 5. Build a live direct index — `build_direct_index`

```python
from skills.direct_indexing.scripts.build_portfolio import build_direct_index

result = build_direct_index('QQQ', capital=100_000, as_of_date='2025-01-02')

print(f"Holdings: {result['n_holdings']}, Coverage: {result['coverage_pct']:.1f}%")
for pos in result['positions'][:5]:
    print(f"  {pos['symbol']:6s}  {pos['etf_weight_pct']:.2f}%  "
          f"{pos['shares']} shares @ ${pos['price']:.2f}")

# Place orders via Alpaca
from skills.alpaca.scripts.trading import place_order
for pos in result['positions']:
    place_order(symbol=pos['symbol'], qty=pos['shares'], side='buy', paper=True)
```

---

## 6. Score a single harvest opportunity

```python
from skills.direct_indexing.scripts.tlh_engine import score_harvest_opportunity

score = score_harvest_opportunity(
    dollar_loss=1550,
    tax_rate=0.37,
    substitute_correlation=0.91,
    annualized_volatility=0.30,
    hold_days=31,
    years_until_liquidation=10,
)
# {'tax_savings': 573.50, 'tracking_error_cost': 82.40, 'net_expected_value': 491.10,
#  'break_even_hold_days': 4, 'recommendation': 'HARVEST', 'explanation': '...'}
```

---

## Tax rates — always ask the user's state

| State | Short-term total | Long-term total |
|---|---|---|
| Federal only | 37.0% | 23.8% |
| California | ~50.3% | ~37.1% |
| New York City | ~47.9% | ~34.7% |
| Texas / Florida | 37.0% | 23.8% |

Pass combined rates to `build_tlh_plan(tax_rate_st=0.503, tax_rate_lt=0.371)`.

---

## Expected TLH yields by market regime

| Regime | Annual yield | Example |
|---|---|---|
| Strong bull | 0.5–1.5% | 2013–2017 |
| Choppy / sideways | 2–4% | most normal years |
| Bear / high vol | 4–8% | 2022, Q1 2025 |

Yields are highest in years 1–3 of a new account (fresh lots near cost basis).
