"""Wiz's side of a DISCOVER_AGENTS scan.

Two inventories from one Wiz tenant. The AI-SPM inventory lists the cloud resources of
the configured Wiz Security Graph entity types and emits one record per resource. The
workload inventory lists the AI frameworks and SDKs Wiz detected on VMs, container
images and serverless functions -- self-hosted agents no managed AI service knows
about -- and emits one record per (technology, workload). Wiz is not the cloud the
agents run in but a scanner of it, so one source covers every AWS account, Azure
subscription and GCP project the tenant has connected. Both are inventories, so the
scan's lookback is not applied: an agent deployed a year ago and still there is still
there.

THE DEFAULT TYPES ARE WIZ'S OWN NAMES. `DEFAULT_ENTITY_TYPES` is AI_AGENT and AI_SERVICE,
both members of Wiz's `GraphEntityType` enum, as are the other AI types a source can
list instead with `entity_types`: AI_AGENT_REGISTRY, AI_DATASET, AI_DEPLOYMENT,
AI_EXTENSION, AI_GATEWAY, AI_GUARDRAIL, AI_MODEL, AI_PIPELINE, AI_SECURITY_FINDING,
AI_SKILL, AI_SKILL_TEMPLATE, AI_TOOL and MCP_SERVER. Only the two are listed by default
because the others are not agents: a model, a deployment or a tool per record would
mint a task per item. If the tenant does not know a name Wiz answers BAD_USER_INPUT,
and the scan fails as NOT_CONFIGURED with a message that says to set `entity_types` --
it never silently reports nothing.

ONE AI-SPM RESOURCE, ONE RECORD, KEYED ON THE PROVIDER'S OWN ID. `external_id` is
`native_id`: the `cloudResourcesV2` node's `providerUniqueId` verbatim when Wiz has one
(an AWS ARN, an Azure resource path, a GCP resource name), so an agent Wiz reports and
the same agent a native cloud source reports carry the same identity string; else its
`externalId` qualified as `<cloudPlatform>:<account>:<externalId>`, because
`externalId` can be unique only inside its account. Wiz fills `providerUniqueId` on
some resources only (see the client's docstring), so a resource that gains one later
changes identity once. The record is never keyed on an id Wiz mints itself (the node's
`id`, a scan or issue id): such an id names Wiz's view of the resource, not the
resource, and would split one agent into two. A resource with neither id is skipped
with a warning naming its Wiz entity type. The address is `instance` = the cloud
account (`cloudAccount.externalId`: the AWS account id, Azure subscription id or GCP
project id; lower-cased for Azure, whose ids are case-insensitive GUIDs), `scope` = the
resource's `region`, else its `regionLocation`, "global" when it has neither, and
`resource_id` = the `external_id`. `last_seen` is Wiz's `lastSeen`, else the resource's
`updatedAt`, `firstSeen` or `createdAt`; a resource with none is skipped with a warning
naming its id, never stamped with the scan's time. `runs_on` is set only for AWS, Azure
and GCP, which `RunsOn` already has.

NO SERVICE NAMES, NO MODELS. Wiz sees configuration, not traces: nothing here says what
`service.name` an agent's spans carry, and GenAI Engine's resolver claims every service
name a record holds, so none is claimed. Nor is `llm_models` set: nothing the queries
read names a model, and a guess would be wrong in a way nobody notices.

WORKLOAD RECORDS ARE ADDRESSED LIKE A VM'S SOFTWARE. One record per (technology,
workload), as Compute Engine and EC2 report the agents on a VM: `address.instance` is the
workload's `native_id` (its `graphEntity.providerUniqueId` -- an instance ARN or resource
path, a function ARN, an image id -- else `<cloudPlatform>:<account>:<externalId>`),
`address.scope` is `<account>/<region>` (`<account>/global` without a region), and
`resource_kind` "technology" with `resource_id` the technology's name as Wiz spells it.
`external_id` is `<workload native id>:<technology key>`, the key being the name
lower-cased with every run of other characters made one "-":
`arn:aws:ec2:us-east-1:123456789012:instance/i-0abc:langchain`, or
`aws:123456789012:i-0abc:langchain` without a `providerUniqueId`. Nothing Wiz assigns
(a resource id, a technology id) is part of it, so a workload with neither provider id
is skipped with a warning naming its entity type, as is one without an account or a
timestamp. `last_seen` is the hosted technology's `updatedAt`, else its `firstSeen`, and
a technology Wiz reports twice on one workload is one record dated by the newer.
`version` is the detected version; no model, no service name. Wiz's technology id
(a numeric string, "2599" for NGINX in port-labs/ocean 67254a9
`integrations/wiz/.port/examples/hosted-technology/a.json:5`) has no `AgentObservations`
field, so it reaches only the unmatched-names log. A running container is not a
workload here: its id changes on every restart, and its image carries the same
technologies under an id that does not.

WHICH AI TECHNOLOGIES ARE AGENT FRAMEWORKS IS MATCHED HERE, ON `technology.name` ONLY.
The hosted technology's own `name` is "<technology> (<resource name>)" (confirmed:
"NGINX (docker.io/nginx@dec7a90b)", same Port example, line 3), so a resource called
"mcp-gateway" would otherwise make NGINX an agent. Wiz is asked only for technologies
it files under the MACHINE_LEARNING_AND_AI stack layer, which also holds technologies no
agent is built from (strong inference: "PyTorch, TensorFlow, etc." in
lindsp77/wiz-health-assessment-skill e4afe70 `scripts/csv_metrics_processor.py:38`).
A technology Wiz marks `isCloudService` (Azure OpenAI, say) is dropped: managed AI
services are the AI-SPM inventory's. Otherwise a name is kept when, folded to
lower-case letters and digits, it contains one of `AGENT_FRAMEWORK_STEMS` ("LangChain",
"langchain-core", "Llama Index"); when one of its words is in `AGENT_FRAMEWORK_WORDS`
("MCP Server", not "mcpx"); or when it names a model vendor beside a word that makes it
the vendor's library (`VENDOR_SDK_WORDS`: "OpenAI Python SDK", "openai-node",
"Anthropic SDK", "Claude Agent SDK"). A vendor's name alone ("OpenAI", "Anthropic")
is not kept: it names the service (strong inference: the same repo's
`csv_metrics_processor.py:255-257` lists "OpenAI" beside "Azure OpenAI" as services a
scanner covers). Wiz's exact spellings are not published, so the scan logs, once, the
ML and AI technology names (with Wiz's technology id) it saw and did not match: no
resource names, so the first live scan shows what the rules miss.

THE WORKLOAD INVENTORY IS ONE PART OF THE SCAN. A service account Wiz refuses the
`hostedTechnologies` query (UNAUTHORIZED, for a scope it lacks), or a tenant that
rejects its shape (BAD_USER_INPUT), costs that part and not the scan: the job log says
so, quoting the scopes Wiz's denial says it wanted, the run reports the denied scope
`workload-inventory`, and the AI-SPM records are published.

COMPLETENESS BEFORE RECORDS. Every page of both inventories is read before the first
batch is handed over, so the job log says how much was read -- pages, duplicates, a
page cap, a repeated cursor, a stop, a refused part -- before anything is published. A
call that fails part way for any other reason still publishes the records collected
before it, after that report, and then re-raises the failure unchanged, so the scan
still fails with Wiz's status.
"""

import logging
import os
import re
from dataclasses import dataclass, field
from typing import (
    Callable,
    ClassVar,
    Iterator,
    Mapping,
    Optional,
    Protocol,
    Sequence,
    TypeVar,
)
from urllib.parse import urlsplit

from arthur_client.api_bindings import DiscoverySourceConfigSpec
from arthur_common.models.agent_discovery_schemas import DiscoveredAgentRecord
from arthur_common.models.agent_governance_schemas import (
    AgentObservations,
    CloudAgentCreationSource,
    RunsOn,
    SourceAddress,
)

from discovery.address import address_problem
from discovery.cloud.wiz.client import (
    TOKEN_URLS,
    ResourcePage,
    ScanStopped,
    WizClient,
    WizError,
    WizResource,
    WizSettings,
    WorkloadPage,
    WorkloadTechnology,
)
from discovery.endpoint.scope import parse_group_names
from job_executors.discovery_scan import (
    DENIED_PERMISSION,
    DENIED_UNREACHABLE,
    DeniedScope,
    DiscoveryConfigurationError,
)

# The wire value. Identical to arthur-client's DiscoverySourceVendor member.
VENDOR = "wiz"

# Field names. Identical to the Platform catalog's field names, one constant each.
API_ENDPOINT_URL_FIELD = "api_endpoint_url"
AUTH_ENVIRONMENT_FIELD = "auth_environment"
CLIENT_ID_FIELD = "client_id"
CLIENT_SECRET_FIELD = "client_secret"
ENTITY_TYPES_FIELD = "entity_types"

DEFAULT_AUTH_ENVIRONMENT = "commercial"

# The Wiz Security Graph entity types listed when a source leaves `entity_types` blank:
# agents and the managed AI services that host them. See the module docstring for the
# other AI types a source can list.
DEFAULT_ENTITY_TYPES: tuple[str, ...] = ("AI_AGENT", "AI_SERVICE")

# The tenant's GraphQL endpoint: `https://api.<data center>.app.wiz.io/graphql`, or
# `.app.wiz.us` for FedRAMP. Anything else is refused before contact, so the token is
# only ever sent to a Wiz API host.
API_ENDPOINT_PATTERN = re.compile(
    r"https://api\.[a-z0-9]([a-z0-9-]*[a-z0-9])?\.app\.wiz\.(io|us)/graphql",
)

# Development only, never a source field: the base URL of a local fake Wiz
# (tests/fakes/wiz) that then serves `/oauth/token` and `/graphql` in place of Wiz. The
# source's fields are still validated as for Wiz. Only a loopback host is accepted, so
# an engine cannot be pointed at any other host this way.
LOCAL_OVERRIDE_ENV_VAR = "ARTHUR_ENGINE_WIZ_API_BASE_URL_OVERRIDE"
LOCAL_OVERRIDE_HOSTS = frozenset({"localhost", "127.0.0.1", "::1"})

# What one entity type name looks like in Wiz's enum: capitals, digits and underscores.
ENTITY_TYPE_PATTERN = re.compile(r"[A-Z][A-Z0-9_]*")

# Every record's address scope when the resource names no region.
GLOBAL_SCOPE = "global"

# Agent frameworks as `_fold` writes them, each distinctive enough to match as a
# substring of a folded name.
AGENT_FRAMEWORK_STEMS: tuple[str, ...] = (
    "langchain",
    "langgraph",
    "llamaindex",
    "crewai",
    "autogen",
    "semantickernel",
    "haystack",
    "openaiagents",
    "claudeagent",
    "agentdevelopmentkit",
    "googleadk",
    "modelcontextprotocol",
    "fastmcp",
)

# Matched only as a whole word of the name.
AGENT_FRAMEWORK_WORDS = frozenset({"mcp"})

# A model vendor's word -> the words that make a name its library rather than its service.
VENDOR_SDK_WORDS: Mapping[str, frozenset[str]] = {
    "openai": frozenset(
        {"sdk", "agent", "agents", "python", "node", "nodejs", "library"},
    ),
    "anthropic": frozenset({"sdk", "agent", "agents"}),
    "claude": frozenset({"sdk", "agent", "agents"}),
}

# The most unmatched technology names one scan's log line lists.
MAX_UNMATCHED_NAMES_LOGGED = 50

# A workload record's `address.resource_kind`.
TECHNOLOGY_RESOURCE_KIND = "technology"

# The denied scope a run reports when Wiz refuses the workload inventory.
WORKLOAD_INVENTORY_SCOPE = "workload-inventory"

# The statuses that cost the workload inventory rather than the scan: a missing scope
# (403) and a query shape the tenant rejects (400).
WORKLOAD_REFUSED: Mapping[int, str] = {
    403: DENIED_PERMISSION,
    400: DENIED_UNREACHABLE,
}

_TECHNOLOGY_KEY_SEPARATOR = re.compile(r"[^a-z0-9]+")


def _fold(name: str) -> str:
    """A technology name in lower-case letters and digits only: "Llama-Index" and
    "llama index" are both "llamaindex"."""
    return _TECHNOLOGY_KEY_SEPARATOR.sub("", name.casefold())


def is_agent_framework(name: str) -> bool:
    """Whether a Wiz ML and AI `technology.name` is an agent framework or SDK; see the
    module docstring for the three rules."""
    folded = _fold(name)
    if any(stem in folded for stem in AGENT_FRAMEWORK_STEMS):
        return True
    words = set(_TECHNOLOGY_KEY_SEPARATOR.split(name.casefold()))
    if words & AGENT_FRAMEWORK_WORDS:
        return True
    return any(
        vendor in words and not words.isdisjoint(context)
        for vendor, context in VENDOR_SDK_WORDS.items()
    )


def native_id(
    provider_unique_id: Optional[str],
    external_id: Optional[str],
    platform: str,
    account: str,
) -> Optional[str]:
    """The provider's id for a resource, unique across every cloud the tenant scans.

    `providerUniqueId` verbatim when Wiz has it; else `<platform>:<account>:<externalId>`
    (`aws:123456789012:i-0abc`), with `platform` Wiz's `cloudPlatform` lower-cased.
    None when Wiz has neither, or only `externalId` and no platform to qualify it.
    """
    if provider_unique_id is not None:
        return provider_unique_id
    if external_id is None or not platform:
        return None
    return f"{platform}:{account}:{external_id.strip()}"


# Wiz's `cloudPlatform` (lower-cased) -> where the agent runs, for the clouds
# `RunsOn` already has. Every other platform leaves `runs_on` unset.
RUNS_ON: Mapping[str, RunsOn] = {
    "aws": RunsOn.AWS,
    "azure": RunsOn.AZURE,
    "gcp": RunsOn.GCP,
}

# Clouds whose account ids are case-insensitive, so `instance` is lower-cased for them.
CASE_INSENSITIVE_PLATFORMS = frozenset({"azure"})

# Pages of either inventory read before giving up: 100 x 500 resources. A tenant past
# that is reported as capped rather than read for ever.
MAX_PAGES = 100

# Records per published batch. Every page has been read already; this only bounds how
# much one failed publish costs.
BATCH_SIZE = 100

ClientFactory = Callable[[WizSettings, logging.Logger], WizClient]


def _default_client(settings: WizSettings, logger: logging.Logger) -> WizClient:
    return WizClient(settings, logger=logger)


class _Page(Protocol):
    @property
    def has_next_page(self) -> bool: ...

    @property
    def end_cursor(self) -> Optional[str]: ...

    @property
    def unaddressable(self) -> int: ...


_PageT = TypeVar("_PageT", bound=_Page)

_RESOURCES = "AI-SPM inventory"
_WORKLOADS = "workload inventory"


@dataclass
class _Progress:
    """Which inventory the scan was reading, and how it ended."""

    phase: str = _RESOURCES
    stopped: bool = False
    failed: bool = False


@dataclass
class _Tally:
    """How much of one inventory a scan read, for the completeness report."""

    listed: int = 0
    pages: int = 0
    duplicates: int = 0
    unaddressable: int = 0
    skipped: int = 0
    page_cap_hit: bool = False
    repeated_cursor: bool = False
    missing_cursor: bool = False
    listing_complete: bool = False
    # Workload inventory only: ML and AI technologies that are not agent frameworks,
    # their distinct names, and Wiz's refusal.
    not_listed: int = 0
    cloud_services: int = 0
    unmatched_names: set[str] = field(default_factory=set)
    refused_status: Optional[int] = None


class WizConnector:
    """Implements `job_executors.discovery_scan.DiscoverySourceConnector` and
    `AcceptsStopCheck` (structurally; the Protocols are not imported).

    Holds one scan's stop check, which is safe only because a connector is built fresh
    for every scan -- see `DiscoveryConnectorFactory`.
    """

    # Must equal the set of fields the Platform catalog marks is_sensitive.
    SENSITIVE_FIELDS: ClassVar[frozenset[str]] = frozenset({CLIENT_SECRET_FIELD})

    def __init__(self, client_factory: ClientFactory = _default_client) -> None:
        self._client_factory = client_factory
        self._should_stop: Callable[[], bool] = lambda: False
        self._denied: list[DeniedScope] = []

    def stop_when(self, should_stop: Callable[[], bool]) -> None:
        self._should_stop = should_stop

    def denied_scopes(self) -> Sequence[DeniedScope]:
        """The workload inventory, when Wiz refused it; see the module docstring."""
        return tuple(self._denied)

    def scan(
        self,
        config: DiscoverySourceConfigSpec,
        lookback_hours: int,
        credentials: Mapping[str, Optional[str]],
        source_fields: Mapping[str, str],
        logger: logging.Logger,
    ) -> Iterator[Sequence[DiscoveredAgentRecord]]:
        """Every resource of the configured types in the source's tenant, then every
        agent framework on its workloads, in batches.

        `lookback_hours` is not applied: both queries read an inventory, not a log, and
        filtering on `lastSeen` or `updatedAt` would make an agent that has not changed
        vanish from every scan after the first. `logger` is the JOB's, so what this
        reports reaches the Platform job log.
        """
        settings = settings_from(credentials, source_fields)
        if settings.local_override_url is not None:
            logger.warning(
                "%s is set: this scan talks to %s, not to Wiz. It is for local "
                "development against a fake Wiz; unset it on any other engine.",
                LOCAL_OVERRIDE_ENV_VAR,
                settings.local_override_url,
            )
        client = self._client_factory(settings, logger)
        client.stop_when(self._should_stop)

        logger.info(
            "Wiz scan starting against the %s environment, listing entity "
            "type(s) %s%s",
            settings.auth_environment,
            ", ".join(settings.entity_types),
            (
                f" from {ENTITY_TYPES_FIELD}"
                if settings.entity_types_overridden
                else " (the engine's default)"
            ),
        )

        self._denied = []
        tally, workloads = _Tally(), _Tally()
        records: list[DiscoveredAgentRecord] = []
        workload_records: dict[str, DiscoveredAgentRecord] = {}
        progress = _Progress()
        try:
            self._collect(client, logger, tally, records)
            progress.phase = _WORKLOADS
            self._collect_workloads(client, logger, workloads, workload_records)
        except ScanStopped:
            progress.stopped = True
        except Exception:
            found = records + list(workload_records.values())
            if found:
                progress.failed = True
                _report_all(logger, tally, workloads, progress, len(records), found)
                yield from _batches(found)
            raise

        found = records + list(workload_records.values())
        # Reported before the first batch is handed over, so a publish that fails part
        # way cannot leave a capped or partial answer unannounced.
        _report_all(logger, tally, workloads, progress, len(records), found)
        yield from _batches(found)

    def _collect(
        self,
        client: WizClient,
        logger: logging.Logger,
        tally: _Tally,
        records: list[DiscoveredAgentRecord],
    ) -> None:
        """Every page of the AI-SPM inventory, appending to `records` as pages arrive,
        so a stop part-way still hands over what was found."""
        seen_ids: set[str] = set()

        def take(page: ResourcePage) -> None:
            for resource in page.resources:
                if resource.graph_id in seen_ids:
                    tally.duplicates += 1
                    continue
                seen_ids.add(resource.graph_id)
                tally.listed += 1
                record = record_for(resource, logger)
                if record is None:
                    tally.skipped += 1
                else:
                    records.append(record)

        self._walk(client.cloud_resources_page, take, tally)

    def _collect_workloads(
        self,
        client: WizClient,
        logger: logging.Logger,
        tally: _Tally,
        records: dict[str, DiscoveredAgentRecord],
    ) -> None:
        """Every page of the workload inventory, into `records` by `external_id`.

        One technology on one workload can arrive more than once -- two versions, two
        paths to it -- and is one record, dated by its newest sighting. A refusal costs
        this part only; see the module docstring.
        """

        def take(page: WorkloadPage) -> None:
            for technology in page.technologies:
                tally.listed += 1
                if technology.is_cloud_service:
                    tally.cloud_services += 1
                    continue
                if not is_agent_framework(technology.technology_name):
                    tally.not_listed += 1
                    tally.unmatched_names.add(_logged_name(technology))
                    continue
                record = workload_record_for(technology, logger)
                if record is None:
                    tally.skipped += 1
                    continue
                kept = records.get(record.external_id)
                if kept is not None:
                    tally.duplicates += 1
                    if kept.last_seen >= record.last_seen:
                        continue
                records[record.external_id] = record

        try:
            self._walk(client.workload_technologies_page, take, tally)
        except WizError as exc:
            reason = WORKLOAD_REFUSED.get(exc.status_code or 0)
            if reason is None:
                raise
            tally.refused_status = exc.status_code
            self._denied.append(DeniedScope(WORKLOAD_INVENTORY_SCOPE, reason))
            logger.warning(
                "Wiz refused the workload inventory: %s. The AI-SPM records are still "
                "published; the run reports the denied scope %s.",
                # Most of the client's messages end without a full stop, some with one.
                str(exc).rstrip("."),
                WORKLOAD_INVENTORY_SCOPE,
            )

    def _walk(
        self,
        fetch: Callable[[Optional[str]], _PageT],
        take: Callable[[_PageT], None],
        tally: _Tally,
    ) -> None:
        """Every page `fetch` returns, each handed to `take` as it arrives.

        A cursor Wiz hands back twice ends the listing rather than looping on it, and so
        does `MAX_PAGES`; both are reported as incomplete.
        """
        seen_cursors: set[str] = set()
        cursor: Optional[str] = None
        while True:
            if tally.pages >= MAX_PAGES:
                tally.page_cap_hit = True
                return
            if self._should_stop():
                raise ScanStopped()
            page = fetch(cursor)
            tally.pages += 1
            tally.unaddressable += page.unaddressable
            take(page)
            if not page.has_next_page:
                tally.listing_complete = True
                return
            if page.end_cursor is None:
                tally.missing_cursor = True
                return
            if page.end_cursor in seen_cursors:
                tally.repeated_cursor = True
                return
            seen_cursors.add(page.end_cursor)
            cursor = page.end_cursor


def _batches(
    records: list[DiscoveredAgentRecord],
) -> Iterator[list[DiscoveredAgentRecord]]:
    for start in range(0, len(records), BATCH_SIZE):
        yield records[start : start + BATCH_SIZE]


def record_for(
    resource: WizResource,
    logger: logging.Logger,
) -> Optional[DiscoveredAgentRecord]:
    """One resource's record, or None when Wiz gave nothing to key, date or place it by."""
    if resource.last_seen is None:
        logger.warning(
            "Wiz resource %s reported no lastSeen, update, first-seen or creation time; "
            "skipped, because last_seen is required and inventing one would date the "
            "record to the scan",
            resource.graph_id,
        )
        return None
    platform = (resource.cloud_platform or "").strip().lower()
    account = resource.account
    if account is None:
        logger.warning(
            "Wiz resource %s names no cloud account (cloudAccount.externalId); skipped, "
            "because the account is part of the record's address",
            resource.graph_id,
        )
        return None
    if platform in CASE_INSENSITIVE_PLATFORMS:
        account = account.lower()
    identity = native_id(
        resource.provider_unique_id,
        resource.provider_external_id,
        platform,
        account,
    )
    if identity is None:
        logger.warning(
            "Wiz resource %s of entity type %s (%s) reported no providerUniqueId and "
            "no externalId with a cloudPlatform; skipped, because a record is keyed on "
            "the provider's own resource id, never on an id Wiz assigns",
            resource.graph_id,
            resource.entity_type or "(unknown)",
            resource.native_type or "no native type",
        )
        return None
    return DiscoveredAgentRecord(
        external_id=identity,
        name=resource.name or resource.graph_id,
        last_seen=resource.last_seen,
        runs_on=RUNS_ON.get(platform),
        creation_source=CloudAgentCreationSource(
            vendor=VENDOR,
            address=SourceAddress(
                instance=account,
                scope=resource.region or GLOBAL_SCOPE,
                resource_id=identity,
            ),
        ),
    )


def workload_record_for(
    technology: WorkloadTechnology,
    logger: logging.Logger,
) -> Optional[DiscoveredAgentRecord]:
    """One technology's record on one workload, or None when Wiz gave nothing to key,
    date or place it by."""
    key = _TECHNOLOGY_KEY_SEPARATOR.sub("-", technology.technology_name.lower()).strip(
        "-",
    )
    if not key:
        return None
    if technology.last_seen is None:
        logger.warning(
            "Wiz %s %s reported no update or first-seen time for %s; skipped, because "
            "last_seen is required and inventing one would date the record to the scan",
            technology.workload_type,
            technology.workload_graph_id,
            technology.technology_name,
        )
        return None
    platform = (technology.cloud_platform or "").strip().lower()
    account = technology.account
    if account is None:
        logger.warning(
            "Wiz %s %s names no cloud account (cloudAccount.externalId); its %s is "
            "skipped, because the account is part of the record's address",
            technology.workload_type,
            technology.workload_graph_id,
            technology.technology_name,
        )
        return None
    if platform in CASE_INSENSITIVE_PLATFORMS:
        account = account.lower()
    workload_id = native_id(
        technology.workload_provider_id,
        technology.workload_external_id,
        platform,
        account,
    )
    if workload_id is None:
        logger.warning(
            "Wiz %s %s (%s) reported no providerUniqueId and no externalId with a "
            "cloudPlatform; its %s is skipped, because a record is keyed on the "
            "provider's own id for the workload, never on an id Wiz assigns",
            technology.workload_type,
            technology.workload_graph_id,
            technology.workload_native_type or "no native type",
            technology.technology_name,
        )
        return None
    return DiscoveredAgentRecord(
        external_id=f"{workload_id}:{key}",
        name=f"{technology.technology_name} on {technology.workload_name or workload_id}",
        last_seen=technology.last_seen,
        runs_on=RUNS_ON.get(platform),
        creation_source=CloudAgentCreationSource(
            vendor=VENDOR,
            address=SourceAddress(
                instance=workload_id,
                scope=f"{account}/{technology.region or GLOBAL_SCOPE}",
                resource_kind=TECHNOLOGY_RESOURCE_KIND,
                resource_id=technology.technology_name,
            ),
            observations=AgentObservations(version=technology.technology_version),
        ),
    )


def _logged_name(technology: WorkloadTechnology) -> str:
    """A technology's name for the unmatched-names log, with Wiz's id when it has one."""
    if technology.technology_id is None:
        return technology.technology_name
    return f"{technology.technology_name} [{technology.technology_id}]"


def _report_all(
    logger: logging.Logger,
    tally: _Tally,
    workloads: _Tally,
    progress: _Progress,
    resource_records: int,
    found: list[DiscoveredAgentRecord],
) -> None:
    """Both inventories' completeness, then how the scan ended."""
    _report(logger, tally, resource_records)
    workloads_read = workloads.pages > 0 or workloads.refused_status is not None
    if workloads_read:
        _report_workloads(logger, workloads, len(found) - resource_records)
    if progress.failed:
        logger.warning(
            "Wiz scan failed part-way, in the %s; the %s record(s) found before "
            "the failure are published, then the scan fails.",
            progress.phase,
            len(found),
        )
    if progress.stopped:
        logger.warning(
            "Wiz scan stopped early on request, in the %s; the records found so "
            "far are all that is reported%s.",
            progress.phase,
            "" if workloads_read else ", and the workload inventory was not read",
        )


def _report_workloads(logger: logging.Logger, tally: _Tally, records: int) -> None:
    """Say how complete the workload inventory is."""
    if tally.refused_status is not None:
        logger.warning(
            "Wiz workload inventory not read (HTTP %s); %s record(s) from it.",
            tally.refused_status,
            records,
        )
        return
    logger.info(
        "Wiz workload inventory listed %s ML and AI technology sighting(s) over %s "
        "page(s); %s record(s), %s skipped, %s cloud service(s) left to the AI-SPM "
        "inventory, %s not an agent framework, %s duplicate(s)",
        tally.listed,
        tally.pages,
        records,
        tally.skipped,
        tally.cloud_services,
        tally.not_listed,
        tally.duplicates,
    )
    if tally.unmatched_names:
        names = sorted(tally.unmatched_names, key=str.casefold)
        shown = names[:MAX_UNMATCHED_NAMES_LOGGED]
        more = len(names) - len(shown)
        logger.info(
            "Wiz ML and AI technologies seen that the engine does not match as agent "
            "frameworks: %s%s",
            ", ".join(shown),
            f", and {more} more" if more else "",
        )
    if tally.page_cap_hit:
        logger.warning(
            "Wiz workload inventory stopped at %s pages (%s sightings); technologies "
            "past that were not read.",
            tally.pages,
            tally.listed,
        )
    if tally.repeated_cursor or tally.missing_cursor:
        logger.warning(
            "Wiz workload inventory ended after %s page(s) because Wiz %s; technologies "
            "past that point may be missing.",
            tally.pages,
            (
                "returned a page cursor it had already returned"
                if tally.repeated_cursor
                else "said more pages exist but returned no cursor"
            ),
        )
    if tally.unaddressable:
        logger.warning(
            "Wiz returned %s hosted technology record(s) without a name or an "
            "identified resource; skipped.",
            tally.unaddressable,
        )
    if tally.listing_complete and tally.listed == 0:
        logger.info(
            "Wiz reported no ML or AI technologies on any VM, container image or "
            "serverless function.",
        )


def _report(logger: logging.Logger, tally: _Tally, records: int) -> None:
    """Say how complete the AI-SPM inventory is. A partial answer must not read as a
    full one."""
    logger.info(
        "Wiz scan listed %s resource(s) over %s page(s); %s record(s), %s "
        "skipped, %s duplicate(s) across pages",
        tally.listed,
        tally.pages,
        records,
        tally.skipped,
        tally.duplicates,
    )
    if tally.page_cap_hit:
        logger.warning(
            "Wiz resource list stopped at %s pages (%s resources); resources past that "
            "were not read. Narrow the scan with %s.",
            tally.pages,
            tally.listed,
            ENTITY_TYPES_FIELD,
        )
    if tally.repeated_cursor:
        logger.warning(
            "Wiz returned a page cursor it had already returned, so the resource list "
            "was ended after %s page(s) rather than read in a loop; resources past that "
            "point may be missing.",
            tally.pages,
        )
    if tally.missing_cursor:
        logger.warning(
            "Wiz said more pages exist but returned no cursor for them, so the resource "
            "list was ended after %s page(s); resources past that point may be missing.",
            tally.pages,
        )
    if tally.unaddressable:
        logger.warning(
            "Wiz returned %s resource(s) without an id; skipped, because the id is the "
            "record's identity.",
            tally.unaddressable,
        )
    if tally.listing_complete and tally.listed == 0:
        logger.info(
            "Wiz listed no resources of the configured entity type(s). If AI agents "
            "are expected, check %s against the entity types this tenant uses.",
            ENTITY_TYPES_FIELD,
        )


def settings_from(
    credentials: Mapping[str, Optional[str]],
    source_fields: Mapping[str, str],
) -> WizSettings:
    """The tenant and type filter from the source's fields, the secret from its
    credentials. Errors name fields, never their values."""
    api_endpoint_url = (source_fields.get(API_ENDPOINT_URL_FIELD) or "").strip()
    client_id = (source_fields.get(CLIENT_ID_FIELD) or "").strip()
    client_secret = (credentials.get(CLIENT_SECRET_FIELD) or "").strip()
    missing = [
        name
        for name, value in (
            (API_ENDPOINT_URL_FIELD, api_endpoint_url),
            (CLIENT_ID_FIELD, client_id),
            (CLIENT_SECRET_FIELD, client_secret),
        )
        if not value
    ]
    if missing:
        raise DiscoveryConfigurationError(
            f"Wiz source is missing required field(s): {', '.join(missing)}. "
            f"{API_ENDPOINT_URL_FIELD} and {CLIENT_ID_FIELD} are source fields; "
            f"{CLIENT_SECRET_FIELD} is a secret.",
        )

    normalized_url = api_endpoint_url.rstrip("/")
    if (
        address_problem(normalized_url) is not None
        or API_ENDPOINT_PATTERN.fullmatch(normalized_url.lower()) is None
    ):
        raise DiscoveryConfigurationError(
            f"Wiz source's {API_ENDPOINT_URL_FIELD} is not a Wiz GraphQL "
            f"endpoint. Use the tenant's API endpoint as Wiz shows it under User "
            f"Settings > Tenant: https://api.<data center>.app.wiz.io/graphql, or "
            f"https://api.<data center>.app.wiz.us/graphql for FedRAMP.",
        )

    environment = (
        source_fields.get(AUTH_ENVIRONMENT_FIELD) or ""
    ).strip().lower() or DEFAULT_AUTH_ENVIRONMENT
    if environment not in TOKEN_URLS:
        raise DiscoveryConfigurationError(
            f"Wiz source's {AUTH_ENVIRONMENT_FIELD} must be one of "
            f"{', '.join(TOKEN_URLS)}.",
        )

    entity_types = tuple(
        dict.fromkeys(
            name.upper()
            for name in parse_group_names(source_fields.get(ENTITY_TYPES_FIELD))
        ),
    )
    if any(ENTITY_TYPE_PATTERN.fullmatch(name) is None for name in entity_types):
        raise DiscoveryConfigurationError(
            f"Wiz source's {ENTITY_TYPES_FIELD} must be comma-separated Wiz "
            f"Security Graph entity type names, such as VIRTUAL_MACHINE: letters, "
            f"digits and underscores only.",
        )

    return WizSettings(
        api_endpoint_url=normalized_url.lower(),
        auth_environment=environment,
        client_id=client_id,
        client_secret=client_secret,
        entity_types=entity_types or DEFAULT_ENTITY_TYPES,
        entity_types_overridden=bool(entity_types),
        local_override_url=local_override(),
    )


def local_override() -> Optional[str]:
    """`LOCAL_OVERRIDE_ENV_VAR` as `scheme://host[:port]`, or None when it is unset.

    Anything but an http(s) URL on a loopback host with no path, user, query or
    fragment fails the scan rather than falling back to Wiz, so a mistyped override is
    never silently ignored. The error does not quote the value.
    """
    raw = os.getenv(LOCAL_OVERRIDE_ENV_VAR, "").strip()
    if not raw:
        return None
    parts = urlsplit(raw)
    try:
        port = parts.port
    except ValueError:
        port = -1
    if (
        parts.scheme not in ("http", "https")
        or parts.hostname not in LOCAL_OVERRIDE_HOSTS
        or port == -1
        or parts.username is not None
        or parts.password is not None
        or parts.path not in ("", "/")
        or parts.query
        or parts.fragment
    ):
        raise DiscoveryConfigurationError(
            f"{LOCAL_OVERRIDE_ENV_VAR} is set on this engine but is not an http:// or "
            f"https:// URL on localhost, 127.0.0.1 or [::1] with no path, such as "
            f"http://127.0.0.1:8099. It is for local development against a fake Wiz "
            f"only; unset it to reach Wiz.",
        )
    host = f"[{parts.hostname}]" if parts.hostname == "::1" else parts.hostname
    return f"{parts.scheme}://{host}{f':{port}' if port is not None else ''}"
