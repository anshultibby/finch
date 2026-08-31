"""CRUD for user-owned strategies (pillar 5). Only the user's own rows — the
starter catalog is served from services/strategy_starters.py."""
import re
import uuid
from typing import Any, Dict, List, Optional

from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from models.strategy import Strategy

_WRITABLE = {"name", "slug", "description", "style", "spec", "source", "source_id", "status"}


def _slugify(name: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", (name or "").lower()).strip("-")
    return (s or "strategy")[:60]


async def list_user_strategies(db: AsyncSession, user_id: str,
                               status: str = "adopted") -> List[Strategy]:
    q = select(Strategy).where(Strategy.user_id == user_id)
    if status:
        q = q.where(Strategy.status == status)
    q = q.order_by(desc(Strategy.created_at))
    return list((await db.execute(q)).scalars().all())


async def get_strategy(db: AsyncSession, strategy_id: str, user_id: str) -> Optional[Strategy]:
    return (await db.execute(
        select(Strategy).where(Strategy.id == strategy_id, Strategy.user_id == user_id)
    )).scalar_one_or_none()


async def create_strategy(db: AsyncSession, user_id: str, data: Dict[str, Any]) -> Strategy:
    fields = {k: v for k, v in data.items() if k in _WRITABLE}
    fields.setdefault("slug", _slugify(fields.get("name", "")))
    row = Strategy(id=uuid.uuid4().hex[:12], user_id=user_id, **fields)
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return row


async def set_status(db: AsyncSession, strategy_id: str, user_id: str, status: str) -> Optional[Strategy]:
    row = await get_strategy(db, strategy_id, user_id)
    if row is None:
        return None
    row.status = status
    await db.commit()
    await db.refresh(row)
    return row
