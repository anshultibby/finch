// Shared prompt templates for AI quick-actions across the app.
// Used by HomePage action cards and NewChatWelcome quick-actions.

export const PORTFOLIO_REVIEW_PROMPT = `Give me a comprehensive review of my portfolio.

1. Pull my current holdings from my connected brokerage. Summarize total value, cash position, number of positions, and overall unrealized P&L.
2. Break down allocation by:
   - Asset class (stocks, ETFs, bonds, cash)
   - Sector / industry
   - Geography (US vs. international, by region)
   - Market cap (large / mid / small)
3. Flag concentration risks. Call out any single position above 10% of portfolio, any sector above 25%, or unusual factor exposure.
4. Show per-position performance: unrealized gain/loss in $ and %, weighted return, and which positions are driving the most P&L.
5. Highlight anything notable across my holdings — recent earnings beats/misses, material news, valuation outliers, momentum shifts, upcoming catalysts.
6. End with 3–5 specific, actionable suggestions: rebalancing moves, positions to trim or research further, tax considerations, or risks to monitor.

Be direct about tradeoffs. Don't hedge generic advice — tie everything to my actual holdings.`;

export const RESEARCH_STOCK_PROMPT = `Help me research a stock. Walk me through:

1. What the company does and how they make money — main products, customers, revenue mix.
2. Recent financial performance — revenue growth, margins, free cash flow, key trends over the last 4–8 quarters.
3. Recent news, latest earnings, and current analyst sentiment.
4. Valuation: current multiples (P/E, EV/EBITDA, P/S) vs. sector median and the company's own history.
5. Bull case and bear case — the strongest argument on each side.
6. Your overall take, with confidence level and what would change your mind.

Stock: `;

