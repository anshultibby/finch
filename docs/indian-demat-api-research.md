# Indian Demat Account Aggregation — Research Findings

> Researched June 2026. Goal: connect Indian brokerage accounts (esp. HDFC Securities) the way SnapTrade connects US brokers.

---

## Bottom Line

**There is no SnapTrade for India.** The closest equivalent is India's Account Aggregator (AA) framework, but it has a hard regulatory gate for most fintechs. The best practical path for Finch today is **local CAS PDF parsing** (open-source, zero cost).

---

## Option Comparison

| Option | Covers HDFC Securities | Live/Automated | Cost | Regulatory gate |
|--------|----------------------|----------------|------|-----------------|
| **Local `casparser` lib (PDF upload)** | ✅ (via CDSL) | ❌ User uploads PDF | Free | None |
| **CASParser API — CDSL OTP flow** | ✅ (via CDSL) | ✅ OTP every refresh | ₹3,500/mo (Pro 200) | None |
| **smallcase Gateway SHI API** | ❌ (HDFC Sky only) | ✅ OAuth once | Custom pricing | None |
| **Account Aggregator (AA) framework** | ✅ (via CDSL FIP) | ✅ Consent once | Varies by AA | **SEBI/RBI regulated entity required** |
| **HDFC Securities direct API** | ✅ | ✅ | N/A | **No public API exists** |

---

## Account Aggregator (AA) Framework

The RBI-regulated framework that's structurally closest to SnapTrade. Three parties:
- **FIPs** (data holders) — CDSL, NSDL, banks
- **AAs** (consent managers) — Finvu, Setu, CAMSFinserv, OneMoney (13 total)
- **FIUs** (data consumers) — brokers, fintechs

**What it can provide:** CDSL went live as an FIP in April 2023. Via the AA framework you can pull: Profile (name, PAN, demat account number), Summary (portfolio value, ISIN-wise holdings), Transactions. Covers equities, MFs, ETFs, AIF, InvIT, REIT.

**The blocker:** Only SEBI/RBI/IRDAI/PFRDA-regulated entities can be FIUs. Unregulated fintechs can only be TSPs (build the tech for a regulated partner, not consume data independently).

**Developer APIs:**
- **Setu** — proper HTTP API, good docs, sandbox available
- **Finvu** — sandbox at `aauat.finvu.in/API/V1`, manual email onboarding (no self-serve)

---

## HDFC Securities Specifically

- **Not a FIP** — HDFC Securities appears in the Sahamati registry as a **FIU** (data consumer), not a data provider. You cannot pull holdings from HDFC Securities via the AA framework.
- **No public API** — unlike Zerodha (Kite Connect) or Upstox, HDFC Securities has no developer API.
- **But:** HDFC Securities customers' demat accounts are held at **CDSL** (as the depository). So CDSL data = HDFC Securities holdings. Any path that reaches CDSL reaches HDFC customers.

---

## What We're Building (Phase 1)

**Open-source `casparser` Python library** — local PDF parsing, no API subscription.

Flow:
1. User downloads their CAS (Consolidated Account Statement) PDF from CDSL website or HDFC Securities app
2. User uploads the PDF in Finch
3. Backend parses it locally with `casparser` — extracts all demat holdings (ISIN, name, quantity) across all accounts in the statement
4. Holdings stored in `casparser_connections` table, displayed in Portfolio

**What you get:** All holdings from all demat accounts in the CAS (CDSL + NSDL), regardless of broker. Covers HDFC Securities, Zerodha, etc. No live prices — just quantity snapshots.

**Upgrade path:** If Indian user base grows, swap the PDF upload step for the CASParser API OTP flow (₹3,500/mo, Pro 200 plan) — the backend routes and DB schema are already built to support it.

---

## What Was Already Built

Backend infrastructure is live (pending migration `083`):
- `casparser_connections` table — stores encrypted PAN/DOB, BO ID, holdings cache
- `routes/casparser.py` — initiate, verify, status, portfolio, refresh, disconnect endpoints
- `schemas/casparser.py` — Pydantic models
- `modules/tools/clients/casparser.py` — API client (currently points at CASParser cloud API; swap for local lib)

Frontend:
- `CdslConnectModal` in `ConnectionsPanel.tsx` — 3-step OTP flow (needs changing to PDF upload)
- Indian Holdings section in portfolio view — shows holdings by demat account
- `casparserApi` in `lib/api.ts` — all client functions

**TODO (tomorrow):** Replace cloud OTP flow with local `casparser` PDF upload. Routes and DB stay the same.

---

## Sources

- Sahamati (AA industry body): https://sahamati.org.in/fip-fiu-in-account-aggregators-ecosystem/
- CDSL FIP page: https://www.cdslindia.com/Investors/FIP.html
- Setu AA docs: https://docs.setu.co/data/account-aggregator/overview
- Finvu sandbox docs: https://finvu.github.io/sandbox/
- smallcase Gateway: https://gateway.smallcase.com/
- CASParser: https://casparser.in
- `casparser` Python library: https://github.com/codereverser/casparser
