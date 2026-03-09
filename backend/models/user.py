"""
User-related ORM models: SnapTradeUser, UserSettings, UserSandbox, CreditTransaction
"""
from sqlalchemy import Column, String, DateTime, Text, Boolean, Integer
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
    credits = Column(Integer, nullable=False, default=500)
    total_credits_used = Column(Integer, nullable=False, default=0)
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
