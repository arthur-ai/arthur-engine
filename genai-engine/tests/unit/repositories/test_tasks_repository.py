import uuid
from datetime import datetime, timedelta

import pytest
from arthur_common.models.enums import PaginationSortMethod

from db_models import DatabaseTask
from dependencies import get_application_config
from repositories.metrics_repository import MetricRepository
from repositories.rules_repository import RuleRepository
from repositories.tasks_repository import TaskRepository
from schemas.enums import TaskSortField
from tests.clients.base_test_client import override_get_db_session
from utils.constants import DEFAULT_ORG_ID


def _build_task_repo(db_session) -> TaskRepository:
    application_config = get_application_config(session=db_session)
    rules_repo = RuleRepository(db_session)
    metric_repo = MetricRepository(db_session)
    return TaskRepository(db_session, rules_repo, metric_repo, application_config)


def _insert_task(
    db_session, name: str, created_at: datetime, updated_at: datetime
) -> str:
    task_id = str(uuid.uuid4())
    db_session.add(
        DatabaseTask(
            id=task_id,
            name=name,
            created_at=created_at,
            updated_at=updated_at,
            is_agentic=False,
            is_autocreated=False,
            is_system_task=False,
            org_id=DEFAULT_ORG_ID,
        ),
    )
    db_session.commit()
    return task_id


@pytest.mark.unit_tests
def test_query_tasks_recently_updated_uses_updated_at():
    """Regression for UP-4693.

    With mode "Recently updated", a task created outside the time window but
    updated inside it must be returned, while a task updated outside the window
    must be excluded. "Recently created" keeps filtering on created_at.
    """
    db_session = override_get_db_session()
    repo = _build_task_repo(db_session)

    now = datetime.now()
    window_start = now - timedelta(days=7)

    prefix = f"up4693_{uuid.uuid4()}_"

    # Created a month ago, updated 16 hours ago -> inside the "updated" window.
    stale_created_fresh_updated = _insert_task(
        db_session,
        name=f"{prefix}stale_created_fresh_updated",
        created_at=now - timedelta(days=30),
        updated_at=now - timedelta(hours=16),
    )
    # Created a month ago, updated a month ago -> outside the "updated" window.
    stale_updated = _insert_task(
        db_session,
        name=f"{prefix}stale_updated",
        created_at=now - timedelta(days=30),
        updated_at=now - timedelta(days=30),
    )
    # Created 2 days ago (inside "created" window), updated 2 days ago.
    fresh_created = _insert_task(
        db_session,
        name=f"{prefix}fresh_created",
        created_at=now - timedelta(days=2),
        updated_at=now - timedelta(days=2),
    )

    all_ids = [stale_created_fresh_updated, stale_updated, fresh_created]

    try:
        # Recently updated: both range bounds filter on updated_at.
        updated_tasks, _ = repo.query_tasks(
            ids=all_ids,
            sort_field=TaskSortField.UPDATED,
            start_time=window_start,
            end_time=now,
            page_size=None,
        )
        updated_result_ids = {t.id for t in updated_tasks}
        assert stale_created_fresh_updated in updated_result_ids
        assert fresh_created in updated_result_ids
        assert stale_updated not in updated_result_ids

        # Recently created: filters on created_at instead.
        created_tasks, _ = repo.query_tasks(
            ids=all_ids,
            sort_field=TaskSortField.CREATED,
            start_time=window_start,
            end_time=now,
            page_size=None,
        )
        created_result_ids = {t.id for t in created_tasks}
        assert fresh_created in created_result_ids
        assert stale_created_fresh_updated not in created_result_ids
        assert stale_updated not in created_result_ids

        # Default (unset) mode preserves created_at behavior.
        default_tasks, _ = repo.query_tasks(
            ids=all_ids,
            start_time=window_start,
            end_time=now,
            page_size=None,
        )
        assert {t.id for t in default_tasks} == created_result_ids
    finally:
        for task_id in all_ids:
            repo.delete_task(task_id=task_id)


@pytest.mark.unit_tests
def test_query_tasks_recently_updated_orders_by_updated_at():
    """Ordering must follow the resolved column so recently-updated old tasks
    surface at the top of a descending sort (matching the pagination fix)."""
    db_session = override_get_db_session()
    repo = _build_task_repo(db_session)

    now = datetime.now()
    prefix = f"up4693_order_{uuid.uuid4()}_"

    # Older created_at but newest updated_at.
    recently_updated = _insert_task(
        db_session,
        name=f"{prefix}recently_updated",
        created_at=now - timedelta(days=30),
        updated_at=now - timedelta(hours=1),
    )
    # Newest created_at but older updated_at.
    recently_created = _insert_task(
        db_session,
        name=f"{prefix}recently_created",
        created_at=now - timedelta(hours=2),
        updated_at=now - timedelta(days=10),
    )

    all_ids = [recently_updated, recently_created]

    try:
        tasks, _ = repo.query_tasks(
            ids=all_ids,
            sort=PaginationSortMethod.DESCENDING,
            sort_field=TaskSortField.UPDATED,
            page_size=None,
        )
        ordered_ids = [t.id for t in tasks]
        assert ordered_ids == [recently_updated, recently_created]
    finally:
        for task_id in all_ids:
            repo.delete_task(task_id=task_id)
