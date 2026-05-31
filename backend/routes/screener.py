"""
Screener API — runs a ScreenSpec against FMP and returns ranked matches.
The spec is the shared contract: the agent tool emits it, the UI edits it,
this route executes it.
"""
import asyncio
import json
import re
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from schemas.screener import ScreenSpec, ScreenResponse
from services.screener import run_screen
from modules.tools.implementations.screener import RunScreenParams, run_stock_screen_impl
from utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/screener", tags=["screener"])


@router.post("/run", response_model=ScreenResponse)
async def run(spec: ScreenSpec):
    """Execute a screen and return sorted, normalized rows."""
    try:
        rows = await asyncio.to_thread(run_screen, spec)
        return ScreenResponse(spec=spec, count=len(rows), results=rows)
    except Exception as e:
        logger.error(f"Screener run failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class ScreenAIRequest(BaseModel):
    prompt: str


_AI_SYSTEM = """You convert a user's stock-screening request into JSON filter params for a US-market screener.

Output ONLY a JSON object. Allowed keys (include only those clearly implied):
- market_cap_min, market_cap_max: market cap in RAW USD (e.g. "$2B" -> 2000000000)
- price_min, price_max: share price in USD
- beta_min, beta_max: beta (1.0 = market). "low volatility" -> beta_max ~1.0
- volume_min: min average daily volume
- dividend_min: min last annual dividend PER SHARE in $ (any dividend payer -> 0.01)
- sector: one of Technology, Healthcare, Financial Services, Consumer Cyclical, Consumer Defensive, Energy, Industrials, Basic Materials, Real Estate, Utilities, Communication Services
- industry, exchange (NASDAQ/NYSE), country (default US)
- is_etf: true to only ETFs, false to exclude
- sort_by: marketCap|price|beta|volume|dividend ; sort_dir: asc|desc ; limit: <=50
- name: a short 2-4 word name for the screen
- rationale: ONE sentence describing what this screen looks for

Map intent faithfully. "cheap" -> low price or low valuation (use price_max). "blue chip / large cap" -> market_cap_min ~10000000000. "small cap" -> market_cap_max ~2000000000."""


def _extract_json(text: str) -> dict:
    """Pull the first JSON object out of an LLM response (handles code fences)."""
    text = text.strip()
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if not m:
        raise ValueError("no JSON object in model output")
    return json.loads(m.group(0))


@router.post("/ai")
async def ai_screen(req: ScreenAIRequest):
    """Compile a natural-language request into a screen, run it, and return the
    spec + results + a one-line rationale. This is the in-view AI entry point."""
    try:
        from litellm import acompletion
        from core.config import settings
        resp = await acompletion(
            model=settings.AGENT_LLM_MODEL,
            messages=[
                {"role": "system", "content": _AI_SYSTEM},
                {"role": "user", "content": req.prompt},
            ],
            temperature=0,
            max_tokens=600,
        )
        content = resp.choices[0].message.content or "{}"
        data = _extract_json(content)
        rationale = data.pop("rationale", None)
        valid = {k: v for k, v in data.items() if k in RunScreenParams.model_fields}
        # Coerce enum-ish fields the model may drift on, so we never 500.
        if valid.get("sort_by") not in {"marketCap", "price", "beta", "volume", "dividend", "companyName"}:
            valid.pop("sort_by", None)
        if valid.get("sort_dir") not in {"asc", "desc"}:
            valid.pop("sort_dir", None)
        params = RunScreenParams(**valid)
        result = await asyncio.to_thread(run_stock_screen_impl, params, None)
        result["rationale"] = rationale
        return result
    except Exception as e:
        logger.error(f"AI screen failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
