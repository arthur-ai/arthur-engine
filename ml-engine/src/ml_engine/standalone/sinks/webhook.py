"""Any HTTPS endpoint that takes a JSON array of events in a POST."""

import json
import logging
import time
from typing import Callable, Literal, Optional, Sequence

import requests
from pydantic import Field

from standalone.config_values import Secret
from standalone.sinks.common import Event, Sink
from standalone.sinks.http import HttpDestination, HttpSink


class WebhookDestination(HttpDestination):
    type: Literal["webhook"]
    # Secrets, because the one header almost every webhook needs is Authorization.
    headers: dict[str, Secret] = Field(default_factory=dict)

    def build_sink(self, logger: logging.Logger) -> Sink:
        return WebhookSink(self, logger)


class WebhookSink(HttpSink):
    """Authenticates with whatever headers the destination configures."""

    kind = "webhook"

    def __init__(
        self,
        destination: WebhookDestination,
        logger: logging.Logger,
        session: Optional[requests.Session] = None,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self._headers = {
            name: value.get_secret_value()
            for name, value in destination.headers.items()
        }
        super().__init__(destination, logger, session, sleep)

    def _destination_secrets(self) -> tuple[str, ...]:
        return tuple(self._headers.values())

    def _encode(self, batch: Sequence[Event]) -> tuple[bytes, dict[str, str]]:
        return json.dumps(list(batch)).encode(), {
            "Content-Type": "application/json",
            **self._headers,
        }
