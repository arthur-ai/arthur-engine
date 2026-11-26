"""Prompt caching on the saved-prompt route: Arthur's system-task prompts get cache
breakpoints, customer prompts are sent as saved."""

from typing import Generator
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from arthur_common.models.common_schemas import VariableTemplateValue
from arthur_common.models.llm_model_providers import ModelProvider
from litellm.types.utils import ModelResponse

from clients.llm.llm_client import LLMClient
from repositories.agentic_prompts_repository import AgenticPromptRepository
from repositories.system_task_repository import onboarding_insight_prompt
from schemas.request_schemas import PromptCompletionRequest
from services.onboarding.insight_prompts import ONBOARDING_INSIGHT_PROMPT_PREFIX
from tests.clients.base_test_client import override_get_db_session
from utils.constants import ARTHUR_SYSTEM_TASK_ID, DEFAULT_ORG_ID

CUSTOMER_TASK_ID = "test_system_prompt_caching_customer"
TRACES = "FACTS\nt01: fetch_url called\n\n[1] AGENT root\n  [2] TOOL fetch_url"
GET_CLIENT = (
    "repositories.agentic_prompts_repository.ModelProviderRepository"
    ".get_model_provider_client"
)


@pytest.fixture
def repo() -> AgenticPromptRepository:
    return AgenticPromptRepository(override_get_db_session())


@pytest.fixture
def saved(repo: AgenticPromptRepository) -> Generator[list, None, None]:
    created: list[tuple[str, str]] = []
    yield created
    for task_id, name in created:
        try:
            repo.delete_llm_item(task_id, name)
        except ValueError:
            pass


def _completion() -> MagicMock:
    message = MagicMock(content="{}", tool_calls=None)
    response = MagicMock(spec=ModelResponse)
    response.choices = [MagicMock(message=message)]
    return MagicMock(response=response, cost="0.001")


async def _run_insight_prompt(
    repo: AgenticPromptRepository,
    saved: list,
    task_id: str,
) -> list[dict]:
    """Save the internet_access insight prompt on Claude under the task, run it on
    TRACES and return the messages sent to the model."""
    name = f"{ONBOARDING_INSIGHT_PROMPT_PREFIX}test_{uuid4().hex}"
    prompt = onboarding_insight_prompt("internet_access").model_copy(
        update={
            "model_provider": ModelProvider.ANTHROPIC,
            "model_name": "claude-sonnet-4-6",
        },
    )
    repo.save_llm_item(task_id, name, prompt)
    saved.append((task_id, name))
    client = LLMClient(provider=ModelProvider.ANTHROPIC, api_key="key")
    client.completion = MagicMock(return_value=_completion())  # type: ignore[method-assign]

    with patch(GET_CLIENT, return_value=client):
        await repo.run_saved_prompt(
            task_id,
            name,
            "1",
            PromptCompletionRequest(
                variables=[VariableTemplateValue(name="traces", value=TRACES)],
            ),
            org_id=DEFAULT_ORG_ID,
        )

    messages: list[dict] = client.completion.call_args.kwargs["messages"]
    return messages


@pytest.mark.unit_tests
@pytest.mark.asyncio
async def test_system_task_insight_prompt_is_sent_with_a_breakpoint_after_the_traces(
    repo: AgenticPromptRepository,
    saved: list,
) -> None:
    messages = await _run_insight_prompt(repo, saved, ARTHUR_SYSTEM_TASK_ID)

    head, tail = messages[1]["content"]
    assert head == {
        "type": "text",
        "text": TRACES + "\n\n",
        "cache_control": {"type": "ephemeral"},
    }
    assert tail["text"].startswith("Insight kind: internet_access")


@pytest.mark.unit_tests
@pytest.mark.asyncio
async def test_customer_prompt_is_sent_as_saved(
    repo: AgenticPromptRepository,
    saved: list,
) -> None:
    messages = await _run_insight_prompt(repo, saved, CUSTOMER_TASK_ID)

    assert isinstance(messages[1]["content"], str)
    assert messages[1]["content"].startswith(TRACES + "\n\nInsight kind:")
    assert "cache_control" not in str(messages)
