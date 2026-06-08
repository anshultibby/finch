"""
API route handlers
"""
from .chat import router as chat_router
from .snaptrade import router as snaptrade_router
from .robinhood import router as robinhood_router
from .resources import router as resources_router
from .chat_files import router as chat_files_router
from .api_keys import router as api_keys_router
from .credits import router as credits_router
from .market import router as market_router
from .watchlist import router as watchlist_router
from .push import router as push_router
from .analysis import router as analysis_router
from .visualizations import router as visualizations_router
from .bot_store import router as bot_store_router
from .account import router as account_router
from .trades import router as trades_router

__all__ = [
    "chat_router",
    "snaptrade_router",
    "robinhood_router",
    "resources_router",
    "chat_files_router",
    "api_keys_router",
    "credits_router",
    "market_router",
    "watchlist_router",
    "push_router",
    "analysis_router",
    "visualizations_router",
    "bot_store_router",
    "account_router",
    "trades_router",
]

