"""
Configuration settings for the backend

Uses Pydantic Settings for validation and type coercion.
All environment variables are defined here with their types and defaults.
"""
import os
from typing import Optional, List
from pydantic_settings import BaseSettings
from pydantic import Field, field_validator


class Settings(BaseSettings):
    """
    Application configuration loaded from environment variables.
    
    All env vars are defined here - if you add a new one, add it here too.
    Pydantic will validate types and provide helpful error messages.
    """
    
    # =========================================================================
    # Database
    # =========================================================================
    DATABASE_URL: str = Field(
        default="postgresql://user:password@localhost/finch",
        description="PostgreSQL connection string"
    )
    DATABASE_URL_POOLER: str = Field(
        default="",
        description="PostgreSQL connection pooler URL (for IPv4/network issues)"
    )
    USE_POOLER: bool = Field(
        default=False,
        description="Use connection pooler instead of direct connection"
    )
    
    # =========================================================================
    # LLM Configuration
    # =========================================================================
    MASTER_LLM_MODEL: str = Field(
        default="gemini/gemini-3-pro-preview",
        description="LLM model to use for the Master Agent"
    )
    EXECUTOR_LLM_MODEL: str = Field(
        default="gemini/gemini-3-pro-preview",
        description="LLM model to use for the Executor Agent"
    )
    OPENAI_API_KEY: Optional[str] = Field(
        default=None,
        description="OpenAI API key (required for OpenAI models)"
    )
    ANTHROPIC_API_KEY: Optional[str] = Field(
        default=None,
        description="Anthropic API key (required for Claude models)"
    )
    GEMINI_API_KEY: Optional[str] = Field(
        default=None,
        description="Google Gemini API key (required for Gemini models)"
    )
    
    # =========================================================================
    # External API Keys
    # =========================================================================
    SNAPTRADE_CLIENT_ID: Optional[str] = Field(
        default=None,
        description="SnapTrade client ID for portfolio access"
    )
    SNAPTRADE_CONSUMER_KEY: Optional[str] = Field(
        default=None,
        description="SnapTrade consumer key (secret)"
    )
    FMP_API_KEY: Optional[str] = Field(
        default=None,
        description="Financial Modeling Prep API key"
    )
    POLYGON_API_KEY: Optional[str] = Field(
        default=None,
        description="Polygon.io API key for market data"
    )
    SERPER_API_KEY: Optional[str] = Field(
        default=None,
        description="Serper API key for Google search"
    )
    
    # =========================================================================
    # Supabase Storage
    # =========================================================================
    SUPABASE_URL: str = Field(
        default="",
        description="Supabase project URL"
    )
    SUPABASE_SERVICE_KEY: str = Field(
        default="",
        description="Supabase service role key (server-side only)"
    )
    SUPABASE_STORAGE_BUCKET: str = Field(
        default="chat-files",
        description="Supabase storage bucket name"
    )
    
    # =========================================================================
    # Security
    # =========================================================================
    ENCRYPTION_KEY: Optional[str] = Field(
        default=None,
        description="Fernet encryption key for sensitive data"
    )
    
    # =========================================================================
    # API Server
    # =========================================================================
    API_HOST: str = Field(
        default="0.0.0.0",
        description="Host to bind the API server"
    )
    API_PORT: int = Field(
        default=8000,
        description="Port for the API server"
    )
    CORS_ORIGINS: str = Field(
        default="http://localhost:3000,http://localhost:3001,http://localhost:3002,http://localhost:3003,http://localhost:3004,https://finch-omega.vercel.app",
        description="Allowed CORS origins (comma-separated)"
    )
    
    # =========================================================================
    # Chat Configuration
    # =========================================================================
    CHAT_HISTORY_LIMIT: int = Field(
        default=50,
        description="Max messages to send to LLM for context"
    )
    
    # =========================================================================
    # Agent Tool Configuration
    # =========================================================================
    # Shared tools available to all agents
    AGENT_TOOLS: List[str] = Field(
        default=[
            'execute_code',
            'write_chat_file',
            'read_chat_file',
            'replace_in_chat_file',
            'web_search',
            'news_search',
            'scrape_url',
        ],
        description="Base tools available to all agents"
    )
    
    # Master agent gets delegation + ETF builder
    MASTER_AGENT_EXTRA_TOOLS: List[str] = Field(
        default=['delegate_execution', 'build_custom_etf'],
        description="Additional tools for Master Agent"
    )
    
    # Executor agent gets finish_execution
    EXECUTOR_AGENT_EXTRA_TOOLS: List[str] = Field(
        default=['finish_execution'],
        description="Additional tools for Executor Agent"
    )
    
    # =========================================================================
    # Observability (LangFuse)
    # =========================================================================
    LANGFUSE_PUBLIC_KEY: Optional[str] = Field(
        default=None,
        description="LangFuse public key for LLM observability"
    )
    LANGFUSE_SECRET_KEY: Optional[str] = Field(
        default=None,
        description="LangFuse secret key"
    )
    LANGFUSE_HOST: str = Field(
        default="https://cloud.langfuse.com",
        description="LangFuse host URL"
    )
    
    # =========================================================================
    # Debug Settings
    # =========================================================================
    DEBUG_CHAT_LOGS: bool = Field(
        default=False,
        description="Save full conversation logs to chat_logs/"
    )
    ENABLE_TIMING_LOGS: bool = Field(
        default=True,
        description="Log performance timing (backend only)"
    )
    
    # =========================================================================
    # Validators
    # =========================================================================
    @property
    def cors_origins_list(self) -> List[str]:
        """Parse comma-separated CORS origins into a list"""
        return [origin.strip() for origin in self.CORS_ORIGINS.split(',') if origin.strip()]
    
    @field_validator('API_PORT', mode='before')
    @classmethod
    def parse_port(cls, v):
        """Handle Railway's PORT env var"""
        if v is None:
            # Check for Railway's PORT
            return int(os.getenv('PORT', 8000))
        return int(v)
    
    # =========================================================================
    # Helper Methods
    # =========================================================================
    def get_database_url(self) -> str:
        """Get the appropriate database URL based on USE_POOLER setting"""
        if self.USE_POOLER and self.DATABASE_URL_POOLER:
            return self.DATABASE_URL_POOLER
        return self.DATABASE_URL
    
    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",  # Ignore extra env vars not defined here
    }


# Global settings instance - import this
settings = Settings()

# Backward compatibility: Config class that proxies to settings
# This allows existing code using `from config import Config` to keep working
class Config:
    """Backward-compatible Config class that proxies to settings"""
    
    # Database
    DATABASE_URL = settings.DATABASE_URL
    DATABASE_URL_POOLER = settings.DATABASE_URL_POOLER
    USE_POOLER = settings.USE_POOLER
    
    # LLM
    MASTER_LLM_MODEL = settings.MASTER_LLM_MODEL
    EXECUTOR_LLM_MODEL = settings.EXECUTOR_LLM_MODEL
    OPENAI_API_KEY = settings.OPENAI_API_KEY
    ANTHROPIC_API_KEY = settings.ANTHROPIC_API_KEY
    GEMINI_API_KEY = settings.GEMINI_API_KEY
    
    # External APIs
    SNAPTRADE_CLIENT_ID = settings.SNAPTRADE_CLIENT_ID
    SNAPTRADE_CONSUMER_KEY = settings.SNAPTRADE_CONSUMER_KEY
    FMP_API_KEY = settings.FMP_API_KEY
    POLYGON_API_KEY = settings.POLYGON_API_KEY
    SERPER_API_KEY = settings.SERPER_API_KEY
    
    # Supabase
    SUPABASE_URL = settings.SUPABASE_URL
    SUPABASE_SERVICE_KEY = settings.SUPABASE_SERVICE_KEY
    SUPABASE_STORAGE_BUCKET = settings.SUPABASE_STORAGE_BUCKET
    
    # Security
    ENCRYPTION_KEY = settings.ENCRYPTION_KEY
    
    # API Server
    API_HOST = settings.API_HOST
    API_PORT = settings.API_PORT
    CORS_ORIGINS = settings.cors_origins_list
    
    # Chat
    CHAT_HISTORY_LIMIT = settings.CHAT_HISTORY_LIMIT
    
    # Observability
    LANGFUSE_PUBLIC_KEY = settings.LANGFUSE_PUBLIC_KEY
    LANGFUSE_SECRET_KEY = settings.LANGFUSE_SECRET_KEY
    LANGFUSE_HOST = settings.LANGFUSE_HOST
    
    # Debug
    DEBUG_CHAT_LOGS = settings.DEBUG_CHAT_LOGS
    ENABLE_TIMING_LOGS = settings.ENABLE_TIMING_LOGS
    
    # Agent Tools
    AGENT_TOOLS = settings.AGENT_TOOLS
    MASTER_AGENT_TOOLS = settings.AGENT_TOOLS + settings.MASTER_AGENT_EXTRA_TOOLS
    EXECUTOR_AGENT_TOOLS = settings.AGENT_TOOLS + settings.EXECUTOR_AGENT_EXTRA_TOOLS
    
    @classmethod
    def get_database_url(cls) -> str:
        """Get the appropriate database URL based on USE_POOLER setting"""
        return settings.get_database_url()
