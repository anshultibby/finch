"""Close an Alpaca Broker API sandbox account. Stdlib only.

Usage:
    python3 scripts/close_alpaca_account.py <account_id>
"""
import json
import os
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path


def load_env():
    env_path = Path(__file__).resolve().parent.parent / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def http(method, url, headers=None, data=None):
    if isinstance(data, dict):
        data = urllib.parse.urlencode(data).encode()
    req = urllib.request.Request(url, data=data, method=method, headers=headers or {})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.status, resp.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()


def main(account_id: str) -> int:
    load_env()
    sandbox = os.environ.get("ALPACA_BROKER_SANDBOX", "true").lower() in ("1", "true", "yes")
    base = "https://broker-api.sandbox.alpaca.markets" if sandbox else "https://broker-api.alpaca.markets"
    auth_base = "https://authx.sandbox.alpaca.markets" if sandbox else "https://authx.alpaca.markets"

    print(f"Environment: {'SANDBOX' if sandbox else 'LIVE'}  base={base}")

    # Token
    status, body = http(
        "POST",
        f"{auth_base}/v1/oauth2/token",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        data={
            "grant_type": "client_credentials",
            "client_id": os.environ.get("ALPACA_BROKER_CLIENT_ID", ""),
            "client_secret": os.environ.get("ALPACA_BROKER_CLIENT_SECRET", ""),
        },
    )
    if status != 200:
        print(f"Token error {status}: {body}")
        return 1
    token = json.loads(body)["access_token"]
    h = {"Authorization": f"Bearer {token}", "Accept": "application/json"}

    # Snapshot
    status, body = http("GET", f"{base}/v1/accounts/{account_id}", headers=h)
    if status != 200:
        print(f"Account fetch {status}: {body}")
        return 1
    acct = json.loads(body)
    print(f"Before: status={acct.get('status')} cash={acct.get('cash')} equity={acct.get('equity')}")

    # Liquidate positions + cancel orders
    status, body = http(
        "DELETE",
        f"{base}/v1/trading/accounts/{account_id}/positions?cancel_orders=true",
        headers=h,
    )
    print(f"Close positions: {status} {body[:200]}")
    time.sleep(2)

    # Close account
    status, body = http("POST", f"{base}/v1/accounts/{account_id}/actions/close", headers=h)
    print(f"Close account: {status} {body[:300]}")

    # Verify
    status, body = http("GET", f"{base}/v1/accounts/{account_id}", headers=h)
    if status == 200:
        print(f"After: status={json.loads(body).get('status')}")
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python3 scripts/close_alpaca_account.py <account_id>")
        sys.exit(2)
    sys.exit(main(sys.argv[1]))
