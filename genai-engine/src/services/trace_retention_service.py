"""Background service that deletes trace data older than the configured retention period.

Leader election
---------------
A PostgreSQL session-level advisory lock (``TRACE_RETENTION_ADVISORY_LOCK_KEY``)
ensures that only one replica runs the retention loop at a time.  Non-leaders
stand by and retry each interval; if the leader crashes its DB session closes,
releasing the lock so another replica can take over.

Scheduling
----------
The leader enqueues a retention job immediately on startup and then once every
24 hours.  Each job queries for traces whose ``end_time`` is older than the
configured ``trace_retention_days`` and deletes them in batches of
``DEFAULT_TRACE_RETENTION_BATCH_SIZE`` (500).

Inter-batch throttling
----------------------
A 1-second pause (``INTER_BATCH_DELAY_SECONDS``) is inserted between batches
so the deletion workload doesn't spike database load, especially on startup
when a large backlog may exist.  The pause is interruptible via the shutdown
event for graceful termination.

Circuit breaker / fail-stop latch
---------------------------------
The service maintains a consecutive-failure counter.  If a run fails
``CIRCUIT_BREAKER_THRESHOLD`` (3) times in a row, or if a single run deletes
more than ``MAX_TRACES_PER_RUN`` (100 000) traces, a fail-stop latch is
tripped.  Once tripped the background loop exits permanently and a
``CRITICAL`` log is emitted.  **A process restart is required to resume
retention.**
"""

from __future__ import annotations

import logging
import threading
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import text

from dependencies import db_session_context, get_db_session
from repositories.configuration_repository import ConfigurationRepository
from repositories.trace_retention_repository import (
    DEFAULT_TRACE_RETENTION_BATCH_SIZE,
    delete_trace_batch,
    get_expired_trace_ids,
)
from services.base_queue_service import BaseQueueJob, BaseQueueService

logger = logging.getLogger(__name__)

ONE_DAY_SECONDS = 24 * 3600
TRACE_RETENTION_JOB_KEY = "trace_retention"
# PostgreSQL session-level advisory lock key for leader election.
# Must be unique across all advisory lock users in the application
# (see also POLLING_ADVISORY_LOCK_KEY and _SYSTEM_TASK_INIT_LOCK_ID).
TRACE_RETENTION_ADVISORY_LOCK_KEY = 17449341
INTER_BATCH_DELAY_SECONDS = 1
MAX_TRACES_PER_RUN = 100_000
CIRCUIT_BREAKER_THRESHOLD = 3
LEADER_ELECTION_RETRY_SECONDS = 60


class TraceRetentionJob(BaseQueueJob):
    """Job representing one run of the trace retention cleanup."""

    def __init__(self, delay_seconds: int = 0) -> None:
        super().__init__(delay_seconds=delay_seconds)


class TraceRetentionService(BaseQueueService[TraceRetentionJob]):
    """Background service that periodically deletes trace data older than the configured retention period."""

    job_model = TraceRetentionJob
    service_name = "trace_retention_service"
    background_thread_name = "trace-retention"

    def __init__(self, **kwargs: object) -> None:
        super().__init__(**kwargs)  # type: ignore[arg-type]
        self._tripped = threading.Event()
        self._failure_lock = threading.Lock()
        self._consecutive_failures = 0

    def _trip_latch(self, reason: str) -> None:
        """Trip the fail-stop latch. Once tripped it stays tripped until process restart."""
        logger.critical("Trace retention latch tripped: %s", reason)
        self._tripped.set()
        self.shutdown_event.set()

    def _get_job_key(self, job: TraceRetentionJob) -> str:
        return TRACE_RETENTION_JOB_KEY

    def _execute_job(self, job: TraceRetentionJob) -> None:
        """Run one retention pass: delete traces older than configured retention."""
        total_deleted = 0
        batch_error = False

        try:
            with db_session_context() as db_session:
                config_repo = ConfigurationRepository(db_session)
                config = config_repo.get_configurations()
                cutoff = datetime.now(timezone.utc) - timedelta(
                    days=config.trace_retention_days
                )

                while True:
                    try:
                        trace_ids = get_expired_trace_ids(
                            db_session,
                            cutoff,
                            batch_size=DEFAULT_TRACE_RETENTION_BATCH_SIZE,
                        )
                        if not trace_ids:
                            break
                        delete_trace_batch(db_session, trace_ids)
                        db_session.commit()
                        total_deleted += len(trace_ids)
                    except Exception:
                        logger.exception(
                            "Trace retention batch failed after deleting %d traces",
                            total_deleted,
                        )
                        db_session.rollback()
                        batch_error = True
                        break

                    if total_deleted >= MAX_TRACES_PER_RUN:
                        self._trip_latch(
                            f"runaway deletion cap reached: deleted {total_deleted} "
                            f"traces (cutoff={cutoff.isoformat()})"
                        )
                        break

                    if self.shutdown_event.wait(INTER_BATCH_DELAY_SECONDS):
                        break

                if total_deleted > 0:
                    logger.info(
                        "Trace retention: deleted %d traces older than %s",
                        total_deleted,
                        cutoff.isoformat(),
                    )
        except Exception:
            with self._failure_lock:
                self._consecutive_failures += 1
                failures = self._consecutive_failures
            logger.exception(
                "Trace retention run failed (%d consecutive)",
                failures,
            )
            if failures >= CIRCUIT_BREAKER_THRESHOLD:
                self._trip_latch(
                    f"circuit breaker threshold reached: "
                    f"{failures} consecutive failures"
                )
            return

        with self._failure_lock:
            if batch_error and total_deleted == 0:
                self._consecutive_failures += 1
                failures = self._consecutive_failures
            else:
                self._consecutive_failures = 0
                failures = 0

        if failures >= CIRCUIT_BREAKER_THRESHOLD:
            self._trip_latch(
                f"circuit breaker threshold reached: "
                f"{failures} consecutive failures"
            )

    def _background_loop(self) -> None:
        """Run retention once, then wait 24 hours and enqueue again.

        Uses a PostgreSQL session-level advisory lock to elect a single leader
        across all replicas.  Only the replica that acquires the lock runs the
        retention loop.  Non-leaders wait and retry each interval so they can
        take over if the leader crashes (the lock is released automatically
        when the leader's DB session closes).
        """
        logger.info("Background thread started for %s", self.service_name)

        while not self.shutdown_event.is_set():
            leader_session = None
            try:
                leader_session = next(get_db_session())
                acquired = leader_session.execute(
                    text("SELECT pg_try_advisory_lock(:key)"),
                    {"key": TRACE_RETENTION_ADVISORY_LOCK_KEY},
                ).scalar()

                if not acquired:
                    logger.info(
                        "Another replica holds the trace retention leader lock, standing by"
                    )
                    self.shutdown_event.wait(timeout=ONE_DAY_SECONDS)
                    continue

                logger.info("Acquired trace retention leader lock")

                if not self.shutdown_event.is_set():
                    self.enqueue(TraceRetentionJob(delay_seconds=0))

                while not self.shutdown_event.is_set():
                    if self.shutdown_event.wait(timeout=ONE_DAY_SECONDS):
                        break
                    if not self.shutdown_event.is_set():
                        self.enqueue(TraceRetentionJob(delay_seconds=0))

            except Exception as e:
                logger.error(
                    "Error in trace retention leader election: %s",
                    e,
                    exc_info=True,
                )
                self.shutdown_event.wait(timeout=LEADER_ELECTION_RETRY_SECONDS)
            finally:
                if leader_session is not None:
                    leader_session.close()

        if self._tripped.is_set():
            logger.critical(
                "Trace retention latch is tripped; background thread exiting. "
                "Manual intervention required -- restart the process to resume.",
            )
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
