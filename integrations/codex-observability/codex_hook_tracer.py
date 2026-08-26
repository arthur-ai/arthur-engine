#!/usr/bin/env python3
"""Export Codex lifecycle-hook events as OpenInference traces to Arthur Engine."""

from __future__ import annotations

import contextlib
import fcntl
import hashlib
import json
import logging
import os
import secrets
import sys
import time
from pathlib import Path
from typing import Any, Callable, Iterator, Mapping, Optional

logging.basicConfig(
    level=logging.WARNING,
    format="[codex_hook_tracer] %(levelname)s: %(message)s",
    stream=sys.stderr,
)
log = logging.getLogger("codex_hook_tracer")

STATE_DIR = Path.home() / ".codex" / "tracer"
STATE_MAX_AGE_SECONDS = 48 * 60 * 60
TOKEN_FIELDS = (
    "input_tokens",
    "cached_input_tokens",
    "output_tokens",
    "reasoning_output_tokens",
    "total_tokens",
)

ExportFunction = Callable[[dict, str, list[dict]], None]


def _load_config_file(path: Path) -> dict:
    try:
        if path.is_file():
            value = json.loads(path.read_text())
            return value if isinstance(value, dict) else {}
    except (OSError, json.JSONDecodeError) as exc:
        log.debug("Could not read config %s: %s", path, exc)
    return {}


def discover_config(
    env: Optional[Mapping[str, str]] = None,
    cwd: Optional[Path] = None,
    home: Optional[Path] = None,
) -> Optional[dict]:
    """Resolve Engine configuration without ever logging credential values."""
    env = os.environ if env is None else env
    cwd = Path.cwd() if cwd is None else Path(cwd)
    home = Path.home() if home is None else Path(home)

    config = {
        "api_key": env.get("GENAI_ENGINE_API_KEY", ""),
        "task_id": env.get("GENAI_ENGINE_TASK_ID", ""),
        "endpoint": env.get("GENAI_ENGINE_TRACE_ENDPOINT", ""),
    }
    for candidate in (
        cwd / ".codex" / "arthur_config.json",
        home / ".codex" / "arthur_config.json",
    ):
        values = _load_config_file(candidate)
        for key in config:
            config[key] = config[key] or values.get(key, "")
        if all(config.values()):
            return config
    return config if all(config.values()) else None


def _state_key(session_id: str, turn_id: str) -> str:
    return hashlib.sha256(f"{session_id}\0{turn_id}".encode()).hexdigest()


def _state_path(session_id: str, turn_id: str) -> Path:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    return STATE_DIR / f"{_state_key(session_id, turn_id)}.json"


def _lock_path(session_id: str, turn_id: str) -> Path:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    return STATE_DIR / f"{_state_key(session_id, turn_id)}.lock"


@contextlib.contextmanager
def _turn_lock(session_id: str, turn_id: str) -> Iterator[None]:
    with _lock_path(session_id, turn_id).open("a+") as lock_file:
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)


def _load_state(session_id: str, turn_id: str) -> dict:
    path = _state_path(session_id, turn_id)
    try:
        return json.loads(path.read_text()) if path.is_file() else {}
    except (OSError, json.JSONDecodeError) as exc:
        log.warning("Could not read hook state for session %s: %s", session_id, exc)
        return {}


def _save_state(state: dict) -> None:
    path = _state_path(state["session_id"], state["turn_id"])
    path.write_text(json.dumps(state, sort_keys=True))
    path.chmod(0o600)


def _delete_state(session_id: str, turn_id: str) -> None:
    _state_path(session_id, turn_id).unlink(missing_ok=True)


def _cleanup_stale_state() -> None:
    try:
        cutoff = time.time() - STATE_MAX_AGE_SECONDS
        for path in STATE_DIR.glob("*.json"):
            if path.stat().st_mtime < cutoff:
                path.unlink(missing_ok=True)
    except OSError as exc:
        log.debug("Could not clean stale hook state: %s", exc)


def _new_trace_id() -> str:
    return secrets.token_hex(16)


def _new_span_id() -> str:
    return secrets.token_hex(8)


def _encoded_attribute(value: Any) -> str:
    if isinstance(value, str):
        return value
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)


def read_token_usage(transcript_path: Path, turn_id: str) -> dict[str, int]:
    """Sum each model call recorded between this turn's start and completion."""
    totals = {field: 0 for field in TOKEN_FIELDS}
    inside_turn = False
    try:
        lines = transcript_path.read_text().splitlines()
    except OSError:
        return totals

    for line in lines:
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue
        if record.get("type") != "event_msg":
            continue
        payload = record.get("payload") or {}
        event_type = payload.get("type")
        if event_type == "task_started":
            inside_turn = payload.get("turn_id") == turn_id
            continue
        if event_type == "task_complete":
            if payload.get("turn_id") == turn_id:
                break
            inside_turn = False
            continue
        if inside_turn and event_type == "token_count":
            usage = (payload.get("info") or {}).get("last_token_usage") or {}
            for field in TOKEN_FIELDS:
                totals[field] += int(usage.get(field) or 0)
    return totals


def _common_ids(data: dict) -> tuple[str, str]:
    return str(data.get("session_id") or ""), str(data.get("turn_id") or "")


def handle_user_prompt_submit(
    data: dict,
    config: dict,
    export: ExportFunction = None,
) -> None:
    del config, export
    session_id, turn_id = _common_ids(data)
    if not session_id or not turn_id:
        return
    now_ns = time.time_ns()
    with _turn_lock(session_id, turn_id):
        _save_state(
            {
                "session_id": session_id,
                "turn_id": turn_id,
                "model": data.get("model") or "unknown",
                "prompt": data.get("prompt") or "",
                "trace_id_hex": _new_trace_id(),
                "root_span_id_hex": _new_span_id(),
                "start_ns": now_ns,
                "pending_tools": {},
            }
        )


def handle_pre_tool(data: dict, config: dict) -> None:
    del config
    session_id, turn_id = _common_ids(data)
    tool_use_id = str(data.get("tool_use_id") or "")
    if not session_id or not turn_id or not tool_use_id:
        return
    with _turn_lock(session_id, turn_id):
        state = _load_state(session_id, turn_id)
        if not state:
            return
        state.setdefault("pending_tools", {})[tool_use_id] = {
            "start_ns": time.time_ns(),
            "tool_name": data.get("tool_name") or "unknown",
            "tool_input": data.get("tool_input"),
        }
        _save_state(state)


def _tool_span_record(state: dict, data: dict, start_ns: int, end_ns: int) -> dict:
    tool_name = data.get("tool_name") or "unknown"
    tool_use_id = str(data.get("tool_use_id") or "")
    return {
        "name": tool_name,
        "trace_id_hex": state["trace_id_hex"],
        "span_id_hex": _new_span_id(),
        "parent_span_id_hex": state["root_span_id_hex"],
        "kind": "CLIENT",
        "status_code": "OK",
        "start_ns": start_ns,
        "end_ns": end_ns,
        "attributes": {
            "openinference.span.kind": "TOOL",
            "tool.name": tool_name,
            "tool.call.id": tool_use_id,
            "input.value": _encoded_attribute(data.get("tool_input")),
            "input.mime_type": "application/json",
            "output.value": _encoded_attribute(data.get("tool_response")),
            "output.mime_type": "application/json",
            "session.id": state["session_id"],
            "codex.thread.id": state["session_id"],
            "codex.turn.id": state["turn_id"],
        },
    }


def handle_post_tool(
    data: dict,
    config: dict,
    export: Optional[ExportFunction] = None,
) -> None:
    export = _build_and_export_spans if export is None else export
    session_id, turn_id = _common_ids(data)
    tool_use_id = str(data.get("tool_use_id") or "")
    if not session_id or not turn_id:
        return
    end_ns = time.time_ns()
    with _turn_lock(session_id, turn_id):
        state = _load_state(session_id, turn_id)
        if not state:
            return
        pending = state.setdefault("pending_tools", {}).pop(tool_use_id, {})
        start_ns = int(pending.get("start_ns") or end_ns - 1_000_000)
        record = _tool_span_record(state, data, start_ns, end_ns)
        _save_state(state)
    export(config, session_id, [record])


def _root_span_record(state: dict, data: dict, end_ns: int) -> dict:
    attributes = {
        "openinference.span.kind": "LLM",
        "input.value": state.get("prompt") or "",
        "input.mime_type": "text/plain",
        "output.value": data.get("last_assistant_message") or "",
        "output.mime_type": "text/plain",
        "session.id": state["session_id"],
        "codex.thread.id": state["session_id"],
        "codex.turn.id": state["turn_id"],
        "codex.turn.status": "completed",
        "codex.emission.transport": "hooks",
        "codex.observer.name": "arthur-codex-hook-tracer",
        "graph.node.id": f"turn:{state['turn_id']}",
        "graph.node.name": "codex.turn",
        "llm.model_name": state.get("model") or "unknown",
    }
    transcript_path = data.get("transcript_path")
    if transcript_path:
        usage = read_token_usage(Path(str(transcript_path)), state["turn_id"])
        if any(usage.values()):
            attributes.update(
                {
                    "llm.token_count.prompt": usage["input_tokens"],
                    "llm.token_count.completion": usage["output_tokens"],
                    "llm.token_count.total": usage["total_tokens"],
                    "llm.token_count.prompt_details.cache_read": usage[
                        "cached_input_tokens"
                    ],
                    "llm.token_count.completion_details.reasoning": usage[
                        "reasoning_output_tokens"
                    ],
                }
            )
    return {
        "name": "codex.turn",
        "trace_id_hex": state["trace_id_hex"],
        "span_id_hex": state["root_span_id_hex"],
        "parent_span_id_hex": None,
        "kind": "INTERNAL",
        "status_code": "OK",
        "start_ns": state["start_ns"],
        "end_ns": end_ns,
        "attributes": attributes,
    }


def handle_stop(
    data: dict,
    config: dict,
    export: Optional[ExportFunction] = None,
) -> None:
    export = _build_and_export_spans if export is None else export
    session_id, turn_id = _common_ids(data)
    if not session_id or not turn_id:
        return
    end_ns = time.time_ns()
    with _turn_lock(session_id, turn_id):
        state = _load_state(session_id, turn_id)
        if not state:
            return
        record = _root_span_record(state, data, end_ns)
        _delete_state(session_id, turn_id)
    export(config, session_id, [record])
    _cleanup_stale_state()


def _otel_imports():
    from opentelemetry import trace
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import SpanContext, TracerProvider
    from opentelemetry.sdk.trace.export import SimpleSpanProcessor
    from opentelemetry.sdk.trace.id_generator import IdGenerator
    from opentelemetry.trace import (
        NonRecordingSpan,
        SpanKind,
        Status,
        StatusCode,
        TraceFlags,
    )

    return (
        trace,
        Resource,
        TracerProvider,
        SpanContext,
        SimpleSpanProcessor,
        OTLPSpanExporter,
        IdGenerator,
        NonRecordingSpan,
        SpanKind,
        Status,
        StatusCode,
        TraceFlags,
    )


def _build_and_export_spans(config: dict, session_id: str, records: list[dict]) -> None:
    (
        trace,
        Resource,
        TracerProvider,
        SpanContext,
        SimpleSpanProcessor,
        OTLPSpanExporter,
        IdGenerator,
        NonRecordingSpan,
        SpanKind,
        Status,
        StatusCode,
        TraceFlags,
    ) = _otel_imports()

    resource = Resource.create(
        {
            "service.name": "codex",
            "arthur.task": config["task_id"],
            "arthur.session": session_id,
            "arthur.user": os.environ.get(
                "USER", os.environ.get("USERNAME", "unknown")
            ),
        }
    )

    for record in records:
        trace_id = int(record["trace_id_hex"], 16)
        span_id = int(record["span_id_hex"], 16)

        class FixedIdGenerator(IdGenerator):
            def generate_trace_id(self) -> int:
                return trace_id

            def generate_span_id(self) -> int:
                return span_id

        exporter = OTLPSpanExporter(
            endpoint=config["endpoint"],
            headers={"Authorization": f"Bearer {config['api_key']}"},
            timeout=4,
        )
        provider = TracerProvider(resource=resource, id_generator=FixedIdGenerator())
        provider.add_span_processor(SimpleSpanProcessor(exporter))
        tracer = provider.get_tracer("arthur-codex-hook-tracer")

        context = None
        parent_span_id = record.get("parent_span_id_hex")
        if parent_span_id:
            parent_context = SpanContext(
                trace_id=trace_id,
                span_id=int(parent_span_id, 16),
                is_remote=True,
                trace_flags=TraceFlags(TraceFlags.SAMPLED),
            )
            context = trace.set_span_in_context(NonRecordingSpan(parent_context))

        kind = {
            "CLIENT": SpanKind.CLIENT,
            "INTERNAL": SpanKind.INTERNAL,
        }.get(record.get("kind"), SpanKind.INTERNAL)
        span = tracer.start_span(
            record["name"],
            context=context,
            kind=kind,
            start_time=record["start_ns"],
        )
        for key, value in record["attributes"].items():
            if value is not None:
                span.set_attribute(key, value)
        if record.get("status_code") == "OK":
            span.set_status(Status(StatusCode.OK))
        span.end(end_time=record["end_ns"])
        provider.shutdown()


HANDLERS = {
    "user_prompt_submit": handle_user_prompt_submit,
    "pre_tool": handle_pre_tool,
    "post_tool": handle_post_tool,
    "stop": handle_stop,
}


def main() -> int:
    if len(sys.argv) != 2 or sys.argv[1] not in HANDLERS:
        print(
            "Usage: codex_hook_tracer.py <user_prompt_submit|pre_tool|post_tool|stop>",
            file=sys.stderr,
        )
        return 0
    try:
        raw = sys.stdin.read()
        data = json.loads(raw) if raw.strip() else {}
    except json.JSONDecodeError as exc:
        log.warning("Could not parse Codex hook input: %s", exc)
        return 0

    config = discover_config(cwd=Path(str(data.get("cwd") or Path.cwd())))
    if config is None:
        return 0
    try:
        HANDLERS[sys.argv[1]](data, config)
    except Exception as exc:
        log.warning("Tracer error for %s: %s", sys.argv[1], exc, exc_info=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
