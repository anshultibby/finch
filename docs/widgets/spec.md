# Finch Widgets — Design Spec v1

**Status:** implemented (Aug 5 2026) — all 6 phases coded and verified offline (28 pytest pass; data service validated against live FMP/FRED/Kalshi; frontend typechecks + production-builds; app boots with routes mounted). **One gated step remains: `alembic upgrade head` to apply migration 089** (not run unattended against the hosted Supabase DB), then seed + prod E2E. See §7.
**Goal:** Finch specializes in agent-generated financial widgets. A user (or Anshul) types one sentence ("make me a Strait of Hormuz tracker") and gets a live, cloneable, publicly shareable dashboard widget. Topical widgets are the acquisition loop (post on Reddit → public live page → "Clone this" → signup); personal portfolio/watchlist widgets are the retention loop.

---

## 1. Product decisions (settled in discussion)

| Decision | Choice | Why |
|---|---|---|
| Widget form | In-app dashboard cards **+ public share page** | Reddit loop requires a no-login live URL; screenshot alone converts nobody |
| Architecture | **Declarative JSON spec + fixed tile renderer** — NOT generated code/iframes | Cloneable, cacheable, safe to embed, visually coherent; existing viz gallery (arbitrary HTML in iframes) is the wrong substrate |
| Flexibility | Flexibility lives in the **data layer**, not the render layer | Agent computes anything in its sandbox → emits standard data shapes; renderer stays fixed |
| Tiering | **No Pro gate.** Everything free; only real cost control is caching | 21 signups — tiering is a problem we don't have; creation already metered by existing credits |
| Refresh | **On-view polling + shared server-side cache. No background jobs in v1** | Viewers polling share one upstream fetch; abandoned widgets cost zero; no cron to babysit |
| Agent integration | **No new agent tools.** REST API + `backend/skills/widgets/` skill using the existing `finch_api` sandbox client | Matches every other skill; SKILL.md is editable without deploys; same artifact later adapts into a Claude Code / Codex store skill |
| Arbitrary compute | v1 = `inline` frozen data (agent computes in sandbox, embeds result) + small in-backend transform DSL. Sandbox-refreshed computed tiles are **v2** | 90% of flexibility, none of the per-refresh sandbox cost or code-execution risk |

### Prior art distilled (research done, agents' findings)

- **TradingView embeds**: industry-standard config shape — data selector, `interval` distinct from `range`, compact/display flags, shared theme envelope, *every field optional with sane defaults*, named string enums everywhere (LLM-friendly). Their gap: every widget is single-data-source.
- **Koyfin**: dashboards need grid layout + link groups. We take a simplified layout (size enum, no x/y).
- **Grafana**: the durable decisions — tile type decoupled from data source; fixed pipeline `query → transform → display → render`; published specs contain **typed holes, never concrete account refs** (`__inputs` rebind-on-import); `specVersion` + migrations from day one. Their pain we avoid: verbosity (omit defaults on serialize), id/uid split (one `id`), one-way migrations.
- **Datawrapper/Flourish**: frozen-snapshot data for public previews; clone = copy with lineage + attribution; opt-in (never automatic) template update propagation.
- **Market gaps we occupy**: thesis/event trackers (odds + tickers + news in one card), portfolio-aware widgets, AI-narrative tiles, dynamic query-defined symbol lists. Nobody does these.

---

## 2. Widget spec (the JSON document)

Stored in `widgets.spec` (JSONB). Emitted whole by the agent. Validated by Pydantic on every create/update.

```jsonc
{
  "spec_version": 1,
  "tiles": [ /* 1..12 tiles, see below */ ],
  "refresh": { "interval_seconds": 60 }   // optional; server clamps to >= 60
}
```

Widget-level metadata (title, description, emoji, tags) lives on the DB row, not in the spec — no duplication.

### 2.1 Tile

```jsonc
{
  "id": "oil",                    // unique within widget, slug-like
  "type": "chart",                // chart | stat | odds | news | table | text
  "title": "Oil benchmarks",      // optional
  "size": "md",                   // sm | md | lg | full  (default md)
  "query": { /* one data query, see 2.2 */ },
  "transforms": [ /* optional ordered ops, see 2.3 */ ],
  "options": { /* tile-type-specific display options, all optional */ }
}
```

Layout: no coordinates. Tiles auto-flow into a CSS grid; `size` maps to col-spans (desktop 4-col grid: sm=1, md=2, lg=2 rows tall ×2, full=4). Agent can't fumble x/y math.

### 2.2 Query sources

| `source` | Params | Returns shape | Powered by |
|---|---|---|---|
| `quote` | `symbols: [str]` (≤20) | `table` (symbol, price, change, change_pct) | FMP |
| `series` | `symbols: [{symbol, label?}]` (≤6), `range: 1D\|5D\|1M\|3M\|6M\|YTD\|1Y\|5Y` | `series` (multi) | FMP historical |
| `news` | `query?: str`, `symbols?: [str]`, `limit?: int≤20` | `news` items | FMP news/search |
| `kalshi` | `ticker: str` (market ticker) | `odds` (prob, prior history if available, title, close_date) | Kalshi public API (no auth needed for market data) |
| `fred` | `series_id: str`, `range?` | `series` | FRED (`FRED_API_KEY` in config) |
| `user_portfolio` | — | `table` (holdings w/ P&L) | SnapTrade holdings, resolved **per viewing user** |
| `user_watchlist` | — | `table` | user watchlist, resolved per viewer |
| `inline` | `shape: series\|table\|number\|markdown`, `data: ...`, `asof: iso` | as declared | frozen data the agent computed in its sandbox |

**Symbolic bindings:** `user_portfolio` / `user_watchlist` never contain account ids in the spec. On a public page with no auth, these tiles render an empty state + "Connect your portfolio" CTA. On clone, they automatically rebind to the cloner (zero-question clone — the Grafana `__inputs` flow collapsed to automatic because our binding kinds are unambiguous).

**Symbols:** FMP conventions (`AAPL`, `BZUSD`/`CLUSD` for Brent/WTI, `^GSPC`, `BTCUSD`). The skill documents the commodity/index symbol quirks.

### 2.3 Transforms (in-backend, safe, no code execution)

Ordered list applied to the query result before render:

- `{"op": "normalize", "base": 100}` — index each series to base at window start (the "4 tickers indexed to 100 since event X" tile)
- `{"op": "pct_change"}` — series → cumulative % change
- `{"op": "spread", "a": "<label>", "b": "<label>"}` — two series → one (a−b)
- `{"op": "ratio", "a": "<label>", "b": "<label>"}`
- `{"op": "sort", "by": "<column>", "desc": true}`, `{"op": "limit", "n": 5}` — table shapes

Anything beyond this, the agent precomputes in its sandbox and ships as `inline`.

### 2.4 Tile options (per type, all optional)

- `chart`: `chart_type: line|area` (default area), `show_legend`, `y_format: pct|currency|number`
- `stat`: `format: currency|pct|number`, `show_sparkline` (default true), `delta_from: prev_close|window_start`
- `odds`: `show_history` (default true)
- `news`: `show_source` (default true), `compact`
- `table`: `columns?: [str]` (subset/order), `compact`
- `text`: markdown comes from query (`inline` markdown or future AI source); options: none v1

### 2.5 Example — the flagship Hormuz tracker

```json
{
  "spec_version": 1,
  "tiles": [
    {"id": "oil", "type": "chart", "title": "Brent vs WTI", "size": "lg",
     "query": {"source": "series", "symbols": [{"symbol": "BZUSD", "label": "Brent"}, {"symbol": "CLUSD", "label": "WTI"}], "range": "3M"},
     "options": {"chart_type": "line"}},
    {"id": "odds", "type": "odds", "title": "Strait closure by Sep 30", "size": "sm",
     "query": {"source": "kalshi", "ticker": "KXHORMUZ-26SEP30"}},
    {"id": "brent-stat", "type": "stat", "title": "Brent", "size": "sm",
     "query": {"source": "quote", "symbols": ["BZUSD"]}},
    {"id": "tankers", "type": "chart", "title": "Tankers & defense, indexed", "size": "md",
     "query": {"source": "series", "symbols": [{"symbol": "FRO"}, {"symbol": "STNG"}, {"symbol": "LMT"}, {"symbol": "RTX"}], "range": "1M"},
     "transforms": [{"op": "normalize", "base": 100}]},
    {"id": "movers", "type": "table", "title": "Related names", "size": "md",
     "query": {"source": "quote", "symbols": ["FRO", "STNG", "TNK", "LMT", "RTX", "NOC", "XOM", "OXY"]},
     "transforms": [{"op": "sort", "by": "change_pct", "desc": true}]},
    {"id": "news", "type": "news", "title": "Latest", "size": "md",
     "query": {"source": "news", "query": "Strait of Hormuz oil", "limit": 8}},
    {"id": "context", "type": "text", "size": "full",
     "query": {"source": "inline", "shape": "markdown", "data": "**Why this matters:** ~20% of global oil transits the Strait...", "asof": "2026-08-04T12:00:00Z"}}
  ],
  "refresh": {"interval_seconds": 60}
}
```

### 2.6 Data shapes (the contract between backend and renderer)

```jsonc
// series:  {"shape": "series", "series": [{"label": "Brent", "points": [{"t": "2026-08-01", "v": 78.2}, ...]}], "asof": iso}
// table:   {"shape": "table", "columns": ["symbol","price","change_pct"], "rows": [[...], ...], "asof": iso}
// number:  {"shape": "number", "value": 78.2, "delta": 1.3, "delta_pct": 1.69, "sparkline": [..], "asof": iso}
// odds:    {"shape": "odds", "prob": 0.17, "title": "...", "close_date": iso, "history": [{"t","v"}], "asof": iso}
// news:    {"shape": "news", "items": [{"title","url","source","published_at","symbols?"}], "asof": iso}
// markdown:{"shape": "markdown", "text": "...", "asof": iso}
// error (per-tile, page still renders): {"shape": "error", "message": "..."}
```

---

## 3. Backend

### 3.1 Model — `backend/models/widget.py` (pattern: `models/kalshi_bot.py`)

```python
class Widget(Base):
    __tablename__ = "widgets"
    id = Column(String, primary_key=True)          # uuid4 str — ONE id, no numeric/uid split
    user_id = Column(String, nullable=False, index=True)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    emoji = Column(String, nullable=True)
    tags = Column(JSONB, nullable=True)             # ["oil", "geopolitics"]
    spec = Column(JSONB, nullable=False)
    visibility = Column(String, nullable=False, server_default="private")  # private | public
    slug = Column(String, nullable=True, unique=True, index=True)  # set on publish; unguessable-ish: "hormuz-tracker-x7k2"
    cloned_from = Column(String, nullable=True)     # widget id lineage
    view_count = Column(Integer, nullable=False, server_default="0")
    clone_count = Column(Integer, nullable=False, server_default="0")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
```

### 3.2 Migration — `backend/alembic/versions/089_add_widgets.py`

`revision='089'`, `down_revision='088'` (current head — re-verify at implementation time). Hand-written mirroring the model; indexes on `user_id`, `slug`, and `(visibility, created_at)` for the gallery query; full downgrade.

### 3.3 Schemas — `backend/schemas/widget.py`

Pydantic models for **both** the API request/response AND the spec itself (`WidgetSpec`, `Tile`, `Query` as a discriminated union on `source`, `Transform` union on `op`). Spec validation IS the product guardrail: strict enums, symbol-count caps, ≤12 tiles, unknown fields rejected (`model_config = ConfigDict(extra="forbid")`) so agent typos fail loudly at create time with a readable error the agent can self-correct from. Response models `from_attributes = True`; update request all-`Optional`.

### 3.4 CRUD — `backend/crud/widget.py`

Async free functions `(db, user_id, ...)`: create, get (owner-scoped), get_by_slug (public only), list_mine, list_gallery (visibility=public, order by created_at/clone_count, optional `q` filter on title/tags), update, delete, publish (assign slug), clone (copy spec + `cloned_from`, strip nothing — spec is guaranteed reference-clean, see 3.6), increment view/clone counts.

### 3.5 Routes — `backend/routes/widget.py` (pattern: `routes/kalshi_bot.py`)

`APIRouter(prefix="/widgets", tags=["widgets"])`, sessions via `async with get_db_session() as db`, auth via `user_id: str = Depends(get_current_user_id)` (trust JWT only; ignore the `user_id` query param the finch_api client appends).

| Route | Auth | Purpose |
|---|---|---|
| `POST /widgets` | ✓ | create (validates spec, returns full widget + any validation warnings) |
| `GET /widgets` | ✓ | my widgets |
| `GET /widgets/gallery?q=&tag=&sort=` | ✓ | browse public widgets (the agent's "search before build"; also feeds an in-app gallery later) |
| `GET /widgets/{id}` | ✓ | owner or public |
| `PATCH /widgets/{id}` | ✓ | update title/desc/spec (owner) |
| `DELETE /widgets/{id}` | ✓ | owner |
| `POST /widgets/{id}/publish` | ✓ | publish sweep (3.6) → visibility=public, mint slug; body `{unpublish: true}` reverses |
| `POST /widgets/{id}/clone` | ✓ | clone public (or own) widget into my collection |
| `GET /widgets/{id}/data` | ✓ | resolve all tile data (owner or public; bindings resolve to caller) |
| `GET /widgets/shared/{slug}` | **none** | public read (pattern: `routes/chat.py:268` `get_shared_chat`) — widget meta + spec; increments view_count (fire-and-forget) |
| `GET /widgets/shared/{slug}/data` | **none** | public tile data; binding tiles → empty-state payload |

Registration: `routes/__init__.py` (+`__all__`) and `main.py` (import line + `app.include_router(widget_router)`).

### 3.6 Publish sweep (the privacy rule)

On publish, walk the spec: any tile whose query source is NOT in the public-safe set {quote, series, news, kalshi, fred, inline, user_portfolio, user_watchlist} → reject. `user_portfolio`/`user_watchlist` are allowed **because they're symbolic** — the sweep asserts the query params dict for them is empty (no account ids possible by schema anyway, `extra="forbid"` enforces it). `inline` data is allowed (frozen snapshot, Datawrapper-style) — but sweep rejects `inline` markdown/table content matching obvious PII patterns? **No — keep v1 simple: it's the author's own content, same trust model as sharing a chat.** Fail the publish loudly with a per-tile reason.

### 3.7 Data service — `backend/services/widget_data.py`

The heart. `async def resolve_widget_data(spec, viewer_user_id: str | None) -> dict[tile_id, shape-payload]`.

- **Fetchers** per source. Reuse existing backend market-data code where it exists (the `/market/prices` route that powers `MiniSparkline` has an FMP path — find and reuse its service; likewise any news/quote helpers). Where nothing exists server-side (Kalshi public market data, FRED), call the public APIs directly with `httpx` using keys from `core/config.py`. **Do NOT import from `backend/skills/`** — those scripts are sandbox-side code.
- **Cache**: module-level dict, pattern copied from `services/move_explainer.py` — key `(source, frozen params)`, value `{at, data}`, per-key `asyncio.Lock` double-checked locking, size-bounded eviction (>500 → evict oldest 100). TTLs: quote/kalshi 60s, series/news 300s, fred 3600s. Transforms run *after* cache (cache raw fetches, so `normalize` variants share one upstream call).
- **Fan-out**: `asyncio.gather` across tiles with per-tile try/except → `{"shape": "error"}` payloads; one bad symbol never blanks the widget.
- Binding sources: `user_portfolio`/`user_watchlist` fetch via existing holdings/watchlist services with `viewer_user_id`; `viewer_user_id=None` (public page) → `{"shape": "empty", "reason": "connect_portfolio"}`.

### 3.8 Skill — `backend/skills/widgets/SKILL.md`

Frontmatter (flat "YAML-ish" — nested keys don't parse, see `skills_registry.py` `_parse_frontmatter`):

```yaml
---
name: widgets
description: Create, search, update, and publish live financial dashboard widgets (charts, stats, Kalshi odds, news, tables) that users can view in-app and share publicly. Use whenever a user wants a tracker/dashboard/widget for any theme, event, or their portfolio.
metadata:
  emoji: "📊"
  category: product
  is_system: true
  auto_on: true
  requires:
    env: []
    bins: []
---
```

Body contents (the heuristics — this file IS the product quality lever, iterate without deploys):
1. **API reference**: all endpoints above, called via `from skills.finch_api.scripts.client import finch_api` (`finch_api("POST", "/widgets", body={...})`). Auth is automatic.
2. **Full spec reference** with the data shapes and 2–3 complete example specs (Hormuz tracker verbatim, a portfolio widget, a single-stock widget).
3. **Playbook — theme → instruments**: event/theme → (a) direct commodities/assets, (b) proxy equities (who profits/loses), (c) a Kalshi contract if one exists (search Kalshi first via the kalshi skill), (d) news query, (e) one `text` tile of context. FMP symbol quirks table (commodities `BZUSD`/`CLUSD`/`NGUSD`, indices `^GSPC`/`^VIX`, crypto `BTCUSD`).
4. **Composition taste**: 4–8 tiles; lead with the hero chart (`lg`); one odds tile beats three; always include a news tile for event widgets; `normalize` for any multi-symbol comparison; end topical widgets with a `text` context tile.
5. **Hard rules**: search the gallery first (`GET /widgets/gallery?q=`) and offer clone/remix before building from scratch; after `POST`, fetch `GET /widgets/{id}/data` and sanity-check every tile returned real data (no `error`/empty shapes) — fix symbols and retry before telling the user it's done; never publish without the user asking.
6. Exotic computations → compute in sandbox, embed as `inline` (with `asof`), and tell the user it's a snapshot.

### 3.9 Backend config

No new keys needed if FMP/FRED keys already in `core/config.py` (they are — fmp key confirmed; `FRED_API_KEY` per fred skill). Kalshi public market data needs no key. Nothing to add to `SKILL_ENV_KEYS` (skill talks to our own API via the always-injected `FINCH_API_URL`/`FINCH_AUTH_TOKEN`).

---

## 4. Frontend (web; mobile = follow-up, note in PR per parity convention)

### 4.1 Tile renderer — `frontend/components/widgets/`

- `WidgetCanvas.tsx` — takes `{spec, data}`; CSS grid `grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3`; maps `size` → spans; renders tiles.
- `tiles/ChartTile.tsx` — `PriceRangeChart` DataProps mode (`data: {date,value}[]` per series) — already supports multi-series, ranges, pct/currency formats.
- `tiles/StatTile.tsx` — styled after `IndexCard` (`components/home/HomePage.tsx` ~line 141): `bg-white rounded-2xl border border-gray-200 shadow-sm`, `font-numeric`, emerald/red delta, sparkline via a small `data[]`-prop variant of `MiniSparkline` (add `data?: number[]` prop to it — it's currently self-fetching only).
- `tiles/OddsTile.tsx` — big % + small history sparkline + close date. Kalshi prices display in cents per house style (`17¢ · 17%`).
- `tiles/NewsTile.tsx`, `tiles/TableTile.tsx`, `tiles/TextTile.tsx` (existing markdown renderer from chat).
- All tiles handle `error`/`empty` shapes with `EmptyState`-style fallbacks.
- Palette: light-only, `#fafaf9` page, white cards, emerald accents — copy `IndexCard`, don't invent.

### 4.2 In-app panel — `frontend/components/widgets/WidgetsPanel.tsx`

Pattern: `VisualizationsPanel.tsx`. Grid of widget cards (emoji, title, tag chips, view/clone counts, mini preview optional-v2) → click opens `WidgetView` (canvas + polling `widgetsApi.getData(id)` every `refresh.interval_seconds` while `document.visibilityState === 'visible'`; pause when hidden) with share/publish button (copies public URL), edit title, delete.

Wiring (four known touchpoints):
1. `contexts/NavigationContext.tsx` — add `{ type: 'widgets'; widgetId?: string }` to `View` union
2. `components/layout/AppLayout.tsx` — switch case + title map
3. `components/layout/AppSidebar.tsx` — `navItems` entry + inline icon component
4. `lib/api.ts` — `widgetsApi` namespace (axios instance pattern): `list, get, create, update, delete, publish, clone, getData, gallery, getShared, getSharedData`

### 4.3 Public page — `frontend/app/share/widget/[slug]/page.tsx`

Clone `app/share/chat/[token]/page.tsx` exactly (the good pattern — server component, `cache()`-wrapped anonymous fetch, `generateMetadata`, NOT the client-side viz share page):
- `generateMetadata`: title = widget title, description from widget description, OG image (below).
- Client child `SharedWidgetView.tsx`: renders `WidgetCanvas` with public data + polls `/widgets/shared/{slug}/data`; tracked CTAs (`track('shared_widget_viewed'|'shared_widget_cta_clicked')` via existing `initAnalytics`): sticky header "Try Finch" emerald button + fixed bottom banner "Made with Finch — live in 60s refresh" + **primary CTA "Clone this widget"** → `/?clone=<slug>` (post-auth: clone API + open widgets view; wire `clone` query param handling in AppLayout/AuthGate).
- Binding tiles show "Connect your portfolio to see yours" state — itself a CTA.
- **OG image**: `app/share/widget/[slug]/opengraph-image.tsx` with `next/og` `ImageResponse` — greenfield (nothing exists in codebase), keep simple: emoji + title + up-to-4 headline stats fetched from the public data endpoint, emerald-on-stone branding. This is the Reddit link preview — it matters.

---

## 5. Implementation order

Each phase leaves the app working; commit per phase.

1. **Backend core**: model + migration 089 + schemas (spec validation) + crud + routes + registration. *(No data service yet — `/data` returns 501.)*
2. **Data service**: fetchers (reuse existing FMP service code — find via the `/market/prices` route; httpx for Kalshi/FRED) + cache + transforms + binding resolution.
3. **Skill**: `backend/skills/widgets/SKILL.md` (auto-discovered, no registration).
4. **Frontend renderer + panel**: tiles, canvas, WidgetsPanel, nav wiring, `widgetsApi`.
5. **Public page**: share route + OG image + clone flow + analytics events.
6. **Seed content**: create 2–3 real widgets via the agent (Hormuz-style event tracker with a *current* event, a "Mag 7 earnings season" tracker, a portfolio widget) — these are both QA and the first Reddit posts.

## 6. Testing plan

**Backend unit (pytest, `backend/tests/test_widgets.py`):**
- Spec validation: valid specs pass; unknown fields/enum typos/13 tiles/oversize symbol lists rejected with readable messages (these errors are agent-facing prompts — assert the message names the bad tile id).
- Transforms: normalize/pct_change/spread/ratio/sort/limit on fixture series & tables, incl. mismatched-length series and empty series.
- Publish sweep: portfolio-bound spec publishes (symbolic ok); hypothetical concrete-ref query shape rejected; unpublish clears slug? (No — keep slug reserved so re-publish keeps URL; test that.)
- Cache: TTL expiry, per-key lock single-flight (two concurrent `resolve` → one upstream call; mock fetcher with a counter), eviction bound.
- Routes: auth required everywhere except `/shared/*`; owner-scoping (user B can't read/patch user A's private widget — 404); clone lineage + counts; public data with `viewer_user_id=None` → binding tiles empty-shaped.

**Data service integration (hits real APIs, marked `@pytest.mark.integration`, run manually):** one real resolve of the Hormuz example spec — every tile returns its declared shape, no `error` shapes; FMP commodity symbols actually resolve (this is where `BZUSD` vs `BZ=F` typos die).

**Frontend:** Playwright UX harness (`frontend/tests/` per existing setup): create-widget-via-API fixture → widgets panel renders all 6 tile types (use a fixture spec with an `inline` tile per shape so no live data needed) → publish → public page renders logged-out → clone CTA navigates. Visual sanity via harness screenshots.

**End-to-end agent test (manual, AFTER prod deploy):** ⚠️ **The E2B sandbox points `FINCH_API_URL` at prod Railway even in local dev** (`backend/.env` line ~59) — the skill will 404 against new routes until the backend is deployed (this exact thing bit `report_insight` in July). Sequence: deploy backend → in prod chat, prompt "make me a widget tracking <current event>" → verify the agent searches gallery, creates, self-checks data, and the widget renders. Alternatively point `FINCH_BACKEND_URL` at a tunnel for pre-deploy testing.

## 7. Verification checklist (for Anshul)

Fast path — after phases 1–2 (`cd backend && alembic upgrade head`, server running, `TOKEN` = a Supabase access token from the web app's network tab):

```bash
# create the Hormuz example (spec JSON in this doc §2.5)
curl -s -X POST localhost:8000/widgets -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d @docs/widgets/example-hormuz.json | jq .id
curl -s localhost:8000/widgets/<id>/data -H "Authorization: Bearer $TOKEN" | jq 'to_entries[] | {tile: .key, shape: .value.shape}'
# expect: every tile a real shape, no "error"
curl -s -X POST localhost:8000/widgets/<id>/publish -H "Authorization: Bearer $TOKEN" | jq .slug
curl -s localhost:8000/widgets/shared/<slug>/data | jq 'keys'   # no auth header — must work
```

Product path — after phase 5:
1. Sidebar → Widgets → see the seed widgets; open one; numbers tick on the refresh interval.
2. Chat: "make me a widget tracking gold vs bitcoin this year" → agent creates it without new tools, it appears in the panel, every tile has data.
3. Open the public URL logged out (incognito): live tiles, OG preview correct when pasted into Slack/Discord (or `curl -s <url> | grep og:`), Clone CTA → auth → widget in your collection.
4. The real test: create a topical widget for whatever is in the news *that day*, post the public link somewhere, and watch view_count move.

## 8. Phase 2 (committed, designed, not in v1): widget notifications

Widgets get a notion of alerts — "when key stuff happens, Finch notifies you." This is the retention hook on top of the widget surface (a widget you get pinged about is a widget you come back to).

**Design sketch:**
- New table `widget_alerts`: `id, widget_id, user_id, tile_id, condition (JSONB), channels (JSONB: push|email), cooldown_minutes, last_fired_at, enabled, created_at`.
- Condition v1 = threshold/crossing on things the tile already computes, e.g. `{"metric": "price"|"change_pct"|"prob", "symbol"|"ticker": ..., "op": ">"|"<"|"crosses", "value": 95}`. The agent creates alerts via the same widgets skill (`POST /widgets/{id}/alerts`) when the user says "and tell me if Brent goes above 95."
- **Evaluation is a background loop, unlike v1's view-driven refresh** — piggyback on the existing intraday monitor/heartbeat scheduler (`services/market_monitor.py` pattern), evaluating only widgets that have enabled alerts (so background cost scales with alerts, not widgets). Reuses the same `widget_data` fetch-cache, so an alert check and a viewer share upstream calls.
- Delivery via existing `services/notifications.py` (push mobile-first, email fallback) with cooldown to prevent spam; fired alerts also land in the `agent_events` ledger so they show in "while you were gone."
- Why not v1: needs the background evaluator + dedup/cooldown correctness; shipping v1 without it keeps the no-cron property and gets widgets in front of users a week earlier. Nothing in the v1 schema blocks it (alerts are a sibling table; `spec` unchanged).

## 9. v2 backlog (explicitly out of scope now)

- Sandbox-refreshed computed tiles (live arbitrary transforms; needs per-refresh sandbox budget + timeout sandboxing)
- Mobile parity (WidgetCanvas in RN; tile components map to existing mobile chart components) — note in PR per CLAUDE.md convention
- iOS home-screen widgets (WidgetKit + server-rendered payloads) — the retention thesis payoff
- Embeddable `<script>`/iframe embed for third-party sites (TradingView-style)
- Claude Code / Codex store skill (adaptation of `backend/skills/widgets/SKILL.md` against the public API with a PAT)
- Link groups (Koyfin-style click-symbol-retargets-tiles), gallery curation shelf ("Picks"), template-update-propagation (Flourish opt-in pull)
- Dynamic query-defined symbol lists ("top 5 movers in my watchlist" as a symbol source) — differentiator, nobody has it

## 10. Open questions (non-blocking, defaults chosen)

- **Kalshi ticker discovery**: agent finds contract tickers via the existing kalshi skill in-sandbox (default), vs a backend search param on the kalshi source. Default: skill-side.
- **Gallery in-app** (browse others' widgets inside Finch, not just via links): trivially enabled by `GET /widgets/gallery` — v1 ships the endpoint (agent needs it), UI shelf can wait.
- **Slug format**: `kebab-title-{4 random chars}` — readable for Reddit, unguessable enough for unlisted-ish behavior pre-publish. Sweep is what protects privacy, not the slug.
