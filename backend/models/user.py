"""
User-related ORM models: SnapTradeUser, UserSettings, UserSandbox, CreditTransaction
"""
from sqlalchemy import Column, String, DateTime, Date, Text, Boolean, Integer, Float, JSON
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.sql import func
from core.database import Base
import uuid


class SnapTradeUser(Base):
    """
    Stores SnapTrade user connections per user
    """
    __tablename__ = "snaptrade_users"

    user_id = Column(String, primary_key=True, index=True)
    snaptrade_user_id = Column(String, unique=True, nullable=False, index=True)
    snaptrade_user_secret = Column(Text, nullable=False)
    connected_account_ids = Column(Text, nullable=True)
    is_connected = Column(Boolean, default=False, nullable=False)
    brokerage_name = Column(String, nullable=True)
    plan = Column(String, nullable=False, default="free")  # free | pro | admin
    stripe_customer_id = Column(String, nullable=True)
    stripe_subscription_id = Column(String, nullable=True)
    subscription_status = Column(String, nullable=True)
    cancel_at_period_end = Column(Boolean, default=False, nullable=False)
    current_period_end = Column(DateTime(timezone=True), nullable=True)
    credits = Column(Integer, nullable=False, default=1_000)
    total_credits_used = Column(Integer, nullable=False, default=0)
    last_credit_refresh = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    last_activity = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    def __repr__(self):
        return f"<SnapTradeUser(user_id='{self.user_id}', snaptrade_user_id='{self.snaptrade_user_id}', is_connected={self.is_connected}, credits={self.credits})>"


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


class AlpacaWaitlist(Base):
    __tablename__ = "alpaca_waitlist"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String, nullable=False, unique=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class TLHReminder(Base):
    __tablename__ = "tlh_reminders"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(String, nullable=False, index=True)
    email = Column(String, nullable=False)
    symbol_sold = Column(String, nullable=False)
    symbol_bought = Column(String, nullable=True)
    loss_amount = Column(Float, nullable=True)
    sale_date = Column(Date, nullable=False)
    remind_at = Column(DateTime(timezone=True), nullable=False)  # sale_date + 61 days
    sent = Column(Boolean, default=False, nullable=False)
    sent_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self):
        return f"<TLHReminder(id='{self.id}', user_id='{self.user_id}', symbol_sold='{self.symbol_sold}', sent={self.sent})>"


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
