import hashlib
import json
import logging
from datetime import datetime, timezone
from typing import Literal, Union, cast

from arthur_common.models.llm_model_providers import (
    MessageRole,
    ModelProvider,
    OpenAIMessage,
)
from pydantic import Field
from sqlalchemy import text
from sqlalchemy.orm import Session

from db_models.task_models import DatabaseTask
from repositories.agentic_prompts_repository import AgenticPromptRepository
from schemas.agentic_prompt_schemas import AgenticPrompt
from schemas.request_schemas import (
    CreateAgenticPromptRequest,
    LLMPromptRequestConfigSettings,
)
from services.chatbot.chatbot_prompts import (
    CALL_ARTHUR_API_TOOL,
    SEARCH_ARTHUR_API_TOOL,
    SUMMARIZE_HISTORY_PROMPT,
    SYSTEM_PROMPT,
)
from services.onboarding.insight_prompts import (
    ONBOARDING_INSIGHT_MAX_TOKENS,
    ONBOARDING_INSIGHT_PROMPT_PREFIX,
    ONBOARDING_INSIGHT_QUESTIONS,
    ONBOARDING_INSIGHT_SYSTEM_PROMPT,
    onboarding_insight_response_format,
    onboarding_insight_user_message,
)
from utils.constants import (
    ARTHUR_SYSTEM_TASK_ID,
    ARTHUR_SYSTEM_TASK_NAME,
    CHATBOT_PROMPT_NAME,
    CHATBOT_SUMMARIZER_PROMPT_NAME,
    EMPTY_MODEL_NAME,
    EMPTY_MODEL_PROVIDER,
    PRODUCTION_TAG,
    SYSTEM_ORG_ID,
)

logger = logging.getLogger(__name__)

# Arbitrary fixed ID used as a PostgreSQL advisory lock key to serialize
# system task initialization across concurrent workers/replicas.
_SYSTEM_TASK_INIT_LOCK_ID = 8675309

# Marks a prompt version the seeder wrote, with a hash of its content. A version without
# such a tag was made by someone else, and the seeder never replaces it.
SEED_TAG_PREFIX = "arthur-seed-"


def seed_tag(prompt: CreateAgenticPromptRequest) -> str:
    """The tag of a seeded version: the same content always gets the same tag."""
    content = json.dumps(prompt.model_dump(mode="json"), sort_keys=True)
    return SEED_TAG_PREFIX + hashlib.sha256(content.encode()).hexdigest()[:12]


class SeededPromptRequest(CreateAgenticPromptRequest):
    """A prompt Arthur seeds, which may leave the model to the instance's default."""

    model_provider: Union[ModelProvider, Literal["empty"]] = Field(  # type: ignore[assignment]
        description="Provider of the LLM model, or 'empty' for the default model provider",
    )


def onboarding_insight_prompt(kind: str) -> SeededPromptRequest:
    """One onboarding insight prompt as Arthur ships it, on the default model."""
    return SeededPromptRequest(
        model_name=EMPTY_MODEL_NAME,
        model_provider=cast(Literal["empty"], EMPTY_MODEL_PROVIDER),
        messages=[
            OpenAIMessage(
                role=MessageRole.SYSTEM,
                content=ONBOARDING_INSIGHT_SYSTEM_PROMPT,
            ),
            OpenAIMessage(
                role=MessageRole.USER,
                content=onboarding_insight_user_message(kind),
            ),
        ],
        tools=[],
        config=LLMPromptRequestConfigSettings.model_validate(
            {
                "max_tokens": ONBOARDING_INSIGHT_MAX_TOKENS,
                "response_format": onboarding_insight_response_format(kind),
            },
        ),
    )


class SystemTaskRepository:
    def __init__(self, db_session: Session):
        self.db_session = db_session
        self.agentic_prompt_repo = AgenticPromptRepository(db_session)

    def _create_chatbot_prompt(self) -> None:
        """
        Create the chatbot system prompt if it doesn't already exist.
        If a production-tagged prompt already exists, leave it as-is to preserve
        user-configured model provider and model name.
        """
        model_provider = ModelProvider.ANTHROPIC
        model_name = "claude-sonnet-4-6"

        try:
            existing = cast(
                AgenticPrompt,
                self.agentic_prompt_repo.get_llm_item_by_tag(
                    task_id=ARTHUR_SYSTEM_TASK_ID,
                    item_name=CHATBOT_PROMPT_NAME,
                    tag="production",
                ),
            )

            # Preserve the user's configured model. If the stored value is the
            # "empty" SDG sentinel (shouldn't happen for chatbot), fall back to
            # the default above.
            if existing.model_provider != EMPTY_MODEL_PROVIDER:
                model_provider = ModelProvider(existing.model_provider)
            model_name = existing.model_name

            self.agentic_prompt_repo.delete_llm_item(
                ARTHUR_SYSTEM_TASK_ID,
                CHATBOT_PROMPT_NAME,
            )
            logger.info("Deleting old chatbot prompt.")
        except ValueError:
            pass

        prompt = self.agentic_prompt_repo.save_llm_item(
            task_id=ARTHUR_SYSTEM_TASK_ID,
            item_name=CHATBOT_PROMPT_NAME,
            item=CreateAgenticPromptRequest(
                model_name=model_name,
                model_provider=model_provider,
                messages=[
                    OpenAIMessage(role=MessageRole.SYSTEM, content=SYSTEM_PROMPT),
                ],
                tools=[SEARCH_ARTHUR_API_TOOL, CALL_ARTHUR_API_TOOL],
                config=None,
            ),
        )
        self.agentic_prompt_repo.add_tag_to_llm_item_version(
            task_id=ARTHUR_SYSTEM_TASK_ID,
            item_name=CHATBOT_PROMPT_NAME,
            item_version=str(prompt.version),
            tag="production",
        )
        logger.info("Chatbot prompt created.")

    def _create_chatbot_summarizer_prompt(self) -> None:
        """Create the chatbot summarizer prompt for compressing conversation history."""
        model_provider = ModelProvider.ANTHROPIC
        model_name = "claude-sonnet-4-6"

        try:
            existing = cast(
                AgenticPrompt,
                self.agentic_prompt_repo.get_llm_item_by_tag(
                    task_id=ARTHUR_SYSTEM_TASK_ID,
                    item_name=CHATBOT_SUMMARIZER_PROMPT_NAME,
                    tag="production",
                ),
            )

            # Preserve the user's configured model. If the stored value is the
            # "empty" SDG sentinel (shouldn't happen for chatbot), fall back to
            # the default above.
            if existing.model_provider != EMPTY_MODEL_PROVIDER:
                model_provider = ModelProvider(existing.model_provider)
            model_name = existing.model_name

            self.agentic_prompt_repo.delete_llm_item(
                ARTHUR_SYSTEM_TASK_ID,
                CHATBOT_SUMMARIZER_PROMPT_NAME,
            )
            logger.info("Deleting old chatbot summarizer prompt.")
        except ValueError:
            pass

        messages = [
            OpenAIMessage(
                role=MessageRole.SYSTEM,
                content=SUMMARIZE_HISTORY_PROMPT,
            ),
            OpenAIMessage(
                role=MessageRole.USER,
                content="""PREVIOUS CONVERSATION:

                {{prev_conversation}}""",
            ),
        ]

        prompt = self.agentic_prompt_repo.save_llm_item(
            task_id=ARTHUR_SYSTEM_TASK_ID,
            item_name=CHATBOT_SUMMARIZER_PROMPT_NAME,
            item=CreateAgenticPromptRequest(
                model_name=model_name,
                model_provider=model_provider,
                messages=messages,
                tools=[],
                config=None,
            ),
        )
        self.agentic_prompt_repo.add_tag_to_llm_item_version(
            task_id=ARTHUR_SYSTEM_TASK_ID,
            item_name=CHATBOT_SUMMARIZER_PROMPT_NAME,
            item_version=str(prompt.version),
            tag="production",
        )
        logger.info("Chatbot summarizer prompt created.")

    def _seed_prompt(self, name: str, prompt: CreateAgenticPromptRequest) -> None:
        """Make Arthur's version of a prompt the `production` one, unless someone else's is.

        The decision is made on the version tagged `production`, which is the one that runs.
        Unlike the chatbot's prompts, these are never deleted and recreated:
        - no version is `production` (none yet, or saved by hand): save this content;
        - `production` is this content already: nothing to do;
        - `production` is an older seeded version: save this content as a new version;
        - `production` is a version someone else made (no seed tag): leave it.
        The new version is tagged `production` and with its seed tag, so `production` only
        moves off a version the seeder wrote. Versions saved since then keep their content.
        """
        tag = seed_tag(prompt)
        try:
            production = self.agentic_prompt_repo.get_llm_item(
                ARTHUR_SYSTEM_TASK_ID,
                name,
                PRODUCTION_TAG,
            )
        except ValueError:
            production = None

        if production is not None:
            if tag in production.tags:
                return
            if not any(t.startswith(SEED_TAG_PREFIX) for t in production.tags):
                logger.info(
                    f"Prompt {name} version {production.version} was made `production` "
                    "by someone other than Arthur; leaving it.",
                )
                return

        saved = self.agentic_prompt_repo.save_llm_item(
            task_id=ARTHUR_SYSTEM_TASK_ID,
            item_name=name,
            item=prompt,
        )
        for version_tag in (PRODUCTION_TAG, tag):
            self.agentic_prompt_repo.add_tag_to_llm_item_version(
                task_id=ARTHUR_SYSTEM_TASK_ID,
                item_name=name,
                item_version=str(saved.version),
                tag=version_tag,
            )
        logger.info(f"Prompt {name} version {saved.version} seeded.")

    def _seed_onboarding_insight_prompts(self) -> None:
        for kind in ONBOARDING_INSIGHT_QUESTIONS:
            self._seed_prompt(
                ONBOARDING_INSIGHT_PROMPT_PREFIX + kind,
                onboarding_insight_prompt(kind),
            )

    def _create_chatbot_task(self) -> None:
        existing = self.db_session.get(DatabaseTask, ARTHUR_SYSTEM_TASK_ID)
        if existing is None:
            now = datetime.now(timezone.utc)
            self.db_session.add(
                DatabaseTask(
                    id=ARTHUR_SYSTEM_TASK_ID,
                    name=ARTHUR_SYSTEM_TASK_NAME,
                    created_at=now,
                    updated_at=now,
                    is_agentic=True,
                    is_autocreated=False,
                    is_system_task=True,
                    org_id=SYSTEM_ORG_ID,
                ),
            )
            self.db_session.commit()
            logger.info("Chatbot system task created.")

        self._create_chatbot_prompt()
        self._create_chatbot_summarizer_prompt()
        self._seed_onboarding_insight_prompts()

    def _is_postgresql(self) -> bool:
        return (
            self.db_session.bind is not None
            and self.db_session.bind.dialect.name == "postgresql"
        )

    def initialize_system_tasks(self) -> None:
        # Use a non-blocking advisory lock so only the first worker runs the
        # delete-and-recreate sequence. Other workers skip immediately.
        # Advisory locks are PostgreSQL-specific; skip locking on other backends
        # (e.g. SQLite in tests).
        if self._is_postgresql():
            logger.info("Acquiring system task initialization lock.")
            result = self.db_session.execute(
                text("SELECT pg_try_advisory_lock(:lock_id)"),
                {"lock_id": _SYSTEM_TASK_INIT_LOCK_ID},
            )
            acquired = result.scalar()

            if not acquired:
                logger.info(
                    "System task initialization already in progress on another worker, skipping.",
                )
                return

        try:
            self._create_chatbot_task()
        finally:
            if self._is_postgresql():
                self.db_session.execute(
                    text("SELECT pg_advisory_unlock(:lock_id)"),
                    {"lock_id": _SYSTEM_TASK_INIT_LOCK_ID},
                )
                logger.info("Released system task initialization lock.")
