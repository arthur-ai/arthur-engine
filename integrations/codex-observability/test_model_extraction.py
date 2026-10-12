import importlib.util
import json
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "parity_tracer", Path(__file__).with_name("codex_hook_tracer.py")
)
t = importlib.util.module_from_spec(spec)
spec.loader.exec_module(t)


def test_stop_extracts_model_steps_and_falls_back_to_final_transcript(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(t, "STATE_DIR", tmp_path / "state")
    common = {"session_id": "session", "turn_id": "turn", "model": "example-model"}
    t.handle_user_prompt_submit({**common, "prompt": "Run the check"}, {})
    records = []

    def add(kind, payload, second):
        records.append(
            {
                "type": kind,
                "payload": payload,
                "timestamp": f"2026-09-21T15:00:{second:02d}Z",
            }
        )

    add("event_msg", {"type": "task_started", "turn_id": "other"}, 0)
    add(
        "response_item",
        {
            "type": "message",
            "role": "assistant",
            "content": [{"type": "output_text", "text": "Wrong turn"}],
        },
        1,
    )
    add("event_msg", {"type": "task_started", "turn_id": "turn"}, 2)
    add(
        "response_item",
        {
            "type": "message",
            "role": "assistant",
            "content": [{"type": "output_text", "text": "I will run the check"}],
        },
        3,
    )
    add(
        "response_item",
        {
            "type": "custom_tool_call",
            "call_id": "call1",
            "name": "exec_command",
            "input": '{"cmd":"printf OK"}',
        },
        4,
    )
    add(
        "response_item",
        {"type": "custom_tool_call_output", "call_id": "call1", "output": "OK"},
        5,
    )
    usage = {
        "type": "token_count",
        "info": {
            "last_token_usage": {
                "input_tokens": 10,
                "output_tokens": 2,
                "total_tokens": 12,
            },
            "total_token_usage": {"total_tokens": 12},
        },
    }
    add("event_msg", usage, 6)
    add("event_msg", usage, 7)
    add(
        "response_item",
        {
            "type": "message",
            "role": "assistant",
            "phase": "final_answer",
            "content": [{"type": "output_text", "text": "FINAL_FROM_TRANSCRIPT"}],
        },
        8,
    )
    add(
        "event_msg",
        {
            "type": "token_count",
            "info": {
                "last_token_usage": {
                    "input_tokens": 15,
                    "output_tokens": 3,
                    "total_tokens": 18,
                },
                "total_token_usage": {"total_tokens": 30},
            },
        },
        9,
    )
    add("event_msg", {"type": "task_complete", "turn_id": "turn"}, 10)
    add(
        "response_item",
        {
            "type": "message",
            "role": "assistant",
            "content": [{"type": "output_text", "text": "Future turn"}],
        },
        11,
    )
    path = tmp_path / "transcript.jsonl"
    path.write_text("\n".join(json.dumps(r) for r in records))
    exported = []
    t.handle_stop(
        {**common, "transcript_path": str(path)}, {}, lambda c, s, r: exported.extend(r)
    )
    roots = [
        r for r in exported if r["attributes"]["openinference.span.kind"] == "CHAIN"
    ]
    models = [
        r for r in exported if r["attributes"]["openinference.span.kind"] == "LLM"
    ]
    assert len(roots) == 1
    assert len(models) == 2
    assert roots[0]["attributes"]["output.value"] == "FINAL_FROM_TRANSCRIPT"
    assert models[0]["attributes"]["output.value"] == "I will run the check"
    assert (
        models[0]["attributes"][
            "llm.output_messages.0.message.tool_calls.0.tool_call.id"
        ]
        == "call1"
    )
    assert models[1]["attributes"]["llm.input_messages.0.message.role"] == "tool"
    assert "OK" in models[1]["attributes"]["input.value"]
    assert sum(r["attributes"]["llm.token_count.total"] for r in models) == 30
    assert "llm.token_count.total" not in roots[0]["attributes"]
    assert all(r["parent_span_id_hex"] == roots[0]["span_id_hex"] for r in models)
    assert not t._load_state("session", "turn")


def test_missing_transcript_keeps_hook_answer_without_inventing_model_spans(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(t, "STATE_DIR", tmp_path / "state")
    common = {"session_id": "session", "turn_id": "turn"}
    t.handle_user_prompt_submit({**common, "prompt": "hello"}, {})
    exported = []
    t.handle_stop(
        {
            **common,
            "transcript_path": str(tmp_path / "missing"),
            "last_assistant_message": "hook answer",
        },
        {},
        lambda c, s, r: exported.extend(r),
    )
    assert len(exported) == 1
    assert exported[0]["attributes"]["openinference.span.kind"] == "CHAIN"
    assert exported[0]["attributes"]["output.value"] == "hook answer"


def test_response_records_without_matching_turn_boundary_are_not_exported(tmp_path):
    path = tmp_path / "transcript.jsonl"
    path.write_text(
        json.dumps(
            {
                "type": "response_item",
                "payload": {
                    "type": "message",
                    "role": "assistant",
                    "content": [{"type": "output_text", "text": "unrelated"}],
                },
            }
        )
    )
    models, answer = t._model_records(
        {"session_id": "s", "turn_id": "t", "start_ns": 1},
        {"transcript_path": str(path)},
    )
    assert models == []
    assert answer == ""


def test_tool_call_output_only_contains_public_call_fields(tmp_path):
    path = tmp_path / "calls.jsonl"
    entries = [
        {"type": "event_msg", "payload": {"type": "task_started", "turn_id": "t"}},
        {
            "type": "response_item",
            "timestamp": "2026-09-21T15:00:00Z",
            "payload": {
                "type": "custom_tool_call",
                "call_id": "c",
                "name": "exec",
                "input": "printf OK",
                "internal_chat_message_metadata_passthrough": {
                    "private_field": "DO_NOT_EXPORT"
                },
            },
        },
    ]
    path.write_text("\n".join(json.dumps(e) for e in entries))
    models, _ = t._model_records(
        {
            "session_id": "s",
            "turn_id": "t",
            "start_ns": 1,
            "trace_id_hex": "1" * 32,
            "root_span_id_hex": "2" * 16,
        },
        {"transcript_path": str(path)},
    )
    assert "DO_NOT_EXPORT" not in json.dumps(models)
    assert json.loads(models[0]["attributes"]["output.value"]) == [
        {"call_id": "c", "name": "exec", "input": "printf OK"}
    ]
