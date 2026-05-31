# Finch — Full App Design Review

A design review of the Finch web app, benchmarked against three references the
team admires: **Robinhood** (consumer finance), **Perplexity** (AI answers), and
**Claude** (calm, editorial AI). Written from a full-app screenshot audit.

---

## 1. What the references do well (the bar)

**Robinhood** — *finance done confidently.*
- **Numbers are the hero.** Portfolio value and prices are large, bold, tabular. Everything else recedes.
- **Ruthless color restraint.** Greyscale + one green (and red for down). Color = meaning, never decoration.
- **Clean cards, big whitespace, simple line charts.** No visual noise.

**Perplexity** — *minimal and calm.*
- Near-white background, **soft deeply-rounded** inputs/cards, generous whitespace.
- A single subtle accent (teal). Quiet chrome; the content is the UI.
- Confident, readable sans typography with a clear hierarchy.

**Claude** — *warm and editorial.*
- Soft rounded surfaces, lots of breathing room, an unhurried feel.
- One warm accent used sparingly; restraint everywhere else.

**The through-line for all three:** *restraint, generous whitespace, soft rounded
surfaces, one accent used for meaning, and confident typography.* Finance-specific:
**make the numbers big and tabular** (Robinhood).

---

## 2. Finch today — honest assessment

Finch is already in good shape (white, emerald accent, DM Sans + Space Grotesk
numerals, clean cards). Recent work added real polish: ticker logos, distinctive
price numerals, count-up, sparkline draw-in, delightful empty states, and a
strong Scheduled page. The foundation is solid.

What keeps it from feeling top-tier:

### P0 — highest impact
1. **Loading = spinners, not skeletons.** The dashboard (and several panels) show a
   centered spinner while data loads. Robinhood/Perplexity/Claude all use
   **skeleton placeholders** that mirror the final layout — the page feels instant
   and stable. *Finch already has `.animate-shimmer` in globals.css; it's underused.*
2. **Inconsistent page headers.** Each surface styles its header differently
   (Dashboard has none / breadcrumb only; Stock has its own; Memory/Visualizations
   each differ; Scheduled now has the nicest one). **Standardize one header pattern**
   (left-aligned bold title + muted subtitle + right-aligned actions, filling the
   content width) across every page.
3. **Color noise in places.** Colored badges (emerald/red/amber/blue pills),
   multiple accent uses, gradient buttons (`linear-gradient(135deg,#059669,#10b981)`
   on trade buttons) compete. Pull back to **emerald-as-the-only-accent + greyscale**;
   reserve red strictly for "down/destructive."

### P1 — clear wins
4. **Numbers could be bolder.** Robinhood makes the portfolio/price the visual
   anchor. Finch's stock price is good (Space Grotesk); extend the tabular numeric
   treatment to the **portfolio net-worth, position values, and key stats**, and
   size the hero number up.
5. **Card system isn't fully consistent.** Radii vary (`rounded-xl`/`2xl`), borders
   vary (`gray-100`/`200`, some `/70` opacities), shadows vary. Define **one card
   token**: `rounded-2xl border border-gray-200` + `hover:shadow-md`, and use it
   everywhere (the Scheduled cards are the reference).
6. **Spacing rhythm.** Page paddings differ (`px-4/5/6/8`), section gaps vary.
   Adopt a scale: page `px-6 sm:px-10 py-8`, section gap `mb-8`, card gap `gap-3`.
7. **Dense tables (Financials) are strong but cramped at the composer.** Already
   improved with the fade bar; ensure consistent bottom padding so nothing hides
   under the sticky input.

### P2 — refinement
8. **Index "$" prefix on indices** (e.g. `$7,580` for S&P) is technically wrong —
   indices aren't dollar-denominated. Drop the `$` for `^`-prefixed symbols.
9. **Empty states are good** (EmptyState component) — extend the same component to
   Orders and any remaining bare states for consistency.
10. **Motion is tasteful but thin.** Count-up + sparkline draw-in are in. Add
    **skeleton→content cross-fade** and keep transitions ≤200ms. Respect
    `prefers-reduced-motion` (already guarded).
11. **Sidebar** is clean and on-pattern with Perplexity/Claude (icon + label, active
    pill). Minor: the "CHATS" section + search could use the same type scale as nav.

---

## 3. A small design-token foundation (recommended)

Encode the system so consistency is automatic, not manual:

- **Surface:** page `bg-white`; card `rounded-2xl border border-gray-200`,
  `hover:shadow-md`; modal `rounded-3xl`.
- **Accent:** emerald-600 (actions), emerald-50/emerald-600 (icon tiles). Red only
  for down/destructive. No gradients on buttons.
- **Type:** title `text-2xl font-bold tracking-tight`; section label
  `text-xs font-semibold uppercase tracking-wider text-gray-400`; numbers
  `.font-numeric` (tabular).
- **Spacing:** page `px-6 sm:px-10 py-8`; section `mb-8`; grid `gap-3`.
- **Radius:** controls `rounded-lg`, cards `rounded-2xl`, modals `rounded-3xl`,
  pills `rounded-full`.
- **Loading:** skeletons (`.animate-shimmer`) shaped like the content, never a bare
  spinner on a primary surface.

---

## 4. Prioritized plan

1. **Skeletons** for dashboard + panels (replaces spinners). *Highest perceived-quality win.*
2. **Standard `PageHeader` component** rolled across all surfaces.
3. **Card token** unification (radius/border/shadow) — start with the highest-traffic surfaces.
4. **Color restraint pass** — remove gradient buttons, reduce badge colors.
5. **Bigger, tabular hero numbers** on portfolio + stock.
6. **Index `$` fix** + remaining empty states.

Items 1–2 are safe and universally positive; 3–6 benefit from a quick eyeball before
shipping broadly. See the companion commit for what was applied in this pass.
