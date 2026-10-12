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


def _agent_key(agent_id: str) -> str:
    return hashlib.sha256(agent_id.encode()).hexdigest()


def _state_path(session_id: str, turn_id: str) -> Path:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    return STATE_DIR / f"{_state_key(session_id, turn_id)}.json"


def _lock_path(session_id: str, turn_id: str) -> Path:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    return STATE_DIR / f"{_state_key(session_id, turn_id)}.lock"


def _agent_context_path(agent_id: str) -> Path:
    directory = STATE_DIR / "agents"
    directory.mkdir(parents=True, exist_ok=True)
    return directory / f"{_agent_key(agent_id)}.json"


def _activation_path(session_id: str) -> Path:
    directory = STATE_DIR / "activation"
    directory.mkdir(parents=True, exist_ok=True)
    return directory / f"{hashlib.sha256(session_id.encode()).hexdigest()}.json"


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


def _load_agent_context(agent_id: str) -> dict:
    path = _agent_context_path(agent_id)
    try:
        return json.loads(path.read_text()) if path.is_file() else {}
    except (OSError, json.JSONDecodeError) as exc:
        log.warning("Could not read hook state for agent %s: %s", agent_id, exc)
        return {}


def _save_agent_context(context: dict) -> None:
    path = _agent_context_path(context["agent_id"])
    path.write_text(json.dumps(context, sort_keys=True))
    path.chmod(0o600)


def _delete_agent_context(agent_id: str) -> None:
    _agent_context_path(agent_id).unlink(missing_ok=True)


def _cleanup_stale_state() -> None:
    try:
        cutoff = time.time() - STATE_MAX_AGE_SECONDS
        for path in STATE_DIR.rglob("*.json"):
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


TAIL_CHUNK_BYTES = 1 << 20
# Stop runs under the hook timeout.  A turn whose transcript portion is bigger
# than this (large tool outputs) is traced from the hook payload alone.
TURN_READ_LIMIT_BYTES = 32 << 20


_TURN_LINES_CACHE: dict[tuple, list[str]] = {}


def _turn_lines(transcript_path: Any, turn_id: str) -> list[str]:
    """Cached per hook process: Stop needs the turn for usage and model spans."""
    try:
        size = os.path.getsize(transcript_path)
    except OSError:
        return []
    key = (str(transcript_path), turn_id, size)
    if key not in _TURN_LINES_CACHE:
        _TURN_LINES_CACHE.clear()
        _TURN_LINES_CACHE[key] = _read_turn_lines(transcript_path, turn_id)
    return _TURN_LINES_CACHE[key]


def _read_turn_lines(transcript_path: Any, turn_id: str) -> list[str]:
    """Return the transcript lines from this turn's ``task_started`` to the end.

    Long sessions grow the transcript to hundreds of MB, and Stop runs inside a
    time-limited hook, so the turn's start is found by scanning backwards from
    the end of the file, one chunk at a time, instead of reading it whole.

    Returns nothing if the turn's start is further than ``TURN_READ_LIMIT_BYTES``
    from the end, so Stop's cost stays bounded.
    """
    needle = json.dumps(turn_id).encode()
    try:
        with open(transcript_path, "rb") as f:
            f.seek(0, os.SEEK_END)
            size = pos = f.tell()
            carry = b""  # partial first line of the chunk searched last
            while pos > 0 and size - pos < TURN_READ_LIMIT_BYTES:
                step = min(TAIL_CHUNK_BYTES, pos)
                pos -= step
                f.seek(pos)
                block = f.read(step) + carry
                # Unless at the start of the file, the first line is partial.
                first = 0 if pos == 0 else block.find(b"\n") + 1
                if pos > 0 and first == 0:
                    carry = block
                    continue
                i = block.find(needle, first)
                while i != -1:
                    start = block.rfind(b"\n", 0, i) + 1
                    end = block.find(b"\n", i)
                    line = block[start : end if end != -1 else None]
                    if b'"task_started"' in line and _starts_turn(line, turn_id):
                        f.seek(pos + start)
                        return f.read().decode("utf-8", "replace").splitlines()
                    i = block.find(needle, i + 1)
                carry = block[:first]
    except OSError:
        pass
    return []


def _starts_turn(line: bytes, turn_id: str) -> bool:
    try:
        record = json.loads(line)
    except ValueError:
        return False
    payload = record.get("payload") if isinstance(record, dict) else None
    return (
        isinstance(payload, dict)
        and payload.get("type") == "task_started"
        and payload.get("turn_id") == turn_id
    )


def read_token_usage(transcript_path: Path, turn_id: str) -> dict[str, int]:
    """Sum each model call recorded between this turn's start and completion."""
    totals = {field: 0 for field in TOKEN_FIELDS}
    inside_turn = False
    lines = _turn_lines(transcript_path, turn_id)

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


def _agent_fields(data: dict) -> tuple[str, str]:
    return str(data.get("agent_id") or ""), str(data.get("agent_type") or "")


def _find_agent_id(value: Any) -> str:
    if isinstance(value, str):
        try:
            return _find_agent_id(json.loads(value))
        except json.JSONDecodeError:
            return ""
    if isinstance(value, dict):
        agent_id = value.get("agent_id")
        if isinstance(agent_id, str) and agent_id:
            return agent_id
        for nested in value.values():
            found = _find_agent_id(nested)
            if found:
                return found
    if isinstance(value, list):
        for nested in value:
            found = _find_agent_id(nested)
            if found:
                return found
    return ""


def _agent_prompt(tool_input: Any) -> str:
    if not isinstance(tool_input, dict):
        return ""
    for key in ("message", "prompt", "description"):
        value = tool_input.get(key)
        if isinstance(value, str) and value:
            return value
    return ""


def handle_session_start(
    data: dict,
    config: dict,
    export: Optional[ExportFunction] = None,
) -> None:
    del config, export
    session_id = str(data.get("session_id") or "")
    if not session_id:
        return
    path = _activation_path(session_id)
    path.write_text(
        json.dumps(
            {
                "session_id": session_id,
                "source": data.get("source") or "unknown",
                "model": data.get("model") or "unknown",
                "observed_at_ns": time.time_ns(),
            },
            sort_keys=True,
        )
    )
    path.chmod(0o600)


def handle_user_prompt_submit(
    data: dict,
    config: dict,
    export: ExportFunction = None,
) -> None:
    del config, export
    session_id, turn_id = _common_ids(data)
    if not session_id or not turn_id:
        return
    agent_id, agent_type = _agent_fields(data)
    agent_context = _load_agent_context(agent_id) if agent_id else {}
    now_ns = time.time_ns()
    with _turn_lock(session_id, turn_id):
        _save_state(
            {
                "session_id": session_id,
                "turn_id": turn_id,
                "model": data.get("model") or "unknown",
                "prompt": data.get("prompt") or "",
                "trace_id_hex": agent_context.get("trace_id_hex") or _new_trace_id(),
                "root_span_id_hex": _new_span_id(),
                "parent_span_id_hex": agent_context.get("agent_span_id_hex"),
                "trace_session_id": agent_context.get("parent_session_id")
                or session_id,
                "agent_id": agent_id,
                "agent_type": agent_type or agent_context.get("agent_type") or "",
                "start_ns": now_ns,
                "pending_tools": {},
            }
        )
    if agent_context:
        agent_context["turn_id"] = turn_id
        _save_agent_context(agent_context)


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
    attributes = {
        "openinference.span.kind": "TOOL",
        "tool.name": tool_name,
        "tool.call.id": tool_use_id,
        "input.value": _encoded_attribute(data.get("tool_input")),
        "input.mime_type": "application/json",
        "output.value": _encoded_attribute(data.get("tool_response")),
        "output.mime_type": "application/json",
        "session.id": state.get("trace_session_id") or state["session_id"],
        "codex.thread.id": state.get("agent_id") or state["session_id"],
        "codex.turn.id": state["turn_id"],
    }
    if state.get("agent_id"):
        attributes.update(
            {
                "codex.parent.thread.id": state.get("trace_session_id")
                or state["session_id"],
                "codex.agent.id": state["agent_id"],
                "codex.agent.type": state.get("agent_type") or "unknown",
            }
        )
    return {
        "name": tool_name,
        "trace_id_hex": state["trace_id_hex"],
        "span_id_hex": _new_span_id(),
        "parent_span_id_hex": state["root_span_id_hex"],
        "kind": "CLIENT",
        # No status: Codex's tool_response is the model-facing output and
        # carries no exit code, so success can't be known here.
        "start_ns": start_ns,
        "end_ns": end_ns,
        "attributes": attributes,
    }


def _record_spawned_agent(state: dict, pending: dict, data: dict) -> None:
    tool_name = str(data.get("tool_name") or "").lower()
    if tool_name not in {"agent", "spawn_agent", "task"}:
        return
    agent_id = _find_agent_id(data.get("tool_response"))
    if not agent_id:
        return
    existing = _load_agent_context(agent_id)
    tool_input = pending.get("tool_input", data.get("tool_input"))
    _save_agent_context(
        {
            **existing,
            "parent_session_id": state.get("trace_session_id") or state["session_id"],
            "parent_turn_id": state["turn_id"],
            "agent_id": agent_id,
            "agent_type": existing.get("agent_type") or "unknown",
            "prompt": _agent_prompt(tool_input),
            "trace_id_hex": state["trace_id_hex"],
            "agent_span_id_hex": existing.get("agent_span_id_hex") or _new_span_id(),
            "parent_span_id_hex": state["root_span_id_hex"],
            "start_ns": int(pending.get("start_ns") or time.time_ns()),
        }
    )


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
        _record_spawned_agent(state, pending, data)
        _save_state(state)
    export(config, state.get("trace_session_id") or session_id, [record])


def _root_span_record(state: dict, data: dict, end_ns: int) -> dict:
    attributes = {
        "openinference.span.kind": "LLM",
        "input.value": state.get("prompt") or "",
        "input.mime_type": "text/plain",
        "output.value": data.get("last_assistant_message") or "",
        "output.mime_type": "text/plain",
        "session.id": state.get("trace_session_id") or state["session_id"],
        "codex.thread.id": state.get("agent_id") or state["session_id"],
        "codex.turn.id": state["turn_id"],
        "codex.turn.status": "completed",
        "codex.emission.transport": "hooks",
        "codex.observer.name": "arthur-codex-hook-tracer",
        "graph.node.id": f"turn:{state['turn_id']}",
        "graph.node.name": "codex.turn",
        "llm.model_name": state.get("model") or "unknown",
    }
    if state.get("agent_id"):
        attributes.update(
            {
                "codex.parent.thread.id": state.get("trace_session_id")
                or state["session_id"],
                "codex.agent.id": state["agent_id"],
                "codex.agent.type": state.get("agent_type") or "unknown",
            }
        )
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
        "parent_span_id_hex": state.get("parent_span_id_hex"),
        "kind": "INTERNAL",
        "status_code": "OK",
        "start_ns": state["start_ns"],
        "end_ns": end_ns,
        "attributes": attributes,
    }


def handle_subagent_start(
    data: dict,
    config: dict,
    export: Optional[ExportFunction] = None,
) -> None:
    del config, export
    session_id, turn_id = _common_ids(data)
    agent_id, agent_type = _agent_fields(data)
    if not session_id or not turn_id or not agent_id:
        return
    context = _load_agent_context(agent_id)
    context.update(
        {
            "parent_session_id": context.get("parent_session_id") or session_id,
            "turn_id": turn_id,
            "agent_id": agent_id,
            "agent_type": agent_type or context.get("agent_type") or "unknown",
            "prompt": context.get("prompt") or "",
            "trace_id_hex": context.get("trace_id_hex") or _new_trace_id(),
            "agent_span_id_hex": context.get("agent_span_id_hex") or _new_span_id(),
            "parent_span_id_hex": context.get("parent_span_id_hex"),
            "start_ns": int(context.get("start_ns") or time.time_ns()),
        }
    )
    _save_agent_context(context)


def _agent_span_record(context: dict, data: dict, end_ns: int) -> dict:
    agent_id = context["agent_id"]
    agent_type = context.get("agent_type") or "unknown"
    parent_session_id = context.get("parent_session_id") or data.get("session_id", "")
    return {
        "name": "codex.agent",
        "trace_id_hex": context["trace_id_hex"],
        "span_id_hex": context["agent_span_id_hex"],
        "parent_span_id_hex": context.get("parent_span_id_hex"),
        "kind": "INTERNAL",
        "status_code": "OK",
        "start_ns": context["start_ns"],
        "end_ns": end_ns,
        "attributes": {
            "openinference.span.kind": "AGENT",
            "input.value": context.get("prompt") or "",
            "input.mime_type": "text/plain",
            "output.value": data.get("last_assistant_message") or "",
            "output.mime_type": "text/plain",
            "session.id": parent_session_id,
            "codex.thread.id": agent_id,
            "codex.parent.thread.id": parent_session_id,
            "codex.turn.id": context.get("turn_id") or "",
            "codex.agent.id": agent_id,
            "codex.agent.type": agent_type,
            "graph.node.id": f"agent:{agent_id}",
            "graph.node.name": "codex.agent",
        },
    }


def handle_subagent_stop(
    data: dict,
    config: dict,
    export: Optional[ExportFunction] = None,
) -> None:
    export = _build_and_export_spans if export is None else export
    session_id, turn_id = _common_ids(data)
    agent_id, _ = _agent_fields(data)
    if not session_id or not turn_id or not agent_id:
        return
    end_ns = time.time_ns()
    records = []
    with _turn_lock(session_id, turn_id):
        state = _load_state(session_id, turn_id)
        if state:
            root_data = dict(data)
            if data.get("agent_transcript_path"):
                root_data["transcript_path"] = data["agent_transcript_path"]
            records.extend(_completed_records(state, root_data, end_ns))
            _delete_state(session_id, turn_id)
    context = _load_agent_context(agent_id)
    if context:
        records.append(_agent_span_record(context, data, end_ns))
        _delete_agent_context(agent_id)
    if records:
        export(config, context.get("parent_session_id") or session_id, records)
    _cleanup_stale_state()


def _model_records(state: dict, data: dict) -> tuple[list[dict], str]:
    """Reconstruct public model outputs, grouped by transcript usage checkpoints.

    Timestamps mark observations in the transcript, not measured request latency.
    Reasoning records and system/developer messages are deliberately not exported.
    """
    path = data.get("transcript_path")
    if not path:
        return [], ""
    lines = _turn_lines(path, state["turn_id"])
    records = []
    active = False
    texts, calls, next_inputs = [], [], []
    current_input = state.get("prompt") or ""
    input_role = "user"
    first_ns = last_ns = None
    final_text = ""
    seen_usage = set()

    def flush(usage=None):
        nonlocal texts, calls, next_inputs, current_input, input_role, first_ns, last_ns
        if texts or calls:
            index = len(records)
            output = "\n".join(texts)
            attrs = {
                "openinference.span.kind": "LLM",
                "llm.model_name": state.get("model") or "unknown",
                "session.id": state.get("trace_session_id") or state["session_id"],
                "codex.turn.id": state["turn_id"],
                "codex.emission.source": "transcript",
                "codex.timing.source": "transcript_observation",
                "input.value": current_input,
                "input.mime_type": (
                    "text/plain" if input_role == "user" else "application/json"
                ),
                "output.value": output or json.dumps(calls),
                "output.mime_type": "text/plain" if output else "application/json",
                "llm.input_messages.0.message.role": input_role,
                "llm.input_messages.0.message.content": current_input,
                "llm.output_messages.0.message.role": "assistant",
                "llm.output_messages.0.message.content": output,
            }
            for i, call in enumerate(calls):
                prefix = f"llm.output_messages.0.message.tool_calls.{i}.tool_call."
                attrs[prefix + "id"] = call.get("call_id", "")
                attrs[prefix + "function.name"] = call.get("name", "")
                attrs[prefix + "function.arguments"] = _encoded_attribute(
                    call.get("arguments", call.get("input", ""))
                )
            if usage:
                for source, dest in (
                    ("input_tokens", "prompt"),
                    ("output_tokens", "completion"),
                    ("total_tokens", "total"),
                    ("cached_input_tokens", "prompt_details.cache_read"),
                    ("reasoning_output_tokens", "completion_details.reasoning"),
                ):
                    if source in usage:
                        attrs["llm.token_count." + dest] = int(usage[source])
            records.append(
                {
                    "name": "codex/" + (state.get("model") or "unknown"),
                    "trace_id_hex": state["trace_id_hex"],
                    "span_id_hex": hashlib.sha256(
                        f'{state["root_span_id_hex"]}:model:{index}'.encode()
                    ).hexdigest()[:16],
                    "parent_span_id_hex": state["root_span_id_hex"],
                    "kind": "CLIENT",
                    "start_ns": first_ns or state["start_ns"],
                    "end_ns": max(
                        last_ns or state["start_ns"], first_ns or state["start_ns"]
                    ),
                    "attributes": attrs,
                }
            )
        if next_inputs:
            current_input = json.dumps(next_inputs)
            input_role = "tool"
        texts, calls, next_inputs = [], [], []
        first_ns = last_ns = None

    for line in lines:
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(entry, dict):
            continue
        payload = entry.get("payload") or {}
        if not isinstance(payload, dict):
            continue
        kind = payload.get("type")
        if entry.get("type") == "event_msg" and kind == "task_started":
            if active:
                break
            active = payload.get("turn_id") == state["turn_id"]
            continue
        if not active:
            continue
        if entry.get("type") == "event_msg":
            if kind == "task_complete":
                break
            if kind == "token_count":
                info = payload.get("info") or {}
                cumulative = info.get("total_token_usage")
                fingerprint = (
                    json.dumps(cumulative, sort_keys=True) if cumulative else None
                )
                if fingerprint is None or fingerprint not in seen_usage:
                    flush(info.get("last_token_usage"))
                    if fingerprint:
                        seen_usage.add(fingerprint)
            continue
        if entry.get("type") != "response_item":
            continue
        if kind in ("function_call_output", "custom_tool_call_output"):
            next_inputs.append(
                {
                    "tool_call_id": payload.get("call_id", ""),
                    "content": payload.get("output", ""),
                }
            )
            continue
        if kind == "message" and payload.get("role") == "assistant":
            parts = [
                c.get("text", "")
                for c in payload.get("content", [])
                if isinstance(c, dict) and c.get("type") in ("output_text", "text")
            ]
            text = "".join(parts)
            if not text:
                continue
            texts.append(text)
            final_text = text
        elif kind in ("function_call", "custom_tool_call"):
            calls.append(
                {
                    key: payload[key]
                    for key in ("call_id", "name", "input", "arguments")
                    if key in payload
                }
            )
        else:
            continue
        try:
            from datetime import datetime

            ns = int(
                datetime.fromisoformat(
                    entry["timestamp"].replace("Z", "+00:00")
                ).timestamp()
                * 1_000_000_000
            )
        except (KeyError, ValueError, TypeError):
            ns = state["start_ns"]
        first_ns = ns if first_ns is None else first_ns
        last_ns = ns
    flush()
    return records, final_text


def _completed_records(state: dict, data: dict, end_ns: int) -> list[dict]:
    models, final_text = _model_records(state, data)
    root_data = dict(data)
    root_data["last_assistant_message"] = (
        data.get("last_assistant_message") or final_text
    )
    root = _root_span_record(state, root_data, end_ns)
    root["attributes"]["openinference.span.kind"] = "CHAIN"
    if models:
        root["start_ns"] = min(root["start_ns"], *(r["start_ns"] for r in models))
        root["end_ns"] = max(root["end_ns"], *(r["end_ns"] for r in models))
        # Usage belongs on model spans, not both models and their parent.
        for key in list(root["attributes"]):
            if key.startswith("llm.token_count."):
                del root["attributes"][key]
    # Root first: if the hook is cut short, the turn still has its parent.
    return [root] + models


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
        records = _completed_records(state, data, end_ns)
        _delete_state(session_id, turn_id)
    export(config, session_id, records)
    _cleanup_stale_state()


def _otel_imports():
    from opentelemetry import trace
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import SpanContext, TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor
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
        BatchSpanProcessor,
        OTLPSpanExporter,
        IdGenerator,
        NonRecordingSpan,
        SpanKind,
        Status,
        StatusCode,
        TraceFlags,
    )


def _build_and_export_spans(config: dict, session_id: str, records: list[dict]) -> None:
    """Export ``records`` in one request, in list order."""
    if not records:
        return
    (
        trace,
        Resource,
        TracerProvider,
        SpanContext,
        BatchSpanProcessor,
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

    class RecordIdGenerator(IdGenerator):
        """Hands out the IDs of the record being started."""

        trace_id = 0
        span_id = 0

        def generate_trace_id(self) -> int:
            return self.trace_id

        def generate_span_id(self) -> int:
            return self.span_id

    ids = RecordIdGenerator()
    exporter = OTLPSpanExporter(
        endpoint=config["endpoint"],
        headers={"Authorization": f"Bearer {config['api_key']}"},
        timeout=4,
    )
    provider = TracerProvider(resource=resource, id_generator=ids)
    provider.add_span_processor(
        BatchSpanProcessor(exporter, max_export_batch_size=max(len(records), 1))
    )
    tracer = provider.get_tracer("arthur-codex-hook-tracer")

    for record in records:
        ids.trace_id = int(record["trace_id_hex"], 16)
        ids.span_id = int(record["span_id_hex"], 16)

        context = None
        parent_span_id = record.get("parent_span_id_hex")
        if parent_span_id:
            parent_context = SpanContext(
                trace_id=ids.trace_id,
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
    "session_start": handle_session_start,
    "user_prompt_submit": handle_user_prompt_submit,
    "pre_tool": handle_pre_tool,
    "post_tool": handle_post_tool,
    "subagent_start": handle_subagent_start,
    "subagent_stop": handle_subagent_stop,
    "stop": handle_stop,
}


def main() -> int:
    if len(sys.argv) != 2 or sys.argv[1] not in HANDLERS:
        print(
            "Usage: codex_hook_tracer.py "
            "<session_start|user_prompt_submit|pre_tool|post_tool|subagent_start|subagent_stop|stop>",
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
