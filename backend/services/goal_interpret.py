"""
Goal interpret — turns a user's free-text goal ("make a quick $1k", "grow slow
and safe") into a structured mission draft for the Meet-Finch onboarding. One
fast LLM call; falls back to a keyword heuristic if the model is unavailable so
onboarding never blocks. Nothing is persisted here — the draft is shown in the
reveal, then persisted via PUT /goal when the user hits "Let's go".
"""
import json
import re
from typing import Any, Dict

from litellm import acompletion
from core.constants import Models
from utils.logger import get_logger

logger = get_logger(__name__)

SYSTEM = """You are Finch, a sharp, warm investing analyst helping a new user set their "mission" from one sentence.

Classify their goal and fill in sensible defaults. Reply with ONLY a raw JSON object (no code fences, no prose):
{
  "kind": "number" | "grow" | "income" | "protect",
  "target_amount": <int dollars, number goals only, else null>,   // e.g. 1000
  "days": <7 | 21 | 30 | 90, number goals only, else null>,
  "horizon_years": <int, grow goals only, else null>,             // e.g. 10
  "monthly_income": <int dollars/mo, income goals only, else null>,
  "risk": <int 1-10, null for protect>,                           // aggressive~8, balanced~6, safe~4
  "options_enabled": <bool>,                                       // true only if clearly aggressive
  "title": "<short mission title, e.g. 'Make $1,000 in 3 weeks'>",
  "stance": "<short tag, e.g. 'full send · stocks + options' or 'low-stress · diversified'>",
  "reaction": "<ONE witty, specific, encouraging line in Finch's voice reacting to their goal. Honest, a little funny, never salesy. e.g. 'A ~20% run on ~$5k. Ambitious — not delusional. I like it.'>"
}

kind guide: number=a dollar target by a deadline / aggressive profits; grow=long-term steady compounding / safe growth; income=recurring monthly cash flow; protect=watch-only, no return target ("just watch", "don't lose it").
Assume a ~$5k starting book if unknown. Keep numbers realistic. reaction must be specific to what they said."""

_ALLOWED_DAYS = {7, 21, 30, 90}


def _heuristic(text: str) -> Dict[str, Any]:
    s = text.lower()
    if re.search(r"watch|monitor|protect|warn|keep an eye|don.?t lose|safe.?ty|back", s) and "growth" not in s:
        return {"kind": "protect", "risk": None, "options_enabled": False,
                "title": "Watch & protect my portfolio", "stance": "alerts only · no trades without you",
                "reaction": "Smoke detector, not arsonist. I'll watch, you sleep."}
    if re.search(r"income|monthly|cash ?flow|dividend|passive", s):
        return {"kind": "income", "monthly_income": 300, "risk": 5, "options_enabled": True,
                "title": "Generate ~$300/mo income", "stance": "conservative · covered calls + dividends",
                "reaction": "Cash flow mode. Let's get you paid."}
    if re.search(r"grow|long|steady|slow|retire|years|wealth|nest egg", s):
        return {"kind": "grow", "horizon_years": 10, "risk": 4, "options_enabled": False,
                "title": "Grow steadily over 10 years", "stance": "low-stress · diversified",
                "reaction": "The boring plan. My favorite. This is how real money gets made."}
    return {"kind": "number", "target_amount": 1000, "days": 21, "risk": 7, "options_enabled": True,
            "title": "Make $1,000 in 3 weeks", "stance": "full send · stocks + options",
            "reaction": "A target. My favorite kind of problem. Ambitious — not delusional."}


def _normalize(d: Dict[str, Any], text: str) -> Dict[str, Any]:
    base = _heuristic(text)
    kind = d.get("kind") if d.get("kind") in {"number", "grow", "income", "protect"} else base["kind"]
    out: Dict[str, Any] = {
        "kind": kind,
        "target_amount": None, "days": None, "horizon_years": None, "monthly_income": None,
        "risk": d.get("risk") if isinstance(d.get("risk"), int) else base.get("risk"),
        "options_enabled": bool(d.get("options_enabled", base.get("options_enabled", False))),
        "title": (str(d.get("title") or base.get("title") or "")[:80]),
        "stance": (str(d.get("stance") or base.get("stance") or "")[:60]),
        "reaction": (str(d.get("reaction") or base.get("reaction") or "")[:180]),
    }
    if kind == "protect":
        out["risk"] = None
    if kind == "number":
        out["target_amount"] = int(d.get("target_amount") or base.get("target_amount") or 1000)
        days = d.get("days") or base.get("days") or 21
        out["days"] = days if days in _ALLOWED_DAYS else min(_ALLOWED_DAYS, key=lambda x: abs(x - days))
    elif kind == "grow":
        out["horizon_years"] = int(d.get("horizon_years") or base.get("horizon_years") or 10)
    elif kind == "income":
        out["monthly_income"] = int(d.get("monthly_income") or base.get("monthly_income") or 300)
    return out


async def interpret_goal(text: str) -> Dict[str, Any]:
    """Free-text goal → structured mission draft. Never raises; falls back to a
    keyword heuristic on any LLM/parse failure."""
    text = (text or "").strip()[:400]
    if not text:
        return _normalize({}, "")
    try:
        resp = await acompletion(
            model=Models.CLAUDE_HAIKU_4_5,
            max_tokens=300,
            messages=[
                {"role": "system", "content": SYSTEM},
                {"role": "user", "content": f'The user said: "{text}"'},
            ],
        )
        content = resp.choices[0].message.content or ""
        m = re.search(r"\{.*\}", content, re.DOTALL)
        data = json.loads(m.group(0)) if m else {}
        return _normalize(data if isinstance(data, dict) else {}, text)
    except Exception as e:
        logger.info(f"interpret_goal fell back to heuristic ({e})")
        return _normalize({}, text)
