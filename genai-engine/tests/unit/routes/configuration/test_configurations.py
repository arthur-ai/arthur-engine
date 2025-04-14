import re

import pytest
from tests.clients.base_test_client import (
    MASTER_KEY_AUTHORIZED_HEADERS,
    GenaiEngineTestClientBase,
)
from utils import utils


@pytest.fixture
def config_setup(client: GenaiEngineTestClientBase):
    headers = MASTER_KEY_AUTHORIZED_HEADERS
    current_config = client.get_configs(headers=headers).json()
    yield
    client.update_configs(current_config, headers=headers)


@pytest.mark.unit_tests
def test_config_update_get(client: GenaiEngineTestClientBase, config_setup):
    headers = MASTER_KEY_AUTHORIZED_HEADERS

    status_code, task_response = client.create_task("TestTask123")
    task_id = task_response.id
    new_config = {"max_llm_rules_per_task_count": 1}

    config_update_response = client.update_configs(
        new_config,
        headers=headers,
    )

    assert config_update_response.status_code == 200
    assert config_update_response.json()["max_llm_rules_per_task_count"] == 1

    _, task2 = client.create_task("TestTask456")
    task_id_2 = task2.id
    updated_config = {"max_llm_rules_per_task_count": 2}
    config_update2_response = client.update_configs(
        updated_config,
        headers=headers,
    )

    assert config_update2_response.status_code == 200
    assert config_update2_response.json()["max_llm_rules_per_task_count"] == 2


@pytest.mark.unit_tests
def test_version_read_env_var_not_present():
    version = utils.get_genai_engine_version()
    semver_regex = r"^\d+\.\d+\.\d+$"
    assert (
        re.match(semver_regex, version) is not None
    ), "Version is not a valid semantic version"
