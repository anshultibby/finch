"""
Strategy / playbook — a named set of trading rules the user can adopt and bind
to their goal. Pillar 5 of the strip-down → cockpit initiative (Phase-0).

Only USER-owned strategies live in this table (custom-authored or distilled, plus
starters the user has adopted). The starter "menu to try" is served from code
constants (services/strategy_starters.py), not seeded here — so the table stays
clean and the catalog can evolve without migrations.

The `spec` is the strategy_distiller shape (universe / entry / exit / sizing /
risk / cadence). Adopting a strategy also writes a pointer into UserGoal.config
so the agent's <mission> block runs it.
"""
from sqlalchemy import Column, String, Text, DateTime, func
from sqlalchemy.dialects.postgresql import JSONB

from core.database import Base


class Strategy(Base):
    __tablename__ = "strategies"

    id = Column(String, primary_key=True)  # uuid4 hex[:12]
    user_id = Column(String, nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(),
                        onupdate=func.now(), nullable=False)

    name = Column(String, nullable=False)
    slug = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    # Grouping for the browse menu: income | momentum | dividend | index | custom
    style = Column(String, nullable=False, server_default="custom")
    spec = Column(JSONB, nullable=True)          # distiller shape
    source = Column(String, nullable=False, server_default="custom")  # starter|reddit|custom
    status = Column(String, nullable=False, server_default="adopted", index=True)  # adopted|archived
    source_id = Column(String, nullable=True)    # starter slug this was adopted from (lineage)

    def __repr__(self):
        return f"<Strategy({self.name} style={self.style} status={self.status})>"
