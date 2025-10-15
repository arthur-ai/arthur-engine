from datetime import datetime
from typing import Any, Dict, List
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from litellm.types.utils import ChatCompletionMessageToolCall, Function
from sqlalchemy.exc import IntegrityError

from db_models.agentic_prompt_models import DatabaseAgenticPrompt
from repositories.agentic_prompts_repository import AgenticPromptRepository
from schemas.agentic_prompt_schemas import (
    AgenticPrompt,
    AgenticPromptMessage,
    AgenticPromptRunConfig,
    AgenticPrompts,
    AgenticPromptUnsavedRunConfig,
    VariableTemplateValue,
)
from schemas.response_schemas import AgenticPromptRunResponse


def to_agentic_prompt_messages(
    messages: List[Dict[str, Any]],
) -> List[AgenticPromptMessage]:
    return [AgenticPromptMessage(**message) for message in messages]


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
def sample_unsaved_run_config(sample_prompt_data):
    """Create sample AgenticPrompt instance"""
    return AgenticPromptUnsavedRunConfig(**sample_prompt_data)


@pytest.fixture
def sample_db_prompt(sample_prompt_data):
    """Create sample DatabaseAgenticPrompt instance"""
    task_id = str(uuid4())
    return AgenticPrompt(**sample_prompt_data).to_db_model(task_id)


@pytest.fixture
def expected_db_prompt_messages(sample_db_prompt):
    """Create expected DatabaseAgenticPrompt messages"""
    return to_agentic_prompt_messages(sample_db_prompt.messages)


@pytest.mark.unit_tests
def test_create_prompt(agentic_prompt_repo, sample_prompt_data):
    """Test creating a new AgenticPrompt instance"""
    prompt = agentic_prompt_repo.create_prompt(**sample_prompt_data)

    assert isinstance(prompt, AgenticPrompt)
    assert prompt.name == sample_prompt_data["name"]
    assert prompt.messages == to_agentic_prompt_messages(sample_prompt_data["messages"])
    assert prompt.model_name == sample_prompt_data["model_name"]
    assert prompt.model_provider == sample_prompt_data["model_provider"]
    assert prompt.temperature == sample_prompt_data["temperature"]
    assert prompt.max_tokens == sample_prompt_data["max_tokens"]


@pytest.mark.unit_tests
@patch("schemas.agentic_prompt_schemas.completion")
@patch("schemas.agentic_prompt_schemas.completion_cost")
def test_run_prompt(
    mock_completion_cost,
    mock_completion,
    agentic_prompt_repo,
    sample_unsaved_run_config,
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

    prompt, config = sample_unsaved_run_config._to_prompt_and_config()
    result = agentic_prompt_repo.run_prompt_completion(prompt, config)

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
        to_agentic_prompt_messages(call_args["messages"])
        == sample_unsaved_run_config.messages
    )
    assert call_args["temperature"] == sample_unsaved_run_config.temperature


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
    mock_filter.first.return_value = sample_db_prompt

    result = agentic_prompt_repo.get_prompt(task_id, prompt_name)

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
    messages = to_agentic_prompt_messages(added_prompt.messages)

    assert isinstance(added_prompt, DatabaseAgenticPrompt)
    assert added_prompt.task_id == task_id
    assert added_prompt.name == sample_agentic_prompt.name
    assert messages == sample_agentic_prompt.messages


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
@patch("schemas.agentic_prompt_schemas.completion")
@patch("schemas.agentic_prompt_schemas.completion_cost")
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

    prompt = agentic_prompt_repo.get_prompt(task_id, prompt_name)
    result = agentic_prompt_repo.run_prompt_completion(prompt)

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
def test_agentic_prompt_to_dict(sample_agentic_prompt):
    """Test converting AgenticPrompt to dictionary"""
    prompt_dict = sample_agentic_prompt.to_dict()

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
@patch("schemas.agentic_prompt_schemas.completion")
@patch("schemas.agentic_prompt_schemas.completion_cost")
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
        "tool_calls": [{"id": "call_456", "function": {"name": "test_tool"}}],
    }
    mock_completion.return_value = mock_response
    mock_completion_cost.return_value = 0.003456

    result = sample_agentic_prompt.run_chat_completion()

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

    prompt = AgenticPromptRunConfig(variables=variables)
    message = [{"role": "user", "content": message}]
    result = prompt.replace_variables(message)
    assert result[0]["content"] == expected_message


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
        "tool_choice": "get_weather",
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
    assert reconstructed_prompt.tools[0].name == "get_weather"
    assert reconstructed_prompt.tools[0].description == "Get weather info"
    assert reconstructed_prompt.tools[0].strict == True
    assert len(reconstructed_prompt.tools[0].function_definition.properties) == 1
    assert reconstructed_prompt.tools[0].function_definition.required == ["location"]

    # Verify tool_choice is deserialized correctly (should be function name string)
    assert reconstructed_prompt.tool_choice == "get_weather"


@pytest.mark.unit_tests
def test_agentic_prompt_response_format_serialization():
    """Test that response_format serializes and deserializes correctly"""
    prompt_data = {
        "name": "test_response_format",
        "messages": [{"role": "user", "content": "Test"}],
        "model_name": "gpt-4",
        "model_provider": "openai",
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
    assert reconstructed_prompt.response_format.type == "json_schema"
    assert reconstructed_prompt.response_format.response_schema.name == "user_schema"
    assert (
        reconstructed_prompt.response_format.response_schema.description
        == "User information"
    )
    assert reconstructed_prompt.response_format.response_schema.strict == None
    assert (
        len(reconstructed_prompt.response_format.response_schema.json_schema.properties)
        == 1
    )
    assert (
        reconstructed_prompt.response_format.response_schema.json_schema.required
        == ["name"]
    )


@pytest.mark.unit_tests
@patch("schemas.agentic_prompt_schemas.completion")
@patch("schemas.agentic_prompt_schemas.completion_cost")
def test_agentic_prompt_tool_call_message_serialization(
    mock_completion_cost,
    mock_completion,
    agentic_prompt_repo,
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

    run_config = AgenticPromptUnsavedRunConfig(
        name="tool_call_prompt",
        messages=messages,
        model_name="gpt-4o",
        model_provider="openai",
    )

    # Mock LiteLLM completion response
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message = {
        "content": "Got it!",
        "tool_calls": None,
    }
    mock_completion.return_value = mock_response
    mock_completion_cost.return_value = 0.000123

    # Run the unsaved prompt
    prompt, config = run_config._to_prompt_and_config()
    result = agentic_prompt_repo.run_prompt_completion(prompt, config)
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
