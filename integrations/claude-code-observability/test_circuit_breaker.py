"""
Unit tests for claude_code_circuit_breaker.py

Run with:  python3 -m pytest integrations/claude-code-observability/test_circuit_breaker.py -v
"""

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))
import claude_code_circuit_breaker as cb

NOW = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
ENGINE = {"api_key": "k", "task_id": "task-1", "base_url": "http://engine/api/v1"}


def _config(**overrides) -> dict:
    config = json.loads(json.dumps(cb.DEFAULT_CONFIG))
    config.update(overrides)
    return config


def _span_row(
    minutes_ago: float,
    cost,
    tokens: int = 1000,
    now: datetime = NOW,
) -> dict:
    return {
        "start_time": (now - timedelta(minutes=minutes_ago)).strftime(
            "%Y-%m-%dT%H:%M:%S.%f",
        ),
        "total_token_cost": cost,
        "total_token_count": tokens,
        "prompt_token_count": tokens - 100,
        "completion_token_count": 100,
    }


class FakeEngine:
    """Replaces cb._request; records calls and serves canned responses."""

    def __init__(
        self,
        spans=None,
        sessions=None,
        users=None,
        overviews=None,
        error=None,
    ):
        self.spans = spans or []
        self.sessions = sessions or []
        self.users = users or []
        self.overviews = overviews or []
        self.error = error
        self.calls = []

    def __call__(self, engine, method, path, params=None, body=None, timeout=5.0):
        self.calls.append((method, path, dict(params or {}), body))
        if self.error:
            raise cb.EngineError(self.error)
        if path == "/traces/spans":
            page = params["page"]
            size = params["page_size"]
            return {
                "count": len(self.spans),
                "spans": self.spans[page * size : (page + 1) * size],
            }
        if path == "/traces/sessions":
            return {"count": len(self.sessions), "sessions": self.sessions}
        if path == "/traces/users":
            return {"count": len(self.users), "users": self.users}
        if path == "/traces/overview":
            return {"count": len(self.overviews), "overviews": self.overviews}
        raise AssertionError(f"unexpected path {path}")


@pytest.fixture
def state_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(cb, "STATE_DIR", tmp_path / "breaker")
    return tmp_path / "breaker"


@pytest.fixture
def fake_engine(monkeypatch):
    def install(**kwargs):
        fake = FakeEngine(**kwargs)
        monkeypatch.setattr(cb, "_request", fake)
        return fake

    return install


# ---------------------------------------------------------------------------
# Config discovery
# ---------------------------------------------------------------------------


def test_api_base_url_strips_traces_suffix():
    assert cb.api_base_url("https://host/api/v1/traces") == "https://host/api/v1"
    assert cb.api_base_url("https://host/api/v1/traces/") == "https://host/api/v1"
    assert cb.api_base_url("https://host/api/v1") == "https://host/api/v1"


def test_discover_engine_config_from_env(monkeypatch):
    monkeypatch.setenv("GENAI_ENGINE_API_KEY", "key")
    monkeypatch.setenv("GENAI_ENGINE_TASK_ID", "task")
    monkeypatch.setenv("GENAI_ENGINE_TRACE_ENDPOINT", "http://e/api/v1/traces")
    assert cb.discover_engine_config() == {
        "api_key": "key",
        "task_id": "task",
        "base_url": "http://e/api/v1",
    }


def test_discover_engine_config_from_project_file(tmp_path, monkeypatch):
    for var in (
        "GENAI_ENGINE_API_KEY",
        "GENAI_ENGINE_TASK_ID",
        "GENAI_ENGINE_TRACE_ENDPOINT",
    ):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(tmp_path))
    monkeypatch.setattr(cb.Path, "home", lambda: tmp_path / "nohome")
    (tmp_path / ".claude").mkdir()
    (tmp_path / ".claude" / "arthur_config.json").write_text(
        json.dumps(
            {"api_key": "k", "task_id": "t", "endpoint": "http://e/api/v1/traces"},
        ),
    )
    assert cb.discover_engine_config()["task_id"] == "t"


def test_discover_engine_config_none_when_unconfigured(tmp_path, monkeypatch):
    for var in (
        "GENAI_ENGINE_API_KEY",
        "GENAI_ENGINE_TASK_ID",
        "GENAI_ENGINE_TRACE_ENDPOINT",
    ):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(tmp_path))
    monkeypatch.setattr(cb.Path, "home", lambda: tmp_path / "nohome")
    assert cb.discover_engine_config() is None


def test_load_breaker_config_overlays_file_and_env(tmp_path, monkeypatch):
    path = tmp_path / "breaker.json"
    path.write_text(
        json.dumps({"budget_usd": 5, "scope": "task", "cooldown_minutes": 1}),
    )
    monkeypatch.setenv(cb.CONFIG_ENV, str(path))
    monkeypatch.delenv("ARTHUR_BREAKER_SCOPE", raising=False)
    monkeypatch.setenv("ARTHUR_BREAKER_BUDGET_USD", "7.5")
    config = cb.load_breaker_config()
    assert config["scope"] == "task"
    assert config["budget_usd"] == 7.5  # env beats file
    assert config["cooldown_minutes"] == 1
    assert config["rules"] == cb.DEFAULT_CONFIG["rules"]  # untouched defaults survive


def test_load_breaker_config_rejects_unknown_scope(tmp_path, monkeypatch):
    path = tmp_path / "breaker.json"
    path.write_text(json.dumps({"scope": "galaxy"}))
    monkeypatch.setenv(cb.CONFIG_ENV, str(path))
    monkeypatch.delenv("ARTHUR_BREAKER_SCOPE", raising=False)
    monkeypatch.delenv("ARTHUR_BREAKER_BUDGET_USD", raising=False)
    assert cb.load_breaker_config()["scope"] == "session"


# ---------------------------------------------------------------------------
# Burn-rate math
# ---------------------------------------------------------------------------


def test_burn_rate_is_relative_to_budget_rate():
    config = _config(budget_usd=24.0, budget_period_hours=24.0)  # $1/h budget rate
    assert cb.burn_rate(1.0, 60, config) == pytest.approx(1.0)
    assert cb.burn_rate(1.0, 5, config) == pytest.approx(12.0)
    assert cb.burn_rate(0.0, 5, config) == 0.0
    assert cb.burn_rate(1.0, 0, config) == 0.0


def test_window_spend_only_counts_spans_inside_window():
    spans = [
        cb.LLMSpan(start=NOW - timedelta(minutes=1), cost=1.0, tokens=1),
        cb.LLMSpan(start=NOW - timedelta(minutes=9), cost=2.0, tokens=1),
        cb.LLMSpan(start=NOW - timedelta(minutes=30), cost=4.0, tokens=1),
    ]
    assert cb.window_spend(spans, NOW, 2, None) == 1.0
    assert cb.window_spend(spans, NOW, 10, None) == 3.0
    assert cb.window_spend(spans, NOW, 60, None) == 7.0


def test_span_cost_fallback_pricing():
    unpriced = cb.LLMSpan(
        start=NOW,
        cost=None,
        tokens=1_000_000,
        prompt_tokens=900_000,
        completion_tokens=100_000,
    )
    assert cb.span_cost(unpriced, None) is None
    assert cb.span_cost(unpriced, {"prompt": 3.0, "completion": 15.0}) == pytest.approx(
        0.9 * 3.0 + 0.1 * 15.0,
    )
    priced = cb.LLMSpan(start=NOW, cost=0.5, tokens=10)
    assert cb.span_cost(priced, {"prompt": 3.0, "completion": 15.0}) == 0.5
    empty = cb.LLMSpan(start=NOW, cost=None, tokens=0)
    assert cb.span_cost(empty, None) == 0.0


def test_rule_requires_both_windows_to_exceed_threshold():
    config = _config(
        budget_usd=24.0,
        budget_period_hours=24.0,
        rules=[
            {
                "name": "r",
                "window_minutes": 10,
                "short_window_minutes": 2,
                "burn_rate": 6.0,
            },
        ],
    )
    # $2 spent 8 minutes ago: 10m window burns at 12x, but the last 2m are quiet.
    old_burst = [cb.LLMSpan(start=NOW - timedelta(minutes=8), cost=2.0, tokens=1)]
    (result,) = cb.evaluate_rules(old_burst, NOW, config)
    assert result.window_burn_rate == pytest.approx(12.0)
    assert result.short_burn_rate == 0.0
    assert not result.fired

    # Same spend, still going: $1 in the last minute too.
    ongoing = old_burst + [
        cb.LLMSpan(start=NOW - timedelta(minutes=1), cost=1.0, tokens=1),
    ]
    (result,) = cb.evaluate_rules(ongoing, NOW, config)
    assert result.window_burn_rate == pytest.approx(18.0)
    assert result.short_burn_rate == pytest.approx(30.0)
    assert result.fired


def test_single_window_rule_when_short_window_is_null():
    config = _config(
        budget_usd=24.0,
        budget_period_hours=24.0,
        rules=[
            {
                "name": "r",
                "window_minutes": 10,
                "short_window_minutes": None,
                "burn_rate": 6.0,
            },
        ],
    )
    spans = [cb.LLMSpan(start=NOW - timedelta(minutes=8), cost=2.0, tokens=1)]
    (result,) = cb.evaluate_rules(spans, NOW, config)
    assert result.short_burn_rate is None
    assert result.fired


# ---------------------------------------------------------------------------
# evaluate(): engine queries → Evaluation
# ---------------------------------------------------------------------------


def test_evaluate_queries_llm_spans_for_session_scope(fake_engine):
    fake = fake_engine(spans=[_span_row(1, 0.01)])
    config = _config(scope="session")
    evaluation = cb.evaluate(ENGINE, config, "sess-1", NOW)
    assert not evaluation.tripped
    method, path, params, _ = fake.calls[0]
    assert (method, path) == ("GET", "/traces/spans")
    assert params["task_ids"] == "task-1"
    assert params["session_ids"] == "sess-1"
    assert params["span_types"] == "LLM"
    assert params["end_time"] == "2026-01-01T12:00:00.000Z"
    assert params["start_time"] == "2026-01-01T11:00:00.000Z"  # widest rule window


def test_evaluate_user_scope_filters_by_username(fake_engine, monkeypatch):
    monkeypatch.setenv("USER", "nori")
    fake = fake_engine(spans=[])
    cb.evaluate(ENGINE, _config(scope="user"), "sess-1", NOW)
    assert fake.calls[0][2]["user_ids"] == "nori"
    assert "session_ids" not in fake.calls[0][2]


def test_evaluate_task_scope_has_no_session_or_user_filter(fake_engine):
    fake = fake_engine(spans=[])
    cb.evaluate(ENGINE, _config(scope="task"), "sess-1", NOW)
    params = fake.calls[0][2]
    assert "session_ids" not in params and "user_ids" not in params


def test_evaluate_trips_on_fast_burn(fake_engine):
    # Default config: $100/24h → $4.17/h budget rate; fast-burn trips at 14.4x
    # over 10m AND 2m, i.e. ≥ $10 in 10m and ≥ $2 in 2m.
    fake_engine(spans=[_span_row(1, 3.0), _span_row(5, 8.0)])
    evaluation = cb.evaluate(ENGINE, _config(), "s", NOW)
    assert evaluation.tripped
    assert evaluation.reason.startswith("fast-burn:")
    assert "$11.00 in the last 10m" in evaluation.reason


def test_evaluate_paginates_spans(fake_engine, monkeypatch):
    monkeypatch.setattr(cb, "SPAN_PAGE_SIZE", 2)
    fake = fake_engine(spans=[_span_row(1, 1.0), _span_row(1, 1.0), _span_row(1, 1.0)])
    evaluation = cb.evaluate(ENGINE, _config(), "s", NOW)
    assert [c[2]["page"] for c in fake.calls] == [0, 1]
    assert evaluation.rules[0].window_spend == 3.0


def test_evaluate_warns_near_threshold_without_tripping(fake_engine):
    # fast-burn warns at 0.75 × 14.4 = 10.8x on both windows: $8.10 in 10m is
    # 11.7x and $1.60 in 2m is 11.5x, neither reaching the 14.4x trip line.
    fake_engine(spans=[_span_row(1, 1.6), _span_row(5, 6.5)])
    config = _config(rules=[cb.DEFAULT_CONFIG["rules"][0]])
    evaluation = cb.evaluate(ENGINE, config, "s", NOW)
    assert not evaluation.tripped
    assert "fast-burn" in evaluation.warning
    assert "trips at 14.4x" in evaluation.warning


def test_evaluate_warns_about_unpriced_spans(fake_engine):
    fake_engine(spans=[_span_row(1, None, tokens=5000)])
    evaluation = cb.evaluate(ENGINE, _config(), "s", NOW)
    assert not evaluation.tripped
    assert evaluation.unpriced_spans == 1
    assert evaluation.unpriced_tokens == 5000
    assert "fallback_usd_per_million_tokens" in evaluation.warning


def test_evaluate_prices_unpriced_spans_with_fallback(fake_engine):
    fake_engine(spans=[_span_row(1, None, tokens=1_000_000)])
    config = _config(
        fallback_usd_per_million_tokens={"prompt": 10.0, "completion": 50.0},
        rules=[
            {
                "name": "r",
                "window_minutes": 10,
                "short_window_minutes": None,
                "burn_rate": 1.0,
            },
        ],
    )
    evaluation = cb.evaluate(ENGINE, config, "s", NOW)
    assert evaluation.unpriced_spans == 0
    assert evaluation.tripped


def test_evaluate_hard_cap_session_scope(fake_engine):
    fake = fake_engine(
        spans=[],
        sessions=[{"session_id": "s", "total_token_cost": 42.0}],
    )
    evaluation = cb.evaluate(
        ENGINE,
        _config(scope="session", hard_cap_usd=40),
        "s",
        NOW,
    )
    assert evaluation.tripped
    assert "hard cap" in evaluation.reason
    assert evaluation.scope_total_usd == 42.0
    assert ("GET", "/traces/sessions") in [(c[0], c[1]) for c in fake.calls]


def test_evaluate_hard_cap_task_scope_uses_overview(fake_engine):
    fake = fake_engine(
        spans=[],
        overviews=[{"task_id": "task-1", "trace_token_cost": 10.0}],
    )
    evaluation = cb.evaluate(ENGINE, _config(scope="task", hard_cap_usd=50), "s", NOW)
    assert not evaluation.tripped
    assert evaluation.warning == ""  # $10 is under 75% of the $50 cap
    method, path, _, body = fake.calls[-1]
    assert (method, path) == ("POST", "/traces/overview")
    assert body["task_ids"] == ["task-1"]
    assert body["start_time"] == "2025-12-31T12:00:00.000Z"


def test_evaluate_hard_cap_user_scope_exact_match(fake_engine, monkeypatch):
    monkeypatch.setenv("USER", "nori")
    fake_engine(
        spans=[],
        users=[
            {"user_id": "nori-bot", "total_token_cost": 999.0},
            {"user_id": "nori", "total_token_cost": 1.0},
        ],
    )
    evaluation = cb.evaluate(ENGINE, _config(scope="user", hard_cap_usd=50), "s", NOW)
    assert evaluation.scope_total_usd == 1.0
    assert not evaluation.tripped


def test_evaluate_skips_hard_cap_query_when_unset(fake_engine):
    fake = fake_engine(spans=[])
    cb.evaluate(ENGINE, _config(hard_cap_usd=None), "s", NOW)
    assert [c[1] for c in fake.calls] == ["/traces/spans"]


def test_evaluate_fail_open_on_engine_error(fake_engine):
    fake_engine(error="connection refused")
    evaluation = cb.evaluate(ENGINE, _config(fail_mode="open"), "s", NOW)
    assert not evaluation.tripped
    assert "failing open" in evaluation.warning
    assert evaluation.engine_error == "connection refused"


def test_evaluate_fail_closed_on_engine_error(fake_engine):
    fake_engine(error="HTTP 500")
    evaluation = cb.evaluate(ENGINE, _config(fail_mode="closed"), "s", NOW)
    assert evaluation.tripped
    assert "fail_mode is closed" in evaluation.reason


def test_parse_engine_time_treats_naive_as_utc():
    assert cb.parse_engine_time("2026-01-01T12:00:00.123456") == datetime(
        2026,
        1,
        1,
        12,
        0,
        0,
        123456,
        tzinfo=timezone.utc,
    )
    assert cb.parse_engine_time("2026-01-01T12:00:00Z").tzinfo is not None


# ---------------------------------------------------------------------------
# decide(): the state machine
# ---------------------------------------------------------------------------

TRIP_SPANS = [_span_row(1, 3.0), _span_row(5, 8.0)]


def test_decide_closed_caches_verdict_within_interval(state_dir, fake_engine):
    fake = fake_engine(spans=[_span_row(1, 0.01)])
    config = _config(check_interval_seconds=30)
    first = cb.decide(ENGINE, config, "s", NOW)
    assert not first.tripped and first.fresh
    second = cb.decide(ENGINE, config, "s", NOW + timedelta(seconds=10))
    assert not second.tripped and not second.fresh
    assert len(fake.calls) == 1
    third = cb.decide(ENGINE, config, "s", NOW + timedelta(seconds=31))
    assert third.fresh
    assert len(fake.calls) == 2


def test_decide_trips_and_stays_open_through_cooldown(state_dir, fake_engine):
    fake = fake_engine(spans=TRIP_SPANS)
    config = _config(cooldown_minutes=15)
    verdict = cb.decide(ENGINE, config, "s", NOW)
    assert verdict.tripped and verdict.fresh
    assert "Arthur circuit breaker OPEN" in verdict.message
    assert "fast-burn" in verdict.message
    assert "reset" in verdict.message

    state = cb.load_state(cb.state_key(ENGINE, config, "s"))
    assert state["status"] == cb.STATUS_OPEN

    # Within cooldown: blocked without touching the engine.
    fake.spans = []
    again = cb.decide(ENGINE, config, "s", NOW + timedelta(minutes=5))
    assert again.tripped and not again.fresh
    assert len(fake.calls) == 1


def test_decide_half_open_closes_when_calm(state_dir, fake_engine):
    fake = fake_engine(spans=TRIP_SPANS)
    config = _config(cooldown_minutes=15)
    cb.decide(ENGINE, config, "s", NOW)
    fake.spans = []
    probe = cb.decide(ENGINE, config, "s", NOW + timedelta(minutes=16))
    assert not probe.tripped and probe.fresh
    assert "closed again" in probe.warning
    assert (
        cb.load_state(cb.state_key(ENGINE, config, "s"))["status"] == cb.STATUS_CLOSED
    )


def test_decide_half_open_reopens_when_still_burning(state_dir, fake_engine):
    fake = fake_engine(spans=TRIP_SPANS)
    config = _config(cooldown_minutes=15)
    cb.decide(ENGINE, config, "s", NOW)
    later = NOW + timedelta(minutes=16)
    fake.spans = [_span_row(1, 3.0), _span_row(5, 8.0)]
    # Re-anchor the canned spans to the probe time so they are inside the window.
    for row in fake.spans:
        row["start_time"] = (later - timedelta(minutes=2)).strftime(
            "%Y-%m-%dT%H:%M:%S.%f",
        )
    probe = cb.decide(ENGINE, config, "s", later)
    assert probe.tripped and probe.fresh
    state = cb.load_state(cb.state_key(ENGINE, config, "s"))
    assert state["opened_at"] == later.timestamp()


def test_decide_scope_keys_are_isolated(state_dir, fake_engine):
    fake_engine(spans=TRIP_SPANS)
    session_cfg = _config(scope="session")
    cb.decide(ENGINE, session_cfg, "s1", NOW)
    assert (
        cb.load_state(cb.state_key(ENGINE, session_cfg, "s1"))["status"]
        == cb.STATUS_OPEN
    )
    assert cb.load_state(cb.state_key(ENGINE, session_cfg, "s2")) == {}
    assert cb.state_key(ENGINE, _config(scope="task"), "s1") == cb.state_key(
        ENGINE,
        _config(scope="task"),
        "s2",
    )


def test_reset_clears_state(state_dir, fake_engine):
    fake_engine(spans=TRIP_SPANS)
    config = _config()
    cb.decide(ENGINE, config, "s", NOW)
    assert cb.clear_state() == 1
    assert cb.load_state(cb.state_key(ENGINE, config, "s")) == {}


# ---------------------------------------------------------------------------
# Hook output
# ---------------------------------------------------------------------------


def test_hook_output_blocks_prompt_when_tripped():
    out = cb.hook_output("user_prompt_submit", cb.Verdict(tripped=True, message="OPEN"))
    assert out["decision"] == "block"
    assert out["reason"] == "OPEN"
    assert out["hookSpecificOutput"]["hookEventName"] == "UserPromptSubmit"


def test_hook_output_stops_turn_when_tripped_on_tool():
    out = cb.hook_output("pre_tool", cb.Verdict(tripped=True, message="OPEN"))
    assert out["continue"] is False
    assert out["stopReason"] == "OPEN"
    assert out["hookSpecificOutput"]["permissionDecision"] == "deny"
    assert out["hookSpecificOutput"]["permissionDecisionReason"] == "OPEN"


def test_hook_output_session_start_reports_open_breaker():
    assert cb.hook_output(
        "session_start",
        cb.Verdict(tripped=True, message="OPEN"),
    ) == {
        "systemMessage": "OPEN",
    }
    assert cb.hook_output("session_start", cb.Verdict(tripped=False)) is None


def test_hook_output_warns_only_on_fresh_checks():
    assert cb.hook_output(
        "pre_tool",
        cb.Verdict(tripped=False, warning="w", fresh=True),
    ) == {
        "systemMessage": "w",
    }
    assert (
        cb.hook_output("pre_tool", cb.Verdict(tripped=False, warning="w", fresh=False))
        is None
    )
    assert cb.hook_output("user_prompt_submit", cb.Verdict(tripped=False)) is None


def test_run_hook_noop_without_engine_config(monkeypatch, tmp_path):
    for var in (
        "GENAI_ENGINE_API_KEY",
        "GENAI_ENGINE_TASK_ID",
        "GENAI_ENGINE_TRACE_ENDPOINT",
    ):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(tmp_path))
    monkeypatch.setattr(cb.Path, "home", lambda: tmp_path / "nohome")
    assert cb.run_hook("pre_tool", {"session_id": "s"}) is None


def test_run_hook_bypass_env(monkeypatch):
    monkeypatch.setenv(cb.BYPASS_ENV, "1")
    monkeypatch.setattr(
        cb,
        "discover_engine_config",
        lambda: pytest.fail("should not run"),
    )
    assert cb.run_hook("pre_tool", {"session_id": "s"}) is None


def test_run_hook_disabled_config(monkeypatch, state_dir):
    monkeypatch.delenv(cb.BYPASS_ENV, raising=False)
    monkeypatch.setattr(cb, "discover_engine_config", lambda: ENGINE)
    monkeypatch.setattr(cb, "load_breaker_config", lambda: _config(enabled=False))
    monkeypatch.setattr(cb, "_request", lambda *a, **k: pytest.fail("should not query"))
    assert cb.run_hook("pre_tool", {"session_id": "s"}) is None


def test_run_hook_end_to_end_trip(monkeypatch, state_dir, fake_engine):
    monkeypatch.delenv(cb.BYPASS_ENV, raising=False)
    monkeypatch.setattr(cb, "discover_engine_config", lambda: ENGINE)
    monkeypatch.setattr(cb, "load_breaker_config", lambda: _config())
    real_now = datetime.now(timezone.utc)
    fake_engine(
        spans=[_span_row(0.5, 3.0, now=real_now), _span_row(0.6, 8.0, now=real_now)],
    )
    out = cb.run_hook("user_prompt_submit", {"session_id": "s"})
    assert out["decision"] == "block"
    out = cb.run_hook("pre_tool", {"session_id": "s"})
    assert out["continue"] is False
