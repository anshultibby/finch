"""
Kalshi Trading — authenticated HTTP client for the Kalshi REST API.

Handles RSA-PS256 signing. Call get/post/delete with any Kalshi API path.
All responses are raw JSON from Kalshi.

Higher-level helpers:
  get_all() — auto-paginating GET for any list endpoint
"""
from .kalshi import get, get_all, post, delete

__all__ = ["get", "get_all", "post", "delete"]
