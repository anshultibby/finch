# App Store — Review Notes & "What to Test"

Paste these into App Store Connect → App Review Information.

## Demo account (Sign-In required: Yes)
- **Username:** `appstore.review@finchapp.ai`
- **Password:** `FinchApp`

## What to Test (this build)
- **NEW: In-app account deletion** — Profile → **Delete account** (below Sign Out).
  Confirms, permanently deletes the account, and signs out. (Guideline 5.1.1(v).)
- **AI Research Chat** — Markets tab → "Ask anything about the markets…" bar, or the
  compose icon. Try "Is NVDA overvalued right now?" — streams a sourced answer.
- **Markets** — gainers/losers/most active, index cards, expandable news; US/India toggle.
- **Stock research** — tap any ticker → price chart (1W–1Y), key stats, 52-week range,
  analyst ratings, Financials/Earnings/News/Analysis tabs; star to watchlist.
- **Watchlist & Earnings** — home tabs.

## Notes
- Finch is for RESEARCH/information only — no financial advice, no trading on the user's
  own brokerage.
- The Portfolio tab can link a real brokerage (read-only, via SnapTrade OAuth). It requires
  a reviewer's own brokerage login, so it can't be exercised with the demo account; all
  other features work fully without it.
- Account/data deletion is in-app (above); support: support@finchapp.ai.
- Export compliance: no non-exempt encryption (`ITSAppUsesNonExemptEncryption: false`).
- Marketing/Privacy: https://finchapp.ai · https://finchapp.ai/privacy
