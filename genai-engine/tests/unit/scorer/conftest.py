from typing import Generator

import pytest
from scorer.llm_client import LLMExecutor


@pytest.fixture
def openai_executor(
    request: pytest.FixtureRequest,
) -> Generator[LLMExecutor, None, None]:
    llm_config = request.param
    llm_client = LLMExecutor(llm_config)
    yield llm_client
