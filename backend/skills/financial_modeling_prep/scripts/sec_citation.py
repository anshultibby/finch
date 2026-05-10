"""Resolve deep-link anchors into SEC iXBRL filings."""

import os
import re

import httpx

from ._cache import cache_key, load_cache, save_cache
from .xbrl_mapping import get_xbrl_concepts

CACHE_DIR = os.path.join(os.path.dirname(__file__), "..", ".cache", "sec_citations")

# Match <ix:nonFraction ... name="concept" ... id="elem_id"> in either attribute order
_IX_RE = re.compile(
    r"<ix:(?:nonFraction|nonfraction|nonNumeric|nonnumeric)"
    r"(?=[^>]*\bname=[\"']([^\"']+)[\"'])"
    r"(?=[^>]*\bid=[\"']([^\"']+)[\"'])"
    r"[^>]*>",
    re.IGNORECASE,
)

_HEADERS = {
    "User-Agent": "Finch/1.0 (anshul.tibrewal2203@gmail.com)",
    "Accept-Encoding": "gzip",
}


def _parse_filing(html: str) -> dict[str, str]:
    """Extract all concept → element-id pairs from iXBRL HTML."""
    mapping: dict[str, str] = {}
    for m in _IX_RE.finditer(html):
        concept, elem_id = m.group(1), m.group(2)
        if concept not in mapping:
            mapping[concept] = elem_id
    return mapping


def _fetch_tag_map(filing_url: str) -> dict[str, str]:
    """Fetch iXBRL HTML and return concept→id mapping (disk-cached)."""
    key = cache_key(filing_url)
    cached = load_cache(CACHE_DIR, key)
    if cached is not None:
        return cached

    resp = httpx.get(filing_url, headers=_HEADERS, timeout=20, follow_redirects=True)
    resp.raise_for_status()
    mapping = _parse_filing(resp.text)

    save_cache(CACHE_DIR, key, mapping)
    return mapping


def resolve_anchor(filing_url: str, fmp_key: str) -> dict | None:
    """Given a filing URL and FMP field name, return the deep-link anchor.

    Returns {"anchor_id": "...", "url": "..."} or None.
    """
    concepts = get_xbrl_concepts(fmp_key)
    if not concepts:
        return None

    tag_map = _fetch_tag_map(filing_url)

    # Exact match
    for concept in concepts:
        if concept in tag_map:
            return {"anchor_id": tag_map[concept], "url": f"{filing_url}#{tag_map[concept]}"}

    # Fuzzy: strip namespace, compare local name only
    for concept in concepts:
        bare = concept.split(":")[-1]
        for tagged, elem_id in tag_map.items():
            if tagged.split(":")[-1] == bare:
                return {"anchor_id": elem_id, "url": f"{filing_url}#{elem_id}"}

    return None
