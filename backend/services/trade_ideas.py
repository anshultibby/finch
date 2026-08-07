"""
Trade ideas — proposal, decision, scoring, metrics.

The scoring sweep is the heart of this. It walks every still-open idea, replays
the daily bars since it was proposed, and decides what actually happened:

    stop hit first  -> outcome="stop"     (a loss, even if we never traded it)
    target hit      -> outcome="target"
    horizon elapsed -> outcome="expired"  (marked at the last close)

Stop is checked before target within a day. We only have daily OHLC here, so a
bar that spans both levels is genuinely ambiguous — assuming the stop is the
pessimistic read, and pessimistic is the honest default for a system grading its
own suggestions.

Every scored idea is also measured against SPY over the identical window, so
`alpha_pct` separates "the pick was good" from "the market went up".
"""
import uuid
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional

from sqlalchemy import select

from core.database import get_db_session
from models.trade_idea import TradeIdea
from schemas.trade_ideas import (
    Idea, IdeaCreate, IdeaDecision, IdeaList, IdeaScorecard,
)
from utils.logger import get_logger

logger = get_logger(__name__)

BENCHMARK = "SPY"
# Ideas per user that may sit un-decided at once. Keeps the agent from firing a
# scattergun of low-conviction names the user then has to wade through.
OPEN_PROPOSAL_LIMIT = 10


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _to_dto(row: TradeIdea) -> Idea:
    return Idea(
        id=row.id, user_id=row.user_id, created_at=row.created_at,
        symbol=row.symbol, direction=row.direction,
        catalyst_type=row.catalyst_type, catalyst_summary=row.catalyst_summary,
        thesis=row.thesis, bear_case=row.bear_case, sources=row.sources or [],
        entry_ref=row.entry_ref, stop=row.stop, target=row.target,
        horizon_days=row.horizon_days, conviction=row.conviction,
        status=row.status, execution_mode=row.execution_mode,
        decided_at=row.decided_at, outcome=row.outcome, scored_at=row.scored_at,
        exit_price=row.exit_price, return_pct=row.return_pct,
        benchmark_return_pct=row.benchmark_return_pct, r_multiple=row.r_multiple,
    )


# ── proposal & decision ──────────────────────────────────────────────────────

async def propose(user_id: str, ic: IdeaCreate) -> Idea:
    """Record a new idea. Raises ValueError if the user already has too many
    undecided proposals waiting."""
    async with get_db_session() as db:
        open_proposals = len((await db.execute(
            select(TradeIdea.id).where(TradeIdea.user_id == user_id,
                                       TradeIdea.status == "proposed",
                                       TradeIdea.outcome == "pending")
        )).scalars().all())
        if open_proposals >= OPEN_PROPOSAL_LIMIT:
            raise ValueError(
                f"{open_proposals} ideas are already awaiting a decision "
                f"(limit {OPEN_PROPOSAL_LIMIT}). Let those resolve first."
            )
        row = TradeIdea(
            id=uuid.uuid4().hex[:12], user_id=user_id, symbol=ic.symbol.upper(),
            direction=ic.direction, catalyst_type=ic.catalyst_type,
            catalyst_summary=ic.catalyst_summary, thesis=ic.thesis,
            bear_case=ic.bear_case, sources=ic.sources or [],
            entry_ref=ic.entry_ref, stop=ic.stop, target=ic.target,
            horizon_days=ic.horizon_days, conviction=ic.conviction,
            status="proposed", outcome="pending",
        )
        db.add(row)
        await db.commit()
        await db.refresh(row)
        logger.info(f"Idea {row.id}: {row.symbol} {row.catalyst_type} for {user_id}")
        return _to_dto(row)


async def decide(user_id: str, idea_id: str, d: IdeaDecision) -> Optional[Idea]:
    """Approve (choosing auto or manual execution) or reject a proposal."""
    async with get_db_session() as db:
        row = (await db.execute(
            select(TradeIdea).where(TradeIdea.id == idea_id,
                                    TradeIdea.user_id == user_id)
        )).scalars().first()
        if not row:
            return None
        if row.status != "proposed":
            raise ValueError(f"Idea is already {row.status}.")
        row.status = "approved" if d.approve else "rejected"
        row.execution_mode = d.execution_mode if d.approve else None
        row.decided_at = _now()
        await db.commit()
        await db.refresh(row)
        # A rejected idea keeps getting scored — that's how we learn whether the
        # rejections were right.
        return _to_dto(row)


# ── scoring ──────────────────────────────────────────────────────────────────

def _classify(idea: TradeIdea, bars: List[Dict], horizon_end: datetime) -> Optional[Dict]:
    """Walk daily bars after the proposal and decide the outcome.

    Returns None while the idea is still genuinely open (horizon not elapsed and
    neither level touched). Stop wins ties within a bar — see module docstring.
    """
    long = idea.direction == "long"
    for b in bars:
        hi, lo = b["high"], b["low"]
        hit_stop = lo <= idea.stop if long else hi >= idea.stop
        hit_target = hi >= idea.target if long else lo <= idea.target
        if hit_stop:
            return {"outcome": "stop", "exit_price": idea.stop}
        if hit_target:
            return {"outcome": "target", "exit_price": idea.target}
    if _now() >= horizon_end:
        last = bars[-1]["close"] if bars else idea.entry_ref
        return {"outcome": "expired", "exit_price": last}
    return None


def _returns(idea: TradeIdea, exit_price: float) -> Dict[str, float]:
    sign = 1.0 if idea.direction == "long" else -1.0
    ret = sign * (exit_price - idea.entry_ref) / idea.entry_ref * 100.0
    risk = abs(idea.entry_ref - idea.stop)
    r = (sign * (exit_price - idea.entry_ref) / risk) if risk else 0.0
    return {"return_pct": round(ret, 3), "r_multiple": round(r, 3)}


async def daily_bars(symbol: str, start: datetime, end: datetime) -> List[Dict]:
    """Daily OHLC for a symbol over [start, end], oldest first.

    FMP returns newest-first and its client is sync + cached, so this reverses
    and offloads it the way services/widget_data.py does.
    """
    import asyncio
    from skills.financial_modeling_prep.scripts.api import fmp

    def _fetch() -> List[Dict]:
        r = fmp(f"/historical-price-full/{symbol}",
                {"from": start.date().isoformat(), "to": end.date().isoformat()})
        rows = r.get("historical", []) if isinstance(r, dict) else []
        return [
            {"date": b["date"], "high": float(b["high"]),
             "low": float(b["low"]), "close": float(b["close"])}
            for b in reversed(rows)
            # The proposal day itself is excluded: entry_ref is that day's price,
            # so its own range would score the idea against its own bar.
            if b["date"] > start.date().isoformat()
        ]

    return await asyncio.to_thread(_fetch)


async def run_scoring_loop(interval_seconds: int = 3600) -> None:
    """Background sweep that keeps the scorecard current.

    Deliberately NOT an automation. Scoring is deterministic code — no model, no
    credits — and it has to keep running whether or not the user has the idea
    job enabled, or a paused job would silently freeze the record it's judged on.
    """
    import asyncio
    logger.info(f"Trade-idea scoring loop started (every {interval_seconds}s)")
    while True:
        try:
            await score_open_ideas()
        except Exception as e:
            logger.error(f"Idea scoring sweep failed: {e}")
        await asyncio.sleep(interval_seconds)


async def score_open_ideas(fetch_bars=None) -> int:
    """Score every open idea whose outcome is now determinable.

    `fetch_bars(symbol, start, end) -> [{date, high, low, close}]` is injected so
    this is testable without network; defaults to the FMP daily-bar client.
    """
    if fetch_bars is None:
        fetch_bars = daily_bars

    scored = 0
    async with get_db_session() as db:
        rows = (await db.execute(
            select(TradeIdea).where(TradeIdea.outcome == "pending")
        )).scalars().all()

        for row in rows:
            horizon_end = row.created_at + timedelta(days=row.horizon_days * 7 / 5)
            try:
                bars = await fetch_bars(row.symbol, row.created_at, _now())
                verdict = _classify(row, bars, horizon_end)
                if verdict is None:
                    continue
                row.outcome = verdict["outcome"]
                row.exit_price = verdict["exit_price"]
                row.scored_at = _now()
                for k, v in _returns(row, verdict["exit_price"]).items():
                    setattr(row, k, v)

                spy = await fetch_bars(BENCHMARK, row.created_at, _now())
                if spy:
                    row.benchmark_return_pct = round(
                        (spy[-1]["close"] - spy[0]["close"]) / spy[0]["close"] * 100.0, 3
                    )
                scored += 1
            except Exception as e:
                logger.warning(f"Scoring idea {row.id} ({row.symbol}) failed: {e}")
        await db.commit()
    if scored:
        logger.info(f"Scored {scored} trade idea(s)")
    return scored


# ── metrics ──────────────────────────────────────────────────────────────────

def _scorecard(ideas: List[Idea]) -> IdeaScorecard:
    done = [i for i in ideas if i.outcome != "pending"]
    wins = [i for i in done if i.outcome == "target"]
    losses = [i for i in done if i.outcome == "stop"]
    alphas = [i.alpha_pct for i in done if i.alpha_pct is not None]
    rets = [i.return_pct for i in done if i.return_pct is not None]
    rs = [i.r_multiple for i in done if i.r_multiple is not None]
    return IdeaScorecard(
        total=len(ideas),
        open=sum(1 for i in ideas if i.outcome == "pending"),
        scored=len(done),
        wins=len(wins),
        losses=len(losses),
        hit_rate=round(len(wins) / len(done), 3) if done else None,
        avg_return_pct=round(sum(rets) / len(rets), 3) if rets else None,
        avg_alpha_pct=round(sum(alphas) / len(alphas), 3) if alphas else None,
        avg_r_multiple=round(sum(rs) / len(rs), 3) if rs else None,
    )


async def list_ideas(user_id: str, limit: int = 100) -> IdeaList:
    async with get_db_session() as db:
        rows = (await db.execute(
            select(TradeIdea).where(TradeIdea.user_id == user_id)
            .order_by(TradeIdea.created_at.desc()).limit(limit)
        )).scalars().all()
    ideas = [_to_dto(r) for r in rows]
    by_catalyst: Dict[str, IdeaScorecard] = {}
    for kind in {i.catalyst_type for i in ideas}:
        by_catalyst[kind] = _scorecard([i for i in ideas if i.catalyst_type == kind])
    return IdeaList(ideas=ideas, scorecard=_scorecard(ideas), by_catalyst=by_catalyst)
