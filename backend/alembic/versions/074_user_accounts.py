"""Introduce user_accounts; move account/billing/credits off snaptrade_users

Splits the per-user account record (credits, plan, Stripe fields) out of
snaptrade_users (which now holds broker-connection data only) into a new
public.user_accounts table keyed by the Supabase auth id. See
docs/migrations/074_user_accounts.md for the full rationale.

Revision ID: 074
Revises: 073
"""
from alembic import op
import sqlalchemy as sa

revision = "074"
down_revision = "073"
branch_labels = None
depends_on = None


# Columns that move from snaptrade_users -> user_accounts (drop order: reverse of add)
MOVED_COLUMNS = [
    "last_credit_refresh",
    "total_credits_used",
    "credits",
    "current_period_end",
    "cancel_at_period_end",
    "subscription_status",
    "stripe_subscription_id",
    "stripe_customer_id",
    "plan",
]


def upgrade() -> None:
    # 1. New per-user account/billing table.
    #    PK is the auth user id as text, matching every sibling table
    #    (user_settings, user_skills, ...). No cross-schema FK to auth.users —
    #    consistent with the existing schema and avoids any cascade reaching
    #    other tables (notably chats).
    op.create_table(
        "user_accounts",
        sa.Column("user_id", sa.String(), primary_key=True),
        sa.Column("plan", sa.String(), nullable=False, server_default="free"),
        sa.Column("stripe_customer_id", sa.String(), nullable=True),
        sa.Column("stripe_subscription_id", sa.String(), nullable=True),
        sa.Column("subscription_status", sa.String(), nullable=True),
        sa.Column("cancel_at_period_end", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("current_period_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("credits", sa.Integer(), nullable=False, server_default="1000"),
        sa.Column("total_credits_used", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_credit_refresh", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_user_accounts_stripe_customer_id", "user_accounts", ["stripe_customer_id"])
    op.create_index("ix_user_accounts_user_id", "user_accounts", ["user_id"])

    # 2a. Backfill from existing snaptrade_users rows (preserves current balances).
    op.execute(
        """
        INSERT INTO user_accounts (
            user_id, plan, stripe_customer_id, stripe_subscription_id,
            subscription_status, cancel_at_period_end, current_period_end,
            credits, total_credits_used, last_credit_refresh, created_at
        )
        SELECT
            user_id,
            COALESCE(plan, 'free'),
            stripe_customer_id,
            stripe_subscription_id,
            subscription_status,
            COALESCE(cancel_at_period_end, false),
            current_period_end,
            COALESCE(credits, 1000),
            COALESCE(total_credits_used, 0),
            COALESCE(last_credit_refresh, now()),
            COALESCE(created_at, now())
        FROM snaptrade_users
        ON CONFLICT (user_id) DO NOTHING
        """
    )

    # 2b. Backfill default rows for auth.users that never connected a broker.
    op.execute(
        """
        DO $$
        BEGIN
            IF to_regclass('auth.users') IS NOT NULL THEN
                INSERT INTO user_accounts (user_id, plan, credits, total_credits_used)
                SELECT u.id::text, 'free', 1000, 0
                FROM auth.users u
                ON CONFLICT (user_id) DO NOTHING;
            END IF;
        END $$;
        """
    )

    # 3. Auto-provision a user_accounts row on every new signup.
    #    NOTE: credits literal (1000) mirrors services.credits.DEFAULT_NEW_USER_CREDITS.
    op.execute(
        """
        CREATE OR REPLACE FUNCTION public.handle_new_user()
        RETURNS trigger
        LANGUAGE plpgsql
        SECURITY DEFINER
        SET search_path = public
        AS $$
        BEGIN
            INSERT INTO public.user_accounts (user_id, plan, credits, total_credits_used)
            VALUES (NEW.id::text, 'free', 1000, 0)
            ON CONFLICT (user_id) DO NOTHING;
            RETURN NEW;
        END;
        $$;
        """
    )
    # Trigger creation is best-effort: if the migration role lacks privilege on the
    # auth schema it is skipped, and the app-side _ensure_account() covers correctness.
    op.execute(
        """
        DO $$
        BEGIN
            IF to_regclass('auth.users') IS NOT NULL THEN
                BEGIN
                    DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
                    CREATE TRIGGER on_auth_user_created
                        AFTER INSERT ON auth.users
                        FOR EACH ROW EXECUTE FUNCTION public.handle_new_user();
                EXCEPTION WHEN insufficient_privilege THEN
                    RAISE NOTICE 'Skipped on_auth_user_created trigger (insufficient privilege); relying on app-side _ensure_account()';
                END;
            END IF;
        END $$;
        """
    )

    # 4. Drop the moved columns from snaptrade_users (broker-connection table only now).
    for col in MOVED_COLUMNS:
        op.drop_column("snaptrade_users", col)


def downgrade() -> None:
    # Re-add the columns to snaptrade_users.
    op.add_column("snaptrade_users", sa.Column("plan", sa.String(), nullable=False, server_default="free"))
    op.add_column("snaptrade_users", sa.Column("stripe_customer_id", sa.String(), nullable=True))
    op.add_column("snaptrade_users", sa.Column("stripe_subscription_id", sa.String(), nullable=True))
    op.add_column("snaptrade_users", sa.Column("subscription_status", sa.String(), nullable=True))
    op.add_column("snaptrade_users", sa.Column("cancel_at_period_end", sa.Boolean(), nullable=False, server_default="false"))
    op.add_column("snaptrade_users", sa.Column("current_period_end", sa.DateTime(timezone=True), nullable=True))
    op.add_column("snaptrade_users", sa.Column("credits", sa.Integer(), nullable=False, server_default="1000"))
    op.add_column("snaptrade_users", sa.Column("total_credits_used", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("snaptrade_users", sa.Column("last_credit_refresh", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")))

    # Best-effort restore of values from user_accounts.
    op.execute(
        """
        UPDATE snaptrade_users s
        SET credits = a.credits,
            total_credits_used = a.total_credits_used,
            plan = a.plan,
            stripe_customer_id = a.stripe_customer_id,
            stripe_subscription_id = a.stripe_subscription_id,
            subscription_status = a.subscription_status,
            cancel_at_period_end = a.cancel_at_period_end,
            current_period_end = a.current_period_end,
            last_credit_refresh = a.last_credit_refresh
        FROM user_accounts a
        WHERE a.user_id = s.user_id
        """
    )

    op.execute(
        """
        DO $$
        BEGIN
            IF to_regclass('auth.users') IS NOT NULL THEN
                DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
            END IF;
        END $$;
        """
    )
    op.execute("DROP FUNCTION IF EXISTS public.handle_new_user()")
    op.drop_index("ix_user_accounts_user_id", table_name="user_accounts")
    op.drop_index("ix_user_accounts_stripe_customer_id", table_name="user_accounts")
    op.drop_table("user_accounts")
