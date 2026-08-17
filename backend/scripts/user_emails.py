#!/usr/bin/env python
"""Export the user contact list for outreach.

Email addresses live in Supabase's `auth.users`, not in the application schema —
the app only stores an opaque `user_id`. This joins the two so the list carries
enough context to segment, rather than being a bare email dump:

    python scripts/user_emails.py                  # summary + CSV to stdout
    python scripts/user_emails.py --out users.csv  # write a file
    python scripts/user_emails.py --active-only    # signed in at least once

Read-only. Never writes.
"""
import argparse
import asyncio
import csv
import io
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import text  # noqa: E402

from core.database import get_db_session  # noqa: E402

QUERY = """
SELECT
    u.email,
    u.id::text                                   AS user_id,
    u.created_at                                 AS signed_up_at,
    u.last_sign_in_at,
    u.email_confirmed_at IS NOT NULL             AS email_confirmed,
    COALESCE(a.plan, 'free')                     AS plan,
    COALESCE(c.chat_count, 0)                    AS chats,
    COALESCE(w.symbol_count, 0)                  AS watchlist_symbols,
    (s.user_id IS NOT NULL AND s.is_connected)   AS brokerage_connected,
    (h.user_id IS NOT NULL)                      AS has_holdings
FROM auth.users u
LEFT JOIN user_accounts a ON a.user_id = u.id::text
LEFT JOIN (
    SELECT user_id, COUNT(*) AS chat_count FROM chats GROUP BY user_id
) c ON c.user_id = u.id::text
LEFT JOIN (
    SELECT user_id, COUNT(DISTINCT symbol) AS symbol_count
    FROM user_watchlist GROUP BY user_id
) w ON w.user_id = u.id::text
LEFT JOIN snaptrade_users s ON s.user_id = u.id::text
LEFT JOIN portfolio_holdings_cache h ON h.user_id = u.id::text
WHERE u.email IS NOT NULL
  AND u.deleted_at IS NULL
ORDER BY u.created_at DESC
"""

FIELDS = [
    "email", "user_id", "signed_up_at", "last_sign_in_at", "email_confirmed",
    "plan", "chats", "watchlist_symbols", "brokerage_connected", "has_holdings",
]


async def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--out", help="write CSV here instead of stdout")
    ap.add_argument("--active-only", action="store_true",
                    help="only users who have signed in at least once")
    args = ap.parse_args()

    async with get_db_session() as db:
        result = await db.execute(text(QUERY))
        rows = [dict(r._mapping) for r in result.fetchall()]

    if args.active_only:
        rows = [r for r in rows if r["last_sign_in_at"]]

    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=FIELDS)
    writer.writeheader()
    for r in rows:
        writer.writerow({k: ("" if r[k] is None else r[k]) for k in FIELDS})

    if args.out:
        Path(args.out).write_text(buf.getvalue())
    else:
        print(buf.getvalue())

    # Segments worth knowing before you write the email.
    signed_in = [r for r in rows if r["last_sign_in_at"]]
    chatted = [r for r in rows if r["chats"]]
    connected = [r for r in rows if r["brokerage_connected"]]
    watching = [r for r in rows if r["watchlist_symbols"]]

    print(f"total accounts        : {len(rows)}", file=sys.stderr)
    print(f"  signed in at least once: {len(signed_in)}", file=sys.stderr)
    print(f"  started a chat         : {len(chatted)}", file=sys.stderr)
    print(f"  added a watchlist symbol: {len(watching)}", file=sys.stderr)
    print(f"  connected a brokerage  : {len(connected)}", file=sys.stderr)
    print(f"  never signed in        : {len(rows) - len(signed_in)}", file=sys.stderr)
    if args.out:
        print(f"\nwrote {args.out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
