"""
Executor for the FETCH_DISCOVERED_AGENTS job (D-10).

The second half of discovery. A scan resolves what a source found onto tasks in GenAI
Engine; this reads those tasks back for one source, converts each to an agent, and
upserts them through `PUT /workspaces/{id}/agents`, where the Platform decides whether
each one is a registered application or an unregistered agent.

Tasks are the seam between the two jobs, so everything this uploads carries a
`task_id` by construction. Running it twice over the same window uploads the same
agents twice: task identity is stable across scans (D-08) and the Platform upserts on
`(workspace_id, data_plane_id, task_id)`, so the second run updates in place.
"""

import logging
from typing import List, Optional

from arthur_client.api_bindings import Agent as ScopeAgent
from arthur_client.api_bindings import (
    AgentsV1Api,
)
from arthur_client.api_bindings import Config as ScopeRuleConfig
from arthur_client.api_bindings import (
    ExamplesConfig,
    FetchDiscoveredAgentsJobSpec,
    KeywordsConfig,
    PIIConfig,
    PutAgents,
    RegexConfig,
    ToxicityConfig,
)
from genai_client import (
    ApiClient,
    Configuration,
    EnrichedTaskResponse,
    TasksApi,
)

# Tasks per GET, and so agents per PUT. Well under GenAI Engine's own cap of 1,000:
# every task on a page is enriched from its spans, and the Platform upserts a PUT one
# agent at a time inside a single request, so a smaller page bounds both calls.
FETCH_PAGE_SIZE = 200

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

        uploaded = 0
        with ApiClient(
            Configuration(
                host=self.genai_engine_url,
                access_token=self.genai_engine_api_key,
            ),
        ) as api_client:
            tasks_api = TasksApi(api_client)
            after_task_id: str | None = None
            while True:
                tasks: List[EnrichedTaskResponse] = (
                    tasks_api.get_agent_tasks_api_v2_agent_tasks_get(
                        discovery_source_id=source_id,
                        reported_since=job_spec.reported_since,
                        after_task_id=after_task_id,
                        page_size=self.page_size,
                        _request_timeout=AGENT_TASKS_TIMEOUT_SECONDS,
                    )
                )
                if tasks:
                    uploaded += publish_enriched_tasks(
                        self.agents_client,
                        self.logger,
                        workspace_id,
                        data_plane_id,
                        tasks,
                        include_provenance=True,
                    )
                # A short page is the last one, which is how the endpoint says so.
                if len(tasks) < self.page_size:
                    break
                # Paged by cursor: the next page starts after this one's last task.
                after_task_id = tasks[-1].id

        self.logger.info(
            f"Uploaded {uploaded} agent(s) from discovery source {source_id}",
            extra={
                "workspace_id": workspace_id,
                "discovery_source_id": source_id,
                "num_upserted": uploaded,
            },
        )


def publish_enriched_tasks(
    agents_client: AgentsV1Api,
    logger: logging.Logger,
    workspace_id: str,
    data_plane_id: str,
    enriched_tasks: List[EnrichedTaskResponse],
    include_provenance: bool,
) -> int:
    """Convert enriched tasks to agents and upsert them. Returns how many were upserted."""
    agent_objects: list[ScopeAgent] = []
    unattributed: list[str] = []
    for task in enriched_tasks:
        agent = enriched_task_to_agent(task, data_plane_id, include_provenance)
        if agent is None:
            unattributed.append(task.id)
        else:
            agent_objects.append(agent)

    if unattributed:
        # Left out rather than sent: one agent the Agents API refuses fails the
        # whole PUT, so they would take every other task's agent down with them.
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
    return len(response.agents)


def enriched_task_to_agent(
    enriched_task: EnrichedTaskResponse,
    data_plane_id: str,
    include_provenance: bool,
) -> Optional[ScopeAgent]:
    """Convert a genai_client EnrichedTaskResponse to an arthur_client Agent.

    Bridges between the two auto-generated client libraries by converting
    via dict representation and remapping fields.

    `provenance` crosses as-is when included: both clients generate it from the one
    arthur_common model, and the Platform's input form reads only the fields it stores,
    leaving the derived `source_classes` behind. It is left out for the GCP sweep: the
    Platform reads an agent's infrastructure off `provenance.runs_on` whenever
    provenance is present and off its data plane otherwise, and the sweep uploads every
    agentic task, OTEL ones included, so sending it there would change what those
    agents show until D-14 moves GCP onto discovery.

    None for an auto-created task with no creation source. The Agents API refuses an
    agent that names no sensor (D-03), and naming one here would misreport who found
    it. A task created by hand in GenAI Engine is sent as MANUAL, which is what it is.
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
        "provenance": task_dict.get("provenance") if include_provenance else None,
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
