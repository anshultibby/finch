"""
Store Sync — reads store/ files from the E2B sandbox and syncs them to the
store_files DB table so the frontend Memory Store panel can display them.
"""
import logging

logger = logging.getLogger(__name__)


async def sync_store_files(user_id: str) -> int:
    """Walk /home/user/store/ in the sandbox and upsert each file to store_files.
    Returns the number of files synced."""
    from modules.tools.implementations.code_execution import _get_or_reconnect_sandbox
    from core.database import get_db_session
    from crud.store import upsert_store_file

    sbx = await _get_or_reconnect_sandbox(user_id)
    if not sbx:
        logger.debug(f"No sandbox for user {user_id}, skipping store sync")
        return 0

    try:
        result = await sbx.commands.run(
            "find /home/user/store -type f \\( -name '*.md' -o -name '*.py' -o -name '*.txt' \\) 2>/dev/null",
            timeout=10,
        )
        if result.exit_code != 0 or not result.stdout:
            return 0

        paths = [p.strip() for p in result.stdout.strip().split("\n") if p.strip()]
        if not paths:
            return 0

        synced = 0
        async with get_db_session() as db:
            for abs_path in paths:
                try:
                    content = await sbx.files.read(abs_path, format="text")
                    if content is None:
                        continue
                    rel = abs_path.replace("/home/user/", "")
                    await upsert_store_file(db, user_id, rel, content=content)
                    synced += 1
                except Exception as e:
                    logger.debug(f"Failed to sync {abs_path}: {e}")

        logger.info(f"Synced {synced} store files for user {user_id}")
        return synced

    except Exception as e:
        logger.warning(f"Store sync failed for user {user_id}: {e}")
        return 0
