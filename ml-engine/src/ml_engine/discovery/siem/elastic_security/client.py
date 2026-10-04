"""Elasticsearch's ES|QL query API, as far as a discovery scan needs it.

ONE CALL. `POST /_query` runs the query and returns the whole result: a list of typed
columns and a list of rows in the same order. There is no job to create or delete and
no cursor to page through, so a result is complete or capped, never "more to come".

HOW A CAP SHOWS, which the connector has to read rather than an `is_truncated` flag the
API does not have (observed against Elasticsearch 9.5.4):

* No `LIMIT` in the query: at most 1,000 rows (`esql.query.result_truncation_default_size`)
  and a `Warning` header "No limit defined, adding default limit of [1000]" -- sent
  whether or not anything was cut.
* Any `LIMIT`: at most 10,000 rows (`esql.query.result_truncation_max_size`), cut
  silently, with no warning.
* `is_partial` is about shard failures, not about the row cap.

Authenticated with an Elasticsearch API key, `Authorization: ApiKey <encoded>`, where
`encoded` is what `POST /_security/api_key` returns: base64 of `id:api_key`. Running
ES|QL needs only `read` on the indices the query names; no cluster privilege.
"""

import logging
import re
from dataclasses import dataclass, field
from typing import Any, Optional
from urllib.parse import urljoin

import requests

from discovery.siem.tls import TLSVerification, tls_session
from job_executors.discovery_scan import DiscoveryConfigurationError

# (connect, read). requests applies a single number to the connect and to each socket
# read separately, so one 90s value could let a call run past Test Connection's 120s
# preview deadline. Elasticsearch writes its answer only once the query has finished,
# so the read timeout bounds the query itself, and the two together stay under 120s.
REQUEST_TIMEOUT_SECONDS = (10.0, 90.0)

# Error types of a 400 that is the customer's ES|QL rather than the cluster: a syntax
# error, an unknown column or function, an unknown index or one the key cannot read.
# The fix is in the source config's query, not on Elasticsearch's side.
_QUERY_ERROR_TYPES = frozenset({"parsing_exception", "verification_exception"})

# The quoted text of a `Warning: 299 Elasticsearch-<version>-<hash> "<text>"` header.
_WARNING_TEXT = re.compile(r'"((?:[^"\\]|\\.)*)"')


class ElasticError(Exception):
    """An Elasticsearch call that failed, carrying the HTTP status when it answered.

    `status_code` is what Test Connection reads to tell a 401 from a host that never
    answered, so it is set whenever there was a response.
    """

    def __init__(self, message: str, status_code: Optional[int] = None) -> None:
        super().__init__(message)
        self.status_code = status_code


@dataclass(frozen=True)
class ElasticSettings:
    """Where the cluster is and how to authenticate and trust it."""

    elasticsearch_url: str
    api_key: str
    ca_certificate: Optional[str] = None
    tls_verification: TLSVerification = TLSVerification.FULL
    timeout_seconds: tuple[float, float] = REQUEST_TIMEOUT_SECONDS


@dataclass(frozen=True)
class EsqlResult:
    """One query's answer: column names in order, rows keyed by them, and warnings."""

    columns: list[str]
    rows: list[dict[str, Any]]
    warnings: list[str] = field(default_factory=list)
    is_partial: bool = False


class ElasticClient:
    """One cluster, one API key. Runs ES|QL queries."""

    def __init__(
        self,
        settings: ElasticSettings,
        logger: Optional[logging.Logger] = None,
        session: Optional[requests.Session] = None,
    ) -> None:
        self._s = settings
        self._log = logger or logging.getLogger(__name__)
        self._http = session or tls_session(
            settings.ca_certificate,
            settings.tls_verification,
            "Elastic",
        )

    def query(self, esql: str, lookback_hours: Optional[int]) -> EsqlResult:
        """Run `esql`, restricted to the last `lookback_hours` when it is given.

        The lookback rides in the request's `filter`, a Query DSL range on `@timestamp`
        applied before the query runs. It is never written into the query text, which
        stays exactly what the customer wrote.
        """
        body: dict[str, Any] = {"query": esql}
        if lookback_hours:
            body["filter"] = {
                "range": {"@timestamp": {"gte": f"now-{lookback_hours}h"}},
            }
        url = urljoin(self._s.elasticsearch_url.rstrip("/") + "/", "_query")
        try:
            resp = self._http.post(
                url,
                params={"format": "json"},
                json=body,
                headers={
                    "Authorization": f"ApiKey {self._s.api_key}",
                    "Accept": "application/json",
                },
                # The key is a header. requests drops Authorization on a redirect to
                # another host, but refusing redirects says outright that this client
                # only ever talks to the host it was given.
                allow_redirects=False,
                timeout=self._s.timeout_seconds,
            )
        except requests.exceptions.SSLError as exc:
            raise ElasticError(
                f"Elastic POST /_query: TLS verification failed ({exc}). If the "
                f"cluster uses a private CA -- a self-managed cluster's auto-generated "
                f"http_ca.crt, for one -- set ca_certificate; if its certificate does "
                f"not name the host the engine uses, set tls_verification to ca_only.",
            ) from exc
        except (requests.ConnectionError, requests.Timeout) as exc:
            # Re-raised as the same kind so Test Connection still reads it as the
            # network failure it is.
            raise type(exc)(
                f"Elastic POST /_query unreachable: {exc}. A self-managed cluster "
                f"needs an engine inside its network; an Elastic Cloud deployment "
                f"behind traffic filters needs the engine's address allowed.",
            ) from exc

        if resp.status_code != 200:
            kind, reason = _error_of(resp)
            detail = f"{_reason_suffix(kind, reason)}{_hint(resp.status_code, reason)}"
            if resp.status_code == 400 and kind in _QUERY_ERROR_TYPES:
                # The source config's query, so the source is reported as needing a
                # change rather than as Elasticsearch failing. It carries no
                # status_code, and its text avoids "HTTP 400", either of which Test
                # Connection would read as the vendor's error.
                raise DiscoveryConfigurationError(
                    f"Elasticsearch rejected the source config's ES|QL (status 400)"
                    f"{detail}. Correct the query.",
                )
            raise ElasticError(
                f"Elastic POST /_query failed with HTTP {resp.status_code}{detail}",
                status_code=resp.status_code,
            )
        return _result_from(resp)


def _result_from(resp: requests.Response) -> EsqlResult:
    """The answer of a 200, which is not always Elasticsearch's.

    A proxy or load balancer in front of the cluster can answer 200 with an HTML page.
    That is reported as the vendor's error, with its status, rather than left as a bare
    ValueError, which Test Connection would read as a configuration mistake.
    """
    try:
        payload = resp.json()
    except ValueError:
        payload = None
    if not isinstance(payload, dict) or not isinstance(payload.get("columns"), list):
        raise ElasticError(
            f"Elastic POST /_query answered HTTP {resp.status_code} with a body that "
            f"is not an ES|QL result ({resp.headers.get('Content-Type') or 'no content type'}). "
            f"Check that elasticsearch_url is the Elasticsearch endpoint itself, not "
            f"Kibana or a proxy's login page.",
            status_code=resp.status_code,
        )
    columns = [str(c["name"]) for c in payload["columns"]]
    rows = [dict(zip(columns, values)) for values in payload.get("values") or []]
    return EsqlResult(
        columns=columns,
        rows=rows,
        warnings=warnings_from(resp.headers.get("Warning")),
        is_partial=bool(payload.get("is_partial")),
    )


def warnings_from(header: Optional[str]) -> list[str]:
    """The text of each `Warning` header. requests joins repeated headers with commas,
    and a warning's text can hold commas too, so the quoted parts are what is read."""
    if not header:
        return []
    return [m.group(1).replace('\\"', '"') for m in _WARNING_TEXT.finditer(header)]


def _error_of(resp: requests.Response) -> tuple[str, str]:
    try:
        body = resp.json()
    except ValueError:
        return "", ""
    error = body.get("error") if isinstance(body, dict) else None
    if not error:
        return "", ""
    if isinstance(error, str):
        return "", error
    return str(error.get("type") or ""), str(error.get("reason") or "")


def _reason_suffix(kind: str, reason: str) -> str:
    if not reason:
        return ""
    return f": {kind}: {reason}" if kind else f": {reason}"


def _hint(status: int, reason: str) -> str:
    if status == 401:
        return (
            ". The API key was rejected: it may be expired or invalidated, or not an "
            "Elasticsearch API key (an Elastic Cloud organization key cannot query a "
            "cluster). Paste the 'encoded' value."
        )
    if status == 403:
        return ". The API key cannot run this query: it needs 'read' on every index it names."
    if status == 400 and "Unknown index" in reason:
        # Elasticsearch answers a key that may not read an index exactly as it answers
        # an index that does not exist, so both causes have to be named.
        return (
            ". Either no index matches that name, or the API key lacks 'read' on it -- "
            "Elasticsearch reports both the same way."
        )
    if "no handler found" in reason:
        return (
            ". This cluster may predate ES|QL, which needs Elasticsearch 8.14 or later."
        )
    return ""
