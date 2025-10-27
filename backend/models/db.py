"""
SQLAlchemy database models
"""
from sqlalchemy import Column, String, DateTime, Text, Boolean
from sqlalchemy.sql import func
from database import Base


class RobinhoodSession(Base):
    """
    Stores encrypted Robinhood authentication tokens per user session
    
    SECURITY:
    - access_token and refresh_token are encrypted using Fernet (AES-128)
    - Never log or expose these fields
    - Tokens are decrypted only when making API calls
    """
    __tablename__ = "robinhood_sessions"
    
    # Primary key
    session_id = Column(String, primary_key=True, index=True)
    
    # User identifier (Robinhood username/email for session lookup)
    robinhood_username = Column(String, index=True, nullable=True)
    
    # Encrypted tokens (stored as base64-encoded ciphertext)
    encrypted_access_token = Column(Text, nullable=False)
    encrypted_refresh_token = Column(Text, nullable=False)
    
    # Token metadata
    token_expires_at = Column(DateTime(timezone=True), nullable=False)
    device_token = Column(String, nullable=True)  # For 2FA/MFA
    
    # Session tracking
    logged_in = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    last_activity = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    def __repr__(self):
        return f"<RobinhoodSession(session_id='{self.session_id}', logged_in={self.logged_in})>"

