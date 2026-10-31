"""Task-scoped API keys: a key created with `task_id` reaches only that task.

Covers key creation, the org-scope decorators applying the task scope, the
fail-closed rule in `permission_checker`, and trace ingest.
"""

import json
import random
import uuid

import pytest

from db_models import DatabaseSpan
from tests.clients.base_test_client import (
    MASTER_KEY_AUTHORIZED_HEADERS,
    GenaiEngineTestClientBase,
    override_get_db_session,
)
from tests.routes.trace_api.conftest import _create_base_trace_request, _create_span
from utils import constants


def _create_scoped_key(
    client: GenaiEngineTestClientBase,
    task_id: str,
    roles: list[str],
):
    return client.base_client.post(
        "/auth/api_keys/",
        json={"description": "scoped", "roles": roles, "task_id": task_id},
        headers=MASTER_KEY_AUTHORIZED_HEADERS,
    )


def _scoped_headers(client, task_id: str, roles: list[str]) -> dict:
    response = _create_scoped_key(client, task_id, roles)
    assert response.status_code == 200, response.text
    assert response.json()["task_id"] == task_id
    return {"Authorization": f"Bearer {response.json()['key']}"}


def _two_tasks(client: GenaiEngineTestClientBase) -> tuple[str, str]:
    _, own = client.create_task(f"scoped_own_{random.random()}", is_agentic=True)
    _, other = client.create_task(f"scoped_other_{random.random()}", is_agentic=True)
    return own.id, other.id


def _trace(task_id: str | None, span_name: str) -> bytes:
    trace_request, resource_span, scope_span = _create_base_trace_request(
        task_id=task_id,
    )
    scope_span.spans.append(
        _create_span(
            trace_id=uuid.uuid4().bytes,
            span_id=uuid.uuid4().bytes[:8],
            name=span_name,
        ),
    )
    resource_span.scope_spans.append(scope_span)
    trace_request.resource_spans.append(resource_span)
    return trace_request.SerializeToString()


def _post_trace(
    client,
    headers: dict,
    body: bytes,
    expected_status: int = 200,
) -> dict:
    response = client.base_client.post(
        "/api/v1/traces",
        content=body,
        headers={**headers, "Content-Type": "application/x-protobuf"},
    )
    assert response.status_code == expected_status, response.text
    return json.loads(response.text)


def _span_task(span_name: str) -> str | None:
    db_session = override_get_db_session()
    try:
        span = (
            db_session.query(DatabaseSpan)
            .filter(DatabaseSpan.span_name == span_name)
            .one_or_none()
        )
        return span.task_id if span else None
    finally:
        db_session.close()


@pytest.mark.unit_tests
def test_create_key_unknown_task_is_404(client: GenaiEngineTestClientBase):
    response = _create_scoped_key(
        client,
        str(uuid.uuid4()),
        [constants.VALIDATION_USER],
    )
    assert response.status_code == 404


@pytest.mark.unit_tests
def test_create_key_rejects_org_wide_roles(client: GenaiEngineTestClientBase):
    own, _ = _two_tasks(client)
    response = _create_scoped_key(client, own, [constants.ORG_ADMIN])
    assert response.status_code == 400


@pytest.mark.unit_tests
def test_leaked_validation_key_cannot_write_traces_into_another_task(
    client: GenaiEngineTestClientBase,
):
    own, other = _two_tasks(client)
    headers = _scoped_headers(client, own, [constants.VALIDATION_USER])

    forged = f"forged_{uuid.uuid4().hex}"
    # Every span rejected: the route answers 422, as for any fully rejected batch.
    result = _post_trace(client, headers, _trace(other, forged), expected_status=422)
    assert result["accepted_spans"] == 0
    assert result["rejected_spans"] == 1
    assert _span_task(forged) is None


@pytest.mark.unit_tests
def test_scoped_key_traces_land_in_its_task(client: GenaiEngineTestClientBase):
    own, _ = _two_tasks(client)
    headers = _scoped_headers(client, own, [constants.VALIDATION_USER])

    # Naming its own task is accepted.
    named = f"named_{uuid.uuid4().hex}"
    assert _post_trace(client, headers, _trace(own, named))["accepted_spans"] == 1
    assert _span_task(named) == own

    # No arthur.task attribute: the key's task is used, not service-name mapping.
    unnamed = f"unnamed_{uuid.uuid4().hex}"
    assert _post_trace(client, headers, _trace(None, unnamed))["accepted_spans"] == 1
    assert _span_task(unnamed) == own


@pytest.mark.unit_tests
def test_unscoped_key_still_writes_to_any_task(client: GenaiEngineTestClientBase):
    """Existing keys (task_id NULL) keep today's behaviour."""
    _, other = _two_tasks(client)
    status_code, key = client.create_api_key(
        description="unscoped",
        roles=[constants.VALIDATION_USER],
    )
    assert status_code == 200
    assert key.task_id is None

    name = f"unscoped_{uuid.uuid4().hex}"
    result = _post_trace(
        client,
        {"Authorization": f"Bearer {key.key}"},
        _trace(other, name),
    )
    assert result["accepted_spans"] == 1
    assert _span_task(name) == other


@pytest.mark.unit_tests
def test_scoped_key_path_routes_only_reach_its_task(
    client: GenaiEngineTestClientBase,
):
    own, other = _two_tasks(client)
    headers = _scoped_headers(client, own, [constants.TASK_ADMIN])

    assert (
        client.base_client.get(f"/api/v2/tasks/{own}", headers=headers).status_code
        == 200
    )
    # Same 404 a tenant key gets for another org's task: no enumeration.
    assert (
        client.base_client.get(f"/api/v2/tasks/{other}", headers=headers).status_code
        == 404
    )


@pytest.mark.unit_tests
def test_scoped_key_query_routes_are_narrowed_to_its_task(
    client: GenaiEngineTestClientBase,
):
    own, other = _two_tasks(client)
    headers = _scoped_headers(client, own, [constants.TASK_ADMIN])

    response = client.base_client.get(
        "/api/v1/traces",
        params={"task_ids": [other]},
        headers=headers,
    )
    assert response.status_code == 403

    response = client.base_client.get(
        "/api/v1/traces",
        params={"task_ids": [own]},
        headers=headers,
    )
    assert response.status_code == 200


@pytest.mark.unit_tests
def test_scoped_key_is_refused_on_routes_without_a_task_check(
    client: GenaiEngineTestClientBase,
):
    """Fail closed: TASK-ADMIN may read default rules, but that route does not
    check a task, so a task-scoped TASK-ADMIN key is refused."""
    own, _ = _two_tasks(client)
    headers = _scoped_headers(client, own, [constants.TASK_ADMIN])

    response = client.base_client.get("/api/v2/default_rules", headers=headers)
    assert response.status_code == 403

    status_code, _ = client.get_default_rules()
    assert status_code == 200
