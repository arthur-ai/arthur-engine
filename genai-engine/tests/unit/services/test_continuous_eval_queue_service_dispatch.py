"""Unit tests for ContinuousEvalQueueService dispatch logic (evaluator_type routing)."""

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

from services.continuous_eval.continuous_eval_queue_service import (
    ContinuousEvalJob,
    ContinuousEvalQueueService,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_TASK_ID = "test-task"
_ANNOTATION_ID = uuid.uuid4()
_CE_ID = uuid.uuid4()
_TRACE_ID = "trace-abc"


def _make_job() -> ContinuousEvalJob:
    return ContinuousEvalJob(
        annotation_id=_ANNOTATION_ID,
        trace_id=_TRACE_ID,
        continuous_eval_id=_CE_ID,
        task_id=_TASK_ID,
        delay_seconds=0,
    )


def _make_annotation(run_status: str = ContinuousEvalRunStatus.PENDING.value) -> MagicMock:
    ann = MagicMock()
    ann.id = _ANNOTATION_ID
    ann.trace_id = _TRACE_ID
    ann.continuous_eval_id = _CE_ID
    ann.annotation_type = AgenticAnnotationType.CONTINUOUS_EVAL.value
    ann.run_status = run_status
    return ann


def _make_db_ce(evaluator_type: str = "llm") -> MagicMock:
    ce = MagicMock()
    ce.id = _CE_ID
    ce.task_id = _TASK_ID
    ce.evaluator_type = evaluator_type
    ce.transform_id = uuid.uuid4()
    ce.transform_variable_mapping = []
    ce.llm_eval_name = "my-eval"
    ce.llm_eval_version = 1
    ce.rule_type = RuleType.PROMPT_INJECTION.value if evaluator_type == "rule" else None
    ce.rule_config = {}
    return ce


def _make_service() -> ContinuousEvalQueueService:
    """Return a queue service with a mock scorer client."""
    mock_client = MagicMock()
    svc = ContinuousEvalQueueService(
        num_workers=1,
        override_execution_delay=0,
        scorer_client=mock_client,
    )
    return svc


# ---------------------------------------------------------------------------
# _execute_job routing tests
# ---------------------------------------------------------------------------


@pytest.mark.unit_tests
class TestExecuteJobDispatch:
    """Verify that _execute_job dispatches to the correct path based on evaluator_type."""

    def test_llm_evaluator_type_calls_execute_llm_job(self):
        svc = _make_service()
        job = _make_job()
        annotation = _make_annotation()
        db_ce = _make_db_ce(evaluator_type="llm")

        mock_session = MagicMock()
        mock_session.query.return_value.filter.return_value.first.side_effect = [
            annotation,
            db_ce,
        ]

        with patch.object(svc, "_execute_llm_job") as mock_llm, \
             patch.object(svc, "_execute_rule_job") as mock_rule, \
             patch("services.continuous_eval.continuous_eval_queue_service.get_db_session",
                   return_value=iter([mock_session])):
            svc._execute_job(job)

        mock_llm.assert_called_once()
        mock_rule.assert_not_called()

    def test_rule_evaluator_type_calls_execute_rule_job(self):
        svc = _make_service()
        job = _make_job()
        annotation = _make_annotation()
        db_ce = _make_db_ce(evaluator_type="rule")

        mock_session = MagicMock()
        mock_session.query.return_value.filter.return_value.first.side_effect = [
            annotation,
            db_ce,
        ]

        with patch.object(svc, "_execute_rule_job") as mock_rule, \
             patch.object(svc, "_execute_llm_job") as mock_llm, \
             patch("services.continuous_eval.continuous_eval_queue_service.get_db_session",
                   return_value=iter([mock_session])):
            svc._execute_job(job)

        mock_rule.assert_called_once()
        mock_llm.assert_not_called()

    def test_empty_string_evaluator_type_defaults_to_llm(self):
        """Rows with empty evaluator_type should route to LLM path."""
        svc = _make_service()
        job = _make_job()
        annotation = _make_annotation()
        db_ce = _make_db_ce(evaluator_type="")

        mock_session = MagicMock()
        mock_session.query.return_value.filter.return_value.first.side_effect = [
            annotation,
            db_ce,
        ]

        with patch.object(svc, "_execute_llm_job") as mock_llm, \
             patch.object(svc, "_execute_rule_job") as mock_rule, \
             patch("services.continuous_eval.continuous_eval_queue_service.get_db_session",
                   return_value=iter([mock_session])):
            svc._execute_job(job)

        mock_llm.assert_called_once()
        mock_rule.assert_not_called()
