"""
Tool execution monitoring & alerting.

A single chokepoint for observing the outcome of every tool call. Wired in from
``modules/tools/executor.py`` wherever a ``ToolExecutionResult`` is constructed, so
every tool — first-order and sandbox/skill — flows through here exactly once.

For each outcome it:
  1. Emits one structured log line (``tool_outcome ...``) for log-based metrics/queries.
  2. Reports failures (and slow calls) to Sentry, grouped by tool + error signature.
  3. Fires a throttled, deduped email alert so you're notified the moment tools start
     failing — without getting spammed when the same failure repeats.

Everything here is best-effort: a bug in monitoring must never break a tool call, so
the public entry point swallows its own exceptions.

This is intentionally backend-agnostic: the structured log line is the foundation, and
Sentry/email are layered on top. Pointing it at GCP/Grafana later means adding an
exporter, not changing call sites.
"""
import asyncio
import re
import time
from collections import deque
from typing import Optional

from core.config import Config
from utils.logger import get_logger

logger = get_logger(__name__)

try:
    import sentry_sdk
    _SENTRY_AVAILABLE = True
except ImportError:
    _SENTRY_AVAILABLE = False


# Per-process throttle: error signature -> last alert time (monotonic seconds).
# Per-process is fine — Railway runs a single backend; worst case a second
# instance sends one extra alert per window.
_last_alert: dict[str, float] = {}

# Per-process rolling window of failure timestamps (monotonic seconds) per signature.
# Used to require N failures within a window before a signature is worth reporting,
# so a single transient blip never reaches Sentry/email.
_failure_window: dict[str, deque] = {}


def _error_signature(tool_name: str, error: Optional[str]) -> str:
    """
    Collapse a tool + error string into a stable signature.

    Strips volatile bits (numbers, URLs, whitespace) so that parametrized failures
    — "request abc123 failed", "request def456 failed" — dedupe to one alert and one
    Sentry issue instead of a flood.
    """
    if not error:
        return tool_name
    sig = error.lower()
    sig = re.sub(r"https?://\S+", "<url>", sig)
    sig = re.sub(r"\d+", "#", sig)
    sig = re.sub(r"\s+", " ", sig).strip()
    return f"{tool_name}:{sig[:140]}"


def _should_alert(signature: str) -> bool:
    """True if we haven't alerted for this signature within the throttle window."""
    now = time.monotonic()
    last = _last_alert.get(signature)
    window = Config.TOOL_ALERT_THROTTLE_SECONDS
    if last is not None and (now - last) < window:
        return False
    _last_alert[signature] = now
    return True


def should_report_failure(tool_name: str, error: Optional[str]) -> bool:
    """
    Rolling-window failure gate. Record this failure and return True only once the
    same tool+error signature has failed ``TOOL_ALERT_MIN_FAILURES`` times within the
    last ``TOOL_ALERT_WINDOW_SECONDS`` — then throttle (``TOOL_ALERT_THROTTLE_SECONDS``)
    so the 6th, 7th, ... failures don't re-fire.

    Net effect: a one-off failure is invisible; a tool that's genuinely broken
    (≥5 failures/hour by default) surfaces exactly once per window.

    MUST be called exactly once per failed outcome — it mutates the window counter.
    """
    signature = _error_signature(tool_name, error)
    now = time.monotonic()
    window = Config.TOOL_ALERT_WINDOW_SECONDS

    dq = _failure_window.setdefault(signature, deque())
    dq.append(now)
    cutoff = now - window
    while dq and dq[0] < cutoff:
        dq.popleft()

    if len(dq) < Config.TOOL_ALERT_MIN_FAILURES:
        return False
    # Threshold crossed — collapse the ongoing burst to one alert per throttle window.
    return _should_alert(signature)


def _report_to_sentry(
    *, tool_name: str, signature: str, error: Optional[str],
    duration_ms: float, slow: bool, chat_id: str, user_id: str,
) -> None:
    if not (_SENTRY_AVAILABLE and Config.SENTRY_DSN):
        return
    try:
        with sentry_sdk.new_scope() as scope:
            scope.set_tag("tool_name", tool_name)
            scope.set_tag("tool_slow", slow)
            scope.set_context("tool_call", {
                "tool_name": tool_name,
                "duration_ms": round(duration_ms, 1),
                "chat_id": chat_id,
                "user_id": user_id,
                "error": error,
            })
            # Group by our signature so repeated failures collapse into one issue.
            scope.fingerprint = ["tool", signature]
            if slow:
                sentry_sdk.capture_message(
                    f"Slow tool call: {tool_name} took {duration_ms:.0f}ms",
                    level="warning",
                )
            else:
                sentry_sdk.capture_message(
                    f"Tool failed: {tool_name} — {error or 'unknown error'}",
                    level="error",
                )
    except Exception:
        logger.debug("Sentry capture failed", exc_info=True)


async def _send_alert_email(
    *, tool_name: str, error: Optional[str], duration_ms: float,
    slow: bool, chat_id: str, user_id: str,
) -> None:
    to_email = Config.NOTIFICATION_EMAIL
    if not (to_email and Config.RESEND_API_KEY):
        return
    # Imported lazily to avoid a circular import (notifications -> config -> ...).
    from services.notifications import _send_resend_email

    kind = "running slow" if slow else "failing"
    emoji = "🐢" if slow else "🔴"
    subject = f"{emoji} Finch tool {kind}: {tool_name}"
    detail = (
        f"took {duration_ms:.0f}ms (threshold {Config.TOOL_ALERT_SLOW_MS}ms)"
        if slow else f"<code>{(error or 'unknown error')}</code>"
    )
    html = f"""
        <h2>{emoji} Tool {kind}: <code>{tool_name}</code></h2>
        <p>{detail}</p>
        <table style="border-collapse:collapse;font-family:monospace;font-size:13px">
          <tr><td style="padding:2px 12px 2px 0;color:#888">tool</td><td>{tool_name}</td></tr>
          <tr><td style="padding:2px 12px 2px 0;color:#888">duration</td><td>{duration_ms:.0f}ms</td></tr>
          <tr><td style="padding:2px 12px 2px 0;color:#888">chat_id</td><td>{chat_id}</td></tr>
          <tr><td style="padding:2px 12px 2px 0;color:#888">user_id</td><td>{user_id}</td></tr>
        </table>
        <p style="color:#888;font-size:12px">
          Throttled to one alert per signature per {Config.TOOL_ALERT_THROTTLE_SECONDS}s.
          Full history in Sentry.
        </p>
    """
    try:
        await _send_resend_email(to_email, subject, html)
    except Exception:
        logger.warning("Failed to send tool alert email", exc_info=True)


def record_tool_outcome(
    *,
    tool_name: str,
    success: bool,
    duration_ms: float,
    error: Optional[str] = None,
    chat_id: str = "",
    user_id: str = "",
    exc_reported: bool = False,
    alerted: Optional[bool] = None,
) -> None:
    """
    Record the outcome of a single tool call. Best-effort; never raises.

    Call this once per completed tool execution. Successes are logged at debug level.
    Failures only reach Sentry/email once the same tool+error signature has failed
    ``TOOL_ALERT_MIN_FAILURES`` times within ``TOOL_ALERT_WINDOW_SECONDS`` (see
    ``should_report_failure``); slow calls use a simple per-window throttle.

    exc_reported: True when this failure was a raised exception already handled at the
    source (tool runner) — it ran the same rolling-window gate and, if it crossed the
    threshold, captured the exception to Sentry with its real traceback. In that case
    ``alerted`` carries the gate's decision so we don't re-count or re-report here.
    """
    try:
        slow = success and duration_ms >= Config.TOOL_ALERT_SLOW_MS

        # 1. Structured log line — stable key=value shape for log-based metrics.
        log = logger.error if not success else (logger.warning if slow else logger.debug)
        log(
            "tool_outcome tool=%s success=%s duration_ms=%.0f chat_id=%s%s",
            tool_name, success, duration_ms, chat_id,
            f" error={error!r}" if error else "",
        )

        if success and not slow:
            return  # nothing to alert on

        signature = _error_signature(tool_name, None if slow else error)

        # Decide whether this outcome is worth surfacing, and report to Sentry if so.
        if exc_reported:
            # The runner already ran the rolling-window gate and, if it crossed the
            # threshold, captured the exception to Sentry with its real traceback.
            # Reuse its decision; don't re-count or re-report.
            should = bool(alerted)
        elif slow:
            # Slow calls aren't "failures" — keep the simple one-per-window throttle.
            should = _should_alert(signature)
            if should:
                _report_to_sentry(
                    tool_name=tool_name, signature=signature, error=error,
                    duration_ms=duration_ms, slow=slow, chat_id=chat_id, user_id=user_id,
                )
        else:
            # Non-exception failure (e.g. a 4xx the tool returned): count it toward
            # the rolling window and report to Sentry only once it crosses the threshold.
            should = should_report_failure(tool_name, error)
            if should:
                _report_to_sentry(
                    tool_name=tool_name, signature=signature, error=error,
                    duration_ms=duration_ms, slow=slow, chat_id=chat_id, user_id=user_id,
                )

        if not should or not Config.TOOL_ALERTS_ENABLED:
            return

        # Fire the email without blocking the tool path. Requires a running loop,
        # which we always have here (executor runs inside the async request).
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            return
        loop.create_task(_send_alert_email(
            tool_name=tool_name, error=error, duration_ms=duration_ms,
            slow=slow, chat_id=chat_id, user_id=user_id,
        ))
    except Exception:
        # Monitoring must never break a tool call.
        logger.debug("record_tool_outcome failed", exc_info=True)
