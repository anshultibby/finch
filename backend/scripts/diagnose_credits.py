"""One-off: diagnose credit accounting for a user by email.

Usage:
    python3 scripts/diagnose_credits.py [email]            # diagnose only (read)
    python3 scripts/diagnose_credits.py [email] --grant N  # diagnose + add N credits
"""
import sys, asyncio, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from core.database import get_db_session
from services.credits import calculate_credits_for_llm_call, calculate_cost_usd, CreditsService

EMAIL = sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith("--") else "anshul.tibrewal2203@gmail.com"
GRANT = 0
if "--grant" in sys.argv:
    GRANT = int(sys.argv[sys.argv.index("--grant") + 1])
PLAN = None
if "--plan" in sys.argv:
    PLAN = sys.argv[sys.argv.index("--plan") + 1]


async def main():
    async with get_db_session() as db:
        # look up user_id from auth.users
        row = (await db.execute(
            text("select id, email from auth.users where email = :e"), {"e": EMAIL}
        )).first()
        if not row:
            print(f"No auth user for {EMAIL}")
            return
        user_id = str(row[0])
        print(f"user_id = {user_id}  ({row[1]})")

        acct = (await db.execute(
            text("select plan, credits, total_credits_used, last_credit_refresh, created_at "
                 "from user_accounts where user_id = :u"), {"u": user_id}
        )).first()
        print(f"account: plan={acct[0]} credits={acct[1]} total_used={acct[2]} "
              f"last_refresh={acct[3]} created={acct[4]}")
        print("=" * 120)

        txns = (await db.execute(text(
            "select created_at, transaction_type, amount, balance_after, description, transaction_metadata "
            "from credit_transactions where user_id = :u order by created_at desc limit :n"
        ), {"u": user_id, "n": 40})).all()

        print(f"{'when':<20}{'type':<16}{'amt':>6}{'bal':>8}  {'model':<20}{'in':>9}{'cR':>9}{'cW':>9}{'out':>8}{'recalc':>8}")
        print("-" * 120)
        for t in txns:
            when = str(t[0])[:19]
            md = t[5] or {}
            if isinstance(md, str):
                try: md = json.loads(md)
                except Exception: md = {}
            model = (md.get("model") or "")[:19]
            pin = md.get("prompt_tokens")
            cr = md.get("cache_read_tokens")
            cw = md.get("cache_creation_tokens")
            out = md.get("completion_tokens")
            recalc = ""
            if pin is not None:
                recalc = str(calculate_credits_for_llm_call(
                    md.get("model", ""), pin, out or 0, cr or 0, cw or 0))
            def f(x): return f"{x:,}" if isinstance(x, int) else "-"
            print(f"{when:<20}{t[1]:<16}{t[2]:>6}{t[3]:>8}  {model:<20}"
                  f"{f(pin):>9}{f(cr):>9}{f(cw):>9}{f(out):>8}{recalc:>8}")

        if PLAN:
            print("=" * 120)
            await CreditsService.set_user_plan(db, user_id, PLAN)
            print(f"set plan -> {PLAN}")

        if GRANT > 0:
            print("=" * 120)
            ok = await CreditsService.add_credits(
                db, user_id, GRANT,
                transaction_type="admin_adjustment",
                description="Manual top-up (owner) after cache double-charge fix",
            )

        if PLAN or GRANT > 0:
            await db.commit()
            row = (await db.execute(
                text("select plan, credits from user_accounts where user_id = :u"), {"u": user_id}
            )).first()
            print(f"committed -> plan={row[0]}, balance={row[1]}")


asyncio.run(main())
