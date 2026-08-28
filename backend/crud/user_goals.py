"""
User goal / "mission" CRUD — one active goal per user (keyed by the Supabase
auth user id), stored in the user_goals table (migration 096).

Written by the onboarding wizard, read by the goal-oriented home cockpit, and
injected into the agent's system prompt so its suggestions stay shaped around
what the user is actually trying to do.
"""
from typing import Optional, Dict, Any
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.user import UserGoal

# Columns the wizard is allowed to write. Guards against arbitrary attributes
# being passed straight into setattr from request bodies.
_WRITABLE = {
    "kind", "title", "objective", "target_amount", "deadline",
    "horizon_years", "monthly_contribution", "monthly_income",
    "risk", "options_enabled", "config", "preferences", "status",
}


async def get_goal(db: AsyncSession, user_id: str) -> Optional[UserGoal]:
    """Return the user's goal row, or None if they haven't set one yet."""
    return (
        await db.execute(select(UserGoal).where(UserGoal.user_id == user_id))
    ).scalar_one_or_none()


async def set_goal(db: AsyncSession, user_id: str, data: Dict[str, Any]) -> UserGoal:
    """Upsert the user's active goal (one row per user). Returns the saved row."""
    fields = {k: v for k, v in data.items() if k in _WRITABLE}
    goal = await get_goal(db, user_id)
    if goal is None:
        goal = UserGoal(user_id=user_id, **fields)
        db.add(goal)
    else:
        for key, value in fields.items():
            setattr(goal, key, value)
        goal.status = "active"
    await db.commit()
    await db.refresh(goal)
    return goal


async def clear_goal(db: AsyncSession, user_id: str) -> None:
    """Delete the user's goal (used on reset / account deletion)."""
    goal = await get_goal(db, user_id)
    if goal is not None:
        await db.delete(goal)
        await db.commit()
