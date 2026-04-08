"""
Database configuration and session management
"""
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import NullPool
from typing import Generator, AsyncGenerator
from contextlib import asynccontextmanager
from core.config import Config
import logging

logger = logging.getLogger(__name__)

# Get the appropriate database URL based on USE_POOLER setting
database_url = Config.get_database_url()

# Create async SQLAlchemy engine (for async operations)
async_database_url = database_url.replace('postgresql://', 'postgresql+asyncpg://')

# Determine pool settings and connection args based on whether we're using a pooler
# Session poolers have strict limits, so we use smaller pool sizes
# Direct connections can have larger pools
if Config.USE_POOLER:
    # Transaction mode pooler (port 6543 on Supabase):
    # Connections are released after each transaction, so SQLAlchemy's own pool
    # is redundant. NullPool means each operation borrows a pgbouncer connection,
    # runs the transaction, and returns it immediately — no connections held idle.
    # This allows hundreds of concurrent requests to share a handful of real DB connections.
    pool_recycle = 180
    pool_timeout = 30
    connect_args = {
        'timeout': 10,
        'command_timeout': 30,
        'statement_cache_size': 0,  # Required: pgbouncer doesn't support prepared statements
        'prepared_statement_cache_size': 0,
        'server_settings': {'jit': 'off'},
    }
    execution_options = {"compiled_cache": None}
    async_engine = create_async_engine(
        async_database_url,
        poolclass=NullPool,
        connect_args=connect_args,
        execution_options=execution_options,
        echo=False,
    )
    logger.info("Using POOLER mode with NullPool (transaction-mode pgbouncer)")
else:
    # Direct connection: maintain a real pool
    pool_size = 10
    max_overflow = 20
    pool_recycle = 3600
    pool_timeout = 10
    connect_args = {
        'timeout': 10,
        'command_timeout': 30,
        'statement_cache_size': 100,
        'server_settings': {'jit': 'on'},
    }
    execution_options = {}
    async_engine = create_async_engine(
        async_database_url,
        pool_pre_ping=True,
        pool_size=pool_size,
        max_overflow=max_overflow,
        pool_recycle=pool_recycle,
        pool_timeout=pool_timeout,
        pool_reset_on_return='rollback',
        connect_args=connect_args,
        execution_options=execution_options,
        echo=False,
    )
    logger.info(f"Using DIRECT connection mode: pool_size={pool_size}, max_overflow={max_overflow}")

# Create async session factory
# Note: autocommit=False means we must manually commit transactions
# When using context manager, we handle commits in the context exit
AsyncSessionLocal = async_sessionmaker(
    async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)


@asynccontextmanager
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Async context manager for database sessions with automatic commit/rollback.

    This replaces direct use of AsyncSessionLocal() to ensure proper cleanup.

    Usage:
        async with get_db_session() as db:
            result = await db.execute(query)
            # Automatically commits on success, rolls back on error

    Yields:
        AsyncSession that auto-commits on successful exit
    """
    session = AsyncSessionLocal()
    try:
        yield session
        await session.commit()  # Commit on success
    except Exception:
        await session.rollback()  # Rollback on error
        raise
    finally:
        await session.close()  # Always close to return connection to pool

# Keep sync engine for migrations, initial setup, and legacy sync code only.
# Force psycopg2 driver for sync engine (not asyncpg).
# Minimal pool — runtime DB work should use async sessions via get_db_session().
sync_database_url = database_url.replace('postgresql://', 'postgresql+psycopg2://')
engine = create_engine(
    sync_database_url,
    pool_pre_ping=True,
    pool_size=1,
    max_overflow=2,
    pool_recycle=pool_recycle,
    pool_timeout=pool_timeout
)

# Create sync session factory (for backward compatibility)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create base class for models
Base = declarative_base()


async def get_async_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Async dependency for getting database sessions in FastAPI routes

    Usage:
        @app.get("/items")
        async def get_items(db: AsyncSession = Depends(get_async_db)):
            result = await db.execute(select(Item))
            return result.scalars().all()
    """
    session = AsyncSessionLocal()
    try:
        yield session
        await session.commit()  # Commit successful transactions
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()


def get_pool_status() -> dict:
    """
    Get current connection pool status for monitoring

    Returns:
        Dict with pool statistics (size, checked_out, overflow, etc.)
    """
    from sqlalchemy.pool import NullPool as _NullPool
    pool = async_engine.pool
    if isinstance(pool, _NullPool):
        return {"mode": "nullpool", "pooled": False}
    return {
        "size": pool.size(),
        "checked_out": pool.checkedout(),
        "overflow": pool.overflow(),
        "checkedin": pool.checkedin(),
        "total": pool.size() + pool.overflow(),
        "timeout": pool_timeout,
    }



def get_db() -> Generator[Session, None, None]:
    """
    Sync dependency for getting database sessions (legacy support)

    Usage:
        @app.get("/items")
        def get_items(db: Session = Depends(get_db)):
            return db.query(Item).all()
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()



def init_db():
    """Initialize database tables (creates all tables defined in models)"""
    # Import all models here so Base knows about them
    from models.user import SnapTradeUser  # noqa
    Base.metadata.create_all(bind=engine)
