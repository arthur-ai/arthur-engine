"""Reading a project's Cloud DNS and VPC flow logs, and its Cloud Run jobs.

Both logs are ordinary Cloud Logging entries, read with `entries.list` through the
source's service account. Reading them needs `roles/logging.viewer`; listing Cloud Run
jobs (to name the job behind an execution) needs `roles/run.viewer`, and is optional:
without it a record is named by the execution.
"""

from datetime import datetime, timezone
from typing import Any, Iterator, Optional

from google.auth.credentials import Credentials
from google.auth.transport.requests import AuthorizedSession

ENTRIES_LIST_URL = "https://logging.googleapis.com/v2/entries:list"
RUN_JOBS_URL = (
    "https://run.googleapis.com/v2/projects/{project}/locations/{region}/jobs"
)
PAGE_SIZE = 1000


class LoggingReadError(Exception):
    """Cloud Logging or Cloud Run refused or failed a read; carries the HTTP status."""

    def __init__(self, status_code: int, message: str) -> None:
        super().__init__(f"Google answered {status_code}: {message}")
        self.status_code = status_code


def dns_filter(project_id: str, since: datetime) -> str:
    """Cloud DNS lookups that got an answer. Lookups expanded with a search domain
    (`api.openai.com.c.<project>.internal.`) fail with NXDOMAIN and are left out."""
    return (
        f'logName="projects/{project_id}/logs/dns.googleapis.com%2Fdns_queries"'
        ' AND jsonPayload.responseCode="NOERROR"'
        f' AND timestamp>="{_utc(since)}"'
    )


def serverless_flow_filter(project_id: str, since: datetime) -> str:
    """Flow records sent by serverless workloads. A VM is named by its own DNS lookups,
    and a GKE pod's egress carries only its node, so neither is read here."""
    return (
        f'logName="projects/{project_id}/logs/compute.googleapis.com%2Fvpc_flows"'
        " AND jsonPayload.src_serverless_details:*"
        f' AND timestamp>="{_utc(since)}"'
    )


def _utc(when: datetime) -> str:
    return when.astimezone(timezone.utc).isoformat()


def session_for(credentials: Credentials) -> AuthorizedSession:
    return AuthorizedSession(credentials)  # type: ignore[no-untyped-call]


def read_entries(
    session: AuthorizedSession,
    project_id: str,
    log_filter: str,
) -> Iterator[dict[str, Any]]:
    """`entries.list`, oldest first, paged."""
    body: dict[str, Any] = {
        "resourceNames": [f"projects/{project_id}"],
        "filter": log_filter,
        "orderBy": "timestamp asc",
        "pageSize": PAGE_SIZE,
    }
    while True:
        response = session.post(ENTRIES_LIST_URL, json=body, timeout=(10, 60))
        if response.status_code >= 400:
            raise LoggingReadError(response.status_code, _message(response))
        page = response.json()
        yield from page.get("entries") or []
        token = page.get("nextPageToken")
        if not token:
            return
        body["pageToken"] = token


def list_run_jobs(session: AuthorizedSession, project_id: str, region: str) -> set[str]:
    """The Cloud Run job names in one region of the project."""
    names: set[str] = set()
    params: dict[str, Any] = {"pageSize": 500}
    url = RUN_JOBS_URL.format(project=project_id, region=region)
    while True:
        response = session.get(url, params=params, timeout=(10, 60))
        if response.status_code >= 400:
            raise LoggingReadError(response.status_code, _message(response))
        page = response.json()
        names.update(j["name"].rsplit("/", 1)[-1] for j in page.get("jobs") or [])
        token = page.get("nextPageToken")
        if not token:
            return names
        params["pageToken"] = token


def _message(response: Any) -> str:
    try:
        message: Optional[str] = response.json().get("error", {}).get("message")
    except ValueError:
        message = None
    return str(message or response.reason or "")
