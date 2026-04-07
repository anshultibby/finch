---
name: direct_indexing
description: Build and manage a direct index portfolio — own the individual stocks inside an ETF in the same market-cap weights instead of the ETF itself. Enables per-stock tax-loss harvesting (TLH), custom exclusions, and ESG tilts that ETF wrappers don't allow.
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

> **STOP. Before writing any code:** use `simulate_direct_index` for historical comparisons,
> `build_tlh_plan` for current harvesting, `build_direct_index` for portfolio construction.
> **Do NOT write your own simulation, do NOT use `top_n` or subset the holdings.**
> The "which function to use" table below is your first stop — read it before touching anything else.

**Direct indexing** = buying every stock inside an ETF directly, in the same market-cap-weighted proportions, instead of buying the ETF itself. You own every constituent at its exact index weight — not a subset, not equal-dollar — the same exposure the ETF gives you, just without the wrapper.

## Why bother? The core insight

Owning the stocks directly unlocks something ETFs can't offer: **per-stock tax-loss harvesting**.

When you hold SPY and the market drops 10%, you have one position and one potential loss to harvest. When you directly index the S&P 500, you might have 200 positions underwater — each one a separate TLH opportunity — while the *portfolio overall* tracks the market. You harvest the individual losers, immediately reinvest in the winners (no wash sale since they're different stocks), and the net exposure barely moves.

**The math**: A $500k direct index typically generates $15–40k in harvestable losses per year even in flat markets, because stocks move in opposite directions. ETF investors get zero of this.

## Which function to use — read this first

There are three distinct tasks, each with its own function. Use the right one; do not write your own implementation of any of these.

| Question the user is asking | Function to use | What you write |
|---|---|---|
| "What would I have made with direct indexing + TLH in 2025?" | `simulate_direct_index` | Just call it, plot the result |
| "What should I harvest in my portfolio right now?" | `build_tlh_plan` from `tlh_engine.py` | Glue: pass user's lots and wash sale log |
| "Is this specific harvest worth doing?" | `score_harvest_opportunity` from `tlh_engine.py` | Glue: pass dollar loss, correlation, vol |
| "Build me a direct index portfolio" | `build_direct_index` | Glue: call it, then place orders via Alpaca |

**What the libraries handle — do not reimplement these:**
- Portfolio weighting (`build_direct_index`): exact ETF weights, historical prices at start date, fractional shares
- Portfolio simulation (`simulate_direct_index`): daily P&L, TLH scan loop, cost basis tracking, tax savings accumulation
- Harvest decision (`build_tlh_plan`): HIFO lot selection, ST/LT prioritization, substitute correlation, wash sale windows, EV scoring
- Single opportunity scoring (`score_harvest_opportunity`): tracking error cost, break-even days, deferral NPV

**What you do write** (glue code only):
- Formatting the user's broker positions into `TaxLot` objects for `build_tlh_plan`
- Choosing parameters (`tax_rate_st`, `harvest_threshold_pct`, etc.) based on what the user told you
- Plotting the output of `simulate_direct_index` (exact chart code is in the section below)
- Printing harvest plan results in a readable table

## When to Suggest Direct Indexing

- User asks about building a custom index or "owning the stocks in an ETF"
- User has $50k+ to invest in a single ETF (smaller amounts → too many tiny positions)
- User is in a high tax bracket (32%+) and cares about after-tax returns
- User wants to exclude specific companies (ESG, employer stock concentration, etc.)
- User already does TLH on ETFs but wants to go further
- User says "I want to own the S&P 500 but smarter"

## Core Idea: Direct Indexing + TLH Loop

```
1. Buy all N stocks in SPY/QQQ/VTI proportional to their index weight
2. Every week / after market drops: scan for losers
3. Sell the losers → harvest the loss (tax deduction now)
4. Immediately buy the next-most-correlated stock (different company = no wash sale)
5. Portfolio still tracks the index, but you've banked tax savings
6. After 31 days, optionally rotate back to original holding
```

This is why the two skills belong together: **direct indexing creates the TLH opportunities; TLH is how you monetize them**.

## Step 1: Get ETF Constituents

```python
from skills.direct_indexing.scripts.etf_constituents import get_etf_holdings, get_etf_info

# Get all holdings with weights
holdings = get_etf_holdings('SPY')
# [{'asset': 'AAPL', 'weightPercentage': 7.12, 'name': 'Apple Inc', ...}, ...]

# Get ETF profile
info = get_etf_info('SPY')
print(f"Expense ratio: {info.get('expenseRatio')}%")
```

Holdings include: `asset` (ticker), `name`, `weightPercentage`, `sharesNumber`, `marketValue`.

## Step 2: Build the Direct Index Portfolio

```python
from skills.direct_indexing.scripts.build_portfolio import build_direct_index

# For live portfolio construction — uses today's prices
result = build_direct_index('QQQ', capital=100_000)

# For historical analysis — ALWAYS pass as_of_date
# This prices every constituent at what they actually cost on that date
result = build_direct_index('QQQ', capital=100_000, as_of_date='2025-01-02')

print(f"Holdings: {result['n_holdings']}")
print(f"Coverage: {result['coverage_pct']:.2f}% of ETF weight")  # should be 99%+
print(f"Priced as of: {result['as_of_date']}")
print(f"Deployed: ${result['deployed_capital']:,.2f}")
print(f"Cash:     ${result['cash_remainder']:,.2f}")  # rounding residue only

for pos in result['positions'][:10]:
    print(f"  {pos['symbol']:6s}  {pos['etf_weight_pct']:5.2f}%  "
          f"{pos['shares']:4d} shares @ ${pos['price']:7.2f}  = ${pos['actual_value']:,.0f}")
```

The function holds every constituent at its **true ETF weight** — no trimming, no renormalization.
`cash_remainder` is only rounding residue from converting dollar allocations to whole shares.
`coverage_pct` must be ≥ 99% for the portfolio to faithfully track the ETF.

**`as_of_date` is mandatory for any historical comparison.** If you build the portfolio with
today's prices and then apply 2025 historical returns, the initial share counts are wrong —
a stock that was $100 in Jan 2025 and is $150 today would be allocated 33% fewer shares,
completely distorting the simulation. Always pass the first trading day of the analysis period.

**There is no `top_n` parameter.** Partial replication is not direct indexing — it's a concentrated
bet with different exposure. If you only buy the top 50 stocks of QQQ and renormalize their weights,
the smaller ones (0.5% of QQQ) become 0.57% of your portfolio. In a year where those mid-tier
names return 150%+, your "direct index" wildly outperforms QQQ before TLH — which makes the TLH
comparison meaningless. The only source of outperformance should be TLH alpha.

## Step 3: Executing the Portfolio

Use the Alpaca skill to place the orders:

```python
from skills.alpaca.scripts.trading import place_order

# Place each position (paper first to verify)
for pos in result['positions']:
    order = place_order(
        symbol=pos['symbol'],
        qty=pos['shares'],
        side='buy',
        paper=True,  # switch to False for live
    )
    print(f"  {pos['symbol']}: {order['status']}")
```

**Important ordering tip**: Buy smallest positions first to preserve cash for the large-cap positions, which have less rounding error but larger dollar amounts.

## Answering "what if I had direct indexed instead of holding QQQ?" — use simulate_direct_index

**NEVER write your own portfolio simulation code for this question.** The correct implementation
requires: historical prices at the start date (not today), exact ETF weights (not renormalized),
and TLH savings applied incrementally (not a flat line). Getting any one of these wrong produces
a chart that looks plausible but is completely wrong. Use this instead:

```python
from skills.direct_indexing.scripts.simulate import simulate_direct_index

result = simulate_direct_index(
    etf_symbol='QQQ',
    capital=100_000,
    start_date='2025-01-02',   # first trading day of the year
    end_date='2025-12-31',
    harvest_threshold_pct=3.0, # harvest losses > 3% below cost basis
    tax_rate_st=0.37,           # short-term rate (adjust for state taxes)
    tax_rate_lt=0.238,          # long-term rate
    harvest_frequency_days=30,  # scan monthly
)

# Always print the summary and check tracking error first
print(result['summary'])
# simulate_direct_index uses fractional shares — industry standard tracking is < 0.5%.
# The function errors out above 0.5%. If you got a result, tracking is within bounds.
# The direct index will drift slightly ABOVE the ETF over time (no expense ratio) — correct.
print(f"Tracking error: {result['tracking_error_pct']:.2f}%")  # expect 0.1–0.3%

# Build the chart — three lines, all starting at capital on day 1
import pandas as pd
import matplotlib.pyplot as plt

plt.rcParams['font.size'] = 14
fig, ax = plt.subplots(figsize=(13, 6))

df = pd.DataFrame({
    'date': pd.to_datetime(result['dates']),
    'QQQ Buy & Hold': result['etf_values'],
    'Direct Index (no TLH)': result['direct_index_values'],
    'Direct Index + TLH': result['tlh_values'],
}).set_index('date')

ax.plot(df.index, df['QQQ Buy & Hold'], color='steelblue', linewidth=2, label='QQQ Buy & Hold')
ax.plot(df.index, df['Direct Index (no TLH)'], color='gray', linestyle='--', linewidth=1.5,
        label='Direct Index (no TLH)')
ax.plot(df.index, df['Direct Index + TLH'], color='green', linewidth=2.5,
        label=f"Direct Index + TLH (+${result['total_tax_savings']:,.0f})")

# Shade the TLH alpha region between lines 2 and 3
ax.fill_between(df.index, df['Direct Index (no TLH)'], df['Direct Index + TLH'],
                alpha=0.2, color='green', label='TLH Alpha')

ax.axhline(100_000, color='gray', linestyle=':', alpha=0.5, label='Starting Capital')
ax.set_xlabel('Date')
ax.set_ylabel('Portfolio Value ($)')
ax.set_title(f'Direct Indexing QQQ with TLH — 2025\n'
             f'TLH savings: ${result["total_tax_savings"]:,.0f} from {len(result["harvest_events"])} harvests')
ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f'${x:,.0f}'))
ax.legend()
plt.tight_layout()
plt.savefig('direct_index_comparison.png', dpi=150, bbox_inches='tight')
```

**What the three lines must show:**
- Line 1 (QQQ) and line 2 (Direct Index, no TLH): nearly identical throughout the year.
  If they diverge by more than ~0.5%, the simulation is wrong — `result['tracking_error_pct']`
  will tell you. Do not present the chart if this check fails.
- Line 3 (Direct Index + TLH): starts at the same value as line 2 on day 1, then steps up
  slightly at each harvest event. It ends above line 2 by exactly `total_tax_savings`.
  It must NOT be a flat horizontal line, and must NOT start above lines 1 and 2.

**Print the harvest events table:**
```python
import pandas as pd
events_df = pd.DataFrame(result['harvest_events'])
if not events_df.empty:
    print(events_df.sort_values('tax_savings', ascending=False).head(10).to_string(index=False))
print(f"\nTotal losses harvested: ${result['total_losses_harvested']:,.0f}")
print(f"Total tax savings: ${result['total_tax_savings']:,.0f}")
print(f"Coverage: {result['coverage_pct']:.1f}% of {etf_symbol} weight")
```

## Step 4: Ongoing TLH Harvesting (the profit engine)

Use `tlh_engine.py` for professional-grade harvesting with HIFO lot selection, correlation-
based substitute finding, and wash sale window tracking.

### Quickstart

```python
from skills.direct_indexing.scripts.tlh_engine import (
    TaxLot, lots_from_positions, build_tlh_plan
)
from skills.direct_indexing.scripts.etf_constituents import get_etf_holdings
from datetime import date

# Option A: Build TaxLot objects from broker positions
# (pass per-lot data for HIFO accuracy; aggregate positions work too)
raw_positions = [
    {
        'symbol': 'ADBE',
        'shares': 10,
        'cost_basis_per_share': 580.00,
        'current_price': 425.00,
        'purchase_date': '2025-01-15',   # needed for ST vs LT classification
    },
    {
        'symbol': 'PYPL',
        'shares': 25,
        'cost_basis_per_share': 85.00,
        'current_price': 62.00,
        'purchase_date': '2024-11-01',
    },
    # ... all portfolio lots
]

lots = lots_from_positions(raw_positions)

# Option B: Manually construct TaxLot objects for full control
from datetime import date
lot = TaxLot(
    symbol='ADBE',
    shares=10,
    cost_basis_per_share=580.00,
    purchase_date=date(2025, 1, 15),
    current_price=425.00,
)

# Wash sale log: sales made in the last 31 days that should block re-purchase
wash_sale_log = [
    {'symbol': 'ADBE', 'sale_date': '2026-03-15', 'was_loss': True},
]

# ETF holdings: pass all constituents so the engine prefers in-index substitutes
etf_holdings = get_etf_holdings('QQQ')  # all ~100 QQQ holdings

# Run the TLH plan
plan = build_tlh_plan(
    lots=lots,
    wash_sale_log=wash_sale_log,
    etf_holdings=etf_holdings,
    threshold_loss_pct=3.0,    # only harvest if 3%+ below cost basis
    min_dollar_loss=100.0,      # ignore losses < $100
    tax_rate_st=0.37,           # 37% federal short-term rate
    tax_rate_lt=0.238,          # 23.8% long-term (20% + 3.8% NIIT)
    min_correlation=0.85,       # substitute must have R ≥ 0.85 with sold stock
)

print(plan['summary'])
for opp in plan['harvest_opportunities']:
    print(f"\n{opp['symbol']} ({opp['term']})")
    print(f"  Loss: ${opp['dollar_loss']:,.0f} ({opp['loss_pct']:.1f}%)")
    print(f"  Tax savings: ${opp['estimated_tax_savings']:,.0f}")
    print(f"  Substitute: {opp['substitute']['symbol']} — {opp['substitute']['reason']}")
    print(f"  Safe to repurchase: {opp['safe_repurchase_date']}")
    print(f"  Action: {opp['action']}")
```

### TLH Parameters — When to Adjust

| Parameter | Conservative | Moderate (default) | Aggressive |
|---|---|---|---|
| `threshold_loss_pct` | 5% | 3% | 1–2% |
| `min_dollar_loss` | $500 | $100 | $25 |
| `min_correlation` | 0.92 | 0.85 | 0.75 |
| Monitoring frequency | Monthly | Weekly | Daily |

**When to use aggressive settings:** High-volatility markets (2022, Q1 2025 tariff selloff).
Every additional 1% of loss threshold you cross means more opportunities at cost of more turnover.

**When to use conservative settings:** Low-volatility bull markets where opportunity cost of
being out of a position (tracking error during the 31-day hold) may exceed the tax benefit.

### How Substitute Selection Works

1. **Mega-cap stocks** (AAPL, MSFT, NVDA, AMZN, META, GOOGL, TSLA, NFLX): automatically uses
   the sector ETF (XLK, XLC, etc.) — no single peer can replicate a 5–10% index weight.

2. **All other stocks**: fetches FMP peers, filters out wash-sale-blocked tickers, then
   picks the peer with the highest 90-day return correlation (R ≥ 0.85).
   - In-index peers (also held in the ETF) are preferred — they maintain index exposure better.
   - If no peer clears the correlation bar, falls back to the sector ETF with a warning.

3. **Correlation threshold** (0.85 default): professional platforms target 0.90–0.95.
   Below 0.80 means the substitute may diverge meaningfully during the 31-day hold — only
   accept if the tax savings clearly exceed the expected tracking error cost.

### Wash Sale Rules — Critical

**The 61-day window**: Do NOT buy back the sold security within 30 days before OR 30 days
after the sale. The engine enforces 31 days post-sale (safe side of the 30-day rule).

**DRIP (Dividend Reinvestment) trap**: If a stock pays a dividend during the 31-day window and
auto-reinvests, it triggers a wash sale and disallows the loss. Disable auto-DRIP on
any harvested position for 31 days post-sale.

**Cross-account contamination**: A spouse's IRA or your own 401(k) auto-reinvesting in the
same stock also triggers a wash sale. The wash sale rule is household-wide.

**GOOGL vs GOOG**: The IRS treats dual share classes of the same company as substantially
identical — swapping between them is a wash sale.

### HIFO Lot Selection

The engine sells lots in this priority order (maximizes tax value per dollar of loss):
1. **Short-term losses first** — taxed at ordinary income rates (up to 37%), vs 23.8% LT.
   The 13–17 percentage point rate differential makes ST losses ~1.5x more valuable.
2. **Within short-term**: highest cost basis first (largest absolute loss)
3. **Long-term losses**: same ordering, after all ST losses exhausted
4. **Gains**: never sold (only sells losses)

### Expected Value Scoring (what no platform shows you)

Every opportunity is scored with:
- **Tax savings** = dollar loss × applicable tax rate
- **Tracking error cost** = expected dollar divergence of substitute vs original over 31 days,
  computed from the correlation and the stock's volatility
- **Net expected value** = tax savings − tracking error cost
- **Break-even hold days** = minimum hold where EV turns positive (should be < 31 days)
- **Deferral benefit** = future value of reinvesting the tax savings over 10 years

Results are bucketed into three tiers:
- `HARVEST` — net EV ≥ 50% of tax savings (clear win)
- `BORDERLINE` — positive but thin EV (harvest only if substitute is liquid)
- `SKIP` — tracking error cost exceeds tax savings (wait for bigger loss or better substitute)

```python
from skills.direct_indexing.scripts.tlh_engine import score_harvest_opportunity

score = score_harvest_opportunity(
    dollar_loss=1550,
    tax_rate=0.37,          # short-term rate
    substitute_correlation=0.91,
    annualized_volatility=0.30,   # 30% vol stock like ADBE
    hold_days=31,
    years_until_liquidation=10,
)
# → {'tax_savings': 573.50, 'tracking_error_cost': 82.40,
#    'net_expected_value': 491.10, 'deferral_benefit_10yr': 982.43,
#    'break_even_hold_days': 4, 'recommendation': 'HARVEST',
#    'explanation': 'Strong opportunity. Tax savings $574 far exceed...'}
```

### IRS Loss Netting Order (what the losses offset)

The IRS mandates this sequence — you cannot choose:
1. ST losses → offset ST gains first
2. LT losses → offset LT gains first
3. Excess losses of either type can then offset gains of the other type
4. Net losses beyond all capital gains → deductible against ordinary income up to **$3,000/year**
5. Everything remaining carries forward indefinitely with no expiration

**Critical implication**: if you have a lot of ST gains from active trading elsewhere, a single
ST loss from TLH offsets income taxed at 37%+ — nearly 1.6× more valuable than a LT loss
against LT gains. Always ask what kind of gains the user has before recommending which lots to harvest.

### Loss Carry-Forward: a real financial asset, not a consolation prize

Unused harvested losses carry forward every year until used. A user who says "I don't have
gains this year so TLH is pointless" is wrong in a meaningful way:

- They are pre-loading a tax asset they can deploy against future gains (selling a house,
  RSU vesting, business sale, inheritance)
- Carry-forwards have no expiration and transfer to future tax years automatically
- A $50,000 carry-forward at 23.8% LT rate = $11,900 of future tax liability erased
- When modeling TLH value for a user, always include their existing carry-forward balance
  if they know it — it changes whether to prioritize ST vs LT harvesting this year

### Real tax rates: always clarify federal vs. total

The engine defaults to federal-only rates (37% ST, 23.8% LT). Users in high-tax states
pay significantly more:

| State | ST addition | LT addition | Total ST rate | Total LT rate |
|---|---|---|---|---|
| California | +13.3% | +13.3% | ~50.3% | ~37.1% |
| New York City | +10.9% | +10.9% | ~47.9% | ~34.7% |
| Texas / Florida / Nevada | +0% | +0% | ~40.8% | ~23.8% |
| Oregon | +9.9% | +9.9% | ~46.9% | ~33.7% |

In California, a $10,000 ST loss is worth $5,030 in saved taxes — not $3,700. Always ask
the user's state before presenting tax savings estimates. Pass the correct combined rate to
`build_tlh_plan(tax_rate_st=0.503, tax_rate_lt=0.371)` for accurate numbers.

### Specific identification election — do this first or HIFO means nothing

HIFO lot selection only works if your broker knows which lots you're selling. By default,
the IRS assigns FIFO (oldest shares first) unless you make a **specific identification election**
at or before the time of sale.

**What this means in practice:**
- At Alpaca, Schwab, Fidelity: you designate specific lots when placing the sell order
- At brokers that don't support lot-level designation, HIFO is impossible — FIFO is forced
- If you forget to designate before the trade settles, you cannot retroactively change it
- Some platforms require calling in or using a specific interface to elect specific ID

**Always confirm**: before running any TLH, verify the broker supports specific ID lot
designation and that the user has it enabled on their account.

### The wash sale window is 61 days total — the 30-day BEFORE matters too

Most people focus on the 30 days after a sale. The 30 days before is equally enforced.

**The DCA trap**: If a user buys 10 more shares of ADBE on Feb 1 (adding to their position),
then sells their original ADBE shares at a loss on Feb 20 — the Feb 1 purchase is within the
30-day pre-sale window. The wash sale rule disallows the loss on 10 shares (matched against
the new purchase). The remaining shares can still be harvested.

**Implication for the engine**: before executing a TLH sale, check whether the user bought
any shares of that same security in the 30 days before today. If they did, only the shares
*not* matched against recent purchases are harvestable. Add recent purchases to the wash sale
log with `was_loss: False` to track this correctly:

```python
# Flag recent purchases so the engine can detect pre-sale window violations
wash_sale_log.append({
    'symbol': 'ADBE',
    'sale_date': '2026-03-01',   # date of the purchase (used as reference point)
    'was_loss': False,            # it was a buy, not a loss sale
    'type': 'purchase',          # informational
})
```

The engine's `is_in_wash_sale_window` checks the 30-day post-sale window. Pre-sale window
checks require the caller to filter lots purchased within 30 days of the proposed sale date.

### How to correctly visualize "QQQ vs Direct Index + TLH" — chart construction rules

This comparison comes up often. Getting it wrong produces charts that are misleading or nonsensical.
Follow these rules exactly.

**The three lines:**
1. **QQQ buy & hold** — normalize QQQ's daily close prices to the starting capital. This is the baseline.
2. **Direct index (no TLH)** — apply each constituent's daily return to its initial dollar allocation
   (capital × etf_weight_pct / 100), sum across all positions each day. With correct weights this
   line should be nearly indistinguishable from QQQ (within ~0.2%). If it diverges significantly,
   the weights are wrong.
3. **Direct index + TLH** — same as line 2, but on each harvest date add the cumulative tax savings
   to the portfolio value. Tax savings accumulate over time — each harvest event adds an increment.
   The line starts at the same value as line 2, then pulls ahead incrementally as harvests occur.

**The critical mistake the previous chart made:**
The "Direct Index + TLH" line was drawn as a flat horizontal line at the *final* value ($194k),
applied from January 1. This is wrong. The TLH benefit is not known on day 1 — it accumulates
event by event. The correct line starts identical to the direct index line and steps up slightly
each time a harvest occurs. By year end it sits above the direct index line by the total tax savings.

**Correct construction in pseudocode:**
```python
import pandas as pd

START = '2025-01-02'   # first trading day of analysis period
END   = '2025-12-31'

# --- Line 1: QQQ ---
qqq_prices = get_historical_prices('QQQ', from_date=START, to_date=END)
qqq_df = pd.DataFrame(qqq_prices['prices']).sort_values('date')
qqq_df['portfolio_value'] = capital * (qqq_df['close'] / qqq_df['close'].iloc[0])

# --- Line 2: Direct index (no TLH) ---
# Build portfolio at START date prices — this is what you actually would have bought.
# Do NOT use today's prices for a historical simulation.
portfolio = build_direct_index('QQQ', capital=capital, as_of_date=START)
constituent_values = []
for pos in portfolio['positions']:
    hist = get_historical_prices(pos['symbol'], from_date='2025-01-02', to_date='2025-12-31')
    prices = pd.DataFrame(hist['prices']).sort_values('date').set_index('date')['close']
    initial_alloc = pos['actual_value']     # dollars invested on day 1
    daily_value = initial_alloc * (prices / prices.iloc[0])
    constituent_values.append(daily_value)

direct_index_df = pd.concat(constituent_values, axis=1).sum(axis=1).reset_index()
direct_index_df.columns = ['date', 'portfolio_value']

# --- Line 3: Direct index + TLH ---
# Start from the direct index values, then add cumulative tax savings at each harvest event.
# harvest_events = [(date, tax_savings_dollars), ...] — sorted by date
tlh_df = direct_index_df.copy()
cumulative_savings = 0
for event_date, savings in harvest_events:
    cumulative_savings += savings
    tlh_df.loc[tlh_df['date'] >= event_date, 'portfolio_value'] += savings
# Note: reinvest the savings (they compound) — simplest approximation is to add them
# to the portfolio value on the harvest date and let the subsequent returns apply.
```

**Sanity checks before presenting the chart:**
- Line 1 and line 2 should be nearly identical at every point (divergence < 1% is acceptable)
- Line 3 should start at the same value as line 2 on day 1 — NOT at the final value
- Line 3 should only pull away from line 2 at moments when harvests occur (stepwise increments)
- The final gap between line 2 and line 3 = total tax savings; confirm it matches the harvest log

## Step 5: Rebalancing

Direct indexes drift as stocks move. Rebalance quarterly or after 5%+ weight drift:

```python
# diff_direct_index returns buys, sells, holds
rebalance = diff_direct_index('QQQ', capital=500_000, current_positions=current)

print(f"Buys needed:  {len(rebalance['buys'])}")
print(f"Sells needed: {len(rebalance['sells'])}")
print(f"No change:    {len(rebalance['holds'])}")

# Rebalancing sells that are also at a loss = free TLH (you'd sell anyway)
free_tlh = rebalance['tlh_candidates']

# Sells needed for rebalancing that are at a gain — minimize or defer these
trim_sells = [s for s in rebalance['sells'] if s not in rebalance['tlh_candidates']]
```

**Always harvest before rebalancing.** Rebalancing sells are free TLH opportunities — you
are selling regardless. Harvesting first avoids realizing gains you'd otherwise defer.

**Index reconstitution edge case**: when a stock is added back to the index after you
harvested it, the engine may want to buy it before the 31-day window is up. Check the wash
sale log before executing any index-driven rebalance purchase — buying back a recently
harvested stock at a loss re-triggers the disallowance.

## Common ETFs to Direct Index

| ETF | Index | Holdings | Min Capital (lite) |
|-----|-------|----------|-------------------|
| **SPY** / **IVV** / **VOO** | S&P 500 | ~503 | $25k (top 50) |
| **QQQ** | Nasdaq-100 | 100 | $20k (top 40) |
| **VTI** | CRSP Total Market | ~3,600 | $50k (top 100) |
| **IWM** | Russell 2000 | ~2,000 | Not recommended (too many tiny stocks) |
| **XLK** | S&P Tech Select | ~65 | $15k (full replication feasible) |
| **VGT** | MSCI IT | ~300 | $30k (top 50) |

## TLH Alpha by Market Regime — Setting Real Expectations

TLH yield is not constant. It depends heavily on market conditions and account age.
Use these benchmarks (sourced from Wealthfront's published client data) when setting expectations:

| Market regime | Annual TLH yield | Example years |
|---|---|---|
| Strong bull, low dispersion | 0.5%–1.5% | 2013–2017 (2.5–3% early, decays) |
| Choppy / sideways, high dispersion | 2%–4% | Most "normal" years |
| Bear market or high volatility | 4%–8% | 2022 (6.4%), 2025 tariff selloff (7.9%) |
| COVID-style crash + recovery | 5%–6% | 2020 (5.9%) |

**The yield decay effect**: TLH alpha is highest in years 1–3 of an account's life, when
many lots have a purchase price close to current price. As positions appreciate over years,
fewer lots sit near or below cost basis. A 10-year-old account harvests less than a new one
with the same balance. This is why Wealthfront shows "vintage" cohorts — newer accounts
always show higher yields.

**Practical guidance**:
- Year 1–3: expect 2–4× the steady-state yield; aggressively harvest anything above threshold
- Year 5+: focus on new cash flows (each new purchase is a fresh lot at current price → new
  TLH opportunity) and volatile individual names rather than the whole portfolio
- High-bracket users in high-tax states: even 0.5% annual yield on $500k = $2,500/yr saved,
  compounding for decades — still worth running

## Key Rules and Caveats

1. **Elect specific identification first.** Before any TLH trade, confirm your broker supports
   lot-level designation and the user has it enabled. HIFO is impossible without it.

2. **Taxable accounts only.** IRAs, 401(k)s, and HSAs have no capital gains — TLH provides
   zero benefit there. The capital tied up in these accounts cannot be directly indexed for TLH.

3. **Wash sale is household-wide.** Selling AAPL at a loss in a taxable account while a spouse's
   IRA auto-DRIPs into AAPL disallows the loss. The 61-day window applies across all accounts
   with the same tax filing status.

4. **Minimum capital: $50k.** Below this, position sizes become too small to generate meaningful
   losses worth harvesting, and tracking error from rounding to whole shares becomes material.
   Exception: brokers with fractional shares lower this to ~$20k for lite (top 30) portfolios.

5. **Tracking error is real.** Top-50 lite index: 2–5% annualized vs. full ETF.
   Full replication (500 stocks): < 0.5%. Harvesting increases tracking error temporarily —
   the 31-day substitute period adds idiosyncratic risk that can work for or against you.

6. **Dividends need active management.** Disable auto-DRIP on any harvested position for
   31 days. Reinvestment of even a small dividend into the sold stock triggers a wash sale
   on that lot and can disallow thousands in losses from a $40 dividend.

7. **State taxes can double the benefit.** In California or New York, the combined ST rate
   exceeds 50%. Always use state-adjusted rates in `build_tlh_plan` — federal-only rates
   dramatically understate the value for users in high-tax states.
