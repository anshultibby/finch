"""
OpenTelemetry tracing setup - Industry standard for observability

This provides:
- Auto-instrumentation for FastAPI, SQLAlchemy, HTTP clients (litellm)
- Logs integrated with traces (correlation)
- Near-zero overhead when disabled
- Export to any backend (console, Jaeger, Datadog, etc.)
- Distributed tracing across services

Install dependencies:
    pip install opentelemetry-api opentelemetry-sdk
    pip install opentelemetry-instrumentation-fastapi
    pip install opentelemetry-instrumentation-sqlalchemy
    pip install opentelemetry-instrumentation-httpx
    pip install opentelemetry-exporter-otlp  # For production backends
    pip install opentelemetry-instrumentation-logging  # For log correlation
"""
from typing import Optional, Dict, Any
from config import Config
import logging

# Check if OpenTelemetry is installed
try:
    from opentelemetry import trace
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
    from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
    from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
    from opentelemetry.instrumentation.logging import LoggingInstrumentor
    from opentelemetry.trace import Status, StatusCode
    
    OTEL_AVAILABLE = True
except ImportError:
    OTEL_AVAILABLE = False
    logging.getLogger(__name__).info("OpenTelemetry not installed. Install with: pip install opentelemetry-api opentelemetry-sdk opentelemetry-instrumentation-fastapi opentelemetry-instrumentation-sqlalchemy opentelemetry-instrumentation-httpx opentelemetry-instrumentation-logging")


def setup_tracing(app, engine=None):
    """
    Setup OpenTelemetry tracing with auto-instrumentation and logging
    
    This automatically traces:
    - All FastAPI endpoints (request/response timing)
    - All database queries via SQLAlchemy
    - All HTTP calls (including to OpenAI)
    - All logs (correlated with traces)
    
    Args:
        app: FastAPI application instance
        engine: SQLAlchemy engine (optional)
    """
    if not OTEL_AVAILABLE:
        return
    
    if not Config.ENABLE_TIMING_LOGS:
        return
    
    logger = logging.getLogger(__name__)
    
    # Create a tracer provider with service name and environment info
    resource = Resource.create({
        "service.name": "finch-api",
        "service.version": "1.0.0",
        "deployment.environment": "development",
    })
    provider = TracerProvider(resource=resource)
    
    # Try to export to Jaeger via OTLP if available
    jaeger_endpoint = Config.JAEGER_ENDPOINT if hasattr(Config, 'JAEGER_ENDPOINT') else "http://localhost:4318/v1/traces"
    
    try:
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
        import httpx
        
        # Test if Jaeger is reachable with a quick timeout
        try:
            with httpx.Client() as client:
                response = client.get("http://localhost:16686", timeout=1.0)
            jaeger_available = True
        except:
            jaeger_available = False
        
        if jaeger_available:
            otlp_exporter = OTLPSpanExporter(endpoint=jaeger_endpoint)
            provider.add_span_processor(BatchSpanProcessor(otlp_exporter))
            logger.info("🔍 OpenTelemetry tracing enabled with Jaeger export")
            logger.info("📊 View traces at: http://localhost:16686")
        else:
            logger.info("🔍 OpenTelemetry tracing enabled (Jaeger not running - traces not exported)")
            logger.info("💡 Start Jaeger with: ./start-jaeger.sh")
    except Exception as e:
        logger.warning(f"⚠️  Could not setup Jaeger exporter: {e}")
        logger.info("🔍 OpenTelemetry tracing enabled (local only)")
    
    # Set as global tracer provider
    trace.set_tracer_provider(provider)
    
    # Auto-instrument logging (adds trace_id and span_id to all logs)
    LoggingInstrumentor().instrument(set_logging_format=True)
    
    # Auto-instrument FastAPI (traces all endpoints)
    FastAPIInstrumentor.instrument_app(app)
    
    # Auto-instrument SQLAlchemy (traces all database queries)
    if engine:
        SQLAlchemyInstrumentor().instrument(engine=engine)
    
    # Auto-instrument HTTP clients (traces API calls to OpenAI, etc.)
    HTTPXClientInstrumentor().instrument()


def get_tracer(name: str = "finch"):
    """
    Get a tracer for manual span creation
    
    Usage:
        from utils.tracing import get_tracer
        
        tracer = get_tracer(__name__)
        
        with tracer.start_as_current_span("my_operation"):
            # Do work
            result = expensive_function()
    """
    if not OTEL_AVAILABLE:
        # Return a no-op tracer
        class NoOpTracer:
            def start_as_current_span(self, name):
                from contextlib import contextmanager
                @contextmanager
                def noop():
                    yield
                return noop()
        return NoOpTracer()
    
    return trace.get_tracer(name)


def add_span_attributes(attributes: Dict[str, Any]):
    """
    Add attributes to the current span for better visibility in Jaeger
    
    Args:
        attributes: Dictionary of key-value pairs to add to the span
        
    Usage:
        add_span_attributes({
            "user.id": user_id,
            "tool.name": tool_name,
            "model": "gpt-4"
        })
    """
    if not OTEL_AVAILABLE:
        return
    
    span = trace.get_current_span()
    if span and span.is_recording():
        for key, value in attributes.items():
            span.set_attribute(key, value)


def add_span_event(name: str, attributes: Optional[Dict[str, Any]] = None):
    """
    Add an event (log) to the current span - shows up in Jaeger timeline
    
    Args:
        name: Event name (e.g., "tool_started", "cache_hit")
        attributes: Optional additional context
        
    Usage:
        add_span_event("Processing message", {
            "message_length": len(message),
            "has_tool_calls": has_tools
        })
    """
    if not OTEL_AVAILABLE:
        return
    
    span = trace.get_current_span()
    if span and span.is_recording():
        span.add_event(name, attributes=attributes or {})


def record_exception(exception: Exception):
    """
    Record an exception in the current span
    
    Args:
        exception: The exception to record
    """
    if not OTEL_AVAILABLE:
        return
    
    span = trace.get_current_span()
    if span and span.is_recording():
        span.record_exception(exception)
        span.set_status(Status(StatusCode.ERROR, str(exception)))


def set_span_status(success: bool, description: Optional[str] = None):
    """
    Set the status of the current span
    
    Args:
        success: Whether the operation succeeded
        description: Optional description (used for errors)
    """
    if not OTEL_AVAILABLE:
        return
    
    span = trace.get_current_span()
    if span and span.is_recording():
        if success:
            span.set_status(Status(StatusCode.OK))
        else:
            span.set_status(Status(StatusCode.ERROR, description or "Operation failed"))

