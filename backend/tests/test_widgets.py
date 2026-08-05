"""
Widget tests — spec validation, transforms, publish sweep, and the data-service
cache. These cover the product guardrails without needing a database. Route /
CRUD tests require a Postgres (JSONB) test DB; see docs/widgets/spec.md §6.

Run: ./venv/bin/pytest tests/test_widgets.py -q
"""
import asyncio

import pytest
from pydantic import ValidationError

from schemas.widget import WidgetSpec, CreateWidgetRequest
from crud.widget import assert_publishable, PublishError, _slugify
from services import widget_data as wd


# ── spec validation ─────────────────────────────────────────────────────────
def _spec(**tile_over):
    tile = {"id": "t", "type": "chart", "query": {"source": "quote", "symbols": ["AAPL"]}}
    tile.update(tile_over)
    return {"spec_version": 1, "tiles": [tile]}


def test_valid_spec_parses():
    s = WidgetSpec(**_spec())
    assert len(s.tiles) == 1
    assert s.refresh.interval_seconds == 60


def test_extra_field_rejected():
    with pytest.raises(ValidationError):
        WidgetSpec(**_spec(bogus=1))


def test_bad_tile_type_rejected():
    with pytest.raises(ValidationError):
        WidgetSpec(**_spec(type="candlestick"))


def test_empty_symbols_rejected():
    with pytest.raises(ValidationError):
        WidgetSpec(spec_version=1, tiles=[{"id": "t", "type": "chart",
                                           "query": {"source": "quote", "symbols": []}}])


def test_too_many_tiles_rejected():
    tiles = [{"id": f"t{i}", "type": "stat", "query": {"source": "quote", "symbols": ["AAPL"]}}
             for i in range(13)]
    with pytest.raises(ValidationError):
        WidgetSpec(spec_version=1, tiles=tiles)


def test_unknown_source_rejected():
    with pytest.raises(ValidationError):
        WidgetSpec(**_spec(query={"source": "bloomberg", "symbols": ["AAPL"]}))


def test_refresh_floor_enforced():
    with pytest.raises(ValidationError):
        WidgetSpec(spec_version=1, tiles=[_spec()["tiles"][0]], refresh={"interval_seconds": 5})


def test_tile_ids_unique_helper():
    dup = WidgetSpec(spec_version=1, tiles=[
        {"id": "x", "type": "stat", "query": {"source": "quote", "symbols": ["A"]}},
        {"id": "x", "type": "stat", "query": {"source": "quote", "symbols": ["B"]}},
    ])
    assert dup.tile_ids_unique() is False


def test_inline_and_binding_sources_parse():
    WidgetSpec(spec_version=1, tiles=[
        {"id": "p", "type": "table", "query": {"source": "user_portfolio"}},
        {"id": "c", "type": "text", "query": {"source": "inline", "shape": "markdown", "data": "hi"}},
    ])


def test_create_request_full_example():
    import json, pathlib
    ex = json.loads(pathlib.Path("../docs/widgets/example-hormuz.json").read_text())
    req = CreateWidgetRequest(**ex)
    assert req.spec.tile_ids_unique()
    assert len(req.spec.tiles) == 7


# ── publish sweep ────────────────────────────────────────────────────────────
def test_publish_allows_symbolic_binding():
    assert_publishable({"tiles": [{"id": "p", "query": {"source": "user_portfolio"}}]})


def test_publish_allows_market_sources():
    assert_publishable({"tiles": [
        {"id": "a", "query": {"source": "series", "symbols": [{"symbol": "AAPL"}]}},
        {"id": "b", "query": {"source": "kalshi", "ticker": "X"}},
        {"id": "c", "query": {"source": "inline", "shape": "markdown", "data": "x"}},
    ]})


def test_publish_rejects_unknown_source():
    with pytest.raises(PublishError) as e:
        assert_publishable({"tiles": [{"id": "bad", "query": {"source": "secret_db"}}]})
    assert "bad" in str(e.value)  # names the offending tile


def test_slug_is_readable_and_unique_suffixed():
    a = _slugify("Strait of Hormuz Tracker!!")
    b = _slugify("Strait of Hormuz Tracker!!")
    assert a.startswith("strait-of-hormuz-tracker-")
    assert a != b  # random suffix


# ── transforms ───────────────────────────────────────────────────────────────
def _series(*vals):
    return {"shape": "series", "series": [
        {"label": lbl, "points": [{"t": f"d{i}", "v": v} for i, v in enumerate(pts)]}
        for lbl, pts in vals
    ]}


def test_normalize():
    out = wd._apply_transform(_series(("A", [100, 110, 90])), {"op": "normalize", "base": 100})
    assert [p["v"] for p in out["series"][0]["points"]] == [100.0, 110.0, 90.0]


def test_pct_change():
    out = wd._apply_transform(_series(("A", [100, 110])), {"op": "pct_change"})
    assert [p["v"] for p in out["series"][0]["points"]] == [0.0, 10.0]


def test_normalize_handles_none_and_zero_base():
    out = wd._apply_transform(_series(("A", [None, 50])), {"op": "normalize", "base": 100})
    # first non-null (50) is the base → None stays None, 50 → 100
    pts = [p["v"] for p in out["series"][0]["points"]]
    assert pts[0] is None and pts[1] == 100.0


def test_spread():
    out = wd._apply_transform(_series(("A", [100, 110]), ("B", [40, 50])), {"op": "spread", "a": "A", "b": "B"})
    assert len(out["series"]) == 1
    assert [p["v"] for p in out["series"][0]["points"]] == [60, 60]


def test_ratio_guards_zero_denominator():
    out = wd._apply_transform(_series(("A", [100]), ("B", [0])), {"op": "ratio", "a": "A", "b": "B"})
    assert out["series"][0]["points"][0]["v"] is None


def test_spread_missing_series_errors():
    out = wd._apply_transform(_series(("A", [1])), {"op": "spread", "a": "A", "b": "Z"})
    assert out["shape"] == "error"


def test_sort_table_desc():
    t = {"shape": "table", "columns": ["symbol", "change_pct"],
         "rows": [["X", 1.0], ["Y", 3.0], ["Z", 2.0]]}
    out = wd._apply_transform(t, {"op": "sort", "by": "change_pct", "desc": True})
    assert [r[0] for r in out["rows"]] == ["Y", "Z", "X"]


def test_sort_handles_none_values():
    t = {"shape": "table", "columns": ["s", "v"], "rows": [["A", None], ["B", 2]]}
    out = wd._apply_transform(t, {"op": "sort", "by": "v", "desc": True})
    assert out["rows"][0][0] == "B"  # None sorts last


def test_limit_table_and_news():
    t = {"shape": "table", "columns": ["s"], "rows": [[i] for i in range(10)]}
    assert len(wd._apply_transform(t, {"op": "limit", "n": 3})["rows"]) == 3
    n = {"shape": "news", "items": list(range(10))}
    assert len(wd._apply_transform(n, {"op": "limit", "n": 2})["items"]) == 2


# ── inline payloads ──────────────────────────────────────────────────────────
def test_inline_markdown():
    p = wd._inline_payload({"source": "inline", "shape": "markdown", "data": "**hi**"})
    assert p["shape"] == "markdown" and p["text"] == "**hi**"


def test_inline_unknown_shape_errors():
    p = wd._inline_payload({"source": "inline", "shape": "hologram", "data": 1})
    assert p["shape"] == "error"


# ── cache single-flight ──────────────────────────────────────────────────────
def test_cache_single_flight(monkeypatch):
    """Concurrent resolves of the same (source, params) trigger ONE upstream fetch."""
    wd._cache.clear()
    wd._locks.clear()
    calls = {"n": 0}

    async def fake_fetch():
        calls["n"] += 1
        await asyncio.sleep(0.05)
        return {"shape": "number", "value": 42}

    async def go():
        return await asyncio.gather(*[
            wd._cached("quote", {"n": "AAPL"}, fake_fetch) for _ in range(10)
        ])

    results = asyncio.run(go())
    assert all(r["value"] == 42 for r in results)
    assert calls["n"] == 1  # single-flight collapsed 10 concurrent calls to 1


def test_cache_ttl_reuse(monkeypatch):
    wd._cache.clear()
    wd._locks.clear()
    calls = {"n": 0}

    async def fake_fetch():
        calls["n"] += 1
        return {"shape": "number", "value": 1}

    async def go():
        await wd._cached("quote", {"n": "X"}, fake_fetch)
        await wd._cached("quote", {"n": "X"}, fake_fetch)  # within TTL → cached

    asyncio.run(go())
    assert calls["n"] == 1


# ── tile resolution error isolation ──────────────────────────────────────────
def test_one_bad_tile_does_not_blank_widget():
    async def go():
        spec = {"tiles": [
            {"id": "ok", "type": "text", "query": {"source": "inline", "shape": "markdown", "data": "hi"}},
            {"id": "bad", "type": "chart", "query": {"source": "nonsense"}},
        ]}
        return await wd.resolve_widget_data(spec, viewer_user_id=None)

    out = asyncio.run(go())
    assert out["ok"]["shape"] == "markdown"
    assert out["bad"]["shape"] == "error"
