import logging

from cachetools import TTLCache
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from config.cache_config import cache_config
from db_models import DatabaseTaskToMetrics

CACHED_TASK_METRICS: TTLCache[str, list[str]] = TTLCache(
    maxsize=1000,
    ttl=cache_config.TASK_METRICS_CACHE_TTL,
)
logger = logging.getLogger(__name__)


class TasksMetricsRepository:
    def __init__(self, db_session: Session):
        self.db_session = db_session

    def get_task_metrics_ids_cached(self, task_id: str) -> list[str]:
        if not cache_config.TASK_METRICS_CACHE_ENABLED:
            return self._get_task_metrics_ids(task_id)
        CACHED_TASK_METRICS.expire()
        # Try to get from cache first
        cached_metrics = CACHED_TASK_METRICS.get(task_id)
        if cached_metrics is not None:
            logger.debug(f"Returning cached metrics for task {task_id}")
            return cached_metrics

        # If not in cache, query from DB
        logger.debug(f"Querying DB for metrics for task {task_id}")
        metrics = self._get_task_metrics_ids(task_id)
        # Store in cache for future use
        CACHED_TASK_METRICS[task_id] = metrics
        return metrics

    def _get_task_metrics_ids(
        self,
        task_id: str,
        only_enabled: bool = True,
    ) -> list[str]:
        statement = select(DatabaseTaskToMetrics).where(
            DatabaseTaskToMetrics.task_id == task_id,
        )
        if only_enabled:
            statement = statement.where(DatabaseTaskToMetrics.enabled == True)
        statement = statement.options(joinedload(DatabaseTaskToMetrics.task))
        result = self.db_session.execute(statement).unique().scalars().all()
        return [metric.metric_id for metric in result]

    def clear_cache(self) -> None:
        CACHED_TASK_METRICS.clear()
