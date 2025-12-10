"""
File Management Implementation (Manus-inspired)

File manipulation tools for chat sessions.
"""
from modules.agent.context import AgentContext
from models.sse import SSEEvent
from pydantic import BaseModel, Field
from utils.logger import get_logger
import re

logger = get_logger(__name__)


class ReplaceInFileParams(BaseModel):
    """Replace text in a file"""
    filename: str = Field(..., description="Filename in current chat directory")
    old_str: str = Field(..., description="Text to find")
    new_str: str = Field(..., description="Text to replace with")


class FindInFileParams(BaseModel):
    """Search for pattern in file"""
    filename: str = Field(..., description="Filename in current chat directory")
    pattern: str = Field(..., description="Regular expression pattern to search for")


# Basic file tools (read, write, list) plus advanced tools (replace, find)

def replace_in_chat_file_impl(
    params: ReplaceInFileParams,
    context: AgentContext
):
    """Replace text in file"""
    from modules.resource_manager import resource_manager
    
    try:
        # Read file
        content = resource_manager.read_chat_file(
            context.user_id,
            context.chat_id,
            params.filename
        )
        
        if content is None:
            return {
                "success": False,
                "error": f"File '{params.filename}' not found"
            }
        
        # Count occurrences
        count = content.count(params.old_str)
        
        if count == 0:
            return {
                "success": False,
                "error": f"Text not found: '{params.old_str}'"
            }
        
        # Replace
        new_content = content.replace(params.old_str, params.new_str)
        
        # Write back
        path = resource_manager.write_chat_file(
            context.user_id,
            context.chat_id,
            params.filename,
            new_content
        )
        
        return {
            "success": True,
            "filename": params.filename,
            "replacements": count,
            "message": f"Replaced {count} occurrence(s) of '{params.old_str}'"
        }
    
    except Exception as e:
        logger.error(f"Error replacing in file: {str(e)}", exc_info=True)
        return {"success": False, "error": str(e)}


def find_in_chat_file_impl(
    params: FindInFileParams,
    context: AgentContext
):
    """Find pattern in file"""
    from modules.resource_manager import resource_manager
    
    try:
        # Read file
        content = resource_manager.read_chat_file(
            context.user_id,
            context.chat_id,
            params.filename
        )
        
        if content is None:
            return {
                "success": False,
                "error": f"File '{params.filename}' not found"
            }
        
        # Search
        lines = content.split('\n')
        matches = []
        
        for i, line in enumerate(lines):
            if re.search(params.pattern, line):
                matches.append({
                    "line": i,
                    "content": line.strip()
                })
        
        return {
            "success": True,
            "filename": params.filename,
            "pattern": params.pattern,
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
    """Write file to chat directory"""
    from modules.resource_manager import resource_manager
    
    try:
        file_id = resource_manager.write_chat_file(
            context.user_id,
            context.chat_id,
            filename,
            content
        )
        
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
        elif filename.endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp', '.svg')):
            file_type = "image"
        
        # Emit SSE resource event so frontend shows the file
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
    filename: str
):
    """Read file from chat directory"""
    from modules.resource_manager import resource_manager
    
    try:
        content = resource_manager.read_chat_file(
            context.user_id,
            context.chat_id,
            filename
        )
        if content is None:
            return {"success": False, "error": f"File '{filename}' not found"}
        
        return {
            "success": True,
            "content": content,
            "filename": filename
        }
    except Exception as e:
        logger.error(f"Error reading chat file: {str(e)}", exc_info=True)
        return {"success": False, "error": str(e)}

