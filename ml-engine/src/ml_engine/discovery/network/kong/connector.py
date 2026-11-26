"""Kong Gateway's side of a DISCOVER_AGENTS scan: its MCP servers.

A STANDALONE-ONLY SOURCE. It reports MCP servers and no agents, and the Platform has
nowhere to put a server, so it has no Platform vendor.

SELF-HOSTED KONG, THROUGH ITS ADMIN API. Every workspace's plugins are listed and each
`ai-mcp-proxy` plugin is read by its `mode`:

=====================  ========================================================
passthrough-listener   an MCP server: the route fronts one that runs upstream
conversion-listener    an MCP server: Kong serves a REST API's operations as tools
listener               an MCP server: Kong serves tools other plugins define
conversion-only        tools for a `listener` to serve; counted, never a record
=====================  ========================================================

An inventory, not a log, so the lookback is not applied. Konnect is not read.

THE RECORD. One `McpServerRecord` per MCP server, `registered`. `external_id` is
`kong:{instance}:{workspace}:mcp_server:{plugin id}`, the plugin's id being the one
thing about a server that renaming its route does not change. It is named by the
plugin's instance name, else its route's name, else the plugin id. `tools` are the
names of the tools a `conversion-listener` defines. A `passthrough-listener`'s tools
are upstream, and a `listener`'s are other plugins', matched by a tag this scan does
not resolve, so neither has any on its record. Kong's Admin API keeps no record of who
called a server, so there is no `used_by`.

A DISABLED PLUGIN IS NOT A SERVER. It serves nothing, and is counted.

A REFUSED WORKSPACE IS A WARNING, NOT A FAILED SCAN. Each workspace is read on its own.
A rejected token ends the scan, and so does a scan in which every workspace was refused,
which would otherwise read as a Kong with no MCP servers.
"""

import logging
from dataclasses import dataclass
from typing import Callable, ClassVar, Iterator, Mapping, Optional, Sequence

from arthur_client.api_bindings import DiscoverySourceConfigSpec
from arthur_common.models.agent_discovery_schemas import DiscoveryOutputRecord
from arthur_common.models.agent_governance_schemas import Tool

from discovery.address import address_problem
from discovery.network.gateway_records import gateway_instance
from discovery.network.kong.client import (
    KongClient,
    KongError,
    KongSettings,
    McpPlugin,
)
from discovery.siem.tls import parse_tls_verification
from job_executors.discovery_scan import (
    DiscoveryConfigurationError,
    McpServerDetection,
    McpServerRecord,
)

VENDOR = "kong"

BASE_URL_FIELD = "base_url"
ADMIN_TOKEN_FIELD = "admin_token"
CA_CERTIFICATE_FIELD = "ca_certificate"
TLS_VERIFICATION_FIELD = "tls_verification"

# Records per published batch.
BATCH_SIZE = 100

# The modes in which the plugin's route is an MCP server.
_SERVER_MODES = frozenset({"passthrough-listener", "conversion-listener", "listener"})
_TOOLS_ONLY_MODE = "conversion-only"
# The name a Kong without workspaces is given in an external id, which is also the
# name of the workspace such a Kong's entities are in once it has them.
_DEFAULT_WORKSPACE = "default"

ClientFactory = Callable[[KongSettings, logging.Logger], KongClient]


def _default_client(settings: KongSettings, logger: logging.Logger) -> KongClient:
    return KongClient(settings, logger=logger)


@dataclass
class _Counts:
    workspaces: int = 0
    servers: int = 0
    tools_only: int = 0
    disabled: int = 0
    other_modes: int = 0
    undated: int = 0


class KongConnector:
    """Implements `job_executors.discovery_scan.DiscoverySourceConnector` and
    `AcceptsStopCheck`.

    Holds one scan's stop check, which is safe only because a connector is built fresh
    for every scan -- see `DiscoveryConnectorFactory`.
    """

    SENSITIVE_FIELDS: ClassVar[frozenset[str]] = frozenset({ADMIN_TOKEN_FIELD})

    def __init__(self, client_factory: ClientFactory = _default_client) -> None:
        self._client_factory = client_factory
        self._should_stop: Callable[[], bool] = lambda: False

    def stop_when(self, should_stop: Callable[[], bool]) -> None:
        self._should_stop = should_stop

    def scan(
        self,
        config: DiscoverySourceConfigSpec,
        lookback_hours: int,
        credentials: Mapping[str, Optional[str]],
        source_fields: Mapping[str, str],
        logger: logging.Logger,
    ) -> Iterator[Sequence[DiscoveryOutputRecord]]:
        """Every MCP server the Kong serves, in batches."""
        settings = settings_from(credentials, source_fields)
        instance = gateway_instance(settings.base_url)
        logger.info(
            "Kong scan starting against %s. MCP servers are an inventory: the "
            "lookback is not applied.",
            instance,
        )
        client = self._client_factory(settings, logger)
        # None is a Kong without workspaces, read as its one unnamed workspace.
        listed = client.workspaces(self._should_stop)
        workspaces: list[Optional[str]] = [None] if listed is None else list(listed)

        counts = _Counts()
        refused: list[KongError] = []
        batch: list[DiscoveryOutputRecord] = []
        for workspace in workspaces:
            if self._should_stop():
                logger.info("Kong scan stopped early on request")
                break
            try:
                for plugin in client.mcp_plugins(workspace, self._should_stop):
                    record = self._record(client, instance, workspace, plugin, counts)
                    if record is None:
                        continue
                    batch.append(record)
                    if len(batch) >= BATCH_SIZE:
                        yield batch
                        batch = []
            except KongError as exc:
                if exc.status_code not in (403, 404):
                    raise
                refused.append(exc)
                logger.warning(
                    "Kong workspace %s not read, the rest of the scan goes on: %s",
                    workspace or _DEFAULT_WORKSPACE,
                    exc,
                )
                continue
            counts.workspaces += 1
        if batch:
            yield batch

        _report(logger, counts, len(refused))
        if counts.workspaces == 0 and refused:
            # Every workspace was refused: not a Kong with no MCP servers.
            raise refused[0]

    def _record(
        self,
        client: KongClient,
        instance: str,
        workspace: Optional[str],
        plugin: McpPlugin,
        counts: _Counts,
    ) -> Optional[McpServerRecord]:
        """The plugin's record, or None, counted, when it is not a server to report."""
        if plugin.mode == _TOOLS_ONLY_MODE:
            counts.tools_only += 1
            return None
        if plugin.mode not in _SERVER_MODES:
            counts.other_modes += 1
            return None
        if not plugin.enabled:
            counts.disabled += 1
            return None
        if plugin.changed is None:
            counts.undated += 1
            return None
        name = plugin.instance_name
        if name is None and plugin.route_id is not None:
            name = client.route_name(workspace, plugin.route_id)
        counts.servers += 1
        return McpServerRecord(
            external_id=(
                f"{VENDOR}:{instance}:{workspace or _DEFAULT_WORKSPACE}:mcp_server:"
                f"{plugin.id}"
            ),
            name=name or plugin.id,
            last_seen=plugin.changed,
            tools=[Tool(name=t) for t in plugin.tools] or None,
            detection=McpServerDetection.REGISTERED,
        )


def _report(logger: logging.Logger, counts: _Counts, refused: int) -> None:
    logger.info(
        "Kong scan found %s MCP server(s) in %s workspace(s); %s tools-only plugin(s) "
        "and %s disabled plugin(s) not reported; %s workspace(s) refused",
        counts.servers,
        counts.workspaces,
        counts.tools_only,
        counts.disabled,
        refused,
    )
    if counts.other_modes:
        # Loud, because a mode this scan does not know is a server it may be missing.
        logger.warning(
            "Kong: %s ai-mcp-proxy plugin(s) in a mode this scan does not know were "
            "not reported.",
            counts.other_modes,
        )
    if counts.undated:
        logger.warning(
            "Kong: %s MCP server(s) not reported, because Kong gave no time for them "
            "and last_seen is required.",
            counts.undated,
        )


def settings_from(
    credentials: Mapping[str, Optional[str]],
    source_fields: Mapping[str, str],
) -> KongSettings:
    """The Admin API's address and trust from the source's fields, the token from its
    secrets. `base_url` is not a secret, so a failure can name the host."""
    url = (source_fields.get(BASE_URL_FIELD) or "").strip()
    token = (credentials.get(ADMIN_TOKEN_FIELD) or "").strip()
    missing = [
        name
        for name, value in ((BASE_URL_FIELD, url), (ADMIN_TOKEN_FIELD, token))
        if not value
    ]
    if missing:
        raise DiscoveryConfigurationError(
            f"Kong source is missing required field(s): {', '.join(missing)}. "
            f"base_url is a source field; admin_token is a secret.",
        )
    if not url.lower().startswith("https://"):
        # The token travels in a header. Over http it is in cleartext, and this is the
        # only place it can be refused before it is sent.
        raise DiscoveryConfigurationError(
            f"Kong base_url must be https, got "
            f"{url.split('://', 1)[0] or url!r}. The admin token travels in a request "
            f"header.",
        )
    problem = address_problem(url)
    if problem:
        raise DiscoveryConfigurationError(
            f"Kong base_url {problem}. Expected https://host or https://host:port.",
        )
    return KongSettings(
        base_url=url,
        admin_token=token,
        ca_certificate=(source_fields.get(CA_CERTIFICATE_FIELD) or "").strip() or None,
        tls_verification=parse_tls_verification(
            source_fields.get(TLS_VERIFICATION_FIELD),
            "Kong",
        ),
    )
