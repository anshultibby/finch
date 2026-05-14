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
