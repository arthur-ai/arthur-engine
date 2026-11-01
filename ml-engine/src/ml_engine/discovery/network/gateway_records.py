"""Requests through an AI gateway folded into one record per caller.

THE GATEWAY IS THE SOURCE, NEVER A RECORD. A gateway (an LLM proxy holding the
provider keys) logs who called which model; a record is a caller seen through it, in
the gateway-caller shape of arthur-common's NetworkAgentCreationSource:

- `address.instance` is the gateway, `address.resource_kind` the gateway's namespace
  for the caller (`agent_id`, `virtual_key`, `consumer`, `client_address`) and
  `address.resource_id` the caller's id in it. `scope` is unset: a team can change
  between scans, and everything in the address is identity.
- `identity_basis` says what the record rests on, and sets its detection.
- `external_id` is `<vendor>:<gateway>:<kind>:<id>`, so two gateways, or an agent id
  and a key hash that happen to be equal, never share a record. Never an alias, which
  is optional and reusable.
- The team alias is observed as `host_group`. Nothing else: no client addresses and no
  end users, which the class refuses.

What each vendor's request log means -- which id a row proves, which rows are not
callers -- is the vendor package's. Only the record shape and the fold are shared.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from urllib.parse import urlsplit

from arthur_common.models.agent_discovery_schemas import DiscoveredAgentRecord
from arthur_common.models.agent_governance_schemas import (
    AgentObservations,
    IdentityBasis,
    LLMModel,
    NetworkAgentCreationSource,
    NetworkCallerKind,
    SourceAddress,
    Tool,
)

# Characters of an opaque id (a key hash) shown in a name when nothing better names it.
SHORT_ID_LENGTH = 8
_OPAQUE_KINDS = frozenset({NetworkCallerKind.VIRTUAL_KEY, NetworkCallerKind.CONSUMER})


def gateway_instance(url: str) -> str:
    """The gateway as one stable string: host, a port other than 443, and any path.

    Built from the parsed host rather than taken as the netloc, which would carry any
    `user:password@` written into the URL onto every record. An IPv6 host keeps its
    brackets so the port stays readable.
    """
    parts = urlsplit(url)
    host = (parts.hostname or url).lower()
    if ":" in host:
        host = f"[{host}]"
    if parts.port and parts.port != 443:
        host = f"{host}:{parts.port}"
    return f"{host}{parts.path.rstrip('/')}"


@dataclass(frozen=True)
class CallerKey:
    """Which record a request belongs to."""

    kind: NetworkCallerKind
    basis: IdentityBasis
    resource_id: str


@dataclass
class Caller:
    """One caller and everything the scan saw it do."""

    key: CallerKey
    alias: Optional[str] = None
    team_alias: Optional[str] = None
    last_seen: Optional[datetime] = None
    models: set[str] = field(default_factory=set)
    tools: set[str] = field(default_factory=set)

    def seen(self, when: datetime) -> None:
        if self.last_seen is None or when > self.last_seen:
            self.last_seen = when

    @property
    def name(self) -> str:
        if self.alias:
            return self.alias
        rid = self.key.resource_id
        if self.team_alias and self.key.kind in _OPAQUE_KINDS:
            return f"{self.team_alias} {rid[:SHORT_ID_LENGTH]}"
        return rid


class GatewayCallers:
    """The running fold: one Caller per CallerKey."""

    def __init__(self) -> None:
        self._callers: dict[CallerKey, Caller] = {}

    def __len__(self) -> int:
        return len(self._callers)

    def get(self, key: CallerKey) -> Optional[Caller]:
        return self._callers.get(key)

    def caller(self, key: CallerKey) -> Caller:
        found = self._callers.get(key)
        if found is None:
            found = self._callers[key] = Caller(key)
        return found

    def callers(self) -> list[Caller]:
        return sorted(
            self._callers.values(),
            key=lambda c: (c.key.kind.value, c.key.resource_id),
        )

    def by_basis(self) -> dict[IdentityBasis, int]:
        counts: dict[IdentityBasis, int] = {}
        for caller in self._callers.values():
            counts[caller.key.basis] = counts.get(caller.key.basis, 0) + 1
        return counts

    def records(self, vendor: str, instance: str) -> list[DiscoveredAgentRecord]:
        return [
            caller_record(c, vendor, instance)
            for c in self.callers()
            if c.last_seen is not None
        ]


def caller_record(
    caller: Caller,
    vendor: str,
    instance: str,
) -> DiscoveredAgentRecord:
    """One caller's record. `runs_on` and `service_names` stay unset: a gateway does
    not know where its caller runs, and an alias is not a span's `service.name`."""
    assert caller.last_seen is not None
    key = caller.key
    return DiscoveredAgentRecord(
        external_id=f"{vendor}:{instance}:{key.kind.value}:{key.resource_id}",
        name=caller.name,
        last_seen=caller.last_seen,
        llm_models=[LLMModel(name=m) for m in sorted(caller.models)] or None,
        tools=[Tool(name=t) for t in sorted(caller.tools)] or None,
        creation_source=NetworkAgentCreationSource(
            vendor=vendor,
            identity_basis=key.basis,
            address=SourceAddress(
                instance=instance,
                resource_kind=key.kind.value,
                resource_id=key.resource_id,
            ),
            observations=AgentObservations(host_group=caller.team_alias or None),
        ),
    )
