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


def append(path, lines):
    with open(path, "a") as f:
        for line in lines:
            f.write(json.dumps(line) + "\n")


def record(i, inp, out, cached=0, ts=None):
    return {"timestamp": iso(ts or time.time()), "type": "token_usage_record",
            "payload": {"response_id": f"resp_{i}", "usage": {"input_tokens": inp, "cached_input_tokens": cached, "output_tokens": out}}}


def spent(env):
    return round(sum(v[1] for v in json.load(open(env["ARTHUR_BREAKER_STATE"]))["spend"].values()), 6)


def test_reset_is_not_undone_by_the_next_hook(tmp_path, env):
    rollout = tmp_path / "r.jsonl"
    write_rollout(rollout, [(10000, 0, 100)])  # $0.105, over the cap
    hook(env, "UserPromptSubmit", prompt="breaker reset", transcript_path=str(rollout))
    # Another session reads the same responses for the first time after the reset.
    assert hook(env, "PreToolUse", tool_name="shell", transcript_path=str(rollout), session_id="other") == {}
    assert hook(env, "PreToolUse", tool_name="shell", transcript_path=str(rollout)) == {}


def test_new_responses_after_a_reset_still_count(tmp_path, env):
    rollout = tmp_path / "r.jsonl"
    write_rollout(rollout, [(10000, 0, 100)])
    hook(env, "UserPromptSubmit", prompt="breaker reset", transcript_path=str(rollout))
    time.sleep(0.01)
    append(rollout, [record(9, 10000, 100)])
    assert hook(env, "PreToolUse", tool_name="shell", transcript_path=str(rollout))["hookSpecificOutput"]["permissionDecision"] == "deny"


def test_rollout_is_read_incrementally(tmp_path, env):
    rollout = tmp_path / "r.jsonl"
    write_rollout(rollout, [(1000, 0, 0)])  # $0.01
    hook(env, "PreToolUse", tool_name="shell", transcript_path=str(rollout))
    state = json.load(open(env["ARTHUR_BREAKER_STATE"]))
    assert state["sessions"]["s1"]["pos"] == rollout.stat().st_size
    append(rollout, [record(5, 2000, 0)])  # +$0.02
    hook(env, "PreToolUse", tool_name="shell", transcript_path=str(rollout))
    hook(env, "PreToolUse", tool_name="shell", transcript_path=str(rollout))
    assert spent(env) == 0.03


def test_a_line_still_being_written_is_read_next_time(tmp_path, env):
    rollout = tmp_path / "r.jsonl"
    write_rollout(rollout, [])
    with open(rollout, "a") as f:
        f.write(json.dumps(record(1, 1000, 0))[:-5])  # no newline yet
    hook(env, "PreToolUse", tool_name="shell", transcript_path=str(rollout))
    assert spent(env) == 0
    with open(rollout, "w") as f:
        f.write(json.dumps({"timestamp": iso(time.time()), "type": "turn_context", "payload": {"model": "gpt-6-astra"}}) + "\n")
        f.write(json.dumps(record(1, 1000, 0)) + "\n")
    hook(env, "PreToolUse", tool_name="shell", transcript_path=str(rollout))
    assert spent(env) == 0.01


def test_a_repeated_legacy_token_count_is_counted_once(tmp_path, env):
    rollout = tmp_path / "r.jsonl"
    now = iso(time.time())
    tc = lambda total: {"timestamp": now, "type": "event_msg", "payload": {"type": "token_count", "info": {
        "total_token_usage": {"total_tokens": total},
        "last_token_usage": {"input_tokens": 1000, "cached_input_tokens": 0, "output_tokens": 0, "total_tokens": 1000}}}}
    rollout.write_text("".join(json.dumps(x) + "\n" for x in [
        {"timestamp": now, "type": "turn_context", "payload": {"model": "gpt-6-astra"}},
        tc(1000), tc(1000),  # the second repeats the same usage (a rate-limit update)
        tc(2000),
    ]))
    hook(env, "PreToolUse", tool_name="shell", transcript_path=str(rollout))
    assert spent(env) == 0.02


def test_unknown_model_gets_the_highest_rate_of_each_kind(tmp_path, env):
    rollout = tmp_path / "r.jsonl"
    env["ARTHUR_BREAKER_RATES_JSON"] = json.dumps({"input-heavy": {"input": 40.0, "cached": 4.0, "output": 1.0}})
    write_rollout(rollout, [(2000, 0, 0)], model="some-new-model")  # 2000 x $40/M = $0.08, not $0.02
    hook(env, "PreToolUse", tool_name="shell", transcript_path=str(rollout))
    assert spent(env) == 0.08


def test_concurrent_hooks_lose_no_spend(tmp_path, env):
    procs = []
    for n in range(40):
        rollout = tmp_path / f"r{n}.jsonl"
        write_rollout(rollout, [(1000, 0, 0)])  # $0.01 each, forty sessions at once
        procs.append(subprocess.Popen([sys.executable, HOOK], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True, env={**env, "ARTHUR_BREAKER_CAP_USD": "10"}))
        procs[-1].stdin.write(json.dumps({"hook_event_name": "PreToolUse", "session_id": f"s{n}", "transcript_path": str(rollout)}))
        procs[-1].stdin.close()
    for p in procs:
        p.wait(timeout=10)
    assert spent(env) == 0.4


@pytest.mark.parametrize("bad", ['[1, 2]', '{"x": "cheap"}', '{"x": {"input": 1}}', '{"x": {"input": "1", "cached": 0, "output": 1}}', 'not json'])
def test_a_bad_rates_override_cannot_turn_the_breaker_off(tmp_path, env, bad):
    rollout = tmp_path / "r.jsonl"
    write_rollout(rollout, [(10000, 0, 100)], model="some-new-model")  # over the cap at any built-in rate
    env["ARTHUR_BREAKER_RATES_JSON"] = bad
    assert hook(env, "PreToolUse", tool_name="shell", transcript_path=str(rollout))["hookSpecificOutput"]["permissionDecision"] == "deny"


@pytest.mark.parametrize("bad", ['Infinity', '1e999', 'NaN', '-1', '1' + '0' * 400])
def test_a_rate_that_is_not_a_finite_non_negative_number_is_ignored(tmp_path, env, bad):
    rollout = tmp_path / "r.jsonl"
    write_rollout(rollout, [(1000, 0, 0)], model="gpt-6-astra")  # $0.01 at the built-in rate, under the cap
    env["ARTHUR_BREAKER_RATES_JSON"] = '{"gpt-6-astra": {"input": %s, "cached": 0, "output": 1}}' % bad
    assert hook(env, "PreToolUse", tool_name="shell", transcript_path=str(rollout)) == {}
    assert spent(env) == 0.01


def test_valid_rows_beside_a_bad_one_still_apply(tmp_path, env):
    rollout = tmp_path / "r.jsonl"
    write_rollout(rollout, [(0, 0, 2100)], model="cheap-model")
    env["ARTHUR_BREAKER_RATES_JSON"] = json.dumps({"broken": "x", "cheap-model": {"input": 0.1, "cached": 0.01, "output": 0.4}})
    assert hook(env, "PreToolUse", tool_name="shell", transcript_path=str(rollout)) == {}
