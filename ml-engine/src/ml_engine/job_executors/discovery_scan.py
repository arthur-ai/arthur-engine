"""The per-source half of the DISCOVER_AGENTS job: seams, outcome, and the scan loop.

A discovery scan job carries exactly one source config (D-06 dispatches one job per
(config x engine)), so isolation between sources is structural: two configs are two
jobs, and nothing here can reach outside the config it was handed. What this module
adds is the resiliency *within* one source -- a source that throws part-way through
must not discard the records it already produced.

The two seams below are deliberately empty. Fetching credentials, making the vendor
call and validating the output columns belong to the connector framework (D-13), and
resolving a discovery record onto a task belongs to GenAI Engine (D-08). Neither
exists yet, so no vendor is registered and every source-scoped job fails with a named
reason -- which is the correct behaviour for an unsupported vendor either way, and is
reported per job rather than per engine.
"""

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Iterator, Optional, Protocol, Sequence

from arthur_client.api_bindings import DiscoverySourceConfigSpec
from arthur_common.models.agent_discovery_schemas import DiscoveryOutputRecord


class UnsupportedDiscoveryVendorError(Exception):
    """No connector is registered for the vendor a source config names."""


class DiscoverySourceScanner(Protocol):
    """One vendor's side of a scan, as the job handler needs to see it.

    Yields records in batches rather than returning them whole so that a source which
    fails half way through has still handed over everything it read before the failure.
    A scanner that can only fetch in one shot yields a single batch and loses nothing.

    D-13 owns the real interface -- credentials from the Platform (D-05), the native
    call, and output-column validation all sit behind this method.
    """

    def scan(
        self,
        config: DiscoverySourceConfigSpec,
        lookback_hours: int,
    ) -> Iterator[Sequence[DiscoveryOutputRecord]]: ...


class DiscoveryRecordSink(Protocol):
    """Where a batch of records goes once a scanner has produced it.

    Returns the number of records it accepted, which is what a run reports as this
    source's contribution. Publishing a discovery record means resolving it onto a task
    keyed on ``external_id``, which is D-08's, so there is no implementation yet.
    """

    def publish(
        self,
        workspace_id: str,
        data_plane_id: str,
        config: DiscoverySourceConfigSpec,
        records: Sequence[DiscoveryOutputRecord],
    ) -> int: ...


# Vendor -> scanner, populated by D-13 as connectors land. Keyed on
# DiscoverySourceVendor values, e.g. "splunk_enterprise".
SOURCE_SCANNERS: dict[str, DiscoverySourceScanner] = {}


@dataclass
class DiscoveryScanOutcome:
    """What one source contributed to one run, and how it ended.

    This is the shape D-11's run store will persist. Until it exists the outcome is
    emitted as JSON in the job log -- the log exporter ships only the message text, so
    a structured record has to be *in* the message to survive the trip to the Platform.
    """

    # Everything naming the source is optional: a job whose spec is too malformed to
    # say what it would have scanned still owes the Platform a record that it ran and
    # failed, and a guessed-at vendor would be aggregated as a real source by D-11.
    discovery_source_config_id: Optional[str]
    discovery_source_config_name: Optional[str]
    discovery_source_id: Optional[str]
    vendor: Optional[str]
    job_id: str
    scan_id: Optional[str]
    lookback_hours: Optional[int]
    started_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc),
    )
    finished_at: Optional[datetime] = None
    batches_published: int = 0
    records_published: int = 0
    error_count: int = 0
    error: Optional[str] = None

    def record_failure(self, exc: BaseException) -> None:
        self.error_count += 1
        self.error = f"{type(exc).__name__}: {exc}"

    def to_log_payload(self) -> dict[str, object]:
        return {
            "event": "discovery_scan_outcome",
            "discovery_source_config_id": self.discovery_source_config_id,
            "discovery_source_config_name": self.discovery_source_config_name,
            "discovery_source_id": self.discovery_source_id,
            "vendor": self.vendor,
            "job_id": self.job_id,
            "scan_id": self.scan_id,
            "lookback_hours": self.lookback_hours,
            "started_at": self.started_at.isoformat(),
            "finished_at": (self.finished_at.isoformat() if self.finished_at else None),
            "batches_published": self.batches_published,
            "records_published": self.records_published,
            "error_count": self.error_count,
            "error": self.error,
            "succeeded": self.error is None,
        }


def run_source_scan(
    config: DiscoverySourceConfigSpec,
    lookback_hours: int,
    workspace_id: str,
    data_plane_id: str,
    outcome: DiscoveryScanOutcome,
    scanner: DiscoverySourceScanner,
    sink: DiscoveryRecordSink,
    logger: logging.Logger,
) -> DiscoveryScanOutcome:
    """Scan one source, publishing each batch as it arrives.

    Publishing inside the loop rather than after it is the whole point: when the source
    throws on its third page, the first two pages are already on the Platform and the
    run records both the contribution and the failure. The exception is re-raised so
    the job fails -- the Platform derives this source's leg of the scan from job state,
    and a source that failed must not read as succeeded just because it published
    something first.
    """
    try:
        for batch in scanner.scan(config, lookback_hours):
            if not batch:
                continue
            accepted = sink.publish(workspace_id, data_plane_id, config, batch)
            outcome.batches_published += 1
            outcome.records_published += accepted
    except Exception as e:
        outcome.record_failure(e)
        logger.error(
            f"Discovery scan of source config '{config.name}' failed after "
            f"{outcome.records_published} record(s): {e}",
            extra={
                "discovery_source_config_id": outcome.discovery_source_config_id,
                "vendor": config.vendor,
                "records_published": outcome.records_published,
            },
            exc_info=True,
        )
        raise
    finally:
        finalize_outcome(outcome, logger)

    return outcome


def finalize_outcome(
    outcome: DiscoveryScanOutcome,
    logger: logging.Logger,
) -> DiscoveryScanOutcome:
    """Close out a run and report it, however it ended.

    Every exit from a source-scoped job goes through here, including the ones that fail
    before a scanner is ever reached, so the Platform gets one outcome record per job
    rather than silence for the sources that never got as far as the vendor call.
    """
    outcome.finished_at = datetime.now(timezone.utc)
    # In the message, not in `extra`: ScopeJobLogExporter ships getMessage() only.
    logger.info(json.dumps(outcome.to_log_payload(), sort_keys=True))
    return outcome
