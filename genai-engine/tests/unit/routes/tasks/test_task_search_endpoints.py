import random

import pytest

from arthur_common.models.enums import PaginationSortMethod
from tests.clients.base_test_client import GenaiEngineTestClientBase


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

    sc, task_resp_base = client.search_tasks(sort=sort, page=page, page_size=page_size)
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
        assert set([t.id for t in task_resp.tasks]) == set(request_ids)


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
