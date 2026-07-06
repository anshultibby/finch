"""
One-off backfill: regenerate titles for chats stuck with the literal "New Chat"
sentinel (a bug in services/chat_title.py used to persist that string whenever
title generation failed, instead of leaving the title unset). Also backfills
chats with a NULL title that already have messages.

Usage:
    python -m scripts.backfill_chat_titles [--dry-run] [--limit N]
"""
import argparse
import asyncio

from sqlalchemy import select, or_

from core.database import get_db_session
from models.chat_models import Chat
from crud import chat_async
from services.chat_title import generate_chat_title, TitleGenerationError


def _fallback_title(first_message: str) -> str:
    text = first_message.strip().replace("\n", " ")
    return (text[:50] + "...") if len(text) > 50 else text


async def backfill(dry_run: bool, limit: int) -> None:
    async with get_db_session() as db:
        result = await db.execute(
            select(Chat).where(or_(Chat.title == "New Chat", Chat.title.is_(None))).limit(limit)
        )
        chats = list(result.scalars().all())

    print(f"Found {len(chats)} chat(s) to backfill")

    fixed, skipped = 0, 0
    for chat in chats:
        async with get_db_session() as db:
            messages = await chat_async.get_chat_messages(db, chat.chat_id)
        first_user_message = next((m.content for m in messages if m.role == "user" and m.content), None)
        if not first_user_message:
            skipped += 1
            continue

        try:
            title, icon = await generate_chat_title(first_user_message)
        except TitleGenerationError as e:
            title, icon = _fallback_title(first_user_message), "💬"
            print(f"  {chat.chat_id}: generation failed ({e}), using fallback {title!r}")
        else:
            print(f"  {chat.chat_id}: {icon} {title}")

        if not dry_run:
            async with get_db_session() as db:
                await chat_async.update_chat_title(db, chat.chat_id, title, icon)
        fixed += 1

    print(f"Done. Fixed {fixed}, skipped {skipped} (no messages){' [dry-run, no writes]' if dry_run else ''}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Preview without writing to the DB")
    parser.add_argument("--limit", type=int, default=1000, help="Max chats to process")
    args = parser.parse_args()
    asyncio.run(backfill(args.dry_run, args.limit))


if __name__ == "__main__":
    main()
