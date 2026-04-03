---
name: portfolio_health_check
description: Analyze a user's portfolio for concentration risk, sector allocation, diversification gaps, fee drag, and rebalancing opportunities. Produces a concise diagnostic — not a lecture.
metadata:
  emoji: "🩺"
  category: finance
  is_system: true
  requires:
    env: []
    bins: []
---

# Portfolio Health Check Skill

Run a data-driven diagnostic on the user's portfolio. Surface what matters, skip what doesn't. **Only run when the user asks** — never volunteer a health check unprompted.

## Tone

- Lead with data, not opinions.
- Present findings as observations, not recommendations. "Your portfolio is 62% tech" — not "You should reduce your tech exposure."
- If something looks risky, flag it as a question: "Did you intentionally concentrate in tech, or did it drift there?"
- Keep the report to **one screen of text**. Users can ask to drill into any section.
- No disclaimers, no "consult a financial advisor" boilerplate unless they're about to act on something.

## How to Run

### Step 1: Pull Holdings

```python
from skills.snaptrade.scripts.portfolio.get_holdings import get_holdings
from skills.snaptrade.scripts.account.get_positions import get_positions

holdings = await get_holdings(user_id)
# Collect all positions across all taxable + tax-advantaged accounts
all_positions = []
for account in holdings.get("accounts", []):
    positions = await get_positions(user_id, account["id"])
    for p in positions:
        p["account_type"] = account.get("type", "unknown")  # taxable, ira, 401k, etc.
        p["account_name"] = account.get("name", "")
    all_positions.extend(positions)
```

### Step 2: Enrich with FMP

For each unique ticker, pull profile data to get sector, industry, market cap, and beta:

```python
from skills.financial_modeling_prep.scripts.company.profile import get_profile

profiles = {}
for symbol in set(p["symbol"] for p in all_positions):
    profile = get_profile(symbol=symbol)
    if profile and "error" not in profile:
        profiles[symbol] = profile
```

### Step 3: Compute the Diagnostics

Run ALL of these. Present only the ones that surface something interesting.

#### 3a. Concentration Check

```python
total_value = sum(p["market_value"] for p in all_positions)
by_position = sorted(all_positions, key=lambda p: p["market_value"], reverse=True)

# Flag any single position > 15% of portfolio
concentrated = [p for p in by_position if p["market_value"] / total_value > 0.15]

# Top 5 positions as % of total
top5_pct = sum(p["market_value"] for p in by_position[:5]) / total_value
```

**What to report:**
- Any position > 15%: "{SYMBOL} is {pct}% of your portfolio"
- If top 5 > 60%: "Your top 5 positions are {pct}% of the portfolio"
- Otherwise: skip this section entirely

#### 3b. Sector Allocation

```python
sector_totals = {}
for p in all_positions:
    profile = profiles.get(p["symbol"], {})
    sector = profile.get("sector", "Unknown")
    sector_totals[sector] = sector_totals.get(sector, 0) + p["market_value"]

sector_pcts = {s: v / total_value for s, v in sector_totals.items()}
```

**What to report:**
- Any sector > 40%: flag it
- Any sector at 0% that's typically in a diversified portfolio (Tech, Healthcare, Financials, Consumer, Industrials, Energy): mention the gap
- Show a simple bar: `Technology: ████████████ 52%  |  Healthcare: ███ 12%  | ...`
- If reasonably diversified (no sector >35%, at least 4 sectors): just say "Sector mix looks balanced" and show the bar

#### 3c. Risk Profile

```python
# Portfolio beta (weighted)
portfolio_beta = sum(
    (p["market_value"] / total_value) * (profiles.get(p["symbol"], {}).get("beta") or 1.0)
    for p in all_positions
)

# Count of positions
position_count = len(all_positions)
```

**What to report:**
- Portfolio beta: ">1.2 means you move more than the market, <0.8 means less"
- Position count: "<10 is concentrated, 10-30 is typical, >50 may be over-diversified"
- Only flag if beta > 1.3 or < 0.7 or position count < 5

#### 3d. Fee Audit (ETFs/Funds only)

For ETF positions, check if there's a cheaper alternative with similar exposure:

```python
# Common high-fee → low-fee swaps
FEE_SWAPS = {
    # Actively managed / high-fee → passive / low-fee
    "ARKK": ("VGT", "0.75% → 0.10%"),
    "ARKW": ("VGT", "0.75% → 0.10%"),
    "SPHD": ("SCHD", "0.30% → 0.06%"),
    "SPYD": ("SCHD", "0.07% → 0.06%"),
    "IEFA": ("VEA", "0.07% → 0.05%"),
    "GLD":  ("IAUM", "0.40% → 0.09%"),
    "SLV":  ("SIVR", "0.50% → 0.30%"),
    "HYG":  ("USHY", "0.49% → 0.15%"),
    "EMB":  ("VWOB", "0.39% → 0.20%"),
}

fee_flags = []
for p in all_positions:
    if p["symbol"] in FEE_SWAPS:
        alt, savings = FEE_SWAPS[p["symbol"]]
        fee_flags.append((p["symbol"], alt, savings, p["market_value"]))
```

**What to report:**
- Only mention if estimated annual fee savings > $50
- Format: "{SYMBOL} → {ALT} saves ~${annual_savings}/yr ({fee_diff})"
- If no fee issues: skip this section

#### 3e. Dividend Summary

```python
from skills.financial_modeling_prep.scripts.financials.key_metrics import get_key_metrics_ttm

total_annual_dividends = 0
for p in all_positions:
    ttm = get_key_metrics_ttm(symbol=p["symbol"])
    if ttm and isinstance(ttm, dict):
        div_yield = ttm.get("dividendYieldTTM") or 0
        annual_div = p["market_value"] * div_yield
        total_annual_dividends += annual_div

portfolio_yield = total_annual_dividends / total_value if total_value else 0
```

**What to report:**
- Portfolio yield and estimated annual income: "~${total}/yr ({yield}%)"
- Only show if user holds dividend-paying stocks
- Don't editorialize about whether the yield is "good" or "bad"

#### 3f. Unrealized Gains/Losses Summary

```python
total_unrealized = sum(p.get("unrealized_gain_loss", 0) for p in all_positions)
winners = [p for p in all_positions if p.get("unrealized_gain_loss", 0) > 0]
losers = [p for p in all_positions if p.get("unrealized_gain_loss", 0) < 0]
total_gains = sum(p["unrealized_gain_loss"] for p in winners)
total_losses = sum(p["unrealized_gain_loss"] for p in losers)
```

**What to report:**
- Net unrealized: "+${gains} in gains, -${losses} in losses"
- If losses > $500, add: "Run `cat /home/user/skills/tax_loss_harvesting/SKILL.md` for TLH analysis"
- Don't repeat the full TLH workflow here — just point to it

## Output Format

Keep it tight. One section per finding, skip sections with nothing interesting:

```
## Portfolio Health Check — {date}

**{position_count} positions | ${total_value:,.0f} total | Beta: {beta:.2f}**

### Concentration
- AAPL is 22% of your portfolio
- Top 5 positions = 64% of total

### Sectors
Technology:  ████████████ 52%
Healthcare:  ███         12%
Financials:  ███         11%
Energy:      ██           8%
Other:       ████        17%

### Fees
- ARKK → VGT saves ~$180/yr (0.75% → 0.10%)

### Income
- ~$2,400/yr estimated dividends (1.8% yield)

### Tax
- $3,200 in unrealized losses available to harvest
  → Run TLH skill for detailed analysis
```

If everything looks healthy, say so in one line: "Portfolio looks well-diversified, no major concentration or fee issues." Don't pad the report.

## What NOT to Do

- Don't run this unless the user asks for it
- Don't recommend specific trades — this is diagnostic, not prescriptive
- Don't compare to benchmarks unless the user asks "how am I doing vs SPY"
- Don't project future returns or use phrases like "expected return"
- Don't suggest rebalancing targets — you don't know the user's goals yet. Ask first.
- Don't repeat information the user already knows (e.g., don't list every position they own)
