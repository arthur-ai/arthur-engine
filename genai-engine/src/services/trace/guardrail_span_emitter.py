"""Best-effort emission of GUARDRAIL trace spans from the stateful validate flow.

Stateful ``/validate`` calls persist an inference + rule results but emit no telemetry,
so guardrail invocations never appear in the trace viewer. ``guardrail_span`` brackets
the rule evaluation with a GUARDRAIL span (duration = evaluation time); the span is
flushed in a separate ``persist()`` step the caller invokes after the inference is
saved, so a span is never stored for an inference that wasn't — no orphans, no
duplicates from rejected re-validations, no telemetry DB write ahead of the save.

Emission is best-effort: every recorder method swallows and logs exceptions. If the
evaluation raises, an ERROR span is flushed immediately (no save will follow) and the
exception propagates unchanged.
"""

import hashlib
import logging
from contextlib import contextmanager
from typing import Any, Iterator, Optional

from sqlalchemy.orm import Session

from schemas.guardrail_span_schemas import GuardrailSpanResult
from schemas.internal_schemas import (
    PromptRuleResult,
    ResponseRuleResult,
    RuleEngineResult,
)
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


class _GuardrailSpanRecorder:
    """One GUARDRAIL span around a stateful validate evaluation.

    ``start()`` opens the span before evaluation, ``finish()`` ends it right after,
    and ``persist()`` — called only after the inference save commits — writes it to
    the trace store. ``record_error()`` flushes immediately instead. Inert (every
    method no-ops) when disabled, unanchored, or the span could not be started.
    """

    def __init__(
        self,
        db_session: Session,
        *,
        enabled: bool,
        task_id: Optional[str],
        inference_id: Optional[str],
        input_payload: dict[str, Any],
        is_response: bool,
        trace_id: Optional[str],
        parent_span_id: Optional[str],
        user_id: Optional[str],
        session_id: Optional[str],
    ) -> None:
        self._db_session = db_session
        self._enabled = enabled
        self._task_id = task_id
        self._inference_id = inference_id
        self._input_payload = input_payload
        self._is_response = is_response
        self._trace_id = trace_id
        self._parent_span_id = parent_span_id
        self._user_id = user_id
        self._session_id = session_id
        self._tracing: Optional[InternalTraceService] = None
        self._span: Any = None
        self._rule_results: Optional[list[RuleEngineResult]] = None

    def start(self) -> None:
        task_id, inference_id = self._task_id, self._inference_id
        if not self._enabled or task_id is None or not inference_id:
            return
        try:
            stage = "response" if self._is_response else "prompt"
            trace_id_bytes, parent_span_id_bytes = self._resolve_placement(
                inference_id,
            )
            self._tracing = InternalTraceService(
                self._db_session,
                task_id=task_id,
                service_name=_SERVICE_NAME,
                trace_id=trace_id_bytes,
            )
            self._span = self._tracing.start_guardrail_span(
                name=f"guardrail.validate_{stage}",
                parent_span_id=parent_span_id_bytes,
                span_id=_derive_span_id(inference_id, stage),
                user_id=self._user_id,
                session_id=self._session_id,
            )
            self._tracing.set_input_json(self._span, self._input_payload)
        except Exception:
            logger.exception(
                "Failed to start guardrail span for inference %s",
                self._inference_id,
            )
            self._tracing = None
            self._span = None

    def set_rule_results(self, rule_results: list[RuleEngineResult]) -> None:
        """Store raw engine results; ``finish()`` converts them under its
        swallow-and-log protection, so a conversion bug can only cost the span."""
        self._rule_results = rule_results

    def finish(self) -> None:
        if self._tracing is None or self._span is None or self._inference_id is None:
            return
        try:
            results = self._rule_results or []
            if not results:
                # Nothing to show; discard so persist() is a no-op.
                self._tracing = None
                self._span = None
                return
            model_cls = ResponseRuleResult if self._is_response else PromptRuleResult
            external = [
                model_cls._from_rule_engine_model(r)._to_response_model()
                for r in results
            ]
            payload = GuardrailSpanResult.from_validation(self._inference_id, external)
            self._tracing.set_output_json(self._span, payload.model_dump(mode="json"))
            self._tracing.end_span(self._span)
        except Exception:
            logger.exception(
                "Failed to finish guardrail span for inference %s",
                self._inference_id,
            )
            # Discard so persist() can't flush a half-built span.
            self._tracing = None
            self._span = None

    def persist(self) -> None:
        """Flush the finished span. Call only after the business write has committed.
        No-op if the span was never started, was discarded, or already flushed."""
        if self._tracing is None or self._span is None:
            return
        try:
            self._tracing.flush()
        except Exception:
            logger.exception(
                "Failed to persist guardrail span for inference %s",
                self._inference_id,
            )

    def record_error(self, exc: Exception) -> None:
        if self._tracing is None or self._span is None:
            return
        try:
            self._tracing.end_span_with_error(
                self._span,
                str(exc) or exc.__class__.__name__,
            )
            self._tracing.flush()
        except Exception:
            logger.exception(
                "Failed to record guardrail span error for inference %s",
                self._inference_id,
            )

    def _resolve_placement(self, inference_id: str) -> tuple[bytes, Optional[bytes]]:
        """Precedence: caller trace_id + parent_span_id -> nest under that parent;
        caller trace_id only -> top-level in that trace; neither -> trace derived
        from the inference id, response span nested under the prompt span. Malformed
        caller ids are logged and treated as absent."""
        resolved_trace: Optional[bytes] = None
        resolved_parent: Optional[bytes] = None
        if self._trace_id:
            try:
                resolved_trace = _hex_to_bytes(self._trace_id, _TRACE_ID_LEN_BYTES)
            except ValueError:
                logger.warning(
                    "Invalid caller trace_id for inference %s; deriving a trace.",
                    inference_id,
                )
                resolved_trace = None
            if resolved_trace is not None and self._parent_span_id:
                try:
                    resolved_parent = _hex_to_bytes(
                        self._parent_span_id,
                        _SPAN_ID_LEN_BYTES,
                    )
                except ValueError:
                    logger.warning(
                        "Invalid caller parent_span_id for inference %s; placing the "
                        "guardrail span at the top level of the trace.",
                        inference_id,
                    )
                    resolved_parent = None
        if resolved_trace is not None:
            return resolved_trace, resolved_parent
        derived_parent = (
            _derive_span_id(inference_id, "prompt") if self._is_response else None
        )
        return _derive_trace_id(inference_id), derived_parent


@contextmanager
def guardrail_span(
    db_session: Session,
    *,
    enabled: bool,
    task_id: Optional[str],
    inference_id: Optional[str],
    input_payload: dict[str, Any],
    is_response: bool,
    trace_id: Optional[str] = None,
    parent_span_id: Optional[str] = None,
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
) -> Iterator[_GuardrailSpanRecorder]:
    """Bracket a stateful guardrail evaluation with a GUARDRAIL trace span.

    Usage::

        with guardrail_span(db_session, enabled=..., task_id=..., inference_id=..., ...) as gspan:
            rule_results = RuleEngine(scorer_client).evaluate(request, rules)
            gspan.set_rule_results(rule_results)  # raw RuleEngineResult list
        inference = repo.save_prompt(...)  # business write commits first
        gspan.persist()                    # only now is the span flushed

    The span's duration covers the body only. If ``persist()`` is never called
    (e.g. the save failed) the span is dropped, so spans never reference an
    unpersisted inference. If the body raises, an ERROR span is flushed immediately
    and the exception propagates. When ``enabled`` is False or there is no
    task/inference, the recorder is a no-op — the body still runs.
    """
    recorder = _GuardrailSpanRecorder(
        db_session,
        enabled=enabled,
        task_id=task_id,
        inference_id=inference_id,
        input_payload=input_payload,
        is_response=is_response,
        trace_id=trace_id,
        parent_span_id=parent_span_id,
        user_id=user_id,
        session_id=session_id,
    )
    recorder.start()
    try:
        yield recorder
    except Exception as exc:
        recorder.record_error(exc)
        raise
    recorder.finish()
