"""
Code Execution Implementation with Virtual Persistent Filesystem

Provides a persistent filesystem experience backed by the database:
- All chat files are mounted into execution environment
- Agent can read/write files naturally across executions
- Changes are automatically synced back to DB
- Temp directory is cleaned up after each run
"""
from modules.agent.context import AgentContext
from models.sse import SSEEvent
from typing import Optional, Dict, Any, AsyncGenerator, List, Set
from pydantic import BaseModel, Field
from utils.logger import get_logger
import subprocess
import tempfile
import os
import shutil
import hashlib
from pathlib import Path
from datetime import datetime
import json
import time

logger = get_logger(__name__)


def _wrap_code_for_notebook_mode(user_code: str) -> str:
    """
    Wrap user code with state persistence logic for notebook mode.
    
    Loads state from .finch_state.pkl before execution,
    saves state after execution.
    
    This allows variables, imports, and functions to persist
    between execute_code calls (like Jupyter cells).
    
    CRITICAL: State file is saved in working directory so it gets
    synced back to DB by VirtualFilesystem.sync_changes()
    """
    load_state = '''import pickle as __p, os as __o
if __o.path.exists('.finch_state.pkl'):
    try:
        with open('.finch_state.pkl', 'rb') as __f: globals().update(__p.load(__f))
    except: pass

'''
    
    save_state = '''
try:
    with open('.finch_state.pkl', 'wb') as __f:
        __p.dump({k: v for k, v in globals().items() 
                 if not k.startswith('_') and k not in ['pickle', 'os', 'sys']
                 and __p.dumps(v) or True}, __f)
except: pass
'''
    
    return load_state + user_code + save_state


def _save_code_execution_log(
    user_id: str,
    chat_id: str,
    execution_data: Dict[str, Any]
):
    """
    Save code execution log to file for debugging
    
    Saves to: backend/chat_logs/{date}/{timestamp}_{chat_id}/code_executions/{timestamp}_{filename}.json
    """
    from config import Config
    from modules.agent.chat_logger import get_chat_log_dir
    
    # Only log if DEBUG_CHAT_LOGS is enabled
    if not Config.DEBUG_CHAT_LOGS:
        return
    
    try:
        # Get backend directory (4 levels up from implementations/)
        # Path: backend/modules/tools/implementations/code_execution.py
        backend_dir = Path(__file__).parent.parent.parent.parent
        
        # Get the chat log directory (using shared helper function)
        chat_log_dir = get_chat_log_dir(chat_id, backend_dir)
        code_log_dir = chat_log_dir / "code_executions"
        code_log_dir.mkdir(parents=True, exist_ok=True)
        
        # Create filename with timestamp and execution filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        exec_filename = execution_data.get("execution_filename", "script")
        # Sanitize filename for safe filesystem use
        safe_exec_filename = exec_filename.replace("/", "_").replace("\\", "_").replace(".py", "")
        log_filename = f"{timestamp}_{safe_exec_filename}.json"
        log_filepath = code_log_dir / log_filename
        
        # Save execution data
        logger.debug(f"Writing code execution log to: {log_filepath}")
        with open(log_filepath, "w") as f:
            json.dump(execution_data, f, indent=2)
        
        # Verify file was written
        if log_filepath.exists():
            logger.info(f"💾 Saved code execution log to: {log_filepath}")
        else:
            logger.error(f"File write appeared to succeed but file not found: {log_filepath}")
        
    except Exception as e:
        logger.error(f"Failed to save code execution log: {e}", exc_info=True)


class ExecuteCodeParams(BaseModel):
    """Execute Python code"""
    code: Optional[str] = Field(
        None,
        description="Python code to execute directly in sandbox (provide this OR filename). Code runs immediately without creating any file - only output files are saved."
    )
    filename: Optional[str] = Field(
        None,
        description="Filename of saved code in chat directory to execute (provide this OR code). This runs an existing saved file from the filesystem."
    )
    mode: Optional[str] = Field(
        "isolated",
        description="Execution mode: 'isolated' (default, fresh process each time) or 'notebook' (persistent state like Jupyter)"
    )


class VirtualFilesystem:
    """
    Virtual filesystem that syncs with database.
    
    Provides persistent file storage across code executions while
    keeping everything in the database.
    """
    
    def __init__(self, user_id: str, chat_id: str):
        self.user_id = user_id
        self.chat_id = chat_id
        self.temp_dir = None
        self.file_hashes = {}  # Track file state before execution
        self.exclude_from_sync = set()  # Files to exclude from syncing (e.g., execution scripts)
    
    def setup(self) -> str:
        """
        Create temp directory and mount all chat files + API docs.
        
        Returns:
            Path to temp directory
        """
        from modules.resource_manager import resource_manager
        
        # Create temp directory
        self.temp_dir = tempfile.mkdtemp(prefix='vfs_')
        logger.info(f"Created virtual filesystem at: {self.temp_dir}")
        
        # Mount API documentation (progressive disclosure)
        self._mount_api_docs()
        # Exclude APIs directory from sync - these are system docs, not user files
        self.exclude_from_sync.add('apis')
        
        # Mount finch_runtime module for discoverability
        self._mount_finch_runtime()
        # Exclude finch_runtime from sync - this is a system file, not a user file
        self.exclude_from_sync.add('finch_runtime.py')
        
        # Note: .finch_state.pkl is NOT excluded - it's a user file that persists notebook state
        
        # Load all existing chat files from DB
        chat_files = resource_manager.list_chat_files(
            self.user_id,
            self.chat_id,
            pattern="*"
        )
        
        mounted_count = 0
        for file_info in chat_files:
            filename = file_info['name']
            
            # Read file content from DB
            content = resource_manager.read_chat_file(
                self.user_id,
                self.chat_id,
                filename
            )
            
            if content is not None:
                # Write to temp directory
                file_path = os.path.join(self.temp_dir, filename)
                
                # Create subdirectories if needed
                file_dir = os.path.dirname(file_path)
                if file_dir:
                    os.makedirs(file_dir, exist_ok=True)
                
                # Detect if this is base64-encoded binary data
                is_binary = False
                try:
                    # Try to detect base64 encoded binary files
                    # Strip any whitespace that might have been added during storage
                    content_stripped = content.strip()
                    # Check if content looks like base64 (only alphanumeric, +, /, =)
                    if len(content_stripped) > 100 and all(c in 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/=\n' for c in content_stripped[:100]):
                        # Try to decode as base64
                        import base64
                        try:
                            # Remove any newlines/whitespace from base64 string before decoding
                            content_clean = content_stripped.replace('\n', '').replace('\r', '').replace(' ', '')
                            binary_data = base64.b64decode(content_clean)
                            # If successful and looks like binary file (images, pickles, etc), it's binary
                            # Check for common binary file signatures:
                            # - PNG: \x89PNG
                            # - JPEG: \xff\xd8
                            # - GIF: GIF
                            # - BMP: BM
                            # - Python pickle: \x80 (pickle protocol 2+) or other non-text bytes
                            is_likely_binary = (
                                binary_data[:4] == b'\x89PNG' or 
                                binary_data[:2] in [b'\xff\xd8', b'GIF', b'BM'] or
                                binary_data[:1] == b'\x80' or  # pickle protocol 2+
                                any(b < 0x20 and b not in [0x09, 0x0a, 0x0d] for b in binary_data[:50])  # non-printable bytes (excluding tab, newline, CR)
                            )
                            if is_likely_binary:
                                is_binary = True
                                with open(file_path, 'wb') as f:
                                    f.write(binary_data)
                                self.file_hashes[filename] = hashlib.md5(binary_data).hexdigest()
                        except Exception:
                            pass
                except Exception:
                    pass
                
                if not is_binary:
                    # Regular text file
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(content)
                    self.file_hashes[filename] = self._hash_content(content)
                
                mounted_count += 1
        
        if mounted_count > 0:
            logger.info(f"Mounted {mounted_count} existing files from chat resources")
        
        return self.temp_dir
    
    def _mount_api_docs(self):
        """
        Mount API documentation from tools marked with api_docs_only=True.
        
        This implements progressive disclosure - tools are discovered on-demand
        by exploring the filesystem rather than loaded into context upfront.
        """
        from modules.tools.registry import tool_registry
        
        # Get tools marked for API docs only
        api_tools = tool_registry.get_api_docs_only_tools()
        
        if not api_tools:
            return
        
        # Create /apis directory in temp filesystem
        apis_dir = os.path.join(self.temp_dir, 'apis')
        os.makedirs(apis_dir, exist_ok=True)
        
        # Write each tool's documentation as a file
        for tool in api_tools:
            # Create filename from tool name
            filename = f"{tool.name}.md"
            filepath = os.path.join(apis_dir, filename)
            
            # Format tool documentation
            doc_content = self._format_tool_docs(tool)
            
            with open(filepath, 'w') as f:
                f.write(doc_content)
        
        logger.info(f"Mounted {len(api_tools)} API docs in /apis/ for progressive discovery")
    
    def _mount_finch_runtime(self):
        """
        Mount finch_runtime.py into the temp filesystem for discoverability.
        
        This allows the LLM to:
        1. See that finch_runtime exists when exploring the filesystem
        2. Read the source code to discover available methods
        3. Understand the API without relying solely on tool description
        """
        try:
            # Get path to finch_runtime.py
            tools_dir = os.path.join(os.path.dirname(__file__), '..')
            finch_runtime_path = os.path.join(tools_dir, 'finch_runtime.py')
            
            if os.path.exists(finch_runtime_path):
                # Read the source
                with open(finch_runtime_path, 'r') as f:
                    content = f.read()
                
                # Write to temp filesystem
                dest_path = os.path.join(self.temp_dir, 'finch_runtime.py')
                with open(dest_path, 'w') as f:
                    f.write(content)
                
                logger.info("Mounted finch_runtime.py for progressive discovery")
        except Exception as e:
            logger.warning(f"Failed to mount finch_runtime.py: {e}")
    
    @staticmethod
    def _format_tool_docs(tool) -> str:
        """Format tool documentation for filesystem"""
        lines = [
            f"# {tool.name}",
            "",
            tool.description,
            "",
            "## Parameters",
            ""
        ]
        
        # Add parameter documentation
        properties = tool.parameters_schema.get("properties", {})
        required = tool.parameters_schema.get("required", [])
        
        for param_name, param_schema in properties.items():
            is_required = param_name in required
            param_type = param_schema.get("type", "any")
            param_desc = param_schema.get("description", "")
            
            req_marker = " (required)" if is_required else " (optional)"
            lines.append(f"### `{param_name}` - {param_type}{req_marker}")
            if param_desc:
                lines.append(f"{param_desc}")
            lines.append("")
        
        return "\n".join(lines)

    
    def sync_changes(self) -> Dict[str, List[str]]:
        """
        Sync changes back to database.
        
        Detects:
        - New files (didn't exist before)
        - Modified files (hash changed)
        - Deleted files (existed before, now gone)
        
        Returns:
            Dict with lists of new, modified, and deleted files
        """
        from modules.resource_manager import resource_manager
        
        if not self.temp_dir or not os.path.exists(self.temp_dir):
            return {"new": [], "modified": [], "deleted": []}
        
        changes = {"new": [], "modified": [], "deleted": []}
        current_files = set()
        
        # Scan all files in temp directory
        for root, dirs, files in os.walk(self.temp_dir):
            for filename in files:
                file_path = os.path.join(root, filename)
                relative_path = os.path.relpath(file_path, self.temp_dir)
                
                # Skip Python cache and hidden files (except .finch_state.pkl for notebook mode)
                if '__pycache__' in relative_path:
                    continue
                if relative_path.startswith('.') and relative_path != '.finch_state.pkl':
                    continue
                
                # Skip files/directories marked for exclusion (e.g., temporary execution scripts, system files)
                # Check if file itself is excluded OR if it's inside an excluded directory
                should_exclude = False
                if relative_path in self.exclude_from_sync:
                    should_exclude = True
                else:
                    # Check if file is inside an excluded directory (e.g., apis/some_file.md)
                    for excluded_path in self.exclude_from_sync:
                        if relative_path.startswith(excluded_path + '/') or relative_path.startswith(excluded_path + os.sep):
                            should_exclude = True
                            break
                
                if should_exclude:
                    continue
                
                current_files.add(relative_path)
                
                # Try to read as text first, then fall back to binary
                is_binary = False
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    current_hash = self._hash_content(content)
                except UnicodeDecodeError:
                    # Binary file - read as bytes and base64 encode
                    is_binary = True
                    with open(file_path, 'rb') as f:
                        binary_content = f.read()
                    import base64
                    content = base64.b64encode(binary_content).decode('ascii')
                    current_hash = hashlib.md5(binary_content).hexdigest()
                    logger.info(f"Detected binary file: {relative_path} ({len(binary_content)} bytes)")
                
                # Check if new or modified
                if relative_path not in self.file_hashes:
                    # New file
                    resource_manager.write_chat_file(
                        self.user_id,
                        self.chat_id,
                        relative_path,
                        content
                    )
                    changes["new"].append(relative_path)
                    file_type = " (binary)" if is_binary else ""
                    logger.info(f"New file{file_type}: {relative_path}")
                
                elif current_hash != self.file_hashes[relative_path]:
                    # Modified file
                    resource_manager.write_chat_file(
                        self.user_id,
                        self.chat_id,
                        relative_path,
                        content
                    )
                    changes["modified"].append(relative_path)
                    file_type = " (binary)" if is_binary else ""
                    logger.info(f"Modified file{file_type}: {relative_path}")
        
        # Check for deleted files
        for old_file in self.file_hashes.keys():
            if old_file not in current_files:
                resource_manager.delete_chat_file(
                    self.user_id,
                    self.chat_id,
                    old_file
                )
                changes["deleted"].append(old_file)
                logger.info(f"Deleted file: {old_file}")
        
        return changes
    
    def cleanup(self):
        """Remove temp directory"""
        if self.temp_dir and os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir, ignore_errors=True)
            logger.info(f"Cleaned up virtual filesystem")
    
    @staticmethod
    def _hash_content(content: str) -> str:
        """Hash file content for change detection"""
        return hashlib.md5(content.encode('utf-8')).hexdigest()


async def execute_code_impl(
    params: ExecuteCodeParams,
    context: AgentContext
) -> AsyncGenerator[SSEEvent | Dict[str, Any], None]:
    """Execute Python code with virtual persistent filesystem"""
    from modules.resource_manager import resource_manager
    
    # Determine execution mode
    exec_mode = params.mode or "isolated"
    
    yield SSEEvent(event="tool_status", data={
        "status": "loading",
        "message": f"Setting up environment ({'notebook mode' if exec_mode == 'notebook' else 'isolated mode'})..."
    })
    
    vfs = VirtualFilesystem(context.user_id, context.chat_id)
    
    try:
        # Determine execution mode
        is_inline = params.code is not None
        execution_mode = "inline"
        script_path = None
        code = None
        
        if params.code:
            # Inline code - execute directly without creating files in VFS
            code = params.code
            source = "inline code"
            execution_mode = "inline"
            
            # Check for special kernel commands in notebook mode
            if exec_mode == "notebook" and code.strip() == "__reset_kernel__":
                # Reset kernel by deleting state file
                try:
                    resource_manager.delete_chat_file(context.user_id, context.chat_id, ".finch_state.pkl")
                    yield {"success": True, "message": "♻️ Kernel state reset - starting fresh!"}
                    return
                except:
                    yield {"success": True, "message": "♻️ Kernel state reset (no previous state)"}
                    return
                    
        elif params.filename:
            # File-based execution - run existing file from VFS
            code = resource_manager.read_chat_file(
                context.user_id,
                context.chat_id,
                params.filename
            )
            if not code:
                yield {"success": False, "error": f"File '{params.filename}' not found"}
                return
            source = f"file '{params.filename}'"
            execution_mode = "file"
        else:
            yield {"success": False, "error": "Provide either 'code' or 'filename'"}
            return
        
        # Wrap code for notebook mode (state persistence)
        if exec_mode == "notebook":
            code = _wrap_code_for_notebook_mode(code)
        
        # Setup virtual filesystem (mount existing files)
        temp_dir = vfs.setup()
        
        # Determine where to write the script
        if execution_mode == "inline":
            # For inline code, write to a temp file OUTSIDE the VFS to avoid it showing up in filesystem
            import tempfile
            temp_script_fd, script_path = tempfile.mkstemp(suffix='.py', prefix='inline_', dir=None)
            os.close(temp_script_fd)  # Close the file descriptor, we'll write to it below
        else:
            # For file execution, the file is already in the VFS
            script_path = os.path.join(temp_dir, params.filename)
        
        # Track execution start time for logging
        execution_start_time = time.time()
        execution_timestamp = datetime.now().isoformat()
        
        # Get list of mounted files for logging
        mounted_files = []
        if os.path.exists(temp_dir):
            for root, dirs, files in os.walk(temp_dir):
                for f in files:
                    rel_path = os.path.relpath(os.path.join(root, f), temp_dir)
                    if not rel_path.startswith('.') and '__pycache__' not in rel_path:
                        mounted_files.append(rel_path)
        
        # Log detailed execution info for debugging
        logger.info(f"=" * 80)
        logger.info(f"CODE EXECUTION START")
        logger.info(f"Timestamp: {execution_timestamp}")
        logger.info(f"Source: {source}")
        logger.info(f"Execution mode: {execution_mode}")
        logger.info(f"Script path: {script_path}")
        logger.info(f"Working dir: {temp_dir}")
        logger.info(f"User: {context.user_id}, Chat: {context.chat_id}")
        logger.info(f"Mounted files: {len(mounted_files)} files")
        if mounted_files:
            logger.info(f"  Available files: {', '.join(mounted_files[:10])}")
            if len(mounted_files) > 10:
                logger.info(f"  ... and {len(mounted_files) - 10} more")
        logger.info(f"Code length: {len(code)} characters")
        logger.info(f"Code to execute:\n{'-' * 40}\n{code}\n{'-' * 40}")
        
        yield SSEEvent(event="tool_status", data={
            "status": "executing",
            "message": f"Running {source}..."
        })
        
        try:
            # Write code to script file
            # For inline: writes to temp file outside VFS
            # For file execution: file already exists in VFS, but we write it anyway for consistency
            with open(script_path, 'w') as f:
                f.write(code)
            
            # Set up environment with proper PYTHONPATH for finch_runtime access
            # Go up 3 levels: implementations -> tools -> modules -> backend
            backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
            env = os.environ.copy()
            env['FMP_API_KEY'] = os.getenv('FMP_API_KEY', '')
            env['POLYGON_API_KEY'] = os.getenv('POLYGON_API_KEY', '')
            
            # Add both temp_dir and backend directory to PYTHONPATH
            # temp_dir: allows "from finch_runtime import X" (direct import)
            # backend_dir: allows "from modules.tools.finch_runtime import X" (module import)
            if 'PYTHONPATH' in env:
                env['PYTHONPATH'] = f"{temp_dir}:{backend_dir}:{env['PYTHONPATH']}"
            else:
                env['PYTHONPATH'] = f"{temp_dir}:{backend_dir}"
            
            # Suppress logging noise in sandbox environment
            env['PYTHONWARNINGS'] = 'ignore'  # Suppress Python warnings (e.g., opentelemetry)
            env['LOG_LEVEL'] = 'ERROR'  # Only show ERROR logs, suppress INFO/DEBUG
            env['CODE_SANDBOX'] = 'true'  # Flag to indicate we're in sandbox (for future use)
            
            # Execute with subprocess
            result = subprocess.run(
                ['python', script_path],
                capture_output=True,
                text=True,
                timeout=60,
                cwd=temp_dir,
                env=env
            )
            
            # Log execution output to console for debugging
            logger.info(f"Code execution completed with exit code: {result.returncode}")
            if result.stdout:
                logger.info(f"STDOUT:\n{result.stdout}")
            if result.stderr:
                logger.warning(f"STDERR:\n{result.stderr}")
            
            # Sync changes back to database
            changes = vfs.sync_changes()
            
            # Calculate execution duration
            execution_duration = time.time() - execution_start_time
            
            # Log file changes
            if changes["new"]:
                logger.info(f"New files created: {', '.join(changes['new'])}")
            if changes["modified"]:
                logger.info(f"Files modified: {', '.join(changes['modified'])}")
            if changes["deleted"]:
                logger.info(f"Files deleted: {', '.join(changes['deleted'])}")
            
            # Save code execution log
            execution_log_data = {
                "timestamp": execution_timestamp,
                "execution_mode": execution_mode,
                "execution_filename": params.filename if params.filename else "inline_code",
                "source": source,
                "user_id": context.user_id,
                "chat_id": context.chat_id,
                "code": code,
                "code_length": len(code),
                "working_directory": temp_dir,
                "script_path": script_path,
                "exit_code": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "execution_duration_seconds": execution_duration,
                "mounted_files": mounted_files,
                "file_changes": changes,
                "success": result.returncode == 0
            }
            _save_code_execution_log(context.user_id, context.chat_id, execution_log_data)
            
            # Emit resource events for new/modified files so frontend knows about them
            for filename in changes["new"] + changes["modified"]:
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
                
                # Get file content to determine size
                try:
                    content = resource_manager.read_chat_file(context.user_id, context.chat_id, filename)
                    size_bytes = len(content.encode('utf-8')) if isinstance(content, str) else len(content)
                except:
                    size_bytes = 0
                
                yield SSEEvent(
                    event="resource",
                    data={
                        "resource_type": "file",
                        "tool_name": "execute_code",
                        "title": filename,
                        "data": {
                            "filename": filename,
                            "file_type": file_type,
                            "size_bytes": size_bytes
                        }
                    }
                )
            
            # Clean up temp directory
            vfs.cleanup()
            
            # Clean up inline script temp file if it exists
            if execution_mode == "inline" and script_path and os.path.exists(script_path):
                try:
                    os.remove(script_path)
                except:
                    pass
            
            # Truncate output if needed
            MAX_OUTPUT_SIZE = 8000
            stdout_truncated = result.stdout
            stderr_truncated = result.stderr
            truncation_note = ""
            
            if len(stdout_truncated) > MAX_OUTPUT_SIZE:
                stdout_truncated = stdout_truncated[:MAX_OUTPUT_SIZE] + "\n... [OUTPUT TRUNCATED]"
                truncation_note = " (output truncated)"
            
            if len(stderr_truncated) > MAX_OUTPUT_SIZE:
                stderr_truncated = stderr_truncated[:MAX_OUTPUT_SIZE] + "\n... [OUTPUT TRUNCATED]"
            
            if result.returncode != 0:
                # Format error message with stderr for user
                error_msg = f"Code failed with exit code {result.returncode}\n\n"
                if stderr_truncated:
                    error_msg += f"**Error output:**\n```\n{stderr_truncated}\n```"
                if stdout_truncated:
                    error_msg += f"\n\n**Standard output:**\n```\n{stdout_truncated}\n```"
                
                # Clean up inline script temp file if it exists
                if execution_mode == "inline" and script_path and os.path.exists(script_path):
                    try:
                        os.remove(script_path)
                    except:
                        pass
                
                yield {
                    "success": False,
                    "error": error_msg,
                    "stderr": stderr_truncated,
                    "stdout": stdout_truncated,
                    "changes": changes
                }
                return
            
            yield SSEEvent(event="tool_status", data={
                "status": "complete",
                "message": f"Execution complete{truncation_note}"
            })
            
            yield {
                "success": True,
                "stdout": stdout_truncated,
                "stderr": stderr_truncated,
                "changes": changes,
                "message": f"Code executed successfully{truncation_note}"
            }
        
        except subprocess.TimeoutExpired:
            vfs.cleanup()
            # Clean up inline script temp file
            if execution_mode == "inline" and script_path and os.path.exists(script_path):
                try:
                    os.remove(script_path)
                except:
                    pass
            yield {"success": False, "error": "Code execution timed out after 60 seconds"}
        
        except Exception as e:
            vfs.cleanup()
            # Clean up inline script temp file
            if execution_mode == "inline" and script_path and os.path.exists(script_path):
                try:
                    os.remove(script_path)
                except:
                    pass
            raise e
    
    except Exception as e:
        logger.error(f"Error executing code: {str(e)}", exc_info=True)
        vfs.cleanup()
        # Clean up inline script temp file
        if execution_mode == "inline" and script_path and os.path.exists(script_path):
            try:
                os.remove(script_path)
            except:
                pass
        yield {"success": False, "error": str(e)}

