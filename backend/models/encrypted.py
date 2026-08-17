"""Transparently-encrypted column type for credential material.

Credential columns are read all over the codebase via plain ORM attribute
access (`user.snaptrade_user_secret`, `row.refresh_token`, tools, scripts,
tests). Encrypting at the *call sites* would mean finding and changing every
one of them, and any path that was missed would silently read ciphertext and
fail at the brokerage instead of at the boundary.

Doing it at the column type instead means storage changes and every existing
read/write keeps working untouched.

Reads are backward compatible on purpose: a value that isn't valid ciphertext
is assumed to be a legacy plaintext row and returned as-is. That makes the
backfill (migration 093) safe to run while the app is serving traffic — a
half-migrated table works either way — and it means deploying this code before
running the migration cannot break existing connections.
"""
from sqlalchemy import Text
from sqlalchemy.types import TypeDecorator


class EncryptedText(TypeDecorator):
    """Text column encrypted at rest with Fernet (AES-128-CBC + HMAC).

    Keyed by `ENCRYPTION_KEY` via `services.encryption.encryption_service`.
    Losing that key means losing every value stored in these columns.
    """

    impl = Text
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if not value:
            # None stays None; "" would make encrypt() raise and is never a
            # meaningful credential anyway.
            return value
        from services.encryption import encryption_service

        return encryption_service.encrypt(value)

    def process_result_value(self, value, dialect):
        if not value:
            return value
        from services.encryption import encryption_service

        try:
            return encryption_service.decrypt(value)
        except Exception:
            # Written before this column was encrypted. Returning it as-is
            # keeps pre-backfill rows usable; migration 093 converts them.
            return value
