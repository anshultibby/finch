"""
Code Execution Tool

Simple: Execute Python code from files or inline.
Generation is handled by the agent writing files directly.
Automatically captures and saves any output files.
"""
from modules.tools import tool
from modules.agent.context import AgentContext
from models.sse import SSEEvent
from typing import Optional, Dict, Any, AsyncGenerator, List
from pydantic import BaseModel, Field
from utils.logger import get_logger
import subprocess
import tempfile
import os
import shutil
from pathlib import Path

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


@tool(
    name="execute_code",
    description="""Execute Python code with a 60-second timeout.

**What it does:**
- Runs Python code from a file or inline (60s timeout)
- Captures stdout and stderr
- Automatically saves any output files (CSV, JSON, images, etc.) to chat resources
- Returns results and list of saved files

**The code should be complete** - include all imports, data fetching, logic, etc.

**Examples:**
- Execute a saved file: `execute_code(filename="analysis.py")`  
- Execute inline: `execute_code(code="print('hello')")`
- Save output: Code that writes files like `df.to_csv('results.csv', index=False)` will auto-save to resources

**Environment:**
- FMP_API_KEY is available as an environment variable
- Standard Python libraries available (requests, pandas, numpy, etc.)
- Any files written during execution are automatically saved and accessible

**Best Practices:**
- Prefer pandas DataFrames for numerical data
- Save intermediate results as CSV: `df.to_csv('results.csv', index=False)`
- Print progress: `print(f"Processing {ticker}...")`
- Handle errors: Use try/except blocks
- Clean data: Remove NaN values with `df.dropna()` or `df.fillna(0)`

**Error Handling:**
If execution fails:
1. Check stderr for the error message
2. Use read_chat_file to review the code
3. Use replace_in_chat_file to fix the issue
4. Re-run execute_code""",
    category="code"
)
async def execute_code(
    *,
    params: ExecuteCodeParams,
    context: AgentContext
) -> AsyncGenerator[SSEEvent | Dict[str, Any], None]:
    """Execute Python code from file or inline"""
    from modules.resource_manager import resource_manager
    
    yield SSEEvent(event="tool_status", data={
        "status": "loading",
        "message": "Loading code..."
    })
    
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
        
        # Execute code
        yield SSEEvent(event="tool_status", data={
            "status": "executing",
            "message": f"Running {source}..."
        })
        
        # Create temp directory for execution
        temp_dir = tempfile.mkdtemp(prefix='code_exec_')
        script_path = os.path.join(temp_dir, 'script.py')
        
        try:
            # Write code to temp file
            with open(script_path, 'w') as f:
                f.write(code)
            
            # Get initial files in directory
            files_before = set(os.listdir(temp_dir))
            
            # Execute with subprocess (safer and captures output properly)
            result = subprocess.run(
                ['python', script_path],
                capture_output=True,
                text=True,
                timeout=60,  # 60s timeout for complex backtests
                cwd=temp_dir,  # Run in temp directory
                env={**os.environ, 'FMP_API_KEY': os.getenv('FMP_API_KEY', '')}
            )
            
            # Find any new files created
            files_after = set(os.listdir(temp_dir))
            new_files = files_after - files_before
            
            # Save any output files to chat resources
            saved_files: List[str] = []
            for filename in new_files:
                file_path = os.path.join(temp_dir, filename)
                if os.path.isfile(file_path):
                    try:
                        # Read file (try as text, fallback to binary if needed)
                        try:
                            with open(file_path, 'r', encoding='utf-8') as f:
                                content = f.read()
                        except UnicodeDecodeError:
                            # For binary files, read as bytes and convert to string
                            with open(file_path, 'rb') as f:
                                content = f.read().decode('utf-8', errors='ignore')
                        
                        # Save to chat directory
                        resource_manager.write_chat_file(
                            context.user_id,
                            context.chat_id,
                            filename,
                            content
                        )
                        saved_files.append(filename)
                        logger.info(f"Saved output file: {filename}")
                    except Exception as e:
                        logger.error(f"Failed to save file {filename}: {str(e)}")
            
            # Clean up temp directory
            shutil.rmtree(temp_dir, ignore_errors=True)
            
            # Truncate stdout/stderr to reasonable size (8K chars each = 16K total max)
            MAX_OUTPUT_SIZE = 8000
            stdout_truncated = result.stdout
            stderr_truncated = result.stderr
            truncation_note = ""
            
            if len(stdout_truncated) > MAX_OUTPUT_SIZE:
                stdout_truncated = stdout_truncated[:MAX_OUTPUT_SIZE] + "\n... [OUTPUT TRUNCATED]"
                truncation_note = f" (stdout truncated from {len(result.stdout)} to {MAX_OUTPUT_SIZE} chars)"
            
            if len(stderr_truncated) > MAX_OUTPUT_SIZE:
                stderr_truncated = stderr_truncated[:MAX_OUTPUT_SIZE] + "\n... [OUTPUT TRUNCATED]"
                truncation_note += f" (stderr truncated from {len(result.stderr)} to {MAX_OUTPUT_SIZE} chars)"
            
            if result.returncode != 0:
                yield {
                    "success": False,
                    "error": f"Code failed with exit code {result.returncode}",
                    "stderr": stderr_truncated,
                    "stdout": stdout_truncated,
                    "files_saved": saved_files
                }
                return
            
            # Prepare completion message
            files_msg = ""
            if saved_files:
                files_msg = f" | {len(saved_files)} file(s) saved: {', '.join(saved_files)}"
            
            yield SSEEvent(event="tool_status", data={
                "status": "complete",
                "message": f"Execution complete{truncation_note}{files_msg}"
            })
            
            yield {
                "success": True,
                "stdout": stdout_truncated,
                "stderr": stderr_truncated,
                "files_saved": saved_files,
                "message": f"Code executed successfully{truncation_note}{files_msg}"
            }
        
        except subprocess.TimeoutExpired:
            shutil.rmtree(temp_dir, ignore_errors=True)
            yield {"success": False, "error": "Code execution timed out after 60 seconds. Consider optimizing the code or reducing data size."}
        
        except Exception as e:
            shutil.rmtree(temp_dir, ignore_errors=True)
            raise e
    
    except Exception as e:
        logger.error(f"Error executing code: {str(e)}", exc_info=True)
        yield {"success": False, "error": str(e)}

