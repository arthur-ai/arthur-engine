"""Executor for the TEST_DISCOVERY_SOURCE job (D-12): Test Connection.

A test runs the same connector a scan runs, against the same credentials, but it is
built so that it cannot do what a scan is for. There is no sink here: nothing is
published to GenAI Engine, no fetch is chained, and no Discovery Run is written. What
it produces is a bounded preview -- the first rows the connector yields, the output
column check over them, whether the source answered, and the vendor's error if it did
not -- reported back to the Platform against this job's attempt.

A failed test is still a completed job. The job's work is to answer the question, and
"the vendor said 401" is an answer; the job fails only when the answer cannot be
delivered.

Every string that leaves the engine goes through the same redaction a scan's log does:
the config's credentials are removed by exact match from the error message and from the
preview rows, and the pattern backstop catches tokens minted from them at run time.
"""

import json
import logging
import re
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable, Iterator, Mapping, Optional, Sequence

import requests
from arthur_client.api_bindings import (
    DiscoverySourceReachability,
    DiscoverySourcesV1Api,
    DiscoverySourceTestError,
    DiscoverySourceTestErrorCategory,
    DiscoverySourceTestOutcome,
    Job,
    OutputColumnCheckResult,
    PutDiscoverySourceTestResult,
    TestDiscoverySourceJobSpec,
)
from arthur_common.models.agent_discovery_schemas import DiscoveryOutputRecord

from job_executors.discovery_output_contract import OutputContractError, check_batch
from job_executors.discovery_scan import SOURCE_SCANNERS, DiscoveryScannerFactory
from log_redaction import redact_secrets, register_secrets, secret_values

# How long a test may keep reading once it has started. Checked between batches: a
# scanner blocked inside one vendor call is bounded by its own request timeout, not by
# this. A test is something a person is waiting on, and a preview that takes longer
# than this to assemble is better reported as partial than not at all.
PREVIEW_DEADLINE_SECONDS = 120.0

# Kept under the Platform's 256 KiB bound so a preview this engine considers in-bounds
# is never refused for a few bytes of encoding difference.
MAX_PREVIEW_BYTES = 200 * 1024

# The Platform's bound on an error message.
MAX_ERROR_MESSAGE_LENGTH = 2000

# A vendor status that an SDK or connector wrote into its message rather than onto an
# attribute: Jamf's "failed with HTTP 401", a retry's "(HTTP 503)".
_HTTP_STATUS_IN_MESSAGE = re.compile(r"\bHTTP[ /]?(?:1\.[01] )?([1-5]\d\d)\b")


@dataclass(frozen=True)
class _Classified:
    category: DiscoverySourceTestErrorCategory
    reachability: DiscoverySourceReachability
    vendor_status_code: Optional[int]


class DiscoverySourceTestExecutor:
    def __init__(
        self,
        discovery_sources_client: DiscoverySourcesV1Api,
        logger: logging.Logger,
        scanners: Optional[dict[str, DiscoveryScannerFactory]] = None,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.discovery_sources_client = discovery_sources_client
        self.logger = logger
        # A copy, for the reason DiscoverAgentsExecutor copies it.
        self.scanners = dict(SOURCE_SCANNERS if scanners is None else scanners)
        self.clock = clock

    def execute(
        self,
        job: Job,
        job_run_id: str,
        job_spec: TestDiscoverySourceJobSpec,
    ) -> PutDiscoverySourceTestResult:
        """Run the test and report it. Raises only if the report cannot be delivered."""
        config = job_spec.discovery_source_config
        self.logger.info(
            f"Testing discovery source config '{config.name}' ({config.vendor}), "
            f"reading at most {job_spec.preview_limit} row(s)",
            extra={
                "discovery_source_config_id": str(job_spec.discovery_source_config_id),
                "vendor": config.vendor,
            },
        )
        result = _PreviewRun(self, job_spec).run()

        # Counts and the error only. The rows are customer data bound for one
        # authorized read route; the job log is listed far more widely.
        if result.error is not None:
            self.logger.warning(
                f"Test of source config '{config.name}' failed "
                f"({result.error.category.value}, reachability "
                f"{result.reachability.value}): {result.error.message}",
            )
        self.logger.info(
            f"Test of source config '{config.name}' read {len(result.rows or [])} "
            f"row(s){' (truncated)' if result.truncated else ''}; column check "
            f"{result.output_column_check.outcome.value if result.output_column_check else 'not run'}",
        )

        self.discovery_sources_client.put_discovery_source_test_result(
            job_id=str(job.id),
            job_run_id=str(job_run_id),
            put_discovery_source_test_result=result,
        )
        self.logger.info("Test result delivered to the Platform")
        return result


class _PreviewRun:
    """One test's state: the rows so far, the column check, and the scrub set."""

    def __init__(
        self,
        executor: DiscoverySourceTestExecutor,
        job_spec: TestDiscoverySourceJobSpec,
    ) -> None:
        self.executor = executor
        self.logger = executor.logger
        self.job_spec = job_spec
        self.config = job_spec.discovery_source_config
        self.limit = max(1, int(job_spec.preview_limit))
        self.started_at = datetime.now(timezone.utc)
        self.rows: list[dict[str, Any]] = []
        self.row_bytes = 0
        self.truncated = False
        self.column_check: Optional[OutputColumnCheckResult] = None
        self.batches_read = 0
        self.known_secrets: tuple[str, ...] = ()

    def run(self) -> PutDiscoverySourceTestResult:
        try:
            return self._run()
        except Exception as e:  # a defect here must still produce an answer
            return self._failed(
                DiscoverySourceTestErrorCategory.INTERNAL,
                DiscoverySourceReachability.UNKNOWN,
                f"The engine could not complete the test: {self._describe(e)}",
            )

    def _run(self) -> PutDiscoverySourceTestResult:
        scanner_factory = self.executor.scanners.get(self.config.vendor)
        if scanner_factory is None:
            return self._failed(
                DiscoverySourceTestErrorCategory.UNSUPPORTED_VENDOR,
                DiscoverySourceReachability.UNKNOWN,
                f"No discovery connector is registered for vendor "
                f"'{self.config.vendor}' on this engine.",
            )

        try:
            credentials: dict[str, Optional[str]] = (
                self.executor.discovery_sources_client.retrieve_discovery_source_credentials(
                    str(self.job_spec.discovery_source_config_id),
                )
            )
        except Exception as e:
            # Nothing came back, so there is nothing to scrub; the Platform's refusal
            # names only the config. Its status says which refusal it was.
            status = getattr(e, "status", None)
            return self._failed(
                DiscoverySourceTestErrorCategory.CREDENTIALS_UNAVAILABLE,
                DiscoverySourceReachability.UNKNOWN,
                f"The engine could not read this config's credentials from the "
                f"Platform{f' (HTTP {status})' if status else ''}: "
                f"{type(e).__name__}",
            )
        self.known_secrets = secret_values(credentials)
        register_secrets(self.logger, self.known_secrets)

        deadline = self.executor.clock() + PREVIEW_DEADLINE_SECONDS
        scan: Optional[Iterator[Sequence[DiscoveryOutputRecord]]] = None
        try:
            # Built inside the classified block: a scanner that validates its config
            # eagerly, before its first yield, is reporting a configuration problem,
            # not an engine defect.
            scan = scanner_factory().scan(
                self.config,
                int(self.job_spec.lookback_hours),
                credentials,
                dict(self.config.source_fields or {}),
                self.logger,
            )
            for batch in scan:
                if not batch:
                    continue
                self.batches_read += 1
                try:
                    self.column_check = check_batch(
                        batch,
                        f"Source config '{self.config.name}' ({self.config.vendor})",
                    )
                except OutputContractError as contract_error:
                    # The rows the source returned, as it returned them, so the
                    # unmapped columns can be seen beside the check that names them.
                    self.column_check = contract_error.result
                    self._take(_raw_row(item) for item in batch)
                    return self._failed(
                        DiscoverySourceTestErrorCategory.OUTPUT_CONTRACT,
                        DiscoverySourceReachability.REACHABLE,
                        str(contract_error),
                    )
                self._take(_mapped_row(record) for record in batch)
                if self.truncated:
                    break
                if self.executor.clock() >= deadline:
                    self.logger.info(
                        f"Test stopped at its {PREVIEW_DEADLINE_SECONDS:.0f}s deadline",
                    )
                    self.truncated = True
                    break
        except Exception as e:
            classified = _classify(e, contacted=self.batches_read > 0)
            return self._failed(
                classified.category,
                classified.reachability,
                self._describe(e),
                vendor_status_code=classified.vendor_status_code,
            )
        finally:
            # Stop the connector where it is rather than letting it page on: a
            # generator closed here never makes its next vendor call.
            close = getattr(scan, "close", None)
            if callable(close):
                close()

        return PutDiscoverySourceTestResult(
            outcome=DiscoverySourceTestOutcome.SUCCEEDED,
            # The connector ran to its end or to the limit without the vendor
            # refusing it, which it cannot have done without an answer.
            reachability=DiscoverySourceReachability.REACHABLE,
            rows=self.rows,
            truncated=self.truncated,
            output_column_check=self.column_check,
            error=None,
            started_at=self.started_at,
            finished_at=datetime.now(timezone.utc),
        )

    def _take(self, rows: Iterator[dict[str, Any]]) -> None:
        """Keep rows up to the limit and the size bound, redacted, and no further."""
        for row in rows:
            if len(self.rows) >= self.limit:
                self.truncated = True
                return
            row = _redact_row(row, self.known_secrets)
            size = len(json.dumps(row, default=str).encode())
            if self.row_bytes + size > MAX_PREVIEW_BYTES:
                self.truncated = True
                return
            self.rows.append(row)
            self.row_bytes += size
        if len(self.rows) >= self.limit:
            # At the limit: stop here rather than read another batch to learn
            # whether one exists.
            self.truncated = True

    def _describe(self, e: BaseException) -> str:
        return redact_secrets(f"{type(e).__name__}: {e}", self.known_secrets)

    def _failed(
        self,
        category: DiscoverySourceTestErrorCategory,
        reachability: DiscoverySourceReachability,
        message: str,
        vendor_status_code: Optional[int] = None,
    ) -> PutDiscoverySourceTestResult:
        message = redact_secrets(message, self.known_secrets)
        if len(message) > MAX_ERROR_MESSAGE_LENGTH:
            message = message[: MAX_ERROR_MESSAGE_LENGTH - 1] + "…"
        return PutDiscoverySourceTestResult(
            outcome=DiscoverySourceTestOutcome.FAILED,
            reachability=reachability,
            rows=self.rows,
            truncated=self.truncated,
            output_column_check=self.column_check,
            error=DiscoverySourceTestError(
                category=category,
                message=message,
                vendor_status_code=vendor_status_code,
            ),
            started_at=self.started_at,
            finished_at=datetime.now(timezone.utc),
        )


def _mapped_row(record: object) -> dict[str, Any]:
    """A record as the connector mapped it onto the output contract, JSON-safe."""
    if isinstance(record, DiscoveryOutputRecord):
        dumped: dict[str, Any] = record.model_dump(mode="json")
        return dumped
    # check_batch passed it, so this is not reached; kept total for safety.
    return _raw_row(record)


def _raw_row(item: object) -> dict[str, Any]:
    """A row as the source returned it, JSON-safe, for an output-contract failure."""
    if isinstance(item, Mapping):
        safe: dict[str, Any] = json.loads(
            json.dumps({str(k): v for k, v in item.items()}, default=str),
        )
        return safe
    return {"value": repr(item)}


def _redact_row(value: Any, known_secrets: Sequence[str]) -> Any:
    """Every string in a row, credentials removed. Keys are column names and kept."""
    if isinstance(value, str):
        return redact_secrets(value, known_secrets)
    if isinstance(value, dict):
        return {k: _redact_row(v, known_secrets) for k, v in value.items()}
    if isinstance(value, list):
        return [_redact_row(v, known_secrets) for v in value]
    return value


def _exception_chain(e: BaseException) -> Iterator[BaseException]:
    seen: set[int] = set()
    current: Optional[BaseException] = e
    while current is not None and id(current) not in seen:
        seen.add(id(current))
        yield current
        current = current.__cause__ or current.__context__


def _status_of(e: BaseException) -> Optional[int]:
    for candidate in (
        getattr(e, "status_code", None),
        getattr(getattr(e, "response", None), "status_code", None),
        getattr(e, "status", None),
    ):
        if isinstance(candidate, int) and 100 <= candidate <= 599:
            return candidate
    match = _HTTP_STATUS_IN_MESSAGE.search(str(e))
    return int(match.group(1)) if match else None


def _classify(e: BaseException, contacted: bool) -> _Classified:
    """Name a connector failure so a 401 reads differently from a DNS failure.

    The exception chain is read, not just the outermost exception: connectors wrap the
    transport error in their own type (`JamfError(...) from ConnectionError`), and the
    wrapper is what says nothing about the network.

    Any HTTP status means the host answered, so it is reachable whatever the status
    says about the credentials -- authentication rejection is not unreachability.
    """
    chain = list(_exception_chain(e))
    for link in chain:
        status = _status_of(link)
        if status is not None:
            category = {
                401: DiscoverySourceTestErrorCategory.AUTHENTICATION,
                403: DiscoverySourceTestErrorCategory.AUTHORIZATION,
            }.get(status, DiscoverySourceTestErrorCategory.VENDOR_ERROR)
            return _Classified(category, DiscoverySourceReachability.REACHABLE, status)

    for link in chain:
        if isinstance(link, requests.ConnectTimeout):
            return _Classified(
                DiscoverySourceTestErrorCategory.TIMEOUT,
                DiscoverySourceReachability.UNREACHABLE,
                None,
            )
        if isinstance(link, (requests.ReadTimeout, TimeoutError)):
            # Connected, then waited: the host is there but did not answer in time.
            return _Classified(
                DiscoverySourceTestErrorCategory.TIMEOUT,
                (
                    DiscoverySourceReachability.REACHABLE
                    if isinstance(link, requests.ReadTimeout)
                    else DiscoverySourceReachability.UNREACHABLE
                ),
                None,
            )
        if isinstance(link, (requests.ConnectionError, ConnectionError, OSError)):
            return _Classified(
                DiscoverySourceTestErrorCategory.NETWORK,
                DiscoverySourceReachability.UNREACHABLE,
                None,
            )

    reachability = (
        DiscoverySourceReachability.REACHABLE
        if contacted
        else DiscoverySourceReachability.UNKNOWN
    )
    if isinstance(e, (ValueError, KeyError, TypeError)) and not contacted:
        # Raised before the connector reached the vendor: a missing field, an http
        # URL. Nothing is known about the network.
        return _Classified(
            DiscoverySourceTestErrorCategory.CONFIGURATION,
            DiscoverySourceReachability.UNKNOWN,
            None,
        )
    return _Classified(
        DiscoverySourceTestErrorCategory.VENDOR_ERROR,
        reachability,
        None,
    )
