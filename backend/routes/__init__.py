"""
API route handlers
"""
from .chat import router as chat_router
from .snaptrade import router as snaptrade_router
from .resources import router as resources_router
from .chat_files import router as chat_files_router
from .api_keys import router as api_keys_router
from .credits import router as credits_router
from .reminders import router as reminders_router
from .reminders import alpaca_router
from .market import router as market_router
from .alpaca_broker import router as alpaca_broker_router, execute_router
from .watchlist import router as watchlist_router
from .memory import router as memory_router

__all__ = [
    "chat_router",
    "snaptrade_router",
    "resources_router",
    "chat_files_router",
    "api_keys_router",
    "credits_router",
    "reminders_router",
    "alpaca_router",
    "market_router",
    "alpaca_broker_router",
    "execute_router",
    "watchlist_router",
    "memory_router",
]

