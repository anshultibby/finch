"""Authoritative map of where a user's data lives, and the operations over it.

Three compliance obligations reduce to one question — *which rows belong to this
user* — so they share one map rather than three drifting implementations:

- **Retention** (`apply_retention`): delete rows older than their documented life.
- **Deletion / export** (`purge_user`, `export_user`): answer "return or destroy
  our firm's data on termination".
- **Tenant attribution** (`summarize_user`): answer "whose data was affected"
  during an incident, while the notification clock is running.

The map is written out by hand rather than reflected, because a compliance
artifact should be reviewable. `audit_coverage()` is what keeps it honest: it
fails if any table in the schema is neither registered nor explicitly excluded,
so adding a table without classifying it breaks the test instead of silently
creating an unmapped pocket of user data.

Retention periods below are defaults chosen to be defensible, not legal advice.
They are the documented schedule referenced by `docs/compliance/data-inventory.md`
— change the numbers there and here together.
"""
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import text

from core.database import get_db_session

logger = logging.getLogger(__name__)

# Financial records are kept long by convention; user content follows the
# account; operational noise expires quickly.
RETENTION_BILLING_DAYS = 2555        # ~7 years — financial/billing records
RETENTION_ACTIVITY_DAYS = 400        # activity ledger / analytics
RETENTION_NOTIFICATION_DAYS = 90     # transient user-facing noise
RETENTION_JOB_DAYS = 180             # job bookkeeping


@dataclass(frozen=True)
class UserTable:
    table: str
    category: str
    # Direct ownership: this column holds the user id.
    user_column: Optional[str] = None
    # Indirect ownership: (local_col, parent_table, parent_col) — used where a
    # row belongs to a user only through its parent.
    via: Optional[tuple] = None
    # Column used to age rows out. None means the rows live as long as the
    # account and are removed only by deletion.
    timestamp_column: Optional[str] = None
    retention_days: Optional[int] = None

    def where_clause(self) -> str:
        if self.user_column:
            return f"{self.user_column} = :uid"
        local, parent, pcol = self.via
        return f"{local} IN (SELECT {pcol} FROM {parent} WHERE user_id = :uid)"


USER_TABLES: List[UserTable] = [
    # --- Financial position data -------------------------------------------
    UserTable("portfolio_holdings_cache", "financial", user_column="user_id"),
    UserTable("portfolio_intraday_cache", "financial", user_column="user_id"),
    UserTable("portfolio_snapshots", "financial", user_column="user_id"),
    UserTable("transactions", "financial", user_column="user_id"),
    UserTable("transaction_sync_jobs", "financial", user_column="user_id",
              timestamp_column="created_at", retention_days=RETENTION_JOB_DAYS),
    UserTable("trade_analytics", "financial", user_column="user_id"),
    UserTable("trade_ideas", "financial", user_column="user_id",
              timestamp_column="created_at", retention_days=RETENTION_ACTIVITY_DAYS),
    UserTable("pending_trades", "financial", user_column="user_id",
              timestamp_column="created_at", retention_days=RETENTION_ACTIVITY_DAYS),
    UserTable("brokerage_accounts", "financial", user_column="user_id"),
    UserTable("user_watchlist", "financial", user_column="user_id"),
    UserTable("watchlist_list", "financial", user_column="user_id"),

    # --- Credentials --------------------------------------------------------
    UserTable("snaptrade_users", "credential", user_column="user_id"),
    UserTable("robinhood_connections", "credential", user_column="user_id"),
    UserTable("casparser_connections", "credential", user_column="user_id"),
    UserTable("user_auth_tokens", "credential", user_column="user_id"),

    # --- User-generated content --------------------------------------------
    UserTable("chats", "content", user_column="user_id"),
    # Owned through its chat — the only indirectly-owned table in the schema.
    UserTable("chat_messages", "content",
              via=("chat_id", "chats", "chat_id"), timestamp_column="timestamp"),
    UserTable("chat_files", "content", user_column="user_id"),
    UserTable("store_files", "content", user_column="user_id"),
    UserTable("resources", "content", user_column="user_id"),
    UserTable("widgets", "content", user_column="user_id"),
    UserTable("visualizations", "content", user_column="user_id"),
    UserTable("stock_analysis", "content", user_column="user_id"),
    UserTable("agent_tasks", "content", user_column="user_id"),
    UserTable("dreams", "content", user_column="user_id"),
    UserTable("message_feedback", "content", user_column="user_id",
              timestamp_column="created_at", retention_days=RETENTION_ACTIVITY_DAYS),

    # --- Activity and operations -------------------------------------------
    UserTable("agent_events", "activity", user_column="user_id",
              timestamp_column="created_at", retention_days=RETENTION_ACTIVITY_DAYS),
    UserTable("agent_activity_seen", "activity", user_column="user_id"),
    UserTable("user_activity", "activity", user_column="user_id"),
    UserTable("scheduled_jobs", "activity", user_column="user_id",
              timestamp_column="created_at", retention_days=RETENTION_JOB_DAYS),
    UserTable("notifications", "activity", user_column="user_id",
              timestamp_column="created_at", retention_days=RETENTION_NOTIFICATION_DAYS),
    UserTable("device_tokens", "activity", user_column="user_id"),
    UserTable("user_sandboxes", "activity", user_column="user_id"),

    # --- Account, billing, settings ----------------------------------------
    UserTable("user_accounts", "account", user_column="user_id"),
    UserTable("user_settings", "account", user_column="user_id"),
    UserTable("user_skills", "account", user_column="user_id"),
    UserTable("credit_transactions", "billing", user_column="user_id",
              timestamp_column="created_at", retention_days=RETENTION_BILLING_DAYS),
    UserTable("promo_redemptions", "billing", user_column="user_id",
              timestamp_column="created_at", retention_days=RETENTION_BILLING_DAYS),
]

# Tables that intentionally hold no user data. Listed explicitly so the
# coverage audit can tell "no user data" apart from "nobody looked".
EXCLUDED_TABLES: Dict[str, str] = {
    "promo_codes": "Global promo definitions; redemptions are tracked per user separately.",
    "alembic_version": "Schema bookkeeping.",
}

# Deleted last: other rows are located through these, and a partial failure
# should leave the account findable rather than orphaning its data.
_DELETE_LAST = {"chats", "user_accounts"}


def audit_coverage() -> List[str]:
    """Tables present in the schema but neither registered nor excluded.

    A non-empty result means user data may exist somewhere this module cannot
    see — which would silently break retention, deletion, and attribution.
    """
    import importlib
    import pkgutil

    import models

    for m in pkgutil.iter_modules(models.__path__):
        try:
            importlib.import_module(f"models.{m.name}")
        except Exception:
            logger.warning("coverage audit: could not import models.%s", m.name)

    from core.database import Base

    known = {t.table for t in USER_TABLES} | set(EXCLUDED_TABLES)
    return sorted(set(Base.metadata.tables) - known)


def _ordered_for_delete() -> List[UserTable]:
    return sorted(USER_TABLES, key=lambda t: t.table in _DELETE_LAST)


async def summarize_user(user_id: str) -> Dict[str, int]:
    """Row counts per table for one user — the tenant-attribution answer.

    Tables with no rows are omitted. Run this during an incident to scope which
    data categories are implicated.
    """
    out: Dict[str, int] = {}
    async with get_db_session() as db:
        for spec in USER_TABLES:
            try:
                result = await db.execute(
                    text(f"SELECT COUNT(*) FROM {spec.table} WHERE {spec.where_clause()}"),
                    {"uid": user_id},
                )
                count = result.scalar() or 0
            except Exception:
                logger.exception("attribution: count failed for %s", spec.table)
                out[spec.table] = -1  # surfaced, not silently dropped
                continue
            if count:
                out[spec.table] = count
    return out


async def export_user(user_id: str) -> Dict[str, Any]:
    """Every row belonging to `user_id`, keyed by table.

    Credential columns come back decrypted (the ORM would too), so treat the
    output as sensitive: deliver it over a channel the customer nominated, and
    do not leave it on disk.
    """
    export: Dict[str, Any] = {
        "user_id": user_id,
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "tables": {},
    }
    async with get_db_session() as db:
        for spec in USER_TABLES:
            try:
                result = await db.execute(
                    text(f"SELECT * FROM {spec.table} WHERE {spec.where_clause()}"),
                    {"uid": user_id},
                )
                rows = [dict(r._mapping) for r in result.fetchall()]
            except Exception:
                logger.exception("export: failed for %s", spec.table)
                export["tables"][spec.table] = {"error": "export failed"}
                continue
            if rows:
                export["tables"][spec.table] = rows
    return export


async def purge_user(user_id: str, dry_run: bool = True) -> Dict[str, int]:
    """Delete every row belonging to `user_id`.

    Defaults to a dry run: nothing is destructive unless `dry_run=False` is
    passed explicitly. Returns per-table counts (deleted, or would-be-deleted).

    Out of scope, and still required to finish an erasure request:
    Supabase Auth identity, Supabase Storage objects, and any data already
    handed to a subprocessor (see docs/compliance/subprocessors.md).
    """
    counts: Dict[str, int] = {}
    async with get_db_session() as db:
        for spec in _ordered_for_delete():
            where = spec.where_clause()
            try:
                if dry_run:
                    result = await db.execute(
                        text(f"SELECT COUNT(*) FROM {spec.table} WHERE {where}"),
                        {"uid": user_id},
                    )
                    n = result.scalar() or 0
                else:
                    result = await db.execute(
                        text(f"DELETE FROM {spec.table} WHERE {where}"), {"uid": user_id}
                    )
                    n = result.rowcount or 0
            except Exception:
                logger.exception("purge: failed for %s", spec.table)
                counts[spec.table] = -1
                continue
            if n:
                counts[spec.table] = n
        if not dry_run:
            await db.commit()
    return counts


async def apply_retention(dry_run: bool = True) -> Dict[str, int]:
    """Delete rows past their documented retention period, across all users.

    Only tables carrying both a `retention_days` and a `timestamp_column` are
    touched; everything else lives for the life of the account and is removed
    by `purge_user`.
    """
    counts: Dict[str, int] = {}
    now = datetime.now(timezone.utc)
    async with get_db_session() as db:
        for spec in USER_TABLES:
            if not (spec.retention_days and spec.timestamp_column):
                continue
            cutoff = now - timedelta(days=spec.retention_days)
            clause = f"{spec.timestamp_column} < :cutoff"
            try:
                if dry_run:
                    result = await db.execute(
                        text(f"SELECT COUNT(*) FROM {spec.table} WHERE {clause}"),
                        {"cutoff": cutoff},
                    )
                    n = result.scalar() or 0
                else:
                    result = await db.execute(
                        text(f"DELETE FROM {spec.table} WHERE {clause}"), {"cutoff": cutoff}
                    )
                    n = result.rowcount or 0
            except Exception:
                logger.exception("retention: failed for %s", spec.table)
                counts[spec.table] = -1
                continue
            if n:
                counts[spec.table] = n
        if not dry_run:
            await db.commit()
    return counts
