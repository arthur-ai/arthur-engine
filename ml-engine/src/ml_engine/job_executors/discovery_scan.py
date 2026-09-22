"""The per-source half of the DISCOVER_AGENTS job: seams, outcome, and the scan loop.

A discovery scan job carries exactly one source config (D-06 dispatches one job per
(config x engine)), so isolation between sources is structural: two configs are two
jobs, and nothing here can reach outside the config it was handed. What this module
adds is the resiliency *within* one source -- a source that throws part-way through
must not discard the records it already produced.

The two seams below are deliberately empty. Making the vendor call and validating the
output columns belong to the connector framework (D-13), and resolving a discovery
record onto a task belongs to GenAI Engine (D-08). Neither exists yet, so no vendor is
registered and every source-scoped job fails with a named reason -- which is the
correct behaviour for an unsupported vendor either way, and is reported per job rather
than per engine.

Credentials are not a seam: D-05 has landed, so the executor reads this config's
sensitive fields at the point of the scan and hands them to the scanner. They serve
twice, because the same values are registered with the job's logger, which removes
them by exact match from everything it ships (see `log_redaction`).
"""

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Callable, Iterator, Mapping, Optional, Protocol, Sequence

from arthur_client.api_bindings import DiscoverySourceConfigSpec
from arthur_common.models.agent_discovery_schemas import DiscoveryOutputRecord

from log_redaction import redact_secrets, secret_values


class UnsupportedDiscoveryVendorError(Exception):
    """No connector is registered for the vendor a source config names."""


class DiscoverySourceScanner(Protocol):
    """One vendor's side of a scan, as the job handler needs to see it.

    Yields records in batches rather than returning them whole so that a source which
    fails half way through has still handed over everything it read before the failure.
    A scanner that can only fetch in one shot yields a single batch and loses nothing.

    D-13 owns the real interface -- the native call and output-column validation sit
    behind this method. Credentials arrive as an argument rather than being fetched
    here: the route that returns them says never to put the result in job parameters,
    so they are read once per scan at execution, and the caller that reads them is also
    what scrubs them out of anything bound for the job log.
    """

    def scan(
        self,
        config: DiscoverySourceConfigSpec,
        lookback_hours: int,
        credentials: Mapping[str, Optional[str]],
    ) -> Iterator[Sequence[DiscoveryOutputRecord]]: ...


class DiscoveryRecordSink(Protocol):
    """Where a batch of records goes once a scanner has produced it.

    Returns the number of records it accepted, which is what a run reports as this
    source's contribution. Publishing a discovery record means resolving it onto a task
    keyed on ``external_id``, which is D-08's, so there is no implementation yet.

    Accepted means every record the sink took, whether it created a task or updated one
    that already existed -- a source that reports the same twenty agents every scan
    contributes twenty each time. The count says how much of what the source produced
    survived the trip, not how many agents are new, and nothing downstream should
    present it as a count of new agents.

    A batch must be published atomically: an implementation that raises has committed
    nothing, and the run counts nothing for that batch. The return value is the only
    channel by which the caller learns what the Platform accepted, so a sink that
    commits half a batch and then throws would leave the run under-reporting its own
    contribution. That is a bug in the sink, not a case this module accounts for.
    """

    def publish(
        self,
        workspace_id: str,
        data_plane_id: str,
        config: DiscoverySourceConfigSpec,
        records: Sequence[DiscoveryOutputRecord],
    ) -> int: ...


# Builds a fresh scanner for one scan. A factory rather than an instance because
# low-memory jobs run as threads in one interpreter: two configs for the same vendor
# are two concurrent jobs, and a shared scanner would share whatever per-scan state it
# holds -- session, paging cursor, the credentials it was just handed -- between them.
DiscoveryScannerFactory = Callable[[], DiscoverySourceScanner]

# Vendor -> scanner factory, populated by D-13 as connectors land. Keyed on
# DiscoverySourceVendor values, e.g. "splunk_enterprise". A scanner class is itself a
# factory, so registering one is `SOURCE_SCANNERS["splunk_enterprise"] = SplunkScanner`.
SOURCE_SCANNERS: dict[str, DiscoveryScannerFactory] = {}


@dataclass
class DiscoveryScanOutcome:
    """What one source contributed to one run, and how it ended.

    This is the shape D-11's run store will persist. Until it exists the outcome is
    emitted as JSON in the job log -- the log exporter drops `extra`, so a structured
    record has to be *in* the message to survive the trip to the Platform.
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
    # Records the sink accepted, created and updated alike -- see DiscoveryRecordSink.
    records_published: int = 0
    error_count: int = 0
    error: Optional[str] = None

    def record_failure(
        self,
        exc: BaseException,
        known_secrets: Sequence[str] = (),
    ) -> None:
        """Record a failure, with the credentials taken back out of its message.

        The scrub set is passed in rather than held on this object: an outcome exists
        to be serialized into the job log, and a record that carried the secrets it is
        supposed to be protecting would be one careless field away from emitting them.
        """
        self.error_count += 1
        self.error = redact_secrets(f"{type(exc).__name__}: {exc}", known_secrets)

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
    credentials: Mapping[str, Optional[str]],
) -> DiscoveryScanOutcome:
    """Scan one source, publishing each batch as it arrives.

    Publishing inside the loop rather than after it is the whole point: when the source
    throws on its third page, the first two pages are already on the Platform and the
    run records both the contribution and the failure. The exception is re-raised so
    the job fails -- the Platform derives this source's leg of the scan from job state,
    and a source that failed must not read as succeeded just because it published
    something first.

    The catch is `BaseException`: a scan killed part-way -- the job agent shutting down,
    or the scanner's generator being closed -- still runs the `finally` below, and
    without a recorded failure its outcome would report a partial scan as a success.
    """
    known_secrets = secret_values(credentials)
    try:
        for batch in scanner.scan(config, lookback_hours, credentials):
            if not batch:
                continue
            accepted = sink.publish(workspace_id, data_plane_id, config, batch)
            outcome.batches_published += 1
            outcome.records_published += accepted
    except BaseException as e:
        outcome.record_failure(e, known_secrets)
        logger.error(
            f"Discovery scan of source config '{config.name}' failed after "
            f"{outcome.records_published} record(s): "
            f"{redact_secrets(str(e), known_secrets)}",
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
    # In the message, not in `extra`: ScopeJobLogExporter does not ship `extra`.
    logger.info(json.dumps(outcome.to_log_payload(), sort_keys=True))
    return outcome
