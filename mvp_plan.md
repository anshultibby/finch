# Finch MVP Plan: AI Trading Bots for Prediction Markets

## Vision

The first polished platform where anyone can build, deploy, and evolve AI bots that trade prediction markets (Kalshi → Polymarket).

**One-liner**: "Your AI agent that trades prediction markets while you sleep."

---

## Market Opportunity

| Metric | 2025 Data |
|--------|-----------|
| Kalshi volume | $23.8B (1,108% YoY) |
| Polymarket volume | $21.5B |
| Kalshi valuation | Seeking $20B |
| Active traders (peak) | ~478,000 |
| Existing AI bot tools | Fragmented, dev-only, single-strategy |

**Whitespace**: No polished, non-technical platform exists for AI-powered prediction market trading. Competitors are either $9/mo basic UIs (Bot for Kalshi), one-off scripts ($100-250, PolyTraderBot), signal-only tools (Predly.ai), or open-source GitHub projects requiring engineering skill.

**Our edge**: Multi-market support, evolving strategy memory (STRATEGY.md + MEMORY.md), autonomous LLM reasoning loop, and a UX that non-engineers can use.

---

## Target User

**Primary**: Retail prediction market traders who are active on Kalshi, interested in automation, but can't code their own bots. They're in Discord communities (Binary Alpha, PolyZone, PolySmart), follow prediction market Twitter, and currently trade manually.

**Secondary**: Quant-curious traders who've tried open-source bots but want something that "just works."

---

## Pricing: Token-Based

Credits consumed per action:

| Action | Credits |
|--------|---------|
| Bot tick (LLM reasoning + tool calls) | 10 |
| Trade placed | 5 |
| Wakeup/alert triggered | 2 |
| Backtest run | 50 |

Credit packs:

| Pack | Price | Credits | Bonus |
|------|-------|---------|-------|
| Starter | $5 | 500 | — |
| Builder | $20 | 2,500 | +25% |
| Trader | $50 | 7,500 | +50% |

**Free tier**: 200 credits on signup (enough for ~1-2 weeks of paper trading). No credit card required.

---

## MVP Scope

### What Already Works
- Kalshi buy/sell (RSA-signed HTTP client, full order flow)
- Bot creation, strategy doc storage (STRATEGY.md + MEMORY.md)
- Position tracking with P&L
- Wakeup scheduling (bot self-triggers at specific times)
- Trade logging and execution history
- Encrypted credential storage
- Server-side risk enforcement (max order, daily spend, capital checks)
- Bot grid homepage with P&L display
- Bot detail page with chat, positions panel, trades panel

### Critical Gaps to Fix (Pre-Launch)

#### 1. Wakeup-Based Execution (DONE)
Bots run entirely via the wakeup system. No separate "tick executor." Each wakeup:
- Creates a chat thread with the bot
- Sends a preprogrammed message (custom instruction)
- Bot reasons with full tool access (bash, web_search, place_trade, etc.)
- Bot can schedule its own future wakeups (including recurring ones)

**Recurring wakeups**: `every_30m`, `every_1h`, `every_4h`, `daily_9am`, etc. Auto-reschedules after each trigger.

**Removed**: `executor.py` tick system, `approved` concept, `approve_bot` tool/route, `run_bot` tool/route.

#### 2. Credit Deduction Integration
**Current state**: Credit system exists but not wired to bot actions.
**Required**: Deduct credits per wakeup, per trade. Show credit balance prominently. Low-balance warnings. Purchase flow.

### Phase 2 (Post-Launch, Weeks 4-6)

#### 8. Polymarket Trading
- Implement ECDSA wallet signing for order placement
- USDC approval flow
- Wallet import UI (private key or WalletConnect)
- Slippage calculation for AMM pools

#### 9. Performance Analytics
- Win rate, profit factor, Sharpe ratio per bot
- Trade-by-trade analysis with bot reasoning attached
- Equity curve chart
- Comparison across bots

#### 10. Whale/Anomaly Alerts
- Monitor large position changes on markets bot is tracking
- Push notification when a significant move happens
- Configurable alert thresholds

#### 11. Trade Approval Flow
- Wire up pending_approval → SMS/email notification → approve/reject via token URL
- User can require approval for trades above X size

#### 12. Backtesting
- Historical market data ingestion from Kalshi API
- Simulate strategy against past data
- Display equity curve, max drawdown, win rate

### Phase 3 (Growth, Weeks 7-10)

#### 13. Bot Leaderboard
- Public leaderboard of top-performing bots (anonymized)
- Users can browse and clone top strategies
- Social proof + viral loop

#### 14. Strategy Sharing
- Export/import bot strategies
- "Fork this bot" functionality
- Community gallery of strategies

#### 15. Automated Strategy Review
- After every N trades, bot self-reviews and proposes STRATEGY.md updates
- User approves or rejects suggested changes
- Continuous improvement loop

---

## Launch Plan

### Pre-Launch (2-3 weeks before)

**Build the waitlist**:
- Landing page with clear value prop + email capture
- "AI bots that trade prediction markets" — keep it simple
- 200 free credits for early signups

**Seed the communities**:
- Join: Binary Alpha, PolyZone, PolySmart, PolyOdds, Kalshi Official Discord (25k+ members)
- Don't pitch. Contribute for 1-2 weeks: answer questions, share market observations, post interesting analysis
- After building credibility: "I've been building a tool for this, want early access?"
- **Target: 50 beta users from Discord before launch day**

**Build social proof**:
- Run your own bot on Kalshi for 2+ weeks before launch
- Document the journey on Twitter: what the bot did, what it learned, P&L (even if modest)
- Screenshot the bot's reasoning logs — this is novel content nobody else posts

---

### Launch Week: Product Hunt

**Timing**: Tuesday or Wednesday, go live at 12:01 AM PT.

**Pre-coordination**:
- Get 20-30 supporters committed to upvote + leave genuine comments in the first 4 hours
- Products with 100+ upvotes before 4 AM PT have 82% chance of Top 10
- Target: 300-500 upvotes for Top 5 Product of the Day

**Assets to prepare**:
- 3-5 high-quality GIFs showing: (1) bot creation from template, (2) bot reasoning in real-time, (3) trade execution, (4) P&L dashboard, (5) strategy evolution
- 90-second demo video: "Watch this AI bot find and trade a Kalshi market"
- Maker comment draft: what it does, why it exists, invitation for feedback, mention free 200 credits

**Launch day**:
- Post maker comment immediately
- Reply to every comment throughout the day (24 hours)
- Share PH link on Twitter, Discord communities, LinkedIn
- Offer "Product Hunt exclusive": 500 free credits instead of 200 for PH signups

**Category opportunity**: No dominant prediction market trading tool has launched on PH. This is a category-defining moment. Position as "AI trading bots for prediction markets" — not "another crypto tool."

---

### Launch Week: LinkedIn Campaign

LinkedIn is for founder credibility and trust, not direct B2C acquisition. Run a 4-day content sequence:

**Day 1 — Hero Post (launch day)**:
- Format: Native text post (no external links in body — put link in comments)
- Hook (first 2 lines): "I built an AI that trades prediction markets. After 2 weeks of paper trading, here's what happened."
- Content: What Finch does, the result your bot achieved, clear CTA
- Post between 8-10 AM ET, Tuesday-Thursday

**Day 2 — Behind the Scenes**:
- "Why I'm betting on prediction markets as the next frontier for AI agents"
- Share the market size ($44B combined volume), the whitespace, your personal motivation
- Tag people who gave early feedback

**Day 3 — Social Proof**:
- Share beta user reactions, early traction numbers, Product Hunt ranking
- Carousel format (6-9 slides): screenshots of real bot decisions + user testimonials

**Day 4 — Founder Story / Lessons**:
- "3 things I learned building AI agents that trade with real money"
- Authenticity > marketing. Be direct and personal.
- Include a specific technical challenge you solved

**LinkedIn tips**:
- No marketing language. Factual, direct.
- Ask questions that prompt substantive replies (comments weigh more than reactions)
- Tag people who helped build or test. They'll engage and amplify.

---

### Launch Week: Hacker News (Show HN)

**Timing**: 1-2 days after Product Hunt (use PH momentum but don't split attention on same day).

**Title**: `Show HN: Finch – AI agents that autonomously trade prediction markets`

**Post requirements**:
- Must have a live demo people can try (paper trading with free credits)
- Technical depth is mandatory — explain the architecture
- No marketing language. Factual, direct.

**Post structure**:
1. What it does (2 sentences)
2. How the agent works (strategy docs, tool calling, reasoning loop, position management)
3. Technical details HN will appreciate: async execution, sandbox isolation, memory system
4. Link to try it (paper trading, no credit card)
5. "I'm the founder, happy to answer questions about the architecture"

**What works on HN for trading/AI**:
- Open-source angle helps massively — consider open-sourcing a component (strategy templates? Kalshi client?)
- Live demo where people can watch the bot reason and trade
- Share technical details about agent architecture, compaction, tool system

---

### Post-Launch (Weeks 2-4)

**Community-led growth**:
- Weekly "bot performance report" posted to Discord + Twitter
- Invite top Discord members to beta test new features
- Create a Finch Discord for users to share strategies and compare results

**Content flywheel**:
- Bot reasoning logs → Twitter content (weekly)
- User success stories → LinkedIn posts (bi-weekly)
- Technical deep-dives → HN/blog posts (monthly)

**Referral loop**:
- "Give 200 credits, get 200 credits" referral program
- Bot leaderboard drives organic sharing

---

## Success Metrics

### Launch targets
| Metric | Target |
|--------|--------|
| Product Hunt ranking | Top 5 POTD |
| Signups (launch week) | 500 |
| Active bots (month 1) | 100 |
| Paying users (month 1) | 30 |
| Revenue (month 1) | $1,000 |

### Product health (month 2+)
| Metric | Target |
|--------|--------|
| Weekly active bots | 200 |
| Credit purchase conversion | 10% of signups |
| Bot retention (still running after 2 weeks) | 40% |
| Average revenue per paying user | $35/mo |

---

## Risk Mitigation

| Risk | Mitigation |
|------|-----------|
| Users lose money, blame product | Paper trading default. Clear disclaimers. Risk limits enforced server-side. |
| Regulatory concerns | Kalshi is CFTC-regulated. We're a tool layer, not a broker. Clear ToS. |
| Bot makes catastrophic trade | Max order size defaults. Circuit breaker on drawdown. Trade approval flow for large orders. |
| Low initial engagement | Free credits lower barrier. Discord community seeds early users. Strategy templates reduce blank-page problem. |
| Polymarket legal uncertainty | Launch with Kalshi only (US-regulated). Add Polymarket as Phase 2 once legal landscape clarifies. |

---

## Decision Log

- **Kalshi first, Polymarket second**: Kalshi is regulated, API is cleaner, no crypto wallet friction. Polymarket adds complexity (ECDSA signing, USDC, AMM slippage) that delays launch.
- **Token-based pricing over subscriptions**: Usage aligns with value. Bursty activity pattern means subscriptions feel wasteful during quiet periods.
- **Paper trading as default**: Trust is the #1 barrier. Let users watch a bot win on paper before asking for real money.
- **Strategy templates over blank canvas**: Non-technical users freeze on blank STRATEGY.md. Templates solve the cold-start problem.
- **Discord over paid ads for early growth**: The 50k+ members across prediction market Discords are the exact target user. Organic credibility > ad spend at this stage.
