import logging
from datetime import datetime, timezone
from typing import List, Optional, Tuple

from arthur_client.api_bindings import (
    AlertRulesV1Api,
    AlertsV1Api,
    CompliancePolicyCheckJobSpec,
    ComplianceStatus,
    Job,
    MetricsUpload,
    MetricsUploadMetricsInner,
    MetricsV1Api,
    PoliciesV1Api,
    PolicyAssignment,
    PolicyAttestationRule,
    PostMetricsVersions,
    SetComplianceStatusRequest,
)
from arthur_common.models.metrics import (
    Dimension,
    NumericMetric,
    NumericTimeSeries,
)

COMPLIANCE_STATUS_METRIC = "policy_compliance_status"
ATTESTATION_STATUS_METRIC = "policy_attestation_status"

# Numeric encoding for compliance status metric
_STATUS_VALUE = {
    ComplianceStatus.COMPLIANT: 1.0,
    ComplianceStatus.NEEDS_ATTENTION: 2.0,
    ComplianceStatus.NON_COMPLIANT: 0.0,
}


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
        now = datetime.now(timezone.utc)

        assignments = self._fetch_assignments(model_id, job_spec.policy_assignment_id)
        if not assignments:
            self.logger.info("No policy assignments found. Nothing to check.")
            return

        for assignment in assignments:
            self.logger.info(
                f"Checking compliance for assignment {assignment.id} "
                f"(policy={assignment.policy.id}, model={assignment.model.id})"
            )
            attestation_rules = self.policies_client.list_policy_attestation_rules(
                policy_id=assignment.policy.id,
            ).records

            attestation_results = self._check_attestation_rules(
                assignment, attestation_rules, now
            )
            alert_violations = self._check_alert_rules(assignment)

            has_violations = (
                any(not passed for _, passed, _ in attestation_results)
                or len(alert_violations) > 0
            )

            status = self._resolve_status(
                has_violations, assignment.enforcement_starts_at, now
            )
            self.logger.info(f"Assignment {assignment.id} resolved to {status.value}")

            self._report_status(str(assignment.id), status)
            self._write_compliance_metrics(
                model_id, assignment, status, attestation_results, now
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

    def _check_alert_rules(self, assignment: PolicyAssignment) -> list:
        """Returns list of alerts found (any non-empty means violation)."""
        alert_rules_resp = self.alert_rules_client.get_model_alert_rules(
            model_id=assignment.model.id,
            policy_model_assignment_id=str(assignment.id),
        )
        alert_rule_ids = [r.id for r in alert_rules_resp.records]
        if not alert_rule_ids:
            self.logger.info("No policy alert rules for this assignment.")
            return []

        # TODO: scope time_from to last_compliance_checked_at once the field
        # is exposed on the PolicyAssignment response model.
        alerts_resp = self.alerts_client.get_model_alerts(
            model_id=assignment.model.id,
            alert_rule_ids=alert_rule_ids,
        )
        alerts = alerts_resp.records
        if alerts:
            self.logger.info(
                f"Found {len(alerts)} alert violation(s) across "
                f"{len(alert_rule_ids)} policy alert rules."
            )
        else:
            self.logger.info("No alert violations found.")
        return alerts

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

    def _report_status(self, assignment_id: str, status: ComplianceStatus) -> None:
        self.policies_client.set_compliance_status(
            assignment_id=assignment_id,
            set_compliance_status_request=SetComplianceStatusRequest(
                compliance_status=status,
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

        # Overall compliance status metric
        metrics.append(
            NumericMetric(
                name=COMPLIANCE_STATUS_METRIC,
                numeric_series=[
                    NumericTimeSeries(
                        timestamp=now,
                        value=_STATUS_VALUE[status],
                        dimensions=[
                            Dimension(
                                key="policy_id",
                                value=str(assignment.policy.id),
                            ),
                            Dimension(
                                key="assignment_id",
                                value=str(assignment.id),
                            ),
                        ],
                    ),
                ],
            )
        )

        # Per-attestation-rule status metric
        for rule, passed, _reason in attestation_results:
            metrics.append(
                NumericMetric(
                    name=ATTESTATION_STATUS_METRIC,
                    numeric_series=[
                        NumericTimeSeries(
                            timestamp=now,
                            value=1.0 if passed else 0.0,
                            dimensions=[
                                Dimension(
                                    key="policy_id",
                                    value=str(assignment.policy.id),
                                ),
                                Dimension(
                                    key="assignment_id",
                                    value=str(assignment.id),
                                ),
                                Dimension(
                                    key="attestation_rule_id",
                                    value=str(rule.id),
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
                range_start=now,
                range_end=now,
            ),
        )

        upload = MetricsUpload(metrics=[])
        for m in metrics:
            upload.metrics.append(
                MetricsUploadMetricsInner.from_json(m.model_dump_json())
            )

        self.metrics_client.post_model_metrics_by_version(
            model_id=model_id,
            metric_version_num=metrics_version.version_num,
            metrics_upload=upload,
        )
        self.logger.info(
            f"Wrote {len(metrics)} compliance metrics for assignment {assignment.id}"
        )
