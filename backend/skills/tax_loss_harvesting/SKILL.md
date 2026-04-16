---
name: tax_loss_harvesting
description: "Institutional-grade TLH function library. Call individual functions for targeted analysis, or build_tlh_plan() for a full plan. Covers: wash sale lookback check, substitute risk classification, known ETF pairs, netting order analysis, full tax alpha (immediate + deferral NPV + bracket arbitrage), and ranked harvest plans."
metadata:
  emoji: "📉"
  category: finance
  is_system: true
  auto_on: true
  requires:
    env: []
    bins: []
---

# Tax Loss Harvesting Skill

## ⛔ STOP — do not implement your own logic

Do NOT write your own correlation logic, substitute selection, wash sale checks,
or tax savings calculations. All of that is done below. Pick the right function.

---

## Quick-reference: which function to call

| Question | Function |
|---|---|
| "Scan my portfolio for losses" | `build_tlh_plan()` |
| "What are my options for replacing NVDA?" | `find_substitute_candidates()` ← ranked list |
| "Just pick one substitute automatically" | `find_best_correlated_substitute()` |
| "Did I buy this recently? Can I sell it?" | `check_wash_sale_lookback()` |
| "Is VOO → IVV a safe swap?" | `classify_substitute_risk()` |
| "What's a safe swap for QQQ?" | `get_known_substitutes()` |
| "Which losses save the most given my gains this year?" | `compute_netting_order()` |
| "How much would I actually save including deferral?" | `compute_tax_alpha()` |
| "Score this one opportunity" | `score_harvest_opportunity()` |
| "Historical backtest" | See `direct_indexing` skill |

---

## 1. `build_tlh_plan` — full ranked harvest plan

```python
from skills.direct_indexing.scripts.tlh_engine import (
    TaxLot, TaxProfile, lots_from_positions, build_tlh_plan
)
from skills.financial_modeling_prep.scripts.etf.holdings import get_etf_holdings

# Convert broker positions to TaxLot objects
lots = lots_from_positions(positions)  # positions from get_portfolio / SnapTrade

# ETF constituent universe for substitute selection
etf_holdings = get_etf_holdings('SPY')  # or 'QQQ' for tech-heavy portfolios

plan = build_tlh_plan(
    lots=lots,
    wash_sale_log=[],           # [{symbol, sale_date: 'YYYY-MM-DD', was_loss: True}]
    etf_holdings=etf_holdings,
    threshold_loss_pct=3.0,     # Frec/Betterment default; academic optimal is 10% (monthly cadence)
    min_dollar_loss=100.0,
    tax_rate_st=0.37,           # ALWAYS ask user their state — see rates table below
    tax_rate_lt=0.238,
    min_correlation=0.85,
)

print(plan['summary'])
for opp in plan['harvest_now']:
    sub = opp['substitute']
    print(f"{opp['symbol']} → {sub['symbol']} (R={sub['correlation']:.2f}): "
          f"${opp['estimated_tax_savings']:,.0f} saved | EV=${opp['scoring']['net_expected_value']:,.0f}")
```

**Output fields per opportunity:**
- `symbol` — stock being harvested
- `substitute.symbol` — replacement to buy immediately
- `substitute.correlation` — 120-day return correlation (must be ≥ min_correlation)
- `substitute.search_pool` — `'sector_peers'` | `'universe'`
- `estimated_tax_savings` — dollar tax benefit at stated rate
- `scoring.net_expected_value` — tax savings minus estimated tracking error cost
- `scoring.recommendation` — `'HARVEST'` | `'BORDERLINE'` | `'SKIP'`
- `safe_repurchase_date` — sell_date + 31 days (earliest to repurchase original)

**Cross-opportunity conflict protection:** a stock cannot be both sold (harvested)
AND used as a substitute in the same plan. `build_tlh_plan` enforces this automatically.

---

## 2. `find_substitute_candidates` — ranked list for agent reasoning

Call this when you need to reason about tradeoffs rather than auto-pick.
Returns the top-N candidates so you can factor in portfolio context:
user already holds the #1 pick, wants to avoid a sector, correlation is close between options, etc.

```python
from skills.direct_indexing.scripts.tlh_engine import find_substitute_candidates
from skills.financial_modeling_prep.scripts.etf.holdings import get_etf_holdings

etf_holdings = get_etf_holdings('SPY')
universe = [h['asset'] for h in etf_holdings if h.get('asset')]

candidates = find_substitute_candidates(
    sold_symbol='NVDA',
    universe=universe,
    wash_sale_log=[],
    min_correlation=0.80,
    top_n=5,
    existing_holdings=['MSFT', 'AAPL'],  # flag if user already holds any candidate
)

for c in candidates:
    print(f"{c['symbol']:6s}  R={c['correlation']:.3f}  "
          f"{'sector_peer' if c['is_sector_peer'] else 'universe':12s}  "
          f"{'⚠ already held' if c['already_held'] else ''}  "
          f"{'⚠ below threshold' if c['below_threshold'] else ''}  "
          f"wash_sale_risk={c['wash_sale_risk']}")
```

**Output per candidate:**
- `symbol` — ticker
- `correlation` — 120-day adjClose return correlation with sold_symbol
- `correlation_quality` — `STRONG` (≥0.85) / `GOOD` (≥0.70) / `WEAK` (≥0.40) / `POOR` (≥0.00) / `INVERSE` (<0.00)
- `is_sector_peer` — True if from FMP sector peers (tighter economic match)
- `below_threshold` — True if R < min_correlation (flagged, not excluded)
- `already_held` — True if in existing_holdings (concentration risk)
- `wash_sale_risk` — `SIMILAR_INDEX` / `SAME_INDEX` / `UNKNOWN`
- `wash_sale_safe` — bool

**Correlation quality guide:**
- `STRONG` (≥0.85): tight hedge, low tracking error — ideal
- `GOOD` (≥0.70): acceptable for most situations
- `WEAK` (≥0.40): loose hedge, tracking error risk — flag to user, let them decide
- `POOR` (<0.40): essentially uncorrelated — tracking error likely exceeds tax savings
- `INVERSE` (<0.00): moves against you during the hold — avoid in automated plans, but agent can surface if user wants to understand options

**Agent reasoning pattern:**
```
candidates = find_substitute_candidates('NVDA', universe, wash_sale_log, existing_holdings=current_positions)
# Filter to safe options (not already held, above threshold, no wash sale risk)
safe = [c for c in candidates if not c['already_held'] and not c['below_threshold'] and c['wash_sale_safe']]
# If user has a preference or constraint, apply it here before picking
best = safe[0] if safe else candidates[0]
```

---

## 3. `TaxProfile` — bundle user tax situation

```python
from skills.direct_indexing.scripts.tlh_engine import TaxProfile

# By state (combined federal + state rates)
profile = TaxProfile.for_state('california')
profile = TaxProfile.for_state('new_york_city', current_year_st_gains=15000)

# Custom rates
profile = TaxProfile(rate_st=0.37, rate_lt=0.238)

# With current-year context (for netting order analysis)
profile = TaxProfile.for_state('california',
    current_year_st_gains=12000,   # already realized ST gains this year
    current_year_lt_gains=5000,
    loss_carryforward_st=0,        # ST loss carryforward from prior years
    loss_carryforward_lt=3000,
)
```

**State rates (2025, combined federal + state + NIIT):**

| State | Short-term | Long-term |
|---|---|---|
| federal_only | 37.0% | 23.8% |
| california | 50.3% | 37.1% |
| new_york_city | 47.9% | 34.7% |
| new_york | 46.8% | 33.7% |
| texas / florida | 37.0% | 23.8% |
| illinois | 41.9% | 28.7% |
| massachusetts | 44.9% | 28.7% |
| oregon | 45.9% | 32.7% |

---

## 3. `check_wash_sale_lookback` — pre-sale trap check

The often-missed direction: if you bought shares in the 30 days BEFORE the sale,
the loss is disallowed. Most common with dollar-cost-averaging into falling positions.

```python
from skills.direct_indexing.scripts.tlh_engine import check_wash_sale_lookback

result = check_wash_sale_lookback(
    symbol='AAPL',
    purchase_history=[
        {'symbol': 'AAPL', 'purchase_date': '2026-03-15', 'shares': 5},
        {'symbol': 'AAPL', 'purchase_date': '2026-04-01', 'shares': 5},
    ],
    proposed_sale_date=date(2026, 4, 10),   # defaults to today
)

# {'has_lookback_risk': True,
#  'blocking_purchases': [{'purchase_date': '2026-03-15', 'shares': 5, 'days_before_sale': 26},
#                         {'purchase_date': '2026-04-01', 'shares': 5, 'days_before_sale': 9}],
#  'earliest_safe_sale_date': '2026-05-02',
#  'explanation': 'AAPL: 2 purchase(s) within the 30-day lookback window...'}
```

**Also applies to:** dividend reinvestment (DRIP) purchases. Disable DRIP before harvesting.

---

## 4. `classify_substitute_risk` — wash sale risk for a proposed swap

IRS has not ruled on ETF-to-ETF wash sales, but practitioner consensus treats
same-index/different-issuer ETFs as substantially identical. Use this before recommending a swap.

```python
from skills.direct_indexing.scripts.tlh_engine import classify_substitute_risk

# High risk — avoid
result = classify_substitute_risk('VOO', 'IVV')
# {'risk_level': 'SAME_INDEX', 'is_safe': False,
#  'reason': 'Both track S&P 500, different issuers',
#  'recommendation': 'AVOID — substantially identical risk...'}

# Safe
result = classify_substitute_risk('VOO', 'VTI')
# {'risk_level': 'SIMILAR_INDEX', 'is_safe': True,
#  'reason': 'S&P 500 vs. Total Market — materially different index (adds ~3,000 stocks)',
#  'recommendation': 'SAFE — standard institutional TLH pair'}

# Individual stocks — always safe (different corporations)
result = classify_substitute_risk('AAPL', 'MSFT')
# {'risk_level': 'UNKNOWN', 'is_safe': True, ...}
```

---

## 5. `get_known_substitutes` — pre-vetted ETF substitution pairs

```python
from skills.direct_indexing.scripts.tlh_engine import get_known_substitutes

subs = get_known_substitutes('QQQ')
# [{'sub': 'SCHG', 'risk': 'SIMILAR_INDEX', 'desc': 'Schwab Large-Cap Growth (Dow Jones)', 'typical_corr': 0.97},
#  {'sub': 'VGT',  'risk': 'SIMILAR_INDEX', 'desc': 'Vanguard IT sector ETF', 'typical_corr': 0.95},
#  {'sub': 'IWF',  'risk': 'SIMILAR_INDEX', 'desc': 'iShares Russell 1000 Growth', 'typical_corr': 0.97}]

subs = get_known_substitutes('SPY')
# [{'sub': 'VTI', ...}, {'sub': 'SCHB', ...}]

# Include risky pairs (for awareness, not recommendation)
subs = get_known_substitutes('VTI', exclude_risky=False)
```

**Returns empty list for individual stocks** — use `find_best_correlated_substitute()` instead.

**Key safe pairs to know:**
- `SPY / VOO / IVV` → `VTI` or `SCHB` (Total Market, different index)
- `QQQ` → `SCHG` or `VGT` or `IWF`
- `VEA / EFA` → `SCHF`
- `VWO / EEM` → `SCHE`
- `IWM` → `VB` or `SCHA`
- `VNQ` → `SCHH` or `USRT`

**Pairs to AVOID (same index, different issuer):**
`VOO ↔ IVV`, `VTI ↔ ITOT`, `QQQ ↔ QQQM`, `GLD ↔ IAU`, `VXUS ↔ IXUS`

---

## 6. `compute_netting_order` — rank by actual value given current-year gains

The IRS netting rules (§1222) mean losses aren't all equal in value:
- ST loss offsetting ST gain → highest value (full ST rate, ~40.8% max + bracket arbitrage)
- ST loss offsetting LT gain → lower (only LT rate ~23.8%, no bracket arb)
- LT loss offsetting ST gain → value-destroying (saves at LT rate on a ST gain)
- No gains → carryforward at character

```python
from skills.direct_indexing.scripts.tlh_engine import (
    TaxProfile, lots_from_positions, find_harvest_candidates, compute_netting_order
)

profile = TaxProfile.for_state('california',
    current_year_st_gains=18000,
    current_year_lt_gains=5000,
)

lots = lots_from_positions(positions)
candidates = find_harvest_candidates(lots, tax_rate_st=profile.rate_st, tax_rate_lt=profile.rate_lt)
ordered = compute_netting_order(candidates, profile)

for c in ordered:
    nc = c['netting_context']
    print(f"{c['symbol']}: ${nc['effective_tax_savings']:,.0f} effective savings "
          f"(bracket arb: ${nc['bracket_arbitrage']:,.0f}) — {nc['netting_explanation']}")
```

---

## 7. `compute_tax_alpha` — full institutional tax benefit

Three components:
1. **Immediate**: tax not paid this year
2. **Deferral NPV**: deferred tax compounds as reinvested capital
3. **Bracket arbitrage**: permanent gain from ST→LT rate differential (~17ppts max)

```python
from skills.direct_indexing.scripts.tlh_engine import TaxProfile, compute_tax_alpha

profile = TaxProfile.for_state('california', current_year_st_gains=15000)

alpha = compute_tax_alpha(
    dollar_loss=8000,
    tax_profile=profile,
    is_short_term=True,
    years_to_liquidation=10,
    annual_return=0.08,
)

# {
#   'immediate_benefit': 4024,        # 8000 × 50.3% CA ST rate
#   'deferral_npv': 1847,             # compounding benefit over 10yr
#   'bracket_arbitrage': 1064,        # 8000 × (50.3% − 37.1%) rate diff
#   'total_alpha': 6935,
#   'alpha_pct_of_loss': 86.7,        # 86.7% of the dollar loss is total value
#   'niit_component': 304,            # 3.8% NIIT breakout
#   'breakdown': {...}
# }
```

---

## 8. `score_harvest_opportunity` — net expected value for a single opportunity

```python
from skills.direct_indexing.scripts.tlh_engine import score_harvest_opportunity

score = score_harvest_opportunity(
    dollar_loss=3000,
    tax_rate=0.37,
    substitute_correlation=0.91,
    annualized_volatility=0.25,
    hold_days=31,
    years_until_liquidation=10,
)
# {'tax_savings': 1110, 'tracking_error_cost': 127, 'net_expected_value': 983,
#  'break_even_hold_days': 3, 'recommendation': 'HARVEST', 'explanation': '...'}
```

---

## Wash sale rules — always enforce these

| Rule | Detail |
|---|---|
| Lookback window | 30 days BEFORE sale (check with `check_wash_sale_lookback`) |
| Forward window | 30 days AFTER sale (enforced by `is_in_wash_sale_window`) |
| Total window | 61 days: 30 before + sale day + 30 after |
| Safe repurchase | 31+ days after sale (`wash_sale_safe_after`) |
| IRA contamination | Wash sale triggered by IRA purchase = **permanently lost** (can't add to IRA basis) |
| Dividend reinvestment | DRIP purchases count — disable DRIP before harvesting |
| Spouse's accounts | Wash sale applies across spouses filing separately |
| Options | Buying a call within 30 days of selling stock at a loss = wash sale |

**IRA contamination is the most dangerous edge case.** If a user has both a taxable
account and an IRA holding the same ETF, selling the taxable account at a loss while
the IRA holds (or buys within 30 days) the same ETF triggers a permanently lost loss —
not deferred, gone. The Betterment solution: use a 3rd-tier substitute ETF that
appears in neither account.

---

## Harvest threshold guidance

| Cadence | Optimal threshold | Source |
|---|---|---|
| Daily monitoring | 15% below cost basis | Israelov & Lu (2022, SSRN 4152425) |
| Monthly monitoring | 10% below cost basis | Israelov & Lu (2022) |
| ETF-level (robo) | 3–5% | Wealthfront/Betterment practice |

The academic optimal (10% monthly) balances harvesting yield vs. portfolio tracking error.
The default `threshold_loss_pct=3.0` in `build_tlh_plan` is aggressive — appropriate for
ETF-level portfolios with fewer positions. Adjust based on portfolio size and rebalancing goals.

---

## Year-end urgency

- Sale must settle by **December 31** for current-year tax impact
- Equities settle T+1: effective last harvest day = **December 30**
- October–December: proactively flag this deadline
- December purchases create a lookback trap for December 31 harvest — check with `check_wash_sale_lookback`
