import random

import pytest

from schemas.enums import PaginationSortMethod, TaskType
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

    # Verify all tasks have task_type field (should default to LLM)
    for task in task_resp_base.tasks:
        assert hasattr(task, "task_type")
        # Since we didn't specify task_type in create_task, they should all be LLM
        assert task.task_type == TaskType.LLM

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
def test_search_tasks_by_task_type_filter(client: GenaiEngineTestClientBase):
    """Test searching tasks specifically by task_type filter"""
    unique_prefix = str(random.random()) + "task_type_test_"

    # Create a mix of Agent and LLM tasks
    agent_task_ids = []
    llm_task_ids = []

    for i in range(5):
        # Create Agent tasks
        sc, task = client.create_task(
            name=f"{unique_prefix}agent_{i}",
            task_type=TaskType.AGENT,
        )
        assert sc == 200
        agent_task_ids.append(task.id)

        # Create LLM tasks
        sc, task = client.create_task(
            name=f"{unique_prefix}llm_{i}",
            task_type=TaskType.LLM,
        )
        assert sc == 200
        llm_task_ids.append(task.id)

    # Test 1: Search for only Agent tasks
    sc, agent_response = client.search_tasks(task_type=TaskType.AGENT, page_size=50)
    assert sc == 200

    # Filter to only our test tasks
    found_agent = [task for task in agent_response.tasks if task.id in agent_task_ids]
    assert len(found_agent) == 5

    for task in found_agent:
        assert task.task_type == TaskType.AGENT
        assert task.id in agent_task_ids

    # Test 2: Search for only LLM tasks
    sc, llm_response = client.search_tasks(task_type=TaskType.LLM, page_size=50)
    assert sc == 200

    # Filter to only our test tasks
    found_llm = [task for task in llm_response.tasks if task.id in llm_task_ids]
    assert len(found_llm) == 5

    for task in found_llm:
        assert task.task_type == TaskType.LLM
        assert task.id in llm_task_ids

    # Test 3: Search without task_type filter should return both types
    sc, all_response = client.search_tasks(page_size=50)
    assert sc == 200

    all_our_tasks = [
        task for task in all_response.tasks if task.id in agent_task_ids + llm_task_ids
    ]
    assert len(all_our_tasks) == 10


@pytest.mark.unit_tests
def test_search_tasks_task_type_with_other_filters(client: GenaiEngineTestClientBase):
    """Test combining task_type filter with other search filters"""
    unique_prefix = str(random.random()) + "combined_test_"

    # Create tasks with specific names
    agent_task_ids = []
    for i in range(3):
        sc, task = client.create_task(
            name=f"{unique_prefix}special_agent_{i}",
            task_type=TaskType.AGENT,
        )
        assert sc == 200
        agent_task_ids.append(task.id)

    # Also create some LLM tasks with similar names
    for i in range(2):
        sc, task = client.create_task(
            name=f"{unique_prefix}special_llm_{i}",
            task_type=TaskType.LLM,
        )
        assert sc == 200

    # Test combining name search with task_type filter
    sc, response = client.search_tasks(
        task_name=f"{unique_prefix}special",
        task_type=TaskType.AGENT,
        page_size=50,
    )
    assert sc == 200

    # Should only find Agent tasks with "special" in the name
    found_tasks = [task for task in response.tasks if task.id in agent_task_ids]
    assert len(found_tasks) == 3

    for task in found_tasks:
        assert task.task_type == TaskType.AGENT
        assert "special" in task.name.lower()


@pytest.mark.unit_tests
def test_search_tasks_task_type_with_pagination(client: GenaiEngineTestClientBase):
    """Test task_type filter with pagination"""
    unique_prefix = str(random.random()) + "pagination_test_"

    # Create more Agent tasks than page size
    agent_task_ids = []
    for i in range(7):  # More than our page size of 3
        sc, task = client.create_task(
            name=f"{unique_prefix}agent_{i}",
            task_type=TaskType.AGENT,
        )
        assert sc == 200
        agent_task_ids.append(task.id)

    # Test first page
    sc, page1_response = client.search_tasks(
        task_type=TaskType.AGENT,
        page=0,
        page_size=3,
    )
    assert sc == 200

    page1_our_tasks = [
        task for task in page1_response.tasks if task.id in agent_task_ids
    ]
    assert len(page1_our_tasks) <= 3

    # Test second page
    sc, page2_response = client.search_tasks(
        task_type=TaskType.AGENT,
        page=1,
        page_size=3,
    )
    assert sc == 200

    page2_our_tasks = [
        task for task in page2_response.tasks if task.id in agent_task_ids
    ]

    # Ensure no overlap between pages
    page1_ids = [task.id for task in page1_our_tasks]
    page2_ids = [task.id for task in page2_our_tasks]
    assert len(set(page1_ids).intersection(set(page2_ids))) == 0

    # All found tasks should be Agent type
    for task in page1_our_tasks + page2_our_tasks:
        assert task.task_type == TaskType.AGENT
