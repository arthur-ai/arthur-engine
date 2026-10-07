"""One standalone scan, start to finish: what a DISCOVER_AGENTS job is on the Platform.

A Platform job gets its config, credentials, record sink and outcome reporter from the
Platform; a standalone scan gets them from the config file and its sink target, then
runs the same `run_source_scan`. There is no chained fetch afterwards -- the sink
target is where records end -- and no job state to fail: a scan that fails says so in
its outcome, which is logged and sent to the destination, and the engine carries on.

EVERY EXIT REPORTS AN OUTCOME, as it does for a job. A scan that fails before its
connector is reached -- an unregistered vendor, a connector that cannot be constructed
-- is finalized here, and one that fails inside the scan loop is finalized by it.

The sink is not the scan's. The engine builds it once from the config's destination
and every scan shares it, so a scan neither builds nor closes one.
"""

import logging
import uuid
from typing import Callable

from discovery import source_connectors
from job_executors.discovery_scan import (
    AcceptsStopCheck,
    DiscoveryErrorCode,
    DiscoveryScanOutcome,
    DiscoverySourceConnector,
    OutcomeReporter,
    UnsupportedDiscoveryVendorError,
    finalize_outcome,
    run_source_scan,
)
from log_redaction import SecretRedactingFilter, register_secrets, secret_values
from standalone.discovery_config import ResolvedScan
from standalone.sinks.common import Sink, scan_outcome_event
from standalone.sinks.record_sink import StandaloneRecordSink


class ScanCancelled(Exception):
    """The engine began shutting down, and the scan stopped at the connector's next
    safe point rather than reading the whole source."""


class StandaloneOutcomeReporter:
    """Implements `discovery_scan.OutcomeReporter`: the outcome, as an event, to the
    destination the scan's records went to.

    MUST NOT RAISE, like every reporter: the scan has already happened. An outcome that
    cannot be delivered is logged, and the outcome logged before it is the record.
    """

    def __init__(self, sink: Sink, source_name: str, logger: logging.Logger) -> None:
        self._sink = sink
        self._source_name = source_name
        self._log = logger

    def report(self, outcome: DiscoveryScanOutcome) -> None:
        try:
            self._sink.send([scan_outcome_event(outcome, self._source_name)])
        except Exception as e:
            self._log.error(
                f"Could not send this scan's outcome to the destination; the outcome "
                f"logged above is the record of it: {e}",
            )


def scan_logger(scan: ResolvedScan, sink: Sink) -> logging.Logger:
    """The logger a scan of this source and config writes to, run after run.

    Set up once per pair, when the engine starts: loggers live as long as the process,
    and an engine that scans every few hours for months would otherwise accumulate one
    per run. Its redacting filter is told the source's credentials and the destination's
    secrets here, once -- neither changes between runs.
    """
    logger = logging.getLogger(
        f"standalone.scan.{scan.source_name}/{scan.config.name}",
    )
    if not any(isinstance(f, SecretRedactingFilter) for f in logger.filters):
        logger.addFilter(SecretRedactingFilter())
    register_secrets(logger, (*secret_values(scan.credentials), *sink.secrets()))
    return logger


def run_scan(
    scan: ResolvedScan,
    sink: Sink,
    emit_scan_outcomes: bool,
    logger: logging.Logger,
    should_stop: Callable[[], bool] = lambda: False,
) -> DiscoveryScanOutcome:
    """Scan one config of one source and send what it finds; never raises.

    `sink` is the engine's, shared with every other scan and closed by the engine, not
    here. `logger` is this pair's from `scan_logger`, which already scrubs its secrets.

    `should_stop` is the engine's shutdown. A connector that accepts a stop check is
    handed it, and a scan it ends early is reported as cancelled rather than as a
    source that had nothing more to say.
    """
    run_id = str(uuid.uuid4())
    outcome = DiscoveryScanOutcome(
        discovery_source_config_id=scan.discovery_source_config_id,
        discovery_source_config_name=scan.config.name,
        discovery_source_id=scan.config.discovery_source_id,
        vendor=scan.config.vendor,
        # No job: each run of the scan is the unit of work, so its ID stands for both.
        job_id=run_id,
        scan_id=run_id,
        lookback_hours=scan.lookback_hours,
    )
    # A window of zero or less is a full enumeration, which "over the last 0h" would
    # describe as a scan of nothing.
    window = (
        f"over the last {scan.lookback_hours}h"
        if scan.lookback_hours > 0
        else "with no lookback limit"
    )
    logger.info(
        f"Starting discovery scan of '{scan.source_name}/{scan.config.name}' "
        f"({scan.config.vendor}) {window}",
    )
    reporter = (
        StandaloneOutcomeReporter(sink, scan.source_name, logger)
        if emit_scan_outcomes
        else None
    )

    try:
        connector = _connector(scan, _cancel_on(should_stop, outcome))
    except Exception as e:
        _fail_before_scan(outcome, e, logger, reporter)
        return outcome
    try:
        run_source_scan(
            config=scan.config,
            lookback_hours=scan.lookback_hours,
            # A standalone engine has neither; the record sink does not send them.
            workspace_id="",
            data_plane_id="",
            outcome=outcome,
            connector=connector,
            sink=StandaloneRecordSink(sink, scan.source_name),
            logger=logger,
            credentials=scan.credentials,
            source_fields=scan.source_fields,
            reporter=reporter,
        )
    except Exception:
        # Already recorded, logged with its redacted traceback, and reported by the
        # scan loop. There is no job to fail, so the outcome is the whole answer.
        pass
    return outcome


def _connector(
    scan: ResolvedScan,
    should_stop: Callable[[], bool],
) -> DiscoverySourceConnector:
    factory = source_connectors().get(scan.config.vendor)
    if factory is None:
        # Checked when the config was loaded; kept so a scan names the reason anyway.
        raise UnsupportedDiscoveryVendorError(
            f"No discovery connector is registered for vendor '{scan.config.vendor}'",
        )
    connector = factory()
    if isinstance(connector, AcceptsStopCheck):
        connector.stop_when(should_stop)
    return connector


def _cancel_on(
    should_stop: Callable[[], bool],
    outcome: DiscoveryScanOutcome,
) -> Callable[[], bool]:
    """`should_stop`, recording the cancellation on the outcome the first time it fires.

    A connector that is told to stop returns as though the source had ended, so the scan
    loop would finalize a partial scan as a success. Recording the failure here, before
    the loop finalizes, is what makes the logged and reported outcome say cancelled.
    """

    def check() -> bool:
        if not should_stop():
            return False
        if outcome.error is None:
            outcome.record_failure(
                ScanCancelled(
                    "The engine is shutting down; the scan stopped before reading "
                    "the whole source.",
                ),
                error_code=DiscoveryErrorCode.CANCELLED,
            )
        return True

    return check


def _fail_before_scan(
    outcome: DiscoveryScanOutcome,
    error: Exception,
    logger: logging.Logger,
    reporter: OutcomeReporter | None,
) -> None:
    """Close out a scan that failed before its connector was reached."""
    outcome.record_failure(
        error,
        error_code=(
            None
            if isinstance(error, UnsupportedDiscoveryVendorError)
            else DiscoveryErrorCode.INTERNAL_ERROR
        ),
    )
    logger.error(outcome.error)
    finalize_outcome(outcome, logger, reporter)
