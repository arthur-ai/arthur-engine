from copy import deepcopy
from typing import Generator

import pytest
from tests.clients.base_test_client import GenaiEngineTestClientBase
from tests.clients.unit_test_client import get_genai_engine_test_client


@pytest.fixture(scope="module", autouse=True)
def client() -> Generator[GenaiEngineTestClientBase, None, None]:
    yield get_genai_engine_test_client()


@pytest.fixture
def changed_user_client(
    request: pytest.FixtureRequest,
    client: GenaiEngineTestClientBase,
):
    previous_header = deepcopy(client.authorized_chat_headers)
    client.authorized_chat_headers = {
        "Authorization": f"Bearer {request.keywords.node.callspec.params.get('user_role')}",
    }
    yield client
    client.authorized_chat_headers = previous_header
