import posixpath
import re

import pytest

from services.chatbot.api_call_service import ApiCallService
from tests.clients.base_test_client import app
from utils.llm_tool_functions import (
    ALLOWED_PATH_PATTERNS,
    build_condensed_index,
)


def replace_path_params(path: str) -> str:
    return posixpath.normpath(re.sub(r"\{[^}]+\}", "test", path))


def is_allowed(path: str) -> bool:
    if not ALLOWED_PATH_PATTERNS:
        build_condensed_index(app.openapi())

    concrete = replace_path_params(path)
    return any(p.match(concrete) for p in ALLOWED_PATH_PATTERNS)


def get_allowed_paths():
    spec = app.openapi()
    return sorted(p for p in spec.get("paths", {}) if is_allowed(p))


def get_blocked_paths():
    spec = app.openapi()
    return sorted(p for p in spec.get("paths", {}) if not is_allowed(p))


@pytest.mark.unit_tests
@pytest.mark.asyncio
@pytest.mark.parametrize("path", get_allowed_paths())
async def test_allowed_paths_not_blocked(path):
    service = ApiCallService(token="test-token", base_url="http://localhost:3030")
    result = await service.call(method="GET", path=replace_path_params(path))
    assert result.status_code != 403, f"Allowed path {path} was blocked"


@pytest.mark.unit_tests
@pytest.mark.asyncio
@pytest.mark.parametrize("path", get_blocked_paths())
async def test_blocked_paths_are_rejected(path):
    service = ApiCallService(token="test-token", base_url="http://localhost:3030")
    result = await service.call(method="GET", path=replace_path_params(path))
    assert result.status_code == 403, f"Blocked path {path} was not rejected"
