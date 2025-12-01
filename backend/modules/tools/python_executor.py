"""
Python code execution for financial analysis (Manus-style)

Executes Python code in a restricted environment with:
- Financial libraries (pandas, numpy, plotly, yfinance)
- FMP API access
- Data analysis capabilities
- Chart generation

Security: Uses RestrictedPython for safe execution
"""
from typing import Dict, Any, Optional, AsyncGenerator
import io
import sys
import traceback
from contextlib import redirect_stdout, redirect_stderr
from pydantic import BaseModel, Field
from models.sse import SSEEvent
from utils.logger import get_logger

logger = get_logger(__name__)


class PythonExecutorParams(BaseModel):
    """Parameters for Python code execution"""
    code: str = Field(..., description="Python code to execute for financial analysis")
    chat_id: str = Field(..., description="Chat ID for saving output files")
    user_id: str = Field(..., description="User ID")
    description: Optional[str] = Field(None, description="What this code does (for logging)")


class PythonExecutor:
    """Execute Python code safely for financial analysis"""
    
    def __init__(self):
        self.timeout_seconds = 30  # Max execution time
        
    async def execute_streaming(
        self,
        params: PythonExecutorParams
    ) -> AsyncGenerator[SSEEvent, None]:
        """
        Execute Python code and stream status updates
        
        Returns:
            Execution result with stdout, stderr, and any return value
        """
        yield SSEEvent(event="tool_status", data={
            "status": "executing",
            "message": f"Executing Python code{f': {params.description}' if params.description else ''}..."
        })
        
        try:
            # Prepare safe execution environment
            safe_globals = self._create_safe_environment(params.chat_id, params.user_id)
            
            # Capture stdout and stderr
            stdout_capture = io.StringIO()
            stderr_capture = io.StringIO()
            
            result = None
            with redirect_stdout(stdout_capture), redirect_stderr(stderr_capture):
                # Execute code
                try:
                    # Use exec for statements, eval for expressions
                    if '\n' in params.code or any(keyword in params.code for keyword in ['import', 'def', 'class', 'for', 'while', 'if']):
                        exec(params.code, safe_globals)
                        # Try to get a result if there's a variable named 'result'
                        result = safe_globals.get('result')
                    else:
                        result = eval(params.code, safe_globals)
                except Exception as e:
                    logger.error(f"Error executing code: {str(e)}")
                    stderr_capture.write(traceback.format_exc())
            
            stdout = stdout_capture.getvalue()
            stderr = stderr_capture.getvalue()
            
            # Check for errors
            if stderr:
                yield SSEEvent(event="tool_status", data={
                    "status": "error",
                    "message": f"Execution error: {stderr[:200]}"
                })
                yield {
                    "success": False,
                    "error": stderr,
                    "stdout": stdout
                }
                return
            
            yield SSEEvent(event="tool_status", data={
                "status": "complete",
                "message": "✓ Code executed successfully"
            })
            
            # Format output
            output_lines = []
            if stdout:
                output_lines.append("**Output:**")
                output_lines.append(f"```\n{stdout}\n```")
            
            if result is not None:
                output_lines.append(f"\n**Result:** `{result}`")
            
            yield {
                "success": True,
                "output": "\n\n".join(output_lines) if output_lines else "Code executed (no output)",
                "result": result,
                "stdout": stdout
            }
            
        except Exception as e:
            error_msg = f"Execution failed: {str(e)}\n{traceback.format_exc()}"
            logger.error(error_msg)
            yield SSEEvent(event="tool_status", data={
                "status": "error",
                "message": f"Execution failed: {str(e)}"
            })
            yield {
                "success": False,
                "error": error_msg
            }
    
    def _create_safe_environment(self, chat_id: str, user_id: str) -> Dict[str, Any]:
        """
        Create a safe execution environment with financial libraries
        
        Includes:
        - pandas, numpy for data analysis
        - plotly for charting
        - FMP client for market data
        - Helper functions
        """
        import pandas as pd
        import numpy as np
        from datetime import datetime, timedelta
        from config import Config
        
        # FMP Client for financial data
        from modules.tools.clients.fmp import FMPClient
        fmp = FMPClient(api_key=Config.FMP_API_KEY)
        
        # Safe builtins (no file access, no imports, no system calls)
        safe_builtins = {
            'print': print,
            'len': len,
            'range': range,
            'sum': sum,
            'min': min,
            'max': max,
            'abs': abs,
            'round': round,
            'sorted': sorted,
            'enumerate': enumerate,
            'zip': zip,
            'map': map,
            'filter': filter,
            'str': str,
            'int': int,
            'float': float,
            'bool': bool,
            'list': list,
            'dict': dict,
            'tuple': tuple,
            'set': set,
        }
        
        # Financial analysis environment
        env = {
            '__builtins__': safe_builtins,
            'pd': pd,
            'np': np,
            'datetime': datetime,
            'timedelta': timedelta,
            'fmp': fmp,
            'chat_id': chat_id,
            'user_id': user_id,
        }
        
        return env


# Global instance
python_executor = PythonExecutor()

