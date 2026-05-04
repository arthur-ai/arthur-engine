import logging
from datetime import datetime
from typing import List, Optional, Tuple

from arthur_client.api_bindings import (
    Alert,
)
from arthur_client.api_bindings import AlertRule as ClientAlertRule
from arthur_client.api_bindings import (
    AlertRulesV1Api,
    AlertSort,
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
    PolicyAssignment,
    PolicyAttestationRule,
    PostMetricsVersions,
    SetComplianceStatusRequest,
    SortOrder,
)

from job_executors._interval_utils import alert_interval_to_timedelta

_PAGE_SIZE = 100


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
        # Window fields are Optional on the canonical spec (so historical rows
        # deserialize), but every chain-queued compliance job sets them. A None
        # here means we received a malformed or pre-migration spec — fail loudly
        # rather than silently querying alerts with no time bound.
        if (
            job_spec.check_range_start_timestamp is None
            or job_spec.check_range_end_timestamp is None
        ):
            raise ValueError(
                f"CompliancePolicyCheckJobSpec for job {job.id} is missing "
                "check_range_start_timestamp/check_range_end_timestamp; "
                "expected to be set by the upstream alert_check executor."
            )

        self._run_compliance_checks(
            model_id=job_spec.scope_model_id,
            window_start=job_spec.check_range_start_timestamp,
            window_end=job_spec.check_range_end_timestamp,
            policy_assignment_id=(
                str(job_spec.policy_assignment_id)
                if job_spec.policy_assignment_id is not None
                else None
            ),
        )

    def _run_compliance_checks(
        self,
        model_id: str,
        window_start: datetime,
        window_end: datetime,
        policy_assignment_id: Optional[str] = None,
    ) -> None:
        assignments = self._fetch_assignments(model_id, policy_assignment_id)
        if not assignments:
            self.logger.info("No policy assignments found. Nothing to check.")
            return
        self.logger.info(
            f"Found {len(assignments)} policy assignments for model {model_id}... starting checks"
        )

        errors: list[Exception] = []
        for assignment in assignments:
            try:
                self._process_assignment(assignment, model_id, window_start, window_end)
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
        window_start: datetime,
        window_end: datetime,
    ) -> None:
        self.logger.info(
            f"Checking compliance for assignment {assignment.id} "
            f"(policy={assignment.policy.id}, model={assignment.model.id})"
        )
        policy = self.policies_client.get_policy(policy_id=assignment.policy.id)

        attestation_results = self._check_attestation_rules(
            assignment, policy.attestation_rules, window_end
        )
        alert_rule_results = self._check_alert_rules(assignment, window_end)

        has_violations = any(not passed for _, passed, _ in attestation_results) or any(
            not passed for _, passed, _ in alert_rule_results
        )

        status = self._resolve_status(
            has_violations, assignment.enforcement_starts_at, window_end
        )
        self.logger.info(f"Assignment {assignment.id} resolved to {status.value}")

        self._report_status(
            str(assignment.id), status, alert_rule_results, attestation_results
        )
        self._write_compliance_metrics(
            model_id,
            assignment,
            status,
            attestation_results,
            alert_rule_results,
            window_end,
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
        window_end: datetime,
    ) -> List[Tuple[ClientAlertRule, bool, Optional[Alert]]]:
        """Returns list of (alert_rule, passed, triggering_alert) tuples.

        Per rule, query a sliding window of (window_end - 2*rule.interval,
        window_end] and report non-compliant iff any alert exists in there.

        Why 2*interval, not 1: alert timestamps land at fixed bucket
        boundaries, but window_end is arbitrary. The most recent completed
        bucket has a timestamp T satisfying window_end - 2*interval < T <=
        window_end - interval (worst case: window_end falls just before a
        boundary, so the latest completed bucket started almost 2 intervals
        ago). Looking back exactly 1 interval would miss the latest bucket
        whenever window_end is mid-bucket. 2 intervals always catches it,
        and at most one bucket fits in a 2-interval window so we can't pick
        up a stale older one — the user's window_start is irrelevant here
        because we only ever consider the latest bucket, never a sweep.
        """
        alert_rules = self._fetch_alert_rules(assignment)
        if not alert_rules:
            return []

        results: List[Tuple[ClientAlertRule, bool, Optional[Alert]]] = []
        for rule in alert_rules:
            sliding_window_start = window_end - 2 * alert_interval_to_timedelta(
                rule.interval
            )
            resp = self.alerts_client.get_model_alerts(
                model_id=assignment.model.id,
                alert_rule_ids=[rule.id],
                time_from=sliding_window_start,
                time_to=window_end,
                sort=AlertSort.TIMESTAMP,
                order=SortOrder.DESC,
                page=1,
                page_size=1,
            )
            triggering = resp.records[0] if resp.records else None
            if triggering is not None:
                self.logger.info(
                    f"Alert rule {rule.id} ({rule.name}): VIOLATION "
                    f"(latest_bucket_alert={triggering.id})"
                )
                results.append((rule, False, triggering))
            else:
                self.logger.info(f"Alert rule {rule.id} ({rule.name}): PASSING")
                results.append((rule, True, None))

        return results

    def _fetch_alert_rules(
        self,
        assignment: PolicyAssignment,
    ) -> List[ClientAlertRule]:
        self.logger.info(
            f"Fetching alert rules for model={assignment.model.id}, "
            f"assignment={assignment.id}"
        )
        alert_rules: List[ClientAlertRule] = []
        page = 1
        while True:
            resp = self.alert_rules_client.get_model_alert_rules(
                model_id=assignment.model.id,
                policy_model_assignment_id=str(assignment.id),
                page=page,
                page_size=_PAGE_SIZE,
            )
            self.logger.info(
                f"Alert rules page {page}: got {len(resp.records)} records"
            )
            alert_rules.extend(resp.records)
            if len(resp.records) < _PAGE_SIZE:
                break
            page += 1

        if not alert_rules:
            self.logger.info(
                f"No policy alert rules found for assignment={assignment.id} "
                f"on model={assignment.model.id}. "
                f"Check that alert rules are linked to this policy assignment."
            )
        else:
            self.logger.info(
                f"Found {len(alert_rules)} alert rules: {[r.id for r in alert_rules]}"
            )
        return alert_rules

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
        alert_rule_results: List[Tuple[ClientAlertRule, bool, Optional[Alert]]],
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

        # Per-alert-rule violation flag metric. value=1.0 if the rule's latest
        # interval bucket is currently violating, else 0.0. Dashboards read
        # `value` directly and SUM it over time to chart violations per rule.
        for rule, passed, _triggering_alert in alert_rule_results:
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
                                    timestamp=metric_ts,
                                    value=0.0 if passed else 1.0,
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
