"""
Catalyst-scanner hygiene tests.

Every case here is a trap found in live data. They're the difference between a
scanner that surfaces tradeable names and one that surfaces warrants, Taiwanese
listings and law-firm spam ranked by a meaningless percentage.
"""
import pytest

from skills.catalyst_ideas.scripts import screen as S


# ── surprise percentage ──────────────────────────────────────────────────────

def test_normal_surprise():
    assert S.surprise_pct(1.87, 1.76) == 6.3


def test_near_zero_estimate_returns_none():
    """Live case: $56.15 actual vs $-0.016 estimate reads as '+351,476%' and
    dominates any ranking. None means 'unknown', never zero."""
    assert S.surprise_pct(56.15, -0.016) is None


def test_implausible_surprise_returns_none():
    """A -8477% 'miss' is a one-time charge or a restatement, not a signal."""
    assert S.surprise_pct(-5.0, 0.11) is None


def test_boundaries():
    assert S.surprise_pct(0.20, 0.10) == 100.0        # estimate exactly at floor
    assert S.surprise_pct(1.0, 0.09) is None          # just under the floor
    assert S.surprise_pct(0.40, 0.10) == 300.0        # exactly at the cap
    assert S.surprise_pct(0.41, 0.10) is None         # just over


def test_missing_inputs():
    assert S.surprise_pct(None, 1.0) is None
    assert S.surprise_pct(1.0, None) is None


def test_negative_estimate_uses_absolute_denominator():
    """Loss narrower than feared is a positive surprise."""
    assert S.surprise_pct(-0.30, -0.50) == 40.0


# ── litigation spam ──────────────────────────────────────────────────────────

@pytest.mark.parametrize("title", [
    "ERASCA LEAD PLAINTIFF DEADLINE AUGUST 10th: Bragar Eagel & Squire Reminds Investors",
    "ROSEN LAW FIRM Announces Class Action on Behalf of XYZ Investors",
    "INVESTOR ALERT: Pomerantz Law Firm Investigation on Behalf of Shareholders",
])
def test_spam_dropped(title):
    assert S.is_litigation_spam(title)


@pytest.mark.parametrize("title", [
    "Acme Corp Awarded $400M Department of Defense Contract",
    "BioCo Announces FDA Approval of Its Lead Candidate",
    "Widget Inc Raises Full-Year Guidance",
])
def test_real_catalysts_kept(title):
    assert not S.is_litigation_spam(title)


# ── candidate shape ──────────────────────────────────────────────────────────

def test_candidate_uppercases_and_shapes():
    c = S.candidate("nvda", "earnings_beat", "  beat  ", "2026-08-07")
    assert c["symbol"] == "NVDA" and c["headline"] == "beat"
    assert set(c) == {"symbol", "catalyst_type", "headline", "date", "detail", "source_url"}


def test_unknown_catalyst_type_rejected():
    """The scorecard buckets on catalyst_type, so a typo would create a
    phantom category that never accumulates enough data to judge."""
    with pytest.raises(ValueError):
        S.candidate("NVDA", "vibes", "h")


# ── screen ───────────────────────────────────────────────────────────────────

GOOD = {"symbol": "AAPL", "price": 313.0, "avgVolume": 50_000_000,
        "marketCap": 3_000_000_000_000, "volume": 40_000_000,
        "changesPercentage": 0.3}


def _screen(cands, quotes, **kw):
    """Run screen() against a stubbed quote map."""
    import skills.catalyst_ideas.scripts.screen as mod
    real = mod.quotes
    mod.quotes = lambda syms: {k: v for k, v in quotes.items() if k in set(syms)}
    try:
        return mod.screen(cands, **kw)
    finally:
        mod.quotes = real


def test_liquid_name_kept_with_rvol():
    c = S.candidate("AAPL", "earnings_beat", "beat")
    out = _screen([c], {"AAPL": GOOD})
    assert len(out) == 1
    assert out[0]["quote"]["rvol"] == 0.8   # 40M / 50M


def test_foreign_listing_dropped_by_suffix():
    """1808.TW cleared every liquidity floor at a $29.5B cap — only the dot
    identifies it as untradeable here."""
    out = _screen([S.candidate("1808.TW", "earnings_beat", "x")],
                  {"1808.TW": dict(GOOD, symbol="1808.TW")})
    assert out == []


def test_zero_volume_keeps_the_name_but_reports_rvol_none():
    """The feed reports volume=0 for liquid names outside RTH — AAPL does it
    post-close. Dropping them loses real candidates, and an rvol of 0.0 would
    read as 'nobody cares' rather than 'not reported yet'."""
    out = _screen([S.candidate("AAPL", "earnings_beat", "x")],
                  {"AAPL": dict(GOOD, volume=0)})
    assert len(out) == 1 and out[0]["quote"]["rvol"] is None


def test_no_quote_dropped():
    """Preferreds and warrants simply have no quote — that's the filter."""
    assert _screen([S.candidate("GMREPA", "earnings_beat", "x")], {}) == []


@pytest.mark.parametrize("field,value", [
    ("price", 1.5), ("avgVolume", 1_000), ("marketCap", 10_000_000),
])
def test_liquidity_floors(field, value):
    out = _screen([S.candidate("XYZ", "earnings_beat", "x")],
                  {"XYZ": dict(GOOD, symbol="XYZ", **{field: value})})
    assert out == []


def test_empty_input():
    assert S.screen([]) == []


# ── dedupe ───────────────────────────────────────────────────────────────────

def test_dedupe_keeps_first_and_records_overlap():
    """A name hit by two feeds at once is worth flagging, not discarding."""
    out = S.dedupe([
        S.candidate("NVDA", "earnings_beat", "beat"),
        S.candidate("NVDA", "analyst_upgrade", "upgrade"),
        S.candidate("AMD", "m_and_a", "deal"),
    ])
    assert len(out) == 2
    nvda = next(c for c in out if c["symbol"] == "NVDA")
    assert nvda["catalyst_type"] == "earnings_beat"
    assert nvda["also_seen_in"] == ["analyst_upgrade"]
