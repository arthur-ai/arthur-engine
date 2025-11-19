from datetime import datetime
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from arthur_common.models.common_schemas import (
    PaginationParameters,
    PaginationSortMethod,
)
from litellm.types.utils import ModelResponse
from sqlalchemy.exc import IntegrityError

from clients.llm.llm_client import LLMClient, LLMModelResponse
from db_models.llm_eval_models import DatabaseLLMEval, DatabaseLLMEvalVersionTag
from repositories.llm_evals_repository import LLMEvalsRepository
from schemas.enums import ModelProvider
from schemas.llm_eval_schemas import LLMEval
from schemas.llm_schemas import LLMBaseConfigSettings
from schemas.request_schemas import (
    CreateEvalRequest,
    LLMGetAllFilterRequest,
    LLMGetVersionsFilterRequest,
    LLMRequestConfigSettings,
)
from schemas.response_schemas import (
    LLMEvalRunResponse,
    LLMEvalsVersionListResponse,
    LLMGetAllMetadataListResponse,
    LLMGetAllMetadataResponse,
)
from tests.clients.base_test_client import override_get_db_session


@pytest.fixture
def llm_evals_repo():
    db_session = override_get_db_session()
    return LLMEvalsRepository(db_session=db_session)


@pytest.fixture
def sample_llm_eval():
    return LLMEval(
        name="test_llm_eval",
        model_name="gpt-4o",
        model_provider="openai",
        instructions="test_instructions",
        config=LLMBaseConfigSettings(temperature=0.5, max_tokens=100),
        version=1,
        created_at=datetime.now(),
    )


@pytest.fixture
def sample_create_eval_request():
    return CreateEvalRequest(
        model_name="gpt-4o",
        model_provider="openai",
        instructions="test_instructions",
        config=LLMRequestConfigSettings(temperature=0.5, max_tokens=100),
    )


@pytest.fixture
def sample_db_llm_eval():
    """Create sample DatabaseLLMEval instance"""
    task_id = str(uuid4())
    return DatabaseLLMEval(
        task_id=task_id,
        name="test_llm_eval",
        model_name="gpt-4o",
        model_provider="openai",
        instructions="test_instructions",
        variables=[],
        config=LLMBaseConfigSettings(temperature=0.5, max_tokens=100),
        created_at=datetime.now(),
        deleted_at=None,
        version=1,
    )


@pytest.fixture
def mock_llm_client():
    """Mock LiteLLM client for testing"""
    return LLMClient(
        provider=ModelProvider.OPENAI,
        api_key="api_key",
    )


@pytest.mark.unit_tests
def test_save_llm_eval_integrity_error(sample_create_eval_request):
    """Test saving an llm eval when it already exists (IntegrityError)"""
    task_id = "test_task_id"

    mock_db_session = MagicMock()
    llm_evals_repo = LLMEvalsRepository(db_session=mock_db_session)

    # Mock IntegrityError on commit
    mock_db_session.commit.side_effect = IntegrityError("", "", Exception(""))

    with pytest.raises(ValueError) as exc_info:
        llm_evals_repo.save_llm_item(
            task_id,
            sample_llm_eval.name,
            sample_create_eval_request,
        )

    assert (
        str(exc_info.value)
        == f"Failed to save '{sample_llm_eval.name}' for task '{task_id}' — possible duplicate constraint."
    )

    # Verify rollback was called
    mock_db_session.rollback.assert_called_once()


@pytest.mark.unit_tests
def test_save_llm_eval_with_llm_eval_object(
    llm_evals_repo,
    sample_llm_eval,
    sample_create_eval_request,
):
    """Test saving an LLMEval object to database"""
    task_id = "test_task_id"
    result = llm_evals_repo.save_llm_item(
        task_id,
        sample_llm_eval.name,
        sample_create_eval_request,
    )

    # Compare was inserted to the database correctly
    assert isinstance(result, LLMEval)
    assert result.name == sample_llm_eval.name
    assert result.model_name == sample_llm_eval.model_name
    assert result.model_provider == sample_llm_eval.model_provider
    assert result.instructions == sample_llm_eval.instructions
    assert result.config == sample_llm_eval.config
    assert result.version == sample_llm_eval.version
    assert result.deleted_at is None

    # clean up database
    llm_evals_repo.delete_llm_item(task_id, sample_llm_eval.name)


@pytest.mark.unit_tests
def test_llm_eval_repo_from_db_model(llm_evals_repo, sample_db_llm_eval):
    """Test creating LLMEval from DatabaseLLMEval"""
    llm_eval = llm_evals_repo.from_db_model(sample_db_llm_eval)

    assert isinstance(llm_eval, LLMEval)
    assert llm_eval.name == sample_db_llm_eval.name
    assert llm_eval.model_name == sample_db_llm_eval.model_name
    assert llm_eval.model_provider == sample_db_llm_eval.model_provider
    assert llm_eval.instructions == sample_db_llm_eval.instructions
    assert llm_eval.config == sample_db_llm_eval.config
    assert llm_eval.version == sample_db_llm_eval.version
    assert llm_eval.created_at == sample_db_llm_eval.created_at
    assert llm_eval.deleted_at is None


@pytest.mark.unit_tests
def test_llm_eval_model_dump(sample_llm_eval):
    """Test converting LLMEval to dictionary"""
    llm_eval_dict = sample_llm_eval.model_dump(exclude_none=True)

    assert isinstance(llm_eval_dict, dict)
    assert llm_eval_dict["name"] == sample_llm_eval.name
    assert llm_eval_dict["model_name"] == sample_llm_eval.model_name
    assert llm_eval_dict["model_provider"] == sample_llm_eval.model_provider
    assert llm_eval_dict["instructions"] == sample_llm_eval.instructions
    assert "config" in llm_eval_dict
    assert llm_eval_dict["config"]["temperature"] == sample_llm_eval.config.temperature
    assert llm_eval_dict["config"]["max_tokens"] == sample_llm_eval.config.max_tokens
    assert llm_eval_dict["version"] == sample_llm_eval.version


@pytest.mark.unit_tests
def test_delete_eval_success(llm_evals_repo, sample_create_eval_request):
    """Test successfully deleting an llm eval"""
    task_id = "test_task_id"
    eval_name = "test_eval"

    # Mock database query
    llm_evals_repo.save_llm_item(task_id, eval_name, sample_create_eval_request)
    llm_evals_repo.delete_llm_item(task_id, eval_name)

    with pytest.raises(ValueError) as exc_info:
        llm_evals_repo.get_llm_item(task_id, eval_name, "latest")

    assert (
        str(exc_info.value)
        == f"'{eval_name}' (version 'latest') not found for task '{task_id}'"
    )


@pytest.mark.unit_tests
def test_delete_eval_not_found(llm_evals_repo):
    """Test deleting an llm eval that doesn't exist"""
    task_id = "nonexistent_task"
    eval_name = "nonexistent_eval"

    with pytest.raises(
        ValueError,
        match="'nonexistent_eval' not found for task 'nonexistent_task'",
    ):
        llm_evals_repo.delete_llm_item(task_id, eval_name)


@pytest.mark.unit_tests
def test_soft_delete_eval_version_success(
    llm_evals_repo,
    sample_create_eval_request,
):
    """Test successfully soft-deleting an llm eval"""
    task_id = "test_task_id"
    eval_name = "test_llm_eval"

    llm_evals_repo.save_llm_item(task_id, eval_name, sample_create_eval_request)
    llm_evals_repo.soft_delete_llm_item_version(task_id, eval_name, "latest")
    result = llm_evals_repo.get_llm_item(task_id, eval_name, "1")

    # Validate the object was soft deleted
    assert result.deleted_at is not None
    assert result.model_name == ""
    assert result.instructions == ""
    assert result.config is None

    # clean up database
    llm_evals_repo.delete_llm_item(task_id, eval_name)


@pytest.mark.unit_tests
def test_soft_delete_eval_version_errors(llm_evals_repo, sample_create_eval_request):
    """Test all error cases for soft_delete_eval_version"""
    task_id = "test_task"
    eval_name = "test_eval"

    llm_evals_repo.save_llm_item(task_id, eval_name, sample_create_eval_request)
    llm_evals_repo.soft_delete_llm_item_version(task_id, eval_name, "latest")

    # --- Case 1: Not found ---
    with pytest.raises(ValueError) as exc_info:
        llm_evals_repo.soft_delete_llm_item_version(task_id, eval_name, "latest")
    assert f"No matching version of '{eval_name}' found for task '{task_id}'" in str(
        exc_info.value,
    )

    # --- Case 2: Already deleted ---
    with pytest.raises(ValueError) as exc_info:
        llm_evals_repo.soft_delete_llm_item_version(
            task_id,
            eval_name,
            "1",
        )

    assert "has already been deleted" in str(exc_info.value)

    # clean up database
    llm_evals_repo.delete_llm_item(task_id, eval_name)


@pytest.mark.unit_tests
@pytest.mark.parametrize("eval_version", ["latest", "1", "datetime"])
def test_soft_delete_eval_by_version_success(
    llm_evals_repo,
    eval_version,
    sample_create_eval_request,
):
    """Test deleting an eval with different version formats"""
    task_id = str(uuid4())
    eval_name = "test_llm_eval"

    try:
        result = llm_evals_repo.save_llm_item(
            task_id,
            eval_name,
            sample_create_eval_request,
        )
        created_at_timestamp = result.created_at

        if eval_version == "datetime":
            eval_version = created_at_timestamp.isoformat()

        llm_evals_repo.soft_delete_llm_item_version(task_id, eval_name, eval_version)

        if eval_version == "latest":
            with pytest.raises(ValueError) as exc_info:
                llm_evals_repo.get_llm_item(task_id, eval_name, eval_version)
            assert (
                f"'{eval_name}' (version '{eval_version}') not found for task '{task_id}'"
                in str(exc_info.value)
            )
        else:
            result = llm_evals_repo.get_llm_item(task_id, eval_name, eval_version)

            assert isinstance(result, LLMEval)
            assert result.name == eval_name
            assert result.model_name == ""
            assert result.model_provider == "openai"
            assert result.instructions == ""
            assert result.config is None
            assert result.version == 1
            assert result.created_at == created_at_timestamp
            assert result.deleted_at is not None
    finally:
        # Cleanup
        llm_evals_repo.delete_llm_item(task_id, eval_name)


@pytest.mark.unit_tests
def test_get_eval_success(
    llm_evals_repo,
    sample_db_llm_eval,
    sample_create_eval_request,
):
    """Test successfully getting an llm eval from database"""
    task_id = "test_task_id"
    eval_name = "test_llm_eval"

    llm_evals_repo.save_llm_item(task_id, eval_name, sample_create_eval_request)
    result = llm_evals_repo.get_llm_item(task_id, eval_name, "latest")

    assert isinstance(result, LLMEval)
    assert result.name == sample_db_llm_eval.name
    assert result.model_name == sample_db_llm_eval.model_name
    assert result.model_provider == sample_db_llm_eval.model_provider
    assert result.instructions == sample_db_llm_eval.instructions
    assert result.config == sample_db_llm_eval.config
    assert result.version == sample_db_llm_eval.version
    assert result.deleted_at is None

    # clean up database
    llm_evals_repo.delete_llm_item(task_id, eval_name)


@pytest.mark.unit_tests
def test_get_eval_not_found(llm_evals_repo):
    """Test getting an llm eval that doesn't exist"""
    task_id = "test_task_id"
    eval_name = "test_llm_eval"

    with pytest.raises(ValueError) as exc_info:
        llm_evals_repo.get_llm_item(task_id, eval_name, "latest")

    assert (
        str(exc_info.value)
        == "'test_llm_eval' (version 'latest') not found for task 'test_task_id'"
    )


@pytest.mark.unit_tests
@pytest.mark.parametrize("eval_version", ["latest", "1", "datetime"])
def test_get_eval_different_version_types_success(
    llm_evals_repo,
    eval_version,
    sample_db_llm_eval,
    sample_create_eval_request,
):
    """Test getting an llm eval with different version formats"""
    task_id = "test_task_id"
    eval_name = "test_llm_eval"

    try:
        result = llm_evals_repo.save_llm_item(
            task_id,
            eval_name,
            sample_create_eval_request,
        )
        created_at_timestamp = result.created_at

        if eval_version == "datetime":
            eval_version = created_at_timestamp.isoformat()

        result = llm_evals_repo.get_llm_item(task_id, eval_name, eval_version)

        assert isinstance(result, LLMEval)
        assert result.name == sample_db_llm_eval.name
        assert result.model_name == sample_db_llm_eval.model_name
        assert result.model_provider == sample_db_llm_eval.model_provider
        assert result.instructions == sample_db_llm_eval.instructions
        assert result.config == sample_db_llm_eval.config
        assert result.version == sample_db_llm_eval.version
        assert result.created_at == created_at_timestamp
        assert result.deleted_at is None
    finally:
        # Cleanup
        llm_evals_repo.delete_llm_item(task_id, eval_name)


@pytest.mark.unit_tests
def test_get_soft_delete_eval_by_version_no_error(
    llm_evals_repo,
    sample_create_eval_request,
):
    """Test getting a soft-deleted llm eval does not raise an error"""
    task_id = "test_task_id"
    eval_name = "test_llm_eval"

    try:
        result = llm_evals_repo.save_llm_item(
            task_id,
            eval_name,
            sample_create_eval_request,
        )
        created_at_timestamp = result.created_at

        llm_evals_repo.soft_delete_llm_item_version(task_id, eval_name, "latest")
        result = llm_evals_repo.get_llm_item(task_id, eval_name, "1")

        assert isinstance(result, LLMEval)
        assert result.deleted_at is not None
        assert result.model_name == ""
        assert result.instructions == ""
        assert result.config is None
        assert result.version == 1
        assert result.created_at == created_at_timestamp
    finally:
        # Cleanup
        llm_evals_repo.delete_llm_item(task_id, eval_name)


@pytest.mark.unit_tests
@pytest.mark.parametrize(
    "filter_param,filter_value,expected_count",
    [
        ("model_provider", ModelProvider.OPENAI, 2),
        ("model_provider", ModelProvider.ANTHROPIC, 1),
        ("model_name", "gpt-4", 2),
        ("created_after", None, 2),
        ("created_before", None, 2),
        ("exclude_deleted", True, 2),
        ("min_version", 2, 2),
        ("max_version", 2, 2),
        ("min_version", 10, 0),  # verify no returned versions doesn't spawn an error
    ],
)
def test_get_eval_versions_with_filters(
    llm_evals_repo,
    sample_create_eval_request,
    filter_param,
    filter_value,
    expected_count,
):
    """Test getting eval versions with filter_request parameters"""
    task_id = "test_task_id"
    eval_name = "test_llm_eval"

    # Create multiple versions with different properties
    versions_data = [
        CreateEvalRequest(
            instructions="Version 1",
            model_name="gpt-4",
            model_provider="openai",
        ),
        CreateEvalRequest(
            instructions="Version 2",
            model_name="gpt-4",
            model_provider="openai",
        ),
        CreateEvalRequest(
            instructions="Version 3",
            model_name="claude-3-5-sonnet",
            model_provider="anthropic",
        ),
    ]

    try:
        results = []
        for version_data in versions_data:
            result = llm_evals_repo.save_llm_item(task_id, eval_name, version_data)
            results.append(result)

        if filter_param == "created_after":
            filter_value = results[1].created_at.isoformat()
        elif filter_param == "created_before":
            filter_value = results[-1].created_at.isoformat()
        elif filter_param == "exclude_deleted":
            llm_evals_repo.soft_delete_llm_item_version(task_id, eval_name, "latest")

        # Create filter request
        filter_request = LLMGetVersionsFilterRequest(**{filter_param: filter_value})

        # Create pagination parameters
        pagination_params = PaginationParameters(
            page=0,
            page_size=10,
            sort=PaginationSortMethod.ASCENDING,
        )

        # Get filtered results
        result = llm_evals_repo.get_llm_item_versions(
            task_id=task_id,
            item_name=eval_name,
            pagination_parameters=pagination_params,
            filter_request=filter_request,
        )

        # Verify filtering worked
        assert isinstance(result, LLMEvalsVersionListResponse)
        assert result.count == expected_count
        assert len(result.versions) == expected_count

    finally:
        # Cleanup
        llm_evals_repo.delete_llm_item(task_id, eval_name)


@pytest.mark.unit_tests
@pytest.mark.parametrize(
    "page,page_size,sort,expected_versions",
    [
        (0, 2, PaginationSortMethod.ASCENDING, [1, 2]),
        (1, 2, PaginationSortMethod.ASCENDING, [3, 4]),
        (0, 4, PaginationSortMethod.DESCENDING, [4, 3, 2, 1]),
        (0, 10, PaginationSortMethod.ASCENDING, [1, 2, 3, 4]),
        (3, 1, PaginationSortMethod.ASCENDING, [4]),
    ],
)
def test_get_llm_eval_versions_with_pagination(
    llm_evals_repo,
    page,
    page_size,
    sort,
    expected_versions,
):
    """Test getting llm eval versions with all pagination parameters (page, page_size, sort)"""
    task_id = "test_task_id"
    eval_name = "test_llm_eval"

    try:
        # Create multiple versions
        created_evals = []
        for i in range(1, 5):
            version_data = CreateEvalRequest(
                instructions=f"Version {i}",
                model_name="gpt-4",
                model_provider="openai",
            )
            result = llm_evals_repo.save_llm_item(task_id, eval_name, version_data)
            created_evals.append(result)

        # Create pagination parameters
        pagination_params = PaginationParameters(
            page=page,
            page_size=page_size,
            sort=sort,
        )

        # Get paginated results
        result = llm_evals_repo.get_llm_item_versions(
            task_id=task_id,
            item_name=eval_name,
            pagination_parameters=pagination_params,
        )

        # Verify pagination worked
        assert isinstance(result, LLMEvalsVersionListResponse)
        assert result.count == 4  # Total count should always be 4
        assert len(result.versions) == len(expected_versions)

        # Verify the order of versions
        for i, expected_version in enumerate(expected_versions):
            assert result.versions[i].version == expected_version

    finally:
        # Cleanup
        llm_evals_repo.delete_llm_item(task_id, eval_name)


@pytest.mark.unit_tests
def test_get_all_llm_evals(llm_evals_repo, sample_create_eval_request):
    """Test getting all llm evals for a task"""
    task_id = "test_task_id"

    for i in range(2):
        llm_evals_repo.save_llm_item(
            task_id,
            f"test_llm_eval_{i}",
            sample_create_eval_request,
        )

    # Use default pagination parameters
    pagination_parameters = PaginationParameters(
        page=0,
        page_size=10,
        sort=PaginationSortMethod.DESCENDING,
    )
    result = llm_evals_repo.get_all_llm_item_metadata(task_id, pagination_parameters)

    assert isinstance(result, LLMGetAllMetadataListResponse)
    assert len(result.llm_metadata) == 2
    assert all(
        isinstance(llm_eval, LLMGetAllMetadataResponse)
        for llm_eval in result.llm_metadata
    )

    # opposite order since we specified descending
    assert result.llm_metadata[0].name == "test_llm_eval_1"
    assert result.llm_metadata[1].name == "test_llm_eval_0"

    for i in range(2):
        llm_evals_repo.delete_llm_item(task_id, f"test_llm_eval_{i}")


@pytest.mark.unit_tests
def test_get_all_evals_empty(llm_evals_repo):
    """Test getting all llm evals when none exist"""
    task_id = "empty_task"

    # Use default pagination parameters
    pagination_parameters = PaginationParameters(
        page=0,
        page_size=10,
        sort=PaginationSortMethod.DESCENDING,
    )
    result = llm_evals_repo.get_all_llm_item_metadata(task_id, pagination_parameters)

    assert isinstance(result, LLMGetAllMetadataListResponse)
    assert len(result.llm_metadata) == 0


@pytest.mark.unit_tests
@pytest.mark.parametrize(
    "filter_param,filter_value,expected_count,expected_name",
    [
        ("model_provider", ModelProvider.OPENAI, 1, "eval_openai"),
        ("model_name", "gpt-4", 1, "eval_openai"),
        ("llm_asset_names", ["eval_openai"], 1, "eval_openai"),
        ("created_after", None, 2, None),
        ("created_before", None, 1, "eval_openai"),
    ],
)
def test_get_all_llm_eval_metadata_with_filters(
    llm_evals_repo,
    filter_param,
    filter_value,
    expected_count,
    expected_name,
):
    """Test getting all eval metadata with filter_request parameters"""
    task_id = "test_task_id"

    # Create multiple evals with different providers and models
    evals_data = [
        CreateEvalRequest(
            model_name="gpt-4",
            model_provider="openai",
            instructions="OpenAI eval",
        ),
        CreateEvalRequest(
            model_name="claude-3-5-sonnet",
            model_provider="anthropic",
            instructions="Anthropic eval",
        ),
    ]

    for i, eval_data in enumerate(evals_data):
        result = llm_evals_repo.save_llm_item(
            task_id,
            f"eval_{eval_data.model_provider.value}",
            CreateEvalRequest(**eval_data.model_dump()),
        )
        if filter_param == "created_after" and i == 0:
            filter_value = result.created_at
        elif filter_param == "created_before" and i == 1:
            filter_value = result.created_at

    try:
        # Create filter request
        filter_request = LLMGetAllFilterRequest(**{filter_param: filter_value})

        # Create pagination parameters
        pagination_params = PaginationParameters(
            page=0,
            page_size=10,
            sort=PaginationSortMethod.ASCENDING,
        )

        # Get filtered results
        result = llm_evals_repo.get_all_llm_item_metadata(
            task_id=task_id,
            pagination_parameters=pagination_params,
            filter_request=filter_request,
        )

        # Verify filtering worked
        assert isinstance(result, LLMGetAllMetadataListResponse)
        assert result.count == expected_count
        assert len(result.llm_metadata) == expected_count

        # Verify the correct eval was returned based on the filter
        if expected_name:
            assert result.llm_metadata[0].name == expected_name

    finally:
        # Cleanup
        for eval_data in evals_data:
            llm_evals_repo.delete_llm_item(
                task_id,
                f"eval_{eval_data.model_provider.value}",
            )


@pytest.mark.unit_tests
@pytest.mark.parametrize(
    "page,page_size,sort,expected_names",
    [
        (0, 2, PaginationSortMethod.ASCENDING, ["eval_0", "eval_1"]),
        (1, 2, PaginationSortMethod.ASCENDING, ["eval_2"]),
        (0, 3, PaginationSortMethod.DESCENDING, ["eval_2", "eval_1", "eval_0"]),
        (0, 10, PaginationSortMethod.ASCENDING, ["eval_0", "eval_1", "eval_2"]),
        (2, 1, PaginationSortMethod.ASCENDING, ["eval_2"]),
    ],
)
def test_get_all_llm_eval_metadata_with_pagination(
    llm_evals_repo,
    sample_create_eval_request,
    page,
    page_size,
    sort,
    expected_names,
):
    """Test getting all llm eval metadata with all pagination parameters (page, page_size, sort)"""
    task_id = "test_task_id"

    # Create multiple evals
    for i in range(3):
        llm_evals_repo.save_llm_item(task_id, f"eval_{i}", sample_create_eval_request)

    try:
        # Create pagination parameters
        pagination_params = PaginationParameters(
            page=page,
            page_size=page_size,
            sort=sort,
        )

        # Get paginated results
        result = llm_evals_repo.get_all_llm_item_metadata(
            task_id=task_id,
            pagination_parameters=pagination_params,
        )

        # Verify pagination worked
        assert isinstance(result, LLMGetAllMetadataListResponse)
        assert result.count == 3  # Total count should always be 3
        assert len(result.llm_metadata) == len(expected_names)

        # Verify the order of the evals
        for i, expected_name in enumerate(expected_names):
            assert result.llm_metadata[i].name == expected_name

    finally:
        # Cleanup
        for i in range(3):
            llm_evals_repo.delete_llm_item(task_id, f"eval_{i}")


@pytest.mark.unit_tests
@patch("clients.llm.llm_client.completion_cost")
@patch("clients.llm.llm_client.litellm.completion")
def test_run_saved_llm_eval(
    mock_completion,
    mock_completion_cost,
    mock_llm_client,
    llm_evals_repo,
    sample_create_eval_request,
):
    """Test running a saved llm eval from database"""
    task_id = "test_task_id"
    eval_name = "test_llm_eval"

    full_eval = llm_evals_repo.save_llm_item(
        task_id,
        eval_name,
        sample_create_eval_request,
    )

    # Mock completion response
    mock_response = MagicMock(spec=ModelResponse)
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message = {
        "content": '{"reason": "This answer is true because it is supported by the ground truth.", "score": 1}',
    }
    mock_completion.return_value = mock_response
    mock_completion_cost.return_value = 0.002345

    llm_evals_repo.model_provider_repo.get_model_provider_client = MagicMock(
        return_value=mock_llm_client,
    )

    result = llm_evals_repo.run_llm_eval(task_id, eval_name)

    assert isinstance(result, LLMEvalRunResponse)
    assert (
        result.reason
        == "This answer is true because it is supported by the ground truth."
    )
    assert result.score == 1
    assert result.cost == "0.002345"

    llm_evals_repo.delete_llm_item(task_id, eval_name)


@pytest.mark.unit_tests
def test_run_deleted_llm_eval_spawns_error(
    llm_evals_repo,
    sample_create_eval_request,
    mock_llm_client,
):
    """Test running a deleted llm eval spawns an error"""
    task_id = "test_task_id"
    eval_name = "test_llm_eval"

    full_eval = llm_evals_repo.save_llm_item(
        task_id,
        eval_name,
        sample_create_eval_request,
    )
    llm_evals_repo.soft_delete_llm_item_version(task_id, eval_name, "latest")

    llm_evals_repo.model_provider_repo.get_model_provider_client = MagicMock(
        return_value=mock_llm_client,
    )

    with pytest.raises(ValueError) as exc_info:
        llm_evals_repo.run_llm_eval(task_id, eval_name, version="1")
    assert f"Cannot run this llm eval because it was deleted on" in str(exc_info.value)

    llm_evals_repo.delete_llm_item(task_id, eval_name)


@pytest.mark.unit_tests
@patch("clients.llm.llm_client.LLMClient.completion")
def test_run_saved_llm_eval_malformed_response_errors(
    mock_completion,
    llm_evals_repo,
    sample_create_eval_request,
    mock_llm_client,
):
    """Test running a saved llm eval with a malformed response from the llm client raises errors"""
    task_id = "test_task_id"
    eval_name = "test_llm_eval"

    full_eval = llm_evals_repo.save_llm_item(
        task_id,
        eval_name,
        sample_create_eval_request,
    )

    # check if the structured output response is None it raises the appropriate error
    mock_response = MagicMock(spec=LLMModelResponse)
    mock_response.structured_output_response = None
    mock_completion.return_value = mock_response

    llm_evals_repo.model_provider_repo.get_model_provider_client = MagicMock(
        return_value=mock_llm_client,
    )

    with pytest.raises(ValueError) as exc_info:
        llm_evals_repo.run_llm_eval(task_id, eval_name, version="1")
    assert (
        f"No structured output response from model {full_eval.model_name} with provider {full_eval.model_provider}"
        in str(exc_info.value)
    )

    # check if the structured output response is not the correct type it raises the appropriate error
    mock_response = MagicMock(spec=LLMModelResponse)
    mock_response.structured_output_response = full_eval
    mock_completion.return_value = mock_response

    llm_evals_repo.model_provider_repo.get_model_provider_client = MagicMock(
        return_value=mock_llm_client,
    )

    with pytest.raises(TypeError) as exc_info:
        llm_evals_repo.run_llm_eval(task_id, eval_name, version="1")
    assert f"Structured output is not a ReasonedScore instance" in str(exc_info.value)

    llm_evals_repo.delete_llm_item(task_id, eval_name)


@pytest.mark.unit_tests
def test_save_llm_eval_with_empty_model_name_spawns_error(llm_evals_repo):
    """Test saving an llm eval with an empty model name spawns an error"""
    task_id = str(uuid4())
    eval_name = "test_eval"
    llm_eval = CreateEvalRequest(
        model_name="",
        model_provider="openai",
        instructions="Hello, world!",
    )
    with pytest.raises(ValueError, match="Model name cannot be empty."):
        llm_evals_repo.save_llm_item(task_id, eval_name, llm_eval)


@pytest.mark.unit_tests
def test_get_llm_eval_by_tag_success(llm_evals_repo, sample_create_eval_request):
    """Test getting an llm eval by tag successfully"""
    task_id = str(uuid4())
    eval_name = "test_eval"

    # save an eval
    created_eval = llm_evals_repo.save_llm_item(
        task_id,
        eval_name,
        sample_create_eval_request,
    )

    try:
        llm_evals_repo.add_tag_to_llm_item_version(
            task_id,
            eval_name,
            "latest",
            "test_tag",
        )
        result = llm_evals_repo.get_llm_item_by_tag(task_id, eval_name, "test_tag")

        assert isinstance(result, LLMEval)
        assert result.name == eval_name
        assert result.tags == ["test_tag"]
        assert result.version == created_eval.version
    finally:
        # Cleanup
        llm_evals_repo.delete_llm_item(task_id, eval_name)


@pytest.mark.unit_tests
def test_get_llm_eval_by_empty_tag_error(llm_evals_repo):
    """Test getting an llm eval by empty tag raises an error"""
    task_id = str(uuid4())
    eval_name = "test_eval"

    with pytest.raises(ValueError) as exc_info:
        llm_evals_repo.get_llm_item_by_tag(task_id, eval_name, "")
    assert "Tag cannot be empty" in str(exc_info.value)


@pytest.mark.unit_tests
def test_get_llm_eval_by_tag_not_found_error(
    llm_evals_repo,
    sample_create_eval_request,
):
    """Test getting an llm eval by tag that doesn't exist raises an error"""
    task_id = str(uuid4())
    eval_name = "test_eval"

    # save an eval
    created_eval = llm_evals_repo.save_llm_item(
        task_id,
        eval_name,
        sample_create_eval_request,
    )

    with pytest.raises(ValueError) as exc_info:
        llm_evals_repo.get_llm_item_by_tag(task_id, eval_name, "test_tag")
    assert (
        f"Tag 'test_tag' not found for task '{task_id}' and item '{eval_name}'"
        in str(exc_info.value)
    )

    llm_evals_repo.delete_llm_item(task_id, eval_name)


@pytest.mark.unit_tests
def test_add_tag_to_llm_eval_success(llm_evals_repo, sample_create_eval_request):
    """Test adding a tag to an llm eval successfully"""
    task_id = str(uuid4())
    eval_name = "test_eval"

    # save an eval
    created_eval = llm_evals_repo.save_llm_item(
        task_id,
        eval_name,
        sample_create_eval_request,
    )

    try:
        result = llm_evals_repo.add_tag_to_llm_item_version(
            task_id,
            eval_name,
            "latest",
            "test_tag",
        )

        assert isinstance(result, LLMEval)
        assert result.name == eval_name
        assert result.tags == ["test_tag"]
        assert result.version == created_eval.version
    finally:
        # Cleanup
        llm_evals_repo.delete_llm_item(task_id, eval_name)


@pytest.mark.unit_tests
def test_add_duplicate_tags_does_not_error(llm_evals_repo, sample_create_eval_request):
    """
    Test adding a tag of the same name to the same eval does not error it should
    just move that tag to the version being added to.
    """
    task_id = str(uuid4())
    eval_name = "test_eval"

    # save an eval
    for i in range(2):
        llm_evals_repo.save_llm_item(task_id, eval_name, sample_create_eval_request)

    try:
        # add tag to version 2
        result = llm_evals_repo.add_tag_to_llm_item_version(
            task_id,
            eval_name,
            "2",
            "test_tag",
        )

        assert isinstance(result, LLMEval)
        assert result.name == eval_name
        assert result.tags == ["test_tag"]
        assert result.version == 2

        # verify version 1 has no tags
        result = llm_evals_repo.get_llm_item(task_id, eval_name, "1")

        assert isinstance(result, LLMEval)
        assert result.name == eval_name
        assert result.tags == []
        assert result.version == 1

        # move tag to version 1
        result = llm_evals_repo.add_tag_to_llm_item_version(
            task_id,
            eval_name,
            "1",
            "test_tag",
        )

        assert isinstance(result, LLMEval)
        assert result.name == eval_name
        assert result.tags == ["test_tag"]
        assert result.version == 1

        # verify that tag was removed from version 2
        result = llm_evals_repo.get_llm_item(task_id, eval_name, "2")

        assert isinstance(result, LLMEval)
        assert result.name == eval_name
        assert result.tags == []
        assert result.version == 2
    finally:
        # Cleanup
        llm_evals_repo.delete_llm_item(task_id, eval_name)


@pytest.mark.unit_tests
def test_add_duplicate_tags_errors_in_db(llm_evals_repo, sample_create_eval_request):
    """
    Test that the database does not allow duplicate tags for the same eval version
    """
    task_id = str(uuid4())
    eval_name = "test_eval"
    db_session = override_get_db_session()

    # save an eval
    created_eval = llm_evals_repo.save_llm_item(
        task_id,
        eval_name,
        sample_create_eval_request,
    )

    duplicate_tag = DatabaseLLMEvalVersionTag(
        task_id=task_id,
        name=eval_name,
        version=created_eval.version,
        tag="test_tag",
    )
    db_session.add(duplicate_tag)
    db_session.commit()

    # try to add a duplicate tag
    duplicate_tag = DatabaseLLMEvalVersionTag(
        task_id=task_id,
        name=eval_name,
        version=created_eval.version,
        tag="test_tag",
    )
    db_session.add(duplicate_tag)

    with pytest.raises(IntegrityError):
        db_session.commit()

    # Cleanup
    llm_evals_repo.delete_llm_item(task_id, eval_name)


@pytest.mark.unit_tests
def test_add_duplicate_tags_errors_in_db_with_different_versions(
    llm_evals_repo,
    sample_create_eval_request,
):
    """
    Test that the database does not allow duplicate tags for the same eval name but different versions
    """
    task_id = str(uuid4())
    eval_name = "test_eval"
    db_session = override_get_db_session()

    # save an eval
    created_evals = []
    for i in range(2):
        created_evals.append(
            llm_evals_repo.save_llm_item(
                task_id,
                eval_name,
                sample_create_eval_request,
            ),
        )

    duplicate_tag = DatabaseLLMEvalVersionTag(
        task_id=task_id,
        name=eval_name,
        version=created_evals[0].version,
        tag="test_tag",
    )
    db_session.add(duplicate_tag)
    db_session.commit()

    # try to add a duplicate tag
    duplicate_tag = DatabaseLLMEvalVersionTag(
        task_id=task_id,
        name=eval_name,
        version=created_evals[1].version,
        tag="test_tag",
    )
    db_session.add(duplicate_tag)

    with pytest.raises(IntegrityError):
        db_session.commit()

    # Cleanup
    llm_evals_repo.delete_llm_item(task_id, eval_name)


@pytest.mark.unit_tests
def test_add_tag_to_llm_eval_malformed_tag_error(
    llm_evals_repo,
    sample_create_eval_request,
):
    """Test adding a tag to an llm eval with a malformed tag raises an error"""
    task_id = str(uuid4())
    eval_name = "test_eval"

    # save an eval
    created_eval = llm_evals_repo.save_llm_item(
        task_id,
        eval_name,
        sample_create_eval_request,
    )

    with pytest.raises(ValueError) as exc_info:
        llm_evals_repo.add_tag_to_llm_item_version(task_id, eval_name, "latest", "")

    assert "Tag cannot be empty" in str(exc_info.value)

    with pytest.raises(ValueError) as exc_info:
        llm_evals_repo.add_tag_to_llm_item_version(
            task_id,
            eval_name,
            "latest",
            "latest",
        )

    assert "'latest' is a reserved tag" in str(exc_info.value)

    # Cleanup
    llm_evals_repo.delete_llm_item(task_id, eval_name)


@pytest.mark.unit_tests
def test_add_tag_to_llm_eval_to_nonexistent_version_error(llm_evals_repo):
    """Test adding a tag to an llm eval to a nonexistent version raises an error"""
    task_id = str(uuid4())
    eval_name = "test_eval"

    with pytest.raises(ValueError) as exc_info:
        llm_evals_repo.add_tag_to_llm_item_version(
            task_id,
            eval_name,
            "latest",
            "test_tag",
        )

    assert f"'{eval_name}' (version 'latest') not found for task '{task_id}'" in str(
        exc_info.value,
    )


@pytest.mark.unit_tests
def test_add_tag_to_llm_eval_to_soft_deleted_version_error(
    llm_evals_repo,
    sample_create_eval_request,
):
    """Test adding a tag to an llm eval to a soft deleted version raises an error"""
    task_id = str(uuid4())
    eval_name = "test_eval"

    # save an eval
    created_eval = llm_evals_repo.save_llm_item(
        task_id,
        eval_name,
        sample_create_eval_request,
    )

    # soft delete the version
    llm_evals_repo.soft_delete_llm_item_version(task_id, eval_name, "latest")

    with pytest.raises(ValueError) as exc_info:
        llm_evals_repo.add_tag_to_llm_item_version(
            task_id,
            eval_name,
            str(created_eval.version),
            "test_tag",
        )

    assert f"Cannot add tag to a deleted version of '{eval_name}'" in str(
        exc_info.value,
    )

    # Cleanup
    llm_evals_repo.delete_llm_item(task_id, eval_name)


@pytest.mark.unit_tests
def test_soft_delete_llm_eval_version_removes_tags_from_db(
    llm_evals_repo,
    sample_create_eval_request,
):
    """Test soft deleting an llm eval version removes all tags associated with that version"""
    task_id = str(uuid4())
    eval_name = "test_eval"

    # save an eval
    created_eval = llm_evals_repo.save_llm_item(
        task_id,
        eval_name,
        sample_create_eval_request,
    )

    # add a tag to the version
    llm_evals_repo.add_tag_to_llm_item_version(
        task_id,
        eval_name,
        str(created_eval.version),
        "test_tag",
    )

    # soft delete the version
    llm_evals_repo.soft_delete_llm_item_version(task_id, eval_name, "latest")

    # verify that the tag was removed from the version
    with pytest.raises(ValueError) as exc_info:
        llm_evals_repo.get_llm_item_by_tag(task_id, eval_name, "test_tag")
    assert (
        f"Tag 'test_tag' not found for task '{task_id}' and item '{eval_name}'"
        in str(exc_info.value)
    )

    # Cleanup
    llm_evals_repo.delete_llm_item(task_id, eval_name)


@pytest.mark.unit_tests
def test_remove_tag_from_llm_eval_version_success(
    llm_evals_repo,
    sample_create_eval_request,
):
    """Test removing a tag from an llm eval version successfully"""
    task_id = str(uuid4())
    eval_name = "test_eval"

    # save an eval
    created_eval = llm_evals_repo.save_llm_item(
        task_id,
        eval_name,
        sample_create_eval_request,
    )

    # add a tag to the version
    llm_evals_repo.add_tag_to_llm_item_version(
        task_id,
        eval_name,
        str(created_eval.version),
        "test_tag",
    )

    # remove the tag from the version
    llm_evals_repo.delete_llm_item_tag_from_version(
        task_id,
        eval_name,
        str(created_eval.version),
        "test_tag",
    )

    # verify that the tag was removed from the version
    with pytest.raises(ValueError) as exc_info:
        llm_evals_repo.get_llm_item_by_tag(task_id, eval_name, "test_tag")
    assert (
        f"Tag 'test_tag' not found for task '{task_id}' and item '{eval_name}'"
        in str(exc_info.value)
    )

    # verify that the version still exists
    result = llm_evals_repo.get_llm_item(task_id, eval_name, str(created_eval.version))
    assert isinstance(result, LLMEval)
    assert result.name == eval_name
    assert result.tags == []
    assert result.version == created_eval.version

    # Cleanup
    llm_evals_repo.delete_llm_item(task_id, eval_name)


@pytest.mark.unit_tests
def test_remove_tag_from_llm_eval_version_dne_error(
    llm_evals_repo,
    sample_create_eval_request,
):
    """Test removing a tag from an llm eval version that does not exist raises an error"""
    task_id = str(uuid4())
    eval_name = "test_eval"

    # save an eval
    created_eval = llm_evals_repo.save_llm_item(
        task_id,
        eval_name,
        sample_create_eval_request,
    )

    # remove the tag from the version
    with pytest.raises(ValueError) as exc_info:
        llm_evals_repo.delete_llm_item_tag_from_version(
            task_id,
            eval_name,
            str(created_eval.version),
            "test_tag",
        )
    assert (
        f"Tag 'test_tag' not found for task '{task_id}', item '{eval_name}' and version '{created_eval.version}'."
        in str(exc_info.value)
    )

    # Cleanup
    llm_evals_repo.delete_llm_item(task_id, eval_name)
