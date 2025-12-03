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
        Create temp directory and mount all chat files.
        
        Returns:
            Path to temp directory
        """
        from modules.resource_manager import resource_manager
        
        # Create temp directory
        self.temp_dir = tempfile.mkdtemp(prefix='vfs_')
        logger.info(f"Created virtual filesystem at: {self.temp_dir}")
        
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
                os.makedirs(os.path.dirname(file_path), exist_ok=True)
                
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                # Track original hash
                self.file_hashes[filename] = self._hash_content(content)
                mounted_count += 1
        
        if mounted_count > 0:
            logger.info(f"Mounted {mounted_count} existing files from chat resources")
        
        return self.temp_dir
    
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
                
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                except UnicodeDecodeError:
                    # Skip binary files or handle them separately
                    logger.warning(f"Skipping binary file: {relative_path}")
                    continue
                
                current_hash = self._hash_content(content)
                
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
                    logger.info(f"New file: {relative_path}")
                
                elif current_hash != self.file_hashes[relative_path]:
                    # Modified file
                    resource_manager.write_chat_file(
                        self.user_id,
                        self.chat_id,
                        relative_path,
                        content
                    )
                    changes["modified"].append(relative_path)
                    logger.info(f"Modified file: {relative_path}")
        
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
    description="""Execute Python code with persistent filesystem (60s timeout).

**Persistent Filesystem:**
- All files from previous executions are automatically available
- Write files normally: `df.to_csv('data.csv')`
- Read files from previous runs: `df = pd.read_csv('data.csv')`
- Changes are automatically saved to your chat resources
- Files persist across multiple code executions

**What it does:**
1. Mounts all your existing chat files into execution environment
2. Runs your Python code
3. Automatically saves any new/modified files
4. Returns execution results

**Examples:**

First execution:
```python
# Save some data
df.to_csv('results.csv', index=False)
print("Saved results")
```

Later execution (different execute_code call):
```python
# Read the data from previous execution
df = pd.read_csv('results.csv')
print(f"Loaded {len(df)} rows")
```

**Environment:**
- FMP_API_KEY available as environment variable
- Standard libraries: pandas, numpy, requests, matplotlib, plotly, etc.
- All your previous files are accessible

**Best Practices:**
- Save intermediate results as CSV
- Write visualization code separately from data processing
- Use descriptive filenames (e.g., 'backtest_results.csv', not 'data.csv')
- Print progress for long-running operations

**Error Handling:**
If execution fails:
1. Check stderr for error message
2. Fix the issue (use replace_in_chat_file to edit)
3. Re-run execute_code""",
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
        
        yield SSEEvent(event="tool_status", data={
            "status": "executing",
            "message": f"Running {source}..."
        })
        
        try:
            # Write code to temp file
            with open(script_path, 'w') as f:
                f.write(code)
            
            # Execute with subprocess
            result = subprocess.run(
                ['python', script_path],
                capture_output=True,
                text=True,
                timeout=60,
                cwd=temp_dir,
                env={**os.environ, 'FMP_API_KEY': os.getenv('FMP_API_KEY', '')}
            )
            
            # Sync changes back to database
            changes = vfs.sync_changes()
            
            # Clean up temp directory
            vfs.cleanup()
            
            # Prepare file change summary
            files_changed = []
            if changes["new"]:
                files_changed.append(f"{len(changes['new'])} new")
            if changes["modified"]:
                files_changed.append(f"{len(changes['modified'])} modified")
            if changes["deleted"]:
                files_changed.append(f"{len(changes['deleted'])} deleted")
            
            files_msg = ""
            if files_changed:
                all_files = changes["new"] + changes["modified"]
                file_list = ", ".join(all_files[:3])
                if len(all_files) > 3:
                    file_list += f", +{len(all_files) - 3} more"
                files_msg = f" | Files: {file_list}"
            
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
                yield {
                    "success": False,
                    "error": f"Code failed with exit code {result.returncode}",
                    "stderr": stderr_truncated,
                    "stdout": stdout_truncated,
                    "changes": changes
                }
                return
            
            yield SSEEvent(event="tool_status", data={
                "status": "complete",
                "message": f"✓ Execution complete{truncation_note}{files_msg}"
            })
            
            yield {
                "success": True,
                "stdout": stdout_truncated,
                "stderr": stderr_truncated,
                "changes": changes,
                "message": f"✓ Code executed successfully{truncation_note}{files_msg}"
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

