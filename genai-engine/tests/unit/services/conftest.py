from typing import Generator

import pytest

from tests.clients.base_test_client import GenaiEngineTestClientBase
from tests.clients.unit_test_client import get_genai_engine_test_client


@pytest.fixture(scope="module", autouse=True)
def client() -> Generator[GenaiEngineTestClientBase, None, None]:
    yield get_genai_engine_test_client()
