---
name: trade_feedback
description: "Review the user's recent executed trades. Pull them, show a ranked table, ask which ONE to dig into, then critique that trade against their goal and suggest alternatives. Use whenever the user wants feedback on their trading or asks to review/learn from their trades."
metadata:
  emoji: "🔎"
  category: research
  is_system: true
  auto_on: true
  requires:
    env: []
    bins: []
---

# Trade feedback

Help the user learn from their own trading. This is **stepwise and conversational** —
never dump analysis on all their trades at once. The flow is: pull → table → ask → dig in.

## When to use

The user asks to review their trades, wants feedback on their trading, taps "Review my
recent trades", or asks things like "was that a good trade?" / "how have I been doing?".

## Step 1 — Pull the trades

```python
from skills.finch_api.scripts.client import get_recent_trades

result = get_recent_trades(limit=15)
```

Returns `{connected, broker, trades: [{id, symbol, side, quantity, price, amount, date, broker}, ...]}`,
newest-first, `amount` = qty × price.

- If `connected` is `False` (or `trades` is empty): don't fabricate anything. Tell the user
  you can review their trades once a brokerage is connected, and point them to connect one.

## Step 2 — Show a ranked table, then ASK

Present the trades as a compact numbered markdown table so the user can pick one. Rank them
by what's most worth reviewing — lead with the **largest and most recent** (bigger `amount`
and closer dates first); you don't have realized P&L, so don't claim wins/losses here.

| # | Trade | Size | When |
|---|-------|------|------|
| 1 | BUY 10 NVDA @ $120.50 | ~$1,205 | Aug 20 |
| … | … | … | … |

Then **stop and ask** which one they want to dig into. Do not analyze yet — this is a
menu, not a report. Keep any commentary to one line.

## Step 3 — Dig into the chosen trade

Once they pick one, run a focused review of THAT trade and its stock:

1. **Was it a sound decision?** Assess entry, timing, and sizing given what the stock/market
   was doing around `date`, and **frame it against the user's goal** (you already have the
   goal in context). Be honest and specific, not flattering.
2. **What's the situation now?** Where the stock stands today vs. their entry.
3. **Alternatives** — suggest 2-3 concrete things they could do now (adjust the position,
   hedge, or a better-fit idea). Use the `catalyst_ideas` / `alpha_research` skills to ground
   alternatives in real catalysts/data; never invent news. If an alternative is a real,
   trackable idea, you may log it via `propose_idea` (finch_api).
4. **Save a note** so it persists on the stock's Analysis tab: `write_chat_file` to
   `stocks/{SYMBOL}/trade-review.md` (see the `stock_analysis` skill).

Then offer to dig into another trade from the table.

## Keep it tight

Steps 1-2 should be fast and cheap (one API call + a table). Only step 3 does real analysis,
and only for the single trade the user chose — that's the whole point of asking first.
