import logging
from datetime import datetime
from typing import List, Optional, Tuple

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
    Job,
    MetricsUpload,
    MetricsUploadMetricsInner,
    MetricsV1Api,
    NonCompliantAlertRuleStatus,
    NonCompliantAttestationRuleStatus,
    PoliciesV1Api,
    PolicyAssignment,
    PolicyAttestationRule,
    PostMetricsVersions,
    SetComplianceStatusRequest,
)
from arthur_common.models.metrics import (
    Dimension,
    NumericMetric,
    NumericPoint,
    NumericTimeSeries,
)


class CompliancePolicyCheckExecutor:
    def __init__(
        self,
        policies_client: PoliciesV1Api,
        alert_rules_client: AlertRulesV1Api,
        alerts_client: AlertsV1Api,
        metrics_client: MetricsV1Api,
        logger: logging.Logger,
    ) -> None:
        self.policies_client = policies_client
        self.alert_rules_client = alert_rules_client
        self.alerts_client = alerts_client
        self.metrics_client = metrics_client
        self.logger = logger

    def execute(self, job: Job, job_spec: CompliancePolicyCheckJobSpec) -> None:
        model_id = job_spec.scope_model_id

        assignments = self._fetch_assignments(model_id, job_spec.policy_assignment_id)
        if not assignments:
            self.logger.info("No policy assignments found. Nothing to check.")
            return
        self.logger.info(
            f"Found {len(assignments)} policy assignments for model {model_id}.. starting checks"
        )

        errors: list[Exception] = []
        for assignment in assignments:
            try:
                self._process_assignment(assignment, job_spec, model_id)
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
        job_spec: CompliancePolicyCheckJobSpec,
        model_id: str,
    ) -> None:
        self.logger.info(
            f"Checking compliance for assignment {assignment.id} "
            f"(policy={assignment.policy.id}, model={assignment.model.id})"
        )
        attestation_rules = self.policies_client.list_policy_attestation_rules(
            policy_id=assignment.policy.id,
        ).records

        attestation_results = self._check_attestation_rules(
            assignment, attestation_rules, job_spec.end_timestamp
        )
        alert_rule_results = self._check_alert_rules(
            assignment, job_spec.start_timestamp, job_spec.end_timestamp
        )

        has_violations = any(not passed for _, passed, _ in attestation_results) or any(
            not passed for _, passed, _ in alert_rule_results
        )

        status = self._resolve_status(
            has_violations, assignment.enforcement_starts_at, job_spec.end_timestamp
        )
        self.logger.info(f"Assignment {assignment.id} resolved to {status.value}")

        self._report_status(
            str(assignment.id), status, alert_rule_results, attestation_results
        )
        self._write_compliance_metrics(
            model_id, assignment, status, attestation_results, job_spec.end_timestamp
        )

    def _fetch_assignments(
        self,
        model_id: str,
        policy_assignment_id: Optional[str],
    ) -> List[PolicyAssignment]:
        resp = self.policies_client.list_model_policy_assignments(
            model_id=model_id,
            assignment_id=str(policy_assignment_id) if policy_assignment_id else None,
        )
        return resp.records

    def _check_attestation_rules(
        self,
        assignment: PolicyAssignment,
        attestation_rules: List[PolicyAttestationRule],
        now: datetime,
    ) -> List[Tuple[PolicyAttestationRule, bool, str]]:
        """Returns list of (rule, passed, reason) tuples."""
        if not attestation_rules:
            return []

        attestations_resp = self.policies_client.list_model_attestations(
            model_id=assignment.model.id,
            latest=True,
            valid=True,
            policy_assignment_id=str(assignment.id),
        )
        attestation_by_rule = {
            a.policy_attestation_rule_id: a for a in attestations_resp.records
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
        start_timestamp: datetime,
        end_timestamp: datetime,
    ) -> List[Tuple[ClientAlertRule, bool, Optional[Alert]]]:
        """Returns list of (alert_rule, passed, triggering_alert) tuples."""
        alert_rules_resp = self.alert_rules_client.get_model_alert_rules(
            model_id=assignment.model.id,
            policy_model_assignment_id=str(assignment.id),
        )
        alert_rules = alert_rules_resp.records
        if not alert_rules:
            self.logger.info("No policy alert rules for this assignment.")
            return []

        alert_rule_ids = [r.id for r in alert_rules]

        alerts_resp = self.alerts_client.get_model_alerts(
            model_id=assignment.model.id,
            alert_rule_ids=alert_rule_ids,
            time_from=start_timestamp,
            time_to=end_timestamp,
        )
        # Index first alert per rule (one is enough to prove violation)
        alert_by_rule_id: dict[str, Alert] = {}
        for alert in alerts_resp.records:
            if alert.alert_rule_id not in alert_by_rule_id:
                alert_by_rule_id[alert.alert_rule_id] = alert

        results: List[Tuple[ClientAlertRule, bool, Optional[Alert]]] = []
        for rule in alert_rules:
            triggering_alert = alert_by_rule_id.get(rule.id)
            if triggering_alert:
                self.logger.info(
                    f"Alert rule {rule.id} ({rule.name}): VIOLATION "
                    f"(alert={triggering_alert.id})"
                )
                results.append((rule, False, triggering_alert))
            else:
                self.logger.info(f"Alert rule {rule.id} ({rule.name}): PASSING")
                results.append((rule, True, None))

        return results

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
        alert_rule_results: List[Tuple[ClientAlertRule, bool, Optional[Alert]]],
        attestation_results: List[Tuple[PolicyAttestationRule, bool, str]],
    ) -> None:
        compliant_alert_rules: List[CompliantAlertRuleStatus] = []
        non_compliant_alert_rules: List[NonCompliantAlertRuleStatus] = []
        for rule, passed, triggering_alert in alert_rule_results:
            if passed:
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

    def _write_compliance_metrics(
        self,
        model_id: str,
        assignment: PolicyAssignment,
        status: ComplianceStatus,
        attestation_results: List[Tuple[PolicyAttestationRule, bool, str]],
        now: datetime,
    ) -> None:
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
                                name="assignment_id",
                                value=str(assignment.id),
                            ),
                            Dimension(
                                name="status",
                                value=status.value,
                            ),
                        ],
                        values=[
                            NumericPoint(timestamp=now, value=1.0),
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
                                    name="assignment_id",
                                    value=str(assignment.id),
                                ),
                                Dimension(
                                    name="attestation_rule_id",
                                    value=str(rule.id),
                                ),
                                Dimension(
                                    name="status",
                                    value="compliant" if passed else "non_compliant",
                                ),
                            ],
                            values=[
                                NumericPoint(timestamp=now, value=1.0),
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
                range_start=now,
                range_end=now,
            ),
        )

        upload = MetricsUpload(metrics=[])
        for m in metrics:
            upload.metrics.append(
                MetricsUploadMetricsInner(m)
            )

        self.metrics_client.post_model_metrics_by_version(
            model_id=model_id,
            metric_version_num=metrics_version.version_num,
            metrics_upload=upload,
        )
        self.logger.info(
            f"Wrote {len(metrics)} compliance metrics for assignment {assignment.id}"
        )
