"""
CRUD operations for Robinhood sessions
"""
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime, timedelta
from models.db import RobinhoodSession


def create_session(
    db: Session,
    session_id: str,
    encrypted_access_token: str,
    encrypted_refresh_token: str,
    robinhood_username: Optional[str] = None,
    expires_in_seconds: int = 86400,
    device_token: Optional[str] = None
) -> RobinhoodSession:
    """
    Create a new Robinhood session with encrypted tokens
    
    Args:
        db: Database session
        session_id: User session identifier
        encrypted_access_token: Fernet-encrypted access token
        encrypted_refresh_token: Fernet-encrypted refresh token
        expires_in_seconds: Token expiry in seconds (default 24 hours)
        device_token: Optional device token for 2FA
    
    Returns:
        Created RobinhoodSession
    """
    token_expires_at = datetime.utcnow() + timedelta(seconds=expires_in_seconds)
    
    db_session = RobinhoodSession(
        session_id=session_id,
        robinhood_username=robinhood_username,
        encrypted_access_token=encrypted_access_token,
        encrypted_refresh_token=encrypted_refresh_token,
        token_expires_at=token_expires_at,
        device_token=device_token,
        logged_in=True
    )
    
    db.add(db_session)
    db.commit()
    db.refresh(db_session)
    return db_session


def get_session(db: Session, session_id: str) -> Optional[RobinhoodSession]:
    """Get a Robinhood session by session_id"""
    return db.query(RobinhoodSession).filter(
        RobinhoodSession.session_id == session_id
    ).first()


def update_session_activity(db: Session, session_id: str) -> bool:
    """Update last_activity timestamp for a session"""
    session = get_session(db, session_id)
    if session:
        session.last_activity = datetime.utcnow()
        db.commit()
        return True
    return False


def update_session_tokens(
    db: Session,
    session_id: str,
    encrypted_access_token: str,
    encrypted_refresh_token: str,
    expires_in_seconds: int = 86400
) -> bool:
    """Update tokens for an existing session (used after refresh)"""
    session = get_session(db, session_id)
    if session:
        session.encrypted_access_token = encrypted_access_token
        session.encrypted_refresh_token = encrypted_refresh_token
        session.token_expires_at = datetime.utcnow() + timedelta(seconds=expires_in_seconds)
        session.last_activity = datetime.utcnow()
        db.commit()
        return True
    return False


def logout_session(db: Session, session_id: str) -> bool:
    """Mark a session as logged out"""
    session = get_session(db, session_id)
    if session:
        session.logged_in = False
        db.commit()
        return True
    return False


def delete_session(db: Session, session_id: str) -> bool:
    """Permanently delete a session"""
    session = get_session(db, session_id)
    if session:
        db.delete(session)
        db.commit()
        return True
    return False


def is_session_expired(session: RobinhoodSession) -> bool:
    """Check if a session's tokens are expired"""
    return datetime.utcnow() > session.token_expires_at


def get_active_session_for_user(db: Session, robinhood_username: str) -> Optional[RobinhoodSession]:
    """
    Get an active (non-expired) session for a user
    
    Returns the most recent session if multiple exist
    """
    session = db.query(RobinhoodSession).filter(
        RobinhoodSession.robinhood_username == robinhood_username,
        RobinhoodSession.logged_in == True,
        RobinhoodSession.token_expires_at > datetime.utcnow()
    ).order_by(RobinhoodSession.last_activity.desc()).first()
    
    return session


def cleanup_old_sessions(db: Session, days: int = 30) -> int:
    """Delete sessions older than specified days"""
    cutoff_date = datetime.utcnow() - timedelta(days=days)
    deleted = db.query(RobinhoodSession).filter(
        RobinhoodSession.last_activity < cutoff_date
    ).delete()
    db.commit()
    return deleted

