"""
Alpha Source Framework — research context for agent reasoning.

Synthesized from 18 sources: AQR (Asness), Shleifer & Vishny, MIT (Lo),
Yale (Kelly), Chicago Booth (Kim/Muhn/Nikolaev), Man Group, Acadian,
Lopez de Prado, Hirshleifer, McLean & Pontiff, and others.

The agent reads this framework to reason about whether a specific
opportunity has a real edge. No scoring — just structured knowledge.
"""


ALPHA_FRAMEWORK = {
    "sources": {
        "processing_gap": {
            "what": (
                "Public information != processed information. 90% of data is "
                "unstructured text nobody reads. Complex filings cause stronger "
                "underreaction. LLMs outperform on negation and complex narratives."
            ),
            "research": [
                "Kim/Muhn/Nikolaev (Chicago Booth) — GPT-4 60% accuracy vs 53% human analysts on earnings direction from raw financials",
                "Hirshleifer et al. — limited investor attention causes underreaction, strongest for complex low-coverage firms",
                "Chen/Kelly/Xiu (Yale) — LLM news embeddings predict returns beyond traditional NLP, especially small stocks",
                "Signal8 — SEC filings contain shelf registrations, going concern warnings, death spiral convertibles that markets ignore",
            ],
            "look_for": "Low analyst coverage, complex financials, recent unread SEC filings, nuanced earnings call Q&A",
            "decay": "Moderate — erodes as LLM adoption increases",
        },
        "capacity_gap": {
            "what": (
                "80%+ of Russell 2000 is impractical for large funds. "
                "A $50M position in a $200M company takes weeks and moves the price 10%. "
                "At $50k you execute instantly with zero impact."
            ),
            "research": [
                "Xponance — boutique managers outperform in all six equity categories, largest edge in capacity-constrained segments",
                "QuantStart — retail edge is organizational (no compliance, no benchmark), not informational",
            ],
            "look_for": "Market cap <$2B, avg daily volume <$10M, not in major indices, thin prediction markets",
            "decay": "Low — fund size physics is permanent",
        },
        "willingness_gap": {
            "what": (
                "Known anomalies persist because institutions can't act on them. "
                "Fund managers are fired for short-term underperformance. "
                "Over a third of hedge fund capital is too passive."
            ),
            "research": [
                "Shleifer & Vishny (1997) — real arbitrage requires capital and is risky; worst opportunities coincide with max capital withdrawal risk",
                "CFA Institute — principal-agent problem causes closet indexing; known premia go unharvested",
                "Cliff Asness / AQR (2024) — markets are LESS efficient now: passive indexing, social media, gamification destroyed crowd independence",
            ],
            "look_for": "Contrarian positions, multi-month holds through drawdowns, value/quality factor exposure",
            "decay": "Low — structural, not informational",
        },
        "adaptation_gap": {
            "what": (
                "Alpha is ecological, not static. Market structure changes "
                "create new patterns. Passive indexing created predictable "
                "rebalancing flows. Social media made crowds less independent."
            ),
            "research": [
                "Andrew Lo (MIT) — Adaptive Markets Hypothesis: efficiency varies over time, strategies work/crowd/decay/emerge",
                "Resonanz Capital — alpha migrated to passive-induced inefficiencies (ETF NAV arb, rebalancing flows, flow-driven dislocations)",
            ],
            "look_for": "New market structures, index rebalancing events, social media momentum/panic, regulatory changes",
            "decay": "Variable — each pattern decays but new ones emerge",
        },
        "discipline_gap": {
            "what": (
                "~40% of published factor alpha survives. Judgment-based factors "
                "(value, quality) show no systematic decay. Mechanical factors "
                "(momentum, reversal) decay hyperbolically."
            ),
            "research": [
                "McLean & Pontiff (2016) — 97 anomalies declined ~58% post-publication, but ~40% survives",
                "'Not All Factors Crowd Equally' (2024) — momentum Sharpe fell from 1.5 to 0.25; value/quality show no decay",
            ],
            "look_for": "Strategies that require patience through underperformance, judgment-based signals that resist automation",
            "decay": "Low for judgment-based; high for mechanical/formulaic",
        },
    },
    "warnings": {
        "backtest_overfitting": (
            "Lopez de Prado: 3 independent trials suffice to produce a false strategy. "
            "Realized performance typically 30-40% below backtest."
        ),
        "information_overload": (
            "Columbia Law (2025): LLM accuracy follows inverted U-curve — "
            "more context eventually degrades predictions to near-random. Curate inputs."
        ),
        "live_gap": (
            "Frontiers in AI (2025): zero LLM trading systems have demonstrated "
            "validated live alpha. Every published result is a backtest."
        ),
        "mechanical_decay": (
            "If a signal is a formula over price data, assume it's being crowded. "
            "Momentum Sharpe: 1.5 -> 0.25 over two decades."
        ),
    },
}


def get_alpha_framework():
    """
    Return the full alpha source framework for agent reasoning.

    The agent should read this when evaluating trade opportunities
    to determine which structural gaps (if any) the opportunity exploits.
    """
    return ALPHA_FRAMEWORK
