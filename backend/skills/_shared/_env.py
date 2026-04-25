"""
Sandbox environment helpers — direct HTTP calls using API keys from env vars.
"""
import os
import json
import urllib.request
import urllib.error
import urllib.parse
from typing import Any, Dict, Optional


def _get(env_var: str) -> Optional[str]:
    return os.getenv(env_var) or None


def call_proxy(
    service: str,
    method: str = "GET",
    url: str = "",
    params: Dict[str, Any] = None,
    body: Any = None,
) -> Any:
    """
    Make a direct HTTP call to an external API, injecting the API key from env vars.

    service: "fmp" | "polygon" | "serper"
    """
    service = service.lower()
    params = dict(params or {})

    key_map = {
        "fmp":     ("FMP_API_KEY",     "apikey"),
        "polygon": ("POLYGON_API_KEY", "apiKey"),
        "serper":  ("SERPER_API_KEY",  "apiKey"),
    }

    if service not in key_map:
        raise RuntimeError(f"Unknown service: {service}")

    env_var, param_name = key_map[service]
    api_key = _get(env_var)
    if not api_key:
        raise RuntimeError(
            f"{env_var} is not set. Add your {service.upper()} API key in Settings > API Keys."
        )
    params[param_name] = api_key

    # Merge any query string already embedded in the URL with explicit params,
    # then rebuild the URL so we never produce a double '?'.
    parsed = urllib.parse.urlsplit(url)
    existing = urllib.parse.parse_qsl(parsed.query, keep_blank_values=True)
    merged = existing + list(params.items())
    full_url = urllib.parse.urlunsplit((
        parsed.scheme, parsed.netloc, parsed.path,
        urllib.parse.urlencode(merged, doseq=True), parsed.fragment,
    ))
    if method.upper() == "GET":
        req = urllib.request.Request(full_url, headers={"User-Agent": "Mozilla/5.0"})
    else:
        encoded_body = json.dumps(body or {}).encode()
        req = urllib.request.Request(full_url, data=encoded_body, method=method.upper(),
                                     headers={"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"})

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        body_text = e.read().decode(errors="replace")
        raise RuntimeError(f"HTTP {e.code} from {service}: {body_text}") from e


def get_user_id() -> Optional[str]:
    return os.getenv("FINCH_USER_ID") or None
