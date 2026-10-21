"""Google Security Operations' dashboard query API, as far as a discovery scan needs it.

ONE CALL. `POST /v1/{instance}/dashboardQueries:execute` runs a YARA-L 2.0 statistics
query (one with a `match:` or `outcome:` section) and returns the whole result. There is
no job to create or delete and no page token, so a result is complete or capped, never
"more to come". The call is a POST but a read: it changes nothing on the instance, so a
429 or 5xx is safe to send again.

COLUMNS, NOT ROWS. The answer is `results[]`, one entry per match or outcome variable,
`{column, values[]}`, and row i is the i-th value of every column. Each value is a typed
wrapper -- `{"value": {"stringVal": ...}}`, `{"value": {"int64Val": "123"}}` (64-bit
integers are JSON strings), `{"value": {"timestampVal": ...}}`, `{"value": {"nullVal":
true}}` -- or a list of them, `{"list": {"values": [...]}}`, which is what
`array_distinct()` returns. They are unwrapped here into plain values, so the shared
SIEM code sees rows keyed by column name as it does for every other SIEM.

HOW A CAP SHOWS. A custom query returns at most 1,000 rows by default and 10,000 with a
`limit:` section. A result that hit either says so in `queryRuntimeErrors[]` with a
`warningReason` of `ROW_LIMIT_EXCEEDED` or `DEFAULT_ROW_LIMIT_EXCEEDED`; those, and any
other runtime error the query met, are carried to the connector to report.

THE HOST IS BUILT, NEVER GIVEN. Every instance is reached through its region's host,
`https://<location>-chronicle.googleapis.com`, and nothing a source says can point the
Google token at any other host: `location` is checked to be a bare region before it is
put into one.

Authenticated with a Google service account (or the engine's own identity, where the
engine opts in) through google-auth's `AuthorizedSession`, with a token for the
`chronicle.readonly` OAuth scope. Running the query needs one IAM permission on the
instance, `chronicle.dashboardQueries.execute`.
"""

import logging
import re
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Optional, Sequence

import google.auth
import requests
from google.auth.credentials import Credentials
from google.auth.exceptions import DefaultCredentialsError, RefreshError
from google.auth.transport.requests import AuthorizedSession

from discovery.gcp_credentials import SERVICE_ACCOUNT_KEY_FIELD, mark_refused_credential
from discovery.retry import MAX_ATTEMPTS, RETRY_STATUSES, backoff_seconds
from job_executors.discovery_scan import DiscoveryConfigurationError

# (connect, read). requests applies each separately, so together they must stay under
# Test Connection's 120s preview deadline (PREVIEW_DEADLINE_SECONDS). Google answers only
# once the query has run, so the read timeout bounds the query itself. Google's own
# client allows this method 1,800s; a query that needs more than 90s here has to read
# less (a shorter lookback, a narrower filter).
REQUEST_TIMEOUT_SECONDS = (10.0, 90.0)

# Read-only by OAuth scope as well as by IAM, as Compute Engine is with its readonly
# scope: a token minted for this scan cannot write to the instance whatever the service
# account's roles allow.
CHRONICLE_READONLY_SCOPE = "https://www.googleapis.com/auth/chronicle.readonly"

API_VERSION = "v1"

# The warning reasons that mean rows were cut off at a row limit.
_ROW_LIMIT_REASONS = frozenset(
    {
        "ROW_LIMIT_EXCEEDED",
        "DEFAULT_ROW_LIMIT_EXCEEDED",
        "CURATED_QUERY_DEFAULT_ROW_LIMIT_EXCEEDED",
    },
)

# A bracketed or quoted span of a message. A runtime error can quote the value it
# failed on, and a job log is not where a customer's log data should be copied to.
_QUOTED_SPAN = re.compile(r"\[[^\]]*\]|'[^']*'|\"[^\"]*\"|`[^`]*`")


class GcpSecurityOperationsError(Exception):
    """A Google Security Operations call that failed, carrying the HTTP status when
    Google answered.

    `status_code` is what `failure_code` and Test Connection read to tell a 401 from a
    host that never answered, so it is set whenever there was a response.
    """

    def __init__(self, message: str, status_code: Optional[int] = None) -> None:
        super().__init__(message)
        self.status_code = status_code


@dataclass(frozen=True)
class GcpSecurityOperationsSettings:
    """Which instance to query and as whom. `credentials` None is the engine's
    Application Default Credentials, which the connector has already checked the engine
    opted in to."""

    project_id: str
    location: str
    instance_id: str
    credentials: Optional[Credentials] = None
    timeout_seconds: tuple[float, float] = REQUEST_TIMEOUT_SECONDS

    @property
    def host(self) -> str:
        return f"{self.location}-chronicle.googleapis.com"

    @property
    def parent(self) -> str:
        """The instance's resource name, as every Chronicle API path takes it."""
        return (
            f"projects/{self.project_id}/locations/{self.location}"
            f"/instances/{self.instance_id}"
        )

    @property
    def url(self) -> str:
        return (
            f"https://{self.host}/{API_VERSION}/{self.parent}/dashboardQueries:execute"
        )


@dataclass(frozen=True)
class RuntimeNotice:
    """One of `queryRuntimeErrors[]`: what Google said went wrong while the query ran,
    with the title's quoted values taken out."""

    severity: str
    reason: str
    title: str
    row_limit: Optional[int] = None

    @property
    def is_row_limit(self) -> bool:
        return self.reason in _ROW_LIMIT_REASONS


@dataclass(frozen=True)
class QueryResult:
    """One query's answer: column names in order, rows keyed by them, what Google said
    while running it, and, per column, how many values had a type no record field can
    hold (bytes, a date, an embedded proto), which were read as null."""

    columns: list[str]
    rows: list[dict[str, Any]]
    notices: list[RuntimeNotice] = field(default_factory=list)
    unsupported_values: dict[str, int] = field(default_factory=dict)


def authorized_session(
    credentials: Optional[Credentials],
    scopes: Sequence[str],
) -> requests.Session:
    """A requests session that signs every call, refreshing its token as it goes.

    None is the engine's Application Default Credentials; `scopes` is what their token
    must carry.
    """
    if credentials is None:
        try:
            credentials, _ = google.auth.default(scopes=list(scopes))
        except DefaultCredentialsError as e:
            raise DiscoveryConfigurationError(
                f"Google Security Operations source has no "
                f"'{SERVICE_ACCOUNT_KEY_FIELD}', and this engine has no Application "
                f"Default Credentials to use instead: {e}",
            ) from None
    return AuthorizedSession(credentials)  # type: ignore[no-untyped-call]


class GcpSecurityOperationsClient:
    """One Google Security Operations instance, one identity. Runs YARA-L queries."""

    def __init__(
        self,
        settings: GcpSecurityOperationsSettings,
        logger: Optional[logging.Logger] = None,
        session: Optional[requests.Session] = None,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self._s = settings
        self._log = logger or logging.getLogger(__name__)
        self._sleep = sleep
        self._http = session or authorized_session(
            settings.credentials,
            [CHRONICLE_READONLY_SCOPE],
        )

    def query(
        self,
        text: str,
        start_time: str,
        end_time: str,
        should_stop: Callable[[], bool] = lambda: False,
    ) -> QueryResult:
        """Run `text` over [`start_time`, `end_time`), both RFC 3339 UTC.

        The window rides BESIDE the query, in `query.input.timeWindow`. It is never
        written into the query text, which stays exactly what the customer wrote.
        `clearCache` makes Google run the query rather than answer from a dashboard's
        cached result, so a scan reports what is in the logs now.

        A 429 or 5xx is sent again with backoff, asking `should_stop` before each
        retry; a stop then raises the last answer rather than waiting it out.
        """
        body: dict[str, Any] = {
            "query": {
                "query": text,
                "input": {"timeWindow": {"startTime": start_time, "endTime": end_time}},
            },
            "clearCache": True,
        }
        resp = self._post(body, should_stop)
        if resp.status_code == 200:
            return _result_from(resp)

        status, message, reason = _error_of(resp)
        if resp.status_code == 400 and status == "INVALID_ARGUMENT":
            # The source config's query -- a YARA-L compile error, or a query without
            # `match:` or `outcome:` -- so the source is reported as needing a change
            # rather than as Google failing. It carries no status_code, and its text
            # avoids "HTTP 400", either of which Test Connection would read as the
            # vendor's error. Raised here, outside any except block, so nothing rides
            # on __context__ either.
            raise DiscoveryConfigurationError(
                f"Google Security Operations rejected the source config's YARA-L "
                f"(status 400){_suffix(message)}. Correct the query: it must be a "
                f"statistics query, with a match: or outcome: section, whose variables "
                f"are named after the output columns.",
            )
        if resp.status_code == 404:
            raise DiscoveryConfigurationError(_not_found(status))
        raise GcpSecurityOperationsError(
            f"Google Security Operations POST {self._path} failed with HTTP "
            f"{resp.status_code}{_suffix(status)}{_suffix(reason)}{_suffix(message)}"
            f"{_hint(resp.status_code, reason)}",
            status_code=resp.status_code,
        )

    @property
    def _path(self) -> str:
        return f"/{API_VERSION}/{self._s.parent}/dashboardQueries:execute"

    def _post(
        self,
        body: dict[str, Any],
        should_stop: Callable[[], bool],
    ) -> requests.Response:
        for attempt in range(1, MAX_ATTEMPTS + 1):
            try:
                resp = self._http.post(
                    self._s.url,
                    json=body,
                    headers={"Accept": "application/json"},
                    # The token is a header. Refusing redirects says outright that this
                    # client only ever talks to the regional host it built.
                    allow_redirects=False,
                    timeout=self._s.timeout_seconds,
                )
            except RefreshError as e:
                # No token could be minted for the request. See gcp_credentials.
                mark_refused_credential(e)
                raise
            except (requests.ConnectionError, requests.Timeout) as exc:
                # Not retried: a read timeout has already spent most of Test
                # Connection's deadline. Re-raised as the same type so Test Connection
                # still reads it as the network failure (or timeout) it is. An
                # SSLError stays one too: the source has no TLS setting to change, and
                # a TLS-inspecting egress proxy is the engine's to trust.
                raise type(exc)(
                    f"Google Security Operations POST {self._path} unreachable: {exc}. "
                    f"The engine needs a network path to {self._s.host}; behind a "
                    f"TLS-inspecting proxy, its CA must be in the engine's "
                    f"REQUESTS_CA_BUNDLE.",
                ) from exc
            if (
                resp.status_code in RETRY_STATUSES
                and attempt < MAX_ATTEMPTS
                and not should_stop()
            ):
                self._sleep(backoff_seconds(attempt, resp.headers.get("Retry-After")))
                continue
            return resp
        raise AssertionError("unreachable")  # the loop always returns or raises


def _result_from(resp: requests.Response) -> QueryResult:
    """The answer of a 200, which is not always Google's.

    A proxy or captive portal can answer 200 with HTML or someone else's JSON. That is
    reported as the vendor's error, with its status, rather than left as a bare
    ValueError, which Test Connection would read as a configuration mistake.

    proto3 JSON leaves out empty fields, so a query with nothing to report can come back
    without `results`. That is accepted only beside the `timeWindow` Google always
    echoes, which is what tells its empty answer from a body that is not Google's.
    """
    try:
        payload = resp.json()
    except ValueError:
        payload = None
    results = payload.get("results") if isinstance(payload, dict) else None
    if not isinstance(payload, dict) or not (
        isinstance(results, list) or (results is None and "timeWindow" in payload)
    ):
        raise GcpSecurityOperationsError(
            f"Google Security Operations answered HTTP {resp.status_code} with a body "
            f"that is not a dashboard query result "
            f"({resp.headers.get('Content-Type') or 'no content type'}).",
            status_code=resp.status_code,
        )
    columns, rows, unsupported = _rows_from(results or [], resp.status_code)
    return QueryResult(
        columns=columns,
        rows=rows,
        notices=_notices_from(payload.get("queryRuntimeErrors")),
        unsupported_values=unsupported,
    )


def _rows_from(
    results: list[Any],
    status: int,
) -> tuple[list[str], list[dict[str, Any]], dict[str, int]]:
    """Columns to rows. A column name loses one leading `$`, the YARA-L variable sigil,
    in case Google keeps it: the customer's `$external_id` is the column
    `external_id`. That normalises Google's output, not the customer's query."""
    names: list[str] = []
    columns: list[list[Any]] = []
    for entry in results:
        name = entry.get("column") if isinstance(entry, dict) else None
        values = entry.get("values", []) if isinstance(entry, dict) else None
        if (
            not isinstance(name, str)
            or not name.strip()
            or not isinstance(values, list)
        ):
            raise _malformed(status, "every column needs a name and a list of values")
        name = name.strip()
        names.append(name[1:] if name.startswith("$") else name)
        columns.append(values)
    if len(set(names)) != len(names):
        raise _malformed(status, "two columns have the same name")
    if len({len(values) for values in columns}) > 1:
        raise _malformed(status, "its columns do not all hold the same number of rows")

    unsupported: dict[str, int] = {}
    rows: list[dict[str, Any]] = [{} for _ in (columns[0] if columns else [])]
    for name, values in zip(names, columns):
        for row, cell in zip(rows, values):
            value, ok = _cell(cell)
            if ok is None:
                raise _malformed(
                    status,
                    f"a value in column {name} is not a typed value",
                )
            if not ok:
                unsupported[name] = unsupported.get(name, 0) + 1
            row[name] = value
    return names, rows, unsupported


def _cell(cell: Any) -> tuple[Any, Optional[bool]]:
    """One `ColumnType`: a single value, a list of them, or nothing (null).

    Returns the plain value and whether every part of it could be read; None for the
    second when the cell is not shaped like a `ColumnType` at all.
    """
    if not isinstance(cell, dict):
        return None, None
    if "list" in cell:
        items = (
            cell["list"].get("values", []) if isinstance(cell["list"], dict) else None
        )
        if not isinstance(items, list):
            return None, None
        read = [_value(item) for item in items]
        if any(ok is None for _, ok in read):
            return None, None
        return [v for v, _ in read if v is not None], all(ok for _, ok in read)
    if "value" in cell:
        return _value(cell["value"])
    return None, True


def _value(value: Any) -> tuple[Any, Optional[bool]]:
    """One `ColumnValue`, unwrapped. proto3 JSON writes 64-bit integers as strings."""
    if not isinstance(value, dict):
        return None, None
    if "stringVal" in value:
        return str(value["stringVal"]), True
    if "timestampVal" in value:
        return str(value["timestampVal"]), True
    for key in ("int64Val", "uint64Val"):
        if key in value:
            try:
                return int(value[key]), True
            except (TypeError, ValueError):
                return None, False
    if "doubleVal" in value:
        try:
            return float(value["doubleVal"]), True
        except (TypeError, ValueError):
            return None, False
    if "boolVal" in value:
        return bool(value["boolVal"]), True
    if "nullVal" in value:
        return None, True
    if any(key in value for key in ("bytesVal", "dateVal", "protoVal")):
        return None, False
    # Only metadata, or nothing: proto3 JSON leaves a default value out entirely.
    return None, True


def _notices_from(raw: Any) -> list[RuntimeNotice]:
    notices: list[RuntimeNotice] = []
    for error in raw if isinstance(raw, list) else []:
        if not isinstance(error, dict):
            continue
        row_limit = None
        for item in error.get("metadata") or []:
            if isinstance(item, dict) and item.get("key") == "ROW_LIMIT":
                try:
                    row_limit = int(str(item.get("value")))
                except (TypeError, ValueError):
                    pass
        notices.append(
            RuntimeNotice(
                severity=str(
                    error.get("errorSeverity") or "ERROR_SEVERITY_UNSPECIFIED",
                ),
                reason=str(error.get("warningReason") or "WARNING_REASON_UNSPECIFIED"),
                title=_QUOTED_SPAN.sub("[...]", str(error.get("errorTitle") or "")),
                row_limit=row_limit,
            ),
        )
    return notices


def _malformed(status: int, what: str) -> GcpSecurityOperationsError:
    return GcpSecurityOperationsError(
        f"Google Security Operations answered HTTP {status} with a malformed dashboard "
        f"query result: {what}.",
        status_code=status,
    )


def _error_of(resp: requests.Response) -> tuple[str, str, str]:
    """Google's canonical status (`INVALID_ARGUMENT`), its message, and the reason of
    its `ErrorInfo` detail (`IAM_PERMISSION_DENIED`, `SERVICE_DISABLED`), each "" when
    the body does not carry it. Google's error messages name the method, the permission
    and the resource, never the token."""
    try:
        body = resp.json()
    except ValueError:
        return "", "", ""
    error = body.get("error") if isinstance(body, dict) else None
    if not isinstance(error, dict):
        return "", "", ""
    reason = ""
    for detail in error.get("details") or []:
        if isinstance(detail, dict) and str(detail.get("@type", "")).endswith(
            "google.rpc.ErrorInfo",
        ):
            reason = str(detail.get("reason") or "")
    return str(error.get("status") or ""), str(error.get("message") or ""), reason


def _not_found(status: str) -> str:
    if status == "NOT_FOUND":
        return (
            "Google Security Operations has no instance at the project_id, location "
            "and instance_id given (status 404). instance_id is the instance's "
            "customer ID, from SIEM Settings > Profile; project_id is the Google Cloud "
            "project the instance is bound to."
        )
    # Not Google's JSON: no Chronicle API answers at the host built from location.
    return (
        "No Google Security Operations API answered at the host built from location "
        "(status 404). location must be the instance's region as Google names it, "
        "such as us, eu or europe-west2."
    )


def _suffix(text: str) -> str:
    return f": {text}" if text else ""


def _hint(status: int, reason: str) -> str:
    if status == 401:
        return (
            ". The credential was refused: the service account key may be deleted or "
            "disabled, or the engine's own credentials expired."
        )
    if status == 403 and reason == "SERVICE_DISABLED":
        return ". Enable the Chronicle API in project_id."
    if status == 403 and reason == "ACCESS_TOKEN_SCOPE_INSUFFICIENT":
        return (
            ". The token's OAuth scope (chronicle.readonly) does not cover this method."
        )
    if status == 403:
        return (
            ". The service account needs chronicle.dashboardQueries.execute on the "
            "instance (a custom role with that permission, or Chronicle API Viewer, "
            "roles/chronicle.viewer, if it carries it)."
        )
    return ""
