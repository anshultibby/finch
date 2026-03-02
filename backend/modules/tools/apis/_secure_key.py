"""
Secure API Key Wrapper

Prevents accidental logging or printing of API keys while allowing
normal string operations for API calls.
"""
from typing import Optional


class SecureKey:
    """
    Wrapper for API keys that prevents them from being printed or logged.
    
    The key can still be used in API calls and string operations,
    but str() and repr() will never reveal the actual key value.
    
    Usage:
        key = SecureKey("secret_api_key_123")
        
        # Safe - doesn't print the key
        print(key)  # Output: SecureKey(****...123)
        logger.info(f"Using key: {key}")  # Safe
        
        # Works normally for API calls
        headers = {"Authorization": f"Bearer {key.get()}"}
        response = requests.get(url, headers=headers)
    """
    
    __slots__ = ('_key',)
    
    def __init__(self, key: Optional[str]):
        """
        Initialize secure key wrapper.
        
        Args:
            key: The API key to wrap (or None)
        """
        object.__setattr__(self, '_key', key)
    
    def get(self) -> Optional[str]:
        """
        Get the actual key value for use in API calls.
        
        Returns:
            The unwrapped key string, or None if not set
        """
        return self._key
    
    def exists(self) -> bool:
        """Check if key is set (not None and not empty)"""
        return bool(self._key)
    
    def masked(self) -> str:
        """
        Get a masked version showing only first 4 and last 4 characters.
        
        Returns:
            Masked key like "abcd****xyz9" or "****" if not set
        """
        if not self._key:
            return "****"
        if len(self._key) <= 8:
            return "*" * len(self._key)
        return f"{self._key[:4]}{'*' * (len(self._key) - 8)}{self._key[-4:]}"
    
    def __str__(self) -> str:
        """Safe string representation - never reveals the key"""
        return f"SecureKey({self.masked()})"
    
    def __repr__(self) -> str:
        """Safe repr - never reveals the key"""
        return f"SecureKey({self.masked()})"
    
    def __bool__(self) -> bool:
        """Allow truthiness checks: if api_key: ..."""
        return self.exists()
    
    def __eq__(self, other) -> bool:
        """Compare keys securely"""
        if isinstance(other, SecureKey):
            return self._key == other._key
        return False
    
    def __hash__(self) -> int:
        """Allow use in sets/dicts"""
        return hash(self._key) if self._key else hash(None)
    
    def __setattr__(self, name, value):
        """Prevent modification after creation"""
        raise AttributeError("SecureKey is immutable")
    
    def __delattr__(self, name):
        """Prevent deletion"""
        raise AttributeError("SecureKey is immutable")


def secure_key_or_none(value: Optional[str]) -> Optional[SecureKey]:
    """
    Helper to create SecureKey or return None if value is None/empty.
    
    Args:
        value: String value or None
        
    Returns:
        SecureKey wrapper if value exists, None otherwise
    """
    if not value:
        return None
    return SecureKey(value)
