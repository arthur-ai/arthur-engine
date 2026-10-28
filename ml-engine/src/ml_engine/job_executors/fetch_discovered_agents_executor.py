"""
Executor for the FETCH_DISCOVERED_AGENTS job (D-10).

The second half of discovery. A scan resolves what a source found onto tasks in GenAI
Engine; this reads those tasks back for one source, converts each to an agent, and
upserts them through `PUT /workspaces/{id}/agents`, where the Platform decides whether
each one is a registered application or an unregistered agent.

Each fetch then also uploads every task on the engine that no discovery source has
reported, such as an agent GenAI Engine only knows from its traces or one created by
hand: no source's own walk will ever carry those, so they ride along with every scan.

Tasks are the seam between the two jobs, so everything this uploads carries a
`task_id` by construction. Running it twice over the same window uploads the same
agents twice: task identity is stable across scans (D-08) and the Platform upserts on
`(workspace_id, data_plane_id, task_id)`, so the second run updates in place.
"""

import logging
from typing import Any, List, Optional

from arthur_client.api_bindings import Agent as ScopeAgent
from arthur_client.api_bindings import AgentsV1Api
from arthur_client.api_bindings import Config as ScopeRuleConfig
from arthur_client.api_bindings import (
    ExamplesConfig,
    FetchDiscoveredAgentsJobSpec,
    KeywordsConfig,
    PIIConfig,
    PutAgents,
    RegexConfig,
    RejectedAgent,
    ToxicityConfig,
)
from arthur_common.models.agent_governance_schemas import (
    CREATION_SOURCE_TYPE_BY_CLASS,
    IdentityBasis,
    NetworkCallerKind,
)
from genai_client import (
    ApiClient,
    Configuration,
    EnrichedTaskResponse,
    TasksApi,
)

from job_log_exporter import REPORT_AS_JOB_ERROR

# Tasks per GET, and so agents per PUT. Well under GenAI Engine's own cap of 1,000:
# every task on a page is enriched from its spans, and the Platform upserts a PUT one
# agent at a time inside a single request, so a smaller page bounds both calls.
FETCH_PAGE_SIZE = 200

# GenAI Engine's own bookkeeping tasks (genai-engine `utils/constants.py`). They are not
# agents, and the agent-tasks response does not say a task is a system task. The
# unmapped task (`__unmapped__`) is a system task too, but is left out of this set: it
# holds the traces of agents that sent no service name, and is uploaded like an agent.
GENAI_ENGINE_SYSTEM_TASK_NAMES = frozenset(
    {"__arthur_system_task__", "__synthetic_dataset_generation__"},
)

# Rejected agents reported one by one before the rest are summarized: each is a log line
# and a job error, so a batch the Platform refused wholesale does not become thousands.
MAX_REPORTED_REJECTIONS = 20

# (connect, read). The generated client defaults to waiting forever, and this job runs
# as a thread in the runner; see `discovery_record_sink.RESOLVE_TIMEOUT_SECONDS`.
AGENT_TASKS_TIMEOUT_SECONDS = (10.0, 120.0)

# A rule's config model, by rule type. Both generated clients decode `config` as the
# first anyOf member that validates, and ToxicityConfig -- every field optional, unknown
# fields kept -- accepts a PII config; serialized again, it gains `threshold` beside the
# PII fields, a shape none of the Agents API's config types accepts, and one such rule
# gets the whole PUT refused. The rule's type says which config it carries.
_RULE_CONFIG_MODELS: dict[
    str,
    type[ExamplesConfig]
    | type[KeywordsConfig]
    | type[PIIConfig]
    | type[RegexConfig]
    | type[ToxicityConfig],
] = {
    "KeywordRule": KeywordsConfig,
    "ModelSensitiveDataRule": ExamplesConfig,
    "PIIDataRule": PIIConfig,
    "RegexRule": RegexConfig,
    "ToxicityRule": ToxicityConfig,
}


class FetchDiscoveredAgentsExecutor:
    def __init__(
        self,
        agents_client: AgentsV1Api,
        logger: logging.Logger,
        genai_engine_url: str,
        genai_engine_api_key: str,
        page_size: int = FETCH_PAGE_SIZE,
    ) -> None:
        self.agents_client = agents_client
        self.logger = logger
        self.genai_engine_url = genai_engine_url
        self.genai_engine_api_key = genai_engine_api_key
        self.page_size = page_size

    def execute(self, job_spec: FetchDiscoveredAgentsJobSpec) -> None:
        """Upload every task the source reported in the window, a page at a time.

        Then upload every task no source has reported, so the agents the engine knows
        only from their own traces or a manual create surface on the same scan as
        the source's.

        Each page is uploaded as it arrives rather than after the last one, so memory
        is bounded by a page whatever the source reported, and a failure part-way
        leaves the pages before it upserted -- which a retry then updates in place.
        """
        workspace_id = str(job_spec.workspace_id)
        data_plane_id = str(job_spec.data_plane_id)
        source_id = str(job_spec.discovery_source_id)
        window = (
            f"reported since {job_spec.reported_since.isoformat()}"
            if job_spec.reported_since is not None
            else "ever reported"
        )
        self.logger.info(
            f"Fetching the tasks discovery source {source_id} {window}",
            extra={
                "workspace_id": workspace_id,
                "data_plane_id": data_plane_id,
                "discovery_source_id": source_id,
            },
        )

        with ApiClient(
            Configuration(
                host=self.genai_engine_url,
                access_token=self.genai_engine_api_key,
            ),
        ) as api_client:
            tasks_api = TasksApi(api_client)
            uploaded = self._upload_walk(
                tasks_api,
                workspace_id,
                data_plane_id,
                source_id=source_id,
                reported_since=job_spec.reported_since,
                # Left out of a source's request, which reads as before.
                unreported=None,
            )
            # No window: these tasks have no report times to measure one against,
            # and every one of them is uploaded again, which the Platform's upsert on
            # task_id makes an update in place. No source's evidence goes with them:
            # none reported them.
            unreported_uploaded = self._upload_walk(
                tasks_api,
                workspace_id,
                data_plane_id,
                source_id=None,
                reported_since=None,
                unreported=True,
            )

        self.logger.info(
            f"Uploaded {uploaded} agent(s) from discovery source {source_id}, and "
            f"{unreported_uploaded} agent(s) no discovery source reported",
            extra={
                "workspace_id": workspace_id,
                "discovery_source_id": source_id,
                "num_upserted": uploaded,
                "num_unreported_upserted": unreported_uploaded,
            },
        )

    def _upload_walk(
        self,
        tasks_api: TasksApi,
        workspace_id: str,
        data_plane_id: str,
        source_id: Optional[str],
        reported_since: Any,
        unreported: Optional[bool],
    ) -> int:
        """Walk one agent-tasks query by cursor, uploading each page as it arrives.

        Uploads carry `source_id`'s evidence, or none when it is None: the unreported
        tasks were reported by no source, so they must not be dressed as this one's.
        """
        uploaded = 0
        after_task_id: str | None = None
        while True:
            tasks: List[EnrichedTaskResponse] = (
                tasks_api.get_agent_tasks_api_v2_agent_tasks_get(
                    discovery_source_id=source_id,
                    reported_since=reported_since,
                    unreported=unreported,
                    after_task_id=after_task_id,
                    page_size=self.page_size,
                    _request_timeout=AGENT_TASKS_TIMEOUT_SECONDS,
                )
            )
            # A GenAI Engine that predates the `unreported` filter ignores it and
            # answers with every task, so the walk drops what the filter would have.
            to_upload = (
                [t for t in tasks if _is_unreported_agent(t)] if unreported else tasks
            )
            if to_upload:
                uploaded += publish_enriched_tasks(
                    self.agents_client,
                    self.logger,
                    workspace_id,
                    data_plane_id,
                    to_upload,
                    discovery_source_id=source_id,
                )
            # A short page is the last one, which is how the endpoint says so. Judged
            # on the page as served, so the cursor walks on past a filtered page.
            if len(tasks) < self.page_size:
                return uploaded
            # Paged by cursor: the next page starts after this one's last task.
            after_task_id = tasks[-1].id


def _is_unreported_agent(task: EnrichedTaskResponse) -> bool:
    """Whether a task belongs in an unreported walk: no source reported it, and it is
    not one of GenAI Engine's bookkeeping tasks (the unmapped task is not one).

    Every task carries provenance; a task no source reported has only its creation
    source's entry, which names no source. Any entry that names one means a source
    reported the task, and that source's own fetch uploads it with its evidence.
    """
    if task.name in GENAI_ENGINE_SYSTEM_TASK_NAMES:
        return False
    provenance = task.to_dict().get("provenance") or {}
    return not any(entry.get("source_id") for entry in provenance.get("sources") or [])


def publish_enriched_tasks(
    agents_client: AgentsV1Api,
    logger: logging.Logger,
    workspace_id: str,
    data_plane_id: str,
    enriched_tasks: List[EnrichedTaskResponse],
    discovery_source_id: Optional[str] = None,
) -> int:
    """Convert enriched tasks to agents and upsert them. Returns how many were upserted.

    With a discovery source, each agent carries that source's evidence; see
    `source_evidence`.
    """
    agent_objects: list[ScopeAgent] = []
    unattributed: list[str] = []
    for task in enriched_tasks:
        agent = enriched_task_to_agent(task, data_plane_id, discovery_source_id)
        if agent is None:
            unattributed.append(task.id)
        else:
            agent_objects.append(agent)

    if unattributed:
        # Left out rather than sent: the Agents API refuses an agent that names no
        # sensor (D-03), and a Platform that predates UP-5069 refuses the whole PUT
        # over one, taking every other task's agent down with it.
        logger.warning(
            f"Not publishing {len(unattributed)} auto-created task(s) that GenAI "
            f"Engine recorded no creation source for: {', '.join(unattributed)}",
            extra={
                "workspace_id": workspace_id,
                "num_unattributed": len(unattributed),
            },
        )
    if not agent_objects:
        return 0

    response = agents_client.put_agents(
        workspace_id=workspace_id,
        put_agents=PutAgents(agents=agent_objects),
    )
    report_rejected_agents(logger, workspace_id, response.rejected or [])
    return len(response.agents)


def report_rejected_agents(
    logger: logging.Logger,
    workspace_id: str,
    rejected: List[RejectedAgent],
) -> None:
    """Report each agent the Agents API did not store as one of the job's errors.

    The Platform stores the rest of the batch and lists these in `rejected` (UP-5069),
    so the PUT succeeds either way; without this, a task whose agent never lands would
    show up nowhere. Reported rather than raised, since the batch's other agents did
    land and a retry would be refused for the same reason. Empty against a Platform
    that predates `rejected`.
    """
    for agent in rejected[:MAX_REPORTED_REJECTIONS]:
        logger.error(
            f"Agents API did not store the agent for task {agent.task_id} "
            f"({agent.name}): {agent.reason}",
            extra={
                **REPORT_AS_JOB_ERROR,
                "workspace_id": workspace_id,
                "task_id": agent.task_id,
            },
        )
    if len(rejected) > MAX_REPORTED_REJECTIONS:
        logger.error(
            f"Agents API did not store {len(rejected)} agent(s) in all; the first "
            f"{MAX_REPORTED_REJECTIONS} are listed above.",
            extra={**REPORT_AS_JOB_ERROR, "workspace_id": workspace_id},
        )


def enriched_task_to_agent(
    enriched_task: EnrichedTaskResponse,
    data_plane_id: str,
    discovery_source_id: Optional[str] = None,
) -> Optional[ScopeAgent]:
    """Convert a genai_client EnrichedTaskResponse to an arthur_client Agent.

    Bridges between the two auto-generated client libraries by converting
    via dict representation and remapping fields.

    The task's provenance is forwarded as GenAI Engine serves it (D-09). The Platform
    reads an agent's `infrastructure` from `provenance.runs_on` and, for an agent
    without provenance, falls back to the reporting engine's own cloud -- so without
    it every endpoint record renders as running on AWS. It crosses as-is: both
    clients generate it from the one arthur_common model, and the Platform's input
    form reads only the fields it stores, leaving the derived `source_classes` behind.

    None for an auto-created task with no creation source. The Agents API refuses an
    agent that names no source (D-03), and naming one here would misreport who found
    it. A task created by hand in GenAI Engine is sent as MANUAL, which is what it is.

    Given the discovery source being fetched, the agent also carries that source's
    evidence (`source_evidence`). Without any, the Platform lifts the creation source
    into a placeholder record, which is what every upload got before.
    """
    task_dict = enriched_task.to_dict()

    creation_source = task_dict.get("creation_source")
    if creation_source is None:
        if enriched_task.is_autocreated:
            return None
        creation_source = {"type": "MANUAL"}

    agent_dict = {
        "name": task_dict.get("name"),
        "task_id": task_dict.get("id"),
        "data_plane_id": data_plane_id,
        "creation_source": creation_source,
        "provenance": task_dict.get("provenance"),
        "model_id": None,
        "num_spans": task_dict.get("num_spans") or 0,
        "is_autocreated": task_dict.get("is_autocreated", True),
        "rules": task_dict.get("rules") or [],
        "last_fetched": task_dict.get("last_fetched"),
        "tools": task_dict.get("tools") or [],
        "sub_agents": task_dict.get("sub_agents") or [],
        "llm_models": task_dict.get("models") or [],
        "data_sources": task_dict.get("data_sources") or [],
    }
    if discovery_source_id is not None:
        evidence = source_evidence(task_dict, discovery_source_id)
        if evidence:
            agent_dict["evidence"] = evidence

    agent = ScopeAgent.from_dict(agent_dict)
    for rule in agent.rules or []:
        model = _RULE_CONFIG_MODELS.get(rule.type.value)
        if model is None or rule.config is None:
            continue
        decoded = rule.config.to_dict() or {}
        rule.config = ScopeRuleConfig(
            model.from_dict(
                {k: v for k, v in decoded.items() if k in model.model_fields},
            ),
        )
    return agent


def source_evidence(
    task_dict: dict[str, Any],
    discovery_source_id: str,
) -> list[dict[str, Any]]:
    """The fetched source's evidence for one task: a record per provenance entry.

    Each entry of this source that names its record becomes that record's evidence,
    keyed on the record's own `external_id` and dated by the source's sighting
    (`last_seen`) and the last scan that reported it (`last_scanned`). Only this
    source's entries: the Platform merges evidence per source, and every other
    source's entries reach it through that source's own fetch.

    An entry with no `external_id` comes from a GenAI Engine that predates serving it,
    so the record cannot be named and the entry is left out. `first_seen` is not sent:
    the Platform derives it from the sightings it receives, and `visibility` is graded
    there too, so the value sent only satisfies the schema.

    The task's observations belong to the record it was created from, which may be
    another source's: that record is picked among every source's records, and the
    observations go on it only if it is one of this source's.
    """
    task_creation_source = task_dict.get("creation_source") or {}
    provenance = task_dict.get("provenance") or {}
    records: list[dict[str, Any]] = []
    for entry in provenance.get("sources") or []:
        external_id = entry.get("external_id")
        creation_type = _CREATION_SOURCE_TYPES.get(entry.get("source_class"))
        last_seen = entry.get("last_seen") or entry.get("last_scanned")
        # The entry GenAI Engine builds from the creation source itself, when no
        # stored report stands in for it, names no source or record, so is skipped
        # here too.
        if (
            entry.get("source_id") is None
            or not external_id
            or creation_type is None
            or last_seen is None
        ):
            continue
        records.append(
            {
                "creation_source": {
                    "type": creation_type,
                    "vendor": entry.get("vendor"),
                    "address": entry.get("address"),
                },
                "external_id": external_id,
                "visibility": "limited",
                "last_seen": last_seen,
                "last_scanned": entry.get("last_scanned"),
                "source_id": entry.get("source_id"),
            },
        )
    evidence = [
        record for record in records if str(record["source_id"]) == discovery_source_id
    ]
    for record in evidence:
        basis = _identity_basis(record["creation_source"], task_creation_source)
        if basis is not None:
            record["creation_source"]["identity_basis"] = basis

    # What the source observed is carried by the record the task was created from, so
    # only that record's evidence can say it.
    observations = task_creation_source.get("observations")
    origin = _creation_record(records, task_creation_source)
    if (
        observations is not None
        and origin is not None
        and any(record is origin for record in evidence)
    ):
        origin["creation_source"]["observations"] = observations
    return evidence


# The creation source a discovery record of each class is reported as, from
# arthur-common so a class added there is not silently dropped here. OTEL and manual
# entries have no configured source, so never belong to a fetched one.
_CREATION_SOURCE_TYPES: dict[str, str] = {
    source_class.value: type_tag
    for source_class, type_tag in CREATION_SOURCE_TYPE_BY_CLASS.items()
}

# What a gateway caller record of each kind rests on when the kind alone says. An agent
# id may be registered or only claimed, which only the record itself said.
_BASIS_OF_CALLER_KIND = {
    NetworkCallerKind.VIRTUAL_KEY.value: IdentityBasis.CREDENTIAL.value,
    NetworkCallerKind.CONSUMER.value: IdentityBasis.CREDENTIAL.value,
    NetworkCallerKind.CLIENT_ADDRESS.value: IdentityBasis.CLIENT_ADDRESS.value,
}
_CALLER_KINDS = frozenset(_BASIS_OF_CALLER_KIND) | {NetworkCallerKind.AGENT_ID.value}


def _identity_basis(
    creation_source: dict[str, Any],
    task_creation_source: dict[str, Any],
) -> Optional[str]:
    """A gateway caller record's identity basis, which provenance does not carry and
    the Platform requires on one.

    The task's own creation source says it when it is this record. Otherwise the kind
    does, and an agent id falls back to `claimed_agent`, which never claims more than
    the record could.
    """
    kind = (creation_source.get("address") or {}).get("resource_kind")
    if kind not in _CALLER_KINDS:
        return None
    task_basis = task_creation_source.get("identity_basis")
    if task_basis and _same_place(
        creation_source, task_creation_source, _IDENTITY_FIELDS
    ):
        # The generated client's enum member: str() of one is its qualified name.
        return str(getattr(task_basis, "value", task_basis))
    return _BASIS_OF_CALLER_KIND.get(kind, IdentityBasis.CLAIMED_AGENT.value)


# Address fields that say which record an entry is, most specific last. Never the
# query, which a source config can have edited since the task was created.
_IDENTITY_FIELDS = ("instance", "scope", "resource_kind", "resource_id")


def _creation_record(
    evidence: list[dict[str, Any]],
    task_creation_source: dict[str, Any],
) -> Optional[dict[str, Any]]:
    """The evidence record the task was created from, if exactly one can be told.

    First on the whole address but the query, as GenAI Engine matches a stored report
    to a task's creation source. Then, if nothing matches that closely, on the address
    instance alone, provided only one record shares it: an entry holds the latest scan's
    address, and a Jamf record's address is its device's primary route to the agent,
    which changes when that route is uninstalled though the record does not. An
    ambiguous match names no record, since observations on the wrong one are worse than
    none.
    """
    for fields in (_IDENTITY_FIELDS, _IDENTITY_FIELDS[:1]):
        matches = [
            record
            for record in evidence
            if _same_place(record["creation_source"], task_creation_source, fields)
        ]
        if matches:
            return matches[0] if len(matches) == 1 else None
    return None


def _same_place(
    creation_source: dict[str, Any],
    task_creation_source: dict[str, Any],
    fields: tuple[str, ...],
) -> bool:
    if creation_source["type"] != task_creation_source.get("type") or creation_source[
        "vendor"
    ] != task_creation_source.get("vendor"):
        return False
    address = creation_source.get("address") or {}
    task_address = task_creation_source.get("address") or {}
    return all(address.get(field) == task_address.get(field) for field in fields)
