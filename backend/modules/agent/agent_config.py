"""
Agent Configuration — one prompt for all agents (main + sub-agents).
"""
import json
from core.config import Config
from .prompts import get_agent_system_prompt
from utils.logger import get_logger

logger = get_logger(__name__)


async def _get_sandbox_file_listing(user_id: str) -> str:
    """List the user's memory store files (store/) so the agent knows what's available."""
    try:
        from modules.tools.implementations.code_execution import get_or_create_sandbox
        entry = await get_or_create_sandbox(user_id, envs={})
        entries = await entry.sbx.files.list("/home/user/store", depth=2)
        if not entries:
            return ""
        # Show absolute paths — read_chat_file resolves bare `store/...` under the
        # chat-files dir (404), so the agent must use /home/user/store/... here.
        lines = ["/home/user/store/ (read with these absolute paths):"]
        for e in entries:
            # Prefer the entry's full path; fall back to building it from the name.
            path = getattr(e, "path", None) or f"/home/user/store/{getattr(e, 'name', str(e))}"
            if getattr(e, "type", None) == "dir":
                path += "/"
            lines.append(f"  {path}")
        return "\n".join(lines)
    except Exception as e:
        logger.debug(f"Could not list sandbox files (non-fatal): {e}")
        return ""


async def _get_trade_execution_directive(user_id: str) -> str:
    """
    Per-session trade-execution instruction derived from the user's HITL setting.
    Enforcement is prompt-driven: the agent reads this and chooses place_order vs
    request_trade_approval. Defaults to requiring approval if anything fails.
    """
    require_approval = True
    try:
        from core.database import get_db_session
        from crud.user_preferences import get_user_preferences
        async with get_db_session() as db:
            prefs = await get_user_preferences(db, user_id)
            require_approval = bool(prefs.get("require_trade_approval", True))
    except Exception as e:
        logger.debug(f"Could not load trade-approval preference (defaulting to required): {e}")

    if require_approval:
        return (
            "<trade_execution>\n"
            "Per-trade approval is REQUIRED (the user's setting). Never call place_order "
            "directly. Build the risk-defined order, review_order it, then route it through "
            "request_trade_approval (in an automation) or show the user for a one-click "
            "confirm. No order reaches the market without the user approving it.\n"
            "</trade_execution>"
        )
    return (
        "<trade_execution>\n"
        "The user has DISABLED per-trade approval (unattended trading is ON). You MAY call "
        "place_order directly once you've built and review_order'd a risk-defined trade — no "
        "approval email needed. Still respect the day_trading RiskBudget (1% risk/trade, daily "
        "loss limit) and any dollar cap, and only ever trade the isolated agentic account.\n"
        "</trade_execution>"
    )


async def create_agent(context, user_id: str = None, skill_ids: list[str] = None, model: str = None):
    """Create an agent with the base system prompt.

    `model` overrides the default agent model (Config.AGENT_LLM_MODEL) — used by
    the per-chat model picker. None falls back to the configured default.
    """
    from .base_agent import BaseAgent

    # Static part — identical across sessions for the same user/skills (cacheable)
    system_prompt = await get_agent_system_prompt(user_id, skill_ids)

    # Dynamic part — changes per session/page (appended after cache breakpoint)
    dynamic_parts = []
    page_context = context.data.get("page_context") if context.data else None
    if page_context:
        dynamic_parts.append(f"<page_context>\nThe user is currently viewing this page. Use this data as context — don't re-fetch what's already here unless the user asks for something beyond it.\n{json.dumps(page_context, indent=2)}\n</page_context>")

    file_listing = await _get_sandbox_file_listing(context.user_id)
    if file_listing:
        dynamic_parts.append(f"<sandbox_files>\nFiles currently in your workspace:\n{file_listing}\n</sandbox_files>")

    dynamic_parts.append(await _get_trade_execution_directive(context.user_id))

    dynamic_context = "\n\n".join(dynamic_parts) if dynamic_parts else None

    return BaseAgent(
        context=context,
        system_prompt=system_prompt,
        system_prompt_dynamic=dynamic_context,
        model=model or Config.AGENT_LLM_MODEL,
        tool_names=Config.AGENT_TOOLS,
        enable_tool_streaming=True,
    )
