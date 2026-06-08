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
| Chat file uploads (PDF/CSV) | ✅ | ❌ | Mobile has images only |
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
