# Finch UX/UI test harness

Playwright-based harness for **exploratory UX review** (screenshots an agent or
human studies) and **regression assertions** (clean console, no 5xx, key flows
work).

## Run

```bash
npm run e2e          # full suite (auto-starts/reuses dev server on :3000)
npm run e2e:ux       # just the visual landing + app-tour pass
npm run e2e:headed   # watch it drive the browser
npm run e2e:report   # open the HTML report — screenshots inline
```

## Test login (credentials)

Login is **Supabase email/password** (not Google OAuth) via the gate in
`components/PasswordGate.tsx`. The login flow lives in **`auth.setup.ts`**, which
signs in once and saves the session to `.auth/user.json` for the `app` project.

| Where | Variables | Notes |
|-------|-----------|-------|
| `frontend/.env.local` | `E2E_EMAIL` / `E2E_PASSWORD` (+ `TEST_EMAIL` / `TEST_PASSWORD`) | Read by `auth.setup.ts`; gitignored |
| `backend/.env` | same | Mirrored for backend/manual use; gitignored |
| `frontend-mobile/.env` | same | For mobile Playwright; gitignored |

The shared review/test account credentials are **not committed** — they live in
the gitignored env files above as `E2E_EMAIL` / `E2E_PASSWORD`. `auth.setup.ts`
throws if they're unset. To log in manually, open `localhost:3000` and enter
those values in the email/password gate.

## Layout

| File | Purpose |
|------|---------|
| `playwright.config.ts` | 3 projects: `setup` (login) → `public` (no auth) + `app` (authed) |
| `auth.setup.ts` | Logs in via Supabase email/password once, saves session to `.auth/user.json` |
| `helpers/ux.ts` | `snap()`, `snapResponsive()`, `watchHealth()` — screenshot + health utils |
| `*.public.spec.ts` | Tests that run without auth (landing/gate) |
| `*.app.spec.ts` | Tests that reuse the saved session |
| `__shots__/` | Flat, reviewable screenshots (gitignored) |
| `__report__/` | HTML report with inline screenshots (gitignored) |

## Conventions

- **Naming decides the project.** `foo.public.spec.ts` runs unauthenticated;
  `foo.app.spec.ts` runs with the saved session. Anything else (`foo.spec.ts`)
  isn't picked up by a project — add a matcher first.
- **Screenshots are the product.** Use `snap(page, testInfo, 'name')` so shots
  land in `__shots__/<spec>/` *and* attach to the HTML report.
- **Health, two tiers.** `health.assertClean()` hard-fails only on JS crashes
  and 5xx. `health.warn(testInfo)` surfaces console errors + 4xx/404s as
  non-fatal warnings (keeps the suite from flaking on benign noise).
- **Selectors:** prefer `getByRole` / `getByPlaceholder` with *specific* text.
  A loose `/search/i` will match the sidebar chat search before the stock bar.
