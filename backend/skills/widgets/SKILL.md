---
name: widgets
description: Build live financial dashboard widgets (charts, stats, Kalshi odds, news, tables) for any theme, event, or the user's portfolio. Users view them in-app and share them publicly. Use whenever a user wants a tracker, dashboard, or widget.
metadata:
  emoji: "📊"
  category: product
  is_system: true
  auto_on: true
  requires:
    env: []
    bins: []
---

# Widgets

A **widget** is a live financial dashboard card built from a declarative JSON **spec**. You create widgets by calling the Finch backend from the sandbox — there is no special tool. The user sees the widget in-app; they can publish it to a public URL and share it (e.g. on Reddit), and anyone can clone a public widget onto their own data.

Your job is to turn a one-line request ("make me a Strait of Hormuz tracker", "a widget for my portfolio", "track gold vs bitcoin this year") into a tight, correct spec — then verify every tile actually returned data before telling the user it's ready.

## Calling the API

```python
from skills.finch_api.scripts.client import finch_api

# create
w = finch_api("POST", "/widgets", body={
    "title": "Strait of Hormuz Tracker",
    "description": "Oil, closure odds, tanker & defense names, headlines.",
    "emoji": "🛢️",
    "tags": ["oil", "geopolitics"],
    "spec": { ... }        # the WidgetSpec — see below
})
widget_id = w["id"]

# check the data resolved (DO THIS EVERY TIME — see Hard Rules)
data = finch_api("GET", f"/widgets/{widget_id}/data")

# search existing public widgets before building from scratch
hits = finch_api("GET", "/widgets/gallery", params={"q": "oil"})

# clone a public widget onto the current user
finch_api("POST", f"/widgets/{src_id}/clone")

# publish (mint a public share URL) — only when the user asks
pub = finch_api("POST", f"/widgets/{widget_id}/publish")   # -> {"slug": ...}
```

Auth is automatic. If a create fails with a 422, the body names the offending tile/field — fix it and retry; the validation is strict on purpose (`extra="forbid"`, strict enums).

## Spec format

```jsonc
{
  "spec_version": 1,
  "tiles": [ /* 1–12 tiles */ ],
  "refresh": { "interval_seconds": 60 }   // optional; min 60
}
```

### Tile

```jsonc
{
  "id": "oil",                 // unique within the widget, slug-like
  "type": "chart",             // chart | stat | odds | news | table | text
  "title": "Brent vs WTI",     // optional
  "size": "lg",                // sm | md | lg | full  (default md)
  "query": { ... },            // exactly one data source (below)
  "transforms": [ ... ],       // optional, ordered (below)
  "options": { ... }           // optional display options
}
```

Layout is automatic — tiles flow into a grid by `size` (sm=small, md=default, lg=wide, full=full width). No coordinates.

### Data sources (the `query`)

| source | fields | gives you |
|---|---|---|
| `quote` | `symbols: [str]` (1–20) | a **table** of live prices; a *single* symbol renders as a **stat** number |
| `series` | `symbols: [{symbol, label?}]` (1–6), `range` | multi-line **chart** history |
| `news` | `query?`, `symbols?: [str]`, `limit?` (≤20) | **news** headlines |
| `kalshi` | `ticker: str` | prediction-market **odds** (probability) |
| `fred` | `series_id: str`, `range?` | macro **series** (rates, CPI, VIX…) |
| `user_portfolio` | *(none)* | the **viewer's** holdings table (symbolic — resolves per user) |
| `user_watchlist` | *(none)* | the viewer's watchlist |
| `inline` | `shape`, `data`, `asof?` | frozen data **you computed** in the sandbox |

`range` ∈ `1D 5D 1M 3M 6M YTD 1Y 5Y`.

**Symbol conventions (FMP):** commodities `BZUSD` (Brent), `CLUSD` (WTI), `NGUSD` (nat-gas), `GCUSD` (gold), `SIUSD` (silver); indices `^GSPC` (S&P), `^IXIC` (Nasdaq), `^VIX`; crypto `BTCUSD`, `ETHUSD`; equities/ETFs plain (`AAPL`, `XLE`).

**`inline` — the flexibility escape hatch.** For anything the built-in sources can't compute (a custom index, a correlation, a mentions-per-day count), compute it in the sandbox with the FMP/other skills, then embed the result as frozen data:
```python
{"source": "inline", "shape": "series", "asof": "<iso>",
 "data": [{"label": "My index", "points": [{"t": "2026-08-01", "v": 100}, ...]}]}
```
`shape` ∈ `series | table | number | markdown`. Tell the user an inline tile is a snapshot (it won't refresh live).

### Transforms (optional, run server-side after fetch)

- `{"op": "normalize", "base": 100}` — index each series to 100 at the window start. **Use this for any multi-symbol comparison** so different price levels are comparable.
- `{"op": "pct_change"}` — series → cumulative % change.
- `{"op": "spread", "a": "<label>", "b": "<label>"}` / `{"op": "ratio", "a", "b"}` — combine two series into one.
- `{"op": "sort", "by": "<column>", "desc": true}` / `{"op": "limit", "n": 5}` — for tables (`by` a column name like `change_pct`) and news.

### Options (optional, per type)

- `chart`: `chart_type: line|area`, `y_format: pct|currency|number`, `show_legend`
- `stat`: `format: currency|pct|number`, `show_sparkline`
- `table`: `columns: [str]` (subset/order), `compact`
- `news`: `compact`

## Playbook: turn a theme into instruments

This mapping quality is the product. For an event/theme, assemble tiles across these angles:

1. **The direct asset** — the commodity/index/crypto the theme is *about* (oil → `BZUSD`/`CLUSD`; a rate decision → `DGS10` via fred).
2. **Proxy equities** — who profits or suffers. Name 4–8 tickers (Hormuz → tankers `FRO STNG TNK`, defense `LMT RTX NOC`, majors `XOM OXY`). Put them in a `series` chart with `normalize`, and/or a `quote` table sorted by `change_pct`.
3. **A prediction market** — if a Kalshi contract exists for the event, add an `odds` tile. Find the ticker first (use the kalshi skill / search); don't guess — a wrong ticker 404s.
4. **News** — a `news` tile with a tight `query` (or `symbols`).
5. **Context** — one `text`/`inline` markdown tile: one or two sentences on why this matters.

## Composition taste

- 4–8 tiles. Lead with the hero chart at `size: lg`.
- One `odds` tile beats three. One clear comparison chart beats five single-stock charts.
- Always include a news tile for event/topical widgets.
- For a **portfolio** widget: `user_portfolio` table + a `series` of the user's index (or SPY) + a portfolio-relevant news tile.

## Hard rules

1. **Search the gallery first.** `GET /widgets/gallery?q=<theme>`. If a good public widget exists, offer to clone/remix it instead of rebuilding.
2. **Verify data before declaring done.** After create, `GET /widgets/{id}/data` and check every tile's `shape` — if any tile is `"error"` (or a chart/table is empty), fix the symbol/ticker and `PATCH` the spec, then re-check. Never tell the user a widget is ready while a tile is broken. (A `user_portfolio`/`user_watchlist` tile returning `empty` is expected when the user hasn't connected an account — that's fine.)
3. **Don't publish unless asked.** Publishing creates a public URL. Only call `/publish` when the user explicitly wants to share. Personal-data tiles are safe to publish — they're symbolic and show a "connect your portfolio" state to logged-out viewers, rebinding to whoever clones the widget.
4. **Kalshi tickers must be real.** Look them up; a guessed ticker fails.

## Example: single-stock widget

```json
{
  "spec_version": 1,
  "tiles": [
    {"id": "px", "type": "chart", "title": "Apple", "size": "lg",
     "query": {"source": "series", "symbols": [{"symbol": "AAPL", "label": "Apple"}], "range": "6M"}},
    {"id": "quote", "type": "stat", "size": "sm",
     "query": {"source": "quote", "symbols": ["AAPL"]}},
    {"id": "news", "type": "news", "title": "Headlines", "size": "md",
     "query": {"source": "news", "symbols": ["AAPL"], "limit": 6}}
  ]
}
```

## Example: comparison widget

```json
{
  "spec_version": 1,
  "tiles": [
    {"id": "cmp", "type": "chart", "title": "Gold vs Bitcoin (indexed, YTD)", "size": "lg",
     "query": {"source": "series", "symbols": [{"symbol": "GCUSD", "label": "Gold"}, {"symbol": "BTCUSD", "label": "Bitcoin"}], "range": "YTD"},
     "transforms": [{"op": "normalize", "base": 100}]}
  ]
}
```

See the full flagship example (Strait of Hormuz) in the Finch repo at `docs/widgets/example-hormuz.json`.
