"""
Database configuration and session management
"""
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from typing import Generator, AsyncGenerator
from config import Config
import logging

logger = logging.getLogger(__name__)

# Get the appropriate database URL based on USE_POOLER setting
database_url = Config.get_database_url()

# Create async SQLAlchemy engine (for async operations)
async_database_url = database_url.replace('postgresql://', 'postgresql+asyncpg://')

# Determine pool settings based on whether we're using a pooler
# Session poolers have strict limits, so we use smaller pool sizes
# Direct connections can have larger pools
if Config.USE_POOLER:
    # For Supabase session pooler: use VERY small pool to avoid hitting pooler limits
    # Session mode poolers typically have a limit of ~15 connections total
    # Keep pool small and rely on FastAPI's dependency injection to manage connections efficiently
    pool_size = 3
    max_overflow = 2
    pool_recycle = 180  # Recycle connections every 3 minutes
    pool_timeout = 5  # Fail fast if no connections available
    logger.info(f"🔗 Using POOLER mode: pool_size={pool_size}, max_overflow={max_overflow}, max_connections={pool_size + max_overflow}, timeout={pool_timeout}s")
else:
    # Direct connection: can use larger pool
    pool_size = 15
    max_overflow = 15
    pool_recycle = 3600  # Recycle connections every hour
    pool_timeout = 10
    logger.info(f"🔗 Using DIRECT connection mode: pool_size={pool_size}, max_overflow={max_overflow}, max_connections={pool_size + max_overflow}")

async_engine = create_async_engine(
    async_database_url,
    pool_pre_ping=True,
    pool_size=pool_size,
    max_overflow=max_overflow,
    pool_recycle=pool_recycle,
    pool_timeout=pool_timeout,  # Wait for a connection (fail fast)
    echo=False,
    # Additional settings to prevent connection leaks
    pool_reset_on_return='rollback',  # Reset connection state on return
    connect_args={
        'timeout': 10,  # Connection timeout
        'command_timeout': 30,  # Command execution timeout
    }
)

# Create async session factory
AsyncSessionLocal = async_sessionmaker(
    async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)

# Keep sync engine for migrations and initial setup
engine = create_engine(
    database_url,
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
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()


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

