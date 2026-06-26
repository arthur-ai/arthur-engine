import uuid
from datetime import datetime
from types import SimpleNamespace

import pytest
from arthur_common.models.enums import EvalType, RuleResultEnum

from schemas.internal_schemas import AgenticAnnotation


def _make_continuous_eval_annotation(eval_type: str) -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid.uuid4(),
        annotation_type="continuous_eval",
        trace_id="trace-1",
        continuous_eval_id=uuid.uuid4(),
        continuous_eval=SimpleNamespace(
            name="My Eval",
            eval_type=eval_type,
            llm_eval_name="my_llm_eval",
            llm_eval_version=1,
        ),
        annotation_score=1,
        annotation_description="No issues detected.",
        input_variables=[],
        run_status="passed",
        cost=0.0,
        created_at=datetime(2026, 6, 24, 12, 0, 0),
        updated_at=datetime(2026, 6, 24, 12, 0, 0),
    )


@pytest.mark.unit_tests
def test_from_db_model_populates_ml_eval_type():
    db_annotation = _make_continuous_eval_annotation("ml_eval")

    annotation = AgenticAnnotation.from_db_model(db_annotation)

    assert annotation.eval_type == "ml_eval"
    assert annotation.to_response_model().eval_type == EvalType.ML_EVAL


@pytest.mark.unit_tests
def test_from_db_model_populates_llm_eval_type():
    db_annotation = _make_continuous_eval_annotation("llm_eval")

    annotation = AgenticAnnotation.from_db_model(db_annotation)

    assert annotation.eval_type == "llm_eval"
    assert annotation.to_response_model().eval_type == EvalType.LLM_EVAL


@pytest.mark.unit_tests
def test_from_db_model_human_annotation_has_no_eval_type():
    db_annotation = SimpleNamespace(
        id=uuid.uuid4(),
        annotation_type="human",
        trace_id="trace-1",
        continuous_eval_id=None,
        continuous_eval=None,
        annotation_score=1,
        annotation_description="Looks good.",
        input_variables=[],
        run_status=None,
        cost=None,
        created_at=datetime(2026, 6, 24, 12, 0, 0),
        updated_at=datetime(2026, 6, 24, 12, 0, 0),
    )

    annotation = AgenticAnnotation.from_db_model(db_annotation)

    assert annotation.eval_type is None
    assert annotation.to_response_model().eval_type is None


@pytest.mark.unit_tests
def test_ml_score_to_response_reports_zero_cost():
    from scorer.ml_scorers import _score_to_response

    fake_rule_score = SimpleNamespace(
        result=RuleResultEnum.PASS,
        details=SimpleNamespace(message="No issues detected."),
    )

    response = _score_to_response(fake_rule_score)

    assert response.cost == "0"
