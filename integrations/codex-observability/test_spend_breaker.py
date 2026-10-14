"""Tests for codex_spend_breaker.py: run the hook as Codex would, on a synthetic rollout."""

import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone

import pytest

HOOK = os.path.join(os.path.dirname(__file__), "codex_spend_breaker.py")


def iso(ts):
    return datetime.fromtimestamp(ts, timezone.utc).isoformat().replace("+00:00", "Z")


def write_rollout(path, responses, model="gpt-6-astra", ago=0):
    """responses: list of (input_tokens, cached_input_tokens, output_tokens)."""
    now = time.time() - ago
    lines = [{"timestamp": iso(now), "type": "turn_context", "payload": {"model": model}}]
    for i, (inp, cached, out) in enumerate(responses):
        lines.append({
            "timestamp": iso(now),
            "type": "token_usage_record",
            "payload": {"response_id": f"resp_{i}", "usage": {"input_tokens": inp, "cached_input_tokens": cached, "output_tokens": out}},
        })
    path.write_text("\n".join(json.dumps(line) for line in lines) + "\n")


@pytest.fixture
def env(tmp_path):
    return {**os.environ, "ARTHUR_BREAKER_STATE": str(tmp_path / "state.json"), "ARTHUR_BREAKER_CAP_USD": "0.10"}


def hook(env, event, **fields):
    proc = subprocess.run([sys.executable, HOOK], input=json.dumps({"hook_event_name": event, "session_id": "s1", **fields}),
                          capture_output=True, text=True, env=env, timeout=10)
    assert proc.returncode == 0
    return json.loads(proc.stdout) if proc.stdout.strip() else {}


def test_under_cap_allows_prompt_and_tool(tmp_path, env):
    rollout = tmp_path / "r.jsonl"
    write_rollout(rollout, [(1000, 0, 100)])  # $0.015
    assert hook(env, "UserPromptSubmit", prompt="hi", transcript_path=str(rollout)) == {}
    assert hook(env, "PreToolUse", tool_name="shell", transcript_path=str(rollout)) == {}


def test_over_cap_denies_tool_without_continue(tmp_path, env):
    rollout = tmp_path / "r.jsonl"
    write_rollout(rollout, [(10000, 0, 100)])  # $0.105
    out = hook(env, "PreToolUse", tool_name="shell", transcript_path=str(rollout))
    assert out["hookSpecificOutput"]["permissionDecision"] == "deny"
    # Codex rejects a PreToolUse reply that carries `continue` and runs the tool anyway.
    assert "continue" not in out


def test_over_cap_blocks_prompt(tmp_path, env):
    rollout = tmp_path / "r.jsonl"
    write_rollout(rollout, [(10000, 0, 100)])
    out = hook(env, "UserPromptSubmit", prompt="next", transcript_path=str(rollout))
    assert out["decision"] == "block" and "breaker override" in out["reason"]


def test_cached_tokens_are_priced_at_the_cached_rate(tmp_path, env):
    rollout = tmp_path / "r.jsonl"
    write_rollout(rollout, [(10000, 9000, 0)])  # 1000 x $10/M + 9000 x $1/M = $0.019
    assert hook(env, "PreToolUse", tool_name="shell", transcript_path=str(rollout)) == {}
    state = json.load(open(env["ARTHUR_BREAKER_STATE"]))
    assert round(sum(v[1] for v in state["spend"].values()), 6) == 0.019


def test_spend_outside_the_window_does_not_count(tmp_path, env):
    rollout = tmp_path / "r.jsonl"
    write_rollout(rollout, [(10000, 0, 100)], ago=6 * 60)
    assert hook(env, "PreToolUse", tool_name="shell", transcript_path=str(rollout)) == {}


def test_each_response_is_counted_once(tmp_path, env):
    rollout = tmp_path / "r.jsonl"
    write_rollout(rollout, [(6000, 0, 0)])  # $0.06, under the cap
    for _ in range(3):
        assert hook(env, "PreToolUse", tool_name="shell", transcript_path=str(rollout)) == {}


def test_override_lifts_and_reset_clears(tmp_path, env):
    rollout = tmp_path / "r.jsonl"
    write_rollout(rollout, [(10000, 0, 100)])
    out = hook(env, "UserPromptSubmit", prompt="breaker override", transcript_path=str(rollout))
    assert out["decision"] == "block" and "lifted until" in out["reason"]  # the command never reaches the model
    assert hook(env, "PreToolUse", tool_name="shell", transcript_path=str(rollout)) == {}
    out = hook(env, "UserPromptSubmit", prompt="breaker reset", transcript_path=str(rollout))
    assert "$0.0000" in out["reason"]


def test_unknown_model_is_priced_at_the_highest_row(tmp_path, env):
    rollout = tmp_path / "r.jsonl"
    write_rollout(rollout, [(0, 0, 2100)], model="some-new-model")  # 2100 x $50/M = $0.105
    assert hook(env, "PreToolUse", tool_name="shell", transcript_path=str(rollout))["hookSpecificOutput"]["permissionDecision"] == "deny"


def test_rates_can_be_overridden(tmp_path, env):
    rollout = tmp_path / "r.jsonl"
    write_rollout(rollout, [(0, 0, 2100)], model="cheap-model")
    env["ARTHUR_BREAKER_RATES_JSON"] = json.dumps({"cheap-model": {"input": 0.1, "cached": 0.01, "output": 0.4}})
    assert hook(env, "PreToolUse", tool_name="shell", transcript_path=str(rollout)) == {}


def test_bad_input_fails_open(env):
    proc = subprocess.run([sys.executable, HOOK], input="not json", capture_output=True, text=True, env=env, timeout=10)
    assert proc.returncode == 0 and proc.stdout == ""
