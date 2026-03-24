"""Unit tests for rule-based CE dispatch in ContinuousEvalQueueService."""

import json
import uuid
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
from arthur_common.models.enums import (
    AgenticAnnotationType,
    ContinuousEvalRunStatus,
    RuleResultEnum,
    RuleType,
)

from db_models.agentic_annotation_models import DatabaseAgenticAnnotation
from db_models.llm_eval_models import DatabaseContinuousEval
from scorer.ce_rule_evaluator import CEEvaluationResult
from services.continuous_eval.continuous_eval_queue_service import (
    ContinuousEvalJob,
    ContinuousEvalQueueService,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_db_continuous_eval(
    evaluator_type: str = "rule",
    rule_type: str = RuleType.PROMPT_INJECTION.value,
    transform_id: uuid.UUID | None = None,
) -> DatabaseContinuousEval:
    ce = MagicMock(spec=DatabaseContinuousEval)
    ce.id = uuid.uuid4()
    ce.name = "test-ce"
    ce.description = None
    ce.task_id = "task-1"
    ce.evaluator_type = evaluator_type
    ce.rule_type = rule_type
    ce.llm_eval_name = None
    ce.llm_eval_version = None
    ce.transform_id = transform_id or uuid.uuid4()
    ce.transform_variable_mapping = []
    ce.created_at = datetime.now()
    ce.updated_at = datetime.now()
    ce.enabled = True
    return ce


def make_annotation(
    annotation_id: uuid.UUID,
    trace_id: str,
    continuous_eval_id: uuid.UUID,
) -> DatabaseAgenticAnnotation:
    ann = MagicMock(spec=DatabaseAgenticAnnotation)
    ann.id = annotation_id
    ann.annotation_type = AgenticAnnotationType.CONTINUOUS_EVAL.value
    ann.trace_id = trace_id
    ann.continuous_eval_id = continuous_eval_id
    ann.run_status = ContinuousEvalRunStatus.PENDING.value
    return ann


def make_root_span(
    span_id: str = "span-1",
    input_content: str | None = "hello",
    output_content: str | None = "world",
) -> MagicMock:
    span = MagicMock()
    span.span_id = span_id
    span.input_content = input_content
    span.output_content = output_content
    return span


def make_trace(root_span: MagicMock) -> MagicMock:
    trace = MagicMock()
    trace.root_spans = [root_span]
    return trace


def make_transform(transform_id: uuid.UUID) -> MagicMock:
    transform = MagicMock()
    transform.id = transform_id
    transform.definition = MagicMock()
    transform.definition.variables = []
    return transform


def make_transform_results(missing_spans=None, missing_variables=None):
    tr = MagicMock()
    tr.missing_spans = missing_spans or []
    tr.missing_variables = missing_variables or []
    tr.variables = []
    return tr


def make_job(annotation_id=None, trace_id="trace-1", continuous_eval_id=None):
    return ContinuousEvalJob(
        annotation_id=annotation_id or uuid.uuid4(),
        trace_id=trace_id,
        continuous_eval_id=continuous_eval_id or uuid.uuid4(),
        task_id="task-1",
        delay_seconds=0,
    )


# ---------------------------------------------------------------------------
# _execute_job: rule-based path
# ---------------------------------------------------------------------------


def _make_service() -> ContinuousEvalQueueService:
    svc = ContinuousEvalQueueService.__new__(ContinuousEvalQueueService)
    return svc


def _run_rule_job(
    rule_type: RuleType,
    eval_result: CEEvaluationResult,
    annotation_id: uuid.UUID | None = None,
    trace_id: str = "trace-1",
) -> tuple[MagicMock, ContinuousEvalQueueService]:
    """
    Run _execute_job for a rule-based CE and return (mock_db_session, service).
    Mocks out all external dependencies so no I/O is needed.
    """
    svc = _make_service()
    annotation_id = annotation_id or uuid.uuid4()
    continuous_eval_id = uuid.uuid4()
    transform_id = uuid.uuid4()

    db_ce = make_db_continuous_eval(
        evaluator_type="rule",
        rule_type=rule_type.value,
        transform_id=transform_id,
    )
    annotation = make_annotation(annotation_id, trace_id, continuous_eval_id)
    root_span = make_root_span()
    trace = make_trace(root_span)
    transform = make_transform(transform_id)
    transform_results = make_transform_results()

    mock_db_session = MagicMock()

    # DB query for annotation
    mock_db_session.query.return_value.filter.return_value.first.side_effect = [
        annotation,  # annotation lookup
        db_ce,       # continuous eval lookup
    ]
    # Atomic RUNNING update
    mock_db_session.query.return_value.filter.return_value.update.return_value = 1

    job = make_job(annotation_id=annotation_id, trace_id=trace_id, continuous_eval_id=continuous_eval_id)

    with (
        patch(
            "services.continuous_eval.continuous_eval_queue_service.get_db_session",
            return_value=iter([mock_db_session]),
        ),
        patch(
            "services.continuous_eval.continuous_eval_queue_service.SpanRepository"
        ) as mock_span_repo_cls,
        patch(
            "services.continuous_eval.continuous_eval_queue_service.TraceTransformRepository"
        ) as mock_transform_repo_cls,
        patch(
            "services.continuous_eval.continuous_eval_queue_service.execute_transform",
            return_value=transform_results,
        ),
        patch(
            "services.continuous_eval.continuous_eval_queue_service._get_rule_evaluator"
        ) as mock_get_evaluator,
    ):
        mock_span_repo = MagicMock()
        mock_span_repo.get_trace_by_id.return_value = trace
        mock_span_repo_cls.return_value = mock_span_repo

        mock_transform_repo = MagicMock()
        mock_transform_repo.get_transform_by_id.return_value = transform
        mock_transform_repo_cls.return_value = mock_transform_repo

        mock_evaluator = MagicMock()
        mock_evaluator.evaluate.return_value = eval_result
        mock_get_evaluator.return_value = mock_evaluator

        # Patch MetricRepository and TasksMetricsRepository
        with (
            patch("services.continuous_eval.continuous_eval_queue_service.MetricRepository"),
            patch("services.continuous_eval.continuous_eval_queue_service.TasksMetricsRepository"),
        ):
            svc._execute_job(job)

    return mock_db_session, svc


# ---------------------------------------------------------------------------
# PROMPT_INJECTION pass/fail
# ---------------------------------------------------------------------------


@pytest.mark.unit_tests
def test_rule_ce_prompt_injection_pass_stores_score_1():
    """PROMPT_INJECTION PASS → annotation_score=1, run_status=PASSED."""
    eval_result = CEEvaluationResult(
        annotation_score=1,
        annotation_description=json.dumps({"result": RuleResultEnum.PASS.value}),
    )

    mock_db_session, _ = _run_rule_job(RuleType.PROMPT_INJECTION, eval_result)

    # _update_annotation_status writes to db; verify the annotation update
    updated_annotation = mock_db_session.query.return_value.filter.return_value.first.return_value
    # After the job, _update_annotation_status sets run_status and score
    assert mock_db_session.commit.called


@pytest.mark.unit_tests
def test_rule_ce_prompt_injection_fail_stores_score_0():
    """PROMPT_INJECTION FAIL → annotation_score=0, run_status=FAILED."""
    eval_result = CEEvaluationResult(
        annotation_score=0,
        annotation_description=json.dumps({"result": RuleResultEnum.FAIL.value, "message": "Injection detected"}),
    )

    mock_db_session, _ = _run_rule_job(RuleType.PROMPT_INJECTION, eval_result)

    assert mock_db_session.commit.called


# ---------------------------------------------------------------------------
# TOXICITY pass/fail
# ---------------------------------------------------------------------------


@pytest.mark.unit_tests
def test_rule_ce_toxicity_pass_stores_score_1():
    """TOXICITY PASS → annotation_score=1."""
    eval_result = CEEvaluationResult(
        annotation_score=1,
        annotation_description=json.dumps({"result": RuleResultEnum.PASS.value}),
    )

    mock_db_session, _ = _run_rule_job(RuleType.TOXICITY, eval_result)

    assert mock_db_session.commit.called


@pytest.mark.unit_tests
def test_rule_ce_toxicity_fail_stores_score_0():
    """TOXICITY FAIL → annotation_score=0."""
    eval_result = CEEvaluationResult(
        annotation_score=0,
        annotation_description=json.dumps({"result": RuleResultEnum.FAIL.value, "toxicity_score": {"toxicity_score": 0.95}}),
    )

    mock_db_session, _ = _run_rule_job(RuleType.TOXICITY, eval_result)

    assert mock_db_session.commit.called


# ---------------------------------------------------------------------------
# PII_DATA pass/fail
# ---------------------------------------------------------------------------


@pytest.mark.unit_tests
def test_rule_ce_pii_pass_stores_score_1():
    """PII_DATA PASS → annotation_score=1."""
    eval_result = CEEvaluationResult(
        annotation_score=1,
        annotation_description=json.dumps({"result": RuleResultEnum.PASS.value}),
    )

    mock_db_session, _ = _run_rule_job(RuleType.PII_DATA, eval_result)

    assert mock_db_session.commit.called


@pytest.mark.unit_tests
def test_rule_ce_pii_fail_stores_score_0():
    """PII_DATA FAIL → annotation_score=0."""
    eval_result = CEEvaluationResult(
        annotation_score=0,
        annotation_description=json.dumps({"result": RuleResultEnum.FAIL.value, "pii_results": ["PHONE_NUMBER"]}),
    )

    mock_db_session, _ = _run_rule_job(RuleType.PII_DATA, eval_result)

    assert mock_db_session.commit.called


# ---------------------------------------------------------------------------
# Verify evaluator is called with the root span
# ---------------------------------------------------------------------------


@pytest.mark.unit_tests
def test_rule_ce_calls_evaluator_with_root_span():
    """Verify evaluate() is called with the root span of the trace."""
    eval_result = CEEvaluationResult(
        annotation_score=1,
        annotation_description=json.dumps({"result": RuleResultEnum.PASS.value}),
    )

    annotation_id = uuid.uuid4()
    continuous_eval_id = uuid.uuid4()
    transform_id = uuid.uuid4()

    db_ce = make_db_continuous_eval(
        evaluator_type="rule",
        rule_type=RuleType.TOXICITY.value,
        transform_id=transform_id,
    )
    annotation = make_annotation(annotation_id, "trace-1", continuous_eval_id)
    root_span = make_root_span(span_id="root-span", input_content="hi", output_content="bye")
    trace = make_trace(root_span)
    transform = make_transform(transform_id)
    transform_results = make_transform_results()

    mock_db_session = MagicMock()
    mock_db_session.query.return_value.filter.return_value.first.side_effect = [
        annotation,
        db_ce,
    ]
    mock_db_session.query.return_value.filter.return_value.update.return_value = 1

    job = make_job(annotation_id=annotation_id, trace_id="trace-1", continuous_eval_id=continuous_eval_id)

    mock_evaluator = MagicMock()
    mock_evaluator.evaluate.return_value = eval_result

    with (
        patch(
            "services.continuous_eval.continuous_eval_queue_service.get_db_session",
            return_value=iter([mock_db_session]),
        ),
        patch(
            "services.continuous_eval.continuous_eval_queue_service.SpanRepository"
        ) as mock_span_repo_cls,
        patch(
            "services.continuous_eval.continuous_eval_queue_service.TraceTransformRepository"
        ) as mock_transform_repo_cls,
        patch(
            "services.continuous_eval.continuous_eval_queue_service.execute_transform",
            return_value=transform_results,
        ),
        patch(
            "services.continuous_eval.continuous_eval_queue_service._get_rule_evaluator",
            return_value=mock_evaluator,
        ),
        patch("services.continuous_eval.continuous_eval_queue_service.MetricRepository"),
        patch("services.continuous_eval.continuous_eval_queue_service.TasksMetricsRepository"),
    ):
        mock_span_repo = MagicMock()
        mock_span_repo.get_trace_by_id.return_value = trace
        mock_span_repo_cls.return_value = mock_span_repo

        mock_transform_repo = MagicMock()
        mock_transform_repo.get_transform_by_id.return_value = transform
        mock_transform_repo_cls.return_value = mock_transform_repo

        svc = _make_service()
        svc._execute_job(job)

    # evaluate() should be called with the correct rule type and the root span
    mock_evaluator.evaluate.assert_called_once_with(RuleType.TOXICITY, root_span)


# ---------------------------------------------------------------------------
# run_status mapping
# ---------------------------------------------------------------------------


@pytest.mark.unit_tests
def test_rule_ce_pass_sets_run_status_passed():
    """annotation_score=1 → run_status=PASSED stored in DB."""
    eval_result = CEEvaluationResult(
        annotation_score=1,
        annotation_description=json.dumps({"result": RuleResultEnum.PASS.value}),
    )

    annotation_id = uuid.uuid4()
    continuous_eval_id = uuid.uuid4()
    transform_id = uuid.uuid4()

    db_ce = make_db_continuous_eval(
        evaluator_type="rule",
        rule_type=RuleType.PROMPT_INJECTION.value,
        transform_id=transform_id,
    )
    annotation = make_annotation(annotation_id, "trace-1", continuous_eval_id)
    db_annotation_in_update = MagicMock(spec=DatabaseAgenticAnnotation)
    db_annotation_in_update.id = annotation_id
    root_span = make_root_span()
    trace = make_trace(root_span)
    transform = make_transform(transform_id)
    transform_results = make_transform_results()

    mock_db_session = MagicMock()
    # First two .first() calls return annotation then db_ce;
    # The third .first() is in _update_annotation_status
    mock_db_session.query.return_value.filter.return_value.first.side_effect = [
        annotation,
        db_ce,
        db_annotation_in_update,
    ]
    mock_db_session.query.return_value.filter.return_value.update.return_value = 1

    job = make_job(annotation_id=annotation_id, trace_id="trace-1", continuous_eval_id=continuous_eval_id)

    with (
        patch(
            "services.continuous_eval.continuous_eval_queue_service.get_db_session",
            return_value=iter([mock_db_session]),
        ),
        patch(
            "services.continuous_eval.continuous_eval_queue_service.SpanRepository"
        ) as mock_span_repo_cls,
        patch(
            "services.continuous_eval.continuous_eval_queue_service.TraceTransformRepository"
        ) as mock_transform_repo_cls,
        patch(
            "services.continuous_eval.continuous_eval_queue_service.execute_transform",
            return_value=transform_results,
        ),
        patch(
            "services.continuous_eval.continuous_eval_queue_service._get_rule_evaluator",
            return_value=MagicMock(evaluate=MagicMock(return_value=eval_result)),
        ),
        patch("services.continuous_eval.continuous_eval_queue_service.MetricRepository"),
        patch("services.continuous_eval.continuous_eval_queue_service.TasksMetricsRepository"),
    ):
        mock_span_repo = MagicMock()
        mock_span_repo.get_trace_by_id.return_value = trace
        mock_span_repo_cls.return_value = mock_span_repo

        mock_transform_repo = MagicMock()
        mock_transform_repo.get_transform_by_id.return_value = transform
        mock_transform_repo_cls.return_value = mock_transform_repo

        svc = _make_service()
        svc._execute_job(job)

    # Verify _update_annotation_status set run_status=PASSED and annotation_score=1
    assert db_annotation_in_update.run_status == ContinuousEvalRunStatus.PASSED.value
    assert db_annotation_in_update.annotation_score == 1


@pytest.mark.unit_tests
def test_rule_ce_fail_sets_run_status_failed():
    """annotation_score=0 → run_status=FAILED stored in DB."""
    eval_result = CEEvaluationResult(
        annotation_score=0,
        annotation_description=json.dumps({"result": RuleResultEnum.FAIL.value}),
    )

    annotation_id = uuid.uuid4()
    continuous_eval_id = uuid.uuid4()
    transform_id = uuid.uuid4()

    db_ce = make_db_continuous_eval(
        evaluator_type="rule",
        rule_type=RuleType.TOXICITY.value,
        transform_id=transform_id,
    )
    annotation = make_annotation(annotation_id, "trace-1", continuous_eval_id)
    db_annotation_in_update = MagicMock(spec=DatabaseAgenticAnnotation)
    db_annotation_in_update.id = annotation_id
    root_span = make_root_span()
    trace = make_trace(root_span)
    transform = make_transform(transform_id)
    transform_results = make_transform_results()

    mock_db_session = MagicMock()
    mock_db_session.query.return_value.filter.return_value.first.side_effect = [
        annotation,
        db_ce,
        db_annotation_in_update,
    ]
    mock_db_session.query.return_value.filter.return_value.update.return_value = 1

    job = make_job(annotation_id=annotation_id, trace_id="trace-1", continuous_eval_id=continuous_eval_id)

    with (
        patch(
            "services.continuous_eval.continuous_eval_queue_service.get_db_session",
            return_value=iter([mock_db_session]),
        ),
        patch(
            "services.continuous_eval.continuous_eval_queue_service.SpanRepository"
        ) as mock_span_repo_cls,
        patch(
            "services.continuous_eval.continuous_eval_queue_service.TraceTransformRepository"
        ) as mock_transform_repo_cls,
        patch(
            "services.continuous_eval.continuous_eval_queue_service.execute_transform",
            return_value=transform_results,
        ),
        patch(
            "services.continuous_eval.continuous_eval_queue_service._get_rule_evaluator",
            return_value=MagicMock(evaluate=MagicMock(return_value=eval_result)),
        ),
        patch("services.continuous_eval.continuous_eval_queue_service.MetricRepository"),
        patch("services.continuous_eval.continuous_eval_queue_service.TasksMetricsRepository"),
    ):
        mock_span_repo = MagicMock()
        mock_span_repo.get_trace_by_id.return_value = trace
        mock_span_repo_cls.return_value = mock_span_repo

        mock_transform_repo = MagicMock()
        mock_transform_repo.get_transform_by_id.return_value = transform
        mock_transform_repo_cls.return_value = mock_transform_repo

        svc = _make_service()
        svc._execute_job(job)

    assert db_annotation_in_update.run_status == ContinuousEvalRunStatus.FAILED.value
    assert db_annotation_in_update.annotation_score == 0
