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
import ssl
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Optional
from urllib.parse import quote, urljoin

import requests
from requests.adapters import HTTPAdapter

# Under `[restapi] maxresultrows` (50,000 by default), which caps one results request
# whatever `count` asks for.
PAGE_SIZE = 10_000

# How long a request waits on Splunk before giving up. A search runs as long as it runs;
# this bounds each REST call around it, not the search.
REQUEST_TIMEOUT_SECONDS = 30.0

_JOBS = "/services/search/v2/jobs"


class TLSVerification(str, Enum):
    """How the management port's certificate is checked. See the source type schema."""

    FULL = "full"
    CA_ONLY = "ca_only"
    OFF = "off"


class SplunkError(Exception):
    """A Splunk call that failed, carrying the HTTP status when Splunk answered.

    `status_code` is what Test Connection reads to tell a 401 from a host that never
    answered, so it is set whenever there was a response.
    """

    def __init__(self, message: str, status_code: Optional[int] = None) -> None:
        super().__init__(message)
        self.status_code = status_code


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


class _TLSAdapter(HTTPAdapter):
    """Carries an SSL context, and whether to match the hostname, into urllib3.

    Needed for `ca_only`: trusting a CA while not matching the hostname is a setting
    `requests` has no parameter for -- `verify` is all or nothing.
    """

    def __init__(self, ssl_context: ssl.SSLContext, match_hostname: bool) -> None:
        self._ssl_context = ssl_context
        self._match_hostname = match_hostname
        super().__init__()

    def init_poolmanager(self, *args: Any, **kwargs: Any) -> None:
        kwargs["ssl_context"] = self._ssl_context
        if not self._match_hostname:
            kwargs["assert_hostname"] = False
        super().init_poolmanager(*args, **kwargs)


def tls_session(settings: SplunkSettings) -> requests.Session:
    """A session that trusts the management port the way the source says to."""
    context = ssl.create_default_context()
    if settings.ca_certificate:
        try:
            context.load_verify_locations(cadata=settings.ca_certificate)
        except ssl.SSLError as exc:
            raise ValueError(
                f"Splunk source's ca_certificate is not a PEM certificate: {exc}",
            ) from exc
    if settings.tls_verification is not TLSVerification.FULL:
        context.check_hostname = False
    if settings.tls_verification is TLSVerification.OFF:
        context.verify_mode = ssl.CERT_NONE

    session = requests.Session()
    session.verify = settings.tls_verification is not TLSVerification.OFF
    session.mount(
        "https://",
        _TLSAdapter(
            context,
            match_hostname=settings.tls_verification is TLSVerification.FULL,
        ),
    )
    return session


class SplunkClient:
    """One search head, one token. Runs search jobs and pages their results."""

    def __init__(
        self,
        settings: SplunkSettings,
        logger: Optional[logging.Logger] = None,
        session: Optional[requests.Session] = None,
    ) -> None:
        self._s = settings
        self._log = logger or logging.getLogger(__name__)
        self._http = session or tls_session(settings)

    @property
    def page_size(self) -> int:
        """Rows asked for per results request. A shorter page is the last one."""
        return self._s.page_size

    def _url(self, path: str) -> str:
        return urljoin(self._s.base_url.rstrip("/") + "/", path.lstrip("/"))

    def _call(
        self,
        method: str,
        path: str,
        ok: tuple[int, ...],
        params: Optional[dict[str, Any]] = None,
        data: Optional[dict[str, Any]] = None,
    ) -> Any:
        try:
            resp = self._http.request(
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

        if resp.status_code in ok:
            return resp.json() if resp.content else None
        raise SplunkError(
            f"Splunk {method} {path} failed with HTTP {resp.status_code}"
            f"{_hint(resp.status_code)}{_messages_suffix(resp)}",
            status_code=resp.status_code,
        )

    def create_job(self, search: str, earliest: Optional[str], latest: str) -> str:
        """Start a search and return its sid. Does not wait for it."""
        data: dict[str, Any] = {
            "search": search,
            "exec_mode": "normal",
            "latest_time": latest,
        }
        if earliest is not None:
            data["earliest_time"] = earliest
        body = self._call("POST", _JOBS, ok=(200, 201), data=data)
        sid = (body or {}).get("sid")
        if not sid:
            raise SplunkError("Splunk accepted the search but returned no sid")
        return str(sid)

    def job_status(self, sid: str) -> JobStatus:
        body = self._call("GET", f"{_JOBS}/{quote(sid, safe='')}", ok=(200,))
        entries = (body or {}).get("entry") or []
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
        body = (
            self._call(
                "GET",
                f"{_JOBS}/{quote(sid, safe='')}/results",
                ok=(200,),
                params={"offset": offset, "count": self._s.page_size},
            )
            or {}
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
            raise SplunkError(
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
            str(m.get("text")) for m in raw if isinstance(m, dict) and m.get("text")
        ]
    if isinstance(raw, dict):
        out: list[str] = []
        for kind, texts in raw.items():
            for text in texts if isinstance(texts, list) else [texts]:
                out.append(f"{kind}: {text}")
        return out
    return []


def _hint(status: int) -> str:
    if status == 401:
        return (
            ". The token was refused: wrong or expired, issued by another instance, "
            "an HTTP Event Collector token (which cannot search), or the search "
            "head's KV Store is down, which disables token authentication"
        )
    if status == 403:
        return ". The token's role lacks a capability this search needs"
    return ""


def _messages_suffix(resp: requests.Response) -> str:
    """Splunk's own error text, which names the bad SPL command or missing index."""
    try:
        texts = _job_messages((resp.json() or {}).get("messages"))
    except ValueError:
        return ""
    joined = "; ".join(texts)
    return f": {joined[:500]}" if joined else ""
