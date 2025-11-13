import random
from copy import deepcopy
from typing import Generator

import pytest
from arthur_common.models.response_schemas import TaskResponse

from src.schemas.agentic_prompt_schemas import AgenticPrompt
from src.schemas.request_schemas import CreateAgenticPromptRequest
from tests.clients.base_test_client import GenaiEngineTestClientBase
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
        temperature=0.7,
        max_tokens=100,
    )
    _, agentic_prompt = client.create_agentic_prompt(
        task_id=create_agentic_task.id,
        prompt_name=prompt_name,
        prompt_data=prompt_data,
    )
    yield agentic_prompt
