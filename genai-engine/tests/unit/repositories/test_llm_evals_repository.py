from datetime import datetime
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError

from db_models.llm_eval_models import DatabaseLLMEval
from repositories.llm_evals_repository import LLMEvalsRepository
from schemas.agentic_prompt_schemas import LLMConfigSettings
from schemas.llm_eval_schemas import LLMEval
from schemas.request_schemas import CreateEvalRequest
from tests.clients.base_test_client import override_get_db_session


@pytest.fixture
def mock_db_session():
    return MagicMock()


@pytest.fixture
def llm_evals_repo(mock_db_session):
    return LLMEvalsRepository(db_session=mock_db_session)


@pytest.fixture
def sample_llm_eval():
    return LLMEval(
        name="test_llm_eval",
        model_name="gpt-4o",
        model_provider="openai",
        instructions="test_instructions",
        config=LLMConfigSettings(temperature=0.5, max_tokens=100),
        version=1,
    )


@pytest.fixture
def sample_create_eval_request():
    return CreateEvalRequest(
        model_name="gpt-4o",
        model_provider="openai",
        instructions="test_instructions",
        config=LLMConfigSettings(temperature=0.5, max_tokens=100),
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
        min_score=0,
        max_score=1,
        config=LLMConfigSettings(temperature=0.5, max_tokens=100),
        created_at=datetime.now(),
        deleted_at=None,
        version=1,
    )


@pytest.mark.unit_tests
def test_save_llm_eval_integrity_error(
    llm_evals_repo,
    sample_create_eval_request,
    mock_db_session,
):
    """Test saving an llm eval when it already exists (IntegrityError)"""
    task_id = "test_task_id"

    # Mock IntegrityError on commit
    mock_db_session.commit.side_effect = IntegrityError("", "", Exception(""))

    with pytest.raises(ValueError) as exc_info:
        llm_evals_repo.save_eval(
            task_id,
            sample_llm_eval.name,
            sample_create_eval_request,
        )

    assert (
        str(exc_info.value)
        == f"Failed to save llm eval '{sample_llm_eval.name}' for task '{task_id}' — possible duplicate constraint."
    )

    # Verify rollback was called
    mock_db_session.rollback.assert_called_once()


@pytest.mark.unit_tests
def test_save_llm_eval_with_llm_eval_object(
    llm_evals_repo,
    mock_db_session,
    sample_llm_eval,
    sample_create_eval_request,
):
    """Test saving an LLMEval object to database"""
    task_id = "test_task_id"

    mock_db_session.query.return_value.filter.return_value.scalar.return_value = 0

    result = llm_evals_repo.save_eval(
        task_id,
        sample_llm_eval.name,
        sample_create_eval_request,
    )

    # Verify database operations
    mock_db_session.add.assert_called_once()
    mock_db_session.commit.assert_called_once()

    # Check the DatabaseLLMEval object that was added
    added_eval = mock_db_session.add.call_args[0][0]

    # Compare was inserted to the database correctly
    assert isinstance(added_eval, DatabaseLLMEval)
    assert added_eval.task_id == task_id
    assert added_eval.name == sample_llm_eval.name
    assert added_eval.model_name == sample_llm_eval.model_name
    assert added_eval.model_provider == sample_llm_eval.model_provider
    assert added_eval.instructions == sample_llm_eval.instructions
    assert added_eval.min_score == sample_llm_eval.min_score
    assert added_eval.max_score == sample_llm_eval.max_score
    assert added_eval.config == sample_llm_eval.config.model_dump(exclude_none=True)
    assert added_eval.version == sample_llm_eval.version
    assert added_eval.deleted_at is None

    assert result == sample_llm_eval


@pytest.mark.unit_tests
def test_llm_eval_from_db_model(sample_db_llm_eval):
    """Test creating LLMEval from DatabaseLLMEval"""
    llm_eval = LLMEval.from_db_model(sample_db_llm_eval)

    assert isinstance(llm_eval, LLMEval)
    assert llm_eval.name == sample_db_llm_eval.name
    assert llm_eval.model_name == sample_db_llm_eval.model_name
    assert llm_eval.model_provider == sample_db_llm_eval.model_provider
    assert llm_eval.instructions == sample_db_llm_eval.instructions
    assert llm_eval.min_score == sample_db_llm_eval.min_score
    assert llm_eval.max_score == sample_db_llm_eval.max_score
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
    assert llm_eval_dict["min_score"] == sample_llm_eval.min_score
    assert llm_eval_dict["max_score"] == sample_llm_eval.max_score
    assert "config" in llm_eval_dict
    assert llm_eval_dict["config"]["temperature"] == sample_llm_eval.config.temperature
    assert llm_eval_dict["config"]["max_tokens"] == sample_llm_eval.config.max_tokens
    assert llm_eval_dict["version"] == sample_llm_eval.version


@pytest.mark.unit_tests
def test_delete_eval_success(llm_evals_repo, mock_db_session, sample_db_llm_eval):
    """Test successfully deleting an llm eval"""
    task_id = "test_task_id"
    eval_name = "test_eval"

    # Mock database query
    mock_query = MagicMock()
    mock_filter = MagicMock()
    mock_db_session.query.return_value = mock_query
    mock_query.filter.return_value = mock_filter
    mock_filter.all.return_value = [sample_db_llm_eval]

    llm_evals_repo.delete_eval(task_id, eval_name)

    # Verify database operations
    mock_db_session.delete.assert_called_once_with(sample_db_llm_eval)
    mock_db_session.commit.assert_called_once()


@pytest.mark.unit_tests
def test_delete_eval_not_found(llm_evals_repo, mock_db_session):
    """Test deleting an llm eval that doesn't exist"""
    task_id = "nonexistent_task"
    eval_name = "nonexistent_eval"

    # Mock database query returning None
    mock_query = MagicMock()
    mock_filter = MagicMock()
    mock_db_session.query.return_value = mock_query
    mock_query.filter.return_value = mock_filter
    mock_filter.all.return_value = None

    with pytest.raises(
        ValueError,
        match="LLM eval 'nonexistent_eval' not found for task 'nonexistent_task'",
    ):
        llm_evals_repo.delete_eval(task_id, eval_name)


@pytest.mark.unit_tests
def test_soft_delete_eval_version_success(
    llm_evals_repo,
    mock_db_session,
    sample_db_llm_eval,
):
    """Test successfully soft-deleting an llm eval"""
    task_id = "test_task_id"
    eval_name = "test_eval"

    # Ensure deleted_at is initially None
    sample_db_llm_eval.deleted_at = None

    # Mock _get_db_eval_by_version to return sample_db_llm_eval
    llm_evals_repo._get_db_eval_by_version = MagicMock(return_value=sample_db_llm_eval)

    llm_evals_repo.soft_delete_eval_version(task_id, eval_name, "latest")

    # Validate the object was soft deleted
    assert sample_db_llm_eval.deleted_at is not None
    assert sample_db_llm_eval.model_name == ""
    assert sample_db_llm_eval.instructions == ""
    assert sample_db_llm_eval.min_score == 0
    assert sample_db_llm_eval.max_score == 1
    assert sample_db_llm_eval.config is None

    mock_db_session.commit.assert_called_once()


@pytest.mark.unit_tests
def test_soft_delete_eval_version_errors(llm_evals_repo, mock_db_session):
    """Test all error cases for soft_delete_eval_version"""
    task_id = "test_task"
    eval_name = "test_eval"

    deleted_db_llm_eval = DatabaseLLMEval(
        task_id=task_id,
        name=eval_name,
        model_name="",
        model_provider="openai",
        instructions="",
        min_score=0,
        max_score=1,
        config=None,
        created_at=datetime.now(),
        deleted_at=datetime.now(),
        version=1,
    )

    # --- Case 1: Not found ---
    llm_evals_repo._get_db_eval_by_version = MagicMock(
        side_effect=ValueError(
            f"No matching version of llm eval '{eval_name}' found for task '{task_id}'",
        ),
    )
    with pytest.raises(
        ValueError,
        match=f"No matching version of llm eval '{eval_name}' found for task '{task_id}'",
    ):
        llm_evals_repo.soft_delete_eval_version(task_id, eval_name, "latest")

    # --- Case 2: Already deleted ---
    llm_evals_repo._get_db_eval_by_version = MagicMock(return_value=deleted_db_llm_eval)
    with pytest.raises(ValueError) as exc_info:
        llm_evals_repo.soft_delete_eval_version(
            task_id,
            eval_name,
            str(deleted_db_llm_eval.version),
        )

    assert "has already been deleted" in str(exc_info.value)

    # --- Case 3: Invalid version format ---
    llm_evals_repo._get_db_eval_by_version = MagicMock(
        side_effect=ValueError("Invalid version format"),
    )
    with pytest.raises(ValueError, match="Invalid version format"):
        llm_evals_repo.soft_delete_eval_version(task_id, eval_name, "bad_version")


@pytest.mark.unit_tests
def test_validate_score_range():
    """Test max_score must be greater than min_score"""
    with pytest.raises(
        ValueError,
        match="min_score must be less than max_score",
    ):
        LLMEval(
            name="test_llm_eval",
            model_name="gpt-4o",
            model_provider="openai",
            min_score=1,
            max_score=1,
            instructions="test_instructions",
            config=LLMConfigSettings(temperature=0.5, max_tokens=100),
            version=1,
        )


@pytest.mark.unit_tests
@pytest.mark.parametrize("eval_version", ["latest", "1", "2025-01-01T00:00:00"])
def test_soft_delete_eval_by_version_success(eval_version):
    """Test deleting an eval with different version formats"""
    db_session = override_get_db_session()
    repo = LLMEvalsRepository(db_session=db_session)

    task_id = str(uuid4())
    eval_name = "test_eval"

    # Create a database eval with the sample data
    eval_data = LLMEval(
        name="test_eval",
        model_name="gpt-4o",
        model_provider="openai",
        instructions="test_instructions",
        min_score=0,
        max_score=1,
        version=1,
    )
    db_eval = eval_data.to_db_model(task_id)
    db_eval.created_at = datetime.fromisoformat("2025-01-01T00:00:00")

    # Save to database
    db_session.add(db_eval)
    db_session.commit()

    try:
        repo.soft_delete_eval_version(task_id, eval_name, eval_version)

        result = (
            db_session.query(DatabaseLLMEval)
            .filter(DatabaseLLMEval.task_id == task_id)
            .first()
        )

        assert isinstance(result, DatabaseLLMEval)
        assert result.name == eval_name
        assert result.model_name == ""
        assert result.model_provider == "openai"
        assert result.instructions == ""
        assert result.min_score == 0
        assert result.max_score == 1
        assert result.config is None
        assert result.version == 1
        assert result.deleted_at is not None
    finally:
        # Cleanup
        db_session.delete(db_eval)
        db_session.commit()
        db_session.close()
