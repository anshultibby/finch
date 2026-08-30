"""The single-completion narration wrapper shared by the insight passes.

Portfolio digest, ledger review and move explainer each ran the identical
"one non-streaming LLM call, thinking disabled, insight-model policy" pattern
and differed only in prompt, token budget and how they parse the result. That
boilerplate lives here.

Model policy:
- pass `user_id` (and no `model`) → resolved per tenant via insight_model
  (GLM only for opted-in tenants; used by passes that send real holdings).
- pass an explicit `model` → used as-is (e.g. move_explainer's flat, shared,
  symbol-scoped model).
"""
import logging
from typing import Any, Callable, Optional

from services.insight_model import resolve_insight_model, thinking_off_kwargs

logger = logging.getLogger(__name__)


async def narrate(
    *,
    system_prompt: str,
    user_content: str,
    agent_type: str,
    max_tokens: int,
    user_id: Optional[str] = None,
    model: Optional[str] = None,
    parser: Optional[Callable[[str], Any]] = None,
) -> Any:
    """Run one grounded, non-reasoning completion and return its text.

    Returns the stripped text (or `parser(text)` if a parser is given), or
    None on empty output or any failure — callers supply their own fallback.
    """
    from modules.agent.llm_handler import LLMHandler

    if model is None:
        model = await resolve_insight_model(user_id)

    handler = LLMHandler(user_id=None, chat_id=None, agent_type=agent_type)
    try:
        response = await handler.acompletion(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
            stream=False,
            max_tokens=max_tokens,
            **thinking_off_kwargs(model),
        )
        text = (response.choices[0].message.content or "").strip()
    except Exception:
        logger.exception("narrate failed (%s)", agent_type)
        return None

    if parser is not None:
        return parser(text)
    return text or None
