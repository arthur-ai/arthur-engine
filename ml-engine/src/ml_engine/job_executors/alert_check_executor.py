import logging
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Union
from uuid import UUID

from arthur_client.api_bindings import (
    AlertBound,
    AlertCheckJobSpec,
    AlertLogStatus,
    AlertRule,
    AlertRulesV1Api,
    AlertsV1Api,
    CompliancePolicyCheckJobSpec,
    Job,
    JobsV1Api,
    MetricsQueryResult,
    MetricsResultFilterOp,
    MetricsV1Api,
    PoliciesV1Api,
    PolicyAssignmentJobChainPatch,
    PostAlert,
    PostAlertLog,
    PostAlertLogs,
    PostAlerts,
    PostJob,
    PostJobBatch,
    PostJobKind,
    PostJobSpec,
    PostMetricsQuery,
    PostMetricsQueryResultFilter,
    PostMetricsQueryResultFilterAndGroup,
    PostMetricsQueryResultFilterAndGroupAndInner,
    PostMetricsQueryTimeRange,
    ResultFilter,
)

from job_executors._chain_utils import stamp_chain_job_id
from job_executors._interval_utils import alert_interval_to_timedelta

METRIC_TIMESTAMP_COLUMN_NAME = "metric_timestamp"
METRIC_VALUE_COLUMN_NAME = "metric_value"

ALERT_RULES_QUERY_LIMIT = 50
ALERT_RULES_NON_ADDITIONAL_DIMENSION_FIELDS = [
    "model_id",
    "metric_name",
    METRIC_TIMESTAMP_COLUMN_NAME,
    METRIC_VALUE_COLUMN_NAME,
    "metric_version",
    "dimensions",
]
ALERT_RULES_SCALAR_TYPES = (str, int, float, bool, datetime, UUID)
TIME_BUCKET_ORIGIN = datetime(2000, 1, 3, tzinfo=timezone.utc)


def get_expected_bucket_timestamps(
    adjusted_start_time: datetime,
    adjusted_end_time: datetime,
    td: timedelta,
) -> List[datetime]:
    bucket_ts = adjusted_start_time - ((adjusted_start_time - TIME_BUCKET_ORIGIN) % td)
    if bucket_ts < adjusted_start_time:
        bucket_ts += td

    buckets = []
    while bucket_ts <= adjusted_end_time:
        buckets.append(bucket_ts)
        bucket_ts += td
    return buckets


class AlertCheckExecutor:
    def __init__(
        self,
        alerts_client: AlertsV1Api,
        alert_rules_client: AlertRulesV1Api,
        jobs_client: JobsV1Api,
        metrics_client: MetricsV1Api,
        policies_client: PoliciesV1Api,
        logger: logging.Logger,
    ) -> None:
        self.alerts_client = alerts_client
        self.alert_rules_client = alert_rules_client
        self.jobs_client = jobs_client
        self.metrics_client = metrics_client
        self.policies_client = policies_client
        self.logger = logger

    def execute(self, job: Job, job_spec: AlertCheckJobSpec) -> None:
        alert_rules = self._get_all_alert_rules(job_spec.scope_model_id)
        self.logger.info(f"Checking {len(alert_rules)} alert rules")
        processing_exc = None
        for alert_rule in alert_rules:
            try:
                self._process_alert_rule(alert_rule, job, job_spec)
            except Exception as e:
                self.logger.error(
                    f"Error creating alerts and processing alert rule {alert_rule.id}",
                    exc_info=e,
                )
                processing_exc = e

        # re-raise error so job is marked as failed if any alert rule was not processed
        if processing_exc:
            raise processing_exc

        self._submit_compliance_check_job(job, job_spec)

    def _submit_compliance_check_job(
        self,
        job: Job,
        job_spec: AlertCheckJobSpec,
    ) -> None:
        compliance_batch = PostJobBatch(
            jobs=[
                PostJob(
                    kind=PostJobKind.COMPLIANCE_POLICY_CHECK,
                    job_spec=PostJobSpec(
                        CompliancePolicyCheckJobSpec(
                            scope_model_id=job_spec.scope_model_id,
                            check_range_start_timestamp=job_spec.check_range_start_timestamp,
                            check_range_end_timestamp=job_spec.check_range_end_timestamp,
                            policy_assignment_id=job_spec.policy_assignment_id,
                        ),
                    ),
                ),
            ],
        )
        spawned = self.jobs_client.post_submit_jobs_batch(
            project_id=job.project_id,
            post_job_batch=compliance_batch,
        )
        self.logger.info(
            f"Submitted compliance policy check job for model {job_spec.scope_model_id} "
            f"(window {job_spec.check_range_start_timestamp} -> {job_spec.check_range_end_timestamp})"
        )
        # Stamp compliance_job_id on the affected assignment(s) so the FE
        # chain widget can advance from "alerts done" to "compliance running".
        # When this chain is bound to a single assignment (the policy/
        # assignment-level entry points), stamp just that one. When it's a
        # model-wide chain (POST /models/{id}/check_compliance), fan out to
        # every assignment on the model — the spawned compliance job will
        # evaluate each one.
        if spawned.jobs:
            stamp_chain_job_id(
                policies_client=self.policies_client,
                model_id=str(job_spec.scope_model_id),
                explicit_assignment_id=job_spec.policy_assignment_id,
                patch=PolicyAssignmentJobChainPatch(
                    compliance_job_id=spawned.jobs[0].id,
                ),
            )

    def _get_all_alert_rules(self, model_id: str) -> List[AlertRule]:
        alert_rules: List[AlertRule] = []
        page = 1
        page_size = 100
        while True:
            alert_rules_results = self.alert_rules_client.get_model_alert_rules(
                model_id,
                page=page,
                page_size=page_size,
            )
            alert_rules.extend(alert_rules_results.records)
            if len(alert_rules_results.records) < page_size:
                break
            page += 1
        return alert_rules

    def _process_alert_rule(
        self,
        alert_rule: AlertRule,
        job: Job,
        job_spec: AlertCheckJobSpec,
    ) -> None:
        self.logger.info(f"Checking alert rule {alert_rule.id}")
        td = alert_interval_to_timedelta(alert_rule.interval)
        adjusted_start_time = job_spec.check_range_start_timestamp - td
        adjusted_end_time = job_spec.check_range_end_timestamp - td

        try:
            query_response = self._query_model_metrics(
                job_spec,
                alert_rule,
                adjusted_start_time,
                adjusted_end_time,
            )
            self.logger.info(
                f"Query for alert rule {alert_rule.id} returned {len(query_response.results)} results",
            )
        except Exception as e:
            self.logger.error(
                f"Error querying metrics for alert rule {alert_rule.id}",
                exc_info=e,
            )
            raise e

        if len(query_response.results) > ALERT_RULES_QUERY_LIMIT:
            self.logger.warning(
                f"Query for alert rule {alert_rule.id} returned more than {ALERT_RULES_QUERY_LIMIT} results.",
            )

        results_by_ts: Dict[datetime, List[Dict[str, Any]]] = defaultdict(list)
        for r in query_response.results:
            ts = r[METRIC_TIMESTAMP_COLUMN_NAME]

            if isinstance(ts, str):
                ts = datetime.fromisoformat(ts)

            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)

            results_by_ts[ts.astimezone(timezone.utc)].append(r)

        expected_bucket_timestamps = get_expected_bucket_timestamps(
            adjusted_start_time,
            adjusted_end_time,
            td,
        )

        logs: List[PostAlertLog] = []
        fired_rows: List[Dict[str, Any]] = []
        for bucket_ts in expected_bucket_timestamps:
            rows = results_by_ts.get(bucket_ts.astimezone(timezone.utc), [])
            crossed = [
                r
                for r in rows
                if self._crosses_threshold(alert_rule, r[METRIC_VALUE_COLUMN_NAME])
            ]
            if not rows:
                status = AlertLogStatus.NO_DATA
            elif crossed:
                status = AlertLogStatus.FIRED
                fired_rows.extend(crossed)
            else:
                status = AlertLogStatus.OKAY
            logs.append(
                PostAlertLog(
                    alert_rule_id=alert_rule.id,
                    job_id=job.id,
                    policy_model_assignment_id=alert_rule.policy_model_assignment_id,
                    status=status,
                    timestamp=bucket_ts,
                )
            )

        alerts = self._create_alerts(alert_rule, job.id, fired_rows)
        if alerts:
            self._post_alerts(job_spec.scope_model_id, alert_rule.id, alerts)
        else:
            self.logger.info("No alerts found!")

        try:
            self.alerts_client.post_model_alert_logs(
                model_id=job_spec.scope_model_id,
                post_alert_logs=PostAlertLogs(logs=logs),
            )
        except Exception as e:
            self.logger.warning(
                f"Failed to post alert logs for alert rule {alert_rule.id}: {e}"
            )

    def _crosses_threshold(self, alert_rule: AlertRule, value: float) -> bool:
        if alert_rule.bound == AlertBound.UPPER_BOUND:
            return bool(value > alert_rule.threshold)
        return bool(value < alert_rule.threshold)

    def _query_model_metrics(
        self,
        job_spec: AlertCheckJobSpec,
        alert_rule: AlertRule,
        adjusted_start_time: datetime,
        adjusted_end_time: datetime,
    ) -> MetricsQueryResult:
        # in order to prevent alerting on partial alert buckets, this function
        # queries the time range (start_time - interval, end_time) and post-filters
        # results to (start_time - interval, end_time - interval) so only buckets
        # that had the entire interval in the query are reported.
        # see more info here:
        # https://gitlab.com/ArthurAI/arthur-scope/blob/f03cc26e11ea74f019be5b94a04f280b03d027ff/documentation/technical-documentation/implementations/Alert-Rule-Implementation.md#L291-291
        return self.metrics_client.post_model_metrics_query(
            model_id=job_spec.scope_model_id,
            post_metrics_query=PostMetricsQuery(
                query=alert_rule.query,
                time_range=PostMetricsQueryTimeRange(
                    start=adjusted_start_time,
                    end=job_spec.check_range_end_timestamp,
                ),
                interval=alert_rule.interval,
                limit=ALERT_RULES_QUERY_LIMIT + 1,
                result_filter=ResultFilter(
                    PostMetricsQueryResultFilterAndGroup(
                        var_and=[
                            PostMetricsQueryResultFilterAndGroupAndInner(
                                PostMetricsQueryResultFilter(
                                    column=METRIC_TIMESTAMP_COLUMN_NAME,
                                    op=MetricsResultFilterOp.GREATER_THAN_OR_EQUAL,
                                    value=adjusted_start_time,
                                ),
                            ),
                            PostMetricsQueryResultFilterAndGroupAndInner(
                                PostMetricsQueryResultFilter(
                                    column=METRIC_TIMESTAMP_COLUMN_NAME,
                                    op=MetricsResultFilterOp.LESS_THAN_OR_EQUAL,
                                    value=adjusted_end_time,
                                ),
                            ),
                        ],
                    ),
                ),
            ),
        )

    def _create_alerts(
        self,
        alert_rule: AlertRule,
        job_id: str,
        results: List[Dict[str, Any]],
    ) -> List[PostAlert]:
        alerts: List[PostAlert] = []
        for record in results[:ALERT_RULES_QUERY_LIMIT]:
            self.logger.info(f"Checking alert rule {alert_rule.id} for record {record}")
            try:
                alert = self._create_api_alert(alert_rule, job_id, record)
                alerts.append(alert)
            except Exception as e:
                self.logger.error(
                    f"Error during checking alert rule {alert_rule.id}",
                    exc_info=e,
                )
        return alerts

    def _create_api_alert(
        self,
        alert_rule: AlertRule,
        job_id: str,
        record: Dict[str, Any],
    ) -> PostAlert:
        metrics_value = record[METRIC_VALUE_COLUMN_NAME]
        alert_dimensions = self._create_alert_dimensions(record)
        self.logger.info(
            f"rule bound: {alert_rule.bound}, rule threshold: {alert_rule.threshold}, actual value: {metrics_value}",
        )
        alert_description = self._create_alert_description(alert_rule, metrics_value)
        return PostAlert(
            alert_rule_id=alert_rule.id,
            description=alert_description,
            threshold=alert_rule.threshold,
            bound=alert_rule.bound,
            interval=alert_rule.interval,
            timestamp=record[METRIC_TIMESTAMP_COLUMN_NAME],
            value=metrics_value,
            dimensions=alert_dimensions,
            job_id=job_id,
        )

    def _create_alert_dimensions(self, record: Dict[str, Any]) -> Dict[str, str]:
        alert_dimensions: Dict[str, str] = {}
        for key, value in record.items():
            if key in ALERT_RULES_NON_ADDITIONAL_DIMENSION_FIELDS:
                continue
            if not isinstance(value, ALERT_RULES_SCALAR_TYPES):
                self.logger.warning(
                    f"Skipping non-scalar value for column: {key}, value: {value}",
                )
                continue
            alert_dimensions[key] = str(value)
        return alert_dimensions

    def _create_alert_description(
        self,
        alert_rule: AlertRule,
        metrics_value: Union[int, float],
    ) -> str:
        alert_description_condition = (
            "above" if alert_rule.bound == AlertBound.UPPER_BOUND else "below"
        )
        return (
            f"{alert_rule.metric_name} value {metrics_value} is"
            f" {alert_description_condition} threshold {alert_rule.threshold}"
        )

    def _post_alerts(
        self,
        model_id: str,
        alert_rule_id: str,
        alerts: List[PostAlert],
    ) -> None:
        self.logger.info(f"Posting {len(alerts)} alerts for alert rule {alert_rule_id}")
        created_alerts = self.alerts_client.post_model_alerts(
            model_id=model_id,
            post_alerts=PostAlerts(alerts=alerts),
        )
        for alert in created_alerts.alerts:
            if alert.is_duplicate_of:
                self.logger.info(
                    f"Did not recreate alert for alert rule {alert_rule_id} with value {alert.value} for timestamp "
                    f"{alert.timestamp}. Alert already exists with id: {alert.is_duplicate_of}.",
                )
            else:
                self.logger.info(
                    f"Created alert {alert.id} for alert rule {alert_rule_id} with value {alert.value}",
                )

        if not created_alerts.webhooks_called:
            self.logger.info(f"No webhooks called for alert rule {alert_rule_id}")
            return

        for webhook_called in created_alerts.webhooks_called:
            if webhook_called.webhook_result.error or (
                webhook_called.webhook_result.response
                and webhook_called.webhook_result.response.status_code != 200
            ):
                self.logger.error(
                    f"Webhook {webhook_called.webhook_name} ({webhook_called.webhook_id}) "
                    f"failed with result {webhook_called.webhook_result}",
                )
            else:
                self.logger.info(
                    f"Webhook {webhook_called.webhook_name} ({webhook_called.webhook_id}) "
                    f"called with result {webhook_called.webhook_result}",
                )
