"""Seeding the onboarding insight prompts into the Arthur system task.

Arthur's text becomes the `production` version only while `production` is a version the
seeder wrote; a version someone else made `production` is never replaced.
"""

import json
from typing import Generator, cast
from uuid import uuid4

import pytest
from arthur_common.models.llm_model_providers import (
    LLMResponseFormat,
    MessageRole,
    ModelProvider,
    OpenAIMessage,
)
from sqlalchemy.orm import Session

from repositories.agentic_prompts_repository import AgenticPromptRepository
from repositories.system_task_repository import (
    SystemTaskRepository,
    onboarding_insight_prompt,
    seed_tag,
)
from schemas.agentic_prompt_schemas import AgenticPrompt
from schemas.request_schemas import CreateAgenticPromptRequest
from services.onboarding.insight_prompts import (
    ONBOARDING_INSIGHT_PROMPT_PREFIX,
    ONBOARDING_INSIGHT_QUESTIONS,
    ONBOARDING_INSIGHT_SYSTEM_PROMPT,
)
from tests.clients.base_test_client import override_get_db_session
from utils.constants import (
    ARTHUR_SYSTEM_TASK_ID,
    EMPTY_MODEL_NAME,
    EMPTY_MODEL_PROVIDER,
    PRODUCTION_TAG,
)


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    session = override_get_db_session()
    SystemTaskRepository(session).initialize_system_tasks()
    yield session
    session.close()


@pytest.fixture
def prompt_name(db_session: Session) -> Generator[str, None, None]:
    """A prompt name of the test's own in the system task, deleted afterwards."""
    name = f"test_seed_{uuid4().hex}"
    yield name
    try:
        AgenticPromptRepository(db_session).delete_llm_item(ARTHUR_SYSTEM_TASK_ID, name)
    except ValueError:
        pass


def _version(session: Session, name: str, version: str = "latest") -> AgenticPrompt:
    return cast(
        AgenticPrompt,
        AgenticPromptRepository(session).get_llm_item(
            ARTHUR_SYSTEM_TASK_ID,
            name,
            version,
        ),
    )


def _save_by_hand(session: Session, name: str, text: str) -> None:
    """A version saved through the API, as a user's edit is: no seed tag."""
    AgenticPromptRepository(session).save_llm_item(
        task_id=ARTHUR_SYSTEM_TASK_ID,
        item_name=name,
        item=_prompt(text),
    )


def _prompt(text: str) -> CreateAgenticPromptRequest:
    return CreateAgenticPromptRequest(
        model_name="claude-opus-5-5",
        model_provider=ModelProvider.ANTHROPIC,
        messages=[
            OpenAIMessage(role=MessageRole.SYSTEM, content=text),
            OpenAIMessage(role=MessageRole.USER, content="{{ traces }}"),
        ],
        tools=[],
    )


@pytest.mark.unit_tests
def test_every_insight_prompt_is_seeded_on_the_default_model(
    db_session: Session,
) -> None:
    for kind, question in ONBOARDING_INSIGHT_QUESTIONS.items():
        prompt = _version(db_session, ONBOARDING_INSIGHT_PROMPT_PREFIX + kind)

        assert prompt.model_provider == EMPTY_MODEL_PROVIDER
        assert prompt.model_name == EMPTY_MODEL_NAME
        assert prompt.config is not None
        assert prompt.config.max_tokens == 4_000
        assert prompt.config.reasoning_effort is None
        assert isinstance(prompt.config.response_format, LLMResponseFormat)
        schema = prompt.config.response_format.json_schema
        assert schema is not None and schema.strict
        assert schema.schema.properties["kind"].enum == list(
            ONBOARDING_INSIGHT_QUESTIONS,
        )
        assert schema.schema.properties["fired"].enum == ["yes", "no", "cannot_tell"]
        assert prompt.variables == ["traces"]
        assert prompt.messages[0].content == ONBOARDING_INSIGHT_SYSTEM_PROMPT
        assert "JSON only" not in ONBOARDING_INSIGHT_SYSTEM_PROMPT
        assert prompt.messages[1].content == (
            f"{{{{ traces }}}}\n\nInsight kind: {kind}\nQuestion: {question}"
        )
        assert PRODUCTION_TAG in prompt.tags
        assert seed_tag(onboarding_insight_prompt(kind)) in prompt.tags


@pytest.mark.unit_tests
def test_every_insight_prompt_is_seeded_with_the_same_response_format(
    db_session: Session,
) -> None:
    # providers cache the schema with the prompt prefix, so one that differed per kind
    # would stop the prompts of a batch from sharing the cached traces
    formats = set()
    for kind in ONBOARDING_INSIGHT_QUESTIONS:
        config = _version(db_session, ONBOARDING_INSIGHT_PROMPT_PREFIX + kind).config
        assert config is not None and config.response_format is not None
        formats.add(json.dumps(config.response_format.model_dump(), sort_keys=True))
    assert len(formats) == 1


@pytest.mark.unit_tests
def test_seeding_again_adds_no_version(db_session: Session) -> None:
    name = ONBOARDING_INSIGHT_PROMPT_PREFIX + "tool_failures"
    before = _version(db_session, name).version

    SystemTaskRepository(db_session).initialize_system_tasks()
    SystemTaskRepository(db_session).initialize_system_tasks()

    assert _version(db_session, name).version == before


@pytest.mark.unit_tests
def test_new_text_becomes_production_over_a_seeded_version(
    db_session: Session,
    prompt_name: str,
) -> None:
    repo = SystemTaskRepository(db_session)
    repo._seed_prompt(prompt_name, _prompt("first text"))

    repo._seed_prompt(prompt_name, _prompt("second text"))

    production = _version(db_session, prompt_name, PRODUCTION_TAG)
    assert production.version == 2
    assert production.messages[0].content == "second text"
    assert seed_tag(_prompt("second text")) in production.tags
    # The earlier version is kept; only the production tag moved.
    first = _version(db_session, prompt_name, "1")
    assert first.messages[0].content == "first text"
    assert PRODUCTION_TAG not in first.tags


@pytest.mark.unit_tests
def test_an_edit_left_untagged_does_not_stop_arthurs_updates(
    db_session: Session,
    prompt_name: str,
) -> None:
    repo = SystemTaskRepository(db_session)
    repo._seed_prompt(prompt_name, _prompt("arthur text"))
    _save_by_hand(db_session, prompt_name, "the user's text")  # v2, not production

    repo._seed_prompt(prompt_name, _prompt("newer arthur text"))

    production = _version(db_session, prompt_name, PRODUCTION_TAG)
    assert production.version == 3
    assert production.messages[0].content == "newer arthur text"
    # The user's version is kept as it was.
    edit = _version(db_session, prompt_name, "2")
    assert edit.messages[0].content == "the user's text"
    assert edit.tags == []


@pytest.mark.unit_tests
def test_a_version_someone_else_made_production_is_never_replaced(
    db_session: Session,
    prompt_name: str,
) -> None:
    repo = SystemTaskRepository(db_session)
    repo._seed_prompt(prompt_name, _prompt("arthur text"))
    _save_by_hand(db_session, prompt_name, "the user's text")
    AgenticPromptRepository(db_session).add_tag_to_llm_item_version(
        task_id=ARTHUR_SYSTEM_TASK_ID,
        item_name=prompt_name,
        item_version="2",
        tag=PRODUCTION_TAG,
    )

    repo._seed_prompt(prompt_name, _prompt("newer arthur text"))

    production = _version(db_session, prompt_name, PRODUCTION_TAG)
    assert production.version == 2
    assert production.messages[0].content == "the user's text"
    assert _version(db_session, prompt_name).version == 2  # no version added


@pytest.mark.unit_tests
def test_a_prompt_with_no_production_version_gets_one(
    db_session: Session,
    prompt_name: str,
) -> None:
    # As on an engine where the prompts were saved through the API before seeding.
    _save_by_hand(db_session, prompt_name, "saved by hand")

    SystemTaskRepository(db_session)._seed_prompt(prompt_name, _prompt("arthur text"))

    production = _version(db_session, prompt_name, PRODUCTION_TAG)
    assert production.version == 2
    assert production.messages[0].content == "arthur text"
    assert _version(db_session, prompt_name, "1").messages[0].content == "saved by hand"
