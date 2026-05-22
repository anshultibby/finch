"""
CRUD operations for user-scoped memory store files and dreams.
"""
import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional, List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.store import StoreFile, Dream


# ============================================================================
# Store Files
# ============================================================================

async def list_store_files(
    db: AsyncSession,
    user_id: str,
) -> List[StoreFile]:
    result = await db.execute(
        select(StoreFile)
        .where(StoreFile.user_id == user_id)
        .order_by(StoreFile.filename)
    )
    return list(result.scalars().all())


async def get_store_file(
    db: AsyncSession,
    user_id: str,
    filename: str,
) -> Optional[StoreFile]:
    result = await db.execute(
        select(StoreFile).where(
            StoreFile.user_id == user_id,
            StoreFile.filename == filename,
        )
    )
    return result.scalar_one_or_none()


async def upsert_store_file(
    db: AsyncSession,
    user_id: str,
    filename: str,
    content: str,
    file_type: str = "store",
) -> StoreFile:
    existing = await get_store_file(db, user_id, filename)
    if existing:
        existing.content = content
        existing.file_type = file_type
        await db.commit()
        await db.refresh(existing)
        return existing

    file = StoreFile(
        id=uuid.uuid4(),
        user_id=user_id,
        filename=filename,
        content=content,
        file_type=file_type,
    )
    db.add(file)
    await db.commit()
    await db.refresh(file)
    return file


# ============================================================================
# Dreams
# ============================================================================

async def create_dream(
    db: AsyncSession,
    user_id: str,
    trigger: str,
    chat_ids: Optional[List[str]] = None,
) -> Dream:
    dream = Dream(
        id=uuid.uuid4(),
        user_id=user_id,
        status="pending",
        trigger=trigger,
        chat_ids=chat_ids or [],
    )
    db.add(dream)
    await db.commit()
    await db.refresh(dream)
    return dream


async def update_dream(db: AsyncSession, dream: Dream, **fields) -> Dream:
    for key, val in fields.items():
        setattr(dream, key, val)
    await db.commit()
    await db.refresh(dream)
    return dream


async def list_dreams(
    db: AsyncSession,
    user_id: str,
    limit: int = 20,
) -> List[Dream]:
    result = await db.execute(
        select(Dream)
        .where(Dream.user_id == user_id)
        .order_by(Dream.created_at.desc())
        .limit(limit)
    )
    return list(result.scalars().all())


async def get_dream(db: AsyncSession, dream_id: str) -> Optional[Dream]:
    result = await db.execute(select(Dream).where(Dream.id == dream_id))
    return result.scalar_one_or_none()


async def get_running_dream(db: AsyncSession, user_id: str) -> Optional[Dream]:
    result = await db.execute(
        select(Dream).where(
            Dream.user_id == user_id,
            Dream.status.in_(["pending", "running"]),
        )
    )
    return result.scalar_one_or_none()


async def get_recent_dream(
    db: AsyncSession,
    user_id: str,
    within_minutes: int = 30,
) -> Optional[Dream]:
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=within_minutes)
    result = await db.execute(
        select(Dream).where(
            Dream.user_id == user_id,
            Dream.created_at >= cutoff,
        ).limit(1)
    )
    return result.scalar_one_or_none()
