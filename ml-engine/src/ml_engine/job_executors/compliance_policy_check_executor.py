import logging
from datetime import datetime, timedelta, timezone
from typing import List, Optional, Set, Tuple

from arthur_client.api_bindings import (
    Alert,
)
from arthur_client.api_bindings import AlertRule as ClientAlertRule
from arthur_client.api_bindings import (
    AlertRulesV1Api,
    AlertsV1Api,
    ComplianceAlertRuleResults,
    ComplianceAlertSummary,
    ComplianceAttestationRuleResults,
    CompliancePolicyCheckJobSpec,
    ComplianceStatus,
    ComplianceStatusDetail,
    CompliantAlertRuleStatus,
    CompliantAttestationRuleStatus,
    Dimension,
    Job,
    MetricsUpload,
    MetricsUploadMetricsInner,
    MetricsV1Api,
    NonCompliantAlertRuleStatus,
    NonCompliantAttestationRuleStatus,
    NumericMetric,
    NumericPoint,
    NumericTimeSeries,
    PoliciesV1Api,
    Policy,
    PolicyAssignment,
    PolicyAttestationRule,
    PostMetricsQuery,
    PostMetricsQueryTimeRange,
    PostMetricsVersions,
    RuleType,
    SetComplianceStatusRequest,
    TasksV1Api,
)

_PAGE_SIZE = 100

_GUARDRAIL_DATA_LOOKBACK_DAYS = 7

# Guardrail rule types that require task enablement and data ingestion checks.
GUARDRAIL_RULE_TYPES: Set[str] = {
    RuleType.PIIDATARULE.value,
    RuleType.PROMPTINJECTIONRULE.value,
}


class GuardrailCheckResult:
    """Result of a single guardrail validation check."""

    def __init__(
        self,
        rule_type: str,
        enabled: bool,
        has_data: bool,
        reason: str,
    ) -> None:
        self.rule_type = rule_type
        self.enabled = enabled
        self.has_data = has_data
        self.reason = reason

    @property
    def passed(self) -> bool:
        return self.enabled and self.has_data


class CompliancePolicyCheckExecutor:
    def __init__(
        self,
        policies_client: PoliciesV1Api,
        alert_rules_client: AlertRulesV1Api,
        alerts_client: AlertsV1Api,
        metrics_client: MetricsV1Api,
        tasks_client: TasksV1Api,
        logger: logging.Logger,
    ) -> None:
        self.policies_client = policies_client
        self.alert_rules_client = alert_rules_client
        self.alerts_client = alerts_client
        self.metrics_client = metrics_client
        self.tasks_client = tasks_client
        self.logger = logger

    def execute(self, job: Job, job_spec: CompliancePolicyCheckJobSpec) -> None:
        model_id = job_spec.scope_model_id
        self._now = datetime.now(timezone.utc)
        self._alert_window_start = self._now - timedelta(hours=24)

        assignments = self._fetch_assignments(model_id, job_spec.policy_assignment_id)
        if not assignments:
            self.logger.info("No policy assignments found. Nothing to check.")
            return
        self.logger.info(
            f"Found {len(assignments)} policy assignments for model {model_id}... starting checks"
        )

        errors: list[Exception] = []
        for assignment in assignments:
            try:
                self._process_assignment(assignment, model_id)
            except Exception as e:
                self.logger.error(
                    f"Error checking compliance for assignment {assignment.id}",
                    exc_info=e,
                )
                errors.append(e)

        if errors:
            raise RuntimeError(
                f"Compliance check failed for {len(errors)}/{len(assignments)} assignment(s)"
            )

    def _process_assignment(
        self,
        assignment: PolicyAssignment,
        model_id: str,
    ) -> None:
        self.logger.info(
            f"Checking compliance for assignment {assignment.id} "
            f"(policy={assignment.policy.id}, model={assignment.model.id})"
        )
        policy = self.policies_client.get_policy(policy_id=assignment.policy.id)

        attestation_results = self._check_attestation_rules(
            assignment, policy.attestation_rules, self._now
        )
        alert_rule_results = self._check_alert_rules(assignment)
        guardrail_results = self._check_guardrail_rules(policy, model_id)

        has_violations = (
            any(not passed for _, passed, _ in attestation_results)
            or any(not passed for _, passed, _, _count in alert_rule_results)
            or any(not r.passed for r in guardrail_results)
        )

        status = self._resolve_status(
            has_violations, assignment.enforcement_starts_at, self._now
        )
        self.logger.info(f"Assignment {assignment.id} resolved to {status.value}")

        self._report_status(
            str(assignment.id),
            status,
            alert_rule_results,
            attestation_results,
            guardrail_results,
            policy,
        )
        self._write_compliance_metrics(
            model_id,
            assignment,
            status,
            attestation_results,
            alert_rule_results,
            self._now,
        )

    def _fetch_assignments(
        self,
        model_id: str,
        policy_assignment_id: Optional[str],
    ) -> List[PolicyAssignment]:
        all_records: List[PolicyAssignment] = []
        page = 1
        while True:
            resp = self.policies_client.list_model_policy_assignments(
                model_id=model_id,
                assignment_id=(
                    str(policy_assignment_id) if policy_assignment_id else None
                ),
                page=page,
                page_size=_PAGE_SIZE,
            )
            all_records.extend(resp.records)
            if len(resp.records) < _PAGE_SIZE:
                break
            page += 1
        return all_records

    def _check_attestation_rules(
        self,
        assignment: PolicyAssignment,
        attestation_rules: List[PolicyAttestationRule],
        now: datetime,
    ) -> List[Tuple[PolicyAttestationRule, bool, str]]:
        """Returns list of (rule, passed, reason) tuples."""
        if not attestation_rules:
            return []

        all_attestations = []
        page = 1
        while True:
            attestations_resp = self.policies_client.list_model_attestations(
                model_id=assignment.model.id,
                latest=True,
                valid=True,
                policy_assignment_id=str(assignment.id),
                page=page,
                page_size=_PAGE_SIZE,
            )
            all_attestations.extend(attestations_resp.records)
            if len(attestations_resp.records) < _PAGE_SIZE:
                break
            page += 1

        attestation_by_rule = {
            a.policy_attestation_rule_id: a for a in all_attestations
        }

        results: List[Tuple[PolicyAttestationRule, bool, str]] = []
        for rule in attestation_rules:
            attestation = attestation_by_rule.get(rule.id)
            if attestation is None:
                self.logger.info(f"Attestation rule {rule.id} ({rule.name}): MISSING")
                results.append((rule, False, "missing"))
            elif attestation.next_attestation_due <= now:
                self.logger.info(
                    f"Attestation rule {rule.id} ({rule.name}): LAPSED "
                    f"(due={attestation.next_attestation_due})"
                )
                results.append((rule, False, "lapsed"))
            else:
                self.logger.info(
                    f"Attestation rule {rule.id} ({rule.name}): CURRENT "
                    f"(due={attestation.next_attestation_due})"
                )
                results.append((rule, True, "current"))

        return results

    def _check_alert_rules(
        self,
        assignment: PolicyAssignment,
    ) -> List[Tuple[ClientAlertRule, bool, Optional[Alert], int]]:
        """Returns list of (alert_rule, passed, triggering_alert, violation_count) tuples."""
        self.logger.info(
            f"Fetching alert rules for model={assignment.model.id}, "
            f"assignment={assignment.id}"
        )
        alert_rules: List[ClientAlertRule] = []
        page = 1
        while True:
            alert_rules_resp = self.alert_rules_client.get_model_alert_rules(
                model_id=assignment.model.id,
                policy_model_assignment_id=str(assignment.id),
                page=page,
                page_size=_PAGE_SIZE,
            )
            self.logger.info(
                f"Alert rules page {page}: got {len(alert_rules_resp.records)} records"
            )
            alert_rules.extend(alert_rules_resp.records)
            if len(alert_rules_resp.records) < _PAGE_SIZE:
                break
            page += 1

        if not alert_rules:
            self.logger.info(
                f"No policy alert rules found for assignment={assignment.id} "
                f"on model={assignment.model.id}. "
                f"Check that alert rules are linked to this policy assignment."
            )
            return []

        alert_rule_ids = [r.id for r in alert_rules]
        self.logger.info(f"Found {len(alert_rules)} alert rules: {alert_rule_ids}")

        all_alerts: List[Alert] = []
        page = 1
        while True:
            alerts_resp = self.alerts_client.get_model_alerts(
                model_id=assignment.model.id,
                alert_rule_ids=alert_rule_ids,
                created_at_from=self._alert_window_start,
                created_at_to=self._now,
                page=page,
                page_size=_PAGE_SIZE,
            )
            all_alerts.extend(alerts_resp.records)
            if len(alerts_resp.records) < _PAGE_SIZE:
                break
            page += 1

        # Index first alert per rule and count total violations
        alert_by_rule_id: dict[str, Alert] = {}
        alert_count_by_rule_id: dict[str, int] = {}
        for alert in all_alerts:
            if alert.alert_rule_id not in alert_by_rule_id:
                alert_by_rule_id[alert.alert_rule_id] = alert
            alert_count_by_rule_id[alert.alert_rule_id] = (
                alert_count_by_rule_id.get(alert.alert_rule_id, 0) + 1
            )

        results: List[Tuple[ClientAlertRule, bool, Optional[Alert], int]] = []
        for rule in alert_rules:
            triggering_alert = alert_by_rule_id.get(rule.id)
            violation_count = alert_count_by_rule_id.get(rule.id, 0)
            if triggering_alert:
                self.logger.info(
                    f"Alert rule {rule.id} ({rule.name}): VIOLATION "
                    f"(alerts={violation_count}, first={triggering_alert.id})"
                )
                results.append((rule, False, triggering_alert, violation_count))
            else:
                self.logger.info(f"Alert rule {rule.id} ({rule.name}): PASSING")
                results.append((rule, True, None, 0))

        return results

    def _check_guardrail_rules(
        self,
        policy: Policy,
        model_id: str,
    ) -> List[GuardrailCheckResult]:
        """Validate that guardrail rule types on the policy are enabled on the
        model's task and have received data in the last 7 days."""
        required_types: Set[RuleType] = set()
        for alert_rule in policy.alert_rules:
            if alert_rule.rule_type in GUARDRAIL_RULE_TYPES:
                required_types.add(alert_rule.rule_type)

        if not required_types:
            return []

        self.logger.info(
            f"Policy {policy.id} requires guardrail types: {required_types}"
        )

        enabled_rule_types = self._get_enabled_guardrail_types(model_id)

        results: List[GuardrailCheckResult] = []
        for rule_type in sorted(required_types):
            is_enabled = rule_type in enabled_rule_types
            if not is_enabled:
                self.logger.info(
                    f"Guardrail {rule_type.value}: NOT ENABLED on model {model_id}"
                )
                results.append(
                    GuardrailCheckResult(
                        rule_type=rule_type,
                        enabled=False,
                        has_data=False,
                        reason=f"Guardrail {rule_type.value} is not enabled on this application",
                    )
                )
                continue

            has_data = self._has_guardrail_data(model_id, rule_type.value)
            if has_data:
                self.logger.info(f"Guardrail {rule_type.value}: ENABLED and has data")
            else:
                self.logger.info(
                    f"Guardrail {rule_type.value}: ENABLED but NO DATA in last "
                    f"{_GUARDRAIL_DATA_LOOKBACK_DAYS} days"
                )

            results.append(
                GuardrailCheckResult(
                    rule_type=rule_type,
                    enabled=True,
                    has_data=has_data,
                    reason=(
                        "ok"
                        if has_data
                        else f"Guardrail {rule_type.value} has not received data in the "
                        f"last {_GUARDRAIL_DATA_LOOKBACK_DAYS} days"
                    ),
                )
            )

        return results

    def _get_enabled_guardrail_types(self, model_id: str) -> Set[str]:
        """Fetch the model's cached task state and return the set of enabled
        guardrail rule types."""
        try:
            task_read = self.tasks_client.get_task_state_cache(model_id=model_id)
        except Exception as e:
            self.logger.warning(
                f"Could not fetch task state cache for model {model_id}: {e}"
            )
            return set()

        if task_read.task is None or not task_read.task.rules:
            return set()

        enabled: Set[str] = set()
        for rule in task_read.task.rules:
            if rule.enabled and rule.type and rule.type.value in GUARDRAIL_RULE_TYPES:
                enabled.add(rule.type.value)
        return enabled

    def _has_guardrail_data(self, model_id: str, rule_type: str) -> bool:
        """Check whether the model has received any rule_count metrics for the
        given guardrail rule_type in the last 7 days."""
        lookback_start = self._now - timedelta(days=_GUARDRAIL_DATA_LOOKBACK_DAYS)

        query = (
            "SELECT sum(value) AS metric_value, max(timestamp) AS metric_timestamp "
            "FROM metrics_numeric_latest_version "
            "WHERE metric_name = 'rule_count' "
            f"AND dimensions ->> 'rule_type' = '{rule_type}' "
            "AND timestamp >= '{{dateStart}}' AND timestamp < '{{dateEnd}}'"
        )

        try:
            result = self.metrics_client.post_model_metrics_query(
                model_id=model_id,
                post_metrics_query=PostMetricsQuery(
                    query=query,
                    time_range=PostMetricsQueryTimeRange(
                        start=lookback_start,
                        end=self._now,
                    ),
                    limit=1,
                ),
            )
            if not result.results:
                return False
            first = result.results[0]
            return first is not None and first.get("metric_value") is not None
        except Exception:
            self.logger.warning(
                f"Could not query metrics for guardrail {rule_type} "
                f"on model {model_id}. Treating as no data.",
                exc_info=True,
            )
            return False

    @staticmethod
    def _resolve_status(
        has_violations: bool,
        enforcement_starts_at: datetime,
        now: datetime,
    ) -> ComplianceStatus:
        if not has_violations:
            return ComplianceStatus.COMPLIANT
        if enforcement_starts_at > now:
            return ComplianceStatus.NEEDS_ATTENTION
        return ComplianceStatus.NON_COMPLIANT

    def _report_status(
        self,
        assignment_id: str,
        status: ComplianceStatus,
        alert_rule_results: List[Tuple[ClientAlertRule, bool, Optional[Alert], int]],
        attestation_results: List[Tuple[PolicyAttestationRule, bool, str]],
        guardrail_results: Optional[List[GuardrailCheckResult]] = None,
        policy: Optional[Policy] = None,
    ) -> None:
        # Build a map of rule_type to reason for failed guardrail checks
        guardrail_failed_rule_ids: dict[str, str] = {}
        if guardrail_results and policy:
            failed_by_type = {
                gr.rule_type: gr.reason for gr in guardrail_results if not gr.passed
            }
            for par in policy.alert_rules:
                if par.rule_type in failed_by_type:
                    guardrail_failed_rule_ids[str(par.id)] = failed_by_type[
                        par.rule_type
                    ]

        compliant_alert_rules: List[CompliantAlertRuleStatus] = []
        non_compliant_alert_rules: List[NonCompliantAlertRuleStatus] = []
        for rule, passed, triggering_alert, _violation_count in alert_rule_results:
            # Check if we failed the guardrail check
            guardrail_reason = guardrail_failed_rule_ids.get(
                rule.policy_alert_rule_id or ""
            )
            if guardrail_reason:
                non_compliant_alert_rules.append(
                    NonCompliantAlertRuleStatus(
                        id=rule.id,
                        name=rule.name,
                        alert=ComplianceAlertSummary(
                            id=rule.id,
                            description=guardrail_reason,
                        ),
                    )
                )
            elif passed:
                compliant_alert_rules.append(
                    CompliantAlertRuleStatus(id=rule.id, name=rule.name)
                )
            else:
                assert triggering_alert is not None
                non_compliant_alert_rules.append(
                    NonCompliantAlertRuleStatus(
                        id=rule.id,
                        name=rule.name,
                        alert=ComplianceAlertSummary(
                            id=triggering_alert.id,
                            description=triggering_alert.description or "",
                        ),
                    )
                )

        compliant_attestation_rules: List[CompliantAttestationRuleStatus] = []
        non_compliant_attestation_rules: List[NonCompliantAttestationRuleStatus] = []
        for rule, passed, _reason in attestation_results:
            if passed:
                compliant_attestation_rules.append(
                    CompliantAttestationRuleStatus(id=rule.id, name=rule.name)
                )
            else:
                non_compliant_attestation_rules.append(
                    NonCompliantAttestationRuleStatus(id=rule.id, name=rule.name)
                )

        detail = ComplianceStatusDetail(
            status=status,
            alert_rules=ComplianceAlertRuleResults(
                compliant=compliant_alert_rules,
                non_compliant=non_compliant_alert_rules,
            ),
            attestation_rules=ComplianceAttestationRuleResults(
                compliant=compliant_attestation_rules,
                non_compliant=non_compliant_attestation_rules,
            ),
        )

        self.policies_client.set_compliance_status(
            assignment_id=assignment_id,
            set_compliance_status_request=SetComplianceStatusRequest(
                compliance_status=detail,
            ),
        )

    @staticmethod
    def _align_to_5min(ts: datetime) -> datetime:
        """Floor a timestamp to the previous 5-minute boundary."""
        return ts.replace(minute=(ts.minute // 5) * 5, second=0, microsecond=0)

    def _write_compliance_metrics(
        self,
        model_id: str,
        assignment: PolicyAssignment,
        status: ComplianceStatus,
        attestation_results: List[Tuple[PolicyAttestationRule, bool, str]],
        alert_rule_results: List[Tuple[ClientAlertRule, bool, Optional[Alert], int]],
        now: datetime,
    ) -> None:
        metric_ts = self._align_to_5min(now)
        metrics: list[NumericMetric] = []

        # Overall compliance status metric (value=1 for counting, status in dimensions)
        metrics.append(
            NumericMetric(
                name="policy_compliance_check_count",
                numeric_series=[
                    NumericTimeSeries(
                        dimensions=[
                            Dimension(
                                name="policy_id",
                                value=str(assignment.policy.id),
                            ),
                            Dimension(
                                name="policy_name",
                                value=assignment.policy.name,
                            ),
                            Dimension(
                                name="assignment_id",
                                value=str(assignment.id),
                            ),
                            Dimension(
                                name="model_name",
                                value=assignment.model.name,
                            ),
                            Dimension(
                                name="status",
                                value=status.value,
                            ),
                        ],
                        values=[
                            NumericPoint(timestamp=metric_ts, value=1.0),
                        ],
                    ),
                ],
            )
        )

        # Per-attestation-rule status metric (value=1 for counting, status in dimensions)
        for rule, passed, _reason in attestation_results:
            metrics.append(
                NumericMetric(
                    name="policy_attestation_check_count",
                    numeric_series=[
                        NumericTimeSeries(
                            dimensions=[
                                Dimension(
                                    name="policy_id",
                                    value=str(assignment.policy.id),
                                ),
                                Dimension(
                                    name="policy_name",
                                    value=assignment.policy.name,
                                ),
                                Dimension(
                                    name="assignment_id",
                                    value=str(assignment.id),
                                ),
                                Dimension(
                                    name="model_name",
                                    value=assignment.model.name,
                                ),
                                Dimension(
                                    name="attestation_rule_id",
                                    value=str(rule.id),
                                ),
                                Dimension(
                                    name="attestation_rule_name",
                                    value=rule.name,
                                ),
                                Dimension(
                                    name="status",
                                    value="compliant" if passed else "non_compliant",
                                ),
                            ],
                            values=[
                                NumericPoint(timestamp=metric_ts, value=1.0),
                            ],
                        ),
                    ],
                )
            )

        # Per-alert-rule violation count metric
        for rule, _passed, _triggering_alert, violation_count in alert_rule_results:
            metrics.append(
                NumericMetric(
                    name="policy_alert_rule_check_count",
                    numeric_series=[
                        NumericTimeSeries(
                            dimensions=[
                                Dimension(
                                    name="policy_id",
                                    value=str(assignment.policy.id),
                                ),
                                Dimension(
                                    name="policy_name",
                                    value=assignment.policy.name,
                                ),
                                Dimension(
                                    name="assignment_id",
                                    value=str(assignment.id),
                                ),
                                Dimension(
                                    name="model_name",
                                    value=assignment.model.name,
                                ),
                                Dimension(
                                    name="alert_rule_id",
                                    value=str(rule.id),
                                ),
                                Dimension(
                                    name="alert_rule_name",
                                    value=rule.name,
                                ),
                            ],
                            values=[
                                NumericPoint(
                                    timestamp=metric_ts, value=float(violation_count)
                                ),
                            ],
                        ),
                    ],
                )
            )

        if not metrics:
            return

        metrics_version = self.metrics_client.post_model_metrics_version(
            model_id=model_id,
            post_metrics_versions=PostMetricsVersions(
                range_start=metric_ts,
                range_end=metric_ts,
            ),
        )

        upload = MetricsUpload(metrics=[])
        for m in metrics:
            upload.metrics.append(MetricsUploadMetricsInner(actual_instance=m))

        self.metrics_client.post_model_metrics_by_version(
            model_id=model_id,
            metric_version_num=metrics_version.version_num,
            metrics_upload=upload,
        )
        self.logger.info(
            f"Wrote {len(metrics)} compliance metrics for assignment {assignment.id}"
        )
