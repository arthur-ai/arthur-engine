from datetime import datetime, timezone

import pytest

from tests.clients.base_test_client import GenaiEngineTestClientBase


@pytest.mark.unit_tests
def test_inference_overview_counts_per_task(client: GenaiEngineTestClientBase):
    status_code, busy_task = client.create_task(empty_rules=True)
    assert status_code == 200
    status_code, idle_task = client.create_task(empty_rules=True)
    assert status_code == 200

    before = datetime.now(timezone.utc)
    for _ in range(3):
        status_code, _ = client.create_prompt(task_id=busy_task.id)
        assert status_code == 200
    after = datetime.now(timezone.utc)

    status_code, overview = client.get_inferences_overview(
        [busy_task.id, idle_task.id],
    )
    assert status_code == 200
    overviews = {o.task_id: o for o in overview.overviews}
    assert set(overviews) == {busy_task.id, idle_task.id}

    assert overviews[busy_task.id].inference_count == 3
    last_inference_at = overviews[busy_task.id].last_inference_at
    assert last_inference_at is not None
    assert before.replace(microsecond=0) <= last_inference_at <= after

    # a task with no inferences is still reported
    assert overviews[idle_task.id].inference_count == 0
    assert overviews[idle_task.id].last_inference_at is None


@pytest.mark.unit_tests
def test_inference_overview_unknown_task_reports_zero(
    client: GenaiEngineTestClientBase,
):
    status_code, overview = client.get_inferences_overview(["not-a-task"])
    assert status_code == 200
    assert len(overview.overviews) == 1
    assert overview.overviews[0].inference_count == 0


@pytest.mark.unit_tests
def test_inference_overview_requires_task_ids(client: GenaiEngineTestClientBase):
    status_code, _ = client.get_inferences_overview([])
    assert status_code == 400
