"""Keyless HTTP helper for public biotech APIs."""

import httpx

_TIMEOUT = 30
_HEADERS = {"User-Agent": "Finch/1.0 (biotech-pipeline)"}


def get_json(url: str, params: dict = None) -> dict | list:
    try:
        resp = httpx.get(url, params=params or {}, headers=_HEADERS,
                         timeout=_TIMEOUT, follow_redirects=True)
        if resp.status_code >= 400:
            return {"error": f"HTTP {resp.status_code}: {resp.text[:300]}"}
        return resp.json()
    except Exception as e:
        return {"error": f"HTTP request failed: {e}"}


def get_xml(url: str, params: dict = None) -> str:
    try:
        resp = httpx.get(url, params=params or {}, headers=_HEADERS,
                         timeout=_TIMEOUT, follow_redirects=True)
        resp.raise_for_status()
        return resp.text
    except Exception as e:
        return ""


def get_bytes(url: str, timeout: int = 60) -> bytes | None:
    try:
        resp = httpx.get(url, headers=_HEADERS, timeout=timeout,
                         follow_redirects=True)
        resp.raise_for_status()
        return resp.content
    except Exception:
        return None
