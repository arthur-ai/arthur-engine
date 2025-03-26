from typing import Generator

import pytest
from tests.clients.base_test_client import GenaiEngineTestClientBase
from tests.clients.integration_test_client import get_genai_engine_test_client


@pytest.fixture(scope="module", autouse=True)
def client() -> Generator[GenaiEngineTestClientBase, None, None]:
    yield get_genai_engine_test_client()


@pytest.fixture
def create_task(client: GenaiEngineTestClientBase, request: pytest.FixtureRequest):
    status_code, task = client.create_task()
    assert status_code == 200
    yield task
    if request.keywords.node.callspec.params.get("delete_task", False):
        client.delete_task(task.id)
