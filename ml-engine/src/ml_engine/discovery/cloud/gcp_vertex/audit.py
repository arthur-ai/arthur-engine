"""Who calls Vertex AI models in a project, read off its Data Access audit log.

The Agent Engine listing finds agents deployed ON Vertex. It cannot see a workload that
calls a Gemini model directly -- a Compute Engine VM, a Cloud Run job, a GKE workload
with its own service account. Google records each such call in the project's Data
Access audit log for `aiplatform.googleapis.com`: the caller (`principalEmail`, a
service account for a workload), the model (`resourceName`), and the client's user
agent. That caller is a stable identity, unlike an address, so it is what a record is
keyed by.

ONE RECORD PER (SERVICE ACCOUNT, REGION). The region is part of a cloud record's
identity (`CloudAgentCreationSource` requires it), and the model path names the region
it was called in. A record lists every model that caller used there.

WHAT IS NOT A RECORD.
- Calls by the Agent Engine service agent (`service-<number>@gcp-sa-aiplatform-re`).
  That is the identity every Agent Engine runs as, so the engine listing has already
  reported those agents, one record each; a second record for the shared account would
  merge all of them into one.
- Calls by a person (`user@example.com`). A person is not a workload, and naming them
  would put personal data in an agent inventory. They are counted, never named.
- Anything but a model call. The log also holds list and get calls (an Agent Engine
  listing writes one per scan), so the filter names the prediction methods and Google
  applies it before anything is read.

THE LOG MUST BE ON. Data Access audit logs are off by default for every service but
BigQuery, and reading them needs `roles/logging.privateLogViewer`: Logs Viewer cannot.
A refused read is reported in the scan log and leaves the engine listing untouched.

KNOWN LIMIT. A service account shared by several workloads (the default compute account
is the usual one) is one record for all of them; the audit log cannot tell them apart.
A call Vertex refused writes no Data Access entry, so it is not seen.
"""

import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Iterable, Iterator, Optional

import google.auth
import requests
from arthur_common.models.agent_discovery_schemas import DiscoveredAgentRecord
from arthur_common.models.agent_governance_schemas import (
    CloudAgentCreationSource,
    LLMModel,
    RunsOn,
    SourceAddress,
)
from google.auth.credentials import Credentials
from google.auth.exceptions import GoogleAuthError
from google.auth.transport.requests import AuthorizedSession

ENTRIES_LIST_URL = "https://logging.googleapis.com/v2/entries:list"

# The prediction methods: a call that runs a model. CountTokens and ComputeTokens are
# PredictionService methods too, but run nothing, so they are left out.
MODEL_CALL_METHODS = (
    "GenerateContent",
    "StreamGenerateContent",
    "Predict",
    "RawPredict",
    "StreamRawPredict",
    "DirectPredict",
    "ServerStreamingPredict",
)

# A lookback of zero reads this far back rather than the whole retention, so one scan
# cannot page through a year of audit log.
DEFAULT_LOOKBACK = timedelta(days=30)

# Entries read per scan at most; a scan that hits it says so.
MAX_ENTRIES = 50_000
PAGE_SIZE = 1000

RESOURCE_KIND = "service_account"

_AGENT_ENGINE_SERVICE_AGENT = re.compile(
    r"^service-\d+@gcp-sa-aiplatform-re\.iam\.gserviceaccount\.com$"
)
_SERVICE_ACCOUNT = re.compile(r"^[^@\s]+@[^@\s]+\.gserviceaccount\.com$")
_MODEL_PATH = re.compile(
    r"^projects/[^/]+/locations/(?P<location>[^/]+)/"
    r"(?:publishers/[^/]+/models|endpoints)/(?P<model>[^/:]+)"
)
_FRAMEWORK = re.compile(r"\b(google-adk|langchain|langgraph|crewai|llama[-_]index)/")


def audit_filter(project_id: str, since: datetime) -> str:
    """The Cloud Logging filter for model calls in one project since `since`."""
    methods = " OR ".join(f'"PredictionService.{m}"' for m in MODEL_CALL_METHODS)
    return (
        f'logName="projects/{project_id}/logs/cloudaudit.googleapis.com%2Fdata_access"'
        ' AND protoPayload.serviceName="aiplatform.googleapis.com"'
        f" AND protoPayload.methodName:({methods})"
        f' AND timestamp>="{since.astimezone(timezone.utc).isoformat()}"'
    )


# (project, filter, credentials or None) -> raw log entries, newest first. A seam so
# tests can hand in captured entries.
EntryReader = Callable[[str, str, Optional[Credentials]], Iterable[dict[str, Any]]]


def read_entries(
    project_id: str,
    log_filter: str,
    credentials: Optional[Credentials],
) -> Iterator[dict[str, Any]]:
    """`entries.list`, paged, through the source's credentials (or ADC)."""
    if credentials is None:
        credentials, _ = google.auth.default(
            scopes=["https://www.googleapis.com/auth/cloud-platform"]
        )
    session = AuthorizedSession(credentials)  # type: ignore[no-untyped-call]
    body: dict[str, Any] = {
        "resourceNames": [f"projects/{project_id}"],
        "filter": log_filter,
        "orderBy": "timestamp desc",
        "pageSize": PAGE_SIZE,
    }
    seen_tokens: set[str] = set()
    while True:
        response = session.post(ENTRIES_LIST_URL, json=body, timeout=(10, 60))
        if response.status_code >= 400:
            raise AuditReadError(response.status_code, _error_message(response))
        page = response.json()
        yield from page.get("entries") or []
        token = page.get("nextPageToken")
        if not token:
            return
        # A token handed back twice would page forever.
        if token in seen_tokens:
            raise AuditReadError(200, "Cloud Logging repeated a page token")
        seen_tokens.add(token)
        body["pageToken"] = token


def _error_message(response: Any) -> str:
    try:
        message = response.json().get("error", {}).get("message")
    except ValueError:
        message = None
    return str(message or response.reason or "")


class AuditReadError(Exception):
    """Cloud Logging refused or failed the read; carries the HTTP status."""

    def __init__(self, status_code: int, message: str) -> None:
        super().__init__(f"Cloud Logging answered {status_code}: {message}")
        self.status_code = status_code


@dataclass
class Caller:
    """Every model call one service account made in one region."""

    email: str
    location: str
    models: set[str] = field(default_factory=set)
    frameworks: set[str] = field(default_factory=set)
    calls: int = 0
    last_seen: Optional[datetime] = None


@dataclass
class AuditCounts:
    read: int = 0
    calls: int = 0
    agent_engine_calls: int = 0
    user_calls: int = 0
    unparsed: int = 0
    capped: bool = False


def fold(
    entries: Iterable[dict[str, Any]],
    counts: AuditCounts,
) -> dict[tuple[str, str], Caller]:
    """Model calls folded into one Caller per (service account, region)."""
    callers: dict[tuple[str, str], Caller] = {}
    for entry in entries:
        if counts.read >= MAX_ENTRIES:
            counts.capped = True
            break
        counts.read += 1
        payload = entry.get("protoPayload") or {}
        email = (
            (payload.get("authenticationInfo") or {}).get("principalEmail") or ""
        ).strip()
        model = _MODEL_PATH.match(payload.get("resourceName") or "")
        when = _timestamp(entry.get("timestamp"))
        if not email or model is None or when is None:
            counts.unparsed += 1
            continue
        if _AGENT_ENGINE_SERVICE_AGENT.match(email):
            counts.agent_engine_calls += 1
            continue
        if not _SERVICE_ACCOUNT.match(email):
            counts.user_calls += 1
            continue
        counts.calls += 1
        key = (email, model.group("location"))
        caller = callers.setdefault(key, Caller(email, model.group("location")))
        caller.calls += 1
        caller.models.add(model.group("model"))
        agent = (payload.get("requestMetadata") or {}).get(
            "callerSuppliedUserAgent"
        ) or ""
        caller.frameworks.update(m.group(1) for m in _FRAMEWORK.finditer(agent))
        caller.last_seen = max(filter(None, (caller.last_seen, when)))
    return callers


def _timestamp(raw: Optional[str]) -> Optional[datetime]:
    if not raw:
        return None
    text = raw.replace("Z", "+00:00")
    # Cloud Logging gives nanoseconds; Python parses at most microseconds.
    text = re.sub(r"(\.\d{6})\d+", r"\1", text)
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        return None


def record_for(caller: Caller, project_id: str, vendor: str) -> DiscoveredAgentRecord:
    """One caller's record: a cloud record keyed by the service account."""
    assert caller.last_seen is not None
    models = sorted(caller.models)
    account = caller.email.split("@", 1)[0]
    return DiscoveredAgentRecord(
        external_id=(
            f"projects/{project_id}/locations/{caller.location}"
            f"/serviceAccounts/{caller.email}"
        ),
        name=f"{account} calling {', '.join(models)}",
        last_seen=caller.last_seen,
        llm_models=[LLMModel(name=m) for m in models],
        runs_on=RunsOn.GCP,
        creation_source=CloudAgentCreationSource(
            vendor=vendor,
            address=SourceAddress(
                instance=project_id,
                scope=caller.location,
                resource_kind=RESOURCE_KIND,
                resource_id=caller.email,
            ),
        ),
    )


def since_for(lookback_hours: int, now: datetime) -> datetime:
    """The oldest entry a scan reads: its lookback, or DEFAULT_LOOKBACK for zero."""
    if lookback_hours > 0:
        return now - timedelta(hours=lookback_hours)
    return now - DEFAULT_LOOKBACK


def audit_records(
    reader: EntryReader,
    project_id: str,
    credentials: Optional[Credentials],
    lookback_hours: int,
    now: datetime,
    vendor: str,
    logger: logging.Logger,
) -> list[DiscoveredAgentRecord]:
    """The project's model callers as records; a refused read is logged, not raised."""
    log_filter = audit_filter(project_id, since_for(lookback_hours, now))
    counts = AuditCounts()
    try:
        callers = fold(reader(project_id, log_filter, credentials), counts)
    except AuditReadError as e:
        logger.warning(
            "Vertex AI audit log not read for project %s (HTTP %s). Reading Data "
            "Access audit logs needs roles/logging.privateLogViewer on the project; "
            "the Agent Engine listing is unaffected.",
            project_id,
            e.status_code,
        )
        return []
    except (requests.RequestException, GoogleAuthError, ValueError) as e:
        # A network failure, a credential that cannot mint a token, or a body that is
        # not JSON: the audit read is the optional half of the scan, so it is reported
        # and the listing's records still go out.
        logger.warning(
            "Vertex AI audit log not read for project %s (%s); the Agent Engine "
            "listing is unaffected.",
            project_id,
            type(e).__name__,
        )
        return []
    logger.info(
        "Vertex AI audit log for %s: %s entr%s read, %s model call(s) from %s "
        "service account(s); %s by the Agent Engine service agent and %s by people "
        "skipped, %s unreadable",
        project_id,
        counts.read,
        "y" if counts.read == 1 else "ies",
        counts.calls,
        len({email for email, _ in callers}),
        counts.agent_engine_calls,
        counts.user_calls,
        counts.unparsed,
    )
    if counts.capped:
        logger.warning(
            "Vertex AI audit log for %s: stopped at %s entries; shorten the lookback "
            "to read the rest",
            project_id,
            MAX_ENTRIES,
        )
    if counts.read == 0:
        logger.info(
            "Vertex AI audit log for %s had no model calls in the window. If agents "
            "call Gemini here, check that Data Access audit logs are enabled for "
            "aiplatform.googleapis.com",
            project_id,
        )
    return [record_for(c, project_id, vendor) for c in callers.values()]
