"""Matched log lines folded into one record per internal source.

THE RECORD IS THE SOURCE, NOT THE AGENT. A log line shows that something on a host
called a provider, never which process or what it is, so the grain is the host: an
instance when the line names one, else an address within its network. An address is
weaker identity -- Lambda functions, containers and pods share and reuse VPC addresses
-- so a record keyed by one can name a different workload from one scan to the next.

Addressed by account (`instance`; the source's region when the line names no account),
network (`scope`, the VPC when the line names one) and the instance or address
(`resource_id`). Which hosts were called, how often and when go into the name and the
job log: the record shape has no field for them.
"""

import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Iterable, Optional

from arthur_common.models.agent_discovery_schemas import DiscoveredAgentRecord
from arthur_common.models.agent_governance_schemas import (
    AgentObservations,
    NetworkAgentCreationSource,
    RunsOn,
    SourceAddress,
)

from discovery.network.extractor import Extracted
from discovery.network.hosts import InferenceDestination

# Providers named in a record's name before the rest are counted instead.
NAMED_PROVIDERS = 3

_EC2_INSTANCE_ID = re.compile(r"^i-[0-9a-f]{8,17}$")


@dataclass
class TrafficSource:
    """One internal source and every inference destination it reached."""

    instance: str
    vpc_id: str
    instance_id: str
    addresses: set[str] = field(default_factory=set)
    destinations: dict[str, str] = field(default_factory=dict)
    calls: int = 0
    first_seen: Optional[datetime] = None
    last_seen: Optional[datetime] = None

    @property
    def resource_id(self) -> str:
        return self.instance_id or min(self.addresses)

    @property
    def external_id(self) -> str:
        parts = [self.instance]
        if not self.instance_id and self.vpc_id:
            parts.append(self.vpc_id)
        return "/".join(parts + [self.resource_id])

    @property
    def label(self) -> str:
        if self.instance_id:
            return self.instance_id
        address = min(self.addresses)
        return f"{address} in {self.vpc_id}" if self.vpc_id else address

    @property
    def providers(self) -> list[str]:
        return sorted(set(self.destinations.values()))


class TrafficSources:
    """The running fold: `add` per matched line, `records` once every line is read."""

    def __init__(self, default_instance: str) -> None:
        self._default_instance = default_instance
        self._sources: dict[tuple[str, ...], TrafficSource] = {}

    def __len__(self) -> int:
        return len(self._sources)

    def add(
        self,
        line: Extracted,
        destination: InferenceDestination,
        seen_at: datetime,
    ) -> None:
        instance = line.account_id or self._default_instance
        key = (
            (instance, line.instance_id)
            if line.instance_id
            else (instance, line.vpc_id, line.src)
        )
        source = self._sources.get(key)
        if source is None:
            source = TrafficSource(instance, line.vpc_id, line.instance_id)
            self._sources[key] = source
        source.addresses.add(line.src)
        source.vpc_id = source.vpc_id or line.vpc_id
        source.destinations[line.dest.lower().rstrip(".")] = destination.provider
        source.calls += 1
        when = line.timestamp or seen_at
        source.first_seen = min(filter(None, (source.first_seen, when)))
        source.last_seen = max(filter(None, (source.last_seen, when)))

    def sources(self) -> list[TrafficSource]:
        return list(self._sources.values())

    def records(self, vendor: str) -> list[DiscoveredAgentRecord]:
        return [record_for(s, vendor) for s in self._sources.values()]

    def calls_by_provider(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for source in self._sources.values():
            for provider in source.providers:
                counts[provider] = counts.get(provider, 0) + 1
        return counts


def record_for(source: TrafficSource, vendor: str) -> DiscoveredAgentRecord:
    """One source's record. `runs_on` is AWS only for an EC2 instance id: an address
    can belong to a client that reached the VPC from on premises."""
    assert source.last_seen is not None
    return DiscoveredAgentRecord(
        external_id=source.external_id,
        name=f"{source.label} calling {_named(source.providers)}",
        last_seen=source.last_seen,
        runs_on=(
            RunsOn.AWS if _EC2_INSTANCE_ID.match(source.instance_id) else RunsOn.UNKNOWN
        ),
        creation_source=NetworkAgentCreationSource(
            vendor=vendor,
            address=SourceAddress(
                instance=source.instance,
                scope=source.vpc_id or None,
                resource_id=source.resource_id,
            ),
            observations=AgentObservations(
                host_name=source.resource_id,
                host_group=source.vpc_id or None,
            ),
        ),
    )


def _named(providers: Iterable[str]) -> str:
    names = list(providers)
    if len(names) <= NAMED_PROVIDERS:
        return ", ".join(names)
    rest = len(names) - NAMED_PROVIDERS
    return f"{', '.join(names[:NAMED_PROVIDERS])} and {rest} more"
