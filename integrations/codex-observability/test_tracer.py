"""Contract tests for the Codex lifecycle-hook Arthur tracer."""

import importlib.util
import json
import os
import threading
from pathlib import Path

import pytest

MODULE_PATH = Path(__file__).with_name("codex_hook_tracer.py")
SPEC = importlib.util.spec_from_file_location("codex_hook_tracer", MODULE_PATH)
tracer = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(tracer)


@pytest.fixture
def isolated_state(tmp_path, monkeypatch):
    state_dir = tmp_path / "state"
    monkeypatch.setattr(tracer, "STATE_DIR", state_dir)
    return state_dir


def config():
    return {
        "api_key": "example-test-key",
        "task_id": "00000000-0000-0000-0000-000000000123",
        "endpoint": "https://engine.example.com/api/v1/traces",
    }


def common():
    return {
        "session_id": "session-123",
        "turn_id": "turn-456",
        "model": "gpt-5.6-sol",
    }


def test_config_prefers_environment_then_project_then_global(tmp_path):
    """Break caught: global credentials unexpectedly override a narrower source."""
    project = tmp_path / "project"
    home = tmp_path / "home"
    (project / ".codex").mkdir(parents=True)
    (home / ".codex").mkdir(parents=True)
    (project / ".codex" / "arthur_config.json").write_text(
        json.dumps(
            {
                "api_key": "project-key",
                "task_id": "project-task",
                "endpoint": "http://project/api/v1/traces",
            }
        )
    )
    (home / ".codex" / "arthur_config.json").write_text(
        json.dumps(
            {
                "api_key": "global-key",
                "task_id": "global-task",
                "endpoint": "http://global/api/v1/traces",
            }
        )
    )

    assert tracer.discover_config(env={}, cwd=project, home=home) == {
        "api_key": "project-key",
        "task_id": "project-task",
        "endpoint": "http://project/api/v1/traces",
    }
    assert tracer.discover_config(
        env={
            "GENAI_ENGINE_API_KEY": "env-key",
            "GENAI_ENGINE_TASK_ID": "env-task",
            "GENAI_ENGINE_TRACE_ENDPOINT": "http://env/api/v1/traces",
        },
        cwd=project,
        home=home,
    ) == {
        "api_key": "env-key",
        "task_id": "env-task",
        "endpoint": "http://env/api/v1/traces",
    }


def test_incomplete_config_is_a_silent_noop(tmp_path):
    """Break caught: a partial installation crashes every Codex turn."""
    assert tracer.discover_config(env={}, cwd=tmp_path, home=tmp_path) is None


def test_hook_lifecycle_exports_tool_then_complete_turn(isolated_state):
    """Break caught: prompt, tool, or final response is lost between hook processes."""
    exported = []
    export = lambda cfg, session_id, records: exported.append(
        (cfg, session_id, records)
    )

    tracer.handle_user_prompt_submit(
        {**common(), "hook_event_name": "UserPromptSubmit", "prompt": "PROMPT_MARKER"},
        config(),
        export,
    )
    tracer.handle_pre_tool(
        {
            **common(),
            "hook_event_name": "PreToolUse",
            "tool_name": "Bash",
            "tool_use_id": "tool-789",
            "tool_input": {"command": "printf TOOL_MARKER"},
        },
        config(),
    )
    tracer.handle_post_tool(
        {
            **common(),
            "hook_event_name": "PostToolUse",
            "tool_name": "Bash",
            "tool_use_id": "tool-789",
            "tool_input": {"command": "printf TOOL_MARKER"},
            "tool_response": "TOOL_MARKER",
        },
        config(),
        export,
    )

    assert len(exported) == 1
    tool = exported[0][2][0]
    assert tool["name"] == "Bash"
    assert tool["attributes"]["openinference.span.kind"] == "TOOL"
    assert tool["attributes"]["tool.call.id"] == "tool-789"
    assert json.loads(tool["attributes"]["input.value"]) == {
        "command": "printf TOOL_MARKER"
    }
    assert tool["attributes"]["output.value"] == "TOOL_MARKER"
    assert tool["status_code"] == "OK"

    tracer.handle_stop(
        {
            **common(),
            "hook_event_name": "Stop",
            "last_assistant_message": "RESPONSE_MARKER",
        },
        config(),
        export,
    )

    assert len(exported) == 2
    root = exported[1][2][0]
    assert root["name"] == "codex.turn"
    assert root["trace_id_hex"] == tool["trace_id_hex"]
    assert tool["parent_span_id_hex"] == root["span_id_hex"]
    assert root["attributes"] == {
        "openinference.span.kind": "LLM",
        "input.value": "PROMPT_MARKER",
        "input.mime_type": "text/plain",
        "output.value": "RESPONSE_MARKER",
        "output.mime_type": "text/plain",
        "session.id": "session-123",
        "codex.thread.id": "session-123",
        "codex.turn.id": "turn-456",
        "codex.turn.status": "completed",
        "codex.emission.transport": "hooks",
        "codex.observer.name": "arthur-codex-hook-tracer",
        "graph.node.id": "turn:turn-456",
        "graph.node.name": "codex.turn",
        "llm.model_name": "gpt-5.6-sol",
    }
    assert root["end_ns"] > root["start_ns"]
    assert root["status_code"] == "OK"
    assert not list(isolated_state.glob("*.json"))


def test_session_start_records_hook_activation_without_exporting_content(
    isolated_state,
):
    """Break caught: a live task silently uses no Arthur hook runtime."""
    exported = []

    tracer.handle_session_start(
        {
            "session_id": "session-123",
            "hook_event_name": "SessionStart",
            "source": "resume",
            "model": "gpt-5.6-sol",
        },
        config(),
        lambda *args: exported.append(args),
    )

    activation_files = list((isolated_state / "activation").glob("*.json"))
    assert len(activation_files) == 1
    activation = json.loads(activation_files[0].read_text())
    assert activation["session_id"] == "session-123"
    assert activation["source"] == "resume"
    assert activation["model"] == "gpt-5.6-sol"
    assert isinstance(activation["observed_at_ns"], int)
    assert activation_files[0].stat().st_mode & 0o777 == 0o600
    assert exported == []


def test_subagent_lifecycle_exports_agent_turn_and_nested_tools(isolated_state):
    """Break caught: Codex subagent work is flattened or never completed."""
    exported = []
    exported_session_ids = []

    def export(cfg, session_id, records):
        exported_session_ids.append(session_id)
        exported.extend(records)

    tracer.handle_user_prompt_submit(
        {**common(), "prompt": "PARENT_PROMPT"}, config(), export
    )
    tracer.handle_pre_tool(
        {
            **common(),
            "tool_name": "spawn_agent",
            "tool_use_id": "spawn-1",
            "tool_input": {
                "task_name": "researcher",
                "message": "SUBAGENT_PROMPT",
            },
        },
        config(),
    )
    tracer.handle_post_tool(
        {
            **common(),
            "tool_name": "spawn_agent",
            "tool_use_id": "spawn-1",
            "tool_input": {
                "task_name": "researcher",
                "message": "SUBAGENT_PROMPT",
            },
            "tool_response": {
                "agent_id": "agent-789",
                "status": "running",
            },
        },
        config(),
        export,
    )
    tracer.handle_subagent_start(
        {
            "session_id": "session-123",
            "turn_id": "subagent-turn-1",
            "agent_id": "agent-789",
            "agent_type": "researcher",
            "model": "gpt-5.6-sol",
            "hook_event_name": "SubagentStart",
        },
        config(),
        export,
    )
    tracer.handle_user_prompt_submit(
        {
            "session_id": "session-123",
            "turn_id": "subagent-turn-1",
            "agent_id": "agent-789",
            "agent_type": "researcher",
            "model": "gpt-5.6-sol",
            "prompt": "SUBAGENT_PROMPT",
            "hook_event_name": "UserPromptSubmit",
        },
        config(),
        export,
    )
    tracer.handle_pre_tool(
        {
            "session_id": "session-123",
            "turn_id": "subagent-turn-1",
            "agent_id": "agent-789",
            "agent_type": "researcher",
            "tool_name": "Bash",
            "tool_use_id": "child-tool-1",
            "tool_input": {"command": "printf CHILD_TOOL"},
        },
        config(),
    )
    tracer.handle_post_tool(
        {
            "session_id": "session-123",
            "turn_id": "subagent-turn-1",
            "agent_id": "agent-789",
            "agent_type": "researcher",
            "tool_name": "Bash",
            "tool_use_id": "child-tool-1",
            "tool_input": {"command": "printf CHILD_TOOL"},
            "tool_response": "CHILD_TOOL",
        },
        config(),
        export,
    )
    tracer.handle_subagent_stop(
        {
            "session_id": "session-123",
            "turn_id": "subagent-turn-1",
            "agent_id": "agent-789",
            "agent_type": "researcher",
            "agent_transcript_path": None,
            "last_assistant_message": "SUBAGENT_RESPONSE",
            "hook_event_name": "SubagentStop",
        },
        config(),
        export,
    )
    tracer.handle_stop(
        {**common(), "last_assistant_message": "PARENT_RESPONSE"},
        config(),
        export,
    )

    records_by_name = {}
    for record in exported:
        records_by_name.setdefault(record["name"], []).append(record)

    parent_turn = next(
        record
        for record in records_by_name["codex.turn"]
        if record["attributes"]["codex.turn.id"] == "turn-456"
    )
    child_turn = next(
        record
        for record in records_by_name["codex.turn"]
        if record["attributes"]["codex.turn.id"] == "subagent-turn-1"
    )
    agent = records_by_name["codex.agent"][0]
    child_tool = next(
        record
        for record in records_by_name["Bash"]
        if record["attributes"]["tool.call.id"] == "child-tool-1"
    )

    assert agent["trace_id_hex"] == parent_turn["trace_id_hex"]
    assert child_turn["trace_id_hex"] == parent_turn["trace_id_hex"]
    assert child_tool["trace_id_hex"] == parent_turn["trace_id_hex"]
    assert agent["parent_span_id_hex"] == parent_turn["span_id_hex"]
    assert child_turn["parent_span_id_hex"] == agent["span_id_hex"]
    assert child_tool["parent_span_id_hex"] == child_turn["span_id_hex"]
    assert agent["attributes"]["openinference.span.kind"] == "AGENT"
    assert agent["attributes"]["input.value"] == "SUBAGENT_PROMPT"
    assert agent["attributes"]["output.value"] == "SUBAGENT_RESPONSE"
    assert agent["attributes"]["codex.agent.id"] == "agent-789"
    assert agent["attributes"]["codex.agent.type"] == "researcher"
    assert agent["attributes"]["session.id"] == "session-123"
    assert child_turn["attributes"]["codex.agent.id"] == "agent-789"
    assert child_turn["attributes"]["session.id"] == "session-123"
    assert child_turn["attributes"]["codex.parent.thread.id"] == "session-123"
    assert child_tool["attributes"]["codex.agent.id"] == "agent-789"
    assert set(exported_session_ids) == {"session-123"}
    assert not list(isolated_state.glob("*.json"))
    assert not list((isolated_state / "agents").glob("*.json"))


def test_stale_cleanup_removes_abandoned_agent_and_activation_state(
    isolated_state, monkeypatch
):
    """Break caught: missing Stop events retain agent/session identifiers forever."""
    tracer._save_agent_context(
        {
            "parent_session_id": "session-123",
            "agent_id": "agent-789",
            "trace_id_hex": "1" * 32,
            "agent_span_id_hex": "2" * 16,
            "start_ns": 1,
        }
    )
    tracer.handle_session_start(
        {"session_id": "session-123", "source": "startup"}, config()
    )
    paths = [
        *list((isolated_state / "agents").glob("*.json")),
        *list((isolated_state / "activation").glob("*.json")),
    ]
    old_time = 1_000
    for path in paths:
        os.utime(path, (old_time, old_time))
    monkeypatch.setattr(tracer.time, "time", lambda: old_time + 49 * 60 * 60)

    tracer._cleanup_stale_state()

    assert not list((isolated_state / "agents").glob("*.json"))
    assert not list((isolated_state / "activation").glob("*.json"))


def test_token_usage_sums_all_model_calls_in_only_the_matching_turn(tmp_path):
    """Break caught: reporting session totals or only the final model call."""
    transcript = tmp_path / "rollout.jsonl"
    records = [
        {"type": "event_msg", "payload": {"type": "task_started", "turn_id": "older"}},
        {
            "type": "event_msg",
            "payload": {
                "type": "token_count",
                "info": {
                    "last_token_usage": {
                        "input_tokens": 90,
                        "output_tokens": 9,
                        "total_tokens": 99,
                    }
                },
            },
        },
        {"type": "event_msg", "payload": {"type": "task_complete", "turn_id": "older"}},
        {
            "type": "event_msg",
            "payload": {"type": "task_started", "turn_id": "turn-456"},
        },
        {
            "type": "event_msg",
            "payload": {
                "type": "token_count",
                "info": {
                    "last_token_usage": {
                        "input_tokens": 10,
                        "cached_input_tokens": 4,
                        "output_tokens": 2,
                        "reasoning_output_tokens": 1,
                        "total_tokens": 12,
                    }
                },
            },
        },
        {
            "type": "event_msg",
            "payload": {
                "type": "token_count",
                "info": {
                    "last_token_usage": {
                        "input_tokens": 20,
                        "cached_input_tokens": 5,
                        "output_tokens": 3,
                        "reasoning_output_tokens": 0,
                        "total_tokens": 23,
                    }
                },
            },
        },
        {
            "type": "event_msg",
            "payload": {"type": "task_complete", "turn_id": "turn-456"},
        },
    ]
    transcript.write_text("\n".join(json.dumps(record) for record in records))

    assert tracer.read_token_usage(transcript, "turn-456") == {
        "input_tokens": 30,
        "cached_input_tokens": 9,
        "output_tokens": 5,
        "reasoning_output_tokens": 1,
        "total_tokens": 35,
    }


def test_stop_adds_token_attributes_from_the_codex_transcript(tmp_path, isolated_state):
    """Break caught: hook traces reach Arthur without model-usage metadata."""
    transcript = tmp_path / "rollout.jsonl"
    transcript.write_text(
        "\n".join(
            json.dumps(record)
            for record in [
                {
                    "type": "event_msg",
                    "payload": {"type": "task_started", "turn_id": "turn-456"},
                },
                {
                    "type": "event_msg",
                    "payload": {
                        "type": "token_count",
                        "info": {
                            "last_token_usage": {
                                "input_tokens": 30,
                                "cached_input_tokens": 9,
                                "output_tokens": 5,
                                "reasoning_output_tokens": 1,
                                "total_tokens": 35,
                            }
                        },
                    },
                },
                {
                    "type": "event_msg",
                    "payload": {"type": "task_complete", "turn_id": "turn-456"},
                },
            ]
        )
    )
    exported = []
    tracer.handle_user_prompt_submit(
        {**common(), "prompt": "PROMPT_MARKER", "transcript_path": str(transcript)},
        config(),
        lambda *_: None,
    )
    tracer.handle_stop(
        {
            **common(),
            "last_assistant_message": "RESPONSE_MARKER",
            "transcript_path": str(transcript),
        },
        config(),
        lambda cfg, session_id, records: exported.extend(records),
    )

    attrs = exported[0]["attributes"]
    assert attrs["llm.token_count.prompt"] == 30
    assert attrs["llm.token_count.completion"] == 5
    assert attrs["llm.token_count.total"] == 35
    assert attrs["llm.token_count.prompt_details.cache_read"] == 9
    assert attrs["llm.token_count.completion_details.reasoning"] == 1


def test_parallel_post_tool_hooks_do_not_overwrite_state(isolated_state):
    """Break caught: concurrent tools overwrite one another's state updates."""
    tracer.handle_user_prompt_submit(
        {**common(), "prompt": "parallel"}, config(), lambda *_: None
    )
    barrier = threading.Barrier(20)
    exported = []
    export_lock = threading.Lock()

    def export(cfg, session_id, records):
        with export_lock:
            exported.extend(records)

    def post(index):
        barrier.wait()
        tracer.handle_post_tool(
            {
                **common(),
                "tool_name": "Bash",
                "tool_use_id": f"tool-{index}",
                "tool_input": {"command": f"printf {index}"},
                "tool_response": str(index),
            },
            config(),
            export,
        )

    threads = [threading.Thread(target=post, args=(index,)) for index in range(20)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert len(exported) == 20
    assert len({record["attributes"]["tool.call.id"] for record in exported}) == 20


def test_otlp_export_timeout_finishes_inside_hook_timeout(monkeypatch):
    """Break caught: a slow Engine request outlives Codex's five-second hook limit."""
    exporter_kwargs = []

    class FakeResource:
        @staticmethod
        def create(attributes):
            return attributes

    class FakeExporter:
        def __init__(self, **kwargs):
            exporter_kwargs.append(kwargs)

    class FakeProcessor:
        def __init__(self, exporter):
            self.exporter = exporter

    class FakeSpan:
        def set_attribute(self, key, value):
            pass

        def set_status(self, status):
            pass

        def end(self, end_time):
            pass

    class FakeTracer:
        def start_span(self, *args, **kwargs):
            return FakeSpan()

    class FakeProvider:
        def __init__(self, **kwargs):
            pass

        def add_span_processor(self, processor):
            pass

        def get_tracer(self, name):
            return FakeTracer()

        def shutdown(self):
            pass

    class FakeSpanKind:
        CLIENT = "client"
        INTERNAL = "internal"

    class FakeStatusCode:
        OK = "ok"

    class FakeStatus:
        def __init__(self, code):
            self.code = code

    monkeypatch.setattr(
        tracer,
        "_otel_imports",
        lambda: (
            object(),
            FakeResource,
            FakeProvider,
            object,
            FakeProcessor,
            FakeExporter,
            object,
            object,
            FakeSpanKind,
            FakeStatus,
            FakeStatusCode,
            object,
        ),
    )
    record = {
        "name": "codex.turn",
        "trace_id_hex": "1" * 32,
        "span_id_hex": "2" * 16,
        "parent_span_id_hex": None,
        "kind": "INTERNAL",
        "status_code": "OK",
        "start_ns": 1,
        "end_ns": 2,
        "attributes": {},
    }

    tracer._build_and_export_spans(config(), "session-123", [record])

    assert exporter_kwargs == [
        {
            "endpoint": "https://engine.example.com/api/v1/traces",
            "headers": {"Authorization": "Bearer example-test-key"},
            "timeout": 4,
        }
    ]


def test_main_reads_one_hook_payload_and_silently_skips_without_config(monkeypatch):
    """Break caught: the hook command writes invalid output or fails an unconfigured turn."""
    monkeypatch.setattr(tracer.sys, "argv", ["codex_hook_tracer.py", "stop"])
    monkeypatch.setattr(
        tracer.sys, "stdin", __import__("io").StringIO(json.dumps(common()))
    )
    monkeypatch.setattr(tracer, "discover_config", lambda **kwargs: None)
    assert tracer.main() == 0


def test_main_resolves_project_config_from_hook_payload_cwd(tmp_path, monkeypatch):
    """Break caught: project config is missed when the hook process starts elsewhere."""
    project = tmp_path / "project"
    launcher_cwd = tmp_path / "launcher"
    home = tmp_path / "home"
    (project / ".codex").mkdir(parents=True)
    launcher_cwd.mkdir()
    home.mkdir()
    expected = {
        "api_key": "project-key",
        "task_id": "project-task",
        "endpoint": "https://engine.example.com/api/v1/traces",
    }
    (project / ".codex" / "arthur_config.json").write_text(json.dumps(expected))
    for key in (
        "GENAI_ENGINE_API_KEY",
        "GENAI_ENGINE_TASK_ID",
        "GENAI_ENGINE_TRACE_ENDPOINT",
    ):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.chdir(launcher_cwd)
    monkeypatch.setattr(tracer.sys, "argv", ["codex_hook_tracer.py", "stop"])
    monkeypatch.setattr(
        tracer.sys,
        "stdin",
        __import__("io").StringIO(json.dumps({**common(), "cwd": str(project)})),
    )
    received = []
    monkeypatch.setitem(
        tracer.HANDLERS,
        "stop",
        lambda data, resolved_config: received.append(resolved_config),
    )

    assert tracer.main() == 0
    assert received == [expected]
