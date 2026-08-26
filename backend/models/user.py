"""
User-related ORM models: SnapTradeUser, UserSettings, UserSandbox, CreditTransaction
"""
from sqlalchemy import Column, String, DateTime, Date, Text, Boolean, Integer, Float, JSON
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.sql import func
from core.database import Base
from models.encrypted import EncryptedText
import uuid


class UserAccount(Base):
    """
    Per-user account record: credits/billing/plan, keyed by the Supabase auth
    user id (auth.users.id, stored as text to match every sibling table).

    Provisioned on signup by the `on_auth_user_created` trigger on auth.users,
    and lazily by CreditsService._ensure_account() on any credit write.
    Identity lives in Supabase's auth.users; this is the app-side account row.
    """
    __tablename__ = "user_accounts"

    user_id = Column(String, primary_key=True, index=True)
    plan = Column(String, nullable=False, default="free")  # free | pro | admin
    # Which billing system currently owns the Pro grant: "stripe" (web checkout)
    # or "apple" (iOS In-App Purchase via RevenueCat). NULL while on free. Used so
    # each platform only offers/manages the subscription it owns and we never
    # double-charge a user across web + iOS.
    subscription_provider = Column(String, nullable=True)  # stripe | apple
    stripe_customer_id = Column(String, nullable=True, index=True)
    stripe_subscription_id = Column(String, nullable=True)
    subscription_status = Column(String, nullable=True)
    cancel_at_period_end = Column(Boolean, default=False, nullable=False)
    current_period_end = Column(DateTime(timezone=True), nullable=True)
    credits = Column(Integer, nullable=False, default=1_000)
    total_credits_used = Column(Integer, nullable=False, default=0)
    last_credit_refresh = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    def __repr__(self):
        return f"<UserAccount(user_id='{self.user_id}', plan='{self.plan}', credits={self.credits})>"


class UserGoal(Base):
    """
    The user's active goal / "mission" — one row per user (keyed by the Supabase
    auth user id), written by the onboarding wizard, read by the goal-oriented
    home cockpit, and injected into the agent's system prompt so everything it
    surfaces is shaped around what the user is actually trying to do.

    `kind` selects the goal shape:
      number  — a dollar target by a deadline   (target_amount + deadline)
      grow    — long-term compounding           (horizon_years + monthly_contribution)
      income  — recurring monthly income        (monthly_income)
      protect — watch-only, no numeric target   (config.watch / config.notify)

    Shape-specific extras (tradeable assets, watch list, notify channel, …) live
    in `config` (JSONB) so new goal types don't churn the schema.
    """
    __tablename__ = "user_goals"

    user_id = Column(String, primary_key=True, index=True)
    kind = Column(String, nullable=False, default="number")   # number | grow | income | protect
    title = Column(String, nullable=False, default="")        # human label for the cockpit
    objective = Column(Text, nullable=True)                    # the raw thing the user typed
    target_amount = Column(Float, nullable=True)               # number goals
    deadline = Column(Date, nullable=True)                     # number goals
    horizon_years = Column(Integer, nullable=True)             # grow goals
    monthly_contribution = Column(Float, nullable=True)        # grow goals
    monthly_income = Column(Float, nullable=True)              # income goals
    risk = Column(Integer, nullable=True)                      # 1..10 (null for protect)
    options_enabled = Column(Boolean, nullable=False, default=False)
    config = Column(JSONB, nullable=False, default=dict)       # assets, watch prefs, notify, …
    status = Column(String, nullable=False, default="active")  # active | paused | done | archived
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    def __repr__(self):
        return f"<UserGoal(user_id='{self.user_id}', kind='{self.kind}', title='{self.title}')>"


class SnapTradeUser(Base):
    """
    Stores SnapTrade broker connections per user. Account/billing/credits now
    live on UserAccount (migration 074).
    """
    __tablename__ = "snaptrade_users"

    user_id = Column(String, primary_key=True, index=True)
    snaptrade_user_id = Column(String, unique=True, nullable=False, index=True)
    # Encrypted at rest — see models/encrypted.py. Reads/writes are transparent.
    snaptrade_user_secret = Column(EncryptedText, nullable=False)
    connected_account_ids = Column(Text, nullable=True)
    is_connected = Column(Boolean, default=False, nullable=False)
    brokerage_name = Column(String, nullable=True)
    # Stale-connection soft purge (migration 075). purged_at set => de-registered
    # from SnapTrade to stop billing; user must reverify. Cached headline kept for UI.
    purged_at = Column(DateTime(timezone=True), nullable=True)
    last_portfolio_value = Column(Float, nullable=True)
    last_synced_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    last_activity = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    def __repr__(self):
        return f"<SnapTradeUser(user_id='{self.user_id}', snaptrade_user_id='{self.snaptrade_user_id}', is_connected={self.is_connected}, purged={self.purged_at is not None})>"


class UserSettings(Base):
    """
    Stores user settings with encrypted API credentials
    """
    __tablename__ = "user_settings"

    user_id = Column(String, primary_key=True, index=True)
    encrypted_api_keys = Column(Text, nullable=True)
    settings = Column(JSONB, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    def __repr__(self):
        return f"<UserSettings(user_id='{self.user_id}')>"


class UserSandbox(Base):
    """
    Stores a user's persistent E2B sandbox ID so the sandbox can be resumed
    across server restarts.
    """
    __tablename__ = "user_sandboxes"

    user_id = Column(String, primary_key=True, index=True)
    sandbox_id = Column(String, nullable=False)
    skills_loaded = Column(Boolean, nullable=False, default=False)
    skills_hash = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    def __repr__(self):
        return f"<UserSandbox(user_id='{self.user_id}', sandbox_id='{self.sandbox_id}', skills_loaded={self.skills_loaded})>"


class CreditTransaction(Base):
    """
    Audit log of credit usage
    """
    __tablename__ = "credit_transactions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(String, nullable=False, index=True)
    amount = Column(Integer, nullable=False)
    balance_after = Column(Integer, nullable=False)
    transaction_type = Column(String, nullable=False)
    description = Column(String, nullable=False)
    chat_id = Column(String, nullable=True, index=True)
    tool_name = Column(String, nullable=True)
    transaction_metadata = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)

    def __repr__(self):
        return f"<CreditTransaction(id='{self.id}', user='{self.user_id}', amount={self.amount}, type='{self.transaction_type}')>"


class UserSkill(Base):
    """
    Tracks which skills a user has enabled.
    """
    __tablename__ = "user_skills"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, nullable=False, index=True)
    skill_name = Column(String, nullable=False)
    enabled = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    def __repr__(self):
        return f"<UserSkill(user_id='{self.user_id}', skill_name='{self.skill_name}', enabled={self.enabled})>"


class PromoCode(Base):
    __tablename__ = "promo_codes"

    code = Column(String, primary_key=True)
    plan = Column(String, nullable=False, default="pro")
    credits = Column(Integer, nullable=False, default=3000)
    duration_days = Column(Integer, nullable=False, default=90)
    max_uses = Column(Integer, nullable=True)
    times_used = Column(Integer, nullable=False, default=0)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class PromoRedemption(Base):
    __tablename__ = "promo_redemptions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(String, nullable=False, index=True)
    code = Column(String, nullable=False)
    plan_granted = Column(String, nullable=False)
    credits_granted = Column(Integer, nullable=False)
    plan_expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class DeviceToken(Base):
    __tablename__ = "device_tokens"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(String, nullable=False, index=True)
    token = Column(String, nullable=False, unique=True)
    platform = Column(String, nullable=False)  # 'ios' | 'android' | 'web'
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(String, nullable=False, index=True)
    title = Column(String, nullable=False)
    body = Column(Text, nullable=False)
    type = Column(String, nullable=False, default="general")  # general | chat | trade | system
    data = Column(JSON, nullable=True)
    read = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class UserAuthToken(Base):
    """Backend-owned Supabase refresh token so scheduled jobs can run as the
    user. Minted via the admin API (services/job_auth) — its own token family,
    never a client's. Storing a browser/mobile refresh token here logs that
    device out: spending it rotates the shared family, and Supabase's reuse
    detection revokes the family on the device's next silent refresh.

    It's a credential — server-side only.
    """
    __tablename__ = "user_auth_tokens"

    user_id = Column(String, primary_key=True, index=True)
    # Encrypted at rest — see models/encrypted.py.
    refresh_token = Column(EncryptedText, nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class RobinhoodConnection(Base):
    """Per-user OAuth connection to Robinhood's agentic-trading MCP server.

    Uses the standard MCP authorization flow (OAuth 2.1 + PKCE + RFC 7591
    dynamic client registration). Each user self-registers a public client (no
    secret), authorizes via Robinhood's login/consent/funding flow, and we store
    the resulting tokens. Access + refresh tokens are Fernet-encrypted at rest —
    server-side only, never returned to the frontend.

    The in-flight CSRF state + PKCE verifier are carried in a signed (Fernet-
    encrypted) `state` parameter rather than stored here, so a row is only
    created once the user has actually connected.
    """
    __tablename__ = "robinhood_connections"

    user_id = Column(String, primary_key=True, index=True)
    client_id = Column(String, nullable=True)  # DCR-registered public client
    encrypted_access_token = Column(Text, nullable=True)
    encrypted_refresh_token = Column(Text, nullable=True)
    token_expires_at = Column(DateTime(timezone=True), nullable=True)
    is_connected = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
