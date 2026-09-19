import json
import logging
from datetime import datetime, timezone
from typing import Iterator, Sequence
from unittest.mock import MagicMock

import pytest
from arthur_client.api_bindings import (
    DiscoverAgentsJobSpec,
    DiscoverySourceConfigSpec,
    Job,
)
from arthur_common.models.agent_discovery_schemas import DiscoveryOutputRecord

from job_executors.discover_agents_executor import DiscoverAgentsExecutor
from job_executors.discovery_scan import UnsupportedDiscoveryVendorError

WORKSPACE_ID = "11111111-1111-1111-1111-111111111111"
DATA_PLANE_ID = "22222222-2222-2222-2222-222222222222"
CONFIG_ID = "33333333-3333-3333-3333-333333333333"
SOURCE_ID = "44444444-4444-4444-4444-444444444444"
SIBLING_CONFIG_ID = "55555555-5555-5555-5555-555555555555"
SCAN_ID = "66666666-6666-6666-6666-666666666666"


def _config(
    name: str = "splunk prod",
    vendor: str = "splunk_enterprise",
    lookback_window_seconds: int = 3600,
) -> DiscoverySourceConfigSpec:
    return DiscoverySourceConfigSpec(
        discovery_source_id=SOURCE_ID,
        name=name,
        vendor=vendor,
        query="search index=agents",
        query_language="spl",
        lookback_window_seconds=lookback_window_seconds,
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
    ) -> int:
        self.batches.append([r.external_id for r in records])
        self.configs.append(config.name)
        return len(records)


class FakeScanner:
    """Yields the given batches, then optionally throws."""

    def __init__(
        self,
        batches: list[list[DiscoveryOutputRecord]],
        raises: Exception | None = None,
    ) -> None:
        self.batches = batches
        self.raises = raises
        self.calls: list[tuple[str, int]] = []

    def scan(
        self,
        config: DiscoverySourceConfigSpec,
        lookback_hours: int,
    ) -> Iterator[Sequence[DiscoveryOutputRecord]]:
        self.calls.append((config.name, lookback_hours))
        for batch in self.batches:
            yield batch
        if self.raises is not None:
            raise self.raises


def _executor(
    scanner: FakeScanner | None = None,
    sink: RecordingSink | None = None,
    vendor: str = "splunk_enterprise",
    logger: logging.Logger | None = None,
) -> DiscoverAgentsExecutor:
    return DiscoverAgentsExecutor(
        agents_client=MagicMock(),
        logger=logger or logging.getLogger("test-discovery"),
        genai_engine_url="http://genai",
        genai_engine_api_key="key",
        record_sink=sink or RecordingSink(),
        scanners={vendor: scanner} if scanner is not None else {},
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


def test_job_naming_a_config_it_does_not_carry_is_rejected() -> None:
    scanner = FakeScanner([[_record("a")]])

    with pytest.raises(ValueError, match="no materialized config"):
        _executor(scanner).execute(_job(), _spec(None))


def test_job_carrying_a_config_with_no_id_is_rejected() -> None:
    scanner = FakeScanner([[_record("a")]])

    with pytest.raises(ValueError, match="no discovery_source_config_id"):
        _executor(scanner).execute(_job(), _spec(_config(), config_id=None))


def test_lookback_falls_back_to_the_configs_window_rounded_up() -> None:
    scanner = FakeScanner([])

    _executor(scanner).execute(
        _job(),
        _spec(_config(lookback_window_seconds=5400), lookback_hours=None),
    )

    assert scanner.calls == [("splunk prod", 2)]


def test_empty_batches_are_not_published() -> None:
    scanner = FakeScanner([[], [_record("a")], []])
    sink = RecordingSink()

    _executor(scanner, sink).execute(_job(), _spec(_config()))

    assert sink.batches == [["a"]]


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
