"""Turning one Foundry agent off, and on again: what a kill switch does to a Foundry target.

Foundry's disable is reversible and keeps everything: `POST {project_endpoint}/agents/
{agent_name}:disable` stops the agent's endpoint accepting new sessions and requests
(sessions already open drain), and `:enable` undoes it. Versions, definitions and
configuration are untouched. Both go through azure-ai-projects 2.4's own
`AIProjectClient.agents.disable` / `.enable` at the SDK's default `api-version` (`v1`,
the GA data-plane version), so no REST call is hand-built here.

A target is addressed as discovery addressed it: the source's fields and credentials,
which name the project and the principal exactly as a scan of that source would use
them, and the agent name, which is the record's `address.resource_id`.

IDEMPOTENT, AND SAYS WHETHER IT ACTED. The agent is read first; one already in the
asked-for state is left alone and reported unchanged, so a kill job that is retried, or
that fires on an agent someone already disabled by hand, succeeds without a second
call. Foundry documents both calls as idempotent too, so the read is about reporting
what was done, not about safety; a state changed between the read and the call is still
fine.

FAILURES carry `status_code` as the scan's do (see `client`): 401 for a refused
credential, 403 for a principal without the agent-write permission, 404
(`ResourceNotFoundError`) for an agent that is not in the project. The SDK's exception is
re-raised unchanged; settings and credential problems are `DiscoveryConfigurationError`.
"""

import logging
from dataclasses import dataclass
from typing import Any, Mapping, Optional

from discovery.cloud.azure_ai_foundry.client import (
    AgentsFactory,
    FoundryAgents,
    credential_from,
    describe_credential,
    project_agents,
    settings_from,
    vendor_status,
)
from job_executors.discovery_scan import DiscoveryConfigurationError

ENABLED = "enabled"
DISABLED = "disabled"


@dataclass(frozen=True)
class AgentStateChange:
    """What one disable or enable did."""

    agent_name: str
    # The `state` Foundry reported before the call: "enabled" or "disabled", or None
    # when it reported none.
    previous_state: Optional[str]
    state: str
    # False when the agent was already in `state` and nothing was called.
    changed: bool


def disable_agent(
    source_fields: Mapping[str, str],
    credentials: Mapping[str, Optional[str]],
    agent_name: str,
    logger: logging.Logger,
    agents_factory: AgentsFactory = project_agents,
) -> AgentStateChange:
    """Disable `agent_name` in the source's project. Already disabled is success."""
    return _set_state(
        source_fields, credentials, agent_name, DISABLED, logger, agents_factory
    )


def enable_agent(
    source_fields: Mapping[str, str],
    credentials: Mapping[str, Optional[str]],
    agent_name: str,
    logger: logging.Logger,
    agents_factory: AgentsFactory = project_agents,
) -> AgentStateChange:
    """Enable `agent_name` in the source's project. Already enabled is success."""
    return _set_state(
        source_fields, credentials, agent_name, ENABLED, logger, agents_factory
    )


def _set_state(
    source_fields: Mapping[str, str],
    credentials: Mapping[str, Optional[str]],
    agent_name: str,
    target: str,
    logger: logging.Logger,
    agents_factory: AgentsFactory,
) -> AgentStateChange:
    name = agent_name.strip()
    if not name:
        raise DiscoveryConfigurationError(
            "An Azure AI Foundry agent to disable or enable needs its name, the "
            "record's address.resource_id.",
        )
    settings = settings_from(source_fields)
    credential = credential_from(settings, credentials)
    logger.info(
        "Azure AI Foundry: setting agent %s in %s/%s to %s, using %s",
        name,
        settings.resource_name,
        settings.project_name,
        target,
        describe_credential(credential),
    )
    with vendor_status(), agents_factory(settings, credential) as agents:
        previous = state_of(agents.get(name))
        if previous == target:
            logger.info("Azure AI Foundry: agent %s is already %s", name, target)
            return AgentStateChange(name, previous, target, changed=False)
        _call(agents, name, target)
    logger.info(
        "Azure AI Foundry: agent %s is now %s (was %s)",
        name,
        target,
        previous or "unreported",
    )
    return AgentStateChange(name, previous, target, changed=True)


def _call(agents: FoundryAgents, name: str, target: str) -> None:
    if target == DISABLED:
        agents.disable(name)
    else:
        agents.enable(name)


def state_of(agent: Any) -> Optional[str]:
    """`AgentDetails.state` as a lower-case string: a plain str or an `AgentState` enum."""
    state = getattr(agent, "state", None)
    state = getattr(state, "value", state)
    return str(state).lower() if state else None
