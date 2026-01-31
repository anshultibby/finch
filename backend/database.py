"""
Database configuration and session management
"""
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from typing import Generator, AsyncGenerator
from contextlib import asynccontextmanager
from config import Config
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
    # For Supabase session pooler: use moderate pool to handle concurrent requests
    # Session mode poolers typically have a limit of ~15 connections total
    # Increased pool size to handle multiple concurrent requests without exhausting the pool
    pool_size = 8
    max_overflow = 7
    pool_recycle = 180  # Recycle connections every 3 minutes
    pool_timeout = 30  # Wait longer for connections (30s instead of 5s)
    
    # CRITICAL: Disable prepared statements for pgbouncer compatibility
    connect_args = {
        'timeout': 10,
        'command_timeout': 30,
        'statement_cache_size': 0,  # Disable prepared statements
        'prepared_statement_cache_size': 0,
        'server_settings': {
            'jit': 'off'  # Disable JIT compilation for better compatibility
        }
    }
    execution_options = {
        "compiled_cache": None  # Disable SQLAlchemy's query compilation cache
    }
    logger.info(f"🔗 Using POOLER mode: pool_size={pool_size}, max_overflow={max_overflow}, max_connections={pool_size + max_overflow}, timeout={pool_timeout}s, prepared_statements=DISABLED")
else:
    # Direct connection: can use larger pool (Supabase allows ~60 concurrent connections)
    # Using conservative settings to leave headroom for other services
    pool_size = 10  # Base connections always kept alive
    max_overflow = 20  # Additional connections created on demand (total max: 30)
    pool_recycle = 3600  # Recycle connections every hour
    pool_timeout = 10  # Fail faster if pool is exhausted (indicates a leak)
    
    # Enable prepared statements for better performance on direct connections
    connect_args = {
        'timeout': 10,
        'command_timeout': 30,
        'statement_cache_size': 100,  # Cache up to 100 prepared statements per connection
        'server_settings': {
            'jit': 'on'  # Enable JIT compilation for better performance
        }
    }
    execution_options = {}  # Enable SQLAlchemy's query compilation cache
    logger.info(f"🔗 Using DIRECT connection mode: pool_size={pool_size}, max_overflow={max_overflow}, max_connections={pool_size + max_overflow}, prepared_statements=ENABLED")

async_engine = create_async_engine(
    async_database_url,
    pool_pre_ping=True,
    pool_size=pool_size,
    max_overflow=max_overflow,
    pool_recycle=pool_recycle,
    pool_timeout=pool_timeout,
    echo=False,
    pool_reset_on_return='rollback',  # Reset connection state on return
    connect_args=connect_args,
    execution_options=execution_options
)

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

# Keep sync engine for migrations and initial setup
# Force psycopg2 driver for sync engine (not asyncpg)
sync_database_url = database_url.replace('postgresql://', 'postgresql+psycopg2://')
engine = create_engine(
    sync_database_url,
    pool_pre_ping=True,
    pool_size=pool_size,
    max_overflow=max_overflow,
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
    pool = async_engine.pool
    return {
        "size": pool.size(),
        "checked_out": pool.checkedout(),
        "overflow": pool.overflow(),
        "checkedin": pool.checkedin(),
        "total": pool.size() + pool.overflow(),
        "timeout": pool_timeout
    }


class DatabaseSession:
    """
    Context manager for database sessions that ensures proper cleanup.
    
    Usage:
        async with DatabaseSession() as db:
            result = await db.execute(query)
    """
    def __init__(self):
        self.session = None
    
    async def __aenter__(self):
        self.session = AsyncSessionLocal()
        return self.session
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            try:
                if exc_type is None:
                    # Success - commit transaction
                    await self.session.commit()
                else:
                    # Error - rollback transaction
                    await self.session.rollback()
            except Exception as cleanup_error:
                logger.error(f"Error during session cleanup: {cleanup_error}")
                try:
                    await self.session.rollback()
                except:
                    pass
            finally:
                # Always close the session to return connection to pool
                try:
                    await self.session.close()
                except Exception as close_error:
                    logger.error(f"Error closing session: {close_error}")
        
        # Don't suppress the original exception
        return False


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
    from models.db import SnapTradeUser  # noqa
    Base.metadata.create_all(bind=engine)

