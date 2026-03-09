"""
Helper script to update a strategy's code file in the DB directly.

Usage:
    cd backend
    python sandbox/update_strategy.py <strategy_id> <filename> <code_file>

Example:
    python sandbox/update_strategy.py 06bcf846-... strategy.py /tmp/new_strategy.py
"""
import asyncio
import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

_env_file = Path(__file__).parent.parent / ".env"
if _env_file.exists():
    for _line in _env_file.read_text().splitlines():
        _line = _line.strip()
        if _line and not _line.startswith("#") and "=" in _line:
            k, _, v = _line.partition("=")
            os.environ.setdefault(k.strip(), v.strip())


async def main(strategy_id: str, filename: str, code_file: str):
    content = Path(code_file).read_text()
    from database import get_db_session
    from sqlalchemy import text
    async with get_db_session() as db:
        result = await db.execute(
            text("UPDATE strategy_files SET content = :c WHERE strategy_id = :s AND filename = :f"),
            {"c": content, "s": strategy_id, "f": filename},
        )
        await db.commit()
        print(f"Updated {filename} for strategy {strategy_id} ({result.rowcount} row(s) affected)")


if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Usage: python sandbox/update_strategy.py <strategy_id> <filename> <code_file>")
        sys.exit(1)
    asyncio.run(main(sys.argv[1], sys.argv[2], sys.argv[3]))
