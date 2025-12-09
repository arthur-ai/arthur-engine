import random
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Generator

import pytest

from db_models.llm_eval_models import DatabaseLLMEval, DatabaseLLMEvalVersionTag
from db_models.task_models import DatabaseTask
from tests.clients.base_test_client import override_get_db_session


@dataclass
class TaskWithLLMEval:
    """Container for task and LLM eval data created directly in the database"""

    task_id: str
    task_name: str
    eval_name: str
    eval_data: dict
    created_at: datetime


@pytest.fixture
def task_with_llm_eval_in_db() -> Generator[TaskWithLLMEval, None, None]:
    """
    Create an agentic task and LLM eval directly in the database.
    Cleans up both objects after the test completes.
    """
    db_session = override_get_db_session()

    # Create the task directly in DB
    task_id = str(uuid.uuid4())
    task_name = f"agentic_task_{random.random()}"
    # Use a fixed date to avoid flaky tests with datetime-based version lookups
    fixed_date = datetime(2024, 1, 15, 12, 0, 0)

    db_task = DatabaseTask(
        id=task_id,
        name=task_name,
        created_at=fixed_date,
        updated_at=fixed_date,
        is_agentic=True,
    )
    db_session.add(db_task)
    db_session.commit()

    # Create the LLM eval directly in DB
    eval_name = "test_llm_eval"
    eval_data = {
        "model_name": "gpt-4o",
        "model_provider": "openai",
        "instructions": "Test instructions",
    }

    db_llm_eval = DatabaseLLMEval(
        task_id=task_id,
        name=eval_name,
        model_name=eval_data["model_name"],
        model_provider=eval_data["model_provider"],
        instructions=eval_data["instructions"],
        variables=[],
        version=1,
        created_at=fixed_date,
    )
    db_session.add(db_llm_eval)
    db_session.commit()

    yield TaskWithLLMEval(
        task_id=task_id,
        task_name=task_name,
        eval_name=eval_name,
        eval_data=eval_data,
        created_at=fixed_date,
    )

    # Cleanup: delete tags first, then LLM eval (due to FK constraint), then the task
    db_session.query(DatabaseLLMEvalVersionTag).filter(
        DatabaseLLMEvalVersionTag.task_id == task_id,
        DatabaseLLMEvalVersionTag.name == eval_name,
    ).delete()
    db_session.query(DatabaseLLMEval).filter(
        DatabaseLLMEval.task_id == task_id,
        DatabaseLLMEval.name == eval_name,
    ).delete()
    db_session.query(DatabaseTask).filter(DatabaseTask.id == task_id).delete()
    db_session.commit()
    db_session.close()
