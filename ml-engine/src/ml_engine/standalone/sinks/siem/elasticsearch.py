"""Elasticsearch, and so Elastic Security, through its `_bulk` API.

A DOCUMENT IS THE EVENT, plus the `@timestamp` a data stream requires, set to when it
was observed. Each is written with `create`, the one action a data stream takes, and
which an ordinary index takes as well. The default index is a data stream that
Elasticsearch's built-in `logs-*-*` template matches, so it is created on the first
write with no setup on the cluster.

A 200 IS NOT DELIVERY. `_bulk` answers 200 when it refused every document in the batch,
and says so per document in the body, so the body is read before a batch counts as sent.
A document refused for what it holds -- a field the index's mapping cannot take, a
pipeline that fails on it -- is refused again on every re-send, so it is handed back as
a failed record and the scan goes on without it. A document refused with 429 or 503 is
the cluster shedding load, and only those documents are sent again, as Elasticsearch's
own clients do.
"""

import base64
import json
import logging
import time
from typing import Any, Callable, Literal, Optional, Sequence
from urllib.parse import urlencode, urlsplit, urlunsplit

import requests
from pydantic import field_validator, model_validator

from standalone.config_values import Secret
from standalone.sinks.common import Event, RefusedEvent, Sink, SinkDeliveryError
from standalone.sinks.http import (
    ERROR_BODY_CHARS,
    EventResults,
    HttpDestination,
    HttpSink,
)

DEFAULT_INDEX = "logs-arthur.discovery-default"
# What the answer is read for. The rest -- each document's id, index, version, shard
# counts -- is most of a large batch's response and nothing the sink needs.
BULK_FILTER_PATH = "errors,items.*.status,items.*.error"
# Characters Elasticsearch refuses anywhere in an index name.
INDEX_FORBIDDEN = set('\\/*?"<>| ,#:')
# A document's status when the cluster is shedding load rather than refusing it: an
# indexing queue that is full, a shard that is not yet available.
ITEM_RETRY_STATUSES = frozenset({429, 503})


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
            value in ("", ".", "..")
            or value != value.lower()
            or value[0] in "-_+"
            or INDEX_FORBIDDEN & set(value)
        ):
            raise ValueError(
                "must be lowercase, must not be . or .., must not start with -, _ "
                f"or +, and must not contain any of "
                f"{''.join(sorted(INDEX_FORBIDDEN))!r}",
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

    def _read_accepted(
        self, response: requests.Response, batch: Sequence[Event]
    ) -> EventResults:
        results = _bulk_results(response, len(batch))
        if results is None:
            # A proxy in front of the cluster answering for it: nothing says the
            # documents were indexed.
            raise SinkDeliveryError(
                self._redact(
                    f"{self.kind} at {self._host} answered HTTP "
                    f"{response.status_code} with something other than a bulk "
                    f"response for {len(batch)} event(s): "
                    f"{response.text[:ERROR_BODY_CHARS]}",
                ),
                status_code=response.status_code,
            )
        refused: list[RefusedEvent] = []
        retry: list[RefusedEvent] = []
        for position, result in enumerate(results):
            status, error = result["status"], result.get("error")
            if 200 <= status < 300 and not error:
                continue
            if isinstance(error, dict):
                reason = str(error.get("type") or f"http_{status}")
                detail = str(error.get("reason") or "")
            else:
                reason, detail = f"http_{status}", str(error or "")
            # Scrubbed before it is cut, so no part of a secret is left behind.
            detail = self._redact(detail)[:ERROR_BODY_CHARS]
            refusal = RefusedEvent(position=position, reason=reason, detail=detail)
            (retry if status in ITEM_RETRY_STATUSES else refused).append(refusal)
        return EventResults(refused=refused, retry=retry)


def _bulk_results(response: requests.Response, count: int) -> Optional[list[Any]]:
    """Each document's result, in the order they were sent, or None for a body that
    is not a bulk response for `count` documents.

    Matched to the documents by position, which is the order `_bulk` answers in, so a
    body with a different count is refused rather than read against the wrong events.
    """
    try:
        body = response.json()
    except ValueError:
        return None
    items = body.get("items") if isinstance(body, dict) else None
    if not isinstance(items, list) or len(items) != count:
        return None
    results = []
    for item in items:
        # One key, the action: {"create": {"status": 201}}.
        if not isinstance(item, dict) or len(item) != 1:
            return None
        (result,) = item.values()
        if not isinstance(result, dict) or not isinstance(result.get("status"), int):
            return None
        results.append(result)
    return results


def _bulk_url(url: str, pipeline: Optional[str]) -> str:
    """The cluster's `_bulk` endpoint, with the query the sink reads its answer by.

    `url` is the cluster's, as an Elastic source takes it, path included for a cluster
    behind a gateway; one that already names `_bulk` is taken as it is.
    """
    parts = urlsplit(url)
    path = parts.path.rstrip("/")
    if not path.endswith("/_bulk"):
        path += "/_bulk"
    extra = [("filter_path", BULK_FILTER_PATH)]
    if pipeline:
        extra.append(("pipeline", pipeline))
    # Appended to the configured query rather than re-encoding it, which would change
    # how a secret in it is spelt and so slip it past the scrubbing of errors.
    query = "&".join(filter(None, [parts.query, urlencode(extra)]))
    return urlunsplit(parts._replace(path=path, query=query))


def _encoded(api_key: str) -> str:
    """The key as the ApiKey header takes it, as the `elastic_security` source does.

    A key pasted as `id:api_key` is encoded rather than refused; base64 never contains
    a colon, so the two cannot be confused.
    """
    if ":" in api_key:
        return base64.b64encode(api_key.encode()).decode()
    return api_key
