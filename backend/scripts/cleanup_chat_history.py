import argparse
import asyncio

from crud import chat_async


async def cleanup_chat(chat_id: str) -> int:
    from database import get_db_session
    async with get_db_session() as db:
        removed = await chat_async.cleanup_incomplete_tool_sequences(db, chat_id)
        return removed


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--chat-id", required=True)
    args = parser.parse_args()
    removed = asyncio.run(cleanup_chat(args.chat_id))
    print(f"Removed {removed} message(s)")


if __name__ == "__main__":
    main()
