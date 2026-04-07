---
name: trade_lab
description: Playbook for developing prediction market trading strategies. Each bot maintains a STRATEGY.md (its financial soul) and an MEMORY.md (its operational memory). Use when a user brings a trade idea, wants to backtest, or when reviewing bot performance.
metadata:
  emoji: "🧪"
  category: trading
  is_system: true
  auto_on: true
  requires: {}
---

# Trade Lab

Each bot has **one strategy**. One thesis, one edge, one focused approach.

The bot has two core documents:
- **STRATEGY.md** — the bot's financial soul. Stored via `configure_bot(mandate=...)`.
  Defines thesis, signal, risk rules, and learnings. Evolves during brainstorming,
  backtesting, and trade reviews.
- **MEMORY.md** — the bot's operational memory. Stored via `memory_write(durable=True)`.
  Captures learned behaviors, user preferences, and operating rules.

If a user tries to add a second unrelated idea to a bot, suggest they create a new bot
for it. Each bot should be a clean experiment around a single thesis.

---

## STRATEGY.md

Every bot's strategy is stored in its mandate (via `configure_bot(mandate=...)`).
This is the bot's financial soul — it reads this before every tick and evolves it continuously.

### Template

```markdown
# [Bot Name] Strategy

## Thesis
[One paragraph: what you're betting on and why the market is wrong]

## Signal
[The specific logic for deciding when to trade]
- What markets to look at (series, filters)
- When to buy (what conditions, what edge threshold)
- When to sell / exit
- What to skip

## Risk Rules
- Max per position: $X
- Max open positions: N
- Minimum edge: X%
- Sizing: half-Kelly, capped at X% of bankroll

## Learnings
[Updated after each review cycle — newest first]

### [Date] — Review after N trades
- Win rate: X%, P&L: $X, Profit factor: X
- What worked: ...
- What failed: ...
- Adjustment: [specific change made to Signal or Risk Rules above]
```

### When STRATEGY.md evolves

STRATEGY.md is a **living document that evolves continuously** — not just after trades:

1. **During brainstorming** — as the user discusses ideas, refine the thesis and signal
2. **After research** — when you discover new data or market patterns, sharpen the signal
3. **After backtesting** — update with concrete parameters that worked (edge thresholds, filters)
4. **During paper trading** — adjust based on live execution observations
5. **After every ~20 live trades** — structured review: add Learnings entry, tighten rules
6. **When the user gives feedback** — incorporate their input into the strategy

The Signal section should get more specific over time. Start with a rough thesis,
then tighten it as data shows what actually works.

---

## The Lifecycle

### 1. Understand the Idea

Get clarity before doing anything:

- **What markets?** Which series/category? (e.g. NHL games, crypto, weather)
- **What's the thesis?** Why would the market be wrong?
- **What data supports it?** What would prove or disprove this?

Turn vague ideas into specific claims. "Sports underdogs are undervalued" becomes
"NHL home teams priced below 40% win more often than the market implies."

### 2. Backtest

Test the thesis against resolved markets using the Kalshi historical API.

```python
from kalshi_trading.scripts.kalshi import get as kalshi_get

# Fetch resolved markets
all_markets = []
cursor = None
for _ in range(5):
    r = kalshi_get("/historical/markets", {"limit": 100, "series_ticker": "KXNHLGAME", "cursor": cursor} if cursor else {"limit": 100, "series_ticker": "KXNHLGAME"})
    all_markets.extend(r.get("markets", []))
    cursor = r.get("cursor")
    if not cursor:
        break

# Simulate the strategy
wins, losses, total_pnl = 0, 0, 0
for m in all_markets:
    settlement = m.get("settlement_value")  # 100=YES won, 0=NO won
    if settlement is None:
        continue

    market_price = (m.get("yes_ask", 50)) / 100.0
    my_estimate = ...  # your thesis applied to this market
    edge = my_estimate - market_price

    if edge < 0.05:
        continue

    won = settlement == 100
    pnl = (1.0 - market_price) if won else (-market_price)
    if won: wins += 1
    else: losses += 1
    total_pnl += pnl

print(f"{wins}W/{losses}L  Win rate: {wins/(wins+losses):.0%}  P&L: ${total_pnl:.2f}")
```

**What good looks like:**
- 50+ trades minimum, 200+ preferred
- Win rate beats the implied odds (60% at 50¢ is great, 60% at 80¢ is losing)
- Profit factor > 1.3 after fees
- Works across different time periods, not just one lucky stretch

**If backtest fails:** Drop it. Don't tweak until you find a lucky fit. Go back to step 1.

### 3. Write STRATEGY.md

If the backtest looks good, save the strategy via `configure_bot(mandate=...)` with:
- The thesis (what you tested)
- The signal (the specific rules from the backtest that worked)
- Risk rules (conservative — start small)
- Backtest results as the first Learnings entry

Also save setup decisions to MEMORY.md via `memory_write(durable=True)`.

### 4. Paper Trade

Run the bot with paper positions. Validate for 20-30 trades that:
- The signal works on live data, not just historical
- Execution is realistic (spreads, liquidity)
- The bot correctly follows STRATEGY.md

### 5. Go Live

Start conservative: $1-2 per position, small max exposure. Let it run for 20+ trades.

### 6. Review & Evolve

This is the critical step. After every ~20 trades, the bot should:

**a) Check calibration:**
Group trades by confidence level. Compare predicted win rate vs actual.
- Overconfident? Add a discount factor to signals.
- Underconfident? You're leaving money on the table.

**b) Categorize losses:**
For each losing trade, identify the cause:
- **Thin edge** — edge < 5%, fees ate the profit → raise edge threshold
- **Overconfident** — signal said 70%, market was right at 55% → add confidence discount
- **Wrong data** — thesis was based on stale info → improve data sources
- **Bad timing** — right thesis, wrong entry → use limit orders or enter earlier

**c) Check for drift:**
Compare last 20 trades vs backtest baseline:
- Win rate dropping? Edge may be getting arbitraged.
- Drawdown exceeding backtest max? Regime change.
- Profit factor < 1? Stop and investigate.

**d) Update STRATEGY.md:**
Add a new Learnings entry. If patterns are clear, update the Signal or Risk Rules
sections directly via `configure_bot(mandate=...)`. The strategy should get sharper
with every review cycle.

**e) Update MEMORY.md:**
Save operational learnings via `memory_write(durable=True)` — behavioral rules,
things to avoid, patterns discovered. This persists across sessions.

### The Loop

```
Trade 20 times
    ↓
Review: calibration + loss autopsy + drift check
    ↓
Update STRATEGY.md (tighten signal, adjust rules)
Update MEMORY.md (operational learnings)
    ↓
Trade 20 more times with updated rules
    ↓
Review again: did the adjustments help?
    ↓
Repeat — each cycle the strategy gets sharper
```

The bot should **read MEMORY.md before every tick**. The whole point is to
not repeat mistakes. If "thin edge" was identified as a problem and the fix was
"raise threshold to 8%", the bot must actually apply that going forward.

---

## Binary Market Math

Contracts pay $1 if correct, $0 if wrong.

- **Cost** = price in cents / 100. A 45¢ contract costs $0.45.
- **Profit if right** = $1.00 - cost.
- **Loss if wrong** = cost.
- **Edge** = your probability - market probability.
- **Break-even** = cost. A 45¢ contract needs 45% wins to break even (before fees).
- **Fees** ≈ 7¢/contract on Kalshi. Need at least 5-8% edge to be viable after fees.

### Kelly Criterion

How much to bet given your edge:

```
kelly = (p × b - q) / b
where p = win prob, q = 1-p, b = (1 - cost) / cost
```

**Always use half-Kelly or less.** Full Kelly is too aggressive. Cap at 5% of bankroll.

### Quick EV Check

```
EV = win_prob × (1 - cost) - (1 - win_prob) × cost - 0.07
```

If EV ≤ 0, skip. Need meaningful positive EV to overcome variance.

---

## Common Pitfalls

- **Data mining** — Testing 50 variations until one works. That's noise. Would you have predicted this pattern in advance?
- **Small samples** — 15 trades at 80% win rate means nothing. Variance alone produces that.
- **Ignoring fees** — 7¢/contract destroys small edges.
- **Overconfidence after wins** — A streak doesn't validate the model. Check calibration.
- **Not adapting** — Markets learn. An edge from 3 months ago may be gone.
- **Scope creep** — One bot, one strategy. Don't mix unrelated ideas in one bot.
