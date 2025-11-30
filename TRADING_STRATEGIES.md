# Trading Strategies for Short & Medium-Term Play Suggestions

## Overview
This document outlines the quantitative trading strategies implemented in Finch for suggesting short-term (1-4 weeks) and medium-term (1-3 months) trade ideas to users.

## Strategy Categories

### Short-Term Strategies (1-4 Weeks)

#### 1. **Momentum Breakout Strategy**
**Objective:** Identify stocks breaking out of consolidation with strong momentum

**Signals:**
- Price breaks above 20-day resistance with volume 1.5x+ average
- RSI between 55-70 (strong but not overbought)
- Stock mentioned on Reddit with increasing sentiment (optional boost)
- Minimum daily volume: $10M

**Entry:** On breakout confirmation (next day open)
**Exit Target:** +15-25% or resistance level
**Stop Loss:** -7% from entry
**Expected Hold Time:** 1-3 weeks

**Data Required:**
- Historical price data (60 days)
- Volume data
- RSI calculation
- Support/resistance levels
- Reddit sentiment (optional)

---

#### 2. **Gap & Go Strategy**
**Objective:** Capitalize on stocks gapping up on news/catalysts

**Signals:**
- Gap up 5%+ on open with volume 2x+ average
- Price holding above gap level for first 30 min
- Positive news catalyst or insider buying
- Reddit mentions spiking 3x+ (validation)

**Entry:** After 30-min consolidation above gap
**Exit Target:** +10-20% from entry
**Stop Loss:** Below gap level (-5 to -8%)
**Expected Hold Time:** 1-2 weeks

**Data Required:**
- Premarket/opening price data
- News/catalyst detection
- Insider trading data
- Reddit sentiment spikes

---

#### 3. **Mean Reversion (Oversold Bounce)**
**Objective:** Find quality stocks temporarily oversold, ready to bounce

**Signals:**
- RSI < 30 for 2+ days
- Stock down 10-15% from 30-day high
- Strong fundamentals (P/E < sector avg, positive earnings)
- No negative news/downgrade

**Entry:** When RSI crosses back above 35
**Exit Target:** +8-15% or return to 20-day MA
**Stop Loss:** -5% from entry
**Expected Hold Time:** 1-3 weeks

**Data Required:**
- RSI calculation
- Fundamental ratios (P/E, earnings)
- 30-day price range
- News sentiment

---

### Medium-Term Strategies (1-3 Months)

#### 4. **Trend Following with MA Crossover**
**Objective:** Ride established uptrends using moving average signals

**Signals:**
- 50-day MA crosses above 200-day MA (Golden Cross)
- OR 20-day MA > 50-day MA > 200-day MA (stacked bullish)
- Price above all moving averages
- Increasing revenue growth (last 2 quarters)
- Positive analyst sentiment

**Entry:** On crossover confirmation + pullback to 20-day MA
**Exit Target:** +20-40% or when 20-day MA crosses below 50-day
**Stop Loss:** -10% or below 50-day MA
**Expected Hold Time:** 1-3 months

**Data Required:**
- 200-day price history for MAs
- Quarterly revenue data
- Analyst recommendations
- Volume trends

---

#### 5. **Sector Rotation Strategy**
**Objective:** Identify sectors entering bullish phases and find leaders

**Signals:**
- Sector showing relative strength vs S&P 500 (outperforming by 5%+ in 30 days)
- Institutional buying increasing (positive dark pool flow)
- Top 3 stocks in sector by relative strength
- Strong fundamentals in those stocks

**Entry:** Leader stocks showing breakout + sector momentum
**Exit Target:** +25-50% or when sector shows relative weakness
**Stop Loss:** -12% or sector leadership changes
**Expected Hold Time:** 1-4 months

**Data Required:**
- Sector performance comparison
- Individual stock relative strength rankings
- Institutional flow data (if available)
- Fundamental scores

---

#### 6. **Insider Cluster + Momentum**
**Objective:** Follow insider buying clusters combined with technical strength

**Signals:**
- 3+ insiders buying in last 30 days (including C-suite)
- Total insider buying > $500K
- Stock price stable or rising (not catching falling knife)
- Technical: Price > 50-day MA, RSI > 45

**Entry:** On next technical breakout or MA bounce
**Exit Target:** +30-60% (insiders typically have 6-12 month horizon)
**Stop Loss:** -12% from entry
**Expected Hold Time:** 2-4 months

**Data Required:**
- Insider trading transactions (SEC Form 4)
- Insider position/title importance weighting
- Price/MA relationship
- RSI

---

## Implementation Architecture

### Data Sources Integration
1. **FMP (Financial Modeling Prep):**
   - Historical price data
   - Technical indicators (RSI, MAs)
   - Fundamental data (P/E, revenue growth, earnings)
   - Insider trading data
   - Analyst recommendations

2. **Reddit Sentiment (Apewisdom):**
   - Trending tickers
   - Mention volume
   - Sentiment scores
   - Validation signal for momentum plays

3. **User's Transaction History:**
   - Identify patterns in their successful trades
   - Suggest similar setups to their past winners
   - Avoid sectors where they historically underperform

### Signal Scoring System

Each strategy generates signals with:
- **Confidence Score (0-100):** Based on how many criteria are met
- **Risk Level:** Low/Medium/High based on volatility and stop distance
- **Timeframe:** Expected hold period
- **Entry Price:** Specific or trigger level
- **Target Price:** Based on historical probability
- **Stop Loss:** Risk management level
- **Reasoning:** Specific data points supporting the signal

### Personalization Layer

**Match to User's Style:**
- If user historically holds 2-3 weeks → prioritize short-term strategies
- If user has 65% win rate in tech → boost tech sector signals
- If user exits losers quickly (good!) → can tolerate tighter stops
- If user holds winners long → suggest medium-term trend following

**Example:**
```
User pattern: 70% win rate on momentum breakouts in tech, avg hold 18 days
Strategy match: Momentum Breakout + Sector filter (tech) + 2-3 week timeframe
Signal: "NVDA breaking out similar to your TSLA trade (Mar 15, +$2,400)"
```

---

## Risk Management Integration

### Position Sizing Recommendations
Based on user's account size and risk tolerance:
- **High Conviction (90+ confidence):** 5-8% of portfolio
- **Medium Conviction (70-89):** 3-5% of portfolio  
- **Speculative (<70):** 1-2% of portfolio

### Stop Loss Enforcement
- Calculate $ risk per position
- Ensure total portfolio risk < 15% at any time
- Suggest stop loss levels based on ATR (Average True Range)

### Portfolio Correlation
- Avoid suggesting multiple correlated positions
- Diversify across sectors (max 40% in single sector)
- Track overall market beta exposure

---

## Output Format for Trade Suggestions

### Example Output:

```markdown
## 🎯 Trade Idea: NVDA - Momentum Breakout

**Strategy:** Short-term Momentum Breakout  
**Confidence:** 87/100 ⭐⭐⭐⭐  
**Timeframe:** 2-3 weeks  
**Risk Level:** Medium

### Setup Details
- **Current Price:** $485.20
- **Entry Range:** $485-$490 (on breakout confirmation)
- **Target:** $560-$580 (+15-19%)
- **Stop Loss:** $450 (-7.2%)
- **Risk/Reward:** 1:2.3

### Why This Trade?
✅ **Technical Breakout:** Price broke above $480 resistance (held for 6 weeks) with 2.1x average volume
✅ **Strong Momentum:** RSI at 62 (strong but not overbought), up 12% in 10 days
✅ **Reddit Validation:** Mentions up 340% this week (from 45 to 153/day) with 78% positive sentiment
✅ **Fundamentals:** Earnings beat expected, revenue growth 22% YoY

### Similar to Your Past Trades
This setup resembles your **TSLA trade from March 15-29**:
- Both broke multi-week resistance with high volume
- Similar RSI readings (TSLA: 64, NVDA: 62)
- Both had Reddit mention spikes
- **Your result:** +16.2% profit, $2,400 gain in 14 days

### Risk Management
- **Position Size:** $5,000 (4.2% of your $120K portfolio) = ~103 shares
- **Dollar Risk:** $360 if stopped out (0.3% of portfolio)
- **Expected Value:** +$750-950 if target hit (based on 65% historical win rate for this setup)

### Action Plan
1. Set alert for price holding above $485 for 2 hours
2. Enter 50% position at $485-490
3. Add remaining 50% if holds above entry for 24 hours
4. Set stop loss at $450 (trailing stop once up 10%+)
5. Take 50% profit at +12%, let rest run to target

---
**Track this trade:** Reply "Track NVDA" and I'll monitor the setup and alert you on entry/exit signals
```

---

## Backtesting & Validation

### Historical Performance Testing
Before deploying strategies, backtest on:
- 2-3 years of historical data
- Different market conditions (bull, bear, sideways)
- Calculate: Win rate, avg profit, max drawdown, profit factor

### Success Metrics
- **Win Rate:** Target 55%+ for short-term, 60%+ for medium-term
- **Profit Factor:** Target 1.8+ (avg win / avg loss)
- **Risk-Adjusted Return:** Sharpe ratio > 1.5
- **Max Drawdown:** < 20% in any rolling 3-month period

### Continuous Learning
- Track which signals users act on
- Measure actual outcomes vs predictions
- Adjust scoring weights based on real performance
- A/B test strategy variations

---

## Phase 1 Implementation (MVP)

**Priority Strategies to Build First:**
1. ✅ **Momentum Breakout** - Most popular, clear signals
2. ✅ **Insider Cluster + Momentum** - Unique edge, easy to explain
3. ✅ **Trend Following MA Crossover** - Medium-term, lower maintenance

**Data Pipeline:**
1. Daily batch job to scan universe of stocks (S&P 500 + Russell 2000)
2. Calculate indicators and score against strategy criteria
3. Generate top 10 signals per strategy
4. Personalize to user's trading history and style
5. Store signals in database for retrieval

**User Interface:**
- New tool: `get_trade_ideas(strategy=None, timeframe=None, max_results=5)`
- Agent can proactively suggest: "I found 3 momentum breakouts similar to your past wins"
- Users can ask: "Show me medium-term trade ideas in tech"

