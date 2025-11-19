import json
import logging
from typing import Any, Union

from arthur_common.models.metric_schemas import MetricRequest
from sqlalchemy import insert
from sqlalchemy.orm import Session

from db_models import DatabaseMetricResult
from dependencies import get_metrics_engine
from metrics_engine import MetricsEngine
from repositories.metrics_repository import MetricRepository
from repositories.tasks_metrics_repository import TasksMetricsRepository
from schemas.internal_schemas import MetricResult, Span
from utils import trace as trace_utils
from utils.constants import SPAN_KIND_LLM

logger = logging.getLogger(__name__)


class MetricsIntegrationService:
    """Service responsible for computing and integrating metrics with spans."""

    def __init__(
        self,
        db_session: Session,
        tasks_metrics_repo: TasksMetricsRepository,
        metrics_repo: MetricRepository,
    ):
        self.db_session = db_session
        self.tasks_metrics_repo = tasks_metrics_repo
        self.metrics_repo = metrics_repo

    def add_metrics_to_spans(
        self,
        spans: list[Span],
        compute_new_metrics: bool = True,
    ) -> list[Span]:
        """Add metrics to spans by computing missing metrics and embedding all results."""
        span_ids = [span.id for span in spans]
        existing_metric_results = self._get_metric_results_for_spans(span_ids)

        # Compute metrics for spans that don't have them (only if requested)
        if compute_new_metrics:
            spans_without_metrics = [
                span for span in spans if span.id not in existing_metric_results
            ]

            if spans_without_metrics:
                logger.info(
                    f"Need to calculate metrics for {len(spans_without_metrics)} spans",
                )

                logger.debug(
                    f"Computing metrics for {len(spans_without_metrics)} spans",
                )
                new_metric_results = self._compute_metrics_for_spans(
                    spans_without_metrics,
                )
                # Results are now stored as they're computed, so we just update the existing results
                existing_metric_results.update(new_metric_results)

        # Embed metrics into spans
        for span in spans:
            span.metric_results = existing_metric_results.get(span.id, [])

        return spans

    def compute_metrics_for_single_span(self, span: Span) -> list[MetricResult]:
        """Compute metrics for a single span and store them."""
        if not self._should_compute_metrics_for_span(span):
            return []

        try:
            metrics_engine = get_metrics_engine()
        except Exception as e:
            logger.error(f"Error getting metrics engine: {e}")
            return []

        try:
            results = self._compute_metrics_for_single_span(span, metrics_engine)
            if results:
                # Store results immediately as they're computed
                self._store_metric_results_for_span(span.id, results)
                return results
            return []
        except Exception as e:
            logger.error(f"Error computing metrics for span {span.id}: {e}")
            return []

    def get_metric_results_for_spans(
        self,
        span_ids: list[str],
    ) -> dict[str, list[MetricResult]]:
        """Get existing metric results for the given span IDs."""
        return self._get_metric_results_for_spans(span_ids)

    def _get_metric_results_for_spans(
        self,
        span_ids: list[str],
    ) -> dict[str, list[MetricResult]]:
        """Get existing metric results for the given span IDs."""
        if not span_ids:
            return {}

        metric_results = (
            self.db_session.query(DatabaseMetricResult)
            .filter(DatabaseMetricResult.span_id.in_(span_ids))
            .all()
        )

        # Group by span_id
        results_by_span: dict[str, list[MetricResult]] = {}
        for db_result in metric_results:
            span_id = db_result.span_id
            if span_id not in results_by_span:
                results_by_span[span_id] = []
            results_by_span[span_id].append(
                MetricResult._from_database_model(db_result),
            )

        return results_by_span

    def _compute_metrics_for_spans(
        self,
        spans: list[Span],
    ) -> dict[str, list[MetricResult]]:
        """Compute metrics for the given spans."""
        if not spans:
            return {}

        try:
            metrics_engine = get_metrics_engine()
        except Exception as e:
            logger.error(f"Error getting metrics engine: {e}")
            return {}

        metrics_results = {}

        logger.debug(f"Computing metrics for {len(spans)} spans")

        for span in spans:
            if not self._should_compute_metrics_for_span(span):
                continue

            try:
                results = self._compute_metrics_for_single_span(span, metrics_engine)
                if results:
                    # Store results immediately as they're computed
                    self._store_metric_results_for_span(span.id, results)
                    metrics_results[span.id] = results
            except Exception as e:
                logger.error(f"Error computing metrics for span {span.id}: {e}")
                continue

        total_metrics = sum(len(results) for results in metrics_results.values())
        logger.debug(f"Total metrics computed: {total_metrics}")

        return metrics_results

    def _should_compute_metrics_for_span(self, span: Span) -> bool:
        """Check if metrics should be computed for a given span."""
        if not span.task_id:
            logger.warning(
                f"Span {span.id} has no task_id, skipping metric computation",
            )
            return False

        if span.span_kind != SPAN_KIND_LLM:
            logger.debug(
                f"Skipping metric computation for span {span.id} - span kind is {span.span_kind}, not LLM",
            )
            return False

        return True

    def _compute_metrics_for_single_span(
        self,
        span: Span,
        metrics_engine: MetricsEngine,
    ) -> list[MetricResult]:
        """Compute metrics for a single span."""
        # Convert span to MetricRequest format
        span_request = self._span_to_metric_request(span)

        # Get metrics for this task
        metric_ids = self.tasks_metrics_repo.get_task_metrics_ids_cached(span.task_id)
        metrics = self.metrics_repo.get_metrics_by_metric_id(metric_ids)

        if not metrics:
            logger.debug(f"No metrics found for task {span.task_id}")
            return []

        # Compute metrics
        results = metrics_engine.evaluate(span_request, metrics)

        # Set span_id and metric_id on results
        metric_results = []
        for i, result in enumerate(results):
            if i < len(metrics):
                metric_id = metrics[i].id
                result.span_id = span.id
                result.metric_id = metric_id
                metric_results.append(result)

        logger.debug(f"Computed {len(results)} metrics for span {span.id}")
        return metric_results

    def _store_metric_results_for_span(
        self,
        span_id: str,
        results: list[MetricResult],
    ) -> None:
        """Store individual metric results for a specific span."""
        if not results:
            return

        metric_results_to_insert = [
            {
                "id": result.id,
                "created_at": result.created_at,
                "updated_at": result.updated_at,
                "metric_type": result.metric_type.value,
                "details": (result.details.model_dump() if result.details else None),
                "prompt_tokens": result.prompt_tokens,
                "completion_tokens": result.completion_tokens,
                "latency_ms": result.latency_ms,
                "span_id": span_id,
                "metric_id": result.metric_id,
            }
            for result in results
        ]

        if metric_results_to_insert:
            stmt = insert(DatabaseMetricResult).values(metric_results_to_insert)
            self.db_session.execute(stmt)
            self.db_session.commit()

            logger.info(
                f"Stored {len(metric_results_to_insert)} metric results for span {span_id} in database",
            )

        logger.debug(
            f"Stored {len(metric_results_to_insert)} metric results for span {span_id}",
        )

    def _span_to_metric_request(self, span: Span) -> MetricRequest:
        """Convert a Span to MetricRequest format for metric computation.

        Uses trace_utils.extract_span_features() to extract LLM-specific fields
        from raw_data for internal metrics computation.
        """

        # Extract features from raw_data for metrics computation
        span_features = trace_utils.extract_span_features(span.raw_data)

        system_prompt = span_features.get("system_prompt", "")
        user_query = span_features.get("user_query", "")
        context = span_features.get("context", [])
        response_data = span_features.get("response")
        response = (
            self._extract_response_content(response_data) if response_data else ""
        )

        return MetricRequest(
            system_prompt=system_prompt,
            user_query=user_query,
            context=context,
            response=response,
        )

    def _extract_response_content(
        self,
        response_data: Union[str, dict[str, str], Any],
    ) -> str:
        """Extract response content from span features."""
        if isinstance(response_data, str):
            return response_data
        elif isinstance(response_data, dict):
            if "content" in response_data:
                return response_data["content"]
            elif "tool_calls" in response_data:
                return json.dumps(response_data["tool_calls"])
            else:
                return json.dumps(response_data)
        else:
            return str(response_data)
