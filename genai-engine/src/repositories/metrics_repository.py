import logging

from cachetools import TTLCache
from sqlalchemy.orm import Session

from db_models.db_models import DatabaseMetric
from schemas.internal_schemas import Metric
from arthur_common.models.request_schemas import UpdateMetricRequest

logger = logging.getLogger(__name__)

# Simple TTL cache for metrics - 5 minute TTL, 500 item max
METRICS_CACHE = TTLCache(maxsize=500, ttl=300)


class MetricRepository:
    def __init__(self, db_session: Session):
        self.db_session = db_session

    def create_metric(self, metric: Metric):
        database_metric = metric._to_database_model()
        self.db_session.add(database_metric)
        self.db_session.commit()
        # Clear cache entry if it exists
        METRICS_CACHE.pop(metric.id, None)

    def get_metric(self, metric_id: str) -> Metric:
        database_metric = (
            self.db_session.query(DatabaseMetric)
            .filter(DatabaseMetric.id == metric_id)
            .first()
        )
        return Metric._from_database_model(database_metric)

    def update_metric(self, metric_id: str, metric: UpdateMetricRequest):
        database_metric = (
            self.db_session.query(DatabaseMetric)
            .filter(DatabaseMetric.id == metric_id)
            .first()
        )
        if not database_metric:
            raise ValueError(f"Metric with id {metric_id} not found")

        database_metric.name = metric.name
        database_metric.metadata = metric.metadata

        self.db_session.commit()
        # Clear cache entry after update
        METRICS_CACHE.pop(metric_id, None)
        return Metric._from_database_model(database_metric)

    def archive_metric(self, metric_id: str):
        database_metric = (
            self.db_session.query(DatabaseMetric)
            .filter(DatabaseMetric.id == metric_id)
            .first()
        )
        if not database_metric:
            raise ValueError(f"Metric with id {metric_id} not found")

        database_metric.archived = True
        self.db_session.commit()
        # Clear cache entry after archive
        METRICS_CACHE.pop(metric_id, None)

    def get_metrics_by_metric_id(self, metric_ids: list[str]) -> list[Metric]:
        """
        Get metrics by IDs with caching to reduce database lookups.
        """
        if not metric_ids:
            return []

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
