"""
Kalshi HTTP client — plain requests + RSA-PS256 signing.

No SDK dependency. Credentials from env vars:
  KALSHI_API_KEY_ID  — Kalshi API key ID
  KALSHI_PRIVATE_KEY — RSA private key in PEM format
"""
import os
import time
import base64
import json
import urllib.request
import urllib.parse
import urllib.error
from typing import Any, Dict, Optional

KALSHI_BASE = "https://api.elections.kalshi.com/trade-api/v2"

_NO_CREDS = {"error": "Kalshi credentials not found. Add your Kalshi API key in Settings > API Keys."}


def _sign(method: str, path: str, body: str, api_key_id: str, private_key_pem: str) -> Dict[str, str]:
    """Return Authorization headers using RSA-PS256 message signing."""
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import padding

    ts_ms = str(int(time.time() * 1000))
    msg = (ts_ms + method.upper() + path + (body or "")).encode()

    key = serialization.load_pem_private_key(private_key_pem.encode(), password=None)
    sig = key.sign(msg, padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.DIGEST_LENGTH), hashes.SHA256())
    sig_b64 = base64.b64encode(sig).decode()

    return {
        "KALSHI-ACCESS-KEY":       api_key_id,
        "KALSHI-ACCESS-TIMESTAMP": ts_ms,
        "KALSHI-ACCESS-SIGNATURE": sig_b64,
        "Content-Type":            "application/json",
    }


class KalshiHTTPClient:
    """Synchronous Kalshi API client using plain urllib + RSA signing."""

    def __init__(self, api_key_id: str, private_key_pem: str):
        self._key_id  = api_key_id
        self._key_pem = private_key_pem

    def _request(self, method: str, path: str, params: Dict = None, body: Any = None) -> Any:
        query = ("?" + urllib.parse.urlencode(params, doseq=True)) if params else ""
        url   = KALSHI_BASE + path + query

        body_str = json.dumps(body) if body is not None else ""
        # signing uses path without base, but with query string
        sign_path = "/trade-api/v2" + path + query
        headers   = _sign(method, sign_path, body_str, self._key_id, self._key_pem)

        data = body_str.encode() if body_str else None
        req  = urllib.request.Request(url, data=data, headers=headers, method=method.upper())

        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read())
        except urllib.error.HTTPError as e:
            body_text = e.read().decode(errors="replace")
            raise RuntimeError(f"HTTP {e.code}: {body_text}") from e

    def get(self, path: str, params: Dict = None) -> Any:
        return self._request("GET", path, params=params)

    def post(self, path: str, body: Any = None) -> Any:
        return self._request("POST", path, body=body)

    def delete(self, path: str) -> Any:
        return self._request("DELETE", path)


def create_client() -> Optional[KalshiHTTPClient]:
    """Return an authenticated KalshiHTTPClient, or None if credentials are missing."""
    api_key_id  = os.getenv("KALSHI_API_KEY_ID")
    private_key = os.getenv("KALSHI_PRIVATE_KEY")
    if not api_key_id or not private_key:
        return None
    return KalshiHTTPClient(api_key_id, private_key)
