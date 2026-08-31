"""Starter playbooks — the "menu to try" for the strategy library (pillar 5).

Served as code constants, NOT seeded into the DB: the catalog can evolve without
migrations, and the `strategies` table only ever holds a user's own (adopted or
authored) rows. When a user adopts a starter, its `spec` is copied into a new
`strategies` row with `source="starter"` and `source_id=<slug>`.

Specs follow the strategy_distiller shape (a readable subset). These are
educational templates, not advice — every one carries a disclaimer.
"""
from typing import Optional

_DISCLAIMER = (
    "Educational template, not investment advice. Rules run against YOUR account "
    "with hold-to-approve on every trade."
)

STARTER_STRATEGIES: list[dict] = [
    {
        "slug": "index-dca",
        "name": "Index DCA",
        "style": "index",
        "description": "Dollar-cost average a broad index on a fixed cadence. The boring, "
                       "durable base most goals should start from.",
        "spec": {
            "style_summary": "Buy a fixed dollar amount of a broad-market index on a schedule, "
                             "regardless of price. Time in market over timing the market.",
            "instrument": "equity_etf",
            "options_enabled": False,
            "universe": {"selection_rules": "One broad index ETF", "example_tickers": ["VOO", "VTI", "SPY"]},
            "entry": {"trigger": "Fixed cadence (e.g. weekly/monthly), no market timing"},
            "exit": {"stop_or_line_in_sand": "None — long-term hold; only rebalance"},
            "sizing": {"cash_reserve": "Keep an emergency buffer; invest surplus only"},
            "cadence": "weekly or monthly",
            "risk_notes": ["Single-index concentration is market risk; that's the point.",
                           "Don't pause contributions in drawdowns — that breaks the strategy."],
            "disclaimer": _DISCLAIMER,
        },
    },
    {
        "slug": "trend-momentum",
        "name": "Trend / Momentum",
        "style": "momentum",
        "description": "Ride established uptrends; cut quickly when the trend breaks. "
                       "Rules-based, no predictions.",
        "spec": {
            "style_summary": "Hold names in a clear uptrend (above rising 50/200-day MAs); "
                             "exit on a trend break. Let winners run, cut losers fast.",
            "instrument": "equity",
            "options_enabled": False,
            "universe": {"selection_rules": "Liquid large/mid caps in confirmed uptrends",
                         "example_tickers": ["NVDA", "MSFT", "AAPL"]},
            "entry": {"trigger": "Price > rising 50-DMA and 50-DMA > 200-DMA; enter on pullback to 50-DMA"},
            "exit": {"stop_or_line_in_sand": "Close below 50-DMA or a fixed % trailing stop",
                     "profit_target": "None — trail the trend"},
            "sizing": {"max_per_underlying": "~10-15% of book", "concurrent_positions": "5-8"},
            "cadence": "check daily/weekly",
            "risk_notes": ["Whipsaws in choppy markets; expect several small losses per winner.",
                           "Momentum reverses hard — the stop is the whole strategy."],
            "disclaimer": _DISCLAIMER,
        },
    },
    {
        "slug": "dividend-income",
        "name": "Dividend Income",
        "style": "dividend",
        "description": "Build a book of durable dividend payers for growing, recurring income.",
        "spec": {
            "style_summary": "Own quality companies with sustainable, growing dividends; "
                             "reinvest or draw the income. Prioritize payout durability over yield.",
            "instrument": "equity",
            "options_enabled": False,
            "universe": {"selection_rules": "Profitable, low-payout-ratio dividend growers "
                         "(dividend aristocrats / quality high-yield)",
                         "example_tickers": ["JNJ", "PG", "KO", "SCHD"]},
            "entry": {"trigger": "Add on valuation dips; avoid chasing unsustainable yields"},
            "exit": {"stop_or_line_in_sand": "Dividend cut or deteriorating fundamentals"},
            "sizing": {"concurrent_positions": "10-20 for diversification"},
            "cadence": "review quarterly (earnings + dividend declarations)",
            "risk_notes": ["A very high yield is often a warning, not a bargain.",
                           "Sector concentration (utilities/REITs) sneaks in — watch it."],
            "disclaimer": _DISCLAIMER,
        },
    },
    {
        "slug": "wheel",
        "name": "The Wheel",
        "style": "income",
        "description": "Sell cash-secured puts, get assigned, sell covered calls — collect "
                       "premium on stocks you'd happily own. Options required.",
        "spec": {
            "style_summary": "Sell cash-secured puts on a stock you want to own; if assigned, "
                             "sell covered calls against the shares. Repeat, collecting premium.",
            "instrument": "options",
            "options_enabled": True,
            "universe": {"selection_rules": "Stocks you're happy to own at the strike; liquid options",
                         "example_tickers": ["AAPL", "AMD", "F"]},
            "entry": {"trigger": "Sell CSP at ~0.30 delta, 30-45 DTE, on names with IV rank you like",
                      "dte": "30-45", "delta_or_strike": "~0.30 delta"},
            "exit": {"profit_target": "Close at ~50% max profit; roll near expiry if needed",
                     "assignment_handling": "Take assignment on names you want; then sell covered calls"},
            "sizing": {"max_per_underlying": "Only what you can cash-secure",
                       "cash_reserve": "100% of put notional held in cash"},
            "cadence": "weekly management",
            "risk_notes": ["You can be assigned in a fast drop — only wheel names you'd hold.",
                           "Covered calls cap upside; you'll miss big rips on the shares.",
                           "Requires options approval and real options literacy."],
            "disclaimer": _DISCLAIMER,
        },
    },
    {
        "slug": "cash-secured-puts",
        "name": "Cash-Secured Puts",
        "style": "income",
        "description": "Get paid to set a limit buy: sell puts at prices you'd love to own. "
                       "The first half of the wheel.",
        "spec": {
            "style_summary": "Sell cash-secured puts at strikes where you'd be happy to buy the "
                             "stock. Keep the premium if it stays above; own it cheaper if not.",
            "instrument": "options",
            "options_enabled": True,
            "universe": {"selection_rules": "Quality names you want to accumulate on dips",
                         "example_tickers": ["MSFT", "GOOGL", "SCHD"]},
            "entry": {"trigger": "Sell put at a strike = your target buy price, 30-45 DTE",
                      "dte": "30-45", "delta_or_strike": "0.20-0.30 delta or your buy price"},
            "exit": {"profit_target": "~50% max profit or take assignment",
                     "assignment_handling": "Assignment = buying the stock you wanted, cheaper"},
            "sizing": {"cash_reserve": "100% of notional secured in cash"},
            "cadence": "weekly",
            "risk_notes": ["Downside is owning the stock in a crash — size for that.",
                           "Requires options approval."],
            "disclaimer": _DISCLAIMER,
        },
    },
]

_BY_SLUG = {s["slug"]: s for s in STARTER_STRATEGIES}


def get_starter(slug: str) -> Optional[dict]:
    """The starter playbook with this slug, or None."""
    return _BY_SLUG.get(slug)
