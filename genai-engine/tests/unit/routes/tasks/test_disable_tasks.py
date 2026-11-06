import time
import uuid

import pytest
from arthur_common.models.enums import APIKeysRolesEnum, RuleType
from arthur_common.models.request_schemas import NewTaskRequest

from db_models.task_models import DatabaseTask
from dependencies import get_application_config
from repositories.api_key_repository import ApiKeyRepository
from repositories.metrics_repository import MetricRepository
from repositories.organizations_repository import OrganizationsRepository
from repositories.rules_repository import RuleRepository
from repositories.tasks_repository import TaskRepository
from schemas.internal_schemas import Task
from tests.clients.base_test_client import (
    MASTER_KEY_AUTHORIZED_HEADERS,
    GenaiEngineTestClientBase,
    override_get_db_session,
)

KILL_REASON = "Kill switch: prompt injection policy violated"


def _validate_prompt_raw(
    client: GenaiEngineTestClientBase,
    task_id: str,
) -> tuple[int, dict]:
    resp = client.base_client.post(
        f"/api/v2/tasks/{task_id}/validate_prompt",
        json={"prompt": "a harmless prompt"},
        headers=client.authorized_user_api_key_headers,
    )
    return resp.status_code, resp.json()


@pytest.mark.unit_tests
def test_disable_task_blocks_validation_until_enabled(
    client: GenaiEngineTestClientBase,
):
    _, task = client.create_task()
    client.create_rule("", rule_type=RuleType.REGEX, task_id=task.id)
    assert task.is_disabled is False
    assert task.disabled_reason is None
    assert task.disabled_at is None

    # An inference validated before the kill, so the response leg can be tried.
    status_code, prompt = client.create_prompt(task_id=task.id)
    assert status_code == 200

    status_code, disabled = client.disable_task(task.id, KILL_REASON)
    assert status_code == 200
    assert disabled.id == task.id
    assert disabled.is_disabled is True
    assert disabled.disabled_reason == KILL_REASON
    assert disabled.disabled_at is not None
    # Unix milliseconds, UTC.
    assert abs(disabled.disabled_at - time.time() * 1000) < 60_000

    _, fetched = client.get_task(task.id)
    assert fetched.is_disabled is True
    assert fetched.disabled_reason == KILL_REASON

    # The kill takes effect on the very next request, despite the rules cache.
    status_code, body = _validate_prompt_raw(client, task.id)
    assert status_code == 403
    assert body["detail"] == f"Task {task.id} is disabled: {KILL_REASON}"

    status_code, body = client.create_response(prompt.inference_id, task_id=task.id)
    assert status_code == 403
    assert body["detail"] == f"Task {task.id} is disabled: {KILL_REASON}"

    status_code, enabled = client.enable_task(task.id)
    assert status_code == 200
    assert enabled.is_disabled is False
    assert enabled.disabled_reason is None
    assert enabled.disabled_at is None

    status_code, _ = client.create_response(prompt.inference_id, task_id=task.id)
    assert status_code == 200
    status_code, _ = client.create_prompt(task_id=task.id)
    assert status_code == 200

    assert client.delete_task(task.id) == 204


@pytest.mark.unit_tests
def test_disable_and_enable_are_idempotent(client: GenaiEngineTestClientBase):
    _, task = client.create_task()

    # Enabling a task that was never disabled is a no-op.
    status_code, enabled = client.enable_task(task.id)
    assert status_code == 200
    assert enabled.is_disabled is False

    status_code, first = client.disable_task(task.id, "first reason")
    assert status_code == 200

    # Disabling again replaces the reason but keeps the original kill time.
    status_code, second = client.disable_task(task.id, "second reason")
    assert status_code == 200
    assert second.is_disabled is True
    assert second.disabled_reason == "second reason"
    assert second.disabled_at == first.disabled_at

    status_code, body = _validate_prompt_raw(client, task.id)
    assert status_code == 403
    assert body["detail"] == f"Task {task.id} is disabled: second reason"

    assert client.enable_task(task.id)[0] == 200
    status_code, enabled = client.enable_task(task.id)
    assert status_code == 200
    assert enabled.is_disabled is False

    assert client.delete_task(task.id) == 204


@pytest.mark.unit_tests
def test_disable_task_not_found(client: GenaiEngineTestClientBase):
    missing = str(uuid.uuid4())
    assert client.disable_task(missing, KILL_REASON)[0] == 404
    assert client.enable_task(missing)[0] == 404

    # Archived tasks are not found either.
    _, task = client.create_task()
    assert client.delete_task(task.id) == 204
    assert client.disable_task(task.id, KILL_REASON)[0] == 404
    assert client.enable_task(task.id)[0] == 404


@pytest.mark.unit_tests
def test_disable_task_rejects_empty_reason(client: GenaiEngineTestClientBase):
    _, task = client.create_task()
    resp = client.base_client.post(
        f"/api/v2/tasks/{task.id}/disable",
        json={"reason": ""},
        headers=client.authorized_user_api_key_headers,
    )
    assert resp.status_code == 400
    assert client.get_task(task.id)[1].is_disabled is False
    assert client.delete_task(task.id) == 204


@pytest.mark.unit_tests
def test_disable_system_task_rejected(client: GenaiEngineTestClientBase):
    db = override_get_db_session()
    try:
        system_task = (
            db.query(DatabaseTask)
            .filter(DatabaseTask.is_system_task == True)  # noqa: E712
            .filter(DatabaseTask.archived == False)  # noqa: E712
            .first()
        )
    finally:
        db.close()
    assert system_task is not None

    status_code, body = client.disable_task(system_task.id, KILL_REASON)
    assert status_code == 400
    assert body["detail"] == "Cannot disable system tasks"

    status_code, body = client.enable_task(system_task.id)
    assert status_code == 400
    assert body["detail"] == "Cannot enable system tasks"


@pytest.mark.unit_tests
def test_admin_key_can_disable_task(client: GenaiEngineTestClientBase):
    """The ML Engine calls these routes with the engine admin key."""
    _, task = client.create_task()

    status_code, disabled = client.disable_task(
        task.id,
        KILL_REASON,
        headers=MASTER_KEY_AUTHORIZED_HEADERS,
    )
    assert status_code == 200
    assert disabled.is_disabled is True

    status_code, enabled = client.enable_task(
        task.id,
        headers=MASTER_KEY_AUTHORIZED_HEADERS,
    )
    assert status_code == 200
    assert enabled.is_disabled is False

    assert client.delete_task(task.id) == 204


@pytest.mark.unit_tests
def test_tenant_key_cannot_disable_or_enable_own_task(
    client: GenaiEngineTestClientBase,
):
    db = override_get_db_session()
    tasks_repo = TaskRepository(
        db,
        RuleRepository(db),
        MetricRepository(db),
        get_application_config(session=db),
    )
    keys_repo = ApiKeyRepository(db)
    suffix = uuid.uuid4().hex[:8]
    org = OrganizationsRepository(db).create_organization(
        name=f"test-disable-{suffix}",
    )
    task = tasks_repo.create_task(
        Task._from_request_model(
            NewTaskRequest(name=f"disable-{suffix}"),
            org_id=org.id,
        ),
        with_default_rules=False,
    )
    tenant_key = keys_repo.create_api_key(
        description=f"disable-tenant-{suffix}",
        roles=[APIKeysRolesEnum.TENANT_USER],
        org_id=org.id,
    )
    tenant_headers = {"Authorization": f"Bearer {tenant_key.key}"}
    try:
        # The tenant can read its own task, so the 403s below are the role gate.
        resp = client.base_client.get(
            f"/api/v2/tasks/{task.id}",
            headers=tenant_headers,
        )
        assert resp.status_code == 200

        assert (
            client.disable_task(task.id, KILL_REASON, headers=tenant_headers)[0] == 403
        )
        assert client.get_task(task.id)[1].is_disabled is False

        # Once the platform kills it, the tenant cannot turn it back on.
        assert client.disable_task(task.id, KILL_REASON)[0] == 200
        assert client.enable_task(task.id, headers=tenant_headers)[0] == 403
        _, fetched = client.get_task(task.id)
        assert fetched.is_disabled is True
        assert fetched.disabled_reason == KILL_REASON
    finally:
        keys_repo.deactivate_api_key(tenant_key.id)
        tasks_repo.delete_task(task_id=task.id)
        db.close()
