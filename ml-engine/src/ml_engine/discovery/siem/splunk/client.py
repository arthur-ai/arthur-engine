"""Splunk's REST search API, as far as a discovery scan needs it.

A search is a JOB, not a call: it is created, polled until Splunk says it is done, read
a page at a time, and deleted. Each step is its own request against the management port
(8089), all carrying the same bearer token.

DELETED AT THE END, WHATEVER HAPPENED. A finished job keeps holding a slot of the
user's concurrent-search quota (`srchJobsQuota`, 3 by default) until it expires, so a
scan that leaves its job behind makes the next scan queue behind it.

The v2 job endpoints, because v1's are deprecated since Splunk 9.0.1.
"""

import logging
import time
from dataclasses import dataclass
from typing import Any, Callable, Optional
from urllib.parse import quote, urljoin

import requests

from discovery.retry import MAX_ATTEMPTS, RETRY_STATUSES, backoff_seconds
from discovery.siem.tls import TLSVerification, tls_session
from job_executors.discovery_scan import DiscoveryConfigurationError

# Under `[restapi] maxresultrows` (50,000 by default), which caps one results request
# whatever `count` asks for.
PAGE_SIZE = 10_000

# How long a request waits on Splunk before giving up. A search runs as long as it runs;
# this bounds each REST call around it, not the search.
REQUEST_TIMEOUT_SECONDS = 30.0

_JOBS = "/services/search/v2/jobs"

# Safe to send twice. Creating a search is not: a retried POST whose first attempt
# reached Splunk starts a second job, holding a second slot of the user's quota.
_IDEMPOTENT = frozenset({"GET", "DELETE"})


class SplunkError(Exception):
    """A Splunk call that failed, carrying the HTTP status when Splunk answered.

    `status_code` is what Test Connection reads to tell a 401 from a host that never
    answered, so it is set whenever there was a response. `splunk_messages` is
    Splunk's own error text, kept apart so it can be reported without the status.
    """

    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        splunk_messages: str = "",
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.splunk_messages = splunk_messages


@dataclass(frozen=True)
class SplunkSettings:
    """Where the search head is and how to authenticate and trust it."""

    base_url: str
    auth_token: str
    ca_certificate: Optional[str] = None
    tls_verification: TLSVerification = TLSVerification.FULL
    page_size: int = PAGE_SIZE
    timeout_seconds: float = REQUEST_TIMEOUT_SECONDS


@dataclass(frozen=True)
class JobStatus:
    """The fields of a search job that say whether its results can be trusted.

    `is_finalized` is a search Splunk stopped before it completed -- by `srchMaxTime`,
    or by hand -- whose results are partial although the job reports done.
    """

    dispatch_state: str
    is_done: bool
    is_failed: bool
    is_finalized: bool
    result_count: int
    messages: tuple[str, ...]


class SplunkClient:
    """One search head, one token. Runs search jobs and pages their results."""

    def __init__(
        self,
        settings: SplunkSettings,
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
            "Splunk",
        )

    def _url(self, path: str) -> str:
        return urljoin(self._s.base_url.rstrip("/") + "/", path.lstrip("/"))

    def _call(
        self,
        method: str,
        path: str,
        ok: tuple[int, ...],
        params: Optional[dict[str, Any]] = None,
        data: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """One REST call, retried when it is safe to repeat and the failure passes.

        A scan polls a search for as long as it runs, so a single 503 or dropped
        keep-alive would otherwise fail it and delete a search that was nearly done.
        """
        attempts = MAX_ATTEMPTS if method in _IDEMPOTENT else 1
        for attempt in range(1, attempts + 1):
            try:
                resp = self._send(method, path, params, data)
            except (requests.ConnectionError, requests.Timeout):
                # A TLS failure is already a SplunkError by here: retrying cannot fix
                # a certificate.
                if attempt == attempts:
                    raise
                self._sleep(backoff_seconds(attempt, None))
                continue
            if resp.status_code in ok:
                return _object_body(resp, method, path)
            if resp.status_code in RETRY_STATUSES and attempt < attempts:
                self._sleep(backoff_seconds(attempt, resp.headers.get("Retry-After")))
                continue
            messages = _messages_suffix(resp)
            raise SplunkError(
                f"Splunk {method} {path} failed with HTTP {resp.status_code}"
                f"{_hint(resp.status_code, path)}{messages}",
                status_code=resp.status_code,
                splunk_messages=messages,
            )
        raise AssertionError("unreachable: the last attempt returns or raises")

    def _send(
        self,
        method: str,
        path: str,
        params: Optional[dict[str, Any]],
        data: Optional[dict[str, Any]],
    ) -> requests.Response:
        try:
            return self._http.request(
                method,
                self._url(path),
                params={**(params or {}), "output_mode": "json"},
                data=data,
                headers={
                    "Authorization": f"Bearer {self._s.auth_token}",
                    "Accept": "application/json",
                },
                # The token is a header. requests drops Authorization on a redirect
                # to another host, but refusing redirects says outright that this
                # client only ever talks to the host it was given.
                allow_redirects=False,
                timeout=self._s.timeout_seconds,
            )
        except requests.exceptions.SSLError as exc:
            raise SplunkError(
                f"Splunk {method} {path}: TLS verification failed ({exc}). If the "
                f"search head uses a private CA, set ca_certificate; if it still has "
                f"Splunk's default certificate, which names no host, set "
                f"tls_verification to ca_only.",
            ) from exc
        except (requests.ConnectionError, requests.Timeout) as exc:
            # Re-raised as the same kind so Test Connection still reads it as the
            # network failure it is.
            raise type(exc)(
                f"Splunk {method} {path} unreachable: {exc}. An on-premises search "
                f"head needs an engine inside its network; Splunk Cloud needs the "
                f"engine's address on its search-api IP allow list.",
            ) from exc

    def create_job(self, search: str, earliest: Optional[str], latest: str) -> str:
        """Start a search and return its sid. Does not wait for it."""
        data: dict[str, Any] = {
            "search": search,
            "exec_mode": "normal",
            "latest_time": latest,
        }
        if earliest is not None:
            data["earliest_time"] = earliest
        try:
            body = self._call("POST", _JOBS, ok=(200, 201), data=data)
        except SplunkError as exc:
            if exc.status_code != 400:
                raise
            # Splunk parses the SPL when the job is created and answers 400 for a
            # command it does not know or a malformed pipeline: only the query can fix
            # that. Neither chained nor carrying "HTTP 400" in its text: Test Connection
            # finds a status in either and would read it as a vendor fault.
            raise DiscoveryConfigurationError(
                f"Splunk refused the source config's query (status 400)"
                f"{exc.splunk_messages}",
            ) from None
        sid = body.get("sid")
        if not sid:
            raise SplunkError("Splunk accepted the search but returned no sid")
        return str(sid)

    def job_status(self, sid: str) -> JobStatus:
        body = self._call("GET", f"{_JOBS}/{quote(sid, safe='')}", ok=(200,))
        entries = body.get("entry") or []
        if not entries:
            raise SplunkError(f"Splunk returned no status for search {sid}")
        content = entries[0].get("content") or {}
        return JobStatus(
            dispatch_state=str(content.get("dispatchState") or ""),
            is_done=_flag(content.get("isDone")),
            is_failed=_flag(content.get("isFailed")),
            is_finalized=_flag(content.get("isFinalized")),
            result_count=int(content.get("resultCount") or 0),
            messages=tuple(_job_messages(content.get("messages"))),
        )

    def results(self, sid: str, offset: int) -> tuple[list[str], list[dict[str, Any]]]:
        """One page of a finished job's results: the column names, then the rows."""
        body = self._call(
            "GET",
            f"{_JOBS}/{quote(sid, safe='')}/results",
            ok=(200,),
            params={"offset": offset, "count": self._s.page_size},
        )
        columns = [
            str(f.get("name") if isinstance(f, dict) else f)
            for f in body.get("fields") or []
        ]
        return columns, list(body.get("results") or [])

    def delete_job(self, sid: str) -> None:
        """Free the job's quota slot. Best effort: the scan's outcome does not hang on it."""
        try:
            self._call("DELETE", f"{_JOBS}/{quote(sid, safe='')}", ok=(200, 204))
        except (SplunkError, requests.RequestException) as exc:
            self._log.warning(
                "Splunk search %s could not be deleted and holds a search slot until "
                "it expires: %s",
                sid,
                exc,
            )


def wait_for_job(
    client: SplunkClient,
    sid: str,
    should_stop: Callable[[], bool],
    queued_limit_seconds: float,
    sleep: Callable[[float], None] = time.sleep,
    clock: Callable[[], float] = time.monotonic,
) -> Optional[JobStatus]:
    """Poll until the job is done; None when told to stop first.

    The stop check runs on every poll, not only between pages: a Test Connection
    deadline must hold while Splunk is still searching, which is where the time goes.
    """
    delay = 0.5
    queued_since: Optional[float] = None
    while True:
        status = client.job_status(sid)
        if status.is_failed or status.dispatch_state == "FAILED":
            # Splunk accepted the search and then could not run it: an unknown command,
            # a missing macro or lookup. The query is what has to change.
            raise DiscoveryConfigurationError(
                f"Splunk search {sid} failed"
                + (f": {'; '.join(status.messages)}" if status.messages else ""),
            )
        if status.is_done:
            return status
        if status.dispatch_state == "QUEUED":
            queued_since = clock() if queued_since is None else queued_since
            if clock() - queued_since > queued_limit_seconds:
                raise SplunkError(
                    f"Splunk search {sid} stayed queued for over "
                    f"{queued_limit_seconds:.0f}s. The token's user is likely at its "
                    f"concurrent search quota (srchJobsQuota), or the search head at "
                    f"its search limit.",
                )
        else:
            queued_since = None
        if should_stop():
            return None
        sleep(delay)
        delay = min(delay * 2, 5.0)


def _flag(value: Any) -> bool:
    """A job flag, accepted as a JSON boolean or as a "1"/"true" string."""
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true"}
    return bool(value)


def _job_messages(raw: Any) -> list[str]:
    """A job's `messages` is a list of {type, text}, or a dict of type -> texts."""
    if isinstance(raw, list):
        return [
            f"{m['type']}: {m['text']}" if m.get("type") else str(m["text"])
            for m in raw
            if isinstance(m, dict) and m.get("text")
        ]
    if isinstance(raw, dict):
        out: list[str] = []
        for kind, texts in raw.items():
            for text in texts if isinstance(texts, list) else [texts]:
                out.append(f"{kind}: {text}")
        return out
    return []


def _hint(status: int, path: str) -> str:
    if status == 401:
        return (
            ". The token was refused: wrong or expired, issued by another instance, "
            "an HTTP Event Collector token (which cannot search), or the search "
            "head's KV Store is down, which disables token authentication"
        )
    if status == 403:
        return ". The token's role lacks a capability this search needs"
    if status == 404 and path == _JOBS:
        return ". The v2 search API needs Splunk 9.0.1 or later"
    return ""


def _object_body(resp: requests.Response, method: str, path: str) -> dict[str, Any]:
    """A successful response's JSON object, or a SplunkError saying why it is not one.

    A 200 is not proof splunkd answered: a proxy or load balancer in front of the search
    head can send its own page. Raised as a SplunkError carrying the status, so the
    failure names the call and still reads as a host that answered.
    """
    if not resp.content:
        return {}
    try:
        body = resp.json()
    except ValueError as exc:
        raise SplunkError(
            f"Splunk {method} {path} returned HTTP {resp.status_code} with a body that "
            f"is not JSON. Something in front of the search head, such as a proxy or "
            f"load balancer, may have answered instead of splunkd.",
            status_code=resp.status_code,
        ) from exc
    if not isinstance(body, dict):
        raise SplunkError(
            f"Splunk {method} {path} returned HTTP {resp.status_code} with a JSON "
            f"{type(body).__name__} where an object was expected.",
            status_code=resp.status_code,
        )
    return body


def _messages_suffix(resp: requests.Response) -> str:
    """Splunk's own error text, which names the bad SPL command or missing index."""
    try:
        body = resp.json()
    except ValueError:
        return ""
    texts = _job_messages(body.get("messages")) if isinstance(body, dict) else []
    joined = "; ".join(texts)
    return f": {joined[:500]}" if joined else ""
