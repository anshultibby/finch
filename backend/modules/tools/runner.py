"""
Tool Runner - Handles execution of tools

Separates execution logic from registry (storage) and agents (orchestration)
"""
from typing import Dict, Any, Optional, Union, AsyncGenerator
import traceback
import inspect
import time

from pydantic import BaseModel
from modules.agent.context import AgentContext
from modules.agent.tracing_utils import ToolTracer
from .registry import tool_registry
from models.sse import SSEEvent
from utils.logger import get_logger

logger = get_logger(__name__)


class ToolRunner:
    """
    Executes tools with proper error handling and context management.
    
    Responsibilities:
    - Execute tools from the registry
    - Handle errors gracefully
    - Manage context (user_id, etc.)
    - Log execution for debugging
    """
    
    def __init__(self, registry=None):
        """
        Initialize tool runner
        
        Args:
            registry: ToolRegistry to use (defaults to global registry)
        """
        self.registry = registry or tool_registry
    
    async def execute(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        context: AgentContext
    ) -> AsyncGenerator[Union[SSEEvent, Dict[str, Any]], None]:
        """
        Execute a tool with given arguments
        
        This is an async generator that yields:
        1. SSE events from the tool (if tool yields them) - streamed in real-time
        2. Final result dict as the last item
        
        Args:
            tool_name: Name of the tool to execute
            arguments: Arguments from LLM (keyword args for the function)
            context: Agent context with user_id, chat_id, etc.
        
        Yields:
            SSEEvent objects (if tool yields them), followed by final result dict
        """
        # Get tool from registry
        tool = self.registry.get_tool(tool_name)
        if not tool:
            yield {
                "success": False,
                "error": f"Unknown tool: {tool_name}",
                "message": f"Tool '{tool_name}' not found in registry"
            }
            return
        
        # Create tool tracer for clean instrumentation
        tool_tracer = ToolTracer(user_id=context.user_id, chat_id=context.chat_id)
        
        # Start tracing span for this tool execution
        with tool_tracer.execution(
            tool_name=tool_name,
            category=tool.category,
            is_async=tool.is_async,
            arguments=arguments
        ):
            
            try:
                logger.info(f"Executing tool: {tool_name}")
                logger.debug(f"Tool arguments: {arguments}")
                logger.debug(f"Argument types: {[(k, type(v).__name__) for k, v in arguments.items()]}")
                
                # Inspect function signature to detect Pydantic model parameters
                sig = inspect.signature(tool.handler)
                kwargs = {"context": context}
                
                # Check if any parameter (excluding 'context') is a Pydantic model
                pydantic_param = None
                for param_name, param in sig.parameters.items():
                    if param_name == 'context':
                        continue
                    
                    # Check if this parameter is a Pydantic BaseModel
                    param_annotation = param.annotation
                    try:
                        if (isinstance(param_annotation, type) and 
                            issubclass(param_annotation, BaseModel)):
                            # Found a Pydantic model parameter
                            pydantic_param = (param_name, param_annotation)
                            break
                    except TypeError:
                        # param_annotation is not a class (e.g., it's a typing construct)
                        continue
                
                # If we found a Pydantic parameter, construct it from arguments
                if pydantic_param:
                    param_name, param_class = pydantic_param
                    logger.debug(f"Detected Pydantic parameter: {param_name} of type {param_class.__name__}")
                    
                    # Check if arguments are already wrapped in the parameter name
                    if param_name in arguments:
                        arg_value = arguments[param_name]
                        
                        # Check if it's already a Pydantic model instance
                        if isinstance(arg_value, BaseModel):
                            logger.debug(f"'{param_name}' is already a Pydantic model instance")
                            kwargs[param_name] = arg_value
                        # Check if it's a dict that needs to be converted to the model
                        elif isinstance(arg_value, dict):
                            logger.debug(f"Arguments already wrapped in '{param_name}', constructing {param_class.__name__}")
                            try:
                                kwargs[param_name] = param_class(**arg_value)
                            except Exception as e:
                                logger.error(f"Failed to construct {param_class.__name__} from dict: {e}", exc_info=True)
                                raise
                        else:
                            # Invalid type - try to convert or raise error
                            logger.error(f"Invalid type for '{param_name}': {type(arg_value).__name__}, expected dict or {param_class.__name__}")
                            logger.error(f"Received arguments: {arguments}")
                            logger.error(f"Expected schema for {param_class.__name__}: {param_class.model_json_schema()}")
                            raise TypeError(f"Parameter '{param_name}' must be a dict or {param_class.__name__} instance, got {type(arg_value).__name__}. Received: {repr(arg_value)[:200]}")
                    else:
                        # Not wrapped, assume all arguments are for the model: {"data_series": ..., "plot_type": ...}
                        logger.debug(f"Arguments flattened, constructing {param_class.__name__} from: {list(arguments.keys())}")
                        kwargs[param_name] = param_class(**arguments)
                else:
                    # No Pydantic models, just unpack arguments normally
                    kwargs.update(arguments)
                
                # Execute tool (async or sync)
                event_count = 0
                if tool.is_async:
                    result = tool.handler(**kwargs)
                    # Check if it's an async generator (tool yields events)
                    if inspect.isasyncgen(result):
                        logger.debug(f"Tool {tool_name} is async generator, streaming events")
                        final_result = None
                        async for item in result:
                            if isinstance(item, SSEEvent):
                                # Yield SSE event immediately for real-time streaming
                                event_count += 1
                                logger.debug(f"Tool {tool_name} streaming SSE event: {item.event}")
                                yield item
                            else:
                                # Assume last non-SSEEvent item is the final result
                                final_result = item
                        result = final_result
                    else:
                        # Regular async function
                        result = await result
                else:
                    result = tool.handler(**kwargs)
                
                # Ensure result is a dict
                if not isinstance(result, dict):
                    logger.warning(f"Tool {tool_name} returned non-dict: {type(result)}")
                    result = {"success": True, "data": result}
                
                # Add success flag if not present
                if "success" not in result:
                    result["success"] = True
                
                # Record trace result
                success = result.get("success", True)
                if success:
                    logger.info(f"Tool {tool_name} completed successfully, streamed {event_count} events")
                    tool_tracer.record_success(success=True, events_count=event_count)
                else:
                    logger.warning(f"Tool {tool_name} returned success=False: {result.get('message', 'No message')}")
                    tool_tracer.record_success(
                        success=False,
                        error_message=result.get("message", "Tool returned success=False")
                    )
                
                # Yield final result as last item
                yield result
            
            except Exception as e:
                error_msg = str(e)
                error_trace = traceback.format_exc()
                
                logger.error(f"Error executing tool {tool_name}: {error_msg}")
                logger.debug(f"Traceback:\n{error_trace}")
                
                # ToolTracer.execution() context manager already recorded the exception
                
                # Yield error result
                yield {
                    "success": False,
                    "error": error_msg,
                    "message": f"Tool execution failed: {error_msg}",
                    "traceback": error_trace
                }
    
    def validate_arguments(
        self,
        tool_name: str,
        arguments: Dict[str, Any]
    ) -> tuple[bool, Optional[str]]:
        """
        Validate arguments against tool's parameter schema
        
        Args:
            tool_name: Name of the tool
            arguments: Arguments to validate
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        tool = self.registry.get_tool(tool_name)
        if not tool:
            return False, f"Tool '{tool_name}' not found"
        
        schema = tool.parameters_schema
        required_params = schema.get("required", [])
        
        # Check required parameters
        missing = [p for p in required_params if p not in arguments]
        if missing:
            return False, f"Missing required parameters: {', '.join(missing)}"
        
        # Could add type validation here
        
        return True, None


# Global tool runner instance
tool_runner = ToolRunner()

