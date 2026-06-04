# Finch Connect

A small, auditable desktop app that links your **Robinhood Agentic** account to Finch.
Sign in to Finch with Google, click Connect — no tokens to copy, nothing stored on disk.

## Why a desktop app?

Robinhood's agent OAuth has two hard constraints (both verified against their live API):

1. **Consent renders only in a desktop browser** — the mobile/in-app consent page 404s. Robinhood's own docs say agent onboarding must happen on desktop.
2. **The redirect must be loopback** (`http://127.0.0.1:PORT`). Robinhood's agent client is fixed and bound to a loopback redirect; hosted `https://` and custom-scheme redirects are rejected with *"Mismatching Redirect URI."*

A loopback redirect can only be caught on the machine where consent completes → that machine must be a desktop. So this is the **only** shape that works (it's how Claude Code / Cursor connect too). On mobile, Finch uses SnapTrade for Robinhood instead.

## Trust model

- **Your passwords never touch this app.** Google sign-in happens on Google; Robinhood access is granted on robinhood.com.
- **Loopback is local-only** (`127.0.0.1:8765`), accepts one redirect, then closes.
- **No tokens on disk.** The Finch session lives in memory for the app's lifetime; Robinhood tokens are exchanged and stored by *your* Finch backend.
- **Every network destination is a named constant** at the top of [`src-tauri/src/lib.rs`](src-tauri/src/lib.rs) — two readable OAuth flows, no hidden calls.

## How it works

```
[ 1. Continue with Google ]   → Supabase/Google consent in your browser
                              → loopback catches the code → Finch session (in memory)
[ 2. Connect Robinhood ]      → register agent client → robinhood.com consent
                              → loopback catches one-time code
                              → POST to your Finch backend  /robinhood/native/exchange
                              → backend exchanges + stores tokens server-side
```

## One-time setup (Supabase redirect allow-list)

Google sign-in uses the same loopback pattern, so Supabase must allow the desktop
redirect — otherwise it falls back to the web Site URL. In the Finch Supabase project:

**Authentication → URL Configuration → Redirect URLs**, add:

```
http://127.0.0.1:8765/finch-callback
http://127.0.0.1:8765/**
```

## Run it (dev)

```bash
# one-time: Rust toolchain
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
source "$HOME/.cargo/env"

npm install
npm run tauri dev
```

## Build a distributable

```bash
npm run tauri build
# → src-tauri/target/release/bundle/  (.app/.dmg on macOS, .msi/.exe on Windows, .deb/.AppImage on Linux)
```

For real distribution, **code-sign + notarize** (macOS) / sign (Windows) so users get no "unidentified developer" warning — important for a finance app.

> Backend dependency: `POST /robinhood/native/exchange` (`backend/routes/robinhood.py`) plus the `resource` indicator on the token exchange (`backend/services/robinhood_auth.py`).
