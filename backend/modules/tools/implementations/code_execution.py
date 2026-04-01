"""
Code Execution Implementation with Persistent Per-User E2B Sandbox

One sandbox persists per user (not per-chat), surviving server restarts:
- Created with auto-pause enabled; E2B pauses it automatically on timeout
- sandbox_id stored in DB so it can be reconnected after server restarts
- Skills are loaded from backend/skills/ onto the sandbox volume ONCE and stay there
- Skills are read directly from the filesystem — no DB round-trips
- Chat files synced back to DB after each run for UI visibility
- API keys re-injected on reconnect since env vars don't survive pause/resume
- Clearing a chat does NOT destroy the sandbox; reset_sandbox does
"""
from e2b.sandbox.commands.command_handle import CommandExitException
from modules.agent.context import AgentContext
from schemas.sse import SSEEvent
from typing import Optional, Dict, Any, AsyncGenerator, List
from pydantic import BaseModel, Field
from utils.logger import get_logger
import os
import hashlib
import json
import time
import asyncio
from datetime import datetime
from pathlib import Path

logger = get_logger(__name__)

WORKSPACE_DIR = "/home/user"
SKILLS_DIR = f"{WORKSPACE_DIR}/skills"
APIS_DIR = f"{WORKSPACE_DIR}/apis"
EXECUTION_TIMEOUT = 60       # seconds — max runtime per execution
SANDBOX_IDLE_TIMEOUT = 600   # seconds — sandbox auto-pauses after this idle time

# Absolute path to the skills directory on the host (sibling of this file's package root)
_HOST_SKILLS_DIR = Path(__file__).parent.parent.parent.parent / "skills"


# ---------------------------------------------------------------------------
# In-process sandbox cache (user_id → live sandbox + state)
# ---------------------------------------------------------------------------

class _SandboxEntry:
    """Holds a live (running) sandbox and tracks state."""

    def __init__(self, sbx, skills_loaded: bool, envs: Dict[str, str], skills_hash: str = ""):
        self.sbx = sbx
        self.skills_loaded: bool = skills_loaded
        self.skills_hash: str = skills_hash
        self.envs: Dict[str, str] = envs


# user_id → _SandboxEntry  (in-process cache; rebuilt from DB on server restart)
_sandboxes: Dict[str, _SandboxEntry] = {}
_sandboxes_lock = asyncio.Lock()


# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------

async def _get_user_sandbox_record(user_id: str):
    """Return the UserSandbox DB row for this user, or None."""
    from core.database import get_db_session
    from models.user import UserSandbox
    from sqlalchemy import select

    async with get_db_session() as db:
        result = await db.execute(
            select(UserSandbox).where(UserSandbox.user_id == user_id)
        )
        return result.scalar_one_or_none()


async def _upsert_user_sandbox(user_id: str, sandbox_id: str, skills_loaded: bool, skills_hash: str = None) -> None:
    """Persist or update the UserSandbox record."""
    from core.database import get_db_session
    from models.user import UserSandbox
    from sqlalchemy import select

    async with get_db_session() as db:
        result = await db.execute(
            select(UserSandbox).where(UserSandbox.user_id == user_id)
        )
        record = result.scalar_one_or_none()
        if record:
            record.sandbox_id = sandbox_id
            record.skills_loaded = skills_loaded
            if skills_hash is not None:
                record.skills_hash = skills_hash
        else:
            db.add(UserSandbox(
                user_id=user_id,
                sandbox_id=sandbox_id,
                skills_loaded=skills_loaded,
                skills_hash=skills_hash,
            ))
        await db.commit()


async def _delete_user_sandbox_record(user_id: str) -> None:
    """Remove the UserSandbox record (called on hard reset)."""
    from core.database import get_db_session
    from models.user import UserSandbox
    from sqlalchemy import select

    async with get_db_session() as db:
        result = await db.execute(
            select(UserSandbox).where(UserSandbox.user_id == user_id)
        )
        record = result.scalar_one_or_none()
        if record:
            await db.delete(record)
            await db.commit()


# ---------------------------------------------------------------------------
# Sandbox lifecycle
# ---------------------------------------------------------------------------

async def get_or_create_sandbox(user_id: str, envs: Dict[str, str]) -> _SandboxEntry:
    """
    Return a fully-ready sandbox for this user — connected, skills uploaded,
    packages installed.

    Resolution order:
    1. In-process cache hit → renew timeout, refresh envs, check hash.
    2. DB record exists → reconnect via AsyncSandbox.connect(); check hash.
    3. No record / dead sandbox → create new sandbox, upload everything.

    The skills hash covers skill files and (when no template is set) the pip
    package list. Any change triggers a full re-upload automatically.
    """
    from e2b_code_interpreter import AsyncSandbox
    from core.config import Config

    async with _sandboxes_lock:
        # --- 1. In-process cache ---
        entry = _sandboxes.get(user_id)
        if entry is not None:
            try:
                await entry.sbx.set_timeout(SANDBOX_IDLE_TIMEOUT)
                entry.envs = envs
                logger.info(f"Reusing in-process sandbox {entry.sbx.sandbox_id} for user {user_id}")
            except Exception as e:
                logger.warning(f"In-process sandbox for user {user_id} is dead ({e}), reconnecting")
                _sandboxes.pop(user_id, None)
                entry = None

        # --- 2. Try reconnecting from DB ---
        if entry is None:
            record = await _get_user_sandbox_record(user_id)
            if record:
                try:
                    sbx = await AsyncSandbox.connect(
                        record.sandbox_id,
                        api_key=Config.E2B_API_KEY,
                        timeout=SANDBOX_IDLE_TIMEOUT,
                    )
                    entry = _SandboxEntry(
                        sbx=sbx,
                        skills_loaded=record.skills_loaded,
                        skills_hash=record.skills_hash or "",
                        envs=envs,
                    )
                    _sandboxes[user_id] = entry
                    logger.info(
                        f"Reconnected to sandbox {sbx.sandbox_id} for user {user_id} "
                        f"(skills_loaded={record.skills_loaded}, hash={record.skills_hash})"
                    )
                except Exception as e:
                    logger.warning(
                        f"Failed to reconnect to sandbox {record.sandbox_id} for user {user_id} ({e}), "
                        "creating new sandbox"
                    )
                    await _delete_user_sandbox_record(user_id)

        # --- 3. Create new sandbox ---
        if entry is None:
            sbx = await AsyncSandbox.beta_create(
                **({"template": Config.E2B_TEMPLATE_ID} if Config.E2B_TEMPLATE_ID else {}),
                api_key=Config.E2B_API_KEY,
                timeout=SANDBOX_IDLE_TIMEOUT,
                auto_pause=True,
                envs=envs,
            )
            entry = _SandboxEntry(sbx=sbx, skills_loaded=False, envs=envs)
            _sandboxes[user_id] = entry
            await _upsert_user_sandbox(user_id, sbx.sandbox_id, skills_loaded=False)
            logger.info(f"Created new persistent sandbox {sbx.sandbox_id} for user {user_id}")

        # --- 4. Upload skills + runner files if hash has changed ---
        current_hash = _compute_skills_hash_from_fs()
        if not entry.skills_loaded or entry.skills_hash != current_hash:
            logger.info(f"Uploading skills to sandbox {entry.sbx.sandbox_id} (hash changed or first load)")
            new_hash, _, _ = await asyncio.gather(
                _upload_skills(entry.sbx),
                _upload_api_docs(entry.sbx),
                _upload_finch_runtime(entry.sbx),
            )
            await _install_skill_packages(entry.sbx)
            entry.skills_loaded = True
            entry.skills_hash = new_hash
            await _upsert_user_sandbox(user_id, entry.sbx.sandbox_id, skills_loaded=True, skills_hash=new_hash)

        return entry


async def _get_or_reconnect_sandbox(user_id: str):
    """
    Return a live sandbox for file access, reconnecting from DB if not in cache.
    Lighter than get_or_create_sandbox — does not build envs or create new sandboxes.
    Returns None if no sandbox record exists or reconnect fails.
    """
    from e2b_code_interpreter import AsyncSandbox
    from core.config import Config

    entry = _sandboxes.get(user_id)
    if entry:
        return entry.sbx

    record = await _get_user_sandbox_record(user_id)
    if not record:
        return None
    try:
        sbx = await AsyncSandbox.connect(
            record.sandbox_id,
            api_key=Config.E2B_API_KEY,
            timeout=SANDBOX_IDLE_TIMEOUT,
        )
        entry = _SandboxEntry(sbx=sbx, skills_loaded=record.skills_loaded,
                              skills_hash=record.skills_hash or "", envs={})
        _sandboxes[user_id] = entry
        logger.info(f"Reconnected sandbox {sbx.sandbox_id} for file access (user {user_id})")
        return sbx
    except Exception as e:
        logger.warning(f"Could not reconnect sandbox for user {user_id}: {e}")
        return None


async def read_sandbox_file(user_id: str, path: str) -> Optional[bytes]:
    """
    Read a file directly from the user's sandbox volume (reconnecting if paused).
    Returns raw bytes, or None if the sandbox doesn't exist or the file isn't found.
    path may be absolute (/home/user/...) or relative to WORKSPACE_DIR.
    """
    sbx = await _get_or_reconnect_sandbox(user_id)
    if not sbx:
        return None
    abs_path = path if path.startswith("/") else f"{WORKSPACE_DIR}/{path}"
    try:
        raw = await sbx.files.read(abs_path, format="bytes")
        return bytes(raw)
    except Exception:
        try:
            text = await sbx.files.read(abs_path, format="text")
            return text.encode("utf-8")
        except Exception:
            return None


async def reset_sandbox(user_id: str) -> None:
    """
    Hard-reset a user's sandbox: kill the running instance, delete the DB
    record, and evict from cache. The next execution will create a fresh
    sandbox and re-load skills onto it.
    """
    async with _sandboxes_lock:
        entry = _sandboxes.pop(user_id, None)

    if entry:
        try:
            await entry.sbx.kill()
            logger.info(f"Killed sandbox {entry.sbx.sandbox_id} for user {user_id}")
        except Exception as e:
            logger.warning(f"Failed to kill sandbox for user {user_id}: {e}")

    await _delete_user_sandbox_record(user_id)
    logger.info(f"Reset persistent sandbox for user {user_id}")


# ---------------------------------------------------------------------------
# Legacy shim — called by routes/chat.py on chat clear.
# We no longer destroy the sandbox on chat clear; the volume persists.
# ---------------------------------------------------------------------------

async def kill_sandbox(chat_id: str) -> None:
    """
    Backward-compatible shim. Chat clears no longer destroy the user sandbox
    (skills on the volume would be lost). This is now a no-op; use
    reset_sandbox(user_id) for a hard reset.
    """
    logger.info(f"kill_sandbox({chat_id}) called — sandbox preserved (skills volume intact)")


# ---------------------------------------------------------------------------
# File upload helpers
# ---------------------------------------------------------------------------

def _compute_skills_hash_from_fs() -> str:
    """
    MD5 over all files that get uploaded to the sandbox:
    - backend/skills/** (skill code + SKILL.md files)

    When no E2B template is configured, also includes the sorted package list
    so that adding/removing a `requires.bins` entry triggers a re-install.

    When a template is configured, packages are baked into the image and
    excluded from the hash.

    Any change to any of these files invalidates the hash and triggers a full
    re-upload on the next sandbox run.
    """
    from core.config import Config

    h = hashlib.md5()

    # Skills files
    if _HOST_SKILLS_DIR.exists():
        for path in sorted(_HOST_SKILLS_DIR.rglob("*")):
            if path.is_file() and "__pycache__" not in path.parts:
                h.update(str(path.relative_to(_HOST_SKILLS_DIR)).encode())
                h.update(path.read_bytes())

    if not Config.E2B_TEMPLATE_ID:
        from modules.tools.skills_registry import get_all_skill_packages
        packages = sorted(get_all_skill_packages())
        h.update(("\n".join(packages)).encode())

    return h.hexdigest()


async def _upload_skills(sbx) -> str:
    """
    Upload all skill directories from backend/skills/ to /home/user/skills/
    on the sandbox volume. Reads directly from the filesystem — no DB needed.
    Returns a hash of the uploaded content so callers can detect future changes.
    """
    try:
        if not _HOST_SKILLS_DIR.exists():
            logger.warning(f"Skills directory not found at {_HOST_SKILLS_DIR}")
            return ""

        skill_dirs = [p for p in _HOST_SKILLS_DIR.iterdir() if p.is_dir()]
        if not skill_dirs:
            logger.warning(f"No skill subdirectories found in {_HOST_SKILLS_DIR}")
            return ""

        upload_tasks = []
        total_files = 0

        for skill_dir in skill_dirs:
            for file_path in skill_dir.rglob("*"):
                if not file_path.is_file():
                    continue
                if "__pycache__" in file_path.parts:
                    continue
                rel = file_path.relative_to(_HOST_SKILLS_DIR)
                sandbox_path = f"{SKILLS_DIR}/{rel}"
                try:
                    content = file_path.read_bytes()
                    upload_tasks.append((sandbox_path, content))
                    total_files += 1
                except Exception as e:
                    logger.warning(f"Could not read skill file {file_path}: {e}")

        # Nuke stale skills dir (could have files where dirs should be)
        # and pre-create all subdirectories so parallel writes don't race on mkdir
        subdirs = sorted({os.path.dirname(p) for p, _ in upload_tasks})
        mkdir_cmd = f"rm -rf {SKILLS_DIR} && " + " && ".join(
            f"mkdir -p {d}" for d in subdirs
        )
        try:
            await sbx.commands.run(mkdir_cmd, timeout=10)
        except Exception:
            pass

        # Upload files in small batches to avoid E2B timeouts
        BATCH_SIZE = 5
        for i in range(0, len(upload_tasks), BATCH_SIZE):
            batch = upload_tasks[i:i + BATCH_SIZE]
            await asyncio.gather(*[
                sbx.files.write(path, content, request_timeout=60)
                for path, content in batch
            ])

        logger.info(f"Uploaded {len(skill_dirs)} skills ({total_files} files) from {_HOST_SKILLS_DIR}")
        return _compute_skills_hash_from_fs()
    except Exception as e:
        logger.warning(f"Failed to upload system skills: {e}", exc_info=True)
        return ""


async def _install_skill_packages(sbx) -> None:
    """
    Pre-install pip packages declared in skills' SKILL.md `requires.bins` lists.

    Skipped when E2B_TEMPLATE_ID is configured — in that case packages are
    baked into the template image and are always present from the start.

    When no template is set (local dev / fallback), installs at runtime and
    raises RuntimeError on failure so the caller never marks skills_loaded=True
    with missing packages.
    """
    from core.config import Config
    from modules.tools.skills_registry import get_all_skill_packages

    if Config.E2B_TEMPLATE_ID:
        logger.debug("Skipping pip install — packages are baked into the E2B template")
        return

    packages = get_all_skill_packages()
    if not packages:
        return

    pkg_str = " ".join(sorted(packages))
    logger.info(f"Installing skill packages (no template set): {pkg_str}")
    result = await sbx.commands.run(
        f"pip install -q {pkg_str}",
        timeout=120,
    )
    if result.exit_code != 0:
        error_detail = (result.stderr or result.stdout or "(no output)").strip()
        raise RuntimeError(
            f"pip install failed (exit {result.exit_code}) for packages [{pkg_str}]:\n{error_detail}"
        )
    logger.info(f"Installed skill packages: {pkg_str}")


async def _upload_api_docs(sbx) -> None:
    """Write API documentation into the sandbox at /home/user/apis/."""
    try:
        from modules.tools.registry import tool_registry

        api_tools = tool_registry.get_api_docs_only_tools()
        if not api_tools:
            return

        for tool in api_tools:
            properties = tool.parameters_schema.get("properties", {})
            required = tool.parameters_schema.get("required", [])

            lines = [f"# {tool.name}", "", tool.description, "", "## Parameters", ""]
            for param_name, param_schema in properties.items():
                is_required = param_name in required
                param_type = param_schema.get("type", "any")
                param_desc = param_schema.get("description", "")
                req_marker = " (required)" if is_required else " (optional)"
                lines.append(f"### `{param_name}` - {param_type}{req_marker}")
                if param_desc:
                    lines.append(param_desc)
                lines.append("")

            await sbx.files.write(f"{APIS_DIR}/{tool.name}.md", "\n".join(lines))

        logger.info(f"Uploaded {len(api_tools)} API docs to sandbox")
    except Exception as e:
        logger.warning(f"Failed to upload API docs: {e}")


async def _upload_finch_runtime(sbx) -> None:
    """Write finch_runtime.py into the sandbox."""
    try:
        tools_dir = os.path.join(os.path.dirname(__file__), '..')
        finch_runtime_path = os.path.join(tools_dir, 'finch_runtime.py')

        if os.path.exists(finch_runtime_path):
            with open(finch_runtime_path, 'r') as f:
                content = f.read()
            await sbx.files.write(f"{WORKSPACE_DIR}/finch_runtime.py", content)
            logger.info("Uploaded finch_runtime.py to sandbox")
    except Exception as e:
        logger.warning(f"Failed to upload finch_runtime.py: {e}")


# ---------------------------------------------------------------------------
# Debug logging
# ---------------------------------------------------------------------------

def _save_code_execution_log(user_id: str, chat_id: str, execution_data: Dict[str, Any]):
    from core.config import Config
    from modules.agent.chat_logger import get_chat_log_dir

    if not Config.DEBUG_CHAT_LOGS:
        return

    try:
        backend_dir = Path(__file__).parent.parent.parent.parent
        chat_log_dir = get_chat_log_dir(chat_id, backend_dir)
        code_log_dir = chat_log_dir / "code_executions"
        code_log_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        exec_filename = execution_data.get("execution_filename", "script")
        safe_exec_filename = exec_filename.replace("/", "_").replace("\\", "_").replace(".py", "")
        log_filepath = code_log_dir / f"{timestamp}_{safe_exec_filename}.json"

        with open(log_filepath, "w") as f:
            json.dump(execution_data, f, indent=2)

        logger.info(f"Saved code execution log to: {log_filepath}")
    except Exception as e:
        logger.error(f"Failed to save code execution log: {e}", exc_info=True)


# ---------------------------------------------------------------------------
# Tool parameters
# ---------------------------------------------------------------------------

class BashParams(BaseModel):
    """Run a bash command in the persistent sandbox."""
    cmd: str = Field(
        description="Bash command or script to run. The sandbox is a full Linux environment — use python3, pip, curl, cat, tee, heredoc, etc."
    )


async def _build_sandbox_env(context: AgentContext) -> Dict[str, str]:
    """
    Build the environment dict for the sandbox.

    Iterates over SKILL_ENV_KEYS (the registry of all env vars required by skills)
    and injects each one:
    - "system" vars: fetched from global config via ApiKeyService.get_env_var()
    - "user" vars: fetched per-user from DB (currently only Kalshi credentials)

    API keys are injected directly as env vars. The agent is instructed
    never to print or log key values.
    """
    from services.api_keys import ApiKeyService
    from modules.tools.skills_registry import SKILL_ENV_KEYS
    from core.database import get_db_session

    bot_dir = (context.data or {}).get("bot_directory", "")

    env: Dict[str, str] = {
        "FINCH_USER_ID": context.user_id or "",
        "FINCH_CHAT_ID": context.chat_id or "",
        "FINCH_BOT_DIR": f"/home/user/{bot_dir}" if bot_dir else "",
        "PYTHONWARNINGS": "ignore",
        "LOG_LEVEL": "ERROR",
        "CODE_SANDBOX": "true",
        "PYTHONPATH": f"{SKILLS_DIR}:{WORKSPACE_DIR}",
    }

    async with get_db_session() as db:
        svc = ApiKeyService(db, context.user_id)

        # System-owned keys — same value for all users, from global config / .env
        for env_var, (_, owner) in SKILL_ENV_KEYS.items():
            if owner != "system":
                continue
            key = svc.get_env_var(env_var)
            if key and key.get():
                env[env_var] = key.get()

        # User-owned keys — fetched per-user from DB
        # Currently only Kalshi; add new user-key services here as needed.
        kalshi = await svc.get_kalshi_credentials()
        if kalshi:
            import base64
            env["KALSHI_API_KEY_ID"] = kalshi["api_key_id"].get()
            # Base64-encode the PEM key so multiline content survives E2B env var serialization.
            # The sandbox client decodes it back before use.
            private_key = kalshi["private_key"].get().replace("\\n", "\n")
            env["KALSHI_PRIVATE_KEY_B64"] = base64.b64encode(private_key.encode()).decode()

    return env


# ---------------------------------------------------------------------------
# Main execution entry point
# ---------------------------------------------------------------------------

async def bash_impl(
    params: BashParams,
    context: AgentContext
) -> AsyncGenerator[SSEEvent | Dict[str, Any], None]:
    """Run a bash command in the user's persistent E2B sandbox."""
    from core.config import Config

    if not Config.E2B_API_KEY:
        yield {"success": False, "error": "E2B_API_KEY not configured",
               "message": "E2B API key is missing — set E2B_API_KEY in your environment"}
        return

    cmd = params.cmd
    execution_timestamp = datetime.now().isoformat()
    execution_start_time = time.time()

    logger.info("=" * 80)
    logger.info("BASH (persistent E2B sandbox)")
    logger.info(f"User: {context.user_id}, Chat: {context.chat_id}")
    logger.info(f"cmd:\n{'-'*40}\n{cmd}\n{'-'*40}")

    try:
        envs = await _build_sandbox_env(context)

        is_new_sandbox = context.user_id not in _sandboxes

        yield SSEEvent(event="tool_status", data={
            "status": "loading",
            "message": "Starting sandbox..." if is_new_sandbox else "Connecting to sandbox..."
        })

        entry = await get_or_create_sandbox(context.user_id, envs)
        sbx = entry.sbx

        yield SSEEvent(event="tool_status", data={
            "status": "executing",
            "message": "Running..."
        })

        stdout_lines: List[str] = []
        stderr_lines: List[str] = []

        try:
            run_result = await sbx.commands.run(
                cmd,
                cwd=WORKSPACE_DIR,
                timeout=EXECUTION_TIMEOUT,
                envs=entry.envs,
                on_stdout=lambda msg: stdout_lines.append(msg.line if hasattr(msg, 'line') else str(msg)),
                on_stderr=lambda msg: (
                    stderr_lines.append(msg.line if hasattr(msg, 'line') else str(msg)),
                    logger.warning(f"STDERR: {msg.line if hasattr(msg, 'line') else str(msg)}")
                ),
            )
            exit_code = run_result.exit_code
        except CommandExitException as e:
            exit_code = e.exit_code if hasattr(e, 'exit_code') else 1

        # Parse special markers from stdout and strip them
        import re
        import base64 as b64
        clean_stdout_lines = []
        return_images = []  # collect <<RETURN_IMAGE:path>> images for multimodal tool result
        for line in stdout_lines:
            m = re.match(r'^<<OPEN_FILE:(.+?)>>$', line.strip())
            if m:
                yield SSEEvent(event="open_file", data={"path": m.group(1)})
                continue
            m = re.match(r'^<<RETURN_IMAGE:(.+?)>>$', line.strip())
            if m:
                # Read image from sandbox and collect for multimodal result
                img_path = m.group(1)
                try:
                    img_bytes = await sbx.files.read(img_path, format="bytes")
                    ext = img_path.rsplit(".", 1)[-1].lower()
                    media_type = {"png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg"}.get(ext, "image/png")
                    return_images.append({
                        "type": "base64",
                        "media_type": media_type,
                        "data": b64.b64encode(bytes(img_bytes)).decode(),
                    })
                except Exception as img_err:
                    logger.warning(f"Failed to read return image {img_path}: {img_err}")
                continue
            clean_stdout_lines.append(line)
        stdout_lines = clean_stdout_lines

        for line in stdout_lines:
            yield SSEEvent(event="code_output", data={"stream": "stdout", "content": line.rstrip()})
        for line in stderr_lines:
            yield SSEEvent(event="code_output", data={"stream": "stderr", "content": line.rstrip()})
        stdout_text = "\n".join(stdout_lines)
        stderr_text = "\n".join(stderr_lines)

        logger.info(f"Execution completed with exit code: {exit_code}")

        execution_duration = time.time() - execution_start_time

        _save_code_execution_log(context.user_id, context.chat_id, {
            "timestamp": execution_timestamp,
            "user_id": context.user_id,
            "chat_id": context.chat_id,
            "cmd": cmd,
            "sandbox_id": sbx.sandbox_id,
            "exit_code": exit_code,
            "stdout": stdout_text,
            "stderr": stderr_text,
            "execution_duration_seconds": execution_duration,
            "success": exit_code == 0,
        })

        stdout_truncated = stdout_text
        stderr_truncated = stderr_text
        truncation_note = ""

        if exit_code != 0:
            error_msg = f"Command exited with code {exit_code}\n\n"
            if stderr_truncated:
                error_msg += f"**stderr:**\n```\n{stderr_truncated}\n```"
            if stdout_truncated:
                error_msg += f"\n\n**stdout:**\n```\n{stdout_truncated}\n```"

            yield {
                "success": False,
                "error": error_msg,
                "stderr": stderr_truncated,
                "stdout": stdout_truncated,
            }
            return

        yield SSEEvent(event="tool_status", data={
            "status": "complete",
            "message": f"Done{truncation_note}"
        })

        result = {
            "success": True,
            "stdout": stdout_truncated,
            "stderr": stderr_truncated,
            "message": f"Done{truncation_note}",
        }
        if return_images:
            result["images"] = return_images
        yield result

    except Exception as e:
        logger.error(f"bash error: {str(e)}", exc_info=True)
        yield {"success": False, "error": str(e), "message": f"bash failed: {str(e)}"}
