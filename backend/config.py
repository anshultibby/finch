"""
Configuration settings for the backend
"""
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Config:
    """Application configuration"""
    
    # Database
    DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:password@localhost/finch")
    
    # OpenAI
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-5")
    
    # SnapTrade
    SNAPTRADE_CLIENT_ID = os.getenv("SNAPTRADE_CLIENT_ID")
    SNAPTRADE_CONSUMER_KEY = os.getenv("SNAPTRADE_CONSUMER_KEY")
    
    # FMP (Financial Modeling Prep)
    FMP_API_KEY = os.getenv("FMP_API_KEY")
    
    # Encryption key for sensitive data
    ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY")
    
    # Debug mode
    DEBUG_LLM_CALLS = os.getenv("DEBUG_LLM_CALLS", "false").lower() == "true"
    
    # Performance monitoring (backend only - not sent to frontend)
    ENABLE_TIMING_LOGS = os.getenv("ENABLE_TIMING_LOGS", "true").lower() == "true"
    
    # API Configuration
    API_HOST = os.getenv("API_HOST", "0.0.0.0")
    API_PORT = int(os.getenv("API_PORT", "8000"))
    
    # CORS
    CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:3001").split(",")
    
    # LangFuse (optional - for LLM observability)
    LANGFUSE_PUBLIC_KEY = os.getenv("LANGFUSE_PUBLIC_KEY")
    LANGFUSE_SECRET_KEY = os.getenv("LANGFUSE_SECRET_KEY")
    LANGFUSE_HOST = os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com")
