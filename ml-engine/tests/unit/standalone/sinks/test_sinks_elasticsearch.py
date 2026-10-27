"""How a batch is framed, authenticated and read back for Elasticsearch's `_bulk`.

Retries and scrubbing are the HTTP base's, tested once in test_sinks_http; what is here
is what only `_bulk` does -- above all, that a 200 refusing documents is not delivery.
"""

import base64
import json
import logging
from datetime import datetime, timezone
from typing import Any, Iterator
from urllib.parse import parse_qs, urlsplit

import pytest
import responses
from pydantic import ValidationError

from standalone.sinks.common import SinkDeliveryError
from standalone.sinks.siem.elasticsearch import (
    BULK_FILTER_PATH,
    DEFAULT_INDEX,
    ElasticsearchDestination,
    ElasticsearchSink,
)

LOG = logging.getLogger("sinks-elasticsearch-test")
CLUSTER = "https://es.example.com:9243"
BULK = f"{CLUSTER}/_bulk"
API_KEY = "VnVhQ2ZHY0JDZGJrUW0tZTVhT3g6dWkybHAyYXhUTm1zeWFrdzl0dk5udw=="
PASSWORD = "es-passw0rd-value-0003"
OBSERVED_AT = datetime(2026, 10, 7, 12, 0, tzinfo=timezone.utc)
ACCEPTED = {"errors": False, "items": [{"create": {"status": 201}}]}


def es(**overrides: Any) -> ElasticsearchDestination:
    fields = {"type": "elasticsearch", "url": CLUSTER, "api_key": API_KEY}
    return ElasticsearchDestination.model_validate({**fields, **overrides})


def event(n: int) -> dict[str, Any]:
    return {"n": n, "observed_at": OBSERVED_AT.isoformat()}


def lines(call: Any) -> list[dict[str, Any]]:
    return [json.loads(line) for line in call.request.body.decode().splitlines()]


def query(call: Any) -> dict[str, list[str]]:
    return parse_qs(urlsplit(call.request.url).query)


@pytest.fixture
def mock() -> Iterator[responses.RequestsMock]:
    with responses.RequestsMock() as rsps:
        yield rsps


def test_each_event_is_a_create_and_a_document(mock: responses.RequestsMock) -> None:
    mock.add(responses.POST, BULK, json=bulk(201, 201))

    ElasticsearchSink(es(index="ai-inventory"), LOG).send([event(1), event(2)])

    (call,) = mock.calls
    assert call.request.headers["Authorization"] == f"ApiKey {API_KEY}"
    assert call.request.headers["Content-Type"] == "application/x-ndjson"
    assert call.request.body.decode().endswith("\n")
    framed = lines(call)
    assert framed[0::2] == [{"create": {"_index": "ai-inventory"}}] * 2
    assert [doc["n"] for doc in framed[1::2]] == [1, 2]
    assert framed[1]["@timestamp"] == OBSERVED_AT.isoformat()
    assert framed[1]["observed_at"] == OBSERVED_AT.isoformat()
    assert query(call)["filter_path"] == [BULK_FILTER_PATH]


def test_the_default_index_is_a_logs_data_stream(mock: responses.RequestsMock) -> None:
    mock.add(responses.POST, BULK, json=ACCEPTED)

    ElasticsearchSink(es(), LOG).send([event(1)])

    assert lines(mock.calls[0])[0] == {"create": {"_index": DEFAULT_INDEX}}


@pytest.mark.parametrize(
    "url",
    [CLUSTER, f"{CLUSTER}/", BULK, f"{BULK}/"],
)
def test_the_url_is_the_clusters_or_its_bulk_endpoint(
    mock: responses.RequestsMock,
    url: str,
) -> None:
    mock.add(responses.POST, BULK, json=ACCEPTED)

    ElasticsearchSink(es(url=url), LOG).send([event(1)])

    assert urlsplit(mock.calls[0].request.url).path == "/_bulk"


def test_a_cluster_behind_a_gateway_keeps_its_path(
    mock: responses.RequestsMock,
) -> None:
    mock.add(responses.POST, "https://gw.example.com/es-prod/_bulk", json=ACCEPTED)

    ElasticsearchSink(es(url="https://gw.example.com/es-prod"), LOG).send([event(1)])

    assert len(mock.calls) == 1


def test_a_pipeline_is_named_in_the_query(mock: responses.RequestsMock) -> None:
    mock.add(responses.POST, BULK, json=ACCEPTED)

    ElasticsearchSink(es(pipeline="arthur-to-ecs"), LOG).send([event(1)])

    assert query(mock.calls[0])["pipeline"] == ["arthur-to-ecs"]


def test_an_id_and_key_pair_is_encoded(mock: responses.RequestsMock) -> None:
    mock.add(responses.POST, BULK, json=ACCEPTED)

    ElasticsearchSink(es(api_key="key-id:key-secret"), LOG).send([event(1)])

    encoded = base64.b64encode(b"key-id:key-secret").decode()
    assert mock.calls[0].request.headers["Authorization"] == f"ApiKey {encoded}"


def test_basic_auth(mock: responses.RequestsMock) -> None:
    mock.add(responses.POST, BULK, json=ACCEPTED)
    destination = es(api_key=None, username="arthur", password=PASSWORD)

    ElasticsearchSink(destination, LOG).send([event(1)])

    encoded = base64.b64encode(f"arthur:{PASSWORD}".encode()).decode()
    assert mock.calls[0].request.headers["Authorization"] == f"Basic {encoded}"


@pytest.mark.parametrize(
    ("credentials", "message"),
    [
        ({"api_key": None}, "set api_key, or both username and password"),
        ({"api_key": None, "username": "arthur"}, "both username and password"),
        ({"api_key": None, "password": PASSWORD}, "both username and password"),
        ({"username": "arthur", "password": PASSWORD}, "not both"),
    ],
)
def test_exactly_one_credential(credentials: dict[str, Any], message: str) -> None:
    with pytest.raises(ValidationError, match=message):
        es(**credentials)


@pytest.mark.parametrize(
    "index",
    ["AI-Inventory", "_hidden", "ai inventory", "a,b", ".", ".."],
)
def test_an_index_elasticsearch_would_refuse_stops_startup(index: str) -> None:
    with pytest.raises(ValidationError, match="must be lowercase"):
        es(index=index)


def bulk(*statuses: int) -> dict[str, Any]:
    """A filtered `_bulk` answer, one result per status, an error on each non-2xx."""
    errors = {
        400: ("document_parsing_exception", "failed to parse field [agent.name]"),
        429: ("es_rejected_execution_exception", "rejected execution of write"),
        503: ("unavailable_shards_exception", "primary shard is not active"),
    }
    items = []
    for status in statuses:
        result: dict[str, Any] = {"status": status}
        if status in errors:
            kind, reason = errors[status]
            result["error"] = {"type": kind, "reason": reason}
        items.append({"create": result})
    return {"errors": any(s >= 300 for s in statuses), "items": items}


def test_a_document_refused_for_what_it_holds_is_returned_not_raised(
    mock: responses.RequestsMock,
) -> None:
    """One bad record does not stop the batches after it, nor is it sent again: a
    re-send is refused the same way."""
    mock.add(responses.POST, BULK, json=bulk(201, 400))
    mock.add(responses.POST, BULK, json=bulk(201))

    refused = ElasticsearchSink(es(batch_size=2), LOG).send(
        [event(1), event(2), event(3)],
    )

    assert [(r.position, r.reason) for r in refused] == [
        (1, "document_parsing_exception"),
    ]
    assert refused[0].detail == "failed to parse field [agent.name]"
    assert len(mock.calls) == 2


@pytest.mark.parametrize("status", [429, 503])
def test_a_document_refused_for_load_is_sent_again_alone(
    mock: responses.RequestsMock,
    status: int,
) -> None:
    mock.add(responses.POST, BULK, json=bulk(201, status, 201))
    mock.add(responses.POST, BULK, json=bulk(201))
    sleeps: list[float] = []

    refused = ElasticsearchSink(es(), LOG, sleep=sleeps.append).send(
        [event(1), event(2), event(3)],
    )

    assert refused == []
    assert sleeps == [1.0]
    # Only the document it shed: the two it took would otherwise be indexed twice.
    assert [doc["n"] for doc in lines(mock.calls[1])[1::2]] == [2]


def test_positions_survive_a_retry(mock: responses.RequestsMock) -> None:
    """A document refused on the re-send is reported where it was in the batch, not
    where it was in the smaller request."""
    mock.add(responses.POST, BULK, json=bulk(201, 429, 429))
    mock.add(responses.POST, BULK, json=bulk(201, 400))

    refused = ElasticsearchSink(es(), LOG, sleep=lambda _: None).send(
        [event(1), event(2), event(3)],
    )

    assert [r.position for r in refused] == [2]


def test_a_cluster_still_shedding_load_fails_the_batch(
    mock: responses.RequestsMock,
) -> None:
    for _ in range(3):
        mock.add(responses.POST, BULK, json=bulk(429))

    with pytest.raises(SinkDeliveryError) as e:
        ElasticsearchSink(es(), LOG, sleep=lambda _: None).send([event(1)])

    assert "still refused 1 of 1 event(s) after 3 attempt(s)" in str(e.value)
    assert "es_rejected_execution_exception" in str(e.value)
    assert len(mock.calls) == 3


@pytest.mark.parametrize(
    "answer",
    [
        {"errors": False},
        {"errors": False, "items": "nope"},
        {"errors": False, "items": [{"create": {"status": 201}}] * 2},
        {"errors": False, "items": [{"create": {}}]},
        {"errors": True, "items": [["create", 400]]},
    ],
)
def test_a_2xx_that_is_not_a_bulk_response_for_the_batch_is_not_delivery(
    mock: responses.RequestsMock,
    answer: dict[str, Any],
) -> None:
    """Including `errors: false` with no results for the documents sent: nothing says
    they were indexed, and results cannot be matched to the wrong documents."""
    mock.add(responses.POST, BULK, json=answer)

    with pytest.raises(SinkDeliveryError, match="other than a bulk response"):
        ElasticsearchSink(es(), LOG).send([event(1)])


def test_a_2xx_that_is_not_json_is_not_delivery(mock: responses.RequestsMock) -> None:
    mock.add(responses.POST, BULK, body="<html>signed in</html>")

    with pytest.raises(SinkDeliveryError, match="other than a bulk response"):
        ElasticsearchSink(es(), LOG).send([event(1)])


def test_a_secret_in_the_configured_query_never_reaches_an_error() -> None:
    """Appended to rather than re-encoded, so the query the base scrubs is still a
    substring of the URL a connection error quotes -- re-encoded, `/` and `=` became
    `%2F` and `%3D` and the key came through. Nothing is registered, so `responses`
    refuses the request with a ConnectionError quoting the URL, as urllib3 does."""
    sink = ElasticsearchSink(
        es(url=f"{CLUSTER}/es?code=AbC/dEf+GhI=="),
        LOG,
        sleep=lambda _: None,
    )

    with responses.RequestsMock(), pytest.raises(SinkDeliveryError) as e:
        sink.send([event(1)])

    assert "Could not reach Elasticsearch" in str(e.value)
    assert "AbC/dEf" not in str(e.value) and "AbC%2FdEf" not in str(e.value)


def test_a_refusal_never_echoes_the_credentials(mock: responses.RequestsMock) -> None:
    mock.add(responses.POST, BULK, status=401, body=f"bad credentials {PASSWORD}")
    destination = es(api_key=None, username="arthur", password=PASSWORD)

    with pytest.raises(SinkDeliveryError) as e:
        ElasticsearchSink(destination, LOG).send([event(1)])

    assert PASSWORD not in str(e.value)
    assert "Elasticsearch at es.example.com:9243" in str(e.value)


def test_the_credentials_are_secrets() -> None:
    encoded = base64.b64encode(b"key-id:key-secret").decode()
    assert {"key-id:key-secret", encoded} <= set(
        ElasticsearchSink(es(api_key="key-id:key-secret"), LOG).secrets(),
    )
    assert (
        PASSWORD
        in ElasticsearchSink(
            es(api_key=None, username="arthur", password=PASSWORD),
            LOG,
        ).secrets()
    )
    assert API_KEY not in repr(es())


def test_the_destination_builds_its_sink() -> None:
    assert isinstance(es().build_sink(LOG), ElasticsearchSink)
