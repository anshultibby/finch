"""
Encryption service for securely storing sensitive data
Uses Fernet (symmetric encryption) for token storage
"""
from cryptography.fernet import Fernet
from typing import Optional
from config import Config


class EncryptionService:
    """
    Service for encrypting/decrypting sensitive data
    
    Uses Fernet (AES-128 in CBC mode with HMAC for authentication)
    - Encryption key is stored in environment variable
    - Encrypted data is base64-encoded for storage
    
    SECURITY:
    - Never log decrypted values
    - Key must be kept secret and backed up
    - Losing the key means losing access to all encrypted data
    """
    
    def __init__(self, encryption_key: Optional[str] = None):
        """
        Initialize encryption service
        
        Args:
            encryption_key: Base64-encoded Fernet key. If None, uses Config.ENCRYPTION_KEY
        """
        key = encryption_key or Config.ENCRYPTION_KEY
        if not key:
            raise ValueError(
                "ENCRYPTION_KEY is required. Generate one with:\n"
                "python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""
            )
        
        self.cipher = Fernet(key.encode())
    
    def encrypt(self, plaintext: str) -> str:
        """
        Encrypt a string
        
        Args:
            plaintext: String to encrypt
        
        Returns:
            Base64-encoded ciphertext
        """
        if not plaintext:
            raise ValueError("Cannot encrypt empty string")
        
        encrypted_bytes = self.cipher.encrypt(plaintext.encode())
        return encrypted_bytes.decode()
    
    def decrypt(self, ciphertext: str) -> str:
        """
        Decrypt a string
        
        Args:
            ciphertext: Base64-encoded ciphertext
        
        Returns:
            Decrypted plaintext
        
        Raises:
            cryptography.fernet.InvalidToken: If ciphertext is invalid or key is wrong
        """
        if not ciphertext:
            raise ValueError("Cannot decrypt empty string")
        
        decrypted_bytes = self.cipher.decrypt(ciphertext.encode())
        return decrypted_bytes.decode()
    
    @staticmethod
    def generate_key() -> str:
        """
        Generate a new Fernet encryption key
        
        Returns:
            Base64-encoded key (safe to store in .env file)
        
        Usage:
            key = EncryptionService.generate_key()
            print(f"ENCRYPTION_KEY={key}")
        """
        return Fernet.generate_key().decode()


# Global instance
encryption_service = EncryptionService()

