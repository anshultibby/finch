"""FMP API Client — routes through the Finch sandbox proxy."""
from .._env import call_proxy

# Endpoint prefixes that require v4 API (matched with startswith)
V4_ENDPOINT_PREFIXES = (
    '/insider-roster',
    '/insider-trading',
    '/senate-trading',
    '/house-trading',
    '/institutional-ownership',
    '/institutional-holders',
    '/stock_peers',
)


def _fmp_url(endpoint: str, stable: bool = False) -> str:
    if stable:
        return f"https://financialmodelingprep.com/stable{endpoint}"
    base_endpoint = endpoint.split('?')[0]
    version = 'v4' if base_endpoint.startswith(V4_ENDPOINT_PREFIXES) else 'v3'
    return f"https://financialmodelingprep.com/api/{version}{endpoint}"


def call_fmp_api(endpoint: str, params: dict = None):
    """Call FMP API endpoint (auto-detects v3 vs v4) via proxy."""
    try:
        data = call_proxy("fmp", url=_fmp_url(endpoint), params=params or {})
        if isinstance(data, list) and len(data) == 1:
            return data[0]
        return data
    except Exception as e:
        return {"error": str(e)}


def call_fmp_stable_api(endpoint: str, params: dict = None):
    """Call FMP Stable API endpoint via proxy."""
    try:
        data = call_proxy("fmp", url=_fmp_url(endpoint, stable=True), params=params or {})
        if isinstance(data, list) and len(data) == 1:
            return data[0]
        return data
    except Exception as e:
        return {"error": str(e)}
