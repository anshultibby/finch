# Finch

**An AI financial analyst that knows your actual portfolio.**

Finch is a chat-first research platform for stocks and markets. Connect your brokerage (read-only, via SnapTrade — 30+ brokers supported) and Finch can analyze *your* holdings, not hypothetical ones: concentration, sector tilt, fee drag, earnings coming up on positions you own. It runs real Python in a sandbox for analysis and visualizations, and can set standing scheduled jobs ("alert me if NVDA drops below $200") that notify you by email or push.

Live at [finchapp.ai](https://finchapp.ai) · iOS app via Expo/EAS.

## What it does

- **AI research chat** — Claude-powered agent with streaming, tool use, and a code sandbox (E2B). Deep research across fundamentals (FMP), prices (Polygon), options analytics (ORATS), Reddit sentiment, earnings drift, biotech pipelines, and Indian markets (NSE/BSE).
- **Portfolio sync** — read-only brokerage connection through SnapTrade; positions, transactions, P&L, portfolio health checks.
- **Markets** — movers, news, earnings calendar, index cards, watchlist with sparklines, US/India toggle.
- **Stock pages** — financials (5 statement types), earnings history, news, analyst grades, AI research notes.
- **Scheduled jobs** — recurring or one-off agent tasks with email/push notifications; trade automations gated behind one-click email approval.
- **Visualizations** — agent-generated interactive charts (Plotly, D3, etc.) in a gallery.

## Architecture

| Piece | Stack | Where |
|---|---|---|
| Backend | FastAPI + SQLAlchemy (async) + PostgreSQL (Supabase) | `backend/` |
| Web | Next.js (App Router) + Tailwind | `frontend/` |
| Mobile | Expo / React Native + NativeWind | `frontend-mobile/` |
| Agent sandbox | E2B (per-user sandboxes, skill scripts) | `backend/skills/`, `backend/modules/tools/` |
| Auth | Supabase (Google OAuth + email/password) | |
| Billing | Stripe (Pro subscription + credit top-ups) | `backend/routes/credits.py` |

Skills are self-contained folders in `backend/skills/<name>/` with a `SKILL.md`; they're auto-discovered and synced to the sandbox by content hash. See `CLAUDE.md` for development conventions (adding API keys, skills, web/mobile parity).

## Running locally

Prereqs: Python 3.13+, Node 18+, a `backend/.env` (see `backend/.env.example`).

```bash
./setup.sh            # one-time: venv + pip + npm installs
./start-backend.sh    # FastAPI on :8000
./start-frontend.sh   # Next.js on :3000
./start-mobile.sh     # Expo dev server
```

Backend env lives in `backend/.env`, web in `frontend/.env.local`, mobile in `frontend-mobile/.env` — all gitignored. Production mobile env is managed in EAS (`eas env:list --environment production`).

## Deployment

- **Backend**: Railway (`finch-production-8434.up.railway.app`)
- **Web**: Vercel ([finchapp.ai](https://finchapp.ai))
- **Mobile**: EAS Build → App Store
- **DB/Auth/Storage**: Supabase; migrations via Alembic (`backend/alembic/`)

## Disclaimer

Finch is for research and information only. It is not financial advice, and nothing it produces should be treated as a recommendation to buy or sell securities.
