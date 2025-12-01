"""
Code Sandbox - Execution environment for user-generated strategy code

PERMISSIVE MODE:
- All imports allowed
- Full builtins access
- Timeout protection only
- Security screening done by LLM before execution
"""
from typing import Dict, Any, Optional, Tuple
import logging
import signal
import traceback
from contextlib import contextmanager

logger = logging.getLogger(__name__)


class TimeoutException(Exception):
    """Raised when code execution times out"""
    pass


def timeout_handler(signum, frame):
    """Signal handler for timeout"""
    raise TimeoutException("Code execution timed out")


class CodeSandbox:
    """
    Permissive execution environment for strategy code
    
    Security: LLM screens code before execution
    Protection: Timeout only (30 seconds default)
    """
    
    def __init__(self, timeout: int = 30):
        """
        Initialize sandbox
        
        Args:
            timeout: Max execution time in seconds
        """
        self.timeout = timeout
    
    def validate_code(self, code: str) -> Tuple[bool, Optional[str]]:
        """
        Basic syntax validation only
        
        Returns:
            (is_valid, error_message)
        """
        try:
            compile(code, '<string>', 'exec')
            return True, None
        except SyntaxError as e:
            return False, f"Syntax error: {str(e)}"
    
    @contextmanager
    def _timeout_context(self):
        """Context manager for timeout protection"""
        # Set up timeout alarm
        signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(self.timeout)
        try:
            yield
        finally:
            # Disable alarm
            signal.alarm(0)
    
    def execute_function(
        self,
        code: str,
        function_name: str,
        *args,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Execute a function from code
        
        Args:
            code: Python code containing the function
            function_name: Name of function to call
            *args, **kwargs: Arguments to pass to function
        
        Returns:
            {
                "success": bool,
                "result": Any,  # Function return value
                "error": str,   # Error message if failed
                "traceback": str  # Full traceback if failed
            }
        """
        # Basic syntax check
        is_valid, error = self.validate_code(code)
        if not is_valid:
            return {
                "success": False,
                "result": None,
                "error": f"Code validation failed: {error}",
                "traceback": None
            }
        
        # Prepare execution environment - PERMISSIVE (full access)
        from typing import Optional, List, Dict, Any, Union
        
        exec_globals = {
            '__builtins__': __builtins__,  # Full builtins access
            # Add typing constructs for convenience
            'Optional': Optional,
            'List': List,
            'Dict': Dict,
            'Any': Any,
            'Union': Union,
        }
        exec_locals = {}
        
        try:
            # Execute code to define functions with timeout
            with self._timeout_context():
                exec(code, exec_globals, exec_locals)
            
            # Get the function
            if function_name not in exec_locals:
                return {
                    "success": False,
                    "result": None,
                    "error": f"Function '{function_name}' not found in code",
                    "traceback": None
                }
            
            func = exec_locals[function_name]
            if not callable(func):
                return {
                    "success": False,
                    "result": None,
                    "error": f"'{function_name}' is not a function",
                    "traceback": None
                }
            
            # Call the function with timeout
            with self._timeout_context():
                result = func(*args, **kwargs)
            
            return {
                "success": True,
                "result": result,
                "error": None,
                "traceback": None
            }
        
        except TimeoutException:
            return {
                "success": False,
                "result": None,
                "error": f"Code execution timed out (>{self.timeout}s)",
                "traceback": None
            }
        
        except Exception as e:
            error_trace = traceback.format_exc()
            logger.error(f"Error executing function '{function_name}': {str(e)}")
            logger.debug(f"Traceback:\n{error_trace}")
            
            return {
                "success": False,
                "result": None,
                "error": str(e),
                "traceback": error_trace
            }
    
    def test_strategy_code(
        self,
        screening_code: str,
        management_code: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Test strategy code by validating and doing a dry run
        
        Returns:
            {
                "success": bool,
                "screening_valid": bool,
                "management_valid": bool,
                "errors": List[str]
            }
        """
        errors = []
        
        # Test screening code
        is_valid, error = self.validate_code(screening_code)
        screening_valid = is_valid
        if not is_valid:
            errors.append(f"Screening code: {error}")
        else:
            # Try to execute with dummy data
            test_result = self.execute_function(
                screening_code,
                "screen",
                ticker="TEST",
                data={"price": 100, "volume": 1000000}
            )
            if not test_result["success"]:
                screening_valid = False
                errors.append(f"Screening function test: {test_result['error']}")
        
        # Test management code if provided
        management_valid = True
        if management_code:
            is_valid, error = self.validate_code(management_code)
            management_valid = is_valid
            if not is_valid:
                errors.append(f"Management code: {error}")
            else:
                # Try to execute with dummy position
                test_result = self.execute_function(
                    management_code,
                    "manage",
                    ticker="TEST",
                    position={
                        "shares": 10,
                        "entry_price": 100,
                        "current_price": 110,
                        "pnl_pct": 10,
                        "days_held": 5
                    },
                    data={"price": 110}
                )
                if not test_result["success"]:
                    management_valid = False
                    errors.append(f"Management function test: {test_result['error']}")
        
        return {
            "success": screening_valid and management_valid,
            "screening_valid": screening_valid,
            "management_valid": management_valid,
            "errors": errors
        }


# Global instance
code_sandbox = CodeSandbox()
