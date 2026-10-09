"""The events every target is handed, and the record sink that sends them, through the
shared scan loop."""

import logging
from datetime import datetime, timezone
from typing import Any, Iterator, Optional, Sequence, get_args

import pytest
from arthur_client.api_bindings import DiscoverySourceConfigSpec
from arthur_common.models.agent_discovery_schemas import DiscoveryOutputRecord

from job_executors.discovery_scan import (
    DiscoveryErrorCode,
    DiscoveryScanOutcome,
    run_source_scan,
)
from standalone.sinks import Destination
from standalone.sinks.common import (
    DISCOVERED_AGENT_EVENT,
    EVENT_SCHEMA_VERSION,
    SCAN_OUTCOME_EVENT,
    SinkDeliveryError,
    scan_outcome_event,
)
from standalone.sinks.record_sink import StandaloneRecordSink

LOG = logging.getLogger("sinks-record-sink-test")
TOKEN = "hec-t0ken-value-0002"
OBSERVED_AT = datetime(2026, 10, 7, 12, 0, tzinfo=timezone.utc)
SOURCE_ID = "11111111-1111-1111-1111-111111111111"


def config() -> DiscoverySourceConfigSpec:
    return DiscoverySourceConfigSpec(
        discovery_source_id=SOURCE_ID,
        name="all-macs",
        vendor="jamf_pro",
        query="",
        query_language="none",
        lookback_window_seconds=86400,
    )


def record(external_id: str) -> DiscoveryOutputRecord:
    return DiscoveryOutputRecord(
        external_id=external_id,
        name=f"agent-{external_id}",
        last_seen=datetime(2026, 10, 7, 11, 0, tzinfo=timezone.utc),
    )


def outcome(**overrides: Any) -> DiscoveryScanOutcome:
    fields: dict[str, Any] = {
        "discovery_source_config_id": "cfg",
        "discovery_source_config_name": "all-macs",
        "discovery_source_id": SOURCE_ID,
        "vendor": "jamf_pro",
        "job_id": "local",
        "scan_id": None,
        "lookback_hours": 24,
    }
    return DiscoveryScanOutcome(**{**fields, **overrides})


class RecordingSink:
    """Implements `Sink`, failing the send at the given index if asked."""

    def __init__(self, fail_on_call: Optional[int] = None) -> None:
        self.sent: list[list[dict[str, Any]]] = []
        self._fail_on_call = fail_on_call

    def send(self, events: Sequence[dict[str, Any]]) -> None:
        if self._fail_on_call == len(self.sent):
            raise SinkDeliveryError(f"refused (Splunk {TOKEN})")
        self.sent.append(list(events))

    def secrets(self) -> tuple[str, ...]:
        return (TOKEN,)

    def close(self) -> None:
        pass


def test_every_target_builds_its_own_sink() -> None:
    """Each entry in the list of targets owns how its sink is made."""
    union = get_args(Destination)[0]
    for target in get_args(union):
        assert "build_sink" in vars(target), target.__name__


def test_the_record_sink_sends_one_event_per_record() -> None:
    sink = RecordingSink()
    record_sink = StandaloneRecordSink(sink, "corp-macs", clock=lambda: OBSERVED_AT)

    result = record_sink.publish("", "", config(), [record("a"), record("b")])

    assert result.accepted == 2 and not result.failed
    (events,) = sink.sent
    assert [e["agent"]["external_id"] for e in events] == ["a", "b"]
    assert events[0]["event_type"] == DISCOVERED_AGENT_EVENT
    assert events[0]["schema_version"] == EVENT_SCHEMA_VERSION
    assert events[0]["observed_at"] == OBSERVED_AT.isoformat()
    assert events[0]["source"] == {
        "id": SOURCE_ID,
        "name": "corp-macs",
        "vendor": "jamf_pro",
        "config_name": "all-macs",
    }


def test_unset_record_columns_are_left_out_rather_than_sent_as_null() -> None:
    sink = RecordingSink()

    StandaloneRecordSink(sink, "s").publish("", "", config(), [record("a")])

    agent = sink.sent[0][0]["agent"]
    assert "tools" not in agent and "llm_models" not in agent


def test_an_empty_batch_sends_nothing() -> None:
    sink = RecordingSink()

    result = StandaloneRecordSink(sink, "s").publish("", "", config(), [])

    assert result.accepted == 0 and sink.sent == []


def test_the_outcome_event_carries_the_logged_payload() -> None:
    finished = outcome(finished_at=OBSERVED_AT, records_published=3)

    emitted = scan_outcome_event(finished, "corp-macs")

    assert emitted["event_type"] == SCAN_OUTCOME_EVENT
    assert emitted["observed_at"] == OBSERVED_AT.isoformat()
    assert emitted["source"]["name"] == "corp-macs"
    assert emitted["outcome"] == finished.to_log_payload()


class TwoBatchConnector:
    def scan(self, *args: Any) -> Iterator[list[DiscoveryOutputRecord]]:
        yield [record("a"), record("b")]
        yield [record("c")]


def test_a_failed_delivery_fails_the_scan_as_a_publication_failure() -> None:
    """End to end through the shared scan loop: the first batch counts, the run fails
    with the publication code, and the destination's token is not in its error."""
    scanned = outcome()

    with pytest.raises(SinkDeliveryError):
        run_source_scan(
            config=config(),
            lookback_hours=24,
            workspace_id="",
            data_plane_id="",
            outcome=scanned,
            connector=TwoBatchConnector(),
            sink=StandaloneRecordSink(RecordingSink(fail_on_call=1), "corp-macs"),
            logger=LOG,
            credentials={},
            source_fields={},
        )

    assert scanned.records_published == 2
    assert scanned.error_code == DiscoveryErrorCode.PUBLICATION_FAILED
    assert scanned.error is not None and TOKEN not in scanned.error
