---
name: catalyst_ideas
description: "Generate short-term, catalyst-driven trade ideas (1-15 day horizon) and track whether they were any good. Scans market-wide feeds for earnings surprises, analyst actions and press-release catalysts; you can WRITE AND SAVE YOUR OWN SCANNERS for any pattern. Every idea is scored on its horizon whether or not the user approved it, so the scorecard measures picking skill, not execution."
metadata:
  emoji: "🎯"
  category: trading
  is_system: true
  auto_on: true
  requires:
    env: ["FMP_API_KEY"]
    bins: []
---

# Catalyst Ideas

Your job is to find **reasons**, not moves. A stock that's up 9% for no reason
you can name is not an idea; a stock up 2% because it raised full-year guidance
this morning might be. The user executes (or approves auto-execution) — your
value is entirely in the quality of the suggestions and in honestly tracking how
they turn out.

```python
from skills.catalyst_ideas.scripts import feeds, screen, registry, starters
from skills.finch_api.scripts import propose_idea, list_ideas
```

## Start every session by reading your own scorecard

```python
list_ideas()   # {"ideas": [...], "scorecard": {...}, "by_catalyst": {...}}
```

`by_catalyst` is the feedback loop. It gives hit rate, avg return, **avg alpha
(return over SPY)** and avg R per catalyst type. Lean into what's earning alpha;
stop proposing what isn't. `avg_alpha_pct` is the number that matters — +8% in a
+9% market is a bad pick that looks good.

Ideas are scored **whether or not the user approved them**, so your rejections
are graded too. Propose what you actually believe; don't pad the list.

## Finding candidates

Three starters, meant to be read and copied:

```python
starters.scan_all(days_back=1)        # all three, deduped, best-signal first
starters.earnings_surprises()         # reported EPS vs consensus  <- strongest edge
starters.press_release_catalysts()    # contracts, FDA, M&A, guidance
starters.analyst_actions()            # upgrades, price-target raises
```

**Write your own whenever the pattern isn't covered** — that's the point of the
registry, and it's expected of you, not exceptional:

```python
registry.save("sympathy_moves", '''
from skills.catalyst_ideas.scripts import feeds, screen

def scan():
    """A leader's news drags its peers — the peer often lags by a day."""
    out = []
    for r in feeds.press_releases(300):
        ...
    return screen.screen(out)
''')

registry.run("sympathy_moves")
registry.run_all()          # every saved scanner; failures land in "_errors"
registry.list_scanners(); registry.read(name); registry.delete(name)
```

A scanner defines `scan()` with no required args, builds candidates with
`screen.candidate(...)`, and ends with `screen.screen(...)`. Keep it cheap — these
run on a schedule. Prune scanners whose catalyst type stops earning alpha.

## The data (all verified working — build on these)

`feeds.earnings_calendar()` · `analyst_grade_news()` · `analyst_grades_for(sym)`
(has a clean `action` field) · `press_releases()` · `press_releases_for(sym)` ·
`stock_news(syms)` · `movers()` · `quotes(syms)`

Dead ends, already tested — **don't retry**: `/upgrades-downgrades` returns `[]`,
`/stable/upgrades-downgrades` and `/stable/earnings-surprises` 404.

## Hygiene — these traps are real, use the helpers

- **`screen.surprise_pct()`, never the naive formula.** A $56.15 actual against a
  $-0.016 estimate is "+351,476%". Near-zero estimates produce garbage that will
  dominate any ranking. Returns `None` when the estimate is too small — treat
  None as "unknown", never as zero.
- **`screen.is_litigation_spam()` on every headline.** Law-firm class-action
  notices ("LEAD PLAINTIFF DEADLINE...") are a large share of the PR feed and
  name a ticker without being a catalyst.
- **`screen.screen()` before returning.** Earnings feeds carry preferred shares
  (GMRE-PA), warrants (ADVWW) and foreign lines (8370.T). Requiring a real quote
  above price/volume/market-cap floors removes them by construction — don't
  pattern-match ticker suffixes.
- **`rvol`** (added by `screen()`) is corroboration: >1.5 means the market is
  reacting to your catalyst; <1 on a "huge" headline usually means nobody cares.

## Triage — the scan is not the idea

A scan gives you 30-60 names. Most are noise. For the handful that look real:

1. **Read the actual story** — `feeds.stock_news([sym])` or
   `press_releases_for(sym)`. Quote the specific headline; never paraphrase from
   the scanner's summary alone.
2. **Ask if it's durable.** Does this change the next 1-2 quarters, or is it a
   one-day headline? Guidance raises and earnings beats with raised outlooks
   persist; a single analyst PT bump usually doesn't.
3. **Check it isn't already priced in** — if the name is +18% today, the drift
   may be spent. `rvol` and `changesPercentage` from the quote tell you.
4. **Write the bear case honestly.** Required above conviction 3, and it's the
   discipline that keeps the scorecard from filling with hopeful noise.

Catalyst ranking, strongest first: guidance raise ≈ earnings beat + raised
outlook ≫ M&A target ≫ major contract > FDA approval > analyst upgrade >
sympathy move > unexplained spike. Skip dilution, pump-and-dump and going-concern
names entirely.

## Proposing

```python
propose_idea(
    symbol="NVDA", catalyst_type="guidance_raise",
    catalyst_summary="Raised FY guidance to $4.20-4.30 from $3.90 (Q2 release, Aug 7)",
    thesis="Guidance raise of this size has historically drifted for 3-5 sessions...",
    entry_ref=182.40,        # the price RIGHT NOW, from a tool call this run
    stop=176.00, target=196.00, horizon_days=5, conviction=4,
    bear_case="Already +6% today, so much of the move may be spent...",
    sources=[{"title": "NVDA Q2 press release", "url": "..."}],
)
```

`entry_ref` is the scoring reference, not a fill — it must come from a quote in
**this** run, never a remembered price. Levels must satisfy
`stop < entry_ref < target` for a long. `bear_case` is required above conviction
3. Max 10 undecided proposals at once, so quality over quantity.

Reward:risk below ~2 is rarely worth the user's attention. Prefer 2-4 strong
ideas to 10 weak ones — every one you propose is graded.

## Hard rules

1. No catalyst, no idea. Price movement alone is never sufficient.
2. Quote the real headline; read the story before proposing.
3. `entry_ref` and every number come from a tool call in THIS run.
4. Score-check first (`list_ideas()`), then propose — let the record steer you.
5. Never propose a name you can't write an honest bear case for.
6. The user decides. You suggest and, only on approval, execute.
