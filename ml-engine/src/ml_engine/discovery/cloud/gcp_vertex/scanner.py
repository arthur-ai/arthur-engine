"""GCP Vertex AI Agent Engine's side of a DISCOVER_AGENTS scan.

Lists the Agent Engines (Google's API still calls them reasoning engines) in one project
and region, and emits one record per engine. This replaces the discovery phase of GenAI
Engine's `global_agent_polling_service`, which did the same listing from the engine's
GOOGLE_CLOUD_PROJECT / GOOGLE_CLOUD_LOCATION startup variables; here the project and
region come from a Discovery Source instead, so one engine can scan several projects and
none needs a restart to change which.

THE RESOURCE NAME IS COPIED, NEVER REBUILT. The startup-variable poller mapped each task
it created to Google's `api_resource.name` verbatim as a SERVICE_NAME key -- a path that
carries the project NUMBER (`projects/123456789012/...`), not the project ID configured
here. GenAI Engine's resolver joins a record to an existing task by matching its
`service_names` against those keys, so every record carries that exact string as both
`external_id` and its one service name. Rebuilding it from `project_id` would produce
`projects/my-project/...`, match nothing, and mint a duplicate task for every agent a
customer already has.

CREDENTIALS. A source's `service_account_key` is a service account JSON key, read with
`service_account.Credentials.from_service_account_info` -- deliberately not
`google.auth.load_credentials_from_dict`, which also accepts external-account configs
that can name an executable or a file on this engine's disk. A source without a key uses
Application Default Credentials only when the engine opts in with
`ALLOW_ADC_ENV_VAR`; that is how a developer scans with their own `gcloud auth
application-default login`, and how a GKE data plane would use Workload Identity. With
the flag unset a keyless source fails with a reason naming the field, rather than quietly
scanning as whatever identity the engine pod happens to run under.
"""

import json
import logging
import os
from datetime import datetime
from typing import Any, Callable, Iterable, Iterator, Mapping, Optional, Sequence

import vertexai
from arthur_client.api_bindings import DiscoverySourceConfigSpec
from arthur_common.models.agent_discovery_schemas import DiscoveredAgentRecord
from arthur_common.models.agent_governance_schemas import (
    AgentObservations,
    CloudAgentCreationSource,
    RunsOn,
    SourceAddress,
)
from google.auth.credentials import Credentials
from google.oauth2 import service_account
from pydantic import BaseModel

VENDOR = "gcp_vertex"

PROJECT_ID_FIELD = "project_id"
LOCATION_FIELD = "location"
SERVICE_ACCOUNT_KEY_FIELD = "service_account_key"

# The startup-variable poller's default, kept so a source that leaves the region blank
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


# (settings, credentials or None for ADC) -> the SDK's AgentEngine objects. A seam so tests
# can hand in fakes without patching the SDK.
AgentEngineLister = Callable[[VertexSettings, Optional[Credentials]], Iterable[Any]]


def list_agent_engines(
    settings: VertexSettings,
    credentials: Optional[Credentials],
) -> Iterable[Any]:
    """The Agent Engines in one project and region, as the Vertex SDK returns them.

    The same call the startup-variable poller made, with credentials passed explicitly
    rather than taken from the process environment.
    """
    client = vertexai.Client(
        project=settings.project_id,
        location=settings.location,
        credentials=credentials,
    )
    engines: Iterable[Any] = client.agent_engines.list()
    return engines


class VertexAgentEngineScanner:
    """Implements `job_executors.discovery_scan.DiscoverySourceScanner`."""

    def __init__(self, lister: AgentEngineLister = list_agent_engines) -> None:
        self._lister = lister

    def scan(
        self,
        config: DiscoverySourceConfigSpec,
        lookback_hours: int,
        credentials: Mapping[str, Optional[str]],
        source_fields: Mapping[str, str],
        logger: logging.Logger,
    ) -> Iterator[Sequence[DiscoveredAgentRecord]]:
        """Every Agent Engine in the source's project and region, in batches.

        `lookback_hours` is not applied. The list API is an inventory, not a log: an
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
        for engine in self._lister(settings, google_credentials):
            listed += 1
            record = record_for(engine, settings, logger)
            if record is None:
                skipped += 1
                continue
            batch.append(record)
            if len(batch) >= BATCH_SIZE:
                yield batch
                batch = []
        if batch:
            yield batch

        logger.info(
            "Vertex AI Agent Engine scan listed %s engine(s) in %s/%s, %s skipped",
            listed,
            settings.project_id,
            settings.location,
            skipped,
        )


def settings_from(source_fields: Mapping[str, str]) -> VertexSettings:
    """The project and region from the source's non-sensitive fields."""
    project_id = (source_fields.get(PROJECT_ID_FIELD) or "").strip()
    if not project_id:
        raise ValueError(
            f"Vertex AI source is missing required field '{PROJECT_ID_FIELD}'. "
            f"It is a source field, not a secret.",
        )
    location = (source_fields.get(LOCATION_FIELD) or "").strip() or DEFAULT_LOCATION
    return VertexSettings(project_id=project_id, location=location)


def adc_allowed() -> bool:
    return os.getenv(ALLOW_ADC_ENV_VAR, "").strip().lower() in {"1", "true", "yes"}


def credentials_from(
    credentials: Mapping[str, Optional[str]],
    logger: logging.Logger,
) -> Optional[Credentials]:
    """The source's service account, or None to use Application Default Credentials.

    None is returned only when the engine has opted in to ADC; a keyless source on an
    engine that has not raises instead.

    A key that does not parse is reported without its content. The job logger scrubs the
    whole key string by exact match, but a JSON error quotes a fragment of the document,
    and a fragment is not what the scrub set holds.
    """
    raw = (credentials.get(SERVICE_ACCOUNT_KEY_FIELD) or "").strip()
    if not raw:
        if adc_allowed():
            return None
        raise ValueError(
            f"Vertex AI source has no '{SERVICE_ACCOUNT_KEY_FIELD}'. Paste a service "
            f"account JSON key into the source, or set {ALLOW_ADC_ENV_VAR}=true on this "
            f"engine to use its Application Default Credentials.",
        )

    try:
        info = json.loads(raw)
    except json.JSONDecodeError as e:
        raise ValueError(
            f"Vertex AI source's '{SERVICE_ACCOUNT_KEY_FIELD}' is not valid JSON "
            f"(line {e.lineno}, column {e.colno}). Paste the whole key file.",
        ) from None
    if not isinstance(info, dict) or info.get("type") != "service_account":
        raise ValueError(
            f"Vertex AI source's '{SERVICE_ACCOUNT_KEY_FIELD}' is not a service account "
            f'key: expected a JSON object with "type": "service_account".',
        )
    try:
        loaded: Credentials = service_account.Credentials.from_service_account_info(  # type: ignore[no-untyped-call]
            info,
            scopes=[CLOUD_PLATFORM_SCOPE],
        )
        return loaded
    except ValueError as e:
        # google-auth names the missing field, never the key material, so its message
        # is safe to carry; the chained exception is dropped in case a later version
        # is less careful.
        raise ValueError(
            f"Vertex AI source's '{SERVICE_ACCOUNT_KEY_FIELD}' could not be loaded: {e}",
        ) from None


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
        resource, "create_time", None
    )
    if last_seen is None:
        logger.warning(
            "%s: Vertex AI reported neither an update nor a create time; skipped, "
            "because last_seen is required and inventing one would date the finding to "
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
