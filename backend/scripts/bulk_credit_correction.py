"""One-off: raise every user's balance up to a floor (never lower).

Compensation for the cache double-charge + refresh-clawback billing bugs.
For each user_accounts row with credits < FLOOR, add (FLOOR - credits) so the
balance becomes exactly FLOOR and a credit_transaction is logged. Accounts at or
above FLOOR are left completely untouched.

Usage:
    python3 scripts/bulk_credit_correction.py            # dry run (no writes)
    python3 scripts/bulk_credit_correction.py --apply    # perform the top-ups
"""
import sys, asyncio
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from core.database import get_db_session
from services.credits import CreditsService

FLOOR = 5000
APPLY = "--apply" in sys.argv
DESC = "Credit correction: topped up to 5000 after billing-bug fixes"


async def main():
    async with get_db_session() as db:
        rows = (await db.execute(
            text("select user_id, plan, credits from user_accounts order by credits asc")
        )).all()

        below = [r for r in rows if r[2] < FLOOR]
        total_add = sum(FLOOR - r[2] for r in below)

        print(f"accounts total: {len(rows)}")
        print(f"accounts below {FLOOR}: {len(below)}")
        print(f"credits to add (total): {total_add:,}")
        print("-" * 70)
        for r in below[:25]:
            print(f"  {r[0]}  plan={r[1]:<6} {r[2]:>7} -> {FLOOR} (+{FLOOR - r[2]})")
        if len(below) > 25:
            print(f"  ... and {len(below) - 25} more")
        print("-" * 70)

        if not APPLY:
            print("DRY RUN — no changes written. Re-run with --apply to perform top-ups.")
            return

        done = 0
        for r in below:
            await CreditsService.add_credits(
                db, r[0], FLOOR - r[2],
                transaction_type="admin_adjustment",
                description=DESC,
            )
            done += 1
        await db.commit()
        print(f"APPLIED: topped up {done} accounts, added {total_add:,} credits total.")


asyncio.run(main())
