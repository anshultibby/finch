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
from core.config import Config

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
    
    # Determine log level (check env var first, then parameter, then default to INFO)
    if level is None:
        import os
        level = os.getenv('LOG_LEVEL', 'INFO')
    
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
    
    # Log that we've configured logging (skip if in sandbox mode)
    import os
    if not os.getenv('CODE_SANDBOX'):
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

