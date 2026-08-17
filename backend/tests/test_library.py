"""
The library: file by subject, navigate by structure.

These pin the behaviour that keeps context cost flat as the corpus grows —
index tells you what exists AND what it costs, outline tells you what's inside,
read gets one section. Nothing here should ever need to hand back a whole
corpus, and nothing should need rotation or trimming to stay bounded.
"""
import importlib
import os
import tempfile

import pytest


@pytest.fixture
def lib(monkeypatch):
    with tempfile.TemporaryDirectory() as d:
        store = os.path.join(d, "store")
        shared = os.path.join(d, "chat_files")
        os.makedirs(store)
        os.makedirs(os.path.join(shared, "stocks"))
        os.makedirs(os.path.join(shared, "tasks"))
        monkeypatch.setenv("LIBRARY_ROOT", store)
        monkeypatch.setenv("LIBRARY_SHARED_ROOT", shared)
        from skills.library.scripts import notes as N
        importlib.reload(N)
        yield N
    importlib.reload(N)


def _write(lib, rel, text):
    full = lib._resolve(rel)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, "w") as f:
        f.write(text)
    return full


NVDA = """# NVDA

## Thesis
AI capex cycle still expanding. Long into the Q3 print.

## Invalidation
Hyperscaler capex guide cut, or close below 168.

## History
2026-06-02 opened. 2026-07-14 added on the dip.
"""


# ── structure ────────────────────────────────────────────────────────────────

def test_outline_gives_headings_with_line_numbers(lib):
    _write(lib, "stocks/NVDA/thesis.md", NVDA)
    got = lib.outline("stocks/NVDA/thesis.md")
    assert [h["title"] for h in got] == ["NVDA", "Thesis", "Invalidation", "History"]
    assert [h["level"] for h in got] == [1, 2, 2, 2]
    assert got[1]["line"] == 3


def test_headings_inside_code_fences_are_not_headings(lib):
    _write(lib, "playbooks/x.md", "# Real\n\n```python\n# not a heading\n```\n\n## Also real\n")
    assert [h["title"] for h in lib.outline("playbooks/x.md")] == ["Real", "Also real"]


# ── reading one section ──────────────────────────────────────────────────────

def test_read_returns_just_the_section(lib):
    _write(lib, "stocks/NVDA/thesis.md", NVDA)
    got = lib.read("stocks/NVDA/thesis.md", "Invalidation")
    assert "close below 168" in got
    assert "AI capex" not in got      # did not bleed into the previous section
    assert "2026-06-02" not in got    # nor the next


def test_read_section_includes_its_subsections(lib):
    _write(lib, "a.md", "# T\n\n## Big\n\n### Small\ninner\n\n## Next\nother\n")
    got = lib.read("a.md", "Big")
    assert "inner" in got and "other" not in got


def test_read_heading_match_is_forgiving(lib):
    _write(lib, "stocks/NVDA/thesis.md", NVDA)
    assert lib.read("stocks/NVDA/thesis.md", "invalidation") == \
           lib.read("stocks/NVDA/thesis.md", "Invalidation")


def test_missing_heading_names_the_alternatives(lib):
    _write(lib, "stocks/NVDA/thesis.md", NVDA)
    with pytest.raises(KeyError) as e:
        lib.read("stocks/NVDA/thesis.md", "Valuation")
    assert "Thesis" in str(e.value)


# ── the shelf ────────────────────────────────────────────────────────────────

def test_index_spans_both_trees(lib):
    _write(lib, "stocks/NVDA/thesis.md", NVDA)
    _write(lib, "playbooks/day-trading.md", "# Day trading\n\n## Rules\nlongs only\n")
    paths = {e["path"] for e in lib.index()}
    assert paths == {"stocks/NVDA/thesis.md", "playbooks/day-trading.md"}


def test_index_reports_retrieval_cost(lib):
    _write(lib, "big.md", "# Big\n\n" + ("word " * 4000))
    entry = next(e for e in lib.index() if e["path"] == "big.md")
    assert entry["tokens"] > 3000          # the agent can see this is expensive
    assert entry["sections"] == []


def test_index_is_cheap_relative_to_the_corpus(lib):
    """The point of the index: it stays small while the library grows."""
    import json
    for i in range(60):
        _write(lib, f"stocks/S{i}/thesis.md", f"# S{i}\n\n## Thesis\n" + ("filler " * 800))
    corpus = sum(e["tokens"] for e in lib.index())
    idx = len(json.dumps(lib.index())) // 4
    assert corpus > 40_000        # a real pile of research
    assert idx < 3_000            # ...surveyable for a fraction of a percent
    assert idx < corpus / 15


def test_index_scoped_to_a_shelf(lib):
    _write(lib, "stocks/NVDA/thesis.md", NVDA)
    _write(lib, "playbooks/p.md", "# P\n")
    assert [e["path"] for e in lib.index("stocks")] == ["stocks/NVDA/thesis.md"]


def test_paths_from_index_can_be_read_back(lib):
    """_relative must invert _resolve or the index is useless."""
    _write(lib, "stocks/NVDA/thesis.md", NVDA)
    path = lib.index("stocks")[0]["path"]
    assert "Thesis" in lib.read(path, "Thesis")


# ── find: locations, not content ─────────────────────────────────────────────

def test_find_returns_the_section_a_hit_sits_under(lib):
    _write(lib, "stocks/NVDA/thesis.md", NVDA)
    hits = lib.find("close below 168")
    assert len(hits) == 1
    assert hits[0]["path"] == "stocks/NVDA/thesis.md"
    assert hits[0]["heading"] == "Invalidation"


def test_find_spans_documents_and_is_bounded(lib):
    for i in range(30):
        _write(lib, f"journal/2026-{i:02d}.md", "# j\n\n## e\ndilution risk here\n")
    hits = lib.find("dilution", limit=5)
    assert len(hits) == 5


def test_find_snippets_stay_small(lib):
    _write(lib, "a.md", "# a\n\n## s\n" + "x" * 5000 + " needle " + "y" * 5000)
    hit = lib.find("needle")[0]
    assert len(hit["snippet"]) < 300


# ── writing ──────────────────────────────────────────────────────────────────

def test_write_section_leaves_the_rest_alone(lib):
    _write(lib, "stocks/NVDA/thesis.md", NVDA)
    lib.write_section("stocks/NVDA/thesis.md", "Thesis", "Changed my mind — flat.")
    assert "Changed my mind" in lib.read("stocks/NVDA/thesis.md", "Thesis")
    assert "close below 168" in lib.read("stocks/NVDA/thesis.md", "Invalidation")
    assert "2026-06-02" in lib.read("stocks/NVDA/thesis.md", "History")


def test_write_section_creates_missing_sections_and_files(lib):
    lib.write_section("stocks/MU/thesis.md", "Thesis", "cyclical bottom")
    assert "cyclical bottom" in lib.read("stocks/MU/thesis.md", "Thesis")
    lib.write_section("stocks/MU/thesis.md", "Invalidation", "DRAM pricing rolls")
    assert [h["title"] for h in lib.outline("stocks/MU/thesis.md")][1:] == \
           ["Thesis", "Invalidation"]


def test_write_section_append_keeps_existing_body(lib):
    lib.write_section("a.md", "Log", "first")
    lib.write_section("a.md", "Log", "second", mode="append")
    body = lib.read("a.md", "Log")
    assert "first" in body and "second" in body


def test_log_appends_dated_entries_that_outline_lists(lib):
    lib.log("journal/2026-08.md", "2026-08-17 nightly", "flat, no trades")
    lib.log("journal/2026-08.md", "2026-08-18 nightly", "opened MU")
    assert [h["title"] for h in lib.outline("journal/2026-08.md")][1:] == \
           ["2026-08-17 nightly", "2026-08-18 nightly"]
    assert "opened MU" in lib.read("journal/2026-08.md", "2026-08-18 nightly")


def test_latest_returns_the_tail_of_a_log(lib):
    for i in range(10):
        lib.log("journal/2026-08.md", f"entry {i}", f"body {i}")
    got = lib.latest("journal/2026-08.md", 2)
    assert [e["title"] for e in got] == ["entry 8", "entry 9"]
    assert got[-1]["body"] == "body 9"


def test_dated_files_bound_themselves_without_rotation(lib):
    """A month of entries stays small because next month is a new file."""
    for day in range(1, 32):
        lib.log("journal/2026-08.md", f"2026-08-{day:02d}", "did a thing. " * 40)
    lib.log("journal/2026-09.md", "2026-09-01", "new month")
    aug = next(e for e in lib.index("journal") if e["path"].endswith("2026-08.md"))
    assert aug["tokens"] < 6_000
    assert len(lib.index("journal")) == 2


# ── the task board ───────────────────────────────────────────────────────────

TASK = """---
status: {status}
opened: 2026-08-10
symbols: [NVDA]
review: {review}
---
# {title}

## What's next
something
"""


def test_tasks_reads_frontmatter_into_a_board(lib):
    _write(lib, "tasks/nvda-q3.md", TASK.format(status="open", review="2026-08-20", title="NVDA Q3"))
    board = lib.tasks()
    assert len(board) == 1
    assert board[0]["status"] == "open"
    assert board[0]["symbols"] == ["NVDA"]
    assert board[0]["title"] == "NVDA Q3"


def test_tasks_hides_closed_work_by_default(lib):
    _write(lib, "tasks/a.md", TASK.format(status="open", review="2026-08-20", title="A"))
    _write(lib, "tasks/b.md", TASK.format(status="done", review="2026-08-01", title="B"))
    assert [t["title"] for t in lib.tasks()] == ["A"]
    assert len(lib.tasks(status=None)) == 2


def test_tasks_due_by_is_a_work_queue(lib):
    _write(lib, "tasks/now.md", TASK.format(status="open", review="2026-08-17", title="Now"))
    _write(lib, "tasks/later.md", TASK.format(status="open", review="2026-09-30", title="Later"))
    assert [t["title"] for t in lib.tasks(due_by="2026-08-18")] == ["Now"]


def test_frontmatter_absent_is_not_an_error(lib):
    _write(lib, "tasks/plain.md", "# No frontmatter\n\n## Body\n")
    assert lib.frontmatter("tasks/plain.md") == {}
    assert lib.tasks()[0]["title"] == "No frontmatter"   # defaults to open
