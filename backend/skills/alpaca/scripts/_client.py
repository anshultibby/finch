"""
Alpaca client for use inside E2B sandbox.
Uses env vars injected by the backend.
"""
import os


def get_trading_client(paper: bool = True):
    """Get an Alpaca TradingClient using env vars."""
    try:
        from alpaca.trading.client import TradingClient
    except ImportError:
        raise RuntimeError("alpaca-py not installed. Run: pip install alpaca-py")

    api_key = os.environ.get("ALPACA_API_KEY")
    secret_key = os.environ.get("ALPACA_SECRET_KEY")

    if not api_key or not secret_key:
        raise RuntimeError("ALPACA_API_KEY and ALPACA_SECRET_KEY env vars required")

    return TradingClient(api_key=api_key, secret_key=secret_key, paper=paper)
