"""Best-effort emission of GUARDRAIL trace spans from the stateful validate flow.

Stateful ``/validate`` calls persist an inference + rule results but emit no
telemetry, so guardrail invocations never appear in the trace viewer. This module
emits a GUARDRAIL span (carrying the per-rule outcomes) into the trace store via the
self-ingesting ``InternalTraceService`` so they show up alongside (or inside) traces.

Emission is always best-effort: a telemetry failure must never fail the validation
response, so every public entry point swallows and logs exceptions.
"""

import hashlib
import logging
from typing import Any, Optional

from arthur_common.models.response_schemas import ExternalRuleResult
from sqlalchemy.orm import Session

from schemas.guardrail_span_schemas import GuardrailSpanResult
from services.trace.internal_trace_service import InternalTraceService

logger = logging.getLogger(__name__)

_TRACE_ID_LEN_BYTES = 16
_SPAN_ID_LEN_BYTES = 8
_SERVICE_NAME = "guardrail_validate"


def _derive_trace_id(inference_id: str) -> bytes:
    return hashlib.sha256(inference_id.encode()).digest()[:_TRACE_ID_LEN_BYTES]


def _derive_span_id(inference_id: str, stage: str) -> bytes:
    return hashlib.sha256(f"{stage}:{inference_id}".encode()).digest()[
        :_SPAN_ID_LEN_BYTES
    ]


def _hex_to_bytes(hex_str: str, expected_len: int) -> bytes:
    raw = bytes.fromhex(hex_str)  # raises ValueError on malformed hex
    if len(raw) != expected_len:
        raise ValueError(
            f"expected {expected_len} bytes ({expected_len * 2} hex chars), "
            f"got {len(raw)}",
        )
    return raw


def emit_guardrail_span(
    db_session: Session,
    *,
    task_id: Optional[str],
    inference_id: Optional[str],
    rule_results: Optional[list[ExternalRuleResult]],
    input_payload: dict[str, Any],
    is_response: bool,
    trace_id: Optional[str] = None,
    parent_span_id: Optional[str] = None,
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
) -> None:
    """Emit a GUARDRAIL span for one stateful validate call. Never raises.

    Placement precedence:
      1. caller ``trace_id`` + ``parent_span_id`` -> inject under that parent.
      2. caller ``trace_id`` only                 -> top-level span in that trace.
      3. neither (e.g. United)                     -> derive a trace per
         ``inference_id``; the response span nests under the prompt span so a
         prompt+response validation reads as one trace.

    ``trace_id`` (32 hex) / ``parent_span_id`` (16 hex) are the formats the trace API
    returns. A malformed caller id is logged and treated as absent (falls back to the
    derived trace). Emission is skipped for task-less callers (``task_id is None``).
    """
    if task_id is None:
        # Task-less (deprecated/stateless) paths don't emit — avoids polluting the
        # system/UNMAPPED task with orphan guardrail traces.
        return
    if not inference_id or not rule_results:
        # Nothing to anchor on or nothing to show.
        return

    try:
        stage = "response" if is_response else "prompt"
        own_span_id = _derive_span_id(inference_id, stage)

        # Parse trace_id and parent_span_id independently: a malformed parent
        # should only cost the nesting (span lands top-level in the caller's
        # trace), not discard an otherwise-valid trace_id.
        resolved_trace_id: Optional[bytes] = None
        resolved_parent: Optional[bytes] = None
        if trace_id:
            try:
                resolved_trace_id = _hex_to_bytes(trace_id, _TRACE_ID_LEN_BYTES)
            except ValueError:
                logger.warning(
                    "Invalid caller trace_id for inference %s; "
                    "falling back to a derived trace.",
                    inference_id,
                )
                resolved_trace_id = None
            if resolved_trace_id is not None and parent_span_id:
                try:
                    resolved_parent = _hex_to_bytes(parent_span_id, _SPAN_ID_LEN_BYTES)
                except ValueError:
                    logger.warning(
                        "Invalid caller parent_span_id for inference %s; "
                        "placing the guardrail span at the top level of the trace.",
                        inference_id,
                    )
                    resolved_parent = None

        if resolved_trace_id is not None:
            trace_id_bytes = resolved_trace_id
            parent_span_id_bytes = resolved_parent
        else:
            trace_id_bytes = _derive_trace_id(inference_id)
            parent_span_id_bytes = (
                _derive_span_id(inference_id, "prompt") if is_response else None
            )

        result = GuardrailSpanResult.from_validation(inference_id, rule_results)

        tracing = InternalTraceService(
            db_session,
            task_id=task_id,
            service_name=_SERVICE_NAME,
            trace_id=trace_id_bytes,
        )
        span = tracing.start_guardrail_span(
            name=f"guardrail.validate_{stage}",
            parent_span_id=parent_span_id_bytes,
            span_id=own_span_id,
            user_id=user_id,
            session_id=session_id,
        )
        tracing.set_input_json(span, input_payload)
        tracing.set_output_json(span, result.model_dump(mode="json"))
        tracing.end_span(span)
        tracing.flush()
    except Exception:
        logger.exception(
            "Failed to emit guardrail span for inference %s",
            inference_id,
        )
