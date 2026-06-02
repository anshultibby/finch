"""
Prototype: prove Robinhood's agentic OAuth works via a LOOPBACK redirect — the
native-app flow (RFC 8252), exactly how Claude Code does it. This is what a Finch
macOS/iOS app would run on-device.

Flow:
  1. Dynamic client registration with redirect_uri = http://127.0.0.1:PORT/callback
  2. PKCE (S256) authorize URL
  3. Start a loopback HTTP server, wait for Robinhood to redirect the code back
  4. Exchange the code for tokens at the token endpoint

Run, then open the printed AUTHORIZE_URL in a browser on THIS machine, log in, Allow.
If the code lands here (not robinhood.com/oauth/error), loopback works.
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

REG = "https://agent.robinhood.com/oauth/trading/register"
AUTHZ = "https://robinhood.com/oauth"
TOKEN = "https://api.robinhood.com/oauth2/token/"
PORT = 8765
REDIRECT = f"http://127.0.0.1:{PORT}/callback"
SCOPE = "internal"


def _b64(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode()


def register_client() -> str:
    body = json.dumps({
        "client_name": "Finch macOS (prototype)",
        "redirect_uris": [REDIRECT],
        "grant_types": ["authorization_code", "refresh_token"],
        "response_types": ["code"],
        "token_endpoint_auth_method": "none",
    }).encode()
    req = urllib.request.Request(REG, data=body, headers={"Content-Type": "application/json"})
    return json.load(urllib.request.urlopen(req, timeout=20))["client_id"]


_result: dict = {}


class _Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, *a):  # silence
        pass

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path != "/callback":
            self.send_response(404); self.end_headers(); return
        q = urllib.parse.parse_qs(parsed.query)
        _result["code"] = q.get("code", [None])[0]
        _result["error"] = q.get("error", [None])[0]
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
        "scope": SCOPE, "state": state,
    }
    print("CLIENT_ID:", client_id, flush=True)
    print("AUTHORIZE_URL:", f"{AUTHZ}?{urllib.parse.urlencode(params)}", flush=True)

    srv = http.server.HTTPServer(("127.0.0.1", PORT), _Handler)
    print(f"LISTENING: {REDIRECT}", flush=True)
    srv.serve_forever()  # shut down by the handler once the code arrives

    if _result.get("error") or not _result.get("code"):
        print("RESULT: FAILED — no code reached loopback. error =", _result.get("error"), flush=True)
        return
    print("RESULT: CODE RECEIVED ON LOOPBACK ✅", flush=True)

    form = urllib.parse.urlencode({
        "grant_type": "authorization_code", "code": _result["code"],
        "redirect_uri": REDIRECT, "client_id": client_id, "code_verifier": verifier,
    }).encode()
    req = urllib.request.Request(TOKEN, data=form,
                                 headers={"Content-Type": "application/x-www-form-urlencoded"})
    try:
        tok = json.load(urllib.request.urlopen(req, timeout=20))
        print("TOKEN_EXCHANGE: OK ✅  access_token_len =", len(tok.get("access_token", "")),
              " has_refresh =", bool(tok.get("refresh_token")), flush=True)
    except urllib.error.HTTPError as e:
        print("TOKEN_EXCHANGE: FAILED", e.code, e.read().decode(errors="replace"), flush=True)


if __name__ == "__main__":
    main()
