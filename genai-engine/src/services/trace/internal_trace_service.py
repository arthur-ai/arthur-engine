"""
Internal tracing service for emitting OpenInference-flavored spans from
engine-internal services (chatbot, synthetic data generation, etc.) into
the trace store under a caller-specified system task.

One instance per logical operation (a single request/response). Build spans
with ``start_agent_span`` / ``start_llm_span`` / ``start_tool_span``, attach
attributes via the ``set_*`` helpers, then ``flush()`` to persist them.
"""

import json
import logging
import os
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, List, Literal, Optional

from arthur_common.models.llm_model_providers import OpenAIMessage, ToolCall
from openinference.semconv.trace import (
    MessageAttributes,
    SpanAttributes,
    ToolCallAttributes,
)
from opentelemetry.proto.collector.trace.v1.trace_service_pb2 import (
    ExportTraceServiceRequest,
)
from opentelemetry.proto.common.v1.common_pb2 import AnyValue, KeyValue
from opentelemetry.proto.resource.v1.resource_pb2 import Resource
from opentelemetry.proto.trace.v1.trace_pb2 import (
    ResourceSpans,
    ScopeSpans,
    Span,
    Status,
)
from sqlalchemy.orm import Session

from repositories.continuous_evals_repository import ContinuousEvalsRepository
from services.trace.trace_ingestion_service import TraceIngestionService
from utils import constants

logger = logging.getLogger(__name__)


class TraceSpanBuilder:
    def __init__(self, trace_id: bytes, parent_span_id: Optional[bytes] = None) -> None:
        self.trace_id = trace_id
        self.span_id = os.urandom(8)
        self.parent_span_id = parent_span_id or b""
        self.name = ""
        self.start_time = datetime.now(timezone.utc)
        self.end_time: Optional[datetime] = None
        self.attributes: List[KeyValue] = []
        self.status = Status()

    def set_attribute(self, key: str, value: Any) -> None:
        if isinstance(value, int):
            self.attributes.append(KeyValue(key=key, value=AnyValue(int_value=value)))
        elif isinstance(value, Enum):
            self.attributes.append(
                KeyValue(key=key, value=AnyValue(string_value=value.value)),
            )
        else:
            self.attributes.append(
                KeyValue(key=key, value=AnyValue(string_value=str(value))),
            )

    def end(self) -> None:
        self.end_time = datetime.now(timezone.utc)
        self.status = Status(code=Status.STATUS_CODE_OK)

    def end_with_error(self, message: str) -> None:
        self.status = Status(code=Status.STATUS_CODE_ERROR, message=message)
        self.end_time = datetime.now(timezone.utc)

    def to_proto(self) -> Span:
        start_ns = int(self.start_time.timestamp() * 1e9)
        end_ns = int(self.end_time.timestamp() * 1e9) if self.end_time else start_ns
        return Span(
            trace_id=self.trace_id,
            span_id=self.span_id,
            parent_span_id=self.parent_span_id,
            name=self.name,
            kind=Span.SPAN_KIND_INTERNAL,
            start_time_unix_nano=start_ns,
            end_time_unix_nano=end_ns,
            attributes=self.attributes,
            status=self.status,
        )


LLMOutputEnvelope = Literal["text", "raw"]


class InternalTraceService:
    """Collect OpenInference spans for an internal operation and flush them
    to the trace store under a specific system task.

    Args:
        db_session: SQLAlchemy session used by the underlying
            ``TraceIngestionService`` on flush.
        task_id: System task ID to attach to every span's resource, so the
            trace shows up under the right task in the trace UI.
        service_name: Logical name of the calling service, used in log
            messages on flush. Not written to span attributes.
        enqueue_continuous_evals: If True, enqueue continuous-eval jobs for
            root spans after flush. Mirrors the behavior of the public
            ``/api/v1/traces`` route. Defaults to False so internal-only
            traces (chatbot, synthetic data generation) don't trigger evals.
    """

    def __init__(
        self,
        db_session: Session,
        *,
        task_id: str,
        service_name: str,
        enqueue_continuous_evals: bool = False,
    ) -> None:
        self.db_session = db_session
        self.task_id = task_id
        self.service_name = service_name
        self.enqueue_continuous_evals = enqueue_continuous_evals
        self.spans: List[TraceSpanBuilder] = []
        self.trace_id = uuid.uuid4().bytes

    def start_agent_span(
        self,
        *,
        name: str,
        agent_name: str,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> TraceSpanBuilder:
        span = TraceSpanBuilder(self.trace_id)
        span.name = name
        span.set_attribute(SpanAttributes.OPENINFERENCE_SPAN_KIND, "AGENT")
        span.set_attribute(SpanAttributes.AGENT_NAME, agent_name)
        if user_id is not None:
            span.set_attribute(SpanAttributes.USER_ID, user_id)
        if session_id is not None:
            span.set_attribute(SpanAttributes.SESSION_ID, session_id)
        self.spans.append(span)
        return span

    def start_llm_span(
        self,
        parent: TraceSpanBuilder,
        model_name: str,
        model_provider: str,
    ) -> TraceSpanBuilder:
        span = TraceSpanBuilder(self.trace_id, parent.span_id)
        span.name = "llm_call"
        span.set_attribute(SpanAttributes.OPENINFERENCE_SPAN_KIND, "LLM")
        span.set_attribute(SpanAttributes.LLM_MODEL_NAME, model_name)
        span.set_attribute(SpanAttributes.LLM_PROVIDER, model_provider)
        self.spans.append(span)
        return span

    def start_tool_span(
        self,
        parent: TraceSpanBuilder,
        tool_name: str,
    ) -> TraceSpanBuilder:
        span = TraceSpanBuilder(self.trace_id, parent.span_id)
        span.name = tool_name
        span.set_attribute(SpanAttributes.OPENINFERENCE_SPAN_KIND, "TOOL")
        span.set_attribute(SpanAttributes.TOOL_NAME, tool_name)
        self.spans.append(span)
        return span

    def set_llm_input_messages(
        self,
        span: TraceSpanBuilder,
        messages: List[OpenAIMessage],
    ) -> None:
        input_parts = []
        for i, msg in enumerate(messages):
            prefix = f"{SpanAttributes.LLM_INPUT_MESSAGES}.{i}"
            span.set_attribute(f"{prefix}.{MessageAttributes.MESSAGE_ROLE}", msg.role)
            if msg.content:
                content = (
                    msg.content if isinstance(msg.content, str) else str(msg.content)
                )
                span.set_attribute(
                    f"{prefix}.{MessageAttributes.MESSAGE_CONTENT}",
                    content,
                )
                input_parts.append({"role": str(msg.role), "content": content})
        span.set_attribute(
            SpanAttributes.INPUT_VALUE,
            json.dumps({"messages": input_parts}),
        )
        span.set_attribute(SpanAttributes.INPUT_MIME_TYPE, "application/json")

    def set_llm_response(
        self,
        span: TraceSpanBuilder,
        *,
        content: Optional[str] = None,
        tool_calls: Optional[List[ToolCall]] = None,
        input_tokens: Optional[int] = None,
        output_tokens: Optional[int] = None,
        total_tokens: Optional[int] = None,
        output_envelope: LLMOutputEnvelope = "text",
    ) -> None:
        """Record an LLM completion on an LLM span.

        ``output_envelope`` controls how ``OUTPUT_VALUE`` is serialized:
        - ``"text"``: wraps content as ``{"text": content or ""}`` — use for
          prose replies (default, matches chatbot behavior).
        - ``"raw"``: writes content as-is — use when content is already a
          JSON string (e.g. structured-output responses).
        """
        output_prefix = f"{SpanAttributes.LLM_OUTPUT_MESSAGES}.0"
        span.set_attribute(
            f"{output_prefix}.{MessageAttributes.MESSAGE_ROLE}",
            "assistant",
        )
        if content:
            span.set_attribute(
                f"{output_prefix}.{MessageAttributes.MESSAGE_CONTENT}",
                content,
            )

        if tool_calls:
            for j, tc in enumerate(tool_calls):
                tc_prefix = (
                    f"{output_prefix}.{MessageAttributes.MESSAGE_TOOL_CALLS}.{j}"
                )
                span.set_attribute(
                    f"{tc_prefix}.{ToolCallAttributes.TOOL_CALL_FUNCTION_NAME}",
                    tc.function.name,
                )
                span.set_attribute(
                    f"{tc_prefix}.{ToolCallAttributes.TOOL_CALL_FUNCTION_ARGUMENTS_JSON}",
                    tc.function.arguments,
                )

        if output_envelope == "text":
            span.set_attribute(
                SpanAttributes.OUTPUT_VALUE,
                json.dumps({"text": content or ""}),
            )
        else:
            span.set_attribute(
                SpanAttributes.OUTPUT_VALUE,
                content if content is not None else "",
            )
        span.set_attribute(SpanAttributes.OUTPUT_MIME_TYPE, "application/json")

        if input_tokens is not None:
            span.set_attribute(SpanAttributes.LLM_TOKEN_COUNT_PROMPT, input_tokens)
        if output_tokens is not None:
            span.set_attribute(SpanAttributes.LLM_TOKEN_COUNT_COMPLETION, output_tokens)
        if total_tokens is not None:
            span.set_attribute(SpanAttributes.LLM_TOKEN_COUNT_TOTAL, total_tokens)

    def set_tool_input(self, span: TraceSpanBuilder, value: str) -> None:
        span.set_attribute(SpanAttributes.INPUT_VALUE, value)

    def set_tool_output(self, span: TraceSpanBuilder, value: str) -> None:
        span.set_attribute(SpanAttributes.OUTPUT_VALUE, value)

    def set_input_json(self, span: TraceSpanBuilder, value: Any) -> None:
        """Set ``INPUT_VALUE`` to a JSON-serialized value with JSON MIME type."""
        span.set_attribute(SpanAttributes.INPUT_VALUE, json.dumps(value))
        span.set_attribute(SpanAttributes.INPUT_MIME_TYPE, "application/json")

    def set_output_json(self, span: TraceSpanBuilder, value: Any) -> None:
        """Set ``OUTPUT_VALUE`` to a JSON-serialized value with JSON MIME type."""
        span.set_attribute(SpanAttributes.OUTPUT_VALUE, json.dumps(value))
        span.set_attribute(SpanAttributes.OUTPUT_MIME_TYPE, "application/json")

    def end_span(self, span: TraceSpanBuilder) -> None:
        span.end()

    def end_span_with_error(self, span: TraceSpanBuilder, error: str) -> None:
        span.end_with_error(error)

    def flush(self) -> None:
        if not self.spans:
            return

        resource = Resource(
            attributes=[
                KeyValue(
                    key=constants.TASK_ID_KEY,
                    value=AnyValue(string_value=self.task_id),
                ),
            ],
        )
        proto_spans = [s.to_proto() for s in self.spans]
        request = ExportTraceServiceRequest(
            resource_spans=[
                ResourceSpans(
                    resource=resource,
                    scope_spans=[ScopeSpans(spans=proto_spans)],
                ),
            ],
        )

        try:
            service = TraceIngestionService(self.db_session)
            db_spans, _ = service.process_trace_data(request.SerializeToString())
            logger.info(
                "Flushed %d %s spans",
                len(self.spans),
                self.service_name,
            )
            if self.enqueue_continuous_evals and db_spans:
                ContinuousEvalsRepository(
                    self.db_session,
                ).enqueue_continuous_evals_for_root_spans(db_spans)
        except Exception:
            logger.exception("Failed to flush %s spans", self.service_name)

        self.spans.clear()
