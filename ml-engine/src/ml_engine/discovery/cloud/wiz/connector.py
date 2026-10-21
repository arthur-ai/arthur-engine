"""Wiz AI-SPM's side of a DISCOVER_AGENTS scan.

Lists the cloud resources of the configured Wiz Security Graph entity types in one Wiz
tenant and emits one record per resource. Wiz is not the cloud the agents run in but a
scanner of it, so one source covers every AWS account, Azure subscription and GCP
project the tenant has connected. An inventory, so the scan's lookback is not applied:
an agent deployed a year ago and still there is still there.

WHICH TYPES ARE AI AGENTS IS NOT VERIFIED. Wiz documents its Security Graph entity types
only behind a tenant login, and none of the public sources this connector was built from
(Wiz's Backstage plugin, the Cortex XSOAR integration) lists an AI type: XSOAR's list of
`cloudResources` types stops at the classic infrastructure ones. `DEFAULT_ENTITY_TYPES`
is therefore the most plausible pair of names in Wiz's naming style, not a confirmed
one, and a source can replace it with `entity_types`. If the tenant does not know a
default name Wiz answers BAD_USER_INPUT, and the scan fails as NOT_CONFIGURED with a
message that says to set `entity_types` -- it never silently reports nothing.

ONE RESOURCE, ONE RECORD, KEYED LIKE THE CLOUD'S OWN SOURCES. `external_id` is Wiz's
`graphEntity.providerUniqueId` verbatim: the provider's native id (an AWS ARN, an Azure
resource path, a GCP resource name), so an agent Wiz reports and the same agent a
native cloud source reports carry the same identity string. The record is never keyed
on an id Wiz mints itself (`graphEntity.id`, a scan or issue id): such an id names
Wiz's view of the resource, not the resource, and would split one agent into two. A
resource with no provider id is therefore skipped with a warning naming its Wiz entity
type. The address is `instance` = the cloud account Wiz names
(`subscriptionExternalId`: the AWS account id, Azure subscription id or GCP project id;
lower-cased for Azure, whose ids are case-insensitive GUIDs; Wiz's own `subscriptionId`
when the external id is missing), `scope` = the resource's region from its properties
(`region`, else `location`), "global" when it has none, and `resource_id` = the
provider id. `last_seen` is Wiz's `lastSeen`, else the resource's update or creation
time; a resource with none is skipped with a warning naming its id, never stamped with
the scan's time. `runs_on` is set only for AWS, Azure and GCP, which `RunsOn` already
has.

NO SERVICE NAMES, NO MODELS. Wiz sees configuration, not traces: nothing here says what
`service.name` an agent's spans carry, and GenAI Engine's resolver claims every service
name a record holds, so none is claimed. Nor is `llm_models` set: a resource's
properties may name a model, but no public source says which key, and a guess would be
wrong in a way nobody notices.

COMPLETENESS BEFORE RECORDS. Every page is read before the first batch is handed over,
so the job log says how much of the inventory was read -- pages, duplicates, a page
cap, a repeated cursor, a stop -- before anything is published. A call that fails part
way still publishes the records collected before it, after that report, and then
re-raises the failure unchanged, so the scan still fails with Wiz's status.
"""

import logging
import re
from dataclasses import dataclass
from typing import Callable, ClassVar, Iterator, Mapping, Optional, Sequence

from arthur_client.api_bindings import DiscoverySourceConfigSpec
from arthur_common.models.agent_discovery_schemas import DiscoveredAgentRecord
from arthur_common.models.agent_governance_schemas import (
    CloudAgentCreationSource,
    RunsOn,
    SourceAddress,
)

from discovery.address import address_problem
from discovery.cloud.wiz.client import (
    TOKEN_URLS,
    ScanStopped,
    WizClient,
    WizResource,
    WizSettings,
)
from discovery.endpoint.scope import parse_group_names
from job_executors.discovery_scan import DiscoveryConfigurationError

# The wire value. Identical to arthur-client's DiscoverySourceVendor member.
VENDOR = "wiz_ai_spm"

# Field names. Identical to the Platform catalog's field names, one constant each.
API_ENDPOINT_URL_FIELD = "api_endpoint_url"
AUTH_ENVIRONMENT_FIELD = "auth_environment"
CLIENT_ID_FIELD = "client_id"
CLIENT_SECRET_FIELD = "client_secret"
ENTITY_TYPES_FIELD = "entity_types"

DEFAULT_AUTH_ENVIRONMENT = "commercial"

# UNVERIFIED: see the module docstring. The Wiz Security Graph entity types listed when
# a source leaves `entity_types` blank. Chosen to be agents and the managed AI services
# that host them; AI_MODEL is left out on purpose, because a model is not an agent and
# would mint a task per deployed model.
DEFAULT_ENTITY_TYPES: tuple[str, ...] = ("AI_AGENT", "AI_SERVICE")

# The tenant's GraphQL endpoint: `https://api.<data center>.app.wiz.io/graphql`, or
# `.app.wiz.us` for FedRAMP. Anything else is refused before contact, so the token is
# only ever sent to a Wiz API host.
API_ENDPOINT_PATTERN = re.compile(
    r"https://api\.[a-z0-9]([a-z0-9-]*[a-z0-9])?\.app\.wiz\.(io|us)/graphql",
)

# What one entity type name looks like in Wiz's enum: capitals, digits and underscores.
ENTITY_TYPE_PATTERN = re.compile(r"[A-Z][A-Z0-9_]*")

# Every record's address scope when the resource names no region.
GLOBAL_SCOPE = "global"

# Wiz's `cloudPlatform` property (lower-cased) -> where the agent runs, for the clouds
# `RunsOn` already has. Every other platform leaves `runs_on` unset.
RUNS_ON: Mapping[str, RunsOn] = {
    "aws": RunsOn.AWS,
    "azure": RunsOn.AZURE,
    "gcp": RunsOn.GCP,
}

# Clouds whose account ids are case-insensitive, so `instance` is lower-cased for them.
CASE_INSENSITIVE_PLATFORMS = frozenset({"azure"})

# Pages of `cloudResources` read before giving up: 100 x 500 resources. A tenant past
# that is reported as capped rather than read for ever.
MAX_PAGES = 100

# Records per published batch. Every page has been read already; this only bounds how
# much one failed publish costs.
BATCH_SIZE = 100

ClientFactory = Callable[[WizSettings, logging.Logger], WizClient]


def _default_client(settings: WizSettings, logger: logging.Logger) -> WizClient:
    return WizClient(settings, logger=logger)


@dataclass
class _Tally:
    """How much of the inventory one scan read, for the completeness report."""

    listed: int = 0
    pages: int = 0
    duplicates: int = 0
    unaddressable: int = 0
    skipped: int = 0
    page_cap_hit: bool = False
    repeated_cursor: bool = False
    missing_cursor: bool = False
    listing_complete: bool = False
    stopped: bool = False
    failed: bool = False


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

    def stop_when(self, should_stop: Callable[[], bool]) -> None:
        self._should_stop = should_stop

    def scan(
        self,
        config: DiscoverySourceConfigSpec,
        lookback_hours: int,
        credentials: Mapping[str, Optional[str]],
        source_fields: Mapping[str, str],
        logger: logging.Logger,
    ) -> Iterator[Sequence[DiscoveredAgentRecord]]:
        """Every resource of the configured types in the source's tenant, in batches.

        `lookback_hours` is not applied: Wiz's `cloudResources` is an inventory, not a
        log, and filtering on `lastSeen` or `updatedAt` would make an agent that has not
        changed vanish from every scan after the first. `logger` is the JOB's, so what
        this reports reaches the Platform job log.
        """
        settings = settings_from(credentials, source_fields)
        client = self._client_factory(settings, logger)
        client.stop_when(self._should_stop)

        logger.info(
            "Wiz AI-SPM scan starting against the %s environment, listing entity "
            "type(s) %s%s",
            settings.auth_environment,
            ", ".join(settings.entity_types),
            (
                f" from {ENTITY_TYPES_FIELD}"
                if settings.entity_types_overridden
                else " (the engine's unverified default)"
            ),
        )

        tally = _Tally()
        records: list[DiscoveredAgentRecord] = []
        try:
            self._collect(client, logger, tally, records)
        except ScanStopped:
            tally.stopped = True
        except Exception:
            if records:
                tally.failed = True
                _report(logger, tally, len(records))
                yield from _batches(records)
            raise

        # Reported before the first batch is handed over, so a publish that fails part
        # way cannot leave a capped or partial answer unannounced.
        _report(logger, tally, len(records))
        yield from _batches(records)

    def _collect(
        self,
        client: WizClient,
        logger: logging.Logger,
        tally: _Tally,
        records: list[DiscoveredAgentRecord],
    ) -> None:
        """Every page of the inventory, appending to `records` as pages arrive, so a
        stop part-way still hands over what was found.

        A cursor Wiz hands back twice ends the listing rather than looping on it, and so
        does `MAX_PAGES`; both are reported as incomplete.
        """
        seen_ids: set[str] = set()
        seen_cursors: set[str] = set()
        cursor: Optional[str] = None
        while True:
            if tally.pages >= MAX_PAGES:
                tally.page_cap_hit = True
                return
            if self._should_stop():
                raise ScanStopped()
            page = client.cloud_resources_page(cursor)
            tally.pages += 1
            tally.unaddressable += page.unaddressable
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
    provider_id = resource.provider_unique_id
    if provider_id is None:
        logger.warning(
            "Wiz resource %s of entity type %s reported no providerUniqueId; skipped, "
            "because a record is keyed on the provider's own resource id (an ARN or "
            "resource path), never on an id Wiz assigns",
            resource.graph_id,
            resource.entity_type or "(unknown)",
        )
        return None
    if resource.last_seen is None:
        logger.warning(
            "Wiz resource %s reported no lastSeen, update or creation time; skipped, "
            "because last_seen is required and inventing one would date the record to "
            "the scan",
            resource.graph_id,
        )
        return None
    platform = (resource.cloud_platform or "").strip().lower()
    account = resource.subscription_external_id or resource.subscription_id
    if account is None:
        logger.warning(
            "Wiz resource %s names no cloud account (subscriptionExternalId); skipped, "
            "because the account is part of the record's address",
            resource.graph_id,
        )
        return None
    if platform in CASE_INSENSITIVE_PLATFORMS:
        account = account.lower()
    return DiscoveredAgentRecord(
        # Verbatim: see the module docstring.
        external_id=provider_id,
        name=resource.name or resource.graph_id,
        last_seen=resource.last_seen,
        runs_on=RUNS_ON.get(platform),
        creation_source=CloudAgentCreationSource(
            vendor=VENDOR,
            address=SourceAddress(
                instance=account,
                scope=resource.region or GLOBAL_SCOPE,
                resource_id=provider_id,
            ),
        ),
    )


def _report(logger: logging.Logger, tally: _Tally, records: int) -> None:
    """Say how complete the answer is. A partial answer must not read as a full one."""
    logger.info(
        "Wiz AI-SPM scan listed %s resource(s) over %s page(s); %s record(s), %s "
        "skipped, %s duplicate(s) across pages",
        tally.listed,
        tally.pages,
        records,
        tally.skipped,
        tally.duplicates,
    )
    if tally.failed:
        logger.warning(
            "Wiz AI-SPM scan failed part-way after %s page(s); the %s record(s) found "
            "before the failure are published, then the scan fails.",
            tally.pages,
            records,
        )
    if tally.stopped:
        logger.warning(
            "Wiz AI-SPM scan stopped early on request after %s page(s); the records "
            "found so far are all that is reported.",
            tally.pages,
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
            f"Wiz AI-SPM source is missing required field(s): {', '.join(missing)}. "
            f"{API_ENDPOINT_URL_FIELD} and {CLIENT_ID_FIELD} are source fields; "
            f"{CLIENT_SECRET_FIELD} is a secret.",
        )

    normalized_url = api_endpoint_url.rstrip("/")
    if (
        address_problem(normalized_url) is not None
        or API_ENDPOINT_PATTERN.fullmatch(normalized_url.lower()) is None
    ):
        raise DiscoveryConfigurationError(
            f"Wiz AI-SPM source's {API_ENDPOINT_URL_FIELD} is not a Wiz GraphQL "
            f"endpoint. Use the tenant's API endpoint as Wiz shows it under User "
            f"Settings > Tenant: https://api.<data center>.app.wiz.io/graphql, or "
            f"https://api.<data center>.app.wiz.us/graphql for FedRAMP.",
        )

    environment = (
        source_fields.get(AUTH_ENVIRONMENT_FIELD) or ""
    ).strip().lower() or DEFAULT_AUTH_ENVIRONMENT
    if environment not in TOKEN_URLS:
        raise DiscoveryConfigurationError(
            f"Wiz AI-SPM source's {AUTH_ENVIRONMENT_FIELD} must be one of "
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
            f"Wiz AI-SPM source's {ENTITY_TYPES_FIELD} must be comma-separated Wiz "
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
    )
