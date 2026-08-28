---
name: strategy_distiller
description: "Turn a trading community's playbook (pasted chat, pinned rules, posts) into a structured, runnable Strategy spec."
metadata:
  emoji: "🧪"
  category: strategy
  is_system: true
  auto_on: false
  requires:
    env: []
    bins: []
---

# strategy_distiller

Distill messy trading-community content — pasted Discord chat, pinned playbooks, Reddit
posts, an uploaded CSV of past calls — into a **structured Strategy spec** that the
`day_trading` / `routines` skills can execute on a member's own account.

This is the engine behind "package my community's style into a strategy." See
`docs/community-strategies-research.md` §4.

## Inputs

Whatever the user/organizer provides:
- pasted text (chat logs, pinned rules, a post),
- an uploaded file in the sandbox (`read_chat_file`),
- results from the search engine (`reddit` skill / web search) they selected.

## Output — the Strategy spec (JSON)

Emit **one JSON object** matching this shape. Save it to
`/home/user/store/strategies/<slug>.json`. It maps onto the `skills.spec` column (§4b) and
is consumed by `day_trading`.

```jsonc
{
  "name": "string",                       // human name for the strategy
  "slug": "kebab-case",
  "source": { "community": "", "urls": [], "captured_at": "ISO8601" },
  "style_summary": "1-2 sentences, plain English — what this community actually does",
  "instrument": "equity | options | mixed",
  "options_enabled": true,
  "mechanics": "the core loop in plain English (e.g. the wheel: CSP -> assignment -> CC)",
  "universe": {
    "selection_rules": ["market cap > $5B", "..."],   // verbatim-derived, not invented
    "example_tickers": ["..."],                        // only if the source named them
    "explicit_watchlist": []                           // if the community trades a fixed list
  },
  "entry": {
    "trigger": "when to open a position",
    "dte": "e.g. 30-45",
    "delta_or_strike": "e.g. 0.30 delta puts / 5-10% OTM",
    "iv_rank": "e.g. >30 (40-60 ideal) | null",
    "premium_min": "e.g. 1% of strike | null"
  },
  "exit": {
    "profit_target": "e.g. close at 50%",
    "roll_rules": "when/how to roll",
    "assignment_handling": "what to do on assignment",
    "stop_or_line_in_sand": "e.g. defined before entry | null"
  },
  "sizing": {
    "max_per_underlying": "e.g. 5% of account",
    "concurrent_positions": "e.g. 3-5",
    "cash_reserve": "e.g. 20-30% cash"
  },
  "cadence": "how often to act (e.g. weekly expiries, check each market open)",
  "risk_notes": ["..."],
  "confidence": {
    "level": "high | medium | low",
    "conflicts": [                                     // where sources disagreed
      { "field": "sizing.max_per_underlying", "values": ["5%", "20%"], "resolution": "chose the more conservative; flag for organizer" }
    ],
    "gaps": ["fields the source never specified — ask the organizer to confirm"]
  },
  "disclaimer": "Educational tool, not personalized investment advice. Runs on the member's own account with their own risk limits and hold-to-approve execution."
}
```

## Distillation rules (non-negotiable)

1. **Be faithful. Do not invent numbers.** Every rule must trace to the source. If a delta,
   DTE, or size wasn't stated, put `null` and add it to `confidence.gaps` — never fill it
   with a "typical" value.
2. **Surface conflicts, don't silently pick.** When two voices disagree (e.g. 5% vs 20%
   sizing), record both in `confidence.conflicts`, default to the **more conservative**, and
   flag it for the organizer to confirm.
3. **Plain-English `style_summary` first.** The organizer must recognize their own style in
   one read, or the distillation failed.
4. **Regulatory posture:** describe rules the *member's own account* follows. Never phrase
   as a signal to broadcast or a trade to copy. Always emit the `disclaimer`.
5. **Confidence honesty.** `low` if the source was thin/contradictory; say so. A confident
   wrong spec is worse than an honest thin one.
6. After emitting, summarize for the organizer: the style in one line, the top 2-3 gaps to
   confirm, and any conflicts you resolved.

## Handoff

Once confirmed by the organizer, the spec becomes a `category="strategy"` skill row (§4c),
publishable/cloneable; installing it can provision a `ScheduledJob` + `UserGoal` so each
member runs it on their own account (§4f).
