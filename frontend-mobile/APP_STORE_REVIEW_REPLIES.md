# App Review replies — rejection of 1.0 (22), submission 8d319ed2 (June 12, 2026)

Paste each section as a reply in App Store Connect → App Review messages, after
uploading the new build. Fill `<E2E_EMAIL>` / `<E2E_PASSWORD>` from the
gitignored env files before sending.

---

## Guideline 4.8 — Login Services

> We have added **Sign in with Apple** in this build. It appears as the first
> login option on the sign-in screen (above Google), uses Apple's native
> AuthenticationServices sheet, collects only name and email, supports Hide My
> Email, and does not collect any interactions for advertising purposes.

## Guideline 5.1.1(v) — Registration requirement

> This build no longer requires registration to use non-account-based features.
> On first launch the app opens directly to Markets — users can freely browse
> live market data, index performance, top movers, news, earnings calendars,
> and full per-stock research (charts, key stats, financials, analyst ratings)
> without creating an account.
>
> An account is required only for account-based features: the AI chat assistant
> (each conversation runs in a private, per-user server workspace and history is
> persisted to the user's account), personal watchlists, brokerage portfolio
> sync, and notifications. These are inherently tied to a user account.

## Guideline 4 — iPad usability

> This build adds native iPad support. The app now runs full-screen on iPad
> (previously it ran in iPhone compatibility mode in a fixed portrait window),
> supports all four orientations on iPad including landscape, adapts its
> layouts to iPad widths and window resizing, and supports iPadOS multitasking.
> We verified every screen on an iPad Air 11-inch simulator running iPadOS 26.5
> in both portrait and landscape.
>
> If a specific screen still appears crowded in your review environment, we
> would appreciate a screenshot so we can address it directly.

## Guideline 2.1 — Information needed ("Provide API to verify the app functionality")

> The app is fully functional in review using the demo account below — no
> special hardware, configuration, or external accounts are needed:
>
> - Username: `<E2E_EMAIL>`
> - Password: `<E2E_PASSWORD>`
>
> All app data is served by our production backend over HTTPS at
> https://finch-production-8434.up.railway.app (market data, AI chat, watchlist,
> earnings). The demo account is pre-funded with usage credits, so AI chat can
> be exercised end-to-end. The only feature that cannot be exercised with the
> demo account is connecting a personal brokerage (it requires the reviewer's
> own brokerage login via read-only OAuth); every other feature works fully.
> If you need anything further to verify functionality (e.g. a demo video),
> we're happy to provide it.

## Guideline 2.1(b) — Business model questions

> 1. **Who are the users that will use the paid credits in the app?**
>    Credits are a usage meter for the AI research assistant. Every user
>    receives free credits automatically: 1,000 credits at sign-up, plus a free
>    daily refresh. There is no separate class of "paid credit" users — all iOS
>    users use the same free credit system, and the entire app is usable on the
>    free tier.
>
> 2. **Where can users purchase the credits that can be accessed in the app?**
>    Credits cannot be purchased anywhere in the iOS app. The app contains no
>    store, no pricing, no purchase buttons, and no links or references to any
>    external way to buy credits. Our website offers an optional subscription
>    for power users, but the iOS app does not advertise, mention, or link to
>    it.
>
> 3. **What specific types of previously purchased credits can a user access in
>    the app?**
>    None are required or expected. An account's credit balance (free grants and
>    daily refreshes) is shown in Settings as a usage meter. When credits run
>    out, the app simply informs the user that credits refresh automatically
>    each day.
>
> 4. **What paid content, subscriptions, or features are unlocked within the
>    app that do not use In-App Purchase?**
>    None. No feature in the iOS app is locked behind a payment. All
>    functionality — market data, stock research, AI chat, watchlists,
>    portfolio sync — is available to every user on the free tier.

---

## Before resubmitting — required configuration (not yet done)

1. **Apple Developer portal**: enable the *Sign In with Apple* capability for
   the App ID `ai.finchapp.mobile` (Certificates, Identifiers & Profiles →
   Identifiers). If EAS manages credentials, `eas build` will prompt/sync the
   entitlement automatically.
2. **Supabase Dashboard** → Authentication → Sign In / Providers → **Apple**:
   enable the provider and add `ai.finchapp.mobile` to **Authorized Client IDs**
   (the native `signInWithIdToken` flow needs only the bundle ID — no service
   ID / client secret required unless web Apple login is added later).
3. **EAS build + submit**: `cd frontend-mobile && eas build --platform ios
   --profile production` (build number must exceed 22), then update the demo
   credentials + notes in App Store Connect and reply with the messages above.
4. **Smoke-test on TestFlight**: Apple sign-in (first + repeat auth), guest
   browse → sign-in prompts on Watchlist/Portfolio/Chat, login screen's
   "Browse markets without an account" link.
