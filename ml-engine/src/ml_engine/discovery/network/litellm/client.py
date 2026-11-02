"""The LiteLLM proxy's admin API, as far as a discovery scan needs it.

Three read-only routes, all `GET`, all answered to a `proxy_admin_viewer` key:

* `/user/list?page_size=1`, the PROBE. A non-admin key gets a clean 403 here, while
  the spend-log route answers it 401, which would read as a bad credential. Asked
  first so a key with the wrong role is reported as permission denied.
* `/key/list?return_full_object=true`, the keys and the agent each is bound to.
  Paged with `page` / `size` (at most 100) up to `total_pages`.
* `/spend/logs/v2`, the request log. Paged with `page` / `page_size` (at most 1000)
  up to `total_pages`, except that `total` stops counting at 10,000 rows and says so
  with `total_is_capped`; past that, paging goes on until a page comes back short.
  `start_date` / `end_date` are UTC `YYYY-MM-DD HH:MM:SS`; ISO 8601 is refused with a
  400. Sorted oldest first, so a row written late (the proxy writes them in batches,
  20-60 s after the request) shifts later pages forward rather than out of reach.

Request and response bodies are never asked for: the list route leaves them out.
Never a write route, even though a mis-scoped key could call one.

Every auth error the proxy writes echoes a masked fragment of the key it was sent, so
no error text from the proxy is ever copied into an exception or the log.
"""

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Iterator, Optional
from urllib.parse import urljoin

import requests

from discovery.retry import MAX_ATTEMPTS, RETRY_STATUSES, backoff_seconds
from discovery.siem.tls import TLSVerification, tls_session
from job_executors.discovery_scan import DiscoveryConfigurationError

# (connect, read): each page is one bounded query, and the pair stays under Test
# Connection's 120 s preview deadline (PREVIEW_DEADLINE_SECONDS).
REQUEST_TIMEOUT_SECONDS = (10.0, 60.0)

SPEND_PAGE_SIZE = 1000
KEY_PAGE_SIZE = 100

# What `start_date` accepts for "everything the proxy retains".
EARLIEST = datetime(1970, 1, 1)
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

PROBE_PATH = "/user/list"
KEYS_PATH = "/key/list"
SPEND_LOGS_PATH = "/spend/logs/v2"


class LiteLLMError(Exception):
    """A proxy call that failed, carrying the HTTP status when the proxy answered.

    `status_code` is what Test Connection reads to tell a 401 from a proxy that never
    answered, so it is set whenever there was a response.
    """

    def __init__(self, message: str, status_code: Optional[int] = None) -> None:
        super().__init__(message)
        self.status_code = status_code


@dataclass(frozen=True)
class LiteLLMSettings:
    """Where the proxy is and how to authenticate and trust it."""

    base_url: str
    api_key: str = field(repr=False)
    ca_certificate: Optional[str] = None
    tls_verification: TLSVerification = TLSVerification.FULL
    timeout_seconds: tuple[float, float] = REQUEST_TIMEOUT_SECONDS


@dataclass(frozen=True)
class VirtualKey:
    """One key the proxy issued, as `/key/list` reports it. `token` is the proxy's
    hash of the key, never the key."""

    token: str
    alias: Optional[str] = None
    team_alias: Optional[str] = None
    agent_id: Optional[str] = None


class LiteLLMClient:
    """One proxy, one key. Reads its keys and its request log."""

    def __init__(
        self,
        settings: LiteLLMSettings,
        logger: Optional[logging.Logger] = None,
        session: Optional[requests.Session] = None,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self._s = settings
        self._log = logger or logging.getLogger(__name__)
        self._sleep = sleep
        self._http = session or tls_session(
            settings.ca_certificate,
            settings.tls_verification,
            "LiteLLM",
        )

    def probe_admin(self) -> None:
        """Raise unless the key may read the proxy's admin lists."""
        self._get(PROBE_PATH, {"page": 1, "page_size": 1})

    def keys(self, should_stop: Callable[[], bool]) -> Iterator[list[VirtualKey]]:
        """Every key the proxy lists, a page at a time."""
        page = 1
        while not should_stop():
            body = self._get(
                KEYS_PATH,
                {"return_full_object": "true", "page": page, "size": KEY_PAGE_SIZE},
            )
            items = body.get("keys")
            if not isinstance(items, list):
                raise _not_the_proxy(KEYS_PATH)
            yield [k for k in (_key_of(item) for item in items) if k is not None]
            if len(items) < KEY_PAGE_SIZE or page >= _int(body.get("total_pages")):
                return
            page += 1

    def spend_pages(
        self,
        start: datetime,
        end: datetime,
        should_stop: Callable[[], bool],
    ) -> Iterator[list[dict[str, Any]]]:
        """The request log between `start` and `end` (naive UTC), oldest first, a page
        at a time. The stop check is asked before each page."""
        page = 1
        while not should_stop():
            body = self._get(
                SPEND_LOGS_PATH,
                {
                    "start_date": start.strftime(DATE_FORMAT),
                    "end_date": end.strftime(DATE_FORMAT),
                    "page": page,
                    "page_size": SPEND_PAGE_SIZE,
                    "sort_by": "startTime",
                    "sort_order": "asc",
                    "exclude_internal_health_checks": "true",
                },
            )
            data = body.get("data")
            if not isinstance(data, list):
                raise _not_the_proxy(SPEND_LOGS_PATH)
            yield [row for row in data if isinstance(row, dict)]
            if len(data) < SPEND_PAGE_SIZE:
                return
            if not body.get("total_is_capped") and page >= _int(
                body.get("total_pages")
            ):
                return
            page += 1

    def _get(self, path: str, params: dict[str, Any]) -> dict[str, Any]:
        """One GET, retried when the failure passes: every route read is idempotent."""
        for attempt in range(1, MAX_ATTEMPTS + 1):
            try:
                resp = self._send(path, params)
            except (requests.ConnectionError, requests.Timeout):
                if attempt == MAX_ATTEMPTS:
                    raise
                self._sleep(backoff_seconds(attempt, None))
                continue
            if resp.status_code == 200:
                return _object_body(resp, path)
            if resp.status_code in RETRY_STATUSES and attempt < MAX_ATTEMPTS:
                self._sleep(backoff_seconds(attempt, resp.headers.get("Retry-After")))
                continue
            raise LiteLLMError(
                f"LiteLLM GET {path} failed with HTTP {resp.status_code}"
                f"{_hint(resp.status_code, path)}",
                status_code=resp.status_code,
            )
        raise AssertionError("unreachable: the last attempt returns or raises")

    def _send(self, path: str, params: dict[str, Any]) -> requests.Response:
        try:
            return self._http.get(
                urljoin(self._s.base_url.rstrip("/") + "/", path.lstrip("/")),
                params=params,
                headers={
                    "Authorization": f"Bearer {self._s.api_key}",
                    "Accept": "application/json",
                },
                # The key is a header. Refusing redirects says outright that this
                # client only ever talks to the host it was given.
                allow_redirects=False,
                timeout=self._s.timeout_seconds,
            )
        except requests.exceptions.SSLError as exc:
            raise DiscoveryConfigurationError(
                f"LiteLLM GET {path}: TLS verification failed ({exc}). If the proxy "
                f"uses a private CA, set ca_certificate; if its certificate does not "
                f"name the host the engine uses, set tls_verification to ca_only with "
                f"that ca_certificate.",
            ) from exc
        except (requests.ConnectionError, requests.Timeout) as exc:
            # Re-raised as the same kind so Test Connection still reads it as the
            # network failure it is.
            raise type(exc)(
                f"LiteLLM GET {path} unreachable: {exc}. A self-hosted proxy needs an "
                f"engine inside its network.",
            ) from exc


def _object_body(resp: requests.Response, path: str) -> dict[str, Any]:
    """The JSON object of a 200, which is not always the proxy's: a load balancer or
    an SSO front door can answer 200 with a login page."""
    try:
        body = resp.json()
    except ValueError:
        body = None
    if not isinstance(body, dict):
        raise _not_the_proxy(path)
    return body


def _not_the_proxy(path: str) -> LiteLLMError:
    return LiteLLMError(
        f"LiteLLM GET {path} answered HTTP 200 with a body that is not the proxy's "
        f"answer. Check that base_url is the LiteLLM proxy itself, not its admin UI "
        f"or a login page in front of it.",
        status_code=200,
    )


def _key_of(item: Any) -> Optional[VirtualKey]:
    if not isinstance(item, dict):
        return None
    token = _text(item.get("token"))
    if token is None:
        return None
    return VirtualKey(
        token=token,
        alias=_text(item.get("key_alias")),
        team_alias=_text(item.get("team_alias")),
        agent_id=_text(item.get("agent_id")),
    )


def _text(value: Any) -> Optional[str]:
    if not isinstance(value, str):
        return None
    return value.strip() or None


def _int(value: Any) -> int:
    return value if isinstance(value, int) and not isinstance(value, bool) else 0


def _hint(status: int, path: str) -> str:
    if status == 401:
        return (
            ". The proxy rejected api_key: it may be expired, blocked or deleted, or "
            "not a key this proxy issued."
        )
    if status == 403:
        return (
            ". The key may not read the proxy's admin lists: create it for a user "
            "with the proxy_admin_viewer role."
        )
    if status == 400 and path == SPEND_LOGS_PATH:
        return (
            ". The proxy refused the request log query. Check that base_url is the "
            "proxy itself and that it serves /spend/logs/v2."
        )
    return ""
