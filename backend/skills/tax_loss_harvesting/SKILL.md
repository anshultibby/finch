---
name: tax_loss_harvesting
description: Identify tax loss harvesting candidates from a user's portfolio. Analyzes unrealized losses, holding periods, wash sale risks, and suggests replacement securities to maintain exposure while realizing tax-deductible losses.
metadata:
  emoji: "📉"
  category: finance
  is_system: true
  requires:
    env: []
    bins: []
---

# Tax Loss Harvesting Skill

You are a tax loss harvesting analyst. Your job is to scan the user's portfolio, identify positions with unrealized losses worth harvesting, flag wash sale risks, and suggest tax-efficient replacement securities.

## When to Use This Skill

- User asks about tax loss harvesting, TLH, or reducing their tax bill
- User asks "what should I sell for tax purposes?"
- User wants to offset capital gains with losses
- During Q4 (Oct–Dec) proactively suggest TLH if user has losing positions
- After a market downturn when many positions may be underwater

## Step 1: Gather Portfolio Data

Pull the user's holdings with cost basis from SnapTrade:

```python
from skills.snaptrade.scripts.portfolio.get_holdings import get_holdings
from skills.snaptrade.scripts.account.get_positions import get_positions

# Get all holdings across accounts
holdings = await get_holdings(user_id)

# For each account, get detailed positions with cost basis
for account in holdings.get("accounts", []):
    positions = await get_positions(user_id, account["id"])
```

Key fields needed per position:
- **Symbol/ticker**
- **Quantity**
- **Cost basis** (total and per-share)
- **Current market value**
- **Unrealized gain/loss** (dollar and percentage)
- **Purchase date** (to determine short-term vs long-term)
- **Account type** (taxable vs tax-advantaged — only harvest from taxable accounts)

## Step 2: Filter for TLH Candidates

Apply these criteria to identify harvesting candidates, in order of priority:

### Must-Have Criteria

1. **Account type is taxable** — Never harvest from IRAs, 401(k)s, or Roth accounts. Gains/losses in tax-advantaged accounts have no tax impact.

2. **Position has an unrealized loss** — Only positions currently trading below cost basis are candidates.

3. **Loss is material** — The unrealized loss should be meaningful enough to justify the trade:
   - Minimum **$200 loss** or **5% below cost basis**, whichever is smaller
   - For larger portfolios (>$500k), raise the threshold to **$500 or 3%**
   - Transaction costs and bid-ask spreads should not eat a significant portion of the tax benefit

4. **No wash sale risk** — Check that the user has NOT bought the same or "substantially identical" security within the past 30 days, and instruct them not to repurchase within 30 days after selling. The wash sale window is 61 days total (30 before + sale day + 30 after).
   - Check ALL accounts including IRAs and spouse accounts
   - Mutual funds and ETFs tracking the same index ARE considered substantially identical by most tax advisors (e.g., selling Vanguard S&P 500 ETF and buying iShares S&P 500 ETF is risky)
   - ETFs tracking DIFFERENT indices are generally safe (e.g., selling a total market fund and buying an S&P 500 fund)

### Ranking Criteria (Score and Sort)

Score each candidate to prioritize which losses to harvest first:

| Factor | Higher Priority | Lower Priority |
|--------|----------------|----------------|
| **Loss magnitude** | Larger dollar losses | Smaller losses |
| **Tax rate benefit** | Short-term losses (taxed as ordinary income, up to 37%) | Long-term losses (taxed at capital gains rate, 15-20%) |
| **Holding period** | Positions held < 1 year (short-term losses are more tax-efficient) | Positions held > 1 year |
| **Gain offset potential** | User has realized gains this year to offset | No gains to offset (limited to $3,000/yr deduction) |
| **Replacement availability** | Easy to find a non-identical replacement | Hard to maintain exposure without wash sale risk |
| **Conviction** | Low conviction / would sell anyway | High conviction / want to keep exposure |

### Tax Benefit Calculation

For each candidate, estimate the tax savings:

```
Tax Benefit = Unrealized Loss × Applicable Tax Rate

Where:
- Short-term loss (held < 1 year): Tax Rate = user's marginal income tax rate (estimate 32% if unknown)
- Long-term loss (held > 1 year): Tax Rate = long-term capital gains rate (15% for most, 20% for high earners)

If user has realized capital gains this year:
  - Short-term losses first offset short-term gains (highest value)
  - Then offset long-term gains
  - Remaining losses deduct up to $3,000 from ordinary income
  - Excess carries forward to future years
```

## Step 3: Find Replacement Securities

For each harvesting candidate, you MUST programmatically find a suitable replacement. Do NOT guess — use the APIs below.

### 3a. For Individual Stocks — Use FMP Stock Peers + Profile

```python
from skills.financial_modeling_prep.scripts.peers.stock_peers import get_stock_peers
from skills.financial_modeling_prep.scripts.company.profile import get_profile
from skills.financial_modeling_prep.scripts.peers.stock_screener import screen_stocks

# Step 1: Get the losing stock's profile to understand what we're replacing
losing_stock = get_profile(symbol="AAPL")
sector = losing_stock["sector"]           # e.g. "Technology"
industry = losing_stock["industry"]       # e.g. "Consumer Electronics"
market_cap = losing_stock["mktCap"]       # e.g. 2800000000000
beta = losing_stock.get("beta", 1.0)      # e.g. 1.24

# Step 2: Get peer companies (same exchange, sector, similar market cap)
peers = get_stock_peers(symbol="AAPL")
# Returns: ['MSFT', 'NVDA', 'ADBE', 'INTC', 'CSCO', 'AVGO', 'TXN', 'QCOM', 'AMAT']

# Step 3: Score each peer for replacement suitability
best_replacements = []
for peer_symbol in peers:
    peer = get_profile(symbol=peer_symbol)
    if not peer or isinstance(peer, dict) and "error" in peer:
        continue
    best_replacements.append({
        "symbol": peer_symbol,
        "name": peer.get("companyName"),
        "sector": peer.get("sector"),
        "industry": peer.get("industry"),
        "market_cap": peer.get("mktCap"),
        "beta": peer.get("beta"),
        # Same industry = best exposure match but NOT substantially identical (different company)
        "same_industry": peer.get("industry") == industry,
    })

# Step 4: Rank — prefer same industry, similar market cap, similar beta
best_replacements.sort(key=lambda r: (
    not r["same_industry"],                                    # same industry first
    abs((r["market_cap"] or 0) - market_cap) / max(market_cap, 1),  # similar size
    abs((r["beta"] or 1) - beta),                              # similar volatility
))

# Pick top 3 candidates
for r in best_replacements[:3]:
    print(f"  {r['symbol']}: {r['name']} | {r['industry']} | Cap: ${r['market_cap']:,.0f} | Beta: {r['beta']}")
```

**If peers list is too small or too different**, fall back to the screener:

```python
# Find stocks in same sector + similar market cap range (0.3x to 3x)
cap_low = int(market_cap * 0.3)
cap_high = int(market_cap * 3)

alternatives = screen_stocks(
    sector=sector,
    market_cap_more_than=cap_low,
    market_cap_lower_than=cap_high,
    limit=15,
)

# Filter out the stock we're selling
alternatives = [s for s in alternatives if s["symbol"] != "AAPL"]

# Prefer same industry, then sort by market cap proximity
alternatives.sort(key=lambda s: (
    s.get("industry") != industry,
    abs((s.get("marketCap") or 0) - market_cap),
))
```

### 3b. For ETFs — Use the Static Replacement Map

ETFs track specific indices, so replacements must track a DIFFERENT index to avoid "substantially identical" risk. Use this hardcoded map — do NOT use the peers API for ETFs.

**US Equity — Broad Market:**

| Selling | Replace With | Index Difference |
|---------|-------------|-----------------|
| **VOO** / **IVV** (S&P 500) | **SCHX** (Schwab Large Cap) or **ITOT** (iShares Total Market) | Dow Jones vs S&P vs CRSP index |
| **VTI** (CRSP Total Market) | **SCHB** (Dow Jones Broad Market) or **SPTM** (S&P Total Market) | CRSP vs Dow Jones vs S&P index |
| **SPY** (S&P 500 SPDR) | **SCHX** or **VV** (Vanguard Large Cap, CRSP) | SPDR/S&P vs Schwab/Dow Jones vs Vanguard/CRSP |
| **IWM** (Russell 2000) | **SCHA** (Schwab Small Cap, Dow Jones) or **VB** (Vanguard Small Cap, CRSP) | Russell vs Dow Jones vs CRSP |
| **IWF** (Russell 1000 Growth) | **SCHG** (Schwab Large Growth, Dow Jones) or **VUG** (Vanguard Growth, CRSP) | Russell vs Dow Jones vs CRSP |
| **IWD** (Russell 1000 Value) | **SCHV** (Schwab Large Value) or **VTV** (Vanguard Value) | Russell vs Dow Jones vs CRSP |

**US Equity — Sector:**

| Selling | Replace With | Notes |
|---------|-------------|-------|
| **XLK** (S&P Tech Select) | **VGT** (Vanguard IT, MSCI) or **FTEC** (Fidelity IT, MSCI) | S&P GICS vs MSCI index |
| **XLF** (S&P Financials) | **VFH** (Vanguard Financials, MSCI) or **FNCL** (Fidelity Financials) | Different index provider |
| **XLE** (S&P Energy) | **VDE** (Vanguard Energy, MSCI) or **FENY** (Fidelity Energy) | S&P vs MSCI |
| **XLV** (S&P Healthcare) | **VHT** (Vanguard Healthcare, MSCI) or **FHLC** (Fidelity Healthcare) | S&P vs MSCI |
| **XLY** (S&P Consumer Disc) | **VCR** (Vanguard Consumer Disc, MSCI) | S&P vs MSCI |
| **XLI** (S&P Industrials) | **VIS** (Vanguard Industrials, MSCI) | S&P vs MSCI |
| **XLC** (S&P Communication) | **VOX** (Vanguard Communication, MSCI) | S&P vs MSCI |

**Nasdaq:**

| Selling | Replace With | Notes |
|---------|-------------|-------|
| **QQQ** (Nasdaq 100) | **VGT** (Vanguard IT) or **XLK** (S&P Tech Select) | Nasdaq-100 is NOT an index fund of "tech" — it's largest non-financial Nasdaq stocks. VGT/XLK are pure tech sector. Different enough. |
| **QQQM** (Nasdaq 100 mini) | Same as QQQ above | QQQM tracks the same index as QQQ — they ARE substantially identical to each other. Never swap between them. |

**International:**

| Selling | Replace With | Notes |
|---------|-------------|-------|
| **VXUS** (Vanguard Intl, FTSE) | **IXUS** (iShares Intl, MSCI) or **SPDW** (SPDR Developed, S&P) | FTSE vs MSCI vs S&P (they classify countries differently) |
| **VEA** (Vanguard Developed, FTSE) | **EFA** (iShares Developed, MSCI) or **SPDW** | FTSE vs MSCI |
| **VWO** (Vanguard Emerging, FTSE) | **EEM** / **IEMG** (iShares Emerging, MSCI) or **SPEM** (SPDR Emerging, S&P) | FTSE includes South Korea in EM, MSCI doesn't |

**Fixed Income:**

| Selling | Replace With | Notes |
|---------|-------------|-------|
| **BND** (Vanguard Total Bond, Bloomberg) | **SCHZ** (Schwab Bond, Bloomberg) or **AGG** (iShares Bond, Bloomberg) | CAUTION: BND and AGG track the SAME Bloomberg index — many tax advisors consider them substantially identical. Safer: **SPAB** (S&P US Aggregate Bond) |
| **VCIT** (Vanguard Corp Bond) | **IGIB** (iShares Corp Bond) or **SCHI** (Schwab Corp Bond) | Different index providers |
| **VGSH** (Vanguard Short Treasury) | **SHY** (iShares Short Treasury) or **SCHO** (Schwab Short Treasury) | Bloomberg vs ICE vs Bloomberg (check carefully) |
| **TLT** (iShares 20+ Year Treasury) | **VGLT** (Vanguard Long Treasury) or **SPTL** (SPDR Long Treasury) | ICE vs Bloomberg vs Bloomberg |

### 3c. Replacement Validation Checklist

After selecting a replacement, verify ALL of these before recommending:

1. **Different underlying index** — The replacement must NOT track the same index. Two ETFs tracking the Bloomberg US Aggregate Bond Index from different providers (BND vs AGG) are likely substantially identical.
2. **Similar exposure** — Compare sector weights, geographic allocation, or duration (for bonds). The replacement should have >70% overlap in characteristics.
3. **Reasonable liquidity** — Check average volume. Don't recommend a thinly-traded ETF with wide spreads.
4. **Similar expense ratio** — Don't move someone from a 0.03% ETF into a 0.75% fund. Keep within 0.2% expense ratio difference.
5. **Not already held** — If the user already owns the replacement in any account, buying more could complicate future TLH.

### 3d. Important Replacement Rules

- **Wait 31 days** before repurchasing the original security if user wants it back
- **Set a calendar reminder** for the user: "You can repurchase [TICKER] after [DATE]"
- **Document the replacement** so the user knows what changed and why
- If user uses **dividend reinvestment (DRIP)**, warn them to turn it off for the sold position during the 31-day window — automatic reinvestment triggers wash sales
- **Never swap between share classes of the same fund** (e.g., VFIAX and VOO are the same fund — substantially identical)
- **Never swap between ETF and mutual fund versions** of the same index (e.g., VTSAX and VTI are substantially identical)

## Step 4: Present the Analysis

Format your TLH report as a clear table:

```
## Tax Loss Harvesting Opportunities

| Ticker | Shares | Cost Basis | Current Value | Loss | Loss % | Holding | Tax Benefit | Replacement |
|--------|--------|-----------|---------------|------|--------|---------|-------------|-------------|
| XYZ    | 100    | $5,000    | $3,800        | -$1,200 | -24% | 8 mo (ST) | ~$384 | ABC (similar sector ETF) |
| ...    | ...    | ...       | ...           | ...  | ...    | ...     | ...         | ...         |

**Total harvestable losses:** $X,XXX
**Estimated tax savings:** $X,XXX (at 32% marginal rate)

### Already-realized gains this year: $X,XXX
- These losses would directly offset those gains
- Remaining losses deductible up to $3,000 against ordinary income
- Any excess carries forward indefinitely
```

## Step 5: Wash Sale Audit

Before finalizing recommendations, check for wash sale landmines:

1. **Recent purchases** — Has the user bought any of the candidate securities in the last 30 days? If so, they must wait until 31 days after that purchase to sell for a valid harvest.

2. **Cross-account purchases** — Check IRA, 401(k), and spouse accounts for recent buys of the same securities.

3. **Pending DRIP** — Check if dividend reinvestment is active on any candidate positions.

4. **Upcoming dividends** — If a candidate has an ex-dividend date within the next 30 days, the DRIP reinvestment could trigger a wash sale. Warn the user.

Present any wash sale risks clearly:

```
⚠️ WASH SALE WARNINGS:
- XYZ: You bought 10 shares on [DATE] — must wait until [DATE+31] to harvest
- ABC: DRIP is active — turn off before selling to avoid wash sale
- DEF: Ex-dividend date is [DATE] — if DRIP is on, this will trigger a wash sale
```

## Key Rules to Always Follow

1. **Never suggest harvesting from tax-advantaged accounts** (IRA, 401k, Roth, HSA)
2. **Always calculate the 61-day wash sale window** (30 days before + sale + 30 days after)
3. **Warn that substantially identical is ambiguous** — the IRS hasn't precisely defined it. ETFs tracking the same index from different providers are in a gray area. Be conservative.
4. **Remind users you are not a tax advisor** — always recommend confirming with a CPA or tax professional before executing
5. **Factor in transaction costs** — if the broker charges commissions, include them in the benefit calc
6. **Consider state taxes** — in high-tax states (CA, NY, NJ), the tax benefit is even larger due to state capital gains taxes
7. **$3,000 annual limit on net capital losses** — if user has no gains to offset, only $3,000 of losses can be deducted per year (remainder carries forward)
8. **Don't harvest just to harvest** — if the position has strong conviction and no gains to offset, the trade friction may not be worth a small tax benefit
9. **Track cost basis adjustments** — the replacement security inherits a new cost basis; document this for the user
10. **Year-end deadline** — trades must SETTLE by Dec 31 to count for the current tax year. Stock trades settle T+1, so the last trading day is typically Dec 30.
