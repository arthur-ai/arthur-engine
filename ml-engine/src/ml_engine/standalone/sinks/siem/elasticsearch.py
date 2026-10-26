"""Elasticsearch, and so Elastic Security, through its `_bulk` API.

A DOCUMENT IS THE EVENT, plus the `@timestamp` a data stream requires, set to when it
was observed. Each is written with `create`, the one action a data stream takes, and
which an ordinary index takes as well. The default index is a data stream that
Elasticsearch's built-in `logs-*-*` template matches, so it is created on the first
write with no setup on the cluster.

A 200 IS NOT DELIVERY. `_bulk` answers 200 when it refused every document in the batch,
and says so per document in the body, so the body is read before a batch counts as sent.
"""

import base64
import json
import logging
import time
from typing import Callable, Literal, Optional, Sequence
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import requests
from pydantic import field_validator, model_validator

from standalone.config_values import Secret
from standalone.sinks.common import Event, Sink, SinkDeliveryError
from standalone.sinks.http import ERROR_BODY_CHARS, HttpDestination, HttpSink

DEFAULT_INDEX = "logs-arthur.discovery-default"
# What the answer is read for. The rest -- each document's id, index, version, shard
# counts -- is most of a large batch's response and nothing the sink needs.
BULK_FILTER_PATH = "errors,items.*.status,items.*.error"
# Characters Elasticsearch refuses anywhere in an index name.
INDEX_FORBIDDEN = set('\\/*?"<>| ,#:')


class ElasticsearchDestination(HttpDestination):
    type: Literal["elasticsearch"]
    # One of the two. An API key is either the `encoded` value
    # `POST /_security/api_key` returns, or `id:api_key`.
    api_key: Optional[Secret] = None
    username: Optional[str] = None
    password: Optional[Secret] = None
    # An index, alias or data stream the credentials can write to.
    index: str = DEFAULT_INDEX
    # An ingest pipeline to run each document through, as when mapping it onto ECS.
    pipeline: Optional[str] = None

    @field_validator("index")
    @classmethod
    def _index_name(cls, value: str) -> str:
        # Refused here, naming the setting, rather than by every delivery.
        if (
            not value
            or value != value.lower()
            or value[0] in "-_+"
            or INDEX_FORBIDDEN & set(value)
        ):
            raise ValueError(
                "must be lowercase, must not start with -, _ or +, and must not "
                f"contain any of {''.join(sorted(INDEX_FORBIDDEN))!r}",
            )
        return value

    @model_validator(mode="after")
    def _one_credential(self) -> "ElasticsearchDestination":
        basic = self.username is not None or self.password is not None
        if self.api_key and basic:
            raise ValueError("set api_key, or username and password, not both")
        if not self.api_key and not (self.username and self.password):
            raise ValueError("set api_key, or both username and password")
        return self

    def build_sink(self, logger: logging.Logger) -> Sink:
        return ElasticsearchSink(self, logger)


class ElasticsearchSink(HttpSink):
    """A batch is one `_bulk` request: an action line and a document per event."""

    kind = "Elasticsearch"

    def __init__(
        self,
        destination: ElasticsearchDestination,
        logger: logging.Logger,
        session: Optional[requests.Session] = None,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        if destination.api_key:
            credential = _encoded(destination.api_key.get_secret_value())
            self._authorization = f"ApiKey {credential}"
            self._credentials: tuple[str, ...] = (
                destination.api_key.get_secret_value(),
                credential,
            )
        else:
            assert destination.username and destination.password
            password = destination.password.get_secret_value()
            credential = base64.b64encode(
                f"{destination.username}:{password}".encode(),
            ).decode()
            self._authorization = f"Basic {credential}"
            self._credentials = (password, credential)
        self._action = json.dumps({"create": {"_index": destination.index}})
        super().__init__(destination, logger, session, sleep)
        self._url = _bulk_url(destination.url, destination.pipeline)

    def _destination_secrets(self) -> tuple[str, ...]:
        return self._credentials

    def _encode(self, batch: Sequence[Event]) -> tuple[bytes, dict[str, str]]:
        lines: list[str] = []
        for event in batch:
            lines.append(self._action)
            # The event's own time, so a search over time finds it when it was
            # observed rather than when it arrived.
            lines.append(json.dumps({"@timestamp": event["observed_at"], **event}))
        # `_bulk` requires the body to end in a newline.
        return ("\n".join(lines) + "\n").encode(), {
            "Authorization": self._authorization,
            "Content-Type": "application/x-ndjson",
        }

    def _check_accepted(
        self, response: requests.Response, batch: Sequence[Event]
    ) -> None:
        try:
            body = response.json()
        except ValueError:
            body = None
        if not isinstance(body, dict) or "errors" not in body:
            # A proxy in front of the cluster answering for it: nothing says the
            # documents were indexed.
            raise SinkDeliveryError(
                self._redact(
                    f"{self.kind} at {self._host} answered HTTP "
                    f"{response.status_code} with something other than a bulk "
                    f"response: {response.text[:ERROR_BODY_CHARS]}",
                ),
                status_code=response.status_code,
            )
        if not body["errors"]:
            return
        refused = [
            result
            for item in body.get("items", [])
            for result in item.values()
            if isinstance(result, dict) and result.get("error")
        ]
        first = refused[0] if refused else {}
        error = first.get("error") or {}
        reason = (
            f"{error.get('type')}: {error.get('reason')}"
            if isinstance(error, dict)
            else str(error)
        )
        indexed = ", and indexed the rest" if 0 < len(refused) < len(batch) else ""
        raise SinkDeliveryError(
            self._redact(
                f"{self.kind} at {self._host} refused {len(refused) or 'some'} of "
                f"{len(batch)} event(s) in a bulk request{indexed}. "
                f"First refusal, HTTP {first.get('status')}: "
                f"{reason[:ERROR_BODY_CHARS]}",
            ),
            status_code=first.get("status"),
        )


def _bulk_url(url: str, pipeline: Optional[str]) -> str:
    """The cluster's `_bulk` endpoint, with the query the sink reads its answer by.

    `url` is the cluster's, as an Elastic source takes it, path included for a cluster
    behind a gateway; one that already names `_bulk` is taken as it is.
    """
    parts = urlsplit(url)
    path = parts.path.rstrip("/")
    if not path.endswith("/_bulk"):
        path += "/_bulk"
    query = parse_qsl(parts.query)
    query.append(("filter_path", BULK_FILTER_PATH))
    if pipeline:
        query.append(("pipeline", pipeline))
    return urlunsplit(parts._replace(path=path, query=urlencode(query)))


def _encoded(api_key: str) -> str:
    """The key as the ApiKey header takes it, as the `elastic_security` source does.

    A key pasted as `id:api_key` is encoded rather than refused; base64 never contains
    a colon, so the two cannot be confused.
    """
    if ":" in api_key:
        return base64.b64encode(api_key.encode()).decode()
    return api_key
