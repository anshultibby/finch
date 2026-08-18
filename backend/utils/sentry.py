"""
Sentry initialization — error tracking, alerting, and (optional) performance tracing.

Sentry is the observability backend for Finch:
  - Captures unhandled exceptions across FastAPI request handlers automatically.
  - Receives tool-call failures and slow calls reported from services/tool_monitoring.py,
    grouped by tool + error signature so repeated failures collapse into one issue.
  - Has its own alert rules (email/Slack) configured in the Sentry dashboard.

Disabled cleanly (no-op) when SENTRY_DSN is unset, so local/dev runs need no setup.

Install:
    pip install "sentry-sdk[fastapi]"
"""
from core.config import Config
from utils.logger import get_logger

logger = get_logger(__name__)

_initialized = False


def setup_sentry() -> bool:
    """
    Initialize the Sentry SDK. Safe to call once at startup.

    Returns True if Sentry was initialized, False if disabled or unavailable.
    Call this BEFORE the FastAPI app starts handling requests so the SDK's
    auto-instrumentation can hook in.
    """
    global _initialized
    if _initialized:
        return True

    dsn = Config.SENTRY_DSN
    if not dsn:
        logger.info("Sentry disabled (SENTRY_DSN not set)")
        return False

    try:
        import sentry_sdk
    except ImportError:
        logger.warning(
            "SENTRY_DSN is set but sentry-sdk is not installed. "
            'Run: pip install "sentry-sdk[fastapi]"'
        )
        return False

    # FastAPI/Starlette, SQLAlchemy, and HTTP integrations auto-enable when the
    # SDK detects those libraries are installed — no explicit wiring needed.
    sentry_sdk.init(
        dsn=dsn,
        environment=Config.SENTRY_ENVIRONMENT,
        traces_sample_rate=Config.SENTRY_TRACES_SAMPLE_RATE,
        send_default_pii=False,  # don't ship user PII; we attach our own safe tags
    )

    _initialized = True
    logger.info(
        "Sentry initialized (environment=%s, traces_sample_rate=%s)",
        Config.SENTRY_ENVIRONMENT,
        Config.SENTRY_TRACES_SAMPLE_RATE,
    )
    return True


def capture_tool_exception(exc: BaseException, *, tool_name: str,
                           chat_id: str = "", user_id: str = "") -> None:
    """
    Send a tool's raised exception to Sentry with its full traceback.

    Called from the tool runner's except block — the one place the live exception
    object still exists — so Sentry gets real stack frames and groups by exception
    type, instead of the flat "str(e)" message the downstream monitor would produce.

    Best-effort; never raises. No-op when Sentry is disabled.
    """
    if not _initialized:
        return
    try:
        import sentry_sdk
        with sentry_sdk.new_scope() as scope:
            scope.set_tag("tool_name", tool_name)
            scope.set_context("tool_call", {
                "tool_name": tool_name, "chat_id": chat_id, "user_id": user_id,
            })
            scope.fingerprint = ["tool", tool_name, type(exc).__name__]
            sentry_sdk.capture_exception(exc)
    except Exception:
        logger.debug("capture_tool_exception failed", exc_info=True)


def capture_agent_exception(exc: BaseException, *, chat_id: str = "", user_id: str = "",
                            model: str = "", category: str = "", phase: str = "agent_loop") -> None:
    """
    Send an agent-loop / LLM exception to Sentry with useful tags.

    The interactive chat path catches LLM errors (rate limits, overloads,
    timeouts) in base_agent and yields them to the client as an SSE `error`
    event — so the HTTP request returns 200 and Sentry's request-handler
    auto-instrumentation never sees them. Call this from that except block so
    those failures still become grouped, alertable Sentry issues.

    `category` (from llm_handler.classify_llm_error) drives the fingerprint so
    all e.g. rate-limit failures collapse into one issue.

    Best-effort; never raises. No-op when Sentry is disabled.
    """
    if not _initialized:
        return
    try:
        import sentry_sdk
        with sentry_sdk.new_scope() as scope:
            etype = type(exc).__name__
            scope.set_tag("error_phase", phase)
            scope.set_tag("llm_error_type", etype)
            if category:
                scope.set_tag("llm_error_category", category)
            if model:
                scope.set_tag("llm_model", model)
            scope.set_context("agent_call", {
                "chat_id": chat_id, "user_id": user_id, "model": model,
                "category": category, "phase": phase,
            })
            scope.fingerprint = ["agent", phase, category or etype]
            sentry_sdk.capture_exception(exc)
    except Exception:
        logger.debug("capture_agent_exception failed", exc_info=True)
