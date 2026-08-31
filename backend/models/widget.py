"""
Widgets — declarative financial dashboard cards, agent-generated.

A widget is a JSON `spec` (a list of tiles, each bound to a data source) plus
row-level metadata. The spec is rendered by a fixed client-side renderer, so
widgets are cloneable, cacheable, and safe to embed publicly. See
docs/widgets/spec.md for the full design.

Visibility: private (owner-only) or public (has a `slug`, served at
/widgets/shared/{slug} with no auth). Publishing runs a sweep that guarantees
the spec contains no concrete user-account references — personal data sources
(user_portfolio / user_watchlist) are symbolic and resolve per viewer.
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, func
from sqlalchemy.dialects.postgresql import JSONB

from core.database import Base


class Widget(Base):
    __tablename__ = "widgets"

    id = Column(String, primary_key=True)  # uuid4 hex — one id, no numeric/uid split
    user_id = Column(String, nullable=False, index=True)
    # "widget" (a dashboard card, the default) | "cockpit" (the user's home board,
    # one per user, excluded from lists/gallery). One unified blocks system.
    kind = Column(String, nullable=False, server_default="widget", index=True)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    emoji = Column(String, nullable=True)
    tags = Column(JSONB, nullable=True)  # ["oil", "geopolitics"]
    spec = Column(JSONB, nullable=False)  # WidgetSpec — tiles + refresh
    visibility = Column(String, nullable=False, server_default="private")  # private | public
    slug = Column(String, nullable=True, unique=True, index=True)  # minted on publish
    cloned_from = Column(String, nullable=True)  # source widget id, for lineage
    view_count = Column(Integer, nullable=False, server_default="0")
    clone_count = Column(Integer, nullable=False, server_default="0")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    def __repr__(self):
        return f"<Widget(id='{self.id}', title='{self.title}', visibility='{self.visibility}')>"
