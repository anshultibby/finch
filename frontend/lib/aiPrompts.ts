// Shared prompt templates for AI quick-actions across the app.
// Used by HomePage action cards and NewChatWelcome quick-actions.

export const TLH_PROMPT = `Run a comprehensive tax-loss harvesting analysis on my portfolio.

1. Pull my current holdings from my connected brokerage and compute unrealized gains/losses for each position from cost basis.
2. Identify positions sitting at unrealized losses worth harvesting. State the loss threshold you used and why.
3. For each candidate, propose 1–2 replacement securities that preserve similar market and sector exposure without triggering a wash sale (different CUSIP, similar but not substantially identical).
4. Check for wash-sale risk from purchases in the last 30 days, including dividend reinvestments and partial fills.
5. Estimate total tax savings. Assume long-term capital gains for positions held >1 year and short-term otherwise. Ask me my marginal rates if you need them.
6. Present results as actionable swap proposals I can approve or reject one by one.

Be precise about dollar amounts and lot-level detail where it matters.`;

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

// Investor persona review prompts
export interface InvestorPersona {
  id: string;
  name: string;
  shortName: string;
  tagline: string;
  quote: string;
  description: string;
  gradient: string;
  accentColor: string;
  initial: string;
}

export const INVESTOR_PERSONAS: InvestorPersona[] = [
  {
    id: 'buffett',
    name: 'Warren Buffett',
    shortName: 'Buffett',
    tagline: 'The Oracle of Omaha',
    quote: 'Price is what you pay. Value is what you get.',
    description: 'Moats, business quality, owner earnings',
    gradient: 'from-blue-500 to-indigo-600',
    accentColor: 'blue',
    initial: 'WB',
  },
  {
    id: 'munger',
    name: 'Charlie Munger',
    shortName: 'Munger',
    tagline: 'The Abominable No-Man',
    quote: 'Invert, always invert.',
    description: 'Mental models, cognitive biases, brutal clarity',
    gradient: 'from-amber-500 to-orange-600',
    accentColor: 'amber',
    initial: 'CM',
  },
  {
    id: 'marks',
    name: 'Howard Marks',
    shortName: 'Marks',
    tagline: 'The Memo Writer',
    quote: 'The most important thing is being attentive to cycles.',
    description: 'Second-level thinking, risk, market cycles',
    gradient: 'from-emerald-500 to-teal-600',
    accentColor: 'emerald',
    initial: 'HM',
  },
  {
    id: 'lynch',
    name: 'Peter Lynch',
    shortName: 'Lynch',
    tagline: 'The People\'s Investor',
    quote: 'Know what you own, and know why you own it.',
    description: 'Ten-baggers, stock categories, everyday edge',
    gradient: 'from-violet-500 to-purple-600',
    accentColor: 'violet',
    initial: 'PL',
  },
  {
    id: 'soros',
    name: 'George Soros',
    shortName: 'Soros',
    tagline: 'The Man Who Broke the Bank of England',
    quote: 'Find the trend whose premise is false, and bet against it.',
    description: 'Reflexivity, macro regimes, boom/bust cycles',
    gradient: 'from-red-500 to-rose-600',
    accentColor: 'red',
    initial: 'GS',
  },
  {
    id: 'cathie_wood',
    name: 'Cathie Wood',
    shortName: 'Cathie',
    tagline: 'The Disruption Evangelist',
    quote: 'The biggest risk is not being exposed to disruptive innovation.',
    description: 'Innovation platforms, exponential growth, 5-year bets',
    gradient: 'from-fuchsia-500 to-pink-600',
    accentColor: 'fuchsia',
    initial: 'CW',
  },
  {
    id: 'damodaran',
    name: 'Aswath Damodaran',
    shortName: 'Damodaran',
    tagline: 'The Dean of Valuation',
    quote: 'A story without numbers is a fairy tale. Numbers without a story are noise.',
    description: 'Narrative-to-numbers, DCF, valuation craft',
    gradient: 'from-slate-500 to-gray-700',
    accentColor: 'slate',
    initial: 'AD',
  },
];

export function getInvestorReviewPrompt(investor: InvestorPersona): string {
  return `Review my portfolio as ${investor.name}. Pull my current holdings from my connected brokerage and give me ${investor.shortName}'s honest, unfiltered take on every position.`;
}
