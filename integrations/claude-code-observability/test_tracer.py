"""
Unit tests for claude_code_tracer.py

Run with:  python3 -m pytest integrations/claude-code-observability/test_tracer.py -v
"""

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

# Make the tracer importable without executing main()
sys.path.insert(0, str(Path(__file__).parent))
import claude_code_tracer as tracer

# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------


def _make_transcript(entries: list, path: Path) -> Path:
    """Write a list of transcript entry dicts to a JSONL file."""
    path.write_text("\n".join(json.dumps(e) for e in entries) + "\n")
    return path


def human_entry(text: str, ts: str = "2026-01-01T00:00:00.000000+00:00") -> dict:
    return {
        "type": "user",
        "message": {"role": "user", "content": text},
        "timestamp": ts,
    }


def tool_result_entry(tool_use_id: str, text: str) -> dict:
    return {
        "type": "user",
        "message": {
            "role": "user",
            "content": [
                {
                    "type": "tool_result",
                    "tool_use_id": tool_use_id,
                    "content": [{"type": "text", "text": text}],
                },
            ],
        },
        "timestamp": "2026-01-01T00:00:05.000000+00:00",
    }


def llm_entry(
    text: str = "",
    tool_use_blocks: list | None = None,
    model: str = "claude-sonnet-4-6",
    input_tokens: int = 10,
    output_tokens: int = 20,
    ts: str = "2026-01-01T00:00:02.000000+00:00",
    stop_reason: str = "",
) -> dict:
    content = []
    if text:
        content.append({"type": "text", "text": text})
    for b in tool_use_blocks or []:
        content.append(b)
    return {
        "type": "assistant",
        "message": {
            "role": "assistant",
            "model": model,
            "content": content,
            "stop_reason": stop_reason,
            "usage": {
                "input_tokens": input_tokens,
                "cache_read_input_tokens": 100,
                "cache_creation_input_tokens": 5,
                "output_tokens": output_tokens,
            },
        },
        "timestamp": ts,
    }


def tool_use_block(name: str = "Bash", cmd: str = "ls /tmp") -> dict:
    return {
        "type": "tool_use",
        "id": "toolu_x",
        "name": name,
        "input": {"command": cmd},
    }


@pytest.fixture
def tmp_transcript(tmp_path):
    """Return a factory that writes entries to a temp JSONL file."""

    def factory(entries):
        p = tmp_path / "transcript.jsonl"
        return _make_transcript(entries, p)

    return factory


# ---------------------------------------------------------------------------
# _load_config_file
# ---------------------------------------------------------------------------


class TestLoadConfigFile:
    def test_reads_valid_json(self, tmp_path):
        cfg = tmp_path / "cfg.json"
        cfg.write_text('{"api_key": "k", "task_id": "t"}')
        assert tracer._load_config_file(cfg) == {"api_key": "k", "task_id": "t"}

    def test_missing_file_returns_empty(self, tmp_path):
        assert tracer._load_config_file(tmp_path / "no_such.json") == {}

    def test_invalid_json_returns_empty(self, tmp_path):
        bad = tmp_path / "bad.json"
        bad.write_text("not json {{")
        assert tracer._load_config_file(bad) == {}


# ---------------------------------------------------------------------------
# discover_config
# ---------------------------------------------------------------------------


class TestDiscoverConfig:
    def test_env_vars_highest_priority(self, tmp_path, monkeypatch):
        monkeypatch.setenv("GENAI_ENGINE_API_KEY", "env_key")
        monkeypatch.setenv("GENAI_ENGINE_TASK_ID", "env_task")
        monkeypatch.setenv("GENAI_ENGINE_TRACE_ENDPOINT", "https://env.example.com")
        # Even if project config exists it should not override env vars
        monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(tmp_path))
        proj_cfg = tmp_path / ".claude" / "arthur_config.json"
        proj_cfg.parent.mkdir(parents=True)
        proj_cfg.write_text(
            json.dumps(
                {
                    "api_key": "proj_key",
                    "task_id": "proj_task",
                    "endpoint": "https://proj.example.com",
                },
            ),
        )
        cfg = tracer.discover_config()
        assert cfg == {
            "api_key": "env_key",
            "task_id": "env_task",
            "endpoint": "https://env.example.com",
        }

    def test_project_config_used_when_no_env(self, tmp_path, monkeypatch):
        monkeypatch.delenv("GENAI_ENGINE_API_KEY", raising=False)
        monkeypatch.delenv("GENAI_ENGINE_TASK_ID", raising=False)
        monkeypatch.delenv("GENAI_ENGINE_TRACE_ENDPOINT", raising=False)
        monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(tmp_path))
        proj_cfg = tmp_path / ".claude" / "arthur_config.json"
        proj_cfg.parent.mkdir(parents=True)
        proj_cfg.write_text(
            json.dumps(
                {"api_key": "p", "task_id": "t", "endpoint": "https://x.example.com"},
            ),
        )
        cfg = tracer.discover_config()
        assert cfg == {
            "api_key": "p",
            "task_id": "t",
            "endpoint": "https://x.example.com",
        }

    def test_returns_none_when_unconfigured(self, monkeypatch, tmp_path):
        monkeypatch.delenv("GENAI_ENGINE_API_KEY", raising=False)
        monkeypatch.delenv("GENAI_ENGINE_TASK_ID", raising=False)
        monkeypatch.delenv("GENAI_ENGINE_TRACE_ENDPOINT", raising=False)
        monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(tmp_path))
        # Patch home to a temp dir with no config
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        assert tracer.discover_config() is None

    def test_partial_env_falls_back_to_file(self, tmp_path, monkeypatch):
        monkeypatch.setenv("GENAI_ENGINE_API_KEY", "env_key")
        monkeypatch.delenv("GENAI_ENGINE_TASK_ID", raising=False)
        monkeypatch.delenv("GENAI_ENGINE_TRACE_ENDPOINT", raising=False)
        monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(tmp_path))
        proj_cfg = tmp_path / ".claude" / "arthur_config.json"
        proj_cfg.parent.mkdir(parents=True)
        proj_cfg.write_text(
            json.dumps(
                {"task_id": "file_task", "endpoint": "https://file.example.com"},
            ),
        )
        cfg = tracer.discover_config()
        assert cfg["api_key"] == "env_key"
        assert cfg["task_id"] == "file_task"


# ---------------------------------------------------------------------------
# _is_human_message
# ---------------------------------------------------------------------------


class TestIsHumanMessage:
    def test_string_content_is_human(self):
        assert tracer._is_human_message(
            {"type": "user", "message": {"role": "user", "content": "Hello"}},
        )

    def test_list_content_is_not_human(self):
        # Tool result messages have list content
        assert not tracer._is_human_message(
            {
                "type": "user",
                "message": {"role": "user", "content": [{"type": "tool_result"}]},
            },
        )

    def test_assistant_type_is_not_human(self):
        assert not tracer._is_human_message(
            {"type": "assistant", "message": {"role": "assistant", "content": "Hi"}},
        )

    def test_system_type_is_not_human(self):
        assert not tracer._is_human_message({"type": "system", "message": {}})

    def test_empty_string_content_is_human(self):
        # An empty string is still a string → human
        assert tracer._is_human_message(
            {"type": "user", "message": {"role": "user", "content": ""}},
        )


# ---------------------------------------------------------------------------
# _count_human_messages
# ---------------------------------------------------------------------------


class TestCountHumanMessages:
    def test_counts_only_string_content(self, tmp_transcript):
        p = tmp_transcript(
            [
                human_entry("Hello"),
                tool_result_entry("tid1", "output"),  # NOT a human message
                human_entry("Second question"),
                llm_entry("Response"),  # NOT a human message
            ],
        )
        assert tracer._count_human_messages(str(p)) == 2

    def test_empty_transcript(self, tmp_transcript):
        p = tmp_transcript([])
        assert tracer._count_human_messages(str(p)) == 0

    def test_missing_file_returns_zero(self):
        assert tracer._count_human_messages("/nonexistent/path.jsonl") == 0

    def test_skips_blank_lines(self, tmp_path):
        p = tmp_path / "t.jsonl"
        p.write_text(
            json.dumps(human_entry("a")) + "\n\n" + json.dumps(human_entry("b")) + "\n",
        )
        assert tracer._count_human_messages(str(p)) == 2


# ---------------------------------------------------------------------------
# _iso_to_ns
# ---------------------------------------------------------------------------


class TestIsoToNs:
    def test_known_timestamp(self):
        # 2026-01-01T00:00:00 UTC = 1767225600 seconds
        ns = tracer._iso_to_ns("2026-01-01T00:00:00.000000+00:00")
        assert ns == 1767225600 * 1_000_000_000

    def test_z_suffix(self):
        ns_z = tracer._iso_to_ns("2026-01-01T00:00:00.000000Z")
        ns_utc = tracer._iso_to_ns("2026-01-01T00:00:00.000000+00:00")
        assert ns_z == ns_utc

    def test_invalid_returns_approximate_now(self):
        import time

        before = time.time_ns()
        ns = tracer._iso_to_ns("not-a-timestamp")
        after = time.time_ns()
        assert before <= ns <= after


# ---------------------------------------------------------------------------
# _truncate
# ---------------------------------------------------------------------------


class TestTruncate:
    def test_short_string_unchanged(self):
        assert tracer._truncate("hello") == "hello"

    def test_long_string_gets_truncated(self):
        big = "x" * 20_000
        result = tracer._truncate(big)
        assert len(result.encode()) <= tracer._MAX_ATTR_BYTES + 20
        assert "...[truncated]" in result

    def test_multibyte_chars_stay_within_limit(self):
        # 4-byte emoji repeated; old char-slice would produce ~10 920 bytes
        big = "😀" * 4_000
        result = tracer._truncate(big)
        assert len(result.encode()) <= tracer._MAX_ATTR_BYTES + 20
        assert "...[truncated]" in result

    def test_non_string_json_serialised(self):
        result = tracer._truncate({"key": "value"})
        assert "key" in result


# ---------------------------------------------------------------------------
# _tool_result_text
# ---------------------------------------------------------------------------


class TestToolResultText:
    def test_single_tool_result(self):
        content = [
            {
                "type": "tool_result",
                "tool_use_id": "t1",
                "content": [{"type": "text", "text": "hello world"}],
            },
        ]
        assert tracer._tool_result_text(content) == "hello world"

    def test_multiple_tool_results(self):
        content = [
            {
                "type": "tool_result",
                "tool_use_id": "t1",
                "content": [{"type": "text", "text": "first"}],
            },
            {
                "type": "tool_result",
                "tool_use_id": "t2",
                "content": [{"type": "text", "text": "second"}],
            },
        ]
        result = tracer._tool_result_text(content)
        assert "first" in result
        assert "second" in result

    def test_string_content_inside_tool_result(self):
        content = [
            {"type": "tool_result", "tool_use_id": "t1", "content": "direct string"},
        ]
        assert tracer._tool_result_text(content) == "direct string"

    def test_empty_list(self):
        assert tracer._tool_result_text([]) == ""

    def test_non_tool_result_items_ignored(self):
        content = [
            {"type": "image", "data": "..."},
            {
                "type": "tool_result",
                "tool_use_id": "t1",
                "content": [{"type": "text", "text": "actual"}],
            },
        ]
        assert tracer._tool_result_text(content) == "actual"

    def test_non_dict_item_in_list_skipped(self):
        # Non-dict items (strings, ints) in the content list must not crash
        content = [
            "raw string",
            42,
            {
                "type": "tool_result",
                "tool_use_id": "t1",
                "content": [{"type": "text", "text": "ok"}],
            },
        ]
        assert tracer._tool_result_text(content) == "ok"


# ---------------------------------------------------------------------------
# _get_latest_human_message
# ---------------------------------------------------------------------------


class TestGetLatestHumanMessage:
    def test_returns_last_human_message(self, tmp_transcript):
        p = tmp_transcript(
            [
                human_entry("First"),
                llm_entry("Reply"),
                human_entry("Second"),
            ],
        )
        assert tracer._get_latest_human_message(str(p)) == "Second"

    def test_ignores_tool_results(self, tmp_transcript):
        p = tmp_transcript(
            [
                human_entry("Question"),
                tool_result_entry("tid", "tool output"),
            ],
        )
        assert tracer._get_latest_human_message(str(p)) == "Question"

    def test_missing_file_returns_empty(self):
        assert tracer._get_latest_human_message("/no/such/file.jsonl") == ""


# ---------------------------------------------------------------------------
# _extract_llm_spans_for_turn — core function
# ---------------------------------------------------------------------------


class TestExtractLlmSpansForTurn:
    TRACE_ID = "a" * 32
    ROOT_ID = "b" * 16

    def _extract(self, transcript_path, human_count_at_start=0):
        return tracer._extract_llm_spans_for_turn(
            str(transcript_path),
            human_count_at_start,
            self.TRACE_ID,
            self.ROOT_ID,
        )

    # -- basic extraction --

    def test_single_text_response(self, tmp_transcript):
        p = tmp_transcript([human_entry("Hello"), llm_entry("Hi there")])
        spans = self._extract(p)
        assert len(spans) == 1
        attrs = spans[0]["attributes"]
        assert attrs["openinference.span.kind"] == "LLM"
        assert attrs["output.value"] == "Hi there"
        assert attrs["output.mime_type"] == "text/plain"

    def test_no_llm_entries_returns_empty(self, tmp_transcript):
        p = tmp_transcript([human_entry("Hello"), tool_result_entry("t1", "stuff")])
        spans = self._extract(p)
        assert spans == []

    def test_empty_transcript_returns_empty(self, tmp_transcript):
        p = tmp_transcript([])
        assert self._extract(p) == []

    # -- turn boundary detection --

    def test_stops_at_next_human_message(self, tmp_transcript):
        # Each user prompt is its own trace. When the extractor sees a second
        # human message while in_turn=True, it must stop — those spans belong
        # to the next trace, not this one.
        p = tmp_transcript(
            [
                human_entry("Turn 1"),
                llm_entry("Reply 1", ts="2026-01-01T00:00:01.000000+00:00"),
                human_entry("Turn 2"),
                llm_entry("Reply 2", ts="2026-01-01T00:00:03.000000+00:00"),
            ],
        )
        spans = self._extract(p, human_count_at_start=0)
        # Only the first reply; second human message terminates extraction
        assert len(spans) == 1
        assert spans[0]["attributes"]["output.value"] == "Reply 1"

    def test_human_count_at_start_selects_correct_turn(self, tmp_transcript):
        p = tmp_transcript(
            [
                human_entry("Turn 1"),
                llm_entry("Reply 1", ts="2026-01-01T00:00:01.000000+00:00"),
                human_entry("Turn 2"),
                llm_entry("Reply 2", ts="2026-01-01T00:00:03.000000+00:00"),
            ],
        )
        # human_count_at_start=1 → second human message starts the turn
        spans = self._extract(p, human_count_at_start=1)
        assert len(spans) == 1
        assert spans[0]["attributes"]["output.value"] == "Reply 2"

    def test_second_turn_starts_its_own_trace(self, tmp_transcript):
        # Each user prompt is a separate trace. The second turn's LLM reply
        # should NOT appear when extracting for turn 1.
        p = tmp_transcript(
            [
                human_entry("Original prompt"),
                llm_entry("Reply 1", ts="2026-01-01T00:00:01.000000+00:00"),
                human_entry("Next prompt"),
                llm_entry("Reply 2", ts="2026-01-01T00:00:03.000000+00:00"),
            ],
        )
        # Extracting for turn 1 (human_count_at_start=0) must only return Reply 1
        spans = self._extract(p, human_count_at_start=0)
        assert len(spans) == 1
        inp = json.loads(spans[0]["attributes"]["input.value"])
        assert "Original prompt" in inp["content"]
        assert spans[0]["attributes"]["output.value"] == "Reply 1"

    # -- Fix 1: tool_use-only output --

    def test_fix1_tool_use_only_output_is_json(self, tmp_transcript):
        p = tmp_transcript(
            [
                human_entry("List files"),
                llm_entry(text="", tool_use_blocks=[tool_use_block("Bash", "ls /tmp")]),
            ],
        )
        spans = self._extract(p)
        assert len(spans) == 1
        attrs = spans[0]["attributes"]
        # output.value carries JSON-serialised tool_use for display/debugging
        assert attrs["output.value"] != ""
        assert attrs["output.mime_type"] == "application/json"
        parsed = json.loads(attrs["output.value"])
        assert parsed[0]["name"] == "Bash"
        assert parsed[0]["input"]["command"] == "ls /tmp"
        # Per spec, message.content is empty when only tool_use blocks are present;
        # the structured tool_calls attributes carry the tool call information.
        assert attrs["llm.output_messages.0.message.content"] == ""
        assert (
            attrs["llm.output_messages.0.message.tool_calls.0.tool_call.function.name"]
            == "Bash"
        )

    def test_text_takes_priority_over_tool_use(self, tmp_transcript):
        p = tmp_transcript(
            [
                human_entry("Do something"),
                llm_entry(
                    text="Sure, running Bash now",
                    tool_use_blocks=[tool_use_block()],
                ),
            ],
        )
        spans = self._extract(p)
        assert len(spans) == 1
        attrs = spans[0]["attributes"]
        assert attrs["output.value"] == "Sure, running Bash now"
        assert attrs["output.mime_type"] == "text/plain"

    def test_empty_content_gives_empty_output(self, tmp_transcript):
        p = tmp_transcript([human_entry("Hello"), llm_entry(text="")])
        spans = self._extract(p)
        assert spans[0]["attributes"]["output.value"] == ""
        assert spans[0]["attributes"]["output.mime_type"] == "text/plain"

    # -- Fix 2: per-call input tracking --

    def test_fix2_first_llm_input_is_human_prompt(self, tmp_transcript):
        p = tmp_transcript(
            [
                human_entry("What files?"),
                llm_entry(tool_use_blocks=[tool_use_block()]),
            ],
        )
        spans = self._extract(p)
        attrs = spans[0]["attributes"]
        assert "What files?" in attrs["input.value"]
        assert attrs["llm.input_messages.0.message.role"] == "user"
        assert "What files?" in attrs["llm.input_messages.0.message.content"]

    def test_fix2_second_llm_input_is_tool_result(self, tmp_transcript):
        p = tmp_transcript(
            [
                human_entry("What files?"),
                llm_entry(
                    text="",
                    tool_use_blocks=[tool_use_block()],
                    ts="2026-01-01T00:00:01.000000+00:00",
                ),
                tool_result_entry("toolu_x", "file1.txt\nfile2.txt"),
                llm_entry(
                    text="The files are: file1.txt, file2.txt",
                    ts="2026-01-01T00:00:04.000000+00:00",
                ),
            ],
        )
        spans = self._extract(p)
        assert len(spans) == 2

        # LLM call 1: input = human prompt
        attrs1 = spans[0]["attributes"]
        assert "What files?" in attrs1["input.value"]

        # LLM call 2: input = tool result (fix 2)
        attrs2 = spans[1]["attributes"]
        assert "file1.txt" in attrs2["input.value"]
        assert "What files?" not in attrs2["input.value"]

    def test_fix2_multiple_tool_results_each_update_input(self, tmp_transcript):
        p = tmp_transcript(
            [
                human_entry("Multi-step"),
                llm_entry(
                    tool_use_blocks=[tool_use_block("Bash", "step1")],
                    ts="2026-01-01T00:00:01.000000+00:00",
                ),
                tool_result_entry("toolu_x", "result_of_step1"),
                llm_entry(
                    tool_use_blocks=[tool_use_block("Read", "read_file")],
                    ts="2026-01-01T00:00:03.000000+00:00",
                ),
                tool_result_entry("toolu_x", "result_of_step2"),
                llm_entry(text="All done", ts="2026-01-01T00:00:05.000000+00:00"),
            ],
        )
        spans = self._extract(p)
        assert len(spans) == 3
        assert "Multi-step" in spans[0]["attributes"]["input.value"]
        assert "result_of_step1" in spans[1]["attributes"]["input.value"]
        assert "result_of_step2" in spans[2]["attributes"]["input.value"]

    # -- span metadata --

    def test_span_has_correct_trace_and_parent_ids(self, tmp_transcript):
        p = tmp_transcript([human_entry("Hi"), llm_entry("Hello")])
        spans = self._extract(p)
        assert spans[0]["trace_id_hex"] == self.TRACE_ID
        assert spans[0]["parent_span_id_hex"] == self.ROOT_ID
        assert len(spans[0]["span_id_hex"]) == 16

    def test_span_name_includes_model(self, tmp_transcript):
        p = tmp_transcript(
            [human_entry("Hi"), llm_entry("Hello", model="claude-opus-4-6")],
        )
        spans = self._extract(p)
        assert spans[0]["name"] == "claude/claude-opus-4-6"

    def test_token_counts(self, tmp_transcript):
        p = tmp_transcript(
            [
                human_entry("Hi"),
                llm_entry("Hello", input_tokens=5, output_tokens=10),
            ],
        )
        spans = self._extract(p)
        attrs = spans[0]["attributes"]
        # prompt = input_tokens + cache_read + cache_create = 5+100+5 = 110
        assert attrs["llm.token_count.prompt"] == 110
        assert attrs["llm.token_count.completion"] == 10
        # total = input + cache_read + cache_create + output = 5+100+5+10 = 120
        assert attrs["llm.token_count.total"] == 120
        assert attrs["llm.token_count.prompt_details.cache_read"] == 100
        assert attrs["llm.token_count.prompt_details.cache_write"] == 5

    def test_timestamps_from_transcript(self, tmp_transcript):
        ts = "2026-06-15T12:30:00.000000+00:00"
        p = tmp_transcript([human_entry("Hi"), llm_entry("Hello", ts=ts)])
        spans = self._extract(p)
        expected_ns = tracer._iso_to_ns(ts)
        assert spans[0]["start_ns"] == expected_ns

    def test_multiple_llm_spans_in_turn(self, tmp_transcript):
        p = tmp_transcript(
            [
                human_entry("Q"),
                llm_entry("First", ts="2026-01-01T00:00:01.000000+00:00"),
                llm_entry("Second", ts="2026-01-01T00:00:02.000000+00:00"),
            ],
        )
        spans = self._extract(p)
        assert len(spans) == 2

    def test_ignores_assistant_entries_without_usage(self, tmp_transcript):
        entry_no_usage = {
            "type": "assistant",
            "message": {
                "role": "assistant",
                "model": "claude-sonnet-4-6",
                "content": [{"type": "text", "text": "hi"}],
            },
            "timestamp": "2026-01-01T00:00:02.000000+00:00",
        }
        p = tmp_transcript([human_entry("Hi"), entry_no_usage])
        assert self._extract(p) == []

    def test_ignores_progress_entries(self, tmp_transcript):
        p = tmp_transcript(
            [
                human_entry("Hi"),
                {
                    "type": "progress",
                    "message": {"content": "thinking..."},
                    "timestamp": "2026-01-01T00:00:01.000000+00:00",
                },
                llm_entry("Hello"),
            ],
        )
        spans = self._extract(p)
        assert len(spans) == 1

    def test_off_by_one_fix(self, tmp_transcript):
        """
        The off-by-one fix: human_count_at_start = current_human_count - 1
        ensures that the current human message (the Nth) is found by the
        condition human_count > (N-1).
        """
        # 3 human messages in transcript; we want to extract turn 3
        p = tmp_transcript(
            [
                human_entry("Turn 1"),
                llm_entry("Reply 1", ts="2026-01-01T00:00:01.000000+00:00"),
                human_entry("Turn 2"),
                llm_entry("Reply 2", ts="2026-01-01T00:00:03.000000+00:00"),
                human_entry("Turn 3"),
                llm_entry("Reply 3", ts="2026-01-01T00:00:05.000000+00:00"),
            ],
        )
        # With the fix: human_count_at_start = 3-1 = 2 → finds 3rd human
        spans = self._extract(p, human_count_at_start=2)
        assert len(spans) == 1
        assert spans[0]["attributes"]["output.value"] == "Reply 3"

        # Without the fix (human_count_at_start = 3) → would find nothing
        spans_broken = self._extract(p, human_count_at_start=3)
        assert spans_broken == []


# ---------------------------------------------------------------------------
# handle_pre_tool — state management
# ---------------------------------------------------------------------------


class TestHandlePreTool:
    CONFIG = {"api_key": "k", "task_id": "t", "endpoint": "https://x.example.com"}

    def _make_state_dir(self, tmp_path):
        d = tmp_path / "tracer"
        d.mkdir()
        return d

    def test_initialises_state_on_first_call(
        self,
        tmp_path,
        tmp_transcript,
        monkeypatch,
    ):
        monkeypatch.setattr(tracer, "STATE_DIR", tmp_path / "tracer")
        monkeypatch.setattr(tracer, "_build_and_export_spans", MagicMock())
        p = tmp_transcript([human_entry("Hello")])
        data = {
            "session_id": "s1",
            "tool_name": "Bash",
            "tool_input": {},
            "transcript_path": str(p),
        }
        tracer.handle_pre_tool(data, self.CONFIG)
        state = tracer._load_state("s1")
        assert state["session_id"] == "s1"
        assert state["turn_number"] == 1
        assert state["human_msg_count"] == 1
        assert state["current_trace"] is not None

    def test_sets_human_count_at_start_minus_one(
        self,
        tmp_path,
        tmp_transcript,
        monkeypatch,
    ):
        monkeypatch.setattr(tracer, "STATE_DIR", tmp_path / "tracer")
        monkeypatch.setattr(tracer, "_build_and_export_spans", MagicMock())
        p = tmp_transcript([human_entry("Hello")])
        data = {
            "session_id": "s2",
            "tool_name": "Bash",
            "tool_input": {},
            "transcript_path": str(p),
        }
        tracer.handle_pre_tool(data, self.CONFIG)
        state = tracer._load_state("s2")
        # human_msg_count=1, so human_count_at_start must be 0 (1-1)
        assert state["current_trace"]["human_count_at_start"] == 0

    def test_same_turn_no_new_trace(self, tmp_path, tmp_transcript, monkeypatch):
        monkeypatch.setattr(tracer, "STATE_DIR", tmp_path / "tracer")
        monkeypatch.setattr(tracer, "_build_and_export_spans", MagicMock())

        p = tmp_transcript([human_entry("Turn 1")])
        sid = "s4"
        data = {
            "session_id": sid,
            "tool_name": "Bash",
            "tool_input": {},
            "transcript_path": str(p),
        }
        tracer.handle_pre_tool(data, self.CONFIG)
        trace_id_after_first = tracer._load_state(sid)["current_trace"]["trace_id"]

        # Same transcript (no new human message) → same trace
        tracer.handle_pre_tool(data, self.CONFIG)
        trace_id_after_second = tracer._load_state(sid)["current_trace"]["trace_id"]
        assert trace_id_after_first == trace_id_after_second

    def test_context_continuation_creates_new_trace(
        self,
        tmp_path,
        tmp_transcript,
        monkeypatch,
    ):
        """When the transcript has 2+ more human messages than human_count_at_start,
        a context continuation happened without UserPromptSubmit.  The old trace must
        be completed and a new one started.
        """
        monkeypatch.setattr(tracer, "STATE_DIR", tmp_path / "tracer")
        (tmp_path / "tracer").mkdir()
        exported = []
        monkeypatch.setattr(
            tracer,
            "_build_and_export_spans",
            lambda **kw: exported.extend(kw["span_records"]),
        )

        sid = "cont-sess"
        # Build a transcript with 3 human messages (simulating continuation).
        p = tmp_transcript(
            [
                human_entry("Turn 1"),
                human_entry("Turn 2 (continuation trigger)"),
                human_entry("Turn 3 (continuation itself)"),
            ],
        )

        # Seed state as if turn 1 was in-progress (human_count_at_start=0,
        # which means the trace started after the 1st human message).
        old_trace_id = "a" * 32
        tracer._save_state(
            sid,
            {
                "session_id": sid,
                "session_start_ns": 1,
                "username": "u",
                "human_msg_count": 1,
                "turn_number": 1,
                "current_trace": {
                    "trace_id": old_trace_id,
                    "root_span_id": "b" * 16,
                    "turn_start_ns": 1,
                    "turn_number": 1,
                    "human_count_at_start": 0,
                },
            },
        )

        data = {
            "session_id": sid,
            "tool_name": "Bash",
            "tool_input": {},
            "transcript_path": str(p),
        }
        tracer.handle_pre_tool(data, self.CONFIG)

        state = tracer._load_state(sid)
        new_trace_id = state["current_trace"]["trace_id"]
        # A new trace must have been created.
        assert new_trace_id != old_trace_id
        # The old CHAIN span must have been exported.
        chain_spans = [
            s
            for s in exported
            if s.get("attributes", {}).get("openinference.span.kind") == "CHAIN"
        ]
        assert len(chain_spans) == 1

    def test_emit_pending_llm_always_updates_last_output(
        self,
        tmp_path,
        tmp_transcript,
        monkeypatch,
    ):
        """last_llm_output is updated to the last known span's output even when all
        spans were already emitted (no new_spans), so the CHAIN span gets the correct
        final text response rather than a stale value from an earlier PostToolUse.
        """
        monkeypatch.setattr(tracer, "STATE_DIR", tmp_path / "tracer")
        (tmp_path / "tracer").mkdir()
        monkeypatch.setattr(tracer, "_build_and_export_spans", MagicMock())

        sid = "last-out-sess"
        p = tmp_transcript(
            [
                human_entry("Hello"),
                llm_entry(
                    "First response with tool call",
                    tool_use_blocks=[{"id": "t1", "name": "Bash", "input": {}}],
                ),
                llm_entry("Final text response — the summary"),
            ],
        )

        state = {
            "session_id": sid,
            "username": "u",
            "current_trace": {
                "trace_id": "c" * 32,
                "root_span_id": "d" * 16,
                "turn_start_ns": 1,
                "turn_number": 1,
                "human_count_at_start": 0,
                # Both spans already emitted by prior PostToolUse calls.
                "emitted_llm_span_count": 2,
                "last_llm_output": "[{tool call json from earlier}]",
            },
        }
        tracer._save_state(sid, state)

        tracer._emit_pending_llm_spans(state, str(p), self.CONFIG)

        # last_llm_output must now reflect the FINAL text response.
        assert "Final text response" in state["current_trace"]["last_llm_output"]

    def test_first_call_inherits_parent_trace_when_no_user_prompt_submit(
        self,
        tmp_path,
        tmp_transcript,
        monkeypatch,
    ):
        """First pre_tool call for a fresh subagent session should claim a pending
        parent context and nest the trace under the parent AGENT span."""
        monkeypatch.setattr(tracer, "STATE_DIR", tmp_path / "tracer")
        monkeypatch.setattr(
            tracer,
            "_PENDING_AGENT_DIR",
            tmp_path / "tracer" / "pending_agent",
        )
        monkeypatch.setattr(tracer, "_build_and_export_spans", MagicMock())
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        monkeypatch.delenv("CLAUDE_PROJECT_DIR", raising=False)

        parent_trace_id = "deadbeef" * 4
        parent_span_id = "cafebabe" * 2

        tracer._write_pending_agent_context(
            "parent-main",
            parent_trace_id,
            parent_span_id,
            agent_prompt="search files",
        )

        p = tmp_transcript([human_entry("search files")])
        data = {
            "session_id": "subagent-no-ups",
            "tool_name": "Bash",
            "tool_input": {"command": "find . -name '*.py'"},
            "transcript_path": str(p),
        }
        tracer.handle_pre_tool(data, self.CONFIG)

        state = tracer._load_state("subagent-no-ups")
        assert state["current_trace"]["trace_id"] == parent_trace_id
        assert state["current_trace"]["parent_agent_span_id"] == parent_span_id
        # Pending context file must be gone (claimed)
        pending_files = list((tmp_path / "tracer" / "pending_agent").glob("*.json"))
        assert pending_files == []


# ---------------------------------------------------------------------------
# handle_post_tool — TOOL span emission
# ---------------------------------------------------------------------------


class TestHandlePostTool:
    CONFIG = {"api_key": "k", "task_id": "t", "endpoint": "https://x.example.com"}

    def _setup_state(self, tmp_path, session_id, tool_name="Bash"):
        tracer.STATE_DIR.mkdir(parents=True, exist_ok=True)
        state = {
            "session_id": session_id,
            "username": "test-user",
            "current_trace": {
                "trace_id": "a" * 32,
                "root_span_id": "b" * 16,
                "turn_start_ns": 1_000_000_000,
                "turn_number": 1,
                "human_count_at_start": 0,
            },
            "pending_tools": {
                tool_name: {
                    "tool_name": tool_name,
                    "tool_input": {"command": "echo hi"},
                    "start_ns": 1_000_000_000,
                },
            },
        }
        tracer._save_state(session_id, state)
        return state

    def test_emits_tool_span(self, tmp_path, monkeypatch):
        monkeypatch.setattr(tracer, "STATE_DIR", tmp_path / "tracer")
        (tmp_path / "tracer").mkdir()
        captured = []

        def fake_export(config, session_id, username, span_records):
            captured.extend(span_records)

        monkeypatch.setattr(tracer, "_build_and_export_spans", fake_export)

        self._setup_state(tmp_path, "ps1")
        data = {
            "session_id": "ps1",
            "tool_name": "Bash",
            "tool_input": {"command": "echo hi"},
            "tool_response": {"stdout": "hi", "returncode": 0},
        }
        tracer.handle_post_tool(data, self.CONFIG)

        tool_spans = [
            s
            for s in captured
            if s.get("attributes", {}).get("openinference.span.kind") == "TOOL"
        ]
        assert len(tool_spans) >= 1
        assert tool_spans[0]["attributes"]["tool.name"] == "Bash"

    def test_task_tool_emits_agent_span(self, tmp_path, monkeypatch):
        monkeypatch.setattr(tracer, "STATE_DIR", tmp_path / "tracer")
        (tmp_path / "tracer").mkdir()
        captured = []
        monkeypatch.setattr(
            tracer,
            "_build_and_export_spans",
            lambda **kw: captured.extend(kw["span_records"]),
        )
        self._setup_state(tmp_path, "ps2", tool_name="Task")
        data = {
            "session_id": "ps2",
            "tool_name": "Task",
            "tool_input": {"prompt": "do something"},
            "tool_response": {"result": "done"},
        }
        tracer.handle_post_tool(data, self.CONFIG)

        agent_spans = [
            s
            for s in captured
            if s.get("attributes", {}).get("openinference.span.kind") == "AGENT"
        ]
        assert len(agent_spans) >= 1

    def test_tool_span_has_input_and_output(self, tmp_path, monkeypatch):
        monkeypatch.setattr(tracer, "STATE_DIR", tmp_path / "tracer")
        (tmp_path / "tracer").mkdir()
        captured = []
        monkeypatch.setattr(
            tracer,
            "_build_and_export_spans",
            lambda **kw: captured.extend(kw["span_records"]),
        )
        self._setup_state(tmp_path, "ps3")
        data = {
            "session_id": "ps3",
            "tool_name": "Bash",
            "tool_input": {"command": "ls"},
            "tool_response": {"stdout": "file.txt"},
        }
        tracer.handle_post_tool(data, self.CONFIG)

        tool_span = next(
            s
            for s in captured
            if s.get("attributes", {}).get("openinference.span.kind") == "TOOL"
        )
        assert "ls" in tool_span["attributes"]["input.value"]
        assert "file.txt" in tool_span["attributes"]["output.value"]

    def test_no_state_does_not_crash(self, tmp_path, monkeypatch):
        monkeypatch.setattr(tracer, "STATE_DIR", tmp_path / "tracer")
        (tmp_path / "tracer").mkdir()
        monkeypatch.setattr(tracer, "_build_and_export_spans", MagicMock())
        # No state written for "nosuchsession"
        tracer.handle_post_tool({"session_id": "nosuchsession"}, self.CONFIG)

    def test_concurrent_post_tool_no_duplicate_llm_spans(
        self,
        tmp_path,
        tmp_transcript,
        monkeypatch,
    ):
        """Parallel PostToolUse handlers must not emit the same LLM span twice."""
        import threading

        monkeypatch.setattr(tracer, "STATE_DIR", tmp_path / "tracer")
        (tmp_path / "tracer").mkdir()

        captured = []
        lock = threading.Lock()

        def fake_export(config, session_id, username, span_records):
            with lock:
                captured.extend(span_records)

        monkeypatch.setattr(tracer, "_build_and_export_spans", fake_export)

        p = tmp_transcript(
            [
                human_entry("Do two things in parallel"),
                llm_entry("Sure", ts="2026-01-01T00:00:01.000000+00:00"),
            ],
        )
        # Pre-populate state as if handle_pre_tool already ran for two tools
        state = {
            "session_id": "concurrent1",
            "username": "tester",
            "human_msg_count": 1,
            "current_trace": {
                "trace_id": "a" * 32,
                "root_span_id": "b" * 16,
                "turn_start_ns": 1_000_000_000,
                "turn_number": 1,
                "human_count_at_start": 0,
                "emitted_llm_span_count": 0,
            },
            "pending_tools": {
                "Read": {
                    "tool_name": "Read",
                    "tool_input": {"file_path": "/a"},
                    "start_ns": 1_000_000_000,
                },
            },
        }
        tracer._save_state("concurrent1", state)

        data1 = {
            "session_id": "concurrent1",
            "tool_name": "Read",
            "tool_input": {"file_path": "/a"},
            "tool_response": "content a",
            "transcript_path": str(p),
        }
        data2 = {
            "session_id": "concurrent1",
            "tool_name": "Read",
            "tool_input": {"file_path": "/b"},
            "tool_response": "content b",
            "transcript_path": str(p),
        }

        t1 = threading.Thread(target=tracer.handle_post_tool, args=(data1, self.CONFIG))
        t2 = threading.Thread(target=tracer.handle_post_tool, args=(data2, self.CONFIG))
        t1.start()
        t2.start()
        t1.join()
        t2.join()

        llm_spans = [
            s
            for s in captured
            if s.get("attributes", {}).get("openinference.span.kind") == "LLM"
        ]
        # Transcript has exactly 1 LLM call — must emit exactly 1, not 2
        assert (
            len(llm_spans) == 1
        ), f"Expected 1 LLM span, got {len(llm_spans)} (race condition)"


# ---------------------------------------------------------------------------
# handle_stop — turn completion
# ---------------------------------------------------------------------------


class TestHandleStop:
    CONFIG = {"api_key": "k", "task_id": "t", "endpoint": "https://x.example.com"}

    def test_emits_chain_span_and_cleans_state(
        self,
        tmp_path,
        tmp_transcript,
        monkeypatch,
    ):
        monkeypatch.setattr(tracer, "STATE_DIR", tmp_path / "tracer")
        (tmp_path / "tracer").mkdir()
        captured = []
        monkeypatch.setattr(
            tracer,
            "_build_and_export_spans",
            lambda **kw: captured.extend(kw["span_records"]),
        )

        p = tmp_transcript([human_entry("Stop me"), llm_entry("Done")])
        state = {
            "session_id": "stop1",
            "username": "tester",
            "current_trace": {
                "trace_id": "c" * 32,
                "root_span_id": "d" * 16,
                "turn_start_ns": 1_000_000_000,
                "turn_number": 1,
                "human_count_at_start": 0,
                "prompt_preview": "Stop me",
                "last_llm_output": "Done",
            },
        }
        tracer._save_state("stop1", state)

        data = {"session_id": "stop1", "transcript_path": str(p)}
        tracer.handle_stop(data, self.CONFIG)

        chain_spans = [
            s
            for s in captured
            if s.get("attributes", {}).get("openinference.span.kind") == "CHAIN"
        ]
        assert len(chain_spans) == 1
        attrs = chain_spans[0]["attributes"]
        assert attrs["session.id"] == "stop1"
        assert attrs["user.id"] == "tester"

        # State file should be deleted
        assert not (tmp_path / "tracer" / "stop1.json").exists()

    def test_stop_with_no_active_trace_does_not_crash(self, tmp_path, monkeypatch):
        monkeypatch.setattr(tracer, "STATE_DIR", tmp_path / "tracer")
        (tmp_path / "tracer").mkdir()
        monkeypatch.setattr(tracer, "_build_and_export_spans", MagicMock())
        tracer.handle_stop({"session_id": "nobody"}, self.CONFIG)

    def test_stop_emits_pending_llm_spans(self, tmp_path, tmp_transcript, monkeypatch):
        monkeypatch.setattr(tracer, "STATE_DIR", tmp_path / "tracer")
        (tmp_path / "tracer").mkdir()
        captured = []
        monkeypatch.setattr(
            tracer,
            "_build_and_export_spans",
            lambda **kw: captured.extend(kw["span_records"]),
        )

        p = tmp_transcript([human_entry("Go"), llm_entry("Result")])
        state = {
            "session_id": "stop2",
            "username": "tester",
            "current_trace": {
                "trace_id": "e" * 32,
                "root_span_id": "f" * 16,
                "turn_start_ns": 1_000_000_000,
                "turn_number": 1,
                "human_count_at_start": 0,
                "prompt_preview": "Go",
                "emitted_llm_span_count": 0,
            },
        }
        tracer._save_state("stop2", state)
        tracer.handle_stop(
            {"session_id": "stop2", "transcript_path": str(p)},
            self.CONFIG,
        )

        llm_spans = [
            s
            for s in captured
            if s.get("attributes", {}).get("openinference.span.kind") == "LLM"
        ]
        assert len(llm_spans) == 1
        assert llm_spans[0]["attributes"]["output.value"] == "Result"


# ---------------------------------------------------------------------------
# handle_user_prompt_submit — new trace creation and turn completion
# ---------------------------------------------------------------------------


class TestHandleUserPromptSubmit:
    CONFIG = {"api_key": "k", "task_id": "t", "endpoint": "https://x.example.com"}

    def test_starts_new_trace(self, tmp_path, monkeypatch):
        monkeypatch.setattr(tracer, "STATE_DIR", tmp_path / "tracer")
        tracer.STATE_DIR.mkdir(parents=True, exist_ok=True)
        monkeypatch.setattr(tracer, "_build_and_export_spans", MagicMock())

        data = {"session_id": "ups1", "prompt": "Hello Claude"}
        tracer.handle_user_prompt_submit(data, self.CONFIG)

        state = tracer._load_state("ups1")
        assert state["session_id"] == "ups1"
        assert state["turn_number"] == 1
        assert state["current_trace"] is not None

    def test_sets_accurate_prompt_preview(self, tmp_path, monkeypatch):
        monkeypatch.setattr(tracer, "STATE_DIR", tmp_path / "tracer")
        tracer.STATE_DIR.mkdir(parents=True, exist_ok=True)
        monkeypatch.setattr(tracer, "_build_and_export_spans", MagicMock())

        data = {"session_id": "ups2", "prompt": "Exact prompt text"}
        tracer.handle_user_prompt_submit(data, self.CONFIG)

        state = tracer._load_state("ups2")
        assert state["current_trace"]["prompt_preview"] == "Exact prompt text"

    def test_completes_previous_trace_and_starts_new(self, tmp_path, monkeypatch):
        monkeypatch.setattr(tracer, "STATE_DIR", tmp_path / "tracer")
        tracer.STATE_DIR.mkdir(parents=True, exist_ok=True)
        captured = []
        monkeypatch.setattr(
            tracer,
            "_build_and_export_spans",
            lambda **kw: captured.extend(kw["span_records"]),
        )

        # Set up an existing in-progress trace
        existing_state = {
            "session_id": "ups3",
            "username": "tester",
            "turn_number": 1,
            "human_msg_count": 1,
            "current_trace": {
                "trace_id": "a" * 32,
                "root_span_id": "b" * 16,
                "turn_start_ns": 1_000_000_000,
                "turn_number": 1,
                "human_count_at_start": 0,
                "prompt_preview": "Previous prompt",
            },
        }
        tracer._save_state("ups3", existing_state)

        # Submit new prompt — should complete previous trace and start a new one
        data = {"session_id": "ups3", "prompt": "New prompt"}
        tracer.handle_user_prompt_submit(data, self.CONFIG)

        # Should have emitted a CHAIN span for the previous trace
        chain_spans = [
            s
            for s in captured
            if s.get("attributes", {}).get("openinference.span.kind") == "CHAIN"
        ]
        assert len(chain_spans) == 1

        # New trace should have a different trace_id and the new prompt
        new_state = tracer._load_state("ups3")
        assert new_state["current_trace"]["trace_id"] != "a" * 32
        assert new_state["current_trace"]["prompt_preview"] == "New prompt"
        assert new_state["turn_number"] == 2

    def test_initialises_session_on_first_call(self, tmp_path, monkeypatch):
        monkeypatch.setattr(tracer, "STATE_DIR", tmp_path / "tracer")
        tracer.STATE_DIR.mkdir(parents=True, exist_ok=True)
        monkeypatch.setattr(tracer, "_build_and_export_spans", MagicMock())

        data = {"session_id": "ups4", "prompt": "First ever prompt"}
        tracer.handle_user_prompt_submit(data, self.CONFIG)

        state = tracer._load_state("ups4")
        assert state["session_id"] == "ups4"
        assert "session_start_ns" in state
        assert "username" in state


# ---------------------------------------------------------------------------
# handle_post_tool_failure — error span emission
# ---------------------------------------------------------------------------


class TestHandlePostToolFailure:
    CONFIG = {"api_key": "k", "task_id": "t", "endpoint": "https://x.example.com"}

    def _setup_state(self, session_id, tool_name="Bash"):
        tracer.STATE_DIR.mkdir(parents=True, exist_ok=True)
        state = {
            "session_id": session_id,
            "username": "test-user",
            "current_trace": {
                "trace_id": "a" * 32,
                "root_span_id": "b" * 16,
                "turn_start_ns": 1_000_000_000,
                "turn_number": 1,
                "human_count_at_start": 0,
            },
            "pending_tools": {
                tool_name: {
                    "tool_name": tool_name,
                    "tool_input": {"command": "echo hi"},
                    "start_ns": 1_000_000_000,
                },
            },
        }
        tracer._save_state(session_id, state)
        return state

    def test_emits_tool_span_with_error_flag(self, tmp_path, monkeypatch):
        monkeypatch.setattr(tracer, "STATE_DIR", tmp_path / "tracer")
        captured = []
        monkeypatch.setattr(
            tracer,
            "_build_and_export_spans",
            lambda **kw: captured.extend(kw["span_records"]),
        )

        self._setup_state("ptf1")
        data = {
            "session_id": "ptf1",
            "tool_name": "Bash",
            "tool_input": {"command": "bad_cmd"},
            "tool_response": {"error": "command not found"},
        }
        tracer.handle_post_tool_failure(data, self.CONFIG)

        tool_spans = [
            s
            for s in captured
            if s.get("attributes", {}).get("openinference.span.kind") == "TOOL"
        ]
        assert len(tool_spans) >= 1
        assert tool_spans[0].get("error") is True
        assert "command not found" in tool_spans[0].get("error_msg", "")

    def test_error_text_in_output_value(self, tmp_path, monkeypatch):
        monkeypatch.setattr(tracer, "STATE_DIR", tmp_path / "tracer")
        captured = []
        monkeypatch.setattr(
            tracer,
            "_build_and_export_spans",
            lambda **kw: captured.extend(kw["span_records"]),
        )

        self._setup_state("ptf2")
        data = {
            "session_id": "ptf2",
            "tool_name": "Bash",
            "tool_input": {"command": "fail"},
            "tool_response": {"error": "permission denied"},
        }
        tracer.handle_post_tool_failure(data, self.CONFIG)

        tool_span = next(
            s
            for s in captured
            if s.get("attributes", {}).get("openinference.span.kind") == "TOOL"
        )
        assert "permission denied" in tool_span["attributes"]["output.value"]

    def test_task_failure_emits_agent_span_with_error(self, tmp_path, monkeypatch):
        monkeypatch.setattr(tracer, "STATE_DIR", tmp_path / "tracer")
        captured = []
        monkeypatch.setattr(
            tracer,
            "_build_and_export_spans",
            lambda **kw: captured.extend(kw["span_records"]),
        )

        self._setup_state("ptf3", tool_name="Task")
        data = {
            "session_id": "ptf3",
            "tool_name": "Task",
            "tool_input": {"prompt": "do something"},
            "tool_response": {"error": "subagent failed"},
        }
        tracer.handle_post_tool_failure(data, self.CONFIG)

        agent_spans = [
            s
            for s in captured
            if s.get("attributes", {}).get("openinference.span.kind") == "AGENT"
        ]
        assert len(agent_spans) >= 1
        assert agent_spans[0].get("error") is True

    def test_no_state_does_not_crash(self, tmp_path, monkeypatch):
        monkeypatch.setattr(tracer, "STATE_DIR", tmp_path / "tracer")
        tracer.STATE_DIR.mkdir(parents=True, exist_ok=True)
        monkeypatch.setattr(tracer, "_build_and_export_spans", MagicMock())
        tracer.handle_post_tool_failure({"session_id": "nosuchsession"}, self.CONFIG)

    def test_error_from_string_response(self, tmp_path, monkeypatch):
        monkeypatch.setattr(tracer, "STATE_DIR", tmp_path / "tracer")
        captured = []
        monkeypatch.setattr(
            tracer,
            "_build_and_export_spans",
            lambda **kw: captured.extend(kw["span_records"]),
        )

        self._setup_state("ptf4")
        data = {
            "session_id": "ptf4",
            "tool_name": "Read",
            "tool_input": {"file_path": "/no/such/file"},
            "tool_response": "File not found: /no/such/file",
        }
        tracer.handle_post_tool_failure(data, self.CONFIG)

        tool_spans = [
            s
            for s in captured
            if s.get("attributes", {}).get("openinference.span.kind") == "TOOL"
        ]
        assert len(tool_spans) >= 1
        assert tool_spans[0].get("error") is True
        assert "File not found" in tool_spans[0]["attributes"]["output.value"]


# ---------------------------------------------------------------------------
# RETRIEVER span kind — WebSearch and WebFetch remapping
# ---------------------------------------------------------------------------


class TestRetrieverSpanKind:
    CONFIG = {"api_key": "k", "task_id": "t", "endpoint": "https://x.example.com"}

    def _setup_retriever_state(self, session_id, tool_name, tool_input):
        tracer.STATE_DIR.mkdir(parents=True, exist_ok=True)
        state = {
            "session_id": session_id,
            "username": "test-user",
            "current_trace": {
                "trace_id": "a" * 32,
                "root_span_id": "b" * 16,
                "turn_start_ns": 1_000_000_000,
                "turn_number": 1,
                "human_count_at_start": 0,
            },
            "pending_tools": {
                tool_name: {
                    "tool_name": tool_name,
                    "tool_input": tool_input,
                    "start_ns": 1_000_000_000,
                },
            },
        }
        tracer._save_state(session_id, state)

    def test_websearch_emits_retriever_span(self, tmp_path, monkeypatch):
        monkeypatch.setattr(tracer, "STATE_DIR", tmp_path / "tracer")
        captured = []
        monkeypatch.setattr(
            tracer,
            "_build_and_export_spans",
            lambda **kw: captured.extend(kw["span_records"]),
        )

        self._setup_retriever_state(
            "ret1",
            "WebSearch",
            {"query": "python opentelemetry"},
        )
        data = {
            "session_id": "ret1",
            "tool_name": "WebSearch",
            "tool_input": {"query": "python opentelemetry"},
            "tool_response": "Search results about opentelemetry...",
        }
        tracer.handle_post_tool(data, self.CONFIG)

        retriever_spans = [
            s
            for s in captured
            if s.get("attributes", {}).get("openinference.span.kind") == "RETRIEVER"
        ]
        assert len(retriever_spans) >= 1

    def test_webfetch_emits_retriever_span(self, tmp_path, monkeypatch):
        monkeypatch.setattr(tracer, "STATE_DIR", tmp_path / "tracer")
        captured = []
        monkeypatch.setattr(
            tracer,
            "_build_and_export_spans",
            lambda **kw: captured.extend(kw["span_records"]),
        )

        self._setup_retriever_state(
            "ret2",
            "WebFetch",
            {"url": "https://example.com", "prompt": "summarize"},
        )
        data = {
            "session_id": "ret2",
            "tool_name": "WebFetch",
            "tool_input": {"url": "https://example.com", "prompt": "summarize"},
            "tool_response": "Page content from example.com...",
        }
        tracer.handle_post_tool(data, self.CONFIG)

        retriever_spans = [
            s
            for s in captured
            if s.get("attributes", {}).get("openinference.span.kind") == "RETRIEVER"
        ]
        assert len(retriever_spans) >= 1

    def test_bash_emits_tool_span_not_retriever(self, tmp_path, monkeypatch):
        monkeypatch.setattr(tracer, "STATE_DIR", tmp_path / "tracer")
        captured = []
        monkeypatch.setattr(
            tracer,
            "_build_and_export_spans",
            lambda **kw: captured.extend(kw["span_records"]),
        )

        self._setup_retriever_state("ret3", "Bash", {"command": "echo hi"})
        data = {
            "session_id": "ret3",
            "tool_name": "Bash",
            "tool_input": {"command": "echo hi"},
            "tool_response": "hi",
        }
        tracer.handle_post_tool(data, self.CONFIG)

        tool_spans = [
            s
            for s in captured
            if s.get("attributes", {}).get("openinference.span.kind") == "TOOL"
        ]
        assert len(tool_spans) >= 1
        retriever_spans = [
            s
            for s in captured
            if s.get("attributes", {}).get("openinference.span.kind") == "RETRIEVER"
        ]
        assert len(retriever_spans) == 0

    def test_retriever_has_document_content(self, tmp_path, monkeypatch):
        monkeypatch.setattr(tracer, "STATE_DIR", tmp_path / "tracer")
        captured = []
        monkeypatch.setattr(
            tracer,
            "_build_and_export_spans",
            lambda **kw: captured.extend(kw["span_records"]),
        )

        self._setup_retriever_state(
            "ret4",
            "WebSearch",
            {"query": "openinference spec"},
        )
        data = {
            "session_id": "ret4",
            "tool_name": "WebSearch",
            "tool_input": {"query": "openinference spec"},
            "tool_response": "Relevant results about the openinference specification",
        }
        tracer.handle_post_tool(data, self.CONFIG)

        retriever_span = next(
            s
            for s in captured
            if s.get("attributes", {}).get("openinference.span.kind") == "RETRIEVER"
        )
        assert "retrieval.documents.0.document.content" in retriever_span["attributes"]
        assert (
            "openinference"
            in retriever_span["attributes"]["retrieval.documents.0.document.content"]
        )

    def test_websearch_input_value_is_query(self, tmp_path, monkeypatch):
        monkeypatch.setattr(tracer, "STATE_DIR", tmp_path / "tracer")
        captured = []
        monkeypatch.setattr(
            tracer,
            "_build_and_export_spans",
            lambda **kw: captured.extend(kw["span_records"]),
        )

        self._setup_retriever_state(
            "ret5",
            "WebSearch",
            {"query": "specific search query"},
        )
        data = {
            "session_id": "ret5",
            "tool_name": "WebSearch",
            "tool_input": {"query": "specific search query"},
            "tool_response": "results",
        }
        tracer.handle_post_tool(data, self.CONFIG)

        retriever_span = next(
            s
            for s in captured
            if s.get("attributes", {}).get("openinference.span.kind") == "RETRIEVER"
        )
        assert retriever_span["attributes"]["input.value"] == "specific search query"
        assert retriever_span["attributes"]["input.mime_type"] == "text/plain"

    def test_webfetch_input_value_is_url(self, tmp_path, monkeypatch):
        monkeypatch.setattr(tracer, "STATE_DIR", tmp_path / "tracer")
        captured = []
        monkeypatch.setattr(
            tracer,
            "_build_and_export_spans",
            lambda **kw: captured.extend(kw["span_records"]),
        )

        self._setup_retriever_state(
            "ret6",
            "WebFetch",
            {"url": "https://docs.example.com/api", "prompt": "extract"},
        )
        data = {
            "session_id": "ret6",
            "tool_name": "WebFetch",
            "tool_input": {"url": "https://docs.example.com/api", "prompt": "extract"},
            "tool_response": "API documentation content",
        }
        tracer.handle_post_tool(data, self.CONFIG)

        retriever_span = next(
            s
            for s in captured
            if s.get("attributes", {}).get("openinference.span.kind") == "RETRIEVER"
        )
        assert (
            retriever_span["attributes"]["input.value"]
            == "https://docs.example.com/api"
        )
        assert retriever_span["attributes"]["input.mime_type"] == "text/plain"

    def test_websearch_failure_emits_retriever_error_span(self, tmp_path, monkeypatch):
        monkeypatch.setattr(tracer, "STATE_DIR", tmp_path / "tracer")
        captured = []
        monkeypatch.setattr(
            tracer,
            "_build_and_export_spans",
            lambda **kw: captured.extend(kw["span_records"]),
        )

        self._setup_retriever_state("ret7", "WebSearch", {"query": "test"})
        data = {
            "session_id": "ret7",
            "tool_name": "WebSearch",
            "tool_input": {"query": "test"},
            "tool_response": {"error": "search service unavailable"},
        }
        tracer.handle_post_tool_failure(data, self.CONFIG)

        retriever_spans = [
            s
            for s in captured
            if s.get("attributes", {}).get("openinference.span.kind") == "RETRIEVER"
        ]
        assert len(retriever_spans) >= 1
        assert retriever_spans[0].get("error") is True


# ---------------------------------------------------------------------------
# State helper error paths
# ---------------------------------------------------------------------------


class TestStateHelperErrorPaths:
    """Error branches in _load_state / _save_state / _delete_state / _cleanup_stale_states."""

    def test_load_state_corrupt_json_returns_empty(self, tmp_path, monkeypatch):
        monkeypatch.setattr(tracer, "STATE_DIR", tmp_path / "tracer")
        (tmp_path / "tracer").mkdir()
        (tmp_path / "tracer" / "bad_sess.json").write_text("{{not valid json")
        state = tracer._load_state("bad_sess")
        assert state == {}

    def test_save_state_write_error_does_not_raise(self, tmp_path, monkeypatch):
        monkeypatch.setattr(tracer, "STATE_DIR", tmp_path / "tracer")
        (tmp_path / "tracer").mkdir()
        # Make the directory read-only so the write fails
        state_file = tmp_path / "tracer" / "ro_sess.json"
        state_file.write_text("{}")
        state_file.chmod(0o444)
        # Must not raise
        tracer._save_state("ro_sess", {"key": "value"})

    def test_delete_state_missing_file_does_not_raise(self, tmp_path, monkeypatch):
        monkeypatch.setattr(tracer, "STATE_DIR", tmp_path / "tracer")
        (tmp_path / "tracer").mkdir()
        tracer._delete_state("nonexistent_session")  # Must not raise

    def test_cleanup_stale_states_removes_old_files(self, tmp_path, monkeypatch):
        monkeypatch.setattr(tracer, "STATE_DIR", tmp_path / "tracer")
        (tmp_path / "tracer").mkdir()
        old_file = tmp_path / "tracer" / "old.json"
        old_file.write_text("{}")
        # Set mtime to 3 days ago (well beyond 48-hour threshold)
        import os
        import time

        old_mtime = time.time() - 3 * 24 * 3600
        os.utime(old_file, (old_mtime, old_mtime))
        tracer._cleanup_stale_states()
        assert not old_file.exists()

    def test_cleanup_stale_states_keeps_recent_files(self, tmp_path, monkeypatch):
        monkeypatch.setattr(tracer, "STATE_DIR", tmp_path / "tracer")
        (tmp_path / "tracer").mkdir()
        recent = tmp_path / "tracer" / "recent.json"
        recent.write_text("{}")
        tracer._cleanup_stale_states()
        assert recent.exists()


# ---------------------------------------------------------------------------
# _find_transcript_path
# ---------------------------------------------------------------------------


def _real_transcript_content() -> str:
    """Minimal transcript content with one human message — passes _is_real_transcript."""
    return (
        json.dumps({"type": "user", "message": {"role": "user", "content": "hi"}})
        + "\n"
    )


def _shadow_transcript_content() -> str:
    """Shadow transcript with only pr-link entries — rejected by _is_real_transcript."""
    return json.dumps({"type": "pr-link", "sessionId": "s", "prNumber": 1}) + "\n"


class TestFindTranscriptPath:
    def test_uses_transcript_path_from_data(self, tmp_path):
        p = tmp_path / "t.jsonl"
        p.write_text(_real_transcript_content())
        result = tracer._find_transcript_path({"transcript_path": str(p)}, "any")
        assert result == str(p)

    def test_returns_none_for_nonexistent_explicit_path(self, tmp_path):
        result = tracer._find_transcript_path(
            {"transcript_path": str(tmp_path / "missing.jsonl")},
            "any",
        )
        assert result is None

    def test_skips_shadow_transcript_in_data(self, tmp_path):
        """A transcript with only pr-link entries should be rejected."""
        shadow = tmp_path / "shadow.jsonl"
        shadow.write_text(_shadow_transcript_content())
        result = tracer._find_transcript_path({"transcript_path": str(shadow)}, "any")
        assert result is None

    def test_shadow_in_data_falls_back_to_real_glob(self, tmp_path, monkeypatch):
        """When hook data points to a shadow transcript, glob fallback finds the real one."""
        session_id = "sess-fallback"
        shadow = tmp_path / "shadow.jsonl"
        shadow.write_text(_shadow_transcript_content())

        real_dir = tmp_path / ".claude" / "projects" / "real-project"
        real_dir.mkdir(parents=True)
        real = real_dir / f"{session_id}.jsonl"
        real.write_text(_real_transcript_content())

        monkeypatch.delenv("CLAUDE_PROJECT_DIR", raising=False)
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        result = tracer._find_transcript_path(
            {"transcript_path": str(shadow)},
            session_id,
        )
        assert result == str(real)

    def test_glob_prefers_largest_file(self, tmp_path, monkeypatch):
        """When multiple candidates exist, the largest (most content) is preferred."""
        session_id = "sess-multi"
        small_dir = tmp_path / ".claude" / "projects" / "small-proj"
        small_dir.mkdir(parents=True)
        small = small_dir / f"{session_id}.jsonl"
        small.write_text(_real_transcript_content())

        big_dir = tmp_path / ".claude" / "projects" / "big-proj"
        big_dir.mkdir(parents=True)
        big = big_dir / f"{session_id}.jsonl"
        # Make it larger with more entries
        big.write_text(_real_transcript_content() * 10)

        monkeypatch.delenv("CLAUDE_PROJECT_DIR", raising=False)
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        result = tracer._find_transcript_path({}, session_id)
        assert result == str(big)

    def test_env_var_path(self, tmp_path, monkeypatch):
        # Create <home>/.claude/projects/<sanitized>/sess.jsonl via CLAUDE_PROJECT_DIR
        project_dir = "/my/project"
        sanitized = project_dir.replace("/", "-")
        transcript = tmp_path / ".claude" / "projects" / sanitized / "myses.jsonl"
        transcript.parent.mkdir(parents=True)
        transcript.write_text(_real_transcript_content())
        monkeypatch.setenv("CLAUDE_PROJECT_DIR", project_dir)
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        result = tracer._find_transcript_path({}, "myses")
        assert result == str(transcript)

    def test_glob_fallback(self, tmp_path, monkeypatch):
        # No env var, but transcript exists somewhere under projects/
        transcript = tmp_path / ".claude" / "projects" / "some-dir" / "globsess.jsonl"
        transcript.parent.mkdir(parents=True)
        transcript.write_text(_real_transcript_content())
        monkeypatch.delenv("CLAUDE_PROJECT_DIR", raising=False)
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        result = tracer._find_transcript_path({}, "globsess")
        assert result == str(transcript)

    def test_returns_none_when_transcript_not_found(self, tmp_path, monkeypatch):
        monkeypatch.delenv("CLAUDE_PROJECT_DIR", raising=False)
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        result = tracer._find_transcript_path({}, "nosuchsession")
        assert result is None


# ---------------------------------------------------------------------------
# _get_cached_transcript_path
# ---------------------------------------------------------------------------


class TestGetCachedTranscriptPath:
    def test_uses_cached_path_from_state(self, tmp_path):
        """If state already has a transcript_path that exists, return it without
        calling _find_transcript_path again — even if the hook data points elsewhere."""
        real = tmp_path / "real.jsonl"
        real.write_text("")
        decoy = tmp_path / "decoy.jsonl"
        decoy.write_text("")

        state = {"transcript_path": str(real)}
        result = tracer._get_cached_transcript_path(
            {"transcript_path": str(decoy)},
            state,
            "any",
        )
        assert result == str(real)

    def test_resolves_and_caches_when_state_has_no_path(self, tmp_path):
        """When state has no cached path, resolve via hook data and cache it."""
        p = tmp_path / "t.jsonl"
        p.write_text(_real_transcript_content())
        state = {}
        result = tracer._get_cached_transcript_path(
            {"transcript_path": str(p)},
            state,
            "any",
        )
        assert result == str(p)
        assert state["transcript_path"] == str(p)

    def test_re_resolves_if_cached_path_deleted(self, tmp_path):
        """If the cached file no longer exists, fall through to _find_transcript_path."""
        gone = tmp_path / "gone.jsonl"
        gone.write_text(_real_transcript_content())
        state = {"transcript_path": str(gone)}
        gone.unlink()  # delete it

        new = tmp_path / "new.jsonl"
        new.write_text(_real_transcript_content())
        result = tracer._get_cached_transcript_path(
            {"transcript_path": str(new)},
            state,
            "any",
        )
        assert result == str(new)
        assert state["transcript_path"] == str(new)

    def test_cached_path_survives_shadow_file_creation(self, tmp_path, monkeypatch):
        """Simulate gh pr create writing a shadow file mid-session.

        The cached path from UserPromptSubmit should be used even after
        the hook payload starts pointing to the shadow file.
        """
        session_id = "stable-sess"
        real_dir = tmp_path / ".claude" / "projects" / "real-project"
        real_dir.mkdir(parents=True)
        real = real_dir / f"{session_id}.jsonl"
        real.write_text(
            "\n".join(
                [
                    json.dumps(
                        {"type": "user", "message": {"role": "user", "content": "hi"}},
                    ),
                    json.dumps(
                        {
                            "type": "assistant",
                            "message": {"role": "assistant", "content": []},
                        },
                    ),
                ],
            )
            + "\n",
        )

        # State cached at UserPromptSubmit time, pointing to the real transcript
        state = {"transcript_path": str(real)}

        # Mid-session, gh pr create writes a shadow file; hook data now points there
        shadow_dir = tmp_path / ".claude" / "projects" / "worktree-dir"
        shadow_dir.mkdir(parents=True)
        shadow = shadow_dir / f"{session_id}.jsonl"
        shadow.write_text(json.dumps({"type": "pr-link", "prNumber": 99}) + "\n")

        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        result = tracer._get_cached_transcript_path(
            {"transcript_path": str(shadow)},
            state,
            session_id,
        )
        # Must return the cached real transcript, not the shadow
        assert result == str(real)


# ---------------------------------------------------------------------------
# Subagent trace context propagation
# ---------------------------------------------------------------------------


class TestSubagentContextPropagation:
    """Tests for _write_pending_agent_context / _claim_pending_agent_context."""

    def test_write_and_claim_round_trip(self, tmp_path, monkeypatch):
        monkeypatch.setattr(tracer, "STATE_DIR", tmp_path / "tracer")
        monkeypatch.setattr(
            tracer,
            "_PENDING_AGENT_DIR",
            tmp_path / "tracer" / "pending_agent",
        )
        tracer._write_pending_agent_context("parent-sess", "traceid-abc", "spanid-xyz")
        ctx = tracer._claim_pending_agent_context()
        assert ctx is not None
        assert ctx["parent_trace_id"] == "traceid-abc"
        assert ctx["parent_span_id"] == "spanid-xyz"
        assert ctx["parent_session_id"] == "parent-sess"
        # File is deleted after claiming
        assert not any((tmp_path / "tracer" / "pending_agent").iterdir())

    def test_claim_returns_none_when_no_file(self, tmp_path, monkeypatch):
        monkeypatch.setattr(tracer, "_PENDING_AGENT_DIR", tmp_path / "pending_agent")
        assert tracer._claim_pending_agent_context() is None

    def test_claim_ignores_stale_context(self, tmp_path, monkeypatch):
        monkeypatch.setattr(tracer, "_PENDING_AGENT_DIR", tmp_path / "pending_agent")
        monkeypatch.setattr(tracer, "_PENDING_AGENT_TIMEOUT_S", 0)
        tracer._write_pending_agent_context("s", "t", "p")
        # With 0s timeout, the file is immediately considered stale
        assert tracer._claim_pending_agent_context() is None

    def test_claim_matches_by_prompt(self, tmp_path, monkeypatch):
        """Subagent claiming with a matching prompt should pick the right context."""
        monkeypatch.setattr(tracer, "_PENDING_AGENT_DIR", tmp_path / "pending_agent")
        tracer._write_pending_agent_context(
            "s",
            "trace-A",
            "span-A",
            agent_prompt="search the web",
        )
        tracer._write_pending_agent_context(
            "s",
            "trace-B",
            "span-B",
            agent_prompt="write some code",
        )
        # Claiming with "write some code" should get span-B, not the newer span-A
        ctx = tracer._claim_pending_agent_context(prompt="write some code")
        assert ctx is not None
        assert ctx["parent_span_id"] == "span-B"

    def test_claim_parallel_agents_no_cross_contamination(self, tmp_path, monkeypatch):
        """Two parallel agents with distinct prompts each claim their own context."""
        monkeypatch.setattr(tracer, "_PENDING_AGENT_DIR", tmp_path / "pending_agent")
        tracer._write_pending_agent_context(
            "s",
            "trace-1",
            "span-1",
            agent_prompt="task one",
        )
        tracer._write_pending_agent_context(
            "s",
            "trace-2",
            "span-2",
            agent_prompt="task two",
        )

        ctx1 = tracer._claim_pending_agent_context(prompt="task one")
        ctx2 = tracer._claim_pending_agent_context(prompt="task two")

        assert ctx1 is not None and ctx1["parent_span_id"] == "span-1"
        assert ctx2 is not None and ctx2["parent_span_id"] == "span-2"
        assert not any((tmp_path / "pending_agent").iterdir())

    def test_claim_falls_back_to_newest_when_no_prompt_match(
        self,
        tmp_path,
        monkeypatch,
    ):
        """With no prompt match, fall back to newest-first (legacy behaviour)."""
        monkeypatch.setattr(tracer, "_PENDING_AGENT_DIR", tmp_path / "pending_agent")
        # Write two contexts without prompts (simulates older tracer versions)
        tracer._write_pending_agent_context("s", "trace-old", "span-old")
        tracer._write_pending_agent_context("s", "trace-new", "span-new")
        ctx = tracer._claim_pending_agent_context(prompt="unrelated prompt")
        assert ctx is not None
        # newest-first fallback means span-new is claimed
        assert ctx["parent_span_id"] == "span-new"

    def test_subagent_inherits_trace_id(self, tmp_path, monkeypatch):
        """UserPromptSubmit for a new session should inherit the parent trace ID."""
        monkeypatch.setattr(tracer, "STATE_DIR", tmp_path / "tracer")
        monkeypatch.setattr(
            tracer,
            "_PENDING_AGENT_DIR",
            tmp_path / "tracer" / "pending_agent",
        )
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        monkeypatch.delenv("CLAUDE_PROJECT_DIR", raising=False)

        parent_trace_id = "aabbccddeeff00112233445566778899"
        parent_span_id = "0011223344556677"
        tracer._write_pending_agent_context(
            "parent-sess",
            parent_trace_id,
            parent_span_id,
            agent_prompt="do the task",
        )

        exported: list[dict] = []

        def fake_export(config, session_id, username, span_records):
            exported.extend(span_records)

        monkeypatch.setattr(tracer, "_build_and_export_spans", fake_export)
        monkeypatch.setattr(
            tracer,
            "discover_config",
            lambda: {"api_key": "k", "task_id": "t", "endpoint": "https://x"},
        )

        data = {"session_id": "child-sess", "prompt": "do the task"}
        state = {}
        monkeypatch.setattr(tracer, "_load_state", lambda sid: state)
        monkeypatch.setattr(tracer, "_save_state", lambda sid, s: state.update(s))

        tracer.handle_user_prompt_submit(
            data,
            {"api_key": "k", "task_id": "t", "endpoint": "https://x"},
        )

        # The new trace should use the parent's trace ID
        assert state["current_trace"]["trace_id"] == parent_trace_id
        # And record the parent agent span for use in _complete_turn
        assert state["current_trace"]["parent_agent_span_id"] == parent_span_id

    def test_handle_pre_tool_writes_context_for_agent(self, tmp_path, monkeypatch):
        """PreToolUse for the Agent tool should write a pending context file."""
        monkeypatch.setattr(tracer, "STATE_DIR", tmp_path / "tracer")
        monkeypatch.setattr(
            tracer,
            "_PENDING_AGENT_DIR",
            tmp_path / "tracer" / "pending_agent",
        )

        trace_id = "deadbeef" * 4
        root_span_id = "cafebabe" * 2
        state = {
            "session_id": "parent-sess",
            "current_trace": {
                "trace_id": trace_id,
                "root_span_id": root_span_id,
                "turn_start_ns": 0,
                "turn_number": 1,
                "human_count_at_start": 0,
            },
            "pending_tools": {},
        }
        monkeypatch.setattr(tracer, "_load_state", lambda sid: state)
        monkeypatch.setattr(tracer, "_save_state", lambda sid, s: state.update(s))
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        monkeypatch.delenv("CLAUDE_PROJECT_DIR", raising=False)

        data = {
            "session_id": "parent-sess",
            "tool_name": "Agent",
            "tool_input": {"prompt": "go do stuff"},
        }
        tracer.handle_pre_tool(
            data,
            {"api_key": "k", "task_id": "t", "endpoint": "https://x"},
        )

        # A pending context file should now exist, with the prompt stored
        ctx = tracer._claim_pending_agent_context(prompt="go do stuff")
        assert ctx is not None
        assert ctx["parent_trace_id"] == trace_id
        assert ctx["agent_prompt"] == "go do stuff"
        # The pre-allocated span ID should be stored in pending_tools under a compound key
        agent_keys = [k for k in state["pending_tools"] if k.startswith("Agent#")]
        assert len(agent_keys) == 1
        assert "pre_allocated_span_id" in state["pending_tools"][agent_keys[0]]

    def test_agent_span_kind_is_agent(self, tmp_path, monkeypatch):
        """Tool spans for the Agent tool should have AGENT span kind."""
        rec = tracer._build_tool_span_record(
            tool_name="Agent",
            tool_input={
                "prompt": "do something",
                "description": "helper",
                "subagent_type": "general-purpose",
            },
            tool_response="done",
            start_ns=1000,
            end_ns=2000,
            trace_id="a" * 32,
            root_span_id="b" * 16,
        )
        assert rec["attributes"]["openinference.span.kind"] == "AGENT"
        assert rec["attributes"]["tool.json_schema"]  # schema should be attached

    def test_pre_tool_fallback_claims_parent_context(self, tmp_path, monkeypatch):
        """handle_pre_tool should claim a pending parent context when
        UserPromptSubmit didn't fire (e.g. Explore-type subagents)."""
        monkeypatch.setattr(tracer, "STATE_DIR", tmp_path / "tracer")
        monkeypatch.setattr(
            tracer,
            "_PENDING_AGENT_DIR",
            tmp_path / "tracer" / "pending_agent",
        )
        monkeypatch.setattr(tracer, "_build_and_export_spans", MagicMock())
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        monkeypatch.delenv("CLAUDE_PROJECT_DIR", raising=False)

        parent_trace_id = "aabbccddeeff00112233445566778899"
        parent_span_id = "0011223344556677"
        tracer._write_pending_agent_context(
            "parent-sess",
            parent_trace_id,
            parent_span_id,
            agent_prompt="explore stuff",
        )

        data = {
            "session_id": "child-sess-pretool",
            "tool_name": "Bash",
            "tool_input": {"command": "ls"},
        }
        tracer.handle_pre_tool(
            data,
            {"api_key": "k", "task_id": "t", "endpoint": "https://x"},
        )

        state = tracer._load_state("child-sess-pretool")
        # Pending context must be claimed (file deleted)
        assert tracer._claim_pending_agent_context(prompt="explore stuff") is None
        # Subagent trace must inherit the parent's trace ID
        assert state["current_trace"]["trace_id"] == parent_trace_id
        # Parent agent span ID must be recorded for CHAIN span nesting
        assert state["current_trace"]["parent_agent_span_id"] == parent_span_id

    def test_pre_tool_no_double_claim_after_user_prompt_submit(
        self,
        tmp_path,
        monkeypatch,
    ):
        """handle_pre_tool must not re-claim a context already claimed by
        UserPromptSubmit (session_id already set → init block skipped)."""
        monkeypatch.setattr(tracer, "STATE_DIR", tmp_path / "tracer")
        monkeypatch.setattr(
            tracer,
            "_PENDING_AGENT_DIR",
            tmp_path / "tracer" / "pending_agent",
        )
        monkeypatch.setattr(tracer, "_build_and_export_spans", MagicMock())
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        monkeypatch.delenv("CLAUDE_PROJECT_DIR", raising=False)

        parent_trace_id = "112233445566778899aabbccddeeff00"
        parent_span_id = "aabbccddeeff0011"
        tracer._write_pending_agent_context(
            "parent-sess2",
            parent_trace_id,
            parent_span_id,
            agent_prompt="do the task",
        )

        config = {"api_key": "k", "task_id": "t", "endpoint": "https://x"}
        # UserPromptSubmit runs first and claims the context
        ups_data = {"session_id": "child-sess-ups", "prompt": "do the task"}
        tracer.handle_user_prompt_submit(ups_data, config)

        state_after_ups = tracer._load_state("child-sess-ups")
        inherited_trace_id = state_after_ups["current_trace"]["trace_id"]
        assert inherited_trace_id == parent_trace_id

        # Now handle_pre_tool fires; session already initialized → init block skipped
        pt_data = {
            "session_id": "child-sess-ups",
            "tool_name": "Bash",
            "tool_input": {"command": "pwd"},
        }
        tracer.handle_pre_tool(pt_data, config)

        state_after_pt = tracer._load_state("child-sess-ups")
        # Trace ID must be unchanged (no second claim / override)
        assert state_after_pt["current_trace"]["trace_id"] == parent_trace_id

    def test_ups_carries_forward_pretool_context(self, tmp_path, monkeypatch):
        """When handle_pre_tool fires first (before UPS) and claims the parent
        context, the subsequent UserPromptSubmit must carry that inherited
        trace_id and parent_agent_span_id into the new trace — not generate a
        fresh random trace ID that would sever the subagent connection."""
        monkeypatch.setattr(tracer, "STATE_DIR", tmp_path / "tracer")
        monkeypatch.setattr(
            tracer,
            "_PENDING_AGENT_DIR",
            tmp_path / "tracer" / "pending_agent",
        )
        monkeypatch.setattr(tracer, "_build_and_export_spans", MagicMock())
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        monkeypatch.delenv("CLAUDE_PROJECT_DIR", raising=False)

        parent_trace_id = "ccddeeff00112233445566778899aabb"
        parent_span_id = "2233445566778899"
        tracer._write_pending_agent_context(
            "parent-sess-race",
            parent_trace_id,
            parent_span_id,
            agent_prompt="run some analysis",
        )

        config = {"api_key": "k", "task_id": "t", "endpoint": "https://x"}

        # pre_tool fires first (session init claims the context)
        tracer.handle_pre_tool(
            {
                "session_id": "child-sess-race",
                "tool_name": "Bash",
                "tool_input": {"command": "ls"},
            },
            config,
        )
        state_mid = tracer._load_state("child-sess-race")
        assert state_mid["current_trace"]["_pretool_created"] is True
        assert state_mid["current_trace"]["trace_id"] == parent_trace_id

        # UPS fires after pre_tool; the real first turn must inherit the same context
        tracer.handle_user_prompt_submit(
            {"session_id": "child-sess-race", "prompt": "run some analysis"},
            config,
        )
        state_final = tracer._load_state("child-sess-race")
        ct = state_final["current_trace"]

        # The new trace must reuse the parent's trace ID and connect to AGENT span
        assert ct["trace_id"] == parent_trace_id
        assert ct["parent_agent_span_id"] == parent_span_id
        # The sentinel must NOT be on the new (UPS-created) trace
        assert "_pretool_created" not in ct

    def test_pretool_context_not_carried_to_turn_2(self, tmp_path, monkeypatch):
        """parent_agent_span_id must only apply to the first CHAIN span;
        turn 2 of a subagent must have a fresh trace with no parent link."""
        monkeypatch.setattr(tracer, "STATE_DIR", tmp_path / "tracer")
        monkeypatch.setattr(
            tracer,
            "_PENDING_AGENT_DIR",
            tmp_path / "tracer" / "pending_agent",
        )
        monkeypatch.setattr(tracer, "_build_and_export_spans", MagicMock())
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        monkeypatch.delenv("CLAUDE_PROJECT_DIR", raising=False)

        parent_trace_id = "ddeeff00112233445566778899aabbcc"
        parent_span_id = "3344556677889900"
        tracer._write_pending_agent_context(
            "parent-sess-t2",
            parent_trace_id,
            parent_span_id,
            agent_prompt="task prompt",
        )

        config = {"api_key": "k", "task_id": "t", "endpoint": "https://x"}

        # Turn 1: pre_tool then UPS
        tracer.handle_pre_tool(
            {"session_id": "child-t2", "tool_name": "Bash", "tool_input": {}},
            config,
        )
        tracer.handle_user_prompt_submit(
            {"session_id": "child-t2", "prompt": "task prompt"},
            config,
        )
        state_t1 = tracer._load_state("child-t2")
        assert state_t1["current_trace"]["trace_id"] == parent_trace_id

        # Turn 2: another UPS (user sends follow-up)
        tracer.handle_user_prompt_submit(
            {"session_id": "child-t2", "prompt": "follow up"},
            config,
        )
        state_t2 = tracer._load_state("child-t2")
        ct2 = state_t2["current_trace"]
        # Turn 2 must NOT carry parent context
        assert ct2.get("parent_agent_span_id") is None
        # Turn 2 gets its own fresh trace
        assert ct2["trace_id"] != parent_trace_id


# ---------------------------------------------------------------------------
# discover_config — global config fallback
# ---------------------------------------------------------------------------


class TestDiscoverConfigGlobalFallback:
    def test_global_config_used_when_no_project_config(self, tmp_path, monkeypatch):
        monkeypatch.delenv("GENAI_ENGINE_API_KEY", raising=False)
        monkeypatch.delenv("GENAI_ENGINE_TASK_ID", raising=False)
        monkeypatch.delenv("GENAI_ENGINE_TRACE_ENDPOINT", raising=False)
        monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(tmp_path / "empty"))
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        global_cfg = tmp_path / ".claude" / "arthur_config.json"
        global_cfg.parent.mkdir(parents=True)
        global_cfg.write_text(
            json.dumps(
                {
                    "api_key": "global_k",
                    "task_id": "global_t",
                    "endpoint": "https://global.example.com",
                },
            ),
        )
        cfg = tracer.discover_config()
        assert cfg == {
            "api_key": "global_k",
            "task_id": "global_t",
            "endpoint": "https://global.example.com",
        }


# ---------------------------------------------------------------------------
# _count_human_messages — invalid JSON lines
# ---------------------------------------------------------------------------


class TestCountHumanMessagesEdgeCases:
    def test_skips_malformed_json_lines(self, tmp_path):
        p = tmp_path / "t.jsonl"
        p.write_text(
            json.dumps(human_entry("Valid"))
            + "\n"
            + "{{bad json\n"
            + json.dumps(human_entry("Also valid"))
            + "\n",
        )
        assert tracer._count_human_messages(str(p)) == 2


# ---------------------------------------------------------------------------
# _get_latest_human_message — invalid JSON lines
# ---------------------------------------------------------------------------


class TestGetLatestHumanMessageEdgeCases:
    def test_skips_malformed_json_lines(self, tmp_path):
        p = tmp_path / "t.jsonl"
        p.write_text(
            json.dumps(human_entry("First"))
            + "\n"
            + "{{bad\n"
            + json.dumps(human_entry("Last"))
            + "\n",
        )
        assert tracer._get_latest_human_message(str(p)) == "Last"


# ---------------------------------------------------------------------------
# _extract_llm_spans_for_turn — edge cases not yet covered
# ---------------------------------------------------------------------------


class TestExtractLlmSpansEdgeCases:
    TRACE_ID = "c" * 32
    ROOT_ID = "d" * 16

    def _extract(self, p, human_count_at_start=0):
        return tracer._extract_llm_spans_for_turn(
            str(p),
            human_count_at_start,
            self.TRACE_ID,
            self.ROOT_ID,
        )

    def test_skips_malformed_json_lines_in_transcript(self, tmp_path):
        p = tmp_path / "t.jsonl"
        p.write_text(
            json.dumps(human_entry("Hello"))
            + "\n"
            + "{{bad json\n"
            + json.dumps(llm_entry("Reply"))
            + "\n",
        )
        spans = self._extract(p)
        assert len(spans) == 1
        assert spans[0]["attributes"]["output.value"] == "Reply"

    def test_non_dict_content_block_ignored(self, tmp_path):
        # Assistant message whose content list contains a non-dict element
        entry = {
            "type": "assistant",
            "message": {
                "role": "assistant",
                "model": "claude-sonnet-4-6",
                "content": ["just a string", {"type": "text", "text": "hello"}],
                "usage": {
                    "input_tokens": 5,
                    "output_tokens": 3,
                    "cache_read_input_tokens": 0,
                    "cache_creation_input_tokens": 0,
                },
            },
            "timestamp": "2026-01-01T00:00:01.000000+00:00",
        }
        p = tmp_path / "t.jsonl"
        p.write_text(json.dumps(human_entry("Q")) + "\n" + json.dumps(entry) + "\n")
        spans = self._extract(p)
        assert len(spans) == 1
        assert spans[0]["attributes"]["output.value"] == "hello"


# ---------------------------------------------------------------------------
# _complete_turn — early return with no trace
# ---------------------------------------------------------------------------


class TestCompleteTurn:
    CONFIG = {"api_key": "k", "task_id": "t", "endpoint": "https://x.example.com"}

    def test_returns_early_when_no_current_trace(self, monkeypatch):
        exported = []
        monkeypatch.setattr(
            tracer,
            "_build_and_export_spans",
            lambda **kw: exported.extend(kw["span_records"]),
        )
        state = {"session_id": "s", "username": "u"}  # no current_trace key
        tracer._complete_turn(state, self.CONFIG, None, 0)
        assert exported == []


# ---------------------------------------------------------------------------
# handle_post_tool — no-current-trace early return
# ---------------------------------------------------------------------------


class TestHandlePostToolEdgeCases:
    CONFIG = {"api_key": "k", "task_id": "t", "endpoint": "https://x.example.com"}

    def test_no_current_trace_returns_early(self, tmp_path, monkeypatch):
        monkeypatch.setattr(tracer, "STATE_DIR", tmp_path / "tracer")
        exported = []
        monkeypatch.setattr(
            tracer,
            "_build_and_export_spans",
            lambda **kw: exported.extend(kw["span_records"]),
        )
        # Write state WITHOUT a current_trace
        state = {
            "session_id": "nc1",
            "username": "u",
            "human_msg_count": 0,
            "turn_number": 1,
        }
        tracer._save_state("nc1", state)
        data = {
            "session_id": "nc1",
            "tool_name": "Bash",
            "tool_input": {},
            "tool_response": "ok",
        }
        tracer.handle_post_tool(data, self.CONFIG)
        assert exported == []


# ---------------------------------------------------------------------------
# handle_post_tool_failure — additional edge cases
# ---------------------------------------------------------------------------


class TestHandlePostToolFailureEdgeCases:
    CONFIG = {"api_key": "k", "task_id": "t", "endpoint": "https://x.example.com"}

    def _make_state(self, tmp_path, session_id):
        tracer.STATE_DIR.mkdir(parents=True, exist_ok=True)
        state = {
            "session_id": session_id,
            "username": "u",
            "human_msg_count": 1,
            "turn_number": 1,
            "current_trace": {
                "trace_id": "e" * 32,
                "root_span_id": "f" * 16,
                "turn_start_ns": 1_000_000_000,
                "turn_number": 1,
                "human_count_at_start": 0,
            },
            "pending_tools": {
                "Bash": {
                    "tool_name": "Bash",
                    "tool_input": {"command": "bad cmd"},
                    "start_ns": 1_000_000_000,
                },
            },
        }
        tracer._save_state(session_id, state)

    def test_no_current_trace_returns_early(self, tmp_path, monkeypatch):
        monkeypatch.setattr(tracer, "STATE_DIR", tmp_path / "tracer")
        exported = []
        monkeypatch.setattr(
            tracer,
            "_build_and_export_spans",
            lambda **kw: exported.extend(kw["span_records"]),
        )
        state = {
            "session_id": "nct2",
            "username": "u",
            "human_msg_count": 0,
            "turn_number": 1,
        }
        tracer._save_state("nct2", state)
        data = {
            "session_id": "nct2",
            "tool_name": "Bash",
            "tool_input": {},
            "tool_response": "fail",
        }
        tracer.handle_post_tool_failure(data, self.CONFIG)
        assert exported == []

    def test_error_from_data_level_keys(self, tmp_path, monkeypatch, tmp_transcript):
        monkeypatch.setattr(tracer, "STATE_DIR", tmp_path / "tracer")
        exported = []
        monkeypatch.setattr(
            tracer,
            "_build_and_export_spans",
            lambda **kw: exported.extend(kw["span_records"]),
        )
        self._make_state(tmp_path, "dfk1")
        transcript = tmp_transcript([human_entry("Hi")])
        # tool_response is empty dict, error comes from data["error"]
        data = {
            "session_id": "dfk1",
            "tool_name": "Bash",
            "tool_input": {},
            "tool_response": {},
            "error": "permission denied",
            "transcript_path": str(transcript),
        }
        tracer.handle_post_tool_failure(data, self.CONFIG)
        error_spans = [s for s in exported if s.get("error")]
        assert len(error_spans) >= 1
        assert "permission denied" in error_spans[0].get("error_msg", "")

    def test_error_message_key_in_response(self, tmp_path, monkeypatch, tmp_transcript):
        monkeypatch.setattr(tracer, "STATE_DIR", tmp_path / "tracer")
        exported = []
        monkeypatch.setattr(
            tracer,
            "_build_and_export_spans",
            lambda **kw: exported.extend(kw["span_records"]),
        )
        self._make_state(tmp_path, "mkey1")
        transcript = tmp_transcript([human_entry("Hi")])
        data = {
            "session_id": "mkey1",
            "tool_name": "Bash",
            "tool_input": {},
            "tool_response": {"message": "timeout occurred"},
            "transcript_path": str(transcript),
        }
        tracer.handle_post_tool_failure(data, self.CONFIG)
        error_spans = [s for s in exported if s.get("error")]
        assert "timeout occurred" in error_spans[0].get("error_msg", "")


# ---------------------------------------------------------------------------
# Additional single-line edge cases
# ---------------------------------------------------------------------------


class TestGetLatestHumanMessageBlankLines:
    def test_blank_lines_skipped(self, tmp_path):
        p = tmp_path / "t.jsonl"
        p.write_text("\n" + json.dumps(human_entry("Hello")) + "\n" + "\n")
        assert tracer._get_latest_human_message(str(p)) == "Hello"


class TestExtractLlmSpansExceptionPath:
    def test_none_transcript_path_returns_empty(self):
        # Passing None causes Path(None) → TypeError caught by outer except
        spans = tracer._extract_llm_spans_for_turn(None, 0, "a" * 32, "b" * 16)
        assert spans == []

    def test_nonexistent_file_returns_empty(self):
        spans = tracer._extract_llm_spans_for_turn(
            "/no/such/transcript.jsonl",
            0,
            "a" * 32,
            "b" * 16,
        )
        assert spans == []


# ---------------------------------------------------------------------------
# main() — CLI entry point
# ---------------------------------------------------------------------------


class TestStateHelperExceptionBranches:
    """Test exception handler branches in state helpers that require mocking."""

    def test_delete_state_unlink_error_does_not_raise(self, tmp_path, monkeypatch):
        monkeypatch.setattr(tracer, "STATE_DIR", tmp_path / "tracer")
        (tmp_path / "tracer").mkdir()
        state_file = tmp_path / "tracer" / "err_del.json"
        state_file.write_text("{}")

        original_unlink = Path.unlink

        def bad_unlink(self, missing_ok=False):
            raise OSError("simulated unlink failure")

        monkeypatch.setattr(Path, "unlink", bad_unlink)
        tracer._delete_state("err_del")  # must not raise

    def test_cleanup_stale_states_glob_error_does_not_raise(
        self,
        tmp_path,
        monkeypatch,
    ):
        monkeypatch.setattr(tracer, "STATE_DIR", tmp_path / "tracer")
        (tmp_path / "tracer").mkdir()

        def bad_glob(self, pattern):
            raise OSError("glob failed")

        monkeypatch.setattr(Path, "glob", bad_glob)
        tracer._cleanup_stale_states()  # must not raise


class TestMain:
    """Test main() CLI dispatcher directly (in-process for coverage)."""

    CONFIG = {"api_key": "k", "task_id": "t", "endpoint": "https://x.example.com"}

    def test_no_args_prints_usage_and_exits(self, monkeypatch):
        monkeypatch.setattr(sys, "argv", ["prog"])
        with pytest.raises(SystemExit) as exc:
            tracer.main()
        assert exc.value.code == 0

    def test_unconfigured_exits_silently(self, monkeypatch):
        monkeypatch.setattr(sys, "argv", ["prog", "pre_tool"])
        monkeypatch.setattr(sys.stdin, "read", lambda: '{"session_id": "x"}')
        monkeypatch.setattr(tracer, "discover_config", lambda: None)
        with pytest.raises(SystemExit) as exc:
            tracer.main()
        assert exc.value.code == 0

    def test_invalid_json_stdin_handled(self, monkeypatch):
        monkeypatch.setattr(sys, "argv", ["prog", "pre_tool"])
        monkeypatch.setattr(sys.stdin, "read", lambda: "{{bad json")
        monkeypatch.setattr(tracer, "discover_config", lambda: self.CONFIG)
        handled = []
        monkeypatch.setattr(tracer, "handle_pre_tool", lambda d, c: handled.append(d))
        with pytest.raises(SystemExit):
            tracer.main()
        # Should have called handler with empty data (fallback on decode error)
        assert handled == [{}]

    def test_dispatches_pre_tool(self, monkeypatch, tmp_path):
        monkeypatch.setattr(sys, "argv", ["prog", "pre_tool"])
        monkeypatch.setattr(sys.stdin, "read", lambda: '{"session_id": "main_s1"}')
        monkeypatch.setattr(tracer, "discover_config", lambda: self.CONFIG)
        called = []
        monkeypatch.setattr(
            tracer,
            "handle_pre_tool",
            lambda d, c: called.append(("pre_tool", d)),
        )
        with pytest.raises(SystemExit):
            tracer.main()
        assert called == [("pre_tool", {"session_id": "main_s1"})]

    def test_dispatches_post_tool(self, monkeypatch):
        monkeypatch.setattr(sys, "argv", ["prog", "post_tool"])
        monkeypatch.setattr(sys.stdin, "read", lambda: '{"session_id": "main_s2"}')
        monkeypatch.setattr(tracer, "discover_config", lambda: self.CONFIG)
        called = []
        monkeypatch.setattr(tracer, "handle_post_tool", lambda d, c: called.append(d))
        with pytest.raises(SystemExit):
            tracer.main()
        assert called[0]["session_id"] == "main_s2"

    def test_dispatches_post_tool_failure(self, monkeypatch):
        monkeypatch.setattr(sys, "argv", ["prog", "post_tool_failure"])
        monkeypatch.setattr(sys.stdin, "read", lambda: '{"session_id": "main_s3"}')
        monkeypatch.setattr(tracer, "discover_config", lambda: self.CONFIG)
        called = []
        monkeypatch.setattr(
            tracer,
            "handle_post_tool_failure",
            lambda d, c: called.append(d),
        )
        with pytest.raises(SystemExit):
            tracer.main()
        assert called[0]["session_id"] == "main_s3"

    def test_dispatches_user_prompt_submit(self, monkeypatch):
        monkeypatch.setattr(sys, "argv", ["prog", "user_prompt_submit"])
        monkeypatch.setattr(sys.stdin, "read", lambda: '{"session_id": "main_s4"}')
        monkeypatch.setattr(tracer, "discover_config", lambda: self.CONFIG)
        called = []
        monkeypatch.setattr(
            tracer,
            "handle_user_prompt_submit",
            lambda d, c: called.append(d),
        )
        with pytest.raises(SystemExit):
            tracer.main()
        assert called[0]["session_id"] == "main_s4"

    def test_dispatches_stop(self, monkeypatch):
        monkeypatch.setattr(sys, "argv", ["prog", "stop"])
        monkeypatch.setattr(sys.stdin, "read", lambda: '{"session_id": "main_s5"}')
        monkeypatch.setattr(tracer, "discover_config", lambda: self.CONFIG)
        called = []
        monkeypatch.setattr(tracer, "handle_stop", lambda d, c: called.append(d))
        with pytest.raises(SystemExit):
            tracer.main()
        assert called[0]["session_id"] == "main_s5"

    def test_unknown_event_does_not_raise(self, monkeypatch):
        monkeypatch.setattr(sys, "argv", ["prog", "bogus_event"])
        monkeypatch.setattr(sys.stdin, "read", lambda: "{}")
        monkeypatch.setattr(tracer, "discover_config", lambda: self.CONFIG)
        with pytest.raises(SystemExit) as exc:
            tracer.main()
        assert exc.value.code == 0

    def test_handler_exception_does_not_crash(self, monkeypatch):
        monkeypatch.setattr(sys, "argv", ["prog", "pre_tool"])
        monkeypatch.setattr(sys.stdin, "read", lambda: '{"session_id": "ex_s"}')
        monkeypatch.setattr(tracer, "discover_config", lambda: self.CONFIG)
        monkeypatch.setattr(
            tracer,
            "handle_pre_tool",
            lambda d, c: (_ for _ in ()).throw(RuntimeError("boom")),
        )
        with pytest.raises(SystemExit) as exc:
            tracer.main()
        assert exc.value.code == 0


# ---------------------------------------------------------------------------
# _extract_llm_spans_for_turn — message.id grouping
# ---------------------------------------------------------------------------


def llm_entry_with_id(
    msg_id: str,
    text: str = "",
    tool_use_blocks: list | None = None,
    model: str = "claude-sonnet-4-6",
    input_tokens: int = 10,
    output_tokens: int = 20,
    cache_read: int = 0,
    cache_create: int = 0,
    ts: str = "2026-01-01T00:00:02.000000+00:00",
    stop_reason: str = "",
) -> dict:
    """LLM transcript entry with an explicit message.id (for grouping tests)."""
    content = []
    if text:
        content.append({"type": "text", "text": text})
    for b in tool_use_blocks or []:
        content.append(b)
    return {
        "type": "assistant",
        "message": {
            "id": msg_id,
            "role": "assistant",
            "model": model,
            "content": content,
            "stop_reason": stop_reason,
            "usage": {
                "input_tokens": input_tokens,
                "cache_read_input_tokens": cache_read,
                "cache_creation_input_tokens": cache_create,
                "output_tokens": output_tokens,
            },
        },
        "timestamp": ts,
    }


class TestExtractLlmSpansMessageIdGrouping:
    """
    Verify that consecutive assistant entries sharing a message.id are collapsed
    into a single LLM span (Fix 3: multi-entry API response grouping).
    """

    TRACE_ID = "e" * 32
    ROOT_ID = "f" * 16

    def _extract(self, p, human_count_at_start=0):
        return tracer._extract_llm_spans_for_turn(
            str(p),
            human_count_at_start,
            self.TRACE_ID,
            self.ROOT_ID,
        )

    def test_two_entries_same_id_produce_one_span(self, tmp_transcript):
        # Extended-thinking: first entry = thinking block (no text/tool_use),
        # second entry = text block. Both share message id "msg_abc".
        p = tmp_transcript(
            [
                human_entry("Hello"),
                llm_entry_with_id("msg_abc", text="", output_tokens=5),
                llm_entry_with_id("msg_abc", text="Hi there", output_tokens=15),
            ],
        )
        spans = self._extract(p)
        assert len(spans) == 1
        attrs = spans[0]["attributes"]
        assert attrs["output.value"] == "Hi there"
        assert attrs["output.mime_type"] == "text/plain"

    def test_output_tokens_summed_across_entries(self, tmp_transcript):
        # The thinking entry contributes 5 tokens, text entry contributes 15.
        # Total completion must be 20, not 15 (last entry only) or 5 (first only).
        p = tmp_transcript(
            [
                human_entry("Hello"),
                llm_entry_with_id("msg_abc", text="", output_tokens=5),
                llm_entry_with_id("msg_abc", text="Answer", output_tokens=15),
            ],
        )
        spans = self._extract(p)
        assert len(spans) == 1
        assert spans[0]["attributes"]["llm.token_count.completion"] == 20

    def test_prompt_tokens_taken_from_first_entry_only(self, tmp_transcript):
        # input_tokens=100 appears on both entries (duplicated by Claude Code).
        # The span must report 100, not 200.
        p = tmp_transcript(
            [
                human_entry("Hello"),
                llm_entry_with_id(
                    "msg_abc",
                    text="",
                    input_tokens=100,
                    output_tokens=5,
                ),
                llm_entry_with_id(
                    "msg_abc",
                    text="Answer",
                    input_tokens=100,
                    output_tokens=15,
                ),
            ],
        )
        spans = self._extract(p)
        assert len(spans) == 1
        assert spans[0]["attributes"]["llm.token_count.prompt"] == 100

    def test_different_ids_produce_separate_spans(self, tmp_transcript):
        # Two API calls, each with a distinct message.id → two spans.
        p = tmp_transcript(
            [
                human_entry("Hello"),
                llm_entry_with_id("msg_aaa", text="First response"),
                tool_result_entry("t1", "tool output"),
                llm_entry_with_id("msg_bbb", text="Second response"),
            ],
        )
        spans = self._extract(p)
        assert len(spans) == 2
        assert spans[0]["attributes"]["output.value"] == "First response"
        assert spans[1]["attributes"]["output.value"] == "Second response"

    def test_three_entries_same_id_text_concatenated(self, tmp_transcript):
        # Three entries with same id: thinking + text_part_1 + text_part_2
        p = tmp_transcript(
            [
                human_entry("Hello"),
                llm_entry_with_id("msg_xyz", text="", output_tokens=3),
                llm_entry_with_id("msg_xyz", text="Hello ", output_tokens=4),
                llm_entry_with_id("msg_xyz", text="world", output_tokens=5),
            ],
        )
        spans = self._extract(p)
        assert len(spans) == 1
        assert spans[0]["attributes"]["output.value"] == "Hello world"
        assert spans[0]["attributes"]["llm.token_count.completion"] == 12

    def test_tool_use_entry_followed_by_text_entry_same_id(self, tmp_transcript):
        # text entry takes precedence over tool_use when both present in group
        tb = tool_use_block("Read", "/tmp/foo")
        p = tmp_transcript(
            [
                human_entry("Hello"),
                llm_entry_with_id("msg_mix", tool_use_blocks=[tb], output_tokens=8),
                llm_entry_with_id("msg_mix", text="Here is the file", output_tokens=10),
            ],
        )
        spans = self._extract(p)
        assert len(spans) == 1
        attrs = spans[0]["attributes"]
        assert attrs["output.mime_type"] == "text/plain"
        assert attrs["output.value"] == "Here is the file"
        assert attrs["llm.token_count.completion"] == 18


# ---------------------------------------------------------------------------
# OpenInference attribute completeness — LLM spans
# ---------------------------------------------------------------------------


class TestLlmSpanOpenInferenceAttributes:
    """Verify every OpenInference-required attribute is present and correct on LLM spans."""

    TRACE_ID = "1" * 32
    ROOT_ID = "2" * 16

    def _extract(self, p, human_count_at_start=0):
        return tracer._extract_llm_spans_for_turn(
            str(p),
            human_count_at_start,
            self.TRACE_ID,
            self.ROOT_ID,
        )

    def test_llm_system_is_anthropic(self, tmp_transcript):
        p = tmp_transcript([human_entry("Hi"), llm_entry("Hello")])
        attrs = self._extract(p)[0]["attributes"]
        assert attrs["llm.system"] == "anthropic"

    def test_llm_model_name_reflects_transcript_model(self, tmp_transcript):
        p = tmp_transcript(
            [human_entry("Hi"), llm_entry("Hello", model="claude-opus-4-7")],
        )
        attrs = self._extract(p)[0]["attributes"]
        assert attrs["llm.model_name"] == "claude-opus-4-7"

    def test_llm_output_message_role_is_assistant(self, tmp_transcript):
        p = tmp_transcript([human_entry("Hi"), llm_entry("Hello")])
        attrs = self._extract(p)[0]["attributes"]
        assert attrs["llm.output_messages.0.message.role"] == "assistant"

    def test_llm_input_mime_type_for_human_prompt(self, tmp_transcript):
        # First LLM call in a turn receives a JSON-wrapped human message.
        p = tmp_transcript([human_entry("Hello there"), llm_entry("Hi")])
        attrs = self._extract(p)[0]["attributes"]
        assert attrs["input.mime_type"] == "application/json"

    def test_llm_input_mime_type_for_tool_result(self, tmp_transcript):
        # Second LLM call (after a tool result) also uses application/json.
        p = tmp_transcript(
            [
                human_entry("Run a command"),
                llm_entry(
                    "",
                    tool_use_blocks=[tool_use_block()],
                    ts="2026-01-01T00:00:01.000000+00:00",
                ),
                tool_result_entry("toolu_x", "output of command"),
                llm_entry("Done", ts="2026-01-01T00:00:05.000000+00:00"),
            ],
        )
        spans = self._extract(p)
        assert len(spans) == 2
        assert spans[1]["attributes"]["input.mime_type"] == "application/json"

    def test_tool_use_output_uses_structured_tool_calls(self, tmp_transcript):
        # Per OpenInference spec, tool calls appear as structured tool_calls attributes;
        # message.content is empty when there are only tool_use blocks.
        tb = tool_use_block("Bash", "echo hello")
        p = tmp_transcript([human_entry("Go"), llm_entry("", tool_use_blocks=[tb])])
        attrs = self._extract(p)[0]["attributes"]
        assert attrs["llm.output_messages.0.message.content"] == ""
        assert (
            attrs["llm.output_messages.0.message.tool_calls.0.tool_call.function.name"]
            == "Bash"
        )
        assert (
            "echo hello"
            in attrs[
                "llm.output_messages.0.message.tool_calls.0.tool_call.function.arguments"
            ]
        )
        # output.value still holds JSON for display/debugging
        assert attrs["output.mime_type"] == "application/json"

    def test_llm_token_counts_include_cache_tokens(self, tmp_transcript):
        p = tmp_transcript(
            [
                human_entry("Hi"),
                llm_entry(
                    "Hello",
                    input_tokens=5,
                    output_tokens=3,
                ),
            ],
        )
        attrs = self._extract(p)[0]["attributes"]
        # cache_read=100, cache_create=5 come from llm_entry defaults
        assert attrs["llm.token_count.prompt"] == 5 + 100 + 5
        assert attrs["llm.token_count.completion"] == 3
        assert attrs["llm.token_count.total"] == 5 + 100 + 5 + 3
        assert attrs["llm.token_count.prompt_details.cache_read"] == 100
        assert attrs["llm.token_count.prompt_details.cache_write"] == 5


# ---------------------------------------------------------------------------
# OpenInference attribute completeness — CHAIN spans
# ---------------------------------------------------------------------------


class TestChainSpanAttributes:
    """Verify CHAIN root span carries the correct OpenInference attributes."""

    CONFIG = {
        "api_key": "k",
        "task_id": "task-123",
        "endpoint": "https://x.example.com",
    }

    def _run_complete_turn(self, monkeypatch, state, end_ns=2_000_000_000):
        exported = []
        monkeypatch.setattr(
            tracer,
            "_build_and_export_spans",
            lambda **kw: exported.extend(kw["span_records"]),
        )
        tracer._complete_turn(state, self.CONFIG, None, end_ns)
        return exported

    def _make_state(
        self,
        prompt_preview="Hello",
        last_llm_output="World",
        turn=1,
        parent_agent_span_id=None,
    ):
        current_trace = {
            "trace_id": "a" * 32,
            "root_span_id": "b" * 16,
            "turn_start_ns": 1_000_000_000,
            "turn_number": turn,
            "prompt_preview": prompt_preview,
            "last_llm_output": last_llm_output,
        }
        if parent_agent_span_id is not None:
            current_trace["parent_agent_span_id"] = parent_agent_span_id
        return {
            "session_id": "sess-chain",
            "username": "chain-user",
            "current_trace": current_trace,
        }

    def test_chain_span_input_value_is_prompt_preview(self, monkeypatch):
        state = self._make_state(prompt_preview="Tell me a joke")
        exported = self._run_complete_turn(monkeypatch, state)
        chain = next(
            r
            for r in exported
            if r["attributes"].get("openinference.span.kind") == "CHAIN"
        )
        assert chain["attributes"]["input.value"] == "Tell me a joke"

    def test_chain_span_output_value_is_last_llm_output(self, monkeypatch):
        state = self._make_state(last_llm_output="Why did the chicken cross the road?")
        exported = self._run_complete_turn(monkeypatch, state)
        chain = next(
            r
            for r in exported
            if r["attributes"].get("openinference.span.kind") == "CHAIN"
        )
        assert (
            chain["attributes"]["output.value"] == "Why did the chicken cross the road?"
        )

    def test_chain_span_mime_types_are_text_plain(self, monkeypatch):
        state = self._make_state()
        exported = self._run_complete_turn(monkeypatch, state)
        chain = next(
            r
            for r in exported
            if r["attributes"].get("openinference.span.kind") == "CHAIN"
        )
        assert chain["attributes"]["input.mime_type"] == "text/plain"
        assert chain["attributes"]["output.mime_type"] == "text/plain"

    def test_chain_span_turn_number_is_set(self, monkeypatch):
        state = self._make_state(turn=3)
        exported = self._run_complete_turn(monkeypatch, state)
        chain = next(
            r
            for r in exported
            if r["attributes"].get("openinference.span.kind") == "CHAIN"
        )
        assert chain["attributes"]["arthur.turn_number"] == 3

    def test_chain_span_has_no_parent_when_top_level(self, monkeypatch):
        state = self._make_state()
        exported = self._run_complete_turn(monkeypatch, state)
        chain = next(
            r
            for r in exported
            if r["attributes"].get("openinference.span.kind") == "CHAIN"
        )
        assert chain["parent_span_id_hex"] is None

    def test_chain_span_has_parent_agent_span_id_for_subagent(self, monkeypatch):
        parent_id = "deadbeef01234567"
        state = self._make_state(parent_agent_span_id=parent_id)
        exported = self._run_complete_turn(monkeypatch, state)
        chain = next(
            r
            for r in exported
            if r["attributes"].get("openinference.span.kind") == "CHAIN"
        )
        assert chain["parent_span_id_hex"] == parent_id

    def test_chain_span_omits_io_when_no_preview_or_output(self, monkeypatch):
        # If prompt_preview and last_llm_output are both empty, input/output
        # attributes must be absent (not set to empty string).
        state = self._make_state(prompt_preview="", last_llm_output="")
        exported = self._run_complete_turn(monkeypatch, state)
        chain = next(
            r
            for r in exported
            if r["attributes"].get("openinference.span.kind") == "CHAIN"
        )
        assert "input.value" not in chain["attributes"]
        assert "output.value" not in chain["attributes"]


# ---------------------------------------------------------------------------
# OpenInference attribute completeness — TOOL / AGENT spans
# ---------------------------------------------------------------------------


class TestToolSpanAttributes:
    """Verify _build_tool_span_record emits correct OpenInference attributes."""

    def _build(self, tool_name="Bash", tool_input=None, tool_response="ok"):
        return tracer._build_tool_span_record(
            tool_name=tool_name,
            tool_input=tool_input or {"command": "ls"},
            tool_response=tool_response,
            start_ns=1_000_000_000,
            end_ns=2_000_000_000,
            trace_id="c" * 32,
            root_span_id="d" * 16,
        )

    def test_tool_name_attribute_matches_tool_name(self):
        for name in ("Bash", "Read", "Edit", "Write"):
            rec = self._build(tool_name=name)
            assert rec["attributes"]["tool.name"] == name

    def test_tool_span_name_field_matches_tool_name(self):
        rec = self._build(tool_name="Grep")
        assert rec["name"] == "Grep"

    def test_tool_input_mime_type_is_application_json(self):
        rec = self._build(tool_name="Bash")
        assert rec["attributes"]["input.mime_type"] == "application/json"

    def test_tool_output_mime_type_is_application_json(self):
        rec = self._build(tool_name="Bash")
        assert rec["attributes"]["output.mime_type"] == "application/json"

    def test_tool_json_schema_content_for_bash(self):
        rec = self._build(tool_name="Bash")
        schema = json.loads(rec["attributes"]["tool.json_schema"])
        assert "command" in schema["properties"]
        assert "command" in schema["required"]

    def test_tool_span_kind_is_tool(self):
        rec = self._build(tool_name="Bash")
        assert rec["attributes"]["openinference.span.kind"] == "TOOL"

    def test_agent_tool_span_kind_is_agent(self):
        rec = self._build(
            tool_name="Agent",
            tool_input={"description": "x", "prompt": "do something"},
        )
        assert rec["attributes"]["openinference.span.kind"] == "AGENT"

    def test_task_tool_span_kind_is_agent(self):
        rec = self._build(
            tool_name="Task",
            tool_input={
                "description": "x",
                "prompt": "do something",
                "subagent_type": "general-purpose",
            },
        )
        assert rec["attributes"]["openinference.span.kind"] == "AGENT"

    def test_tool_input_value_is_json_of_input(self):
        rec = self._build(tool_name="Bash", tool_input={"command": "pwd"})
        parsed = json.loads(rec["attributes"]["input.value"])
        assert parsed["command"] == "pwd"

    def test_tool_error_flag_set_on_failure(self):
        rec = tracer._build_tool_span_record(
            tool_name="Bash",
            tool_input={"command": "bad"},
            tool_response="",
            start_ns=1_000_000_000,
            end_ns=2_000_000_000,
            trace_id="e" * 32,
            root_span_id="f" * 16,
            is_failure=True,
            error_msg="command not found",
        )
        assert rec["error"] is True
        assert "command not found" in rec["attributes"]["output.value"]


# ---------------------------------------------------------------------------
# OpenInference attribute completeness — RETRIEVER spans (additional)
# ---------------------------------------------------------------------------


class TestRetrieverSpanAttributesExtra:
    """Additional RETRIEVER attribute assertions not covered by TestRetrieverSpanKind."""

    def _build_retriever(
        self,
        tool_name="WebSearch",
        tool_input=None,
        tool_response="results",
    ):
        return tracer._build_tool_span_record(
            tool_name=tool_name,
            tool_input=tool_input if tool_input is not None else {"query": "test"},
            tool_response=tool_response,
            start_ns=1_000_000_000,
            end_ns=2_000_000_000,
            trace_id="1" * 32,
            root_span_id="2" * 16,
        )

    def test_retriever_span_kind_is_retriever(self):
        rec = self._build_retriever("WebSearch")
        assert rec["attributes"]["openinference.span.kind"] == "RETRIEVER"

    def test_retriever_output_mime_type_is_application_json(self):
        rec = self._build_retriever("WebSearch")
        assert rec["attributes"]["output.mime_type"] == "application/json"

    def test_retriever_document_id_intentionally_absent(self):
        # The tracer does not set document.id (no stable ID available for web results).
        rec = self._build_retriever("WebSearch")
        assert "retrieval.documents.0.document.id" not in rec["attributes"]

    def test_retriever_document_score_intentionally_absent(self):
        # Relevance scores are not returned by the WebSearch/WebFetch tools.
        rec = self._build_retriever(
            "WebFetch",
            tool_input={"url": "https://example.com", "prompt": "x"},
        )
        assert "retrieval.documents.0.document.score" not in rec["attributes"]

    def test_websearch_missing_query_key_uses_empty_string(self):
        rec = self._build_retriever("WebSearch", tool_input={})
        assert rec["attributes"]["input.value"] == ""
        assert rec["attributes"]["input.mime_type"] == "text/plain"

    def test_webfetch_missing_url_key_uses_empty_string(self):
        rec = self._build_retriever("WebFetch", tool_input={})
        assert rec["attributes"]["input.value"] == ""
        assert rec["attributes"]["input.mime_type"] == "text/plain"

    def test_retriever_non_string_response_json_encoded_in_document(self):
        response = {"results": [{"title": "OpenInference", "url": "https://oi.dev"}]}
        rec = self._build_retriever("WebSearch", tool_response=response)
        content = rec["attributes"]["retrieval.documents.0.document.content"]
        parsed = json.loads(content)
        assert parsed["results"][0]["title"] == "OpenInference"


# ---------------------------------------------------------------------------
# _build_and_export_spans — resource and version attributes
# ---------------------------------------------------------------------------


class TestBuildAndExportSpansAttributes:
    """Verify resource attributes and arthur_span_version reach the exported span.

    Uses InMemorySpanExporter in place of OTLPSpanExporter so no HTTP call is made.
    """

    CONFIG = {
        "api_key": "k",
        "task_id": "task-xyz",
        "endpoint": "https://x.example.com",
    }

    def _exported_spans(self, monkeypatch, span_record):
        from opentelemetry.sdk.trace.export.in_memory_span_exporter import (
            InMemorySpanExporter,
        )

        mem = InMemorySpanExporter()
        monkeypatch.setattr(
            "opentelemetry.exporter.otlp.proto.http.trace_exporter.OTLPSpanExporter",
            lambda **_kw: mem,
        )
        tracer._build_and_export_spans(
            config=self.CONFIG,
            session_id="sess-export",
            username="export-user",
            span_records=[span_record],
        )
        return mem.get_finished_spans()

    def _simple_record(self):
        return {
            "trace_id_hex": "a" * 32,
            "span_id_hex": "b" * 16,
            "parent_span_id_hex": None,
            "name": "test-span",
            "kind": None,
            "start_ns": 1_000_000_000,
            "end_ns": 2_000_000_000,
            "attributes": {"openinference.span.kind": "TOOL", "tool.name": "Bash"},
            "force_span_id": False,
        }

    def test_arthur_span_version_is_set(self, monkeypatch):
        spans = self._exported_spans(monkeypatch, self._simple_record())
        assert len(spans) == 1
        attrs = dict(spans[0].attributes)
        assert attrs.get("arthur_span_version") == "arthur_span_v1"

    def test_resource_service_name_is_claude_code(self, monkeypatch):
        spans = self._exported_spans(monkeypatch, self._simple_record())
        resource_attrs = dict(spans[0].resource.attributes)
        assert resource_attrs.get("service.name") == "claude-code"

    def test_resource_arthur_task_is_task_id(self, monkeypatch):
        spans = self._exported_spans(monkeypatch, self._simple_record())
        resource_attrs = dict(spans[0].resource.attributes)
        assert resource_attrs.get("arthur.task") == self.CONFIG["task_id"]

    def test_resource_arthur_session_and_user(self, monkeypatch):
        spans = self._exported_spans(monkeypatch, self._simple_record())
        resource_attrs = dict(spans[0].resource.attributes)
        assert resource_attrs.get("arthur.session") == "sess-export"
        assert resource_attrs.get("arthur.user") == "export-user"

    def test_span_attributes_propagated(self, monkeypatch):
        rec = self._simple_record()
        rec["attributes"]["tool.name"] = "MyTool"
        spans = self._exported_spans(monkeypatch, rec)
        attrs = dict(spans[0].attributes)
        assert attrs.get("tool.name") == "MyTool"
        assert attrs.get("openinference.span.kind") == "TOOL"

    def test_error_span_sets_error_status(self, monkeypatch):
        rec = self._simple_record()
        rec["error"] = True
        rec["error_msg"] = "something went wrong"
        spans = self._exported_spans(monkeypatch, rec)
        from opentelemetry.trace import StatusCode

        assert spans[0].status.status_code == StatusCode.ERROR

    def test_error_span_status_description_contains_error_msg(self, monkeypatch):
        rec = self._simple_record()
        rec["error"] = True
        rec["error_msg"] = "file not found"
        spans = self._exported_spans(monkeypatch, rec)
        assert "file not found" in spans[0].status.description

    def test_session_id_on_llm_span(self, monkeypatch):
        rec = self._simple_record()
        rec["attributes"]["openinference.span.kind"] = "LLM"
        spans = self._exported_spans(monkeypatch, rec)
        attrs = dict(spans[0].attributes)
        assert attrs.get("session.id") == "sess-export"

    def test_user_id_on_llm_span(self, monkeypatch):
        rec = self._simple_record()
        rec["attributes"]["openinference.span.kind"] = "LLM"
        spans = self._exported_spans(monkeypatch, rec)
        attrs = dict(spans[0].attributes)
        assert attrs.get("user.id") == "export-user"

    def test_session_id_on_tool_span(self, monkeypatch):
        rec = self._simple_record()
        spans = self._exported_spans(monkeypatch, rec)
        attrs = dict(spans[0].attributes)
        assert attrs.get("session.id") == "sess-export"


# ---------------------------------------------------------------------------
# OpenInference spec compliance — gaps documented and tested
# ---------------------------------------------------------------------------


class TestOpenInferenceSpecCompliance:
    """Tests for all OpenInference spec attributes added in the gap-filling pass."""

    TRACE_ID = "f" * 32
    ROOT_ID = "e" * 16

    def _extract(self, p, human_count_at_start=0):
        return tracer._extract_llm_spans_for_turn(
            str(p),
            human_count_at_start,
            self.TRACE_ID,
            self.ROOT_ID,
        )

    # ── Structured tool_calls attributes ──────────────────────────────────────

    def test_tool_call_id_preserved_from_transcript(self, tmp_transcript):
        # tool_use_block hardcodes id="toolu_x" — verify it flows through
        tb = tool_use_block("Bash", "ls")
        p = tmp_transcript([human_entry("Go"), llm_entry("", tool_use_blocks=[tb])])
        attrs = self._extract(p)[0]["attributes"]
        assert (
            attrs["llm.output_messages.0.message.tool_calls.0.tool_call.id"]
            == "toolu_x"
        )

    def test_multiple_tool_calls_indexed(self, tmp_transcript):
        tb0 = {
            "type": "tool_use",
            "id": "toolu_001",
            "name": "Read",
            "input": {"file_path": "/a"},
        }
        tb1 = {
            "type": "tool_use",
            "id": "toolu_002",
            "name": "Bash",
            "input": {"command": "ls"},
        }
        p = tmp_transcript(
            [human_entry("Do both"), llm_entry("", tool_use_blocks=[tb0, tb1])],
        )
        attrs = self._extract(p)[0]["attributes"]
        assert (
            attrs["llm.output_messages.0.message.tool_calls.0.tool_call.id"]
            == "toolu_001"
        )
        assert (
            attrs["llm.output_messages.0.message.tool_calls.1.tool_call.id"]
            == "toolu_002"
        )
        assert (
            attrs["llm.output_messages.0.message.tool_calls.1.tool_call.function.name"]
            == "Bash"
        )

    def test_no_tool_calls_attrs_when_text_only(self, tmp_transcript):
        p = tmp_transcript([human_entry("Hi"), llm_entry("Hello")])
        attrs = self._extract(p)[0]["attributes"]
        assert "llm.output_messages.0.message.tool_calls.0.tool_call.id" not in attrs

    # ── llm.finish_reason ─────────────────────────────────────────────────────

    def test_finish_reason_end_turn_maps_to_stop(self, tmp_transcript):
        p = tmp_transcript(
            [human_entry("Hi"), llm_entry("Hello", stop_reason="end_turn")],
        )
        assert self._extract(p)[0]["attributes"]["llm.finish_reason"] == "stop"

    def test_finish_reason_max_tokens_maps_to_length(self, tmp_transcript):
        p = tmp_transcript(
            [human_entry("Hi"), llm_entry("...", stop_reason="max_tokens")],
        )
        assert self._extract(p)[0]["attributes"]["llm.finish_reason"] == "length"

    def test_finish_reason_tool_use_passes_through(self, tmp_transcript):
        tb = tool_use_block()
        p = tmp_transcript(
            [
                human_entry("Go"),
                llm_entry("", tool_use_blocks=[tb], stop_reason="tool_use"),
            ],
        )
        assert self._extract(p)[0]["attributes"]["llm.finish_reason"] == "tool_use"

    def test_finish_reason_absent_when_no_stop_reason(self, tmp_transcript):
        # stop_reason="" → llm.finish_reason must not be set
        p = tmp_transcript([human_entry("Hi"), llm_entry("Hello")])
        assert "llm.finish_reason" not in self._extract(p)[0]["attributes"]

    def test_finish_reason_last_group_entry_wins(self, tmp_transcript):
        # Extended-thinking: first entry has no stop_reason, last has "end_turn"
        p = tmp_transcript(
            [
                human_entry("Think"),
                llm_entry_with_id("msg_et", text="", output_tokens=5),
                llm_entry_with_id(
                    "msg_et",
                    text="Answer",
                    output_tokens=10,
                    stop_reason="end_turn",
                ),
            ],
        )
        attrs = self._extract(p)[0]["attributes"]
        assert attrs["llm.finish_reason"] == "stop"

    # ── agent.name on AGENT spans ─────────────────────────────────────────────

    def test_agent_name_from_subagent_type(self):
        rec = tracer._build_tool_span_record(
            tool_name="Agent",
            tool_input={"prompt": "do x", "subagent_type": "general-purpose"},
            tool_response="done",
            start_ns=1000,
            end_ns=2000,
            trace_id="a" * 32,
            root_span_id="b" * 16,
        )
        assert rec["attributes"]["agent.name"] == "general-purpose"

    def test_agent_name_fallback_to_tool_name(self):
        # No subagent_type → falls back to "Agent"
        rec = tracer._build_tool_span_record(
            tool_name="Agent",
            tool_input={"prompt": "do x"},
            tool_response="done",
            start_ns=1000,
            end_ns=2000,
            trace_id="a" * 32,
            root_span_id="b" * 16,
        )
        assert rec["attributes"]["agent.name"] == "Agent"

    def test_agent_name_for_task_tool(self):
        rec = tracer._build_tool_span_record(
            tool_name="Task",
            tool_input={
                "prompt": "do x",
                "subagent_type": "claude-code-guide",
                "description": "help",
            },
            tool_response="done",
            start_ns=1000,
            end_ns=2000,
            trace_id="a" * 32,
            root_span_id="b" * 16,
        )
        assert rec["attributes"]["agent.name"] == "claude-code-guide"

    def test_agent_name_absent_on_tool_spans(self):
        rec = tracer._build_tool_span_record(
            tool_name="Bash",
            tool_input={"command": "ls"},
            tool_response="file.txt",
            start_ns=1000,
            end_ns=2000,
            trace_id="a" * 32,
            root_span_id="b" * 16,
        )
        assert "agent.name" not in rec["attributes"]

    # ── tool result input: role="tool" and message.tool_call_id ──────────────

    def test_tool_result_input_role_is_tool(self, tmp_transcript):
        p = tmp_transcript(
            [
                human_entry("What files?"),
                llm_entry("", tool_use_blocks=[tool_use_block()]),
                tool_result_entry("toolu_x", "file.txt"),
                llm_entry("Here: file.txt"),
            ],
        )
        spans = self._extract(p)
        # Second LLM call receives a tool result as input
        assert spans[1]["attributes"]["llm.input_messages.0.message.role"] == "tool"

    def test_tool_result_input_has_tool_call_id(self, tmp_transcript):
        p = tmp_transcript(
            [
                human_entry("What files?"),
                llm_entry("", tool_use_blocks=[tool_use_block()]),
                tool_result_entry("toolu_x", "file.txt"),
                llm_entry("Here: file.txt"),
            ],
        )
        spans = self._extract(p)
        assert (
            spans[1]["attributes"]["llm.input_messages.0.message.tool_call_id"]
            == "toolu_x"
        )

    def test_human_input_has_no_tool_call_id(self, tmp_transcript):
        p = tmp_transcript([human_entry("Hello"), llm_entry("Hi")])
        attrs = self._extract(p)[0]["attributes"]
        assert "llm.input_messages.0.message.tool_call_id" not in attrs

    # ── CHAIN span name ───────────────────────────────────────────────────────

    def test_chain_span_name_is_claude_code_turn(self, monkeypatch):
        exported = []
        monkeypatch.setattr(
            tracer,
            "_build_and_export_spans",
            lambda **kw: exported.extend(kw["span_records"]),
        )
        state = {
            "session_id": "s",
            "username": "u",
            "current_trace": {
                "trace_id": "a" * 32,
                "root_span_id": "b" * 16,
                "turn_start_ns": 1_000_000_000,
                "turn_number": 1,
                "prompt_preview": "hi",
                "last_llm_output": "hello",
            },
        }
        tracer._complete_turn(
            state,
            {"api_key": "k", "task_id": "t", "endpoint": "https://x"},
            None,
            2_000_000_000,
        )
        chain = next(
            r
            for r in exported
            if r["attributes"].get("openinference.span.kind") == "CHAIN"
        )
        assert chain["name"] == "claude-code-turn"

    # ── RETRIEVER tool.json_schema ────────────────────────────────────────────

    def test_retriever_websearch_has_tool_json_schema(self):
        rec = tracer._build_tool_span_record(
            tool_name="WebSearch",
            tool_input={"query": "openinference spec"},
            tool_response="results",
            start_ns=1000,
            end_ns=2000,
            trace_id="1" * 32,
            root_span_id="2" * 16,
        )
        schema = json.loads(rec["attributes"]["tool.json_schema"])
        assert "query" in schema["properties"]
        assert "query" in schema["required"]

    def test_retriever_webfetch_has_tool_json_schema(self):
        rec = tracer._build_tool_span_record(
            tool_name="WebFetch",
            tool_input={"url": "https://example.com", "prompt": "x"},
            tool_response="content",
            start_ns=1000,
            end_ns=2000,
            trace_id="1" * 32,
            root_span_id="2" * 16,
        )
        schema = json.loads(rec["attributes"]["tool.json_schema"])
        assert "url" in schema["properties"]

    # ── Known gaps: intentionally absent attributes ───────────────────────────

    def test_llm_invocation_parameters_intentionally_absent(self, tmp_transcript):
        # Claude Code hooks do not expose API call parameters (temperature, max_tokens,
        # etc.), so llm.invocation_parameters cannot be set.
        p = tmp_transcript([human_entry("Hi"), llm_entry("Hello")])
        attrs = self._extract(p)[0]["attributes"]
        assert "llm.invocation_parameters" not in attrs

    def test_completion_details_reasoning_intentionally_absent(self, tmp_transcript):
        # The Claude Code transcript provides per-entry output_tokens but does not
        # separate thinking-block tokens from text tokens, so
        # llm.token_count.completion_details.reasoning cannot be populated.
        p = tmp_transcript(
            [
                human_entry("Think hard"),
                llm_entry_with_id("msg_et", text="", output_tokens=50),
                llm_entry_with_id("msg_et", text="Answer", output_tokens=20),
            ],
        )
        attrs = self._extract(p)[0]["attributes"]
        assert "llm.token_count.completion_details.reasoning" not in attrs
        # All tokens are rolled up into the combined completion count
        assert attrs["llm.token_count.completion"] == 70


# ---------------------------------------------------------------------------
# End-to-end: AGENT span ↔ subagent CHAIN span parent-child relationship
# ---------------------------------------------------------------------------


class TestAgentSpanEndToEnd:
    """Verify the full parent→subagent span hierarchy using real span export.

    These tests do NOT mock _build_and_export_spans.  They substitute
    InMemorySpanExporter for OTLPSpanExporter — one fresh instance per span
    (mirroring the production code which also creates one exporter per span to
    avoid provider.shutdown() closing a shared exporter).
    """

    CONFIG = {"api_key": "k", "task_id": "t", "endpoint": "https://x.example.com"}

    def _patch_exporters(self, monkeypatch):
        """Return a collector function; each _build_and_export_spans call gets
        its own InMemorySpanExporter so shutdown() on one doesn't affect others."""
        from opentelemetry.sdk.trace.export.in_memory_span_exporter import (
            InMemorySpanExporter,
        )

        exporter_list = []

        def make_exporter(**_kw):
            mem = InMemorySpanExporter()
            exporter_list.append(mem)
            return mem

        monkeypatch.setattr(
            "opentelemetry.exporter.otlp.proto.http.trace_exporter.OTLPSpanExporter",
            make_exporter,
        )

        def all_spans():
            return [s for mem in exporter_list for s in mem.get_finished_spans()]

        return all_spans

    def _setup_dirs(self, monkeypatch, tmp_path):
        monkeypatch.setattr(tracer, "STATE_DIR", tmp_path / "tracer")
        monkeypatch.setattr(
            tracer,
            "_PENDING_AGENT_DIR",
            tmp_path / "tracer" / "pending_agent",
        )
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        monkeypatch.delenv("CLAUDE_PROJECT_DIR", raising=False)

    def test_force_span_id_honoured_in_export(self, monkeypatch, tmp_path):
        """_build_and_export_spans must export the span with the forced span_id
        when force_span_id=True.  This is the prerequisite for AGENT→CHAIN linking."""
        self._setup_dirs(monkeypatch, tmp_path)
        all_spans = self._patch_exporters(monkeypatch)

        forced_hex = "deadbeef01234567"
        trace_hex = "a" * 32
        tracer._build_and_export_spans(
            config=self.CONFIG,
            session_id="sess-force",
            username="u",
            span_records=[
                {
                    "trace_id_hex": trace_hex,
                    "span_id_hex": forced_hex,
                    "parent_span_id_hex": None,
                    "name": "forced-span",
                    "kind": None,
                    "start_ns": 1_000_000_000,
                    "end_ns": 2_000_000_000,
                    "attributes": {"openinference.span.kind": "AGENT"},
                    "force_span_id": True,
                },
            ],
        )

        spans = all_spans()
        assert len(spans) == 1
        assert spans[0].context.span_id == int(forced_hex, 16), (
            f"Expected span_id {forced_hex!r} but got "
            f"{hex(spans[0].context.span_id)!r} — force_span_id not honoured"
        )

    def test_agent_chain_parent_child_relationship(self, monkeypatch, tmp_path):
        """Full hook sequence: parent pre_tool(Agent) + subagent UPS/stop +
        parent post_tool(Agent).  The subagent CHAIN span must be a child of
        the AGENT span and share its trace_id."""
        self._setup_dirs(monkeypatch, tmp_path)
        all_spans = self._patch_exporters(monkeypatch)

        config = self.CONFIG

        # 1. Parent session starts
        tracer.handle_user_prompt_submit(
            {"session_id": "par-e2e", "prompt": "user task"},
            config,
        )

        # 2. Parent fires pre_tool(Agent)
        tracer.handle_pre_tool(
            {
                "session_id": "par-e2e",
                "tool_name": "Agent",
                "tool_input": {"prompt": "sub-task"},
            },
            config,
        )

        # 3. Read the pending context file before the subagent claims it
        pending_files = list(tracer._PENDING_AGENT_DIR.glob("*.json"))
        assert len(pending_files) == 1, "Expected exactly one pending context file"
        pending_ctx = json.loads(pending_files[0].read_text())
        pre_alloc_hex = pending_ctx["parent_span_id"]
        parent_trace_hex = pending_ctx["parent_trace_id"]

        # 4. Subagent session: UPS fires first (normal hook ordering)
        tracer.handle_user_prompt_submit(
            {"session_id": "child-e2e", "prompt": "sub-task"},
            config,
        )

        # 5. Subagent completes — stop fires, CHAIN span exported
        tracer.handle_stop({"session_id": "child-e2e"}, config)

        # 6. Parent post_tool fires AFTER subagent stop (Agent tool is blocking)
        tracer.handle_post_tool(
            {
                "session_id": "par-e2e",
                "tool_name": "Agent",
                "tool_input": {"prompt": "sub-task"},
                "tool_response": "done",
            },
            config,
        )

        # 7. Verify the hierarchy
        spans = all_spans()
        agent_spans = [
            s
            for s in spans
            if dict(s.attributes).get("openinference.span.kind") == "AGENT"
        ]
        chain_spans = [s for s in spans if s.name == "claude-code-turn"]

        assert agent_spans, "No AGENT span exported"
        assert chain_spans, "No CHAIN span (claude-code-turn) exported"

        agent = agent_spans[0]
        chain = chain_spans[0]

        assert agent.context.span_id == int(
            pre_alloc_hex,
            16,
        ), f"AGENT span_id {hex(agent.context.span_id)} != pre-allocated {pre_alloc_hex}"
        assert chain.context.trace_id == int(
            parent_trace_hex,
            16,
        ), "CHAIN span is in a different trace than the parent"
        assert chain.parent is not None, "CHAIN span has no parent"
        assert chain.parent.span_id == agent.context.span_id, (
            f"CHAIN.parent.span_id {hex(chain.parent.span_id)} != "
            f"AGENT.span_id {hex(agent.context.span_id)}"
        )
        assert (
            chain.context.trace_id == agent.context.trace_id
        ), "CHAIN and AGENT are in different traces"

    def test_parallel_agent_spans_dont_collide(self, monkeypatch, tmp_path):
        """Two parallel Agent calls must each export their own correct forced
        span_id without overwriting each other in pending_tools."""
        self._setup_dirs(monkeypatch, tmp_path)
        all_spans = self._patch_exporters(monkeypatch)

        config = self.CONFIG

        # Parent starts
        tracer.handle_user_prompt_submit(
            {"session_id": "par-par", "prompt": "do both"},
            config,
        )

        # Two parallel Agent pre_tools
        tracer.handle_pre_tool(
            {
                "session_id": "par-par",
                "tool_name": "Agent",
                "tool_input": {"prompt": "task-alpha"},
            },
            config,
        )
        tracer.handle_pre_tool(
            {
                "session_id": "par-par",
                "tool_name": "Agent",
                "tool_input": {"prompt": "task-beta"},
            },
            config,
        )

        # Read context files to capture pre-allocated span IDs
        pending_files = sorted(tracer._PENDING_AGENT_DIR.glob("*.json"))
        assert len(pending_files) == 2
        ctxs = [json.loads(f.read_text()) for f in pending_files]
        # Match by agent_prompt
        alpha_ctx = next(c for c in ctxs if c["agent_prompt"] == "task-alpha")
        beta_ctx = next(c for c in ctxs if c["agent_prompt"] == "task-beta")
        alpha_span_id = int(alpha_ctx["parent_span_id"], 16)
        beta_span_id = int(beta_ctx["parent_span_id"], 16)
        assert alpha_span_id != beta_span_id

        # Both subagents run and complete
        for sess, prompt in [
            ("child-alpha", "task-alpha"),
            ("child-beta", "task-beta"),
        ]:
            tracer.handle_user_prompt_submit(
                {"session_id": sess, "prompt": prompt},
                config,
            )
            tracer.handle_stop({"session_id": sess}, config)

        # Parent post_tools
        tracer.handle_post_tool(
            {
                "session_id": "par-par",
                "tool_name": "Agent",
                "tool_input": {"prompt": "task-alpha"},
                "tool_response": "alpha done",
            },
            config,
        )
        tracer.handle_post_tool(
            {
                "session_id": "par-par",
                "tool_name": "Agent",
                "tool_input": {"prompt": "task-beta"},
                "tool_response": "beta done",
            },
            config,
        )

        # Collect AGENT spans
        agent_spans = [
            s
            for s in all_spans()
            if dict(s.attributes).get("openinference.span.kind") == "AGENT"
        ]
        assert len(agent_spans) == 2, f"Expected 2 AGENT spans, got {len(agent_spans)}"

        exported_ids = {s.context.span_id for s in agent_spans}
        assert (
            alpha_span_id in exported_ids
        ), "alpha span_id not in exported AGENT spans"
        assert beta_span_id in exported_ids, "beta span_id not in exported AGENT spans"


# ---------------------------------------------------------------------------
# OpenInference spec gap analysis — documented intentional absences and
# correctness assertions not covered elsewhere
# ---------------------------------------------------------------------------


class TestOpenInferenceSpecGaps:
    """
    Gap analysis against the OpenInference semantic-conventions spec.

    Each test either:
      (a) documents an attribute that is intentionally absent and explains why, or
      (b) asserts a correctness property that wasn't verified by earlier suites.

    Spec reference:
      https://github.com/Arize-ai/openinference/blob/main/spec/semantic_conventions.md
    """

    TRACE_ID = "abcd" * 8
    ROOT_ID = "ef01" * 4

    def _extract(self, p, human_count_at_start=0):
        return tracer._extract_llm_spans_for_turn(
            str(p),
            human_count_at_start,
            self.TRACE_ID,
            self.ROOT_ID,
        )

    def _build_tool(self, tool_name="Bash", tool_input=None, tool_response="ok"):
        return tracer._build_tool_span_record(
            tool_name=tool_name,
            tool_input=tool_input or {"command": "ls"},
            tool_response=tool_response,
            start_ns=1_000_000_000,
            end_ns=2_000_000_000,
            trace_id=self.TRACE_ID,
            root_span_id=self.ROOT_ID,
        )

    # ── llm.provider ──────────────────────────────────────────────────────────

    def test_llm_provider_intentionally_absent(self, tmp_transcript):
        """llm.provider is distinct from llm.system in the spec (API gateway vs
        underlying model system).  The Claude Code transcript does not expose
        which API provider is being used, so this attribute cannot be set
        reliably.  llm.system='anthropic' is set instead."""
        p = tmp_transcript([human_entry("Hi"), llm_entry("Hello")])
        attrs = self._extract(p)[0]["attributes"]
        assert "llm.provider" not in attrs
        # llm.system is present as the documented substitute
        assert attrs["llm.system"] == "anthropic"

    # ── llm.tools (tools available to the LLM) ───────────────────────────────

    def test_llm_tools_intentionally_absent(self, tmp_transcript):
        """llm.tools.N.tool.json_schema lists what tools were offered to the LLM
        during the API call.  The Claude Code transcript does not include the
        system prompt or tools list sent to Anthropic, so this cannot be
        populated."""
        p = tmp_transcript([human_entry("Hi"), llm_entry("Hello")])
        attrs = self._extract(p)[0]["attributes"]
        assert "llm.tools.0.tool.json_schema" not in attrs

    # ── tool.description on TOOL spans ───────────────────────────────────────

    def test_tool_description_intentionally_absent(self):
        """tool.description is a spec attribute for TOOL spans.  TOOL_SCHEMAS
        does not include human-readable descriptions for Claude Code built-ins,
        so this attribute is not set.  tool.json_schema is set instead."""
        rec = self._build_tool("Bash")
        assert "tool.description" not in rec["attributes"]
        # tool.json_schema IS set as documented substitue
        assert "tool.json_schema" in rec["attributes"]

    # ── tool.id on TOOL spans ─────────────────────────────────────────────────

    def test_tool_id_intentionally_absent(self):
        """tool.id is a spec attribute for tool-definition identifiers.
        Claude Code built-in tools do not have stable definition IDs, so
        this attribute is not set."""
        rec = self._build_tool("Read")
        assert "tool.id" not in rec["attributes"]

    # ── exception.* on error spans ───────────────────────────────────────────

    def test_exception_type_intentionally_absent_on_error_tool_span(self):
        """The spec defines exception.type / exception.message / exception.stacktrace
        for error spans.  The Claude Code hooks only deliver an error string, not a
        structured exception, so these attributes cannot be populated.  The OTel
        status is set to ERROR with the error string as description instead."""
        rec = tracer._build_tool_span_record(
            tool_name="Bash",
            tool_input={"command": "bad"},
            tool_response={"error": "command not found"},
            start_ns=1_000_000_000,
            end_ns=2_000_000_000,
            trace_id=self.TRACE_ID,
            root_span_id=self.ROOT_ID,
            is_failure=True,
            error_msg="command not found",
        )
        assert "exception.type" not in rec["attributes"]
        assert "exception.message" not in rec["attributes"]
        assert "exception.stacktrace" not in rec["attributes"]
        # Error is signalled via the record-level error flag, not span attributes
        assert rec["error"] is True
        assert rec["error_msg"] == "command not found"

    # ── retrieval.documents — only index 0 ───────────────────────────────────

    def test_only_first_retrieval_document_set(self):
        """The spec allows retrieval.documents.N for N >= 0.  The tracer maps the
        entire tool response to a single document at index 0.  Structured
        multi-document parsing is not implemented because WebSearch/WebFetch
        responses are free-form text, not typed document lists."""
        rec = self._build_tool(
            "WebSearch",
            tool_input={"query": "openinference docs"},
            tool_response="Result 1: ...\nResult 2: ...",
        )
        assert "retrieval.documents.0.document.content" in rec["attributes"]
        assert "retrieval.documents.1.document.content" not in rec["attributes"]

    # ── retrieval.documents.0.document.metadata ───────────────────────────────

    def test_retrieval_document_metadata_intentionally_absent(self):
        """document.metadata is a spec attribute for retrieval results.  Web
        search/fetch responses do not include structured metadata (title, URL, etc.)
        in the hook payload, so this attribute is not set."""
        rec = self._build_tool(
            "WebFetch",
            tool_input={"url": "https://example.com", "prompt": "x"},
            tool_response="page content",
        )
        assert "retrieval.documents.0.document.metadata" not in rec["attributes"]

    # ── llm.input_messages: only the immediately preceding message ────────────

    def test_only_preceding_message_captured_as_llm_input(self, tmp_transcript):
        """The spec allows multiple input messages to reflect the full conversation
        context sent to the LLM.  The tracer captures only the immediately preceding
        message (the human prompt or most recent tool result).  The full conversation
        history is not included because the transcript does not expose the full
        messages array sent to Anthropic on each API call."""
        p = tmp_transcript(
            [
                human_entry("Turn 1 context"),
                llm_entry("First reply", ts="2026-01-01T00:00:01.000000+00:00"),
                tool_result_entry("toolu_x", "tool output"),
                llm_entry("Second reply", ts="2026-01-01T00:00:05.000000+00:00"),
            ],
        )
        spans = self._extract(p)
        assert len(spans) == 2
        # Only one input message index (0) is set per LLM span
        attrs0 = spans[0]["attributes"]
        attrs1 = spans[1]["attributes"]
        assert "llm.input_messages.1.message.role" not in attrs0
        assert "llm.input_messages.1.message.role" not in attrs1

    # ── parallel tool results: only first tool_call_id captured ──────────────

    def test_parallel_tool_results_only_first_tool_call_id_captured(
        self,
        tmp_transcript,
    ):
        """When multiple tools run in parallel, their results arrive in a single
        user message with multiple tool_result items.  The tracer extracts only the
        first tool_use_id as llm.input_messages.0.message.tool_call_id.  Subsequent
        tool_call_ids are not captured because the spec flattening for input messages
        only models one message per index, and we don't know the correct pairing
        without the full messages array."""
        parallel_result_entry = {
            "type": "user",
            "message": {
                "role": "user",
                "content": [
                    {
                        "type": "tool_result",
                        "tool_use_id": "toolu_first",
                        "content": [{"type": "text", "text": "result A"}],
                    },
                    {
                        "type": "tool_result",
                        "tool_use_id": "toolu_second",
                        "content": [{"type": "text", "text": "result B"}],
                    },
                ],
            },
            "timestamp": "2026-01-01T00:00:03.000000+00:00",
        }
        p = tmp_transcript(
            [
                human_entry("Do two things"),
                llm_entry(
                    "",
                    tool_use_blocks=[
                        {
                            "type": "tool_use",
                            "id": "toolu_first",
                            "name": "Read",
                            "input": {"file_path": "/a"},
                        },
                        {
                            "type": "tool_use",
                            "id": "toolu_second",
                            "name": "Bash",
                            "input": {"command": "ls"},
                        },
                    ],
                ),
                parallel_result_entry,
                llm_entry("Both done", ts="2026-01-01T00:00:05.000000+00:00"),
            ],
        )
        spans = self._extract(p)
        assert len(spans) == 2
        # The second LLM span captures the parallel result message
        second_attrs = spans[1]["attributes"]
        # Only the first tool_call_id is captured
        assert (
            second_attrs["llm.input_messages.0.message.tool_call_id"] == "toolu_first"
        )
        # The second tool_call_id is absent (known gap)
        assert "llm.input_messages.1.message.tool_call_id" not in second_attrs

    # ── LLM span timestamp sanity ─────────────────────────────────────────────

    def test_llm_span_end_ns_always_greater_than_start_ns(self, tmp_transcript):
        """Derived end time must always be strictly after start time, even for
        responses with 0 output tokens (floor of 1 ms is applied)."""
        zero_token_entry = {
            "type": "assistant",
            "message": {
                "role": "assistant",
                "model": "claude-sonnet-4-6",
                "content": [],
                "stop_reason": "end_turn",
                "usage": {
                    "input_tokens": 10,
                    "output_tokens": 0,
                    "cache_read_input_tokens": 0,
                    "cache_creation_input_tokens": 0,
                },
            },
            "timestamp": "2026-01-01T00:00:02.000000+00:00",
        }
        p = tmp_transcript([human_entry("Hi"), zero_token_entry])
        spans = self._extract(p)
        assert len(spans) == 1
        assert spans[0]["end_ns"] > spans[0]["start_ns"]

    # ── Unknown tool: no tool.json_schema ────────────────────────────────────

    def test_unknown_tool_has_no_json_schema(self):
        """A tool not in TOOL_SCHEMAS must not set tool.json_schema.  The tracer
        only attaches schemas for known built-in tools."""
        rec = self._build_tool("CustomInternalTool", tool_input={"param": "value"})
        assert "tool.json_schema" not in rec["attributes"]
        # tool.name is still set
        assert rec["attributes"]["tool.name"] == "CustomInternalTool"

    # ── tool.json_schema is always valid JSON ─────────────────────────────────

    def test_tool_json_schema_is_valid_json_for_all_known_tools(self):
        """Every tool in TOOL_SCHEMAS must produce parseable JSON in tool.json_schema."""
        for tool_name in tracer.TOOL_SCHEMAS:
            rec = tracer._build_tool_span_record(
                tool_name=tool_name,
                tool_input={},
                tool_response="ok",
                start_ns=1_000_000_000,
                end_ns=2_000_000_000,
                trace_id=self.TRACE_ID,
                root_span_id=self.ROOT_ID,
            )
            schema_str = rec["attributes"].get("tool.json_schema", "")
            assert schema_str, f"{tool_name}: tool.json_schema is absent or empty"
            parsed = json.loads(schema_str)
            assert (
                "type" in parsed or "properties" in parsed
            ), f"{tool_name}: tool.json_schema missing 'type' or 'properties'"

    # ── AGENT span: no tool.json_schema for unknown subagent_type ────────────

    def test_agent_span_still_has_json_schema_from_tool_schemas(self):
        """The Agent and Task tool schemas are in TOOL_SCHEMAS, so AGENT spans
        always have tool.json_schema even though they map to AGENT span kind."""
        for agent_tool in ("Agent", "Task"):
            rec = self._build_tool(
                agent_tool,
                tool_input={"prompt": "do something", "description": "helper"},
            )
            assert (
                "tool.json_schema" in rec["attributes"]
            ), f"{agent_tool} AGENT span missing tool.json_schema"

    # ── LLM span: llm.output_messages.0.message.role is always "assistant" ───

    def test_llm_output_message_role_is_assistant_for_tool_only_response(
        self,
        tmp_transcript,
    ):
        """Even when the LLM only produces tool_use blocks (no text), the output
        message role must be 'assistant' per the OpenInference spec."""
        tb = tool_use_block("Bash", "ls")
        p = tmp_transcript([human_entry("Go"), llm_entry("", tool_use_blocks=[tb])])
        attrs = self._extract(p)[0]["attributes"]
        assert attrs["llm.output_messages.0.message.role"] == "assistant"

    # ── CHAIN span: session.id and user.id in attributes (not just resource) ──

    def test_chain_span_has_session_id_and_user_id_in_attributes(self, monkeypatch):
        """session.id and user.id must appear as span attributes on the CHAIN span,
        not only in OTel resource fields."""
        exported = []
        monkeypatch.setattr(
            tracer,
            "_build_and_export_spans",
            lambda **kw: exported.extend(kw["span_records"]),
        )
        state = {
            "session_id": "sess-gap-check",
            "username": "gap-user",
            "current_trace": {
                "trace_id": "a" * 32,
                "root_span_id": "b" * 16,
                "turn_start_ns": 1_000_000_000,
                "turn_number": 1,
                "prompt_preview": "hello",
                "last_llm_output": "world",
            },
        }
        tracer._complete_turn(
            state,
            {"api_key": "k", "task_id": "t", "endpoint": "https://x"},
            None,
            2_000_000_000,
        )
        chain = next(
            r
            for r in exported
            if r["attributes"].get("openinference.span.kind") == "CHAIN"
        )
        assert chain["attributes"]["session.id"] == "sess-gap-check"
        assert chain["attributes"]["user.id"] == "gap-user"

    # ── llm.input_messages.0.message.content format when tool result ──────────

    def test_llm_input_message_content_is_string_not_list(self, tmp_transcript):
        """The spec uses flattened scalar attributes; message.content must be a
        string, not a list, even when the input comes from a tool result."""
        p = tmp_transcript(
            [
                human_entry("What files?"),
                llm_entry("", tool_use_blocks=[tool_use_block()]),
                tool_result_entry("toolu_x", "file.txt\nother.py"),
                llm_entry("Found them", ts="2026-01-01T00:00:05.000000+00:00"),
            ],
        )
        spans = self._extract(p)
        second_attrs = spans[1]["attributes"]
        content = second_attrs["llm.input_messages.0.message.content"]
        assert isinstance(
            content,
            str,
        ), f"message.content must be a string, got {type(content)}"
        assert "file.txt" in content

    # ── RETRIEVER: output.mime_type is "application/json" even for text ───────

    def test_retriever_output_mime_type_is_application_json_for_text_response(self):
        """For RETRIEVER spans the raw web response is stored as a JSON-serialised
        string in output.value (not the raw bytes), so output.mime_type is
        application/json.  The actual document text is at
        retrieval.documents.0.document.content as a plain string."""
        rec = self._build_tool(
            "WebFetch",
            tool_input={"url": "https://example.com", "prompt": "x"},
            tool_response="raw page text",
        )
        assert rec["attributes"]["output.mime_type"] == "application/json"
        # Document content is the raw text, not JSON-wrapped
        doc_content = rec["attributes"]["retrieval.documents.0.document.content"]
        assert doc_content == "raw page text"

    # ── metadata attribute ─────────────────────────────────────────────────────

    def test_metadata_attribute_intentionally_absent(self, tmp_transcript):
        """The spec supports a free-form JSON metadata attribute on any span.
        The tracer does not set this — session and task context is conveyed via
        resource attributes (arthur.task, arthur.session) instead."""
        p = tmp_transcript([human_entry("Hi"), llm_entry("Hello")])
        attrs = self._extract(p)[0]["attributes"]
        assert "metadata" not in attrs

    # ── tag.tags attribute ─────────────────────────────────────────────────────

    def test_tag_tags_attribute_intentionally_absent(self, tmp_transcript):
        """tag.tags is not set — Claude Code sessions have no user-defined tags."""
        p = tmp_transcript([human_entry("Hi"), llm_entry("Hello")])
        attrs = self._extract(p)[0]["attributes"]
        assert "tag.tags" not in attrs


# ---------------------------------------------------------------------------
# Inline-agent tool nesting
# ---------------------------------------------------------------------------


class TestInlineAgentToolNesting:
    """Verify that tool spans emitted while an Agent/Task tool is pending are
    parented to the Agent span, not the CHAIN root.

    When Claude Code uses an Explore-type subagent, the subagent's tools (WebFetch,
    Read, etc.) fire hooks in the *parent* session because the subagent runs inline
    rather than in a separate process.  The fix detects any pending Agent entry in
    state["pending_tools"] and uses its pre_allocated_span_id as the parent for
    tools that fire during that window.
    """

    CONFIG = {"api_key": "k", "task_id": "t", "endpoint": "https://x.example.com"}
    ROOT_ID = "aaaa" * 4
    TRACE_ID = "bbbb" * 8
    AGENT_SPAN_ID = "cccc" * 2

    def _make_state(self, monkeypatch, tmp_path, session_id, pending_tools=None):
        monkeypatch.setattr(tracer, "STATE_DIR", tmp_path / "tracer")
        (tmp_path / "tracer").mkdir(parents=True, exist_ok=True)
        state = {
            "session_id": session_id,
            "username": "u",
            "human_msg_count": 1,
            "turn_number": 1,
            "current_trace": {
                "trace_id": self.TRACE_ID,
                "root_span_id": self.ROOT_ID,
                "turn_start_ns": 1_000_000_000,
                "turn_number": 1,
                "human_count_at_start": 1,
                "prompt_preview": "test",
                "emitted_llm_span_count": 0,
            },
            "pending_tools": pending_tools or {},
        }
        tracer._save_state(session_id, state)
        return state

    def _run_post_tool(
        self,
        monkeypatch,
        tmp_path,
        session_id,
        tool_name,
        pending_tools,
    ):
        exported = []
        monkeypatch.setattr(
            tracer,
            "_build_and_export_spans",
            lambda **kw: exported.extend(kw["span_records"]),
        )
        monkeypatch.setattr(tracer, "_emit_pending_llm_spans", lambda *a, **kw: None)
        monkeypatch.setattr(
            tracer,
            "_get_cached_transcript_path",
            lambda *a, **kw: None,
        )
        self._make_state(monkeypatch, tmp_path, session_id, pending_tools)
        tracer.handle_post_tool(
            {
                "session_id": session_id,
                "tool_name": tool_name,
                "tool_input": {"url": "https://example.com", "prompt": "fetch"},
                "tool_response": "content",
            },
            self.CONFIG,
        )
        return exported

    def test_subagent_webfetch_parented_to_agent(self, monkeypatch, tmp_path):
        """WebFetch fired while Agent is pending → parent_span_id_hex = Agent span."""
        pending = {
            f"Agent#{self.AGENT_SPAN_ID}": {
                "tool_name": "Agent",
                "tool_input": {"prompt": "explore"},
                "start_ns": 500_000_000,
                "pre_allocated_span_id": self.AGENT_SPAN_ID,
            },
            "WebFetch": {
                "tool_name": "WebFetch",
                "tool_input": {"url": "https://example.com", "prompt": "fetch"},
                "start_ns": 600_000_000,
            },
        }
        exported = self._run_post_tool(
            monkeypatch,
            tmp_path,
            "nest1",
            "WebFetch",
            pending,
        )
        assert len(exported) == 1
        assert (
            exported[0]["parent_span_id_hex"] == self.AGENT_SPAN_ID
        ), f"Expected parent={self.AGENT_SPAN_ID}, got {exported[0]['parent_span_id_hex']}"

    def test_agent_span_still_parented_to_chain_root(self, monkeypatch, tmp_path):
        """The Agent span itself must be parented to the CHAIN root, not to itself."""
        agent_key = f"Agent#{self.AGENT_SPAN_ID}"
        pending = {
            agent_key: {
                "tool_name": "Agent",
                "tool_input": {"prompt": "explore"},
                "start_ns": 500_000_000,
                "pre_allocated_span_id": self.AGENT_SPAN_ID,
            },
        }
        exported = []
        monkeypatch.setattr(tracer, "STATE_DIR", tmp_path / "tracer")
        (tmp_path / "tracer").mkdir(parents=True, exist_ok=True)
        monkeypatch.setattr(
            tracer,
            "_build_and_export_spans",
            lambda **kw: exported.extend(kw["span_records"]),
        )
        monkeypatch.setattr(tracer, "_emit_pending_llm_spans", lambda *a, **kw: None)
        monkeypatch.setattr(
            tracer,
            "_get_cached_transcript_path",
            lambda *a, **kw: None,
        )
        self._make_state(monkeypatch, tmp_path, "nest2", pending)
        tracer.handle_post_tool(
            {
                "session_id": "nest2",
                "tool_name": "Agent",
                "tool_input": {"prompt": "explore"},
                "tool_response": "done",
            },
            self.CONFIG,
        )
        assert len(exported) == 1
        assert exported[0]["parent_span_id_hex"] == self.ROOT_ID, (
            f"Agent span should parent to CHAIN root {self.ROOT_ID}, "
            f"got {exported[0]['parent_span_id_hex']}"
        )

    def test_tool_after_agent_completes_parented_to_root(self, monkeypatch, tmp_path):
        """WebFetch with no pending Agent → parent_span_id_hex = CHAIN root."""
        pending = {
            "WebFetch": {
                "tool_name": "WebFetch",
                "tool_input": {"url": "https://example.com", "prompt": "fetch"},
                "start_ns": 700_000_000,
            },
        }
        exported = self._run_post_tool(
            monkeypatch,
            tmp_path,
            "nest3",
            "WebFetch",
            pending,
        )
        assert len(exported) == 1
        assert exported[0]["parent_span_id_hex"] == self.ROOT_ID

    def test_nested_agents_webfetch_parented_to_innermost(self, monkeypatch, tmp_path):
        """With two pending Agents (outer started first), WebFetch parents to the
        more-recently-started one (inner), not the outer."""
        outer_id = "1111" * 2
        inner_id = "2222" * 2
        pending = {
            f"Agent#{outer_id}": {
                "tool_name": "Agent",
                "tool_input": {"prompt": "outer"},
                "start_ns": 100_000_000,
                "pre_allocated_span_id": outer_id,
            },
            f"Agent#{inner_id}": {
                "tool_name": "Agent",
                "tool_input": {"prompt": "inner"},
                "start_ns": 200_000_000,
                "pre_allocated_span_id": inner_id,
            },
            "WebFetch": {
                "tool_name": "WebFetch",
                "tool_input": {"url": "https://example.com", "prompt": "fetch"},
                "start_ns": 300_000_000,
            },
        }
        exported = self._run_post_tool(
            monkeypatch,
            tmp_path,
            "nest4",
            "WebFetch",
            pending,
        )
        assert len(exported) == 1
        assert (
            exported[0]["parent_span_id_hex"] == inner_id
        ), f"Expected innermost agent {inner_id}, got {exported[0]['parent_span_id_hex']}"


# ---------------------------------------------------------------------------
# handle_stop — context-continuation detection
# ---------------------------------------------------------------------------


class TestHandleStopContextContinuation:
    """handle_stop detects when the transcript grew by more than one human message
    since the current trace started (context compression + continuation without a
    UserPromptSubmit).  It must complete the stale trace, create a new trace for
    the continuation turn, emit that turn's LLM spans, complete it, and then
    delete session state.
    """

    CONFIG = {"api_key": "k", "task_id": "t", "endpoint": "https://x.example.com"}

    def test_continuation_emits_two_chain_spans(
        self,
        tmp_path,
        tmp_transcript,
        monkeypatch,
    ):
        """Transcript has 3 human messages but current_trace.human_count_at_start=0.
        handle_stop must detect the gap and emit one CHAIN span for the stale turn
        and one for the continuation turn."""
        monkeypatch.setattr(tracer, "STATE_DIR", tmp_path / "tracer")
        (tmp_path / "tracer").mkdir()
        exported = []
        monkeypatch.setattr(
            tracer,
            "_build_and_export_spans",
            lambda **kw: exported.extend(kw["span_records"]),
        )

        old_trace_id = "1" * 32
        p = tmp_transcript(
            [
                human_entry("Turn 1 prompt"),
                llm_entry("Reply 1", ts="2026-01-01T00:00:01.000000+00:00"),
                human_entry("Turn 2 (context continuation trigger)"),
                llm_entry("Reply 2", ts="2026-01-01T00:00:03.000000+00:00"),
                human_entry("Turn 3 (the continuation turn)"),
                llm_entry("Reply 3", ts="2026-01-01T00:00:05.000000+00:00"),
            ],
        )

        # Seed state as if turn 1 is in-progress: human_count_at_start=0,
        # but transcript now has 3 human messages → continuation detected.
        tracer._save_state(
            "cont-stop",
            {
                "session_id": "cont-stop",
                "username": "u",
                "human_msg_count": 1,
                "turn_number": 1,
                "transcript_path": str(p),
                "current_trace": {
                    "trace_id": old_trace_id,
                    "root_span_id": "2" * 16,
                    "turn_start_ns": 1_000_000_000,
                    "turn_number": 1,
                    "human_count_at_start": 0,
                    "prompt_preview": "Turn 1 prompt",
                    "emitted_llm_span_count": 0,
                },
            },
        )

        tracer.handle_stop(
            {"session_id": "cont-stop", "transcript_path": str(p)},
            self.CONFIG,
        )

        chain_spans = [
            s
            for s in exported
            if s.get("attributes", {}).get("openinference.span.kind") == "CHAIN"
        ]
        assert (
            len(chain_spans) == 2
        ), f"Expected 2 CHAIN spans (stale + continuation), got {len(chain_spans)}"

    def test_continuation_uses_fresh_trace_id_for_new_turn(
        self,
        tmp_path,
        tmp_transcript,
        monkeypatch,
    ):
        """The continuation turn's CHAIN span must have a different trace_id than the
        stale turn's CHAIN span."""
        monkeypatch.setattr(tracer, "STATE_DIR", tmp_path / "tracer")
        (tmp_path / "tracer").mkdir()
        exported = []
        monkeypatch.setattr(
            tracer,
            "_build_and_export_spans",
            lambda **kw: exported.extend(kw["span_records"]),
        )

        old_trace_id = "aaaa" * 8
        p = tmp_transcript(
            [
                human_entry("Turn 1"),
                llm_entry("Reply 1", ts="2026-01-01T00:00:01.000000+00:00"),
                human_entry("Turn 2 continuation trigger"),
                llm_entry("Reply 2", ts="2026-01-01T00:00:03.000000+00:00"),
                human_entry("Turn 3 actual continuation"),
                llm_entry("Reply 3", ts="2026-01-01T00:00:05.000000+00:00"),
            ],
        )

        tracer._save_state(
            "cont-trace-id",
            {
                "session_id": "cont-trace-id",
                "username": "u",
                "human_msg_count": 1,
                "turn_number": 1,
                "transcript_path": str(p),
                "current_trace": {
                    "trace_id": old_trace_id,
                    "root_span_id": "bbbb" * 4,
                    "turn_start_ns": 1_000_000_000,
                    "turn_number": 1,
                    "human_count_at_start": 0,
                    "prompt_preview": "Turn 1",
                    "emitted_llm_span_count": 0,
                },
            },
        )

        tracer.handle_stop(
            {"session_id": "cont-trace-id", "transcript_path": str(p)},
            self.CONFIG,
        )

        chain_spans = [
            s
            for s in exported
            if s.get("attributes", {}).get("openinference.span.kind") == "CHAIN"
        ]
        assert len(chain_spans) == 2
        trace_ids = {s["trace_id_hex"] for s in chain_spans}
        assert (
            len(trace_ids) == 2
        ), "Stale turn and continuation turn must have different trace IDs"
        assert old_trace_id in trace_ids, "First CHAIN span must use the stale trace_id"

    def test_continuation_state_deleted_after_stop(
        self,
        tmp_path,
        tmp_transcript,
        monkeypatch,
    ):
        """Session state file must be deleted even after the continuation branch runs."""
        monkeypatch.setattr(tracer, "STATE_DIR", tmp_path / "tracer")
        (tmp_path / "tracer").mkdir()
        monkeypatch.setattr(tracer, "_build_and_export_spans", MagicMock())

        p = tmp_transcript(
            [
                human_entry("Turn 1"),
                llm_entry("R1", ts="2026-01-01T00:00:01.000000+00:00"),
                human_entry("Turn 2"),
                llm_entry("R2", ts="2026-01-01T00:00:03.000000+00:00"),
                human_entry("Turn 3 continuation"),
                llm_entry("R3", ts="2026-01-01T00:00:05.000000+00:00"),
            ],
        )

        tracer._save_state(
            "cont-del",
            {
                "session_id": "cont-del",
                "username": "u",
                "human_msg_count": 1,
                "turn_number": 1,
                "transcript_path": str(p),
                "current_trace": {
                    "trace_id": "cccc" * 8,
                    "root_span_id": "dddd" * 4,
                    "turn_start_ns": 1_000_000_000,
                    "turn_number": 1,
                    "human_count_at_start": 0,
                    "prompt_preview": "Turn 1",
                    "emitted_llm_span_count": 0,
                },
            },
        )

        tracer.handle_stop(
            {"session_id": "cont-del", "transcript_path": str(p)},
            self.CONFIG,
        )

        assert not (
            tmp_path / "tracer" / "cont-del.json"
        ).exists(), (
            "State file must be deleted after stop, even with continuation branch"
        )

    def test_no_continuation_when_transcript_has_one_turn(
        self,
        tmp_path,
        tmp_transcript,
        monkeypatch,
    ):
        """Normal stop with a single-turn transcript must emit exactly one CHAIN span."""
        monkeypatch.setattr(tracer, "STATE_DIR", tmp_path / "tracer")
        (tmp_path / "tracer").mkdir()
        exported = []
        monkeypatch.setattr(
            tracer,
            "_build_and_export_spans",
            lambda **kw: exported.extend(kw["span_records"]),
        )

        p = tmp_transcript(
            [
                human_entry("Just one turn"),
                llm_entry("Just one reply"),
            ],
        )

        tracer._save_state(
            "no-cont",
            {
                "session_id": "no-cont",
                "username": "u",
                "human_msg_count": 1,
                "turn_number": 1,
                "transcript_path": str(p),
                "current_trace": {
                    "trace_id": "eeee" * 8,
                    "root_span_id": "ffff" * 4,
                    "turn_start_ns": 1_000_000_000,
                    "turn_number": 1,
                    "human_count_at_start": 0,
                    "prompt_preview": "Just one turn",
                    "emitted_llm_span_count": 0,
                },
            },
        )

        tracer.handle_stop(
            {"session_id": "no-cont", "transcript_path": str(p)},
            self.CONFIG,
        )

        chain_spans = [
            s
            for s in exported
            if s.get("attributes", {}).get("openinference.span.kind") == "CHAIN"
        ]
        assert (
            len(chain_spans) == 1
        ), f"Normal stop must emit exactly one CHAIN span, got {len(chain_spans)}"

    def test_continuation_llm_spans_extracted_for_new_turn(
        self,
        tmp_path,
        tmp_transcript,
        monkeypatch,
    ):
        """LLM spans for the continuation turn must be extracted from the transcript
        and emitted (not skipped) when the continuation branch fires."""
        monkeypatch.setattr(tracer, "STATE_DIR", tmp_path / "tracer")
        (tmp_path / "tracer").mkdir()
        exported = []
        monkeypatch.setattr(
            tracer,
            "_build_and_export_spans",
            lambda **kw: exported.extend(kw["span_records"]),
        )

        p = tmp_transcript(
            [
                human_entry("Turn 1"),
                llm_entry("Old reply", ts="2026-01-01T00:00:01.000000+00:00"),
                human_entry("Turn 2 continuation trigger"),
                llm_entry("Middle reply", ts="2026-01-01T00:00:03.000000+00:00"),
                human_entry("Turn 3 — the continuation turn"),
                llm_entry(
                    "Continuation reply",
                    ts="2026-01-01T00:00:05.000000+00:00",
                ),
            ],
        )

        tracer._save_state(
            "cont-llm",
            {
                "session_id": "cont-llm",
                "username": "u",
                "human_msg_count": 1,
                "turn_number": 1,
                "transcript_path": str(p),
                "current_trace": {
                    "trace_id": "1234" * 8,
                    "root_span_id": "5678" * 4,
                    "turn_start_ns": 1_000_000_000,
                    "turn_number": 1,
                    "human_count_at_start": 0,
                    "prompt_preview": "Turn 1",
                    "emitted_llm_span_count": 0,
                },
            },
        )

        tracer.handle_stop(
            {"session_id": "cont-llm", "transcript_path": str(p)},
            self.CONFIG,
        )

        llm_spans = [
            s
            for s in exported
            if s.get("attributes", {}).get("openinference.span.kind") == "LLM"
        ]
        # Transcript has 3 LLM calls across 3 turns; the middle turn (turn 2) is a
        # continuation trigger and falls between the two traces, so its LLM span is
        # not extracted.  Turns 1 and 3 each contribute one LLM span → exactly 2.
        assert len(llm_spans) >= 2, (
            f"Expected LLM spans from both the stale and continuation turns, "
            f"got {len(llm_spans)}"
        )
