"""
Tracing service for synthetic dataset generation.

Emits OpenInference-flavored spans into the trace store under the
"Synthetic Dataset Generation" system task so that SDG LLM calls are
visible in the same trace UI as other agentic work.
"""

import json
import logging
import os
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from arthur_common.models.llm_model_providers import OpenAIMessage
from openinference.semconv.trace import MessageAttributes, SpanAttributes
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

from services.trace.trace_ingestion_service import TraceIngestionService
from utils import constants

logger = logging.getLogger(__name__)


class SyntheticDataSpanBuilder:
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


class SyntheticDataTracingService:
    def __init__(self, db_session: Session) -> None:
        self.db_session = db_session
        self.spans: List[SyntheticDataSpanBuilder] = []
        self.trace_id = uuid.uuid4().bytes

    def start_agent_span(
        self,
        operation: str,
        session_id: str,
    ) -> SyntheticDataSpanBuilder:
        span = SyntheticDataSpanBuilder(self.trace_id)
        span.name = f"synthetic_data.{operation}"
        span.set_attribute(SpanAttributes.OPENINFERENCE_SPAN_KIND, "AGENT")
        span.set_attribute(SpanAttributes.AGENT_NAME, "synthetic_data_generation")
        span.set_attribute(SpanAttributes.SESSION_ID, session_id)
        self.spans.append(span)
        return span

    def start_llm_span(
        self,
        parent: SyntheticDataSpanBuilder,
        model_name: str,
        model_provider: str,
    ) -> SyntheticDataSpanBuilder:
        span = SyntheticDataSpanBuilder(self.trace_id, parent.span_id)
        span.name = "llm_call"
        span.set_attribute(SpanAttributes.OPENINFERENCE_SPAN_KIND, "LLM")
        span.set_attribute(SpanAttributes.LLM_MODEL_NAME, model_name)
        span.set_attribute(SpanAttributes.LLM_PROVIDER, model_provider)
        self.spans.append(span)
        return span

    def set_llm_input_messages(
        self,
        span: SyntheticDataSpanBuilder,
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
        span: SyntheticDataSpanBuilder,
        content: Optional[str] = None,
        input_tokens: Optional[int] = None,
        output_tokens: Optional[int] = None,
        total_tokens: Optional[int] = None,
    ) -> None:
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

    def set_agent_input(
        self,
        span: SyntheticDataSpanBuilder,
        value: Dict[str, Any],
    ) -> None:
        span.set_attribute(SpanAttributes.INPUT_VALUE, json.dumps(value))
        span.set_attribute(SpanAttributes.INPUT_MIME_TYPE, "application/json")

    def set_agent_output(
        self,
        span: SyntheticDataSpanBuilder,
        value: Dict[str, Any],
    ) -> None:
        span.set_attribute(SpanAttributes.OUTPUT_VALUE, json.dumps(value))
        span.set_attribute(SpanAttributes.OUTPUT_MIME_TYPE, "application/json")

    def end_span(self, span: SyntheticDataSpanBuilder) -> None:
        span.end()

    def end_span_with_error(
        self,
        span: SyntheticDataSpanBuilder,
        error: str,
    ) -> None:
        span.end_with_error(error)

    def flush(self) -> None:
        if not self.spans:
            return

        resource = Resource(
            attributes=[
                KeyValue(
                    key=constants.TASK_ID_KEY,
                    value=AnyValue(string_value=constants.SYNTHETIC_DATASET_TASK_ID),
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
            service.process_trace_data(request.SerializeToString())
            logger.info("Flushed %d synthetic data spans", len(self.spans))
        except Exception:
            logger.exception("Failed to flush synthetic data spans")

        self.spans.clear()
