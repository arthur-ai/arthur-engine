"""The base for sink targets that deliver over HTTP: their shared config and plumbing.

A target subclasses both halves -- `HttpDestination` for the settings every HTTP
destination has, `HttpSink` for batching, retries and scrubbing -- and supplies only
how it frames a batch and which of its settings are secret.

A DESTINATION'S SECRETS NEVER LEAVE IN AN ERROR. `HttpSink` scrubs what its subclass
declares, plus the URL's password, path and query, which is where a webhook's own
secret usually lives, and names the destination by host alone.

NOR DO THEY FOLLOW A REDIRECT. requests follows one by default, re-sending the body
and every header but `Authorization` to wherever the destination points -- another
host included -- so a webhook's `X-Api-Key` and the agent inventory would go to an
address nobody configured. A redirect is refused like any other answer that is not a
2xx, naming the status, and the fix is to configure the address it points at.
"""

import logging
import threading
import time
from typing import Callable, ClassVar, Optional, Sequence
from urllib.parse import urlsplit

import requests
from pydantic import Field, model_validator

from log_redaction import redact_secrets
from standalone.config_values import StrictModel
from standalone.sinks.common import Event, Sink, SinkDeliveryError

DELIVERY_ATTEMPTS = 3
# What a retry can fix. Anything else -- a bad token, a payload the destination will
# never take -- fails the same way every time.
RETRY_STATUSES = frozenset({429, 500, 502, 503, 504})
# The longest a destination's Retry-After is honoured for. A scan holds its slot while
# it waits, and a destination asking for minutes is better reported down.
MAX_RETRY_DELAY_SECONDS = 30.0
# How much of a refusal's body the error keeps: enough for HEC's `{"text": "Invalid
# token", "code": 4}`, not enough for a proxy's whole HTML error page.
ERROR_BODY_CHARS = 300


def require_url(url: str, allow_http: bool) -> str:
    scheme, _, rest = url.partition("://")
    if not rest.split("/", 1)[0]:
        raise ValueError("expected an absolute URL, e.g. https://host/path")
    if scheme.lower() == "https" or (allow_http and scheme.lower() == "http"):
        return url
    raise ValueError(
        f"must be https, got {scheme or 'no scheme'}"
        + ("" if allow_http else "; set allow_insecure_http to send over http"),
    )


class HttpDestination(StrictModel):
    """Settings every HTTP sink target has. A target adds its `type` and credentials."""

    url: str
    verify_tls: bool = True
    # Off by default: the token or auth header travels with every request, and over
    # http it travels in cleartext.
    allow_insecure_http: bool = False
    # Events per request.
    batch_size: int = Field(default=100, gt=0)
    timeout_seconds: float = Field(default=30.0, gt=0)

    @model_validator(mode="after")
    def _url(self) -> "HttpDestination":
        require_url(self.url, allow_http=self.allow_insecure_http)
        return self

    def build_sink(self, logger: logging.Logger) -> Sink:
        """A sink for this destination, with a session of its own."""
        raise NotImplementedError


class HttpSink:
    """Implements `Sink` over HTTP; a subclass says how a batch is framed.

    ONE SINK SERVES EVERY SCAN, and scans run as threads. It keeps one HTTP session, so
    connections to the destination are reused across scans, and since a requests
    Session is not documented as safe to share between threads, each request is sent
    under a lock. Only the request itself: a retry waits outside it, so one scan
    backing off from a 429 does not hold up the others.
    """

    kind: ClassVar[str]

    def __init__(
        self,
        destination: HttpDestination,
        logger: logging.Logger,
        session: Optional[requests.Session] = None,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self._url = destination.url
        self._batch_size = destination.batch_size
        self._timeout = destination.timeout_seconds
        self._log = logger
        self._sleep = sleep
        self._session = session or requests.Session()
        self._session.verify = destination.verify_tls
        self._session_lock = threading.Lock()
        parts = urlsplit(destination.url)
        # Host and port only: the netloc can carry user:password.
        self._host = parts.hostname or "destination"
        if parts.port:
            self._host = f"{self._host}:{parts.port}"
        self._secrets = tuple(
            value
            for value in (
                *self._destination_secrets(),
                parts.password,
                parts.path,
                parts.query,
            )
            if value and value != "/"
        )

    def _destination_secrets(self) -> tuple[str, ...]:
        """The credentials the subclass sends with each request."""
        raise NotImplementedError

    def _encode(self, batch: Sequence[Event]) -> tuple[bytes, dict[str, str]]:
        """The request body and headers for one batch."""
        raise NotImplementedError

    def secrets(self) -> tuple[str, ...]:
        return self._secrets

    def close(self) -> None:
        self._session.close()

    def send(self, events: Sequence[Event]) -> None:
        """Deliver every event, a batch per request, in order.

        A batch that cannot be delivered raises, and the batches before it stay
        delivered: a destination has no transaction to roll them back into, and
        re-sending the scan's batches on the next interval is harmless.
        """
        for start in range(0, len(events), self._batch_size):
            self._post(events[start : start + self._batch_size])

    def _post(self, batch: Sequence[Event]) -> None:
        body, headers = self._encode(batch)
        for attempt in range(1, DELIVERY_ATTEMPTS + 1):
            last = attempt == DELIVERY_ATTEMPTS
            try:
                with self._session_lock:
                    response = self._session.post(
                        self._url,
                        data=body,
                        headers=headers,
                        timeout=self._timeout,
                        allow_redirects=False,
                    )
            except (requests.ConnectionError, requests.Timeout) as e:
                if last:
                    # `from None`: the cause's own traceback quotes the full URL.
                    raise SinkDeliveryError(
                        self._redact(
                            f"Could not reach {self.kind} at {self._host} after "
                            f"{attempt} attempt(s): {type(e).__name__}: {e}",
                        ),
                    ) from None
                reason, delay = type(e).__name__, self._backoff(attempt)
            else:
                status = response.status_code
                # Not `response.ok`, which is anything under 400: with redirects off, a
                # 3xx means the events went nowhere.
                if 200 <= status < 300:
                    return
                if status not in RETRY_STATUSES or last:
                    hint = (
                        " (a redirect, which is not followed: set url to the address it "
                        "points at)"
                        if 300 <= status < 400
                        else ""
                    )
                    raise SinkDeliveryError(
                        self._redact(
                            f"{self.kind} at {self._host} refused {len(batch)} "
                            f"event(s) with HTTP {status}{hint}: "
                            f"{response.text[:ERROR_BODY_CHARS]}",
                        ),
                        status_code=status,
                    )
                reason = f"HTTP {status}"
                delay = self._retry_after(response) or self._backoff(attempt)
            self._log.warning(
                f"Could not deliver {len(batch)} event(s) to {self.kind} at "
                f"{self._host} ({reason}); retrying in {delay:g}s",
            )
            self._sleep(delay)

    def _redact(self, text: str) -> str:
        return redact_secrets(text, self._secrets)

    @staticmethod
    def _backoff(attempt: int) -> float:
        return float(2 ** (attempt - 1))

    @staticmethod
    def _retry_after(response: requests.Response) -> Optional[float]:
        """A 429's Retry-After in seconds, capped. The HTTP-date form is ignored."""
        value = response.headers.get("Retry-After", "")
        try:
            seconds = float(value)
        except ValueError:
            return None
        return min(max(seconds, 0.0), MAX_RETRY_DELAY_SECONDS)
