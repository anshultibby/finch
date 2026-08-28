"""
Profile → sandbox file. Renders the user's unified profile (mission + the
onboarding "about me" preferences) to markdown and writes it to
/home/user/store/profile.md, where the agent's sandbox file listing already
advertises it. Called on every profile save and when a fresh sandbox is booted.

Best-effort throughout: a missing sandbox or a write failure is logged and
never propagated — the profile still lives in the DB and the <mission> system
prompt directive still carries the gist.
"""
from typing import Optional

from utils.logger import get_logger

logger = get_logger(__name__)

PROFILE_PATH = "/home/user/store/profile.md"


def render_profile_md(goal) -> str:
    """Render a UserGoal row (mission + preferences) as agent-facing markdown."""
    prefs = dict(getattr(goal, "preferences", None) or {})
    lines = ["# User profile", ""]
    lines.append("This is what the user told Finch about their money and how to work with "
                 "them. Shape ideas, alerts and trades around it. Nothing trades without "
                 "their approval unless they've explicitly turned that off.")
    lines.append("")

    # ── mission ──
    lines.append("## Mission")
    if goal.title:
        lines.append(f"- **Goal:** {goal.title}")
    lines.append(f"- **Type:** {goal.kind}")
    if goal.target_amount is not None:
        t = f"- **Target:** ${goal.target_amount:,.0f}"
        if goal.deadline:
            t += f" by {goal.deadline.isoformat()}"
        lines.append(t)
    if goal.horizon_years is not None:
        h = f"- **Horizon:** {goal.horizon_years} years"
        if goal.monthly_contribution is not None:
            h += f", ${goal.monthly_contribution:,.0f}/mo contributions"
        lines.append(h)
    if goal.monthly_income is not None:
        lines.append(f"- **Target income:** ${goal.monthly_income:,.0f}/month")
    if goal.risk is not None:
        lines.append(f"- **Risk tolerance:** {goal.risk}/10")
    lines.append(f"- **Options allowed:** {'yes' if goal.options_enabled else 'no'}")
    if goal.objective:
        lines.append(f'- **In their words:** "{goal.objective}"')

    # ── preferences ──
    watch = prefs.get("watch") or []
    constraints = prefs.get("constraints") or []
    notes = (prefs.get("notes") or "").strip()
    if any([watch, constraints, notes, prefs.get("notify"), prefs.get("experience")]):
        lines.append("")
        lines.append("## Preferences")
        if prefs.get("experience"):
            exp = {"new": "new to investing", "some": "some experience", "pro": "experienced"}.get(prefs["experience"], prefs["experience"])
            lines.append(f"- **Experience:** {exp}")
        if watch:
            lines.append(f"- **Keep an eye on:** {', '.join(watch)}")
        if prefs.get("notify"):
            ch = {"app": "in-app only", "both": "app + email", "email": "email only"}.get(prefs["notify"], prefs["notify"])
            lines.append(f"- **Notify via:** {ch}")
        if constraints:
            lines.append(f"- **Never do:** {', '.join(constraints)}")
        if notes:
            lines.append(f"- **Also:** {notes}")

    lines.append("")
    return "\n".join(lines)


async def write_profile_md(user_id: str, sbx=None) -> bool:
    """Render the user's profile and write it to the sandbox. Returns True on write.

    Pass `sbx` to write into an already-open sandbox (e.g. during sandbox boot)
    and avoid a reconnect; otherwise reconnect to the user's live sandbox without
    creating one. No-op (False) if there's no sandbox or no goal."""
    try:
        from core.database import get_db_session
        from crud.user_goals import get_goal
        async with get_db_session() as db:
            goal = await get_goal(db, user_id)
        if goal is None:
            return False

        if sbx is None:
            from modules.tools.implementations.code_execution import _get_or_reconnect_sandbox
            sbx = await _get_or_reconnect_sandbox(user_id)
            if not sbx:
                return False

        await sbx.files.write(PROFILE_PATH, render_profile_md(goal))
        logger.info(f"Wrote profile.md for user {user_id}")
        return True
    except Exception as e:
        logger.debug(f"write_profile_md failed for {user_id} (non-fatal): {e}")
        return False
