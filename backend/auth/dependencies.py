"""
Authentication Dependencies for FastAPI Routes

Simple Supabase Auth JWT verification using JWKS.
No secrets needed - just your SUPABASE_URL from .env
"""
from fastapi import Header, HTTPException, status
from typing import Optional
import logging
import jwt
from jwt.algorithms import RSAAlgorithm
import requests

from config import Config

logger = logging.getLogger(__name__)

# Cache for JWKS keys (refreshed every hour)
_jwks_cache = None


def _get_jwks():
    """Fetch public JWKS keys from Supabase"""
    global _jwks_cache
    
    if _jwks_cache is not None:
        return _jwks_cache
    
    jwks_url = f"{Config.SUPABASE_URL}/auth/v1/.well-known/jwks.json"
    response = requests.get(jwks_url, timeout=5)
    response.raise_for_status()
    _jwks_cache = response.json()
    return _jwks_cache


async def get_current_user_id(
    authorization: Optional[str] = Header(None, description="Bearer token from Supabase Auth")
) -> str:
    """
    Verify Supabase JWT token and extract user ID.
    
    The frontend sends: Authorization: Bearer <supabase_jwt_token>
    This function verifies the token and returns the user_id.
    
    Args:
        authorization: Authorization header with Bearer token
        
    Returns:
        Validated user ID string
        
    Raises:
        HTTPException: If token is missing, invalid, or expired
    """
    # Check authorization header exists
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization header"
        )
    
    # Extract token from "Bearer <token>"
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization format. Use: Bearer <token>"
        )
    
    token = parts[1]
    
    try:
        # Get key ID from token header
        header = jwt.get_unverified_header(token)
        kid = header.get("kid")
        
        if not kid:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token: missing key ID"
            )
        
        # Fetch JWKS and find matching key
        jwks = _get_jwks()
        signing_key = None
        
        for key in jwks.get("keys", []):
            if key.get("kid") == kid:
                signing_key = RSAAlgorithm.from_jwk(key)
                break
        
        if not signing_key:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token: unknown key"
            )
        
        # Verify and decode token
        payload = jwt.decode(
            token,
            signing_key,
            algorithms=["RS256", "ES256"],
            audience="authenticated",
            options={"verify_exp": True}
        )
        
        # Extract user ID
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token: missing user ID"
            )
        
        return user_id
        
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired"
        )
    except requests.RequestException as e:
        logger.error(f"Failed to fetch JWKS: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service unavailable"
        )
    except Exception as e:
        logger.warning(f"Token verification failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )


async def verify_user_access(
    user_id: str,
    authenticated_user_id: str
) -> None:
    """
    Verify that the authenticated user has permission to access the requested user's resources.
    
    Args:
        user_id: The user ID being accessed (from URL path)
        authenticated_user_id: The authenticated user's ID (from auth)
        
    Raises:
        HTTPException: If user tries to access another user's resources
    """
    if user_id != authenticated_user_id:
        logger.warning(
            f"Authorization failure: User {authenticated_user_id} attempted to access "
            f"resources for user {user_id}"
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to access this user's resources."
        )
