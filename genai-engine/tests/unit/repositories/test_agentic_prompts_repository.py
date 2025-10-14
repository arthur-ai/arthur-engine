from datetime import datetime
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError

from db_models.agentic_prompt_models import DatabaseAgenticPrompt
from repositories.agentic_prompts_repository import (
    AgenticPrompt,
    AgenticPromptRepository,
    AgenticPromptRunResponse,
    AgenticPrompts,
)


@pytest.fixture
def mock_db_session():
    """Mock database session for testing"""
    return MagicMock()


@pytest.fixture
def agentic_prompt_repo(mock_db_session):
    """Create AgenticPromptRepository instance with mocked db session"""
    return AgenticPromptRepository(mock_db_session)


@pytest.fixture
def sample_prompt_data():
    """Sample prompt data for testing"""
    return {
        "name": "test_prompt",
        "messages": [{"role": "user", "content": "Hello, world!"}],
        "model_name": "gpt-4",
        "model_provider": "openai",
        "temperature": 0.7,
        "max_tokens": 100,
        "tools": [{"type": "function", "function": {"name": "test_tool"}}],
        "tool_choice": "auto",
    }


@pytest.fixture
def sample_agentic_prompt(sample_prompt_data):
    """Create sample AgenticPrompt instance"""
    return AgenticPrompt(**sample_prompt_data)


@pytest.fixture
def sample_db_prompt(sample_prompt_data):
    """Create sample DatabaseAgenticPrompt instance"""
    task_id = str(uuid4())
    return AgenticPrompt(**sample_prompt_data).to_db_model(task_id)


@pytest.mark.unit_tests
def test_create_prompt(agentic_prompt_repo, sample_prompt_data):
    """Test creating a new AgenticPrompt instance"""
    prompt = agentic_prompt_repo.create_prompt(**sample_prompt_data)

    assert isinstance(prompt, AgenticPrompt)
    assert prompt.name == sample_prompt_data["name"]
    assert prompt.messages == sample_prompt_data["messages"]
    assert prompt.model_name == sample_prompt_data["model_name"]
    assert prompt.model_provider == sample_prompt_data["model_provider"]
    assert prompt.temperature == sample_prompt_data["temperature"]
    assert prompt.max_tokens == sample_prompt_data["max_tokens"]


@pytest.mark.unit_tests
@patch("repositories.agentic_prompts_repository.completion")
@patch("repositories.agentic_prompts_repository.completion_cost")
def test_run_prompt(
    mock_completion_cost,
    mock_completion,
    agentic_prompt_repo,
    sample_agentic_prompt,
):
    """Test running a prompt and getting response"""
    # Mock completion response
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message = {
        "content": "Test response",
        "tool_calls": [{"id": "call_123", "function": {"name": "test_tool"}}],
    }
    mock_completion.return_value = mock_response
    mock_completion_cost.return_value = 0.001234

    result = agentic_prompt_repo.run_prompt(sample_agentic_prompt)

    assert isinstance(result, AgenticPromptRunResponse)
    assert result.content == "Test response"
    assert result.tool_calls == [{"id": "call_123", "function": {"name": "test_tool"}}]
    assert result.cost == "0.001234"

    # Verify completion was called with correct parameters
    mock_completion.assert_called_once()
    call_args = mock_completion.call_args[1]
    assert call_args["model"] == "openai/gpt-4"
    assert call_args["messages"] == sample_agentic_prompt.messages
    assert call_args["temperature"] == sample_agentic_prompt.temperature


@pytest.mark.unit_tests
def test_get_prompt_success(agentic_prompt_repo, mock_db_session, sample_db_prompt):
    """Test successfully getting a prompt from database"""
    task_id = "test_task_id"
    prompt_name = "test_prompt"

    # Mock database query
    mock_query = MagicMock()
    mock_filter = MagicMock()
    mock_db_session.query.return_value = mock_query
    mock_query.filter.return_value = mock_filter
    mock_filter.first.return_value = sample_db_prompt

    result = agentic_prompt_repo.get_prompt(task_id, prompt_name)

    assert isinstance(result, AgenticPrompt)
    assert result.name == sample_db_prompt.name
    assert result.messages == sample_db_prompt.messages

    # Verify database query was called correctly
    mock_db_session.query.assert_called_once_with(DatabaseAgenticPrompt)
    mock_query.filter.assert_called_once()


@pytest.mark.unit_tests
def test_get_prompt_not_found(agentic_prompt_repo, mock_db_session):
    """Test getting a prompt that doesn't exist"""
    task_id = "nonexistent_task"
    prompt_name = "nonexistent_prompt"

    # Mock database query returning None
    mock_query = MagicMock()
    mock_filter = MagicMock()
    mock_db_session.query.return_value = mock_query
    mock_query.filter.return_value = mock_filter
    mock_filter.first.return_value = None

    with pytest.raises(
        ValueError,
        match="Prompt 'nonexistent_prompt' not found for task 'nonexistent_task'",
    ):
        agentic_prompt_repo.get_prompt(task_id, prompt_name)


@pytest.mark.unit_tests
def test_get_all_prompts(agentic_prompt_repo, mock_db_session, sample_db_prompt):
    """Test getting all prompts for a task"""
    task_id = "test_task_id"

    # Create multiple sample prompts
    prompt2 = DatabaseAgenticPrompt(
        task_id=task_id,
        name="prompt2",
        messages=[{"role": "user", "content": "Second prompt"}],
        model_name="gpt-3.5-turbo",
        model_provider="openai",
        created_at=datetime.now(),
    )

    # Mock database query
    mock_query = MagicMock()
    mock_filter = MagicMock()
    mock_db_session.query.return_value = mock_query
    mock_query.filter.return_value = mock_filter
    mock_filter.all.return_value = [sample_db_prompt, prompt2]

    result = agentic_prompt_repo.get_all_prompts(task_id)

    assert isinstance(result, AgenticPrompts)
    assert len(result.prompts) == 2
    assert all(isinstance(prompt, AgenticPrompt) for prompt in result.prompts)
    assert result.prompts[0].name == sample_db_prompt.name
    assert result.prompts[1].name == prompt2.name


@pytest.mark.unit_tests
def test_get_all_prompts_empty(agentic_prompt_repo, mock_db_session):
    """Test getting all prompts when none exist"""
    task_id = "empty_task"

    # Mock database query returning empty list
    mock_query = MagicMock()
    mock_filter = MagicMock()
    mock_db_session.query.return_value = mock_query
    mock_query.filter.return_value = mock_filter
    mock_filter.all.return_value = []

    result = agentic_prompt_repo.get_all_prompts(task_id)

    assert isinstance(result, AgenticPrompts)
    assert len(result.prompts) == 0


@pytest.mark.unit_tests
def test_save_prompt_with_agentic_prompt_object(
    agentic_prompt_repo,
    mock_db_session,
    sample_agentic_prompt,
):
    """Test saving an AgenticPrompt object to database"""
    task_id = "test_task_id"

    agentic_prompt_repo.save_prompt(task_id, sample_agentic_prompt)

    # Verify database operations
    mock_db_session.add.assert_called_once()
    mock_db_session.commit.assert_called_once()

    # Check the DatabaseAgenticPrompt object that was added
    added_prompt = mock_db_session.add.call_args[0][0]
    assert isinstance(added_prompt, DatabaseAgenticPrompt)
    assert added_prompt.task_id == task_id
    assert added_prompt.name == sample_agentic_prompt.name
    assert added_prompt.messages == sample_agentic_prompt.messages


@pytest.mark.unit_tests
def test_save_prompt_with_dict(
    agentic_prompt_repo,
    mock_db_session,
    sample_prompt_data,
):
    """Test saving a prompt from dictionary data"""
    task_id = "test_task_id"

    agentic_prompt_repo.save_prompt(task_id, sample_prompt_data)

    # Verify database operations
    mock_db_session.add.assert_called_once()
    mock_db_session.commit.assert_called_once()

    # Check the DatabaseAgenticPrompt object that was added
    added_prompt = mock_db_session.add.call_args[0][0]
    assert isinstance(added_prompt, DatabaseAgenticPrompt)
    assert added_prompt.task_id == task_id
    assert added_prompt.name == sample_prompt_data["name"]


@pytest.mark.unit_tests
def test_save_prompt_integrity_error(
    agentic_prompt_repo,
    mock_db_session,
    sample_agentic_prompt,
):
    """Test saving a prompt when it already exists (IntegrityError)"""
    task_id = "test_task_id"

    # Mock IntegrityError on commit
    mock_db_session.commit.side_effect = IntegrityError("", "", "")

    with pytest.raises(
        ValueError,
        match="Prompt 'test_prompt' already exists for task 'test_task_id'",
    ):
        agentic_prompt_repo.save_prompt(task_id, sample_agentic_prompt)

    # Verify rollback was called
    mock_db_session.rollback.assert_called_once()


@pytest.mark.unit_tests
def test_delete_prompt_success(agentic_prompt_repo, mock_db_session, sample_db_prompt):
    """Test successfully deleting a prompt"""
    task_id = "test_task_id"
    prompt_name = "test_prompt"

    # Mock database query
    mock_query = MagicMock()
    mock_filter = MagicMock()
    mock_db_session.query.return_value = mock_query
    mock_query.filter.return_value = mock_filter
    mock_filter.first.return_value = sample_db_prompt

    agentic_prompt_repo.delete_prompt(task_id, prompt_name)

    # Verify database operations
    mock_db_session.delete.assert_called_once_with(sample_db_prompt)
    mock_db_session.commit.assert_called_once()


@pytest.mark.unit_tests
def test_delete_prompt_not_found(agentic_prompt_repo, mock_db_session):
    """Test deleting a prompt that doesn't exist"""
    task_id = "nonexistent_task"
    prompt_name = "nonexistent_prompt"

    # Mock database query returning None
    mock_query = MagicMock()
    mock_filter = MagicMock()
    mock_db_session.query.return_value = mock_query
    mock_query.filter.return_value = mock_filter
    mock_filter.first.return_value = None

    with pytest.raises(
        ValueError,
        match="Prompt 'nonexistent_prompt' not found for task 'nonexistent_task'",
    ):
        agentic_prompt_repo.delete_prompt(task_id, prompt_name)


@pytest.mark.unit_tests
@patch("repositories.agentic_prompts_repository.completion")
@patch("repositories.agentic_prompts_repository.completion_cost")
def test_run_saved_prompt(
    mock_completion_cost,
    mock_completion,
    agentic_prompt_repo,
    mock_db_session,
    sample_db_prompt,
):
    """Test running a saved prompt from database"""
    task_id = "test_task_id"
    prompt_name = "test_prompt"

    # Mock database query
    mock_query = MagicMock()
    mock_filter = MagicMock()
    mock_db_session.query.return_value = mock_query
    mock_query.filter.return_value = mock_filter
    mock_filter.first.return_value = sample_db_prompt

    # Mock completion response
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message = {
        "content": "Saved prompt response",
        "tool_calls": None,
    }
    mock_completion.return_value = mock_response
    mock_completion_cost.return_value = 0.002345

    result = agentic_prompt_repo.run_saved_prompt(task_id, prompt_name)

    assert isinstance(result, AgenticPromptRunResponse)
    assert result.content == "Saved prompt response"
    assert result.cost == "0.002345"


@pytest.mark.unit_tests
def test_agentic_prompt_from_db_model(sample_db_prompt):
    """Test creating AgenticPrompt from DatabaseAgenticPrompt"""
    prompt = AgenticPrompt.from_db_model(sample_db_prompt)

    assert isinstance(prompt, AgenticPrompt)
    assert prompt.name == sample_db_prompt.name
    assert prompt.messages == sample_db_prompt.messages
    assert prompt.model_name == sample_db_prompt.model_name
    assert prompt.model_provider == sample_db_prompt.model_provider


@pytest.mark.unit_tests
def test_agentic_prompt_to_dict(sample_agentic_prompt):
    """Test converting AgenticPrompt to dictionary"""
    prompt_dict = sample_agentic_prompt.to_dict()

    assert isinstance(prompt_dict, dict)
    assert prompt_dict["name"] == sample_agentic_prompt.name
    assert prompt_dict["messages"] == sample_agentic_prompt.messages
    assert prompt_dict["model_name"] == sample_agentic_prompt.model_name
    assert prompt_dict["model_provider"] == sample_agentic_prompt.model_provider


@pytest.mark.unit_tests
@patch("repositories.agentic_prompts_repository.completion")
@patch("repositories.agentic_prompts_repository.completion_cost")
def test_agentic_prompt_run_chat_completion(
    mock_completion_cost,
    mock_completion,
    sample_agentic_prompt,
):
    """Test running chat completion directly on AgenticPrompt"""
    # Mock completion response
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message = {
        "content": "Direct completion response",
        "tool_calls": [{"id": "call_456"}],
    }
    mock_completion.return_value = mock_response
    mock_completion_cost.return_value = 0.003456

    result = sample_agentic_prompt.run_chat_completion()

    assert result.content == "Direct completion response"
    assert result.tool_calls == [{"id": "call_456"}]
    assert result.cost == "0.003456"

    # Verify completion was called with correct model format
    mock_completion.assert_called_once()
    call_args = mock_completion.call_args[1]
    assert call_args["model"] == "openai/gpt-4"
