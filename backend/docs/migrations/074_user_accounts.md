# Migration 074 — `user_accounts` (split account/billing off `snaptrade_users`)

## Why

`snaptrade_users` was the first per-user table, so credits, plan, and Stripe
fields got bolted onto it over time (migrations 062, 064, 069). But that row is
only created when a user **connects a broker** (`crud/snaptrade_user.create_user_async`,
called from `modules/tools/clients/snaptrade.py`).

Consequences observed in prod (super-alpha):

- `auth.users` had 20 rows; `snaptrade_users` had 10. **Half the users had no
  account row at all.**
- Every credit write (`deduct_credits`, `add_credits`, `set_user_plan`,
  `set_subscription_info`, `set_stripe_customer_id`) is `UPDATE … WHERE user_id = …`,
  so for those users it matched zero rows and **silently no-op'd**.
- A user who paid via Stripe but never connected a broker would have the webhook
  call `set_user_plan('pro')` / `add_credits(...)` against a non-existent row and
  **get nothing**.

Supabase's `auth.users` is the canonical identity table, but it's managed by
Supabase Auth — you don't add app columns there. The standard pattern is a
`public` table keyed by `auth.users.id`, provisioned by an on-signup trigger.

## Target shape

```
auth.users            (Supabase-managed: identity only)
   │ id
   ▼
public.user_accounts  (NEW: credits, total_credits_used, last_credit_refresh,
   │                        plan, stripe_customer_id, stripe_subscription_id,
   │                        subscription_status, cancel_at_period_end,
   │                        current_period_end)
   ▼
snaptrade_users       (broker connection ONLY: snaptrade_user_id/secret,
                        connected_account_ids, is_connected, brokerage_name)
```

`user_settings`, `user_skills`, `user_sandboxes`, `user_watchlist` already key off
the same auth id and are unaffected.

## What the migration does (`alembic/versions/074_user_accounts.py`)

1. Creates `public.user_accounts` (PK `user_id` = auth id as text, to match every
   sibling table; no cross-schema FK, consistent with the existing schema and to
   avoid any cascade risk to other tables).
2. **Backfill A** — copies every existing `snaptrade_users` row's billing/credit
   columns into `user_accounts` (preserves current balances).
3. **Backfill B** — inserts a default row (`plan='free'`, `credits=1000`) for every
   `auth.users` id that doesn't already have one (the broker-less users).
4. Creates `public.handle_new_user()` + `on_auth_user_created` trigger on
   `auth.users`. Wrapped in an exception guard so the migration still succeeds if
   the migration role can't create triggers on the `auth` schema — the lazy
   ensure (below) covers correctness either way.
5. Drops the nine moved columns from `snaptrade_users`.

`downgrade()` re-adds the columns and best-effort restores values from
`user_accounts` before dropping the new table/trigger.

## App-layer changes

- `models/user.py` — new `UserAccount` model; moved columns removed from
  `SnapTradeUser` (now broker-connection only).
- `services/credits.py` — all queries repointed `SnapTradeUser → UserAccount`.
  New `CreditsService._ensure_account(db, user_id)` (`INSERT … ON CONFLICT DO
  NOTHING`, defaults to `DEFAULT_NEW_USER_CREDITS` / `free`) is called at the top
  of every **write** (`deduct_credits`, `add_credits`, `set_stripe_customer_id`,
  `set_subscription_info`, `set_user_plan`). Reads stay pure and keep the
  free-tier default fallback.
- `routes/credits.py` — the three direct `select(SnapTradeUser.…)` reads (balance,
  cancel-subscription, resubscribe) repointed to `UserAccount`.

Response shapes (`CreditBalanceResponse`, webhook) are unchanged → **no frontend
or mobile changes required.**

## Safety / scope

- **User chats are never touched.** Tables in scope: `user_accounts` (new),
  `snaptrade_users` (drop columns), `auth.users` (add trigger only).
- 0 paying customers at migration time, so no live Stripe data is at stake; the
  only real data preserved is credit balances, handled by Backfill A.

## Rollout

```bash
cd backend
alembic upgrade head      # applies 074
# verify:
#   - select count(*) from user_accounts;            -> == count(*) from auth.users
#   - spot-check credits for known users
#   - \d snaptrade_users                              -> billing columns gone
```
