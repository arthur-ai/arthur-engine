from datetime import datetime, timedelta, timezone
from typing import Any
from unittest.mock import Mock
from uuid import uuid4

import pytest
from arthur_client.api_bindings import (
    Alert,
    AlertBound,
    AlertCheckJobSpec,
    AlertRule,
    AlertRuleInterval,
    CreatedAlerts,
    IntervalUnit,
    Job,
    JobKind,
    JobPriority,
    JobSpec,
    JobState,
    JobTrigger,
    MetricsQueryResult,
)
from job_executors.alert_check_executor import AlertCheckExecutor


def test_alert_check_executor_fault_tolerance():
    # the goal of this test is to make sure that when the alert check job fails for one alert rule, any other
    # alert rules on the model are still processed

    # Setup test data
    interval = AlertRuleInterval(
        unit=IntervalUnit.MINUTES,
        count=1,
    )
    model_id = str(uuid4())
    now = datetime.now(timezone.utc)
    alert_rule1 = AlertRule(
        id="rule1",
        name="test_rule",
        metric_name="test_metric",
        query="test query",
        threshold=100,
        bound=AlertBound.UPPER_BOUND,
        notification_webhooks=[],
        interval=interval,
        model_id=model_id,
        created_at=now,
        updated_at=now,
    )
    alert_rule2 = AlertRule(
        id="rule2",
        name="test_rule2",
        metric_name="test_metric2",
        query="test query2",
        threshold=50,
        bound=AlertBound.LOWER_BOUND,
        notification_webhooks=[],
        interval=interval,
        model_id=model_id,
        created_at=now,
        updated_at=now,
    )

    # Create job spec
    end_time = datetime.now(timezone.utc)
    start_time = end_time - timedelta(hours=1)
    job_spec = AlertCheckJobSpec(
        scope_model_id=model_id,
        check_range_start_timestamp=start_time,
        check_range_end_timestamp=end_time,
    )
    job = Job(
        id=str(uuid4()),
        kind=JobKind.ALERT_CHECK,
        job_spec=JobSpec(job_spec),
        state=JobState.RUNNING,
        project_id=str(uuid4()),
        data_plane_id=str(uuid4()),
        queued_at=start_time,
        ready_at=start_time,
        trigger_type=JobTrigger.USER,
        attempts=1,
        max_attempts=1,
        memory_requirements_mb=100,
        job_priority=JobPriority.NUMBER_100,
    )

    # Mock clients
    alerts_client = Mock()
    alert_rules_client = Mock()
    jobs_client = Mock()
    metrics_client = Mock()
    logger = Mock()

    # Setup alert rules client to return our test rules
    alert_rules_response = Mock()
    alert_rules_response.records = [alert_rule1, alert_rule2]
    alert_rules_client.get_model_alert_rules.return_value = alert_rules_response

    # Setup metrics client to return test data
    metrics_client.post_model_metrics_query.return_value = MetricsQueryResult(
        results=[{"metric_timestamp": end_time, "metric_value": 150}],
    )

    # Setup alerts client
    alerts_client.post_model_alerts.return_value = CreatedAlerts(
        alerts=[
            Alert(
                description="test alert",
                timestamp=datetime.now(timezone.utc),
                value=1,
                threshold=0,
                bound=AlertBound.UPPER_BOUND,
                dimensions={},
                alert_rule_id=str(uuid4()),
                job_id=None,
                is_duplicate_of=None,
                interval=interval,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
                id=str(uuid4()),
                model_id=model_id,
                alert_rule_name="alert rule",
                alert_rule_metric_name="alert rule metric name",
            ),
        ],
        webhooks_called=[],
    )

    # Create executor
    executor = AlertCheckExecutor(
        alerts_client=alerts_client,
        alert_rules_client=alert_rules_client,
        jobs_client=jobs_client,
        metrics_client=metrics_client,
        logger=logger,
    )

    # Make the first alert rule processing fail
    def fail_first_rule(model_id: str, post_metrics_query: Any) -> MetricsQueryResult:
        if post_metrics_query.query == alert_rule1.query:
            raise Exception("Simulated failure for rule1")
        return MetricsQueryResult(
            results=[{"metric_timestamp": end_time, "metric_value": 25}],
        )

    metrics_client.post_model_metrics_query.side_effect = fail_first_rule

    # Execute and verify it raises the exception
    with pytest.raises(Exception) as exc_info:
        executor.execute(job, job_spec)

    # Verify the error is from rule1
    assert "Simulated failure for rule1" in str(exc_info.value)

    # Verify both rules were attempted to be processed
    assert metrics_client.post_model_metrics_query.call_count == 2

    # Verify the calls were made in the correct order
    calls = metrics_client.post_model_metrics_query.call_args_list
    assert calls[0][1]["post_metrics_query"].query == alert_rule1.query
    assert calls[1][1]["post_metrics_query"].query == alert_rule2.query

    # Verify both errors were logged for rule1
    assert logger.error.call_count == 2
    call_args_list = logger.error.call_args_list

    # First error - metrics query failure
    assert call_args_list[0][0][0] == "Error querying metrics for alert rule rule1"
    assert isinstance(call_args_list[0][1]["exc_info"], Exception)
    assert str(call_args_list[0][1]["exc_info"]) == "Simulated failure for rule1"

    # Second error - alert creation failure
    assert (
        call_args_list[1][0][0]
        == "Error creating alerts and processing alert rule rule1"
    )
    assert isinstance(call_args_list[1][1]["exc_info"], Exception)
    assert str(call_args_list[1][1]["exc_info"]) == "Simulated failure for rule1"
