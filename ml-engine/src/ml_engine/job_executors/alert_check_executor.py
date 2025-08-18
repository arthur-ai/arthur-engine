import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Union
from uuid import UUID

from arthur_client.api_bindings import (
    AlertBound,
    AlertCheckJobSpec,
    AlertRule,
    AlertRuleInterval,
    AlertRulesV1Api,
    AlertsV1Api,
    Job,
    JobsV1Api,
    MetricsQueryResult,
    MetricsResultFilterOp,
    MetricsV1Api,
    PostAlert,
    PostAlerts,
    PostMetricsQuery,
    PostMetricsQueryResultFilter,
    PostMetricsQueryResultFilterAndGroup,
    PostMetricsQueryResultFilterAndGroupAndInner,
    PostMetricsQueryTimeRange,
    ResultFilter,
)

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


class AlertCheckExecutor:
    def __init__(
        self,
        alerts_client: AlertsV1Api,
        alert_rules_client: AlertRulesV1Api,
        jobs_client: JobsV1Api,
        metrics_client: MetricsV1Api,
        logger: logging.Logger,
    ) -> None:
        self.alerts_client = alerts_client
        self.alert_rules_client = alert_rules_client
        self.jobs_client = jobs_client
        self.metrics_client = metrics_client
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
        try:
            query_response = self._query_model_metrics(job_spec, alert_rule)
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

        alerts = self._create_alerts(alert_rule, job.id, query_response.results)

        if not alerts:
            self.logger.info("No alerts found! Exiting.")
            return

        self._post_alerts(job_spec.scope_model_id, alert_rule.id, alerts)

    def _query_model_metrics(
        self,
        job_spec: AlertCheckJobSpec,
        alert_rule: AlertRule,
    ) -> MetricsQueryResult:

        # in order to prevent alerting on partial alert buckets, this function
        # queries the time range (start_time - interval, end_time)
        # see more info here:
        # https://gitlab.com/ArthurAI/arthur-scope/blob/f03cc26e11ea74f019be5b94a04f280b03d027ff/documentation/technical-documentation/implementations/Alert-Rule-Implementation.md#L291-291

        td = self._alert_interval_to_timedelta(alert_rule.interval)
        adjusted_start_time = job_spec.check_range_start_timestamp - td

        # similarly, to prevent alerting on partial alert buckets,
        # this function post-filters the results to be in the range
        # (start_time - interval, end_time - interval) so only the
        # buckets that had the entire interval in the query are reported.
        # This needs to be a post-filter so that all the data for the interval is
        # included in the original time_bucket aggregation, then we filter
        # on the post-aggregated results
        adjusted_end_time = job_spec.check_range_end_timestamp - td

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
                                    column=METRIC_VALUE_COLUMN_NAME,
                                    op=(
                                        MetricsResultFilterOp.GREATER_THAN
                                        if alert_rule.bound == AlertBound.UPPER_BOUND
                                        else MetricsResultFilterOp.LESS_THAN
                                    ),
                                    value=alert_rule.threshold,
                                ),
                            ),
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

    @staticmethod
    def _alert_interval_to_timedelta(interval: AlertRuleInterval) -> timedelta:
        kwargs = {interval.unit: interval.count}
        return timedelta(**kwargs)
