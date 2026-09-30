"""Delivering a source scan's outcome to the Platform's run store (D-11).

The run store keeps one outcome per job attempt, and writes the source's health from
it: a Jamf source whose client secret was revoked reads failed after its next scan
rather than connected forever. This module maps `DiscoveryScanOutcome` onto the
Platform's shape and delivers it.

A REPORT NEVER FAILS ITS JOB. The scan already happened and its records are already
published; failing the job would make the retry rescan the source to resend a report.
So a report the Platform will not take is logged and dropped, and one it could not be
reached for is retried a few times first. The PUT is idempotent -- an identical report
for the same attempt returns the run already stored -- so retrying one whose
acknowledgement was lost records it once.
"""

import logging
import time
from dataclasses import asdict
from datetime import datetime, timezone
from typing import Callable

from arthur_client.api_bindings import (
    DiscoveryDeviceCoverage,
    DiscoveryRunStatus,
    DiscoveryRunsV1Api,
    PutDiscoveryRunOutcome,
)
from arthur_client.api_bindings.exceptions import ApiException

from job_executors.discovery_scan import DiscoveryErrorCode, DiscoveryScanOutcome

DELIVERY_ATTEMPTS = 3
# Seconds per attempt, so a Platform that accepts the connection and never answers
# cannot hold the job open.
DELIVERY_TIMEOUT_SECONDS = 10.0
# What a retry can fix. A 409 is not: the Platform already holds a different outcome
# for this attempt, and it keeps that one.
RETRY_STATUSES = frozenset({429, 500, 502, 503, 504})


def platform_outcome(outcome: DiscoveryScanOutcome) -> PutDiscoveryRunOutcome:
    """The run store's shape for one outcome: counts and a code.

    The redacted error, failed records and column check stay in the job log, which
    the stored run leads to by its job and job-run IDs. No scan here reports denied
    scopes yet: Jamf reads one tenant, and a query-language source one index.
    """
    failed = outcome.error is not None
    return PutDiscoveryRunOutcome(
        schema_version=1,
        status=DiscoveryRunStatus.FAILED if failed else DiscoveryRunStatus.DONE,
        started_at=outcome.started_at,
        finished_at=outcome.finished_at or datetime.now(timezone.utc),
        records_published=outcome.records_published,
        batches_published=outcome.batches_published,
        error_count=outcome.error_count,
        error_code=(
            (outcome.error_code or DiscoveryErrorCode.INTERNAL_ERROR).value
            if failed
            else None
        ),
        denied_scopes=[],
        device_coverage=(
            DiscoveryDeviceCoverage(**asdict(outcome.device_coverage))
            if outcome.device_coverage is not None
            else None
        ),
    )


class PlatformRunReporter:
    """Implements `discovery_scan.OutcomeReporter` against the Platform's run store."""

    def __init__(
        self,
        runs_client: DiscoveryRunsV1Api,
        job_id: str,
        job_run_id: str,
        logger: logging.Logger,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self.runs_client = runs_client
        self.job_id = job_id
        self.job_run_id = job_run_id
        self.logger = logger
        self._sleep = sleep

    def report(self, outcome: DiscoveryScanOutcome) -> None:
        try:
            body = platform_outcome(outcome)
        except Exception as e:
            self.logger.error(
                f"This run's outcome does not fit the Platform's run store, so the run "
                f"is missing from its history and the source's health is unchanged: {e}",
            )
            return

        for attempt in range(1, DELIVERY_ATTEMPTS + 1):
            try:
                run = self.runs_client.put_discovery_run_outcome(
                    self.job_id,
                    self.job_run_id,
                    body,
                    _request_timeout=DELIVERY_TIMEOUT_SECONDS,
                )
            except ApiException as e:
                if e.status not in RETRY_STATUSES or attempt == DELIVERY_ATTEMPTS:
                    self._dropped(f"HTTP {e.status} {e.reason}: {(e.body or '')[:500]}")
                    return
                reason = f"HTTP {e.status}"
            except Exception as e:
                if attempt == DELIVERY_ATTEMPTS:
                    self._dropped(f"{type(e).__name__}: {e}")
                    return
                reason = type(e).__name__
            else:
                self.logger.info(
                    f"Recorded this scan as discovery run {run.id} ({body.status.value})",
                )
                return
            self.logger.warning(
                f"Could not deliver this run's outcome ({reason}); retrying",
            )
            self._sleep(2 ** (attempt - 1))

    def _dropped(self, why: str) -> None:
        self.logger.error(
            f"The Platform did not record this run's outcome ({why}). The run is "
            f"missing from its history and the source's health is unchanged; the "
            f"outcome logged above is the record of it.",
        )
