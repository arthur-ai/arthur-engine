import io
import json
import logging
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from typing import Iterator, Mapping, Sequence
from unittest.mock import MagicMock, call

import pytest
import urllib3
from arthur_client.api_bindings import (
    ApiClient,
    DiscoverAgentsJobSpec,
    DiscoverySourceConfigSpec,
    DiscoverySourcesV1Api,
    FetchDiscoveredAgentsJobSpec,
    Job,
    PostJobBatch,
    PostJobKind,
)
from arthur_client.api_bindings.exceptions import ForbiddenException
from arthur_client.api_bindings.rest import RESTResponse
from arthur_common.models.agent_discovery_schemas import DiscoveryOutputRecord
from genai_client import EnrichedTaskResponse

from job_executors.discover_agents_executor import (
    CHAINED_FETCH_SKEW,
    DiscoverAgentsExecutor,
)
from job_executors.discovery_scan import (
    SOURCE_SCANNERS,
    DiscoveryPublishResult,
    FailedDiscoveryRecord,
    UnsupportedDiscoveryVendorError,
)
from job_log_exporter import ExportContextedLogger, ScopeJobLogExporter
from log_redaction import redact_secrets, secret_values

WORKSPACE_ID = "11111111-1111-1111-1111-111111111111"
DATA_PLANE_ID = "22222222-2222-2222-2222-222222222222"
CONFIG_ID = "33333333-3333-3333-3333-333333333333"
SOURCE_ID = "44444444-4444-4444-4444-444444444444"
SIBLING_CONFIG_ID = "55555555-5555-5555-5555-555555555555"
SCAN_ID = "66666666-6666-6666-6666-666666666666"
PROJECT_ID = "88888888-8888-8888-8888-888888888888"
FAKE_TOKEN = "shhh-this-is-a-fake-credential"


def _config(
    name: str = "splunk prod",
    vendor: str = "splunk_enterprise",
    lookback_window_seconds: int = 3600,
    source_fields: dict[str, str] | None = None,
) -> DiscoverySourceConfigSpec:
    return DiscoverySourceConfigSpec(
        discovery_source_id=SOURCE_ID,
        name=name,
        vendor=vendor,
        query="search index=agents",
        query_language="spl",
        lookback_window_seconds=lookback_window_seconds,
        source_fields=source_fields,
    )


def _spec(
    config: DiscoverySourceConfigSpec | None = None,
    config_id: str | None = CONFIG_ID,
    lookback_hours: int | None = 1,
    scan_id: str | None = SCAN_ID,
) -> DiscoverAgentsJobSpec:
    return DiscoverAgentsJobSpec(
        workspace_id=WORKSPACE_ID,
        data_plane_id=DATA_PLANE_ID,
        lookback_hours=lookback_hours,
        discovery_source_config_id=config_id,
        discovery_source_config=config,
        scan_id=scan_id,
    )


def _record(external_id: str) -> DiscoveryOutputRecord:
    return DiscoveryOutputRecord(
        external_id=external_id,
        name=f"agent-{external_id}",
        last_seen=datetime(2026, 9, 17, 12, 0, tzinfo=timezone.utc),
    )


def _job(job_id: str = "77777777-7777-7777-7777-777777777777") -> Job:
    job = MagicMock(spec=Job)
    job.id = job_id
    job.project_id = PROJECT_ID
    return job


class RecordingSink:
    """Accepts every record and remembers what it was given, in order."""

    def __init__(self) -> None:
        self.batches: list[list[str]] = []
        self.configs: list[str] = []

    def publish(
        self,
        workspace_id: str,
        data_plane_id: str,
        config: DiscoverySourceConfigSpec,
        records: Sequence[DiscoveryOutputRecord],
    ) -> DiscoveryPublishResult:
        self.batches.append([r.external_id for r in records])
        self.configs.append(config.name)
        return DiscoveryPublishResult(accepted=len(records))


class PartlyFailingSink(RecordingSink):
    """Resolves every record except the named ones, which it reports as failed."""

    def __init__(self, failing_external_ids: set[str]) -> None:
        super().__init__()
        self.failing_external_ids = failing_external_ids

    def publish(
        self,
        workspace_id: str,
        data_plane_id: str,
        config: DiscoverySourceConfigSpec,
        records: Sequence[DiscoveryOutputRecord],
    ) -> DiscoveryPublishResult:
        super().publish(workspace_id, data_plane_id, config, records)
        failed = [
            FailedDiscoveryRecord(
                external_id=r.external_id,
                reason="task_not_found",
                detail=f"Discovered record '{r.external_id}' resolved to task "
                "'missing-task', which does not exist",
            )
            for r in records
            if r.external_id in self.failing_external_ids
        ]
        return DiscoveryPublishResult(
            accepted=len(records) - len(failed),
            failed=failed,
        )


class RaisingSink(RecordingSink):
    """Accepts batches until the given one, then throws before it could report any."""

    def __init__(self, fail_on_batch: int) -> None:
        super().__init__()
        self.fail_on_batch = fail_on_batch

    def publish(
        self,
        workspace_id: str,
        data_plane_id: str,
        config: DiscoverySourceConfigSpec,
        records: Sequence[DiscoveryOutputRecord],
    ) -> DiscoveryPublishResult:
        if len(self.batches) + 1 == self.fail_on_batch:
            raise RuntimeError("platform rejected the batch")
        return super().publish(workspace_id, data_plane_id, config, records)


class FakeScanner:
    """Yields the given batches, then optionally throws."""

    def __init__(
        self,
        batches: list[list[DiscoveryOutputRecord]],
        raises: BaseException | None = None,
    ) -> None:
        self.batches = batches
        self.raises = raises
        self.calls: list[tuple[str, int]] = []
        self.credentials: list[dict[str, str | None]] = []
        self.loggers: list[logging.Logger] = []
        self.source_fields: list[dict[str, str]] = []

    def scan(
        self,
        config: DiscoverySourceConfigSpec,
        lookback_hours: int,
        credentials: Mapping[str, str | None],
        source_fields: Mapping[str, str],
        logger: logging.Logger,
    ) -> Iterator[Sequence[DiscoveryOutputRecord]]:
        self.calls.append((config.name, lookback_hours))
        self.credentials.append(dict(credentials))
        self.source_fields.append(dict(source_fields))
        self.loggers.append(logger)
        for batch in self.batches:
            yield batch
        if self.raises is not None:
            raise self.raises


CONFIGURED_SECRET = "cfg-fake-credential-value"


def _http_response(status: int, body: object) -> RESTResponse:
    """What the transport hands the generated client for one request."""
    return RESTResponse(
        urllib3.HTTPResponse(
            body=io.BytesIO(json.dumps(body).encode()),
            headers={"content-type": "application/json"},
            status=status,
            preload_content=False,
        ),
    )


def _credentials_client(
    credentials: dict[str, str | None] | None = None,
    source_fields: dict[str, str] | None = None,
    status: int = 200,
) -> DiscoverySourcesV1Api:
    """Stands in for the D-05 route, which returns the sensitive fields and only those,
    and for the source read that returns the non-sensitive ones.

    The credentials read goes through the real generated client over a stubbed
    transport rather than a mock of its return value, so a response the client cannot
    deserialize fails here instead of on the first real scan."""
    client = DiscoverySourcesV1Api(ApiClient())
    client.api_client.call_api = MagicMock(  # type: ignore[method-assign]
        return_value=_http_response(
            status,
            {"password": CONFIGURED_SECRET} if credentials is None else credentials,
        ),
    )
    source = MagicMock()
    source.fields = [
        SimpleNamespace(key=k, value=v)
        for k, v in (source_fields or {"base_url": "https://splunk.example"}).items()
    ]
    client.get_discovery_source = MagicMock(  # type: ignore[method-assign]
        return_value=source,
    )
    return client


def _executor(
    scanner: FakeScanner | None = None,
    sink: RecordingSink | None = None,
    vendor: str = "splunk_enterprise",
    logger: logging.Logger | None = None,
    credentials_client: DiscoverySourcesV1Api | None = None,
    jobs_client: MagicMock | None = None,
) -> DiscoverAgentsExecutor:
    return DiscoverAgentsExecutor(
        agents_client=MagicMock(),
        logger=logger or logging.getLogger("test-discovery"),
        genai_engine_url="http://genai",
        genai_engine_api_key="key",
        discovery_sources_client=credentials_client or _credentials_client(),
        record_sink=sink or RecordingSink(),
        scanners={vendor: lambda: scanner} if scanner is not None else {},
        jobs_client=jobs_client or MagicMock(),
    )


def test_scan_publishes_every_batch_from_its_one_config() -> None:
    scanner = FakeScanner([[_record("a"), _record("b")], [_record("c")]])
    sink = RecordingSink()

    _executor(scanner, sink).execute(_job(), _spec(_config()))

    assert sink.batches == [["a", "b"], ["c"]]
    assert sink.configs == ["splunk prod", "splunk prod"]
    assert scanner.calls == [("splunk prod", 1)]


def test_mid_scan_failure_keeps_already_published_records() -> None:
    """The acceptance criterion: partial results survive, and the job still fails."""
    scanner = FakeScanner(
        [[_record("a")], [_record("b")]],
        raises=RuntimeError("source went away"),
    )
    sink = RecordingSink()

    with pytest.raises(RuntimeError, match="source went away"):
        _executor(scanner, sink).execute(_job(), _spec(_config()))

    assert sink.batches == [["a"], ["b"]]


def test_failing_source_reports_its_contribution_and_its_failure() -> None:
    scanner = FakeScanner([[_record("a"), _record("b")]], raises=RuntimeError("boom"))
    logger = logging.getLogger("test-discovery-outcome")
    records = _capture(logger)

    with pytest.raises(RuntimeError):
        _executor(scanner, logger=logger).execute(_job(), _spec(_config()))

    outcome = _find_outcome(records)
    assert outcome["records_published"] == 2
    assert outcome["batches_published"] == 1
    assert outcome["error_count"] == 1
    assert outcome["error"] == "RuntimeError: boom"
    assert outcome["succeeded"] is False


def test_successful_scan_reports_a_clean_outcome() -> None:
    logger = logging.getLogger("test-discovery-outcome-ok")
    scanner = FakeScanner([[_record("a")]])
    records = _capture(logger)

    _executor(scanner, logger=logger).execute(_job(), _spec(_config()))

    outcome = _find_outcome(records)
    assert outcome["succeeded"] is True
    assert outcome["error"] is None
    assert outcome["records_published"] == 1
    assert outcome["discovery_source_config_id"] == CONFIG_ID
    assert outcome["discovery_source_id"] == SOURCE_ID
    assert outcome["scan_id"] == SCAN_ID
    assert outcome["vendor"] == "splunk_enterprise"


def test_a_sources_failure_does_not_touch_a_sibling_config() -> None:
    """Two configs are two jobs, so one blowing up cannot reach the other.

    The executor is the shared piece, so the check that matters is that a failed run
    leaves nothing behind that changes the next one: the sibling scans its own config,
    with its own lookback, and publishes its own records.
    """
    sink = RecordingSink()
    failing = FakeScanner([[_record("a")]], raises=RuntimeError("splunk down"))

    with pytest.raises(RuntimeError):
        _executor(failing, sink).execute(_job(), _spec(_config()))

    sibling_config = DiscoverySourceConfigSpec(
        discovery_source_id=SOURCE_ID,
        name="bedrock us-east-1",
        vendor="aws_bedrock",
        query="",
        query_language="none",
        lookback_window_seconds=14400,
    )
    healthy = FakeScanner([[_record("z")]])
    sibling_spec = _spec(
        sibling_config,
        config_id=SIBLING_CONFIG_ID,
        lookback_hours=4,
    )

    _executor(healthy, sink, vendor="aws_bedrock").execute(_job(), sibling_spec)

    assert healthy.calls == [("bedrock us-east-1", 4)]
    assert sink.batches == [["a"], ["z"]]


def test_unregistered_vendor_fails_only_this_job() -> None:
    sink = RecordingSink()

    with pytest.raises(UnsupportedDiscoveryVendorError, match="jamf_pro"):
        _executor(sink=sink).execute(_job(), _spec(_config(vendor="jamf_pro")))

    assert sink.batches == []


def test_unregistered_vendor_still_reports_an_outcome() -> None:
    """A job that never reaches the vendor owes the Platform an outcome all the same."""
    logger = logging.getLogger("test-discovery-outcome-vendor")
    records = _capture(logger)

    with pytest.raises(UnsupportedDiscoveryVendorError):
        _executor(logger=logger).execute(_job(), _spec(_config(vendor="jamf_pro")))

    outcome = _find_outcome(records)
    assert outcome["succeeded"] is False
    assert outcome["error_count"] == 1
    assert "jamf_pro" in outcome["error"]
    assert outcome["vendor"] == "jamf_pro"
    assert outcome["records_published"] == 0
    assert outcome["finished_at"] is not None


def test_missing_record_sink_still_reports_an_outcome() -> None:
    logger = logging.getLogger("test-discovery-outcome-sink")
    records = _capture(logger)
    executor = DiscoverAgentsExecutor(
        agents_client=MagicMock(),
        logger=logger,
        genai_engine_url="http://genai",
        genai_engine_api_key="key",
        record_sink=None,
        scanners={"splunk_enterprise": lambda: FakeScanner([[_record("a")]])},
    )

    with pytest.raises(RuntimeError, match="No discovery record sink"):
        executor.execute(_job(), _spec(_config()))

    outcome = _find_outcome(records)
    assert outcome["succeeded"] is False
    assert outcome["error_count"] == 1
    assert outcome["error"].startswith("RuntimeError: No discovery record sink")
    assert outcome["records_published"] == 0
    assert outcome["finished_at"] is not None


def test_job_naming_a_config_it_does_not_carry_is_rejected() -> None:
    scanner = FakeScanner([[_record("a")]])

    with pytest.raises(ValueError, match="no materialized config"):
        _executor(scanner).execute(_job(), _spec(None))


def test_job_naming_a_config_it_does_not_carry_still_reports_an_outcome() -> None:
    """A dispatch bug is still a run, and a run the Platform never hears about is
    indistinguishable from one that was never enqueued."""
    logger = logging.getLogger("test-discovery-outcome-no-config")
    records = _capture(logger)

    with pytest.raises(ValueError):
        _executor(FakeScanner([]), logger=logger).execute(_job(), _spec(None))

    outcome = _find_outcome(records)
    assert outcome["succeeded"] is False
    assert outcome["error_count"] == 1
    assert "no materialized config" in outcome["error"]
    assert outcome["finished_at"] is not None
    assert outcome["records_published"] == 0
    # The half the dispatcher did send, and nulls for the half it did not.
    assert outcome["discovery_source_config_id"] == CONFIG_ID
    assert outcome["scan_id"] == SCAN_ID
    assert outcome["discovery_source_config_name"] is None
    assert outcome["discovery_source_id"] is None
    assert outcome["vendor"] is None


def test_job_carrying_a_config_with_no_id_is_rejected() -> None:
    scanner = FakeScanner([[_record("a")]])

    with pytest.raises(ValueError, match="no discovery_source_config_id"):
        _executor(scanner).execute(_job(), _spec(_config(), config_id=None))


def test_job_carrying_a_config_with_no_id_still_reports_an_outcome() -> None:
    logger = logging.getLogger("test-discovery-outcome-no-id")
    records = _capture(logger)

    with pytest.raises(ValueError):
        _executor(FakeScanner([]), logger=logger).execute(
            _job(),
            _spec(_config(), config_id=None),
        )

    outcome = _find_outcome(records)
    assert outcome["succeeded"] is False
    assert outcome["error_count"] == 1
    assert "no discovery_source_config_id" in outcome["error"]
    assert outcome["finished_at"] is not None
    assert outcome["records_published"] == 0
    assert outcome["discovery_source_config_id"] is None
    assert outcome["discovery_source_config_name"] == "splunk prod"
    assert outcome["discovery_source_id"] == SOURCE_ID
    assert outcome["vendor"] == "splunk_enterprise"


def test_a_rejected_job_publishes_nothing() -> None:
    sink = RecordingSink()

    with pytest.raises(ValueError):
        _executor(FakeScanner([[_record("a")]]), sink).execute(_job(), _spec(None))

    assert sink.batches == []


def test_lookback_is_the_dispatched_window_not_the_configs() -> None:
    """D-06 already rounded the config's window into lookback_hours; that is what runs."""
    scanner = FakeScanner([])

    _executor(scanner).execute(
        _job(),
        _spec(_config(lookback_window_seconds=5400), lookback_hours=6),
    )

    assert scanner.calls == [("splunk prod", 6)]


def test_job_carrying_no_lookback_is_rejected_rather_than_guessed() -> None:
    logger = logging.getLogger("test-discovery-outcome-no-lookback")
    records = _capture(logger)
    scanner = FakeScanner([[_record("a")]])

    with pytest.raises(ValueError, match="no lookback_hours"):
        _executor(scanner, logger=logger).execute(
            _job(),
            _spec(_config(), lookback_hours=None),
        )

    outcome = _find_outcome(records)
    assert outcome["succeeded"] is False
    assert outcome["lookback_hours"] is None
    assert scanner.calls == []


def test_missing_credentials_client_still_reports_an_outcome() -> None:
    logger = logging.getLogger("test-discovery-outcome-no-client")
    records = _capture(logger)
    sink = RecordingSink()
    executor = DiscoverAgentsExecutor(
        agents_client=MagicMock(),
        logger=logger,
        genai_engine_url="http://genai",
        genai_engine_api_key="key",
        discovery_sources_client=None,
        record_sink=sink,
        scanners={"splunk_enterprise": lambda: FakeScanner([[_record("a")]])},
    )

    with pytest.raises(RuntimeError, match="No discovery sources client"):
        executor.execute(_job(), _spec(_config()))

    outcome = _find_outcome(records)
    assert outcome["succeeded"] is False
    assert outcome["error"].startswith("RuntimeError: No discovery sources client")
    assert sink.batches == []


def test_records_that_fail_resolution_are_reported_without_failing_the_scan() -> None:
    """A mixed batch keeps both halves: the records that resolved count as the
    source's contribution, the one that did not is carried on the outcome for whoever
    configured the source, and the scan itself still succeeded."""
    logger = logging.getLogger("test-discovery-outcome-partial")
    records = _capture(logger)
    sink = PartlyFailingSink({"b"})
    scanner = FakeScanner([[_record("a"), _record("b"), _record("c")]])

    _executor(scanner, sink, logger=logger).execute(_job(), _spec(_config()))

    outcome = _find_outcome(records)
    assert outcome["succeeded"] is True
    assert outcome["records_published"] == 2
    assert outcome["records_failed"] == 1
    assert outcome["failed_records"] == [
        {
            "external_id": "b",
            "reason": "task_not_found",
            "detail": "Discovered record 'b' resolved to task 'missing-task', "
            "which does not exist",
        },
    ]


def test_failed_records_accumulate_across_batches() -> None:
    logger = logging.getLogger("test-discovery-outcome-partial-batches")
    records = _capture(logger)
    sink = PartlyFailingSink({"a", "d"})
    scanner = FakeScanner([[_record("a"), _record("b")], [_record("c"), _record("d")]])

    _executor(scanner, sink, logger=logger).execute(_job(), _spec(_config()))

    outcome = _find_outcome(records)
    assert outcome["records_published"] == 2
    assert [r["external_id"] for r in outcome["failed_records"]] == ["a", "d"]


def test_a_clean_scan_reports_no_failed_records() -> None:
    logger = logging.getLogger("test-discovery-outcome-no-failures")
    records = _capture(logger)

    _executor(FakeScanner([[_record("a")]]), logger=logger).execute(
        _job(),
        _spec(_config()),
    )

    outcome = _find_outcome(records)
    assert outcome["records_failed"] == 0
    assert outcome["failed_records"] == []


def test_a_failing_publish_counts_only_the_batches_that_landed() -> None:
    """A batch whose publish raised never reported what it resolved, so it is not
    counted, while the batches before it still are."""
    logger = logging.getLogger("test-discovery-outcome-sink-raises")
    records = _capture(logger)
    sink = RaisingSink(fail_on_batch=2)
    scanner = FakeScanner(
        [[_record("a"), _record("b")], [_record("c")], [_record("d")]],
    )

    with pytest.raises(RuntimeError, match="platform rejected the batch"):
        _executor(scanner, sink, logger=logger).execute(_job(), _spec(_config()))

    assert sink.batches == [["a", "b"]]
    outcome = _find_outcome(records)
    assert outcome["batches_published"] == 1
    assert outcome["records_published"] == 2
    assert outcome["error"] == "RuntimeError: platform rejected the batch"
    assert outcome["succeeded"] is False


def test_a_killed_scan_is_not_reported_as_a_success() -> None:
    """Shutdown mid-scan skips `except Exception` but still runs the finally."""
    logger = logging.getLogger("test-discovery-outcome-killed")
    records = _capture(logger)
    scanner = FakeScanner([[_record("a"), _record("b")]], raises=KeyboardInterrupt())

    with pytest.raises(KeyboardInterrupt):
        _executor(scanner, logger=logger).execute(_job(), _spec(_config()))

    outcome = _find_outcome(records)
    assert outcome["succeeded"] is False
    assert outcome["error"] == "KeyboardInterrupt: "
    assert outcome["error_count"] == 1
    assert outcome["records_published"] == 2


def test_every_scan_gets_its_own_scanner() -> None:
    """Two jobs for the same vendor must not share per-scan state."""
    built: list[FakeScanner] = []

    def factory() -> FakeScanner:
        built.append(FakeScanner([[_record("a")]]))
        return built[-1]

    executor = _executor()
    executor.scanners = {"splunk_enterprise": factory}
    executor.execute(_job(), _spec(_config()))
    executor.execute(_job(), _spec(_config()))

    assert len(built) == 2
    assert all(len(scanner.calls) == 1 for scanner in built)


def test_an_executor_does_not_alias_the_global_registry() -> None:
    executor = DiscoverAgentsExecutor(
        agents_client=MagicMock(),
        logger=logging.getLogger("test-discovery-registry"),
        genai_engine_url="http://genai",
        genai_engine_api_key="key",
    )

    # A vendor no connector registers, so this asserts the copy rather than which
    # connectors happen to ship: `jamf_pro` is a real registered vendor now.
    executor.scanners["not_a_real_vendor"] = lambda: FakeScanner([])

    assert "not_a_real_vendor" not in SOURCE_SCANNERS


def test_empty_batches_are_not_published() -> None:
    scanner = FakeScanner([[], [_record("a")], []])
    sink = RecordingSink()

    _executor(scanner, sink).execute(_job(), _spec(_config()))

    assert sink.batches == [["a"]]


def test_configured_credentials_are_removed_exactly() -> None:
    """The control: the values D-05 handed this scan, whatever shape they turn up in.

    None of these messages is credential-shaped -- no header, no query parameter, no
    key name -- so nothing but exact removal can catch them.
    """
    secrets = secret_values({"password": CONFIGURED_SECRET, "username": "svc"})

    for message in (
        f"LoginFailed: rejected for user svc ({CONFIGURED_SECRET})",
        f"RuntimeError: retrying <Session cred={CONFIGURED_SECRET!r}>",
        f"KeyError: {{'password': '{CONFIGURED_SECRET}', 'host': 'splunk'}}",
    ):
        redacted = redact_secrets(message, secrets)
        assert CONFIGURED_SECRET not in redacted
        assert "[redacted]" in redacted


def test_a_secret_is_not_left_half_blanked_by_a_shorter_one() -> None:
    """Longest-first, or the tail of the longer secret survives as ordinary text."""
    redacted = redact_secrets(
        "failed with abcd1234-extended",
        secret_values({"short": "abcd1234", "long": "abcd1234-extended"}),
    )

    assert redacted == "failed with [redacted]"


def test_values_too_short_to_be_credentials_are_left_alone() -> None:
    """Scrubbing a two-character value would shred the message it is protecting."""
    assert redact_secrets(
        "ValueError: region eu is not valid",
        secret_values({"r": "eu"}),
    ) == ("ValueError: region eu is not valid")


@pytest.mark.parametrize(
    "message",
    [
        # An OAuth access token, minted from client_secret inside the scan.
        "HTTPError: 401 Authorization: Bearer drv-fake-access-token-value",
        # A Splunk session key: the scheme is not one anybody thought to enumerate.
        "HTTPError: 401 header Authorization: Splunk drv-fake-access-token-value",
        "KeyError: {'Authorization': 'Splunk drv-fake-access-token-value'}",
        "JWTError: rejected Bearer drv-fake-access-token-value",
        "HTTPError: 403 for https://s3.amazonaws.com/b/o"
        "?X-Amz-Signature=drv-fake-access-token-value&X-Amz-Date=2026",
    ],
)
def test_derived_credentials_are_caught_by_the_backstop(message: str) -> None:
    """Runtime-minted credentials are never in the scrub set, so patterns must hold.

    Passing no known_secrets is the point: these values were never handed to us.
    """
    redacted = redact_secrets(message)

    assert "drv-fake-access-token-value" not in redacted
    assert "[redacted]" in redacted


@pytest.mark.parametrize(
    "message",
    [
        "SyntaxError: Unexpected token: 'stats' at position 14",
        "JSONDecodeError: invalid token: expected ',' delimiter",
        "HTTPError: 500 for https://splunk.example.com/services/search"
        "?output_mode=json&count=100&earliest=-24h",
        "ConnectionError: auth: handshake timed out after 30s",
        "AuthError: token: expired at 2026-09-01T00:00:00Z",
        "Warning: cookie: SameSite=None requires Secure",
        "RuntimeError: boom",
    ],
)
def test_the_backstop_leaves_ordinary_error_prose_alone(message: str) -> None:
    """The diagnosis is the whole value of the message; over-redaction destroys it."""
    assert redact_secrets(message) == message


@pytest.mark.parametrize(
    "message",
    [
        "ConnectionError: splunk enterprise host unreachable",
        "ValueError: Basic configuration missing for connector",
        "TimeoutError: token refresh_endpoint timed out",
        "GET /x?design=modern&assignee=alice&monkey=1&keyword=agents&author=bob",
        "HTTPError: 400 for https://s3.amazonaws.com/b/o?signature_version=v4",
    ],
)
def test_the_backstop_leaves_scheme_words_and_lookalike_names_alone(
    message: str,
) -> None:
    """A scheme word followed by ordinary prose, and a parameter whose name merely
    contains a credential word, are not credentials."""
    assert redact_secrets(message) == message


@pytest.mark.parametrize(
    ("message", "expected"),
    [
        (
            "HTTPError: 401 Authorization: Bearer abc12345 while GET "
            "https://splunk.example.com/services/search returned 401",
            "HTTPError: 401 Authorization: Bearer [redacted] while GET "
            "https://splunk.example.com/services/search returned 401",
        ),
        (
            "HTTPError: 401 Authorization: abc12345 while GET /services/search",
            "HTTPError: 401 Authorization: [redacted] while GET /services/search",
        ),
        (
            "GET /services/search?access_token=abc12345&count=100 returned 401",
            "GET /services/search?access_token=[redacted]&count=100 returned 401",
        ),
    ],
)
def test_the_backstop_takes_the_credential_and_not_the_rest_of_the_line(
    message: str,
    expected: str,
) -> None:
    """An SDK stringifying the request it failed on puts the credential mid-line;
    the URL and status after it are the diagnosis."""
    assert redact_secrets(message) == expected


def test_redacting_twice_changes_nothing() -> None:
    """The filter and the exporter both scrub, so a second pass must be a no-op."""
    message = (
        f"401 for {CONFIGURED_SECRET}; Authorization: Splunk drv-fake-access-token-value"
        " at /x?api_key=abc12345&count=1"
    )
    once = redact_secrets(message, (CONFIGURED_SECRET,))

    assert redact_secrets(once, (CONFIGURED_SECRET,)) == once


def test_the_scan_is_handed_the_credentials_it_authenticates_with() -> None:
    scanner = FakeScanner([[_record("a")]])
    credentials = {"username": "svc", "password": CONFIGURED_SECRET}

    _executor(
        scanner,
        credentials_client=_credentials_client(credentials),
    ).execute(_job(), _spec(_config()))

    assert scanner.credentials == [credentials]


def test_the_scan_connects_where_the_job_says_without_reading_the_source() -> None:
    """The engine's account cannot read the discovery source -- that takes an
    organization-level role -- so the fields the Platform snapshotted into the job
    are the ones used, and the source is never fetched."""
    scanner = FakeScanner([[_record("a")]])
    client = _credentials_client()

    _executor(scanner, credentials_client=client).execute(
        _job(),
        _spec(_config(source_fields={"base_url": "https://jamf.example"})),
    )

    assert scanner.source_fields == [{"base_url": "https://jamf.example"}]
    client.get_discovery_source.assert_not_called()  # type: ignore[attr-defined]


def test_a_job_dispatched_before_the_snapshot_reads_the_source() -> None:
    scanner = FakeScanner([[_record("a")]])
    client = _credentials_client(source_fields={"base_url": "https://splunk.example"})

    _executor(scanner, credentials_client=client).execute(_job(), _spec(_config()))

    assert scanner.source_fields == [{"base_url": "https://splunk.example"}]
    client.get_discovery_source.assert_called_once_with(  # type: ignore[attr-defined]
        SOURCE_ID
    )


def test_neither_kind_of_credential_reaches_the_job_log() -> None:
    """End to end: the outcome rides to the Platform as log text, so a vendor error
    carrying both a configured field and a token minted from it must leave neither."""
    logger = logging.getLogger("test-discovery-outcome-redaction")
    records = _capture(logger)
    scanner = FakeScanner(
        [[_record("a")]],
        raises=RuntimeError(
            f"401 for user svc ({CONFIGURED_SECRET}); "
            "retried with Authorization: Splunk drv-fake-access-token-value",
        ),
    )

    with pytest.raises(RuntimeError):
        _executor(scanner, logger=logger).execute(_job(), _spec(_config()))

    outcome = _find_outcome(records)
    assert CONFIGURED_SECRET not in outcome["error"]
    assert "drv-fake-access-token-value" not in outcome["error"]
    assert outcome["error"].startswith("RuntimeError: 401 for user svc")
    assert outcome["error_count"] == 1
    # Not just the outcome: every message this job emits is shipped.
    for secret in (CONFIGURED_SECRET, "drv-fake-access-token-value"):
        assert not any(secret in record.getMessage() for record in records)


def test_neither_kind_of_credential_reaches_the_platform() -> None:
    """Through the real exporter, as JobExecutor wires it.

    The scan no longer logs with `exc_info`: the exporter formats that itself and posts
    the result unredacted, so the traceback is redacted and carried in the message
    instead. The escaping exception still reaches JobExecutor's own handler, which does
    log with `exc_info` -- so its `args` are redacted in place before it is re-raised.
    """
    derived = "drv-fake-access-token-value"
    logger = logging.getLogger("test-discovery-exporter-redaction")
    logger.setLevel(logging.INFO)
    stdout_records = _capture(logger)
    jobs_client = MagicMock()
    exporter = ScopeJobLogExporter(
        job_id="job",
        job_run_id="run",
        jobs_client=jobs_client,
    )
    scanner = FakeScanner(
        [[_record("a")]],
        raises=RuntimeError(
            f"401 for user svc ({CONFIGURED_SECRET}); "
            f"retried with Authorization: Splunk {derived}",
        ),
    )

    with ExportContextedLogger(logger, exporter):
        try:
            _executor(scanner, logger=logger).execute(_job(), _spec(_config()))
        except RuntimeError as e:
            # JobExecutor.execute's own handler.
            logger.error("Error executing job", exc_info=e)

    shipped = [
        log.log
        for posted in jobs_client.post_job_logs.call_args_list
        for log in posted.args[2].logs
    ] + [
        error.error
        for posted in jobs_client.post_job_errors.call_args_list
        for error in posted.kwargs["job_errors"].errors
    ]
    assert jobs_client.post_job_errors.call_count >= 1
    # The diagnosis survives: the message, and the traceback now carried inside it.
    assert any("401 for user svc" in text for text in shipped)
    assert any("Traceback (most recent call last)" in text for text in shipped)
    formatter = logging.Formatter()
    printed = [formatter.format(record) for record in stdout_records]
    for secret in (CONFIGURED_SECRET, derived):
        assert not any(secret in text for text in shipped)
        assert not any(secret in text for text in printed)
    # The filter is the job's, and leaves with it.
    assert logger.filters == []
    assert jobs_client.post_job_logs.call_args_list[0] != call()


def test_a_credentials_fetch_failure_still_reports_an_outcome() -> None:
    logger = logging.getLogger("test-discovery-outcome-creds")
    records = _capture(logger)
    client = _credentials_client()
    client.api_client.call_api.side_effect = RuntimeError(  # type: ignore[attr-defined]
        "credentials unavailable",
    )
    sink = RecordingSink()

    with pytest.raises(RuntimeError, match="credentials unavailable"):
        _executor(
            FakeScanner([[_record("a")]]),
            sink,
            logger=logger,
            credentials_client=client,
        ).execute(_job(), _spec(_config()))

    outcome = _find_outcome(records)
    assert outcome["succeeded"] is False
    assert outcome["error_count"] == 1
    assert outcome["records_published"] == 0
    assert outcome["finished_at"] is not None
    assert sink.batches == []


def test_a_denied_credentials_read_still_fails_the_run() -> None:
    """Decoding the raw response must not swallow an error status: the route answers
    403 to an engine that is not assigned the config, and that has to fail the run."""
    logger = logging.getLogger("test-discovery-outcome-creds-denied")
    records = _capture(logger)
    sink = RecordingSink()

    with pytest.raises(ForbiddenException):
        _executor(
            FakeScanner([[_record("a")]]),
            sink,
            logger=logger,
            credentials_client=_credentials_client(
                {"detail": "Discovery credential access denied."},
                status=403,
            ),
        ).execute(_job(), _spec(_config()))

    outcome = _find_outcome(records)
    assert outcome["succeeded"] is False
    assert outcome["records_published"] == 0
    assert sink.batches == []


OTEL_SOURCE = {
    "type": "OTEL",
    "service_names": ["checkout-agent"],
    "vendor": None,
    "address": None,
    "observations": {},
}
PII_CONFIG = {
    "disabled_pii_entities": ["EMAIL_ADDRESS"],
    "confidence_threshold": 0.5,
    "allow_list": ["arthur.ai"],
}


def _rule(rule_type: str, config: dict[str, object] | None) -> dict[str, object]:
    return {
        "id": f"rule-{rule_type}",
        "name": rule_type,
        "type": rule_type,
        "apply_to_prompt": True,
        "apply_to_response": False,
        "scope": "task",
        "created_at": 0,
        "updated_at": 0,
        "config": config,
    }


def _enriched_task(
    task_id: str,
    rules: list[dict[str, object]] | None = None,
    is_autocreated: bool = True,
    creation_source: dict[str, object] | None = OTEL_SOURCE,
) -> EnrichedTaskResponse:
    """A task as GenAI Engine's enriched-tasks route returns it, through genai_client."""
    return EnrichedTaskResponse.from_dict(
        {
            "id": task_id,
            "name": task_id,
            "created_at": "2026-09-25T00:00:00Z",
            "updated_at": "2026-09-25T00:00:00Z",
            "is_autocreated": is_autocreated,
            "creation_source": creation_source,
            "rules": rules or [],
        }
    )


def _published_agents(tasks: list[EnrichedTaskResponse]) -> list[dict[str, object]]:
    """The agents the sweep PUTs, as the request body carries them."""
    agents_client = MagicMock()
    agents_client.put_agents.return_value.agents = []
    DiscoverAgentsExecutor(
        agents_client=agents_client,
        logger=logging.getLogger("test-agents-sync"),
        genai_engine_url="http://genai",
        genai_engine_api_key="key",
    )._publish_to_agents_api(WORKSPACE_ID, DATA_PLANE_ID, tasks)
    if not agents_client.put_agents.called:
        return []
    body = agents_client.put_agents.call_args.kwargs["put_agents"].to_dict()
    return list(body["agents"])


def test_the_agents_sync_sends_each_rule_config_as_its_rule_type() -> None:
    """Both generated clients decode a PII config as ToxicityConfig, which serializes
    it back with a `threshold` no platform config type accepts -- and one such rule
    got the whole PUT refused, so no agent reached the Platform."""
    [agent] = _published_agents(
        [
            _enriched_task(
                "t1",
                rules=[
                    _rule("PIIDataRule", PII_CONFIG),
                    _rule("ToxicityRule", {"threshold": 0.7}),
                    _rule("RegexRule", {"regex_patterns": ["\\d{3}-\\d{4}"]}),
                    _rule("PromptInjectionRule", None),
                ],
            )
        ]
    )

    configs = {rule["type"]: rule.get("config") for rule in agent["rules"]}
    assert configs == {
        "PIIDataRule": PII_CONFIG,
        "ToxicityRule": {"threshold": 0.7},
        "RegexRule": {"regex_patterns": ["\\d{3}-\\d{4}"]},
        "PromptInjectionRule": None,
    }


def test_a_task_without_a_creation_source_is_sent_as_manual_only_if_made_by_hand() -> (
    None
):
    """The Agents API refuses an agent that names no sensor (D-03), and one refused
    agent fails the whole PUT, so an auto-created task nobody recorded a source for
    is left out rather than sent -- and never guessed at."""
    agents = _published_agents(
        [
            _enriched_task("hand-made", is_autocreated=False, creation_source=None),
            _enriched_task("unattributed", is_autocreated=True, creation_source=None),
            _enriched_task("discovered"),
        ]
    )

    by_task = {agent["task_id"]: agent for agent in agents}
    assert set(by_task) == {"hand-made", "discovered"}
    assert by_task["hand-made"]["creation_source"] == {"type": "MANUAL"}
    assert by_task["discovered"]["creation_source"]["type"] == "OTEL"  # type: ignore[index]


def test_job_without_a_source_config_runs_the_gcp_sweep() -> None:
    executor = _executor()
    executor._execute_gcp_sweep = MagicMock()  # type: ignore[method-assign]

    executor.execute(
        _job(),
        DiscoverAgentsJobSpec(
            workspace_id=WORKSPACE_ID,
            data_plane_id=DATA_PLANE_ID,
        ),
    )

    executor._execute_gcp_sweep.assert_called_once()


def _chained_fetches(jobs_client: MagicMock) -> list[tuple[str, PostJobBatch]]:
    return [
        (c.kwargs["project_id"], c.kwargs["post_job_batch"])
        for c in jobs_client.post_submit_jobs_batch.call_args_list
    ]


def test_a_scan_chains_one_fetch_for_its_source() -> None:
    """D-10: every scan completion chains a fetch for that same source, under the
    scan's own project, so what it found reaches the Platform."""
    jobs_client = MagicMock()
    before = datetime.now(timezone.utc)

    _executor(FakeScanner([[_record("a")]]), jobs_client=jobs_client).execute(
        _job(),
        _spec(_config()),
    )

    [(project_id, batch)] = _chained_fetches(jobs_client)
    assert project_id == PROJECT_ID
    [post_job] = batch.jobs
    assert post_job.kind == PostJobKind.FETCH_DISCOVERED_AGENTS
    spec = post_job.job_spec.actual_instance
    assert isinstance(spec, FetchDiscoveredAgentsJobSpec)
    assert str(spec.workspace_id) == WORKSPACE_ID
    assert str(spec.data_plane_id) == DATA_PLANE_ID
    assert str(spec.discovery_source_id) == SOURCE_ID
    # The window opens before the scan did, by the skew allowance: a report stamped
    # by GenAI Engine's clock must not land before a start stamped by this one.
    assert spec.reported_since is not None
    assert spec.reported_since <= before
    assert spec.reported_since >= before - CHAINED_FETCH_SKEW - timedelta(seconds=5)
    # no nonce: a retried scan chains again, and the fetch is an idempotent upsert
    assert post_job.nonce is None


def test_a_scan_that_found_nothing_still_chains_its_fetch() -> None:
    """On all runs, not only the ones that found something."""
    jobs_client = MagicMock()

    _executor(FakeScanner([]), jobs_client=jobs_client).execute(
        _job(),
        _spec(_config()),
    )

    assert len(_chained_fetches(jobs_client)) == 1


def test_a_failed_scan_chains_a_fetch_for_what_it_published() -> None:
    """Records published before the failure are kept, and a fetch is what makes
    them visible; the job still fails with the scan's own error."""
    jobs_client = MagicMock()
    scanner = FakeScanner([[_record("a")]], raises=RuntimeError("source went away"))

    with pytest.raises(RuntimeError, match="source went away"):
        _executor(scanner, jobs_client=jobs_client).execute(_job(), _spec(_config()))

    assert len(_chained_fetches(jobs_client)) == 1


def test_a_failed_scan_that_published_nothing_chains_nothing() -> None:
    jobs_client = MagicMock()
    scanner = FakeScanner([], raises=RuntimeError("source went away"))

    with pytest.raises(RuntimeError, match="source went away"):
        _executor(scanner, jobs_client=jobs_client).execute(_job(), _spec(_config()))

    assert _chained_fetches(jobs_client) == []


def test_a_chaining_failure_does_not_mask_why_the_scan_failed() -> None:
    jobs_client = MagicMock()
    jobs_client.post_submit_jobs_batch.side_effect = RuntimeError("platform down")
    scanner = FakeScanner([[_record("a")]], raises=RuntimeError("source went away"))

    with pytest.raises(RuntimeError, match="source went away"):
        _executor(scanner, jobs_client=jobs_client).execute(_job(), _spec(_config()))


def test_a_chaining_failure_fails_an_otherwise_successful_scan() -> None:
    """As a failed alert-check submission fails a metrics job: the retry rescans,
    which is idempotent, and chains again."""
    jobs_client = MagicMock()
    jobs_client.post_submit_jobs_batch.side_effect = RuntimeError("platform down")

    with pytest.raises(RuntimeError, match="platform down"):
        _executor(FakeScanner([[_record("a")]]), jobs_client=jobs_client).execute(
            _job(),
            _spec(_config()),
        )


def test_a_scan_that_never_reached_its_source_chains_nothing() -> None:
    jobs_client = MagicMock()

    with pytest.raises(UnsupportedDiscoveryVendorError):
        _executor(
            FakeScanner([[_record("a")]]),
            vendor="some_other_vendor",
            jobs_client=jobs_client,
        ).execute(_job(), _spec(_config()))

    assert _chained_fetches(jobs_client) == []


def test_a_scan_without_a_jobs_client_fails_rather_than_dropping_its_fetch() -> None:
    executor = _executor(FakeScanner([[_record("a")]]))
    executor.jobs_client = None

    with pytest.raises(RuntimeError, match="No jobs client"):
        executor.execute(_job(), _spec(_config()))


def _capture(logger: logging.Logger) -> list[logging.LogRecord]:
    """Collect the records a logger emits, without touching global config."""
    records: list[logging.LogRecord] = []

    class _Handler(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:
            records.append(record)

    handler = _Handler()
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    return records


def _find_outcome(records: list[logging.LogRecord]) -> dict:
    """The outcome rides in the message text, since that is all the exporter ships."""
    for record in records:
        message = record.getMessage()
        if not message.startswith("{"):
            continue
        payload = json.loads(message)
        if payload.get("event") == "discovery_scan_outcome":
            return payload
    raise AssertionError("no discovery_scan_outcome was logged")
