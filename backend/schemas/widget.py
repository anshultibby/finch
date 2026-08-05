"""
Pydantic schemas for widgets — both the API request/response models AND the
widget spec itself.

Spec validation is the product guardrail: strict enums, symbol-count caps, a
tile cap, and `extra="forbid"` so an agent's typo fails loudly at create time
with a readable, self-correctable error rather than rendering a broken widget.
See docs/widgets/spec.md.
"""
from typing import Any, Dict, List, Literal, Optional, Union
from typing_extensions import Annotated

from pydantic import BaseModel, ConfigDict, Field, model_validator


# ──────────────────────────────────────────────────────────────────────────
# Enums (string literals — LLM-friendly, easy to validate)
# ──────────────────────────────────────────────────────────────────────────
TileType = Literal["chart", "stat", "odds", "news", "table", "text"]
TileSize = Literal["sm", "md", "lg", "full"]
Range = Literal["1D", "5D", "1M", "3M", "6M", "YTD", "1Y", "5Y"]
InlineShape = Literal["series", "table", "number", "markdown"]

# Data sources allowed in a *published* (public) widget. All of these are
# either public market data or symbolic per-viewer bindings — never a concrete
# user-account reference. The publish sweep asserts every tile uses one of them.
PUBLIC_SAFE_SOURCES = {
    "quote", "series", "news", "kalshi", "fred", "inline",
    "user_portfolio", "user_watchlist",
}


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


# ──────────────────────────────────────────────────────────────────────────
# Query sources (discriminated on `source`)
# ──────────────────────────────────────────────────────────────────────────
class SeriesSymbol(_Strict):
    symbol: str
    label: Optional[str] = None


class QuoteQuery(_Strict):
    source: Literal["quote"]
    symbols: List[str] = Field(..., min_length=1, max_length=20)


class SeriesQuery(_Strict):
    source: Literal["series"]
    symbols: List[SeriesSymbol] = Field(..., min_length=1, max_length=6)
    range: Range = "3M"


class NewsQuery(_Strict):
    source: Literal["news"]
    query: Optional[str] = None
    symbols: Optional[List[str]] = Field(None, max_length=20)
    limit: int = Field(8, ge=1, le=20)


class KalshiQuery(_Strict):
    source: Literal["kalshi"]
    ticker: str


class FredQuery(_Strict):
    source: Literal["fred"]
    series_id: str
    range: Optional[Range] = "1Y"


class PortfolioQuery(_Strict):
    """Symbolic binding — resolves to the *viewing* user's portfolio. No params
    by design (extra='forbid' means no account ids can be smuggled in)."""
    source: Literal["user_portfolio"]


class WatchlistQuery(_Strict):
    source: Literal["user_watchlist"]


class InlineQuery(_Strict):
    """Frozen data the agent computed in its sandbox (Datawrapper-style
    snapshot). `data` shape must match `shape`."""
    source: Literal["inline"]
    shape: InlineShape
    data: Any
    asof: Optional[str] = None


Query = Annotated[
    Union[
        QuoteQuery, SeriesQuery, NewsQuery, KalshiQuery, FredQuery,
        PortfolioQuery, WatchlistQuery, InlineQuery,
    ],
    Field(discriminator="source"),
]


# ──────────────────────────────────────────────────────────────────────────
# Transforms (discriminated on `op`) — run in-backend, no code execution
# ──────────────────────────────────────────────────────────────────────────
class NormalizeTransform(_Strict):
    op: Literal["normalize"]
    base: float = 100.0


class PctChangeTransform(_Strict):
    op: Literal["pct_change"]


class SpreadTransform(_Strict):
    op: Literal["spread"]
    a: str
    b: str


class RatioTransform(_Strict):
    op: Literal["ratio"]
    a: str
    b: str


class SortTransform(_Strict):
    op: Literal["sort"]
    by: str
    desc: bool = True


class LimitTransform(_Strict):
    op: Literal["limit"]
    n: int = Field(..., ge=1, le=100)


Transform = Annotated[
    Union[
        NormalizeTransform, PctChangeTransform, SpreadTransform,
        RatioTransform, SortTransform, LimitTransform,
    ],
    Field(discriminator="op"),
]


# ──────────────────────────────────────────────────────────────────────────
# Interactive controls — client-side filter/sort/search over a table tile's
# rows. The viewer manipulates these live; no backend refetch. v1 targets
# `table` tiles (the filtering use case). See docs/widgets/spec.md.
# ──────────────────────────────────────────────────────────────────────────
class RangeControl(_Strict):
    id: str = Field(..., min_length=1, max_length=64)
    type: Literal["range"]
    label: str
    column: str  # numeric column to threshold
    min: Optional[float] = None
    max: Optional[float] = None
    step: Optional[float] = None


class SelectControl(_Strict):
    id: str = Field(..., min_length=1, max_length=64)
    type: Literal["select"]
    label: str
    column: str
    options: Optional[List[str]] = None  # None → derive distinct values from data


class SearchControl(_Strict):
    id: str = Field(..., min_length=1, max_length=64)
    type: Literal["search"]
    label: str
    columns: List[str] = Field(..., min_length=1)  # columns to match the query against


class SortControl(_Strict):
    id: str = Field(..., min_length=1, max_length=64)
    type: Literal["sort"]
    label: str
    columns: List[str] = Field(..., min_length=1)
    default_desc: bool = True


Control = Annotated[
    Union[RangeControl, SelectControl, SearchControl, SortControl],
    Field(discriminator="type"),
]


# ──────────────────────────────────────────────────────────────────────────
# Tile + Spec
# ──────────────────────────────────────────────────────────────────────────
class Tile(_Strict):
    id: str = Field(..., min_length=1, max_length=64)
    type: TileType
    title: Optional[str] = None
    size: TileSize = "md"
    query: Query
    transforms: Optional[List[Transform]] = None
    # Display-only, tile-type-specific; kept permissive on purpose (low risk,
    # avoids over-constraining the render layer).
    options: Optional[Dict[str, Any]] = None
    # Interactive filter/sort controls (table tiles only in v1).
    controls: Optional[List[Control]] = Field(None, max_length=6)

    @model_validator(mode="after")
    def _controls_only_on_tables(self):
        if self.controls and self.type != "table":
            raise ValueError(
                f"Tile '{self.id}': controls are only supported on 'table' tiles "
                f"(this tile is '{self.type}')."
            )
        return self


class RefreshPolicy(_Strict):
    interval_seconds: int = Field(60, ge=60, le=86400)


class WidgetSpec(_Strict):
    spec_version: Literal[1] = 1
    tiles: List[Tile] = Field(..., min_length=1, max_length=12)
    refresh: RefreshPolicy = Field(default_factory=RefreshPolicy)

    def tile_ids_unique(self) -> bool:
        ids = [t.id for t in self.tiles]
        return len(ids) == len(set(ids))


# ──────────────────────────────────────────────────────────────────────────
# API request / response models
# ──────────────────────────────────────────────────────────────────────────
class CreateWidgetRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    emoji: Optional[str] = None
    tags: Optional[List[str]] = None
    spec: WidgetSpec


class UpdateWidgetRequest(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    emoji: Optional[str] = None
    tags: Optional[List[str]] = None
    spec: Optional[WidgetSpec] = None


class PublishRequest(BaseModel):
    unpublish: bool = False


class WidgetResponse(BaseModel):
    id: str
    user_id: str
    title: str
    description: Optional[str]
    emoji: Optional[str]
    tags: Optional[List[str]]
    spec: Dict[str, Any]
    visibility: str
    slug: Optional[str]
    cloned_from: Optional[str]
    view_count: int
    clone_count: int
    is_owner: bool = True
    created_at: str
    updated_at: str


class WidgetSummary(BaseModel):
    """Lighter row for lists/gallery — omits the full spec."""
    id: str
    title: str
    description: Optional[str]
    emoji: Optional[str]
    tags: Optional[List[str]]
    visibility: str
    slug: Optional[str]
    view_count: int
    clone_count: int
    created_at: str


class PublicWidgetResponse(BaseModel):
    """Shape returned by the no-auth /shared/{slug} route. Includes the opaque
    widget id so a logged-in viewer can clone it (POST /widgets/{id}/clone)."""
    id: str
    slug: str
    title: str
    description: Optional[str]
    emoji: Optional[str]
    tags: Optional[List[str]]
    spec: Dict[str, Any]
    view_count: int
    clone_count: int
