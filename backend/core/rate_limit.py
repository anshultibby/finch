from fastapi import Request
from slowapi import Limiter
from slowapi.util import get_remote_address


def _get_user_or_ip(request: Request) -> str:
    """Rate limit by authenticated user ID when available, else by IP."""
    auth = request.headers.get("authorization", "")
    if auth.startswith("Bearer "):
        try:
            import jwt
            payload = jwt.decode(auth[7:], options={"verify_signature": False})
            return payload.get("sub", get_remote_address(request))
        except Exception:
            pass
    return get_remote_address(request)


limiter = Limiter(key_func=_get_user_or_ip, default_limits=["120/minute"])
