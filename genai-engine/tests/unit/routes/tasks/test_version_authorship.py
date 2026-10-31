import random

import pytest

from schemas.enums import ActorKind
from schemas.internal_schemas import User
from tests.clients.base_test_client import MASTER_API_KEY, GenaiEngineTestClientBase
from utils.constants import ON_BEHALF_OF_HEADER

PROMPT = {
    "messages": [{"role": "user", "content": "Hello, world!"}],
    "model_name": "gpt-4",
    "model_provider": "openai",
}

TRANSFORM_DEFINITION = {
    "variables": [
        {
            "variable_name": "test_variable",
            "span_name": "test-span",
            "attribute_path": "attributes.test",
            "fallback": None,
        },
    ],
}


def _save_prompt_and_get_author(
    client: GenaiEngineTestClientBase,
    headers: dict,
) -> dict:
    status_code, task = client.create_task(
        f"authorship_{random.random()}",
        is_agentic=True,
    )
    assert status_code == 200

    response = client.base_client.post(
        f"/api/v1/tasks/{task.id}/prompts/greeting",
        json=PROMPT,
        headers=headers,
    )
    assert response.status_code == 200
    saved = response.json()

    response = client.base_client.get(
        f"/api/v1/tasks/{task.id}/prompts/greeting/versions",
        headers=client.authorized_user_api_key_headers,
    )
    assert response.status_code == 200
    versions = response.json()["versions"]
    assert len(versions) == 1
    # The save response and the version list agree on the author.
    assert versions[0]["created_by"] == saved["created_by"]
    return versions[0]["created_by"]


@pytest.mark.unit_tests
def test_prompt_version_records_api_key_author(client: GenaiEngineTestClientBase):
    author = _save_prompt_and_get_author(
        client,
        client.authorized_user_api_key_headers,
    )
    assert author["kind"] == ActorKind.API_KEY.value
    # The test client's key is created with description "TestClient".
    assert author["name"] == "TestClient"


@pytest.mark.unit_tests
def test_on_behalf_of_header_is_ignored_for_api_keys(
    client: GenaiEngineTestClientBase,
):
    author = _save_prompt_and_get_author(
        client,
        {
            **client.authorized_user_api_key_headers,
            ON_BEHALF_OF_HEADER: "mallory@example.com",
        },
    )
    assert author["kind"] == ActorKind.API_KEY.value
    assert "mallory@example.com" not in (author["id"], author["name"])


@pytest.mark.unit_tests
def test_master_key_without_header_records_master_key(
    client: GenaiEngineTestClientBase,
):
    author = _save_prompt_and_get_author(
        client,
        {"Authorization": f"Bearer {MASTER_API_KEY}"},
    )
    # The route excludes None fields, so the master key has no name key.
    assert author == {"kind": ActorKind.MASTER_KEY.value, "id": "master-key"}


@pytest.mark.unit_tests
def test_master_key_on_behalf_of_records_the_person(
    client: GenaiEngineTestClientBase,
):
    author = _save_prompt_and_get_author(
        client,
        {
            "Authorization": f"Bearer {MASTER_API_KEY}",
            ON_BEHALF_OF_HEADER: "alice@example.com",
        },
    )
    assert author == {
        "kind": ActorKind.ON_BEHALF_OF_USER.value,
        "id": "alice@example.com",
        "name": "alice@example.com",
    }


@pytest.mark.unit_tests
def test_transform_versions_record_author(client: GenaiEngineTestClientBase):
    status_code, task = client.create_task(
        f"authorship_{random.random()}",
        is_agentic=True,
    )
    assert status_code == 200

    status_code, transform = client.create_transform(
        task_id=task.id,
        name="authored_transform",
        definition=TRANSFORM_DEFINITION,
    )
    assert status_code == 200

    status_code, versions = client.list_transform_versions(str(transform.id))
    assert status_code == 200
    assert versions.versions[0].created_by is not None
    assert versions.versions[0].created_by.kind == ActorKind.API_KEY
    assert versions.versions[0].created_by.name == "TestClient"


@pytest.mark.unit_tests
def test_jwt_user_actor_uses_subject_and_email():
    user = User(id="sub-123", email="priya@example.com", roles=[])
    actor = user.to_actor()
    assert actor.kind == ActorKind.USER
    assert actor.id == "sub-123"
    assert actor.name == "priya@example.com"
