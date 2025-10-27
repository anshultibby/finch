"""
Configuration module for Finch backend
Loads environment variables from .env file
"""
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Config:
    """Application configuration"""
    
    # LLM Configuration (works with any provider via LiteLLM)
    # Supported models: gpt-5, gpt-4, claude-3-5-sonnet-20241022, gemini-pro, etc.
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-5")
    
    # SnapTrade Configuration
    SNAPTRADE_CLIENT_ID = os.getenv("SNAPTRADE_CLIENT_ID")
    SNAPTRADE_CONSUMER_KEY = os.getenv("SNAPTRADE_CONSUMER_KEY")
    
    # Database Configuration (Supabase PostgreSQL)
    DATABASE_URL = os.getenv("DATABASE_URL")
    
    # Encryption Configuration
    # Generate with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
    ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY")
    
    # API Configuration
    API_HOST = os.getenv("API_HOST", "0.0.0.0")
    API_PORT = int(os.getenv("API_PORT", "8000"))
    
    # CORS Configuration
    CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")
    
    # Validate required configuration
    @classmethod
    def validate(cls):
        """Validate that required configuration is present"""
        if not cls.OPENAI_API_KEY:
            raise ValueError(
                "OPENAI_API_KEY is required. Please add it to your .env file.\n"
                "Get your API key from: https://platform.openai.com/api-keys"
            )
        
        if not cls.SNAPTRADE_CLIENT_ID or not cls.SNAPTRADE_CONSUMER_KEY:
            raise ValueError(
                "SNAPTRADE_CLIENT_ID and SNAPTRADE_CONSUMER_KEY are required.\n"
                "Get your API keys from: https://snaptrade.com/dashboard"
            )
    
    @classmethod
    def is_snaptrade_configured(cls):
        """Check if SnapTrade credentials are configured"""
        return bool(cls.SNAPTRADE_CLIENT_ID and cls.SNAPTRADE_CONSUMER_KEY)


# Validate configuration on import
Config.validate()

