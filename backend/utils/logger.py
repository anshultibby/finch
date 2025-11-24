"""
Centralized logging configuration for the application

Usage:
    from utils.logger import get_logger
    
    logger = get_logger(__name__)
    logger.info("Processing message")
    logger.error("Failed to connect", exc_info=True)
"""
import logging
import sys
from typing import Optional
from config import Config

# Define log format
LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# Global logging configuration
_configured = False


def configure_logging(level: Optional[str] = None):
    """
    Configure logging for the entire application
    Call this once at startup (e.g., in main.py)
    
    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR). 
               Defaults to INFO. DEBUG_LLM_CALLS only controls file saving, not console verbosity.
    """
    global _configured
    
    if _configured:
        return
    
    # Determine log level (default to INFO - DEBUG_LLM_CALLS only affects file saving, not console)
    if level is None:
        level = "INFO"
    
    # Configure root logger
    logging.basicConfig(
        level=level,
        format=LOG_FORMAT,
        datefmt=DATE_FORMAT,
        stream=sys.stdout,
        force=True  # Override any existing configuration
    )
    
    # Set specific loggers to reduce noise
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    
    # LiteLLM can be very noisy, control it
    logging.getLogger("LiteLLM").setLevel(logging.WARNING)
    logging.getLogger("litellm").setLevel(logging.WARNING)
    
    # Suppress verbose OpenAI SDK HTTP logs
    logging.getLogger("openai").setLevel(logging.WARNING)
    logging.getLogger("openai._base_client").setLevel(logging.WARNING)
    
    _configured = True
    
    # Log that we've configured logging
    root_logger = logging.getLogger()
    root_logger.info(f"Logging configured at {level} level")


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger for a module
    
    Args:
        name: Usually __name__ of the calling module
        
    Returns:
        Configured logger instance
        
    Usage:
        logger = get_logger(__name__)
        logger.info("Hello world")
    """
    # Ensure logging is configured
    if not _configured:
        configure_logging()
    
    return logging.getLogger(name)


# Convenience functions for common use cases
def log_api_call(logger: logging.Logger, method: str, url: str, status: int, duration_ms: float):
    """Log an API call with consistent format"""
    logger.info(
        f"API {method} {url} - {status} ({duration_ms:.0f}ms)",
        extra={
            "method": method,
            "url": url,
            "status": status,
            "duration_ms": duration_ms,
            "type": "api_call"
        }
    )


def log_db_query(logger: logging.Logger, operation: str, table: str, duration_ms: float, count: Optional[int] = None):
    """Log a database query with consistent format"""
    count_str = f" ({count} rows)" if count is not None else ""
    logger.debug(
        f"DB {operation} {table}{count_str} ({duration_ms:.0f}ms)",
        extra={
            "operation": operation,
            "table": table,
            "duration_ms": duration_ms,
            "count": count,
            "type": "db_query"
        }
    )


def log_tool_execution(logger: logging.Logger, tool_name: str, success: bool, duration_ms: float, error: Optional[str] = None):
    """Log a tool execution with consistent format"""
    status = "✅" if success else "❌"
    error_str = f" - {error}" if error else ""
    logger.info(
        f"{status} Tool {tool_name} ({duration_ms:.0f}ms){error_str}",
        extra={
            "tool_name": tool_name,
            "success": success,
            "duration_ms": duration_ms,
            "error": error,
            "type": "tool_execution"
        }
    )


def log_llm_call(logger: logging.Logger, model: str, tokens: Optional[int], duration_ms: float, stream: bool = False):
    """Log an LLM call with consistent format"""
    stream_str = " (streaming)" if stream else ""
    tokens_str = f" - {tokens} tokens" if tokens else ""
    logger.info(
        f"LLM {model}{stream_str}{tokens_str} ({duration_ms:.0f}ms)",
        extra={
            "model": model,
            "tokens": tokens,
            "duration_ms": duration_ms,
            "stream": stream,
            "type": "llm_call"
        }
    )

