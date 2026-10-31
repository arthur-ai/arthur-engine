"""Task-scoped API keys: a key created with `task_id` reaches only that task.

Covers key creation, the org-scope decorators applying the task scope, the
fail-closed rule in `permission_checker`, and trace ingest.
"""

import json
import random
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

import pytest

from db_models import DatabaseSpan, DatabaseTraceMetadata
from tests.clients.base_test_client import (
    MASTER_KEY_AUTHORIZED_HEADERS,
    GenaiEngineTestClientBase,
    override_get_db_session,
)
from tests.routes.trace_api.conftest import _create_base_trace_request, _create_span
from utils import constants


@dataclass
class _Created:
    """Keys, tasks and traces a test created, removed after it runs."""

    client: GenaiEngineTestClientBase
    key_ids: list[str] = field(default_factory=list)
    task_ids: list[str] = field(default_factory=list)
    trace_ids: list[bytes] = field(default_factory=list)


@pytest.fixture
def created(client: GenaiEngineTestClientBase):
    state = _Created(client)
    yield state

    for key_id in state.key_ids:
        client.base_client.delete(
            f"/auth/api_keys/deactivate/{key_id}",
            headers=MASTER_KEY_AUTHORIZED_HEADERS,
        )
    hex_ids = [trace_id.hex() for trace_id in state.trace_ids]
    db_session = override_get_db_session()
    try:
        db_session.query(DatabaseSpan).filter(
            DatabaseSpan.trace_id.in_(hex_ids),
        ).delete(synchronize_session=False)
        db_session.query(DatabaseTraceMetadata).filter(
            DatabaseTraceMetadata.trace_id.in_(hex_ids),
        ).delete(synchronize_session=False)
        db_session.commit()
    finally:
        db_session.close()
    for task_id in state.task_ids:
        client.delete_task(task_id)


def _create_scoped_key(created: _Created, task_id: str, roles: list[str]):
    response = created.client.base_client.post(
        "/auth/api_keys/",
        json={"description": "scoped", "roles": roles, "task_id": task_id},
        headers=MASTER_KEY_AUTHORIZED_HEADERS,
    )
    if response.status_code == 200:
        created.key_ids.append(response.json()["id"])
    return response


def _scoped_headers(created: _Created, task_id: str, roles: list[str]) -> dict:
    response = _create_scoped_key(created, task_id, roles)
    assert response.status_code == 200, response.text
    assert response.json()["task_id"] == task_id
    return {"Authorization": f"Bearer {response.json()['key']}"}


def _two_tasks(created: _Created) -> tuple[str, str]:
    _, own = created.client.create_task(
        f"scoped_own_{random.random()}",
        is_agentic=True,
    )
    _, other = created.client.create_task(
        f"scoped_other_{random.random()}",
        is_agentic=True,
    )
    created.task_ids += [own.id, other.id]
    return own.id, other.id


def _trace(
    created: _Created,
    task_id: str | None,
    span_name: str,
    trace_id: bytes | None = None,
) -> bytes:
    trace_id = trace_id or uuid.uuid4().bytes
    created.trace_ids.append(trace_id)
    trace_request, resource_span, scope_span = _create_base_trace_request(
        task_id=task_id,
    )
    scope_span.spans.append(
        _create_span(
            trace_id=trace_id,
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
def test_create_key_unknown_task_is_404(created: _Created):
    response = _create_scoped_key(
        created,
        str(uuid.uuid4()),
        [constants.VALIDATION_USER],
    )
    assert response.status_code == 404


@pytest.mark.unit_tests
def test_create_key_rejects_org_wide_roles(created: _Created):
    own, _ = _two_tasks(created)
    response = _create_scoped_key(created, own, [constants.ORG_ADMIN])
    assert response.status_code == 400


@pytest.mark.unit_tests
def test_leaked_validation_key_cannot_write_traces_into_another_task(created: _Created):
    own, other = _two_tasks(created)
    headers = _scoped_headers(created, own, [constants.VALIDATION_USER])

    forged = f"forged_{uuid.uuid4().hex}"
    # Every span rejected: the route answers 422, as for any fully rejected batch.
    result = _post_trace(
        created.client, headers, _trace(created, other, forged), expected_status=422
    )
    assert result["accepted_spans"] == 0
    assert result["rejected_spans"] == 1
    assert _span_task(forged) is None


@pytest.mark.unit_tests
def test_scoped_key_traces_land_in_its_task(created: _Created):
    own, _ = _two_tasks(created)
    headers = _scoped_headers(created, own, [constants.VALIDATION_USER])

    # Naming its own task is accepted.
    named = f"named_{uuid.uuid4().hex}"
    assert (
        _post_trace(created.client, headers, _trace(created, own, named))[
            "accepted_spans"
        ]
        == 1
    )
    assert _span_task(named) == own

    # No arthur.task attribute: the key's task is used, not service-name mapping.
    unnamed = f"unnamed_{uuid.uuid4().hex}"
    assert (
        _post_trace(created.client, headers, _trace(created, None, unnamed))[
            "accepted_spans"
        ]
        == 1
    )
    assert _span_task(unnamed) == own


@pytest.mark.unit_tests
def test_unscoped_key_still_writes_to_any_task(created: _Created):
    """Existing keys (task_id NULL) keep today's behaviour."""
    _, other = _two_tasks(created)
    status_code, key = created.client.create_api_key(
        description="unscoped",
        roles=[constants.VALIDATION_USER],
    )
    assert status_code == 200
    created.key_ids.append(key.id)
    assert key.task_id is None

    name = f"unscoped_{uuid.uuid4().hex}"
    result = _post_trace(
        created.client,
        {"Authorization": f"Bearer {key.key}"},
        _trace(created, other, name),
    )
    assert result["accepted_spans"] == 1
    assert _span_task(name) == other


@pytest.mark.unit_tests
def test_scoped_key_path_routes_only_reach_its_task(created: _Created):
    own, other = _two_tasks(created)
    headers = _scoped_headers(created, own, [constants.TASK_ADMIN])

    assert (
        created.client.base_client.get(
            f"/api/v2/tasks/{own}", headers=headers
        ).status_code
        == 200
    )
    # Same 404 a tenant key gets for another org's task: no enumeration.
    assert (
        created.client.base_client.get(
            f"/api/v2/tasks/{other}", headers=headers
        ).status_code
        == 404
    )


@pytest.mark.unit_tests
def test_scoped_key_query_routes_are_narrowed_to_its_task(created: _Created):
    own, other = _two_tasks(created)
    headers = _scoped_headers(created, own, [constants.TASK_ADMIN])

    response = created.client.base_client.get(
        "/api/v1/traces",
        params={"task_ids": [other]},
        headers=headers,
    )
    assert response.status_code == 403

    response = created.client.base_client.get(
        "/api/v1/traces",
        params={"task_ids": [own]},
        headers=headers,
    )
    assert response.status_code == 200


@pytest.mark.unit_tests
def test_scoped_key_is_refused_on_routes_without_a_task_check(created: _Created):
    """Fail closed: TASK-ADMIN may read default rules, but that route does not
    check a task, so a task-scoped TASK-ADMIN key is refused."""
    own, _ = _two_tasks(created)
    headers = _scoped_headers(created, own, [constants.TASK_ADMIN])

    response = created.client.base_client.get("/api/v2/default_rules", headers=headers)
    assert response.status_code == 403

    status_code, _ = created.client.get_default_rules()
    assert status_code == 200


@pytest.mark.unit_tests
def test_scoped_key_cannot_add_spans_to_another_tasks_trace(created: _Created):
    """Trace metadata keeps the task that first stored the trace, so a span
    joining that trace would show up in the other task."""
    own, other = _two_tasks(created)
    shared_trace_id = uuid.uuid4().bytes
    first = f"first_{uuid.uuid4().hex}"
    _post_trace(
        created.client,
        MASTER_KEY_AUTHORIZED_HEADERS,
        _trace(created, other, first, trace_id=shared_trace_id),
    )
    assert _span_task(first) == other

    headers = _scoped_headers(created, own, [constants.VALIDATION_USER])
    injected = f"injected_{uuid.uuid4().hex}"
    result = _post_trace(
        created.client,
        headers,
        _trace(created, own, injected, trace_id=shared_trace_id),
        expected_status=422,
    )
    assert result["rejected_spans"] == 1
    assert _span_task(injected) is None


@pytest.mark.unit_tests
def test_scoped_key_timeseries_only_reaches_its_task(created: _Created):
    own, other = _two_tasks(created)
    headers = _scoped_headers(created, own, [constants.TASK_ADMIN])
    end = datetime.now(timezone.utc)
    window = {
        "start_time": (end - timedelta(days=1)).isoformat(),
        "end_time": end.isoformat(),
        "bucket_size": "hour",
    }

    response = created.client.base_client.post(
        "/api/v1/traces/overview/timeseries",
        json={"task_id": other, **window},
        headers=headers,
    )
    assert response.status_code == 404

    response = created.client.base_client.post(
        "/api/v1/traces/overview/timeseries",
        json={"task_id": own, **window},
        headers=headers,
    )
    assert response.status_code == 200, response.text


@pytest.mark.unit_tests
def test_scoped_key_cannot_validate_another_tasks_inference(created: _Created):
    own, other = _two_tasks(created)
    status_code, prompt_result = created.client.create_prompt(task_id=other)
    assert status_code == 200

    headers = _scoped_headers(created, own, [constants.VALIDATION_USER])
    response = created.client.base_client.post(
        f"/api/v2/tasks/{own}/validate_response/{prompt_result.inference_id}",
        json={"response": "hello"},
        headers=headers,
    )
    assert response.status_code == 404
