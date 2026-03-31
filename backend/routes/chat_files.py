"""
Chat Files Routes — Files served from the bot's sandbox root directory when available,
otherwise from /home/user/chat_files/.
"""
from fastapi import APIRouter, Depends, HTTPException, Response, UploadFile, File, Form
from sqlalchemy.orm import Session
from core.database import get_db
from pydantic import BaseModel
from typing import List, Optional
import logging
import mimetypes

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/chat-files", tags=["chat-files"])

FALLBACK_FILES_DIR = "/home/user/chat_files"


class ChatFileResponse(BaseModel):
    """Chat file metadata"""
    filename: str
    file_type: str
    size_bytes: int


def _detect_file_type(filename: str) -> str:
    ext_map = {
        '.py': 'python', '.md': 'markdown', '.csv': 'csv',
        '.json': 'json', '.html': 'html',
        '.png': 'image', '.jpg': 'image', '.jpeg': 'image',
        '.gif': 'image', '.webp': 'image', '.svg': 'image',
    }
    for ext, ftype in ext_map.items():
        if filename.lower().endswith(ext):
            return ftype
    return "text"


async def _get_chat_info(chat_id: str, db: Session) -> tuple:
    """Look up the user_id and files root directory for this chat.
    Returns (user_id, files_dir)."""
    from models.chat_models import Chat
    from sqlalchemy import select as sa_select

    result = db.execute(sa_select(Chat).where(Chat.chat_id == chat_id))
    chat = result.scalar_one_or_none()
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")

    files_dir = FALLBACK_FILES_DIR

    # If chat belongs to a bot, use the bot's root directory
    if chat.bot_id:
        try:
            from models.bot import TradingBot
            bot_result = db.execute(
                sa_select(TradingBot).where(TradingBot.id == chat.bot_id)
            )
            bot = bot_result.scalar_one_or_none()
            if bot:
                bot_dir = bot.directory or f"bots/{str(bot.id)[:8]}"
                files_dir = f"/home/user/{bot_dir}"
        except Exception as e:
            logger.warning(f"Could not resolve bot directory for chat {chat_id}: {e}")

    return chat.user_id, files_dir


@router.get("/{chat_id}", response_model=List[ChatFileResponse])
async def get_chat_files(
    chat_id: str,
    db: Session = Depends(get_db)
):
    """List all files in the bot's root directory on the sandbox."""
    user_id, files_dir = await _get_chat_info(chat_id, db)

    try:
        from modules.tools.implementations.code_execution import _get_or_reconnect_sandbox
        sbx = await _get_or_reconnect_sandbox(user_id)
        if not sbx:
            return []

        try:
            entries = await sbx.files.list(files_dir, depth=5)
        except Exception:
            return []

        files = []
        for entry in entries:
            if entry.type == "dir":
                continue
            files.append(ChatFileResponse(
                filename=entry.name,
                file_type=_detect_file_type(entry.name),
                size_bytes=entry.size or 0,
            ))
        return files

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing chat files: {e}", exc_info=True)
        return []


@router.get("/{chat_id}/download/{filename:path}")
async def download_chat_file(
    chat_id: str,
    filename: str,
    db: Session = Depends(get_db)
):
    """Download a file from the sandbox."""
    user_id, files_dir = await _get_chat_info(chat_id, db)

    try:
        from modules.tools.implementations.code_execution import read_sandbox_file
        path = f"{files_dir}/{filename}"
        data = await read_sandbox_file(user_id, path)

        if data is None:
            raise HTTPException(status_code=404, detail=f"File '{filename}' not found")

        content_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"
        disposition = "inline" if content_type.startswith("image/") or content_type in (
            "text/html", "text/csv", "application/json"
        ) else "attachment"

        return Response(
            content=data,
            media_type=content_type,
            headers={"Content-Disposition": f'{disposition}; filename="{filename}"'}
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error downloading file: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{chat_id}/sandbox-file")
async def get_sandbox_file(
    chat_id: str,
    path: str,
    db: Session = Depends(get_db)
):
    """
    Proxy a file directly from the user's live sandbox by absolute path.
    Used when the agent references a file by its VM path (e.g. /home/user/subdir/chart.png).
    """
    from models.chat_models import Chat
    from sqlalchemy import select as sa_select

    result = db.execute(sa_select(Chat).where(Chat.chat_id == chat_id))
    chat = result.scalar_one_or_none()
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    user_id = chat.user_id

    try:
        from modules.tools.implementations.code_execution import read_sandbox_file
        basename = path.split("/")[-1] if "/" in path else path
        data = await read_sandbox_file(user_id, path)

        if data is None:
            raise HTTPException(status_code=404, detail=f"File not found in sandbox: {path}")

        content_type = mimetypes.guess_type(basename)[0] or "application/octet-stream"
        disposition = "inline" if content_type.startswith("image/") or content_type in (
            "text/html", "text/csv", "application/json"
        ) else "attachment"

        return Response(
            content=data,
            media_type=content_type,
            headers={"Content-Disposition": f'{disposition}; filename="{basename}"'}
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error proxying sandbox file {path}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{chat_id}/{filename:path}")
async def delete_chat_file(
    chat_id: str,
    filename: str,
    db: Session = Depends(get_db)
):
    """Delete a file from the sandbox."""
    user_id, files_dir = await _get_chat_info(chat_id, db)

    try:
        from modules.tools.implementations.code_execution import _get_or_reconnect_sandbox
        sbx = await _get_or_reconnect_sandbox(user_id)
        if not sbx:
            raise HTTPException(status_code=404, detail="Sandbox not available")

        path = f"{files_dir}/{filename}"
        await sbx.commands.run(f"rm -f {path}")
        return {"success": True, "message": f"Deleted {filename}"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting file: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{chat_id}/upload")
async def upload_file_to_sandbox(
    chat_id: str,
    file: UploadFile = File(...),
    dest_dir: str = Form("/home/user/tax/uploads"),
    db: Session = Depends(get_db),
):
    """Upload a file (PDF, CSV, etc.) directly to the user's sandbox.

    Returns the sandbox path so the frontend can reference it in the chat message.
    """
    user_id, _ = await _get_chat_info(chat_id, db)

    try:
        from modules.tools.implementations.code_execution import _get_or_reconnect_sandbox
        sbx = await _get_or_reconnect_sandbox(user_id)
        if not sbx:
            raise HTTPException(status_code=503, detail="Sandbox not available — start a chat first")

        content = await file.read()
        await sbx.commands.run(f"mkdir -p {dest_dir}", timeout=5)

        dest_path = f"{dest_dir}/{file.filename}"
        await sbx.files.write(dest_path, content, request_timeout=60)

        return {
            "filename": file.filename,
            "path": dest_path,
            "size_bytes": len(content),
            "media_type": file.content_type or mimetypes.guess_type(file.filename)[0],
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading file to sandbox: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
