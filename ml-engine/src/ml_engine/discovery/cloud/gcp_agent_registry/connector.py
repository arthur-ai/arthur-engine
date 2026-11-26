"""Google Cloud Agent Registry's side of a DISCOVER_AGENTS scan: its MCP servers.

A STANDALONE-ONLY SOURCE. It reports MCP servers and no agents, and the Platform has
nowhere to put a server, so it has no Platform vendor.

ONE PROJECT PER SOURCE, EVERY LOCATION. The registry keeps servers per location and a
list does not span them, so the scan lists the project's locations and reads each, or
only those the source's `locations` names. `global` is always read: it is where Google
registers its own MCP servers for the APIs the project has enabled. An inventory, not a
log, so the lookback is not applied.

THE RECORD. Each registered server is one `McpServerRecord`, `registered`. `external_id`
is the server's resource name, verbatim: `projects/{project}/locations/{location}/
mcpServers/{id}`. `tools` are the tools the registry lists on it. Nothing in the list
says who calls a server, so there is no `used_by`.

WHAT IS NOT HERE. A server nobody registered: the registry holds Google's own servers,
workloads on runtimes that register themselves, and what someone added by hand. Nor
does the list say whether IAM lets anyone call a server it holds.

A REFUSED LOCATION IS A WARNING, NOT A FAILED SCAN. Each location is read on its own. A
refused credential ends the scan, and so does a scan in which every location was
refused, which would otherwise read as a project with no MCP servers; the Agent Registry
API not being enabled on the project is that case.

CREDENTIALS are `discovery.gcp_credentials`', under this vendor's own opt-in for the
engine's identity.
"""

import logging
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable, ClassVar, Iterator, Mapping, Optional, Sequence

import google.auth
import requests
from arthur_client.api_bindings import DiscoverySourceConfigSpec
from arthur_common.models.agent_discovery_schemas import DiscoveryOutputRecord
from arthur_common.models.agent_governance_schemas import Tool
from google.auth.credentials import Credentials
from google.auth.exceptions import DefaultCredentialsError
from google.auth.transport.requests import AuthorizedSession

from discovery.cloud.gcp_agent_registry.client import (
    CLOUD_PLATFORM_READONLY_SCOPE,
    GLOBAL_LOCATION,
    AgentRegistryClient,
    AgentRegistryError,
)
from discovery.endpoint.scope import parse_group_names
from discovery.gcp_credentials import (
    GCP_PROJECT_ID,
    SERVICE_ACCOUNT_KEY_FIELD,
    service_account_credentials,
)
from job_executors.discovery_scan import (
    DiscoveryConfigurationError,
    McpServerDetection,
    McpServerRecord,
)

VENDOR = "gcp_agent_registry"

PROJECT_ID_FIELD = "project_id"
LOCATIONS_FIELD = "locations"

# Opt-in for Application Default Credentials when a source has no key.
ALLOW_ADC_ENV_VAR = "ARTHUR_ENGINE_GCP_AGENT_REGISTRY_ALLOW_ADC"

# Records per published batch.
BATCH_SIZE = 100

_SOURCE = "Agent Registry source"
_LOCATION = re.compile(r"^[a-z][a-z0-9-]{0,62}$")
_SERVER_NAME = re.compile(r"^projects/[^/]+/locations/[^/]+/mcpServers/[^/]+$")
# RFC 3339 with more fractional digits than `datetime.fromisoformat` reads.
_EXTRA_FRACTION = re.compile(r"(\.\d{6})\d+")
# What a location the account cannot read, or the registry does not run in, answers.
_REFUSED_LOCATION = (403, 404)

SessionFactory = Callable[[Optional[Credentials], Sequence[str]], requests.Session]


@dataclass(frozen=True)
class AgentRegistrySettings:
    project_id: str
    # Empty means every location the project lists.
    locations: tuple[str, ...] = ()


def authorized_session(
    credentials: Optional[Credentials],
    scopes: Sequence[str],
) -> requests.Session:
    """A requests session that signs every call, refreshing its token as it goes.

    None is the engine's Application Default Credentials, which the caller has already
    checked the engine opted in to.
    """
    if credentials is None:
        try:
            credentials, _ = google.auth.default(scopes=list(scopes))
        except DefaultCredentialsError as e:
            raise DiscoveryConfigurationError(
                f"{_SOURCE} has no '{SERVICE_ACCOUNT_KEY_FIELD}', and this engine has "
                f"no Application Default Credentials to use instead: {e}",
            ) from None
    return AuthorizedSession(credentials)  # type: ignore[no-untyped-call]


class GcpAgentRegistryConnector:
    """Implements `job_executors.discovery_scan.DiscoverySourceConnector` and
    `AcceptsStopCheck`.

    Holds one scan's stop check, which is safe only because a connector is built fresh
    for every scan -- see `DiscoveryConnectorFactory`.
    """

    SENSITIVE_FIELDS: ClassVar[frozenset[str]] = frozenset({SERVICE_ACCOUNT_KEY_FIELD})

    def __init__(
        self,
        session_for: SessionFactory = authorized_session,
        sleep: Optional[Callable[[float], None]] = None,
    ) -> None:
        self._session_for = session_for
        self._sleep = sleep
        self._should_stop: Callable[[], bool] = lambda: False

    def stop_when(self, should_stop: Callable[[], bool]) -> None:
        """Asked before every request to Google."""
        self._should_stop = should_stop

    def scan(
        self,
        config: DiscoverySourceConfigSpec,
        lookback_hours: int,
        credentials: Mapping[str, Optional[str]],
        source_fields: Mapping[str, str],
        logger: logging.Logger,
    ) -> Iterator[Sequence[DiscoveryOutputRecord]]:
        """Every MCP server registered in the source's project, in batches."""
        settings = settings_from(source_fields)
        google_credentials = service_account_credentials(
            credentials,
            source=_SOURCE,
            allow_adc_env_var=ALLOW_ADC_ENV_VAR,
            scopes=[CLOUD_PLATFORM_READONLY_SCOPE],
        )
        session = self._session_for(google_credentials, [CLOUD_PLATFORM_READONLY_SCOPE])
        client = AgentRegistryClient(
            session,
            logger,
            should_stop=self._should_stop,
            **({"sleep": self._sleep} if self._sleep else {}),
        )
        logger.info(
            "Agent Registry scan starting against project %s, %s, using %s. MCP "
            "servers are an inventory: the lookback is not applied.",
            settings.project_id,
            (
                f"location(s) {', '.join(settings.locations)} and {GLOBAL_LOCATION}"
                if settings.locations
                else "every location the project lists"
            ),
            (
                "the source's service account key"
                if google_credentials is not None
                else "Application Default Credentials"
            ),
        )

        locations = list(settings.locations) or list(
            client.locations(settings.project_id),
        )
        locations = list(dict.fromkeys([GLOBAL_LOCATION, *locations]))

        servers = skipped = read = 0
        refused: list[AgentRegistryError] = []
        batch: list[DiscoveryOutputRecord] = []
        for location in locations:
            if self._should_stop():
                logger.info("Agent Registry scan stopped early on request")
                break
            try:
                for listed in client.mcp_servers(settings.project_id, location):
                    record = record_for(listed, logger)
                    if record is None:
                        skipped += 1
                        continue
                    servers += 1
                    batch.append(record)
                    if len(batch) >= BATCH_SIZE:
                        yield batch
                        batch = []
            except AgentRegistryError as e:
                if e.status_code not in _REFUSED_LOCATION:
                    raise
                refused.append(e)
                logger.warning(
                    "Agent Registry location %s not read, the rest of the scan goes "
                    "on: %s",
                    location,
                    e,
                )
                continue
            read += 1
        if batch:
            yield batch

        logger.info(
            "Agent Registry scan found %s MCP server(s) in %s location(s) of %s; %s "
            "skipped; %s location(s) refused",
            servers,
            read,
            settings.project_id,
            skipped,
            len(refused),
        )
        if read == 0 and refused:
            # Every location was refused: not a project with no MCP servers.
            raise refused[0]


def settings_from(source_fields: Mapping[str, str]) -> AgentRegistrySettings:
    """The project and locations from the source's non-sensitive fields."""
    project_id = (source_fields.get(PROJECT_ID_FIELD) or "").strip()
    if not project_id:
        raise DiscoveryConfigurationError(
            f"{_SOURCE} is missing required field '{PROJECT_ID_FIELD}'. It is a "
            f"source field, not a secret.",
        )
    if not GCP_PROJECT_ID.match(project_id):
        raise DiscoveryConfigurationError(
            f"{_SOURCE}'s '{PROJECT_ID_FIELD}' {project_id!r} is not a project ID. "
            f"A project ID looks like my-project-123456; it is not the project's "
            f"name or number.",
        )
    locations = parse_group_names(source_fields.get(LOCATIONS_FIELD))
    bad = [name for name in locations if not _LOCATION.match(name)]
    if bad:
        raise DiscoveryConfigurationError(
            f"{_SOURCE}'s '{LOCATIONS_FIELD}' has value(s) that are not location "
            f"names: {', '.join(repr(name) for name in bad)}. A location looks like "
            f"global, us or europe-west1.",
        )
    return AgentRegistrySettings(project_id=project_id, locations=tuple(locations))


def record_for(
    server: Mapping[str, Any],
    logger: logging.Logger,
) -> Optional[McpServerRecord]:
    """One registered server's record, or None when it cannot be identified or dated."""
    name = server.get("name")
    if not isinstance(name, str) or not _SERVER_NAME.match(name):
        logger.warning(
            "Agent Registry returned an MCP server with an unrecognised resource "
            "name; skipped, because the name is its identity",
        )
        return None
    last_seen = _time(server.get("updateTime")) or _time(server.get("createTime"))
    if last_seen is None:
        logger.warning(
            "%s: Agent Registry reported neither an update nor a create time; "
            "skipped, because last_seen is required and inventing one would date the "
            "record to the scan",
            name,
        )
        return None
    tools = server.get("tools")
    tool_names = sorted(
        {
            tool["name"].strip()
            for tool in (tools if isinstance(tools, list) else [])
            if isinstance(tool, dict)
            and isinstance(tool.get("name"), str)
            and tool["name"].strip()
        },
    )
    return McpServerRecord(
        external_id=name,
        name=_text(server.get("displayName"))
        or _text(server.get("mcpServerId"))
        or name.rsplit("/", 1)[-1],
        last_seen=last_seen,
        tools=[Tool(name=t) for t in tool_names] or None,
        detection=McpServerDetection.REGISTERED,
    )


def _time(value: Any) -> Optional[datetime]:
    """A Google timestamp as aware UTC. They carry up to nine fractional digits."""
    if not isinstance(value, str) or not value.strip():
        return None
    text = _EXTRA_FRACTION.sub(r"\1", value.strip().replace("Z", "+00:00"))
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _text(value: Any) -> Optional[str]:
    if not isinstance(value, str):
        return None
    return value.strip() or None
