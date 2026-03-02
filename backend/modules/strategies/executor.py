"""
Strategy Executor — runs a strategy tick via the user's persistent E2B sandbox.

Flow:
  1. Load strategy files from strategy_files table
  2. Get (or create/reconnect) the user's persistent sandbox
  3. Upload strategy_runner.py (once per sandbox lifetime, alongside skills)
  4. Upload strategy files to /home/user/strategies/<strategy_id>/
  5. Run: python /home/user/strategy_runner.py
     with strategy config injected as env vars
  6. Parse JSON output from stdout
  7. Write StrategyExecution audit record
"""
import asyncio
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from models.db import Strategy, StrategyExecution
from models.strategies import ExecutionAction
from crud.strategies import (
    load_strategy_files,
    create_execution,
    complete_execution,
)

logger = logging.getLogger(__name__)

EXECUTION_TIMEOUT_SECONDS = 120

# Path to the runner script on the host
_RUNNER_PATH = Path(__file__).parent.parent.parent / "sandbox_runner" / "strategy_runner.py"
_SANDBOX_RUNNER_PATH = "/home/user/strategy_runner.py"
_SANDBOX_STRATEGIES_DIR = "/home/user/strategies"


async def execute_strategy(
    db: AsyncSession,
    strategy: Strategy,
    trigger: str = "manual",
    dry_run: bool = True,
) -> StrategyExecution:
    """
    Execute a strategy in the user's E2B sandbox.

    Args:
        db: Database session
        strategy: Strategy to execute
        trigger: 'scheduled', 'manual', or 'dry_run'
        dry_run: If True, no real orders are placed

    Returns:
        StrategyExecution record with results
    """
    execution = await create_execution(db, strategy, trigger)

    try:
        files = await load_strategy_files(db, strategy)
    except Exception as e:
        logger.error(f"Failed to load strategy files for {strategy.id}: {e}")
        return await complete_execution(
            db, execution,
            status="failed",
            error=f"Failed to load strategy files: {e}",
            summary="Strategy execution failed: could not load files",
        )

    config = strategy.config or {}

    try:
        result = await asyncio.wait_for(
            _run_in_sandbox(strategy, config, files, dry_run),
            timeout=EXECUTION_TIMEOUT_SECONDS,
        )
    except asyncio.TimeoutError:
        msg = f"Strategy timed out after {EXECUTION_TIMEOUT_SECONDS}s"
        logger.error(f"Strategy {strategy.id} timed out")
        return await complete_execution(
            db, execution,
            status="failed",
            error=msg,
            summary="Strategy execution timed out",
        )
    except Exception as e:
        logger.exception(f"Strategy {strategy.id} failed: {e}")
        return await complete_execution(
            db, execution,
            status="failed",
            error=str(e),
            summary=f"Strategy failed: {str(e)[:100]}",
        )

    status = "success" if result.get("status") == "success" else "failed"
    actions = [
        ExecutionAction(
            type=a["type"],
            timestamp=datetime.fromisoformat(a["timestamp"]),
            dry_run=a.get("dry_run", dry_run),
            details=a.get("details", {}),
        )
        for a in result.get("actions", [])
    ]

    return await complete_execution(
        db, execution,
        status=status,
        summary=result.get("summary"),
        error=result.get("error"),
        actions=actions,
        logs=result.get("logs", []),
    )


async def _run_in_sandbox(
    strategy: Strategy,
    config: dict,
    files: dict[str, str],
    dry_run: bool,
) -> dict:
    """
    Upload strategy files to the user's sandbox and run the runner.
    Returns the parsed JSON output from the runner.
    """
    from modules.tools.implementations.code_execution import (
        get_or_create_sandbox,
        _compute_skills_hash_from_fs,
        _upload_skills,
        _upload_api_docs,
        _upload_finch_runtime,
        _install_skill_packages,
        _upsert_user_sandbox,
        _sandboxes,
    )

    envs = await _build_strategy_env(strategy, config, dry_run)

    entry = await get_or_create_sandbox(strategy.user_id, envs)
    sbx = entry.sbx

    # Ensure skills + runner are loaded (reuse the same flag as chat execution)
    current_hash = _compute_skills_hash_from_fs()
    needs_upload = not entry.skills_loaded or entry.skills_hash != current_hash
    if needs_upload:
        new_hash, _, _ = await asyncio.gather(
            _upload_skills(sbx),
            _upload_api_docs(sbx),
            _upload_finch_runtime(sbx),
        )
        await _install_skill_packages(sbx)
        entry.skills_loaded = True
        entry.skills_hash = new_hash
        await _upsert_user_sandbox(strategy.user_id, sbx.sandbox_id, skills_loaded=True, skills_hash=new_hash)

    # Upload strategy_runner.py once (idempotent)
    await _ensure_runner_uploaded(sbx, entry)

    # Upload strategy files to /home/user/strategies/<strategy_id>/
    strategy_dir = f"{_SANDBOX_STRATEGIES_DIR}/{strategy.id}"
    await asyncio.gather(*[
        sbx.files.write(f"{strategy_dir}/{filename}", content)
        for filename, content in files.items()
    ])
    logger.info(f"Uploaded {len(files)} file(s) to {strategy_dir}")

    # Run the strategy runner
    cmd = f"python {_SANDBOX_RUNNER_PATH}"
    try:
        result = await sbx.commands.run(cmd, envs=envs, timeout=EXECUTION_TIMEOUT_SECONDS)
    except Exception as e:
        raise RuntimeError(f"Sandbox command failed: {e}")

    stdout = result.stdout or ""
    stderr = result.stderr or ""

    if stderr:
        logger.debug(f"Strategy runner stderr (strategy {strategy.id}):\n{stderr}")

    if result.exit_code != 0 and not stdout.strip():
        raise RuntimeError(
            f"Strategy runner exited with code {result.exit_code}. stderr: {stderr[:500]}"
        )

    # Parse JSON from stdout
    try:
        # Runner may emit non-JSON lines from print() — find the last JSON blob
        for line in reversed(stdout.strip().splitlines()):
            line = line.strip()
            if line.startswith("{"):
                return json.loads(line)
        raise ValueError("No JSON output found in runner stdout")
    except (json.JSONDecodeError, ValueError) as e:
        raise RuntimeError(f"Could not parse runner output: {e}. stdout: {stdout[:500]}")


async def _ensure_runner_uploaded(sbx, entry) -> None:
    """Upload strategy_runner.py to the sandbox (once per skills upload cycle)."""
    if not _RUNNER_PATH.exists():
        raise FileNotFoundError(f"strategy_runner.py not found at {_RUNNER_PATH}")

    content = _RUNNER_PATH.read_text()
    await sbx.files.write(_SANDBOX_RUNNER_PATH, content)
    logger.debug("Uploaded strategy_runner.py to sandbox")


async def _build_strategy_env(
    strategy: Strategy,
    config: dict,
    dry_run: bool,
) -> dict[str, str]:
    """Build env vars to inject into the sandbox for a strategy run."""
    from services.api_keys import ApiKeyService
    from modules.tools.skills_registry import SKILL_ENV_KEYS
    from database import get_db_session
    from modules.tools.implementations.code_execution import SKILLS_DIR

    risk_limits = config.get("risk_limits", {})
    platform = config.get("platform", "kalshi")

    env: dict[str, str] = {
        "FINCH_STRATEGY_ID": strategy.id,
        "FINCH_USER_ID": strategy.user_id,
        "FINCH_EXECUTION_ID": "",  # populated after execution record is created
        "FINCH_DRY_RUN": "true" if dry_run else "false",
        "FINCH_PLATFORM": platform,
        "FINCH_MAX_ORDER_USD": str(risk_limits.get("max_order_usd") or ""),
        "FINCH_MAX_DAILY_USD": str(risk_limits.get("max_daily_usd") or ""),
        "PYTHONWARNINGS": "ignore",
        "LOG_LEVEL": "ERROR",
        "PYTHONPATH": f"{SKILLS_DIR}:/home/user",
    }

    async with get_db_session() as db:
        svc = ApiKeyService(db, strategy.user_id)

        # System-owned env vars
        for env_var, (_, owner) in SKILL_ENV_KEYS.items():
            if owner != "system":
                continue
            key = svc.get_env_var(env_var)
            if key and key.get():
                env[env_var] = key.get()

        # User Kalshi credentials
        kalshi = await svc.get_kalshi_credentials()
        if kalshi:
            env["KALSHI_API_KEY_ID"] = kalshi["api_key_id"].get()
            env["KALSHI_PRIVATE_KEY"] = kalshi["private_key"].get()

    return env
