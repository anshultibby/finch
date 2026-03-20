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


def _sandbox_path(filename: str, context: AgentContext) -> str:
    """Build full sandbox path for a chat file."""
    return f"{_files_dir(context)}/{filename}"


async def _read_sandbox_text(user_id: str, filename: str, context: AgentContext) -> Optional[str]:
    """Read a text file from the sandbox. Returns None if not found."""
    from modules.tools.implementations.code_execution import read_sandbox_file
    data = await read_sandbox_file(user_id, _sandbox_path(filename, context))
    if data is None:
        return None
    return data.decode("utf-8", errors="replace")




# ============================================================================
# Tool implementations
# ============================================================================

async def write_chat_file_impl(
    context: AgentContext,
    filename: str,
    content: str
):
    """Write file to sandbox in the bot's chat_files directory."""
    try:
        entry = await _get_sandbox(context.user_id)
        # Ensure the chat_files directory exists
        chat_dir = _files_dir(context)
        await entry.sbx.commands.run(f"mkdir -p {chat_dir}", timeout=5)
        await entry.sbx.files.write(_sandbox_path(filename, context), content)

        yield {
            "success": True,
            "filename": filename,
            "sandbox_path": _sandbox_path(filename, context),
            "message": f"Wrote {filename} (available at {_sandbox_path(filename, context)})"
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
