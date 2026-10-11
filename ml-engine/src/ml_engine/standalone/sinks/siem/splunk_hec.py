"""Splunk's HTTP Event Collector, at its `/services/collector/event` endpoint."""

import json
import logging
import time
from datetime import datetime
from typing import Callable, Literal, Optional, Sequence

import requests

from standalone.config_values import Secret
from standalone.sinks.common import Event, Sink
from standalone.sinks.http import HttpDestination, HttpSink


class SplunkHecDestination(HttpDestination):
    type: Literal["splunk_hec"]
    token: Secret
    # Omitted, HEC uses the token's default index.
    index: Optional[str] = None
    source: str = "arthur-ml-engine"
    sourcetype: str = "arthur:discovered_agent"

    def build_sink(self, logger: logging.Logger) -> Sink:
        return SplunkHecSink(self, logger)


class SplunkHecSink(HttpSink):
    """A batch is one request of concatenated event objects, which HEC indexes as
    separate events.

    Without indexer acknowledgement a 200 means HEC accepted the batch, not that it is
    searchable yet; that is HEC's own guarantee, and the one every forwarder that does
    not configure acks relies on.
    """

    kind = "Splunk HEC"

    def __init__(
        self,
        destination: SplunkHecDestination,
        logger: logging.Logger,
        session: Optional[requests.Session] = None,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self._token = destination.token.get_secret_value()
        self._metadata: dict[str, str] = {
            "source": destination.source,
            "sourcetype": destination.sourcetype,
        }
        if destination.index:
            self._metadata["index"] = destination.index
        super().__init__(destination, logger, session, sleep)

    def _destination_secrets(self) -> tuple[str, ...]:
        return (self._token,)

    def _encode(self, batch: Sequence[Event]) -> tuple[bytes, dict[str, str]]:
        lines = (
            json.dumps(
                {
                    # HEC's own timestamp, so a search over time finds the event when
                    # it was observed rather than when it arrived.
                    "time": datetime.fromisoformat(event["observed_at"]).timestamp(),
                    **self._metadata,
                    "event": event,
                },
            )
            for event in batch
        )
        return "\n".join(lines).encode(), {
            "Authorization": f"Splunk {self._token}",
            "Content-Type": "application/json",
        }
