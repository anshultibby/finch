"""
Tool Stream Handler - Allows tools to emit progress updates during execution

Tools can optionally use this to stream progress, logs, or partial results.
"""
from typing import Optional, AsyncGenerator, Callable, Any, Dict
from datetime import datetime


class ToolStreamHandler:
    """
    Handler for streaming events from tool execution.
    
    Tools receive this in their context and can emit:
    - Progress updates (0-100%)
    - Log messages
    - Partial results
    - Custom events
    
    Usage in a tool:
        @tool(description="Long-running analysis")
        async def analyze_data(*, context: ToolContext, data: list):
            if context.stream_handler:
                await context.stream_handler.emit_progress(0, "Starting analysis...")
            
            # Do work
            for i, item in enumerate(data):
                process(item)
                progress = int((i / len(data)) * 100)
                if context.stream_handler:
                    await context.stream_handler.emit_progress(progress, f"Processed {i}/{len(data)}")
            
            if context.stream_handler:
                await context.stream_handler.emit_progress(100, "Complete!")
            
            return {"success": True, "data": results}
    """
    
    def __init__(self, callback: Optional[Callable] = None):
        """
        Initialize stream handler
        
        Args:
            callback: Optional async callback that receives events
                      Signature: async def callback(event: Dict[str, Any])
        """
        self.callback = callback
        self._events = []  # Store events if no callback
    
    async def emit(self, event_type: str, data: Dict[str, Any]):
        """
        Emit a generic event
        
        Args:
            event_type: Type of event (progress, log, result, custom)
            data: Event data
        """
        event = {
            "type": event_type,
            "timestamp": datetime.now().isoformat(),
            **data
        }
        
        if self.callback:
            await self.callback(event)
        else:
            # Store for later retrieval
            self._events.append(event)
    
    async def emit_progress(self, percent: float, message: Optional[str] = None):
        """
        Emit progress update
        
        Args:
            percent: Progress percentage (0-100)
            message: Optional progress message
        """
        await self.emit("progress", {
            "percent": percent,
            "message": message
        })
    
    async def emit_log(self, level: str, message: str):
        """
        Emit log message
        
        Args:
            level: Log level (info, warning, error, debug)
            message: Log message
        """
        await self.emit("log", {
            "level": level,
            "message": message
        })
    
    async def emit_partial_result(self, data: Any):
        """
        Emit partial result (for tools that can return results incrementally)
        
        Args:
            data: Partial result data
        """
        await self.emit("partial_result", {
            "data": data
        })
    
    async def emit_status(self, status: str, message: Optional[str] = None):
        """
        Emit status update
        
        Args:
            status: Status string (processing, analyzing, fetching, etc.)
            message: Optional status message
        """
        await self.emit("status", {
            "status": status,
            "message": message
        })
    
    def get_events(self) -> list[Dict[str, Any]]:
        """Get all stored events (if no callback was provided)"""
        return self._events.copy()
    
    def clear_events(self):
        """Clear stored events"""
        self._events.clear()


class ToolStreamHandlerBuilder:
    """
    Builder for creating stream handlers with different configurations
    """
    
    @staticmethod
    def create_sse_handler(sse_queue: AsyncGenerator) -> ToolStreamHandler:
        """
        Create handler that emits SSE events
        
        Args:
            sse_queue: Async generator to yield SSE events to
        """
        async def callback(event: Dict[str, Any]):
            # Convert to SSE format
            from models.sse import SSEEvent
            sse_event = SSEEvent(
                event=f"tool_{event['type']}",
                data=event
            )
            # Yield to SSE stream
            # Note: This needs special handling in the agent
        
        return ToolStreamHandler(callback=callback)
    
    @staticmethod
    def create_logging_handler() -> ToolStreamHandler:
        """
        Create handler that logs events to console
        """
        async def callback(event: Dict[str, Any]):
            event_type = event.get("type", "unknown")
            if event_type == "progress":
                percent = event.get("percent", 0)
                message = event.get("message", "")
                print(f"📊 Progress: {percent}% - {message}", flush=True)
            elif event_type == "log":
                level = event.get("level", "info").upper()
                message = event.get("message", "")
                print(f"📝 [{level}] {message}", flush=True)
            elif event_type == "status":
                status = event.get("status", "")
                message = event.get("message", "")
                print(f"⚙️ Status: {status} - {message}", flush=True)
            else:
                print(f"🔔 Event: {event}", flush=True)
        
        return ToolStreamHandler(callback=callback)
    
    @staticmethod
    def create_storage_handler() -> ToolStreamHandler:
        """
        Create handler that just stores events (no callback)
        Useful for testing or batch processing
        """
        return ToolStreamHandler(callback=None)

