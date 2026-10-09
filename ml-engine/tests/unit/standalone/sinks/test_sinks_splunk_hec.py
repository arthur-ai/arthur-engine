"""How a batch is framed and authenticated for Splunk HEC.

Retries and scrubbing are the HTTP base's, tested once in test_sinks_http; what is here
is what only HEC does.
"""

import json
import logging
from datetime import datetime, timezone
from typing import Any, Iterator

import pytest
import responses

from standalone.sinks.common import SinkDeliveryError
from standalone.sinks.siem.splunk_hec import SplunkHecDestination, SplunkHecSink

LOG = logging.getLogger("sinks-hec-test")
URL = "https://splunk.example.com:8088/services/collector/event"
TOKEN = "hec-t0ken-value-0002"
OBSERVED_AT = datetime(2026, 10, 7, 12, 0, tzinfo=timezone.utc)


def hec(**overrides: Any) -> SplunkHecDestination:
    return SplunkHecDestination.model_validate(
        {"type": "splunk_hec", "url": URL, "token": TOKEN, **overrides},
    )


def event(n: int) -> dict[str, Any]:
    return {"n": n, "observed_at": OBSERVED_AT.isoformat()}


def lines(call: Any) -> list[dict[str, Any]]:
    return [json.loads(line) for line in call.request.body.decode().splitlines()]


@pytest.fixture
def mock() -> Iterator[responses.RequestsMock]:
    with responses.RequestsMock() as rsps:
        yield rsps


def test_each_event_is_framed_with_its_metadata(mock: responses.RequestsMock) -> None:
    mock.add(responses.POST, URL, json={"text": "Success", "code": 0})

    SplunkHecSink(hec(index="ai_inventory"), LOG).send([event(1), event(2)])

    (call,) = mock.calls
    assert call.request.headers["Authorization"] == f"Splunk {TOKEN}"
    framed = lines(call)
    assert [line["event"]["n"] for line in framed] == [1, 2]
    assert framed[0]["time"] == OBSERVED_AT.timestamp()
    assert framed[0]["index"] == "ai_inventory"
    assert framed[0]["source"] == "arthur-ml-engine"
    assert framed[0]["sourcetype"] == "arthur:discovered_agent"


def test_the_index_is_left_to_the_token_when_unset(
    mock: responses.RequestsMock,
) -> None:
    mock.add(responses.POST, URL)

    SplunkHecSink(hec(), LOG).send([event(1)])

    assert "index" not in lines(mock.calls[0])[0]


def test_a_refusal_never_echoes_the_token(mock: responses.RequestsMock) -> None:
    mock.add(responses.POST, URL, status=400, body=f"bad request for {TOKEN}")

    with pytest.raises(SinkDeliveryError) as e:
        SplunkHecSink(hec(), LOG).send([event(1)])

    assert TOKEN not in str(e.value)
    assert "Splunk HEC at splunk.example.com:8088" in str(e.value)


def test_the_token_is_a_secret() -> None:
    assert TOKEN in SplunkHecSink(hec(), LOG).secrets()
    assert TOKEN not in repr(hec())


def test_the_destination_builds_its_sink() -> None:
    assert isinstance(hec().build_sink(LOG), SplunkHecSink)
