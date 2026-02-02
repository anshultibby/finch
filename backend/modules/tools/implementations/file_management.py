"""
File Management Implementation (Manus-inspired)

File manipulation tools for chat sessions.
"""
from modules.agent.context import AgentContext
from models.sse import SSEEvent
from pydantic import BaseModel, Field
from typing import Optional, List
from utils.logger import get_logger
import re

logger = get_logger(__name__)


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


# Basic file tools (read, write, list) plus advanced tools (replace, find)

async def replace_in_chat_file_impl(
    old_str: Optional[str],
    new_str: Optional[str],
    filename: str,
    context: AgentContext,
    replace_all: bool = False,
    edits: Optional[List[EditItem]] = None
):
    """Replace text in file with streaming content to frontend.
    
    Supports two modes:
    1. Single edit: old_str + new_str (legacy mode)
    2. Multiple edits: edits list with multiple EditItem objects
    """
    from modules.resource_manager import resource_manager
    
    try:
        # Build list of edits to apply
        edit_list: List[EditItem] = []
        
        if edits:
            # Multiple edits mode - convert dicts to EditItem if needed
            for edit in edits:
                if isinstance(edit, dict):
                    edit_list.append(EditItem(**edit))
                elif isinstance(edit, EditItem):
                    edit_list.append(edit)
                else:
                    yield {
                        "success": False,
                        "error": f"Invalid edit item type: {type(edit).__name__}"
                    }
                    return
        elif old_str is not None and new_str is not None:
            # Single edit mode (backward compatible)
            edit_list = [EditItem(old_str=old_str, new_str=new_str, replace_all=replace_all)]
        else:
            yield {
                "success": False,
                "error": "Must provide either (old_str + new_str) or edits list"
            }
            return
        
        # Read file
        content = resource_manager.read_chat_file(
            context.user_id,
            context.chat_id,
            filename
        )
        
        if content is None:
            yield {
                "success": False,
                "error": f"File '{filename}' not found"
            }
            return
        
        # Apply each edit in sequence
        total_replacements = 0
        edit_results = []
        
        for i, edit in enumerate(edit_list):
            # Count occurrences
            count = content.count(edit.old_str)
            
            if count == 0:
                # Truncate long strings in error message
                display_str = f"'{edit.old_str[:100]}...'" if len(edit.old_str) > 100 else f"'{edit.old_str}'"
                yield {
                    "success": False,
                    "error": f"Edit {i + 1}: Text not found: {display_str}",
                    "partial_results": edit_results if edit_results else None
                }
                return
            
            # If not replace_all and multiple matches, fail for safety
            if count > 1 and not edit.replace_all:
                yield {
                    "success": False,
                    "error": f"Edit {i + 1}: Found {count} occurrences of the text. Either:\n"
                             f"1. Include more surrounding context to make it unique, OR\n"
                             f"2. Set replace_all=True to replace all {count} occurrences",
                    "partial_results": edit_results if edit_results else None
                }
                return
            
            # Replace (single or all based on flag)
            if edit.replace_all:
                content = content.replace(edit.old_str, edit.new_str)
                actual_count = count
            else:
                content = content.replace(edit.old_str, edit.new_str, 1)
                actual_count = 1
            
            total_replacements += actual_count
            edit_results.append({
                "edit_index": i + 1,
                "replacements": actual_count
            })
        
        # Determine file type
        file_type = "text"
        if filename.endswith('.py'):
            file_type = "python"
        elif filename.endswith('.md'):
            file_type = "markdown"
        elif filename.endswith('.csv'):
            file_type = "csv"
        elif filename.endswith('.json'):
            file_type = "json"
        elif filename.endswith('.html'):
            file_type = "html"
        
        # Stream the updated file content to frontend
        yield SSEEvent(
            event="file_content",
            data={
                "tool_call_id": context.current_tool_call_id or "",
                "filename": filename,
                "content": content,
                "file_type": file_type,
                "is_complete": False
            }
        )
        
        # Write back
        file_id = resource_manager.write_chat_file(
            context.user_id,
            context.chat_id,
            filename,
            content
        )
        
        # Send completion signal
        yield SSEEvent(
            event="file_content",
            data={
                "tool_call_id": context.current_tool_call_id or "",
                "filename": filename,
                "content": "",
                "file_type": file_type,
                "is_complete": True
            }
        )
        
        # Emit SSE resource event so frontend updates the file in resources
        yield SSEEvent(
            event="resource",
            data={
                "resource_type": "file",
                "tool_name": "replace_in_chat_file",
                "title": filename,
                "data": {
                    "filename": filename,
                    "file_type": file_type,
                    "size_bytes": len(content.encode('utf-8')),
                    "file_id": file_id
                }
            }
        )
        
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


def find_in_chat_file_impl(
    pattern: str,
    filename: str,
    context: AgentContext
):
    """Find pattern in file"""
    from modules.resource_manager import resource_manager
    
    try:
        # Read file
        content = resource_manager.read_chat_file(
            context.user_id,
            context.chat_id,
            filename
        )
        
        if content is None:
            return {
                "success": False,
                "error": f"File '{filename}' not found"
            }
        
        # Search
        lines = content.split('\n')
        matches = []
        
        for i, line in enumerate(lines):
            if re.search(pattern, line):
                matches.append({
                    "line": i,
                    "content": line.strip()
                })
        
        return {
            "success": True,
            "filename": filename,
            "pattern": pattern,
            "matches": matches,
            "count": len(matches)
        }
    
    except re.error as e:
        return {
            "success": False,
            "error": f"Invalid regex pattern: {str(e)}"
        }
    except Exception as e:
        logger.error(f"Error searching file: {str(e)}", exc_info=True)
        return {"success": False, "error": str(e)}


# Add basic file tools

def list_chat_files_impl(
    context: AgentContext,
    directory: str = ""
):
    """List files in chat directory (Cursor-style progressive exploration)"""
    from modules.resource_manager import resource_manager
    import os
    
    try:
        # Get all files from DB
        all_files = resource_manager.list_chat_files(context.user_id, context.chat_id)
        
        # Normalize directory path
        dir_path = directory.strip().strip('/')
        
        # Filter files in the specified directory
        files_in_dir = []
        subdirs = set()
        
        for file_obj in all_files:
            filename = file_obj['name']
            
            # Check if file is in the specified directory
            if dir_path:
                # File must start with directory path
                if not filename.startswith(dir_path + '/'):
                    continue
                # Get relative path from this directory
                relative = filename[len(dir_path)+1:]
            else:
                # Root directory
                relative = filename
            
            # Check if this is a direct child or in a subdirectory
            parts = relative.split('/')
            
            if len(parts) == 1:
                # Direct file in this directory
                files_in_dir.append({
                    **file_obj,
                    "relative_name": relative
                })
            else:
                # File in subdirectory - track the subdirectory
                subdirs.add(parts[0])
        
        # Format output similar to Cursor's list_dir
        result_lines = []
        
        current_path = f"/{dir_path}" if dir_path else "/"
        result_lines.append(f"Contents of {current_path}:\n")
        
        # List subdirectories first
        if subdirs:
            result_lines.append("📁 Directories:")
            for subdir in sorted(subdirs):
                result_lines.append(f"  {subdir}/")
            result_lines.append("")
        
        # List files
        if files_in_dir:
            result_lines.append("📄 Files:")
            for f in sorted(files_in_dir, key=lambda x: x['relative_name']):
                size_kb = f['size'] / 1024 if f['size'] else 0
                result_lines.append(f"  {f['relative_name']:40} ({size_kb:>8.1f} KB)  {f.get('type', 'unknown')}")
        
        if not subdirs and not files_in_dir:
            result_lines.append("(empty directory)")
        
        result_lines.append(f"\n📊 Summary: {len(subdirs)} directories, {len(files_in_dir)} files")
        
        return {
            "success": True,
            "directory": current_path,
            "subdirectories": sorted(list(subdirs)),
            "files": files_in_dir,
            "summary": "\n".join(result_lines)
        }
    except Exception as e:
        logger.error(f"Error listing chat files: {str(e)}", exc_info=True)
        return {"success": False, "error": str(e)}


def show_filesystem_tree_impl(context: AgentContext):
    """Show chat filesystem as a tree"""
    from modules.resource_manager import resource_manager
    import tempfile
    import os
    import shutil
    
    try:
        # Create temp directory to mount files
        temp_dir = tempfile.mkdtemp(prefix='tree_view_')
        
        try:
            # Get all chat files
            chat_files = resource_manager.list_chat_files(
                context.user_id,
                context.chat_id,
                pattern="*"
            )
            
            # Mount files to temp directory
            for file_info in chat_files:
                filename = file_info['name']
                
                # Read file content from DB
                content = resource_manager.read_chat_file(
                    context.user_id,
                    context.chat_id,
                    filename
                )
                
                if content is not None:
                    file_path = os.path.join(temp_dir, filename)
                    
                    # Create subdirectories if needed
                    file_dir = os.path.dirname(file_path)
                    if file_dir:
                        os.makedirs(file_dir, exist_ok=True)
                    
                    # Write file (just for tree visualization)
                    try:
                        with open(file_path, 'w', encoding='utf-8') as f:
                            f.write(content)
                    except:
                        # If can't write as text, skip (binary files don't affect tree)
                        pass
            
            # Generate tree visualization
            tree_lines = ["# Chat Filesystem Tree\n"]
            
            # Build tree structure
            def add_tree_lines(directory, prefix="", is_last=True):
                """Recursively build tree lines"""
                items = []
                try:
                    for item in sorted(os.listdir(directory)):
                        if item.startswith('.') or item == '__pycache__':
                            continue
                        item_path = os.path.join(directory, item)
                        items.append((item, item_path, os.path.isdir(item_path)))
                except PermissionError:
                    return
                
                for i, (name, path, is_dir) in enumerate(items):
                    is_last_item = i == len(items) - 1
                    connector = "└── " if is_last_item else "├── "
                    tree_lines.append(f"{prefix}{connector}{name}{'/' if is_dir else ''}")
                    
                    if is_dir:
                        extension = "    " if is_last_item else "│   "
                        add_tree_lines(path, prefix + extension, is_last_item)
            
            tree_lines.append("\n```")
            tree_lines.append(".")
            add_tree_lines(temp_dir, "")
            tree_lines.append("```\n")
            
            # Add statistics
            file_count = len(chat_files)
            total_size = sum(f.get('size', 0) for f in chat_files)
            
            tree_lines.append(f"\n**Statistics:**")
            tree_lines.append(f"- Files: {file_count}")
            tree_lines.append(f"- Total Size: {total_size:,} bytes ({total_size / 1024:.1f} KB)")
            
            tree = "\n".join(tree_lines)
            
            return {
                "success": True,
                "tree": tree,
                "file_count": file_count,
                "total_size": total_size
            }
        
        finally:
            # Clean up temp directory
            shutil.rmtree(temp_dir, ignore_errors=True)
    
    except Exception as e:
        logger.error(f"Error generating filesystem tree: {str(e)}", exc_info=True)
        return {"success": False, "error": str(e)}


async def write_chat_file_impl(
    context: AgentContext,
    filename: str,
    content: str
):
    """Write file to chat directory with streaming content to frontend"""
    from modules.resource_manager import resource_manager
    
    try:
        # Determine file type first
        file_type = "text"
        if filename.endswith('.py'):
            file_type = "python"
        elif filename.endswith('.md'):
            file_type = "markdown"
        elif filename.endswith('.csv'):
            file_type = "csv"
        elif filename.endswith('.json'):
            file_type = "json"
        elif filename.endswith('.html'):
            file_type = "html"
        elif filename.endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp', '.svg')):
            file_type = "image"
        
        # Stream the file content to frontend immediately (before writing to DB)
        # This allows the side panel to show content as it's "being written"
        yield SSEEvent(
            event="file_content",
            data={
                "tool_call_id": context.current_tool_call_id or "",
                "filename": filename,
                "content": content,
                "file_type": file_type,
                "is_complete": False
            }
        )
        
        # Now write to DB
        file_id = resource_manager.write_chat_file(
            context.user_id,
            context.chat_id,
            filename,
            content
        )
        
        # Send completion signal
        yield SSEEvent(
            event="file_content",
            data={
                "tool_call_id": context.current_tool_call_id or "",
                "filename": filename,
                "content": "",  # No additional content
                "file_type": file_type,
                "is_complete": True
            }
        )
        
        # Emit SSE resource event so frontend shows the file in resources
        yield SSEEvent(
            event="resource",
            data={
                "resource_type": "file",
                "tool_name": "write_chat_file",
                "title": filename,
                "data": {
                    "filename": filename,
                    "file_type": file_type,
                    "size_bytes": len(content.encode('utf-8')),
                    "file_id": file_id
                }
            }
        )
        
        yield {
            "success": True,
            "file_id": file_id,
            "filename": filename,
            "message": f"Wrote {filename} to chat directory"
        }
    except Exception as e:
        logger.error(f"Error writing chat file: {str(e)}", exc_info=True)
        yield {"success": False, "error": str(e)}


def read_chat_file_impl(
    context: AgentContext,
    filename: str,
    start_line: Optional[int] = None,
    end_line: Optional[int] = None
):
    """
    Read file from chat directory with optional line range (like Cursor).
    
    For text files: returns content as string, optionally sliced by line range
    For images: returns image data that can be viewed by the LLM (multimodal)
    
    Args:
        context: Agent context
        filename: File to read
        start_line: 1-indexed start line (default: 1)
        end_line: 1-indexed end line, inclusive (default: last line)
    """
    from modules.resource_manager import resource_manager
    
    try:
        # Use the new method that supports images
        file_data = resource_manager.read_chat_file_with_metadata(
            context.user_id,
            context.chat_id,
            filename
        )
        
        if file_data is None:
            return {"success": False, "error": f"File '{filename}' not found"}
        
        # For images, return image data for multimodal viewing
        if file_data.get("is_image"):
            if file_data.get("image_base64"):
                return {
                    "success": True,
                    "filename": filename,
                    "file_type": "image",
                    "is_image": True,
                    "image": {
                        "type": "base64",
                        "media_type": file_data.get("media_type", "image/png"),
                        "data": file_data["image_base64"]
                    },
                    "message": f"Image '{filename}' loaded. I can now see the image content."
                }
            elif file_data.get("image_url"):
                return {
                    "success": True,
                    "filename": filename,
                    "file_type": "image",
                    "is_image": True,
                    "image_url": file_data["image_url"],
                    "message": f"Image '{filename}' is available at URL but could not be loaded for viewing."
                }
            else:
                return {
                    "success": False,
                    "error": f"Image '{filename}' exists but has no accessible content"
                }
        
        # For text files, return content (with optional line slicing)
        content = file_data.get("content", "")
        lines = content.split('\n')
        total_lines = len(lines)
        
        # Apply line range if specified
        if start_line is not None or end_line is not None:
            # Convert to 0-indexed, handle defaults
            start_idx = (start_line or 1) - 1
            end_idx = end_line or total_lines
            
            # Clamp to valid range
            start_idx = max(0, min(start_idx, total_lines - 1)) if total_lines > 0 else 0
            end_idx = max(start_idx + 1, min(end_idx, total_lines))
            
            # Slice and rejoin
            selected_lines = lines[start_idx:end_idx]
            content = '\n'.join(selected_lines)
            
            # Build navigation hints
            nav_hints = []
            if start_idx > 0:
                nav_hints.append(f"lines 1-{start_idx} above")
            if end_idx < total_lines:
                nav_hints.append(f"lines {end_idx + 1}-{total_lines} below")
            
            return {
                "success": True,
                "content": content,
                "filename": filename,
                "file_type": file_data.get("file_type", "text"),
                "start_line": start_idx + 1,
                "end_line": end_idx,
                "total_lines": total_lines,
                "navigation": f"({', '.join(nav_hints)})" if nav_hints else None
            }
        
        # No line range - return full content
        return {
            "success": True,
            "content": content,
            "filename": filename,
            "file_type": file_data.get("file_type", "text"),
            "total_lines": total_lines
        }
    except Exception as e:
        logger.error(f"Error reading chat file: {str(e)}", exc_info=True)
        return {"success": False, "error": str(e)}

