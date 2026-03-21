import logging
from datetime import datetime, timezone

from arthur_common.models.llm_model_providers import (
    MessageRole,
    ModelProvider,
    OpenAIMessage,
)
from sqlalchemy.orm import Session

from db_models.task_models import DatabaseTask
from repositories.agentic_prompts_repository import AgenticPromptRepository
from schemas.request_schemas import CreateAgenticPromptRequest
from services.chatbot.chatbot_prompts import (
    CALL_ARTHUR_API_TOOL,
    SEARCH_ARTHUR_API_TOOL,
    SYSTEM_PROMPT,
)
from utils.constants import (
    CHATBOT_PROMPT_NAME,
    CHATBOT_TASK_ID,
    CHATBOT_TASK_NAME,
)

logger = logging.getLogger(__name__)


class SystemTaskRepository:
    def __init__(self, db_session: Session):
        self.db_session = db_session
        self.agentic_prompt_repo = AgenticPromptRepository(db_session)

    def _create_chatbot_prompt(self) -> None:
        """
        Create (or replace) the chatbot system prompt as an agentic prompt on the chatbot system task,
        tagged as 'production'. Always overwrites so code changes to SYSTEM_PROMPT and tools are
        picked up on restart.
        """
        try:
            self.agentic_prompt_repo.delete_llm_item(
                CHATBOT_TASK_ID,
                CHATBOT_PROMPT_NAME,
            )
            logger.info("Deleting old chatbot prompt.")
        except ValueError:
            pass

        prompt = self.agentic_prompt_repo.save_llm_item(
            task_id=CHATBOT_TASK_ID,
            item_name=CHATBOT_PROMPT_NAME,
            item=CreateAgenticPromptRequest(
                model_name="claude-sonnet-4-6",
                model_provider=ModelProvider.ANTHROPIC,
                messages=[
                    OpenAIMessage(role=MessageRole.SYSTEM, content=SYSTEM_PROMPT),
                ],
                tools=[SEARCH_ARTHUR_API_TOOL, CALL_ARTHUR_API_TOOL],
                config=None,
            ),
        )
        self.agentic_prompt_repo.add_tag_to_llm_item_version(
            task_id=CHATBOT_TASK_ID,
            item_name=CHATBOT_PROMPT_NAME,
            item_version=str(prompt.version),
            tag="production",
        )
        logger.info("Chatbot prompt created.")

    def _create_chatbot_task(self) -> None:
        existing = self.db_session.get(DatabaseTask, CHATBOT_TASK_ID)
        if existing is None:
            now = datetime.now(timezone.utc)
            self.db_session.add(
                DatabaseTask(
                    id=CHATBOT_TASK_ID,
                    name=CHATBOT_TASK_NAME,
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

    def initialize_system_tasks(self) -> None:
        self._create_chatbot_task()
