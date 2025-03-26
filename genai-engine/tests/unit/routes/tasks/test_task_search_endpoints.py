import random

import pytest
from schemas.enums import PaginationSortMethod
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
