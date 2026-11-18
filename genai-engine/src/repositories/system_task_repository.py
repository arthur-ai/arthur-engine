import logging
from datetime import datetime, timezone
from typing import cast

from arthur_common.models.llm_model_providers import (
    LLMTool,
    MessageRole,
    ModelProvider,
    OpenAIMessage,
)
from sqlalchemy import text
from sqlalchemy.orm import Session

from db_models.task_models import DatabaseTask
from repositories.agentic_prompts_repository import AgenticPromptRepository
from schemas.agentic_prompt_schemas import AgenticPrompt
from schemas.request_schemas import CreateAgenticPromptRequest
from services.chatbot.chatbot_prompts import (
    CALL_ARTHUR_API_TOOL,
    SEARCH_ARTHUR_API_TOOL,
    SUMMARIZE_HISTORY_PROMPT,
    SYSTEM_PROMPT,
)
from utils.constants import (
    ARTHUR_SYSTEM_TASK_ID,
    ARTHUR_SYSTEM_TASK_NAME,
    CHATBOT_PROMPT_NAME,
    CHATBOT_SUMMARIZER_PROMPT_NAME,
    EMPTY_MODEL_NAME,
    EMPTY_MODEL_PROVIDER,
    SYSTEM_ORG_ID,
)

logger = logging.getLogger(__name__)

# The model both chatbot prompts were seeded with before they used the default
# model provider. A stored copy of it was never picked by an admin, so it moves to
# the default.
_OLD_CHATBOT_SEED_PROVIDER = ModelProvider.ANTHROPIC
_OLD_CHATBOT_SEED_MODEL = "claude-sonnet-4-6"

# Arbitrary fixed ID used as a PostgreSQL advisory lock key to serialize
# system task initialization across concurrent workers/replicas.
_SYSTEM_TASK_INIT_LOCK_ID = 8675309


class SystemTaskRepository:
    def __init__(self, db_session: Session):
        self.db_session = db_session
        self.agentic_prompt_repo = AgenticPromptRepository(db_session)

    def _take_existing_model(
        self,
        prompt_name: str,
    ) -> tuple[str, str]:
        """Delete the production version of a chatbot system prompt and return the
        model to re-create it with.

        A model an admin picked is kept. Anything else (no prompt yet, the 'empty'
        placeholder, or the old hard-coded seed) becomes 'empty', so the prompt runs
        on the instance's default model provider."""
        try:
            existing = cast(
                AgenticPrompt,
                self.agentic_prompt_repo.get_llm_item_by_tag(
                    task_id=ARTHUR_SYSTEM_TASK_ID,
                    item_name=prompt_name,
                    tag="production",
                ),
            )
        except ValueError:
            return EMPTY_MODEL_PROVIDER, EMPTY_MODEL_NAME

        self.agentic_prompt_repo.delete_llm_item(ARTHUR_SYSTEM_TASK_ID, prompt_name)
        logger.info(f"Deleting old {prompt_name}.")

        stored = (existing.model_provider, existing.model_name)
        if existing.model_provider == EMPTY_MODEL_PROVIDER or stored == (
            _OLD_CHATBOT_SEED_PROVIDER,
            _OLD_CHATBOT_SEED_MODEL,
        ):
            return EMPTY_MODEL_PROVIDER, EMPTY_MODEL_NAME
        return ModelProvider(existing.model_provider).value, existing.model_name

    def _save_production_prompt(
        self,
        prompt_name: str,
        model_provider: str,
        model_name: str,
        messages: list[OpenAIMessage],
        tools: list[LLMTool],
    ) -> None:
        item = CreateAgenticPromptRequest(
            # Placeholder provider: the request type only accepts real providers, so
            # the 'empty' sentinel is set below without re-validating.
            model_provider=ModelProvider.OPENAI,
            model_name=model_name,
            messages=messages,
            tools=tools,
            config=None,
        )
        item = item.model_copy(update={"model_provider": model_provider})
        prompt = self.agentic_prompt_repo.save_llm_item(
            task_id=ARTHUR_SYSTEM_TASK_ID,
            item_name=prompt_name,
            item=item,
        )
        self.agentic_prompt_repo.add_tag_to_llm_item_version(
            task_id=ARTHUR_SYSTEM_TASK_ID,
            item_name=prompt_name,
            item_version=str(prompt.version),
            tag="production",
        )

    def _create_chatbot_prompt(self) -> None:
        """Re-create the chatbot system prompt with the latest text, keeping a model
        an admin picked; otherwise it uses the default model provider."""
        model_provider, model_name = self._take_existing_model(CHATBOT_PROMPT_NAME)
        self._save_production_prompt(
            CHATBOT_PROMPT_NAME,
            model_provider,
            model_name,
            messages=[
                OpenAIMessage(role=MessageRole.SYSTEM, content=SYSTEM_PROMPT),
            ],
            tools=[SEARCH_ARTHUR_API_TOOL, CALL_ARTHUR_API_TOOL],
        )
        logger.info("Chatbot prompt created.")

    def _create_chatbot_summarizer_prompt(self) -> None:
        """Create the chatbot summarizer prompt for compressing conversation history."""
        model_provider, model_name = self._take_existing_model(
            CHATBOT_SUMMARIZER_PROMPT_NAME,
        )
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
        self._save_production_prompt(
            CHATBOT_SUMMARIZER_PROMPT_NAME,
            model_provider,
            model_name,
            messages=messages,
            tools=[],
        )
        logger.info("Chatbot summarizer prompt created.")

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
