# Web ↔ Mobile feature parity

Two frontends must stay in parity:
- **Web**: Next.js in `frontend/` (App Router + Tailwind)
- **Mobile**: Expo/React Native in `frontend-mobile/` (Expo Router + NativeWind)

**Convention.** When adding or changing a feature in one frontend, check whether the other
needs a matching update, and note it in the PR description. Features should exist in both
unless there's a platform-specific reason not to.

**Shared API layer.** Both call the same backend; function names in `lib/api.ts` should
match across web and mobile.

## Checklist

| Feature | Web | Mobile | Notes |
|---------|-----|--------|-------|
| Google OAuth login | ✅ | ✅ | |
| Chat (streaming + tools) | ✅ | ✅ | |
| Markets (movers, news) | ✅ | ✅ | |
| Market region toggle (US/India) | ✅ | ✅ | |
| Index cards with sparklines | ✅ | ✅ | |
| Watchlist with sparklines | ✅ | ✅ | |
| Earnings calendar | ✅ | ✅ | |
| Portfolio (SnapTrade multi-broker) | ✅ | ✅ | |
| Stock detail (overview, stats, peers) | ✅ | ✅ | |
| Financials (5 statement types) | ✅ | ✅ | |
| Earnings tab | ✅ | ✅ | |
| News tab | ✅ | ✅ | |
| Analysis tab (grades, AI notes) | ✅ | ✅ | |
| Trades tab (order history) | ✅ | ✅ | |
| Holdings display on stock page | ✅ | ✅ | |
| Trade modal (buy/sell) | ✅ | ✅ | |
| Orders page | ✅ | ✅ | |
| Message actions (copy, feedback) | ✅ | ✅ | |
| Tool call expansion (view output) | ✅ | ✅ | |
| Sidebar/drawer navigation | ✅ | ✅ | |
| "Automation runs" sidebar section | ✅ | ✅ | Collapsed by default, fetched on first open; `GET /chat/user/{id}/chats?source=automation`. Run chats are `job-{job_id}-r{n}` and carry no title, so the automation's name stands in |
| Chat file uploads (PDF/CSV) | ✅ | ✅ | |
| Live task checklist (update_todos) | ✅ | ✅ | |
| Live thinking stream | ✅ | ✅ | Mobile shows pulsing tail line |
| Multiple reasoning cards per turn (live) | ✅ | ❌ | Backend persists per-round reasoning (each tool round + final answer), so both show multiple collapsed cards **after reload**. Web also shows them live: `saveTools` folds each round's thinking onto its committed message. Mobile still lumps all tool rounds into one message and keeps only the last round's reasoning live — needs a stream-hook restructure to commit per-round |
| Stream drop recovery (poll /chat/status) | ✅ | ✅ | Mobile also recovers on app foreground |
| Morning brief settings | ✅ | ✅ | |
| Pro subscription | ✅ | ✅ | Web = Stripe; iOS = Apple IAP (RevenueCat). See `docs/iap-setup.md` |
| "Why is it moving?" AI chip (stock page) | ✅ | ✅ | `/insights/why/{symbol}`, cached server-side |
| "While you were gone" recap + agent ledger | ✅ | ✅ | `/activity/recap`; `agent_events` table; mobile full ledger at `/activity` |
| In-app trade approval (hold-to-approve) | ✅ | ✅ | `/trades/pending` + approve/reject; email links remain as fallback |
| Heartbeat (agentic portfolio/news watch) | ✅ | ✅ | Settings toggle + interval; spends credits (not comped); Pro = minute-level interval, free = daily |
| Tasks (agent's long-running work) | ✅ | ✅ | One markdown file per task at `tasks/{slug}.md` with YAML frontmatter (status/opened/symbols/review); syncs to `agent_tasks` via the same hook pattern as stock analysis. Read-only API — the file is the source of truth, so users steer tasks by asking the agent. See `skills/library/SKILL.md` |
| Widgets (agent-built live dashboards) | ✅ | ✅ | Declarative JSON spec + fixed tile renderer; `/widgets` API + `skills/widgets`; public share page `/share/widget/[slug]` w/ OG + clone CTA; view-driven refresh cache; per-tile source citations. **Replaced the old Visualizations gallery** (deleted Aug 2026). Mobile parity shipped Aug 5 2026: `frontend-mobile/components/widgets/` (SVG charts, WebView Plotly for `chart_spec`), list/detail screens under `app/widgets/`, Sidebar entry; publish→share sheet (web share URL); edit-via-chat-drawer is web-only. See `docs/widgets/spec.md` |
| Portfolio "Today" AI digest | ✅ | ✅ | `/insights/portfolio-digest`; watchlist fallback |
| Trade feedback (review a recent trade) | ✅ | ✅ | Agent-driven via the `trade_feedback` skill: home "Review my trades" entry seeds a chat → skill pulls trades (`finch_api.get_recent_trades` → `GET /trades/recent`, unified SnapTrade `Transaction` + Robinhood filled orders), shows a ranked table, asks which to dig into, then critiques it + suggests alternatives. Realized-P&L ranking deferred |
| Smart move alerts (push + why) | — | ✅ | `services/market_monitor.py`; push is mobile-only |
| App icon badge (unread) | — | ✅ | Mobile-only by nature |
| Swaps (tax-loss harvesting) | ✅ | ❌ | Complex feature |
| TradingView chart | ✅ | ❌ | Needs WebView embed |
| Agent peek panel | ✅ | ❌ | |
| Chat message pagination | ✅ | ❌ | |
| Email notification banner | ✅ | ❌ | |
| PDF export | ✅ | ❌ | |
| Earnings transcript | ✅ | ❌ | |
| Privacy page | ✅ | ❌ | |
