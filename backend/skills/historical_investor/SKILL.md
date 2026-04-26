---
name: historical_investor
description: "MUST READ before any portfolio review, position evaluation, or buy/sell/hold recommendation. Contains structured frameworks from Damodaran, Buffett/Munger, Marks, Lynch, and Soros. Use the composite checklist (Section 6) to evaluate each position."
metadata:
  emoji: "📐"
  category: finance
  is_system: true
  auto_on: true
  requires:
    env: []
    bins: []
---

# Investment Analysis Frameworks

This skill contains battle-tested frameworks from five legendary investors. Use them as structured lenses — not rigid checklists — when reviewing portfolios, evaluating holdings, or making buy/sell/hold recommendations.

**When to use which section:**
- **Valuing a company** → Damodaran (Section 1)
- **Assessing business quality + sell discipline** → Buffett/Munger (Section 2)
- **Checking for edge and market positioning** → Marks (Section 3)
- **Categorizing a holding + applying the right sell criteria** → Lynch (Section 4)
- **Thematic/momentum positions + sizing** → Soros (Section 5)
- **Full portfolio review** → Composite Checklist (Section 6)

---

## 1. Damodaran — Narrative-to-Numbers Valuation

*Source: Aswath Damodaran, NYU Stern. Published frameworks, Musings on Markets blog, annual ERP updates.*

### The Core Insight

Every valuation is a story expressed in numbers. If the story is incoherent, the numbers are worthless. If the numbers don't map to a story, you're just curve-fitting.

### Five-Step Narrative Process

1. **Write the story**: What is the TAM? What share can this company capture? What sustains margins? 3-4 sentences a non-investor could understand.
2. **Stress-test it**: (a) Has any company actually lived this story? (b) Does it survive first-principles reasoning? High growth + high margins + low reinvestment is internally inconsistent. (c) Name 2-3 scenarios that break it.
3. **Map to value drivers**:
   - Market size × share → revenue growth rate
   - Competitive moat → target operating margin
   - Capital intensity → reinvestment rate
   - Business risk + leverage → cost of capital (WACC)
4. **Run the DCF**: Forecast FCFF 10 years, terminal value via stable growth, discount at WACC. Subtract net debt for equity value.
5. **Feedback loop**: When new info arrives, update the *narrative first*, then re-derive numbers. Changing numbers without updating the story creates incoherence.

### The Growth-Value Nexus

**Growth Rate = Reinvestment Rate × ROIC**

- ROIC > WACC → growth creates value
- ROIC = WACC → growth is neutral
- ROIC < WACC → **growth destroys value** — the faster it grows, the worse

A "high growth" company earning below its cost of capital is worth LESS the faster it grows. Never assume growth is inherently good.

### DCF Sanity Checks

| Input | Sanity check |
|---|---|
| Revenue growth >30% sustained | Requires network effects or platform economics — who else has done this? |
| Terminal growth >3-4% | Implies the company outgrows the economy forever. Almost never justified. |
| Target margin 2x peers | Must explain specifically why (IP, scale, regulatory moat) |
| Discount rate manipulation | Never squeeze failure risk into the discount rate. Model failure as a separate scenario with probability. |

### Sell Criteria (Damodaran)

- **Sell when**: Concrete business evidence breaks the narrative — market share loss, 3+ quarters of margin compression, missed milestones the story required, or price exceeds intrinsic value with no updated narrative justifying it.
- **Hold when**: Price dropped but the stress-tested narrative is intact and ROIC still exceeds cost of capital.
- **Never sell because**: Price dropped, macro headlines are scary, or one quarter was weak.

### Common Mistakes

- Anchoring to purchase price (your cost basis is irrelevant to current valuation)
- Spreadsheet precision on made-up inputs ("4-decimal DCF on guessed growth rates is theater")
- Stories without numbers or numbers without stories
- Ignoring base rates (most high-growth companies decelerate; most turnarounds fail)

---

## 2. Buffett/Munger — Business Quality + Margin of Safety

*Source: Berkshire Hathaway shareholder letters, Owner's Manual, Munger's Psychology of Human Misjudgment.*

### Circle of Competence Gate

Before any analysis:
- Can you describe how this business makes money in two sentences?
- Do you understand the unit economics?
- Could you explain why this business will look similar in 10 years?

**If NO to any**: Flag as "outside circle." Require 2x margin of safety or PASS.

### Business Quality Scorecard

| Factor | What to measure | Threshold |
|---|---|---|
| Moat durability | Brand, switching costs, network effects, cost advantages, regulatory barriers | Must be self-reinforcing, not requiring constant rebuilding |
| Pricing power | Can it raise prices 10% without losing meaningful volume? | If no, the moat is weaker than it looks |
| ROE | Sustained >15% without excessive leverage (D/E < 0.5) | High ROE + low debt = genuine advantage |
| ROIC | >12% sustained over 10 years | Single best signal of real value creation |
| Management | Rational capital allocation, insider ownership, candid reporting | Watch for serial acquirers, empire-builders |
| Predictability | Can you forecast earnings 5 years out within a reasonable band? | If no, the business is too uncertain for concentrated positions |

### Owner Earnings (Not GAAP Earnings)

```
Owner Earnings = Net Income
  + Depreciation & Amortization
  + Change in Deferred Tax
  - Maintenance CapEx (NOT growth CapEx — use 70% of total as conservative proxy)
  +/- Changes in Working Capital
```

**Owner Earnings Yield** = Owner Earnings / Market Cap. Compare to 10-year Treasury. If below Treasury yield, you need an extraordinary growth case.

### Intrinsic Value + Margin of Safety

1. Project owner earnings 10 years forward (conservative: lower of historical growth, consensus, or GDP + inflation)
2. Discount at 10-year Treasury rate
3. Terminal value = Year 10 owner earnings / discount rate
4. Sum = intrinsic value

**Required margin of safety:**
- High-confidence (stable, predictable): 25-30% discount
- Medium-confidence: 35-50% discount
- Low-confidence / outside circle: 50%+ discount

**The whole-company test**: "Would I buy 100% of this company at this market cap, with my own money, and hold it for 10 years?" If no, don't buy shares either.

### Sell Criteria (Buffett)

Sell ONLY when:
1. **Competitive advantage permanently eroded** — moat breached, not just temporarily pressured
2. **Management deterioration** — irrational capital allocation, dishonesty, empire-building
3. **Original thesis was wrong** — you misjudged the economics. Admit the error.
4. **Dramatically better opportunity** — clearly superior risk-adjusted return needs the capital (should be rare)
5. **Extreme overvaluation** — price >2x conservative intrinsic value with no justifying narrative

**NOT a sell reason**: Price drops alone, macro fear, quarterly misses, or because others are selling.

### Munger's Bias Checklist (Pre-Decision)

Before finalizing any recommendation:
- [ ] **Confirmation bias**: Did you only seek supporting data? Find the bear case.
- [ ] **Anchoring**: Are you anchored to purchase price, a past high, or a target?
- [ ] **Social proof**: Buying because others are, or because the business is genuinely good?
- [ ] **Loss aversion / sunk cost**: Holding a loser because selling "locks in" the loss? The stock doesn't know your cost basis.
- [ ] **Overconfidence**: Have you assigned a probability to being wrong?
- [ ] **Recency bias**: Are recent results (good or bad) dominating your 10-year view?

**Munger's inversion**: Instead of "Why buy?", ask "What would make this a terrible investment?" If you can't name 3 genuine risks, you haven't done the work.

---

## 3. Howard Marks — Second-Level Thinking + Cycle Awareness

*Source: Oaktree Capital memos, "The Most Important Thing."*

### Second-Level Thinking

First-level: "Good company. Buy."
Second-level: "Good company. Everyone knows it. Priced for perfection. What if they merely meet expectations?"

**For every position:**
- What is the consensus view? How does mine differ?
- What is already priced in?
- What is the range of outcomes and their probabilities?
- Am I being compensated for the risk?

If your view matches consensus and is already priced in, you have no edge. Move on.

### Market Temperature

**Running hot** (reduce risk):
- Prospective returns near historic lows across asset classes
- High prices everywhere with few genuine bargains
- Pro-risk behavior: high leverage, loose credit, record issuance
- "This time is different" narratives accepted uncritically

**Running cold** (increase risk):
- Forced selling (margin calls, redemptions)
- Quality assets below replacement cost
- Credit markets seizing — good companies can't refinance
- Media consensus is panic

**Key insight**: Risk is highest when everyone thinks it's lowest (peak complacency), and lowest when everyone thinks it's highest (peak fear).

### Risk Posture

- **Defensive when**: Valuations stretched AND enthusiasm high. Favor quality, reduce sizes, hold cash.
- **Aggressive when**: Pessimism prevails AND assets genuinely underpriced. Increase sizes, accept illiquidity for discount.
- "The goal is not to find good assets, but good deals."

---

## 4. Peter Lynch — Categorize, Then Apply the Right Rules

*Source: "One Up on Wall Street," "Beating the Street."*

### Six Categories (Every Stock Fits One)

| Category | Profile | Sell when |
|---|---|---|
| **Slow growers** | 2-4% growth, high dividend | Dividend cut, growth below inflation |
| **Stalwarts** | 10-12% growth, large cap | After 30-50% gain, P/E > growth rate, or management "diworseifies" (unrelated acquisitions) |
| **Fast growers** | 20-25%+ growth | Growth decelerates, P/E > growth rate, expansion stumbles, same-store metrics weaken |
| **Cyclicals** | Tied to economic cycle | Late cycle when earnings peak. **Don't wait for the downturn** — stock drops before earnings. Watch inventory builds + capacity utilization. |
| **Turnarounds** | Distressed, potential recovery | Turnaround mechanism unclear, debt not declining, or recovery fully priced in |
| **Asset plays** | Hidden balance sheet value | Hidden value recognized (gap closes), or management destroys the assets |

### Lynch's Rules

- **"Know what you own"**: If you can't explain the thesis in 2 sentences, you don't understand it.
- **The two-minute drill**: (1) Why did I buy? (2) What has to happen for it to work? (3) Has anything changed?
- **Sell your losers, let your winners run**: "Pulling the flowers and watering the weeds" is the #1 amateur mistake.

---

## 5. Soros — Reflexivity + Position Sizing

*Source: "The Alchemy of Finance," Soros Fund Management.*

### Reflexivity: Prices Change Fundamentals

Market prices aren't just reflections — they shape reality. Rising stock → better ability to raise capital, attract talent, win deals → improved fundamentals → higher stock. Works in reverse too.

### The Boom/Bust Cycle (8 Phases)

1. **Trend starts**: Real fundamental change
2. **Self-reinforcement**: Price moves trigger feedback accelerating the trend
3. **Successful test**: Survives a pullback — conviction increases
4. **Growing doubt**: Price-fundamental gap widens but momentum sustains
5. **Climax**: Fastest rise, late buyers, maximum divergence
6. **Reversal**: Momentum fades
7. **Crash**: Falling prices deteriorate fundamentals — accelerating downward spiral
8. **New equilibrium**: Overshoot below fair value — buying opportunity

**Ask for each thematic position**: "Where are we in the reflexive cycle?" Long in phases 2-3. Take profits in 5-6. Look for entries in 7-8.

### Position Sizing (Anti-Martingale)

- **Increase size when profitable** — thesis confirmed
- **Cut size when losing** — something may be wrong
- **Pyramid into winners**, not losers
- **What matters**: Not whether you're right, but how much you make when right vs lose when wrong
- **Cut immediately when thesis invalidated** — not at an arbitrary stop, but when the *reason you bought* no longer holds

---

## 6. Composite Portfolio Review Checklist

Use this for full portfolio reviews. For each position:

```
TICKER: [symbol]

— CATEGORIZATION (Lynch) —
Category: [slow grower / stalwart / fast grower / cyclical / turnaround / asset play]
Category sell signal triggered? [Y/N + detail]

— BUSINESS QUALITY (Buffett) —
Moat: [type + durability assessment]
ROIC vs WACC: [value creating / neutral / destroying]
Owner earnings yield: [X]% vs Treasury [Y]%

— VALUATION (Damodaran) —
Narrative: [2-3 sentence story]
Narrative risk: [what breaks it]
Intrinsic value: $[X] vs current price $[Y] → [premium/discount]%
Growth creating value? [ROIC vs WACC check]

— EDGE CHECK (Marks) —
Consensus view: [what's priced in]
My non-consensus view: [if any — if none, no edge]
Risk compensation: [adequate / inadequate]

— CYCLE + SIZING (Soros) —
Reflexivity phase: [1-8]
Position size appropriate? [Y/N — adjust direction]

— VERDICT —
Action: [BUY / HOLD / TRIM / SELL]
Rationale: [one line]
Key risk: [single biggest threat]
Bias check: [any Munger flags triggered]
```
