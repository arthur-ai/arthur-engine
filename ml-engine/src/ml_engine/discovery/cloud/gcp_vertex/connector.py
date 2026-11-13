"""GCP Vertex AI Agent Engine's side of a DISCOVER_AGENTS scan.

Lists the Agent Engines (Google's API still calls them reasoning engines) in one project
and region, and emits one record per engine. This replaces the discovery phase of GenAI
Engine's `global_agent_polling_service`, which did the same listing from the engine's
GOOGLE_CLOUD_PROJECT / GOOGLE_CLOUD_LOCATION startup variables; here the project and
region come from a discovery source instead, so one engine can scan several projects and
none needs a restart to change which.

THE RESOURCE NAME IS COPIED, NEVER REBUILT. The legacy Vertex poller mapped each task
it created to Google's `api_resource.name` verbatim as a SERVICE_NAME key -- a path that
carries the project NUMBER (`projects/123456789012/...`), not the project ID configured
here. GenAI Engine's resolver joins a record to an existing task by matching its
`service_names` against those keys, so every record carries that exact string as both
`external_id` and its one service name. Rebuilding it from `project_id` would produce
`projects/my-project/...`, match nothing, and mint a duplicate task for every agent a
customer already has.

CREDENTIALS. A source's `service_account_key` is a service account JSON key, loaded by
`discovery.gcp_credentials`, which Compute Engine shares. A source without a key uses
Application Default Credentials only when the engine opts in with
`ALLOW_ADC_ENV_VAR`; that is how a developer scans with their own `gcloud auth
application-default login`, and how an engine on GKE would use Workload Identity.

WHAT GOOGLE ANSWERED. `discovery_scan.failure_code` tells a refused credential from a
denied project by a `status_code` attribute on the exception, and leaves it to the
connector to put one there. Google's SDK raises its own `APIError`, which carries the
status on `.code`, so without a translation a key with no access to the project is
reported as `provider_error` -- the code that sends an admin to Google's status page
rather than to the project's IAM bindings. The attribute is set on the SDK's exception
and that same exception is re-raised, never wrapped: `run_source_scan` redacts and
re-raises what it catches unchanged in type, and a wrapper would trade the type the job
log names for one that says less.
"""

import logging
from datetime import datetime, timezone
from typing import (
    Any,
    Callable,
    ClassVar,
    Iterable,
    Iterator,
    Mapping,
    Optional,
    Sequence,
)

import agentplatform
from arthur_client.api_bindings import DiscoverySourceConfigSpec
from arthur_common.models.agent_discovery_schemas import DiscoveredAgentRecord
from arthur_common.models.agent_governance_schemas import (
    AgentObservations,
    CloudAgentCreationSource,
    RunsOn,
    SourceAddress,
)
from google.auth.credentials import Credentials
from google.auth.exceptions import RefreshError
from google.genai import errors as genai_errors
from pydantic import BaseModel

from discovery.cloud.gcp_vertex.audit import EntryReader, audit_records, read_entries
from discovery.gcp_credentials import (
    SERVICE_ACCOUNT_KEY_FIELD,
    mark_refused_credential,
    service_account_credentials,
)

VENDOR = "gcp_vertex"

PROJECT_ID_FIELD = "project_id"
LOCATION_FIELD = "location"
# "true" to also read the project's Vertex AI Data Access audit log for the service
# accounts that call models directly. See `discovery.cloud.gcp_vertex.audit`.
READ_AUDIT_LOGS_FIELD = "read_audit_logs"

# The legacy Vertex poller's default, kept so a source that leaves the region blank
# scans what that poller scanned.
DEFAULT_LOCATION = "us-central1"

# Opt-in for Application Default Credentials when a source has no key. Off unless set to
# a true value; see the module docstring.
ALLOW_ADC_ENV_VAR = "ARTHUR_ENGINE_GCP_VERTEX_ALLOW_ADC"

CLOUD_PLATFORM_SCOPE = "https://www.googleapis.com/auth/cloud-platform"

# Records per published batch. The list API pages internally, so this bounds how much a
# failure part-way through the listing can cost rather than mirroring Google's pages.
BATCH_SIZE = 100


class VertexSettings(BaseModel):
    project_id: str
    location: str
    read_audit_logs: bool = False


# (settings, credentials or None for ADC) -> the SDK's AgentEngine objects. A seam so tests
# can hand in fakes without patching the SDK.
AgentEngineLister = Callable[[VertexSettings, Optional[Credentials]], Iterable[Any]]


def list_agent_engines(
    settings: VertexSettings,
    credentials: Optional[Credentials],
) -> Iterable[Any]:
    """The Agent Engines in one project and region, as Google's SDK returns them.

    `agentplatform.Client().runtimes`, which google-cloud-aiplatform 2.x ships in place
    of the deprecated `vertexai.Client().agent_engines`. It lists the same
    `reasoningEngines` resources and each item carries the same `api_resource`
    (name, display_name, create_time, update_time), so nothing downstream changes;
    checked live against a project with two deployed engines, where both calls return
    the same two. Credentials are passed explicitly rather than taken from the
    process environment.
    """
    client = agentplatform.Client(
        project=settings.project_id,
        location=settings.location,
        credentials=credentials,
    )
    engines: Iterable[Any] = client.runtimes.list()
    return engines


class VertexAgentEngineConnector:
    """Implements `job_executors.discovery_scan.DiscoverySourceConnector`."""

    SENSITIVE_FIELDS: ClassVar[frozenset[str]] = frozenset({SERVICE_ACCOUNT_KEY_FIELD})

    def __init__(
        self,
        lister: AgentEngineLister = list_agent_engines,
        audit_reader: EntryReader = read_entries,
        clock: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
    ) -> None:
        self._lister = lister
        self._audit_reader = audit_reader
        self._clock = clock

    def scan(
        self,
        config: DiscoverySourceConfigSpec,
        lookback_hours: int,
        credentials: Mapping[str, Optional[str]],
        source_fields: Mapping[str, str],
        logger: logging.Logger,
    ) -> Iterator[Sequence[DiscoveredAgentRecord]]:
        """Every Agent Engine in the source's project and region, in batches.

        `lookback_hours` is not applied to the listing. The list API is an inventory, not a log: an
        engine deployed a year ago and never updated is still deployed, and filtering
        on `update_time` would make it vanish from every scan after the first.
        """
        settings = settings_from(source_fields)
        google_credentials = credentials_from(credentials, logger)

        logger.info(
            "Vertex AI Agent Engine scan starting against project %s, location %s, "
            "using %s",
            settings.project_id,
            settings.location,
            (
                "the source's service account key"
                if google_credentials is not None
                else "Application Default Credentials"
            ),
        )

        listed = skipped = 0
        batch: list[DiscoveredAgentRecord] = []
        for engine in with_vendor_status(self._lister, settings, google_credentials):
            listed += 1
            record = record_for(engine, settings, logger)
            if record is None:
                skipped += 1
                continue
            batch.append(record)
            if len(batch) >= BATCH_SIZE:
                yield batch
                batch = []
        logger.info(
            "Vertex AI Agent Engine scan listed %s engine(s) in %s/%s, %s skipped",
            listed,
            settings.project_id,
            settings.location,
            skipped,
        )

        # Unlike the listing, the audit log is a log: the lookback applies.
        if settings.read_audit_logs:
            batch.extend(
                audit_records(
                    self._audit_reader,
                    settings.project_id,
                    google_credentials,
                    lookback_hours,
                    self._clock(),
                    VENDOR,
                    logger,
                )
            )
        for offset in range(0, len(batch), BATCH_SIZE):
            yield batch[offset : offset + BATCH_SIZE]


def with_vendor_status(
    lister: AgentEngineLister,
    settings: VertexSettings,
    credentials: Optional[Credentials],
) -> Iterator[Any]:
    """The lister's engines, with a failure's status where `failure_code` reads it.

    Wraps the call as well as the iteration. Today's `runtimes.list()` is a generator
    and asks Google nothing until it is read, but a lister that fetched its first page
    eagerly would otherwise fail outside the translation. See the module docstring for
    why the exception is annotated rather than replaced.

    A refused credential is 401 whatever the wire said; `discovery.gcp_credentials`
    says which `RefreshError`s count.
    """
    try:
        yield from lister(settings, credentials)
    except genai_errors.APIError as e:
        setattr(e, "status_code", e.code)
        raise
    except RefreshError as e:
        mark_refused_credential(e)
        raise


def settings_from(source_fields: Mapping[str, str]) -> VertexSettings:
    """The project and region from the source's non-sensitive fields."""
    project_id = (source_fields.get(PROJECT_ID_FIELD) or "").strip()
    if not project_id:
        raise ValueError(
            f"Vertex AI source is missing required field '{PROJECT_ID_FIELD}'. "
            f"It is a source field, not a secret.",
        )
    location = (source_fields.get(LOCATION_FIELD) or "").strip() or DEFAULT_LOCATION
    read_audit_logs = (source_fields.get(READ_AUDIT_LOGS_FIELD) or "").strip().lower()
    return VertexSettings(
        project_id=project_id,
        location=location,
        read_audit_logs=read_audit_logs in {"true", "1", "yes"},
    )


def credentials_from(
    credentials: Mapping[str, Optional[str]],
    logger: logging.Logger,
) -> Optional[Credentials]:
    """The source's service account, or None to use Application Default Credentials.

    None is returned only when the engine has opted in to ADC; a keyless source on an
    engine that has not raises instead.
    """
    return service_account_credentials(
        credentials,
        source="Vertex AI source",
        allow_adc_env_var=ALLOW_ADC_ENV_VAR,
        scopes=[CLOUD_PLATFORM_SCOPE],
    )


def parse_resource_name(name: str) -> Optional[tuple[str, str, str]]:
    """(project, location, engine id) from `projects/P/locations/L/reasoningEngines/E`."""
    parts = name.split("/")
    if (
        len(parts) != 6
        or parts[0] != "projects"
        or parts[2] != "locations"
        or parts[4] != "reasoningEngines"
        or not all(p.strip() for p in (parts[1], parts[3], parts[5]))
    ):
        return None
    return parts[1], parts[3], parts[5]


def record_for(
    engine: Any,
    settings: VertexSettings,
    logger: logging.Logger,
) -> Optional[DiscoveredAgentRecord]:
    """One engine's record, or None when the API returned one that cannot be addressed."""
    resource = getattr(engine, "api_resource", None)
    name = getattr(resource, "name", None) or ""
    parsed = parse_resource_name(name)
    if parsed is None:
        logger.warning(
            "Vertex AI returned an Agent Engine with an unrecognised resource name %r; "
            "skipped, because the name is the identity every existing task is mapped by",
            name,
        )
        return None
    _, region, engine_id = parsed

    last_seen: Optional[datetime] = getattr(resource, "update_time", None) or getattr(
        resource,
        "create_time",
        None,
    )
    if last_seen is None:
        logger.warning(
            "%s: Vertex AI reported neither an update nor a create time; skipped, "
            "because last_seen is required and inventing one would date the record to "
            "the scan",
            name,
        )
        return None

    return DiscoveredAgentRecord(
        # Verbatim, both times: see the module docstring.
        external_id=name,
        name=getattr(resource, "display_name", None) or engine_id,
        last_seen=last_seen,
        runs_on=RunsOn.GCP,
        creation_source=CloudAgentCreationSource(
            vendor=VENDOR,
            # The configured project ID rather than the number in `name`: it is what the
            # customer typed and recognises, and what the deprecated GCP creation source
            # has always put in the same place.
            address=SourceAddress(
                instance=settings.project_id,
                scope=region,
                resource_id=engine_id,
            ),
            observations=AgentObservations(service_names=[name]),
        ),
    )
