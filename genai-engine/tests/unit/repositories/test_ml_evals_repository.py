"""Unit tests for MLEvalsRepository and MLEvaluator."""

from datetime import datetime
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from arthur_common.models.task_eval_schemas import MLEval

from db_models.llm_eval_models import DatabaseMLEval
from repositories.ml_evals_repository import MLEvaluator, MLEvalsRepository, get_ml_scorer
from schemas.request_schemas import (
    ML_EVAL_INPUT_VARIABLE,
    ML_EVAL_TYPE_PII_V2,
    ML_EVAL_TYPE_TOXICITY,
    CreateMLEvalRequest,
)
from schemas.response_schemas import (
    EvalRunResponse,
    MLEvalsVersionListResponse,
    MLGetAllMetadataListResponse,
)
from tests.clients.base_test_client import override_get_db_session


@pytest.fixture
def ml_evals_repo():
    db_session = override_get_db_session()
    return MLEvalsRepository(db_session=db_session)


@pytest.fixture
def task_id():
    return str(uuid4())


@pytest.fixture
def pii_create_request():
    return CreateMLEvalRequest(ml_eval_type=ML_EVAL_TYPE_PII_V2)


@pytest.fixture
def toxicity_create_request():
    return CreateMLEvalRequest(ml_eval_type=ML_EVAL_TYPE_TOXICITY)


@pytest.fixture
def sample_db_ml_eval():
    return DatabaseMLEval(
        task_id=str(uuid4()),
        name="test_ml_eval",
        version=1,
        ml_eval_type=ML_EVAL_TYPE_PII_V2,
        model_provider="arthur_builtin",
        config=None,
        variables=[ML_EVAL_INPUT_VARIABLE],
        created_at=datetime.now(),
        deleted_at=None,
    )


# ---------------------------------------------------------------------------
# get_ml_scorer
# ---------------------------------------------------------------------------


@pytest.mark.unit_tests
def test_get_ml_scorer_returns_none_for_unknown_type():
    scorer = get_ml_scorer("unknown_type_xyz")
    assert scorer is None


@pytest.mark.unit_tests
def test_get_ml_scorer_caches_instances():
    import repositories.ml_evals_repository as repo_module

    # Clear any cached instance so we control the first call.
    repo_module._ML_SCORER_REGISTRY.pop(ML_EVAL_TYPE_PII_V2, None)

    # PIIScorerV2 is lazily imported inside get_ml_scorer, so patch at the source module.
    with patch("scorer.ml_scorers.PIIScorerV2") as MockPII:
        MockPII.return_value = MagicMock()
        scorer1 = get_ml_scorer(ML_EVAL_TYPE_PII_V2)
        scorer2 = get_ml_scorer(ML_EVAL_TYPE_PII_V2)

    assert scorer1 is scorer2
    MockPII.assert_called_once()

    # Restore so other tests are unaffected.
    repo_module._ML_SCORER_REGISTRY.pop(ML_EVAL_TYPE_PII_V2, None)


# ---------------------------------------------------------------------------
# MLEvalsRepository.from_db_model
# ---------------------------------------------------------------------------


@pytest.mark.unit_tests
def test_from_db_model(ml_evals_repo, sample_db_ml_eval):
    ml_eval = ml_evals_repo.from_db_model(sample_db_ml_eval)

    assert isinstance(ml_eval, MLEval)
    assert ml_eval.name == sample_db_ml_eval.name
    assert ml_eval.ml_eval_type == sample_db_ml_eval.ml_eval_type
    assert ml_eval.model_provider == sample_db_ml_eval.model_provider
    assert ml_eval.variables == sample_db_ml_eval.variables
    assert ml_eval.version == sample_db_ml_eval.version
    assert ml_eval.created_at == sample_db_ml_eval.created_at
    assert ml_eval.deleted_at is None


# ---------------------------------------------------------------------------
# MLEvalsRepository.save_ml_eval
# ---------------------------------------------------------------------------


@pytest.mark.unit_tests
def test_save_ml_eval_creates_version_1(ml_evals_repo, task_id, pii_create_request):
    eval_name = f"test_pii_{uuid4().hex[:8]}"

    result = ml_evals_repo.save_ml_eval(task_id, eval_name, pii_create_request)

    assert isinstance(result, MLEval)
    assert result.name == eval_name
    assert result.ml_eval_type == ML_EVAL_TYPE_PII_V2
    assert result.version == 1
    assert result.deleted_at is None

    ml_evals_repo.delete_all_versions(task_id, eval_name)


@pytest.mark.unit_tests
def test_save_ml_eval_auto_increments_version(ml_evals_repo, task_id, pii_create_request):
    eval_name = f"test_incr_{uuid4().hex[:8]}"

    v1 = ml_evals_repo.save_ml_eval(task_id, eval_name, pii_create_request)
    v2 = ml_evals_repo.save_ml_eval(task_id, eval_name, pii_create_request)

    assert v1.version == 1
    assert v2.version == 2

    ml_evals_repo.delete_all_versions(task_id, eval_name)


@pytest.mark.unit_tests
def test_save_ml_eval_stores_config(ml_evals_repo, task_id):
    eval_name = f"test_cfg_{uuid4().hex[:8]}"
    request = CreateMLEvalRequest(
        ml_eval_type=ML_EVAL_TYPE_TOXICITY,
        config={"threshold": 0.8},
    )

    result = ml_evals_repo.save_ml_eval(task_id, eval_name, request)

    assert result.config == {"threshold": 0.8}

    ml_evals_repo.delete_all_versions(task_id, eval_name)


# ---------------------------------------------------------------------------
# MLEvalsRepository.get_ml_eval
# ---------------------------------------------------------------------------


@pytest.mark.unit_tests
def test_get_ml_eval_latest(ml_evals_repo, task_id, pii_create_request):
    eval_name = f"test_get_{uuid4().hex[:8]}"
    ml_evals_repo.save_ml_eval(task_id, eval_name, pii_create_request)
    ml_evals_repo.save_ml_eval(task_id, eval_name, pii_create_request)

    result = ml_evals_repo.get_ml_eval(task_id, eval_name, "latest")
    assert result.version == 2

    ml_evals_repo.delete_all_versions(task_id, eval_name)


@pytest.mark.unit_tests
def test_get_ml_eval_by_version_number(ml_evals_repo, task_id, pii_create_request):
    eval_name = f"test_byver_{uuid4().hex[:8]}"
    ml_evals_repo.save_ml_eval(task_id, eval_name, pii_create_request)
    ml_evals_repo.save_ml_eval(task_id, eval_name, pii_create_request)

    result = ml_evals_repo.get_ml_eval(task_id, eval_name, "1")
    assert result.version == 1

    ml_evals_repo.delete_all_versions(task_id, eval_name)


@pytest.mark.unit_tests
def test_get_ml_eval_not_found_raises(ml_evals_repo):
    with pytest.raises(ValueError, match="not found"):
        ml_evals_repo.get_ml_eval(str(uuid4()), "nonexistent_eval", "latest")


# ---------------------------------------------------------------------------
# MLEvalsRepository.list_versions
# ---------------------------------------------------------------------------


@pytest.mark.unit_tests
def test_list_versions_returns_all_in_ascending_order(
    ml_evals_repo, task_id, pii_create_request, toxicity_create_request
):
    eval_name = f"test_list_{uuid4().hex[:8]}"
    ml_evals_repo.save_ml_eval(task_id, eval_name, pii_create_request)
    ml_evals_repo.save_ml_eval(task_id, eval_name, toxicity_create_request)

    result = ml_evals_repo.list_versions(task_id, eval_name)

    assert isinstance(result, MLEvalsVersionListResponse)
    assert result.count == 2
    version_numbers = [v.version for v in result.versions]
    assert version_numbers == sorted(version_numbers)

    ml_evals_repo.delete_all_versions(task_id, eval_name)


@pytest.mark.unit_tests
def test_list_versions_empty_for_unknown_name(ml_evals_repo, task_id):
    result = ml_evals_repo.list_versions(task_id, "nonexistent_eval")
    assert result.count == 0
    assert result.versions == []


@pytest.mark.unit_tests
def test_list_versions_includes_soft_deleted(ml_evals_repo, task_id, pii_create_request):
    eval_name = f"test_softlist_{uuid4().hex[:8]}"
    ml_evals_repo.save_ml_eval(task_id, eval_name, pii_create_request)
    ml_evals_repo.delete_version(task_id, eval_name, "latest")

    result = ml_evals_repo.list_versions(task_id, eval_name)
    assert result.count == 1
    assert result.versions[0].deleted_at is not None

    ml_evals_repo.delete_all_versions(task_id, eval_name)


# ---------------------------------------------------------------------------
# MLEvalsRepository.get_all_metadata
# ---------------------------------------------------------------------------


@pytest.mark.unit_tests
def test_get_all_metadata_returns_one_entry_per_name(
    ml_evals_repo, task_id, pii_create_request, toxicity_create_request
):
    name_a = f"eval_a_{uuid4().hex[:8]}"
    name_b = f"eval_b_{uuid4().hex[:8]}"

    ml_evals_repo.save_ml_eval(task_id, name_a, pii_create_request)
    ml_evals_repo.save_ml_eval(task_id, name_a, pii_create_request)
    ml_evals_repo.save_ml_eval(task_id, name_b, toxicity_create_request)

    result = ml_evals_repo.get_all_metadata(task_id)

    assert isinstance(result, MLGetAllMetadataListResponse)
    names = {m.name for m in result.ml_metadata}
    assert name_a in names
    assert name_b in names

    meta_a = next(m for m in result.ml_metadata if m.name == name_a)
    assert meta_a.versions == 2

    ml_evals_repo.delete_all_versions(task_id, name_a)
    ml_evals_repo.delete_all_versions(task_id, name_b)


@pytest.mark.unit_tests
def test_get_all_metadata_empty_task(ml_evals_repo):
    result = ml_evals_repo.get_all_metadata(str(uuid4()))
    assert result.count == 0
    assert result.ml_metadata == []


# ---------------------------------------------------------------------------
# MLEvalsRepository.delete_version (soft delete)
# ---------------------------------------------------------------------------


@pytest.mark.unit_tests
def test_delete_version_sets_deleted_at(ml_evals_repo, task_id, pii_create_request):
    eval_name = f"test_soft_{uuid4().hex[:8]}"
    ml_evals_repo.save_ml_eval(task_id, eval_name, pii_create_request)

    result = ml_evals_repo.delete_version(task_id, eval_name, "latest")

    assert result.deleted_at is not None

    ml_evals_repo.delete_all_versions(task_id, eval_name)


@pytest.mark.unit_tests
def test_delete_version_hides_from_latest(ml_evals_repo, task_id, pii_create_request):
    eval_name = f"test_hide_{uuid4().hex[:8]}"
    ml_evals_repo.save_ml_eval(task_id, eval_name, pii_create_request)
    ml_evals_repo.delete_version(task_id, eval_name, "latest")

    with pytest.raises(ValueError, match="not found"):
        ml_evals_repo.get_ml_eval(task_id, eval_name, "latest")

    ml_evals_repo.delete_all_versions(task_id, eval_name)


@pytest.mark.unit_tests
def test_delete_version_not_found_raises(ml_evals_repo, task_id):
    with pytest.raises(ValueError, match="not found"):
        ml_evals_repo.delete_version(task_id, "nonexistent", "latest")


# ---------------------------------------------------------------------------
# MLEvalsRepository.delete_all_versions (hard delete)
# ---------------------------------------------------------------------------


@pytest.mark.unit_tests
def test_delete_all_versions_removes_all(ml_evals_repo, task_id, pii_create_request):
    eval_name = f"test_hard_{uuid4().hex[:8]}"
    ml_evals_repo.save_ml_eval(task_id, eval_name, pii_create_request)
    ml_evals_repo.save_ml_eval(task_id, eval_name, pii_create_request)

    ml_evals_repo.delete_all_versions(task_id, eval_name)

    result = ml_evals_repo.list_versions(task_id, eval_name)
    assert result.count == 0


@pytest.mark.unit_tests
def test_delete_all_versions_not_found_raises(ml_evals_repo, task_id):
    with pytest.raises(ValueError, match="not found"):
        ml_evals_repo.delete_all_versions(task_id, "nonexistent")


# ---------------------------------------------------------------------------
# MLEvaluator.run
# ---------------------------------------------------------------------------


@pytest.mark.unit_tests
def test_ml_evaluator_run_calls_scorer_with_input_variable(ml_evals_repo, task_id):
    eval_name = f"test_run_{uuid4().hex[:8]}"
    create_req = CreateMLEvalRequest(ml_eval_type=ML_EVAL_TYPE_TOXICITY)
    ml_evals_repo.save_ml_eval(task_id, eval_name, create_req)

    evaluator = MLEvaluator(ml_evals_repo.db_session)

    mock_result = MagicMock()
    mock_result.passed = True
    mock_result.reason = "not toxic"

    with patch("repositories.ml_evals_repository.get_ml_scorer") as mock_get_scorer:
        mock_scorer = MagicMock()
        mock_scorer.score.return_value = mock_result
        mock_get_scorer.return_value = mock_scorer

        response = evaluator.run(
            task_id=task_id,
            eval_name=eval_name,
            eval_version="latest",
            variable_mapping=[],
            resolved_variables={ML_EVAL_INPUT_VARIABLE: "some text"},
        )

    assert isinstance(response, EvalRunResponse)
    assert response.score  # True/1 — Pydantic may coerce bool to int
    assert response.reason == "not toxic"
    mock_scorer.score.assert_called_once_with(text="some text", config={})

    ml_evals_repo.delete_all_versions(task_id, eval_name)


@pytest.mark.unit_tests
def test_ml_evaluator_run_passes_config_to_scorer(ml_evals_repo, task_id):
    eval_name = f"test_cfg_run_{uuid4().hex[:8]}"
    create_req = CreateMLEvalRequest(
        ml_eval_type=ML_EVAL_TYPE_TOXICITY,
        config={"threshold": 0.9},
    )
    ml_evals_repo.save_ml_eval(task_id, eval_name, create_req)

    evaluator = MLEvaluator(ml_evals_repo.db_session)

    mock_result = MagicMock()
    mock_result.passed = False
    mock_result.reason = "toxic"

    with patch("repositories.ml_evals_repository.get_ml_scorer") as mock_get_scorer:
        mock_scorer = MagicMock()
        mock_scorer.score.return_value = mock_result
        mock_get_scorer.return_value = mock_scorer

        evaluator.run(
            task_id=task_id,
            eval_name=eval_name,
            eval_version="latest",
            variable_mapping=[],
            resolved_variables={ML_EVAL_INPUT_VARIABLE: "bad text"},
        )

        mock_scorer.score.assert_called_once_with(
            text="bad text", config={"threshold": 0.9}
        )

    ml_evals_repo.delete_all_versions(task_id, eval_name)


@pytest.mark.unit_tests
def test_ml_evaluator_run_passes_empty_string_when_variable_missing(ml_evals_repo, task_id):
    eval_name = f"test_missing_{uuid4().hex[:8]}"
    create_req = CreateMLEvalRequest(ml_eval_type=ML_EVAL_TYPE_TOXICITY)
    ml_evals_repo.save_ml_eval(task_id, eval_name, create_req)

    evaluator = MLEvaluator(ml_evals_repo.db_session)

    mock_result = MagicMock()
    mock_result.passed = True
    mock_result.reason = "ok"

    with patch("repositories.ml_evals_repository.get_ml_scorer") as mock_get_scorer:
        mock_scorer = MagicMock()
        mock_scorer.score.return_value = mock_result
        mock_get_scorer.return_value = mock_scorer

        evaluator.run(
            task_id=task_id,
            eval_name=eval_name,
            eval_version="latest",
            variable_mapping=[],
            resolved_variables={},  # ML_EVAL_INPUT_VARIABLE key absent
        )

        mock_scorer.score.assert_called_once_with(text="", config={})

    ml_evals_repo.delete_all_versions(task_id, eval_name)


@pytest.mark.unit_tests
def test_ml_evaluator_run_raises_for_deleted_eval(ml_evals_repo, task_id):
    eval_name = f"test_del_run_{uuid4().hex[:8]}"
    create_req = CreateMLEvalRequest(ml_eval_type=ML_EVAL_TYPE_TOXICITY)
    ml_evals_repo.save_ml_eval(task_id, eval_name, create_req)
    ml_evals_repo.delete_version(task_id, eval_name, "latest")

    evaluator = MLEvaluator(ml_evals_repo.db_session)

    with pytest.raises(ValueError, match="deleted"):
        evaluator.run(
            task_id=task_id,
            eval_name=eval_name,
            eval_version="1",
            variable_mapping=[],
            resolved_variables={ML_EVAL_INPUT_VARIABLE: "text"},
        )

    ml_evals_repo.delete_all_versions(task_id, eval_name)


@pytest.mark.unit_tests
def test_ml_evaluator_run_raises_for_unknown_scorer_type(ml_evals_repo, task_id):
    eval_name = f"test_no_scorer_{uuid4().hex[:8]}"
    create_req = CreateMLEvalRequest(ml_eval_type=ML_EVAL_TYPE_TOXICITY)
    ml_evals_repo.save_ml_eval(task_id, eval_name, create_req)

    evaluator = MLEvaluator(ml_evals_repo.db_session)

    with patch("repositories.ml_evals_repository.get_ml_scorer", return_value=None):
        with pytest.raises(ValueError, match="No scorer registered"):
            evaluator.run(
                task_id=task_id,
                eval_name=eval_name,
                eval_version="latest",
                variable_mapping=[],
                resolved_variables={ML_EVAL_INPUT_VARIABLE: "text"},
            )

    ml_evals_repo.delete_all_versions(task_id, eval_name)
