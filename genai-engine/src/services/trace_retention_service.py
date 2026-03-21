"""Background service that deletes trace data older than the configured retention period."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from dependencies import get_db_session
from repositories.configuration_repository import ConfigurationRepository
from repositories.trace_retention_repository import (
    DEFAULT_BATCH_SIZE,
    delete_trace_batch,
    get_expired_trace_ids,
)
from services.base_queue_service import BaseQueueJob, BaseQueueService
from utils.constants import DEFAULT_TRACE_RETENTION_DAYS

logger = logging.getLogger(__name__)

ONE_DAY_SECONDS = 24 * 3600
TRACE_RETENTION_JOB_KEY = "trace_retention"


class TraceRetentionJob(BaseQueueJob):
    """Job representing one run of the trace retention cleanup."""

    def __init__(self, delay_seconds: int = 0) -> None:
        super().__init__(delay_seconds=delay_seconds)


class TraceRetentionService(BaseQueueService[TraceRetentionJob]):
    """Background service that periodically deletes trace data older than the configured retention period."""

    job_model = TraceRetentionJob
    service_name = "trace_retention_service"
    background_thread_name = "trace-retention"

    def _get_job_key(self, job: TraceRetentionJob) -> str:
        return TRACE_RETENTION_JOB_KEY

    def _execute_job(self, job: TraceRetentionJob) -> None:
        """Run one retention pass: delete traces older than configured retention."""
        db_session = next(get_db_session())
        try:
            config_repo = ConfigurationRepository(db_session)
            config = config_repo.get_configurations()
            retention_days = getattr(
                config, "trace_retention_days", DEFAULT_TRACE_RETENTION_DAYS
            )
            cutoff = datetime.now(timezone.utc) - timedelta(days=retention_days)

            total_deleted = 0
            while True:
                trace_ids = get_expired_trace_ids(
                    db_session, cutoff, batch_size=DEFAULT_BATCH_SIZE
                )
                if not trace_ids:
                    break
                delete_trace_batch(db_session, trace_ids)
                total_deleted += len(trace_ids)

            if total_deleted > 0:
                logger.info(
                    "Trace retention: deleted %d traces older than %s",
                    total_deleted,
                    cutoff.isoformat(),
                )
        finally:
            db_session.close()

    def _background_loop(self) -> None:
        """Run retention once, then wait 24 hours and enqueue again."""
        logger.info("Background thread started for %s", self.service_name)
        if not self.shutdown_event.is_set():
            self.enqueue(TraceRetentionJob(delay_seconds=0))

        while not self.shutdown_event.is_set():
            if self.shutdown_event.wait(timeout=ONE_DAY_SECONDS):
                break
            if not self.shutdown_event.is_set():
                self.enqueue(TraceRetentionJob(delay_seconds=0))

        logger.info("Background thread stopped for %s", self.service_name)


TRACE_RETENTION_SERVICE: Optional[TraceRetentionService] = None


def get_trace_retention_service() -> Optional[TraceRetentionService]:
    """Return the global trace retention service instance."""
    return TRACE_RETENTION_SERVICE


def initialize_trace_retention_service() -> None:
    """Initialize and start the global trace retention service."""
    global TRACE_RETENTION_SERVICE
    if TRACE_RETENTION_SERVICE is None:
        TRACE_RETENTION_SERVICE = TraceRetentionService(num_workers=1)
        TRACE_RETENTION_SERVICE.start()


def shutdown_trace_retention_service() -> None:
    """Shutdown the global trace retention service."""
    global TRACE_RETENTION_SERVICE
    if TRACE_RETENTION_SERVICE is not None:
        TRACE_RETENTION_SERVICE.stop(timeout=30)
        TRACE_RETENTION_SERVICE = None
