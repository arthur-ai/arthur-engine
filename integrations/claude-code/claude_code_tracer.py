#!/usr/bin/env python3
"""
claude_code_tracer.py — OpenInference tracer for Claude Code hooks.

Ships Claude Code activities as OpenInference traces to Arthur Engine.

Trace model:
  - Each user prompt → one trace (CHAIN root + TOOL/RETRIEVER/AGENT children + LLM children)
  - Exiting the session completes the current in-progress trace
  - Traces are linked by arthur.session attribute

Hook events:
  user_prompt_submit — start a new trace; complete previous trace if in progress
  pre_tool           — record current tool start (fallback trace creation if UserPromptSubmit unavailable)
  post_tool          — send a TOOL/RETRIEVER/AGENT span for the completed tool call
  post_tool_failure  — send an error TOOL/RETRIEVER/AGENT span for a failed tool call
  stop               — complete the current trace and clean up session state

Config priority (highest first):
  1. Env vars: GENAI_ENGINE_API_KEY, GENAI_ENGINE_TASK_ID, GENAI_ENGINE_TRACE_ENDPOINT
  2. Project config: $CLAUDE_PROJECT_DIR/.claude/arthur_config.json
  3. Global config: ~/.claude/arthur_config.json
  4. Silent no-op if nothing configured
"""

import contextlib
import fcntl
import json
import logging
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

# ---------------------------------------------------------------------------
# Logging — stderr only so stdout stays clean for Claude hooks
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.WARNING,
    format="[claude_code_tracer] %(levelname)s: %(message)s",
    stream=sys.stderr,
)
log = logging.getLogger("claude_code_tracer")


# ---------------------------------------------------------------------------
# Config discovery
# ---------------------------------------------------------------------------


def _load_config_file(path: Path) -> dict:
    try:
        if path.exists():
            return json.loads(path.read_text())
    except Exception as e:
        log.debug("Failed to read config %s: %s", path, e)
    return {}


def discover_config() -> Optional[dict]:
    """Returns config dict with keys: api_key, task_id, endpoint.
    Returns None if not configured (silent no-op)."""
    api_key = os.environ.get("GENAI_ENGINE_API_KEY", "")
    task_id = os.environ.get("GENAI_ENGINE_TASK_ID", "")
    endpoint = os.environ.get("GENAI_ENGINE_TRACE_ENDPOINT", "")

    if not (api_key and task_id and endpoint):
        project_dir = os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd())
        project_cfg = _load_config_file(
            Path(project_dir) / ".claude" / "arthur_config.json",
        )
        api_key = api_key or project_cfg.get("api_key", "")
        task_id = task_id or project_cfg.get("task_id", "")
        endpoint = endpoint or project_cfg.get("endpoint", "")

    if not (api_key and task_id and endpoint):
        global_cfg = _load_config_file(Path.home() / ".claude" / "arthur_config.json")
        api_key = api_key or global_cfg.get("api_key", "")
        task_id = task_id or global_cfg.get("task_id", "")
        endpoint = endpoint or global_cfg.get("endpoint", "")

    if not (api_key and task_id and endpoint):
        return None

    return {"api_key": api_key, "task_id": task_id, "endpoint": endpoint}


# ---------------------------------------------------------------------------
# State file helpers
# ---------------------------------------------------------------------------

STATE_DIR = Path.home() / ".claude" / "tracer"
STATE_MAX_AGE_S = 48 * 3600


def _state_path(session_id: str) -> Path:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    path = (STATE_DIR / f"{session_id}.json").resolve()
    if not path.is_relative_to(STATE_DIR.resolve()):
        raise ValueError(f"Invalid session_id: {session_id!r}")
    return path


def _load_state(session_id: str) -> dict:
    path = _state_path(session_id)
    try:
        if path.exists():
            return json.loads(path.read_text())
    except Exception as e:
        log.debug("Failed to load state for %s: %s", session_id, e)
    return {}


def _save_state(session_id: str, state: dict) -> None:
    try:
        _state_path(session_id).write_text(json.dumps(state))
    except Exception as e:
        log.warning("Failed to save state for %s: %s", session_id, e)


def _delete_state(session_id: str) -> None:
    try:
        p = _state_path(session_id)
        if p.exists():
            p.unlink()
    except Exception as e:
        log.debug("Failed to delete state for %s: %s", session_id, e)


def _cleanup_stale_states() -> None:
    try:
        now = time.time()
        for p in STATE_DIR.glob("*.json"):
            if now - p.stat().st_mtime > STATE_MAX_AGE_S:
                p.unlink()
    except Exception as e:
        log.debug("Stale state cleanup failed: %s", e)


def _new_trace_id() -> str:
    import secrets

    return secrets.token_hex(16)


def _new_span_id() -> str:
    import secrets

    return secrets.token_hex(8)


@contextlib.contextmanager
def _session_lock(session_id: str):
    """Exclusive per-session file lock.

    Serialises concurrent handle_post_tool / handle_post_tool_failure
    processes so that _emit_pending_llm_spans reads a consistent
    emitted_llm_span_count and never emits the same LLM span twice.
    This is necessary because Claude Code can run multiple tools in parallel,
    which causes multiple PostToolUse hook processes to fire concurrently.
    """
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    lock_path = (STATE_DIR / f"{session_id}.lock").resolve()
    if not lock_path.is_relative_to(STATE_DIR.resolve()):
        raise ValueError(f"Invalid session_id: {session_id!r}")

    with open(lock_path, "w") as fh:
        fcntl.flock(fh, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(fh, fcntl.LOCK_UN)


# ---------------------------------------------------------------------------
# Transcript helpers
# ---------------------------------------------------------------------------


def _find_transcript_path(data: dict, session_id: str) -> Optional[str]:
    """Locate the session's transcript JSONL file."""
    # 1. Provided directly in hook data
    tp = data.get("transcript_path", "")
    if tp and Path(tp).exists():
        return tp

    # 2. Construct from CLAUDE_PROJECT_DIR (path with / → -)
    project_dir = os.environ.get("CLAUDE_PROJECT_DIR", "")
    if project_dir:
        sanitized = project_dir.replace("/", "-")
        path = Path.home() / ".claude" / "projects" / sanitized / f"{session_id}.jsonl"
        if path.exists():
            return str(path)

    # 3. Glob fallback across all project dirs
    projects_dir = Path.home() / ".claude" / "projects"
    if projects_dir.exists():
        matches = list(projects_dir.glob(f"*/{session_id}.jsonl"))
        if matches:
            return str(matches[0])

    return None


def _is_human_message(entry: dict) -> bool:
    """True for user-initiated messages (not tool results)."""
    if entry.get("type") != "user":
        return False
    content = entry.get("message", {}).get("content", "")
    # Tool result messages have content as a list; human messages have a string
    return isinstance(content, str)


def _count_human_messages(transcript_path: str) -> int:
    """Count human (non-tool-result) user messages to detect turn boundaries."""
    try:
        count = 0
        for line in Path(transcript_path).read_text().splitlines():
            if not line.strip():
                continue
            try:
                if _is_human_message(json.loads(line)):
                    count += 1
            except json.JSONDecodeError:
                pass
        return count
    except Exception:
        return 0


def _iso_to_ns(ts: str) -> int:
    """Convert ISO 8601 timestamp string to nanoseconds."""
    try:
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        return int(dt.timestamp() * 1_000_000_000)
    except Exception:
        return time.time_ns()


def _tool_result_text(content: list) -> str:
    """Extract readable text from a tool_result content list."""
    parts = []
    for item in content:
        if not isinstance(item, dict):
            continue
        if item.get("type") == "tool_result":
            inner = item.get("content", "")
            if isinstance(inner, str):
                parts.append(inner)
            elif isinstance(inner, list):
                for rc in inner:
                    if isinstance(rc, dict) and rc.get("type") == "text":
                        parts.append(rc.get("text", ""))
    return "\n".join(parts)


def _extract_llm_spans_for_turn(
    transcript_path: str,
    human_count_at_start: int,
    trace_id_hex: str,
    root_span_id_hex: str,
) -> list[dict]:
    """
    Extract LLM spans from transcript entries that belong to this turn.

    A turn starts after the `human_count_at_start`-th human message and continues
    until the end of the transcript (or until the trace is completed by _complete_turn).
    If additional human messages appear (e.g. context-compression continuations that
    don't fire UserPromptSubmit), scanning continues so no LLM spans are dropped.
    Uses actual timestamps from the transcript.

    For each LLM call we use the immediately-preceding message as the input:
      - First call in turn  → the human prompt (text/plain)
      - Subsequent calls    → the tool result(s) that preceded them (application/json)

    Output is the assistant's text response when present; otherwise the
    tool_use blocks serialised as JSON so the span always has an output value.
    """
    spans = []
    try:
        lines = Path(transcript_path).read_text().splitlines()
        human_count = 0
        in_turn = False

        # Tracks the input for the *next* LLM call we encounter
        last_input_value = ""
        last_input_mime = "text/plain"
        last_input_role = "user"
        last_input_content = ""

        for line in lines:
            if not line.strip():
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue

            entry_type = entry.get("type", "")

            # ── Human message: marks the start of this turn ──────────────────
            if _is_human_message(entry):
                human_count += 1
                if in_turn:
                    # A second human message within the same trace can happen when
                    # the Claude Code context is compressed and the session continues
                    # without firing a new UserPromptSubmit hook.  Keep scanning so
                    # the LLM spans from the continuation are also captured.
                    human_text = entry.get("message", {}).get("content", "")
                    last_input_value = json.dumps(
                        {"role": "user", "content": human_text[:500]},
                    )
                    last_input_mime = "application/json"
                    last_input_role = "user"
                    last_input_content = _truncate(human_text)
                    continue
                if human_count > human_count_at_start:
                    in_turn = True
                    human_text = entry.get("message", {}).get("content", "")
                    last_input_value = json.dumps(
                        {"role": "user", "content": human_text[:500]},
                    )
                    last_input_mime = "application/json"
                    last_input_role = "user"
                    last_input_content = _truncate(human_text)
                continue

            if not in_turn:
                continue

            # ── Tool result (user message with list content) ──────────────────
            if entry_type == "user":
                content = entry.get("message", {}).get("content", "")
                if isinstance(content, list):
                    text = _tool_result_text(content)
                    payload = text if text else json.dumps(content)
                    last_input_value = json.dumps(
                        {"role": "user", "content": payload[:500]},
                    )
                    last_input_mime = "application/json"
                    last_input_role = "user"
                    last_input_content = _truncate(payload)
                continue

            # ── Assistant LLM response ────────────────────────────────────────
            if entry_type != "assistant":
                continue

            msg = entry.get("message", {})
            usage = msg.get("usage", {})
            if not usage:
                continue

            model = msg.get("model", "claude")
            content_blocks = msg.get("content", [])
            ts = entry.get("timestamp", "")

            # Output: prefer text; fall back to serialised tool_use blocks
            text_parts = []
            tool_use_parts = []
            for block in content_blocks:
                if not isinstance(block, dict):
                    continue
                if block.get("type") == "text":
                    text_parts.append(block.get("text", ""))
                elif block.get("type") == "tool_use":
                    tool_use_parts.append(
                        {
                            "name": block.get("name", ""),
                            "input": block.get("input", {}),
                        },
                    )

            if text_parts:
                output_value = _truncate("".join(text_parts))
                output_mime = "text/plain"
            elif tool_use_parts:
                output_value = _truncate(json.dumps(tool_use_parts))
                output_mime = "application/json"
            else:
                output_value = ""
                output_mime = "text/plain"

            input_tokens = usage.get("input_tokens", 0)
            cache_read = usage.get("cache_read_input_tokens", 0)
            cache_create = usage.get("cache_creation_input_tokens", 0)
            output_tokens = usage.get("output_tokens", 0)

            start_ns = _iso_to_ns(ts)
            end_ns = start_ns + max(output_tokens * 10_000_000, 1_000_000)

            attrs: dict[str, Any] = {
                "openinference.span.kind": "LLM",
                "llm.system": "anthropic",
                "llm.model_name": model,
                "llm.token_count.prompt": input_tokens,
                "llm.token_count.completion": output_tokens,
                "llm.token_count.total": input_tokens
                + cache_read
                + cache_create
                + output_tokens,
                "llm.token_count.prompt_details.cache_read": cache_read,
                "llm.token_count.prompt_details.cache_write": cache_create,
                # Input: the message that immediately preceded this LLM call
                "llm.input_messages.0.message.role": last_input_role,
                "llm.input_messages.0.message.content": last_input_content,
                "input.value": last_input_value,
                "input.mime_type": last_input_mime,
                # Output: text response or serialised tool_use blocks
                "llm.output_messages.0.message.role": "assistant",
                "llm.output_messages.0.message.content": output_value,
                "output.value": output_value,
                "output.mime_type": output_mime,
            }

            spans.append(
                {
                    "trace_id_hex": trace_id_hex,
                    "span_id_hex": _new_span_id(),
                    "parent_span_id_hex": root_span_id_hex,
                    "name": f"claude/{model}",
                    "kind": None,  # Caller sets SpanKind
                    "start_ns": start_ns,
                    "end_ns": end_ns,
                    "attributes": attrs,
                    "force_span_id": False,
                },
            )

            # Update last_input for the next LLM call: the assistant's output
            # becomes part of what the model was shown next (via tool results).
            # We leave last_input* unchanged here — the tool result user message
            # that follows will overwrite it when we see that entry.

    except Exception as e:
        log.warning("Failed to extract LLM spans: %s", e)

    return spans


# ---------------------------------------------------------------------------
# OpenTelemetry imports (lazy)
# ---------------------------------------------------------------------------


def _otel_imports():
    from opentelemetry import trace
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import SpanContext, TracerProvider
    from opentelemetry.sdk.trace.export import SimpleSpanProcessor
    from opentelemetry.trace import NonRecordingSpan, SpanKind, StatusCode, TraceFlags

    return (
        trace,
        Resource,
        TracerProvider,
        SpanContext,
        SimpleSpanProcessor,
        OTLPSpanExporter,
        SpanKind,
        TraceFlags,
        NonRecordingSpan,
        StatusCode,
    )


# ---------------------------------------------------------------------------
# Tool schemas
# ---------------------------------------------------------------------------

TOOL_SCHEMAS: dict[str, dict] = {
    "Bash": {
        "type": "object",
        "properties": {
            "command": {"type": "string"},
            "description": {"type": "string"},
            "timeout": {"type": "number"},
            "run_in_background": {"type": "boolean"},
        },
        "required": ["command"],
    },
    "Read": {
        "type": "object",
        "properties": {
            "file_path": {"type": "string"},
            "offset": {"type": "number"},
            "limit": {"type": "number"},
        },
        "required": ["file_path"],
    },
    "Edit": {
        "type": "object",
        "properties": {
            "file_path": {"type": "string"},
            "old_string": {"type": "string"},
            "new_string": {"type": "string"},
            "replace_all": {"type": "boolean"},
        },
        "required": ["file_path", "old_string", "new_string"],
    },
    "Write": {
        "type": "object",
        "properties": {
            "file_path": {"type": "string"},
            "content": {"type": "string"},
        },
        "required": ["file_path", "content"],
    },
    "Glob": {
        "type": "object",
        "properties": {
            "pattern": {"type": "string"},
            "path": {"type": "string"},
        },
        "required": ["pattern"],
    },
    "Grep": {
        "type": "object",
        "properties": {
            "pattern": {"type": "string"},
            "path": {"type": "string"},
            "glob": {"type": "string"},
            "type": {"type": "string"},
            "output_mode": {
                "type": "string",
                "enum": ["content", "files_with_matches", "count"],
            },
            "context": {"type": "number"},
        },
        "required": ["pattern"],
    },
    "Task": {
        "type": "object",
        "properties": {
            "description": {"type": "string"},
            "prompt": {"type": "string"},
            "subagent_type": {"type": "string"},
            "run_in_background": {"type": "boolean"},
        },
        "required": ["description", "prompt", "subagent_type"],
    },
    "WebFetch": {
        "type": "object",
        "properties": {"url": {"type": "string"}, "prompt": {"type": "string"}},
        "required": ["url", "prompt"],
    },
    "WebSearch": {
        "type": "object",
        "properties": {
            "query": {"type": "string"},
            "allowed_domains": {"type": "array", "items": {"type": "string"}},
            "blocked_domains": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["query"],
    },
    "NotebookEdit": {
        "type": "object",
        "properties": {
            "notebook_path": {"type": "string"},
            "new_source": {"type": "string"},
            "cell_id": {"type": "string"},
            "cell_type": {"type": "string"},
            "edit_mode": {"type": "string"},
        },
        "required": ["notebook_path", "new_source"],
    },
    "Skill": {
        "type": "object",
        "properties": {"skill": {"type": "string"}, "args": {"type": "string"}},
        "required": ["skill"],
    },
    "AskUserQuestion": {
        "type": "object",
        "properties": {"questions": {"type": "array"}},
        "required": ["questions"],
    },
    "EnterPlanMode": {"type": "object", "properties": {}, "required": []},
    "ExitPlanMode": {"type": "object", "properties": {}, "required": []},
    "TaskCreate": {
        "type": "object",
        "properties": {
            "subject": {"type": "string"},
            "description": {"type": "string"},
            "activeForm": {"type": "string"},
        },
        "required": ["subject", "description"],
    },
    "TaskUpdate": {
        "type": "object",
        "properties": {
            "taskId": {"type": "string"},
            "status": {"type": "string"},
            "subject": {"type": "string"},
            "description": {"type": "string"},
        },
        "required": ["taskId"],
    },
    "TaskGet": {
        "type": "object",
        "properties": {"taskId": {"type": "string"}},
        "required": ["taskId"],
    },
    "TaskList": {"type": "object", "properties": {}, "required": []},
    "TaskStop": {
        "type": "object",
        "properties": {"task_id": {"type": "string"}},
        "required": [],
    },
    "TaskOutput": {
        "type": "object",
        "properties": {
            "task_id": {"type": "string"},
            "block": {"type": "boolean"},
            "timeout": {"type": "number"},
        },
        "required": ["task_id"],
    },
}

# Tools that map to RETRIEVER span kind (web retrieval operations)
RETRIEVER_TOOLS = {"WebSearch", "WebFetch"}

_MAX_ATTR_BYTES = 8192


def _truncate(value: Any) -> str:
    s = json.dumps(value) if not isinstance(value, str) else value
    if len(s.encode()) > _MAX_ATTR_BYTES:
        s = s[: _MAX_ATTR_BYTES // 3] + "…[truncated]"
    return s


# ---------------------------------------------------------------------------
# FixedSpanIdGenerator — forces the pre-generated root span ID
# ---------------------------------------------------------------------------


def _make_fixed_id_generator(forced_span_id_hex: str):
    import secrets

    from opentelemetry.sdk.trace.id_generator import IdGenerator

    forced_int = int(forced_span_id_hex, 16)

    class FixedSpanIdGenerator(IdGenerator):
        def __init__(self):
            self._used = False

        def generate_span_id(self) -> int:
            if not self._used:
                self._used = True
                return forced_int
            return int(secrets.token_hex(8), 16)

        def generate_trace_id(self) -> int:
            return int(secrets.token_hex(16), 16)

    return FixedSpanIdGenerator()


# ---------------------------------------------------------------------------
# OTLP export helper
# ---------------------------------------------------------------------------


def _build_and_export_spans(
    config: dict,
    session_id: str,
    username: str,
    span_records: list[dict],
) -> None:
    """Create spans from records and export via OTLP HTTP."""
    (
        trace,
        Resource,
        TracerProvider,
        SpanContext,
        SimpleSpanProcessor,
        OTLPSpanExporter,
        SpanKind,
        TraceFlags,
        NonRecordingSpan,
        StatusCode,
    ) = _otel_imports()

    resource = Resource.create(
        {
            "service.name": "claude-code",
            "arthur.task": config["task_id"],
            "arthur.session": session_id,
            "arthur.user": username,
        },
    )

    for rec in span_records:
        # Each span gets its own exporter so that provider.shutdown() on span N
        # doesn't mark the shared exporter as closed before span N+1 is sent.
        exporter = OTLPSpanExporter(
            endpoint=config["endpoint"],
            headers={"Authorization": f"Bearer {config['api_key']}"},
        )
        # Resolve None kind (used for LLM spans set by caller)
        kind = rec.get("kind") or SpanKind.CLIENT

        id_generator = None
        if rec.get("force_span_id"):
            id_generator = _make_fixed_id_generator(rec["span_id_hex"])

        kwargs = {"resource": resource}
        if id_generator:
            kwargs["id_generator"] = id_generator

        provider = TracerProvider(**kwargs)
        provider.add_span_processor(SimpleSpanProcessor(exporter))
        tracer = provider.get_tracer("claude-code-tracer")

        ctx = None
        if rec.get("parent_span_id_hex"):
            parent_sc = SpanContext(
                trace_id=int(rec["trace_id_hex"], 16),
                span_id=int(rec["parent_span_id_hex"], 16),
                is_remote=True,
                trace_flags=TraceFlags(TraceFlags.SAMPLED),
            )
            ctx = trace.set_span_in_context(NonRecordingSpan(parent_sc))

        span = tracer.start_span(
            name=rec["name"],
            context=ctx,
            kind=kind,
            start_time=rec["start_ns"],
        )

        # Patch trace_id if provider generated a different one
        try:
            sc = span.get_span_context()
            desired = int(rec["trace_id_hex"], 16)
            if sc.trace_id != desired:
                span._context = SpanContext(
                    trace_id=desired,
                    span_id=sc.span_id,
                    is_remote=sc.is_remote,
                    trace_flags=sc.trace_flags,
                )
        except Exception:
            pass

        span.set_attribute("arthur_span_version", "arthur_span_v1")
        for k, v in rec.get("attributes", {}).items():
            span.set_attribute(k, v)

        if rec.get("error"):
            span.set_status(StatusCode.ERROR, description=rec.get("error_msg", ""))

        span.end(end_time=rec["end_ns"])
        provider.shutdown()


# ---------------------------------------------------------------------------
# Turn completion
# ---------------------------------------------------------------------------


def _emit_pending_llm_spans(
    state: dict,
    transcript_path: Optional[str],
    config: dict,
) -> None:
    """Emit any new LLM spans from the transcript that haven't been sent yet.

    Called from handle_post_tool (real-time, after each tool response) and
    handle_stop (catches the final LLM response after the last tool call).
    Updates state.current_trace in-place so the caller must save state afterwards.
    """
    current_trace = state.get("current_trace")
    if not current_trace or not transcript_path:
        return

    (_, _, _, _, _, _, SpanKind, _, _, _) = _otel_imports()

    all_llm_spans = _extract_llm_spans_for_turn(
        transcript_path,
        current_trace.get("human_count_at_start", 0),
        current_trace["trace_id"],
        current_trace["root_span_id"],
    )

    emitted = current_trace.get("emitted_llm_span_count", 0)
    new_spans = all_llm_spans[emitted:]
    if not new_spans:
        return

    for sp in new_spans:
        sp["kind"] = SpanKind.CLIENT

    _build_and_export_spans(
        config=config,
        session_id=state["session_id"],
        username=state.get("username", "unknown"),
        span_records=new_spans,
    )

    current_trace["emitted_llm_span_count"] = emitted + len(new_spans)
    current_trace["last_llm_output"] = new_spans[-1]["attributes"].get(
        "output.value",
        "",
    )


def _complete_turn(
    state: dict,
    config: dict,
    transcript_path: Optional[str],
    end_ns: int,
) -> None:
    """Send the CHAIN root span for the current turn's trace.

    LLM spans are emitted in real-time from _emit_pending_llm_spans (called
    from handle_post_tool and handle_stop), so they do not need to be re-sent
    here.  The root span's output.value is taken from the last LLM output
    already tracked in state.
    """
    current_trace = state.get("current_trace")
    if not current_trace:
        return

    (_, _, _, _, _, _, SpanKind, _, _, _) = _otel_imports()

    trace_id = current_trace["trace_id"]
    root_span_id = current_trace["root_span_id"]
    turn_start_ns = current_trace["turn_start_ns"]
    turn_number = current_trace.get("turn_number", 1)
    prompt_preview = current_trace.get("prompt_preview", "")
    final_output = current_trace.get("last_llm_output", "")

    # Root CHAIN span
    username = state.get("username", "unknown")
    root_attrs: dict[str, Any] = {
        "openinference.span.kind": "CHAIN",
        "session.id": state["session_id"],
        "user.id": username,
        "arthur.turn_number": turn_number,
    }
    if prompt_preview:
        root_attrs["input.value"] = prompt_preview
        root_attrs["input.mime_type"] = "text/plain"
    if final_output:
        root_attrs["output.value"] = final_output
        root_attrs["output.mime_type"] = "text/plain"

    _build_and_export_spans(
        config=config,
        session_id=state["session_id"],
        username=username,
        span_records=[
            {
                "trace_id_hex": trace_id,
                "span_id_hex": root_span_id,
                "parent_span_id_hex": None,
                "name": "claude-code-turn",
                "kind": SpanKind.INTERNAL,
                "start_ns": turn_start_ns,
                "end_ns": end_ns,
                "attributes": root_attrs,
                "force_span_id": True,
            },
        ],
    )


# ---------------------------------------------------------------------------
# Tool span record builder (shared by post_tool and post_tool_failure)
# ---------------------------------------------------------------------------


def _build_tool_span_record(
    tool_name: str,
    tool_input: Any,
    tool_response: Any,
    start_ns: int,
    end_ns: int,
    trace_id: str,
    root_span_id: str,
    is_failure: bool = False,
    error_msg: str = "",
) -> dict:
    """Build a span record dict for a tool call (success or failure).

    Returns a record suitable for passing to _build_and_export_spans.
    The kind field is left as None so _build_and_export_spans defaults to
    SpanKind.CLIENT.
    """
    if tool_name in RETRIEVER_TOOLS:
        span_kind_str = "RETRIEVER"
    elif tool_name == "Task":
        span_kind_str = "AGENT"
    else:
        span_kind_str = "TOOL"

    input_value = (
        json.dumps(tool_input) if not isinstance(tool_input, str) else tool_input
    )
    output_str = (
        json.dumps(tool_response)
        if not isinstance(tool_response, str)
        else tool_response
    )

    if is_failure and error_msg:
        output_value = f"ERROR: {error_msg}\n{output_str}"
    else:
        output_value = output_str

    attrs: dict[str, Any] = {
        "openinference.span.kind": span_kind_str,
        "tool.name": tool_name,
        "input.value": input_value,
        "input.mime_type": "application/json",
        "output.value": output_value,
        "output.mime_type": "application/json",
    }

    schema = TOOL_SCHEMAS.get(tool_name)
    if schema:
        attrs["tool.json_schema"] = json.dumps(schema)

    # RETRIEVER-specific attributes per OpenInference spec
    if span_kind_str == "RETRIEVER":
        if tool_name == "WebSearch":
            query = tool_input.get("query", "") if isinstance(tool_input, dict) else ""
            attrs["input.value"] = query
            attrs["input.mime_type"] = "text/plain"
        elif tool_name == "WebFetch":
            url = tool_input.get("url", "") if isinstance(tool_input, dict) else ""
            attrs["input.value"] = url
            attrs["input.mime_type"] = "text/plain"

        # First retrieval document content
        if isinstance(tool_response, str):
            doc_content = _truncate(tool_response)
        else:
            doc_content = _truncate(json.dumps(tool_response))
        attrs["retrieval.documents.0.document.content"] = doc_content

    rec: dict[str, Any] = {
        "trace_id_hex": trace_id,
        "span_id_hex": _new_span_id(),
        "parent_span_id_hex": root_span_id,
        "name": tool_name,
        "kind": None,  # defaults to SpanKind.CLIENT in _build_and_export_spans
        "start_ns": start_ns,
        "end_ns": end_ns,
        "attributes": attrs,
        "force_span_id": False,
    }

    if is_failure:
        rec["error"] = True
        rec["error_msg"] = error_msg

    return rec


# ---------------------------------------------------------------------------
# Handlers
# ---------------------------------------------------------------------------


def handle_user_prompt_submit(data: dict, config: dict) -> None:
    """Handle UserPromptSubmit hook: complete previous trace and start a new one.

    Fires before Claude processes the prompt, giving an accurate turn_start_ns
    and the exact prompt text without transcript parsing.
    """
    session_id = data.get("session_id", "unknown")
    prompt = data.get("prompt", "")
    now_ns = time.time_ns()

    state = _load_state(session_id)

    # Initialize session on first event
    if not state.get("session_id"):
        state["session_id"] = session_id
        state["session_start_ns"] = now_ns
        state["username"] = os.environ.get(
            "USER",
            os.environ.get("USERNAME", "unknown"),
        )
        state["human_msg_count"] = 0
        state["turn_number"] = 0

    # Complete the previous turn's trace if one is in progress
    if state.get("current_trace"):
        transcript_path = _find_transcript_path(data, session_id)
        _emit_pending_llm_spans(state, transcript_path, config)
        _complete_turn(state, config, transcript_path, now_ns)

    # Count human messages for LLM span extraction.
    # UserPromptSubmit fires before Claude processes the prompt, so the new
    # message is not yet in the transcript — human_count_at_start equals the
    # current count (the new prompt will become count+1 in the transcript).
    transcript_path = _find_transcript_path(data, session_id)
    current_human_count = (
        _count_human_messages(transcript_path) if transcript_path else 0
    )

    turn_number = state.get("turn_number", 0) + 1
    state["turn_number"] = turn_number
    state["human_msg_count"] = current_human_count
    state["current_trace"] = {
        "trace_id": _new_trace_id(),
        "root_span_id": _new_span_id(),
        "turn_start_ns": now_ns,
        "turn_number": turn_number,
        "human_count_at_start": current_human_count,
        "prompt_preview": _truncate(prompt) if prompt else "",
    }

    _save_state(session_id, state)


def handle_pre_tool(data: dict, config: dict) -> None:
    session_id = data.get("session_id", "unknown")
    tool_name = data.get("tool_name", "")
    tool_input = data.get("tool_input", {})
    now_ns = time.time_ns()

    state = _load_state(session_id)

    # Initialize session on first call
    if not state.get("session_id"):
        state["session_id"] = session_id
        state["session_start_ns"] = now_ns
        state["username"] = os.environ.get(
            "USER",
            os.environ.get("USERNAME", "unknown"),
        )
        state["human_msg_count"] = 0
        state["turn_number"] = 0

    # Fallback: create a trace if UserPromptSubmit has not set one yet.
    # This handles cases where the hook isn't registered or fires before the
    # UserPromptSubmit event is available.
    if not state.get("current_trace"):
        transcript_path = _find_transcript_path(data, session_id)
        current_human_count = (
            _count_human_messages(transcript_path) if transcript_path else 0
        )
        prompt_preview = (
            _get_latest_human_message(transcript_path) if transcript_path else ""
        )

        turn_number = state.get("turn_number", 0) + 1
        state["turn_number"] = turn_number
        state["human_msg_count"] = current_human_count
        state["current_trace"] = {
            "trace_id": _new_trace_id(),
            "root_span_id": _new_span_id(),
            "turn_start_ns": now_ns,
            "turn_number": turn_number,
            # human_count_at_start is one less than the current count so that
            # _extract_llm_spans_for_turn finds entries where count > this value,
            # i.e. entries belonging to the NEW turn whose prompt is the
            # current_human_count-th human message.
            "human_count_at_start": max(0, current_human_count - 1),
            "prompt_preview": _truncate(prompt_preview) if prompt_preview else "",
        }

    state["current_tool"] = {
        "tool_name": tool_name,
        "tool_input": tool_input,
        "start_ns": now_ns,
    }
    _save_state(session_id, state)


def _get_latest_human_message(transcript_path: str) -> str:
    """Return the text of the most recent human message in the transcript."""
    try:
        last = ""
        for line in Path(transcript_path).read_text().splitlines():
            if not line.strip():
                continue
            try:
                entry = json.loads(line)
                if _is_human_message(entry):
                    content = entry.get("message", {}).get("content", "")
                    if isinstance(content, str):
                        last = content
            except json.JSONDecodeError:
                pass
        return last
    except Exception:
        return ""


def handle_post_tool(data: dict, config: dict) -> None:
    session_id = data.get("session_id", "unknown")
    end_ns = time.time_ns()

    # Read state once to build the tool span (no mutation needed).
    state = _load_state(session_id)
    if not state:
        log.warning("No state found for session %s in post_tool", session_id)
        return

    current_trace = state.get("current_trace")
    if not current_trace:
        log.debug("No current trace for session %s in post_tool", session_id)
        return

    current_tool = state.get("current_tool", {})
    tool_name = data.get("tool_name") or current_tool.get("tool_name", "unknown")
    tool_input = data.get("tool_input") or current_tool.get("tool_input", {})
    tool_response = data.get("tool_response", {})
    start_ns = current_tool.get("start_ns", end_ns - 1_000_000)

    span_record = _build_tool_span_record(
        tool_name=tool_name,
        tool_input=tool_input,
        tool_response=tool_response,
        start_ns=start_ns,
        end_ns=end_ns,
        trace_id=current_trace["trace_id"],
        root_span_id=current_trace["root_span_id"],
    )

    # Export the tool span before acquiring the lock — this is the slow network
    # I/O and does not mutate state, so it is safe to run outside the lock.
    _build_and_export_spans(
        config=config,
        session_id=session_id,
        username=state.get("username", "unknown"),
        span_records=[span_record],
    )

    # Acquire an exclusive per-session lock before emitting LLM spans.
    # Parallel PostToolUse processes race on emitted_llm_span_count; the lock
    # ensures each process re-reads the latest count and never double-emits.
    transcript_path = _find_transcript_path(data, session_id)
    with _session_lock(session_id):
        state = _load_state(session_id)
        state.pop("current_tool", None)
        _emit_pending_llm_spans(state, transcript_path, config)
        _save_state(session_id, state)


def handle_post_tool_failure(data: dict, config: dict) -> None:
    """Handle PostToolUseFailure: emit an error TOOL/RETRIEVER/AGENT span."""
    session_id = data.get("session_id", "unknown")
    end_ns = time.time_ns()

    state = _load_state(session_id)
    if not state:
        log.warning("No state found for session %s in post_tool_failure", session_id)
        return

    current_trace = state.get("current_trace")
    if not current_trace:
        log.debug("No current trace for session %s in post_tool_failure", session_id)
        return

    current_tool = state.get("current_tool", {})
    tool_name = data.get("tool_name") or current_tool.get("tool_name", "unknown")
    tool_input = data.get("tool_input") or current_tool.get("tool_input", {})
    tool_response = data.get("tool_response", {})
    start_ns = current_tool.get("start_ns", end_ns - 1_000_000)

    # Extract error message from various possible fields
    error_msg = ""
    if isinstance(tool_response, dict):
        error_msg = tool_response.get("error", tool_response.get("message", ""))
    elif isinstance(tool_response, str):
        error_msg = tool_response
    if not error_msg:
        error_msg = data.get("error", data.get("error_message", "Tool call failed"))

    span_record = _build_tool_span_record(
        tool_name=tool_name,
        tool_input=tool_input,
        tool_response=tool_response,
        start_ns=start_ns,
        end_ns=end_ns,
        trace_id=current_trace["trace_id"],
        root_span_id=current_trace["root_span_id"],
        is_failure=True,
        error_msg=error_msg,
    )

    _build_and_export_spans(
        config=config,
        session_id=session_id,
        username=state.get("username", "unknown"),
        span_records=[span_record],
    )

    transcript_path = _find_transcript_path(data, session_id)
    with _session_lock(session_id):
        state = _load_state(session_id)
        state.pop("current_tool", None)
        _emit_pending_llm_spans(state, transcript_path, config)
        _save_state(session_id, state)


def handle_stop(data: dict, config: dict) -> None:
    session_id = data.get("session_id", "unknown")
    end_ns = time.time_ns()
    transcript_path = _find_transcript_path(data, session_id)

    with _session_lock(session_id):
        state = _load_state(session_id)
        if not state.get("current_trace"):
            log.debug("No active trace for session %s at stop", session_id)
            return

        # Emit the final LLM span(s) — the last response has no tool call after it,
        # so handle_post_tool never got the chance to emit it.
        _emit_pending_llm_spans(state, transcript_path, config)

        _complete_turn(state, config, transcript_path, end_ns)

        _delete_state(session_id)

    _cleanup_stale_states()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    if len(sys.argv) < 2:
        print(
            "Usage: claude_code_tracer.py <pre_tool|post_tool|post_tool_failure|user_prompt_submit|stop>",
            file=sys.stderr,
        )
        sys.exit(0)

    event = sys.argv[1]

    try:
        raw = sys.stdin.read()
        data = json.loads(raw) if raw.strip() else {}
    except json.JSONDecodeError as e:
        log.warning("Failed to parse stdin JSON: %s", e)
        data = {}

    config = discover_config()
    if config is None:
        log.debug("Arthur Engine not configured, skipping tracing.")
        sys.exit(0)

    try:
        if event == "pre_tool":
            handle_pre_tool(data, config)
        elif event == "post_tool":
            handle_post_tool(data, config)
        elif event == "post_tool_failure":
            handle_post_tool_failure(data, config)
        elif event == "user_prompt_submit":
            handle_user_prompt_submit(data, config)
        elif event == "stop":
            handle_stop(data, config)
        else:
            log.warning("Unknown event: %s", event)
    except Exception as e:
        log.warning("Tracer error (%s): %s", event, e, exc_info=True)

    sys.exit(0)


if __name__ == "__main__":
    main()
