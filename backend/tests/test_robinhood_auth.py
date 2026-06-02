"""
Unit tests for the Robinhood agentic-trading OAuth helpers (pure logic only —
no DB, no network). Covers PKCE generation, the signed/self-contained state
round-trip, the redirect URI, and MCP-result parsing.
"""
import base64
import hashlib
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Provide an encryption key + minimal DB URL so importing the service (which
# constructs the Fernet-backed encryption_service) succeeds.
os.environ.setdefault(
    "ENCRYPTION_KEY",
    __import__("cryptography.fernet", fromlist=["Fernet"]).Fernet.generate_key().decode(),
)
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://u:p@localhost/db")

import services.robinhood_auth as ra


def test_pkce_challenge_matches_verifier():
    verifier, challenge = ra._new_pkce()
    # No padding, URL-safe.
    assert "=" not in verifier and "=" not in challenge
    expected = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    assert challenge == expected


def test_state_roundtrip_is_tamper_evident():
    payload = {"user_id": "u123", "code_verifier": "v", "client_id": "c", "nonce": "n"}
    state = ra._encode_state(payload)
    assert ra._decode_state(state) == payload
    # Mutating the token body must fail HMAC verification, not silently decode.
    flipped = ("A" if state[0] != "A" else "B") + state[1:]
    assert ra._decode_state(flipped) is None
    assert ra._decode_state("not-a-real-state") is None


def test_redirect_uri_is_backend_callback():
    assert ra._redirect_uri().endswith("/robinhood/callback")


class _Block:
    def __init__(self, text):
        self.text = text


class _Result:
    def __init__(self, content):
        self.content = content


def test_parse_mcp_result_json_and_text():
    assert ra._parse_mcp_result(_Result([_Block('{"a": 1}')])) == {"a": 1}
    assert ra._parse_mcp_result(_Result([_Block("plain")])) == "plain"
    assert ra._parse_mcp_result(_Result([])) is None
