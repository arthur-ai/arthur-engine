import pytest
from tests.clients.base_test_client import GenaiEngineTestClientBase


@pytest.mark.unit_tests
@pytest.mark.parametrize(
    "user_role",
    ["admin_0", "auditor_0"],
)
def test_chat_default_task(
    user_role: str,
    changed_user_client: GenaiEngineTestClientBase,
):
    client = changed_user_client
    _, task_response = client.create_task("ArthurChat")
    new_config = {"chat_task_id": task_response.id}
    client.update_configs(
        new_config,
        headers=client.authorized_org_admin_api_key_headers,
    )
    status_code, response = client.get_chat_default_task()
    assert status_code == 200
    assert response.task_id == task_response.id


@pytest.mark.unit_tests
@pytest.mark.parametrize(
    "user_role",
    ["admin_0"],
)
def test_update_chat_default_task(
    user_role: str,
    changed_user_client: GenaiEngineTestClientBase,
):
    client = changed_user_client
    _, first_task_response = client.create_task("ArthurChat")
    _, second_task_response = client.create_task("ArthurChat2")
    status_code, first_response = client.update_chat_default_task(
        first_task_response.id,
    )
    assert status_code == 200
    assert first_response.task_id == first_task_response.id
    status_code, second_response = client.update_chat_default_task(
        second_task_response.id,
    )
    assert status_code == 200
    assert second_response.task_id == second_task_response.id
    assert first_response.task_id != second_response.task_id


@pytest.mark.unit_tests
@pytest.mark.parametrize(
    "user_role",
    ["admin_0"],
)
def test_update_chat_default_task_with_invalid_task_id(
    user_role: str,
    changed_user_client: GenaiEngineTestClientBase,
):
    client = changed_user_client
    status_code, _ = client.update_chat_default_task("invalid_task_id")
    assert status_code == 404
