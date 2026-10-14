"""The per-source half of the DISCOVER_AGENTS job: seams, outcome, and the scan loop.

A discovery scan job carries exactly one source config (D-06 dispatches one job per
(config x engine)), so isolation between sources is structural: two configs are two
jobs, and nothing here can reach outside the config it was handed. What this module
adds is the resiliency *within* one source -- a source that throws part-way through
must not discard the records it already produced.

Making the vendor call is a connector's, behind the first seam below. Resolving a
discovery record onto a task is GenAI Engine's (D-08), behind the second, whose
implementation is the connector framework's handoff (D-13) and has not landed yet -- so
a source-scoped job fails with a named reason, reported per job rather than per engine,
as it does for a vendor with no connector registered.

Checking the output columns is neither: it is this module's, run on every batch before
it is published, so a connector cannot decide for itself what the contract means.

Credentials are not a seam: D-05 has landed, so the executor reads this config's
sensitive fields at the point of the scan and hands them to the connector. They serve
twice, because the same values are registered with the job's logger, which removes
them by exact match from everything it ships (see `log_redaction`).
"""

import json
import logging
import traceback
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import (
    Callable,
    Iterator,
    Mapping,
    Optional,
    Protocol,
    Sequence,
    runtime_checkable,
)

from arthur_client.api_bindings import (
    DiscoverySourceConfigSpec,
    OutputColumnCheckResult,
)
from arthur_common.models.agent_discovery_schemas import DiscoveryOutputRecord

from job_executors.discovery_output_contract import (
    OutputContractError,
    check_batch,
    result_payload,
)
from log_redaction import redact_secrets, secret_values


class UnsupportedDiscoveryVendorError(Exception):
    """No connector is registered for the vendor a source config names."""


class DiscoveryConfigurationError(ValueError):
    """The source's settings or query cannot be scanned as they are.

    A required field that is missing, a device group that resolves to nothing: a
    person has to change the source before any retry can succeed. A ValueError, so a
    caller that already catches one still does.
    """


class DiscoveryErrorCode(str, Enum):
    """Why a run failed, as the Platform's run store accepts it (D-11).

    The Platform writes what an admin reads from the code alone, so no vendor text
    has to travel for a source to say why it is failing.
    """

    INVALID_JOB = "invalid_job"
    UNSUPPORTED_VENDOR = "unsupported_vendor"
    NOT_CONFIGURED = "not_configured"
    CREDENTIALS_UNAVAILABLE = "credentials_unavailable"
    AUTHENTICATION_FAILED = "authentication_failed"
    PERMISSION_DENIED = "permission_denied"
    PROVIDER_ERROR = "provider_error"
    PUBLICATION_FAILED = "publication_failed"
    CANCELLED = "cancelled"
    INTERNAL_ERROR = "internal_error"


def failure_code(exc: BaseException) -> DiscoveryErrorCode:
    """The code for a failure raised while a connector was scanning.

    A connector that talks HTTP says what the vendor answered through a `status_code`
    attribute on what it raises, which is how 401 and 403 are told from the rest.
    Anything else the vendor call raised is the vendor's error.
    """
    if not isinstance(exc, Exception):
        # KeyboardInterrupt, SystemExit, GeneratorExit: the scan was stopped, and
        # nothing about the source follows from that.
        return DiscoveryErrorCode.CANCELLED
    if isinstance(exc, UnsupportedDiscoveryVendorError):
        return DiscoveryErrorCode.UNSUPPORTED_VENDOR
    if isinstance(exc, (DiscoveryConfigurationError, OutputContractError)):
        # A query whose output misses the contract is the config's to fix.
        return DiscoveryErrorCode.NOT_CONFIGURED
    status = getattr(exc, "status_code", None)
    if status == 401:
        return DiscoveryErrorCode.AUTHENTICATION_FAILED
    if status == 403:
        return DiscoveryErrorCode.PERMISSION_DENIED
    return DiscoveryErrorCode.PROVIDER_ERROR


class DiscoverySourceConnector(Protocol):
    """One vendor's side of a scan, as the job handler needs to see it.

    Yields records in batches rather than returning them whole so that a source which
    fails half way through has still handed over everything it read before the failure.
    A connector that can only fetch in one shot yields a single batch and loses nothing.

    Only the native call sits behind this method. What it yields is checked against the
    D-02 output contract by the caller, so a connector owes typed records and nothing
    else. Credentials arrive as an argument rather than being fetched
    here: the route that returns them says never to put the result in job parameters,
    so they are read once per scan at execution, and the caller that reads them is also
    what scrubs them out of anything bound for the job log.

    `source_fields` is the source's NON-SENSITIVE configuration, kept apart from
    `credentials` rather than merged into it. Every vendor here needs at least one --
    Jamf's `base_url`, Splunk's, Elastic's `elasticsearch_url` -- and none of them is a
    secret. Merging them would also register them as scrub targets, so a URL would be
    struck out of the very log lines that exist to say which host failed.

    THE LOGGER IS THE JOB'S, NOT THE MODULE'S. `ScopeJobLogExporter` is attached to the
    per-job logger alone, so a connector logging to `getLogger(__name__)` reaches process
    stdout and never the Platform -- and every connector's "reported, not suppressed"
    behaviour is worth nothing if the report does not leave the engine.
    """

    def scan(
        self,
        config: DiscoverySourceConfigSpec,
        lookback_hours: int,
        credentials: Mapping[str, Optional[str]],
        source_fields: Mapping[str, str],
        logger: logging.Logger,
    ) -> Iterator[Sequence[DiscoveryOutputRecord]]: ...


@dataclass
class DeviceCoverage:
    """Which devices an endpoint scan read, and which of them it was allowed to use.

    The denominator a record count needs: "12 Macs have agents" cannot be told from
    "12 of 4,000, and 900 are excluded by policy" without it. Counts cover the devices
    this run was handed -- the lookback window, or the whole roster for a full
    enumeration -- not the fleet's total size.

    A device in several excluded groups counts toward each of them, so the per-group
    counts can sum to more than `devices_excluded`. Those are two different questions:
    how many devices policy kept out, and what each rule is keeping out.
    """

    devices_read: int = 0
    devices_in_scope: int = 0
    # In scope and carrying a payload that decoded, versus one that did not.
    devices_decoded: int = 0
    devices_unreadable: int = 0
    # Why each unreadable device was, e.g. "never-reported" -> 120. Sums to
    # `devices_unreadable`: a Mac that has not reported since the collector shipped
    # asks for a different fix than a payload this side cannot parse.
    unreadable_by_reason: dict[str, int] = field(default_factory=dict)
    devices_excluded: int = 0
    # Group name -> devices it kept out.
    excluded_by_group: dict[str, int] = field(default_factory=dict)
    # Include groups were set and the device was in none of them.
    devices_outside_included_groups: int = 0
    # Group name -> in-scope devices it let in.
    included_by_group: dict[str, int] = field(default_factory=dict)

    def count_unreadable(self, reason: str) -> None:
        self.devices_unreadable += 1
        self.unreadable_by_reason[reason] = self.unreadable_by_reason.get(reason, 0) + 1


@runtime_checkable
class ReportsDeviceCoverage(Protocol):
    """A connector that reads managed devices, and can say which it read and used.

    Optional, so a query-language source owes nothing. Asked once the scan ends,
    however it ended: a scan that fails on page 40 still read pages 1-39, and those
    counts are what explain the records that did land.
    """

    def device_coverage(self) -> Optional[DeviceCoverage]: ...


@runtime_checkable
class AcceptsStopCheck(Protocol):
    """A connector that can be told to end its scan early, between vendor calls.

    Optional, like `ReportsDeviceCoverage`, and deliberately not a parameter of `scan`:
    a Protocol method with an extra parameter, even a defaulted one, is a signature a
    connector without it no longer satisfies, and every connector would have to change
    to keep type-checking. A connector that implements this is handed the check before
    `scan` is called; one that does not is simply never stopped early.

    The caller that sets a check is the one with a deadline -- Test Connection, whose
    preview someone is waiting on. A scan's caller sets none: a scheduled scan reads
    the whole source.

    A connector that honours it asks `should_stop()` between devices or pages and, when
    it answers True, returns as if the source had ended: no exception, nothing more
    requested from the vendor. It is a request to stop at the next safe point, not an
    interruption, so a single vendor call in flight is still bounded only by its own
    request timeout.
    """

    def stop_when(self, should_stop: Callable[[], bool]) -> None: ...


@dataclass(frozen=True)
class FailedDiscoveryRecord:
    """A record GenAI Engine could not resolve onto a task, as the run reports it.

    Mirrors GenAI Engine's `FailedDiscoveredRecord` but is declared here rather than
    taken from the generated client, so the outcome D-11 persists does not change shape
    whenever that client is regenerated.
    """

    external_id: str
    # GenAI Engine's `DiscoveredRecordFailureReason`, e.g. "task_not_found".
    reason: str
    detail: str


@dataclass(frozen=True)
class DiscoveryPublishResult:
    """What GenAI Engine made of one batch: every record is in exactly one of the two."""

    accepted: int
    failed: Sequence[FailedDiscoveryRecord] = ()


class DiscoveryRecordSink(Protocol):
    """Where a batch of records goes once a connector has produced it.

    Publishing a discovery record means resolving it onto a task keyed on
    ``external_id`` (D-08). `discovery_record_sink.GenAIEngineRecordSink` implements it
    against that endpoint.

    Accepted means every record that resolved, whether it created a task or joined one
    that already existed -- a source that reports the same twenty agents every scan
    contributes twenty each time. The count says how much of what the source produced
    survived the trip, not how many agents are new, and nothing downstream should
    present it as a count of new agents.

    A RECORD THAT FAILS DOES NOT FAIL ITS BATCH. GenAI Engine resolves the rest and
    reports the failure alongside them, and the sink hands both back. There is nothing
    for the caller to decide: a failure is final for that input -- re-submitting the
    record unchanged fails the same way -- so it is reported on the run for whoever
    configured the source, and never retried.

    A sink that raises is a different case: the request itself did not complete. Each
    record GenAI Engine resolved before then stays resolved, so a batch is not atomic,
    but re-publishing it is safe -- resolved records come back to the tasks they already
    have. The run cannot know how much of a raising batch landed, so it counts none of
    it, and its contribution is a lower bound on what reached the Platform.
    """

    def publish(
        self,
        workspace_id: str,
        data_plane_id: str,
        config: DiscoverySourceConfigSpec,
        records: Sequence[DiscoveryOutputRecord],
    ) -> DiscoveryPublishResult: ...


class OutcomeReporter(Protocol):
    """Where a finished run's outcome goes: D-11's run store, which also writes the
    source's health from it. `discovery_run_reporter.PlatformRunReporter` implements
    it against the Platform.

    MUST NOT RAISE. A report that cannot be delivered is logged and dropped: the scan
    has already happened, and failing its job over the report would make the retry
    rescan the source to resend it.
    """

    def report(self, outcome: "DiscoveryScanOutcome") -> None: ...


# Builds a fresh connector for one scan. A factory rather than an instance because
# low-memory jobs run as threads in one interpreter: two configs for the same vendor
# are two concurrent jobs, and a shared connector would share whatever per-scan state it
# holds -- session, paging cursor, the credentials it was just handed -- between them.
DiscoveryConnectorFactory = Callable[[], DiscoverySourceConnector]


@dataclass
class DiscoveryScanOutcome:
    """What one source contributed to one run, and how it ended.

    Delivered to D-11's run store by an `OutcomeReporter`, which is also what writes
    the source's health there. It is emitted as JSON in the job log as well, for
    what the run store does not keep (failed records, the column check, the redacted
    error) -- the log exporter drops `extra`, so a structured record has to be *in*
    the message to survive the trip to the Platform.
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
    # Records GenAI Engine could not resolve. They do not fail the run: the source
    # reported them and the rest of their batch landed, so the scan succeeded and these
    # are something for whoever configured the source to fix.
    failed_records: list[FailedDiscoveryRecord] = field(default_factory=list)
    error_count: int = 0
    error: Optional[str] = None
    # What the run store is told instead of `error`, which stays in the job log.
    error_code: Optional[DiscoveryErrorCode] = None
    # The D-02 column check for this run. Null means the run failed before a batch was
    # ever produced, which is not the same answer as a source that produced one and
    # failed the contract.
    output_column_check: Optional[OutputColumnCheckResult] = None
    # Endpoint sources only: the devices behind the records, and the ones policy kept
    # out. Null for a source that does not read devices.
    device_coverage: Optional[DeviceCoverage] = None

    def record_failure(
        self,
        exc: BaseException,
        known_secrets: Sequence[str] = (),
        error_code: Optional[DiscoveryErrorCode] = None,
    ) -> None:
        """Record a failure, with the credentials taken back out of its message.

        The scrub set is passed in rather than held on this object: an outcome exists
        to be serialized into the job log, and a record that carried the secrets it is
        supposed to be protecting would be one careless field away from emitting them.

        `error_code` is for a caller that knows what failed better than the exception
        says. Without one, the exception is classified as a connector's.
        """
        self.error_count += 1
        self.error = redact_secrets(f"{type(exc).__name__}: {exc}", known_secrets)
        self.error_code = error_code or failure_code(exc)

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
            "records_failed": len(self.failed_records),
            "failed_records": [asdict(record) for record in self.failed_records],
            "error_count": self.error_count,
            "error": self.error,
            "error_code": self.error_code.value if self.error_code else None,
            "output_column_check": result_payload(self.output_column_check),
            "device_coverage": (
                asdict(self.device_coverage) if self.device_coverage else None
            ),
            "succeeded": self.error is None,
        }


def run_source_scan(
    config: DiscoverySourceConfigSpec,
    lookback_hours: int,
    workspace_id: str,
    data_plane_id: str,
    outcome: DiscoveryScanOutcome,
    connector: DiscoverySourceConnector,
    sink: DiscoveryRecordSink,
    logger: logging.Logger,
    credentials: Mapping[str, Optional[str]],
    source_fields: Mapping[str, str],
    reporter: Optional[OutcomeReporter] = None,
) -> DiscoveryScanOutcome:
    """Scan one source, publishing each batch as it arrives.

    Publishing inside the loop rather than after it is the whole point: when the source
    throws on its third page, the first two pages are already on the Platform and the
    run records both the contribution and the failure. The exception is re-raised so
    the job fails -- the Platform derives this source's leg of the scan from job state,
    and a source that failed must not read as succeeded just because it published
    something first.

    The catch is `BaseException`: a scan killed part-way -- the job agent shutting down,
    or the connector's generator being closed -- still runs the `finally` below, and
    without a recorded failure its outcome would report a partial scan as a success.
    """
    known_secrets = secret_values(credentials)
    publishing = False
    try:
        for batch in connector.scan(
            config,
            lookback_hours,
            credentials,
            source_fields,
            logger,
        ):
            if not batch:
                continue
            # Checked before publishing, so a batch that fails the contract is never
            # half-delivered: the run reports the columns rather than the sink
            # reporting whatever it choked on.
            #
            # The failing result is taken off the exception rather than left to the
            # assignment, which never runs when the check raises -- the outcome would
            # otherwise carry the last batch's pass as its verdict on a failed run.
            try:
                outcome.output_column_check = check_batch(
                    batch,
                    f"Source config '{config.name}' ({config.vendor})",
                )
            except OutputContractError as contract_error:
                outcome.output_column_check = contract_error.result
                raise
            publishing = True
            result = sink.publish(workspace_id, data_plane_id, config, batch)
            publishing = False
            outcome.batches_published += 1
            outcome.records_published += result.accepted
            if result.failed:
                outcome.failed_records.extend(result.failed)
                # Each failure's detail travels on the outcome; this is the line
                # someone reading the job log sees first.
                logger.warning(
                    f"{len(result.failed)} record(s) from source config "
                    f"'{config.name}' could not be resolved to a task; see "
                    f"failed_records on the scan outcome",
                )
    except BaseException as e:
        if isinstance(e, OutputContractError):
            # A connector that checks a result's columns before building records -- the
            # SIEM connectors, so an unmapped column is refused rather than dropped --
            # raises here, outside the per-batch check above. The run still owes the
            # per-column verdict, not just the failure.
            outcome.output_column_check = e.result
        # A publish that raised failed on GenAI Engine's side, not the vendor's.
        outcome.record_failure(
            e,
            known_secrets,
            (
                DiscoveryErrorCode.PUBLICATION_FAILED
                if publishing and isinstance(e, Exception)
                else None
            ),
        )
        # The traceback is redacted and carried IN THE MESSAGE rather than passed as
        # `exc_info`. The exporter formats `exc_info` itself and posts the result
        # unredacted, so a vendor exception quoting the request it failed on -- or a
        # token minted from a configured secret -- would reach the Platform verbatim.
        detail = redact_secrets(str(e), known_secrets)
        trace = redact_secrets("".join(traceback.format_exception(e)), known_secrets)
        logger.error(
            f"Discovery scan of source config '{config.name}' failed after "
            f"{outcome.records_published} record(s): {detail}\n{trace}",
            extra={
                "discovery_source_config_id": outcome.discovery_source_config_id,
                "vendor": config.vendor,
                "records_published": outcome.records_published,
            },
        )
        # REDACTED IN PLACE, THEN RE-RAISED UNCHANGED IN TYPE. JobExecutor.execute logs
        # whatever it catches with `exc_info`, and the exporter posts
        # `traceback.format_exception(...)` and `str(exc_value)` -- both of which read the
        # message out of `args`. Rewriting args scrubs that second export while leaving
        # the exception's type intact, which callers and tests depend on; wrapping it in a
        # new type would fix the leak by breaking the contract.
        if e.args:
            e.args = (detail,) + tuple(e.args[1:])
        raise
    finally:
        if isinstance(connector, ReportsDeviceCoverage):
            outcome.device_coverage = connector.device_coverage()
        finalize_outcome(outcome, logger, reporter)

    return outcome


def finalize_outcome(
    outcome: DiscoveryScanOutcome,
    logger: logging.Logger,
    reporter: Optional[OutcomeReporter] = None,
) -> DiscoveryScanOutcome:
    """Close out a run and report it, however it ended.

    Every exit from a source-scoped job goes through here, including the ones that fail
    before a connector is ever reached, so the Platform gets one outcome record per job
    rather than silence for the sources that never got as far as the vendor call.
    """
    outcome.finished_at = datetime.now(timezone.utc)
    # In the message, not in `extra`: ScopeJobLogExporter does not ship `extra`.
    logger.info(json.dumps(outcome.to_log_payload(), sort_keys=True))
    if reporter is not None:
        reporter.report(outcome)
    return outcome
