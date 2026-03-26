import logging
from datetime import datetime, timezone
from typing import cast

from arthur_common.models.llm_model_providers import (
    MessageRole,
    ModelProvider,
    OpenAIMessage,
)
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
)

logger = logging.getLogger(__name__)


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

            model_provider = existing.model_provider
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

            model_provider = existing.model_provider
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
                content=""""PREVIOUS CONVERSATION:

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
                ),
            )
            self.db_session.commit()
            logger.info("Chatbot system task created.")

        self._create_chatbot_prompt()
        self._create_chatbot_summarizer_prompt()

    def initialize_system_tasks(self) -> None:
        self._create_chatbot_task()
