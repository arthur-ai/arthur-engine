from uuid import uuid4

import pytest

from config.config import Config
from monitoring.audit_log_middleware import ENDPOINT_OVERRIDES, AuditLogMiddleware
from schemas.audit_log_schemas import RouteInfo
from tests.clients.base_test_client import GenaiEngineTestClientBase

from .helpers import get_audit_logs_with_ids, read_audit_entries


@pytest.mark.unit_tests
@pytest.mark.skipif(not Config.audit_log_enabled(), reason="Audit logging is disabled")
def test_audit_log_middleware(client: GenaiEngineTestClientBase):
    """Tests audit log middleware against the real app.

    All operations target specific task IDs so we can filter audit entries
    reliably even when other tests run in parallel (pytest-xdist) and write
    to the same audit log file.
    """
    # 1) POST to create a task
    status_code, task = client.create_task(name="audit test task")
    assert status_code == 200
    task_id = task.id

    # 2) GET single resource
    status_code, _ = client.get_task(task_id)
    assert status_code == 200

    # 3) GET default rules — bare list[RuleResponse]
    status_code, _ = client.get_default_rules()
    assert status_code == 200

    # 4) Health check — should NOT be logged
    client.base_client.get("/health")

    # 5) GET non-existent task triggers 404
    non_existent_task_id = str(uuid4())
    status_code, _ = client.get_task(non_existent_task_id)

    all_entries = read_audit_entries()
    new_entries = get_audit_logs_with_ids(all_entries, {task_id, non_existent_task_id})

    assert len(new_entries) >= 3, (
        f"Expected at least 3 audit entries for task {task_id}, got {len(new_entries)}: "
        f"{[(e.request_method.value, e.request_path) for e in new_entries]}"
    )

    # POST /api/v2/tasks
    post_task_entry = next(
        e
        for e in new_entries
        if e.request_method.value == "post" and "/tasks" in e.request_path
    )
    assert post_task_entry.status_code == 200
    assert len(post_task_entry.response_ids) == 1
    assert post_task_entry.response_ids[0].response_type == "TaskResponse"
    assert str(post_task_entry.response_ids[0].response_id) == task_id

    # GET /api/v2/tasks/{id} — 200
    get_task_entry = next(
        e
        for e in new_entries
        if e.request_method.value == "get" and f"/tasks/{task_id}" in e.request_path
    )
    assert get_task_entry.status_code == 200
    assert len(get_task_entry.response_ids) == 1
    assert get_task_entry.response_ids[0].response_type == "TaskResponse"
    assert str(get_task_entry.response_ids[0].response_id) == task_id

    # GET /api/v2/tasks/{id} — non-existent
    get_missing_entry = [
        e for e in new_entries if non_existent_task_id in e.request_path
    ]
    assert len(get_missing_entry) == 1
    assert get_missing_entry[0].response_ids == []

    # Verify no health check entries were logged
    for entry in all_entries:
        assert entry.request_path != "/health"

    # Cleanup
    client.delete_task(task_id)


@pytest.mark.unit_tests
@pytest.mark.parametrize(
    "override_key,collection_field,id_field_override",
    [(key, cf, idf) for key, (cf, idf) in ENDPOINT_OVERRIDES.items()],
    ids=list(ENDPOINT_OVERRIDES.keys()),
)
def test_extract_ids_for_override(override_key, collection_field, id_field_override):
    """
    For each case presented in ENDPOINT_OVERRIDES, build a fake response matching
    the shape of the expected response and verify _extract_ids returns the correct
    response_ids.
    """
    id_field = id_field_override or "id"
    fake_id = "test-id-abc-123"

    if collection_field is None:
        # Bare list response
        data = [{id_field: fake_id}]
    else:
        data = {collection_field: [{id_field: fake_id}], "count": 1}

    route_info = RouteInfo(
        resource_name=override_key,
        collection_field=collection_field,
        id_field=id_field,
    )

    result = AuditLogMiddleware._extract_ids(data, route_info)

    assert (
        len(result) == 1
    ), f"{override_key}: expected 1 response_id, got {len(result)}"
    assert result[0].response_id == fake_id
    assert result[0].response_type == override_key
    assert result[0].id_field == id_field


@pytest.mark.unit_tests
def test_extract_ids_with_integer_id_field():
    """
    Endpoints like LLMEvalsVersionListResponse use integer version numbers
    as the id_field. Verify _extract_ids coerces them to strings so
    AuditLogResponseID validation doesn't fail.
    """
    # Collection response
    route_info = RouteInfo(
        resource_name="LLMEvalsVersionListResponse",
        collection_field="versions",
        id_field="version",
    )
    data = {"versions": [{"version": 1, "name": "Tone"}], "count": 1}

    result = AuditLogMiddleware._extract_ids(data, route_info)

    assert len(result) == 1
    assert result[0].response_id == "1"
    assert result[0].id_field == "version"

    # Single dict response
    route_info_single = RouteInfo(
        resource_name="SomeVersionResponse",
        collection_field=None,
        id_field="version",
    )
    data_single = {"version": 3, "name": "test"}

    result_single = AuditLogMiddleware._extract_ids(data_single, route_info_single)

    assert len(result_single) == 1
    assert result_single[0].response_id == "3"
