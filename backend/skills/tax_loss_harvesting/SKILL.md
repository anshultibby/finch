---
name: tax_loss_harvesting
description: "Identify TLH candidates from a live portfolio. Entry point: build_tlh_plan() — pass lots from SnapTrade positions and it returns ranked harvest opportunities with correlation-selected substitutes, wash-sale guards, and net-EV scoring. Do NOT implement your own substitute selection or correlation logic."
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

Do NOT:
- Write your own correlation computation
- Implement your own substitute selection (same sector, similar beta, etc.)
- Manually score harvest opportunities
- Use `yfinance` or raw price fetches

All of that is already done. Use the functions below.

---

## Primary entry point — `build_tlh_plan`

```python
from skills.snaptrade.scripts.account.get_positions import get_positions
from skills.direct_indexing.scripts.tlh_engine import TaxLot, lots_from_positions, build_tlh_plan
from skills.financial_modeling_prep.scripts.etf.holdings import get_etf_holdings

# 1. Pull live positions from broker (SnapTrade)
positions = await get_positions(user_id, account_id)

# 2. Convert to TaxLot objects
lots = lots_from_positions(positions)

# 3. Get ETF universe for substitute selection
#    Use QQQ for tech-heavy portfolios, SPY for broad portfolios
etf_holdings = get_etf_holdings('QQQ')

# 4. Run the plan — substitute selection uses sector peers + correlation, not qualitative matching
plan = build_tlh_plan(
    lots=lots,
    wash_sale_log=[],        # [{symbol, sale_date, was_loss}] from prior transactions
    etf_holdings=etf_holdings,
    threshold_loss_pct=3.0,
    min_dollar_loss=200.0,
    tax_rate_st=0.37,        # ask user for their state — CA=0.503, NYC=0.479
    tax_rate_lt=0.238,
    min_correlation=0.85,    # substitutes below this are market bets, not hedges
)

print(plan['summary'])
for opp in plan['harvest_now']:
    sub = opp['substitute']
    print(f"{opp['symbol']} → {sub['symbol']} (R={sub['correlation']:.2f}, pool={sub['search_pool']}): "
          f"${opp['estimated_tax_savings']:,.0f} saved | EV=${opp['scoring']['net_expected_value']:,.0f}")
```

**How substitute selection works inside `build_tlh_plan`:**
1. Fetches FMP sector peers for the harvested stock (same sector, exchange, market cap)
2. Intersects with the ETF universe (substitutes must be in the index)
3. Computes 120-day adjClose return correlations for all candidates
4. Picks highest-correlated sector peer that clears `min_correlation`
5. Falls back to full ETF universe only if no sector peer clears the threshold
6. Reports `search_pool: 'sector_peers'` or `'universe'` so you know which path was taken

**Output fields per opportunity:**
- `symbol` — stock being harvested
- `substitute.symbol` — replacement to buy
- `substitute.correlation` — R between sold and substitute (must be ≥ min_correlation)
- `substitute.search_pool` — `'sector_peers'` or `'universe'` or `'sector_peers+universe'`
- `estimated_tax_savings` — dollar tax benefit
- `scoring.net_expected_value` — tax savings minus expected tracking error cost
- `scoring.recommendation` — `'HARVEST'` | `'BORDERLINE'` | `'SKIP'`
- `safe_repurchase_date` — earliest date to buy back original (31 days from today)

---

## Tax rates — always ask the user's state

| State | Short-term | Long-term |
|---|---|---|
| Federal only | 37.0% | 23.8% |
| California | 50.3% | 37.1% |
| New York City | 47.9% | 34.7% |
| Texas / Florida | 37.0% | 23.8% |

---

## Wash sale rules

- 61-day window: 30 days before sale + sale day + 30 days after
- Block list is in `wash_sale_log` — include prior loss sales from the broker history
- `build_tlh_plan` enforces cross-opportunity conflicts automatically:
  a stock assigned as a substitute cannot also be harvested in the same plan
- **Share classes of the same company are substantially identical** — GOOGL↔GOOG,
  BRK.A↔BRK.B swaps are blocked

---

## For historical simulation / backtesting

Use `direct_indexing` skill instead:
```python
from skills.direct_indexing.scripts.model import run_direct_index_model
result = run_direct_index_model('QQQ', capital=500_000, start_date='2024-01-02', end_date='2024-12-31',
                                tax_rate_st=0.503, tax_rate_lt=0.371)
print(result['summary'])
```
`tax_loss_harvesting` skill is for **live portfolios** (what to harvest today).
`direct_indexing` skill is for **historical backtests** (what TLH would have produced).
