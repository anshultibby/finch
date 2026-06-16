# In-App Purchase setup (Apple / RevenueCat) — Finch Pro

This is the manual, dashboard-side setup that the code can't do. It backs the
iOS **Finch Pro** subscription required by App Store **Guideline 3.1.1** (paid
digital content must be purchasable via In-App Purchase).

Architecture: the iOS app sells the subscription through **RevenueCat**
(`react-native-purchases`). RevenueCat validates the App Store receipt and POSTs
lifecycle events to the backend (`POST /credits/revenuecat-webhook`), which flips
`user_accounts.plan` to `pro` and grants credits. The backend stays the single
source of truth across web (Stripe) and iOS (Apple) — `subscription_provider`
records which one owns the active grant.

> ⚠️ None of this works until the Apple Developer account is enrolled as an
> **Organization** (Guideline 5.1.1(ix)) and the app is renamed off "Finch"
> (Guideline 4.1(b)). Those two gates block the submission regardless of IAP.

---

## 1. App Store Connect — create the subscription product

1. **My Apps → (the app) → Subscriptions** → create a **Subscription Group**
   (e.g. "Finch Pro").
2. Add an **auto-renewable subscription**:
   - **Reference Name:** Finch Pro Monthly
   - **Product ID:** `ai.finchapp.mobile.pro.monthly` (record this — used in RevenueCat)
   - **Duration:** 1 month
   - **Price:** $19.99 (closest tier to the $20 web price)
3. Add a **localization** (display name + description) and a **subscription
   review screenshot** — required or the IAP can't be submitted.
4. Enroll in the **Small Business Program** (App Store Connect → Agreements) to
   drop Apple's cut from 30% → 15% (eligible under $1M/yr).
5. The IAP is submitted **with the app build** for first review — attach it on
   the version's "In-App Purchases" section before submitting.

## 2. RevenueCat dashboard

1. Create a project → add the **App Store** app (bundle id `ai.finchapp.mobile`),
   upload the **App Store Connect API key** (for receipt validation + Server
   Notifications).
2. **Products:** import `ai.finchapp.mobile.pro.monthly`.
3. **Entitlements:** create one with identifier **`pro`** and attach the product.
   (The code checks `entitlements.active['pro']` — see `lib/purchases.ts`
   `PRO_ENTITLEMENT`.)
4. **Offerings:** create the default (current) offering with a **monthly**
   package pointing at the product. (`getProPackage()` reads `current.monthly`.)
5. **API keys:** copy the **iOS public SDK key** (`appl_…`).
6. **Integrations → Webhooks:** add the backend URL
   `https://<backend>/credits/revenuecat-webhook` and set an **Authorization
   header** value (any strong random string). This must equal the backend's
   `REVENUECAT_WEBHOOK_AUTH`.

## 3. Env vars

**Backend** (`backend/.env` + Railway):
```
REVENUECAT_WEBHOOK_AUTH=<same secret set in the RevenueCat webhook Authorization header>
```

**Mobile** — the iOS public SDK key (`appl_…`):
- Local dev build: `frontend-mobile/.env` → `EXPO_PUBLIC_REVENUECAT_IOS_KEY=appl_…`
- Production: **EAS env** (environment `production`) AND the local mirror
  `frontend-mobile/.env.production`:
  ```
  eas env:create --environment production --name EXPO_PUBLIC_REVENUECAT_IOS_KEY --value appl_…
  ```
  (If unset, IAP is a graceful no-op — the upgrade button hides and the paywall
  shows "not available". So a missing key fails safe, it doesn't crash.)

## 4. Build & test

- IAP needs a **dev build** (not Expo Go): `eas build --profile development --platform ios`.
- Test purchases with a **Sandbox Apple ID** (App Store Connect → Users and
  Access → Sandbox Testers), signed into the device's App Store sandbox.
- Verify the round trip: purchase in the paywall → RevenueCat webhook fires →
  `user_accounts.plan = 'pro'`, `subscription_provider = 'apple'`, credits
  granted → settings shows the PRO badge after `refreshBalance()`.
- Test **Restore purchases** and **Manage subscription** (opens the Apple ID
  subscriptions sheet).

## Code touchpoints

| Concern | File |
|---|---|
| SDK wrapper (configure / logIn / offerings / purchase / restore) | `frontend-mobile/lib/purchases.ts` |
| Configure + identify user on auth | `frontend-mobile/contexts/AuthContext.tsx` |
| Paywall UI | `frontend-mobile/components/PaywallModal.tsx` |
| Plan card + upgrade CTA + manage | `frontend-mobile/app/settings.tsx` |
| Webhook → plan/credits | `backend/routes/credits.py` (`/credits/revenuecat-webhook`) |
| `subscription_provider` column | `backend/models/user.py`, migration `084` |
| Config | `backend/core/config.py` (`REVENUECAT_WEBHOOK_AUTH`) |
