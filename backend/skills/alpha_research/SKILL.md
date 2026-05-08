---
name: alpha_research
description: "Alpha research framework and data building blocks. Framework: structured knowledge from 18 academic sources on where public-data alpha comes from (processing gaps, capacity gaps, willingness gaps, adaptation, discipline). Building blocks: earnings surprise + drift data, insider activity around earnings, IV context, cross-asset snapshot, peer reactions, historical earnings moves."
metadata:
  emoji: "🔬"
  category: alpha_signals
  is_system: true
  auto_on: true
  requires:
    env: []
    bins: []
---

# Alpha Research Skill

Research-backed framework and data building blocks for finding trading opportunities. Combines existing data sources (FMP, ORATS, Polygon) — no new API keys needed.

Two layers:
1. **Framework** — structured research on where alpha comes from, for reasoning about whether an opportunity has a real edge
2. **Data blocks** — functions that fetch and enrich data, returning raw context for the agent to analyze

## Framework

```python
from skills.alpha_research.scripts.framework.alpha_sources import get_alpha_framework

framework = get_alpha_framework()

# Five structural alpha sources:
# - processing_gap: reading what others skip (SEC filings, complex 10-Ks, earnings call Q&A)
# - capacity_gap: markets too small for institutional capital
# - willingness_gap: trades institutions can't stomach (career risk, tracking error)
# - adaptation_gap: new market structures creating new patterns
# - discipline_gap: strategies that require painful patience

# Each source includes: what it is, research citations with specific numbers,
# what to look for, and decay risk assessment.

# Also includes warnings: backtest overfitting, information overload,
# live-vs-backtest gap, mechanical signal decay.
```

Read the framework before evaluating any trade idea. Ask: which of these five gaps does this opportunity exploit? If none — it's probably noise.

## Data: Earnings

```python
from skills.alpha_research.scripts.data.earnings import (
    get_recent_surprises,
    get_upcoming_earnings,
    get_earnings_history,
    get_insider_activity,
    enrich_with_profile,
)
```

### Recent earnings with surprise + drift

```python
# All earnings in the last 2 weeks with surprise data and post-earnings price drift
surprises = get_recent_surprises(lookback_days=14, min_surprise_pct=5.0)
for s in surprises:
    print(f"{s['symbol']}: surprise={s['surprise_pct']:+.1f}% drift={s['drift_pct']:+.1f}% days_since={s['days_since']}")
```

### Insider activity around earnings

```python
# Get insider buys/sells split by pre and post earnings
insider = get_insider_activity("AAPL", days_around_earnings=90)
print(f"Pre-earnings net shares: {insider['net_shares_pre']:+,}")
print(f"Post-earnings net shares: {insider['net_shares_post']:+,}")
print(f"Pre-earnings trades: {len(insider['pre_earnings'])}")
# Raw trades available in insider['all_trades'] for deeper analysis
```

### Enrich with company context

```python
# Add market cap, sector, analyst coverage to a list of symbols
profiles = enrich_with_profile(["AAPL", "TSLA", "PLTR"])
for sym, p in profiles.items():
    print(f"{sym}: {p['market_cap_b']}B, {p['analyst_count']} analysts, {p['sector']}")
```

## Data: Market Context

```python
from skills.alpha_research.scripts.data.market_context import (
    get_cross_asset_snapshot,
    get_peer_reactions,
    get_iv_context,
    get_historical_moves_around_earnings,
)
```

### Cross-asset snapshot

```python
# VIX, credit spreads, dollar, bonds, oil, gold — latest + 30d trend
snapshot = get_cross_asset_snapshot()
print(f"VIX: {snapshot['vix']['latest']:.1f} ({snapshot['vix']['trend_30d_pct']:+.1f}% 30d)")
print(f"Dollar: {snapshot['dollar']['trend_30d_pct']:+.1f}% 30d")
print(f"HYG: {snapshot['hyg']['trend_30d_pct']:+.1f}% 30d")
```

### Peer price reactions

```python
# After TSMC reports, which peers have/haven't moved?
peers = get_peer_reactions("TSM", since_date="2025-04-25")
for p in peers:
    print(f"{p['symbol']}: {p['price_change_pct']:+.1f}%")
# Sorted by magnitude — unmoved peers at the top
```

### IV context for a stock

```python
# IV rank, vol risk premium, implied earnings move, contango
iv = get_iv_context("NFLX")
if iv:
    print(f"IV rank (1y): {iv.get('iv_rank_1y')}")
    print(f"Vol risk premium: {iv.get('vol_risk_premium')}")
    print(f"Implied earnings move: {iv.get('implied_earnings_move')}")
```

### Historical earnings moves vs implied

```python
# How much did the stock actually move around past earnings?
moves = get_historical_moves_around_earnings("NFLX", n_quarters=8)
avg_move = sum(m['move_pct'] for m in moves) / len(moves) if moves else 0
print(f"Avg actual move: {avg_move:.1f}%")
for m in moves:
    print(f"  {m['earnings_date']}: {m['direction']} {m['move_pct']:.1f}%")
# Compare to current implied move from get_iv_context() to assess over/underpricing
```

## Example: Compound Analysis

The agent should combine building blocks with framework reasoning:

```python
from skills.alpha_research.scripts.framework.alpha_sources import get_alpha_framework
from skills.alpha_research.scripts.data.earnings import get_recent_surprises, get_insider_activity, enrich_with_profile
from skills.alpha_research.scripts.data.market_context import get_cross_asset_snapshot

# 1. Get macro context
macro = get_cross_asset_snapshot()

# 2. Find recent earnings surprises
surprises = get_recent_surprises(lookback_days=14, min_surprise_pct=5.0)
symbols = [s['symbol'] for s in surprises[:10]]

# 3. Enrich with company data
profiles = enrich_with_profile(symbols)

# 4. Check insider activity for interesting ones
for sym in symbols:
    insider = get_insider_activity(sym)
    profile = profiles.get(sym, {})
    surprise = next((s for s in surprises if s['symbol'] == sym), {})
    
    # Now reason: does this opportunity exploit any alpha gap?
    # - Processing gap? (low analyst count, complex business)
    # - Capacity gap? (small market cap)
    # - Insider confirmation? (pre-earnings buying + positive surprise)
    # Print raw data for analysis...

# 5. Read framework to inform reasoning
framework = get_alpha_framework()
# Check warnings before acting on any signal
```

## Extending: Write Your Own Analysis Functions

The functions here are starting points, not a complete set. You should write your own analysis functions on the fly when the situation calls for it. You have full access to all other skills (FMP, Polygon, ORATS, etc.) and can combine them however makes sense.

Examples of functions you might write ad hoc:
- Sector rotation detector using cross-asset data + FMP sector performance
- Earnings revision momentum tracker using FMP analyst estimates over time
- Congressional trading signal using FMP senate/house trading data + earnings timing
- Options skew analyzer combining ORATS IV surface with FMP fundamentals
- Custom stock screener combining multiple FMP endpoints with your own filters
- Correlation/pair analysis using Polygon historical prices

Don't limit yourself to what's pre-built. Read the framework, identify which alpha gap you're targeting, pull the raw data you need from any available skill, and build the analysis inline.

## When to Use

- Researching trade opportunities or scanning for ideas
- Evaluating whether a specific opportunity has a real edge
- Building bot strategies that need earnings/insider/IV data
- Checking macro context before entering positions
- Comparing implied vs actual earnings moves for options plays

## When NOT to Use

- For real-time price monitoring (use polygon_io)
- For placing trades (use alpaca or snaptrade)
- For portfolio analysis (use direct_indexing or portfolio_health_check)
