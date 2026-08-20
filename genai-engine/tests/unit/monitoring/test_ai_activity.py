"""Unit tests for the request-scoped AI-activity accumulator.

Covers the mechanism that feeds model invocations into the audit log:
the no-op-when-disabled behaviour, recording, propagation into
TracedThreadPoolExecutor workers, and the local-model decorator.
"""

from concurrent.futures import wait

import pytest
from opentelemetry import trace

import monitoring.ai_activity as ai
from monitoring.ai_activity import (
    begin_ai_activity,
    end_ai_activity,
    get_recorded_invocations,
    record_model_invocation,
    track_ml_model_invocation,
)
from schemas.audit_log_schemas import ModelInvocation
from utils.utils import TracedThreadPoolExecutor


def _invocation(**overrides) -> ModelInvocation:
    fields = dict(
        provider="local",
        model_type="ml_classifier",
        operation="pii",
        latency_ms=1,
        success=True,
    )
    fields.update(overrides)
    return ModelInvocation(**fields)


@pytest.fixture(autouse=True)
def _reset_accumulator():
    """ContextVar values persist across test calls in the same thread; isolate them."""
    token = ai._model_invocations.set(None)
    yield
    ai._model_invocations.reset(token)


@pytest.mark.unit_tests
def test_record_is_noop_without_accumulator():
    # No accumulator active (feature off / outside a request) -> silent no-op.
    record_model_invocation(_invocation())
    assert ai._model_invocations.get() is None
    assert get_recorded_invocations() == []


@pytest.mark.unit_tests
def test_begin_disabled_does_not_collect(monkeypatch):
    monkeypatch.setenv("AUDIT_LOG_INCLUDE_AI_ACTIVITY", "false")
    token = begin_ai_activity()
    try:
        assert token is None
        record_model_invocation(_invocation())
        assert get_recorded_invocations() == []
    finally:
        end_ai_activity(token)


@pytest.mark.unit_tests
def test_begin_enabled_records_and_reads_back(monkeypatch):
    monkeypatch.setenv("AUDIT_LOG_INCLUDE_AI_ACTIVITY", "true")
    token = begin_ai_activity()
    try:
        assert token is not None
        record_model_invocation(_invocation(operation="toxicity"))
        record_model_invocation(
            _invocation(
                model_type="llm",
                provider="azure",
                operation="hallucination",
                model_name="gpt-4o",
                prompt_tokens=3,
                completion_tokens=2,
                total_tokens=5,
            ),
        )
        recorded = get_recorded_invocations()
        assert [r.operation for r in recorded] == ["toxicity", "hallucination"]
    finally:
        end_ai_activity(token)


@pytest.mark.unit_tests
def test_end_resets_so_recording_stops(monkeypatch):
    monkeypatch.setenv("AUDIT_LOG_INCLUDE_AI_ACTIVITY", "true")
    token = begin_ai_activity()
    record_model_invocation(_invocation())
    end_ai_activity(token)

    # After the request ends, further records must not leak into a stale list.
    record_model_invocation(_invocation(operation="leak"))
    assert get_recorded_invocations() == []


@pytest.mark.unit_tests
def test_thread_pool_propagates_accumulator(monkeypatch):
    """Workers spawned by TracedThreadPoolExecutor record into the request's list."""
    monkeypatch.setenv("AUDIT_LOG_INCLUDE_AI_ACTIVITY", "true")
    token = begin_ai_activity()
    try:
        tracer = trace.get_tracer(__name__)
        with TracedThreadPoolExecutor(tracer, max_workers=4) as executor:
            futures = [
                executor.submit(
                    record_model_invocation, _invocation(operation=f"op{i}")
                )
                for i in range(5)
            ]
            wait(futures)

        recorded = get_recorded_invocations()
        assert len(recorded) == 5
        assert {r.operation for r in recorded} == {f"op{i}" for i in range(5)}
    finally:
        end_ai_activity(token)


@pytest.mark.unit_tests
def test_track_ml_decorator_records_success_and_failure(monkeypatch):
    monkeypatch.setenv("AUDIT_LOG_INCLUDE_AI_ACTIVITY", "true")
    token = begin_ai_activity()
    try:

        class FakeScorer:
            @track_ml_model_invocation(model_name="m", operation="toxicity")
            def score(self, request):
                return "ok"

            @track_ml_model_invocation(model_name="m", operation="pii")
            def failing(self, request):
                raise ValueError("boom")

        scorer = FakeScorer()
        assert scorer.score(None) == "ok"
        with pytest.raises(ValueError):
            scorer.failing(None)

        ok, bad = get_recorded_invocations()
        assert ok.operation == "toxicity"
        assert ok.success is True
        assert ok.provider == "local"
        assert ok.model_type == "ml_classifier"
        assert ok.prompt_tokens is None  # local models are not LLM-tokenized
        assert bad.operation == "pii"
        assert bad.success is False
        assert bad.error_type == "ValueError"
    finally:
        end_ai_activity(token)
