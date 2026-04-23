"""Unit tests for MLEvalsRepository."""

from uuid import uuid4

import pytest
from arthur_common.models.common_schemas import PaginationParameters
from arthur_common.models.enums import PaginationSortMethod

from repositories.ml_evals_repository import MLEvalsRepository
from schemas.llm_eval_schemas import MLEval
from schemas.request_schemas import CreateMLEvalRequest
from schemas.response_schemas import (
    LLMGetAllMetadataListResponse,
    MLEvalsVersionListResponse,
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
    return CreateMLEvalRequest(eval_type="pii")


@pytest.fixture
def toxicity_create_request():
    return CreateMLEvalRequest(eval_type="toxicity")


def _list_versions(
    repo: MLEvalsRepository,
    task_id: str,
    eval_name: str,
) -> MLEvalsVersionListResponse:
    """Helper: list all versions of an ML eval using the base class method (ascending order)."""
    pagination = PaginationParameters(
        page=0,
        page_size=100,
        sort=PaginationSortMethod.ASCENDING,
    )
    return repo.get_llm_item_versions(task_id, eval_name, pagination)


# ---------------------------------------------------------------------------
# MLEvalsRepository.save_ml_eval
# ---------------------------------------------------------------------------


@pytest.mark.unit_tests
def test_save_ml_eval_creates_version_1(ml_evals_repo, task_id, pii_create_request):
    eval_name = f"test_pii_{uuid4().hex[:8]}"

    result = ml_evals_repo.save_ml_eval(task_id, eval_name, pii_create_request)

    assert isinstance(result, MLEval)
    assert result.name == eval_name
    assert result.eval_type == "pii"
    assert result.version == 1
    assert result.deleted_at is None

    ml_evals_repo.delete_llm_item(task_id, eval_name)


@pytest.mark.unit_tests
def test_save_ml_eval_auto_increments_version(
    ml_evals_repo,
    task_id,
    pii_create_request,
):
    eval_name = f"test_incr_{uuid4().hex[:8]}"

    v1 = ml_evals_repo.save_ml_eval(task_id, eval_name, pii_create_request)
    v2 = ml_evals_repo.save_ml_eval(task_id, eval_name, pii_create_request)

    assert v1.version == 1
    assert v2.version == 2

    ml_evals_repo.delete_llm_item(task_id, eval_name)


@pytest.mark.unit_tests
def test_save_ml_eval_stores_config(ml_evals_repo, task_id):
    eval_name = f"test_cfg_{uuid4().hex[:8]}"
    request = CreateMLEvalRequest(eval_type="toxicity", config={"threshold": 0.8})

    result = ml_evals_repo.save_ml_eval(task_id, eval_name, request)

    assert result.config == {"threshold": 0.8}

    ml_evals_repo.delete_llm_item(task_id, eval_name)


@pytest.mark.unit_tests
def test_save_ml_eval_rejects_unknown_type(ml_evals_repo, task_id):
    # CreateMLEvalRequest.eval_type is a Literal — invalid values are rejected
    # at Pydantic parse time (ValidationError), before the repository is called.
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        CreateMLEvalRequest(eval_type="llm_as_a_judge")  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# get_llm_item (base class method on MLEvalsRepository)
# ---------------------------------------------------------------------------


@pytest.mark.unit_tests
def test_get_ml_eval_latest(ml_evals_repo, task_id, pii_create_request):
    eval_name = f"test_get_{uuid4().hex[:8]}"
    ml_evals_repo.save_ml_eval(task_id, eval_name, pii_create_request)
    ml_evals_repo.save_ml_eval(task_id, eval_name, pii_create_request)

    result = ml_evals_repo.get_llm_item(task_id, eval_name, "latest")
    assert result.version == 2

    ml_evals_repo.delete_llm_item(task_id, eval_name)


@pytest.mark.unit_tests
def test_get_ml_eval_by_version_number(ml_evals_repo, task_id, pii_create_request):
    eval_name = f"test_byver_{uuid4().hex[:8]}"
    ml_evals_repo.save_ml_eval(task_id, eval_name, pii_create_request)
    ml_evals_repo.save_ml_eval(task_id, eval_name, pii_create_request)

    result = ml_evals_repo.get_llm_item(task_id, eval_name, "1")
    assert result.version == 1

    ml_evals_repo.delete_llm_item(task_id, eval_name)


@pytest.mark.unit_tests
def test_get_ml_eval_not_found_raises(ml_evals_repo):
    with pytest.raises(ValueError, match="not found"):
        ml_evals_repo.get_llm_item(str(uuid4()), "nonexistent_eval", "latest")


# ---------------------------------------------------------------------------
# get_llm_item_versions (base class method for listing versions)
# ---------------------------------------------------------------------------


@pytest.mark.unit_tests
def test_list_versions_returns_all_in_ascending_order(
    ml_evals_repo,
    task_id,
    pii_create_request,
    toxicity_create_request,
):
    eval_name = f"test_list_{uuid4().hex[:8]}"
    ml_evals_repo.save_ml_eval(task_id, eval_name, pii_create_request)
    ml_evals_repo.save_ml_eval(task_id, eval_name, toxicity_create_request)

    result = _list_versions(ml_evals_repo, task_id, eval_name)

    assert isinstance(result, MLEvalsVersionListResponse)
    assert result.count == 2
    version_numbers = [v.version for v in result.versions]
    assert version_numbers == sorted(version_numbers)

    ml_evals_repo.delete_llm_item(task_id, eval_name)


@pytest.mark.unit_tests
def test_list_versions_empty_for_unknown_name(ml_evals_repo, task_id):
    result = _list_versions(ml_evals_repo, task_id, "nonexistent_eval")
    assert result.count == 0
    assert result.versions == []


@pytest.mark.unit_tests
def test_list_versions_includes_soft_deleted(
    ml_evals_repo,
    task_id,
    pii_create_request,
):
    eval_name = f"test_softlist_{uuid4().hex[:8]}"
    ml_evals_repo.save_ml_eval(task_id, eval_name, pii_create_request)
    ml_evals_repo.delete_version(task_id, eval_name, "latest")

    result = _list_versions(ml_evals_repo, task_id, eval_name)
    assert result.count == 1
    assert result.versions[0].deleted_at is not None

    ml_evals_repo.delete_llm_item(task_id, eval_name)


# ---------------------------------------------------------------------------
# MLEvalsRepository.get_all_llm_item_metadata
# ---------------------------------------------------------------------------


@pytest.mark.unit_tests
def test_get_all_metadata_returns_one_entry_per_name(
    ml_evals_repo,
    task_id,
    pii_create_request,
    toxicity_create_request,
):
    name_a = f"eval_a_{uuid4().hex[:8]}"
    name_b = f"eval_b_{uuid4().hex[:8]}"

    ml_evals_repo.save_ml_eval(task_id, name_a, pii_create_request)
    ml_evals_repo.save_ml_eval(task_id, name_a, pii_create_request)
    ml_evals_repo.save_ml_eval(task_id, name_b, toxicity_create_request)

    pagination = PaginationParameters(page=0, page_size=100)
    result = ml_evals_repo.get_all_llm_item_metadata(task_id, pagination)

    assert isinstance(result, LLMGetAllMetadataListResponse)
    names = {m.name for m in result.llm_metadata}
    assert name_a in names
    assert name_b in names

    meta_a = next(m for m in result.llm_metadata if m.name == name_a)
    assert meta_a.versions == 2

    ml_evals_repo.delete_llm_item(task_id, name_a)
    ml_evals_repo.delete_llm_item(task_id, name_b)


@pytest.mark.unit_tests
def test_get_all_metadata_empty_task(ml_evals_repo):
    pagination = PaginationParameters(page=0, page_size=100)
    result = ml_evals_repo.get_all_llm_item_metadata(str(uuid4()), pagination)
    assert result.count == 0
    assert result.llm_metadata == []


# ---------------------------------------------------------------------------
# MLEvalsRepository.delete_version (soft delete)
# ---------------------------------------------------------------------------


@pytest.mark.unit_tests
def test_delete_version_sets_deleted_at(ml_evals_repo, task_id, pii_create_request):
    eval_name = f"test_soft_{uuid4().hex[:8]}"
    ml_evals_repo.save_ml_eval(task_id, eval_name, pii_create_request)

    result = ml_evals_repo.delete_version(task_id, eval_name, "latest")

    assert result.deleted_at is not None

    ml_evals_repo.delete_llm_item(task_id, eval_name)


@pytest.mark.unit_tests
def test_delete_version_hides_from_latest(ml_evals_repo, task_id, pii_create_request):
    eval_name = f"test_hide_{uuid4().hex[:8]}"
    ml_evals_repo.save_ml_eval(task_id, eval_name, pii_create_request)
    ml_evals_repo.delete_version(task_id, eval_name, "latest")

    with pytest.raises(ValueError, match="not found"):
        ml_evals_repo.get_llm_item(task_id, eval_name, "latest")

    ml_evals_repo.delete_llm_item(task_id, eval_name)


@pytest.mark.unit_tests
def test_delete_version_not_found_raises(ml_evals_repo, task_id):
    with pytest.raises(ValueError, match="nonexistent"):
        ml_evals_repo.delete_version(task_id, "nonexistent", "latest")


# ---------------------------------------------------------------------------
# delete_llm_item (hard delete all versions)
# ---------------------------------------------------------------------------


@pytest.mark.unit_tests
def test_delete_all_versions_removes_all(ml_evals_repo, task_id, pii_create_request):
    eval_name = f"test_hard_{uuid4().hex[:8]}"
    ml_evals_repo.save_ml_eval(task_id, eval_name, pii_create_request)
    ml_evals_repo.save_ml_eval(task_id, eval_name, pii_create_request)

    ml_evals_repo.delete_llm_item(task_id, eval_name)

    result = _list_versions(ml_evals_repo, task_id, eval_name)
    assert result.count == 0


@pytest.mark.unit_tests
def test_delete_all_versions_not_found_raises(ml_evals_repo, task_id):
    with pytest.raises(ValueError, match="not found"):
        ml_evals_repo.delete_llm_item(task_id, "nonexistent")


# ---------------------------------------------------------------------------
# eval_types isolation — ML evals must not see llm_as_a_judge rows
# ---------------------------------------------------------------------------


@pytest.mark.unit_tests
def test_ml_repo_does_not_see_llm_as_a_judge_evals(task_id):
    """ML repo must not surface llm_as_a_judge rows; LLM repo surfaces all eval types."""
    from arthur_common.models.llm_model_providers import ModelProvider

    from repositories.llm_evals_repository import LLMEvalsRepository
    from schemas.request_schemas import CreateEvalRequest

    db_session = override_get_db_session()
    llm_repo = LLMEvalsRepository(db_session)
    ml_repo = MLEvalsRepository(db_session)

    llm_eval_name = f"llm_eval_{uuid4().hex[:8]}"
    ml_eval_name = f"ml_eval_{uuid4().hex[:8]}"

    llm_repo.save_llm_item(
        task_id,
        llm_eval_name,
        CreateEvalRequest(
            model_name="gpt-4o",
            model_provider=ModelProvider.OPENAI,
            instructions="Score the response: {{input}}",
        ),
    )
    ml_repo.save_ml_eval(task_id, ml_eval_name, CreateMLEvalRequest(eval_type="pii"))

    # ML repo should not see the LLM eval (MLEvalsRepository filters to ML types only)
    ml_result = ml_repo.get_llm_item(task_id, ml_eval_name, "latest")
    assert ml_result.eval_type == "pii"

    with pytest.raises(ValueError, match="not found"):
        ml_repo.get_llm_item(task_id, llm_eval_name, "latest")

    # LLM repo surfaces all eval types stored in llm_evals (including ML evals)
    llm_result = llm_repo.get_llm_item(task_id, llm_eval_name, "latest")
    assert llm_result.name == llm_eval_name
    assert llm_result.eval_type == "llm_as_a_judge"

    ml_via_llm_repo = llm_repo.get_llm_item(task_id, ml_eval_name, "latest")
    assert ml_via_llm_repo.name == ml_eval_name
    assert ml_via_llm_repo.eval_type == "pii"

    # Cleanup
    llm_repo.delete_llm_item(task_id, llm_eval_name)
    ml_repo.delete_llm_item(task_id, ml_eval_name)
