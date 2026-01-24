"""
Strategy Executor - Safely execute strategy code

Handles:
- Loading strategy files from database
- Setting up execution context
- Running code in restricted environment
- Capturing results and errors
"""
import asyncio
import logging
from typing import Any, Optional
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from models.db import Strategy, StrategyExecution
from models.strategies import RiskLimits, ExecutionAction
from crud.strategies import (
    load_strategy_files,
    create_execution,
    complete_execution,
)
from .context import StrategyContext

logger = logging.getLogger(__name__)

# Execution timeout (prevent runaway strategies)
EXECUTION_TIMEOUT_SECONDS = 60


async def execute_strategy(
    db: AsyncSession,
    strategy: Strategy,
    trigger: str = "manual",  # 'scheduled', 'manual', 'dry_run'
    dry_run: bool = True
) -> StrategyExecution:
    """
    Execute a strategy
    
    Args:
        db: Database session
        strategy: Strategy to execute
        trigger: What triggered this execution
        dry_run: If True, don't execute real trades
    
    Returns:
        StrategyExecution record with results
    """
    # Create execution record
    execution = await create_execution(db, strategy, trigger)
    
    # Load strategy files
    try:
        files = await load_strategy_files(db, strategy)
    except Exception as e:
        logger.error(f"Failed to load strategy files: {e}")
        return await complete_execution(
            db, execution,
            status="failed",
            error=f"Failed to load strategy files: {e}",
            summary="Strategy execution failed: could not load files"
        )
    
    # Build context
    config = strategy.config or {}
    risk_limits = None
    if config.get("risk_limits"):
        risk_limits = RiskLimits(**config["risk_limits"])
    
    ctx = StrategyContext(
        user_id=strategy.user_id,
        strategy_id=strategy.id,
        execution_id=str(execution.id),
        dry_run=dry_run,
        _db=db,
        _risk_limits=risk_limits,
        _files={k: v for k, v in files.items() if not k.endswith('.py')},  # Non-code files
    )
    
    ctx.log(f"Starting execution (trigger={trigger}, dry_run={dry_run})")
    
    try:
        # Execute via BaseStrategy pattern
        from modules.tools.servers.strategies._executor import execute_strategy_cycle
        result = await asyncio.wait_for(
            execute_strategy_cycle(db, strategy, ctx),
            timeout=EXECUTION_TIMEOUT_SECONDS
        )
        
        # Build summary
        actions = ctx.get_actions()
        summary = _build_summary(result, actions, ctx.dry_run)
        
        ctx.log(f"Execution completed: {summary}")
        
        return await complete_execution(
            db, execution,
            status="success",
            result=result,
            summary=summary,
            actions=actions,
            logs=ctx.get_logs()
        )
        
    except asyncio.TimeoutError:
        error_msg = f"Strategy timed out after {EXECUTION_TIMEOUT_SECONDS}s"
        ctx.log(f"ERROR: {error_msg}")
        logger.error(f"Strategy {strategy.id} timed out")
        
        return await complete_execution(
            db, execution,
            status="failed",
            error=error_msg,
            summary="Strategy execution timed out",
            actions=ctx.get_actions(),
            logs=ctx.get_logs()
        )
        
    except Exception as e:
        error_msg = str(e)
        ctx.log(f"ERROR: {error_msg}")
        logger.exception(f"Strategy {strategy.id} failed: {e}")
        
        return await complete_execution(
            db, execution,
            status="failed",
            error=error_msg,
            summary=f"Strategy failed: {error_msg[:100]}",
            actions=ctx.get_actions(),
            logs=ctx.get_logs()
        )
        
    finally:
        await ctx.cleanup()


async def _run_strategy_code(
    files: dict[str, str],
    entrypoint: str,
    ctx: StrategyContext
) -> Any:
    """
    Execute strategy code in a controlled environment
    
    The entrypoint file must define an async function `strategy(ctx)`.
    Other .py files in the bundle can be imported within the strategy.
    """
    if entrypoint not in files:
        raise ValueError(f"Entrypoint '{entrypoint}' not found in strategy files")
    
    # Build execution globals
    # We provide:
    # - ctx: The StrategyContext
    # - Common imports that strategies might need
    # - A custom __import__ that allows importing strategy modules
    
    strategy_modules = {
        name[:-3]: content 
        for name, content in files.items() 
        if name.endswith('.py') and name != entrypoint
    }
    
    exec_globals = {
        "ctx": ctx,
        # Standard library
        "datetime": __import__("datetime"),
        "json": __import__("json"),
        "math": __import__("math"),
        "re": __import__("re"),
        # Common data processing
        "asyncio": __import__("asyncio"),
        # Custom import for strategy modules
        "__builtins__": _get_safe_builtins(strategy_modules),
    }
    
    # Compile and execute the entrypoint
    try:
        code = compile(files[entrypoint], entrypoint, "exec")
        exec(code, exec_globals)
    except SyntaxError as e:
        raise ValueError(f"Syntax error in {entrypoint}: {e}")
    
    # Find and call the strategy function
    if "strategy" not in exec_globals:
        raise ValueError(
            f"Entrypoint '{entrypoint}' must define an async function called 'strategy'"
        )
    
    strategy_func = exec_globals["strategy"]
    
    if not asyncio.iscoroutinefunction(strategy_func):
        raise ValueError("'strategy' must be an async function (async def strategy(ctx): ...)")
    
    # Execute the strategy
    return await strategy_func(ctx)


def _get_safe_builtins(strategy_modules: dict[str, str]) -> dict:
    """
    Get a restricted set of builtins for strategy execution
    
    Allows:
    - Basic operations (print, len, range, etc.)
    - Type conversions
    - Math operations
    - Iteration helpers
    
    Blocks:
    - File I/O (open, read, write)
    - Code execution (eval, exec, compile)
    - System access (import of dangerous modules)
    """
    import builtins
    
    # Allowed builtins
    allowed = {
        # Basic
        "print", "len", "range", "enumerate", "zip", "map", "filter",
        "sorted", "reversed", "list", "dict", "set", "tuple", "frozenset",
        # Types
        "str", "int", "float", "bool", "bytes", "bytearray",
        "type", "isinstance", "issubclass",
        # Math
        "abs", "min", "max", "sum", "pow", "round", "divmod",
        # Iteration
        "iter", "next", "all", "any",
        # String
        "chr", "ord", "repr", "format",
        # Object
        "getattr", "setattr", "hasattr", "delattr",
        "callable", "id", "hash",
        # Exceptions
        "Exception", "ValueError", "TypeError", "KeyError", "IndexError",
        "RuntimeError", "StopIteration", "AttributeError",
        # Other
        "None", "True", "False", "Ellipsis",
        "slice", "property", "staticmethod", "classmethod",
    }
    
    safe_builtins = {
        name: getattr(builtins, name)
        for name in allowed
        if hasattr(builtins, name)
    }
    
    # Custom import that only allows strategy modules and safe stdlib
    def safe_import(name, globals=None, locals=None, fromlist=(), level=0):
        # Allow importing strategy modules
        if name in strategy_modules:
            module_globals = {"__builtins__": safe_builtins}
            exec(compile(strategy_modules[name], f"{name}.py", "exec"), module_globals)
            
            # Create a simple namespace object
            class ModuleNamespace:
                pass
            
            module = ModuleNamespace()
            for key, value in module_globals.items():
                if not key.startswith("_"):
                    setattr(module, key, value)
            return module
        
        # Allow safe stdlib modules
        safe_modules = {
            "datetime", "json", "math", "re", "random", "collections",
            "itertools", "functools", "operator", "decimal", "statistics",
            "csv", "io"  # For reading strategy data files
        }
        
        if name in safe_modules:
            return __import__(name, globals, locals, fromlist, level)
        
        # Block everything else
        raise ImportError(f"Import of '{name}' is not allowed in strategies")
    
    safe_builtins["__import__"] = safe_import
    
    return safe_builtins


def _build_summary(result: Any, actions: list[ExecutionAction], dry_run: bool) -> str:
    """Build a human-readable summary of the execution"""
    prefix = "[DRY RUN] " if dry_run else ""
    
    if not actions:
        # No actions taken
        if isinstance(result, dict) and "message" in result:
            return f"{prefix}{result['message']}"
        return f"{prefix}Completed with no trading actions"
    
    # Count actions by type
    action_counts = {}
    total_usd = 0.0
    
    for action in actions:
        action_type = action.type
        action_counts[action_type] = action_counts.get(action_type, 0) + 1
        if "estimated_cost_usd" in action.details:
            total_usd += action.details["estimated_cost_usd"]
    
    # Build summary
    parts = []
    for action_type, count in action_counts.items():
        if action_type == "kalshi_order":
            parts.append(f"{count} Kalshi order{'s' if count > 1 else ''}")
        elif action_type == "alpaca_order":
            parts.append(f"{count} Alpaca order{'s' if count > 1 else ''}")
        else:
            parts.append(f"{count} {action_type}")
    
    summary = ", ".join(parts)
    
    if total_usd > 0:
        summary += f" (${total_usd:.2f})"
    
    return f"{prefix}{summary}"
