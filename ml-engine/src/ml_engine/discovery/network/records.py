"""Matched log lines folded into one record per internal source.

THE RECORD IS THE SOURCE, NOT THE AGENT. A log line shows that something on a host
called a provider, never which process or what it is, so the grain is the host: an
instance when the line names one, else an address within its network. An address is
weaker identity -- Lambda functions, containers and pods share and reuse VPC addresses
-- so a record keyed by one can name a different workload from one scan to the next.

Addressed by the host, the way arthur-common's NetworkAgentCreationSource requires, so a
host seen in two kinds of log keeps one address:

- an instance id: `resource_kind=instance`, the id in `instance` and `resource_id`;
- else a network interface id (default VPC flow logs carry no instance and no VPC):
  `resource_kind=eni`, the id in `instance` and `resource_id`;
- else an address: `resource_kind=ip`, the VPC in `instance`, the address in
  `resource_id`. A line naming an address but no VPC cannot be placed, since one
  address in two VPCs is two hosts; it is counted and dropped, never guessed;
- `scope` is where the host is, `<account>/<region>`, or the region alone when the
  source's lines carry no account. Never the VPC, which Route 53 Resolver logs carry
  and flow logs may not. The VPC is observed as `host_group`.

What it called -- each destination with its provider -- goes into the creation
source's `destinations`, busiest first. Counts and times are not sent: the task keeps
its first report's creation source, so when the host last called is the record's
`last_seen`, which every scan updates.
"""

import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Iterable, Optional

from arthur_common.models.agent_discovery_schemas import DiscoveredAgentRecord
from arthur_common.models.agent_governance_schemas import (
    AgentObservations,
    NetworkAgentCreationSource,
    NetworkDestination,
    NetworkHostKind,
    RunsOn,
    SourceAddress,
)

from discovery.network.extractor import Extracted
from discovery.network.hosts import InferenceDestination

# Providers named in a record's name before the rest are counted instead.
NAMED_PROVIDERS = 3

# Destinations carried per record, busiest first, so one source calling a wildcard
# host under many names cannot grow its record without bound.
MAX_DESTINATIONS = 50

_EC2_INSTANCE_ID = re.compile(r"^i-[0-9a-f]{8,17}$")


@dataclass
class Calls:
    """Every call one source made to one destination. The count only ranks
    destinations; it is not reported."""

    provider: str
    count: int = 0


@dataclass
class TrafficSource:
    """One internal host and every inference destination it reached."""

    scope: str
    kind: NetworkHostKind
    instance: str
    resource_id: str
    vpc_id: str = ""
    destinations: dict[str, Calls] = field(default_factory=dict)
    first_seen: Optional[datetime] = None
    last_seen: Optional[datetime] = None

    @property
    def external_id(self) -> str:
        parts = [self.scope, self.kind.value]
        if self.kind is NetworkHostKind.IP:
            parts.append(self.instance)
        return "/".join(parts + [self.resource_id])

    @property
    def label(self) -> str:
        if self.kind is NetworkHostKind.IP:
            return f"{self.resource_id} in {self.instance}"
        return self.resource_id

    @property
    def providers(self) -> list[str]:
        return sorted({calls.provider for calls in self.destinations.values()})


class TrafficSources:
    """The running fold: `add` per matched line, `records` once every line is read."""

    def __init__(self, region: str) -> None:
        self._region = region
        self._sources: dict[tuple[str, ...], TrafficSource] = {}
        self.unplaced = 0
        """Matched calls from an address whose line named no VPC, dropped."""

    def __len__(self) -> int:
        return len(self._sources)

    def add(
        self,
        line: Extracted,
        destination: InferenceDestination,
        seen_at: datetime,
    ) -> None:
        scope = f"{line.account_id}/{self._region}" if line.account_id else self._region
        if line.instance_id:
            kind, instance, resource_id = (
                NetworkHostKind.INSTANCE,
                line.instance_id,
                line.instance_id,
            )
        elif line.interface_id and line.interface_id != "-":
            kind, instance, resource_id = (
                NetworkHostKind.ENI,
                line.interface_id,
                line.interface_id,
            )
        elif line.vpc_id:
            kind, instance, resource_id = NetworkHostKind.IP, line.vpc_id, line.src
        else:
            self.unplaced += 1
            return
        key = (scope, kind.value, instance, resource_id)
        source = self._sources.get(key)
        if source is None:
            source = TrafficSource(scope, kind, instance, resource_id)
            self._sources[key] = source
        source.vpc_id = source.vpc_id or line.vpc_id
        host = line.dest.strip().lower().rstrip(".")
        calls = source.destinations.setdefault(host, Calls(destination.provider))
        calls.count += 1
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
            RunsOn.AWS
            if source.kind is NetworkHostKind.INSTANCE
            and _EC2_INSTANCE_ID.match(source.resource_id)
            else RunsOn.UNKNOWN
        ),
        creation_source=NetworkAgentCreationSource(
            vendor=vendor,
            address=SourceAddress(
                instance=source.instance,
                scope=source.scope,
                resource_kind=source.kind.value,
                resource_id=source.resource_id,
            ),
            observations=AgentObservations(
                host_name=source.resource_id,
                host_group=source.vpc_id or None,
            ),
            destinations=destinations_of(source),
        ),
    )


def destinations_of(source: TrafficSource) -> list[NetworkDestination]:
    """The source's destinations, busiest first, then by host."""
    ranked = sorted(source.destinations.items(), key=lambda kv: (-kv[1].count, kv[0]))
    return [
        NetworkDestination(host=host, provider=calls.provider)
        for host, calls in ranked[:MAX_DESTINATIONS]
    ]


def _named(providers: Iterable[str]) -> str:
    names = list(providers)
    if len(names) <= NAMED_PROVIDERS:
        return ", ".join(names)
    rest = len(names) - NAMED_PROVIDERS
    return f"{', '.join(names[:NAMED_PROVIDERS])} and {rest} more"
