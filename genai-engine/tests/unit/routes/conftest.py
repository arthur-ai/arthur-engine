import random
from contextlib import contextmanager
from copy import deepcopy
from typing import Generator
from unittest.mock import MagicMock

import pytest
from arthur_common.models.response_schemas import TaskResponse

from src.schemas.agentic_prompt_schemas import AgenticPrompt
from src.schemas.request_schemas import (
    CreateAgenticPromptRequest,
    LLMPromptRequestConfigSettings,
)
from tests.clients.base_test_client import (
    GenaiEngineTestClientBase,
    override_get_db_session,
)
from tests.clients.unit_test_client import get_genai_engine_test_client


@pytest.fixture(scope="module", autouse=True)
def client() -> Generator[GenaiEngineTestClientBase, None, None]:
    yield get_genai_engine_test_client()


@pytest.fixture
def changed_user_client(
    request: pytest.FixtureRequest,
    client: GenaiEngineTestClientBase,
):
    previous_header = deepcopy(client.authorized_chat_headers)
    client.authorized_chat_headers = {
        "Authorization": f"Bearer {request.keywords.node.callspec.params.get('user_role')}",
    }
    yield client
    client.authorized_chat_headers = previous_header


@pytest.fixture
def create_agentic_task(
    client: GenaiEngineTestClientBase,
) -> Generator[TaskResponse, None, None]:
    status_code, task = client.create_task(
        name=f"agentic_task_{random.random()}",
        is_agentic=True,
    )
    assert status_code == 200
    yield task
    client.delete_task(task.id)


@pytest.fixture
def create_agentic_prompt(
    client: GenaiEngineTestClientBase,
    create_agentic_task: TaskResponse,
) -> Generator[AgenticPrompt, None, None]:
    prompt_name = "test_prompt"
    prompt_data = CreateAgenticPromptRequest(
        messages=[{"role": "user", "content": "Hello, world!"}],
        model_name="gpt-4",
        model_provider="openai",
        config=LLMPromptRequestConfigSettings(
            temperature=0.7,
            max_tokens=100,
        ),
    )
    _, agentic_prompt = client.create_agentic_prompt(
        task_id=create_agentic_task.id,
        prompt_name=prompt_name,
        prompt_data=prompt_data,
    )
    yield agentic_prompt


def setup_db_session_context_mock(mock_db_session_context: MagicMock) -> None:
    """
    Helper function to set up the db_session_context mock for background thread execution.

    This ensures all background threads use the same test database engine by replicating
    the behavior of db_session_context but using override_get_db_session.

    Args:
        mock_db_session_context: The mock object for services.experiment_executor.db_session_context
    """

    def mock_get_db_session_generator():
        """Generator that yields a test database session, matching get_db_session() behavior"""
        session = override_get_db_session()
        try:
            yield session
        finally:
            session.close()

    @contextmanager
    def mock_db_session_context_func():
        """Context manager that uses override_get_db_session for background threads"""
        # Replicate the exact behavior of db_session_context
        session_gen = mock_get_db_session_generator()
        session = next(session_gen)
        try:
            yield session
        finally:
            try:
                next(session_gen)  # This will raise StopIteration and close the session
            except StopIteration:
                pass

    # db_session_context is a context manager function, so when called it should return a context manager
    # Use side_effect to return a new context manager each time it's called
    mock_db_session_context.side_effect = lambda: mock_db_session_context_func()
