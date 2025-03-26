import os
import re

import pytest
from tests.clients.base_test_client import (
    MASTER_KEY_AUTHORIZED_HEADERS,
    GenaiEngineTestClientBase,
)
from utils import utils


@pytest.mark.parametrize(
    ("environment"),
    [
        pytest.param("test", marks=pytest.mark.unit_tests),
        pytest.param(
            "azure",
            marks=pytest.mark.azure_live,
        ),
        pytest.param(
            "aws",
            marks=pytest.mark.aws_live,
        ),
    ],
)
def test_config_update_get(environment, client: GenaiEngineTestClientBase):
    status_code, task_response = client.create_task("TestTask123")
    task_id = task_response.id
    new_config = {"chat_task_id": task_id}

    document_config = None
    if environment == "azure":
        document_config = {
            "environment": "azure",
            "connection_string": os.environ["AZURE_STORAGE_CONNECTION_STRING"],
            "container_name": os.environ["AZURE_STORAGE_CONTAINER_NAME"],
        }
        headers = MASTER_KEY_AUTHORIZED_HEADERS
    elif environment == "aws":
        document_config = {
            "environment": "aws",
            "bucket_name": os.environ["AWS_BUCKET_NAME"],
            "assumable_role_arn": os.environ["AWS_ASSUMABLE_ROLE_ARN"],
        }
        headers = MASTER_KEY_AUTHORIZED_HEADERS
    else:
        headers = {"Authorization": "Bearer admin_0"}

    if document_config is not None:
        new_config["document_storage_configuration"] = document_config
    config_update_response = client.update_configs(
        new_config,
        headers=headers,
    )

    assert config_update_response.status_code == 200
    assert config_update_response.json()["chat_task_id"] == task_id

    _, task2 = client.create_task("TestTask456")
    task_id_2 = task2.id
    updated_config = {"chat_task_id": task_id_2}
    config_update2_response = client.update_configs(
        updated_config,
        headers=headers,
    )

    assert config_update2_response.status_code == 200
    assert config_update2_response.json()["chat_task_id"] == task_id_2

    get_configs_response = client.get_configs(headers=headers)
    assert get_configs_response.status_code == 200
    configs = get_configs_response.json()
    assert configs["chat_task_id"] == task_id_2

    doc_storage_config_response = configs["document_storage_configuration"]
    if document_config is not None and document_config["environment"] == "aws":
        assert (
            doc_storage_config_response["bucket_name"] == document_config["bucket_name"]
        )
    if document_config is not None and document_config["environment"] == "azure":
        assert (
            doc_storage_config_response["container_name"]
            == document_config["container_name"]
        )
        assert "connection_string" not in doc_storage_config_response


@pytest.mark.unit_tests
def test_version_read_env_var_not_present():
    version = utils.get_genai_engine_version()
    semver_regex = r"^\d+\.\d+\.\d+$"
    assert (
        re.match(semver_regex, version) is not None
    ), "Version is not a valid semantic version"
