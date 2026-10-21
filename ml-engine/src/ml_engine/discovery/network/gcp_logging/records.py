"""Cloud DNS lookups and serverless flow records folded into one record per workload.

WHO CALLED. Cloud DNS names the VM that asked (`vmInstanceIdString`, never the numeric
`vmInstanceId`, which loses precision as a JSON number). It names nothing for Cloud Run:
a serverless lookup carries no source fields. A Cloud Run workload is named by its VPC
flow records instead (`src_serverless_details`), which record the execution or revision
behind each connection. A GKE pod's lookups are made by the node running kube-dns and
its egress is masqueraded to its node, so neither log names the pod; a GKE node appears
as the VM it is.

WHAT WAS CALLED. A DNS lookup names the host. A flow record names only an address, so it
is labelled by the DNS answers in the same window: an address one of them gave for a
known inference host is that host. An address that also answered for a host that is
not inference (Google's shared front ends answer for every googleapis.com host) cannot
say which was called, and is counted, never guessed.

THE ADDRESS IS THE WORKLOAD, as for every network record:
- a VM: `resource_kind=instance`, its id in `instance` and `resource_id`, `scope`
  `<project>/<zone>`, the same address a Compute Engine record gives it;
- a Cloud Run job or service: `resource_kind=workload`, `run/jobs/<job>` or
  `run/services/<service>` in `instance` and `resource_id`, `scope` `<project>/<region>`.
  A job execution (`<job>-<suffix>`) is folded into its job when the job is known.
"""

import ipaddress
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Iterable, Optional

from arthur_common.models.agent_discovery_schemas import DiscoveredAgentRecord
from arthur_common.models.agent_governance_schemas import (
    AgentObservations,
    NetworkAgentCreationSource,
    NetworkDestination,
    NetworkHostKind,
    RunsOn,
    SourceAddress,
)

from discovery.network.hosts import DestinationMatcher, InferenceDestination

# Providers named in a record's name before the rest are counted instead.
NAMED_PROVIDERS = 3
MAX_DESTINATIONS = 50

# A Compute Engine VM's name in a DNS log is prefixed with its project number.
_PROJECT_NUMBER_PREFIX = re.compile(r"^\d+\.")


@dataclass
class Workload:
    project: str
    location: str
    kind: NetworkHostKind
    identity: str
    label: str
    network: str = ""
    destinations: dict[str, InferenceDestination] = field(default_factory=dict)
    last_seen: Optional[datetime] = None

    def saw(self, destination: InferenceDestination, host: str, when: datetime) -> None:
        self.destinations.setdefault(host, destination)
        self.last_seen = max(filter(None, (self.last_seen, when)))


@dataclass
class Counts:
    lookups: int = 0
    inference_lookups: int = 0
    unplaced_lookups: int = 0
    flows: int = 0
    inference_flows: int = 0
    ambiguous_flows: int = 0


class NetworkFold:
    """The running fold: `lookup` per DNS entry, then `flow` per flow entry."""

    def __init__(
        self, matcher: DestinationMatcher, run_jobs: Callable[[str], set[str]]
    ) -> None:
        self._matcher = matcher
        # region -> the Cloud Run job names there, listed once per region on first use
        self._list_run_jobs = run_jobs
        self._run_jobs: dict[str, set[str]] = {}
        self.workloads: dict[tuple[str, ...], Workload] = {}
        # address -> the inference host it answered for; addresses that also answered
        # for anything else are ambiguous
        self._inference_ips: dict[str, tuple[str, InferenceDestination]] = {}
        self._other_ips: set[str] = set()
        self.counts = Counts()

    def lookup(self, entry: dict[str, Any]) -> None:
        payload = entry.get("jsonPayload") or {}
        when = _timestamp(entry.get("timestamp"))
        name = (payload.get("queryName") or "").strip().lower().rstrip(".")
        if not name or when is None:
            return
        self.counts.lookups += 1
        destination = self._matcher.match(name)
        answers = _answer_addresses(payload.get("rdata") or "")
        if destination is None:
            self._other_ips.update(answers)
            return
        self.counts.inference_lookups += 1
        for ip in answers:
            self._inference_ips.setdefault(ip, (name, destination))
        vm_id = (payload.get("vmInstanceIdString") or "").strip()
        project = (payload.get("vmProjectId") or "").strip()
        zone = (payload.get("vmZoneName") or "").strip()
        if not (vm_id and project and zone):
            self.counts.unplaced_lookups += 1
            return
        label = _PROJECT_NUMBER_PREFIX.sub("", payload.get("vmInstanceName") or vm_id)
        workload = self.workloads.setdefault(
            ("vm", project, zone, vm_id),
            Workload(project, zone, NetworkHostKind.INSTANCE, vm_id, label),
        )
        workload.network = workload.network or (payload.get("sourceNetwork") or "")
        workload.saw(destination, name, when)

    def flow(self, entry: dict[str, Any]) -> None:
        payload = entry.get("jsonPayload") or {}
        when = _timestamp(entry.get("timestamp") or payload.get("start_time"))
        serverless = payload.get("src_serverless_details") or {}
        dest_ip = ((payload.get("connection") or {}).get("dest_ip") or "").strip()
        if not serverless or not dest_ip or when is None:
            return
        self.counts.flows += 1
        known = self._inference_ips.get(dest_ip)
        if known is None:
            return
        if dest_ip in self._other_ips:
            self.counts.ambiguous_flows += 1
            return
        identity = self._serverless_identity(serverless, serverless.get("region") or "")
        if identity is None:
            return
        self.counts.inference_flows += 1
        project = serverless.get("project_id") or ""
        region = serverless.get("region") or ""
        workload = self.workloads.setdefault(
            ("run", project, region, identity),
            Workload(
                project,
                region,
                NetworkHostKind.WORKLOAD,
                identity,
                identity.rsplit("/", 1)[-1],
            ),
        )
        vpc = payload.get("src_vpc") or {}
        workload.network = workload.network or (vpc.get("vpc_name") or "")
        host, destination = known
        workload.saw(destination, host, when)

    def _serverless_identity(
        self, details: dict[str, Any], region: str
    ) -> Optional[str]:
        job = (details.get("cloud_run_job_details") or {}).get("job_name")
        if job:
            return f"run/jobs/{self._job_of(job, region)}"
        service = (details.get("cloud_run_service_details") or {}).get("service_name")
        if service:
            return f"run/services/{service}"
        return None

    def _job_of(self, execution: str, region: str) -> str:
        """The job an execution belongs to, when the job is known."""
        if region not in self._run_jobs:
            self._run_jobs[region] = self._list_run_jobs(region) if region else set()
        candidates = [
            j
            for j in self._run_jobs[region]
            if execution.startswith(f"{j}-") or execution == j
        ]
        return max(candidates, key=len) if candidates else execution

    def records(self, vendor: str) -> list[DiscoveredAgentRecord]:
        return [
            record_for(w, vendor) for w in self.workloads.values() if w.destinations
        ]


def record_for(workload: Workload, vendor: str) -> DiscoveredAgentRecord:
    assert workload.last_seen is not None
    providers = sorted({d.provider for d in workload.destinations.values()})
    scope = f"{workload.project}/{workload.location}"
    return DiscoveredAgentRecord(
        external_id=f"{scope}/{workload.kind.value}/{workload.identity}",
        name=f"{workload.label} calling {_named(providers)}",
        last_seen=workload.last_seen,
        runs_on=RunsOn.GCP,
        creation_source=NetworkAgentCreationSource(
            vendor=vendor,
            address=SourceAddress(
                instance=workload.identity,
                scope=scope,
                resource_kind=workload.kind.value,
                resource_id=workload.identity,
            ),
            observations=AgentObservations(
                host_name=workload.label,
                host_group=workload.network or None,
            ),
            destinations=[
                NetworkDestination(host=host, provider=d.provider)
                for host, d in sorted(workload.destinations.items())[:MAX_DESTINATIONS]
            ],
        ),
    )


def _answer_addresses(rdata: str) -> set[str]:
    """The A and AAAA addresses in a Cloud DNS `rdata` (one record per line, the
    address last). A line cut short by the log is skipped."""
    out: set[str] = set()
    for line in rdata.splitlines():
        parts = line.split()
        if len(parts) < 5 or parts[3].lower() not in {"a", "aaaa"}:
            continue
        try:
            out.add(str(ipaddress.ip_address(parts[4])))
        except ValueError:
            continue
    return out


def _timestamp(raw: Optional[str]) -> Optional[datetime]:
    if not raw:
        return None
    text = re.sub(r"(\.\d{6})\d+", r"\1", raw.replace("Z", "+00:00"))
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        return None


def _named(providers: Iterable[str]) -> str:
    names = list(providers)
    if len(names) <= NAMED_PROVIDERS:
        return ", ".join(names)
    return (
        f"{', '.join(names[:NAMED_PROVIDERS])} and {len(names) - NAMED_PROVIDERS} more"
    )
