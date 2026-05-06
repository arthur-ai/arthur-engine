from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, call, patch
from uuid import uuid4

import pytest
from arthur_common.models.enums import RuleType
from arthur_client.api_bindings import (
    Alert,
    AlertBound,
    AlertRule,
    AlertRuleInterval,
    AttestationRecord,
    ComplianceAlertRuleResults,
    ComplianceAttestationRuleResults,
    CompliancePolicyCheckJobSpec,
    ComplianceStatus,
    ComplianceStatusDetail,
    IntervalUnit,
    Job,
    JobKind,
    JobPriority,
    JobSpec,
    JobState,
    JobTrigger,
    ModelSummary,
    Policy,
    PolicyAlertRule,
    PolicyAlertGuardrailRule,
    PolicyAssignment,
    PolicyAttestationRule,
    PolicySummary,
    RuleType,
)

from job_executors.compliance_policy_check_executor import CompliancePolicyCheckExecutor

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

NOW = datetime(2026, 3, 31, 12, 0, 0, tzinfo=timezone.utc)
ALERT_WINDOW_START = NOW - timedelta(hours=24)


def _make_policy_summary(policy_id: str = None) -> PolicySummary:
    return PolicySummary(
        id=policy_id or str(uuid4()),
        name="Test Policy",
        description="A test policy",
    )


def _make_model_summary(model_id: str = None) -> ModelSummary:
    return ModelSummary(
        id=model_id or str(uuid4()),
        name="Test Model",
        project_id=str(uuid4()),
    )


def _make_assignment(
    policy_summary: PolicySummary = None,
    model_summary: ModelSummary = None,
    enforcement_in_past: bool = True,
) -> PolicyAssignment:
    enforcement = (
        NOW - timedelta(days=7) if enforcement_in_past else NOW + timedelta(days=7)
    )
    return PolicyAssignment(
        id=str(uuid4()),
        policy=policy_summary or _make_policy_summary(),
        model=model_summary or _make_model_summary(),
        applied_at=NOW - timedelta(days=14),
        enforcement_starts_at=enforcement,
        compliance_status=ComplianceStatusDetail(
            status=ComplianceStatus.PENDING,
            alert_rules=ComplianceAlertRuleResults(),
            attestation_rules=ComplianceAttestationRuleResults(),
        ),
        compliance_job_id=None,
        created_at=NOW - timedelta(days=14),
        updated_at=NOW - timedelta(days=14),
    )


def _make_attestation_rule(
    rule_id: str = None, policy_id: str = None
) -> PolicyAttestationRule:
    return PolicyAttestationRule(
        id=rule_id or str(uuid4()),
        policy_id=policy_id or str(uuid4()),
        name="Quarterly Review",
        validity_period_days=90,
        created_at=NOW,
        updated_at=NOW,
    )


def _make_alert_rule(
    rule_id: str = None,
    model_id: str = None,
    policy_alert_rule_id: str = None,
    name: str = "PII Score Alert",
    interval: AlertRuleInterval = None,
) -> AlertRule:
    return AlertRule(
        id=rule_id or str(uuid4()),
        model_id=model_id or str(uuid4()),
        name=name,
        threshold=0.8,
        bound=AlertBound.UPPER_BOUND,
        query="SELECT ...",
        metric_name="pii_score",
        interval=interval or AlertRuleInterval(unit=IntervalUnit.DAYS, count=1),
        notification_webhooks=[],
        policy_alert_rule_id=policy_alert_rule_id,
        created_at=NOW,
        updated_at=NOW,
    )


def _make_alert(
    alert_rule_id: str,
    model_id: str = None,
    timestamp: datetime = None,
    interval: AlertRuleInterval = None,
) -> Alert:
    return Alert(
        id=str(uuid4()),
        model_id=model_id or str(uuid4()),
        alert_rule_id=alert_rule_id,
        alert_rule_name="PII Score Alert",
        alert_rule_metric_name="pii_score",
        timestamp=timestamp or NOW,
        value=0.95,
        threshold=0.8,
        bound=AlertBound.UPPER_BOUND,
        interval=interval or AlertRuleInterval(unit=IntervalUnit.DAYS, count=1),
        description="PII score exceeded threshold",
        dimensions={},
        created_at=NOW,
        updated_at=NOW,
    )


def _alerts_side_effect(rule_to_alerts: dict):
    """Mock side_effect for alerts_client.get_model_alerts that returns
    different alert lists based on the alert_rule_ids filter."""

    def _impl(*args, **kwargs):
        ids = kwargs.get("alert_rule_ids") or []
        rule_id = ids[0] if ids else None
        return _paginated_response(list(rule_to_alerts.get(rule_id, [])))

    return _impl


def _make_attestation_record(
    rule_id: str,
    assignment_id: str,
    model_id: str,
    next_due: datetime = None,
) -> AttestationRecord:
    return AttestationRecord(
        id=str(uuid4()),
        policy_attestation_rule_id=rule_id,
        policy_model_assignment_id=assignment_id,
        model_id=model_id,
        attested_by_user_id=str(uuid4()),
        notes="All good",
        attested_at=NOW - timedelta(days=30),
        next_attestation_due=next_due or (NOW + timedelta(days=60)),
        created_at=NOW - timedelta(days=30),
    )


def _make_policy(
    policy_id: str,
    attestation_rules: list = None,
    alert_rules: list = None,
) -> Policy:
    return Policy(
        id=policy_id,
        organization_id=str(uuid4()),
        name="Test Policy",
        owner_group_id=str(uuid4()),
        webhook_id=str(uuid4()),
        enforcement_delay_days=14,
        alert_rules=alert_rules or [],
        attestation_rules=attestation_rules or [],
        created_at=NOW,
        updated_at=NOW,
    )


def _make_policy_alert_rule(dependent_resource: PolicyAlertGuardrailRule = None, policy_id: str = None) -> PolicyAlertRule:
    return PolicyAlertRule(
        id=str(uuid4()),
        policy_id=policy_id or str(uuid4()),
        name=f"Alert for {dependent_resource.name}",
        threshold=0.8,
        bound=AlertBound.UPPER_BOUND,
        query="SELECT ...",
        metric_name="rule_count",
        dependent_resource=dependent_resource,
        created_at=NOW,
        updated_at=NOW,
    )


def _make_task_read_response(enabled_rule_types: list[str]) -> Mock:
    """Build a mock TaskReadResponse with the given rule types enabled."""
    rules = []
    for rt in enabled_rule_types:
        rule = Mock()
        rule.enabled = True
        rule.type = RuleType(rt)
        rules.append(rule)
    task = Mock()
    task.rules = rules
    task_read = Mock()
    task_read.task = task
    return task_read


def _make_metrics_query_result(has_data: bool) -> Mock:
    result = Mock()
    result.results = [{"metric_value": 42}] if has_data else []
    return result


def _make_policy_alert_rule(dependent_resource: PolicyAlertGuardrailRule = None, policy_id: str = None) -> PolicyAlertRule:
    return PolicyAlertRule(
        id=str(uuid4()),
        policy_id=policy_id or str(uuid4()),
        name=f"Alert for {dependent_resource.name}",
        threshold=0.8,
        bound=AlertBound.UPPER_BOUND,
        query="SELECT ...",
        metric_name="rule_count",
        dependent_resource=dependent_resource,
        created_at=NOW,
        updated_at=NOW,
    )


def _make_task_read_response(enabled_rule_types: list[str]) -> Mock:
    """Build a mock TaskReadResponse with the given rule types enabled."""
    rules = []
    for rt in enabled_rule_types:
        rule = Mock()
        rule.enabled = True
        rule.type = RuleType(rt)
        rules.append(rule)
    task = Mock()
    task.rules = rules
    task_read = Mock()
    task_read.task = task
    return task_read


def _make_metrics_query_result(has_data: bool) -> Mock:
    result = Mock()
    result.results = [{"metric_value": 42}] if has_data else []
    return result


def _make_job_and_spec(
    model_id: str,
    assignment_id: str = None,
    window_start: datetime = None,
    window_end: datetime = None,
) -> tuple[Job, CompliancePolicyCheckJobSpec]:
    job_spec = CompliancePolicyCheckJobSpec(
        scope_model_id=model_id,
        check_range_start_timestamp=window_start or ALERT_WINDOW_START,
        check_range_end_timestamp=window_end or NOW,
        policy_assignment_id=assignment_id,
    )
    job = Job(
        id=str(uuid4()),
        kind=JobKind.COMPLIANCE_POLICY_CHECK,
        job_spec=JobSpec(job_spec),
        state=JobState.RUNNING,
        project_id=str(uuid4()),
        data_plane_id=str(uuid4()),
        queued_at=NOW,
        ready_at=NOW,
        trigger_type=JobTrigger.USER,
        attempts=1,
        max_attempts=1,
        memory_requirements_mb=45,
        job_priority=JobPriority.NUMBER_100,
    )
    return job, job_spec


def _make_executor():
    policies_client = Mock()
    alert_rules_client = Mock()
    alerts_client = Mock()
    metrics_client = Mock()
    tasks_client = Mock()
    logger = Mock()

    executor = CompliancePolicyCheckExecutor(
        policies_client=policies_client,
        alert_rules_client=alert_rules_client,
        alerts_client=alerts_client,
        metrics_client=metrics_client,
        tasks_client=tasks_client,
        logger=logger,
    )

    # Default: metrics version creation returns a mock with version_num
    metrics_version = Mock()
    metrics_version.version_num = 1
    metrics_client.post_model_metrics_version.return_value = metrics_version

    # Default: no task state cache (guardrail checks will find no enabled rules)
    task_read = Mock()
    task_read.task = None
    tasks_client.get_task_state_cache.return_value = task_read

    return (
        executor,
        policies_client,
        alert_rules_client,
        alerts_client,
        metrics_client, 
        tasks_client,
        logger,
    )


def _paginated_response(records):
    resp = Mock()
    resp.records = records
    return resp


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@patch("job_executors.compliance_policy_check_executor.datetime")
def test_no_assignments_is_noop(mock_datetime):
    """When no assignments exist for the model, the job exits early without errors."""
    mock_datetime.now.return_value = NOW
    mock_datetime.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)

    executor, policies_client, _, _, metrics_client, _, logger = _make_executor()

    model_id = str(uuid4())
    job, job_spec = _make_job_and_spec(model_id)

    policies_client.list_model_policy_assignments.return_value = _paginated_response([])

    executor.execute(job, job_spec)

    policies_client.set_compliance_status.assert_not_called()
    metrics_client.post_model_metrics_version.assert_not_called()
    logger.info.assert_any_call("No policy assignments found. Nothing to check.")


@patch("job_executors.compliance_policy_check_executor.datetime")
def test_all_rules_pass_compliant(mock_datetime):
    """When all attestation rules have valid attestations and no alerts exist, status is COMPLIANT."""
    mock_datetime.now.return_value = NOW
    mock_datetime.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)

    executor, policies_client, alert_rules_client, alerts_client, metrics_client, _, _ = (
        _make_executor()
    )

    model_id = str(uuid4())
    policy_id = str(uuid4())
    assignment = _make_assignment(
        policy_summary=_make_policy_summary(policy_id),
        model_summary=_make_model_summary(model_id),
    )
    attestation_rule = _make_attestation_rule(policy_id=policy_id)
    policy = _make_policy(policy_id, attestation_rules=[attestation_rule])

    job, job_spec = _make_job_and_spec(model_id)

    # Setup mocks
    policies_client.list_model_policy_assignments.return_value = _paginated_response(
        [assignment]
    )
    policies_client.get_policy.return_value = policy
    policies_client.list_model_attestations.return_value = _paginated_response(
        [
            _make_attestation_record(
                rule_id=attestation_rule.id,
                assignment_id=assignment.id,
                model_id=model_id,
                next_due=NOW + timedelta(days=60),  # valid
            ),
        ]
    )
    alert_rules_client.get_model_alert_rules.return_value = _paginated_response([])

    executor.execute(job, job_spec)

    # Verify COMPLIANT status was reported
    set_call = policies_client.set_compliance_status.call_args
    detail = set_call.kwargs["set_compliance_status_request"].compliance_status
    assert detail.status == ComplianceStatus.COMPLIANT
    assert len(detail.attestation_rules.compliant) == 1
    assert len(detail.attestation_rules.non_compliant) == 0
    assert len(detail.alert_rules.compliant) == 0
    assert len(detail.alert_rules.non_compliant) == 0

    # Verify metrics were uploaded
    metrics_client.post_model_metrics_version.assert_called_once()
    metrics_client.post_model_metrics_by_version.assert_called_once()


@patch("job_executors.compliance_policy_check_executor.datetime")
def test_missing_attestation_non_compliant(mock_datetime):
    """When an attestation rule has no attestation record, status is NON_COMPLIANT (enforcement in past)."""
    mock_datetime.now.return_value = NOW
    mock_datetime.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)

    executor, policies_client, alert_rules_client, alerts_client, metrics_client, _, _ = (
        _make_executor()
    )

    model_id = str(uuid4())
    policy_id = str(uuid4())
    assignment = _make_assignment(
        policy_summary=_make_policy_summary(policy_id),
        model_summary=_make_model_summary(model_id),
        enforcement_in_past=True,
    )
    attestation_rule = _make_attestation_rule(policy_id=policy_id)
    policy = _make_policy(policy_id, attestation_rules=[attestation_rule])

    job, job_spec = _make_job_and_spec(model_id)

    policies_client.list_model_policy_assignments.return_value = _paginated_response(
        [assignment]
    )
    policies_client.get_policy.return_value = policy
    policies_client.list_model_attestations.return_value = _paginated_response(
        []
    )  # no attestations
    alert_rules_client.get_model_alert_rules.return_value = _paginated_response([])

    executor.execute(job, job_spec)

    detail = policies_client.set_compliance_status.call_args.kwargs[
        "set_compliance_status_request"
    ].compliance_status
    assert detail.status == ComplianceStatus.NON_COMPLIANT
    assert len(detail.attestation_rules.non_compliant) == 1
    assert detail.attestation_rules.non_compliant[0].id == attestation_rule.id


@patch("job_executors.compliance_policy_check_executor.datetime")
def test_lapsed_attestation_non_compliant(mock_datetime):
    """When an attestation has expired (next_due in past), status is NON_COMPLIANT."""
    mock_datetime.now.return_value = NOW
    mock_datetime.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)

    executor, policies_client, alert_rules_client, alerts_client, metrics_client, _, _ = (
        _make_executor()
    )

    model_id = str(uuid4())
    policy_id = str(uuid4())
    assignment = _make_assignment(
        policy_summary=_make_policy_summary(policy_id),
        model_summary=_make_model_summary(model_id),
    )
    attestation_rule = _make_attestation_rule(policy_id=policy_id)
    policy = _make_policy(policy_id, attestation_rules=[attestation_rule])

    job, job_spec = _make_job_and_spec(model_id)

    policies_client.list_model_policy_assignments.return_value = _paginated_response(
        [assignment]
    )
    policies_client.get_policy.return_value = policy
    policies_client.list_model_attestations.return_value = _paginated_response(
        [
            _make_attestation_record(
                rule_id=attestation_rule.id,
                assignment_id=assignment.id,
                model_id=model_id,
                next_due=NOW - timedelta(days=1),  # expired
            ),
        ]
    )
    alert_rules_client.get_model_alert_rules.return_value = _paginated_response([])

    executor.execute(job, job_spec)

    detail = policies_client.set_compliance_status.call_args.kwargs[
        "set_compliance_status_request"
    ].compliance_status
    assert detail.status == ComplianceStatus.NON_COMPLIANT
    assert len(detail.attestation_rules.non_compliant) == 1


@patch("job_executors.compliance_policy_check_executor.datetime")
def test_alert_violation_non_compliant(mock_datetime):
    """When an alert exists for a policy alert rule, status is NON_COMPLIANT and alert is included."""
    mock_datetime.now.return_value = NOW
    mock_datetime.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)

    executor, policies_client, alert_rules_client, alerts_client, metrics_client, _, _ = (
        _make_executor()
    )

    model_id = str(uuid4())
    policy_id = str(uuid4())
    assignment = _make_assignment(
        policy_summary=_make_policy_summary(policy_id),
        model_summary=_make_model_summary(model_id),
    )
    policy = _make_policy(policy_id)

    alert_rule = _make_alert_rule(model_id=model_id)
    triggering_alert = _make_alert(alert_rule_id=alert_rule.id, model_id=model_id)

    job, job_spec = _make_job_and_spec(model_id)

    policies_client.list_model_policy_assignments.return_value = _paginated_response(
        [assignment]
    )
    policies_client.get_policy.return_value = policy
    policies_client.list_model_attestations.return_value = _paginated_response([])
    alert_rules_client.get_model_alert_rules.return_value = _paginated_response(
        [alert_rule]
    )
    alerts_client.get_model_alerts.return_value = _paginated_response(
        [triggering_alert]
    )

    executor.execute(job, job_spec)

    detail = policies_client.set_compliance_status.call_args.kwargs[
        "set_compliance_status_request"
    ].compliance_status
    assert detail.status == ComplianceStatus.NON_COMPLIANT
    assert len(detail.alert_rules.non_compliant) == 1
    assert detail.alert_rules.non_compliant[0].id == alert_rule.id
    assert detail.alert_rules.non_compliant[0].alert.id == triggering_alert.id
    assert (
        detail.alert_rules.non_compliant[0].alert.description
        == triggering_alert.description
    )


@patch("job_executors.compliance_policy_check_executor.datetime")
def test_violation_before_enforcement_needs_attention(mock_datetime):
    """When there's a violation but enforcement hasn't started, status is NEEDS_ATTENTION."""
    mock_datetime.now.return_value = NOW
    mock_datetime.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)

    executor, policies_client, alert_rules_client, alerts_client, metrics_client, _, _ = (
        _make_executor()
    )

    model_id = str(uuid4())
    policy_id = str(uuid4())
    assignment = _make_assignment(
        policy_summary=_make_policy_summary(policy_id),
        model_summary=_make_model_summary(model_id),
        enforcement_in_past=False,  # enforcement in the future
    )
    attestation_rule = _make_attestation_rule(policy_id=policy_id)
    policy = _make_policy(policy_id, attestation_rules=[attestation_rule])

    job, job_spec = _make_job_and_spec(model_id)

    policies_client.list_model_policy_assignments.return_value = _paginated_response(
        [assignment]
    )
    policies_client.get_policy.return_value = policy
    policies_client.list_model_attestations.return_value = _paginated_response(
        []
    )  # missing attestation
    alert_rules_client.get_model_alert_rules.return_value = _paginated_response([])

    executor.execute(job, job_spec)

    detail = policies_client.set_compliance_status.call_args.kwargs[
        "set_compliance_status_request"
    ].compliance_status
    assert detail.status == ComplianceStatus.NEEDS_ATTENTION


@patch("job_executors.compliance_policy_check_executor.datetime")
def test_single_assignment_filter(mock_datetime):
    """When policy_assignment_id is set, it's passed through to the API call."""
    mock_datetime.now.return_value = NOW
    mock_datetime.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)

    executor, policies_client, alert_rules_client, alerts_client, metrics_client, _, _ = (
        _make_executor()
    )

    model_id = str(uuid4())
    assignment_id = str(uuid4())
    assignment = _make_assignment()
    policy = _make_policy(assignment.policy.id)

    job, job_spec = _make_job_and_spec(model_id, assignment_id=assignment_id)

    policies_client.list_model_policy_assignments.return_value = _paginated_response(
        [assignment]
    )
    policies_client.get_policy.return_value = policy
    policies_client.list_model_attestations.return_value = _paginated_response([])
    alert_rules_client.get_model_alert_rules.return_value = _paginated_response([])

    executor.execute(job, job_spec)

    # Verify assignment_id was passed to the API
    list_call = policies_client.list_model_policy_assignments.call_args
    assert list_call.kwargs["assignment_id"] == assignment_id


@patch("job_executors.compliance_policy_check_executor.datetime")
def test_fault_tolerance_across_assignments(mock_datetime):
    """When one assignment fails, others are still processed, and the job raises at the end."""
    mock_datetime.now.return_value = NOW
    mock_datetime.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)

    (
        executor,
        policies_client,
        alert_rules_client,
        alerts_client,
        metrics_client, 
        _,
        logger,
    ) = _make_executor()

    model_id = str(uuid4())
    assignment_1 = _make_assignment(model_summary=_make_model_summary(model_id))
    assignment_2 = _make_assignment(model_summary=_make_model_summary(model_id))

    job, job_spec = _make_job_and_spec(model_id)

    policies_client.list_model_policy_assignments.return_value = _paginated_response(
        [assignment_1, assignment_2]
    )

    # First assignment's get_policy raises, second succeeds
    policy_2 = _make_policy(assignment_2.policy.id)
    call_count = {"n": 0}

    def get_policy_side_effect(policy_id):
        call_count["n"] += 1
        if call_count["n"] == 1:
            raise Exception("Simulated failure for assignment 1")
        return policy_2

    policies_client.get_policy.side_effect = get_policy_side_effect
    policies_client.list_model_attestations.return_value = _paginated_response([])
    alert_rules_client.get_model_alert_rules.return_value = _paginated_response([])

    with pytest.raises(RuntimeError, match="1/2 assignment"):
        executor.execute(job, job_spec)

    # Verify both were attempted
    assert policies_client.get_policy.call_count == 2

    # Verify the second assignment still got its status set
    policies_client.set_compliance_status.assert_called_once()
    set_call = policies_client.set_compliance_status.call_args
    assert set_call.kwargs["assignment_id"] == str(assignment_2.id)

    # Verify error was logged
    assert logger.error.call_count == 1


@patch("job_executors.compliance_policy_check_executor.datetime")
def test_mixed_alert_rules_compliant_and_non_compliant(mock_datetime):
    """Alert rules with no alerts pass; those with alerts fail. Both appear in the detail."""
    mock_datetime.now.return_value = NOW
    mock_datetime.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)

    executor, policies_client, alert_rules_client, alerts_client, metrics_client, _, _ = (
        _make_executor()
    )

    model_id = str(uuid4())
    policy_id = str(uuid4())
    assignment = _make_assignment(
        policy_summary=_make_policy_summary(policy_id),
        model_summary=_make_model_summary(model_id),
    )
    policy = _make_policy(policy_id)

    passing_rule = _make_alert_rule(rule_id="passing-rule", model_id=model_id)
    failing_rule = _make_alert_rule(rule_id="failing-rule", model_id=model_id)
    triggering_alert = _make_alert(alert_rule_id="failing-rule", model_id=model_id)

    job, job_spec = _make_job_and_spec(model_id)

    policies_client.list_model_policy_assignments.return_value = _paginated_response(
        [assignment]
    )
    policies_client.get_policy.return_value = policy
    policies_client.list_model_attestations.return_value = _paginated_response([])
    alert_rules_client.get_model_alert_rules.return_value = _paginated_response(
        [passing_rule, failing_rule]
    )
    alerts_client.get_model_alerts.side_effect = _alerts_side_effect(
        {"failing-rule": [triggering_alert], "passing-rule": []}
    )

    executor.execute(job, job_spec)

    detail = policies_client.set_compliance_status.call_args.kwargs[
        "set_compliance_status_request"
    ].compliance_status
    assert detail.status == ComplianceStatus.NON_COMPLIANT
    assert len(detail.alert_rules.compliant) == 1
    assert detail.alert_rules.compliant[0].id == "passing-rule"
    assert len(detail.alert_rules.non_compliant) == 1
    assert detail.alert_rules.non_compliant[0].id == "failing-rule"


@patch("job_executors.compliance_policy_check_executor.datetime")
def test_metrics_uploaded_with_correct_dimensions(mock_datetime):
    """Verify compliance metrics include policy_name, model_name, and status dimensions."""
    mock_datetime.now.return_value = NOW
    mock_datetime.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)

    executor, policies_client, alert_rules_client, alerts_client, metrics_client, _, _ = (
        _make_executor()
    )

    model_id = str(uuid4())
    policy_id = str(uuid4())
    policy_summary = _make_policy_summary(policy_id)
    model_summary = _make_model_summary(model_id)
    assignment = _make_assignment(
        policy_summary=policy_summary,
        model_summary=model_summary,
    )
    attestation_rule = _make_attestation_rule(policy_id=policy_id)
    policy = _make_policy(policy_id, attestation_rules=[attestation_rule])

    job, job_spec = _make_job_and_spec(model_id)

    policies_client.list_model_policy_assignments.return_value = _paginated_response(
        [assignment]
    )
    policies_client.get_policy.return_value = policy
    policies_client.list_model_attestations.return_value = _paginated_response(
        [
            _make_attestation_record(
                rule_id=attestation_rule.id,
                assignment_id=assignment.id,
                model_id=model_id,
            ),
        ]
    )
    alert_rules_client.get_model_alert_rules.return_value = _paginated_response([])

    executor.execute(job, job_spec)

    # Check that post_model_metrics_by_version was called
    upload_call = metrics_client.post_model_metrics_by_version.call_args
    upload = upload_call.kwargs["metrics_upload"]

    # Should have 2 metrics: 1 compliance check + 1 attestation check
    assert len(upload.metrics) == 2

    # Check compliance metric dimensions
    compliance_metric = upload.metrics[0].actual_instance
    dim_names = {d.name for d in compliance_metric.numeric_series[0].dimensions}
    assert "policy_id" in dim_names
    assert "policy_name" in dim_names
    assert "assignment_id" in dim_names
    assert "model_name" in dim_names
    assert "status" in dim_names

    # Check attestation metric dimensions
    attestation_metric = upload.metrics[1].actual_instance
    att_dim_names = {d.name for d in attestation_metric.numeric_series[0].dimensions}
    assert "attestation_rule_id" in att_dim_names
    assert "attestation_rule_name" in att_dim_names
    assert "policy_name" in att_dim_names
    assert "model_name" in att_dim_names


@patch("job_executors.compliance_policy_check_executor.datetime")
def test_alert_rule_metrics_uploaded_with_correct_dimensions(mock_datetime):
    """Verify alert rule metrics include alert_rule_id, alert_rule_name, and status dimensions."""
    mock_datetime.now.return_value = NOW
    mock_datetime.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)

    executor, policies_client, alert_rules_client, alerts_client, metrics_client, _, _ = (
        _make_executor()
    )

    model_id = str(uuid4())
    policy_id = str(uuid4())
    policy_summary = _make_policy_summary(policy_id)
    model_summary = _make_model_summary(model_id)
    assignment = _make_assignment(
        policy_summary=policy_summary,
        model_summary=model_summary,
    )

    alert_rule = _make_alert_rule(rule_id="failing-rule", model_id=model_id)
    # Distinct alert timestamp from NOW so we can verify the metric is keyed
    # to the alert, not the check run.
    alert_ts = NOW - timedelta(minutes=17)
    alert = _make_alert(
        alert_rule_id="failing-rule", model_id=model_id, timestamp=alert_ts
    )
    policy_alert_rule = PolicyAlertRule(
        id="failing-rule",
        policy_id=policy_id,
        name=alert_rule.name,
        threshold=alert_rule.threshold,
        bound=alert_rule.bound,
        query=alert_rule.query,
        metric_name=alert_rule.metric_name,
        interval=alert_rule.interval,
        created_at=NOW,
        updated_at=NOW,
    )
    policy = _make_policy(policy_id, alert_rules=[policy_alert_rule])

    job, job_spec = _make_job_and_spec(model_id)

    policies_client.list_model_policy_assignments.return_value = _paginated_response(
        [assignment]
    )
    policies_client.get_policy.return_value = policy
    policies_client.list_model_attestations.return_value = _paginated_response([])
    alert_rules_client.get_model_alert_rules.return_value = _paginated_response(
        [alert_rule]
    )
    alerts_client.get_model_alerts.return_value = _paginated_response([alert])

    executor.execute(job, job_spec)

    upload_call = metrics_client.post_model_metrics_by_version.call_args
    upload = upload_call.kwargs["metrics_upload"]

    # Should have 2 metrics: 1 compliance check + 1 alert rule check (no attestation rules)
    assert len(upload.metrics) == 2

    # First metric is the overall compliance check
    compliance_metric = upload.metrics[0].actual_instance
    assert compliance_metric.name == "policy_compliance_check_count"

    # Second metric is the alert rule check
    alert_metric = upload.metrics[1].actual_instance
    assert alert_metric.name == "policy_alert_rule_check_count"
    alert_dims = {d.name: d.value for d in alert_metric.numeric_series[0].dimensions}
    assert "policy_id" in alert_dims
    assert "policy_name" in alert_dims
    assert "assignment_id" in alert_dims
    assert "model_name" in alert_dims
    assert "alert_rule_id" in alert_dims
    assert "alert_rule_name" in alert_dims
    # Violations carry the alert's id so re-runs collapse to one row.
    assert alert_dims["alert_id"] == alert.id

    # Verify violation count is 1 since one alert fired
    assert alert_metric.numeric_series[0].values[0].value == 1.0
    # Timestamp is the alert's timestamp aligned to 5min, not the check run.
    expected_ts = alert_ts.replace(
        minute=(alert_ts.minute // 5) * 5, second=0, microsecond=0
    )
    assert alert_metric.numeric_series[0].values[0].timestamp == expected_ts


@patch("job_executors.compliance_policy_check_executor.datetime")
def test_alert_rule_metric_is_one_for_violation(mock_datetime):
    """The alert-rule metric value is a 0/1 violation flag, not a count.
    Even if many alerts exist in the latest bucket, value is 1.0 when violating."""
    mock_datetime.now.return_value = NOW
    mock_datetime.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)

    executor, policies_client, alert_rules_client, alerts_client, metrics_client, _, _ = (
        _make_executor()
    )

    model_id = str(uuid4())
    policy_id = str(uuid4())
    assignment = _make_assignment(
        policy_summary=_make_policy_summary(policy_id),
        model_summary=_make_model_summary(model_id),
    )
    policy = _make_policy(policy_id)

    alert_rule = _make_alert_rule(rule_id="multi-alert-rule", model_id=model_id)
    alerts = [
        _make_alert(alert_rule_id="multi-alert-rule", model_id=model_id)
        for _ in range(3)
    ]

    job, job_spec = _make_job_and_spec(model_id)

    policies_client.list_model_policy_assignments.return_value = _paginated_response(
        [assignment]
    )
    policies_client.get_policy.return_value = policy
    policies_client.list_model_attestations.return_value = _paginated_response([])
    alert_rules_client.get_model_alert_rules.return_value = _paginated_response(
        [alert_rule]
    )
    alerts_client.get_model_alerts.return_value = _paginated_response(alerts)

    executor.execute(job, job_spec)

    upload = metrics_client.post_model_metrics_by_version.call_args.kwargs[
        "metrics_upload"
    ]
    alert_metric = upload.metrics[1].actual_instance
    assert alert_metric.name == "policy_alert_rule_check_count"
    assert alert_metric.numeric_series[0].values[0].value == 1.0


@patch("job_executors.compliance_policy_check_executor.datetime")
def test_alert_outside_latest_bucket_is_compliant(mock_datetime):
    """An alert exists in the window but outside the rule's latest interval bucket
    → rule is reported compliant. This is the regression that motivated the change:
    a long-lookback manual check no longer pins a rule as non-compliant on stale alerts.
    """
    mock_datetime.now.return_value = NOW
    mock_datetime.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)

    executor, policies_client, alert_rules_client, alerts_client, metrics_client, _ = (
        _make_executor()
    )

    model_id = str(uuid4())
    policy_id = str(uuid4())
    assignment = _make_assignment(
        policy_summary=_make_policy_summary(policy_id),
        model_summary=_make_model_summary(model_id),
    )
    policy = _make_policy(policy_id)

    # 1h interval → latest bucket is (NOW - 1h, NOW]. The alert at NOW - 6h is in
    # the broader 24h check window but outside that bucket. The API would not return
    # it for the per-rule query (time_from=NOW-1h), so the mock returns no records.
    alert_rule = _make_alert_rule(
        rule_id="hourly-rule",
        model_id=model_id,
        interval=AlertRuleInterval(unit=IntervalUnit.HOURS, count=1),
    )

    job, job_spec = _make_job_and_spec(model_id)

    policies_client.list_model_policy_assignments.return_value = _paginated_response(
        [assignment]
    )
    policies_client.get_policy.return_value = policy
    policies_client.list_model_attestations.return_value = _paginated_response([])
    alert_rules_client.get_model_alert_rules.return_value = _paginated_response(
        [alert_rule]
    )
    alerts_client.get_model_alerts.return_value = _paginated_response([])

    executor.execute(job, job_spec)

    detail = policies_client.set_compliance_status.call_args.kwargs[
        "set_compliance_status_request"
    ].compliance_status
    assert detail.status == ComplianceStatus.COMPLIANT
    assert len(detail.alert_rules.compliant) == 1
    assert detail.alert_rules.compliant[0].id == "hourly-rule"
    assert len(detail.alert_rules.non_compliant) == 0

    upload = metrics_client.post_model_metrics_by_version.call_args.kwargs[
        "metrics_upload"
    ]
    alert_metric = upload.metrics[1].actual_instance
    assert alert_metric.name == "policy_alert_rule_check_count"
    assert alert_metric.numeric_series[0].values[0].value == 0.0


@patch("job_executors.compliance_policy_check_executor.datetime")
def test_per_rule_query_uses_rule_interval(mock_datetime):
    """Each rule is queried with time_from = window_end - rule.interval, so two rules
    with different intervals get different per-rule queries."""
    mock_datetime.now.return_value = NOW
    mock_datetime.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)

    executor, policies_client, alert_rules_client, alerts_client, metrics_client, _ = (
        _make_executor()
    )

    model_id = str(uuid4())
    policy_id = str(uuid4())
    assignment = _make_assignment(
        policy_summary=_make_policy_summary(policy_id),
        model_summary=_make_model_summary(model_id),
    )
    policy = _make_policy(policy_id)

    minute_rule = _make_alert_rule(
        rule_id="minute-rule",
        model_id=model_id,
        interval=AlertRuleInterval(unit=IntervalUnit.MINUTES, count=1),
    )
    hour_rule = _make_alert_rule(
        rule_id="hour-rule",
        model_id=model_id,
        interval=AlertRuleInterval(unit=IntervalUnit.HOURS, count=1),
    )

    # Hour rule has an alert in its latest bucket (timestamp = NOW - 30min — inside
    # (NOW - 1h, NOW]); minute rule has none. Expect mixed verdicts.
    hour_alert = _make_alert(
        alert_rule_id="hour-rule",
        model_id=model_id,
        timestamp=NOW - timedelta(minutes=30),
        interval=hour_rule.interval,
    )

    job, job_spec = _make_job_and_spec(model_id)

    policies_client.list_model_policy_assignments.return_value = _paginated_response(
        [assignment]
    )
    policies_client.get_policy.return_value = policy
    policies_client.list_model_attestations.return_value = _paginated_response([])
    alert_rules_client.get_model_alert_rules.return_value = _paginated_response(
        [minute_rule, hour_rule]
    )
    alerts_client.get_model_alerts.side_effect = _alerts_side_effect(
        {"hour-rule": [hour_alert], "minute-rule": []}
    )

    executor.execute(job, job_spec)

    # Verify time_from values: per-rule sliding window of 2*rule.interval back
    # from window_end. The 2x ensures we always catch the latest completed
    # bucket regardless of how window_end aligns to bucket boundaries.
    calls = alerts_client.get_model_alerts.call_args_list
    by_rule = {c.kwargs["alert_rule_ids"][0]: c.kwargs for c in calls}
    assert by_rule["minute-rule"]["time_from"] == NOW - timedelta(minutes=2)
    assert by_rule["minute-rule"]["time_to"] == NOW
    assert by_rule["hour-rule"]["time_from"] == NOW - timedelta(hours=2)
    assert by_rule["hour-rule"]["time_to"] == NOW
    assert by_rule["minute-rule"]["page_size"] == 1
    assert by_rule["hour-rule"]["page_size"] == 1

    detail = policies_client.set_compliance_status.call_args.kwargs[
        "set_compliance_status_request"
    ].compliance_status
    assert detail.status == ComplianceStatus.NON_COMPLIANT
    compliant_ids = {r.id for r in detail.alert_rules.compliant}
    non_compliant_ids = {r.id for r in detail.alert_rules.non_compliant}
    assert compliant_ids == {"minute-rule"}
    assert non_compliant_ids == {"hour-rule"}


@patch("job_executors.compliance_policy_check_executor.datetime")
def test_alert_rule_metric_has_no_status_dimension(mock_datetime):
    """The alert-rule metric must not carry a `status` dimension. The dashboard
    chart query reads `value` directly for this metric — adding a status dim would
    silently change its semantics."""
    mock_datetime.now.return_value = NOW
    mock_datetime.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)

    executor, policies_client, alert_rules_client, alerts_client, metrics_client, _ = (
        _make_executor()
    )

    model_id = str(uuid4())
    policy_id = str(uuid4())
    assignment = _make_assignment(
        policy_summary=_make_policy_summary(policy_id),
        model_summary=_make_model_summary(model_id),
    )
    policy = _make_policy(policy_id)
    alert_rule = _make_alert_rule(rule_id="any-rule", model_id=model_id)
    alert = _make_alert(alert_rule_id="any-rule", model_id=model_id)

    job, job_spec = _make_job_and_spec(model_id)

    policies_client.list_model_policy_assignments.return_value = _paginated_response(
        [assignment]
    )
    policies_client.get_policy.return_value = policy
    policies_client.list_model_attestations.return_value = _paginated_response([])
    alert_rules_client.get_model_alert_rules.return_value = _paginated_response(
        [alert_rule]
    )
    alerts_client.get_model_alerts.return_value = _paginated_response([alert])

    executor.execute(job, job_spec)

    upload = metrics_client.post_model_metrics_by_version.call_args.kwargs[
        "metrics_upload"
    ]
    alert_metric = upload.metrics[1].actual_instance
    assert alert_metric.name == "policy_alert_rule_check_count"
    dim_names = {d.name for d in alert_metric.numeric_series[0].dimensions}
    assert "status" not in dim_names


@patch("job_executors.compliance_policy_check_executor.datetime")
def test_alert_rule_metric_emits_zero_for_passing_rule(mock_datetime):
    """A passing alert rule emits a violation count of 0."""
    mock_datetime.now.return_value = NOW
    mock_datetime.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)

    executor, policies_client, alert_rules_client, alerts_client, metrics_client, _, _ = (
        _make_executor()
    )

    model_id = str(uuid4())
    policy_id = str(uuid4())
    assignment = _make_assignment(
        policy_summary=_make_policy_summary(policy_id),
        model_summary=_make_model_summary(model_id),
    )
    policy = _make_policy(policy_id)

    alert_rule = _make_alert_rule(rule_id="clean-rule", model_id=model_id)

    job, job_spec = _make_job_and_spec(model_id)

    policies_client.list_model_policy_assignments.return_value = _paginated_response(
        [assignment]
    )
    policies_client.get_policy.return_value = policy
    policies_client.list_model_attestations.return_value = _paginated_response([])
    alert_rules_client.get_model_alert_rules.return_value = _paginated_response(
        [alert_rule]
    )
    alerts_client.get_model_alerts.return_value = _paginated_response([])  # no alerts

    executor.execute(job, job_spec)

    upload = metrics_client.post_model_metrics_by_version.call_args.kwargs[
        "metrics_upload"
    ]
    alert_metric = upload.metrics[1].actual_instance
    assert alert_metric.name == "policy_alert_rule_check_count"
    assert alert_metric.numeric_series[0].values[0].value == 0.0


# ---------------------------------------------------------------------------
# Guardrail check tests
# ---------------------------------------------------------------------------


@patch("job_executors.compliance_policy_check_executor.datetime")
def test_guardrail_not_enabled_non_compliant(mock_datetime):
    """When a policy requires a guardrail that is not enabled on the model, status is NON_COMPLIANT."""
    mock_datetime.now.return_value = NOW
    mock_datetime.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)

    executor, policies_client, alert_rules_client, alerts_client, metrics_client, tasks_client, _ = _make_executor()

    model_id = str(uuid4())
    policy_id = str(uuid4())
    assignment = _make_assignment(
        policy_summary=_make_policy_summary(policy_id),
        model_summary=_make_model_summary(model_id),
    )

    pii_alert_rule = _make_policy_alert_rule(dependent_resource=PolicyAlertGuardrailRule(name=RuleType.PIIDATARULE), policy_id=policy_id)
    policy = _make_policy(policy_id, alert_rules=[pii_alert_rule])
    materialized_pii = _make_alert_rule(
        model_id=model_id,
        policy_alert_rule_id=pii_alert_rule.id,
        name="PII Detection",
    )

    job, job_spec = _make_job_and_spec(model_id)

    policies_client.list_model_policy_assignments.return_value = _paginated_response([assignment])
    policies_client.get_policy.return_value = policy
    policies_client.list_model_attestations.return_value = _paginated_response([])
    alert_rules_client.get_model_alert_rules.return_value = _paginated_response([materialized_pii])
    alerts_client.get_model_alerts.return_value = _paginated_response([])
    # Task has no rules enabled
    tasks_client.get_task_state_cache.return_value = _make_task_read_response([])

    executor.execute(job, job_spec)

    detail = policies_client.set_compliance_status.call_args.kwargs["set_compliance_status_request"].compliance_status
    assert detail.status == ComplianceStatus.NON_COMPLIANT
    assert len(detail.alert_rules.non_compliant) == 1
    assert detail.alert_rules.non_compliant[0].id == materialized_pii.id
    assert "PIIDataRule is not enabled" in detail.alert_rules.non_compliant[0].alert.description


@patch("job_executors.compliance_policy_check_executor.datetime")
def test_guardrail_enabled_but_no_data_non_compliant(mock_datetime):
    """When a guardrail is enabled but has no data in the last 7 days, status is NON_COMPLIANT."""
    mock_datetime.now.return_value = NOW
    mock_datetime.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)

    executor, policies_client, alert_rules_client, alerts_client, metrics_client, tasks_client, _ = _make_executor()

    model_id = str(uuid4())
    policy_id = str(uuid4())
    assignment = _make_assignment(
        policy_summary=_make_policy_summary(policy_id),
        model_summary=_make_model_summary(model_id),
    )

    pii_alert_rule = _make_policy_alert_rule(dependent_resource=PolicyAlertGuardrailRule(name=RuleType.PIIDATARULE), policy_id=policy_id)
    policy = _make_policy(policy_id, alert_rules=[pii_alert_rule])
    materialized_pii = _make_alert_rule(
        model_id=model_id,
        policy_alert_rule_id=pii_alert_rule.id,
        name="PII Detection",
    )

    job, job_spec = _make_job_and_spec(model_id)

    policies_client.list_model_policy_assignments.return_value = _paginated_response([assignment])
    policies_client.get_policy.return_value = policy
    policies_client.list_model_attestations.return_value = _paginated_response([])
    alert_rules_client.get_model_alert_rules.return_value = _paginated_response([materialized_pii])
    alerts_client.get_model_alerts.return_value = _paginated_response([])
    tasks_client.get_task_state_cache.return_value = _make_task_read_response(["PIIDataRule"])
    metrics_client.post_model_metrics_query.return_value = _make_metrics_query_result(has_data=False)

    executor.execute(job, job_spec)

    detail = policies_client.set_compliance_status.call_args.kwargs["set_compliance_status_request"].compliance_status
    assert detail.status == ComplianceStatus.NON_COMPLIANT
    assert len(detail.alert_rules.non_compliant) == 1
    assert "has not received data" in detail.alert_rules.non_compliant[0].alert.description


@patch("job_executors.compliance_policy_check_executor.datetime")
def test_guardrail_enabled_and_has_data_compliant(mock_datetime):
    """When a guardrail is enabled and has data, the guardrail check passes."""
    mock_datetime.now.return_value = NOW
    mock_datetime.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)

    executor, policies_client, alert_rules_client, alerts_client, metrics_client, tasks_client, _ = _make_executor()

    model_id = str(uuid4())
    policy_id = str(uuid4())
    assignment = _make_assignment(
        policy_summary=_make_policy_summary(policy_id),
        model_summary=_make_model_summary(model_id),
    )

    pii_alert_rule = _make_policy_alert_rule(dependent_resource=PolicyAlertGuardrailRule(name=RuleType.PIIDATARULE), policy_id=policy_id)
    policy = _make_policy(policy_id, alert_rules=[pii_alert_rule])
    materialized_pii = _make_alert_rule(
        model_id=model_id,
        policy_alert_rule_id=pii_alert_rule.id,
        name="PII Detection",
    )

    job, job_spec = _make_job_and_spec(model_id)

    policies_client.list_model_policy_assignments.return_value = _paginated_response([assignment])
    policies_client.get_policy.return_value = policy
    policies_client.list_model_attestations.return_value = _paginated_response([])
    alert_rules_client.get_model_alert_rules.return_value = _paginated_response([materialized_pii])
    alerts_client.get_model_alerts.return_value = _paginated_response([])
    tasks_client.get_task_state_cache.return_value = _make_task_read_response(["PIIDataRule"])
    metrics_client.post_model_metrics_query.return_value = _make_metrics_query_result(has_data=True)

    executor.execute(job, job_spec)

    detail = policies_client.set_compliance_status.call_args.kwargs["set_compliance_status_request"].compliance_status
    assert detail.status == ComplianceStatus.COMPLIANT


@patch("job_executors.compliance_policy_check_executor.datetime")
def test_guardrail_custom_rule_type_skips_check(mock_datetime):
    """When a policy only has custom rule_type alert rules, no guardrail check is performed."""
    mock_datetime.now.return_value = NOW
    mock_datetime.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)

    executor, policies_client, alert_rules_client, alerts_client, metrics_client, tasks_client, _ = _make_executor()

    model_id = str(uuid4())
    policy_id = str(uuid4())
    assignment = _make_assignment(
        policy_summary=_make_policy_summary(policy_id),
        model_summary=_make_model_summary(model_id),
    )

    custom_alert_rule = _make_policy_alert_rule(dependent_resource=None, policy_id=policy_id)
    policy = _make_policy(policy_id, alert_rules=[custom_alert_rule])

    job, job_spec = _make_job_and_spec(model_id)

    policies_client.list_model_policy_assignments.return_value = _paginated_response([assignment])
    policies_client.get_policy.return_value = policy
    policies_client.list_model_attestations.return_value = _paginated_response([])
    alert_rules_client.get_model_alert_rules.return_value = _paginated_response([])

    executor.execute(job, job_spec)

    tasks_client.get_task_state_cache.assert_not_called()
    detail = policies_client.set_compliance_status.call_args.kwargs["set_compliance_status_request"].compliance_status
    assert detail.status == ComplianceStatus.COMPLIANT


@patch("job_executors.compliance_policy_check_executor.datetime")
def test_guardrail_before_enforcement_needs_attention(mock_datetime):
    """When guardrail fails but enforcement hasn't started, status is NEEDS_ATTENTION."""
    mock_datetime.now.return_value = NOW
    mock_datetime.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)

    executor, policies_client, alert_rules_client, alerts_client, metrics_client, tasks_client, _ = _make_executor()

    model_id = str(uuid4())
    policy_id = str(uuid4())
    assignment = _make_assignment(
        policy_summary=_make_policy_summary(policy_id),
        model_summary=_make_model_summary(model_id),
        enforcement_in_past=False,
    )

    pii_alert_rule = _make_policy_alert_rule(dependent_resource=PolicyAlertGuardrailRule(name=RuleType.PIIDATARULE), policy_id=policy_id)
    policy = _make_policy(policy_id, alert_rules=[pii_alert_rule])
    materialized_pii = _make_alert_rule(
        model_id=model_id,
        policy_alert_rule_id=pii_alert_rule.id,
        name="PII Detection",
    )

    job, job_spec = _make_job_and_spec(model_id)

    policies_client.list_model_policy_assignments.return_value = _paginated_response([assignment])
    policies_client.get_policy.return_value = policy
    policies_client.list_model_attestations.return_value = _paginated_response([])
    alert_rules_client.get_model_alert_rules.return_value = _paginated_response([materialized_pii])
    alerts_client.get_model_alerts.return_value = _paginated_response([])
    tasks_client.get_task_state_cache.return_value = _make_task_read_response([])

    executor.execute(job, job_spec)

    detail = policies_client.set_compliance_status.call_args.kwargs["set_compliance_status_request"].compliance_status
    assert detail.status == ComplianceStatus.NEEDS_ATTENTION


@patch("job_executors.compliance_policy_check_executor.datetime")
def test_guardrail_failure_without_materialized_rule_still_reported(mock_datetime):
    """Guardrail failure for a policy rule with no materialized alert rule
    still appears in non_compliant_alert_rules (fallback path)."""
    mock_datetime.now.return_value = NOW
    mock_datetime.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)

    executor, policies_client, alert_rules_client, alerts_client, metrics_client, tasks_client, _ = _make_executor()

    model_id = str(uuid4())
    policy_id = str(uuid4())
    assignment = _make_assignment(
        policy_summary=_make_policy_summary(policy_id),
        model_summary=_make_model_summary(model_id),
    )

    pii_alert_rule = _make_policy_alert_rule(dependent_resource=PolicyAlertGuardrailRule(name=RuleType.PIIDATARULE), policy_id=policy_id)
    policy = _make_policy(policy_id, alert_rules=[pii_alert_rule])

    job, job_spec = _make_job_and_spec(model_id)

    policies_client.list_model_policy_assignments.return_value = _paginated_response([assignment])
    policies_client.get_policy.return_value = policy
    policies_client.list_model_attestations.return_value = _paginated_response([])
    # No materialized alert rule for the policy rule
    alert_rules_client.get_model_alert_rules.return_value = _paginated_response([])
    tasks_client.get_task_state_cache.return_value = _make_task_read_response([])

    executor.execute(job, job_spec)

    detail = policies_client.set_compliance_status.call_args.kwargs["set_compliance_status_request"].compliance_status
    assert detail.status == ComplianceStatus.NON_COMPLIANT
    assert len(detail.alert_rules.non_compliant) == 1
    assert detail.alert_rules.non_compliant[0].id == pii_alert_rule.id
    assert detail.alert_rules.non_compliant[0].name == pii_alert_rule.name
    assert "PIIDataRule is not enabled" in detail.alert_rules.non_compliant[0].alert.description
