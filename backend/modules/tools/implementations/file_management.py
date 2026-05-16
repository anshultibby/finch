"""
File Management Implementation — Sandbox-backed

Chat files live inside the bot's sandbox directory when a bot context is active,
otherwise fall back to /home/user/chat_files/.
No database storage for file content — only Resource entries for UI sidebar.
"""
from modules.agent.context import AgentContext
from pydantic import BaseModel, Field
from typing import Optional, List
from utils.logger import get_logger
import re

logger = get_logger(__name__)

FALLBACK_FILES_DIR = "/home/user/chat_files"


def _files_dir(context: AgentContext) -> str:
    """Return the file workspace — bot root dir if available, else /home/user/chat_files."""
    bot_dir = (context.data or {}).get("bot_directory", "")
    if bot_dir:
        return f"/home/user/{bot_dir}"
    return FALLBACK_FILES_DIR


def _detect_file_type(filename: str) -> str:
    """Detect file type from extension."""
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


class EditItem(BaseModel):
    """A single edit operation"""
    old_str: str = Field(..., description="Text to find (must be unique unless replace_all=True)")
    new_str: str = Field(..., description="Text to replace with")
    replace_all: bool = Field(
        default=False,
        description="Replace all occurrences. Default False requires unique match for safety."
    )


class ReplaceInFileParams(BaseModel):
    """Replace text in a file - supports multiple edits in one call"""
    filename: str = Field(..., description="Filename in current chat directory")
    old_str: Optional[str] = Field(None, description="Text to find (must be unique unless replace_all=True). Use 'edits' for multiple changes.")
    new_str: Optional[str] = Field(None, description="Text to replace with. Use 'edits' for multiple changes.")
    replace_all: bool = Field(
        default=False,
        description="Replace all occurrences. Default False requires unique match for safety."
    )
    edits: Optional[List[EditItem]] = Field(
        None,
        description="List of edits to apply in sequence. Use this for multiple changes in one call."
    )


class FindInFileParams(BaseModel):
    """Search for pattern in file"""
    filename: str = Field(..., description="Filename in current chat directory")
    pattern: str = Field(..., description="Regular expression pattern to search for")


async def _get_sandbox(user_id: str):
    """Get a sandbox entry for the user (creating if needed)."""
    from modules.tools.implementations.code_execution import get_or_create_sandbox
    return await get_or_create_sandbox(user_id, envs={})


_STOCK_ANALYSIS_MD_PATTERN = re.compile(r"^stocks/([A-Z0-9.]+)/([^/]+\.md)$", re.IGNORECASE)
_VISUALIZATION_HTML_PATTERN = re.compile(r"^visualizations/[^/]+\.html$", re.IGNORECASE)
_VISUALIZATION_JS_PATTERN = re.compile(r"^visualizations/[^/]+\.js$", re.IGNORECASE)

_INVALID_SYMBOLS = {
    "PDUFA", "BIOTECH", "EARNINGS", "FDA", "NDA", "BLA", "SNDA",
    "PHARMA", "INDEX", "MARKET", "SECTOR", "ETF", "MACRO", "MISC",
    "WATCHLIST", "CALENDAR", "RESEARCH", "NOTES", "DRAFT", "TEMP",
}

def _is_valid_ticker(symbol: str) -> bool:
    """Reject category names masquerading as tickers."""
    if len(symbol) > 6:
        return False
    if symbol in _INVALID_SYMBOLS:
        return False
    if not re.match(r"^[A-Z]{1,5}(\.[A-Z]{1,2})?$", symbol):
        return False
    return True


def _extract_title(content: str) -> str | None:
    """Extract the first markdown heading as the note title."""
    for line in content.split('\n'):
        line = line.strip()
        if line.startswith('# '):
            return line[2:].strip()[:200]
    return None


async def _maybe_sync_stock_analysis(
    filename: str, content: str, context: AgentContext,
    *, sync_to_analysis: bool = True,
):
    """If filename matches stocks/{SYMBOL}/*.md, upsert note to DB and add to watchlist."""
    m = _STOCK_ANALYSIS_MD_PATTERN.match(filename)
    if not m:
        return
    symbol = m.group(1).upper()
    md_filename = m.group(2)

    if not _is_valid_ticker(symbol):
        logger.warning(f"Rejected invalid ticker '{symbol}' from filename '{filename}' — skipping sync")
        return

    if not sync_to_analysis:
        return

    title = _extract_title(content)
    try:
        from core.database import get_db_session
        from sqlalchemy import text
        chat_id = (context.data or {}).get("chat_id")
        async with get_db_session() as db:
            await db.execute(
                text(
                    "INSERT INTO stock_analysis (id, user_id, symbol, filename, title, content, chat_id, created_at, updated_at) "
                    "VALUES (gen_random_uuid(), :user_id, :symbol, :filename, :title, :content, :chat_id, now(), now()) "
                    "ON CONFLICT ON CONSTRAINT uq_stock_analysis_user_symbol_filename DO UPDATE SET "
                    "content = EXCLUDED.content, title = EXCLUDED.title, "
                    "chat_id = COALESCE(EXCLUDED.chat_id, stock_analysis.chat_id), updated_at = now()"
                ),
                {"user_id": context.user_id, "symbol": symbol, "filename": md_filename,
                 "title": title, "content": content, "chat_id": chat_id},
            )

            ai_list = await db.execute(
                text(
                    "SELECT id FROM watchlist_list "
                    "WHERE user_id = :user_id AND list_type = 'ai_picks' LIMIT 1"
                ),
                {"user_id": context.user_id},
            )
            ai_list_row = ai_list.fetchone()
            if not ai_list_row:
                await db.execute(
                    text(
                        "INSERT INTO watchlist_list (id, user_id, name, list_type, position) "
                        "VALUES (gen_random_uuid(), :user_id, 'AI Picks', 'ai_picks', 0) "
                        "ON CONFLICT (user_id, name) DO NOTHING"
                    ),
                    {"user_id": context.user_id},
                )
                ai_list = await db.execute(
                    text("SELECT id FROM watchlist_list WHERE user_id = :user_id AND list_type = 'ai_picks' LIMIT 1"),
                    {"user_id": context.user_id},
                )
                ai_list_row = ai_list.fetchone()

            ai_list_id = str(ai_list_row[0]) if ai_list_row else None
            await db.execute(
                text(
                    "INSERT INTO user_watchlist (id, user_id, symbol, source, list_id) "
                    "VALUES (gen_random_uuid(), :user_id, :symbol, 'ai', :list_id) "
                    "ON CONFLICT (user_id, symbol, list_id) DO NOTHING"
                ),
                {"user_id": context.user_id, "symbol": symbol, "list_id": ai_list_id},
            )
            await db.commit()
        logger.info(f"Auto-synced stock analysis + watchlist for {symbol}/{md_filename} (user {context.user_id})")
    except Exception as e:
        logger.warning(f"Stock analysis sync failed for {symbol} (non-fatal): {e}")


def _extract_html_title(content: str) -> str | None:
    m = re.search(r'<title>(.*?)</title>', content, re.IGNORECASE | re.DOTALL)
    return m.group(1).strip()[:200] if m else None


_CDN_LIBS = {
    "d3":       "https://cdn.jsdelivr.net/npm/d3@7/dist/d3.min.js",
    "chartjs":  "https://cdn.jsdelivr.net/npm/chart.js@4/dist/chart.umd.min.js",
    "plotly":   "https://cdn.plot.ly/plotly-2.35.2.min.js",
    "three":    "https://cdn.jsdelivr.net/npm/three@0.170/build/three.module.min.js",
    "anime":    "https://cdn.jsdelivr.net/npm/animejs@3/lib/anime.min.js",
    "gsap":     "https://cdn.jsdelivr.net/npm/gsap@3/dist/gsap.min.js",
    "leaflet":  "https://cdn.jsdelivr.net/npm/leaflet@1/dist/leaflet.min.js",
    "maplibre": "https://cdn.jsdelivr.net/npm/maplibre-gl@4/dist/maplibre-gl.min.js",
    "mermaid":  "https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.min.js",
    "katex":    "https://cdn.jsdelivr.net/npm/katex@0/dist/katex.min.js",
    "marked":   "https://cdn.jsdelivr.net/npm/marked@15/marked.min.js",
    "tone":     "https://cdn.jsdelivr.net/npm/tone@15/build/Tone.min.js",
}
_CDN_CSS = {
    "leaflet":  "https://cdn.jsdelivr.net/npm/leaflet@1/dist/leaflet.min.css",
    "katex":    "https://cdn.jsdelivr.net/npm/katex@0/dist/katex.min.css",
    "maplibre": "https://cdn.jsdelivr.net/npm/maplibre-gl@4/dist/maplibre-gl.min.css",
}

_LIB_DIRECTIVE_RE = re.compile(r"^//\s*@lib\s+(.+)$", re.MULTILINE)


def _wrap_js_in_html(js_code: str, title: str) -> str:
    """Wrap a JS file in a self-contained HTML shell with CDN libs and Finch theming."""
    libs = []
    for m in _LIB_DIRECTIVE_RE.finditer(js_code):
        libs.append(m.group(1).strip())

    script_urls = []
    css_urls = []
    use_module = False
    for lib in libs:
        if lib.startswith("http"):
            script_urls.append(lib)
        else:
            key = lib.lower()
            if key in _CDN_LIBS:
                script_urls.append(_CDN_LIBS[key])
                if key in _CDN_CSS:
                    css_urls.append(_CDN_CSS[key])
                if key == "three":
                    use_module = True

    css_tags = "\n".join(f'<link rel="stylesheet" href="{u}">' for u in css_urls)
    script_tags = "\n".join(
        f'<script src="{u}"></script>'
        for u in script_urls if "three" not in u
    )
    three_import = ""
    if use_module:
        three_url = _CDN_LIBS["three"]
        three_import = f'<script type="importmap">{{"imports":{{"three":"{three_url}"}}}}</script>'

    script_type = ' type="module"' if use_module else ""

    from html import escape
    title_esc = escape(title)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title_esc}</title>
{css_tags}
{script_tags}
{three_import}
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
:root{{
  --bg:#fafaf9;--surface:#ffffff;--surface-raised:#f5f5f4;
  --border:rgba(0,0,0,0.06);--border-md:rgba(0,0,0,0.1);
  --text:#0f172a;--text-2:#64748b;--text-3:#94a3b8;
  --accent:#10b981;
  --pos:#16a34a;--neg:#dc2626;
  --blue:#3b82f6;--purple:#a855f7;--amber:#f59e0b;--teal:#14b8a6;--pink:#ec4899;--indigo:#6366f1;
  --radius:8px;--radius-lg:12px;
}}
body{{
  font-family:-apple-system,BlinkMacSystemFont,'Inter','Segoe UI',system-ui,sans-serif;
  background:var(--bg);color:var(--text);min-height:100vh;
  -webkit-font-smoothing:antialiased;font-size:14px;line-height:1.5;
}}
#root{{width:100%;min-height:100vh;padding:24px}}
::-webkit-scrollbar{{width:6px}}::-webkit-scrollbar-thumb{{background:#ccc;border-radius:3px}}
.card{{background:var(--surface);border:1px solid var(--border);border-radius:var(--radius-lg);padding:20px}}
.card-sm{{background:var(--surface);border:1px solid var(--border);border-radius:var(--radius);padding:12px}}
.grid{{display:grid;gap:16px}}.grid-2{{grid-template-columns:repeat(2,1fr)}}.grid-3{{grid-template-columns:repeat(3,1fr)}}.grid-4{{grid-template-columns:repeat(4,1fr)}}
.flex{{display:flex}}.flex-col{{flex-direction:column}}.gap-sm{{gap:8px}}.gap-md{{gap:16px}}.gap-lg{{gap:24px}}.items-center{{align-items:center}}.justify-between{{justify-content:space-between}}
.kpi{{font-size:28px;font-weight:700;letter-spacing:-0.02em;font-variant-numeric:tabular-nums}}.kpi-sm{{font-size:20px;font-weight:600;font-variant-numeric:tabular-nums}}
.label{{font-size:11px;font-weight:500;color:var(--text-3);text-transform:uppercase;letter-spacing:0.05em}}
.title{{font-size:16px;font-weight:600;color:var(--text)}}.subtitle{{font-size:13px;color:var(--text-2)}}
.positive{{color:var(--pos)}}.negative{{color:var(--neg)}}
.tabular{{font-variant-numeric:tabular-nums}}
.mono{{font-family:'SF Mono',Menlo,monospace;font-size:12px}}
.badge{{display:inline-flex;align-items:center;padding:2px 8px;border-radius:999px;font-size:11px;font-weight:500}}
.badge-pos{{background:#dcfce7;color:var(--pos)}}.badge-neg{{background:#fef2f2;color:var(--neg)}}.badge-accent{{background:#d1fae5;color:#065f46}}
.tooltip{{position:absolute;background:var(--text);color:#fff;padding:4px 8px;border-radius:4px;font-size:11px;pointer-events:none;white-space:nowrap;z-index:100}}
</style>
</head>
<body>
<div id="root"></div>
<script>
window.finch={{_cb:{{}},fetch(url,body){{return new Promise((resolve,reject)=>{{const id=Math.random().toString(36).slice(2);this._cb[id]={{resolve,reject}};parent.postMessage({{type:'finch-fetch',url,body,id}},'*');setTimeout(()=>{{if(this._cb[id]){{delete this._cb[id];reject(new Error('timeout'))}}}},30000)}})}}}}; addEventListener('message',e=>{{if(e.data?.type==='finch-response'&&finch._cb[e.data.id]){{const h=finch._cb[e.data.id];delete finch._cb[e.data.id];e.data.error?h.reject(new Error(e.data.error)):h.resolve(e.data.data)}}}});
</script>
<script{script_type}>
(function(){{
  function _run(){{
{js_code}
  }}
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',_run);
  else _run();
}})();
</script>
</body>
</html>"""


async def _maybe_sync_visualization(filename: str, content: str, context: AgentContext):
    """If filename matches visualizations/*.html or *.js, upsert into visualizations table.

    For .js files: auto-wrap in HTML shell, derive title from filename, store with .html extension.
    For .html files: extract title from <title> tag, store as-is.
    """
    is_html = _VISUALIZATION_HTML_PATTERN.match(filename)
    is_js = _VISUALIZATION_JS_PATTERN.match(filename)
    if not is_html and not is_js:
        return

    if is_js:
        basename = re.sub(r"\.js$", "", filename.rsplit("/", 1)[-1], flags=re.IGNORECASE)
        title = basename.replace("_", " ").replace("-", " ").title()
        html_content = _wrap_js_in_html(content, title)
        db_filename = re.sub(r"\.js$", ".html", filename, flags=re.IGNORECASE)
    else:
        title = _extract_html_title(content)
        html_content = content
        db_filename = filename

    try:
        from core.database import get_db_session
        from sqlalchemy import text
        chat_id = (context.data or {}).get("chat_id")
        async with get_db_session() as db:
            await db.execute(
                text(
                    "INSERT INTO visualizations (id, user_id, chat_id, title, filename, html_content, created_at, updated_at) "
                    "VALUES (gen_random_uuid(), :user_id, :chat_id, :title, :filename, :html_content, now(), now()) "
                    "ON CONFLICT ON CONSTRAINT uq_viz_user_filename DO UPDATE SET "
                    "html_content = EXCLUDED.html_content, title = EXCLUDED.title, "
                    "chat_id = COALESCE(EXCLUDED.chat_id, visualizations.chat_id), updated_at = now() "
                    "WHERE visualizations.html_content IS DISTINCT FROM EXCLUDED.html_content "
                    "OR visualizations.title IS DISTINCT FROM EXCLUDED.title"
                ),
                {"user_id": context.user_id, "chat_id": chat_id, "title": title, "filename": db_filename, "html_content": html_content},
            )
            await db.commit()
        logger.info(f"Auto-synced visualization '{filename}' → '{db_filename}' for user {context.user_id}")
    except Exception as e:
        logger.warning(f"Visualization sync failed for {filename} (non-fatal): {e}")


def _sandbox_path(filename: str, context: AgentContext) -> str:
    """Build full sandbox path. Absolute paths are used as-is; relative paths are under the files dir."""
    if filename.startswith("/"):
        return filename
    return f"{_files_dir(context)}/{filename}"


async def _read_sandbox_text(user_id: str, filename: str, context: AgentContext) -> Optional[str]:
    """Read a text file from the sandbox. Returns None if not found."""
    from modules.tools.implementations.code_execution import read_sandbox_file
    data = await read_sandbox_file(user_id, _sandbox_path(filename, context))
    if data is None:
        return None
    return data.decode("utf-8", errors="replace")


SYNC_MANIFEST_PATH = f"{FALLBACK_FILES_DIR}/.sync_pending"


async def process_sync_manifest(context: AgentContext):
    """Scan visualizations/ for .js/.html files and sync to DB. Also processes .sync_pending manifest."""
    from modules.tools.implementations.code_execution import read_sandbox_file, get_or_create_sandbox

    synced = 0

    # Scan visualizations/ directory for any .js or .html files
    try:
        entry = await get_or_create_sandbox(context.user_id, envs={})
        viz_dir = f"{_files_dir(context)}/visualizations"
        try:
            entries = await entry.sbx.files.list(viz_dir, depth=1)
        except Exception:
            entries = []

        for e in entries:
            if e.type == "dir":
                continue
            name_lower = e.name.lower()
            if not (name_lower.endswith(".js") or name_lower.endswith(".html")):
                continue
            filename = f"visualizations/{e.name}"
            content = await _read_sandbox_text(context.user_id, filename, context)
            if content:
                await _maybe_sync_visualization(filename, content, context)
                synced += 1
    except Exception as e:
        logger.debug(f"Viz directory scan skipped: {e}")

    # Also process legacy .sync_pending manifest
    data = await read_sandbox_file(context.user_id, SYNC_MANIFEST_PATH)
    if data:
        filenames = [
            line.strip() for line in data.decode("utf-8", errors="replace").splitlines()
            if line.strip()
        ]
        for filename in filenames:
            content = await _read_sandbox_text(context.user_id, filename, context)
            if content is None:
                continue
            await _maybe_sync_visualization(filename, content, context)
            await _maybe_sync_stock_analysis(filename, content, context)
            synced += 1

        try:
            await entry.sbx.files.write(SYNC_MANIFEST_PATH, "")
        except Exception:
            pass

    if synced:
        logger.info(f"Synced {synced} visualization(s) for user {context.user_id}")


# ============================================================================
# Tool implementations
# ============================================================================

async def write_chat_file_impl(
    context: AgentContext,
    filename: str,
    content: str,
    *,
    sync_to_analysis: bool = True,
):
    """Write file to sandbox. Absolute paths write directly; relative paths go to the chat files dir."""
    try:
        entry = await _get_sandbox(context.user_id)
        full_path = _sandbox_path(filename, context)

        if filename.startswith("/"):
            # Absolute path — ensure parent dir exists
            parent = "/".join(full_path.rsplit("/", 1)[:-1])
            await entry.sbx.commands.run(f"mkdir -p {parent}", timeout=5)
        else:
            # Relative path — ensure the chat_files directory exists
            chat_dir = _files_dir(context)
            await entry.sbx.commands.run(f"mkdir -p {chat_dir}", timeout=5)

        await entry.sbx.files.write(full_path, content)

        # Only sync analysis/viz for relative paths (chat workspace files)
        if not filename.startswith("/"):
            await _maybe_sync_stock_analysis(filename, content, context, sync_to_analysis=sync_to_analysis)
            await _maybe_sync_visualization(filename, content, context)

        yield {
            "success": True,
            "filename": filename,
            "sandbox_path": full_path,
            "message": f"Wrote {filename} (available at {full_path})"
        }
    except Exception as e:
        logger.error(f"Error writing chat file: {str(e)}", exc_info=True)
        yield {"success": False, "error": str(e)}


async def read_chat_file_impl(
    context: AgentContext,
    filename: str,
    start_line: Optional[int] = None,
    end_line: Optional[int] = None,
    peek: bool = False,
):
    """Read file from sandbox."""
    if peek:
        start_line = 1
        end_line = 100

    if start_line is not None:
        start_line = int(start_line)
    if end_line is not None:
        end_line = int(end_line)

    try:
        file_type = _detect_file_type(filename)

        # For images, read as bytes and return base64
        if file_type == "image":
            from modules.tools.implementations.code_execution import read_sandbox_file
            import base64
            data = await read_sandbox_file(context.user_id, _sandbox_path(filename, context))
            if data is None:
                return {"success": False, "error": f"File '{filename}' not found"}

            media_type = "image/png"
            if filename.lower().endswith(('.jpg', '.jpeg')):
                media_type = "image/jpeg"
            elif filename.lower().endswith('.gif'):
                media_type = "image/gif"
            elif filename.lower().endswith('.webp'):
                media_type = "image/webp"
            elif filename.lower().endswith('.svg'):
                media_type = "image/svg+xml"

            return {
                "success": True,
                "filename": filename,
                "file_type": "image",
                "is_image": True,
                "image": {
                    "type": "base64",
                    "media_type": media_type,
                    "data": base64.b64encode(data).decode('utf-8')
                },
                "message": f"Image '{filename}' loaded."
            }

        # Text file — read from sandbox
        content = await _read_sandbox_text(context.user_id, filename, context)
        if content is None:
            return {"success": False, "error": f"File '{filename}' not found"}

        lines = content.split('\n')
        total_lines = len(lines)

        if start_line is not None or end_line is not None:
            start_idx = (start_line or 1) - 1
            end_idx = end_line or total_lines
            start_idx = max(0, min(start_idx, total_lines - 1)) if total_lines > 0 else 0
            end_idx = max(start_idx + 1, min(end_idx, total_lines))

            selected_lines = lines[start_idx:end_idx]
            content = '\n'.join(selected_lines)

            nav_hints = []
            if start_idx > 0:
                nav_hints.append(f"lines 1-{start_idx} above")
            if end_idx < total_lines:
                nav_hints.append(f"lines {end_idx + 1}-{total_lines} below")

            return {
                "success": True,
                "content": content,
                "filename": filename,
                "file_type": file_type,
                "start_line": start_idx + 1,
                "end_line": end_idx,
                "total_lines": total_lines,
                "navigation": f"({', '.join(nav_hints)})" if nav_hints else None
            }

        return {
            "success": True,
            "content": content,
            "filename": filename,
            "file_type": file_type,
            "total_lines": total_lines
        }
    except Exception as e:
        logger.error(f"Error reading chat file: {str(e)}", exc_info=True)
        return {"success": False, "error": str(e)}


async def replace_in_chat_file_impl(
    old_str: Optional[str],
    new_str: Optional[str],
    filename: str,
    context: AgentContext,
    replace_all: bool = False,
    edits: Optional[List[EditItem]] = None
):
    """Replace text in file on sandbox."""
    try:
        # Build edit list
        edit_list: List[EditItem] = []

        if edits:
            for edit in edits:
                if isinstance(edit, dict):
                    edit_list.append(EditItem(**edit))
                elif isinstance(edit, EditItem):
                    edit_list.append(edit)
                else:
                    yield {"success": False, "error": f"Invalid edit item type: {type(edit).__name__}"}
                    return
        elif old_str is not None and new_str is not None:
            edit_list = [EditItem(old_str=old_str, new_str=new_str, replace_all=replace_all)]
        else:
            yield {"success": False, "error": "Must provide either (old_str + new_str) or edits list"}
            return

        # Read from sandbox
        content = await _read_sandbox_text(context.user_id, filename, context)
        if content is None:
            yield {"success": False, "error": f"File '{filename}' not found"}
            return

        # Apply edits
        total_replacements = 0
        edit_results = []

        for i, edit in enumerate(edit_list):
            count = content.count(edit.old_str)

            if count == 0:
                display_str = f"'{edit.old_str[:100]}...'" if len(edit.old_str) > 100 else f"'{edit.old_str}'"
                yield {
                    "success": False,
                    "error": f"Edit {i + 1}: Text not found: {display_str}",
                    "partial_results": edit_results if edit_results else None
                }
                return

            if count > 1 and not edit.replace_all:
                yield {
                    "success": False,
                    "error": f"Edit {i + 1}: Found {count} occurrences of the text. Either:\n"
                             f"1. Include more surrounding context to make it unique, OR\n"
                             f"2. Set replace_all=True to replace all {count} occurrences",
                    "partial_results": edit_results if edit_results else None
                }
                return

            if edit.replace_all:
                content = content.replace(edit.old_str, edit.new_str)
                actual_count = count
            else:
                content = content.replace(edit.old_str, edit.new_str, 1)
                actual_count = 1

            total_replacements += actual_count
            edit_results.append({"edit_index": i + 1, "replacements": actual_count})

        # Write back to sandbox
        entry = await _get_sandbox(context.user_id)
        await entry.sbx.files.write(_sandbox_path(filename, context), content)

        await _maybe_sync_stock_analysis(filename, content, context)
        await _maybe_sync_visualization(filename, content, context)

        yield {
            "success": True,
            "filename": filename,
            "edits_applied": len(edit_list),
            "total_replacements": total_replacements,
            "message": f"Applied {len(edit_list)} edit(s) with {total_replacements} total replacement(s)"
        }

    except Exception as e:
        logger.error(f"Error replacing in file: {str(e)}", exc_info=True)
        yield {"success": False, "error": str(e)}


async def find_in_chat_file_impl(
    pattern: str,
    filename: str,
    context: AgentContext
):
    """Find pattern in file on sandbox."""
    try:
        content = await _read_sandbox_text(context.user_id, filename, context)
        if content is None:
            return {"success": False, "error": f"File '{filename}' not found"}

        lines = content.split('\n')
        matches = []

        for i, line in enumerate(lines):
            if re.search(pattern, line):
                matches.append({"line": i, "content": line.strip()})

        return {
            "success": True,
            "filename": filename,
            "pattern": pattern,
            "matches": matches,
            "count": len(matches)
        }

    except re.error as e:
        return {"success": False, "error": f"Invalid regex pattern: {str(e)}"}
    except Exception as e:
        logger.error(f"Error searching file: {str(e)}", exc_info=True)
        return {"success": False, "error": str(e)}


async def list_chat_files_impl(
    context: AgentContext,
    directory: str = ""
):
    """List files on sandbox in the bot's chat_files directory."""
    try:
        entry = await _get_sandbox(context.user_id)

        base_dir = _files_dir(context)
        target_dir = base_dir
        dir_path = directory.strip().strip('/')
        if dir_path:
            target_dir = f"{base_dir}/{dir_path}"

        try:
            entries = await entry.sbx.files.list(target_dir, depth=1)
        except Exception:
            # Directory doesn't exist yet
            entries = []

        subdirs = []
        files = []
        for e in entries:
            if e.type == "dir":
                subdirs.append(e.name)
            else:
                files.append({
                    "name": e.name,
                    "type": _detect_file_type(e.name),
                    "size": e.size or 0,
                })

        # Format output
        current_path = f"/{dir_path}" if dir_path else "/"
        result_lines = [f"Contents of {current_path}:\n"]

        if subdirs:
            result_lines.append("Directories:")
            for d in sorted(subdirs):
                result_lines.append(f"  {d}/")
            result_lines.append("")

        if files:
            result_lines.append("Files:")
            for f in sorted(files, key=lambda x: x['name']):
                size_kb = f['size'] / 1024
                result_lines.append(f"  {f['name']:40} ({size_kb:>8.1f} KB)  {f['type']}")

        if not subdirs and not files:
            result_lines.append("(empty directory)")

        result_lines.append(f"\nSummary: {len(subdirs)} directories, {len(files)} files")

        return {
            "success": True,
            "directory": current_path,
            "subdirectories": sorted(subdirs),
            "files": files,
            "summary": "\n".join(result_lines)
        }
    except Exception as e:
        logger.error(f"Error listing chat files: {str(e)}", exc_info=True)
        return {"success": False, "error": str(e)}


async def show_filesystem_tree_impl(context: AgentContext):
    """Show chat filesystem tree from sandbox."""
    try:
        entry = await _get_sandbox(context.user_id)
        base_dir = _files_dir(context)

        try:
            entries = await entry.sbx.files.list(base_dir, depth=10)
        except Exception:
            entries = []

        if not entries:
            return {
                "success": True,
                "tree": "# Chat Filesystem Tree\n\n(empty — no files yet)",
                "file_count": 0,
                "total_size": 0
            }

        # Build tree from flat entry list
        tree_lines = ["# Chat Filesystem Tree\n", "```", "."]
        file_count = 0
        total_size = 0

        for e in sorted(entries, key=lambda x: x.path):
            rel_path = e.path.replace(base_dir + "/", "", 1)
            depth = rel_path.count('/')
            indent = "│   " * depth
            name = e.name + ("/" if e.type == "dir" else "")
            tree_lines.append(f"{indent}├── {name}")
            if e.type != "dir":
                file_count += 1
                total_size += e.size or 0

        tree_lines.append("```\n")
        tree_lines.append(f"**Statistics:**")
        tree_lines.append(f"- Files: {file_count}")
        tree_lines.append(f"- Total Size: {total_size:,} bytes ({total_size / 1024:.1f} KB)")

        return {
            "success": True,
            "tree": "\n".join(tree_lines),
            "file_count": file_count,
            "total_size": total_size
        }
    except Exception as e:
        logger.error(f"Error generating filesystem tree: {str(e)}", exc_info=True)
        return {"success": False, "error": str(e)}
