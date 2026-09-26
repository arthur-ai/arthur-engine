"""D-12: the Test Connection executor, against a fake scanner and against Jamf's.

What is under test is the contract the Platform and the UI read: the first N mapped
rows and no more, the output-column check naming unmapped columns, reachability that
tells a 401 from a DNS failure, the vendor's error with its credentials removed, and
nothing published anywhere but the one result route.
"""

import io
import logging
from datetime import datetime, timezone
from typing import Iterator, Mapping, Optional, Sequence
from unittest.mock import MagicMock

import pytest
import requests
import responses
from arthur_client.api_bindings import (
    DiscoverySourceConfigSpec,
    DiscoverySourceReachability,
    DiscoverySourcesV1Api,
    DiscoverySourceTestErrorCategory,
    DiscoverySourceTestOutcome,
    Job,
    PutDiscoverySourceTestResult,
    TestDiscoverySourceJobSpec,
    ValidationOutcome,
)
from arthur_client.api_bindings.exceptions import ForbiddenException
from arthur_common.models.agent_discovery_schemas import DiscoveryOutputRecord

from discovery.endpoint.jamf.client import JamfError
from discovery.endpoint.jamf.scanner import JamfScanner
from job_executors.discovery_source_test_executor import (
    PREVIEW_DEADLINE_SECONDS,
    DiscoverySourceTestExecutor,
)
from log_redaction import SecretRedactingFilter

JOB_ID = "77777777-7777-7777-7777-777777777777"
JOB_RUN_ID = "99999999-9999-9999-9999-999999999999"
CONFIG_ID = "33333333-3333-3333-3333-333333333333"
SOURCE_ID = "44444444-4444-4444-4444-444444444444"
CLIENT_SECRET = "shhh-this-is-a-fake-client-secret-42"
JAMF_URL = "https://tenant.jamfcloud.example"


def _spec(
    vendor: str = "fake_vendor",
    preview_limit: int = 4,
    source_fields: Optional[dict[str, str]] = None,
) -> TestDiscoverySourceJobSpec:
    return TestDiscoverySourceJobSpec(
        workspace_id="11111111-1111-1111-1111-111111111111",
        data_plane_id="22222222-2222-2222-2222-222222222222",
        discovery_source_config_id=CONFIG_ID,
        discovery_source_config=DiscoverySourceConfigSpec(
            discovery_source_id=SOURCE_ID,
            name="fake prod",
            vendor=vendor,
            query="",
            query_language="jamf_api",
            lookback_window_seconds=3600,
            source_fields=source_fields,
        ),
        lookback_hours=1,
        test_id="66666666-6666-6666-6666-666666666666",
        preview_limit=preview_limit,
    )


def _job() -> Job:
    job = MagicMock(spec=Job)
    job.id = JOB_ID
    return job


def _record(external_id: str) -> DiscoveryOutputRecord:
    return DiscoveryOutputRecord(
        external_id=external_id,
        name=f"agent-{external_id}",
        last_seen=datetime(2026, 9, 17, 12, 0, tzinfo=timezone.utc),
    )


class FakeScanner:
    """Yields the given batches, or raises after them; remembers how far it got."""

    def __init__(
        self,
        batches: Sequence[Sequence[object]] = (),
        raise_after: Optional[BaseException] = None,
    ) -> None:
        self.batches = batches
        self.raise_after = raise_after
        self.yielded = 0
        self.closed = False
        self.seen_credentials: Optional[Mapping[str, Optional[str]]] = None

    def scan(
        self,
        config: DiscoverySourceConfigSpec,
        lookback_hours: int,
        credentials: Mapping[str, Optional[str]],
        source_fields: Mapping[str, str],
        logger: logging.Logger,
    ) -> Iterator[Sequence[object]]:
        self.seen_credentials = credentials
        try:
            for batch in self.batches:
                self.yielded += 1
                yield batch
            if self.raise_after is not None:
                raise self.raise_after
        finally:
            self.closed = True


def _client(
    credentials: Optional[dict[str, str]] = None,
    credentials_error: Optional[Exception] = None,
) -> MagicMock:
    client = MagicMock(spec=DiscoverySourcesV1Api)
    if credentials_error is not None:
        client.retrieve_discovery_source_credentials.side_effect = credentials_error
    else:
        client.retrieve_discovery_source_credentials.return_value = (
            {"client_id": "fake-client-id", "client_secret": CLIENT_SECRET}
            if credentials is None
            else credentials
        )
    return client


@pytest.fixture
def job_log() -> tuple[logging.Logger, io.StringIO]:
    """A logger shaped like a job's: redacting filter on, output captured."""
    logger = logging.getLogger(f"test-connection-{id(object())}")
    logger.setLevel(logging.INFO)
    logger.addFilter(SecretRedactingFilter())
    stream = io.StringIO()
    logger.addHandler(logging.StreamHandler(stream))
    return logger, stream


def _run(
    scanner: object,
    spec: TestDiscoverySourceJobSpec,
    client: MagicMock,
    logger: logging.Logger,
    vendor: str = "fake_vendor",
    clock: Optional[object] = None,
) -> PutDiscoverySourceTestResult:
    kwargs = {"clock": clock} if clock is not None else {}
    return DiscoverySourceTestExecutor(
        client,
        logger,
        scanners={vendor: lambda: scanner},
        **kwargs,
    ).execute(_job(), JOB_RUN_ID, spec)


def _delivered(client: MagicMock) -> PutDiscoverySourceTestResult:
    client.put_discovery_source_test_result.assert_called_once()
    kwargs = client.put_discovery_source_test_result.call_args.kwargs
    assert kwargs["job_id"] == JOB_ID
    assert kwargs["job_run_id"] == JOB_RUN_ID
    result: PutDiscoverySourceTestResult = kwargs["put_discovery_source_test_result"]
    return result


def test_returns_the_first_n_mapped_rows_and_stops_reading(job_log) -> None:
    logger, _ = job_log
    scanner = FakeScanner(
        batches=[
            [_record("a"), _record("b"), _record("c")],
            [_record("d"), _record("e"), _record("f")],
            [_record("never-read")],
        ],
    )
    client = _client()

    _run(scanner, _spec(preview_limit=4), client, logger)

    result = _delivered(client)
    assert result.outcome == DiscoverySourceTestOutcome.SUCCEEDED
    assert result.reachability == DiscoverySourceReachability.REACHABLE
    assert [row["external_id"] for row in result.rows] == ["a", "b", "c", "d"]
    # rows are mapped onto the contract, not the vendor's raw payload
    assert result.rows[0]["name"] == "agent-a"
    assert result.rows[0]["last_seen"] == "2026-09-17T12:00:00Z"
    assert result.truncated is True
    assert result.output_column_check.outcome == ValidationOutcome.PASS
    assert result.error is None
    # the connector was stopped at the limit, not drained
    assert scanner.yielded == 2
    assert scanner.closed is True
    # credentials were fetched at run time and handed to the scanner
    client.retrieve_discovery_source_credentials.assert_called_once_with(CONFIG_ID)
    assert scanner.seen_credentials["client_secret"] == CLIENT_SECRET
    # the only write is the result: no publish, no chained job, no run outcome
    assert {name for name, _, _ in client.method_calls} == {
        "retrieve_discovery_source_credentials",
        "put_discovery_source_test_result",
    }


def test_a_401_is_reachable_and_surfaces_the_vendors_error_redacted(job_log) -> None:
    logger, log = job_log
    scanner = FakeScanner(
        raise_after=JamfError(
            f"Jamf token request failed with HTTP 401 for client_secret={CLIENT_SECRET} "
            "Authorization: Bearer eyJhbGciOiJIUzI1NiJ9.minted.at.runtime",
        ),
    )
    client = _client()

    _run(scanner, _spec(), client, logger)

    result = _delivered(client)
    assert result.outcome == DiscoverySourceTestOutcome.FAILED
    # a rejected credential proves the host answered
    assert result.reachability == DiscoverySourceReachability.REACHABLE
    assert result.error.category == DiscoverySourceTestErrorCategory.AUTHENTICATION
    assert result.error.vendor_status_code == 401
    assert "HTTP 401" in result.error.message
    assert result.error.message.startswith("JamfError: ")
    for leaked in (CLIENT_SECRET, "eyJhbGciOiJIUzI1NiJ9"):
        assert leaked not in result.error.message
        assert leaked not in log.getvalue()
    assert "[redacted]" in result.error.message
    # no rows were read, so nothing was checked -- distinct from a check that passed
    assert result.rows == []
    assert result.output_column_check is None


def test_jamfs_real_401_is_reported_as_authentication(job_log) -> None:
    """The real connector against a Jamf that rejects the client credentials."""
    logger, log = job_log
    client = _client()
    with responses.RequestsMock() as mock:
        mock.add(
            responses.POST,
            f"{JAMF_URL}/api/oauth/token",
            status=401,
            body=f'{{"error":"invalid_client","echo":"{CLIENT_SECRET}"}}',
        )
        _run(
            JamfScanner(),
            _spec(vendor="jamf_pro", source_fields={"base_url": JAMF_URL}),
            client,
            logger,
            vendor="jamf_pro",
        )

    result = _delivered(client)
    assert result.outcome == DiscoverySourceTestOutcome.FAILED
    assert result.reachability == DiscoverySourceReachability.REACHABLE
    assert result.error.category == DiscoverySourceTestErrorCategory.AUTHENTICATION
    assert result.error.vendor_status_code == 401
    assert result.error.message == (
        "JamfError: Jamf token request failed with HTTP 401"
    )
    assert CLIENT_SECRET not in log.getvalue()


def test_an_unreachable_host_is_not_an_authentication_failure(job_log) -> None:
    logger, _ = job_log
    client = _client()
    with responses.RequestsMock() as mock:
        mock.add(
            responses.POST,
            f"{JAMF_URL}/api/oauth/token",
            body=requests.ConnectionError(
                "Failed to resolve 'tenant.jamfcloud.example'",
            ),
        )
        _run(
            JamfScanner(),
            _spec(vendor="jamf_pro", source_fields={"base_url": JAMF_URL}),
            client,
            logger,
            vendor="jamf_pro",
        )

    result = _delivered(client)
    assert result.reachability == DiscoverySourceReachability.UNREACHABLE
    assert result.error.category == DiscoverySourceTestErrorCategory.NETWORK
    assert result.error.vendor_status_code is None


def test_a_wrapped_connection_timeout_reads_as_unreachable(job_log) -> None:
    logger, _ = job_log
    try:
        try:
            raise requests.ConnectTimeout("connect timed out")
        except requests.ConnectTimeout as exc:
            raise JamfError("Jamf GET /api/v1/computers-inventory unreachable") from exc
    except JamfError as wrapped:
        error = wrapped
    client = _client()

    _run(FakeScanner(raise_after=error), _spec(), client, logger)

    result = _delivered(client)
    assert result.reachability == DiscoverySourceReachability.UNREACHABLE
    assert result.error.category == DiscoverySourceTestErrorCategory.TIMEOUT


def test_a_missing_field_is_configuration_with_reachability_unknown(job_log) -> None:
    logger, _ = job_log
    client = _client()

    # no base_url source field: the Jamf connector refuses before any request
    _run(JamfScanner(), _spec(vendor="jamf_pro"), client, logger, vendor="jamf_pro")

    result = _delivered(client)
    assert result.error.category == DiscoverySourceTestErrorCategory.CONFIGURATION
    assert result.reachability == DiscoverySourceReachability.UNKNOWN
    assert "base_url" in result.error.message


def test_unmapped_columns_are_named_and_the_raw_rows_shown(job_log) -> None:
    logger, _ = job_log
    scanner = FakeScanner(
        batches=[
            [
                {
                    "external_id": "a",
                    "agentName": "Copilot",
                    "last_seen": "2026-09-17T12:00:00Z",
                    "note": f"token {CLIENT_SECRET}",
                },
            ],
        ],
    )
    client = _client()

    _run(scanner, _spec(), client, logger)

    result = _delivered(client)
    assert result.outcome == DiscoverySourceTestOutcome.FAILED
    assert result.error.category == DiscoverySourceTestErrorCategory.OUTPUT_CONTRACT
    assert result.reachability == DiscoverySourceReachability.REACHABLE
    assert result.output_column_check.outcome == ValidationOutcome.FAIL
    assert "name" in result.output_column_check.missing_columns
    assert set(result.output_column_check.unmapped_columns) == {"agentName", "note"}
    assert "agentName" in result.error.message
    # the row the source returned, so the mistake is visible -- credentials removed
    assert result.rows[0]["agentName"] == "Copilot"
    assert CLIENT_SECRET not in str(result.rows)


def test_an_empty_source_succeeds_without_a_column_check(job_log) -> None:
    logger, _ = job_log
    client = _client()

    _run(FakeScanner(batches=[[], []]), _spec(), client, logger)

    result = _delivered(client)
    assert result.outcome == DiscoverySourceTestOutcome.SUCCEEDED
    assert result.rows == []
    assert result.truncated is False
    assert result.output_column_check is None
    assert result.error is None


def test_the_deadline_stops_reading_and_keeps_what_was_read(job_log) -> None:
    logger, _ = job_log
    ticks = iter([0.0, PREVIEW_DEADLINE_SECONDS + 1])
    scanner = FakeScanner(batches=[[_record("a")], [_record("b")]])
    client = _client()

    _run(scanner, _spec(preview_limit=10), client, logger, clock=lambda: next(ticks))

    result = _delivered(client)
    assert result.outcome == DiscoverySourceTestOutcome.SUCCEEDED
    assert [row["external_id"] for row in result.rows] == ["a"]
    assert result.truncated is True
    assert scanner.yielded == 1


def test_an_unsupported_vendor_never_reads_credentials(job_log) -> None:
    logger, _ = job_log
    client = _client()

    DiscoverySourceTestExecutor(client, logger, scanners={}).execute(
        _job(),
        JOB_RUN_ID,
        _spec(vendor="splunk_enterprise"),
    )

    result = _delivered(client)
    assert result.error.category == DiscoverySourceTestErrorCategory.UNSUPPORTED_VENDOR
    assert result.reachability == DiscoverySourceReachability.UNKNOWN
    assert "splunk_enterprise" in result.error.message
    client.retrieve_discovery_source_credentials.assert_not_called()


def test_refused_credentials_are_reported_not_scanned(job_log) -> None:
    logger, _ = job_log
    scanner = FakeScanner(batches=[[_record("a")]])
    client = _client(credentials_error=ForbiddenException(status=403, reason="no"))

    _run(scanner, _spec(), client, logger)

    result = _delivered(client)
    assert (
        result.error.category
        == DiscoverySourceTestErrorCategory.CREDENTIALS_UNAVAILABLE
    )
    assert "HTTP 403" in result.error.message
    assert scanner.yielded == 0


def test_a_result_that_cannot_be_delivered_fails_the_job(job_log) -> None:
    logger, _ = job_log
    client = _client()
    client.put_discovery_source_test_result.side_effect = RuntimeError("platform down")

    with pytest.raises(RuntimeError, match="platform down"):
        _run(FakeScanner(batches=[[_record("a")]]), _spec(), client, logger)
