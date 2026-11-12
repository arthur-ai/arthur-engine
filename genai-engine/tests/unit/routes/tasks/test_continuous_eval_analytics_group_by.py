"""Daily continuous-eval analytics can be split by an attribute on the run's trace."""

from datetime import datetime, timedelta

import pytest
from arthur_common.models.enums import ContinuousEvalRunStatus

from db_models.agentic_annotation_models import DatabaseAgenticAnnotation
from db_models.telemetry_models import DatabaseSpan
from schemas.response_schemas import AgenticAnnotationAnalyticsResponse
from tests.clients.base_test_client import (
    GenaiEngineTestClientBase,
    override_get_db_session,
)
from tests.unit.routes.tasks.test_continuous_eval_crud_routes import (
    create_test_llm_eval,
)
from tests.unit.routes.tasks.test_continuous_eval_spend_routes import (
    _add_root_span,
    _add_run,
    _add_traces,
    _cleanup,
    _create_continuous_eval,
)


def _analytics(client: GenaiEngineTestClientBase, task_id: str, **params):
    resp = client.base_client.get(
        f"/api/v1/tasks/{task_id}/continuous_evals/analytics/daily",
        params=params,
        headers=client.authorized_user_api_key_headers,
    )
    assert resp.status_code == 200, resp.text
    return AgenticAnnotationAnalyticsResponse.model_validate(resp.json()).stats


@pytest.mark.unit_tests
def test_daily_analytics_split_by_prompt_version(client: GenaiEngineTestClientBase):
    status_code, task = client.create_task(name="analytics_group_by", is_agentic=True)
    assert status_code == 200
    status_code, llm_eval = create_test_llm_eval(client, task.id, "grouped_eval")
    assert status_code == 200
    continuous_eval, _ = _create_continuous_eval(client, task.id, llm_eval.name, None)
    other_task = None
    trace_ids: list[str] = []
    try:
        now = datetime.now()
        trace_ids = _add_traces(task.id, [now - timedelta(minutes=30)] * 7)
        versions = ["1", "1", "1", "2", "2", "2", None]
        outcomes = [0, 0, 0, 1, 1, 0, 1]
        for trace_id, version, score in zip(trace_ids, versions, outcomes):
            attributes = {"metadata": {"prompt_version": version}} if version else {}
            _add_root_span(task.id, trace_id, attributes)
            _add_run(
                continuous_eval.id,
                trace_id,
                (
                    ContinuousEvalRunStatus.PASSED
                    if score
                    else ContinuousEvalRunStatus.FAILED
                ),
                0.01,
                now - timedelta(minutes=10),
            )
        # The run's annotation_score drives passed/failed counts.
        db_session = override_get_db_session()
        for trace_id, score in zip(trace_ids, outcomes):
            db_session.query(DatabaseAgenticAnnotation).filter(
                DatabaseAgenticAnnotation.trace_id == trace_id,
            ).update({"annotation_score": score})
        db_session.commit()

        overall = _analytics(client, task.id)
        assert len(overall) == 1
        assert overall[0].total_count == 7
        assert overall[0].pass_rate == pytest.approx(3 / 7)
        assert overall[0].group is None

        # Another task's span under the ungrouped trace's id must not label it:
        # trace ids are not unique across tasks.
        status_code, other_task = client.create_task(
            name="analytics_group_by_other",
            is_agentic=True,
        )
        assert status_code == 200
        _add_root_span(
            other_task.id,
            trace_ids[6],
            {"metadata": {"prompt_version": "other-task"}},
        )

        grouped = _analytics(
            client,
            task.id,
            group_by="attributes.metadata.prompt_version",
            group_by_span_name="agent",
        )
        by_group = {row.group: row for row in grouped}
        assert set(by_group) == {None, "1", "2"}
        assert (by_group["1"].passed_count, by_group["1"].failed_count) == (0, 3)
        assert by_group["1"].pass_rate == 0
        assert by_group["2"].pass_rate == pytest.approx(2 / 3)
        assert by_group[None].total_count == 1

        # A span name that doesn't exist leaves every run ungrouped.
        ungrouped = _analytics(
            client,
            task.id,
            group_by="attributes.metadata.prompt_version",
            group_by_span_name="no-such-span",
        )
        assert [(row.group, row.total_count) for row in ungrouped] == [(None, 7)]
    finally:
        db_session = override_get_db_session()
        db_session.query(DatabaseSpan).filter(
            DatabaseSpan.trace_id.in_(trace_ids),
        ).delete(synchronize_session=False)
        db_session.commit()
        if other_task is not None:
            client.delete_task(other_task.id)
        _cleanup(client, task.id, [continuous_eval.id])
