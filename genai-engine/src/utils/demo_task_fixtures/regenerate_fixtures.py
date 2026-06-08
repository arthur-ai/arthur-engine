"""Regenerate the demo-task trace fixtures (`*.binpb`) in place.

The fixtures are captured OTLP ``ExportTraceServiceRequest`` payloads that are
replayed into the trace store when a demo task is created
(``DemoTaskRepository._replay_demo_traces``). They were captured before the
trace service learned to record:

  * ``llm.tools`` (the tool catalog available to the model), and
  * ``tool_calls`` on assistant *input* messages (a pure tool-call turn has
    ``content=None``, so it serialized to just ``{"role": "assistant"}``).

Re-running a live chatbot to recapture them isn't reproducible (the demo models
are placeholders, and tool-call args are non-deterministic). Instead this script
reconstructs the missing pieces from data already in the fixtures:

  * Each assistant tool-call turn that appears in a later span's *input* is the
    *output* of an earlier ``llm_call`` span in the same trace. The k-th
    assistant turn in a span's input is the output of ``llm_call`` span #k
    (spans ordered by start time). The final span's output is the text answer.
  * The tool catalog is the static ``DEMO_TASK_TOOLS``.

The per-span input messages and tools are then re-serialized with the *real*
production helpers (``set_llm_input_messages`` / ``set_llm_tools``) so the
fixtures match exactly what live traces now emit. Idempotent: re-running
reconstructs from role/content + outputs again and produces the same bytes.

Usage:
    PYTHONPATH=src GENAI_ENGINE_SECRET_STORE_KEY=... \
        uv run python -m utils.demo_task_fixtures.regenerate_fixtures
"""

import re
from pathlib import Path
from typing import Dict, List, Tuple
from unittest.mock import MagicMock

from arthur_common.models.llm_model_providers import (
    MessageRole,
    OpenAIMessage,
    ToolCall,
    ToolCallFunction,
)
from opentelemetry.proto.collector.trace.v1.trace_service_pb2 import (
    ExportTraceServiceRequest,
)
from opentelemetry.proto.trace.v1.trace_pb2 import Span

from services.trace.internal_trace_service import InternalTraceService, TraceSpanBuilder
from utils.demo_task_fixtures.demo_task_resources import DEMO_TASK_TOOLS

FIXTURES_DIR = Path(__file__).resolve().parent

# Attribute prefixes this script owns and fully rewrites. Everything else on the
# span (output messages, token counts, model name, span kind, ...) is preserved.
_OWNED_PREFIXES = (
    "llm.input_messages.",
    "llm.tools.",
    "input.value",
    "input.mime_type",
)

_INPUT_MSG_RE = re.compile(r"^llm\.input_messages\.(\d+)\.message\.(.+)$")
_OUTPUT_TC_RE = re.compile(
    r"^llm\.output_messages\.0\.message\.tool_calls\.(\d+)\.tool_call\.function\.(name|arguments)$",
)


def _output_tool_calls(span: Span) -> List[ToolCall]:
    """Extract the assistant output tool calls (name + arguments) for a span."""
    by_index: Dict[int, Dict[str, str]] = {}
    for a in span.attributes:
        m = _OUTPUT_TC_RE.match(a.key)
        if m:
            by_index.setdefault(int(m.group(1)), {})[m.group(2)] = a.value.string_value
    tool_calls = []
    for j in sorted(by_index):
        fn = by_index[j]
        tool_calls.append(
            ToolCall(
                id=f"call_{j}",
                function=ToolCallFunction(
                    name=fn.get("name", ""),
                    arguments=fn.get("arguments", "{}"),
                ),
            ),
        )
    return tool_calls


def _reconstruct_input_messages(
    span: Span,
    prior_outputs: List[List[ToolCall]],
) -> List[OpenAIMessage]:
    """Rebuild the ordered input message list for an llm_call span.

    Assistant messages (a tool-call turn with no content) are filled with the
    tool calls from the matching earlier span output: the k-th assistant message
    in this span's input corresponds to ``prior_outputs[k]``.
    """
    by_index: Dict[int, Dict[str, str]] = {}
    for a in span.attributes:
        m = _INPUT_MSG_RE.match(a.key)
        if m:
            by_index.setdefault(int(m.group(1)), {})[m.group(2)] = a.value.string_value

    messages: List[OpenAIMessage] = []
    assistant_seen = 0
    for i in sorted(by_index):
        fields = by_index[i]
        role = fields.get("role")
        content = fields.get("content")
        if role == MessageRole.AI.value:
            tool_calls = (
                prior_outputs[assistant_seen]
                if assistant_seen < len(prior_outputs)
                else None
            )
            assistant_seen += 1
            messages.append(
                OpenAIMessage(
                    role=MessageRole.AI,
                    content=content or None,
                    tool_calls=tool_calls or None,
                ),
            )
        else:
            messages.append(OpenAIMessage(role=MessageRole(role), content=content))
    return messages


def _rewrite_span(
    service: InternalTraceService,
    span: Span,
    prior_outputs: List[List[ToolCall]],
) -> None:
    messages = _reconstruct_input_messages(span, prior_outputs)

    builder = TraceSpanBuilder(trace_id=span.trace_id)
    service.set_llm_input_messages(builder, messages)
    service.set_llm_tools(builder, DEMO_TASK_TOOLS)

    kept = [a for a in span.attributes if not a.key.startswith(_OWNED_PREFIXES)]
    del span.attributes[:]
    span.attributes.extend(kept)
    span.attributes.extend(builder.attributes)


def regenerate_fixture(path: Path, service: InternalTraceService) -> Tuple[int, int]:
    request = ExportTraceServiceRequest()
    request.ParseFromString(path.read_bytes())

    # Group llm_call spans per trace and order by start time so the
    # assistant-turn -> earlier-output mapping is correct within a conversation.
    llm_spans_by_trace: Dict[bytes, List[Span]] = {}
    for rs in request.resource_spans:
        for ss in rs.scope_spans:
            for sp in ss.spans:
                if sp.name == "llm_call":
                    llm_spans_by_trace.setdefault(sp.trace_id, []).append(sp)

    rewritten = 0
    for spans in llm_spans_by_trace.values():
        spans.sort(key=lambda s: s.start_time_unix_nano)
        outputs = [_output_tool_calls(sp) for sp in spans]
        for idx, sp in enumerate(spans):
            # Prior outputs are the tool-call turns that precede this span.
            prior = [o for o in outputs[:idx] if o]
            _rewrite_span(service, sp, prior)
            rewritten += 1

    path.write_bytes(request.SerializeToString())
    return len(llm_spans_by_trace), rewritten


def main() -> None:
    service = InternalTraceService(
        db_session=MagicMock(),
        task_id="demo",
        service_name="demo-fixture-regen",
    )
    for path in sorted(FIXTURES_DIR.glob("*.binpb")):
        traces, spans = regenerate_fixture(path, service)
        print(f"{path.name}: rewrote {spans} llm_call span(s) across {traces} trace(s)")


if __name__ == "__main__":
    main()
