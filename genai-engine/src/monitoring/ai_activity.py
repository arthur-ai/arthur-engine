"""Request-scoped accumulator for the engine's own AI model invocations.

Model invocations happen deep in the scorer — often inside worker threads spawned
by ``TracedThreadPoolExecutor`` — while the audit log entry is assembled in HTTP
middleware after the request completes. A ``ContextVar`` bridges that gap.

The accumulator is started by the audit middleware **before** it calls the
downstream app and read back **after**, both in the middleware's own context.
Starlette copies that context into the ``call_next`` task, so the scorer (and its
thread-pool workers, which copy the context again at submit time) sees the same
list object and appends to it in place; the middleware then reads those appends
from the very same object. This is why the accumulator is set in the *outer*
middleware scope rather than inside a dependency — ``ContextVar`` mutations made
*inside* ``call_next`` do not propagate back out to the middleware.

When the feature is disabled the ``ContextVar`` is never set, so
:func:`record_model_invocation` is a cheap no-op and the base ``AuditLog`` (V1)
is emitted unchanged. The same no-op behaviour covers model calls made outside
any request (e.g. background continuous-eval runs).
"""

from __future__ import annotations

import functools
import logging
import time
from contextvars import ContextVar, Token
from typing import Any, Callable, Optional

from schemas.audit_log_schemas import ModelInvocation

logger = logging.getLogger(__name__)

_model_invocations: ContextVar[Optional[list[ModelInvocation]]] = ContextVar(
    "model_invocations",
    default=None,
)


def begin_ai_activity() -> Optional[Token[Optional[list[ModelInvocation]]]]:
    """Start collecting model invocations for the current request, if enabled.

    Must be called from the audit middleware **before** ``call_next`` so the
    downstream app inherits this context. Returns a reset token to pass to
    :func:`end_ai_activity`, or None when the feature is disabled.
    """
    # Imported lazily to keep this module off the scorer's hot-path import chain.
    from config.config import Config

    if not Config.audit_log_include_ai_activity():
        return None

    return _model_invocations.set([])


def end_ai_activity(token: Optional[Token[Optional[list[ModelInvocation]]]]) -> None:
    """Reset the accumulator so it never leaks into a later request on this context."""
    if token is not None:
        _model_invocations.reset(token)


def get_recorded_invocations() -> list[ModelInvocation]:
    """Return the invocations recorded for the current request (empty if none)."""
    return _model_invocations.get() or []


def record_model_invocation(invocation: ModelInvocation) -> None:
    """Append one model invocation to the current request's accumulator.

    No-op when there is no active accumulator (feature disabled, or a call made
    outside an HTTP request such as a background eval). Never raises — audit
    instrumentation must not break the evaluation it observes.
    """
    try:
        accumulator = _model_invocations.get()
        if accumulator is None:
            return
        accumulator.append(invocation)
    except Exception:  # pragma: no cover - defensive; instrumentation is best-effort
        logger.debug("Failed to record model invocation", exc_info=True)


def track_ml_model_invocation(
    *,
    model_name: str,
    operation: str,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Decorator that records a local (on-box) ML model invocation.

    Wraps a ``RuleScorer.score(self, request)`` method: times the call, and records
    a metadata-only :class:`ModelInvocation` (no tokens — local models are not
    LLM-tokenized) whether the call succeeds or raises.
    """

    def decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
        @functools.wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            start = time.perf_counter()
            success = True
            error_type: Optional[str] = None
            try:
                return fn(*args, **kwargs)
            except Exception as e:
                success = False
                error_type = type(e).__name__
                raise
            finally:
                try:
                    record_model_invocation(
                        ModelInvocation(
                            model_name=model_name,
                            provider="local",
                            model_type="ml_classifier",
                            operation=operation,
                            latency_ms=int((time.perf_counter() - start) * 1000),
                            success=success,
                            error_type=error_type,
                        ),
                    )
                except Exception:  # pragma: no cover - best-effort instrumentation
                    logger.debug(
                        "Failed to record ML model invocation",
                        exc_info=True,
                    )

        return wrapper

    return decorator
