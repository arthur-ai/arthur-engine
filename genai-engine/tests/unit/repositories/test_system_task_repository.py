from typing import cast

import pytest
from arthur_common.models.llm_model_providers import (
    MessageRole,
    ModelProvider,
    OpenAIMessage,
)

from db_models.configuration_models import DatabaseApplicationConfiguration
from repositories.agentic_prompts_repository import AgenticPromptRepository
from repositories.system_task_repository import SystemTaskRepository
from schemas.agentic_prompt_schemas import AgenticPrompt
from schemas.enums import ApplicationConfigurations
from schemas.request_schemas import CreateAgenticPromptRequest
from tests.clients.base_test_client import override_get_db_session
from utils.constants import (
    ARTHUR_SYSTEM_TASK_ID,
    CHATBOT_PROMPT_NAME,
    CHATBOT_SUMMARIZER_PROMPT_NAME,
    EMPTY_MODEL_NAME,
    EMPTY_MODEL_PROVIDER,
)

# The chatbot prompts are shared system state, read by the chatbot route tests
pytestmark = pytest.mark.xdist_group("default_model_provider")

CHATBOT_PROMPTS = (CHATBOT_PROMPT_NAME, CHATBOT_SUMMARIZER_PROMPT_NAME)


def _production_model(prompt_repo: AgenticPromptRepository, name: str) -> tuple:
    prompt = cast(
        AgenticPrompt,
        prompt_repo.get_llm_item_by_tag(
            task_id=ARTHUR_SYSTEM_TASK_ID,
            item_name=name,
            tag="production",
        ),
    )
    return prompt.model_provider, prompt.model_name


def _store_model(
    prompt_repo: AgenticPromptRepository,
    name: str,
    provider: ModelProvider,
    model_name: str,
) -> None:
    prompt = prompt_repo.save_llm_item(
        task_id=ARTHUR_SYSTEM_TASK_ID,
        item_name=name,
        item=CreateAgenticPromptRequest(
            model_provider=provider,
            model_name=model_name,
            messages=[OpenAIMessage(role=MessageRole.SYSTEM, content="test")],
        ),
    )
    prompt_repo.add_tag_to_llm_item_version(
        task_id=ARTHUR_SYSTEM_TASK_ID,
        item_name=name,
        item_version=str(prompt.version),
        tag="production",
    )


def _simulate_first_boot_after_upgrade(
    db, prompt_repo: AgenticPromptRepository
) -> None:
    """Prompts on the old hard-coded seed, and no marker that they were moved yet."""
    marker = db.get(
        DatabaseApplicationConfiguration,
        ApplicationConfigurations.CHATBOT_SEED_MOVED_TO_DEFAULT,
    )
    if marker is not None:
        db.delete(marker)
        db.commit()
    for name in CHATBOT_PROMPTS:
        _store_model(prompt_repo, name, ModelProvider.ANTHROPIC, "claude-sonnet-4-6")


def _assert_models(prompt_repo: AgenticPromptRepository, expected: tuple) -> None:
    for name in CHATBOT_PROMPTS:
        assert _production_model(prompt_repo, name) == expected


@pytest.mark.unit_tests
def test_chatbot_prompts_use_the_default_model_provider():
    db = override_get_db_session()
    system_tasks = SystemTaskRepository(db)
    prompt_repo = AgenticPromptRepository(db)
    try:
        # first boot after the upgrade: the old seed was never picked by an admin,
        # so it moves to the default, once
        _simulate_first_boot_after_upgrade(db, prompt_repo)
        system_tasks.initialize_system_tasks()
        _assert_models(prompt_repo, (EMPTY_MODEL_PROVIDER, EMPTY_MODEL_NAME))
        assert (
            db.get(
                DatabaseApplicationConfiguration,
                ApplicationConfigurations.CHATBOT_SEED_MOVED_TO_DEFAULT,
            )
            is not None
        )

        # a restart keeps the 'empty' placeholder
        system_tasks.initialize_system_tasks()
        _assert_models(prompt_repo, (EMPTY_MODEL_PROVIDER, EMPTY_MODEL_NAME))

        # after the move, an admin who picks the old seed model keeps it
        for name in CHATBOT_PROMPTS:
            _store_model(
                prompt_repo, name, ModelProvider.ANTHROPIC, "claude-sonnet-4-6"
            )
        system_tasks.initialize_system_tasks()
        _assert_models(prompt_repo, (ModelProvider.ANTHROPIC, "claude-sonnet-4-6"))

        # and any other pick survives a restart too
        for name in CHATBOT_PROMPTS:
            _store_model(prompt_repo, name, ModelProvider.OPENAI, "gpt-4o")
        system_tasks.initialize_system_tasks()
        _assert_models(prompt_repo, (ModelProvider.OPENAI, "gpt-4o"))
    finally:
        # back to the default for the other tests
        _simulate_first_boot_after_upgrade(db, prompt_repo)
        system_tasks.initialize_system_tasks()
        db.close()
