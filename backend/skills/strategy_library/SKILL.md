---
name: strategy_library
description: "Browse trading playbooks/strategies the user can try, explain them, and adopt one for their goal (or distill a new one from a Reddit community or a pasted playbook). Use when the user wants to explore strategies, asks 'what should I try', or wants to systematize how they trade."
metadata:
  emoji: "📓"
  category: strategy
  is_system: true
  auto_on: true
  requires:
    env: []
    bins: []
---

# Strategy library

Finch's window into strategies to try. The flow is **browse → explain → adopt**, and it's
conversational — show a menu and let the user choose; don't dump everything at once.

## Step 1 — Show the menu

```python
from skills.finch_api.scripts.client import list_strategies
lib = list_strategies()   # {"starters": [...], "mine": [...]}
```

Present `starters` (and any `mine` the user already adopted) as a compact **numbered table**:

| # | Strategy | Style | What it is |
|---|----------|-------|------------|
| 1 | Index DCA | index | Dollar-cost average a broad index… |
| … | … | … | … |

Then **ask** which one they want to explore or adopt. Keep it to the table + one line.

## Step 2 — Explain a chosen one

From its `spec`, explain the mechanics plainly: universe, entry trigger, exit/stop, sizing,
risk, cadence, and whether it needs options. Tie it to the user's goal (you have the goal in
context) — who it fits, what it demands, the honest risks (`spec.risk_notes`). Never invent
performance numbers or claim it "beats the market."

## Step 3 — Adopt

When the user picks one:

```python
from skills.finch_api.scripts.client import adopt_strategy
adopt_strategy(starter_slug="wheel")          # a starter, OR
adopt_strategy(spec=distilled_spec, name="…") # a distilled/custom one
```

This persists it and **binds it to their goal** (the agent's `<mission>` will run it going
forward). Confirm what changed in plain words. Then **offer** to schedule a routine so Finch
checks the strategy's decision-points on a cadence:

```python
from skills.finch_api.scripts.client import schedule_job
schedule_job("Run my <strategy> decision-points and propose any trades (hold-to-approve).",
             recurrence="weekdays")
```

Only schedule if the user explicitly says yes. All trades stay hold-to-approve.

## Step 4 — Distill a new one (the "world of ideas")

To create a strategy from outside Finch:
- **From a community:** use the `reddit` skill (`search_community`, `get_community_posts`,
  `read_thread`) to read how a community actually trades, then distill it.
- **From a pasted playbook / CSV of past calls:** read what the user shared.

Produce a spec in the **`strategy_distiller`** format (see [[strategy_distiller]] — universe,
entry, exit, sizing, risk, cadence, options on/off, plus a `confidence` block noting gaps and
a `disclaimer`). Then `save_strategy(spec, name=...)` and offer to adopt it.

Follow reddit's read-live-use-discard rule — don't build a stored corpus. This is education +
backtestable rules the user's own account runs, never "here's a personalized trade we placed."
