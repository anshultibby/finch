"""
API routes for agent-generated HTML visualizations
"""
import logging
import re
import secrets
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List

from core.database import get_async_db
from auth.dependencies import get_current_user_id
from models.brokerage import Visualization

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/visualizations", tags=["visualizations"])


@router.get("")
async def list_visualizations(
    db: AsyncSession = Depends(get_async_db),
    user_id: str = Depends(get_current_user_id),
):
    """List all visualizations for the user (without html_content)."""
    result = await db.execute(
        select(
            Visualization.id,
            Visualization.title,
            Visualization.description,
            Visualization.filename,
            Visualization.category,
            Visualization.tags,
            Visualization.chat_id,
            Visualization.is_public,
            Visualization.share_token,
            Visualization.created_at,
            Visualization.updated_at,
        )
        .where(Visualization.user_id == user_id)
        .order_by(Visualization.updated_at.desc())
    )
    rows = result.all()
    return {
        "visualizations": [
            {
                "id": str(row.id),
                "title": row.title,
                "description": row.description,
                "filename": row.filename,
                "category": row.category,
                "tags": row.tags or [],
                "chat_id": str(row.chat_id) if row.chat_id else None,
                "is_public": row.is_public,
                "share_token": row.share_token,
                "created_at": row.created_at.isoformat() if row.created_at else None,
                "updated_at": row.updated_at.isoformat() if row.updated_at else None,
            }
            for row in rows
        ]
    }


@router.get("/shared/{share_token}")
async def get_shared_visualization(
    share_token: str,
    db: AsyncSession = Depends(get_async_db),
):
    """Get metadata for a publicly shared visualization (no auth required)."""
    result = await db.execute(
        select(Visualization)
        .where(Visualization.share_token == share_token, Visualization.is_public == True)
    )
    viz = result.scalar_one_or_none()
    if not viz:
        raise HTTPException(status_code=404, detail="Visualization not found or not shared")
    return {
        "id": str(viz.id),
        "title": viz.title,
        "description": viz.description,
        "category": viz.category,
        "tags": viz.tags or [],
        "created_at": viz.created_at.isoformat() if viz.created_at else None,
        "updated_at": viz.updated_at.isoformat() if viz.updated_at else None,
    }


@router.get("/shared/{share_token}/render")
async def render_shared_visualization(
    share_token: str,
    db: AsyncSession = Depends(get_async_db),
):
    """Serve the HTML of a publicly shared visualization (no auth required)."""
    result = await db.execute(
        select(Visualization.html_content, Visualization.title)
        .where(Visualization.share_token == share_token, Visualization.is_public == True)
    )
    row = result.one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Visualization not found or not shared")
    return HTMLResponse(content=row.html_content)


@router.get("/{viz_id}")
async def get_visualization(
    viz_id: str,
    db: AsyncSession = Depends(get_async_db),
    user_id: str = Depends(get_current_user_id),
):
    """Get a single visualization's metadata (without html_content)."""
    result = await db.execute(
        select(Visualization)
        .where(Visualization.id == viz_id, Visualization.user_id == user_id)
    )
    viz = result.scalar_one_or_none()
    if not viz:
        raise HTTPException(status_code=404, detail="Visualization not found")
    return {
        "id": str(viz.id),
        "title": viz.title,
        "description": viz.description,
        "filename": viz.filename,
        "category": viz.category,
        "tags": viz.tags or [],
        "chat_id": str(viz.chat_id) if viz.chat_id else None,
        "is_public": viz.is_public,
        "share_token": viz.share_token,
        "created_at": viz.created_at.isoformat() if viz.created_at else None,
        "updated_at": viz.updated_at.isoformat() if viz.updated_at else None,
    }


@router.get("/{viz_id}/render")
async def render_visualization(
    viz_id: str,
    db: AsyncSession = Depends(get_async_db),
    user_id: str = Depends(get_current_user_id),
):
    """Serve the visualization HTML for iframe embedding."""
    result = await db.execute(
        select(Visualization.html_content)
        .where(Visualization.id == viz_id, Visualization.user_id == user_id)
    )
    row = result.one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Visualization not found")
    return HTMLResponse(
        content=row.html_content,
        headers={"X-Frame-Options": "SAMEORIGIN"},
    )


class VizUpdateRequest(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    tags: Optional[List[str]] = None


@router.patch("/{viz_id}")
async def update_visualization(
    viz_id: str,
    body: VizUpdateRequest,
    db: AsyncSession = Depends(get_async_db),
    user_id: str = Depends(get_current_user_id),
):
    """Update visualization metadata."""
    result = await db.execute(
        select(Visualization)
        .where(Visualization.id == viz_id, Visualization.user_id == user_id)
    )
    viz = result.scalar_one_or_none()
    if not viz:
        raise HTTPException(status_code=404, detail="Visualization not found")
    if body.title is not None:
        viz.title = body.title
    if body.description is not None:
        viz.description = body.description
    if body.category is not None:
        viz.category = body.category
    if body.tags is not None:
        viz.tags = body.tags
    await db.commit()
    return {"ok": True}


@router.delete("/{viz_id}")
async def delete_visualization(
    viz_id: str,
    db: AsyncSession = Depends(get_async_db),
    user_id: str = Depends(get_current_user_id),
):
    """Delete a visualization."""
    result = await db.execute(
        select(Visualization)
        .where(Visualization.id == viz_id, Visualization.user_id == user_id)
    )
    viz = result.scalar_one_or_none()
    if not viz:
        raise HTTPException(status_code=404, detail="Visualization not found")
    await db.delete(viz)
    await db.commit()
    return {"ok": True}


@router.post("/{viz_id}/share")
async def toggle_share(
    viz_id: str,
    db: AsyncSession = Depends(get_async_db),
    user_id: str = Depends(get_current_user_id),
):
    """Toggle public sharing for a visualization. Returns the share_token when enabled."""
    result = await db.execute(
        select(Visualization)
        .where(Visualization.id == viz_id, Visualization.user_id == user_id)
    )
    viz = result.scalar_one_or_none()
    if not viz:
        raise HTTPException(status_code=404, detail="Visualization not found")

    if viz.is_public:
        viz.is_public = False
        viz.share_token = None
    else:
        viz.is_public = True
        if not viz.share_token:
            viz.share_token = secrets.token_urlsafe(16)

    await db.commit()
    await db.refresh(viz)
    return {
        "is_public": viz.is_public,
        "share_token": viz.share_token,
    }


_SAFE_SCRIPT_PATH = re.compile(r"^[a-zA-Z0-9_/][a-zA-Z0-9_\-./]*\.py$")


class RunScriptRequest(BaseModel):
    script: str


@router.post("/run-script")
async def run_script(
    body: RunScriptRequest,
    user_id: str = Depends(get_current_user_id),
):
    """Run a Python script in the user's sandbox and return stdout as JSON.

    Used by visualization iframes to fetch live data via the postMessage bridge.
    """
    if ".." in body.script or body.script.startswith("/") or not _SAFE_SCRIPT_PATH.match(body.script):
        raise HTTPException(status_code=400, detail="Invalid script path")

    from modules.tools.implementations.code_execution import get_or_create_sandbox, _build_sandbox_env, WORKSPACE_DIR
    from modules.agent.context import AgentContext

    try:
        ctx = AgentContext(user_id=user_id)
        envs = await _build_sandbox_env(ctx)
        entry = await get_or_create_sandbox(user_id, envs)

        stdout_lines = []
        stderr_lines = []
        result = await entry.sbx.commands.run(
            f"python3 {body.script}",
            cwd=WORKSPACE_DIR,
            timeout=30,
            envs=entry.envs,
            on_stdout=lambda msg: stdout_lines.append(msg.line),
            on_stderr=lambda msg: stderr_lines.append(msg.line),
        )

        if result.exit_code != 0:
            logger.warning(f"run-script failed: {body.script} exit={result.exit_code}")
            raise HTTPException(
                status_code=500,
                detail={"error": "Script failed", "stderr": "\n".join(stderr_lines[-20:])},
            )

        import json
        stdout = "\n".join(stdout_lines)
        try:
            return json.loads(stdout)
        except json.JSONDecodeError:
            return {"raw": stdout}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"run-script error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
