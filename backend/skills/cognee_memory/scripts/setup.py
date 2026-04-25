"""
Cognee Memory skill — sandbox-side helpers that call the backend memory API.
The auth token is injected as FINCH_AUTH_TOKEN env var by the sandbox builder.
"""
import os
import json
import urllib.request
import urllib.error


def _api_url() -> str:
    return os.environ.get("FINCH_API_URL", "http://localhost:8000")


def _headers() -> dict:
    token = os.environ.get("FINCH_AUTH_TOKEN", "")
    h = {"Content-Type": "application/json"}
    if token:
        h["Authorization"] = f"Bearer {token}"
    return h


def _post(path: str, body: dict = None) -> dict:
    url = f"{_api_url()}{path}"
    data = json.dumps(body or {}).encode()
    req = urllib.request.Request(url, data=data, method="POST", headers=_headers())
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return {"success": False, "error": f"HTTP {e.code}: {e.read().decode(errors='replace')}"}


def _get(path: str) -> dict:
    url = f"{_api_url()}{path}"
    req = urllib.request.Request(url, headers=_headers())
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return {"success": False, "error": f"HTTP {e.code}: {e.read().decode(errors='replace')}"}
