"""
Utility functions for task-related operations.
"""

from typing import Optional

from sqlalchemy.orm import Session

from db_models import DatabaseTask
from utils.constants import SYSTEM_TASK_NAME

# Module-level cache for system task ID
_system_task_id_cache: Optional[str] = None


def get_system_task_id(db_session: Session) -> str:
    """
    Get the system task ID for unregistered traces (cached at module level).

    Args:
        db_session: Database session to query with

    Returns:
        str: System task ID

    Raises:
        RuntimeError: If system task not found in database
    """
    global _system_task_id_cache

    if _system_task_id_cache is not None:
        return _system_task_id_cache

    system_task = (
        db_session.query(DatabaseTask)
        .filter(
            DatabaseTask.is_system_task == True,
            DatabaseTask.name == SYSTEM_TASK_NAME,
        )
        .first()
    )
    if not system_task:
        raise RuntimeError(
            f"System task '{SYSTEM_TASK_NAME}' not found. "
            "Ensure database migrations have been run."
        )

    _system_task_id_cache = system_task.id
    return _system_task_id_cache


def clear_system_task_cache():
    """Clear the cached system task ID. Useful for testing."""
    global _system_task_id_cache
    _system_task_id_cache = None
