"""Azure AI Foundry's side of a DISCOVER_AGENTS scan.

Lists the agents in one Foundry project -- the Foundry Agent Service's agents
(`GET {project_endpoint}/agents`, `AIProjectClient.agents.list()` in azure-ai-projects
2.4), prompt, hosted and workflow agents alike -- and emits one record per agent. The
classic Assistants API's agents are a different resource that this list does not
return, so they are not reported. External agents (`kind: external`) are listed too but
skipped: Foundry only holds their metadata, they run wherever their owner hosts them, so
a record saying they run on Azure would be wrong.

THE RECORD. An agent's name is its identity in Foundry: it is unique in the project, it
is what every API addresses (`/agents/{agent_name}`), and it never
changes, where each edit makes a new version. So:

============  ==================================================================
field         value
============  ==================================================================
instance      the Foundry resource (account) name, the endpoint host's first label
scope         the project name, the endpoint path's last segment
resource_id   the agent name
external_id   ``{project_endpoint}/agents/{agent_name}``, from the normalised
              endpoint (lower-case host, no trailing slash)
============  ==================================================================

The external id is composed rather than copied: Foundry's `AgentDetails.id` is not
documented as stable or globally unique, and the composed id is also the agent's own
URL, so it reads alone and names the one project it can be found in.

WHAT IS READ, AND WHAT IS NOT. Each agent's latest version: its `created_at` (the
record's `last_seen`, since an agent has no time of its own), its version string, the
model deployment a prompt agent names, and its tools by name. A prompt agent's
`instructions` and a hosted agent's `environment_variables` arrive in the same listing;
neither is copied into the record or logged.

The lookback is not applied: the list is an inventory, so an agent created a year ago
and never edited is still there.
"""

import logging
from typing import Any, ClassVar, Iterator, Mapping, Optional, Sequence

from arthur_client.api_bindings import DiscoverySourceConfigSpec
from arthur_common.models.agent_discovery_schemas import DiscoveredAgentRecord
from arthur_common.models.agent_governance_schemas import (
    AgentObservations,
    CloudAgentCreationSource,
    LLMModel,
    RunsOn,
    SourceAddress,
    Tool,
)

from discovery.cloud.azure_ai_foundry.client import (
    SENSITIVE_FIELDS,
    AgentsFactory,
    FoundrySettings,
    credential_from,
    describe_credential,
    project_agents,
    settings_from,
    vendor_status,
)

VENDOR = "azure_ai_foundry"

# Records per published batch. The list API pages internally, so this bounds how much a
# failure part-way through the listing can cost rather than mirroring Azure's pages.
BATCH_SIZE = 100

# Agents Foundry only registers; they run outside it. See the module docstring.
_EXTERNAL_KIND = "external"


class FoundryListingError(RuntimeError):
    """Foundry's listing could not be read to the end; the scan is incomplete."""


def external_id_for(settings: FoundrySettings, agent_name: str) -> str:
    """The record's external id; see the module docstring."""
    return f"{settings.project_endpoint}/agents/{agent_name}"


class AzureAIFoundryConnector:
    """Implements `job_executors.discovery_scan.DiscoverySourceConnector`."""

    SENSITIVE_FIELDS: ClassVar[frozenset[str]] = SENSITIVE_FIELDS

    def __init__(self, agents_factory: AgentsFactory = project_agents) -> None:
        self._agents_factory = agents_factory

    def scan(
        self,
        config: DiscoverySourceConfigSpec,
        lookback_hours: int,
        credentials: Mapping[str, Optional[str]],
        source_fields: Mapping[str, str],
        logger: logging.Logger,
    ) -> Iterator[Sequence[DiscoveredAgentRecord]]:
        """Every agent in the source's project, in batches."""
        settings = settings_from(source_fields)
        credential = credential_from(settings, credentials)

        logger.info(
            "Azure AI Foundry scan starting against project %s on resource %s, "
            "using %s",
            settings.project_name,
            settings.resource_name,
            describe_credential(credential),
        )

        listed = skipped = external = 0
        seen: set[str] = set()
        batch: list[DiscoveredAgentRecord] = []
        try:
            # The listing is lazy and fetches each page as it is read, so the whole
            # iteration sits inside the translation, not only the call.
            with vendor_status(), self._agents_factory(settings, credential) as agents:
                for agent in agents.list():
                    # The SDK's pager asks for the next page for as long as a page
                    # names a `last_id`, and ignores `has_more`. A service that kept
                    # naming one would page forever; an agent seen twice is that. The
                    # scan fails rather than publish a listing it could not finish.
                    agent_name = getattr(agent, "name", None)
                    if isinstance(agent_name, str) and agent_name in seen:
                        raise FoundryListingError(
                            f"Azure AI Foundry listed agent {agent_name} twice in "
                            f"{settings.resource_name}/{settings.project_name}; the "
                            f"listing was stopped before it could page forever",
                        )
                    if isinstance(agent_name, str):
                        seen.add(agent_name)
                    listed += 1
                    if _kind(agent) == _EXTERNAL_KIND:
                        external += 1
                        continue
                    record = record_for(agent, settings, logger)
                    if record is None:
                        skipped += 1
                        continue
                    batch.append(record)
                    if len(batch) >= BATCH_SIZE:
                        yield batch
                        batch = []
            if batch:
                yield batch
        finally:
            close = getattr(credential, "close", None)
            if callable(close):
                close()
        logger.info(
            "Azure AI Foundry scan listed %s agent(s) in %s/%s, %s external, %s skipped",
            listed,
            settings.resource_name,
            settings.project_name,
            external,
            skipped,
        )


def _kind(agent: Any) -> Optional[str]:
    """The latest version's definition kind (`prompt`, `hosted`, `workflow`, `external`)."""
    latest = getattr(getattr(agent, "versions", None), "latest", None)
    kind = getattr(getattr(latest, "definition", None), "kind", None)
    return str(getattr(kind, "value", kind)) if kind else None


def record_for(
    agent: Any,
    settings: FoundrySettings,
    logger: logging.Logger,
) -> Optional[DiscoveredAgentRecord]:
    """One agent's record, or None when Foundry returned one that cannot be addressed."""
    name = (getattr(agent, "name", None) or "").strip()
    if not name:
        logger.warning(
            "Azure AI Foundry returned an agent with no name in %s/%s; skipped, "
            "because the name is the identity every Foundry call addresses",
            settings.resource_name,
            settings.project_name,
        )
        return None

    latest = getattr(getattr(agent, "versions", None), "latest", None)
    last_seen = getattr(latest, "created_at", None)
    if last_seen is None:
        logger.warning(
            "%s: Azure AI Foundry reported no latest version with a creation time; "
            "skipped, because last_seen is required and inventing one would date the "
            "record to the scan",
            name,
        )
        return None

    definition = getattr(latest, "definition", None)
    model = getattr(definition, "model", None)
    tools = [_tool_name(t) for t in getattr(definition, "tools", None) or []]
    return DiscoveredAgentRecord(
        external_id=external_id_for(settings, name),
        name=name,
        last_seen=last_seen,
        runs_on=RunsOn.AZURE,
        llm_models=[LLMModel(name=model)] if isinstance(model, str) and model else None,
        tools=[Tool(name=t) for t in tools if t] or None,
        creation_source=CloudAgentCreationSource(
            vendor=VENDOR,
            address=SourceAddress(
                instance=settings.resource_name,
                scope=settings.project_name,
                resource_id=name,
            ),
            observations=AgentObservations(
                version=getattr(latest, "version", None) or None,
            ),
        ),
    )


def _tool_name(tool: Any) -> Optional[str]:
    """A function tool by its function's name; any other tool by its type
    (`code_interpreter`, `file_search`, `mcp`...)."""
    # The SDK gives `type` as a plain str or a `ToolType` str enum; its value either way.
    kind = getattr(getattr(tool, "type", None), "value", getattr(tool, "type", None))
    name = getattr(tool, "name", None)
    if kind == "function" and isinstance(name, str) and name:
        return name
    return str(kind) if kind else None
