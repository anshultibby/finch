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
    DATABASE_URL_POOLER = os.getenv("DATABASE_URL_POOLER", "")
    USE_POOLER = os.getenv("USE_POOLER", "false").lower() == "true"
    
    @classmethod
    def get_database_url(cls) -> str:
        """Get the appropriate database URL based on USE_POOLER setting"""
        if cls.USE_POOLER and cls.DATABASE_URL_POOLER:
            return cls.DATABASE_URL_POOLER
        return cls.DATABASE_URL
    
    # LLM API Keys and Model
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
    LLM_MODEL = os.getenv("LLM_MODEL", "claude-sonnet-4-5-20250929")
    
    # SnapTrade
    SNAPTRADE_CLIENT_ID = os.getenv("SNAPTRADE_CLIENT_ID")
    SNAPTRADE_CONSUMER_KEY = os.getenv("SNAPTRADE_CONSUMER_KEY")
    
    # FMP (Financial Modeling Prep)
    FMP_API_KEY = os.getenv("FMP_API_KEY")
    
    # Encryption key for sensitive data
    ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY")
    
    # Supabase Storage
    SUPABASE_URL = os.getenv("SUPABASE_URL", "")
    SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY", "")
    SUPABASE_STORAGE_BUCKET = os.getenv("SUPABASE_STORAGE_BUCKET", "chat-files")
    
    # Debug settings
    DEBUG_LLM_CALLS = os.getenv("DEBUG_LLM_CALLS", "false").lower() == "true"
    DEBUG_CHAT_LOGS = os.getenv("DEBUG_CHAT_LOGS", "false").lower() == "true"
    
    # Performance monitoring (backend only - not sent to frontend)
    ENABLE_TIMING_LOGS = os.getenv("ENABLE_TIMING_LOGS", "true").lower() == "true"
    
    # API Configuration
    API_HOST = os.getenv("API_HOST", "0.0.0.0")
    API_PORT = int(os.getenv("PORT", os.getenv("API_PORT", "8000")))
    
    # CORS - Parse comma-separated origins, with production defaults
    CORS_ORIGINS = os.getenv(
        "CORS_ORIGINS", 
        "http://localhost:3000,http://localhost:3001,https://finch-omega.vercel.app"
    ).split(",")
    
    # LangFuse (optional - for LLM observability)
    LANGFUSE_PUBLIC_KEY = os.getenv("LANGFUSE_PUBLIC_KEY")
    
    # Chat History Limit (max messages to send to LLM for context)
    CHAT_HISTORY_LIMIT = int(os.getenv("CHAT_HISTORY_LIMIT", "50"))
    LANGFUSE_SECRET_KEY = os.getenv("LANGFUSE_SECRET_KEY")
    LANGFUSE_HOST = os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com")
