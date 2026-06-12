# Finch — Development Notes

## Adding a new API key

When you add a new external API key to the project, you must update **three** places or it won't reach the E2B sandbox:

1. **`backend/core/config.py`** — add the field to `Settings` so it loads from `.env`
2. **`backend/.env`** — add the actual key value
3. **`backend/modules/tools/skills_registry.py` → `SKILL_ENV_KEYS`** — add the env var to the whitelist so `_build_sandbox_env()` forwards it to the sandbox

If you skip step 3, the key will be available on the backend server but **not** inside the E2B sandbox where skills and user code run.

Example entry in `SKILL_ENV_KEYS`:
```python
"MY_NEW_API_KEY": ("MY_SERVICE", "system"),
```

Use `"system"` for keys shared across all users (from `.env`). Use `"user"` for per-user keys stored in the DB.

## Where env values & secrets live (NOT committed)

All real values are in gitignored files / EAS — never hardcode them in tracked code.

**Mobile app production env (`EXPO_PUBLIC_*`):** source of truth for builds is **EAS env vars**, environment `production` (`cd frontend-mobile && eas env:list --environment production`). A local mirror lives in gitignored **`frontend-mobile/.env.production`**. `frontend-mobile/.env` holds the local-dev values (API URL = `localhost`).
- These must be set on EAS or the production build ships with an empty `EXPO_PUBLIC_SUPABASE_URL`, and `createClient('')` throws at module load → **crash on launch** (this caused the v1.0(20) App Store rejection).
- Production backend: `https://finch-production-8434.up.railway.app` (Railway).

**App Store reviewer / E2E test account:** credentials are `E2E_EMAIL` / `E2E_PASSWORD` in gitignored **`frontend/.env.local`**, **`backend/.env`**, and **`frontend-mobile/.env`**. `tests/auth.setup.ts` (web + mobile) reads them from env and throws if unset — no hardcoded fallback. When filling `frontend-mobile/APP_STORE_REVIEW.md` for a submission, paste the values from there; don't commit them.

## Adding / turning on a skill

A skill is a folder `backend/skills/<name>/` with a `SKILL.md` (frontmatter: `name`, `description`, `metadata`). It's auto-discovered — no registration. It syncs to the sandbox by content hash (no backend restart needed).

How it surfaces to the agent:
- **Always:** its one-line `description` appears in the all-skills list (in the `execute_code`/`bash` tool description).
- **`auto_on: true`** in `metadata` → also always in the system prompt's `<available_skills>` block. Omit it → the skill is only active when the user selects it for the chat.
- The full `SKILL.md` is **never** inlined; the agent reads it on demand. So put real usage detail in `SKILL.md` and keep `description` tight.

So: to make a new skill always available, set `auto_on: true`.

## Keeping Web & Mobile in Sync

The project has two frontends that must stay in parity:
- **Web**: Next.js in `frontend/` (App Router + Tailwind)
- **Mobile**: Expo/React Native in `frontend-mobile/` (Expo Router + NativeWind)

### Convention
When adding or changing a feature in one frontend, check whether the other needs a matching update. Note it in the PR description. Features should exist in both unless there's a platform-specific reason not to.

### Shared API Layer
Both frontends call the same backend. The API function names in `lib/api.ts` should match across web and mobile. When adding a new API endpoint, add the client function to both.

### Feature Parity Checklist

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
| Chat file uploads (PDF/CSV) | ✅ | ✅ | |
| Live task checklist (update_todos) | ✅ | ✅ | |
| Live thinking stream | ✅ | ✅ | Mobile shows pulsing tail line |
| Stream drop recovery (poll /chat/status) | ✅ | ✅ | Mobile also recovers on app foreground |
| Morning brief settings | ✅ | ✅ | |
| "Why is it moving?" AI chip (stock page) | ✅ | ✅ | `/insights/why/{symbol}`, cached server-side |
| Portfolio "Today" AI digest | ✅ | ✅ | `/insights/portfolio-digest`; watchlist fallback |
| Smart move alerts (push + why) | — | ✅ | `services/market_monitor.py`; push is mobile-only |
| App icon badge (unread) | — | ✅ | Mobile-only by nature |
| Swaps (tax-loss harvesting) | ✅ | ❌ | Complex feature |
| Visualizations gallery | ✅ | ❌ | Requires iframe/WebView |
| TradingView chart | ✅ | ❌ | Needs WebView embed |
| Agent peek panel | ✅ | ❌ | |
| Chat message pagination | ✅ | ❌ | |
| Email notification banner | ✅ | ❌ | |
| PDF export | ✅ | ❌ | |
| Earnings transcript | ✅ | ❌ | |
| Privacy page | ✅ | ❌ | |

## Chat Logs

Agent chat logs are saved locally at `backend/chat_logs/YYYYMMDD/<timestamp>_<chat_id>/master/`. Each chat directory contains:
- `messages.jsonl` — full message history (user, assistant, tool calls and results)
- `conversation.json` — conversation metadata
- `cache_diagnostics.jsonl` — prompt caching stats
- `code_executions/` — sandbox execution logs

Use these to debug agent behavior (e.g., which tools the model called, truncated outputs, etc.).
