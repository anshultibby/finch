"""
Financial Code Generator (Manus-inspired agent loop)

Generates validated Python code for financial analysis.
Simple, clean, focused on the core problem.

Manus principles:
- File-based execution (save before running)
- Todo.md tracking (visible progress)
- Iterative agent loop with retry
"""
from typing import Dict, Any, AsyncGenerator, List, Optional
from modules.agent.llm_handler import LLMHandler
from modules.agent.llm_config import LLMConfig
from modules.code_sandbox import code_sandbox
from modules.financial_code_planner import (
    create_code_plan, get_current_step, mark_step_complete, mark_step_failed, StepStatus
)
from modules.financial_code_patterns import suggest_data_sources, get_error_fix, BEST_PRACTICES
from modules.todo_manager import todo_manager
from models.sse import SSEEvent
import logging
import tempfile
import os

logger = logging.getLogger(__name__)


class FinancialCodeGenerator:
    """
    Generate and validate Python code for financial analysis
    
    Agent loop:
    1. Analyze → what data/calculations needed
    2. Generate → create Python function
    3. Validate → check syntax, imports, security
    4. Test → run with sample data
    5. Save → store for reuse
    """
    
    def __init__(self):
        self.llm_handler = LLMHandler()
    
    async def generate_code(
        self,
        task_description: str,
        function_name: str = "analyze",
        data_sources: Optional[List[str]] = None,
        todo_path: Optional[str] = None,
        save_path: Optional[str] = None
    ) -> AsyncGenerator[SSEEvent | Dict[str, Any], None]:
        """
        Generate financial analysis code with progress tracking
        
        Args:
            task_description: What the code should do (e.g., "Calculate revenue growth and profit margins")
            function_name: Name of the generated function
            data_sources: FMP endpoints to use (auto-detected if None)
            todo_path: Path to todo.md file (optional, for Manus-style tracking)
            save_path: Path to save generated code (if None, temp file used for testing only)
        
        Yields:
            SSEEvents for progress, final dict with code/file path
        
        Manus approach: We save code to file FIRST, then work with file references
        """
        # Create plan
        plan = create_code_plan(
            description=task_description,
            metadata={
                "function_name": function_name,
                "data_sources": data_sources,
                "save_path": save_path
            }
        )
        
        # Create todo.md (Manus-style)
        if todo_path:
            todo_items = [step.description for step in plan.steps]
            todo_manager.create_todo(
                filepath=todo_path,
                task_title=f"Generate Code: {function_name}",
                items=todo_items
            )
            logger.info(f"Created todo.md: {todo_path}")
        
        yield SSEEvent(event="code_gen_start", data={
            "task": task_description,
            "steps": len(plan.steps),
            "todo_file": todo_path,
            "save_path": save_path
        })
        
        code_file_path = None  # Track file path instead of code string
        
        # Agent loop - execute plan step by step
        while True:
            step = get_current_step(plan)
            if not step:
                break
            
            step.status = StepStatus.IN_PROGRESS
            yield SSEEvent(event="step_progress", data={
                "step": step.number,
                "total": len(plan.steps),
                "description": step.description
            })
            
            try:
                # Execute current step
                if step.number == 1:
                    # Analyze requirements
                    result = self._analyze_requirements(task_description, data_sources)
                    plan.metadata.update(result)
                    
                elif step.number == 2:
                    # Generate code and save to file immediately
                    result = await self._generate_code(
                        task_description,
                        function_name,
                        plan.metadata.get("data_sources", []),
                        plan.metadata.get("save_path")
                    )
                    code_file_path = result["file_path"]
                    
                elif step.number == 3:
                    # Validate (read from file)
                    result = self._validate_code(code_file_path)
                    
                elif step.number == 4:
                    # Test (read from file)
                    result = await self._test_code(code_file_path, function_name)
                    
                elif step.number == 5:
                    # Save (handled by caller)
                    result = {"saved": False}  # Caller decides where to save
                
                else:
                    raise ValueError(f"Unknown step: {step.number}")
                
                # Mark complete
                has_more = mark_step_complete(plan, result)
                
                # Update todo.md
                if todo_path:
                    todo_manager.mark_item_done(todo_path, step.description)
                
                yield SSEEvent(event="step_complete", data={
                    "step": step.number,
                    "description": step.description
                })
                
                if not has_more:
                    break
            
            except Exception as e:
                error_msg = str(e)
                logger.error(f"Step {step.number} error: {error_msg}", exc_info=True)
                
                # Get suggested fix
                suggested_fix = get_error_fix(error_msg)
                
                # Check if should retry
                retry_info = mark_step_failed(plan, error_msg)
                
                if retry_info["should_retry"]:
                    yield SSEEvent(event="step_retry", data={
                        "step": step.number,
                        "error": error_msg,
                        "retry": retry_info["retry_count"],
                        "fix": suggested_fix
                    })
                    # Loop will retry same step
                else:
                    yield SSEEvent(event="step_failed", data={
                        "step": step.number,
                        "error": error_msg,
                        "fix": suggested_fix
                    })
                    yield {
                        "success": False,
                        "error": error_msg,
                        "suggested_fix": suggested_fix
                    }
                    return
        
        # Success!
        yield SSEEvent(event="code_gen_complete", data={
            "message": "✓ Code generated and validated"
        })
        
        # Read final code from file for return
        final_code = None
        if code_file_path:
            try:
                with open(code_file_path, 'r') as f:
                    final_code = f.read()
            except:
                pass
        
        yield {
            "success": True,
            "code": final_code,  # Still return code for backwards compatibility
            "file_path": code_file_path,  # PRIMARY: file reference (Manus approach)
            "function_name": function_name,
            "data_sources": plan.metadata.get("data_sources", []),
            "explanation": plan.metadata.get("explanation", "")
        }
    
    def _analyze_requirements(
        self,
        description: str,
        provided_sources: Optional[List[str]]
    ) -> Dict[str, Any]:
        """Step 1: Analyze what data and calculations are needed"""
        suggested = suggest_data_sources(description)
        data_sources = provided_sources if provided_sources else suggested
        
        return {
            "data_sources": data_sources,
            "suggested_sources": suggested
        }
    
    async def _generate_code(
        self,
        description: str,
        function_name: str,
        data_sources: List[str],
        save_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Step 2: Generate Python code using LLM and save to file
        
        Manus approach: Save to file IMMEDIATELY after generation
        """
        
        prompt = f"""Generate a Python function for financial analysis.

TASK: {description}

AVAILABLE DATA:
The function receives a `data` dict with FMP endpoints: {', '.join(data_sources)}

BEST PRACTICES:
{BEST_PRACTICES['data_validation']}

FUNCTION TEMPLATE:
```python
def {function_name}(ticker: str, data: dict) -> dict:
    \"\"\"
    {description}
    
    Args:
        ticker: Stock symbol
        data: Dict with FMP data
    
    Returns:
        Dict with analysis results
    \"\"\"
    # YOUR CODE HERE
    pass
```

REQUIREMENTS:
1. Return a dict with analysis results
2. Handle missing data gracefully
3. Use only safe imports: math, statistics, datetime
4. Use .get() for dict access
5. Include error handling

Generate the complete function:"""
        
        llm_config = LLMConfig.from_config()
        response = await self.llm_handler.acompletion(
            messages=[{"role": "user", "content": prompt}],
            model=llm_config.model
        )
        
        code = self._extract_code(response.choices[0].message.content)
        explanation = self._extract_explanation(response.choices[0].message.content)
        
        # SAVE TO FILE IMMEDIATELY (Manus approach)
        if save_path:
            file_path = save_path
            with open(file_path, 'w') as f:
                f.write(code)
        else:
            # Temp file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
                f.write(code)
                file_path = f.name
        
        logger.info(f"Saved generated code to: {file_path}")
        
        return {
            "code": code,
            "file_path": file_path,
            "explanation": explanation
        }
    
    def _validate_code(self, file_path: str) -> Dict[str, Any]:
        """
        Step 3: Validate code is safe and correct
        
        Args:
            file_path: Path to code file (Manus approach - work with file references)
        """
        # Read from file
        with open(file_path, 'r') as f:
            code = f.read()
        
        is_valid, error = code_sandbox.validate_code(code)
        if not is_valid:
            raise ValueError(f"Validation failed: {error}")
        return {"valid": True, "file_path": file_path}
    
    async def _test_code(
        self,
        file_path: str,
        function_name: str
    ) -> Dict[str, Any]:
        """
        Step 4: Test code with sample data
        
        Args:
            file_path: Path to code file (Manus approach - file already saved)
        
        IMPORTANT: Code is ALREADY in file from step 2, we just read and execute it.
        This gives us better error messages with file:line numbers.
        """
        
        sample_data = {
            "income-statement": [
                {"revenue": 1000000, "netIncome": 100000},
                {"revenue": 800000, "netIncome": 80000}
            ],
            "key-metrics": [{"peRatio": 15.5, "roe": 0.18}],
            "financial-ratios": [{"returnOnEquity": 0.18}]
        }
        
        logger.info(f"Testing code from file: {file_path}")
        
        # Read code from file (file-based execution)
        with open(file_path, 'r') as f:
            file_code = f.read()
        
        result = code_sandbox.execute_function(
            file_code,
            function_name,
            ticker="TEST",
            data=sample_data
        )
        
        if not result["success"]:
            # Error will reference file path and line numbers
            raise ValueError(f"Test failed: {result['error']}\nFile: {file_path}")
        
        return {
            "test_passed": True,
            "sample_output": result["result"],
            "file_path": file_path
        }
    
    def _extract_code(self, text: str) -> str:
        """Extract code from markdown"""
        if "```python" in text:
            start = text.find("```python") + 9
            end = text.find("```", start)
            return text[start:end].strip() if end != -1 else text
        elif "```" in text:
            start = text.find("```") + 3
            end = text.find("```", start)
            return text[start:end].strip() if end != -1 else text
        return text.strip()
    
    def _extract_explanation(self, text: str) -> str:
        """Extract explanation before code"""
        if "```" in text:
            return text[:text.find("```")].strip()
        return ""


# Global instance
financial_code_generator = FinancialCodeGenerator()

