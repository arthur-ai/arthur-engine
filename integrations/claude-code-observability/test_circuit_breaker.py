"""
Unit tests for claude_code_circuit_breaker.py

Run with:  python3 -m pytest integrations/claude-code-observability/test_circuit_breaker.py -v
"""

import io
import json
import os
import sys
import time
import urllib.error
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))
import claude_code_circuit_breaker as cb

NOW = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
ENGINE = {"api_key": "k", "task_id": "task-1", "base_url": "http://engine/api/v1"}


def _config(**overrides) -> dict:
    config = json.loads(json.dumps(cb.DEFAULT_CONFIG))
    # The burn-rate arithmetic in these tests is worked out on $100/24h
    # ($4.17/h), whatever the scope's default budget is.
    config["budget_usd"] = 100.0
    config.update(overrides)
    return config


def _engine_time(dt: datetime) -> str:
    # The engine returns naive timestamps.
    return dt.strftime("%Y-%m-%dT%H:%M:%S.%f")


def _span_row(
    minutes_ago: float,
    cost,
    tokens: int = 1000,
    now: datetime = NOW,
    user_id: str = "nori",
    duration_minutes: float = 0.0,
    turn_started_minutes_ago: float = None,
) -> dict:
    end = now - timedelta(minutes=minutes_ago)
    start = end - timedelta(minutes=duration_minutes)
    turn_start = (
        start
        if turn_started_minutes_ago is None
        else now - timedelta(minutes=turn_started_minutes_ago)
    )
    return {
        "start_time": _engine_time(start),
        "end_time": _engine_time(end),
        # Not in the API response: the start of the span's trace (its turn),
        # which the fake engine's time filters apply to, as the real one's do.
        "trace_start_time": _engine_time(turn_start),
        "user_id": user_id,
        "total_token_cost": cost,
        "total_token_count": tokens,
        "prompt_token_count": tokens - 100,
        "completion_token_count": 100,
    }


def _page(rows: list, params: dict) -> list:
    page, size = params["page"], params["page_size"]
    return rows[page * size : (page + 1) * size]


class FakeEngine:
    """Replaces cb._request; records calls and serves canned responses."""

    def __init__(
        self,
        spans=None,
        sessions=None,
        traces=None,
        overviews=None,
        error=None,
    ):
        self.spans = spans or []
        self.sessions = sessions or []
        self.traces = traces or []
        self.overviews = overviews or []
        self.error = error
        self.calls = []

    def __call__(self, engine, method, path, params=None, body=None, timeout=5.0):
        self.calls.append((method, path, dict(params or {}), body))
        if self.error:
            raise cb.EngineError(self.error)
        if path == "/traces/spans":
            # Like the engine, start_time filters on the trace, not the span.
            rows = [
                r
                for r in self.spans
                if "start_time" not in params
                or r["trace_start_time"] >= params["start_time"]
            ]
            return {"count": len(rows), "spans": _page(rows, params)}
        if path == "/traces":
            return {"count": len(self.traces), "traces": _page(self.traces, params)}
        if path == "/traces/sessions":
            return {"count": len(self.sessions), "sessions": self.sessions}
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
    monkeypatch.delenv("GENAI_ENGINE_READ_API_KEY", raising=False)
    monkeypatch.setattr(cb.Path, "home", lambda: Path("/nonexistent"))
    assert cb.discover_engine_config() == {
        "api_key": "key",
        "key_name": "api_key",
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
    # Degenerate budgets never divide by zero (a bad config must not fail open).
    assert cb.burn_rate(1.0, 5, _config(budget_period_hours=0)) == 0.0
    assert cb.burn_rate(1.0, 5, _config(budget_usd=0)) == 0.0


def test_window_spend_only_counts_spans_inside_window():
    spans = [
        cb.LLMSpan(end=NOW - timedelta(minutes=1), cost=1.0, tokens=1),
        cb.LLMSpan(end=NOW - timedelta(minutes=9), cost=2.0, tokens=1),
        cb.LLMSpan(end=NOW - timedelta(minutes=30), cost=4.0, tokens=1),
    ]
    assert cb.window_spend(spans, NOW, 2, None) == 1.0
    assert cb.window_spend(spans, NOW, 10, None) == 3.0
    assert cb.window_spend(spans, NOW, 60, None) == 7.0


def test_span_cost_fallback_pricing():
    unpriced = cb.LLMSpan(
        end=NOW,
        cost=None,
        tokens=1_000_000,
        prompt_tokens=900_000,
        completion_tokens=100_000,
    )
    assert cb.span_cost(unpriced, None) is None
    assert cb.span_cost(unpriced, {"prompt": 3.0, "completion": 15.0}) == pytest.approx(
        0.9 * 3.0 + 0.1 * 15.0,
    )
    priced = cb.LLMSpan(end=NOW, cost=0.5, tokens=10)
    assert cb.span_cost(priced, {"prompt": 3.0, "completion": 15.0}) == 0.5
    empty = cb.LLMSpan(end=NOW, cost=None, tokens=0)
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
    old_burst = [cb.LLMSpan(end=NOW - timedelta(minutes=8), cost=2.0, tokens=1)]
    (result,) = cb.evaluate_rules(old_burst, NOW, config)
    assert result.window_burn_rate == pytest.approx(12.0)
    assert result.short_burn_rate == 0.0
    assert not result.fired

    # Same spend, still going: $1 in the last minute too.
    ongoing = old_burst + [
        cb.LLMSpan(end=NOW - timedelta(minutes=1), cost=1.0, tokens=1),
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
    spans = [cb.LLMSpan(end=NOW - timedelta(minutes=8), cost=2.0, tokens=1)]
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
    assert (params["sort"], params["sort_by"]) == ("desc", "start_time")
    # The engine's time filters apply to the trace, so none are sent.
    assert "start_time" not in params and "end_time" not in params
    assert (params["page"], params["page_size"]) == (0, cb.SPAN_FIRST_PAGE_SIZE)


def test_evaluate_buckets_spend_at_span_end(fake_engine):
    # A 4-minute LLM call that finished 1 minute ago belongs to the last 2
    # minutes even though it started before them.
    fake_engine(spans=[_span_row(1, 3.0, duration_minutes=4), _span_row(5, 8.0)])
    evaluation = cb.evaluate(ENGINE, _config(), "s", NOW)
    fast = evaluation.rules[0]
    assert fast.short_spend == 3.0
    assert evaluation.tripped


def test_evaluate_user_scope_filters_by_username(fake_engine, monkeypatch):
    monkeypatch.setenv("USER", "nori")
    # The engine's user_ids filter is a substring match, so it also returns
    # "nori-bot"; only exact matches may count.
    fake = fake_engine(
        spans=[_span_row(1, 50.0, user_id="nori-bot"), _span_row(1, 0.01)],
    )
    evaluation = cb.evaluate(ENGINE, _config(scope="user"), "sess-1", NOW)
    assert fake.calls[0][2]["user_ids"] == "nori"
    assert "session_ids" not in fake.calls[0][2]
    assert evaluation.rules[0].window_spend == 0.01
    assert not evaluation.tripped


def test_evaluate_hard_cap_only_config_skips_span_query(fake_engine):
    fake = fake_engine(
        spans=[],
        sessions=[{"session_id": "s", "total_token_cost": 60.0}],
    )
    evaluation = cb.evaluate(ENGINE, _config(rules=[], hard_cap_usd=50), "s", NOW)
    assert evaluation.tripped
    assert "hard cap" in evaluation.reason
    assert [c[1] for c in fake.calls] == ["/traces/sessions"]


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
    monkeypatch.setattr(cb, "SPAN_FIRST_PAGE_SIZE", 2)
    fake = fake_engine(spans=[_span_row(1, 1.0), _span_row(1, 1.0), _span_row(1, 1.0)])
    evaluation = cb.evaluate(ENGINE, _config(), "s", NOW)
    assert [(c[2]["page"], c[2]["page_size"]) for c in fake.calls] == [(0, 2), (1, 2)]
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
    # Time filters go out in the engine's zone without an offset.
    assert body["start_time"] == "2025-12-31T12:00:00.000"


def test_evaluate_hard_cap_user_scope_sums_own_traces_in_period(
    fake_engine,
    monkeypatch,
):
    monkeypatch.setenv("USER", "nori")
    fake = fake_engine(
        spans=[],
        traces=[
            {"trace_id": "a", "user_id": "nori-bot", "total_token_cost": 999.0},
            {"trace_id": "b", "user_id": "nori", "total_token_cost": 1.0},
            {"trace_id": "c", "user_id": "nori", "total_token_cost": 2.5},
        ],
    )
    evaluation = cb.evaluate(ENGINE, _config(scope="user", hard_cap_usd=50), "s", NOW)
    assert evaluation.scope_total_usd == 3.5
    assert not evaluation.tripped
    method, path, params, _ = fake.calls[-1]
    assert (method, path) == ("GET", "/traces")
    assert params["user_ids"] == "nori"
    assert params["start_time"] == "2025-12-31T12:00:00.000"


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
    assert state["cooldown_until"] == (NOW + timedelta(minutes=15)).timestamp()

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
    # Still burning at probe time.
    fake.spans = [_span_row(1, 3.0, now=later), _span_row(5, 8.0, now=later)]
    probe = cb.decide(ENGINE, config, "s", later)
    assert probe.tripped and probe.fresh
    state = cb.load_state(cb.state_key(ENGINE, config, "s"))
    assert state["opened_at"] == later.timestamp()
    assert state["cooldown_until"] == (later + timedelta(minutes=15)).timestamp()


def test_decide_half_open_stays_open_when_engine_unreachable(state_dir, fake_engine):
    fake = fake_engine(spans=TRIP_SPANS)
    config = _config(cooldown_minutes=15, fail_mode="open")
    cb.decide(ENGINE, config, "s", NOW)
    fake.error = "connection refused"
    probe = cb.decide(ENGINE, config, "s", NOW + timedelta(minutes=16))
    assert probe.tripped and probe.fresh
    assert "re-check failed" in probe.message
    state = cb.load_state(cb.state_key(ENGINE, config, "s"))
    assert state["status"] == cb.STATUS_OPEN
    assert state["opened_at"] == NOW.timestamp()  # cooldown not restarted
    # Engine back and calm: the next hook probes again and closes.
    fake.error = None
    fake.spans = []
    assert not cb.decide(ENGINE, config, "s", NOW + timedelta(minutes=17)).tripped


def test_save_state_prunes_stale_files(state_dir):
    state_dir.mkdir(parents=True)
    import os

    old_ts = NOW.timestamp() - cb.STATE_MAX_AGE_S - 60
    for name in ("old.json", "old.lock"):
        (state_dir / name).write_text("{}")
        os.utime(state_dir / name, (old_ts, old_ts))
    (state_dir / "recent.json").write_text("{}")
    (state_dir / "notes.txt").write_text("keep")
    cb.save_state("current", {"status": "closed"})
    remaining = sorted(p.name for p in state_dir.iterdir())
    assert remaining == ["current.json", "notes.txt", "recent.json"]


def test_prune_ages_open_state_from_its_cooldown_end(state_dir):
    state_dir.mkdir(parents=True)
    import os

    now = NOW.timestamp()
    old_ts = now - cb.STATE_MAX_AGE_S - 60
    files = {
        # Still cooling down: kept however old the file is.
        "open.json": {"status": cb.STATUS_OPEN, "cooldown_until": now + 1},
        # Cooldown ended recently: kept so the half-open probe can run.
        "waiting.json": {"status": cb.STATUS_OPEN, "cooldown_until": now - 60},
        # Cooldown ended longer ago than the prune age: nobody is coming back.
        "lapsed.json": {
            "status": cb.STATUS_OPEN,
            "cooldown_until": now - cb.STATE_MAX_AGE_S - 1,
        },
        "legacy.json": {"status": cb.STATUS_OPEN},  # written before cooldown_until
        "bad.json": {"status": cb.STATUS_OPEN, "cooldown_until": "soon"},
        "closed.json": {"status": cb.STATUS_CLOSED, "cooldown_until": now + 1},
    }
    for name, state in files.items():
        (state_dir / name).write_text(json.dumps(state))
        os.utime(state_dir / name, (old_ts, old_ts))
    cb._prune_stale_state(exclude="current", now_ts=now)
    assert sorted(p.name for p in state_dir.iterdir()) == ["open.json", "waiting.json"]


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


def test_cli_status_rejects_missing_session_value(monkeypatch, capsys):
    monkeypatch.setattr(cb, "discover_engine_config", lambda: ENGINE)
    monkeypatch.setattr(cb, "load_breaker_config", lambda: _config())
    assert cb.cli_status(["--session"]) == 2
    assert "usage" in capsys.readouterr().err


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


# ---------------------------------------------------------------------------
# Override from inside Claude Code
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "prompt, minutes",
    [
        ("breaker override", 30.0),
        ("  Circuit breaker override", 30.0),
        ("circuit-breaker bypass", 30.0),
        ("arthur breaker: override", 30.0),
        ("override the breaker", 30.0),
        ("override the arthur circuit breaker and carry on", 30.0),
        ("breaker override for 45m", 45.0),
        ("breaker override 10 minutes", 10.0),
        ("override the breaker for 2h", 120.0),
        ("breaker override for 1.5 hours", 90.0),
    ],
)
def test_parse_override_matches_override_prompts(prompt, minutes):
    assert cb.parse_override(prompt, _config(override_minutes=30)) == minutes


@pytest.mark.parametrize(
    "prompt",
    [
        "",
        "fix the circuit breaker override test",
        "the breaker tripped, why?",
        "override this function",
        "breaker status",
        "please breaker override",
    ],
)
def test_parse_override_ignores_ordinary_prompts(prompt):
    assert cb.parse_override(prompt, _config()) is None


def test_parse_override_uses_configured_default_minutes():
    assert cb.parse_override("breaker override", _config(override_minutes=5)) == 5.0


def test_decide_honours_override_until_it_lapses(state_dir, fake_engine):
    fake = fake_engine(spans=TRIP_SPANS)
    config = _config(override_minutes=30)
    tripped = cb.decide(ENGINE, config, "s", NOW)
    assert tripped.tripped

    message = cb.override(ENGINE, config, "s", 30, NOW + timedelta(minutes=1))
    assert "overridden" in message and "was open" in message
    state = cb.load_state(cb.state_key(ENGINE, config, "s"))
    assert state["status"] == cb.STATUS_CLOSED
    assert state["override_until"] == (NOW + timedelta(minutes=31)).timestamp()

    # Lifted: no engine query, nothing blocked, even though spend is still high.
    calls = len(fake.calls)
    lifted = cb.decide(ENGINE, config, "s", NOW + timedelta(minutes=20))
    assert not lifted.tripped and not lifted.fresh
    assert len(fake.calls) == calls

    # Lapsed: the regular check runs again and trips on the same spend.
    later = NOW + timedelta(minutes=32)
    fake.spans = [_span_row(1, 3.0, now=later), _span_row(5, 8.0, now=later)]
    again = cb.decide(ENGINE, config, "s", later)
    assert again.tripped and again.fresh


def test_override_is_scoped_like_the_state_key(state_dir, fake_engine):
    fake_engine(spans=TRIP_SPANS)
    config = _config()
    cb.decide(ENGINE, config, "s1", NOW)
    cb.decide(ENGINE, config, "s2", NOW)
    cb.override(ENGINE, config, "s1", 30, NOW)
    assert not cb.decide(ENGINE, config, "s1", NOW + timedelta(minutes=1)).tripped
    assert cb.decide(ENGINE, config, "s2", NOW + timedelta(minutes=1)).tripped


def test_run_hook_override_prompt_lifts_open_breaker(
    monkeypatch,
    state_dir,
    fake_engine,
):
    monkeypatch.delenv(cb.BYPASS_ENV, raising=False)
    monkeypatch.setattr(cb, "discover_engine_config", lambda: ENGINE)
    monkeypatch.setattr(cb, "load_breaker_config", lambda: _config())
    real_now = datetime.now(timezone.utc)
    fake_engine(
        spans=[_span_row(0.5, 3.0, now=real_now), _span_row(0.6, 8.0, now=real_now)],
    )
    blocked = cb.run_hook("user_prompt_submit", {"session_id": "s", "prompt": "go on"})
    assert blocked["decision"] == "block"
    assert "breaker override" in blocked["reason"]

    out = cb.run_hook(
        "user_prompt_submit",
        {"session_id": "s", "prompt": "breaker override for 10m"},
    )
    # The override prompt is consumed so Claude does not take it as "carry on".
    assert out["decision"] == "block"
    assert "lifted for 10 min" in out["reason"]
    assert "not sent to Claude" in out["reason"]
    assert out["hookSpecificOutput"]["hookEventName"] == "UserPromptSubmit"

    # The in-flight turn's tool calls are no longer stopped.
    assert cb.run_hook("pre_tool", {"session_id": "s"}) is None
    assert (
        cb.run_hook("user_prompt_submit", {"session_id": "s", "prompt": "continue"})
        is None
    )


def test_run_hook_override_prompt_ignored_when_disabled(monkeypatch, state_dir):
    monkeypatch.delenv(cb.BYPASS_ENV, raising=False)
    monkeypatch.setattr(cb, "discover_engine_config", lambda: ENGINE)
    monkeypatch.setattr(cb, "load_breaker_config", lambda: _config(enabled=False))
    assert (
        cb.run_hook(
            "user_prompt_submit",
            {"session_id": "s", "prompt": "breaker override"},
        )
        is None
    )
    assert not state_dir.exists() or not list(state_dir.glob("*.json"))


def test_open_message_mentions_override_prompt():
    config = _config(override_minutes=30, cooldown_minutes=15)
    msg = cb._open_message(
        {"opened_at": NOW.timestamp(), "reason": "fast-burn"},
        config,
        NOW.timestamp(),
    )
    assert '"breaker override"' in msg and "30 min" in msg


# ---------------------------------------------------------------------------
# CodeRabbit follow-ups
# ---------------------------------------------------------------------------


def test_load_breaker_config_ignores_invalid_env_budget(tmp_path, monkeypatch):
    monkeypatch.delenv(cb.CONFIG_ENV, raising=False)
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(tmp_path))
    monkeypatch.setattr(cb.Path, "home", lambda: tmp_path / "nohome")
    monkeypatch.delenv("ARTHUR_BREAKER_SCOPE", raising=False)
    monkeypatch.setenv("ARTHUR_BREAKER_BUDGET_USD", "$50")
    assert cb.budget_usd(cb.load_breaker_config()) == cb.SCOPE_BUDGET_USD["session"]


def test_load_breaker_config_replaces_non_positive_budget_values(tmp_path, monkeypatch):
    path = tmp_path / "breaker.json"
    path.write_text(json.dumps({"budget_usd": "lots", "budget_period_hours": 0}))
    monkeypatch.setenv(cb.CONFIG_ENV, str(path))
    monkeypatch.delenv("ARTHUR_BREAKER_SCOPE", raising=False)
    monkeypatch.delenv("ARTHUR_BREAKER_BUDGET_USD", raising=False)
    config = cb.load_breaker_config()
    assert cb.budget_usd(config) == cb.SCOPE_BUDGET_USD["session"]
    assert config["budget_period_hours"] == cb.DEFAULT_CONFIG["budget_period_hours"]


def test_evaluate_flags_truncated_span_query(fake_engine, monkeypatch):
    monkeypatch.setattr(cb, "SPAN_FIRST_PAGE_SIZE", 1)
    monkeypatch.setattr(cb, "SPAN_MAX_ROWS", 1)
    fake_engine(spans=[_span_row(1, 0.01), _span_row(2, 0.01)])
    evaluation = cb.evaluate(ENGINE, _config(), "s", NOW)
    assert evaluation.truncated
    assert "lower bound" in evaluation.warning
    assert evaluation.rules[0].window_spend == 0.01  # only the page we got


def test_open_message_shows_remaining_minutes_and_zone():
    config = _config(cooldown_minutes=15)
    state = {"opened_at": NOW.timestamp(), "reason": "fast-burn"}
    message = cb._open_message(state, config, NOW.timestamp() + 5 * 60)
    assert "paused for another 10 min" in message
    retry_local = datetime.fromtimestamp(
        NOW.timestamp() + 15 * 60,
        tz=timezone.utc,
    ).astimezone()
    assert f"until {retry_local.strftime('%H:%M %Z')}" in message


# ---------------------------------------------------------------------------
# End-to-end review follow-ups
# ---------------------------------------------------------------------------


def _refuse_key(*args, **kwargs):
    raise cb.EngineAuthError("HTTP 403 from GET /traces/spans (using api_key)")


def test_user_hard_cap_reports_a_cut_off_total(fake_engine, monkeypatch):
    monkeypatch.setenv("USER", "nori")
    monkeypatch.setattr(cb, "SPAN_FIRST_PAGE_SIZE", 2)
    fake_engine(
        spans=[],
        traces=[
            {"trace_id": f"t{i}", "user_id": "nori", "total_token_cost": 1.0}
            for i in range(6)
        ],
    )
    # One read for the (empty) span query, one trace page, then out of time.
    config = _config(scope="user", hard_cap_usd=50)
    evaluation = cb.evaluate(ENGINE, config, "s", NOW, _ExpiringDeadline(2))
    assert evaluation.scope_total_usd == 2.0
    assert evaluation.truncated
    assert "hard-cap total is a lower bound" in evaluation.warning
    # A complete read is not flagged.
    complete = cb.evaluate(ENGINE, config, "s", NOW)
    assert complete.scope_total_usd == 6.0
    assert not complete.truncated and complete.warning == ""


def test_evaluate_null_rules_keeps_the_hard_cap(fake_engine):
    fake = fake_engine(sessions=[{"session_id": "s", "total_token_cost": 60.0}])
    evaluation = cb.evaluate(ENGINE, _config(rules=None, hard_cap_usd=50), "s", NOW)
    assert evaluation.tripped and "hard cap" in evaluation.reason
    assert evaluation.rules == []
    assert [c[1] for c in fake.calls] == ["/traces/sessions"]


def test_budget_defaults_by_scope():
    unset = dict(cb.DEFAULT_CONFIG)
    assert unset["budget_usd"] is None
    assert cb.budget_usd(dict(unset, scope="session")) == 200.0
    # A user's parallel sessions share one budget.
    assert cb.budget_usd(dict(unset, scope="user")) == 600.0
    assert cb.budget_usd(dict(unset, scope="task")) is None
    assert cb.budget_usd(dict(unset, scope="task", budget_usd=1000)) == 1000.0


def test_task_scope_without_a_budget_runs_no_rules(fake_engine):
    fake = fake_engine(spans=[_span_row(1, 500.0)])
    config = _config(scope="task", budget_usd=None)
    assert "budget_usd is not set" in cb.config_problem(config)
    evaluation = cb.evaluate(ENGINE, config, "s", NOW)
    assert not evaluation.tripped and evaluation.rules == []
    assert fake.calls == []
    # The hard cap still applies.
    fake.overviews = [{"task_id": "task-1", "trace_token_cost": 900.0}]
    capped = cb.evaluate(ENGINE, dict(config, hard_cap_usd=800), "s", NOW)
    assert capped.tripped and "hard cap" in capped.reason
    assert cb.config_problem(_config(scope="task", budget_usd=1000)) == ""


def test_session_start_reports_a_missing_task_budget(
    monkeypatch,
    state_dir,
    fake_engine,
):
    monkeypatch.delenv(cb.BYPASS_ENV, raising=False)
    monkeypatch.setattr(cb, "discover_engine_config", lambda: ENGINE)
    monkeypatch.setattr(
        cb,
        "load_breaker_config",
        lambda: _config(scope="task", budget_usd=None),
    )
    fake_engine(spans=[])
    out = cb.run_hook("session_start", {"session_id": "s"})
    assert "budget_usd is not set" in out["systemMessage"]


def test_discover_engine_config_prefers_read_key(tmp_path, monkeypatch):
    monkeypatch.setenv("GENAI_ENGINE_API_KEY", "write-key")
    monkeypatch.delenv("GENAI_ENGINE_READ_API_KEY", raising=False)
    monkeypatch.setenv("GENAI_ENGINE_TASK_ID", "task")
    monkeypatch.setenv("GENAI_ENGINE_TRACE_ENDPOINT", "http://e/api/v1/traces")
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(tmp_path))
    monkeypatch.setattr(cb.Path, "home", lambda: tmp_path / "home")
    (tmp_path / "home" / ".claude").mkdir(parents=True)
    # A read key in a config file beats the tracer's key from the environment.
    (tmp_path / "home" / ".claude" / "arthur_config.json").write_text(
        json.dumps({"read_api_key": "file-read-key"}),
    )
    engine = cb.discover_engine_config()
    assert (engine["api_key"], engine["key_name"]) == ("file-read-key", "read_api_key")
    monkeypatch.setenv("GENAI_ENGINE_READ_API_KEY", "env-read-key")
    assert cb.discover_engine_config()["api_key"] == "env-read-key"


def test_request_reports_401_and_403_as_auth_errors(monkeypatch):
    def refuse(code):
        def urlopen(req, timeout):
            raise urllib.error.HTTPError(
                req.full_url,
                code,
                "Forbidden",
                {},
                io.BytesIO(b'{"detail":"Permission denied"}'),
            )

        return urlopen

    engine = dict(ENGINE, key_name="api_key")
    for code in (401, 403):
        monkeypatch.setattr(cb.urllib.request, "urlopen", refuse(code))
        with pytest.raises(cb.EngineAuthError, match=f"HTTP {code}.*using api_key"):
            cb._request(engine, "GET", "/traces/spans")
    monkeypatch.setattr(cb.urllib.request, "urlopen", refuse(500))
    with pytest.raises(cb.EngineError) as excinfo:
        cb._request(engine, "GET", "/traces/spans")
    assert not isinstance(excinfo.value, cb.EngineAuthError)


def test_evaluate_names_the_read_key_on_auth_failure(monkeypatch):
    monkeypatch.setattr(cb, "_request", _refuse_key)
    evaluation = cb.evaluate(ENGINE, _config(fail_mode="open"), "s", NOW)
    assert not evaluation.tripped
    assert "refused the breaker's key" in evaluation.warning
    assert "read_api_key" in evaluation.warning
    closed = cb.evaluate(ENGINE, _config(fail_mode="closed"), "s", NOW)
    assert closed.tripped and "read_api_key" in closed.reason


def test_evaluate_counts_a_turn_that_started_before_the_window(fake_engine):
    # A 3-hour autonomous turn is one trace that started long before the
    # widest window; its recent LLM spans must still count.
    fake_engine(
        spans=[
            _span_row(1, 3.0, turn_started_minutes_ago=180),
            _span_row(5, 8.0, turn_started_minutes_ago=180),
        ],
    )
    evaluation = cb.evaluate(ENGINE, _config(), "s", NOW)
    assert evaluation.rules[0].window_spend == 11.0
    assert evaluation.tripped


def test_span_pages_grow_and_tile_the_list(fake_engine, monkeypatch):
    monkeypatch.setattr(cb, "SPAN_FIRST_PAGE_SIZE", 2)
    monkeypatch.setattr(cb, "SPAN_MAX_PAGE_SIZE", 4)
    rows = [dict(_span_row(1, 1.0), id=f"span-{i}") for i in range(13)]
    fake = fake_engine(spans=rows)
    evaluation = cb.evaluate(ENGINE, _config(), "s", NOW)
    pages = [(c[2]["page"], c[2]["page_size"]) for c in fake.calls]
    # Rows 0-1, 2-3, 4-7, 8-11, 12.
    assert pages == [(0, 2), (1, 2), (1, 4), (2, 4), (3, 4)]
    assert evaluation.rules[0].window_spend == 13.0


def test_span_paging_stops_once_spans_predate_the_window(fake_engine, monkeypatch):
    monkeypatch.setattr(cb, "SPAN_FIRST_PAGE_SIZE", 2)
    recent = [_span_row(1, 1.0), _span_row(2, 1.0)]
    # The widest window is 60m, plus 15m of slack: these started 2h ago.
    old = [_span_row(120, 50.0) for _ in range(6)]
    fake = fake_engine(spans=recent + old)
    evaluation = cb.evaluate(ENGINE, _config(), "s", NOW)
    assert len(fake.calls) == 2  # the second page reached the old spans
    assert evaluation.rules[1].window_spend == 2.0
    assert not evaluation.truncated


def test_span_paging_drops_rows_repeated_across_pages(monkeypatch):
    # A span inserted between two page reads pushes the last row of the first
    # page onto the second; it must be counted once.
    rows = [dict(_span_row(1, 1.0), id=f"span-{i}") for i in range(3)]
    pages = {0: rows[:2], 1: rows[1:3]}

    def engine(engine, method, path, params=None, body=None, timeout=5.0):
        return {"spans": pages.get(params["page"], [])}

    monkeypatch.setattr(cb, "_request", engine)
    monkeypatch.setattr(cb, "SPAN_FIRST_PAGE_SIZE", 2)
    evaluation = cb.evaluate(ENGINE, _config(), "s", NOW)
    assert evaluation.rules[0].window_spend == 3.0


class _ExpiringDeadline(cb.Deadline):
    """Has time for the first `requests` reads, then none."""

    def __init__(self, requests: int):
        super().__init__(60)
        self.left = requests

    def remaining(self) -> float:
        return 60.0 if self.left > 0 else 0.0

    def timeout(self, per_request: float) -> float:
        if self.left <= 0:
            raise cb.EngineError("no reply within the query budget")
        self.left -= 1
        return per_request


def test_span_paging_stops_at_the_query_budget(fake_engine, monkeypatch):
    monkeypatch.setattr(cb, "SPAN_FIRST_PAGE_SIZE", 2)
    fake = fake_engine(spans=[_span_row(1, 1.0) for _ in range(6)])
    evaluation = cb.evaluate(ENGINE, _config(), "s", NOW, _ExpiringDeadline(1))
    assert len(fake.calls) == 1
    assert evaluation.truncated
    assert "query budget" in evaluation.warning
    assert evaluation.rules[0].window_spend == 2.0  # the page it did read


def test_evaluate_fails_as_configured_when_the_budget_is_spent(fake_engine):
    fake_engine(spans=[_span_row(1, 1.0)])
    evaluation = cb.evaluate(ENGINE, _config(), "s", NOW, _ExpiringDeadline(0))
    assert not evaluation.tripped
    assert "query budget" in evaluation.engine_error


def test_deadline_caps_each_request_at_the_time_left():
    deadline = cb.Deadline(2.0)
    assert deadline.timeout(5.0) <= 2.0
    assert deadline.timeout(0.5) == 0.5
    with pytest.raises(cb.EngineError):
        cb.Deadline(0).timeout(5.0)


@pytest.fixture
def pacific_machine():
    """Run the test with this machine's zone set to US Pacific."""
    saved = os.environ.get("TZ")
    os.environ["TZ"] = "America/Los_Angeles"
    time.tzset()
    yield
    if saved is None:
        os.environ.pop("TZ", None)
    else:
        os.environ["TZ"] = saved
    time.tzset()


def test_parse_engine_time_reads_naive_times_in_engine_timezone(pacific_machine):
    noon_utc = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
    # 04:00 Pacific (UTC-8 in January) is 12:00 UTC.
    la = _config(engine_timezone="America/Los_Angeles")
    local = _config(engine_timezone="local")
    assert cb.parse_engine_time("2026-01-01T04:00:00", la) == noon_utc
    assert cb.parse_engine_time("2026-01-01T04:00:00", local) == noon_utc
    assert cb.parse_engine_time("2026-01-01T12:00:00", _config()) == noon_utc
    # An explicit offset wins over the setting.
    assert cb.parse_engine_time("2026-01-01T12:00:00Z", la) == noon_utc
    assert cb._engine_time_param(noon_utc, la) == "2026-01-01T04:00:00.000"
    assert cb._engine_time_param(noon_utc, local) == "2026-01-01T04:00:00.000"


def test_load_breaker_config_rejects_unknown_engine_timezone(tmp_path, monkeypatch):
    path = tmp_path / "breaker.json"
    path.write_text(json.dumps({"engine_timezone": "Mars/Olympus_Mons"}))
    monkeypatch.setenv(cb.CONFIG_ENV, str(path))
    monkeypatch.delenv("ARTHUR_BREAKER_SCOPE", raising=False)
    monkeypatch.delenv("ARTHUR_BREAKER_BUDGET_USD", raising=False)
    assert cb.load_breaker_config()["engine_timezone"] == "UTC"


def test_evaluate_counts_spend_from_a_pacific_engine(fake_engine):
    # The engine stamps spans in Pacific time; read as UTC they would look
    # 8 hours old and the breaker would see $0.
    pacific_now = NOW.astimezone(timezone(timedelta(hours=-8))).replace(tzinfo=None)
    fake_engine(
        spans=[
            _span_row(1, 3.0, now=pacific_now),
            _span_row(5, 8.0, now=pacific_now),
        ],
    )
    assert not cb.evaluate(ENGINE, _config(), "s", NOW).tripped
    la = _config(engine_timezone="America/Los_Angeles")
    assert cb.evaluate(ENGINE, la, "s", NOW).tripped


def _newest_span(end: datetime, created: datetime) -> dict:
    return {
        "start_time": _engine_time(end - timedelta(seconds=5)),
        "end_time": _engine_time(end),
        "created_at": _engine_time(created),
    }


def test_clock_check_is_quiet_when_times_agree(fake_engine):
    fake_engine(spans=[])
    assert cb.check_engine_clock(ENGINE, _config(), cb.Deadline(), NOW) == ""
    end = NOW - timedelta(minutes=3)
    # A couple of minutes of ingest lag is not a zone offset.
    fake_engine(spans=[_newest_span(end, end + timedelta(minutes=2))])
    assert cb.check_engine_clock(ENGINE, _config(), cb.Deadline(), NOW) == ""


def test_clock_check_flags_spans_in_the_future(fake_engine):
    # A UTC+9 engine read as UTC: its newest span ends 9 hours from now.
    tokyo_wall = NOW + timedelta(hours=9)
    fake_engine(spans=[_newest_span(tokyo_wall, tokyo_wall)])
    warning = cb.check_engine_clock(ENGINE, _config(), cb.Deadline(), NOW)
    assert "9.0h in the future" in warning
    assert "engine_timezone" in warning


def test_clock_check_flags_a_local_time_engine_beside_a_utc_database(
    fake_engine,
    pacific_machine,
):
    # `uv run serve` on a Pacific laptop with Postgres in a container: the
    # engine stamps spans in Pacific time, the database stamps created_at in UTC.
    end_utc = NOW - timedelta(minutes=2)
    end_pacific = end_utc - timedelta(hours=8)
    fake_engine(spans=[_newest_span(end_pacific, end_utc + timedelta(seconds=3))])
    warning = cb.check_engine_clock(ENGINE, _config(), cb.Deadline(), NOW)
    assert "8.0h behind its database clock" in warning
    assert '"local"' in warning
    # Configured for it: nothing to report.
    local = _config(engine_timezone="local")
    assert cb.check_engine_clock(ENGINE, local, cb.Deadline(), NOW) == ""


def test_clock_check_names_the_engine_offset_when_not_this_machines(
    fake_engine,
    pacific_machine,
):
    end_utc = NOW - timedelta(minutes=2)
    fake_engine(spans=[_newest_span(end_utc - timedelta(hours=5), end_utc)])
    warning = cb.check_engine_clock(ENGINE, _config(), cb.Deadline(), NOW)
    assert "UTC-05:00" in warning


def test_session_start_reports_a_clock_problem(monkeypatch, state_dir, fake_engine):
    monkeypatch.delenv(cb.BYPASS_ENV, raising=False)
    monkeypatch.setattr(cb, "discover_engine_config", lambda: ENGINE)
    monkeypatch.setattr(cb, "load_breaker_config", lambda: _config())
    future = datetime.now(timezone.utc) + timedelta(hours=9)
    fake_engine(spans=[_newest_span(future, future)])
    out = cb.run_hook("session_start", {"session_id": "s"})
    assert "in the future" in out["systemMessage"]
    # Other events do not repeat the check.
    assert cb.run_hook("pre_tool", {"session_id": "s"}) is None


def test_cli_check_exit_codes(monkeypatch, capsys):
    engine = dict(ENGINE, key_name="api_key")
    monkeypatch.setattr(cb, "load_breaker_config", lambda: _config())

    def check(discovered, request=None):
        monkeypatch.setattr(cb, "discover_engine_config", lambda: discovered)
        if request:
            monkeypatch.setattr(cb, "_request", request)
        return cb.cli_check()

    assert check(None) == cb.CHECK_NOT_CONFIGURED
    assert check(engine, _refuse_key) == cb.CHECK_AUTH_FAILED
    assert "read_api_key" in capsys.readouterr().err

    def down(*args, **kwargs):
        raise cb.EngineError("GET /traces/spans failed: connection refused")

    assert check(engine, down) == cb.CHECK_UNREACHABLE

    future = NOW + timedelta(days=365)
    assert check(engine, FakeEngine(spans=[_newest_span(future, future)])) == (
        cb.CHECK_OK
    )
    out = capsys.readouterr()
    assert "OK: api_key can read" in out.out
    assert "WARNING" in out.err and "in the future" in out.err
