import logging
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from db_models.agent_polling_models import DatabaseTaskPollingState

logger = logging.getLogger(__name__)


class TaskPollingStateRepository:
    """Repository for task polling state operations.

    No failure-tracking methods. Errors are logged for observability
    but do not affect polling state.
    """

    def __init__(self, db_session: Session):
        self.db_session = db_session

    def get_or_create(self, task_id: str) -> DatabaseTaskPollingState:
        """Get existing polling state or create a new one for the task."""
        state = (
            self.db_session.query(DatabaseTaskPollingState)
            .filter(DatabaseTaskPollingState.task_id == task_id)
            .first()
        )
        if state:
            return state

        now = datetime.now()
        state = DatabaseTaskPollingState(
            task_id=task_id,
            last_fetched=None,
            created_at=now,
            updated_at=now,
        )
        self.db_session.add(state)
        self.db_session.commit()
        return state

    def update_last_fetched(self, task_id: str, timestamp: datetime) -> None:
        """Update the last_fetched timestamp for a task."""
        state = self.get_or_create(task_id)
        state.last_fetched = timestamp
        state.updated_at = datetime.now()
        self.db_session.commit()

    def get_by_task_id(self, task_id: str) -> Optional[DatabaseTaskPollingState]:
        """Get polling state by task ID, or None if not found."""
        return (
            self.db_session.query(DatabaseTaskPollingState)
            .filter(DatabaseTaskPollingState.task_id == task_id)
            .first()
        )
