"""Vercel's side of a DISCOVER_AGENTS scan.

Lists one team's projects and emits one record per project that looks like it runs an
AI agent. The project list is an inventory, so the scan's lookback is not applied to it:
a project deployed a year ago and still live is still there. The lookback IS applied to
the two signals that are activity rather than configuration -- Agent Runs and the
Observability Plus metrics -- capped at `ACTIVITY_WINDOW_MAX_HOURS`, and a lookback of 0
reads that cap.

A HEURISTIC, BECAUSE VERCEL HAS NO AGENT RESOURCE. Bedrock and Vertex have an agent
object to list; Vercel hosts web apps and functions, and an AI SDK agent is just code in
one. A project is flagged when any of these says it calls an LLM or runs an agent:

* CONFIGURATION. One of its environment variables, or a team-shared variable linked to
  it, is named exactly as an LLM provider's key (`LLM_PROVIDER_ENV_KEYS`); or an AI
  integration from the Vercel Marketplace is installed with access to it (tagged
  `tag_ai`/`tag_agents` by Vercel, or one of `AI_INTEGRATION_SLUGS`). Exact names
  only: a renamed key (`LLM_TOKEN`) is missed rather than guessed at, and there is
  deliberately no `*_TOKEN` heuristic.
* AGENT RUNS. Vercel lists the project among the team's projects with production Agent
  Runs. The strongest signal -- it is Vercel saying the project runs an agent -- but
  read from an UNDOCUMENTED endpoint (see `client`) that may change; any failure of it
  is one warning and the scan goes on without it.
* OBSERVABILITY PLUS, when the team has it. The project sent AI Gateway requests, or
  requests to an LLM provider's API host (`LLM_API_HOSTS`, `LLM_API_HOST_PATTERNS`).
  This is what sees a project that calls the AI Gateway with its deployment's OIDC
  token, or keeps its key in a secrets manager: neither has a variable to find. A team
  without Observability Plus answers 402, which is logged as "Observability Plus not
  enabled" and nothing more.
* CODE, ONLY WHEN THE SOURCE OPTS IN (`read_deployment_sources`). The `package.json` of
  the project's latest production deployment depends on an AI library
  (`AI_PACKAGE_NAMES`, `AI_PACKAGE_PREFIXES`). Vercel keeps a file tree only for a
  deployment made by the CLI, the API or v0, so a Git deployment is skipped, from its
  `meta` when that names a commit and otherwise from Vercel's 404.

Only variable NAMES are read, never values, and only a package.json's dependency
NAMES, never the rest of it (see `client`).

ONE CALL TO AN LLM IS NOT AN AGENT, AND THIS CANNOT ALWAYS TELL. A single-call
summarizer with `OPENAI_API_KEY` is flagged exactly like an agent with tools: keys,
integrations, packages and traffic all say "calls an LLM". Agent Runs is the one signal
that says "agent". Each flagged project's evidence is logged (`flagged by: ...`), so the
Platform's reviewer can tell them apart; the record contract has no field for it yet.

EVIDENCE IN THE JOB LOG, MODELS ON THE RECORD. `DiscoveredAgentRecord` (arthur-common
2.4.97, unchanged through 2.4.99) has no field for which signal found an agent, so each
flagged project gets one job-log line naming every signal that fired for it: variable
names and their targets, integration slugs, package names, its Agent Runs count, AI
Gateway models and auth methods, LLM API hosts. The AI Gateway's `ai_model` values go
on the record as `llm_models`: that is Vercel stating the model, not a guess from a
name.

A KEY TARGETED ONLY AT PREVIEW OR DEVELOPMENT STILL FLAGS THE PROJECT. Code that reads
the key exists in the project whichever environment it is set for, and a preview-only
key is how an agent is often tried before it ships. The evidence line names the
targets, so a reviewer sees it is not in production.

ONE PROJECT, ONE RECORD. `external_id` is the project ID (`prj_...`), stable across
renames; the team ID is the address's instance and its scope is always "global": Vercel
has no region (a function region is where code runs, not where the project lives), but
a CLOUD address must carry a scope. `last_seen` is the latest of the project's
`updatedAt` and its deployments' `readyAt`/`createdAt`, not `updatedAt` alone, because
a project redeployed without a settings change is still active.

NO SERVICE NAMES. Vertex puts the engine's resource name in `service_names` because
existing tasks are already keyed by exactly that string. Nothing is keyed by a Vercel
project's name, and GenAI Engine's resolver both joins on and CLAIMS every service name
a record carries: a project called `web` or `api` would take that name in the org's
mapping table, and the next trace from any service called `web` would land on this
project's task. A project's telemetry service name is whatever its code passes to
`registerOTel`, which this scan cannot see, so none is claimed.

COMPLETENESS BEFORE RECORDS. Every call is made before the first batch is handed over,
so the job log says how much of the team was read -- pages, filtered, flagged,
unreadable, which extra signals were read, a page cap, a stop -- before anything is
published. A call that fails part way still publishes the records collected before it,
after that report, and then re-raises the failure unchanged, so the scan still fails
with Vercel's status.

ONE PROJECT'S FAILURE IS PARTIAL. A 403, 404 or 5xx (after retries) on one project's
variables skips that project with a warning naming its id and status, unless another
signal already flagged it, and the scan goes on. A 401 means the token is invalid for
every project, so it fails the scan. None of the extra signals can fail a scan.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Callable, ClassVar, Iterator, Mapping, Optional, Sequence

import requests
from arthur_client.api_bindings import DiscoverySourceConfigSpec
from arthur_common.models.agent_discovery_schemas import DiscoveredAgentRecord
from arthur_common.models.agent_governance_schemas import (
    CloudAgentCreationSource,
    LLMModel,
    SourceAddress,
)

from discovery.cloud.vercel_ai.client import (
    AGENT_RUNS_PATH,
    INTEGRATIONS_PATH,
    OBSERVABILITY_QUERY_PATH,
    SHARED_ENV_PATH,
    Cursor,
    IntegrationConfiguration,
    MetricAnswer,
    Project,
    ScanStopped,
    VercelClient,
    VercelError,
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
READ_DEPLOYMENT_SOURCES_FIELD = "read_deployment_sources"

# What `read_deployment_sources` accepts: the catalog's enum. Absent or empty is "false".
BOOLEAN_FIELD_VALUES = ("true", "false")

# Every record's address scope: Vercel has no region.
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

# package.json dependencies that mean a project calls an LLM or runs an agent: exact
# names, and scopes or name prefixes (`@aws-sdk/client-bedrock` covers
# `client-bedrock-runtime` and `client-bedrock-agent-runtime`).
AI_PACKAGE_NAMES = frozenset({"ai", "openai", "langchain", "eve"})
AI_PACKAGE_PREFIXES = (
    "@ai-sdk/",
    "@anthropic-ai/",
    "@mastra/",
    "@aws-sdk/client-bedrock",
)

# Observability Plus metrics, and what each is grouped by.
AI_GATEWAY_METRIC = "vercel.ai_gateway_request.count"
AI_GATEWAY_GROUP_BY = ("project_name", "ai_model", "auth_method")
EXTERNAL_API_METRIC = "vercel.external_api_request.count"
EXTERNAL_API_GROUP_BY = ("project_name", "request_hostname")

# LLM provider API hosts, matched exactly and lower-case.
LLM_API_HOSTS = frozenset(
    {
        "api.openai.com",
        "api.anthropic.com",
        "ai-gateway.vercel.sh",
        "generativelanguage.googleapis.com",
        "aiplatform.googleapis.com",
        "api.groq.com",
        "api.mistral.ai",
    },
)
# And by (prefix, suffix): Bedrock's regional runtime hosts, Vertex AI's regional hosts
# and Azure OpenAI resources.
LLM_API_HOST_PATTERNS: tuple[tuple[str, str], ...] = (
    ("bedrock-runtime.", ".amazonaws.com"),
    ("", "-aiplatform.googleapis.com"),
    ("", ".openai.azure.com"),
)

# How far back Agent Runs and the observability metrics are read, at most, and what a
# lookback of 0 reads: Observability Plus keeps 30 days.
ACTIVITY_WINDOW_MAX_HOURS = 30 * 24

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
class Evidence:
    """Every signal that fired for one project. Names only, never values."""

    # (variable name, its targets)
    env_keys: list[tuple[str, tuple[str, ...]]] = field(default_factory=list)
    shared_env_keys: list[tuple[str, tuple[str, ...]]] = field(default_factory=list)
    integrations: set[str] = field(default_factory=set)
    packages: set[str] = field(default_factory=set)
    package_path: str = ""
    # Listed by Agent Runs; its count when the answer carried one.
    agent_runs: bool = False
    agent_run_count: Optional[int] = None
    gateway_models: set[str] = field(default_factory=set)
    gateway_auth_methods: set[str] = field(default_factory=set)
    gateway_requests: bool = False
    llm_hosts: set[str] = field(default_factory=set)

    def signals(self) -> list[str]:
        """The kinds of signal that fired, in a fixed order."""
        fired = [
            ("environment variable", bool(self.env_keys)),
            ("shared variable", bool(self.shared_env_keys)),
            ("AI integration", bool(self.integrations)),
            ("Agent Runs", self.agent_runs),
            ("AI Gateway", self.gateway_requests),
            ("LLM API host", bool(self.llm_hosts)),
            ("package", bool(self.packages)),
        ]
        return [name for name, on in fired if on]

    def describe(self) -> str:
        parts: list[str] = []
        if self.env_keys:
            parts.append("environment variable(s) " + _keys(self.env_keys))
        if self.shared_env_keys:
            parts.append("shared variable(s) " + _keys(self.shared_env_keys))
        if self.integrations:
            parts.append("AI integration(s) " + ", ".join(sorted(self.integrations)))
        if self.agent_runs:
            count = (
                f"{self.agent_run_count} production run(s)"
                if self.agent_run_count is not None
                else "production runs"
            )
            parts.append(f"Agent Runs ({count})")
        if self.gateway_requests:
            detail = []
            if self.gateway_models:
                detail.append("models " + ", ".join(sorted(self.gateway_models)))
            if self.gateway_auth_methods:
                detail.append("auth " + ", ".join(sorted(self.gateway_auth_methods)))
            parts.append(
                "AI Gateway requests" + (f" ({'; '.join(detail)})" if detail else ""),
            )
        if self.llm_hosts:
            parts.append("LLM API host(s) " + ", ".join(sorted(self.llm_hosts)))
        if self.packages:
            parts.append(
                f"package(s) {', '.join(sorted(self.packages))} in {self.package_path}",
            )
        return "; ".join(parts)


def _keys(keys: list[tuple[str, tuple[str, ...]]]) -> str:
    return ", ".join(
        f"{key} ({', '.join(targets) if targets else 'no target'})"
        for key, targets in keys
    )


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
    flagged: int = 0
    by_signal: dict[str, int] = field(default_factory=dict)
    skipped_undated: int = 0
    unreadable: int = 0
    unreadable_skipped: int = 0
    failed: bool = False
    listing_complete: bool = False
    stopped: bool = False
    missing_names: list[str] = field(default_factory=list)
    # How each extra signal went, for the report: "not read" until it is asked.
    integrations: str = "not read"
    shared_env: str = "not read"
    agent_runs: str = "not read"
    observability: str = "not read"
    sources_read: int = 0
    sources_no_tree: int = 0
    sources_no_manifest: int = 0
    sources_no_deployment: int = 0
    sources_denied: int = 0
    sources_failed: int = 0


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

        `lookback_hours` is applied to Agent Runs and the observability metrics only:
        see the module docstring. `logger` is the JOB's, so what this reports reaches
        the Platform job log.
        """
        settings = settings_from(credentials, source_fields)
        include = parse_group_names(source_fields.get(INCLUDE_PROJECTS_FIELD))
        client = self._client_factory(settings, logger)
        client.stop_when(self._should_stop)

        logger.info(
            "Vercel scan starting against team %s, %s; deployment sources %s",
            settings.team_id,
            (
                f"limited to {len(include)} project(s) by {INCLUDE_PROJECTS_FIELD}"
                if include
                else "all projects"
            ),
            "read" if settings.read_deployment_sources else "not read",
        )

        tally = _Tally()
        records: list[DiscoveredAgentRecord] = []
        try:
            self._collect(
                client,
                settings,
                include,
                lookback_hours,
                logger,
                tally,
                records,
            )
        except ScanStopped:
            tally.stopped = True
        except Exception:
            if records:
                tally.failed = True
                _report(logger, tally, len(records), settings)
                yield from _batches(records)
            raise

        # Reported before the first batch is handed over, so a publish that fails part
        # way cannot leave a capped or partial answer unannounced.
        _report(logger, tally, len(records), settings)
        yield from _batches(records)

    def _checkpoint(self) -> None:
        """Asked before every vendor call."""
        if self._should_stop():
            raise ScanStopped()

    def _collect(
        self,
        client: VercelClient,
        settings: VercelSettings,
        include: tuple[str, ...],
        lookback_hours: int,
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
        evidence = {p.id: Evidence() for p in in_scope}
        resolve = _resolver(in_scope)

        self._integrations(client, in_scope, evidence, logger, tally)
        self._shared_env(client, evidence, logger, tally)
        window = activity_window(lookback_hours, client.now())
        self._agent_runs(client, settings, window, resolve, evidence, logger, tally)
        self._observability(client, window, resolve, evidence, logger, tally)

        for project in in_scope:
            found = evidence[project.id]
            self._checkpoint()
            env_read = self._project_env(client, project, found, logger, tally)
            if settings.read_deployment_sources:
                self._deployment_packages(client, project, found, logger, tally)
            if env_read:
                tally.scanned += 1
            signals = found.signals()
            if not signals:
                if not env_read:
                    tally.unreadable_skipped += 1
                continue
            tally.flagged += 1
            for signal in signals:
                tally.by_signal[signal] = tally.by_signal.get(signal, 0) + 1
            self._add(project, found, settings, logger, tally, records)

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

    def _integrations(
        self,
        client: VercelClient,
        in_scope: list[Project],
        evidence: dict[str, Evidence],
        logger: logging.Logger,
        tally: _Tally,
    ) -> None:
        self._checkpoint()
        configurations = client.integration_configurations()
        if configurations is None:
            tally.integrations = "refused (403)"
            logger.warning(
                "Vercel refused GET %s to this token (403), so attached AI "
                "integrations were not checked; projects are judged by the other "
                "signals.",
                INTEGRATIONS_PATH,
            )
            return
        tally.integrations = "read"
        ai_integrations = [c for c in configurations if is_ai_integration(c)]
        for project in in_scope:
            for configuration in ai_integrations:
                if configuration.covers(project.id):
                    evidence[project.id].integrations.add(
                        configuration.slug or configuration.integration_id or "?",
                    )

    def _shared_env(
        self,
        client: VercelClient,
        evidence: dict[str, Evidence],
        logger: logging.Logger,
        tally: _Tally,
    ) -> None:
        """Team-shared variables named as an LLM provider key flag the projects they
        are linked to. Any failure is a warning: project variables still count."""
        self._checkpoint()
        try:
            shared = client.shared_env()
        except (VercelError, requests.RequestException) as exc:
            tally.shared_env = f"not read ({_failure(exc)})"
            logger.warning(
                "Vercel GET %s (team-shared environment variables) answered %s, so "
                "shared variables were not checked; the scan goes on without them.",
                SHARED_ENV_PATH,
                _failure(exc),
            )
            return
        tally.shared_env = f"read ({len(shared.names)} variable(s))"
        if shared.more_pages:
            logger.warning(
                "Vercel has more team-shared environment variables than one answer "
                "carried; only the first page was checked.",
            )
        for name in shared.names:
            if name.key not in LLM_PROVIDER_ENV_KEYS:
                continue
            for project_id in sorted(name.project_ids):
                if project_id in evidence:
                    evidence[project_id].shared_env_keys.append(
                        (name.key, name.targets),
                    )

    def _agent_runs(
        self,
        client: VercelClient,
        settings: VercelSettings,
        window: tuple[int, int],
        resolve: Callable[[Optional[str], Optional[str]], Optional[str]],
        evidence: dict[str, Evidence],
        logger: logging.Logger,
        tally: _Tally,
    ) -> None:
        """Projects with production Agent Runs. UNDOCUMENTED ENDPOINT: any failure, or
        an answer not in the shape expected, is one warning and nothing more."""
        self._checkpoint()
        try:
            team = client.team_slug()
        except (VercelError, requests.RequestException) as exc:
            # The Vercel CLI sends a linked project's team ID in `teamSlug`, so the ID
            # is the fallback.
            team = settings.team_id
            logger.info(
                "Vercel GET /v2/teams/{teamId} answered %s, so Agent Runs is asked by "
                "team ID rather than slug.",
                _failure(exc),
            )
        self._checkpoint()
        try:
            listed = client.agent_runs_projects(team, window)
        except (VercelError, requests.RequestException) as exc:
            tally.agent_runs = f"not read ({_failure(exc)})"
            logger.warning(
                "Vercel Agent Runs (GET https://vercel.com%s, an undocumented endpoint "
                "that may change) answered %s, so Agent Runs was not checked; the scan "
                "goes on without it.",
                AGENT_RUNS_PATH,
                _failure(exc),
            )
            return
        matched = unmatched = 0
        for entry in listed:
            if entry.runs is not None and entry.runs <= 0:
                continue
            project_id = resolve(entry.project_id, entry.project_name)
            if project_id is None:
                unmatched += 1
                continue
            matched += 1
            found = evidence[project_id]
            found.agent_runs = True
            if entry.runs is not None:
                found.agent_run_count = (found.agent_run_count or 0) + entry.runs
        tally.agent_runs = f"read ({matched} project(s) with production runs)"
        if unmatched:
            logger.info(
                "Vercel Agent Runs named %s project(s) outside this scan's projects; "
                "they are not reported.",
                unmatched,
            )

    def _observability(
        self,
        client: VercelClient,
        window: tuple[int, int],
        resolve: Callable[[Optional[str], Optional[str]], Optional[str]],
        evidence: dict[str, Evidence],
        logger: logging.Logger,
        tally: _Tally,
    ) -> None:
        """AI Gateway and LLM API traffic per project, from Observability Plus. A team
        without it answers 402; that and every other failure leave the scan going."""
        times = (_iso(window[0]), _iso(window[1]))
        granularity = granularity_for(window[1] - window[0])

        def ask(
            metric: str,
            group_by: Sequence[str],
            odata_filter: Optional[str] = None,
        ) -> MetricAnswer:
            self._checkpoint()
            return client.observability_query(
                metric,
                group_by,
                times,
                granularity,
                odata_filter=odata_filter,
            )

        failures: list[tuple[str, Exception]] = []
        try:
            gateway = ask(AI_GATEWAY_METRIC, AI_GATEWAY_GROUP_BY)
        except (VercelError, requests.RequestException) as exc:
            if _observability_off(exc, logger, tally):
                return
            failures.append((AI_GATEWAY_METRIC, exc))
        else:
            _apply_gateway(gateway, resolve, evidence, logger)

        try:
            hosts = _ask_llm_hosts(ask, logger)
        except (VercelError, requests.RequestException) as exc:
            if _observability_off(exc, logger, tally):
                return
            failures.append((EXTERNAL_API_METRIC, exc))
        else:
            _apply_hosts(hosts, resolve, evidence, logger)

        for metric, failure in failures:
            logger.warning(
                "Vercel POST %s for %s answered %s; that signal was not checked and "
                "the scan goes on without it.",
                OBSERVABILITY_QUERY_PATH,
                metric,
                _failure(failure),
            )
        if not failures:
            tally.observability = "read"
        elif len(failures) == 1:
            tally.observability = f"partly read ({_failure(failures[0][1])})"
        else:
            tally.observability = f"not read ({_failure(failures[0][1])})"

    def _project_env(
        self,
        client: VercelClient,
        project: Project,
        found: Evidence,
        logger: logging.Logger,
        tally: _Tally,
    ) -> bool:
        """Read one project's variable names into its evidence. False when Vercel
        would not say, which skips the project unless another signal flagged it."""
        try:
            env = client.project_env(project.id)
        except VercelError as exc:
            if not env_failure_is_partial(exc.status_code):
                raise
            tally.unreadable += 1
            # The id and status only: the exception's text is not logged.
            logger.warning(
                "Vercel project %s: its environment variables answered HTTP %s, so "
                "they were not checked%s%s.",
                project.id,
                exc.status_code,
                "" if found.signals() else " and it is skipped",
                _PARTIAL_HINTS.get(exc.status_code or 0, ""),
            )
            return False
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
        found.env_keys.extend(
            (name.key, name.targets)
            for name in env.names
            if name.key in LLM_PROVIDER_ENV_KEYS
        )
        return True

    def _deployment_packages(
        self,
        client: VercelClient,
        project: Project,
        found: Evidence,
        logger: logging.Logger,
        tally: _Tally,
    ) -> None:
        """AI libraries in the package.json of the project's latest production
        deployment. Opt-in, one file per project; never fails the scan."""
        deployment = project.production_deployment
        if deployment is None:
            tally.sources_no_deployment += 1
            return
        if deployment.from_git:
            tally.sources_no_tree += 1
            return
        self._checkpoint()
        try:
            manifest = client.deployment_package_json(deployment.id)
        except VercelError as exc:
            if exc.status_code == 404:
                # "File tree not found": a Git deployment, whose meta did not say so.
                tally.sources_no_tree += 1
            elif exc.status_code == 403:
                tally.sources_denied += 1
            else:
                tally.sources_failed += 1
                logger.warning(
                    "Vercel project %s: its production deployment's package.json was "
                    "not read (%s).",
                    project.id,
                    _failure(exc),
                )
            return
        except requests.RequestException as exc:
            tally.sources_failed += 1
            logger.warning(
                "Vercel project %s: its production deployment's package.json was not "
                "read (%s).",
                project.id,
                _failure(exc),
            )
            return
        if manifest is None:
            tally.sources_no_manifest += 1
            return
        tally.sources_read += 1
        packages = {n for n in manifest.dependency_names if is_ai_package(n)}
        if packages:
            found.packages.update(packages)
            found.package_path = manifest.path

    @staticmethod
    def _add(
        project: Project,
        found: Evidence,
        settings: VercelSettings,
        logger: logging.Logger,
        tally: _Tally,
        records: list[DiscoveredAgentRecord],
    ) -> None:
        record = record_for(project, settings, logger, sorted(found.gateway_models))
        if record is None:
            tally.skipped_undated += 1
            return
        records.append(record)
        # The record contract has no evidence field: this line is where it lives.
        logger.info(
            "Vercel project %s flagged by: %s",
            project.id,
            found.describe(),
        )


def _observability_off(
    exc: Exception,
    logger: logging.Logger,
    tally: _Tally,
) -> bool:
    """Whether a failed query means observability is off for this team or token, so
    the other query is not worth asking. Says so when it is."""
    status = getattr(exc, "status_code", None)
    if status == 402:
        tally.observability = "off for this team (402)"
        logger.info(
            "Observability Plus not enabled: Vercel POST %s answered 402 for this team, "
            "so AI Gateway and LLM API traffic were not checked.",
            OBSERVABILITY_QUERY_PATH,
        )
        return True
    if status == 403:
        tally.observability = "refused (403)"
        logger.warning(
            "Vercel refused POST %s to this token (403), so AI Gateway and LLM API "
            "traffic were not checked.",
            OBSERVABILITY_QUERY_PATH,
        )
        return True
    return False


def _ask_llm_hosts(
    ask: Callable[..., MetricAnswer],
    logger: logging.Logger,
) -> MetricAnswer:
    """The LLM-host query, filtered by Vercel. If Vercel refuses the filter (400), the
    same query unfiltered: `_apply_hosts` matches the hosts either way."""
    try:
        return ask(EXTERNAL_API_METRIC, EXTERNAL_API_GROUP_BY, llm_host_filter())
    except VercelError as exc:
        if exc.status_code != 400:
            raise
    logger.warning(
        "Vercel refused the LLM host filter on %s (HTTP 400); asking again without it "
        "and matching the hosts here.",
        EXTERNAL_API_METRIC,
    )
    return ask(EXTERNAL_API_METRIC, EXTERNAL_API_GROUP_BY)


def _apply_gateway(
    answer: MetricAnswer,
    resolve: Callable[[Optional[str], Optional[str]], Optional[str]],
    evidence: dict[str, Evidence],
    logger: logging.Logger,
) -> None:
    for group in answer.groups:
        if group.count is not None and group.count <= 0:
            continue
        project_id = resolve(None, group.dimensions.get("project_name"))
        if project_id is None:
            continue
        found = evidence[project_id]
        found.gateway_requests = True
        model = (group.dimensions.get("ai_model") or "").strip()
        if model:
            found.gateway_models.add(model)
        auth = (group.dimensions.get("auth_method") or "").strip()
        if auth:
            found.gateway_auth_methods.add(auth)
    if answer.at_limit:
        logger.warning(
            "Vercel answered %s with as many groups as were asked for; projects "
            "past that were not checked for AI Gateway requests.",
            AI_GATEWAY_METRIC,
        )


def _apply_hosts(
    answer: MetricAnswer,
    resolve: Callable[[Optional[str], Optional[str]], Optional[str]],
    evidence: dict[str, Evidence],
    logger: logging.Logger,
) -> None:
    for group in answer.groups:
        if group.count is not None and group.count <= 0:
            continue
        host = (group.dimensions.get("request_hostname") or "").strip().lower()
        if not is_llm_host(host):
            continue
        project_id = resolve(None, group.dimensions.get("project_name"))
        if project_id is not None:
            evidence[project_id].llm_hosts.add(host)
    if answer.at_limit:
        logger.warning(
            "Vercel answered %s with as many groups as were asked for; projects "
            "past that were not checked for LLM API requests.",
            EXTERNAL_API_METRIC,
        )


def _batches(
    records: list[DiscoveredAgentRecord],
) -> Iterator[list[DiscoveredAgentRecord]]:
    for start in range(0, len(records), BATCH_SIZE):
        yield records[start : start + BATCH_SIZE]


def _failure(exc: BaseException) -> str:
    """A failed call, as a status or an exception type. Never the exception's text,
    which for a requests error quotes the URL."""
    status = getattr(exc, "status_code", None)
    if status is not None:
        code = getattr(exc, "code", "")
        return f"HTTP {status}" + (f" ({code})" if code else "")
    return type(exc).__name__


def env_failure_is_partial(status: Optional[int]) -> bool:
    """Whether a failed read of one project's variables skips that project rather than
    failing the scan."""
    return status is not None and (status in (403, 404) or status >= 500)


_PARTIAL_HINTS = {
    403: " (its user needs a team role that can view this project)",
    404: " (probably deleted during the scan)",
}


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


def _resolver(
    projects: list[Project],
) -> Callable[[Optional[str], Optional[str]], Optional[str]]:
    """Maps how Agent Runs or a metric names a project -- an id, a name, or either in
    the name's place -- to an in-scope project's id. Names are unique within a team."""
    ids = {p.id for p in projects}
    by_name = {p.name: p.id for p in projects}

    def resolve(project_id: Optional[str], name: Optional[str]) -> Optional[str]:
        if project_id in ids:
            return project_id
        if name is not None:
            if name in by_name:
                return by_name[name]
            if name in ids:
                return name
        return None

    return resolve


def is_ai_integration(configuration: IntegrationConfiguration) -> bool:
    """An active configuration Vercel tags as AI, or one of the known AI providers."""
    return configuration.active and bool(
        configuration.tag_ids & AI_INTEGRATION_TAGS
        or configuration.slug in AI_INTEGRATION_SLUGS,
    )


def is_ai_package(name: str) -> bool:
    """A dependency that is an LLM client or agent framework."""
    return name in AI_PACKAGE_NAMES or name.startswith(AI_PACKAGE_PREFIXES)


def is_llm_host(host: str) -> bool:
    """An LLM provider's API host, lower-case."""
    if host in LLM_API_HOSTS:
        return True
    return any(
        host.startswith(prefix) and host.endswith(suffix) and len(host) > len(suffix)
        for prefix, suffix in LLM_API_HOST_PATTERNS
    )


def llm_host_filter() -> str:
    """The OData filter for `request_hostname` that `is_llm_host` matches, so Vercel
    returns only LLM traffic. Built from the same constants."""
    clauses = [f"request_hostname eq '{host}'" for host in sorted(LLM_API_HOSTS)]
    for prefix, suffix in LLM_API_HOST_PATTERNS:
        ends = f"endswith(request_hostname, '{suffix}')"
        clauses.append(
            (
                f"(startswith(request_hostname, '{prefix}') and {ends})"
                if prefix
                else ends
            ),
        )
    return " or ".join(clauses)


def activity_window(lookback_hours: int, now: float) -> tuple[int, int]:
    """(from, to) in epoch seconds for the activity signals: the lookback, capped at
    `ACTIVITY_WINDOW_MAX_HOURS`, which is also what a lookback of 0 reads."""
    hours = lookback_hours if 0 < lookback_hours <= ACTIVITY_WINDOW_MAX_HOURS else 0
    hours = hours or ACTIVITY_WINDOW_MAX_HOURS
    end = int(now)
    return end - hours * 3600, end


def granularity_for(seconds: int) -> dict[str, int]:
    """The bucket size the Vercel CLI picks for a range this long (`vercel metrics`)."""
    hours = seconds / 3600
    if hours <= 1:
        return {"minutes": 1}
    if hours <= 2:
        return {"minutes": 5}
    if hours <= 12:
        return {"minutes": 15}
    if hours <= 72:
        return {"hours": 1}
    if hours <= 30 * 24:
        return {"hours": 4}
    return {"days": 1}


def _iso(epoch_seconds: int) -> str:
    """UTC, with milliseconds and `Z`, as JavaScript's toISOString writes it."""
    moment = datetime.fromtimestamp(epoch_seconds, tz=timezone.utc)
    return moment.strftime("%Y-%m-%dT%H:%M:%S.000Z")


def last_seen_of(project: Project) -> Optional[datetime]:
    """The latest sign of life Vercel reported, as an aware UTC datetime."""
    if not project.activity_ms:
        return None
    return datetime.fromtimestamp(max(project.activity_ms) / 1000, tz=timezone.utc)


def record_for(
    project: Project,
    settings: VercelSettings,
    logger: logging.Logger,
    models: Sequence[str] = (),
) -> Optional[DiscoveredAgentRecord]:
    """One flagged project's record, or None when Vercel gave no time to date it by.
    `models` are the AI Gateway's `ai_model` values for it, which Vercel states."""
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
        llm_models=[LLMModel(name=m) for m in models] or None,
        creation_source=CloudAgentCreationSource(
            vendor=VENDOR,
            address=SourceAddress(
                instance=settings.team_id,
                scope=GLOBAL_SCOPE,
                resource_id=project.id,
            ),
        ),
    )


def _report(
    logger: logging.Logger,
    tally: _Tally,
    records: int,
    settings: VercelSettings,
) -> None:
    """Say how complete the answer is. A partial answer must not read as a full one."""
    by_signal = ", ".join(
        f"{tally.by_signal[name]} by {name}"
        for name in (
            "environment variable",
            "shared variable",
            "AI integration",
            "Agent Runs",
            "AI Gateway",
            "LLM API host",
            "package",
        )
        if tally.by_signal.get(name)
    )
    logger.info(
        "Vercel scan listed %s project(s) over %s page(s); %s outside %s; %s scanned, "
        "%s unreadable; %s flagged (%s); %s record(s), %s skipped",
        tally.listed,
        tally.pages,
        tally.filtered_out,
        INCLUDE_PROJECTS_FIELD,
        tally.scanned,
        tally.unreadable,
        tally.flagged,
        by_signal or "no signal fired",
        records,
        tally.skipped_undated + tally.unreadable_skipped,
    )
    sources = (
        f"{tally.sources_read} package.json read, {tally.sources_no_tree} Git or "
        f"without a file tree, {tally.sources_no_manifest} without a package.json, "
        f"{tally.sources_no_deployment} without a production deployment, "
        f"{tally.sources_denied} refused, {tally.sources_failed} failed"
        if settings.read_deployment_sources
        else f"not read ({READ_DEPLOYMENT_SOURCES_FIELD} is off)"
    )
    logger.info(
        "Vercel signals read: integrations %s; shared variables %s; Agent Runs %s; "
        "observability %s; deployment sources %s",
        tally.integrations,
        tally.shared_env,
        tally.agent_runs,
        tally.observability,
        sources,
    )
    if tally.sources_denied:
        logger.warning(
            "Vercel refused %s deployment file tree(s) to this token (403); those "
            "projects' package.json were not checked.",
            tally.sources_denied,
        )
    if tally.failed:
        logger.warning(
            "Vercel scan failed part-way after scanning %s of %s project(s); the %s "
            "record(s) found before the failure are published, then the scan fails.",
            tally.scanned,
            tally.in_scope or tally.listed,
            records,
        )
    if tally.unreadable:
        logger.warning(
            "Vercel scan could not read the environment variables of %s project(s), "
            "named above; %s with no other signal were skipped, so the answer is "
            "partial.",
            tally.unreadable,
            tally.unreadable_skipped,
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
    return VercelSettings(
        team_id=team_id,
        access_token=token,
        read_deployment_sources=_boolean_field(
            source_fields,
            READ_DEPLOYMENT_SOURCES_FIELD,
        ),
    )


def _boolean_field(source_fields: Mapping[str, str], name: str) -> bool:
    """A catalog enum of `true`/`false`. Absent or empty is false; anything else is the
    source's to fix, named without echoing what it held."""
    raw = source_fields.get(name)
    value = raw.strip().lower() if isinstance(raw, str) else ""
    if value in ("", "false"):
        return False
    if value == "true":
        return True
    raise DiscoveryConfigurationError(
        f"Vercel source's {name} must be one of: {', '.join(BOOLEAN_FIELD_VALUES)}.",
    )
