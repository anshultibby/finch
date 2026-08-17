"""Encrypt credential columns at rest

`snaptrade_users.snaptrade_user_secret` and `user_auth_tokens.refresh_token`
were stored as plaintext while other credential material (user API keys,
Robinhood tokens) was already encrypted with Fernet. Both are credential
material and both are now `EncryptedText` columns (see models/encrypted.py).

This backfills existing rows. It is safe to run against a live database:
`EncryptedText.process_result_value` falls back to returning the raw value
when it isn't valid ciphertext, so rows read fine before, during, and after.
Each row is checked individually, so a partial run or a re-run is a no-op on
anything already converted.

Deploy order: ship the application code first (reads tolerate both forms),
then run this migration.

Revision ID: 093
Revises: 092
Create Date: 2026-08-07
"""
import logging

from alembic import op
import sqlalchemy as sa

revision = '093'
down_revision = '092'
branch_labels = None
depends_on = None

logger = logging.getLogger("alembic.093")

# (table, primary key column, credential column)
_TARGETS = [
    ("snaptrade_users", "user_id", "snaptrade_user_secret"),
    ("user_auth_tokens", "user_id", "refresh_token"),
]


def _service():
    from services.encryption import encryption_service

    return encryption_service


def _looks_encrypted(svc, value: str) -> bool:
    try:
        svc.decrypt(value)
        return True
    except Exception:
        return False


def _convert(direction: str) -> None:
    """direction: 'encrypt' plaintext rows, or 'decrypt' ciphertext rows."""
    svc = _service()
    conn = op.get_bind()

    for table, pk, col in _TARGETS:
        rows = conn.execute(
            sa.text(f"SELECT {pk}, {col} FROM {table} WHERE {col} IS NOT NULL AND {col} <> ''")
        ).fetchall()

        converted = skipped = failed = 0
        for key, value in rows:
            already = _looks_encrypted(svc, value)
            # Encrypting: skip rows already ciphertext. Decrypting: skip plaintext.
            if (direction == "encrypt") == already:
                skipped += 1
                continue
            try:
                new_value = (
                    svc.encrypt(value) if direction == "encrypt" else svc.decrypt(value)
                )
            except Exception:
                # Never drop a credential over a conversion error — leave the row
                # as-is. The column type tolerates both forms, so it stays usable.
                logger.exception("093: could not %s %s.%s for %s", direction, table, col, key)
                failed += 1
                continue
            conn.execute(
                sa.text(f"UPDATE {table} SET {col} = :v WHERE {pk} = :k"),
                {"v": new_value, "k": key},
            )
            converted += 1

        logger.info(
            "093 %s %s.%s: %d converted, %d already done, %d failed",
            direction, table, col, converted, skipped, failed,
        )


def upgrade():
    _convert("encrypt")


def downgrade():
    # Reverts storage to plaintext so the column type can be rolled back with
    # the application code.
    _convert("decrypt")
