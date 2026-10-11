"""One standalone scan, against a fake connector and a recording sink.

What matters most is that every exit reports an outcome and none of them raises: the
engine has no job state to fail, so a scan that throws would end its thread silently
and the destination would never hear that the source is broken.
"""

import dataclasses
import logging
from datetime import datetime, timezone
from typing import Any, Callable, Iterator, Optional, Sequence

import pytest
from arthur_client.api_bindings import DiscoverySourceConfigSpec
from arthur_common.models.agent_discovery_schemas import DiscoveryOutputRecord

from job_executors.discovery_scan import DiscoveryErrorCode
from log_redaction import SecretRedactingFilter
from standalone.discovery_config import ResolvedScan
from standalone.scan import run_scan, scan_logger
from standalone.sinks.common import (
    DISCOVERED_AGENT_EVENT,
    SCAN_OUTCOME_EVENT,
    SinkDeliveryError,
)

VENDOR = "fake_vendor"
CLIENT_SECRET = "s0urce-s3cret-0005"
SINK_SECRET = "s1nk-s3cret-0006"


def resolved(vendor: str = VENDOR) -> ResolvedScan:
    return ResolvedScan(
        source_name="corp-macs",
        discovery_source_config_id="cfg-id",
        config=DiscoverySourceConfigSpec(
            discovery_source_id="src-id",
            name="all-macs",
            vendor=vendor,
            query="",
            query_language="none",
            lookback_window_seconds=86400,
        ),
        lookback_hours=24,
        source_fields={"base_url": "https://acme.example.com"},
        credentials={"client_secret": CLIENT_SECRET},
    )


def record(external_id: str) -> DiscoveryOutputRecord:
    return DiscoveryOutputRecord(
        external_id=external_id,
        name=f"agent-{external_id}",
        last_seen=datetime(2026, 10, 7, 11, 0, tzinfo=timezone.utc),
    )


class RecordingSink:
    """Implements `Sink`; fails every send after the first `fail_after` if asked."""

    def __init__(self, fail_after: Optional[int] = None) -> None:
        self.sent: list[dict[str, Any]] = []
        self.closed = False
        self._fail_after = fail_after
        self._calls = 0

    def send(self, events: Sequence[dict[str, Any]]) -> None:
        self._calls += 1
        if self._fail_after is not None and self._calls > self._fail_after:
            raise SinkDeliveryError("destination unavailable")
        self.sent.extend(events)

    def secrets(self) -> tuple[str, ...]:
        return (SINK_SECRET,)

    def close(self) -> None:
        self.closed = True

    def of_type(self, event_type: str) -> list[dict[str, Any]]:
        return [e for e in self.sent if e["event_type"] == event_type]


class FakeConnector:
    """Yields its batches; raises after them if given an error."""

    def __init__(
        self,
        batches: list[list[DiscoveryOutputRecord]],
        error: Optional[Exception] = None,
        log: Optional[str] = None,
    ) -> None:
        self.batches = batches
        self.error = error
        self.log = log

    def scan(
        self,
        config: Any,
        lookback_hours: int,
        credentials: Any,
        source_fields: Any,
        logger: logging.Logger,
    ) -> Iterator[list[DiscoveryOutputRecord]]:
        if self.log:
            logger.info(self.log)
        yield from self.batches
        if self.error:
            raise self.error


class StoppableConnector(FakeConnector):
    """Implements `AcceptsStopCheck`: asks between batches, as Jamf does between pages."""

    def stop_when(self, should_stop: Callable[[], bool]) -> None:
        self.should_stop = should_stop

    def scan(self, *args: Any) -> Iterator[list[DiscoveryOutputRecord]]:
        for batch in self.batches:
            if self.should_stop():
                return
            yield batch


@pytest.fixture
def connectors(monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    registry: dict[str, Any] = {}
    monkeypatch.setattr("standalone.scan.source_connectors", lambda: registry)
    return registry


def scan(
    sink: RecordingSink,
    target: Optional[ResolvedScan] = None,
    emit: bool = True,
    should_stop: Callable[[], bool] = lambda: False,
) -> Any:
    target = target or resolved()
    return run_scan(
        target,
        sink,
        emit,
        scan_logger(target, sink),
        should_stop,
    )


@pytest.mark.parametrize(
    ("lookback_hours", "expected"),
    [(24, "over the last 24h"), (0, "with no lookback limit")],
)
def test_the_start_line_describes_the_window(
    connectors: dict[str, Any],
    caplog: pytest.LogCaptureFixture,
    lookback_hours: int,
    expected: str,
) -> None:
    connectors[VENDOR] = lambda: FakeConnector([])
    target = dataclasses.replace(resolved(), lookback_hours=lookback_hours)

    with caplog.at_level(logging.INFO):
        scan(RecordingSink(), target=target)

    assert f"(fake_vendor) {expected}" in caplog.text


def test_a_scan_sends_its_records_then_its_outcome(connectors: dict[str, Any]) -> None:
    connectors[VENDOR] = lambda: FakeConnector(
        [[record("a"), record("b")], [record("c")]],
    )
    sink = RecordingSink()

    outcome = scan(sink)

    assert outcome.error is None and outcome.records_published == 3
    agents = sink.of_type(DISCOVERED_AGENT_EVENT)
    assert [e["agent"]["external_id"] for e in agents] == ["a", "b", "c"]
    assert agents[0]["source"]["name"] == "corp-macs"
    assert sink.sent[-1]["event_type"] == SCAN_OUTCOME_EVENT
    assert sink.sent[-1]["outcome"]["succeeded"] is True


def test_a_scan_leaves_the_shared_sink_open(connectors: dict[str, Any]) -> None:
    """The engine's sink outlives every scan; closing it is the engine's job."""
    connectors[VENDOR] = lambda: FakeConnector([[record("a")]], error=RuntimeError())
    sink = RecordingSink()

    scan(sink)

    assert not sink.closed


def test_outcome_events_can_be_switched_off(connectors: dict[str, Any]) -> None:
    connectors[VENDOR] = lambda: FakeConnector([[record("a")]])
    sink = RecordingSink()

    scan(sink, emit=False)

    assert sink.of_type(SCAN_OUTCOME_EVENT) == []
    assert len(sink.of_type(DISCOVERED_AGENT_EVENT)) == 1


def test_a_failing_source_is_reported_not_raised(connectors: dict[str, Any]) -> None:
    error = RuntimeError("vendor exploded")
    connectors[VENDOR] = lambda: FakeConnector([[record("a")]], error=error)
    sink = RecordingSink()

    outcome = scan(sink)

    assert outcome.error_code == DiscoveryErrorCode.PROVIDER_ERROR
    assert outcome.records_published == 1
    (reported,) = sink.of_type(SCAN_OUTCOME_EVENT)
    assert reported["outcome"]["succeeded"] is False
    assert "vendor exploded" in reported["outcome"]["error"]


def test_a_vendor_with_no_connector_is_reported(connectors: dict[str, Any]) -> None:
    sink = RecordingSink()

    outcome = scan(sink, target=resolved(vendor="not_registered"))

    assert outcome.error_code == DiscoveryErrorCode.UNSUPPORTED_VENDOR
    assert sink.of_type(SCAN_OUTCOME_EVENT)[0]["outcome"]["error_code"] == (
        "unsupported_vendor"
    )


def test_a_connector_that_cannot_be_built_is_reported(
    connectors: dict[str, Any],
) -> None:
    def broken() -> Any:
        raise RuntimeError("bad constructor")

    connectors[VENDOR] = broken
    sink = RecordingSink()

    outcome = scan(sink)

    assert outcome.error_code == DiscoveryErrorCode.INTERNAL_ERROR
    assert len(sink.of_type(SCAN_OUTCOME_EVENT)) == 1


def test_an_undeliverable_outcome_is_logged_not_raised(
    connectors: dict[str, Any],
    caplog: pytest.LogCaptureFixture,
) -> None:
    connectors[VENDOR] = lambda: FakeConnector([[record("a")]])
    # The records go out; the outcome, sent after them, does not.
    sink = RecordingSink(fail_after=1)

    with caplog.at_level(logging.ERROR):
        outcome = scan(sink)

    assert outcome.error is None
    assert "Could not send this scan's outcome" in caplog.text


def test_shutdown_cancels_a_stoppable_scan(connectors: dict[str, Any]) -> None:
    connectors[VENDOR] = lambda: StoppableConnector([[record("a")], [record("b")]])
    sink = RecordingSink()

    outcome = scan(sink, should_stop=lambda: len(sink.sent) > 0)

    assert outcome.records_published == 1
    assert outcome.error_code == DiscoveryErrorCode.CANCELLED
    assert sink.sent[-1]["outcome"]["error_code"] == "cancelled"


def test_credentials_and_sink_secrets_are_scrubbed_from_the_log(
    connectors: dict[str, Any],
    caplog: pytest.LogCaptureFixture,
) -> None:
    connectors[VENDOR] = lambda: FakeConnector(
        [[record("a")]],
        log=f"using {CLIENT_SECRET} to send to {SINK_SECRET}",
    )

    with caplog.at_level(logging.INFO):
        scan(RecordingSink())

    assert "using [redacted] to send to [redacted]" in caplog.text
    assert CLIENT_SECRET not in caplog.text and SINK_SECRET not in caplog.text


def test_each_source_and_config_keeps_one_logger_with_one_filter() -> None:
    sink = RecordingSink()

    first, second = scan_logger(resolved(), sink), scan_logger(resolved(), sink)

    assert first is second
    assert sum(isinstance(f, SecretRedactingFilter) for f in first.filters) == 1
