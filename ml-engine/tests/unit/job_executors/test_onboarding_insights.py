"""The onboarding LLM insights against a fake GenAI Engine.

The fake stands in for the engine's configuration and default model provider routes and
its saved-prompt completions route: it records each prompt it is asked to run and answers per insight.
The executor tests run the whole job over fixture traces with the same fake.
"""

import json
import logging
import re
import threading
from typing import Any, Callable, Iterator
from unittest.mock import patch

import pytest
import requests
from test_onboarding_analysis_executor import (
    _agent_trace,
    _days_ago,
    _report,
    _Run,
    _validate_only_trace,
)

from config import Config
from job_executors.onboarding_analysis_executor import (
    OnboardingAnalysisResult,
    OnboardingOutcome,
)
from job_executors.onboarding_insights import (
    BATCH_CHAR_BUDGET,
    INSIGHT_KINDS,
    PROMPT_PREFIX,
    SYSTEM_TASK_ID,
    DefaultModel,
    HttpInsightEngineClient,
    InsightSpan,
    PromptCompletion,
    PromptRejected,
    PromptTooLarge,
    batch_char_budget,
    make_batches,
    run_llm_insights,
)

logger = logging.getLogger("test-onboarding-insights")

Answer = Callable[[str, str], str]  # (kind, traces text) -> reply content


def _verdict(kind: str, fired: str, matched: list[str], span: str | None = None) -> str:
    return json.dumps(
        {
            "kind": kind,
            "fired": fired,
            "matched_traces": matched,
            "example_span_name": span,
            "reason": f"{kind} reason citing {', '.join(matched) or 'no trace'}",
        },
    )


def _all_traces_in(text: str) -> list[str]:
    return re.findall(r"<trace id=(t\d+)>", text)


class FakeEngine:
    def __init__(
        self,
        enabled: bool = True,
        answer: Answer | None = None,
        cost_usd: float = 0.1,
        fail: Callable[[str, int], bool] = lambda kind, attempt: False,
        default_set: bool = True,
        reject: bool = False,
        too_large: Callable[[str], bool] = lambda text: False,
    ) -> None:
        self.enabled = enabled
        self.default_set = default_set
        self.reject = reject
        self.too_large = too_large
        self.answer = answer or (lambda kind, text: _verdict(kind, "no", []))
        self.cost_usd = cost_usd
        self.fail = fail
        self.calls: list[tuple[str, str]] = []
        self.attempts: dict[str, int] = {}
        self.lock = threading.Lock()

    def insights_enabled(self) -> bool:
        return self.enabled

    def default_model(self) -> DefaultModel | None:
        # A model litellm knows with a window of 200k tokens or more: the tuned batch size.
        return (
            DefaultModel("anthropic", "claude-opus-5-5") if self.default_set else None
        )

    def run_prompt(self, prompt_name: str, traces_text: str) -> PromptCompletion:
        kind = prompt_name.removeprefix(PROMPT_PREFIX)
        with self.lock:
            attempt = self.attempts.get(kind, 0)
            self.attempts[kind] = attempt + 1
            self.calls.append((prompt_name, traces_text))
        if self.reject:
            # As the engine answers when the default model has no structured output.
            raise PromptRejected(400)
        if self.too_large(traces_text):
            raise PromptTooLarge()
        if self.fail(kind, attempt):
            raise ConnectionError("provider down")
        return PromptCompletion(
            content=self.answer(kind, traces_text),
            cost_usd=self.cost_usd,
        )


def _no_sleep(seconds: float) -> None:
    pass


def _spans(trace: dict[str, Any]) -> list[InsightSpan]:
    """A fixture trace's spans as the executor hands them over."""
    from datetime import datetime

    return [
        InsightSpan(
            span_id=s["span_id"],
            parent_span_id=s["parent_span_id"],
            span_kind=s["span_kind"],
            span_name=s["span_name"],
            status_code=s["status_code"],
            start_time=datetime.fromisoformat(s["start_time"]),
            end_time=datetime.fromisoformat(s["end_time"]),
            raw_data=s["raw_data"],
        )
        for s in trace["spans"]
    ]


def _traces(n: int) -> dict[str, list[InsightSpan]]:
    traces = [_agent_trace(_days_ago(i), failed=i % 3 == 0) for i in range(n)]
    return {t["trace_id"]: _spans(t) for t in traces}


# --- The setting and the calls ------------------------------------------------------------


def test_insights_off_runs_no_prompt() -> None:
    engine = FakeEngine(enabled=False)

    run = run_llm_insights(engine, _traces(12), logger, sleep=_no_sleep)

    assert run.insights_off is True
    assert run.skipped == [("llm_insights", "insights_off")]
    assert engine.calls == []


def test_an_unreadable_setting_skips_the_insights() -> None:
    class Unreachable(FakeEngine):
        def insights_enabled(self) -> bool:
            raise ConnectionError("engine down")

    run = run_llm_insights(Unreachable(), _traces(12), logger, sleep=_no_sleep)

    assert run.insights_off is False
    assert run.skipped == [("llm_insights", "model_unavailable")]


def test_no_default_model_runs_no_prompt() -> None:
    engine = FakeEngine(default_set=False)

    run = run_llm_insights(engine, _traces(12), logger, sleep=_no_sleep)

    assert run.insights_off is False
    assert run.skipped == [("llm_insights", "default_model_not_configured")]
    assert engine.calls == []


def test_an_unreadable_default_model_skips_the_insights() -> None:
    class Unreachable(FakeEngine):
        def default_model(self) -> DefaultModel | None:
            raise ConnectionError("engine down")

    engine = Unreachable()
    run = run_llm_insights(engine, _traces(12), logger, sleep=_no_sleep)

    assert run.skipped == [("llm_insights", "model_unavailable")]
    assert engine.calls == []


def test_a_refused_call_stops_every_later_call() -> None:
    engine = FakeEngine(reject=True)

    # Two batches: twelve calls if every one were made, 36 with retries.
    run = run_llm_insights(engine, _traces(40), logger, sleep=_no_sleep)

    assert len(engine.calls) == 1
    assert run.verdicts == []
    assert sorted(run.skipped) == sorted(
        (kind, "model_rejected") for kind in INSIGHT_KINDS
    )


def test_a_batch_too_long_for_the_model_skips_only_that_batch() -> None:
    first_batch: list[str] = []

    def too_large(text: str) -> bool:
        if not first_batch:
            first_batch.append(text)
        return text == first_batch[0]

    engine = FakeEngine(too_large=too_large)

    run = run_llm_insights(engine, _traces(40), logger, sleep=_no_sleep)

    # Every insight was asked of both batches, once each: a 413 is not retried, and the
    # other batch still ran, so each "no" becomes cannot_tell.
    assert len(engine.calls) == 2 * len(INSIGHT_KINDS)
    assert {v.fired for v in run.verdicts} == {"cannot_tell"}
    assert run.skipped == []


def test_every_trace_too_large_is_reported_as_too_large() -> None:
    with patch(
        "job_executors.onboarding_insights.batch_char_budget",
        return_value=10,
    ):
        engine = FakeEngine()
        run = run_llm_insights(engine, _traces(3), logger, sleep=_no_sleep)

    assert engine.calls == []
    assert run.traces == 0
    assert sorted(run.skipped) == sorted((kind, "too_large") for kind in INSIGHT_KINDS)


@pytest.mark.parametrize(
    ("model", "budget"),
    [
        # 1M-token window: the tuned size, 89k tokens.
        (DefaultModel("anthropic", "claude-opus-5-5"), BATCH_CHAR_BUDGET),
        # 128k-token window: half of it less the reserve, 53k tokens.
        (DefaultModel("openai", "gpt-4o"), int(53_000 * 3 / 1.15)),
        # Not in litellm's map (an Azure deployment name): the tuned size.
        (DefaultModel("azure", "my-deployment"), BATCH_CHAR_BUDGET),
    ],
)
def test_the_batch_budget_follows_the_input_window(
    model: DefaultModel,
    budget: int,
) -> None:
    assert batch_char_budget(model) == budget


def test_an_empty_example_span_name_is_none() -> None:
    def answer(kind: str, text: str) -> str:
        return _verdict(kind, "yes", _all_traces_in(text)[:1], span="")

    run = run_llm_insights(
        FakeEngine(answer=answer), _traces(3), logger, sleep=_no_sleep
    )

    assert run.verdicts
    assert all(v.example_span_name is None for v in run.verdicts)


def test_each_insight_runs_its_saved_prompt_on_every_batch() -> None:
    engine = FakeEngine()
    traces = _traces(40)

    run = run_llm_insights(engine, traces, logger, sleep=_no_sleep)

    # 40 traces, at most 35 a batch: two batches, every insight asked of each.
    assert run.calls == 2 * len(INSIGHT_KINDS)
    assert sorted({name for name, _ in engine.calls}) == sorted(
        PROMPT_PREFIX + kind for kind in INSIGHT_KINDS
    )
    batches = {text for _, text in engine.calls}
    assert len(batches) == 2
    sent = sorted(t for text in batches for t in _all_traces_in(text))
    assert sent == sorted(f"t{i:02d}" for i in range(1, 41))
    for text in batches:
        assert text.startswith("FACTS\n")
        assert "\n\nTRACES\n<trace id=t" in text
    assert run.cost_usd == pytest.approx(12 * 0.1)


def test_verdicts_merge_across_batches_into_real_trace_ids() -> None:
    def answer(kind: str, text: str) -> str:
        ids = _all_traces_in(text)
        if kind == "tool_failures":
            # Each batch names its first trace.
            return _verdict(kind, "yes", [ids[0]], span="lookup_order")
        if kind == "user_facing" and "t01" in ids:
            return _verdict(kind, "yes", ["t01", "t99"])  # t99 is not a trace
        if kind == "heavy_model":
            return _verdict(kind, "cannot_tell", [])
        return _verdict(kind, "no", [])

    traces = _traces(40)
    ids = list(traces)

    run = run_llm_insights(FakeEngine(answer=answer), traces, logger, sleep=_no_sleep)

    by_kind = {v.kind: v for v in run.verdicts}
    assert set(by_kind) == set(INSIGHT_KINDS)
    failures = by_kind["tool_failures"]
    assert failures.fired == "yes"
    assert failures.matched_trace_ids == sorted([ids[0], ids[35]])
    assert failures.example_span_name == "lookup_order"
    assert failures.suggested_check is not None
    # A yes in one batch is a yes; ids the model made up are dropped.
    assert by_kind["user_facing"].fired == "yes"
    assert by_kind["user_facing"].matched_trace_ids == [ids[0]]
    assert by_kind["heavy_model"].fired == "cannot_tell"
    assert by_kind["internet_access"].fired == "no"
    assert by_kind["internet_access"].suggested_check is None
    assert run.skipped == []


# --- Nothing fails the job ----------------------------------------------------------------


def test_a_call_that_fails_once_is_retried_with_backoff() -> None:
    slept: list[float] = []
    engine = FakeEngine(
        fail=lambda kind, attempt: kind == "tool_failures" and attempt == 0
    )

    run = run_llm_insights(engine, _traces(12), logger, sleep=slept.append)

    assert {v.kind for v in run.verdicts} == set(INSIGHT_KINDS)
    assert slept == [3.0]
    assert engine.attempts["tool_failures"] == 2


def test_a_call_that_keeps_failing_is_skipped_and_the_rest_kept() -> None:
    slept: list[float] = []
    engine = FakeEngine(fail=lambda kind, attempt: kind == "internet_access")

    run = run_llm_insights(engine, _traces(12), logger, sleep=slept.append)

    assert engine.attempts["internet_access"] == 3
    assert slept == [3.0, 6.0]
    assert run.skipped == [("internet_access", "model_unavailable")]
    assert {v.kind for v in run.verdicts} == set(INSIGHT_KINDS) - {"internet_access"}


def test_an_unanswered_batch_makes_a_no_into_cannot_tell() -> None:
    # The second batch's internet_access call keeps failing: its traces were not judged.
    engine = FakeEngine(
        fail=lambda kind, attempt: kind == "internet_access" and attempt >= 1,
    )

    run = run_llm_insights(engine, _traces(40), logger, sleep=_no_sleep)

    verdict = next(v for v in run.verdicts if v.kind == "internet_access")
    assert verdict.fired == "cannot_tell"


def test_a_reply_that_is_not_a_verdict_is_skipped() -> None:
    def answer(kind: str, text: str) -> str:
        return (
            "I am not sure."
            if kind == "reference_material"
            else _verdict(kind, "no", [])
        )

    run = run_llm_insights(
        FakeEngine(answer=answer), _traces(12), logger, sleep=_no_sleep
    )

    assert run.skipped == [("reference_material", "unparsed_reply")]


def test_the_cost_cap_stops_further_calls() -> None:
    engine = FakeEngine(cost_usd=1.0)

    run = run_llm_insights(
        engine,
        _traces(12),
        logger,
        cost_cap_usd=1.0,
        sleep=_no_sleep,
    )

    # The first call spends the cap; at most the calls already in flight finish.
    assert run.calls < len(INSIGHT_KINDS)
    assert ("tool_failures", "cost_cap") in run.skipped


def test_a_trace_too_large_alone_is_not_sent() -> None:
    traces = {f"t{i:02d}": _spans(_agent_trace(_days_ago(i))) for i in range(1, 4)}

    batches, too_large = make_batches(traces, char_budget=10)

    assert batches == []
    assert too_large == ["t01", "t02", "t03"]


# --- Through the job ----------------------------------------------------------------------


@pytest.fixture
def raw_data_enabled() -> Iterator[None]:
    with patch.object(Config, "settings") as settings:
        settings.as_dict.return_value = {"FETCH_RAW_DATA_ENABLED": "true"}
        yield


@pytest.fixture(autouse=True)
def no_backoff() -> Iterator[None]:
    with patch("job_executors.onboarding_insights.time.sleep"):
        yield


def _job(rows: list[dict[str, Any]], engine: FakeEngine) -> OnboardingAnalysisResult:
    return _Run(rows, insight_client=engine)(min_traces=10)


def test_the_job_reports_each_insight_as_a_finding(raw_data_enabled: None) -> None:
    rows = [_agent_trace(_days_ago(i), failed=i % 3 == 0) for i in range(12)]
    rows += [_validate_only_trace(_days_ago(i)) for i in range(3)]

    def answer(kind: str, text: str) -> str:
        if kind == "tool_failures":
            return _verdict(kind, "yes", ["t01", "t04"], span="lookup_order")
        return _verdict(kind, "no", [])

    result = _job(rows, FakeEngine(answer=answer))

    assert result.outcome == OnboardingOutcome.COMPLETED
    report = _report(result)
    findings = {f.kind: f for f in report.findings}
    assert set(findings) == set(INSIGHT_KINDS)
    failures = findings["tool_failures"]
    assert failures.title == "Tool failures: yes, in 2 of 15 sampled traces"
    assert failures.values == {
        "fired": 1.0,
        "traces_matched": 2.0,
        "traces_in_sample": 15.0,
    }
    assert failures.detail is not None
    assert "Example span: lookup_order." in failures.detail
    assert "Suggested: " in failures.detail
    assert "Matched traces: " in failures.detail
    assert findings["internet_access"].values["fired"] == 0.0
    # Only the rule insights are still not built.
    assert [(s.kind, s.reason) for s in report.skipped] == [
        ("rule_insights", "not_implemented"),
    ]


def test_the_job_ends_llm_insights_off_when_the_setting_is_off(
    raw_data_enabled: None,
) -> None:
    rows = [_agent_trace(_days_ago(i)) for i in range(12)]
    engine = FakeEngine(enabled=False)

    result = _job(rows, engine)

    assert result.outcome == OnboardingOutcome.LLM_INSIGHTS_OFF
    report = _report(result)
    assert report.findings == []
    assert ("llm_insights", "insights_off") in [
        (s.kind, s.reason) for s in report.skipped
    ]
    assert report.totals.traces == 12
    assert engine.calls == []


def test_the_job_completes_when_every_insight_call_fails(
    raw_data_enabled: None,
) -> None:
    rows = [_agent_trace(_days_ago(i)) for i in range(12)]

    result = _job(rows, FakeEngine(fail=lambda kind, attempt: True))

    assert result.outcome == OnboardingOutcome.COMPLETED
    report = _report(result)
    assert report.findings == []
    assert sorted(
        s.kind for s in report.skipped if s.reason == "model_unavailable"
    ) == sorted(
        INSIGHT_KINDS,
    )


def test_the_job_completes_without_a_default_model(raw_data_enabled: None) -> None:
    rows = [_agent_trace(_days_ago(i)) for i in range(12)]
    engine = FakeEngine(default_set=False)

    result = _job(rows, engine)

    assert result.outcome == OnboardingOutcome.COMPLETED
    report = _report(result)
    assert report.findings == []
    assert ("llm_insights", "default_model_not_configured") in [
        (s.kind, s.reason) for s in report.skipped
    ]
    assert report.totals.traces == 12
    assert engine.calls == []


def test_a_cannot_tell_finding_has_no_fired_value(raw_data_enabled: None) -> None:
    rows = [_agent_trace(_days_ago(i)) for i in range(12)]

    def answer(kind: str, text: str) -> str:
        return _verdict(kind, "cannot_tell", [])

    report = _report(_job(rows, FakeEngine(answer=answer)))

    finding = next(f for f in report.findings if f.kind == "heavy_model")
    assert (
        finding.title
        == "Heavy model for light work: cannot tell from 12 sampled traces"
    )
    assert "fired" not in finding.values


# --- The HTTP client -------------------------------------------------------------------------


def test_the_http_client_reads_the_setting_and_runs_a_saved_prompt(
    httpserver: Any,
) -> None:
    auth = {"Authorization": "Bearer engine-key"}
    httpserver.expect_request(
        "/api/v2/configuration",
        method="GET",
        headers=auth,
    ).respond_with_json({"insights_generation_enabled": True})
    httpserver.expect_request(
        "/api/v1/default_model_provider",
        method="GET",
        headers=auth,
    ).respond_with_json({"provider": "openai", "model_name": "gpt-4.1-mini"})
    httpserver.expect_request(
        f"/api/v1/tasks/{SYSTEM_TASK_ID}/prompts/onboarding_insight_user_facing"
        "/versions/production/completions",
        method="POST",
        headers=auth,
        json={
            "variables": [{"name": "traces", "value": "FACTS\n..."}],
            "stream": False,
        },
    ).respond_with_json({"content": '{"fired": "no"}', "cost": 0.12})
    client = HttpInsightEngineClient(httpserver.url_for("/"), "engine-key")

    assert client.insights_enabled() is True
    assert client.default_model() == DefaultModel("openai", "gpt-4.1-mini")
    completion = client.run_prompt("onboarding_insight_user_facing", "FACTS\n...")

    assert completion == PromptCompletion(content='{"fired": "no"}', cost_usd=0.12)


def test_an_engine_without_the_setting_has_insights_off(httpserver: Any) -> None:
    httpserver.expect_request("/api/v2/configuration").respond_with_json({})

    client = HttpInsightEngineClient(httpserver.url_for("/"), "engine-key")

    assert client.insights_enabled() is False


def test_the_http_client_reads_an_unset_default_model(httpserver: Any) -> None:
    httpserver.expect_request("/api/v1/default_model_provider").respond_with_json(
        {"provider": None, "model_name": None},
    )

    client = HttpInsightEngineClient(httpserver.url_for("/"), "engine-key")

    assert client.default_model() is None


@pytest.mark.parametrize(
    ("status", "raised"),
    [
        (400, PromptRejected),
        (404, PromptRejected),
        (413, PromptTooLarge),
        (429, requests.HTTPError),
        (500, requests.HTTPError),
    ],
)
def test_the_http_client_tells_a_refused_call_from_a_failed_one(
    httpserver: Any,
    status: int,
    raised: type[Exception],
) -> None:
    httpserver.expect_request(
        f"/api/v1/tasks/{SYSTEM_TASK_ID}/prompts/onboarding_insight_user_facing"
        "/versions/production/completions",
    ).respond_with_json({"detail": "refused"}, status=status)

    client = HttpInsightEngineClient(httpserver.url_for("/"), "engine-key")

    with pytest.raises(raised):
        client.run_prompt("onboarding_insight_user_facing", "FACTS\n...")
