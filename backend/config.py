"""
Configuration settings for the backend

Uses Pydantic Settings for validation and type coercion.
All environment variables are defined here with their types and defaults.
"""
import os
from typing import Optional, List
from pydantic_settings import BaseSettings
from pydantic import Field, field_validator

from models.llm_models import Models

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
    AGENT_LLM_MODEL: str = Field(
        default=Models.CLAUDE_SONNET_4_5,
        description="LLM model for the agent"
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
    REDDIT_CLIENT_ID: Optional[str] = Field(
        default=None,
        description="Reddit app client ID for sentiment data"
    )
    REDDIT_CLIENT_SECRET: Optional[str] = Field(
        default=None,
        description="Reddit app client secret"
    )
    E2B_API_KEY: Optional[str] = Field(
        default=None,
        description="E2B API key for sandboxed code execution"
    )
    
    # =========================================================================
    # Supabase Storage & Auth
    # =========================================================================
    SUPABASE_URL: str = Field(
        default="",
        description="Supabase project URL (required for auth + storage)"
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
    AGENT_TOOLS: List[str] = Field(
        default=[
            # Research
            'web_search',
            'news_search',
            'scrape_url',
            # Sandbox
            'bash',
            # File management
            'write_chat_file',
            'read_chat_file',
            'replace_in_chat_file',
            # Domain tools
            'build_custom_etf',
            'deploy_strategy',
            'update_strategy',
            'approve_strategy',
            'run_strategy',
            'delete_strategy',
            'list_strategies',
            'get_strategy',
            'get_strategy_code',
        ],
        description="All agent tools"
    )
    
    # =========================================================================
    # Context Management
    # =========================================================================
    CONTEXT_PRUNE_ENABLED: bool = Field(
        default=True,
        description="Trim old tool results from in-memory context before each LLM call"
    )
    CONTEXT_PRUNE_KEEP_LAST_ASSISTANTS: int = Field(
        default=3,
        description="Number of recent assistant messages whose tool results are protected from pruning"
    )
    CONTEXT_SOFT_TRIM_MAX_CHARS: int = Field(
        default=4000,
        description="Soft-trim tool results larger than this to head+tail with ellipsis"
    )
    CONTEXT_HARD_CLEAR_RATIO: float = Field(
        default=0.5,
        description="If a tool result exceeds this fraction of CONTEXT_SOFT_TRIM_MAX_CHARS * 10, hard-clear it"
    )
    COMPACTION_ENABLED: bool = Field(
        default=True,
        description="Summarize old history into a persistent compaction message when context is large"
    )
    COMPACTION_THRESHOLD_TOKENS: int = Field(
        default=150000,
        description="Estimated token count at which compaction is triggered"
    )
    COMPACTION_MODEL: str = Field(
        default=Models.CLAUDE_SONNET_4_5,
        description="Model used for compaction summarization (prefer a cheap/fast model)"
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

# Alias for backward compatibility with code using `from config import Config`
Config = settings
