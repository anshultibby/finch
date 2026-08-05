"""MarketData.app options data — real-time & historical chains, quotes, Greeks, IV.

Each contract record carries: optionSymbol, underlying, expiration (epoch),
side, strike, dte, bid, ask, mid, last, bidSize, askSize, volume, openInterest,
underlyingPrice, inTheMoney, intrinsicValue, extrinsicValue,
iv, delta, gamma, theta, vega.  (No rho — MarketData does not expose it.)
"""
from datetime import datetime, timezone
from ._client import call_marketdata, records_from

# snake_case kwarg -> MarketData camelCase query param
_PARAM_MAP = {
    "strike_limit": "strikeLimit",
    "min_open_interest": "minOpenInterest",
    "min_volume": "minVolume",
    "max_bid_ask_spread": "maxBidAskSpread",
    "max_bid_ask_spread_pct": "maxBidAskSpreadPct",
}


def _iso_date(epoch) -> str | None:
    """Convert epoch seconds to a UTC YYYY-MM-DD string."""
    if epoch is None:
        return None
    try:
        return datetime.fromtimestamp(int(epoch), tz=timezone.utc).strftime("%Y-%m-%d")
    except (ValueError, OSError, TypeError):
        return None


def get_options_chain(
    symbol: str,
    *,
    date: str = None,       # historical EOD lookup, e.g. "2025-06-01". Omit for live.
    dte: int = None,        # days-to-expiry, SINGLE value (closest expiry match), e.g. 30
    expiration: str = None, # specific expiration "2026-09-18" or "all"
    from_date: str = None,  # expiration range start, e.g. "2026-08-20"
    to_date: str = None,    # expiration range end, e.g. "2026-09-20"
    side: str = None,       # "call" or "put"
    strike: str = None,     # e.g. 300, ">300", "300-320"
    delta: str = None,      # e.g. .30, ".30-.70" (single, interval, or expression)
    range: str = None,      # "itm" | "otm" | "all"
    strike_limit: int = None,
    min_open_interest: int = None,
    min_volume: int = None,
    **extra,
) -> list[dict]:
    """Full options chain with Greeks + IV for `symbol`.

    Live by default (real-time if you hold OPRA entitlement, else 15-min delayed).
    Pass `date` for an end-of-day historical chain (data goes back to 2005).
    Adds an ISO `expiration_date` field alongside the raw epoch `expiration`.

    Note on expiry filters: `dte` is a SINGLE closest-match value, not a range.
    To span a range of expirations use `from_date`/`to_date`.

    Example:
        chain = get_options_chain("AAPL", dte=30, side="call", delta=".40-.60")
        for c in chain:
            print(c["optionSymbol"], c["strike"], c["delta"], c["iv"])
    """
    params = {
        "date": date, "dte": dte, "expiration": expiration,
        "from": from_date, "to": to_date, "side": side,
        "strike": strike, "delta": delta, "range": range,
        "strikeLimit": strike_limit, "minOpenInterest": min_open_interest,
        "minVolume": min_volume,
    }
    params.update({_PARAM_MAP.get(k, k): v for k, v in extra.items()})

    data = call_marketdata(f"/v1/options/chain/{symbol.upper()}/", params)
    if data.get("s") != "ok":
        return []
    records = records_from(data)
    for r in records:
        r["expiration_date"] = _iso_date(r.get("expiration"))
    return records


def get_option_quote(option_symbol: str, *, date: str = None,
                     from_date: str = None, to_date: str = None) -> list[dict]:
    """Quote(s) with Greeks + IV for a single OCC option symbol (e.g. 'AAPL260918C00300000').

    Live snapshot by default. Pass `date` for a historical EOD quote, or
    `from_date`/`to_date` for a historical time series.
    """
    params = {"date": date, "from": from_date, "to": to_date}
    data = call_marketdata(f"/v1/options/quotes/{option_symbol.upper()}/", params)
    if data.get("s") != "ok":
        return []
    return records_from(data)


def get_expirations(symbol: str, *, date: str = None, strike: float = None) -> list[str]:
    """List available expiration dates (YYYY-MM-DD strings) for `symbol`."""
    params = {"date": date, "strike": strike}
    data = call_marketdata(f"/v1/options/expirations/{symbol.upper()}/", params)
    return data.get("expirations", []) if data.get("s") == "ok" else []


def get_strikes(symbol: str, *, expiration: str = None, date: str = None) -> dict:
    """Available strikes for `symbol`, keyed by expiration date."""
    params = {"expiration": expiration, "date": date}
    data = call_marketdata(f"/v1/options/strikes/{symbol.upper()}/", params)
    if data.get("s") != "ok":
        return {}
    # Response has an `s` field plus one key per expiration date -> [strikes].
    return {k: v for k, v in data.items() if k not in ("s", "updated")}
