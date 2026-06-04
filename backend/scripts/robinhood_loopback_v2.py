"""
Robinhood agentic OAuth loopback — v2, with RFC 8707 resource indicators.

Same flow as robinhood_loopback_prototype.py, but adds `resource=<MCP server>`
to BOTH the authorize request and the token exchange. Robinhood's MCP OAuth
advertises its issuer/resource as https://agent.robinhood.com/mcp/trading, and
the spec (MCP 2025-06-18) requires the resource indicator — its absence is the
most likely cause of the "something went wrong" error on the authorize page.

Run it, open the printed AUTHORIZE_URL in a desktop browser where you're logged
into Robinhood, approve, and watch for the token-exchange result.
"""
import base64
import hashlib
import http.server
import json
import os
import secrets
import threading
import urllib.parse
import urllib.request
import urllib.error

REG = "https://agent.robinhood.com/oauth/trading/register"
AUTHZ = "https://robinhood.com/oauth"
TOKEN = "https://api.robinhood.com/oauth2/token/"
RESOURCE = "https://agent.robinhood.com/mcp/trading"  # RFC 8707 resource indicator
PORT = 8765
REDIRECT = f"http://127.0.0.1:{PORT}/callback"
SCOPE = "internal"


def _b64(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode()


def register_client() -> str:
    body = json.dumps({
        "client_name": "Finch macOS (v2)",
        "redirect_uris": [REDIRECT],
        "grant_types": ["authorization_code", "refresh_token"],
        "response_types": ["code"],
        "token_endpoint_auth_method": "none",
    }).encode()
    req = urllib.request.Request(REG, data=body, headers={"Content-Type": "application/json"})
    return json.load(urllib.request.urlopen(req, timeout=20))["client_id"]


_result: dict = {}


class _Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path != "/callback":
            self.send_response(404); self.end_headers(); return
        q = urllib.parse.parse_qs(parsed.query)
        _result["code"] = q.get("code", [None])[0]
        _result["error"] = q.get("error", [None])[0]
        _result["error_description"] = q.get("error_description", [None])[0]
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        self.wfile.write(b"<h2>Finch connected. You can close this tab.</h2>")
        threading.Thread(target=self.server.shutdown, daemon=True).start()


def main():
    client_id = register_client()
    verifier = _b64(os.urandom(32))
    challenge = _b64(hashlib.sha256(verifier.encode()).digest())
    state = secrets.token_urlsafe(12)
    params = {
        "response_type": "code", "client_id": client_id, "redirect_uri": REDIRECT,
        "code_challenge": challenge, "code_challenge_method": "S256",
        "scope": SCOPE, "state": state, "resource": RESOURCE,
    }
    print("CLIENT_ID:", client_id, flush=True)
    print("AUTHORIZE_URL:", f"{AUTHZ}?{urllib.parse.urlencode(params)}", flush=True)

    srv = http.server.HTTPServer(("127.0.0.1", PORT), _Handler)
    print(f"LISTENING: {REDIRECT}", flush=True)
    srv.serve_forever()

    if _result.get("error") or not _result.get("code"):
        print("RESULT: FAILED — error =", _result.get("error"),
              "desc =", _result.get("error_description"), flush=True)
        return
    print("RESULT: CODE RECEIVED ON LOOPBACK", flush=True)

    form = urllib.parse.urlencode({
        "grant_type": "authorization_code", "code": _result["code"],
        "redirect_uri": REDIRECT, "client_id": client_id, "code_verifier": verifier,
        "resource": RESOURCE,
    }).encode()
    req = urllib.request.Request(TOKEN, data=form,
                                 headers={"Content-Type": "application/x-www-form-urlencoded"})
    try:
        tok = json.load(urllib.request.urlopen(req, timeout=20))
        print("TOKEN_EXCHANGE: OK  access_token_len =", len(tok.get("access_token", "")),
              " has_refresh =", bool(tok.get("refresh_token")), flush=True)
    except urllib.error.HTTPError as e:
        print("TOKEN_EXCHANGE: FAILED", e.code, e.read().decode(errors="replace"), flush=True)


if __name__ == "__main__":
    main()
