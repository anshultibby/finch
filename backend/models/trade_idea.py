"""
Trade ideas — catalyst-driven short-term suggestions, scored independently of
whether they were ever traded.

This is the point of the table. The journal (skills/day_trading/scripts/journal.py)
records *trades*, so it can only ever answer "how did the positions I took do?".
An idea is recorded the moment it's proposed, with the reference price at that
instant, and scored on a fixed horizon regardless of approval or execution. That
separates two questions that were previously tangled:

  - are the ideas any good?      -> outcome / return_pct / r_multiple over ALL ideas
  - did we act on the good ones? -> the same metrics sliced by status

`entry_ref` is the price when the idea was proposed, NOT a fill. Scoring uses it
so an unapproved idea is still measurable.
"""
from sqlalchemy import Column, String, Text, DateTime, Integer, Float, func
from sqlalchemy.dialects.postgresql import JSONB

from core.database import Base


class TradeIdea(Base):
    __tablename__ = "trade_ideas"

    id = Column(String, primary_key=True)  # uuid4 hex[:12]
    user_id = Column(String, nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # ── the idea ─────────────────────────────────────────────────────────────
    symbol = Column(String, nullable=False, index=True)
    direction = Column(String, nullable=False, server_default="long")  # long | short
    catalyst_type = Column(String, nullable=False, index=True)
    catalyst_summary = Column(Text, nullable=False)   # the specific headline, quoted
    thesis = Column(Text, nullable=False)
    bear_case = Column(Text, nullable=True)           # the honest case against
    sources = Column(JSONB, nullable=True)            # [{"title": ..., "url": ...}]

    # ── levels & sizing guidance ─────────────────────────────────────────────
    entry_ref = Column(Float, nullable=False)         # price when proposed (not a fill)
    stop = Column(Float, nullable=False)
    target = Column(Float, nullable=False)
    horizon_days = Column(Integer, nullable=False, server_default="3")
    conviction = Column(Integer, nullable=False, server_default="3")  # 1..5

    # ── lifecycle ────────────────────────────────────────────────────────────
    # proposed -> approved | rejected ; approved ideas may then be executed.
    status = Column(String, nullable=False, server_default="proposed", index=True)
    execution_mode = Column(String, nullable=True)    # auto | manual — chosen at approval
    decided_at = Column(DateTime(timezone=True), nullable=True)

    # ── outcome (scored on the horizon, traded or not) ───────────────────────
    outcome = Column(String, nullable=False, server_default="pending", index=True)
    # pending | target | stop | expired
    scored_at = Column(DateTime(timezone=True), nullable=True)
    exit_price = Column(Float, nullable=True)
    return_pct = Column(Float, nullable=True)
    benchmark_return_pct = Column(Float, nullable=True)  # SPY over the same window
    r_multiple = Column(Float, nullable=True)            # (exit - entry) / (entry - stop)

    def __repr__(self):
        return (f"<TradeIdea({self.symbol} {self.catalyst_type} "
                f"status={self.status} outcome={self.outcome})>")
