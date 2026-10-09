"""Vercel's side of a DISCOVER_AGENTS scan.

Lists one team's projects and emits one record per project that looks like it runs an
AI agent. An inventory, so the scan's lookback is not applied: a project deployed a year
ago and still live is still there.

A HEURISTIC, BECAUSE VERCEL HAS NO AGENT RESOURCE. Bedrock and Vertex have an agent
object to list; Vercel hosts web apps and functions, and an AI SDK agent is just code in
one. What a scan can see without reading code or traffic is configuration, so a project
is flagged when either

* one of its environment variables is named exactly as an LLM provider's key
  (`LLM_PROVIDER_ENV_KEYS`: `OPENAI_API_KEY`, `AI_GATEWAY_API_KEY`, ...), or
* an AI integration from the Vercel Marketplace is installed with access to it: one
  tagged `tag_ai` or `tag_agents` by Vercel, or one of the AI providers in
  `AI_INTEGRATION_SLUGS`.

Only variable NAMES are read, never values (see `client`). The match is on the exact
name, so a renamed key (`MY_OPENAI_KEY`) is missed rather than guessed at.

THE BLIND SPOT: OIDC. A project that calls the Vercel AI Gateway from a Vercel
deployment authenticates with the deployment's OIDC token and needs no API key at all,
so it has nothing for this scan to see unless an AI integration is also attached. Such
a project is not reported. The docs section says so.

ONE PROJECT, ONE RECORD. `external_id` is the project ID (`prj_...`), stable across
renames; the team ID is the address's instance and the project's function region its
scope ("global" when Vercel reports none -- a project is not regional the way a Vertex
engine is, but a CLOUD address must carry a scope).

NO SERVICE NAMES. Vertex puts the engine's resource name in `service_names` because
existing tasks are already keyed by exactly that string. Nothing is keyed by a Vercel
project's name, and GenAI Engine's resolver both joins on and CLAIMS every service name
a record carries: a project called `web` or `api` would take that name in the org's
mapping table, and the next trace from any service called `web` would land on this
project's task. A project's telemetry service name is whatever its code passes to
`registerOTel`, which this scan cannot see, so none is claimed.

COMPLETENESS BEFORE RECORDS. Every call is made before the first batch is handed over,
so the job log says how much of the team was read -- pages, filtered, flagged, a page
cap, a stop -- before anything is published. The cost is that a failure on project 40
publishes nothing, rather than 39 projects' records; a team's projects are few enough
that the rescan is cheap.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Callable, ClassVar, Iterator, Mapping, Optional, Sequence

from arthur_client.api_bindings import DiscoverySourceConfigSpec
from arthur_common.models.agent_discovery_schemas import DiscoveredAgentRecord
from arthur_common.models.agent_governance_schemas import (
    CloudAgentCreationSource,
    SourceAddress,
)

from discovery.cloud.vercel_ai.client import (
    INTEGRATIONS_PATH,
    Cursor,
    IntegrationConfiguration,
    Project,
    ScanStopped,
    VercelClient,
    VercelSettings,
)
from discovery.endpoint.scope import parse_group_names
from job_executors.discovery_scan import DiscoveryConfigurationError

# The wire value. Identical to arthur-client's DiscoverySourceVendor member.
VENDOR = "vercel_ai"

# Field names. Identical to the Platform catalog's field names, one constant each.
TEAM_ID_FIELD = "team_id"
ACCESS_TOKEN_FIELD = "access_token"
INCLUDE_PROJECTS_FIELD = "include_projects"

# What the address's scope says for a project Vercel reports no function region for.
GLOBAL_SCOPE = "global"

# Environment variable names that mean a project calls an LLM provider: the names the
# AI SDK's providers read by default, and the AI Gateway's. Exact, case-sensitive.
LLM_PROVIDER_ENV_KEYS = frozenset(
    {
        "AI_GATEWAY_API_KEY",
        "OPENAI_API_KEY",
        "AZURE_OPENAI_API_KEY",
        "ANTHROPIC_API_KEY",
        "GOOGLE_GENERATIVE_AI_API_KEY",
        "GEMINI_API_KEY",
        "XAI_API_KEY",
        "GROQ_API_KEY",
        "MISTRAL_API_KEY",
        "COHERE_API_KEY",
        "DEEPSEEK_API_KEY",
        "PERPLEXITY_API_KEY",
        "TOGETHER_AI_API_KEY",
        "FIREWORKS_API_KEY",
        "CEREBRAS_API_KEY",
        "DEEPINFRA_API_KEY",
        "OPENROUTER_API_KEY",
        "REPLICATE_API_TOKEN",
        "FAL_KEY",
        "HF_TOKEN",
    },
)

# Vercel's own integration tags for AI products.
AI_INTEGRATION_TAGS = frozenset({"tag_ai", "tag_agents"})

# Marketplace slugs of AI providers, for a configuration whose tags Vercel did not
# return. Lower-case.
AI_INTEGRATION_SLUGS = frozenset(
    {
        "openai",
        "xai",
        "groq",
        "fal",
        "deepinfra",
        "together-ai",
        "elevenlabs",
        "perplexity",
        "replicate",
    },
)

# Pages of `GET /v10/projects` read before giving up: 100 x 100 projects. A team past
# that is reported as capped rather than read for ever.
MAX_PROJECT_PAGES = 100

# Records per published batch. Every call has been made already; this only bounds how
# much one failed publish costs.
BATCH_SIZE = 100

ClientFactory = Callable[[VercelSettings, logging.Logger], VercelClient]


def _default_client(settings: VercelSettings, logger: logging.Logger) -> VercelClient:
    return VercelClient(settings, logger=logger)


@dataclass
class _Tally:
    """How much of the team one scan read, for the completeness report."""

    listed: int = 0
    pages: int = 0
    unaddressable: int = 0
    page_cap_hit: bool = False
    repeated_cursor: bool = False
    filtered_out: int = 0
    in_scope: int = 0
    scanned: int = 0
    gone: int = 0
    flagged_by_env: int = 0
    flagged_by_integration: int = 0
    skipped_undated: int = 0
    integrations_read: bool = False
    integrations_denied: bool = False
    listing_complete: bool = False
    stopped: bool = False
    missing_names: list[str] = field(default_factory=list)


class VercelConnector:
    """Implements `job_executors.discovery_scan.DiscoverySourceConnector` and
    `AcceptsStopCheck` (structurally; the Protocols are not imported).

    Holds one scan's stop check, which is safe only because a connector is built fresh
    for every scan -- see `DiscoveryConnectorFactory`.
    """

    # Must equal the set of fields the Platform catalog marks is_sensitive.
    SENSITIVE_FIELDS: ClassVar[frozenset[str]] = frozenset({ACCESS_TOKEN_FIELD})

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
        """Every flagged project in the source's team, in batches.

        `lookback_hours` is not applied: see the module docstring. `logger` is the
        JOB's, so what this reports reaches the Platform job log.
        """
        settings = settings_from(credentials, source_fields)
        include = parse_group_names(source_fields.get(INCLUDE_PROJECTS_FIELD))
        client = self._client_factory(settings, logger)
        client.stop_when(self._should_stop)

        logger.info(
            "Vercel scan starting against team %s, %s",
            settings.team_id,
            (
                f"limited to {len(include)} project(s) by {INCLUDE_PROJECTS_FIELD}"
                if include
                else "all projects"
            ),
        )

        tally = _Tally()
        records: list[DiscoveredAgentRecord] = []
        try:
            self._collect(client, settings, include, logger, tally, records)
        except ScanStopped:
            tally.stopped = True

        # Reported before the first batch is handed over, so a publish that fails part
        # way cannot leave a capped or partial answer unannounced.
        _report(logger, tally, len(records))
        for start in range(0, len(records), BATCH_SIZE):
            yield records[start : start + BATCH_SIZE]

    def _checkpoint(self) -> None:
        """Asked before every vendor call."""
        if self._should_stop():
            raise ScanStopped()

    def _collect(
        self,
        client: VercelClient,
        settings: VercelSettings,
        include: tuple[str, ...],
        logger: logging.Logger,
        tally: _Tally,
        records: list[DiscoveredAgentRecord],
    ) -> None:
        """Every call the scan makes, appending to `records` as projects are judged, so
        a stop part-way still hands over what was found."""
        projects = self._list_projects(client, logger, tally)

        in_scope = _in_scope(projects, include, tally)
        tally.in_scope = len(in_scope)
        if not in_scope:
            return

        self._checkpoint()
        configurations = client.integration_configurations()
        if configurations is None:
            tally.integrations_denied = True
            logger.warning(
                "Vercel refused GET %s to this token (403), so attached AI "
                "integrations were not checked; projects are judged by environment "
                "variable names alone.",
                INTEGRATIONS_PATH,
            )
            configurations = []
        else:
            tally.integrations_read = True
        ai_integrations = [c for c in configurations if is_ai_integration(c)]

        for project in in_scope:
            if any(c.covers(project.id) for c in ai_integrations):
                # Already an agent; its variables would not change that, so they are
                # not read.
                tally.scanned += 1
                tally.flagged_by_integration += 1
                self._add(project, settings, logger, tally, records)
                continue

            self._checkpoint()
            env = client.project_env(project.id)
            if env is None:
                tally.gone += 1
                logger.warning(
                    "Vercel project %s was listed but its environment variables "
                    "answered 404; it was probably deleted during the scan, and is "
                    "skipped.",
                    project.id,
                )
                continue
            tally.scanned += 1
            if env.hidden_production_count > 0:
                logger.warning(
                    "Vercel project %s has %s production environment variable(s) this "
                    "token cannot see, so an LLM provider key among them would be "
                    "missed. A token whose user can view production variables sees "
                    "them.",
                    project.id,
                    env.hidden_production_count,
                )
            if env.more_pages:
                logger.warning(
                    "Vercel project %s has more environment variables than one answer "
                    "carried; only the first page was checked.",
                    project.id,
                )
            if any(name.key in LLM_PROVIDER_ENV_KEYS for name in env.names):
                tally.flagged_by_env += 1
                self._add(project, settings, logger, tally, records)

    def _list_projects(
        self,
        client: VercelClient,
        logger: logging.Logger,
        tally: _Tally,
    ) -> list[Project]:
        """Every page of the team's projects, de-duplicated by id.

        A cursor Vercel hands back twice ends the listing rather than looping on it,
        and so does `MAX_PROJECT_PAGES`; both are reported as incomplete.
        """
        projects: dict[str, Project] = {}
        cursor: Optional[Cursor] = None
        seen: set[Cursor] = set()
        while True:
            if tally.pages >= MAX_PROJECT_PAGES:
                tally.page_cap_hit = True
                return list(projects.values())
            self._checkpoint()
            page = client.projects_page(cursor)
            tally.pages += 1
            tally.unaddressable += page.unaddressable
            for project in page.projects:
                projects.setdefault(project.id, project)
            tally.listed = len(projects)
            if page.next is None:
                tally.listing_complete = True
                return list(projects.values())
            if page.next in seen:
                tally.repeated_cursor = True
                return list(projects.values())
            seen.add(page.next)
            cursor = page.next

    @staticmethod
    def _add(
        project: Project,
        settings: VercelSettings,
        logger: logging.Logger,
        tally: _Tally,
        records: list[DiscoveredAgentRecord],
    ) -> None:
        record = record_for(project, settings, logger)
        if record is None:
            tally.skipped_undated += 1
        else:
            records.append(record)


def _in_scope(
    projects: list[Project],
    include: tuple[str, ...],
    tally: _Tally,
) -> list[Project]:
    """The projects `include_projects` names, by name or id; all of them when empty."""
    if not include:
        return projects
    wanted = set(include)
    kept = [p for p in projects if p.name in wanted or p.id in wanted]
    tally.filtered_out = len(projects) - len(kept)
    found = {p.name for p in kept} | {p.id for p in kept}
    tally.missing_names = [name for name in include if name not in found]
    return kept


def is_ai_integration(configuration: IntegrationConfiguration) -> bool:
    """An active configuration Vercel tags as AI, or one of the known AI providers."""
    return configuration.active and bool(
        configuration.tag_ids & AI_INTEGRATION_TAGS
        or configuration.slug in AI_INTEGRATION_SLUGS,
    )


def last_seen_of(project: Project) -> Optional[datetime]:
    """The latest sign of life Vercel reported, as an aware UTC datetime."""
    if not project.activity_ms:
        return None
    return datetime.fromtimestamp(max(project.activity_ms) / 1000, tz=timezone.utc)


def record_for(
    project: Project,
    settings: VercelSettings,
    logger: logging.Logger,
) -> Optional[DiscoveredAgentRecord]:
    """One flagged project's record, or None when Vercel gave no time to date it by."""
    last_seen = last_seen_of(project)
    if last_seen is None:
        logger.warning(
            "Vercel project %s reported no deployment or update time; skipped, because "
            "last_seen is required and inventing one would date the record to the scan",
            project.id,
        )
        return None
    return DiscoveredAgentRecord(
        external_id=project.id,
        name=project.name,
        last_seen=last_seen,
        creation_source=CloudAgentCreationSource(
            vendor=VENDOR,
            address=SourceAddress(
                instance=settings.team_id,
                scope=project.region or GLOBAL_SCOPE,
                resource_id=project.id,
            ),
        ),
    )


def _report(logger: logging.Logger, tally: _Tally, records: int) -> None:
    """Say how complete the answer is. A partial answer must not read as a full one."""
    logger.info(
        "Vercel scan listed %s project(s) over %s page(s); %s outside %s; %s scanned; "
        "%s flagged (%s by environment variable name, %s by AI integration); "
        "%s record(s), %s skipped",
        tally.listed,
        tally.pages,
        tally.filtered_out,
        INCLUDE_PROJECTS_FIELD,
        tally.scanned,
        tally.flagged_by_env + tally.flagged_by_integration,
        tally.flagged_by_env,
        tally.flagged_by_integration,
        records,
        tally.skipped_undated + tally.gone,
    )
    if tally.stopped:
        logger.warning(
            "Vercel scan stopped early on request after scanning %s of %s project(s)%s; "
            "the records found so far are all that is reported.",
            tally.scanned,
            tally.in_scope or tally.listed,
            "" if tally.listing_complete else ", before the project list was complete",
        )
    if tally.page_cap_hit:
        logger.warning(
            "Vercel project list stopped at %s pages (%s projects); projects past that "
            "were not read. Limit the source with %s.",
            tally.pages,
            tally.listed,
            INCLUDE_PROJECTS_FIELD,
        )
    if tally.repeated_cursor:
        logger.warning(
            "Vercel returned a page cursor it had already returned, so the project "
            "list was ended after %s page(s) rather than read in a loop; projects past "
            "that point may be missing.",
            tally.pages,
        )
    if tally.unaddressable:
        logger.warning(
            "Vercel returned %s project(s) without an id; skipped, because the id is "
            "the record's identity.",
            tally.unaddressable,
        )
    if tally.missing_names and tally.listing_complete:
        # Only said of a complete listing: a capped or stopped one may simply not have
        # reached the project yet.
        logger.warning(
            "%s names project(s) not in this team, matched by name or id: %s",
            INCLUDE_PROJECTS_FIELD,
            ", ".join(tally.missing_names),
        )
    if tally.listing_complete and tally.listed == 0:
        logger.warning(
            "Vercel listed no projects for team_id. If projects are expected, check "
            "that the token was created with access to that team.",
        )


def settings_from(
    credentials: Mapping[str, Optional[str]],
    source_fields: Mapping[str, str],
) -> VercelSettings:
    """The team from the source's fields, the token from its credentials. The team ID
    is not a secret, but neither is ever echoed into an error: only field names are."""
    team_id = (source_fields.get(TEAM_ID_FIELD) or "").strip()
    token = (credentials.get(ACCESS_TOKEN_FIELD) or "").strip()
    missing = [
        name
        for name, value in ((TEAM_ID_FIELD, team_id), (ACCESS_TOKEN_FIELD, token))
        if not value
    ]
    if missing:
        raise DiscoveryConfigurationError(
            f"Vercel source is missing required field(s): {', '.join(missing)}. "
            f"{TEAM_ID_FIELD} is a source field; {ACCESS_TOKEN_FIELD} is a secret.",
        )
    if any(c.isspace() or not c.isprintable() for c in token):
        # requests would refuse the header itself, with the header's value -- the
        # token -- in its message.
        raise DiscoveryConfigurationError(
            f"Vercel source's {ACCESS_TOKEN_FIELD} contains whitespace or control "
            f"characters. Paste the token alone.",
        )
    if any(c.isspace() or not c.isprintable() for c in team_id):
        raise DiscoveryConfigurationError(
            f"Vercel source's {TEAM_ID_FIELD} contains whitespace or control "
            f"characters. Use the team's ID, which starts team_.",
        )
    return VercelSettings(team_id=team_id, access_token=token)
