import random
import uuid
from datetime import datetime, timedelta

import pytest
from arthur_common.models.enums import PaginationSortMethod

from db_models import DatabaseTask
from db_models.telemetry_models import DatabaseTraceMetadata
from schemas.enums import TaskSortField
from tests.clients.base_test_client import (
    GenaiEngineTestClientBase,
    override_get_db_session,
)
from utils.constants import DEFAULT_ORG_ID


def _set_task_created_at(db_session, task_id, created_at):
    db_session.query(DatabaseTask).filter(DatabaseTask.id == task_id).update(
        {"created_at": created_at, "updated_at": created_at},
    )
    db_session.commit()


def _add_trace_for_task(db_session, task_id, end_time, org_id=DEFAULT_ORG_ID):
    trace = DatabaseTraceMetadata(
        trace_id=str(uuid.uuid4()),
        task_id=task_id,
        org_id=org_id,
        session_id=None,
        user_id=None,
        span_count=1,
        start_time=end_time,
        end_time=end_time,
        created_at=end_time,
        updated_at=end_time,
        input_content="in",
        output_content="out",
    )
    db_session.add(trace)
    db_session.commit()
    return trace.trace_id


@pytest.mark.unit_tests
@pytest.mark.parametrize(
    ("sort", "page", "page_size", "filter_tasks", "expected_count"),
    [
        [None, None, None, False, 10],
        [None, None, 5, False, 5],
        [None, 1, None, False, 10],
        [PaginationSortMethod.ASCENDING, None, None, False, 10],
        [None, None, None, False, 10],
    ],
)
def test_search_tasks(
    sort: PaginationSortMethod,
    page: int,
    page_size: int,
    filter_tasks: bool,
    expected_count: int,
    client: GenaiEngineTestClientBase,
):
    request_ids = []
    for i in range(20):
        sc, task = client.create_task()
        assert sc == 200
        request_ids.append(task.id)

    # Filter by task IDs we created to isolate test from system tasks and ensure proper pagination
    sc, task_resp_base = client.search_tasks(
        sort=sort, page=page, page_size=page_size, task_ids=request_ids
    )
    assert sc == 200
    assert len(task_resp_base.tasks) == expected_count

    # Verify all tasks have is_agentic field (should default to False)
    for task in task_resp_base.tasks:
        assert hasattr(task, "is_agentic")
        # Since we didn't specify is_agentic in create_task, they should all be False
        assert task.is_agentic == False

    if page:
        sc, task_resp = client.search_tasks(
            sort=sort,
            page=page + 1,
            page_size=page_size,
            task_ids=request_ids,
        )
        assert sc == 200

        page_1 = [t.id for t in task_resp_base.tasks]
        page_2 = [t.id for t in task_resp.tasks]
        assert len(set(page_1).intersection(set(page_2))) == 0

    if page_size:
        assert len(task_resp_base.tasks) <= page_size

    base_tasks = task_resp_base.tasks
    t = base_tasks[0]
    if sort == PaginationSortMethod.DESCENDING or sort is None:
        for i in base_tasks[1:]:
            assert i.created_at < t.created_at
            t = i
    elif sort == PaginationSortMethod.ASCENDING:
        for i in base_tasks[1:]:
            assert i.created_at > t.created_at
            t = i

    if filter_tasks:
        sample = random.sample(request_ids, 5)
        sc, task_resp = client.search_tasks(
            sort=sort,
            page=page,
            page_size=page_size,
            task_ids=sample,
        )
        assert len(task_resp.tasks) == 5
        assert set([t.id for t in task_resp.tasks]) == set(sample)


@pytest.mark.unit_tests
@pytest.mark.parametrize(
    ("name", "expected_count"),
    [
        ["", 50],
        ["4", 11],
        ["0", 1],
        ["14", 1],
        ["1", 11],
    ],
)
def test_search_task_name(
    name: str,
    expected_count: int,
    client: GenaiEngineTestClientBase,
):
    unique_prefix = str(random.random()) + "test_search_task_name_"
    for i in range(50):
        client.create_task(name=unique_prefix + str(i))

    task_name = unique_prefix + name
    task_name = task_name.upper()

    sc, task_resp = client.search_tasks(task_name=task_name, page_size=50)

    print(task_resp.tasks)
    assert sc == 200

    assert len(task_resp.tasks) == expected_count
    assert task_resp.count == expected_count


@pytest.mark.unit_tests
def test_search_tasks_by_is_agentic_filter(client: GenaiEngineTestClientBase):
    """Test searching tasks specifically by is_agentic filter"""
    unique_prefix = str(random.random()) + "agentic_test_"

    # Create a mix of agentic and non-agentic tasks
    agentic_task_ids = []
    non_agentic_task_ids = []

    for i in range(5):
        # Create agentic tasks
        sc, task = client.create_task(
            name=f"{unique_prefix}agentic_{i}",
            is_agentic=True,
        )
        assert sc == 200
        agentic_task_ids.append(task.id)

        # Create non-agentic tasks
        sc, task = client.create_task(
            name=f"{unique_prefix}non_agentic_{i}",
            is_agentic=False,
        )
        assert sc == 200
        non_agentic_task_ids.append(task.id)

    # Test 1: Search for only agentic tasks
    sc, agentic_response = client.search_tasks(is_agentic=True, page_size=50)
    assert sc == 200

    # Filter to only our test tasks
    found_agentic = [
        task for task in agentic_response.tasks if task.id in agentic_task_ids
    ]
    assert len(found_agentic) == 5

    for task in found_agentic:
        assert task.is_agentic == True
        assert task.id in agentic_task_ids

    # Test 2: Search for only non-agentic tasks
    sc, non_agentic_response = client.search_tasks(is_agentic=False, page_size=50)
    assert sc == 200

    # Filter to only our test tasks
    found_non_agentic = [
        task for task in non_agentic_response.tasks if task.id in non_agentic_task_ids
    ]
    assert len(found_non_agentic) == 5

    for task in found_non_agentic:
        assert task.is_agentic == False
        assert task.id in non_agentic_task_ids

    # Test 3: Search without is_agentic filter should return both types
    sc, all_response = client.search_tasks(page_size=50)
    assert sc == 200

    all_our_tasks = [
        task
        for task in all_response.tasks
        if task.id in agentic_task_ids + non_agentic_task_ids
    ]
    assert len(all_our_tasks) == 10


@pytest.mark.unit_tests
def test_search_tasks_agentic_with_other_filters(client: GenaiEngineTestClientBase):
    """Test combining is_agentic filter with other search filters"""
    unique_prefix = str(random.random()) + "combined_test_"

    # Create tasks with specific names
    agentic_task_ids = []
    for i in range(3):
        sc, task = client.create_task(
            name=f"{unique_prefix}special_agentic_{i}",
            is_agentic=True,
        )
        assert sc == 200
        agentic_task_ids.append(task.id)

    # Also create some non-agentic tasks with similar names
    for i in range(2):
        sc, task = client.create_task(
            name=f"{unique_prefix}special_non_agentic_{i}",
            is_agentic=False,
        )
        assert sc == 200

    # Test combining name search with is_agentic filter
    sc, response = client.search_tasks(
        task_name=f"{unique_prefix}special",
        is_agentic=True,
        page_size=50,
    )
    assert sc == 200

    # Should only find agentic tasks with "special" in the name
    found_tasks = [task for task in response.tasks if task.id in agentic_task_ids]
    assert len(found_tasks) == 3

    for task in found_tasks:
        assert task.is_agentic == True
        assert "special" in task.name.lower()


@pytest.mark.unit_tests
def test_search_tasks_archived_flags(client: GenaiEngineTestClientBase):
    """Test that only_archived and include_archived correctly filter archived tasks."""
    unique_prefix = str(random.random()) + "archived_search_test_"

    task_ids = []
    for i in range(3):
        sc, task = client.create_task(name=f"{unique_prefix}{i}")
        assert sc == 200
        task_ids.append(task.id)

    archived_ids = task_ids[:2]
    active_ids = task_ids[2:]

    for task_id in archived_ids:
        sc = client.delete_task(task_id)
        assert sc == 204

    # Default search returns only active tasks
    sc, resp = client.search_tasks(task_ids=task_ids, page_size=50)
    assert sc == 200
    assert set(t.id for t in resp.tasks) == set(active_ids)

    # include_archived=True returns active and archived tasks
    sc, resp = client.search_tasks(
        task_ids=task_ids, page_size=50, include_archived=True
    )
    assert sc == 200
    assert set(t.id for t in resp.tasks) == set(task_ids)

    # only_archived=True returns only archived tasks
    sc, resp = client.search_tasks(task_ids=task_ids, page_size=50, only_archived=True)
    assert sc == 200
    assert set(t.id for t in resp.tasks) == set(archived_ids)
    assert all(t.is_archived for t in resp.tasks)

    # only_archived takes precedence when both flags are True
    sc, resp = client.search_tasks(
        task_ids=task_ids, page_size=50, only_archived=True, include_archived=True
    )
    assert sc == 200
    assert set(t.id for t in resp.tasks) == set(archived_ids)


@pytest.mark.unit_tests
def test_search_tasks_agentic_with_pagination(client: GenaiEngineTestClientBase):
    """Test is_agentic filter with pagination"""
    unique_prefix = str(random.random()) + "pagination_test_"

    # Create more agentic tasks than page size
    agentic_task_ids = []
    for i in range(7):  # More than our page size of 3
        sc, task = client.create_task(
            name=f"{unique_prefix}agentic_{i}",
            is_agentic=True,
        )
        assert sc == 200
        agentic_task_ids.append(task.id)

    # Test first page
    sc, page1_response = client.search_tasks(is_agentic=True, page=0, page_size=3)
    assert sc == 200

    page1_our_tasks = [
        task for task in page1_response.tasks if task.id in agentic_task_ids
    ]
    assert len(page1_our_tasks) <= 3

    # Test second page
    sc, page2_response = client.search_tasks(is_agentic=True, page=1, page_size=3)
    assert sc == 200

    page2_our_tasks = [
        task for task in page2_response.tasks if task.id in agentic_task_ids
    ]

    # Ensure no overlap between pages
    page1_ids = [task.id for task in page1_our_tasks]
    page2_ids = [task.id for task in page2_our_tasks]
    assert len(set(page1_ids).intersection(set(page2_ids))) == 0

    # All found tasks should be agentic
    for task in page1_our_tasks + page2_our_tasks:
        assert task.is_agentic == True


@pytest.mark.unit_tests
def test_search_tasks_last_active_filter(client: GenaiEngineTestClientBase):
    """last_active filter returns tasks with recent trace activity even when
    the task record itself is old, and excludes stale / trace-less tasks."""
    db_session = override_get_db_session()
    now = datetime.now()
    prefix = str(random.random()) + "last_active_"

    sc, recent = client.create_task(name=f"{prefix}recent")
    assert sc == 200
    sc, stale = client.create_task(name=f"{prefix}stale")
    assert sc == 200
    sc, traceless = client.create_task(name=f"{prefix}traceless")
    assert sc == 200

    task_ids = [recent.id, stale.id, traceless.id]
    trace_ids = []
    try:
        # All three tasks are old records.
        for tid in task_ids:
            _set_task_created_at(db_session, tid, now - timedelta(days=30))
        # Only `recent` has a trace inside the 7-day window.
        trace_ids.append(
            _add_trace_for_task(db_session, recent.id, now - timedelta(days=1)),
        )
        trace_ids.append(
            _add_trace_for_task(db_session, stale.id, now - timedelta(days=60)),
        )

        sc, resp = client.search_tasks(
            task_ids=task_ids,
            last_active_start_time=(now - timedelta(days=7)).isoformat(),
            page_size=50,
        )
        assert sc == 200
        assert resp.count == 1
        assert [t.id for t in resp.tasks] == [recent.id]

        # Without the filter, all three (including trace-less) are returned.
        sc, resp = client.search_tasks(task_ids=task_ids, page_size=50)
        assert sc == 200
        assert set(t.id for t in resp.tasks) == set(task_ids)
    finally:
        if trace_ids:
            db_session.query(DatabaseTraceMetadata).filter(
                DatabaseTraceMetadata.trace_id.in_(trace_ids),
            ).delete(synchronize_session=False)
            db_session.commit()


@pytest.mark.unit_tests
def test_search_tasks_sort_field_last_active(client: GenaiEngineTestClientBase):
    """sort_field=last_active orders by most recent trace activity, with
    trace-less tasks pushed to the end."""
    db_session = override_get_db_session()
    now = datetime.now()
    prefix = str(random.random()) + "sort_active_"

    sc, recent = client.create_task(name=f"{prefix}recent")
    assert sc == 200
    sc, older = client.create_task(name=f"{prefix}older")
    assert sc == 200
    sc, traceless = client.create_task(name=f"{prefix}traceless")
    assert sc == 200

    task_ids = [recent.id, older.id, traceless.id]
    trace_ids = []
    try:
        trace_ids.append(
            _add_trace_for_task(db_session, recent.id, now - timedelta(days=1)),
        )
        trace_ids.append(
            _add_trace_for_task(db_session, older.id, now - timedelta(days=10)),
        )

        sc, resp = client.search_tasks(
            task_ids=task_ids,
            sort_field=TaskSortField.LAST_ACTIVE.value,
            sort=PaginationSortMethod.DESCENDING,
            page_size=50,
        )
        assert sc == 200
        assert [t.id for t in resp.tasks] == [recent.id, older.id, traceless.id]

        sc, resp = client.search_tasks(
            task_ids=task_ids,
            sort_field=TaskSortField.LAST_ACTIVE.value,
            sort=PaginationSortMethod.ASCENDING,
            page_size=50,
        )
        assert sc == 200
        assert [t.id for t in resp.tasks] == [older.id, recent.id, traceless.id]
    finally:
        if trace_ids:
            db_session.query(DatabaseTraceMetadata).filter(
                DatabaseTraceMetadata.trace_id.in_(trace_ids),
            ).delete(synchronize_session=False)
            db_session.commit()


@pytest.mark.unit_tests
def test_search_tasks_sort_field_name(client: GenaiEngineTestClientBase):
    """sort_field=name orders alphabetically server-side."""
    prefix = str(random.random()) + "sort_name_"
    sc, charlie = client.create_task(name=f"{prefix}charlie")
    assert sc == 200
    sc, alpha = client.create_task(name=f"{prefix}alpha")
    assert sc == 200
    sc, bravo = client.create_task(name=f"{prefix}bravo")
    assert sc == 200

    task_ids = [charlie.id, alpha.id, bravo.id]

    sc, resp = client.search_tasks(
        task_ids=task_ids,
        sort_field=TaskSortField.NAME.value,
        sort=PaginationSortMethod.ASCENDING,
        page_size=50,
    )
    assert sc == 200
    assert [t.id for t in resp.tasks] == [alpha.id, bravo.id, charlie.id]
