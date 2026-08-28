# Community Strategies — research & build plan

*Aug 2026. New product direction: pitch Finch to founders of retail trading communities
(Discord/Reddit) as (a) the place to distill their trading style into a runnable strategy,
and (b) the tooling to share that strategy with their members, who run it on their own
accounts. Sister doc to `hedge-fund-gtm-research.md`.*

---

## 0. The thesis in one paragraph

Retail trading is fragmenting into thousands of Discord/Reddit sub-communities, each running
its own style. Today the founders of those communities sell **access** (Whop handles
payments + Discord roles) but have no way to turn their *style* into something a member can
actually run. Finch's wedge is the layer Whop doesn't touch: **turn a community's trading
style into an executable, personalized, backtestable strategy that runs in each member's own
account, with per-user risk limits and hold-to-approve execution.** Whop sells the door;
Finch is what's behind it.

Two capabilities make this real:
- **A shared search/ingestion engine** — look at Reddit/Discord/X/web *inside Finch*, both
  as a user-facing surface and as agent tools (§3).
- **Strategy-as-skill** — a strategy is a first-class *skill*: authorable, publishable,
  installable, and run by the agent. Requires rewriting the skill substrate to be DB-backed
  and per-user (§4, the deep Phase-1 plan).

---

## 1. The reframe forced by platform + regulatory constraints

Two hard constraints shape the product. Neither is a blocker; both change the *shape*.

### 1a. Ingestion must be consent-based, but reading ≠ training

The distinction that matters (corrected from an earlier over-cautious take):

- **Allowed, normal API use:** reading Reddit through the official API and *showing it to a
  user in-app*, searching it, and summarizing the thread the user is looking at. This is not
  what the Anthropic/Perplexity lawsuits were about — those were *bulk scraping to train
  models*. Live "fetch → show/summarize for the viewer" is a standard API consumer.
- **The real constraints are access + rate, not permission:** Reddit's free Data API tier is
  ~100 queries/min and is *non-commercial*; a paid/monetized product needs a Data API
  contract (~$0.24/1k calls, enterprise bundle $12k/mo). Plan for the contract when Finch
  monetizes this — it is not a reason to delay building.
- **The one thing to avoid:** a background pipeline that *hoards* Reddit content into a
  stored, redistributable corpus you derive a model from. Keep ingestion **per-request and
  live**, not a standing crawler. (This is also just good architecture — see §3.)
- **Discord** bans self-bots/user-bots; a bot must be *invited* to a server and reads
  messages via the privileged Message Content intent (verification required past 100
  servers). So Finch can't lurk — the **organizer invites a Finch bot into their own
  server**. This flips ingestion from scraping strangers to a consented integration, and
  drops Finch *inside* the community in front of paying members (distribution).
- **X/Twitter** API is expensive/gated but exists; treat as a later source behind the same
  engine.

**Net:** ingestion is consent-based and live. The organizer-invited Discord bot is the
cleanest "participate in the community" path; Reddit/web are on-demand reads.

### 1b. "Sharing strategies" is the exact activity the SEC is fining

Signals / "actionable advice" are being treated as unregistered investment advice;
*personalized* advice triggers investment-adviser (RIA) registration. 2024 penalties:
M1 Finance $850k, TradeZero $250k, nine advisers $1.2M — all finfluencer-content
supervision failures.

**The defensible framing, baked into the architecture:** a strategy is a *rules/tools/
education object* that **each member's own Finch runs against their own portfolio**, with
per-user risk limits and hold-to-approve execution — **not** a broadcast signal that gets
auto-copied. The publish step strips the author's personal account references (the widget
"publish sweep" mechanism, §4) so the strategy *rebinds to whoever installs it*. That is the
line between "software + education" (fine) and "unregistered advisory / copy-trading"
(RIA territory).

The regulated copy-trading lane (dub, Collective2, eToro CopyTrader) exists but requires
*being or partnering with an RIA* — a later door, not the wedge. Resist the "auto-copy the
founder's trades" ask; it is both the regulatory trap and the liability trap.

### 1c. Don't rebuild Whop

Whop owns payments/access/roles on Discord (3% + processing; $100–250/mo memberships are
standard). Complement it — be the strategy *engine* behind their paywall, or integrate
(gate strategy install behind a Whop role). Monetize via Finch subscription / rev-share,
framed as a *tool subscription*, never a performance fee on advice.

---

## 2. What already exists in Finch (the good news)

| Need | Existing primitive | Files |
|---|---|---|
| Packaged agent capability | **Skills** (disk folders: `SKILL.md` + `scripts/`) | `backend/skills/*`, `modules/tools/skills_registry.py` |
| DB-backed *shareable* skills | **Built once, dropped** — precedent to rebuild | migrations `025`–`027` (created), `029` (dropped) |
| Share / clone / gallery / public page | **Widgets** — the strongest analogue | `models/widget.py`, `routes/widget.py`, `crud/widget.py`, `frontend/app/share/widget/[slug]/` |
| Per-user recurring agent execution | **ScheduledJob** + waker + `routines`/`day_trading` skills | `models/jobs.py`, `routes/jobs.py`, `services/job_scheduler.py`, `services/system_jobs.py` |
| "Shape the agent around a goal" | **UserGoal → `<mission>` injection** | `models/user.py::UserGoal`, `crud/user_goals.py`, `agent_config.py::_get_goal_directive` |
| Rules-based trading w/ risk + approval | **`day_trading` skill** (RiskBudget, decision-points, hold-to-approve) | `backend/skills/day_trading/` |
| Reddit reads (official API) | **`reddit` skill** (PRAW, `REDDIT_CLIENT_ID/SECRET`) | `backend/skills/reddit/` |
| Web / news / scrape | **Serper tools** | `modules/tools/implementations/web_search.py` |
| External text → cached shared artifact | **why-engine** pattern | `services/move_explainer.py`, `routes/insights.py` |
| File upload into sandbox | `POST /{chat_id}/upload` | `routes/chat_files.py` |

**The three real gaps:**
1. Skills are **disk-only + global-sync** (every disk skill uploads to every user). No
   authoring, no per-user install, no sharing. → the §4 rewrite.
2. Search is **agent-only** — no user-facing surface, no unified multi-source engine. → §3.
3. **No Discord integration** anywhere in the tree. → Phase 2.

---

## 3. Capability A — the shared search / ingestion engine

**Decision: one engine, two consumers** (user-facing surface + agent tools), sources
Reddit / Discord / X / web. Ingestion stays per-request and live (§1a).

### 3a. The engine

New `services/search_engine.py` (or `modules/search/`) exposing a normalized result shape:

```
SearchResult { source, id, url, author, title, body, ts, score, subreddit/channel, ... }
```

Source adapters, each behind a common interface:
- **reddit** — wrap the existing `reddit` skill's PRAW client; add `search_subreddits(q)`,
  `read_thread(id)`, `hot/top(subreddit)`. Official API, already authed.
- **web / news** — reuse `web_search_impl` / `news_search_impl` / `scrape_url_impl` (Serper).
- **discord** — organizer-invited bot (Phase 2); reads only designated channels.
- **x** — later; gated API behind the same interface.

Rate-limit + cache per source (Redis or the existing per-symbol cache pattern from
`move_explainer`). **No persistent corpus** — cache TTL only, keeps Reddit terms clean.

### 3b. Consumer 1 — agent tools

- Extend the `reddit` skill with search/read-thread/per-community pulls.
- Optionally add a `search` tool that fans out across sources, so in-chat "what's r/options
  saying about NVDA earnings" resolves through the engine.

### 3c. Consumer 2 — user-facing surface

- Route `GET /search?q=&sources=reddit,web,news` → normalized results.
- Frontend: a search box + feed (threads/posts/articles), open-to-read, with a one-tap
  **"Distill this into a strategy"** action that hands the selected content to the agent →
  produces a draft Strategy skill (§4). This is the funnel from *browsing a community* to
  *packaging its style*.
- Web ↔ mobile parity (per root `CLAUDE.md`): ship the surface on both or note the gap in
  `docs/feature-parity.md`.

---

## 4. Capability B — Strategy-as-skill (deep Phase-1 plan)

**Decision: a strategy IS a skill, and the skill substrate gets rewritten** to be DB-backed,
authorable, and per-user installable. This reuses the dropped `025`–`027` schema as
precedent and borrows the widget sharing mechanics.

### 4a. Skill substrate rewrite — two origins

- **System skills (unchanged):** disk folders, auto-discovered, `is_system`, `auto_on`.
  These are platform capabilities (`day_trading`, `reddit`, `widgets`, `finch_api`, …).
- **User/community skills (new, DB-backed):** authorable rows. **A Strategy is a user skill
  with `category = "strategy"`** carrying a structured `spec` plus a `SKILL.md` body telling
  the agent how to run it.

### 4b. Data model — new migration (`097+`; goals were `096`)

Recreate a `skills` table for user/community skills (system skills stay on disk), with
widget-style sharing columns merged in:

```
skills
  id            uuid           -- pk
  user_id       str  idx       -- author/owner
  source_id     str  null      -- FK to the skill this was installed/cloned from (lineage)
  category      str            -- "strategy" | "tool" | ...
  name          str
  description   str
  emoji         str  null
  tags          jsonb null
  spec          jsonb null     -- for strategies: watchlist/entry/exit/risk/sizing/cadence
  content       text           -- the SKILL.md markdown body (agent reads on demand)
  version       int            -- bumped on edit; drives per-user re-sync
  visibility    str            -- "private" | "public"   (default private)
  slug          str  uniq null -- minted on publish
  install_count int
  view_count    int
  created_at / updated_at
skill_files            -- multi-file strategies (scripts), mirrors dropped migration 027
  id, skill_id (fk), path, content
```

Keep the existing slim `user_skills(user_id, skill_name, enabled)` **only** as the
on/off toggle for *system* skills; installed user-skills are rows above (installed == a row
owned by `user_id` with `source_id` set).

### 4c. Routes — clone the widget router (`routes/widget.py` is the template)

New `routes/skills.py` (authoring + sharing; system-skill discovery stays where it is):

| Route | Mirrors widget | Behavior |
|---|---|---|
| `POST /skills` | `create_widget` | author a private user skill / strategy |
| `GET /skills` | `list_widgets` | my skills |
| `PATCH /skills/{id}` | `update_widget` | edit; bump `version` |
| `POST /skills/{id}/publish` | `publish_widget` | mint `slug`, run **publish sweep** (§4e) |
| `POST /skills/{id}/clone` | `clone_widget` | **install** a public strategy onto current user (copy row, set `source_id`, `install_count++`) |
| `GET /skills/gallery?q=&sort=` | `gallery` | discover public strategies |
| `GET /skills/shared/{slug}` (no auth) | `get_shared_widget` | share page payload (OG + CTA) |

Auth pattern: trust the JWT only; ignore the sandbox client's `user_id` query param
(same note as `routes/widget.py`). 404 (not 403) for private rows so they're
indistinguishable from missing.

Frontend share page: clone `frontend/app/share/widget/[slug]/` →
`frontend/app/share/strategy/[slug]/` with OG image + "Run this in Finch" CTA (the
morning-brief share page is the other precedent).

### 4d. Per-user sandbox sync — **the main infra rewrite**

Today `code_execution.py::_upload_skills` + `_compute_skills_hash_from_fs` upload **all disk
skills to every user**, hash stored on `user_sandboxes.skills_hash`. Change to:

- **Effective skill set for a user** = system disk skills **+** the user's installed
  user-skill rows (materialized to `/home/user/skills/<name>/` from `content` + `skill_files`).
- **Hash** becomes per-user: `hash(system disk hash + sorted[(installed skill id, version)])`.
  Re-sync only when that changes (a new install or an author edit bumping `version`).
- Materialize DB skills into the sandbox alongside disk skills; the agent's on-demand
  `read_chat_file` of `SKILL.md` is unchanged.

This is the one genuinely new piece of infra. Everything else is CRUD + reuse.

### 4e. Publish sweep — the regulatory-defensible core

Mirror the widget publish sweep: on publish, strip the author's concrete account references
so the strategy's data sources are **symbolic** (`user_portfolio` / `user_watchlist`) and
resolve per-viewer. Result: an installed strategy runs against **the member's** portfolio,
sizing off **the member's** risk settings — never a copy of the author's live trades. This
is what keeps it on the software/education side of §1b.

### 4f. Execution — reuse ScheduledJob + goal injection (no new execution infra)

Installing a strategy can, with the member's consent:
- write a `UserGoal` (`crud/user_goals.py::set_goal`, `kind` e.g. `"grow"`, `config` holding
  the strategy id + watchlist) so the `<mission>` block shapes every session; and/or
- provision a `ScheduledJob` ("run <strategy> decision-points each market morning", bound to
  `user_id`) via `schedule_job` → `POST /jobs`. The `day_trading` skill already executes
  rules-based decision-points with a journal-backed RiskBudget and hold-to-approve trades,
  so a running strategy is just a routine over that machinery.

### 4g. Authoring — how a strategy gets created

Three on-ramps, all producing a private `category="strategy"` skill row:
1. **Conversational** — "Finch, package my strategy: …" → agent writes `SKILL.md` + `spec`.
   (Reuse the `GoalWizard.tsx` / `GoalGate.tsx` pattern for a `StrategyWizard` UI.)
2. **Distill from content** — the "Distill this into a strategy" action from the §3 search
   surface, or from an uploaded playbook/CSV of past calls (`routes/chat_files.py`).
3. **Distill from Discord** — the organizer-consented bot reads their `#alerts`/pinned
   playbook and the agent distills a spec (Phase 2).

Distillation target (the `spec`): universe/watchlist, entry triggers, exit/stop rules,
position sizing, risk-per-trade, cadence, options on/off — the same shape `day_trading`
already consumes.

---

## 5. Phasing

- **Phase 0 — validate distillation (no new infra, days).** Organizer pastes their playbook
  in chat → agent distills a spec → provisions a `ScheduledJob` + `UserGoal` on *their own*
  account. Proves the distillation quality with zero platform work.
- **Phase 1 — Strategy-as-skill (§4).** Skill substrate rewrite (DB-backed rows +
  per-user sandbox sync) + publish/clone/gallery/share-page cloned from widgets + install →
  routine wiring. Shippable MVP of "organizers author, members install & run."
- **Phase 1.5 — search engine + user surface (§3).** Unified Reddit/web engine, agent tools,
  and the user-facing search + "distill this" funnel.
- **Phase 2 — Discord integration.** Organizer-invited bot: Message Content intent, distill
  from designated channels, post P&L recaps back into the server (the Sinux/pickmytrade
  "branded recap after close" pattern) — the "participate" piece and the distribution channel.
- **Phase 3 — monetization + regulatory wrapper.** Stripe rev-share, Whop role integration,
  disclaimers/ToS, and the RIA question if copy-execution is ever pursued.

---

## 6. Risks & non-negotiables

1. **SEC/FINRA advisory line (§1b)** — stay "software + education + backtestable rules the
   member's own account runs." Never "here's a personalized trade, we placed it." The
   publish-sweep rebind (§4e) + hold-to-approve are the technical guardrails.
2. **Reddit access** — reading/showing is fine; a stored corpus is not (§1a). Free tier is
   non-commercial; budget a Data API contract at monetization.
3. **Discord Message Content intent** — privileged, needs app review past 100 servers; plan
   for the verification process.
4. **Auto-execution liability** — keep hold-to-approve; resist "auto-copy the founder."
5. **Don't rebuild Whop** — complement/integrate, be the engine (§1c).

---

## 7. Open questions

- Whop integration depth — gate strategy install behind a Whop role, or fully independent?
- Backtesting: do strategies ship with a backtest before a member can install? (strong trust
  signal, and reinforces the "tool not advice" framing).
- Strategy versioning UX — when an author edits a published strategy, do installs auto-update
  (via §4d `version`) or pin?
