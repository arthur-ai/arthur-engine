"""Running a saved prompt that names no model: it runs on the default model provider."""

from typing import Generator
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from arthur_common.models.llm_model_providers import (
    LLMResponseFormat,
    LLMResponseFormatEnum,
    MessageRole,
    ModelProvider,
    OpenAIMessage,
    ReasoningEffortEnum,
)
from fastapi import HTTPException
from litellm.types.utils import ModelResponse

from clients.llm.llm_client import LLMClient
from repositories.agentic_prompts_repository import AgenticPromptRepository
from repositories.system_task_repository import (
    SeededPromptRequest,
    onboarding_insight_prompt,
)
from schemas.custom_exceptions import DefaultModelProviderNotSetException
from schemas.request_schemas import (
    CreateAgenticPromptRequest,
    LLMPromptRequestConfigSettings,
    PromptCompletionRequest,
)
from schemas.response_schemas import (
    AgenticPromptRunResponse,
    ModelProviderEvalDefaults,
)
from tests.clients.base_test_client import override_get_db_session
from utils.constants import DEFAULT_ORG_ID, EMPTY_MODEL_NAME, EMPTY_MODEL_PROVIDER

TASK_ID = "test_saved_prompt_default_model"
RESOLVE = (
    "repositories.agentic_prompts_repository.ModelProviderRepository.resolve_model"
)
GET_CLIENT = (
    "repositories.agentic_prompts_repository.ModelProviderRepository"
    ".get_model_provider_client"
)
EVAL_DEFAULTS = (
    "repositories.agentic_prompts_repository.ModelProviderRepository.get_eval_defaults"
)


@pytest.fixture
def repo() -> AgenticPromptRepository:
    return AgenticPromptRepository(override_get_db_session())


@pytest.fixture
def prompt_name(repo: AgenticPromptRepository) -> Generator[str, None, None]:
    name = f"default_model_{uuid4().hex}"
    yield name
    try:
        repo.delete_llm_item(TASK_ID, name)
    except ValueError:
        pass


def _empty_model_prompt(
    response_format: LLMResponseFormat | None = None,
) -> SeededPromptRequest:
    return SeededPromptRequest(
        model_name=EMPTY_MODEL_NAME,
        model_provider=EMPTY_MODEL_PROVIDER,
        messages=[OpenAIMessage(role=MessageRole.USER, content="Hello")],
        config=LLMPromptRequestConfigSettings(response_format=response_format),
    )


def _completion() -> MagicMock:
    message = MagicMock(content="hi", tool_calls=None)
    response = MagicMock(spec=ModelResponse)
    response.choices = [MagicMock(message=message)]
    return MagicMock(response=response, cost="0.001")


async def _run(repo: AgenticPromptRepository, name: str) -> AgenticPromptRunResponse:
    result = await repo.run_saved_prompt(
        TASK_ID,
        name,
        "1",
        PromptCompletionRequest(variables=[]),
        org_id=DEFAULT_ORG_ID,
    )
    assert isinstance(result, AgenticPromptRunResponse)
    return result


@pytest.mark.unit_tests
@pytest.mark.asyncio
async def test_a_prompt_without_a_model_runs_on_the_default(
    repo: AgenticPromptRepository,
    prompt_name: str,
) -> None:
    repo.save_llm_item(TASK_ID, prompt_name, _empty_model_prompt())
    client = LLMClient(provider=ModelProvider.OPENAI, api_key="key")
    client.completion = MagicMock(return_value=_completion())  # type: ignore[method-assign]

    with (
        patch(RESOLVE, return_value=(ModelProvider.OPENAI, "gpt-4o")) as resolve,
        patch(GET_CLIENT, return_value=client) as get_client,
    ):
        result = await _run(repo, prompt_name)

    assert result.content == "hi"
    resolve.assert_called_once_with(None, None)
    get_client.assert_called_once_with(provider=ModelProvider.OPENAI)
    assert client.completion.call_args.kwargs["model"] == "openai/gpt-4o"


@pytest.mark.unit_tests
@pytest.mark.asyncio
async def test_a_prompt_that_names_its_model_keeps_it(
    repo: AgenticPromptRepository,
    prompt_name: str,
) -> None:
    repo.save_llm_item(
        TASK_ID,
        prompt_name,
        CreateAgenticPromptRequest(
            model_name="claude-sonnet-4-6",
            model_provider=ModelProvider.ANTHROPIC,
            messages=[OpenAIMessage(role=MessageRole.USER, content="Hello")],
        ),
    )
    client = LLMClient(provider=ModelProvider.ANTHROPIC, api_key="key")
    client.completion = MagicMock(return_value=_completion())  # type: ignore[method-assign]

    with patch(RESOLVE) as resolve, patch(GET_CLIENT, return_value=client):
        await _run(repo, prompt_name)

    resolve.assert_not_called()
    assert client.completion.call_args.kwargs["model"] == "anthropic/claude-sonnet-4-6"


@pytest.mark.unit_tests
@pytest.mark.asyncio
async def test_no_default_is_a_clear_error(
    repo: AgenticPromptRepository,
    prompt_name: str,
) -> None:
    repo.save_llm_item(TASK_ID, prompt_name, _empty_model_prompt())

    with (
        patch(RESOLVE, side_effect=DefaultModelProviderNotSetException()),
        patch(GET_CLIENT) as get_client,
        pytest.raises(DefaultModelProviderNotSetException),
    ):
        await _run(repo, prompt_name)
    get_client.assert_not_called()


@pytest.mark.unit_tests
@pytest.mark.asyncio
async def test_a_default_without_structured_output_is_refused(
    repo: AgenticPromptRepository,
    prompt_name: str,
) -> None:
    # As the onboarding insight prompts are seeded: a JSON schema, no model.
    repo.save_llm_item(TASK_ID, prompt_name, onboarding_insight_prompt("tool_failures"))

    with (
        patch(RESOLVE, return_value=(ModelProvider.OPENAI, "gpt-3.5-turbo")),
        patch(GET_CLIENT) as get_client,
        pytest.raises(HTTPException) as error,
    ):
        await _run(repo, prompt_name)

    assert error.value.status_code == 400
    assert "does not support" in error.value.detail
    get_client.assert_not_called()


@pytest.mark.unit_tests
@pytest.mark.asyncio
async def test_a_default_with_structured_output_gets_the_schema(
    repo: AgenticPromptRepository,
    prompt_name: str,
) -> None:
    repo.save_llm_item(TASK_ID, prompt_name, onboarding_insight_prompt("tool_failures"))
    client = LLMClient(provider=ModelProvider.OPENAI, api_key="key")
    client.completion = MagicMock(return_value=_completion())  # type: ignore[method-assign]

    with (
        patch(RESOLVE, return_value=(ModelProvider.OPENAI, "gpt-4o")),
        patch(GET_CLIENT, return_value=client),
    ):
        await repo.run_saved_prompt(
            TASK_ID,
            prompt_name,
            "1",
            PromptCompletionRequest(
                variables=[{"name": "traces", "value": "TRACE v1"}],
            ),
            org_id=DEFAULT_ORG_ID,
        )

    kwargs = client.completion.call_args.kwargs
    assert kwargs["model"] == "openai/gpt-4o"
    assert kwargs["response_format"]["type"] == LLMResponseFormatEnum.JSON_SCHEMA.value
    assert kwargs["response_format"]["json_schema"]["strict"] is True


@pytest.mark.unit_tests
@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("model_name", "sent_effort"),
    [
        ("gpt-5-mini", "low"),  # takes reasoning_effort: gets the provider's default
        ("gpt-4o", None),  # takes none: gets nothing, so the call still works
    ],
)
async def test_the_default_model_gets_its_providers_reasoning_default(
    repo: AgenticPromptRepository,
    prompt_name: str,
    model_name: str,
    sent_effort: str | None,
) -> None:
    repo.save_llm_item(TASK_ID, prompt_name, onboarding_insight_prompt("tool_failures"))
    client = LLMClient(provider=ModelProvider.OPENAI, api_key="key")
    client.completion = MagicMock(return_value=_completion())  # type: ignore[method-assign]
    defaults = ModelProviderEvalDefaults(
        provider=ModelProvider.OPENAI,
        reasoning_effort=ReasoningEffortEnum.LOW,
    )

    with (
        patch(RESOLVE, return_value=(ModelProvider.OPENAI, model_name)),
        patch(GET_CLIENT, return_value=client),
        patch(EVAL_DEFAULTS, return_value=defaults),
    ):
        await repo.run_saved_prompt(
            TASK_ID,
            prompt_name,
            "1",
            PromptCompletionRequest(
                variables=[{"name": "traces", "value": "TRACE v1"}],
            ),
            org_id=DEFAULT_ORG_ID,
        )

    kwargs = client.completion.call_args.kwargs
    assert kwargs.get("reasoning_effort") == sent_effort
    # The prompt's own settings are kept alongside.
    assert kwargs["max_tokens"] == 4_000
    assert kwargs["response_format"]["type"] == "json_schema"


@pytest.mark.unit_tests
@pytest.mark.asyncio
async def test_a_prompt_that_names_its_model_gets_no_provider_default(
    repo: AgenticPromptRepository,
    prompt_name: str,
) -> None:
    repo.save_llm_item(
        TASK_ID,
        prompt_name,
        CreateAgenticPromptRequest(
            model_name="gpt-5-mini",
            model_provider=ModelProvider.OPENAI,
            messages=[OpenAIMessage(role=MessageRole.USER, content="Hello")],
        ),
    )
    client = LLMClient(provider=ModelProvider.OPENAI, api_key="key")
    client.completion = MagicMock(return_value=_completion())  # type: ignore[method-assign]

    with patch(GET_CLIENT, return_value=client), patch(EVAL_DEFAULTS) as defaults:
        await _run(repo, prompt_name)

    defaults.assert_not_called()
    assert "reasoning_effort" not in client.completion.call_args.kwargs
