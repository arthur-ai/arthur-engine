"""Azure API Management's side of a DISCOVER_AGENTS scan: its MCP servers.

A STANDALONE-ONLY SOURCE. It reports MCP servers and no agents, and the Platform has
nowhere to put a server, so it has no Platform vendor.

ONE SUBSCRIPTION PER SOURCE. Every API Management service in it is listed, then every
API of each, and an API whose type is `mcp` is one `McpServerRecord`, `registered`. An
inventory, not a log, so the lookback is not applied.

THE RECORD. `external_id` is the API's Resource Manager id, lower-cased, because
Resource Manager ids are not case-sensitive and two spellings of one must not be two
servers. `tools` are the server's tools where API Management built it from a REST API;
a server it passes through to has its tools upstream, where this scan does not go, and
so has none on its record. Nothing here says who calls a server, so there is no
`used_by`.

A REVISION IS NOT A SERVER. An API's other revisions are listed beside its current one
and are skipped.

A REFUSED SERVICE IS A WARNING, NOT A FAILED SCAN. A principal that can list the
subscription's services but not one service's APIs loses that service and keeps the
rest. A refused credential ends the scan, and so does a scan in which every service was
refused, which would otherwise read as a subscription with no MCP servers. A server
whose tools cannot be read is still a record, without them.

CREDENTIALS are `discovery.azure_credentials`', under this vendor's own opt-in for the
engine's identity.
"""

import logging
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable, ClassVar, Iterator, Mapping, Optional, Sequence

from arthur_client.api_bindings import DiscoverySourceConfigSpec
from arthur_common.models.agent_discovery_schemas import DiscoveryOutputRecord
from arthur_common.models.agent_governance_schemas import RunsOn, Tool
from azure.core.credentials import TokenCredential

from discovery.azure_credentials import (
    CLIENT_ID_FIELD,
    SENSITIVE_FIELDS,
    TENANT_ID_FIELD,
    describe_credential,
    service_principal_credential,
    vendor_status,
)
from discovery.cloud.azure_api_management.client import (
    MCP_API_TYPE,
    ApiManagementClient,
    ArmError,
    service_path,
)
from job_executors.discovery_scan import (
    DiscoveryConfigurationError,
    McpServerDetection,
    McpServerRecord,
)

VENDOR = "azure_api_management"

SUBSCRIPTION_ID_FIELD = "subscription_id"

# Opt-in for DefaultAzureCredential when a source has no service principal.
ALLOW_DEFAULT_CREDENTIAL_ENV_VAR = (
    "ARTHUR_ENGINE_AZURE_API_MANAGEMENT_ALLOW_DEFAULT_CREDENTIAL"
)

# Records per published batch.
BATCH_SIZE = 100

_SOURCE = "Azure API Management source"
_SUBSCRIPTION_ID = re.compile(r"^[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}$")
# What a principal without access to one service, or to a server's tools, is answered.
_REFUSED_PART = (403, 404)

# (credential, logger, should_stop) -> the client for one scan.
ClientFactory = Callable[
    [TokenCredential, logging.Logger, Callable[[], bool]],
    ApiManagementClient,
]


@dataclass(frozen=True)
class ApiManagementSettings:
    subscription_id: str
    tenant_id: Optional[str] = None
    client_id: Optional[str] = None


@dataclass
class _Counts:
    services: int = 0
    refused_services: int = 0
    apis: int = 0
    servers: int = 0
    revisions: int = 0
    skipped: int = 0
    tools_not_read: int = 0


def _default_client(
    credential: TokenCredential,
    logger: logging.Logger,
    should_stop: Callable[[], bool],
) -> ApiManagementClient:
    return ApiManagementClient(credential, logger, should_stop=should_stop)


class AzureApiManagementConnector:
    """Implements `job_executors.discovery_scan.DiscoverySourceConnector` and
    `AcceptsStopCheck`.

    Holds one scan's stop check, which is safe only because a connector is built fresh
    for every scan -- see `DiscoveryConnectorFactory`.
    """

    SENSITIVE_FIELDS: ClassVar[frozenset[str]] = SENSITIVE_FIELDS

    def __init__(self, client_factory: ClientFactory = _default_client) -> None:
        self._client_factory = client_factory
        self._should_stop: Callable[[], bool] = lambda: False

    def stop_when(self, should_stop: Callable[[], bool]) -> None:
        """Asked before every request to Azure."""
        self._should_stop = should_stop

    def scan(
        self,
        config: DiscoverySourceConfigSpec,
        lookback_hours: int,
        credentials: Mapping[str, Optional[str]],
        source_fields: Mapping[str, str],
        logger: logging.Logger,
    ) -> Iterator[Sequence[DiscoveryOutputRecord]]:
        """Every MCP server in the source's subscription, in batches."""
        settings = settings_from(source_fields)
        credential = service_principal_credential(
            settings.tenant_id,
            settings.client_id,
            credentials,
            source=_SOURCE,
            allow_default_env_var=ALLOW_DEFAULT_CREDENTIAL_ENV_VAR,
        )
        logger.info(
            "Azure API Management scan starting in subscription %s, using %s. MCP "
            "servers are an inventory: the lookback is not applied.",
            settings.subscription_id,
            describe_credential(credential),
        )

        counts = _Counts()
        refused: list[ArmError] = []
        batch: list[DiscoveryOutputRecord] = []
        try:
            with vendor_status():
                client = self._client_factory(credential, logger, self._should_stop)
                # Listed whole before any is read: a refusal here is the scan's.
                services = list(client.services(settings.subscription_id))
                for listed in services:
                    if self._should_stop():
                        logger.info(
                            "Azure API Management scan stopped early on request"
                        )
                        break
                    service = service_path(settings.subscription_id, listed.get("id"))
                    if service is None:
                        counts.skipped += 1
                        continue
                    counts.services += 1
                    try:
                        for record in _servers(client, service, counts, logger):
                            batch.append(record)
                            if len(batch) >= BATCH_SIZE:
                                yield batch
                                batch = []
                    except ArmError as e:
                        if e.status_code not in _REFUSED_PART:
                            raise
                        counts.refused_services += 1
                        refused.append(e)
                        logger.warning(
                            "Azure API Management service %s not read, the rest of "
                            "the scan goes on: %s",
                            service.rsplit("/", 1)[-1],
                            e,
                        )
            if batch:
                yield batch
        finally:
            close = getattr(credential, "close", None)
            if callable(close):
                close()

        _report(logger, counts)
        if refused and counts.refused_services == counts.services:
            # Every service was refused: not a subscription with no MCP servers.
            raise refused[0]


def _servers(
    client: ApiManagementClient,
    service: str,
    counts: _Counts,
    logger: logging.Logger,
) -> Iterator[McpServerRecord]:
    """One service's MCP servers, each with the tools API Management holds for it."""
    for api in client.apis(service):
        counts.apis += 1
        properties = _mapping(api.get("properties"))
        if properties.get("type") != MCP_API_TYPE:
            continue
        if properties.get("isCurrent") is False:
            counts.revisions += 1
            continue
        name = _text(api.get("name"))
        last_seen = _last_modified(api)
        if name is None or last_seen is None:
            counts.skipped += 1
            logger.warning(
                "Azure API Management returned an MCP server with no %s in service "
                "%s; skipped%s",
                "name" if name is None else "modification time",
                service.rsplit("/", 1)[-1],
                (
                    ""
                    if name is None
                    else ", because last_seen is required and inventing one would "
                    "date the record to the scan"
                ),
            )
            continue
        counts.servers += 1
        yield McpServerRecord(
            external_id=f"{service}/apis/{name}".lower(),
            name=_text(properties.get("displayName")) or name,
            last_seen=last_seen,
            runs_on=RunsOn.AZURE,
            tools=_tools(client, service, name, counts),
            detection=McpServerDetection.REGISTERED,
        )


def _tools(
    client: ApiManagementClient,
    service: str,
    api_name: str,
    counts: _Counts,
) -> Optional[list[Tool]]:
    """The server's tools by resource name, or None when it has none here or they
    could not be read."""
    try:
        names = sorted(
            {
                name
                for name in (
                    _text(t.get("name")) for t in client.tools(service, api_name)
                )
                if name is not None
            },
        )
    except ArmError as e:
        if e.status_code not in _REFUSED_PART:
            raise
        counts.tools_not_read += 1
        return None
    return [Tool(name=name) for name in names] or None


def _report(logger: logging.Logger, counts: _Counts) -> None:
    logger.info(
        "Azure API Management scan found %s MCP server(s) among %s API(s) in %s "
        "service(s); %s other revision(s) and %s unusable item(s) skipped; %s "
        "service(s) refused",
        counts.servers,
        counts.apis,
        counts.services,
        counts.revisions,
        counts.skipped,
        counts.refused_services,
    )
    if counts.tools_not_read:
        logger.warning(
            "Azure API Management: the tools of %s MCP server(s) could not be read, so "
            "each is reported without them.",
            counts.tools_not_read,
        )


def settings_from(source_fields: Mapping[str, str]) -> ApiManagementSettings:
    """The subscription and the principal's ids from the source's non-sensitive fields."""
    subscription = (source_fields.get(SUBSCRIPTION_ID_FIELD) or "").strip().lower()
    if not subscription:
        raise DiscoveryConfigurationError(
            f"{_SOURCE} is missing required field '{SUBSCRIPTION_ID_FIELD}', the id of "
            f"the Azure subscription whose API Management services are read. It is a "
            f"source field, not a secret.",
        )
    if not _SUBSCRIPTION_ID.match(subscription):
        raise DiscoveryConfigurationError(
            f"{_SOURCE}'s '{SUBSCRIPTION_ID_FIELD}' is not an Azure subscription id: "
            f"expected a GUID such as 00000000-0000-0000-0000-000000000000.",
        )
    return ApiManagementSettings(
        subscription_id=subscription,
        tenant_id=(source_fields.get(TENANT_ID_FIELD) or "").strip() or None,
        client_id=(source_fields.get(CLIENT_ID_FIELD) or "").strip() or None,
    )


def _last_modified(api: Mapping[str, Any]) -> Optional[datetime]:
    """When the API was last changed, or created if never changed, as aware UTC."""
    system = _mapping(api.get("systemData"))
    for key in ("lastModifiedAt", "createdAt"):
        value = system.get(key)
        if not isinstance(value, str) or not value.strip():
            continue
        try:
            parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
        except ValueError:
            continue
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    return None


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, dict) else {}


def _text(value: Any) -> Optional[str]:
    if not isinstance(value, str):
        return None
    return value.strip() or None
