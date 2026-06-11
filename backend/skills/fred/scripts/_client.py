"""Low-level FRED API client (St. Louis Fed). Free key, generous rate limits."""
import os
import requests

BASE = "https://api.stlouisfed.org/fred"


def fred(endpoint: str, **params) -> dict:
    """
    Call any FRED endpoint, e.g. fred("series/observations", series_id="CPIAUCSL").
    Returns parsed JSON, or {"error": ...} — always check before using.
    """
    key = os.environ.get("FRED_API_KEY")
    if not key:
        return {"error": "FRED_API_KEY is not set — the FRED skill isn't configured."}
    try:
        r = requests.get(f"{BASE}/{endpoint.strip('/')}",
                         params={"api_key": key, "file_type": "json", **params},
                         timeout=30)
        if r.status_code != 200:
            return {"error": f"FRED {endpoint} returned {r.status_code}: {r.text[:200]}"}
        return r.json()
    except requests.RequestException as e:
        return {"error": f"FRED request failed: {e}"}
