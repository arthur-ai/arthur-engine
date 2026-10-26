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
    mock.add(responses.POST, BULK, json=ACCEPTED)

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


@pytest.mark.parametrize("index", ["AI-Inventory", "_hidden", "ai inventory", "a,b"])
def test_an_index_elasticsearch_would_refuse_stops_startup(index: str) -> None:
    with pytest.raises(ValidationError, match="must be lowercase"):
        es(index=index)


def test_a_200_refusing_documents_is_not_delivery(
    mock: responses.RequestsMock,
) -> None:
    mock.add(
        responses.POST,
        BULK,
        json={
            "errors": True,
            "items": [
                {"create": {"status": 201}},
                {
                    "create": {
                        "status": 400,
                        "error": {
                            "type": "mapper_parsing_exception",
                            "reason": "failed to parse field [agent.name]",
                        },
                    },
                },
            ],
        },
    )

    with pytest.raises(SinkDeliveryError) as e:
        ElasticsearchSink(es(), LOG).send([event(1), event(2)])

    assert "refused 1 of 2 event(s) in a bulk request, and indexed the rest" in str(
        e.value
    )
    assert "mapper_parsing_exception: failed to parse field [agent.name]" in str(
        e.value
    )
    assert e.value.status_code == 400
    # Not retried: the document it took would be indexed twice.
    assert len(mock.calls) == 1


def test_a_2xx_that_is_not_a_bulk_response_is_not_delivery(
    mock: responses.RequestsMock,
) -> None:
    mock.add(responses.POST, BULK, body="<html>signed in</html>")

    with pytest.raises(SinkDeliveryError, match="other than a bulk response"):
        ElasticsearchSink(es(), LOG).send([event(1)])


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
