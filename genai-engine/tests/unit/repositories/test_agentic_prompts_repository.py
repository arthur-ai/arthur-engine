from datetime import datetime
from types import SimpleNamespace
from typing import Any, Dict, List
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from arthur_common.models.common_schemas import PaginationParameters
from arthur_common.models.enums import PaginationSortMethod
from litellm.types.utils import ChatCompletionMessageToolCall, Function, ModelResponse
from pydantic import Field, create_model
from sqlalchemy.exc import IntegrityError

from clients.llm.llm_client import LLMClient
from db_models.agentic_prompt_models import DatabaseAgenticPrompt
from repositories.agentic_prompts_repository import AgenticPromptRepository
from schemas.agentic_prompt_schemas import AgenticPrompt
from schemas.common_schemas import JsonSchema
from schemas.enums import MessageRole, ModelProvider
from schemas.llm_schemas import (
    LLMConfigSettings,
    LLMResponseFormat,
    LLMResponseSchema,
    OpenAIMessage,
    ToolChoice,
    ToolChoiceFunction,
)
from schemas.request_schemas import (
    CompletionRequest,
    LLMGetAllFilterRequest,
    LLMGetVersionsFilterRequest,
    PromptCompletionRequest,
    VariableTemplateValue,
)
from schemas.response_schemas import (
    AgenticPromptRunResponse,
    AgenticPromptVersionListResponse,
    LLMGetAllMetadataListResponse,
    LLMGetAllMetadataResponse,
)
from services.prompt.chat_completion_service import ChatCompletionService
from tests.clients.base_test_client import override_get_db_session


def to_openai_messages(
    messages: List[Dict[str, Any]],
) -> List[OpenAIMessage]:
    return [OpenAIMessage(**message) for message in messages]


@pytest.fixture
def mock_db_session():
    """Mock database session for testing"""
    return MagicMock()


@pytest.fixture
def mock_llm_client():
    """Mock LiteLLM client for testing"""
    return LLMClient(
        provider=ModelProvider.OPENAI,
        api_key="api_key",
    )


@pytest.fixture
def agentic_prompt_repo(mock_db_session):
    """Create AgenticPromptRepository instance with mocked db session"""
    return AgenticPromptRepository(mock_db_session)


@pytest.fixture
def sample_prompt_data():
    """Sample prompt data for testing"""
    return {
        "messages": [{"role": "user", "content": "Hello, world!"}],
        "model_name": "gpt-4",
        "model_provider": "openai",
        "tools": [{"type": "function", "function": {"name": "test_tool"}}],
        "version": 1,
        "config": {
            "temperature": 0.7,
            "max_tokens": 100,
            "tool_choice": "auto",
        },
    }


@pytest.fixture
def sample_agentic_prompt(sample_prompt_data):
    """Create sample AgenticPrompt instance"""
    return AgenticPrompt(name="test_prompt", **sample_prompt_data)


@pytest.fixture
def sample_deleted_prompt(sample_db_prompt):
    """Create sample deleted AgenticPrompt instance"""
    return AgenticPrompt(
        name="deleted_prompt",
        messages=[],
        model_name="",
        model_provider="openai",
        version=1,
        deleted_at=datetime.now(),
    )


@pytest.fixture
def sample_unsaved_run_config(sample_prompt_data):
    """Create sample AgenticPrompt instance"""
    unsaved_run_data = {k: v for k, v in sample_prompt_data.items() if k != "version"}
    return CompletionRequest(**unsaved_run_data)


@pytest.fixture
def sample_db_prompt(sample_prompt_data):
    """Create sample DatabaseAgenticPrompt instance"""
    task_id = str(uuid4())
    return AgenticPrompt(name="test_prompt", **sample_prompt_data).to_db_model(task_id)


@pytest.fixture
def expected_db_prompt_messages(sample_db_prompt):
    """Create expected DatabaseAgenticPrompt messages"""
    return to_openai_messages(sample_db_prompt.messages)


def mock_completion(*args, **kwargs):
    response_format = kwargs.get("response_format")
    json_schema = response_format.get("json_schema")
    schema = json_schema.get("schema")

    if json_schema.get("strict") and "additionalProperties" not in schema:
        raise ValueError(
            "Invalid schema for response_format 'joke_struct': "
            "In context=(), 'additionalProperties' is required to be supplied and to be false.",
        )

    mock_response = MagicMock(spec=ModelResponse)
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message = {"content": "ok", "tool_calls": None}
    return mock_response


@pytest.mark.unit_tests
@pytest.mark.asyncio
@patch("clients.llm.llm_client.completion_cost")
@patch("clients.llm.llm_client.litellm.completion")
async def test_run_prompt(
    mock_completion,
    mock_completion_cost,
    mock_llm_client,
    agentic_prompt_repo,
    sample_unsaved_run_config,
):
    """Test running a prompt and getting response"""
    # Mock completion response
    mock_response = MagicMock(spec=ModelResponse)
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message = {
        "content": "Test response",
        "tool_calls": [{"id": "call_123", "function": {"name": "test_tool"}}],
    }
    mock_completion.return_value = mock_response
    mock_completion_cost.return_value = 0.001234

    result = await agentic_prompt_repo.run_unsaved_prompt(sample_unsaved_run_config)

    assert isinstance(result, AgenticPromptRunResponse)
    assert result.content == "Test response"
    assert result.tool_calls == [
        ChatCompletionMessageToolCall(
            function=Function(arguments="", name="test_tool"),
            id="call_123",
            type="function",
        ),
    ]
    assert result.cost == "0.001234"

    # Verify completion was called with correct parameters
    mock_completion.assert_called_once()
    call_args = mock_completion.call_args[1]
    assert call_args["model"] == "openai/gpt-4"
    assert (
        to_openai_messages(call_args["messages"]) == sample_unsaved_run_config.messages
    )
    assert call_args["temperature"] == sample_unsaved_run_config.config.temperature


@pytest.mark.unit_tests
def test_get_prompt_success(
    agentic_prompt_repo,
    mock_db_session,
    sample_db_prompt,
    expected_db_prompt_messages,
):
    """Test successfully getting a prompt from database"""
    task_id = "test_task_id"
    prompt_name = "test_prompt"

    # Mock database query
    mock_query = MagicMock()
    mock_filter = MagicMock()
    mock_db_session.query.return_value = mock_query
    mock_query.filter.return_value = mock_filter
    mock_filter.filter.return_value = mock_filter
    mock_filter.order_by.return_value = mock_filter
    mock_filter.first.return_value = sample_db_prompt

    result = agentic_prompt_repo.get_llm_item(task_id, prompt_name)

    assert isinstance(result, AgenticPrompt)
    assert result.name == sample_db_prompt.name
    assert result.messages == expected_db_prompt_messages

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
    mock_filter.filter.return_value = mock_filter
    mock_filter.order_by.return_value = mock_filter
    mock_filter.first.return_value = None

    with pytest.raises(ValueError) as exc_info:
        agentic_prompt_repo.get_llm_item(task_id, prompt_name)

    assert (
        str(exc_info.value)
        == "'nonexistent_prompt' (version 'latest') not found for task 'nonexistent_task'"
    )


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
        version=1,
        deleted_at=None,
    )

    # Mock database query
    mock_query = MagicMock()
    mock_filter = MagicMock()
    mock_db_session.query.return_value = mock_query
    mock_query.filter.return_value = mock_filter
    mock_filter.group_by.return_value = mock_filter
    mock_filter.order_by.return_value = mock_filter
    mock_filter.all.return_value = [
        SimpleNamespace(
            name=sample_db_prompt.name,
            versions=1,
            created_at=sample_db_prompt.created_at or datetime.now(),
            latest_version_created_at=sample_db_prompt.created_at or datetime.now(),
        ),
        SimpleNamespace(
            name=prompt2.name,
            versions=1,
            created_at=prompt2.created_at or datetime.now(),
            latest_version_created_at=prompt2.created_at or datetime.now(),
        ),
    ]

    # Mock deleted_versions query
    mock_deleted = MagicMock()
    mock_deleted.filter.return_value = mock_deleted
    mock_deleted.order_by.return_value = mock_deleted
    mock_deleted.all.return_value = []
    mock_db_session.query.side_effect = [mock_query, mock_deleted, mock_deleted]

    # Mock count query
    mock_filter.count.return_value = 2
    mock_filter.offset.return_value = mock_filter
    mock_filter.limit.return_value = mock_filter

    # Use default pagination parameters
    pagination_parameters = PaginationParameters(
        page=0,
        page_size=10,
        sort=PaginationSortMethod.DESCENDING,
    )
    result = agentic_prompt_repo.get_all_llm_item_metadata(
        task_id,
        pagination_parameters,
    )

    assert isinstance(result, LLMGetAllMetadataListResponse)
    assert len(result.llm_metadata) == 2
    assert all(
        isinstance(prompt, LLMGetAllMetadataResponse) for prompt in result.llm_metadata
    )
    assert result.llm_metadata[0].name == sample_db_prompt.name
    assert result.llm_metadata[1].name == prompt2.name


@pytest.mark.unit_tests
def test_get_all_prompts_empty(agentic_prompt_repo, mock_db_session):
    """Test getting all prompts when none exist"""
    task_id = "empty_task"

    # Mock database query returning empty list
    mock_query = MagicMock()
    mock_filter = MagicMock()
    mock_db_session.query.return_value = mock_query
    mock_query.filter.return_value = mock_filter
    mock_filter.group_by.return_value = mock_filter
    mock_filter.order_by.return_value = mock_filter
    mock_filter.count.return_value = 0
    mock_filter.offset.return_value = mock_filter
    mock_filter.limit.return_value = mock_filter
    mock_filter.all.return_value = []

    # Use default pagination parameters
    pagination_parameters = PaginationParameters(
        page=0,
        page_size=10,
        sort=PaginationSortMethod.DESCENDING,
    )
    result = agentic_prompt_repo.get_all_llm_item_metadata(
        task_id,
        pagination_parameters,
    )

    assert isinstance(result, LLMGetAllMetadataListResponse)
    assert len(result.llm_metadata) == 0


@pytest.mark.unit_tests
def test_save_prompt_with_agentic_prompt_object(
    agentic_prompt_repo,
    mock_db_session,
    sample_agentic_prompt,
):
    """Test saving an AgenticPrompt object to database"""
    task_id = "test_task_id"

    mock_db_session.query.return_value.filter.return_value.scalar.return_value = 0

    agentic_prompt_repo.save_llm_item(task_id, sample_agentic_prompt)

    # Verify database operations
    mock_db_session.add.assert_called_once()
    mock_db_session.commit.assert_called_once()

    # Check the DatabaseAgenticPrompt object that was added
    added_prompt = mock_db_session.add.call_args[0][0]
    messages = to_openai_messages(added_prompt.messages)

    assert isinstance(added_prompt, DatabaseAgenticPrompt)
    assert added_prompt.task_id == task_id
    assert added_prompt.name == sample_agentic_prompt.name
    assert messages == sample_agentic_prompt.messages


@pytest.mark.unit_tests
def test_save_prompt_integrity_error(
    agentic_prompt_repo,
    mock_db_session,
    sample_agentic_prompt,
):
    """Test saving a prompt when it already exists (IntegrityError)"""
    task_id = "test_task_id"

    # Mock IntegrityError on commit
    mock_db_session.commit.side_effect = IntegrityError("", "", Exception(""))

    with pytest.raises(ValueError) as exc_info:
        agentic_prompt_repo.save_llm_item(task_id, sample_agentic_prompt)

    assert (
        str(exc_info.value)
        == "Failed to save 'test_prompt' for task 'test_task_id' — possible duplicate constraint."
    )

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
    mock_filter.all.return_value = [sample_db_prompt]

    agentic_prompt_repo.delete_llm_item(task_id, prompt_name)

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
    mock_filter.all.return_value = None

    with pytest.raises(
        ValueError,
        match="'nonexistent_prompt' not found for task 'nonexistent_task'",
    ):
        agentic_prompt_repo.delete_llm_item(task_id, prompt_name)


@pytest.mark.unit_tests
@pytest.mark.asyncio
@patch("clients.llm.llm_client.completion_cost")
@patch("clients.llm.llm_client.litellm.completion")
async def test_run_saved_prompt(
    mock_completion,
    mock_completion_cost,
    mock_llm_client,
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
    mock_filter.filter.return_value = mock_filter
    mock_filter.order_by.return_value = mock_filter
    mock_filter.first.return_value = sample_db_prompt

    # Mock completion response
    mock_response = MagicMock(spec=ModelResponse)
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message = {
        "content": "Saved prompt response",
        "tool_calls": None,
    }
    mock_completion.return_value = mock_response
    mock_completion_cost.return_value = 0.002345

    result = await agentic_prompt_repo.run_saved_prompt(
        task_id,
        prompt_name,
        "1",
        PromptCompletionRequest(variables=[]),
    )

    assert isinstance(result, AgenticPromptRunResponse)
    assert result.content == "Saved prompt response"
    assert result.cost == "0.002345"


@pytest.mark.unit_tests
def test_agentic_prompt_from_db_model(sample_db_prompt, expected_db_prompt_messages):
    """Test creating AgenticPrompt from DatabaseAgenticPrompt"""
    prompt = AgenticPrompt.from_db_model(sample_db_prompt)

    assert isinstance(prompt, AgenticPrompt)
    assert prompt.name == sample_db_prompt.name
    assert prompt.messages == expected_db_prompt_messages
    assert prompt.model_name == sample_db_prompt.model_name
    assert prompt.model_provider == sample_db_prompt.model_provider


@pytest.mark.unit_tests
def test_agentic_prompt_model_dump(sample_agentic_prompt):
    """Test converting AgenticPrompt to dictionary"""
    prompt_dict = sample_agentic_prompt.model_dump(exclude_none=True)

    expected_messages = [
        message.model_dump(exclude_none=True)
        for message in sample_agentic_prompt.messages
    ]

    assert isinstance(prompt_dict, dict)
    assert prompt_dict["name"] == sample_agentic_prompt.name
    assert prompt_dict["messages"] == expected_messages
    assert prompt_dict["model_name"] == sample_agentic_prompt.model_name
    assert prompt_dict["model_provider"] == sample_agentic_prompt.model_provider


@pytest.mark.unit_tests
@patch("clients.llm.llm_client.completion_cost")
@patch("clients.llm.llm_client.litellm.completion")
def test_chat_completion_service_run_chat_completion(
    mock_completion,
    mock_completion_cost,
    mock_llm_client,
    sample_agentic_prompt,
):
    """Test running chat completion directly on AgenticPrompt"""
    # Mock completion response
    mock_response = MagicMock(spec=ModelResponse)
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message = {
        "content": "Direct completion response",
        "tool_calls": [{"id": "call_456", "function": {"name": "test_tool"}}],
    }
    mock_completion.return_value = mock_response
    mock_completion_cost.return_value = 0.003456

    chat_completion_service = ChatCompletionService()
    result = chat_completion_service.run_chat_completion(
        sample_agentic_prompt,
        mock_llm_client,
        PromptCompletionRequest(variables=[]),
    )

    assert result.content == "Direct completion response"
    assert result.tool_calls == [
        ChatCompletionMessageToolCall(
            function=Function(arguments="", name="test_tool"),
            id="call_456",
            type="function",
        ),
    ]
    assert result.cost == "0.003456"

    # Verify completion was called with correct model format
    mock_completion.assert_called_once()
    call_args = mock_completion.call_args[1]
    assert call_args["model"] == "openai/gpt-4"


@pytest.mark.unit_tests
@pytest.mark.parametrize(
    "message,variables,expected_message",
    [
        (
            "What is the capital of {{country}}?",
            {"country": "France"},
            "What is the capital of France?",
        ),
        (
            "What is the capital of {{country}}?",
            {"city": "Paris"},
            "What is the capital of ?",
        ),
        (
            "What is the capital of {country}?",
            {"country": "France"},
            "What is the capital of {country}?",
        ),
        (
            "What is the capital of country?",
            {"country": "France"},
            "What is the capital of country?",
        ),
        (
            "User {{user_id}} has {{item_count}} items",
            {"user_id": "123", "item_count": "5"},
            "User 123 has 5 items",
        ),
        ("{{first}}{{second}}", {"first": "Hello", "second": "World"}, "HelloWorld"),
        ("{{first}} {{first}}", {"first": "Hello", "second": "World"}, "Hello Hello"),
        ("{{ name }}", {"name": "Alice"}, "Alice"),
        ("{{     name     }}", {"name": "Alice"}, "Alice"),
        ("   {{     name     }}   ", {"name": "Alice"}, "   Alice   "),
        (
            "This is a message without variables",
            {},
            "This is a message without variables",
        ),
        (
            "This is a message without variables",
            None,
            "This is a message without variables",
        ),
        ("{{ name_variable_1 }}", {"name_variable_1": "Alice"}, "Alice"),
        (
            [{"type": "text", "text": "{{ name_variable_1 }}"}],
            {"name_variable_1": "Alice"},
            [{"type": "text", "text": "Alice"}],
        ),
        (
            [{"type": "text", "text": "name_variable_1"}],
            {"name_variable_1": "Alice"},
            [{"type": "text", "text": "name_variable_1"}],
        ),
        (
            [
                {"type": "text", "text": "{{ name_variable_1 }}"},
                {"type": "text", "text": "{{ name_variable_2 }}"},
            ],
            {"name_variable_1": "Alice", "name_variable_2": "Bob"},
            [{"type": "text", "text": "Alice"}, {"type": "text", "text": "Bob"}],
        ),
        (
            [
                {"type": "text", "text": "{{ name_variable_1 }}"},
                {"type": "image_url", "image_url": {"url": "{{ name_variable_2 }}"}},
            ],
            {"name_variable_1": "Alice", "name_variable_2": "Bob"},
            [
                {"type": "text", "text": "Alice"},
                {"type": "image_url", "image_url": {"url": "{{ name_variable_2 }}"}},
            ],
        ),
        (
            [
                {"type": "text", "text": "{{ name_variable_1 }}"},
                {
                    "type": "input_audio",
                    "input_audio": {"data": "test", "format": "wav"},
                },
            ],
            {"name_variable_1": "Alice", "name_variable_2": "Bob"},
            [
                {"type": "text", "text": "Alice"},
                {
                    "type": "input_audio",
                    "input_audio": {"data": "test", "format": "wav"},
                },
            ],
        ),
        (
            [
                {"type": "text", "text": "{{ name_variable_1 }}"},
                {"type": "image_url", "image_url": {"url": "test"}},
            ],
            {"name_variable_1": "Alice", "name_variable_2": "Bob"},
            [
                {"type": "text", "text": "Alice"},
                {"type": "image_url", "image_url": {"url": "test"}},
            ],
        ),
        (
            [
                {"type": "text", "text": "{{ name_variable_1 }}"},
                {
                    "type": "input_audio",
                    "input_audio": {"data": "{{ name_variable_2 }}", "format": "wav"},
                },
            ],
            {"name_variable_1": "Alice", "name_variable_2": "Bob"},
            [
                {"type": "text", "text": "Alice"},
                {
                    "type": "input_audio",
                    "input_audio": {"data": "{{ name_variable_2 }}", "format": "wav"},
                },
            ],
        ),
    ],
)
def test_agentic_prompt_variable_replacement(message, variables, expected_message):
    """Test running unsaved prompt with variables"""
    if variables is not None:
        variables = [
            VariableTemplateValue(name=name, value=value)
            for name, value in variables.items()
        ]
    else:
        variables = []

    completion_request = PromptCompletionRequest(variables=variables)
    messages = [OpenAIMessage(role=MessageRole.USER, content=message)]

    chat_completion_service = ChatCompletionService()
    result = chat_completion_service.replace_variables(
        completion_request._variable_map,
        messages,
    )
    expected_result = [
        OpenAIMessage(role=MessageRole.USER, content=expected_message),
    ]
    assert result == expected_result

    prompt = AgenticPrompt(
        name="test_prompt",
        messages=messages,
        model_name="gpt-4o",
        model_provider="openai",
    )
    _, completion_params = chat_completion_service._get_completion_params(
        prompt,
        completion_request,
    )

    assert completion_params["messages"][0]["content"] == expected_message


@pytest.mark.unit_tests
@pytest.mark.parametrize(
    "message,variables,missing_variables",
    [
        (
            "What is the capital of {{country}}?",
            {"country": "France"},
            set(),
        ),
        (
            "What is the capital of {{country}}?",
            {"city": "Paris"},
            {"country"},
        ),
        (
            "What is the capital of {country}?",
            {"country": "France"},
            set(),
        ),
        (
            "What is the capital of country?",
            {"country": "France"},
            set(),
        ),
        (
            "User {{user_id}} has {{item_counts}} items",
            {"user_id": "123", "item_count": "5"},
            {"item_counts"},
        ),
        (
            "User {{user_ids}} has {{item_counts}} items",
            {"user_id": "123", "item_count": "5"},
            {"user_ids", "item_counts"},
        ),
        (
            [{"type": "text", "text": "{{ name_variable_1 }}"}],
            {"name_variable_1": "Alice"},
            set(),
        ),
        (
            [{"type": "text", "text": "{{ name_variable_1 }}"}],
            {"name_variable_2": "Alice"},
            {"name_variable_1"},
        ),
        (
            [{"type": "text", "text": "name_variable_1"}],
            {"name_variable_1": "Alice"},
            set(),
        ),
        (
            [
                {"type": "text", "text": "{{ name_variable_1 }}"},
                {"type": "text", "text": "{{ name_variable_2 }}"},
            ],
            {"name_variable_3": "Alice", "name_variable_2": "Bob"},
            {"name_variable_1"},
        ),
        (
            [
                {"type": "text", "text": "{{ name_variable_1 }}"},
                {"type": "image_url", "image_url": {"url": "{{ name_variable_2 }}"}},
            ],
            {"name_variable_1": "Alice"},
            set(),
        ),
        (
            [
                {"type": "text", "text": "{{ name_variable_1 }}"},
                {
                    "type": "input_audio",
                    "input_audio": {"data": "{{ name_variable_2 }}", "format": "wav"},
                },
            ],
            {"name_variable_1": "Alice"},
            set(),
        ),
    ],
)
def test_agentic_prompt_find_missing_variables(message, variables, missing_variables):
    """Test running unsaved prompt with variables"""
    if variables is not None:
        variables = [
            VariableTemplateValue(name=name, value=value)
            for name, value in variables.items()
        ]
    else:
        variables = []

    messages = [OpenAIMessage(role=MessageRole.USER, content=message)]
    completion_request = PromptCompletionRequest(variables=variables)
    chat_completion_service = ChatCompletionService()
    results = chat_completion_service.find_missing_variables_in_messages(
        completion_request._variable_map,
        messages,
    )
    assert results == missing_variables


@pytest.mark.unit_tests
def test_agentic_prompt_tools_serialization():
    """Test that tools serialize and deserialize correctly"""
    prompt_data = {
        "name": "test_tools",
        "messages": [{"role": "user", "content": "Test"}],
        "model_name": "gpt-4",
        "model_provider": "openai",
        "tools": [
            {
                "type": "function",
                "function": {
                    "name": "get_weather",
                    "description": "Get weather info",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "location": {"type": "string", "description": "City name"},
                        },
                        "required": ["location"],
                    },
                },
                "strict": True,
            },
        ],
        "config": {
            "tool_choice": {
                "type": "function",
                "function": {"name": "get_weather"},
            },
        },
    }

    # Create prompt
    prompt = AgenticPrompt(**prompt_data)

    # Convert to DB model
    task_id = str(uuid4())
    db_model = prompt.to_db_model(task_id)

    # Verify tools are serialized correctly
    assert len(db_model.tools) == 1
    assert db_model.tools[0]["type"] == "function"
    assert db_model.tools[0]["function"]["name"] == "get_weather"
    assert db_model.tools[0]["function"]["description"] == "Get weather info"
    assert (
        db_model.tools[0]["function"]["parameters"]["properties"]["location"]["type"]
        == "string"
    )
    assert db_model.tools[0]["function"]["parameters"]["required"] == ["location"]
    assert db_model.tools[0]["strict"] == True

    # Verify tool_choice is serialized correctly
    assert db_model.config["tool_choice"]["type"] == "function"
    assert db_model.config["tool_choice"]["function"]["name"] == "get_weather"

    # Convert back from DB model
    reconstructed_prompt = AgenticPrompt.from_db_model(db_model)

    # Verify tools are deserialized correctly
    assert len(reconstructed_prompt.tools) == 1
    assert reconstructed_prompt.tools[0].function.name == "get_weather"
    assert reconstructed_prompt.tools[0].function.description == "Get weather info"
    assert reconstructed_prompt.tools[0].strict == True
    assert len(reconstructed_prompt.tools[0].function.parameters.properties) == 1
    assert reconstructed_prompt.tools[0].function.parameters.required == ["location"]

    # Verify tool_choice is deserialized correctly (should be function name string)
    assert reconstructed_prompt.config.tool_choice == ToolChoice(
        type="function",
        function=ToolChoiceFunction(name="get_weather"),
    )


@pytest.mark.unit_tests
def test_agentic_prompt_response_format_serialization():
    """Test that response_format serializes and deserializes correctly"""
    prompt_data = {
        "name": "test_response_format",
        "messages": [{"role": "user", "content": "Test"}],
        "model_name": "gpt-4",
        "model_provider": "openai",
        "config": {
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": "user_schema",
                    "description": "User information",
                    "schema": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string", "description": "User's name"},
                        },
                        "required": ["name"],
                    },
                },
            },
        },
    }

    # Create prompt
    prompt = AgenticPrompt(**prompt_data)

    # Convert to DB model
    task_id = str(uuid4())
    db_model = prompt.to_db_model(task_id)

    # Verify response_format is serialized correctly
    assert db_model.config["response_format"]["type"] == "json_schema"
    assert db_model.config["response_format"]["json_schema"]["name"] == "user_schema"
    assert (
        db_model.config["response_format"]["json_schema"]["description"]
        == "User information"
    )
    assert (
        db_model.config["response_format"]["json_schema"]["schema"]["properties"][
            "name"
        ]["type"]
        == "string"
    )
    assert db_model.config["response_format"]["json_schema"]["schema"]["required"] == [
        "name",
    ]
    assert db_model.config["response_format"]["json_schema"].get("strict") == None

    # Convert back from DB model
    reconstructed_prompt = AgenticPrompt.from_db_model(db_model)

    # Verify response_format is deserialized correctly
    assert reconstructed_prompt.config.response_format.type == "json_schema"
    assert reconstructed_prompt.config.response_format.json_schema.name == "user_schema"
    assert (
        reconstructed_prompt.config.response_format.json_schema.description
        == "User information"
    )
    assert reconstructed_prompt.config.response_format.json_schema.strict == None
    assert (
        len(reconstructed_prompt.config.response_format.json_schema.schema.properties)
        == 1
    )
    assert reconstructed_prompt.config.response_format.json_schema.schema.required == [
        "name",
    ]


@pytest.mark.unit_tests
@patch("clients.llm.llm_client.completion_cost")
@patch("clients.llm.llm_client.litellm.completion")
def test_agentic_prompt_tool_call_message_serialization(
    mock_completion,
    mock_completion_cost,
    mock_llm_client,
):
    """Test that assistant tool_call messages are still serialized correctly when set with an invalid type"""
    # Construct an unsaved prompt that includes a tool_call assistant message
    messages = [
        {"role": "user", "content": "What’s the weather?"},
        {
            "role": "assistant",
            "tool_calls": [
                {
                    "id": "call_999",
                    "type": "not_function",  # tests an invalid type is set for a tool call message
                    "function": {
                        "name": "get_weather",
                        "arguments": '{"location": "Paris"}',
                    },
                },
            ],
            "content": None,
        },
        {
            "role": "tool",
            "tool_call_id": "call_999",
            "content": '{"temperature": "20C"}',
        },
    ]

    completion_request = CompletionRequest(
        messages=messages,
        model_name="gpt-4o",
        model_provider=ModelProvider.OPENAI,
    )

    # Mock LiteLLM completion response
    mock_response = MagicMock(spec=ModelResponse)
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message = {
        "content": "Got it!",
        "tool_calls": None,
    }
    mock_completion.return_value = mock_response
    mock_completion_cost.return_value = 0.000123

    # Run the unsaved prompt
    chat_completion_service = ChatCompletionService()
    prompt, request = ChatCompletionService.to_prompt_and_request(completion_request)
    result = chat_completion_service.run_chat_completion(
        prompt,
        mock_llm_client,
        request,
    )
    call_args = mock_completion.call_args[1]

    # Extract messages sent to LiteLLM
    sent_messages = call_args["messages"]

    # Validate proper assistant tool_call serialization
    assert any(
        msg.get("role") == "assistant" and "tool_calls" in msg for msg in sent_messages
    ), "Assistant tool_call message missing from LiteLLM payload"

    assistant_msg = next(msg for msg in sent_messages if msg["role"] == "assistant")
    tool_call = assistant_msg["tool_calls"][0]

    assert tool_call["id"] == "call_999"
    assert (
        tool_call["type"] == "function"
    )  # verifies the type is changed to function on the return
    assert tool_call["function"]["name"] == "get_weather"
    assert tool_call["function"]["arguments"] == '{"location": "Paris"}'

    # Ensure the response object is still parsed properly
    assert isinstance(result.content, str)
    assert result.cost == "0.000123"


@patch("clients.llm.llm_client.completion_cost", return_value=0.0)
@patch("clients.llm.llm_client.litellm.completion", side_effect=mock_completion)
@pytest.mark.parametrize("has_additional_props", [True, False])
def test_chat_completion_service_run_chat_completion_strict_additional_properties_validation(
    mock_completion,
    mock_cost,
    mock_llm_client,
    has_additional_props,
):
    schema_body = JsonSchema(
        type="object",
        properties={
            "question": {"type": "string"},
            "punchline": {"type": "string"},
        },
        required=["question", "punchline"],
        additionalProperties=False if has_additional_props else None,
    )

    response_format = LLMResponseFormat(
        type="json_schema",
        json_schema=LLMResponseSchema(
            name="joke_struct",
            description="Schema to validate strict additionalProperties behavior",
            schema=schema_body,
            strict=True,
        ),
    )

    prompt = AgenticPrompt(
        name="strict_schema_test",
        messages=[{"role": "user", "content": "tell me a joke"}],
        model_name="gpt-4o",
        model_provider="openai",
        config=LLMConfigSettings(
            response_format=response_format,
        ),
    )

    completion_request = PromptCompletionRequest()
    chat_completion_service = ChatCompletionService()

    if has_additional_props:
        result = chat_completion_service.run_chat_completion(
            prompt,
            mock_llm_client,
            completion_request,
        )
        assert result.content == "ok"
    else:
        with pytest.raises(ValueError, match="additionalProperties"):
            chat_completion_service.run_chat_completion(
                prompt,
                mock_llm_client,
                completion_request,
            )


@pytest.mark.unit_tests
def test_run_deleted_prompt_spawns_error(sample_deleted_prompt, mock_llm_client):
    """Test run chat completion raises an error if the prompt has been deleted"""
    with pytest.raises(
        ValueError,
        match="Cannot run chat completion for this prompt because it was deleted on",
    ):
        chat_completion_service = ChatCompletionService()
        chat_completion_service.run_chat_completion(
            sample_deleted_prompt,
            mock_llm_client,
            PromptCompletionRequest(),
        )


@pytest.mark.unit_tests
@pytest.mark.asyncio
async def test_stream_deleted_prompt_spawns_error(
    sample_deleted_prompt,
    mock_llm_client,
):
    """Test stream chat completion raises an error if the prompt has been deleted"""
    chat_completion_service = ChatCompletionService()
    stream = chat_completion_service.stream_chat_completion(
        sample_deleted_prompt,
        mock_llm_client,
        PromptCompletionRequest(),
    )
    events = [event async for event in stream]
    assert len(events) == 1
    assert (
        "event: error\ndata: Cannot stream chat completion for this prompt because it was deleted on"
        in events[0]
    )


@pytest.mark.unit_tests
@pytest.mark.parametrize("prompt_version", ["latest", "1", "2025-01-01T00:00:00"])
def test_get_prompt_by_version_success(prompt_version):
    """Test getting a prompt with different version formats"""
    db_session = override_get_db_session()
    repo = AgenticPromptRepository(db_session)

    task_id = str(uuid4())
    prompt_name = "test_prompt"

    # Create a database prompt with the sample data
    prompt_data = {
        "messages": [{"role": "user", "content": "Hello, world!"}],
        "model_name": "gpt-4",
        "model_provider": "openai",
        "temperature": 0.7,
        "max_tokens": 100,
        "version": 1,
    }
    db_prompt = AgenticPrompt(name="test_prompt", **prompt_data).to_db_model(task_id)
    db_prompt.created_at = datetime.fromisoformat("2025-01-01T00:00:00")

    # Save to database
    db_session.add(db_prompt)
    db_session.commit()

    try:
        result = repo.get_llm_item(task_id, prompt_name, prompt_version)

        assert isinstance(result, AgenticPrompt)
        assert result.name == prompt_name
        assert len(result.messages) == 1
        assert result.messages[0].role == "user"
        assert result.messages[0].content == "Hello, world!"
        assert result.version == 1
    finally:
        # Cleanup
        db_session.delete(db_prompt)
        db_session.commit()
        db_session.close()


@pytest.mark.unit_tests
@pytest.mark.parametrize(
    "filter_param,filter_value,expected_count,expected_name",
    [
        ("model_provider", ModelProvider.OPENAI, 1, "prompt_openai"),
        ("model_name", "gpt-4", 1, "prompt_openai"),
        ("llm_asset_names", ["prompt_openai"], 1, "prompt_openai"),
        ("created_after", datetime(2025, 1, 1), 2, None),
        ("created_before", datetime(2025, 1, 2), 1, "prompt_openai"),
    ],
)
def test_get_all_prompt_metadata_with_filters(
    filter_param,
    filter_value,
    expected_count,
    expected_name,
):
    """Test getting all prompt metadata with filter_request parameters"""
    db_session = override_get_db_session()
    repo = AgenticPromptRepository(db_session)

    task_id = str(uuid4())

    # Create multiple prompts with different providers and models
    prompts_data = [
        {
            "name": "prompt_openai",
            "messages": [{"role": "user", "content": "OpenAI prompt"}],
            "model_name": "gpt-4",
            "model_provider": "openai",
            "created_at": datetime(2025, 1, 1, 12, 0, 0),
        },
        {
            "name": "prompt_anthropic",
            "messages": [{"role": "user", "content": "Anthropic prompt"}],
            "model_name": "claude-3-5-sonnet",
            "model_provider": "anthropic",
            "created_at": datetime(2025, 1, 2, 12, 0, 0),
        },
    ]

    created_prompts = []
    for prompt_data in prompts_data:
        created_at = prompt_data.pop("created_at")
        db_prompt = AgenticPrompt(**prompt_data).to_db_model(task_id)
        db_prompt.created_at = created_at
        db_session.add(db_prompt)
        created_prompts.append(db_prompt)

    db_session.commit()

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
        result = repo.get_all_llm_item_metadata(
            task_id=task_id,
            pagination_parameters=pagination_params,
            filter_request=filter_request,
        )

        # Verify filtering worked
        assert isinstance(result, LLMGetAllMetadataListResponse)
        assert result.count == expected_count
        assert len(result.llm_metadata) == expected_count

        # Verify the correct prompt was returned based on the filter
        if expected_name:
            assert result.llm_metadata[0].name == expected_name

    finally:
        # Cleanup
        for db_prompt in created_prompts:
            db_session.delete(db_prompt)
        db_session.commit()
        db_session.close()


@pytest.mark.unit_tests
@pytest.mark.parametrize(
    "filter_param,filter_value,expected_count",
    [
        ("model_provider", ModelProvider.OPENAI, 2),
        ("model_name", "gpt-4", 2),
        ("created_after", datetime(2025, 1, 1), 3),
        ("created_before", datetime(2025, 1, 2), 2),
        ("exclude_deleted", True, 2),
        ("min_version", 2, 2),
        ("max_version", 2, 2),
        ("min_version", 10, 0),  # verify no returned versions doesn't spawn an error
    ],
)
def test_get_prompt_versions_with_filters(filter_param, filter_value, expected_count):
    """Test getting prompt versions with filter_request parameters"""
    db_session = override_get_db_session()
    repo = AgenticPromptRepository(db_session)

    task_id = str(uuid4())
    prompt_name = "test_prompt"

    # Create multiple versions with different properties
    versions_data = [
        {
            "messages": [{"role": "user", "content": "Version 1"}],
            "model_name": "gpt-4",
            "model_provider": "openai",
            "version": 1,
            "created_at": datetime(2025, 1, 1, 12, 0, 0),
            "deleted_at": None,
        },
        {
            "messages": [{"role": "user", "content": "Version 2"}],
            "model_name": "gpt-4",
            "model_provider": "openai",
            "version": 2,
            "created_at": datetime(2025, 1, 1, 13, 0, 0),
            "deleted_at": None,
        },
        {
            "messages": [{"role": "user", "content": "Version 3"}],
            "model_name": "claude-3-5-sonnet",
            "model_provider": "anthropic",
            "version": 3,
            "created_at": datetime(2025, 1, 2, 12, 0, 0),
            "deleted_at": datetime(2025, 1, 3, 12, 0, 0),  # deleted version
        },
    ]

    created_prompts = []
    for version_data in versions_data:
        created_at = version_data.pop("created_at")
        deleted_at = version_data.pop("deleted_at")
        db_prompt = AgenticPrompt(name=prompt_name, **version_data).to_db_model(task_id)
        db_prompt.created_at = created_at
        db_prompt.deleted_at = deleted_at
        db_session.add(db_prompt)
        created_prompts.append(db_prompt)

    db_session.commit()

    try:
        # Create filter request
        filter_request = LLMGetVersionsFilterRequest(**{filter_param: filter_value})

        # Create pagination parameters
        pagination_params = PaginationParameters(
            page=0,
            page_size=10,
            sort=PaginationSortMethod.ASCENDING,
        )

        # Get filtered results
        result = repo.get_llm_item_versions(
            task_id=task_id,
            item_name=prompt_name,
            pagination_parameters=pagination_params,
            filter_request=filter_request,
        )

        # Verify filtering worked
        assert isinstance(result, AgenticPromptVersionListResponse)
        assert result.count == expected_count
        assert len(result.versions) == expected_count

    finally:
        # Cleanup
        for db_prompt in created_prompts:
            db_session.delete(db_prompt)
        db_session.commit()
        db_session.close()


@pytest.mark.unit_tests
@pytest.mark.parametrize(
    "page,page_size,sort,expected_names",
    [
        (0, 2, PaginationSortMethod.ASCENDING, ["prompt_0", "prompt_1"]),
        (1, 2, PaginationSortMethod.ASCENDING, ["prompt_2"]),
        (0, 3, PaginationSortMethod.DESCENDING, ["prompt_2", "prompt_1", "prompt_0"]),
        (0, 10, PaginationSortMethod.ASCENDING, ["prompt_0", "prompt_1", "prompt_2"]),
        (2, 1, PaginationSortMethod.ASCENDING, ["prompt_2"]),
    ],
)
def test_get_all_prompt_metadata_with_pagination(page, page_size, sort, expected_names):
    """Test getting all prompt metadata with all pagination parameters (page, page_size, sort)"""
    db_session = override_get_db_session()
    repo = AgenticPromptRepository(db_session)

    task_id = str(uuid4())

    # Create multiple prompts
    prompt_data = {
        "messages": [{"role": "user", "content": "Test prompt"}],
        "model_name": "gpt-4",
        "model_provider": "openai",
    }

    created_prompts = []
    for i in range(3):
        db_prompt = AgenticPrompt(name=f"prompt_{i}", **prompt_data).to_db_model(
            task_id,
        )
        db_session.add(db_prompt)
        created_prompts.append(db_prompt)

    db_session.commit()

    try:
        # Create pagination parameters
        pagination_params = PaginationParameters(
            page=page,
            page_size=page_size,
            sort=sort,
        )

        # Get paginated results
        result = repo.get_all_llm_item_metadata(
            task_id=task_id,
            pagination_parameters=pagination_params,
        )

        # Verify pagination worked
        assert isinstance(result, LLMGetAllMetadataListResponse)
        assert result.count == 3  # Total count should always be 3
        assert len(result.llm_metadata) == len(expected_names)

        # Verify the order of prompts
        for i, expected_name in enumerate(expected_names):
            assert result.llm_metadata[i].name == expected_name

    finally:
        # Cleanup
        for db_prompt in created_prompts:
            db_session.delete(db_prompt)
        db_session.commit()
        db_session.close()


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
def test_get_prompt_versions_with_pagination(page, page_size, sort, expected_versions):
    """Test getting prompt versions with all pagination parameters (page, page_size, sort)"""
    db_session = override_get_db_session()
    repo = AgenticPromptRepository(db_session)

    task_id = str(uuid4())
    prompt_name = "test_prompt"

    # Create multiple versions
    created_prompts = []
    for i in range(1, 5):  # Create versions 1-4
        version_data = {
            "messages": [{"role": "user", "content": f"Version {i}"}],
            "model_name": "gpt-4",
            "model_provider": "openai",
            "version": i,
        }
        db_prompt = AgenticPrompt(name=prompt_name, **version_data).to_db_model(task_id)
        db_session.add(db_prompt)
        created_prompts.append(db_prompt)

    db_session.commit()

    try:
        # Create pagination parameters
        pagination_params = PaginationParameters(
            page=page,
            page_size=page_size,
            sort=sort,
        )

        # Get paginated results
        result = repo.get_llm_item_versions(
            task_id=task_id,
            item_name=prompt_name,
            pagination_parameters=pagination_params,
        )

        # Verify pagination worked
        assert isinstance(result, AgenticPromptVersionListResponse)
        assert result.count == 4  # Total count should always be 4
        assert len(result.versions) == len(expected_versions)

        # Verify the order of versions
        for i, expected_version in enumerate(expected_versions):
            assert result.versions[i].version == expected_version

    finally:
        # Cleanup
        for db_prompt in created_prompts:
            db_session.delete(db_prompt)
        db_session.commit()
        db_session.close()


@pytest.mark.unit_tests
@pytest.mark.parametrize("prompt_version", ["latest", "1", "2025-01-01T00:00:00"])
def test_soft_delete_prompt_by_version_success(prompt_version):
    """Test deleting a prompt with different version formats"""
    db_session = override_get_db_session()
    repo = AgenticPromptRepository(db_session)

    task_id = str(uuid4())
    prompt_name = "test_prompt"

    # Create a database prompt with the sample data
    prompt_data = {
        "messages": [{"role": "user", "content": "Hello, world!"}],
        "model_name": "gpt-4",
        "model_provider": "openai",
        "temperature": 0.7,
        "max_tokens": 100,
        "version": 1,
    }
    db_prompt = AgenticPrompt(name="test_prompt", **prompt_data).to_db_model(task_id)
    db_prompt.created_at = datetime.fromisoformat("2025-01-01T00:00:00")

    # Save to database
    db_session.add(db_prompt)
    db_session.commit()

    try:
        repo.soft_delete_llm_item_version(task_id, prompt_name, prompt_version)
        if prompt_version == "latest":
            with pytest.raises(ValueError) as exc_info:
                repo.get_llm_item(task_id, prompt_name, prompt_version)
            assert (
                f"'{prompt_name}' (version 'latest') not found for task '{task_id}'"
                in str(exc_info.value)
            )
        else:
            result = repo.get_llm_item(task_id, prompt_name, prompt_version)

            assert isinstance(result, AgenticPrompt)
            assert result.name == prompt_name
            assert result.model_name == ""
            assert result.model_provider == "openai"
            assert len(result.messages) == 0
            assert result.messages == []
            assert result.version == 1
            assert result.tools is None
            assert result.deleted_at is not None
    finally:
        # Cleanup
        db_session.delete(db_prompt)
        db_session.commit()
        db_session.close()


@pytest.mark.unit_tests
@patch("clients.llm.llm_client.completion_cost")
@patch("clients.llm.llm_client.litellm.completion")
def test_run_saved_agentic_prompt_with_pydantic_response_format(
    mock_completion,
    mock_completion_cost,
    mock_llm_client,
    sample_unsaved_run_config,
):
    """Test running a saved agentic prompt with a BaseModel response format returns a jsonified version of that model"""
    task_id = "test_task_id"
    prompt_name = "test_prompt"

    prompt, completion_request = ChatCompletionService.to_prompt_and_request(
        sample_unsaved_run_config,
    )
    prompt.config.response_format = create_model(
        "GetWeatherResponse",
        city=(str, Field(..., description="The city to get the weather for.")),
        temperature=(
            int,
            Field(..., description="The temperature in farenheit for the city."),
        ),
    )

    # Mock completion response
    mock_response = MagicMock(spec=ModelResponse)
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message = {
        "content": '{"city": "New York", "temperature": 70}',
    }
    mock_completion.return_value = mock_response
    mock_completion_cost.return_value = 0.002345

    chat_completion_service = ChatCompletionService()
    result = chat_completion_service.run_chat_completion(
        prompt,
        mock_llm_client,
        completion_request,
    )

    assert isinstance(result, AgenticPromptRunResponse)
    assert result.content == '{"city": "New York", "temperature": 70}'
    assert result.cost == "0.002345"
