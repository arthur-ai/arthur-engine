"""Initializes built-in system tasks on engine startup."""

import logging
from datetime import datetime

from arthur_common.models.llm_model_providers import (
    MessageRole,
    OpenAIMessage,
)
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from db_models.agentic_prompt_models import (
    DatabaseAgenticPrompt,
    DatabaseAgenticPromptVersionTag,
)
from db_models.task_models import DatabaseTask
from services.synthetic_data_prompts import (
    CONVERSATION_USER_PROMPT_TEMPLATE,
    INITIAL_GENERATION_USER_PROMPT_TEMPLATE,
    SYSTEM_PROMPT_TEMPLATE,
)
from utils.constants import (
    EMPTY_MODEL_NAME,
    EMPTY_MODEL_PROVIDER,
    PRODUCTION_TAG,
    SYNTHETIC_DATA_CONVERSATION_USER_PROMPT_NAME,
    SYNTHETIC_DATA_INITIAL_USER_PROMPT_NAME,
    SYNTHETIC_DATA_SYSTEM_PROMPT_NAME,
    SYNTHETIC_DATASET_TASK_ID,
    SYNTHETIC_DATASET_TASK_NAME,
)

logger = logging.getLogger(__name__)


def initialize_system_tasks(db_session: Session) -> None:
    """Idempotently create all system tasks and their prompts."""
    _ensure_synthetic_dataset_task(db_session)


def _ensure_synthetic_dataset_task(db_session: Session) -> None:
    """Create the Synthetic Dataset Generation system task if it doesn't exist."""
    # 1. Create task if missing
    existing = db_session.get(DatabaseTask, SYNTHETIC_DATASET_TASK_ID)
    if not existing:
        logger.info(f"Creating system task: {SYNTHETIC_DATASET_TASK_NAME}")
        db_task = DatabaseTask(
            id=SYNTHETIC_DATASET_TASK_ID,
            name=SYNTHETIC_DATASET_TASK_NAME,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            is_agentic=True,
            is_system_task=True,
            is_autocreated=False,
        )
        db_session.add(db_task)
        db_session.commit()

    # 2. Seed prompts (idempotent — check production tag first)
    _ensure_prompt_with_production_tag(
        db_session,
        prompt_name=SYNTHETIC_DATA_SYSTEM_PROMPT_NAME,
        role=MessageRole.SYSTEM,
        content=SYSTEM_PROMPT_TEMPLATE,
    )
    _ensure_prompt_with_production_tag(
        db_session,
        prompt_name=SYNTHETIC_DATA_INITIAL_USER_PROMPT_NAME,
        role=MessageRole.USER,
        content=INITIAL_GENERATION_USER_PROMPT_TEMPLATE,
    )
    _ensure_prompt_with_production_tag(
        db_session,
        prompt_name=SYNTHETIC_DATA_CONVERSATION_USER_PROMPT_NAME,
        role=MessageRole.USER,
        content=CONVERSATION_USER_PROMPT_TEMPLATE,
    )


def _ensure_prompt_with_production_tag(
    db_session: Session,
    prompt_name: str,
    role: MessageRole,
    content: str,
) -> None:
    """Create prompt version 1 and tag it 'production', only if no production tag exists."""
    # Check if production tag already exists
    existing_tag = (
        db_session.query(DatabaseAgenticPromptVersionTag)
        .filter(
            DatabaseAgenticPromptVersionTag.task_id == SYNTHETIC_DATASET_TASK_ID,
            DatabaseAgenticPromptVersionTag.name == prompt_name,
            DatabaseAgenticPromptVersionTag.tag == PRODUCTION_TAG,
        )
        .first()
    )
    if existing_tag:
        # Prompt is already seeded; update content if the template has changed
        existing_prompt = db_session.get(
            DatabaseAgenticPrompt,
            (SYNTHETIC_DATASET_TASK_ID, prompt_name, 1),
        )
        if existing_prompt:
            stored_content = existing_prompt.messages[0].get("content", "") if existing_prompt.messages else ""
            if stored_content != content:
                existing_prompt.messages = [OpenAIMessage(role=role, content=content).model_dump()]
                db_session.commit()
                logger.info(f"Updated content for prompt '{prompt_name}' (template changed)")
        return

    # Check if version 1 already exists
    existing_prompt = db_session.get(
        DatabaseAgenticPrompt,
        (SYNTHETIC_DATASET_TASK_ID, prompt_name, 1),
    )
    if not existing_prompt:
        # Insert the prompt record directly (bypasses Pydantic validation so
        # EMPTY_MODEL_PROVIDER / EMPTY_MODEL_NAME can be stored as plain strings)
        message = OpenAIMessage(role=role, content=content)
        db_prompt = DatabaseAgenticPrompt(
            task_id=SYNTHETIC_DATASET_TASK_ID,
            name=prompt_name,
            version=1,
            model_name=EMPTY_MODEL_NAME,
            model_provider=EMPTY_MODEL_PROVIDER,
            messages=[message.model_dump()],
            variables=[],
        )
        db_session.add(db_prompt)
        try:
            db_session.flush()
        except IntegrityError:
            db_session.rollback()
            # Prompt already exists (race condition) — fall through to create the tag

    # Add the production tag
    tag = DatabaseAgenticPromptVersionTag(
        task_id=SYNTHETIC_DATASET_TASK_ID,
        name=prompt_name,
        version=1,
        tag=PRODUCTION_TAG,
    )
    db_session.add(tag)
    try:
        db_session.commit()
        logger.info(
            f"Seeded prompt '{prompt_name}' with production tag for system task"
        )
    except IntegrityError:
        db_session.rollback()
