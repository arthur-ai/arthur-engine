"""How a batch is framed and authenticated for a webhook.

Retries and scrubbing are the HTTP base's, tested once in test_sinks_http; what is here
is what only the webhook does.
"""

import json
import logging
from typing import Any, Iterator

import pytest
import responses

from standalone.sinks.common import SinkDeliveryError
from standalone.sinks.webhook import WebhookDestination, WebhookSink

LOG = logging.getLogger("sinks-webhook-test")
SECRET_PATH = "/hooks/T0KEN1234abcd"
URL = f"https://hooks.example.com{SECRET_PATH}"
AUTH = "Bearer hook-s3cret-0003"


def webhook(**overrides: Any) -> WebhookDestination:
    return WebhookDestination.model_validate(
        {
            "type": "webhook",
            "url": URL,
            "headers": {"Authorization": AUTH},
            **overrides,
        },
    )


@pytest.fixture
def mock() -> Iterator[responses.RequestsMock]:
    with responses.RequestsMock() as rsps:
        yield rsps


def test_a_batch_is_a_json_array_sent_with_its_headers(
    mock: responses.RequestsMock,
) -> None:
    mock.add(responses.POST, URL, status=202)

    WebhookSink(webhook(), LOG).send([{"n": 1}, {"n": 2}])

    (call,) = mock.calls
    assert call.request.headers["Authorization"] == AUTH
    assert call.request.headers["Content-Type"] == "application/json"
    assert json.loads(call.request.body) == [{"n": 1}, {"n": 2}]


def test_a_refusal_never_echoes_a_header_value(mock: responses.RequestsMock) -> None:
    mock.add(responses.POST, URL, status=401, body=f"denied {AUTH}")

    with pytest.raises(SinkDeliveryError) as e:
        WebhookSink(webhook(), LOG).send([{"n": 1}])

    assert "hook-s3cret-0003" not in str(e.value)
    assert "webhook at hooks.example.com" in str(e.value)


def test_header_values_and_the_path_are_secrets() -> None:
    secrets = WebhookSink(webhook(), LOG).secrets()

    assert AUTH in secrets and SECRET_PATH in secrets
    assert "hook-s3cret-0003" not in repr(webhook())


def test_the_destination_builds_its_sink() -> None:
    assert isinstance(webhook().build_sink(LOG), WebhookSink)
