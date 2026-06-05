"""
Authentication Dependencies for FastAPI Routes

Simple Supabase Auth JWT verification using JWKS.
No secrets needed - just your SUPABASE_URL from .env
"""
from fastapi import Header, HTTPException, status
from typing import Optional
import logging
import jwt
from jwt.algorithms import RSAAlgorithm, ECAlgorithm
import requests

from core.config import Config

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


async def _verify_bearer(authorization: Optional[str]) -> dict:
    """Verify a Supabase Bearer JWT (signature, audience, expiry) and return its
    decoded payload. Shared by get_current_user_id / get_current_user_email."""
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization header",
        )

    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization format. Use: Bearer <token>",
        )

    token = parts[1]

    try:
        header = jwt.get_unverified_header(token)
        kid = header.get("kid")
        if not kid:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token: missing key ID",
            )

        jwks = _get_jwks()
        signing_key = None
        key_algorithm = None
        for key in jwks.get("keys", []):
            if key.get("kid") == kid:
                kty = key.get("kty")
                if kty == "RSA":
                    signing_key = RSAAlgorithm.from_jwk(key)
                    key_algorithm = "RS256"
                elif kty == "EC":
                    signing_key = ECAlgorithm.from_jwk(key)
                    key_algorithm = "ES256"
                else:
                    logger.warning(f"Unsupported key type: {kty}")
                    continue
                break

        if not signing_key:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token: unknown key",
            )

        algorithms = [key_algorithm] if key_algorithm else ["RS256", "ES256"]
        payload = jwt.decode(
            token,
            signing_key,
            algorithms=algorithms,
            audience="authenticated",
            options={"verify_exp": True},
        )
        return payload

    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired",
        )
    except requests.RequestException as e:
        logger.error(f"Failed to fetch JWKS: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service unavailable",
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.warning(f"Token verification failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )


async def get_current_user_id(
    authorization: Optional[str] = Header(None, description="Bearer token from Supabase Auth")
) -> str:
    """Verify the Supabase JWT and return the user ID (the `sub` claim)."""
    payload = await _verify_bearer(authorization)
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token: missing user ID",
        )
    return user_id


async def get_current_user_email(
    authorization: Optional[str] = Header(None, description="Bearer token from Supabase Auth")
) -> Optional[str]:
    """Verify the Supabase JWT and return the user's email (`email` claim), or None
    if the token carries no email."""
    payload = await _verify_bearer(authorization)
    return payload.get("email")


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
