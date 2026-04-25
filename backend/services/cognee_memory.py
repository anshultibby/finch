"""
Cognee-powered stock knowledge memory.

Single backend instance manages the knowledge graph. The agent in the sandbox
calls these functions via HTTP routes. The frontend triggers seeding on stock
page open so knowledge is warm by the time the user asks questions.

Post-chat hook: after each chat turn, conversation is fed to cognee which
extracts learnings and updates MEMORY.md in the user's sandbox.
"""
import asyncio
import os
import uuid
import cognee
from datetime import date, datetime, timedelta
from utils.logger import get_logger

logger = get_logger(__name__)

_initialized = False
_seeding_locks: dict[str, asyncio.Lock] = {}
_seeded_tickers: set[str] = set()

STOCK_PROMPT = """
Extract entities and relationships relevant to stock market analysis.
Entity types: Company, Person, Sector, Product, FinancialMetric, Event, Theme.
Relationship types: works_at, competes_with, part_of_sector, reported_metric,
    announced, drives_growth, risk_factor, supplies_to, acquired, partners_with.
Focus on actionable financial information: earnings, guidance, catalysts, risks.
"""


async def _ensure_setup():
    global _initialized
    if _initialized:
        return

    os.environ["COGNEE_SKIP_CONNECTION_TEST"] = "true"

    openai_key = os.environ.get("OPENAI_API_KEY")
    if openai_key:
        cognee.config.set_llm_provider("openai")
        cognee.config.set_llm_api_key(openai_key)
        cognee.config.set_llm_model("gpt-4o-mini")

    cognee.config.set_embedding_provider("fastembed")
    cognee.config.set_embedding_model("BAAI/bge-small-en-v1.5")
    cognee.config.set_embedding_dimensions(384)

    _initialized = True


def _dataset(ticker: str | None) -> str:
    if ticker:
        return f"stock_{ticker.upper().strip()}"
    return "stock_general"


async def remember_stock(ticker: str, content: str, session_id: str | None = None) -> dict:
    await _ensure_setup()
    ds = _dataset(ticker)
    try:
        await cognee.remember(
            content,
            dataset_name=ds,
            session_id=session_id,
            custom_prompt=STOCK_PROMPT,
            self_improvement=False,
        )
        return {
            "success": True,
            "ticker": ticker.upper(),
            "dataset": ds,
            "status": "session_stored" if session_id else "graph_stored",
        }
    except Exception as e:
        logger.error(f"cognee remember failed for {ticker}: {e}")
        return {"success": False, "error": str(e)}


async def recall_stock(query: str, ticker: str | None = None, session_id: str | None = None, top_k: int = 5) -> list:
    await _ensure_setup()
    try:
        kwargs = {"query_text": query, "top_k": top_k}
        if ticker:
            kwargs["datasets"] = [_dataset(ticker)]
        if session_id:
            kwargs["session_id"] = session_id
        results = await cognee.recall(**kwargs)
        return results if results else []
    except Exception as e:
        logger.error(f"cognee recall failed: {e}")
        return []


async def improve_memory(ticker: str | None = None, session_ids: list | None = None) -> dict:
    await _ensure_setup()
    try:
        kwargs = {}
        if ticker:
            kwargs["dataset"] = _dataset(ticker)
        if session_ids:
            kwargs["session_ids"] = session_ids
        await cognee.improve(**kwargs)
        return {"success": True, "ticker": ticker, "sessions_consolidated": session_ids or "all"}
    except Exception as e:
        logger.error(f"cognee improve failed: {e}")
        return {"success": False, "error": str(e)}


def _fetch_fmp_news(symbol: str, days: int) -> list[dict]:
    from skills.financial_modeling_prep.scripts.api import fmp
    from_date = (date.today() - timedelta(days=days)).isoformat()
    to_date = date.today().isoformat()
    articles = fmp("/stock_news", {"tickers": symbol, "from": from_date, "to": to_date, "limit": 50})
    if isinstance(articles, list):
        return articles
    return []


def _fetch_fmp_profile(symbol: str) -> dict | None:
    from skills.financial_modeling_prep.scripts.api import fmp
    data = fmp(f"/profile/{symbol}")
    if isinstance(data, list) and data:
        return data[0]
    if isinstance(data, dict) and data.get("companyName"):
        return data
    return None


def _fetch_fmp_earnings(symbol: str) -> list[dict]:
    from skills.financial_modeling_prep.scripts.api import fmp
    data = fmp(f"/historical/earning_calendar/{symbol}", {"limit": 4})
    if isinstance(data, list):
        return data
    return []


def _fetch_fmp_price_targets(symbol: str) -> list[dict]:
    from skills.financial_modeling_prep.scripts.api import fmp
    data = fmp(f"/price-target/{symbol}")
    if isinstance(data, list):
        return data[:10]
    return []


async def seed_stock(symbol: str, days: int = 60) -> dict:
    """
    Seed the knowledge graph with FMP data for a stock.
    Fetches news, profile, earnings, and analyst targets, then stores them.
    Idempotent — skips if already seeded this server session.
    """
    symbol = symbol.upper().strip()

    if symbol in _seeded_tickers:
        return {"success": True, "status": "already_seeded", "ticker": symbol}

    if symbol not in _seeding_locks:
        _seeding_locks[symbol] = asyncio.Lock()

    async with _seeding_locks[symbol]:
        if symbol in _seeded_tickers:
            return {"success": True, "status": "already_seeded", "ticker": symbol}

        await _ensure_setup()
        logger.info(f"Seeding cognee knowledge graph for {symbol} ({days} days)")

        chunks = []

        profile = await asyncio.to_thread(_fetch_fmp_profile, symbol)
        if profile:
            chunks.append(
                f"{profile.get('companyName', symbol)} ({symbol}): "
                f"{profile.get('description', 'No description')} "
                f"Sector: {profile.get('sector', 'N/A')}. "
                f"Industry: {profile.get('industry', 'N/A')}. "
                f"CEO: {profile.get('ceo', 'N/A')}. "
                f"Market cap: ${profile.get('mktCap', 0):,.0f}."
            )

        news_articles = await asyncio.to_thread(_fetch_fmp_news, symbol, days)
        for article in news_articles:
            title = article.get("title", "")
            text = article.get("text", "")
            published = article.get("publishedDate", "")
            content = f"[{published[:10]}] {title}"
            if text:
                content += f"\n{text[:500]}"
            chunks.append(content)

        earnings = await asyncio.to_thread(_fetch_fmp_earnings, symbol)
        for e in earnings:
            eps_est = e.get("epsEstimated", "N/A")
            eps_act = e.get("eps", "N/A")
            rev_est = e.get("revenueEstimated", "N/A")
            rev_act = e.get("revenue", "N/A")
            d = e.get("date", "")
            chunks.append(
                f"[{d}] {symbol} earnings: EPS {eps_act} (est {eps_est}), "
                f"Revenue {rev_act} (est {rev_est})"
            )

        targets = await asyncio.to_thread(_fetch_fmp_price_targets, symbol)
        for t in targets:
            analyst = t.get("analystName", "Unknown")
            company = t.get("analystCompany", "")
            target = t.get("adjPriceTarget", t.get("priceTarget", "N/A"))
            action = t.get("newsTitle", "")
            d = t.get("publishedDate", "")[:10] if t.get("publishedDate") else ""
            chunks.append(
                f"[{d}] Analyst {analyst} ({company}): price target ${target}. {action}"
            )

        if not chunks:
            return {"success": True, "status": "no_data", "ticker": symbol}

        combined = "\n\n".join(chunks)
        result = await remember_stock(symbol, combined)

        if result.get("success"):
            _seeded_tickers.add(symbol)
            logger.info(f"Seeded {symbol}: {len(chunks)} chunks")

        return {**result, "chunks": len(chunks), "status": "seeded"}


# ---------------------------------------------------------------------------
# Post-chat memory processing
# ---------------------------------------------------------------------------

MEMORY_REWRITE_QUERY = """
Synthesize ALL accumulated knowledge about this user into a complete, structured memory document.
IMPORTANT: Preserve all previously learned information unless it is explicitly contradicted
by newer information. Older facts are valuable context and must be retained even if the
latest conversation doesn't mention them.

Organize under these headings (skip any with no data yet):

## Investment Style & Risk Profile
- Risk tolerance, time horizon, portfolio strategy (growth, value, income, etc.)
- Position sizing preferences, concentration vs diversification stance
- Tax awareness (e.g. harvesting behavior, wash sale sensitivity)

## Current Interests & Watchlist
- Specific stocks, ETFs, or assets they're tracking or considering
- Sectors and themes of interest (e.g. AI infrastructure, data centers, biotech)

## News & Macro Topics
- Market themes, macro trends, or events they're following
- Earnings seasons, Fed policy, geopolitical developments they've asked about

## Research & Analysis Preferences
- How they like to evaluate stocks (fundamental, technical, catalyst-driven, etc.)
- Preferred data sources, metrics, or frameworks (e.g. DCF, P/E ratios, backlog growth)
- Depth preference — quick takes vs deep dives

## Portfolio History & Decisions
- Past trades, buys, sells, and the reasoning behind them
- Outcomes and lessons learned from prior decisions

## Knowledge Level & Communication Style
- Financial literacy level (beginner, intermediate, advanced)
- How they prefer information delivered (bullet points, detailed analysis, comparisons)

Use bullet points. Be concise but comprehensive — err on the side of keeping information
rather than dropping it.
"""


async def process_chat_memory(user_id: str, chat_id: str) -> dict:
    """
    Post-chat hook: feed conversation to cognee, then recall ALL accumulated
    knowledge to rewrite MEMORY.md from scratch. Each version is a complete
    document, not an append.
    """
    await _ensure_setup()

    try:
        from core.database import get_db_session
        from crud import chat_async
        from models.chat_models import MemorySnapshot

        async with get_db_session() as db:
            messages = await chat_async.get_chat_messages(db, chat_id)

        if not messages or len(messages) < 2:
            return {"status": "skipped", "reason": "too_few_messages"}

        conversation = []
        for msg in messages:
            role = msg.role or "user"
            content = msg.content or ""
            if content and role in ("user", "assistant"):
                conversation.append(f"{role}: {content[:1000]}")

        if len(conversation) < 2:
            return {"status": "skipped", "reason": "no_content"}

        conversation_text = "\n".join(conversation[-20:])

        dataset = f"user_{user_id[:8]}_memory"
        await cognee.remember(
            conversation_text,
            dataset_name=dataset,
            self_improvement=False,
        )

        previous_memory = await _read_sandbox_memory(user_id)

        recall_query = MEMORY_REWRITE_QUERY
        if previous_memory:
            recall_query += (
                "\n\nThe user's CURRENT memory document is shown below. "
                "All information here should be preserved unless explicitly contradicted:\n\n"
                + previous_memory[:3000]
            )

        try:
            results = await cognee.recall(
                query_text=recall_query,
                datasets=[dataset],
                top_k=30,
            )
        except Exception as recall_err:
            logger.warning(f"Recall with dataset filter failed, retrying without: {recall_err}")
            results = await cognee.recall(
                query_text=recall_query,
                top_k=30,
            )

        if not results:
            if previous_memory:
                return {"status": "kept_existing", "reason": "no_recall_results"}
            return {"status": "skipped", "reason": "no_recall_results"}

        sections = []
        for r in results:
            if isinstance(r, dict):
                text = r.get("search_result", r.get("text", ""))
                if isinstance(text, list):
                    text = " ".join(str(t) for t in text)
            else:
                text = str(r)
            if text:
                sections.append(text[:500])

        if not sections:
            if previous_memory:
                return {"status": "kept_existing", "reason": "empty_results"}
            return {"status": "skipped", "reason": "empty_results"}

        new_memory = f"# MEMORY.md\n\n"
        new_memory += f"*Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M')} (powered by Cognee)*\n\n"
        for s in sections:
            new_memory += f"{s}\n\n"

        await _write_sandbox_memory(user_id, new_memory)

        async with get_db_session() as db:
            snapshot = MemorySnapshot(
                id=uuid.uuid4(),
                user_id=user_id,
                chat_id=chat_id,
                content=new_memory,
                diff=f"Rewritten from {len(sections)} knowledge fragments after chat {chat_id[:8]}",
                source="cognee",
            )
            db.add(snapshot)
            await db.commit()

        logger.info(f"Rewrote MEMORY.md for user {user_id} from chat {chat_id[:8]} ({len(sections)} sections)")
        return {"status": "rewritten", "sections": len(sections)}

    except Exception as e:
        logger.error(f"Post-chat memory processing failed: {e}")
        return {"status": "error", "error": str(e)}


async def _read_sandbox_memory(user_id: str) -> str:
    """Read current MEMORY.md from user's sandbox."""
    try:
        from modules.tools.implementations.code_execution import _get_or_reconnect_sandbox
        sbx = await _get_or_reconnect_sandbox(user_id)
        if sbx:
            content = await sbx.files.read("/home/user/MEMORY.md", format="text")
            return content or ""
    except Exception:
        pass
    return ""


async def _write_sandbox_memory(user_id: str, content: str) -> bool:
    """Write updated MEMORY.md to user's sandbox."""
    try:
        from modules.tools.implementations.code_execution import _get_or_reconnect_sandbox
        sbx = await _get_or_reconnect_sandbox(user_id)
        if sbx:
            await sbx.files.write("/home/user/MEMORY.md", content)
            return True
    except Exception as e:
        logger.warning(f"Failed to write MEMORY.md to sandbox: {e}")
    return False


async def get_memory_history(user_id: str, limit: int = 20) -> list[dict]:
    """Get memory snapshot history for a user."""
    from core.database import get_db_session
    from models.chat_models import MemorySnapshot
    from sqlalchemy import select

    async with get_db_session() as db:
        result = await db.execute(
            select(MemorySnapshot)
            .where(MemorySnapshot.user_id == user_id)
            .order_by(MemorySnapshot.created_at.desc())
            .limit(limit)
        )
        snapshots = result.scalars().all()
        return [
            {
                "id": str(s.id),
                "chat_id": s.chat_id,
                "content": s.content,
                "diff": s.diff,
                "source": s.source,
                "created_at": s.created_at.isoformat() if s.created_at else None,
            }
            for s in snapshots
        ]


async def get_current_memory(user_id: str) -> str:
    """Get the current MEMORY.md content."""
    content = await _read_sandbox_memory(user_id)
    if content:
        return content

    from core.database import get_db_session
    from models.chat_models import MemorySnapshot
    from sqlalchemy import select

    async with get_db_session() as db:
        result = await db.execute(
            select(MemorySnapshot)
            .where(MemorySnapshot.user_id == user_id)
            .order_by(MemorySnapshot.created_at.desc())
            .limit(1)
        )
        latest = result.scalar_one_or_none()
        return latest.content if latest else ""
