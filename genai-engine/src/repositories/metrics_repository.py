import logging
from uuid import UUID

from cachetools import TTLCache
from sqlalchemy.orm import Session

from db_models import DatabaseMetric
from db_models.task_models import DatabaseTask
from db_models.telemetry_models import DatabaseTaskToMetrics
from schemas.internal_schemas import Metric

logger = logging.getLogger(__name__)

# Simple TTL cache for metrics - 5 minute TTL, 500 item max
METRICS_CACHE: TTLCache[str, Metric] = TTLCache(maxsize=500, ttl=300)


class MetricRepository:
    def __init__(self, db_session: Session):
        self.db_session = db_session

    def create_metric(self, metric: Metric) -> Metric:
        database_metric = metric._to_database_model()
        self.db_session.add(database_metric)
        self.db_session.commit()
        # Clear cache entry if it exists
        METRICS_CACHE.pop(metric.id, None)
        return Metric._from_database_model(database_metric)

    def get_metric_by_id(
        self,
        metric_id: str,
        org_scope: UUID | None = None,
    ) -> DatabaseMetric:
        # Metrics have no direct task_id; org isolation is via the
        # tasks_to_metrics link → tasks.org_id (Pattern C, design §7).
        query = self.db_session.query(DatabaseMetric).filter(
            DatabaseMetric.id == metric_id,
        )
        if org_scope is not None:
            query = (
                query.join(
                    DatabaseTaskToMetrics,
                    DatabaseTaskToMetrics.metric_id == DatabaseMetric.id,
                )
                .join(DatabaseTask, DatabaseTask.id == DatabaseTaskToMetrics.task_id)
                .filter(DatabaseTask.org_id == org_scope)
            )
        database_metric = query.first()
        if not database_metric:
            raise ValueError(f"Metric with id {metric_id} not found")
        return database_metric

    def get_metric(self, metric_id: str, org_scope: UUID | None = None) -> Metric:
        metric_obj_db = self.get_metric_by_id(metric_id, org_scope=org_scope)
        return Metric._from_database_model(metric_obj_db)

    def archive_metric(self, metric_id: str, commit: bool = True) -> None:
        database_metric = (
            self.db_session.query(DatabaseMetric)
            .filter(DatabaseMetric.id == metric_id)
            .first()
        )
        if not database_metric:
            raise ValueError(f"Metric with id {metric_id} not found")

        database_metric.archived = True
        if commit:
            self.db_session.commit()
        METRICS_CACHE.pop(metric_id, None)

    def unarchive_metric(self, metric_id: str, commit: bool = True) -> None:
        database_metric = (
            self.db_session.query(DatabaseMetric)
            .filter(DatabaseMetric.id == metric_id)
            .first()
        )
        if not database_metric:
            raise ValueError(f"Metric with id {metric_id} not found")
        database_metric.archived = False
        if commit:
            self.db_session.commit()
        METRICS_CACHE.pop(metric_id, None)

    def get_metrics_by_metric_id(
        self,
        metric_ids: list[str],
        org_scope: UUID | None = None,
    ) -> list[Metric]:
        """
        Get metrics by IDs with caching to reduce database lookups.
        """
        if not metric_ids:
            return []

        # When org-scoped, bypass the cache entirely: cache entries are keyed
        # by metric_id with no org dimension, so a hit could surface a metric
        # owned by another org. Filter at the DB layer via tasks_to_metrics →
        # tasks.org_id instead (Pattern C, design §7).
        if org_scope is not None:
            database_metrics = (
                self.db_session.query(DatabaseMetric)
                .join(
                    DatabaseTaskToMetrics,
                    DatabaseTaskToMetrics.metric_id == DatabaseMetric.id,
                )
                .join(DatabaseTask, DatabaseTask.id == DatabaseTaskToMetrics.task_id)
                .filter(DatabaseMetric.id.in_(metric_ids))
                .filter(DatabaseTask.org_id == org_scope)
                .distinct()
                .all()
            )
            metrics_dict = {
                db_metric.id: Metric._from_database_model(db_metric)
                for db_metric in database_metrics
            }
            return [metrics_dict[mid] for mid in metric_ids if mid in metrics_dict]

        # Check which metrics are in cache vs need DB lookup
        cached_metrics = []
        uncached_ids = []

        METRICS_CACHE.expire()  # Clean up expired entries

        for metric_id in metric_ids:
            cached_metric = METRICS_CACHE.get(metric_id)
            if cached_metric is not None:
                cached_metrics.append(cached_metric)
                logger.debug(f"Cache hit for metric {metric_id}")
            else:
                uncached_ids.append(metric_id)
                logger.debug(f"Cache miss for metric {metric_id}")

        # Fetch uncached metrics from database
        uncached_metrics = []
        if uncached_ids:
            logger.debug(f"Fetching {len(uncached_ids)} metrics from database")
            database_metrics = (
                self.db_session.query(DatabaseMetric)
                .filter(DatabaseMetric.id.in_(uncached_ids))
                .all()
            )

            for db_metric in database_metrics:
                metric = Metric._from_database_model(db_metric)
                uncached_metrics.append(metric)
                # Cache for future use
                METRICS_CACHE[metric.id] = metric

        # Combine cached and newly fetched metrics
        all_metrics = cached_metrics + uncached_metrics

        # Preserve the original order of metric_ids
        metrics_dict = {metric.id: metric for metric in all_metrics}
        ordered_metrics = [
            metrics_dict[mid] for mid in metric_ids if mid in metrics_dict
        ]

        logger.debug(
            f"Returned {len(ordered_metrics)} metrics ({len(cached_metrics)} from cache, {len(uncached_metrics)} from DB)",
        )
        return ordered_metrics
