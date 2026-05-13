import logging
from datetime import datetime
from typing import List, Optional, Set, Tuple

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
    Policy,
    PolicyAssignment,
    PolicyAttestationRule,
    PostMetricsVersions,
    RuleType,
    SetComplianceStatusRequest,
    SortOrder,
)

from connectors.shield_connector import ShieldBaseConnector
from job_executors._interval_utils import alert_interval_to_timedelta
from job_executors.task_management_job_executors import TaskManagementJobExecutor

_PAGE_SIZE = 100


class GuardrailCheckResult:
    """Result of a single guardrail validation check."""

    def __init__(
        self,
        rule_type: RuleType,
        enabled: bool,
        is_utilized: bool,
        reason: str,
    ) -> None:
        self.rule_type = rule_type
        self.enabled = enabled
        self.is_utilized = is_utilized
        self.reason = reason

    @property
    def passed(self) -> bool:
        return self.enabled and self.is_utilized


class CompliancePolicyCheckExecutor:
    def __init__(
        self,
        policies_client: PoliciesV1Api,
        alert_rules_client: AlertRulesV1Api,
        alerts_client: AlertsV1Api,
        metrics_client: MetricsV1Api,
        tasks_management_job_executor: TaskManagementJobExecutor,
        logger: logging.Logger,
    ) -> None:
        self.policies_client = policies_client
        self.alert_rules_client = alert_rules_client
        self.alerts_client = alerts_client
        self.metrics_client = metrics_client
        self.tasks_management_job_executor = tasks_management_job_executor
        self.logger = logger

    def execute(self, job: Job, job_spec: CompliancePolicyCheckJobSpec) -> None:
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
        guardrail_results = self._check_guardrail_rules(
            policy, model_id, window_start, window_end
        )

        has_violations = (
            any(not passed for _, passed, _ in attestation_results)
            or any(not passed for _, passed, _ in alert_rule_results)
            or any(not r.passed for r in guardrail_results)
        )

        status = self._resolve_status(
            has_violations, assignment.enforcement_starts_at, window_end
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

    def _check_guardrail_rules(
        self,
        policy: Policy,
        model_id: str,
        window_start: datetime,
        window_end: datetime,
    ) -> List[GuardrailCheckResult]:
        """Validate that guardrail rule types on the policy are enabled on the
        model's task and have received data within the check window."""
        required_types: Set[RuleType] = set()
        for alert_rule in policy.alert_rules:
            if (
                alert_rule.dependent_resource is not None
                and alert_rule.dependent_resource.resource_type == "guardrail"
            ):
                required_types.add(alert_rule.dependent_resource.resource_name)

        if not required_types:
            return []

        self.logger.info(
            f"Policy {policy.id} requires guardrail types: {required_types}"
        )

        try:
            _, _, conn, task_id = (
                self.tasks_management_job_executor.retrieve_task_management_resources_from_model_id(
                    model_id=model_id
                )
            )
        except Exception as e:
            self.logger.warning(
                f"Could not fetch task state cache for model {model_id}: {e}"
            )
            return []

        enabled_guardrail_types = self._get_enabled_guardrail_types(task_id, conn)

        results: List[GuardrailCheckResult] = []
        for rule_type in sorted(required_types):
            is_enabled = rule_type.value in enabled_guardrail_types
            if not is_enabled:
                self.logger.info(
                    f"Guardrail {rule_type.value}: NOT ENABLED on model {model_id}"
                )
                results.append(
                    GuardrailCheckResult(
                        rule_type=rule_type,
                        enabled=False,
                        is_utilized=False,
                        reason=f"Guardrail {rule_type.value} is not enabled on this application",
                    )
                )
                continue

            guardrail_utilized = self._is_guardrail_utilized(
                task_id, rule_type, window_start, window_end, conn
            )
            if guardrail_utilized:
                self.logger.info(f"Guardrail {rule_type.value}: ENABLED and utilized")
            else:
                self.logger.info(
                    f"Guardrail {rule_type.value}: ENABLED but NOT UTILIZED in the "
                    f"check window {window_start.isoformat()} to {window_end.isoformat()}"
                )

            results.append(
                GuardrailCheckResult(
                    rule_type=rule_type,
                    enabled=True,
                    is_utilized=guardrail_utilized,
                    reason=(
                        "ok"
                        if guardrail_utilized
                        else f"Guardrail {rule_type.value} has not run in the "
                        f"check window while new traces were received"
                    ),
                )
            )

        return results

    def _get_enabled_guardrail_types(
        self, task_id: str, conn: ShieldBaseConnector
    ) -> Set[str]:
        """Get all enabled guardrail rules for the specified task"""
        task_response = conn.read_task(task_id=task_id)

        enabled: Set[str] = set()
        for rule in task_response.rules:
            if rule.enabled:
                enabled.add(rule.type.value)
        return enabled

    def _is_guardrail_utilized(
        self,
        task_id: str,
        rule_type: RuleType,
        window_start: datetime,
        window_end: datetime,
        conn: ShieldBaseConnector,
    ) -> bool:
        """
        Checks whether the guardrail has run in the specified time period
        given that new traces were received in the same time period.

        This is meant to be used as an indicator that the application is
        being actively used, but they only have guardrails enabled to meet
        compliance and are not actually enforcing any guardrails.
        """

        try:
            num_traces = conn.list_trace_metadata(
                task_ids=[task_id], start_time=window_start, end_time=window_end
            ).count
        except Exception:
            self.logger.warning(
                f"Could not query traces for guardrail {rule_type} "
                f"on task {task_id}",
                exc_info=True,
            )
            return False

        try:
            num_inferences = conn.query_inferences(
                task_ids=[task_id],
                start_time=window_start,
                end_time=window_end,
                rule_types=[rule_type],
            ).count
        except Exception:
            self.logger.warning(
                f"Could not query inferences for guardrail {rule_type} "
                f"on task {task_id}",
                exc_info=True,
            )
            return False

        return not (num_traces > 0 and num_inferences == 0)

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
                if par.dependent_resource is None:
                    continue

                par_rule_type = par.dependent_resource.resource_name
                if par_rule_type in failed_by_type:
                    guardrail_failed_rule_ids[str(par.id)] = failed_by_type[
                        par_rule_type
                    ]

        compliant_alert_rules: List[CompliantAlertRuleStatus] = []
        non_compliant_alert_rules: List[NonCompliantAlertRuleStatus] = []
        for rule, passed, triggering_alert in alert_rule_results:
            # Check if we failed the guardrail check
            guardrail_reason = guardrail_failed_rule_ids.get(
                rule.policy_alert_rule_id or ""
            )
            if guardrail_reason:
                non_compliant_alert_rules.append(
                    NonCompliantAlertRuleStatus(
                        id=rule.id,
                        name=rule.name,
                        error_message=guardrail_reason,
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

        # Fall back to policy alert rule for any guardrail failure not covered
        # by a materialized alert rule above.
        covered_policy_rule_ids = {
            rule.policy_alert_rule_id for rule, *_ in alert_rule_results
        }
        if guardrail_results and policy:
            for par in policy.alert_rules:
                rule_id = str(par.id)
                if (
                    rule_id in guardrail_failed_rule_ids
                    and rule_id not in covered_policy_rule_ids
                ):
                    non_compliant_alert_rules.append(
                        NonCompliantAlertRuleStatus(
                            id=par.id,
                            name=par.name,
                            error_message=guardrail_failed_rule_ids[rule_id],
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
        #
        # For violations, key the metric to the triggering alert (its aligned
        # timestamp + id) instead of the check run. Re-running compliance over
        # the same persistent alert then produces metrics with identical
        # (model_id, metric_name, timestamp) tuples — the platform's existing
        # version-cleanup collapses them to one row, so dashboards stop
        # over-counting a single ongoing violation as N separate ones.
        for rule, passed, triggering_alert in alert_rule_results:
            dimensions = [
                Dimension(name="policy_id", value=str(assignment.policy.id)),
                Dimension(name="policy_name", value=assignment.policy.name),
                Dimension(name="assignment_id", value=str(assignment.id)),
                Dimension(name="model_name", value=assignment.model.name),
                Dimension(name="alert_rule_id", value=str(rule.id)),
                Dimension(name="alert_rule_name", value=rule.name),
            ]
            if passed:
                point_ts = metric_ts
                value = 0.0
            else:
                assert triggering_alert is not None
                point_ts = self._align_to_5min(triggering_alert.timestamp)
                value = 1.0
                dimensions.append(
                    Dimension(name="alert_id", value=str(triggering_alert.id))
                )

            metrics.append(
                NumericMetric(
                    name="policy_alert_rule_check_count",
                    numeric_series=[
                        NumericTimeSeries(
                            dimensions=dimensions,
                            values=[NumericPoint(timestamp=point_ts, value=value)],
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
