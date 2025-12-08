"""
Code Execution Tool with Virtual Persistent Filesystem

Provides a persistent filesystem experience backed by the database:
- All chat files are mounted into execution environment
- Agent can read/write files naturally across executions
- Changes are automatically synced back to DB
- Temp directory is cleaned up after each run
"""
from modules.tools import tool
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

logger = get_logger(__name__)


class ExecuteCodeParams(BaseModel):
    """Execute Python code"""
    code: Optional[str] = Field(
        None,
        description="Python code to execute (provide this OR filename)"
    )
    filename: Optional[str] = Field(
        None,
        description="Filename of saved code in chat directory (provide this OR code)"
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
                    # Check if content looks like base64 (only alphanumeric, +, /, =)
                    if len(content) > 100 and all(c in 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/=\n' for c in content[:100]):
                        # Try to decode as base64
                        import base64
                        try:
                            binary_data = base64.b64decode(content)
                            # If successful and looks like PNG/image, it's binary
                            if binary_data[:4] == b'\x89PNG' or binary_data[:2] in [b'\xff\xd8', b'GIF', b'BM']:
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
                
                # Skip Python cache and hidden files
                if '__pycache__' in relative_path or relative_path.startswith('.'):
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


@tool(
    name="execute_code",
    description="""Execute Python code with direct API access and persistent filesystem (60s timeout).

**Progressive API Discovery (Saves Context!):**
- API docs are in `/apis/` directory - discover them on-demand
- List APIs: `os.listdir('apis')` → ['get_fmp_data.md', 'get_reddit_trending_stocks.md', ...]
- Read when needed: `with open('apis/get_fmp_data.md') as f: print(f.read())`
- This is more efficient than loading all API docs into context upfront

**Direct API Access - Import finch_runtime:**
```python
from modules.tools.finch_runtime import fmp, reddit

# Financial data
quote = fmp.get_quote('AAPL')
trades = fmp.get_insider_trading('NVDA', limit=50)

# Reddit sentiment
trending = reddit.get_trending(limit=10)
```

**Quick Reference:**
fmp: `fetch()`, `get_quote()`, `get_income_statement()`, `get_balance_sheet()`, 
     `get_key_metrics()`, `get_insider_trading()`, `get_historical_prices()`
reddit: `get_trending()`, `get_ticker_sentiment()`

**Persistent Filesystem:**
Files persist across executions:
```python
df.to_csv('results.csv')  # Save
df = pd.read_csv('results.csv')  # Read later
```

**Environment:**
- Standard libs: pandas, numpy, requests, matplotlib, plotly
- FMP_API_KEY available in environment
- All previous chat files mounted
- API documentation in /apis/
- Changes auto-saved to database""",
    category="code"
)
async def execute_code(
    *,
    params: ExecuteCodeParams,
    context: AgentContext
) -> AsyncGenerator[SSEEvent | Dict[str, Any], None]:
    """Execute Python code with virtual persistent filesystem"""
    from modules.resource_manager import resource_manager
    
    yield SSEEvent(event="tool_status", data={
        "status": "loading",
        "message": "Setting up environment..."
    })
    
    vfs = VirtualFilesystem(context.user_id, context.chat_id)
    
    try:
        # Get code (from param or file)
        if params.code:
            code = params.code
            source = "inline code"
        elif params.filename:
            code = resource_manager.read_chat_file(
                context.user_id,
                context.chat_id,
                params.filename
            )
            if not code:
                yield {"success": False, "error": f"File '{params.filename}' not found"}
                return
            source = f"file '{params.filename}'"
        else:
            yield {"success": False, "error": "Provide either 'code' or 'filename'"}
            return
        
        # Setup virtual filesystem (mount existing files)
        temp_dir = vfs.setup()
        script_path = os.path.join(temp_dir, 'script.py')
        
        logger.info(f"Executing code from {source} in temp dir: {temp_dir}")
        
        yield SSEEvent(event="tool_status", data={
            "status": "executing",
            "message": f"Running {source}..."
        })
        
        try:
            # Write code to temp file (no auto-imports - agent does this explicitly)
            with open(script_path, 'w') as f:
                f.write(code)
            
            # Set up environment with proper PYTHONPATH for finch_runtime access
            backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
            env = os.environ.copy()
            env['FMP_API_KEY'] = os.getenv('FMP_API_KEY', '')
            
            # Add backend directory to PYTHONPATH so "from modules.tools.finch_runtime import X" works
            if 'PYTHONPATH' in env:
                env['PYTHONPATH'] = f"{backend_dir}:{env['PYTHONPATH']}"
            else:
                env['PYTHONPATH'] = backend_dir
            
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
            
            # Log file changes
            if changes["new"]:
                logger.info(f"New files created: {', '.join(changes['new'])}")
            if changes["modified"]:
                logger.info(f"Files modified: {', '.join(changes['modified'])}")
            if changes["deleted"]:
                logger.info(f"Files deleted: {', '.join(changes['deleted'])}")
            
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
            yield {"success": False, "error": "Code execution timed out after 60 seconds"}
        
        except Exception as e:
            vfs.cleanup()
            raise e
    
    except Exception as e:
        logger.error(f"Error executing code: {str(e)}", exc_info=True)
        vfs.cleanup()
        yield {"success": False, "error": str(e)}

