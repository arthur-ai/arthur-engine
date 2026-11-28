"""Talking to GravityZone's public API: list endpoints, run one command, read its output.

JSON-RPC 2.0 over HTTPS, one POST per call to `<access_url>/<version>/jsonrpc/<module>`,
authenticated with HTTP Basic: a personal API key as the user name and an empty password
(Public API, 77211-125277). There is no token to mint or refresh, so a refused key is never
retried. GravityZone reports a refusal two ways, and both are read: HTTP 401 / 403, or a
JSON-RPC error -32001 "Authorization error" (wrong scope, missing user rights, licence) in
an HTTP 200, which is how it answers every error but 429.

THE ONE WRITE THIS CLIENT MAKES IS `startCommandExecutionOnEndpoint` (77209-1566170),
under the Remote Shell prerequisites, whose sessions run with root privileges
(77209-111689). The command is a constant of the connector that reads one file and prints
it. Nothing a source field holds is ever put into it.

RATE LIMITS ARE THE CUSTOMER'S, SHARED WITH EVERY OTHER INTEGRATION ON THE KEY. None of
the methods here is listed with its own limit, so the default applies: 10 requests a second
per key, 429 with Retry-After (and JSON-RPC -32003) past it (77211-394430). Calls are spaced
to stay under eight a second, one at a time, and a 429 is retried after the delay it names.

Doc pages are under https://www.bitdefender.com/business/support/en/<id>.html. STILL
UNVERIFIED AGAINST A REAL TENANT: the format of the output archive (the reference says only
"archive containing the command output log"; zip, tar, gzip and plain text are accepted,
and Remote Shell file downloads from Linux are GPG-encrypted, which would read as
unreadable output), whether the download URL needs the API key, and the exact
`enabledApis` token for the Investigation API.
"""

import base64
import gzip
import io
import logging
import tarfile
import time
import uuid
import zipfile
from dataclasses import dataclass
from typing import Any, Callable, Iterator, Optional
from urllib.parse import urlsplit

import requests

from discovery.retry import MAX_ATTEMPTS, RETRY_STATUSES, backoff_seconds

API_VERSION = "v1.0"
# getEndpointsList is documented at 1.1, which is also what allows 1000 a page; 1.0 caps at
# 100 (77211-128483).
ENDPOINTS_LIST_VERSION = "v1.1"
NETWORK = "network"
INVESTIGATION = "investigation"
GENERAL = "general"

# getEndpointsList's maximum page.
PAGE_SIZE = 1000

# Under GravityZone's default 10 requests a second per key, with room for whatever else
# the customer runs on it.
MIN_SECONDS_BETWEEN_CALLS = 0.125

# (connect, read). Their sum stays under Test Connection's 120 s deadline.
TIMEOUT = (10.0, 60.0)

# The command prints one `arthur1.` value of at most 256 KiB. An archive past this bound
# is not that output, and is not read into memory to find out.
MAX_DOWNLOAD_BYTES = 4 * 1024 * 1024

# getInvestigationFileUrl `status` (77209-1565959): pending, in_progress and
# to_be_retrieved are still running; success carries `url`; failed carries `errorCode`.
_DONE = "success"
_FAILED = "failed"
_PICKED_UP = frozenset({"in_progress", "to_be_retrieved"})
# errorCode for a task that ran out of GravityZone's own execution time.
TIMED_OUT_ERROR_CODE = -99997

# JSON-RPC error codes (77211-125277). -32001 covers an invalid key, a key without the
# API, missing user rights and licence restrictions; -32003 is the rate limit.
RPC_AUTHORIZATION_ERROR = -32001
RPC_TOO_MANY_REQUESTS = -32003

# GravityZone Cloud's own domain. The download URL is on the console's host, which is not
# always the access URL's (the reference shows `https://console-url/storage/...`).
CLOUD_DOMAIN = ".gravityzone.bitdefender.com"


class GravityZoneError(RuntimeError):
    """A GravityZone call failed in a way retrying will not fix."""

    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        rpc_code: Optional[int] = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.rpc_code = rpc_code


@dataclass(frozen=True)
class GravityZoneSettings:
    """Where the Control Center API is and the key that reaches it."""

    access_url: str
    api_key: str
    page_size: int = PAGE_SIZE


@dataclass(frozen=True)
class CommandOutput:
    """Where one command stands. `url` is set once its output can be downloaded."""

    state: str  # "pending", "done" or "failed"
    url: Optional[str] = None
    # GravityZone's errorCode for a failed task, e.g. TIMED_OUT_ERROR_CODE.
    error_code: Optional[int] = None
    # Whether the endpoint has started the task: in_progress or to_be_retrieved, rather
    # than pending (assigned, not started).
    picked_up: bool = False


# Module -> the API name an administrator ticks when creating the key, for the 403 hint.
_API_NAMES = {NETWORK: "Network", INVESTIGATION: "Investigation", GENERAL: "General"}


class GravityZoneClient:
    """One API key's session against one GravityZone Control Center."""

    def __init__(
        self,
        settings: GravityZoneSettings,
        logger: Optional[logging.Logger] = None,
        session: Optional[requests.Session] = None,
        sleep: Callable[[float], None] = time.sleep,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._s = settings
        self._log = logger or logging.getLogger(__name__)
        self._http = session or requests.Session()
        self._sleep = sleep
        self._clock = clock
        self._next_call_at = 0.0
        token = base64.b64encode(f"{settings.api_key}:".encode()).decode()
        self._auth = f"Basic {token}"
        self._host = (urlsplit(settings.access_url).hostname or "").lower()

    # --- transport ----------------------------------------------------------------

    def _url(self, module: str, version: str = API_VERSION) -> str:
        return f"{self._s.access_url.rstrip('/')}/{version}/jsonrpc/{module}"

    def _pace(self) -> None:
        wait = self._next_call_at - self._clock()
        if wait > 0:
            self._sleep(wait)
        self._next_call_at = self._clock() + MIN_SECONDS_BETWEEN_CALLS

    def call(
        self,
        module: str,
        method: str,
        params: dict[str, Any],
        idempotent: bool = True,
        version: str = API_VERSION,
    ) -> Any:
        """One JSON-RPC call's `result`, or a `GravityZoneError` with the HTTP status.

        A call that is not idempotent -- starting a command -- is retried only on 429,
        which says it was not run. Repeating it after a 5xx or a dropped connection could
        run the command twice; the command only reads, but nothing makes that free.
        """
        last: Optional[str] = None
        for attempt in range(1, MAX_ATTEMPTS + 1):
            self._pace()
            try:
                resp = self._http.post(
                    self._url(module, version),
                    json={
                        "jsonrpc": "2.0",
                        "method": method,
                        "params": params,
                        "id": str(uuid.uuid4()),
                    },
                    headers={
                        "Authorization": self._auth,
                        "Content-Type": "application/json",
                        "Accept": "application/json",
                    },
                    # The key is in the header. A redirect to another host would carry it
                    # there.
                    allow_redirects=False,
                    timeout=TIMEOUT,
                )
            except (requests.ConnectionError, requests.Timeout) as exc:
                if idempotent and attempt < MAX_ATTEMPTS:
                    last = type(exc).__name__
                    self._sleep(backoff_seconds(attempt, None))
                    continue
                # The same type, so Test Connection still tells unreachable from slow.
                raise type(exc)(
                    f"GravityZone {method} did not answer at {self._host}: "
                    f"{type(exc).__name__}",
                ) from exc

            status = resp.status_code
            retryable = status == 429 or (idempotent and status in RETRY_STATUSES)
            if retryable and attempt < MAX_ATTEMPTS:
                last = f"HTTP {status}"
                self._sleep(backoff_seconds(attempt, resp.headers.get("Retry-After")))
                continue
            if status == 401:
                raise GravityZoneError(
                    f"GravityZone refused the API key (HTTP 401) on {method}. Check "
                    "api_key: it must be a key created under My Account > API keys, "
                    "and it is shown only once.",
                    status_code=401,
                )
            if status == 403:
                raise GravityZoneError(
                    f"GravityZone denied {method} (HTTP 403). The API key needs the "
                    f"{_API_NAMES.get(module, module)} API enabled, and the user who "
                    "owns it needs the rights that API uses.",
                    status_code=403,
                )
            if status != 200:
                # Not echoed: an error body can quote the request it failed on.
                raise GravityZoneError(
                    f"GravityZone {method} failed with HTTP {status}",
                    status_code=status,
                )
            try:
                return self._result(resp, method, module)
            except GravityZoneError as exc:
                # The rate limit as a JSON-RPC error: not run, so safe to send again.
                if exc.rpc_code == RPC_TOO_MANY_REQUESTS and attempt < MAX_ATTEMPTS:
                    last = "JSON-RPC -32003"
                    self._sleep(
                        backoff_seconds(attempt, resp.headers.get("Retry-After")),
                    )
                    continue
                raise

        raise GravityZoneError(
            f"GravityZone {method} still failing after {MAX_ATTEMPTS} attempts ({last})",
        )

    @staticmethod
    def _result(resp: Any, method: str, module: str) -> Any:
        try:
            body = resp.json()
        except ValueError:
            body = None
        if not isinstance(body, dict) or ("result" not in body and "error" not in body):
            # A proxy's login page or an HTML error is not GravityZone answering.
            raise GravityZoneError(
                f"GravityZone {method} answered 200 with a body that is not JSON-RPC; "
                "check access_url is the Control Center API access URL, ending in /api",
                status_code=200,
            )
        # Successful responses carry `"error": null`.
        error = body.get("error")
        if error:
            code = error.get("code") if isinstance(error, dict) else None
            data = error.get("data") if isinstance(error, dict) else None
            details = data.get("details") if isinstance(data, dict) else None
            # GravityZone's own explanation, e.g. "API Key is not allowed to access the
            # selected API: Incidents". It names the API, never the key; bounded anyway.
            said = f": {str(details)[:200]}" if details else ""
            if code == RPC_AUTHORIZATION_ERROR:
                raise GravityZoneError(
                    f"GravityZone denied {method} (JSON-RPC -32001 Authorization "
                    f"error{said}). The API key needs the "
                    f"{_API_NAMES.get(module, module)} API enabled, and the user who "
                    "owns it needs the rights and licence that API uses.",
                    status_code=403,
                    rpc_code=code,
                )
            raise GravityZoneError(
                f"GravityZone {method} returned JSON-RPC error {code}{said}",
                status_code=200,
                rpc_code=code if isinstance(code, int) else None,
            )
        return body.get("result")

    # --- key ----------------------------------------------------------------------

    def enabled_apis(self) -> Optional[frozenset[str]]:
        """The APIs this key was created with, lowercased, or None if it cannot say.

        Best effort: a refusal or an unfamiliar shape is None, never a failure, because
        all this decides is whether to say early what a command would say later.
        """
        try:
            result = self.call(GENERAL, "getApiKeyDetails", {})
        except GravityZoneError as exc:
            if exc.status_code == 401:
                raise
            return None
        apis = result.get("enabledApis") if isinstance(result, dict) else None
        if not isinstance(apis, list):
            return None
        return frozenset(str(api).lower() for api in apis)

    # --- endpoints ----------------------------------------------------------------

    def endpoints(self) -> Iterator[dict[str, Any]]:
        """Every managed endpoint the key's company can see, groups included.

        GravityZone pages by number and sorts by nothing a scan can key on, so an
        endpoint added or removed mid-scan can shift one across a page boundary. Ids
        already yielded are skipped; one shifted the other way is read by the next scan.
        """
        seen: set[str] = set()
        page = 1
        while True:
            result = self.call(
                NETWORK,
                "getEndpointsList",
                {
                    "isManaged": True,
                    "page": page,
                    "perPage": self._s.page_size,
                    "filters": {"depth": {"allItemsRecursively": True}},
                },
                version=ENDPOINTS_LIST_VERSION,
            )
            if not isinstance(result, dict):
                raise GravityZoneError(
                    "GravityZone getEndpointsList returned no result object",
                    status_code=200,
                )
            items = result.get("items") or []
            for item in items:
                ident = str(item.get("id") or "")
                if not ident or ident in seen:
                    continue
                seen.add(ident)
                yield item
            if not items or not _more_pages(result, page):
                return
            page += 1

    def endpoint_details(self, endpoint_id: str) -> dict[str, Any]:
        result = self.call(
            NETWORK,
            "getManagedEndpointDetails",
            {"endpointId": endpoint_id},
        )
        return result if isinstance(result, dict) else {}

    # --- commands -----------------------------------------------------------------

    def start_command(self, endpoint_id: str, command: str) -> str:
        """Start `command` on one endpoint; the activity id to poll it by.

        The result is the task id itself, a string (77209-1566170).
        """
        result = self.call(
            INVESTIGATION,
            "startCommandExecutionOnEndpoint",
            {"targetId": endpoint_id, "command": command},
            idempotent=False,
        )
        activity = _first(result, ("activityId", "taskId", "id"))
        if not activity:
            raise GravityZoneError(
                "GravityZone startCommandExecutionOnEndpoint returned no activity id",
                status_code=200,
            )
        return activity

    def command_output(self, endpoint_id: str, activity_id: str) -> CommandOutput:
        result = self.call(
            INVESTIGATION,
            "getInvestigationFileUrl",
            {"targetId": endpoint_id, "activityId": activity_id},
        )
        if not isinstance(result, dict):
            raise GravityZoneError(
                "GravityZone getInvestigationFileUrl returned no result object",
                status_code=200,
            )
        state = str(result.get("status") or "").strip().lower()
        if state == _FAILED:
            code = result.get("errorCode")
            return CommandOutput(
                "failed",
                error_code=code if isinstance(code, int) else None,
            )
        url = result.get("url")
        if state == _DONE and url:
            return CommandOutput("done", str(url), picked_up=True)
        return CommandOutput("pending", picked_up=state in _PICKED_UP)

    def download(self, url: str) -> bytes:
        """The output archive, bounded.

        The reference shows the URL on the console host (`https://console-url/storage/
        investigationFiles/<fileId>`), so the key goes to the access URL's own host and,
        when the access URL is GravityZone Cloud, to any host under its domain. Any other
        host is taken to be a pre-signed storage URL that must not be handed the key.
        """
        parts = urlsplit(url)
        if parts.scheme != "https":
            raise GravityZoneError(
                "GravityZone returned a download URL that is not https"
            )
        host = (parts.hostname or "").lower()
        ours = host == self._host or (
            self._host.endswith(CLOUD_DOMAIN) and host.endswith(CLOUD_DOMAIN)
        )
        self._pace()
        try:
            resp = self._http.get(
                url,
                headers={"Authorization": self._auth} if ours else {},
                allow_redirects=not ours,
                timeout=TIMEOUT,
                stream=True,
            )
        except (requests.ConnectionError, requests.Timeout) as exc:
            raise GravityZoneError(
                f"GravityZone output download did not answer: {type(exc).__name__}",
            ) from exc
        if resp.status_code != 200:
            raise GravityZoneError(
                f"GravityZone output download failed with HTTP {resp.status_code}",
                status_code=resp.status_code,
            )
        chunks, size = [], 0
        for chunk in resp.iter_content(64 * 1024):
            size += len(chunk)
            if size > MAX_DOWNLOAD_BYTES:
                raise GravityZoneError(
                    f"GravityZone output is past the {MAX_DOWNLOAD_BYTES}-byte bound",
                )
            chunks.append(chunk)
        return b"".join(chunks)


def _more_pages(result: dict[str, Any], page: int) -> bool:
    """Whether another page follows, by whichever signal the response carries."""
    if "hasMoreRecords" in result:
        return bool(result["hasMoreRecords"])
    pages = result.get("pagesCount")
    if isinstance(pages, int):
        return page < pages
    return True  # an empty page ends it


def _first(result: Any, keys: tuple[str, ...]) -> Optional[str]:
    """The first of `keys` present in `result`, as text; `result` itself if a string."""
    if isinstance(result, str):
        return result or None
    if not isinstance(result, dict):
        return None
    for key in keys:
        value = result.get(key)
        if value is not None and value != "":
            return str(value)
    return None


def output_texts(blob: bytes) -> Iterator[str]:
    """Every text the downloaded output holds, whatever it was packed as.

    The reference does not say what the archive is, so zip, tar (any compression) and a
    lone gzip are opened, and anything else is read as the text itself. Each member is
    read up to `MAX_DOWNLOAD_BYTES`: a compressed archive is bounded by what it expands
    to, not by what was downloaded.
    """
    buf = io.BytesIO(blob)
    if zipfile.is_zipfile(buf):
        with zipfile.ZipFile(buf) as archive:
            for info in archive.infolist():
                if info.is_dir():
                    continue
                with archive.open(info) as member:
                    yield _text(member.read(MAX_DOWNLOAD_BYTES + 1))
        return
    buf.seek(0)
    try:
        with tarfile.open(fileobj=buf, mode="r:*") as archive:
            for tar_info in archive:
                if not tar_info.isfile():
                    continue
                handle = archive.extractfile(tar_info)
                if handle is not None:
                    yield _text(handle.read(MAX_DOWNLOAD_BYTES + 1))
        return
    except (tarfile.TarError, EOFError, OSError):
        pass
    if blob[:2] == b"\x1f\x8b":
        try:
            with gzip.GzipFile(fileobj=io.BytesIO(blob)) as gz:
                yield _text(gz.read(MAX_DOWNLOAD_BYTES + 1))
            return
        except (OSError, EOFError):
            pass
    yield _text(blob)


def _text(raw: bytes) -> str:
    if len(raw) > MAX_DOWNLOAD_BYTES:
        return ""
    return raw.decode("utf-8", errors="replace")
