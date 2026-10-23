"""ECS and EKS's side of a DISCOVER_AGENTS scan: container runtime inventory.

Lists every ECS service, every ECS task no service owns, and every EKS workload in the
configured regions of one account, and reports the ones that are, or may be, agents. A
container runtime lists every workload, not only agents, so a workload is reported when:

- one of its images is an agent's in the catalog (`images:` in the vendored
  `agents.yaml`, or the source config's own catalog), matched by the vendored matcher's
  container route; or
- it runs as an IAM role that called a Bedrock model within the lookback, which this
  scan reads from CloudTrail itself (`read_cloudtrail`, on by default). A role whose
  every call Bedrock refused still selects its workload -- it tried -- but adds no
  model to the record; or
- the source sets `report_all_workloads`, which reports every workload so each one's
  role is in the record.

THE CALLERS ARE READ HERE, NOT JOINED FROM THE BEDROCK SOURCE. One job scans one source,
so nothing carries a Bedrock scan's callers into this one; reading them is one more
`cloudtrail:LookupEvents` grant, the same read the Bedrock source makes.

THE RECORD. `instance` is the account id, `scope` the region, `resource_kind` one of
`ecs_service`, `ecs_task_group`, `eks_workload`, and `resource_id` the workload's stable
name -- never a task or a pod. `external_id` is the service's ARN verbatim; for a task
group `{account}/{region}/ecs_task_group/{cluster}/{group}`; for EKS the cluster's ARN
and `/k8s/namespaces/NS/apps/deployments/N`. `install_path` is every container's image,
pinned to the digest its tasks or pods report (`image@sha256:...`) when one is known.
`llm_models` are the models its role was allowed to call.

THE ROLE IS IN THE NAME. `AgentObservations` has no field for the identity a workload
runs as, so the record's name carries it: `<workload> (runs as <role>, ...)`, with how
many workloads in the scan share the role and whether it is a node's. See
`workloads.py` for which role that is on each runtime.

THE LOOKBACK applies to the CloudTrail read only (seven days when it is 0). The
inventories are listed as they are now.

ONE REFUSED PART IS A DENIED SCOPE. An account-region whose ECS or EKS listing is
refused, and a cluster whose Kubernetes API answers 401 or 403 or cannot be reached, is
reported on the run as a denied scope and the rest of the scan goes on. A Kubernetes 401
is not the AWS credential's refusal: EKS answers it to any identity that has no access
entry on that cluster. Only a refused AWS credential ends the scan, and a scan that could
list no workload at all fails with what refused it, so a key without its ECS and EKS
grants reads as denied rather than as an account without workloads. The CloudTrail read
does not count as a listing: it only adds callers to the workloads listed.
"""

import logging
import time
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import (
    Any,
    Callable,
    ClassVar,
    Iterator,
    Mapping,
    Optional,
    Sequence,
    TypeVar,
)

import boto3
import requests
from arthur_client.api_bindings import DiscoverySourceConfigSpec
from arthur_common.models.agent_discovery_schemas import DiscoveredAgentRecord
from arthur_common.models.agent_governance_schemas import (
    AgentObservations,
    CloudAgentCreationSource,
    LLMModel,
    RunsOn,
    SourceAddress,
)

from discovery.aws_credentials import (
    REGION_NAME,
    SENSITIVE_FIELDS,
    aws_session,
    describe_credentials,
)
from discovery.catalog import Matcher
from discovery.cloud.aws_bedrock.client import (
    BedrockClient,
    BedrockError,
    ClientFactory,
    ModelCall,
    default_client_factory,
)
from discovery.cloud.aws_bedrock.connector import SSO_ROLE_PATH, aggregate
from discovery.cloud.aws_containers.client import (
    AwsContainersClient,
    AwsContainersError,
    KubernetesError,
    ScanStopped,
    TokenFactory,
    presigned_token,
)
from discovery.cloud.aws_containers.workloads import (
    K8S_KINDS,
    ClusterIdentity,
    SelectedWorkload,
    Workload,
    ecs_service_workload,
    ecs_task_group_workload,
    eks_workload,
    irsa_annotations,
    pinned_images,
    role_key,
    role_sharing,
    select_workloads,
    service_name_of,
    task_group_of,
)
from discovery.endpoint.scope import parse_group_names
from job_executors.discovery_scan import (
    DENIED_PERMISSION,
    DENIED_UNREACHABLE,
    DeniedScope,
    DiscoveryConfigurationError,
)

VENDOR = "aws_containers"

# Non-sensitive source fields, beside aws_credentials' role_arn and external_id.
REGIONS_FIELD = "regions"
READ_CLOUDTRAIL_FIELD = "read_cloudtrail"
REPORT_ALL_FIELD = "report_all_workloads"

# Opt-in for the engine's own AWS credentials, as Bedrock's.
ALLOW_DEFAULT_CREDENTIALS_ENV_VAR = (
    "ARTHUR_ENGINE_AWS_CONTAINERS_ALLOW_DEFAULT_CREDENTIALS"
)

# The assumed role's session name, which the customer's CloudTrail shows.
SESSION_NAME = "arthur-ai-discovery"

# The window CloudTrail is read over when the scan's lookback is 0.
DEFAULT_CLOUDTRAIL_LOOKBACK = timedelta(days=7)

BATCH_SIZE = 100

_TRUE = frozenset({"true", "1", "yes"})
_FALSE = frozenset({"false", "0", "no", ""})
# What a region the account has not enabled answers with, as a refused credential
# would. Raised only from the region the credential was proven in.
_REGION_NOT_ENABLED_CODES = frozenset(
    {"InvalidClientTokenId", "UnrecognizedClientException"}
)
# A cluster EKS is still building or tearing down has no API worth asking.
_LISTABLE_CLUSTER_STATUSES = frozenset({"ACTIVE", "UPDATING"})

_T = TypeVar("_T")


@dataclass(frozen=True)
class ContainersSettings:
    regions: tuple[str, ...]
    read_cloudtrail: bool = True
    report_all_workloads: bool = False


SessionFactory = Callable[
    [Mapping[str, Optional[str]], Mapping[str, str]],
    boto3.Session,
]


def source_session(
    credentials: Mapping[str, Optional[str]],
    source_fields: Mapping[str, str],
) -> boto3.Session:
    """The source's AWS session, under this vendor's opt-in for the engine's own
    credentials. STS is asked in the first region the source scans."""
    regions = parse_group_names(source_fields.get(REGIONS_FIELD))
    return aws_session(
        credentials,
        source_fields,
        source="ECS and EKS source",
        allow_default_env_var=ALLOW_DEFAULT_CREDENTIALS_ENV_VAR,
        session_name=SESSION_NAME,
        region_name=regions[0] if regions else None,
    )


def default_token_factory(session: boto3.Session) -> TokenFactory:
    """`(region, cluster) -> token`, each from an STS client of its own, because the
    cluster's name is signed in through a handler registered on the client."""

    def token_for(region: str, cluster: str) -> str:
        return presigned_token(session.client("sts", region_name=region), cluster)

    return token_for


class AwsContainersConnector:
    """Implements `job_executors.discovery_scan.DiscoverySourceConnector`,
    `AcceptsStopCheck` and `ReportsDeniedScopes`.

    Built fresh for every scan -- see `DiscoveryConnectorFactory` -- so it may hold that
    scan's stop check and refusals.
    """

    SENSITIVE_FIELDS: ClassVar[frozenset[str]] = SENSITIVE_FIELDS

    def __init__(
        self,
        session_for: SessionFactory = source_session,
        clients_for: Callable[[boto3.Session], ClientFactory] = default_client_factory,
        tokens_for: Callable[[boto3.Session], TokenFactory] = default_token_factory,
        http: Optional[requests.Session] = None,
        clock: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self._session_for = session_for
        self._clients_for = clients_for
        self._tokens_for = tokens_for
        self._http = http
        self._clock = clock
        self._sleep = sleep
        self._should_stop: Callable[[], bool] = lambda: False
        self._denied: list[DeniedScope] = []

    def stop_when(self, should_stop: Callable[[], bool]) -> None:
        """Asked before every call, so a stop never waits on another listing."""
        self._should_stop = should_stop

    def denied_scopes(self) -> Sequence[DeniedScope]:
        """The account-regions and clusters the scan was refused, and continued past."""
        return tuple(self._denied)

    def scan(
        self,
        config: DiscoverySourceConfigSpec,
        lookback_hours: int,
        credentials: Mapping[str, Optional[str]],
        source_fields: Mapping[str, str],
        logger: logging.Logger,
    ) -> Iterator[Sequence[DiscoveredAgentRecord]]:
        """`logger` is the JOB's, so what this reports reaches the Platform job log."""
        settings = settings_from(source_fields)
        session = self._session_for(credentials, source_fields)
        client_for = self._clients_for(session)
        bedrock = BedrockClient(
            client_for,
            logger,
            should_stop=self._should_stop,
            sleep=self._sleep,
        )
        client = AwsContainersClient(
            client_for,
            self._tokens_for(session),
            logger,
            should_stop=self._should_stop,
            http=self._http,
            sleep=self._sleep,
        )
        matcher = Matcher.from_source(catalog_yaml=config.query or None, logger=logger)

        # Asked first: it needs no permission, so a refusal here is the credential.
        identity = bedrock.identity(settings.regions[0])
        end = self._clock()
        start = end - (
            timedelta(hours=lookback_hours)
            if lookback_hours > 0
            else DEFAULT_CLOUDTRAIL_LOOKBACK
        )
        logger.info(
            "ECS and EKS scan starting in account %s, region(s) %s, catalog %s, using "
            "%s; reporting %s. Every workload is listed as it is now. CloudTrail model "
            "callers: %s.",
            identity.account,
            ", ".join(settings.regions),
            matcher.catalog_sha,
            describe_credentials(credentials, source_fields),
            (
                "every workload"
                if settings.report_all_workloads
                else "workloads whose image is in the catalog or whose role calls AI"
            ),
            (
                f"read from {start.isoformat()} to {end.isoformat()}"
                if settings.read_cloudtrail
                else "off"
            ),
        )

        scan = _Scan(
            client,
            identity.account,
            settings.regions[0],
            self._denied,
            logger,
        )
        workloads: list[Workload] = []
        ai_roles: dict[str, frozenset[str]] = {}
        stopped = False
        try:
            if settings.read_cloudtrail:
                ai_roles = scan.ai_roles(bedrock, settings.regions, start, end)
            for region in settings.regions:
                workloads.extend(scan.ecs(region))
                workloads.extend(scan.eks(region))
        except ScanStopped:
            stopped = True
            logger.info(
                "ECS and EKS scan stopped early on request after %s workload(s)",
                len(workloads),
            )

        sharing = role_sharing(workloads)
        selected = select_workloads(
            workloads,
            matcher,
            ai_roles,
            settings.report_all_workloads,
        )
        records = [r for r in (record_for(s, sharing, logger) for s in selected) if r]
        _log_summary(workloads, selected, records, scan, logger)

        for start_at in range(0, len(records), BATCH_SIZE):
            yield records[start_at : start_at + BATCH_SIZE]

        if not stopped and self._denied and not scan.listed:
            # No workload could be listed: a key without its ECS and EKS grants, not
            # an empty account, even when CloudTrail answered. Said with the status
            # failure_code reads.
            raise AwsContainersError(
                f"ECS and EKS scan was refused every workload listing it tried "
                f"({', '.join(d.scope for d in self._denied)}). The first: "
                f"{scan.first_refusal}",
                status_code=(
                    403
                    if all(d.reason == DENIED_PERMISSION for d in self._denied)
                    else None
                ),
            )


class _Scan:
    """One scan's reading of each region and cluster, and its tallies."""

    def __init__(
        self,
        client: AwsContainersClient,
        account: str,
        identity_region: str,
        denied: list[DeniedScope],
        logger: logging.Logger,
    ) -> None:
        self._client = client
        self._account = account
        self._identity_region = identity_region
        self.denied = denied
        self._log = logger
        self.listed = 0
        """Workload listings that succeeded. The CloudTrail read only adds callers to
        them, so it never counts: a source that listed no container is not a clean
        account, whatever CloudTrail answered."""
        self.first_refusal: Optional[Exception] = None
        self.counts: Counter[str] = Counter()
        self._task_definitions: dict[str, Mapping[str, Any]] = {}

    # --- CloudTrail ---------------------------------------------------------------

    def ai_roles(
        self,
        bedrock: BedrockClient,
        regions: Sequence[str],
        start: datetime,
        end: datetime,
    ) -> dict[str, frozenset[str]]:
        """`role_key` -> the models it was allowed to call, across every region read.

        Across regions because a task in one region may call a model in another. A role
        whose every call was refused maps to no models: it tried.
        """
        models: dict[str, set[str]] = {}
        for region in regions:
            try:
                calls: list[ModelCall] = list(bedrock.model_calls(region, start, end))
            except BedrockError as e:
                if self._is_credential(e.status_code, e.code, region):
                    raise
                self._refuse(f"{self._account}/{region}/cloudtrail", e)
                continue
            callers, _, events, denied = aggregate(iter(calls))
            self.counts["model_call_events"] += events
            self.counts["refused_model_calls"] += denied
            for caller in callers:
                models.setdefault(role_key(caller.arn), set()).update(caller.models)
            for call in calls:
                if call.error_code and SSO_ROLE_PATH not in call.caller_arn:
                    models.setdefault(role_key(call.caller_arn), set())
        self.counts["ai_roles"] = len(models)
        return {key: frozenset(m) for key, m in models.items()}

    # --- ECS ----------------------------------------------------------------------

    def ecs(self, region: str) -> list[Workload]:
        try:
            clusters = self._client.ecs_clusters(region)
        except AwsContainersError as e:
            if self._is_credential(e.status_code, e.code, region):
                raise
            self._refuse(f"{self._account}/{region}/ecs", e)
            return []
        self.listed += 1
        out: list[Workload] = []
        for arn in clusters:
            cluster = arn.rsplit("/", 1)[-1]
            try:
                found = self._ecs_cluster(region, arn, cluster)
            except AwsContainersError as e:
                if self._is_credential(e.status_code, e.code, region):
                    raise
                # Half a cluster would read as workloads that were deleted.
                self._refuse(f"{self._account}/{region}/ecs/{cluster}", e)
                continue
            out.extend(found)
        return out

    def _ecs_cluster(self, region: str, arn: str, cluster: str) -> list[Workload]:
        services = [
            s
            for s in self._client.ecs_services(region, arn)
            if str(s.get("status") or "ACTIVE") != "INACTIVE"
        ]
        tasks = self._client.ecs_tasks(region, arn)
        definition_arns = {
            str(d.get("taskDefinition"))
            for s in services
            for d in [*(s.get("deployments") or []), s]
            if d.get("taskDefinition")
        } | {
            str(t.get("taskDefinitionArn")) for t in tasks if t.get("taskDefinitionArn")
        }
        definitions = {
            a: self._task_definition(region, a) for a in sorted(definition_arns)
        }

        by_service: dict[str, list[Mapping[str, Any]]] = {}
        by_group: dict[str, list[Mapping[str, Any]]] = {}
        for task in tasks:
            owner = service_name_of(task)
            if owner is not None:
                by_service.setdefault(owner, []).append(task)
            else:
                by_group.setdefault(task_group_of(task), []).append(task)

        out: list[Workload] = []
        for service in services:
            name = str(service.get("serviceName") or "")
            service_tasks = by_service.get(name, [])
            workload = ecs_service_workload(
                self._account,
                region,
                cluster,
                service,
                definitions,
                service_tasks,
                self._instance_roles(region, arn, service_tasks, definitions),
            )
            if workload is not None:
                out.append(workload)
        for group, group_tasks in sorted(by_group.items()):
            out.append(
                ecs_task_group_workload(
                    self._account,
                    region,
                    cluster,
                    group,
                    group_tasks,
                    definitions,
                    self._instance_roles(region, arn, group_tasks, definitions),
                ),
            )
        self.listed += 1
        return out

    def _task_definition(self, region: str, arn: str) -> Mapping[str, Any]:
        if arn not in self._task_definitions:
            self._task_definitions[arn] = self._client.task_definition(region, arn)
        return self._task_definitions[arn]

    def _instance_roles(
        self,
        region: str,
        cluster_arn: str,
        tasks: Sequence[Mapping[str, Any]],
        definitions: Mapping[str, Mapping[str, Any]],
    ) -> list[str]:
        """The roles of the container instances these tasks run on, for the ones with
        no task role; empty when there are none, or on Fargate, or when refused."""
        instances = [
            str(t.get("containerInstanceArn"))
            for t in tasks
            if t.get("containerInstanceArn")
            and not (t.get("overrides") or {}).get("taskRoleArn")
            and not definitions.get(str(t.get("taskDefinitionArn")), {}).get(
                "taskRoleArn",
            )
        ]
        if not instances:
            return []
        try:
            return self._client.container_instance_roles(region, cluster_arn, instances)
        except AwsContainersError as e:
            if self._is_credential(e.status_code, e.code, region):
                raise
            self._log.warning(
                "The role of the EC2 instances behind %s could not be read (%s); its "
                "tasks without a task role are reported without one",
                cluster_arn,
                e,
            )
            return []

    # --- EKS ----------------------------------------------------------------------

    def eks(self, region: str) -> list[Workload]:
        try:
            names = self._client.eks_clusters(region)
        except AwsContainersError as e:
            if self._is_credential(e.status_code, e.code, region):
                raise
            self._refuse(f"{self._account}/{region}/eks", e)
            return []
        self.listed += 1
        out: list[Workload] = []
        for name in names:
            scope = f"{self._account}/{region}/eks/{name}"
            try:
                cluster = self._client.eks_cluster(region, name)
            except AwsContainersError as e:
                if self._is_credential(e.status_code, e.code, region):
                    raise
                self._refuse(scope, e)
                continue
            if str(cluster.get("status") or "ACTIVE") not in _LISTABLE_CLUSTER_STATUSES:
                self._log.info(
                    "EKS cluster %s is %s; not listed", scope, cluster["status"]
                )
                continue
            identity = ClusterIdentity(
                irsa={},
                pod_identity=self._optional(
                    lambda: self._client.pod_identity_roles(region, name),
                    {},
                    f"Pod Identity associations of {scope}",
                    region,
                ),
                node_roles=tuple(
                    self._optional(
                        lambda: self._client.node_roles(region, name),
                        [],
                        f"Node group roles of {scope}",
                        region,
                    ),
                ),
            )
            try:
                found = self._eks_cluster(region, cluster, identity)
            except KubernetesError as e:
                self._refuse(scope, e, kubernetes=True)
                continue
            out.extend(found)
            self.listed += 1
        return out

    def _eks_cluster(
        self,
        region: str,
        cluster: Mapping[str, Any],
        identity: ClusterIdentity,
    ) -> list[Workload]:
        found: list[Workload] = []
        with self._client.kubernetes(region, cluster) as kube:
            identity = ClusterIdentity(
                irsa=irsa_annotations(kube.items("/api/v1/serviceaccounts")),
                pod_identity=identity.pod_identity,
                node_roles=identity.node_roles,
            )
            for path, kind, asset_kind in K8S_KINDS:
                for raw in kube.items(path):
                    workload = eks_workload(
                        self._account,
                        region,
                        cluster,
                        identity,
                        kind,
                        asset_kind,
                        raw,
                    )
                    if workload is not None:
                        found.append(workload)
        # A cluster counts only when every kind was listed: half a cluster would read
        # as workloads that were deleted.
        return found

    # --- refusals -----------------------------------------------------------------

    def _optional(
        self,
        read: Callable[[], _T],
        empty: _T,
        what: str,
        region: str,
    ) -> _T:
        """A read whose refusal costs the records some identity, not the cluster."""
        try:
            return read()
        except AwsContainersError as e:
            if self._is_credential(e.status_code, e.code, region):
                raise
            self._log.warning("%s not read (%s); roles from it are missing", what, e)
            return empty

    def _is_credential(
        self,
        status: Optional[int],
        code: Optional[str],
        region: str,
    ) -> bool:
        """Whether an AWS refusal is the credential's, which ends the scan. Elsewhere
        than the region it was proven in, these codes are what an opt-in region the
        account has not enabled answers with."""
        return status == 401 and (
            region == self._identity_region or code not in _REGION_NOT_ENABLED_CODES
        )

    def _refuse(self, scope: str, error: Exception, kubernetes: bool = False) -> None:
        status = getattr(error, "status_code", None)
        if kubernetes and status not in (None, 401, 403):
            # A failing API, not a refused or unreachable one: logged, not a scope.
            self._log.warning("%s: not read: %s", scope, error)
            return
        reason = DENIED_PERMISSION if status in (401, 403) else DENIED_UNREACHABLE
        self.denied.append(DeniedScope(scope, reason))
        if self.first_refusal is None:
            self.first_refusal = error
        hint = (
            " -- give this source's identity an EKS access entry with "
            "AmazonEKSViewPolicy on the cluster"
            if kubernetes and status in (401, 403)
            else ""
        )
        self._log.warning("%s: not read (%s): %s%s", scope, reason, error, hint)


def record_for(
    selected: SelectedWorkload,
    sharing: Mapping[str, int],
    logger: logging.Logger,
) -> Optional[DiscoveredAgentRecord]:
    """One reported workload's record, or None when it has no time to date it by."""
    workload = selected.workload
    if workload.last_seen is None:
        logger.warning(
            "%s: no create, update or start time; skipped, because last_seen is "
            "required and inventing one would date the record to the scan",
            workload.external_id,
        )
        return None
    classification = next(
        (f.classification for f in selected.findings if f.classification),
        None,
    )
    return DiscoveredAgentRecord(
        external_id=workload.external_id,
        name=display_name(selected, sharing),
        last_seen=workload.last_seen,
        llm_models=[LLMModel(name=m) for m in selected.models] or None,
        runs_on=RunsOn.AWS,
        creation_source=CloudAgentCreationSource(
            vendor=VENDOR,
            address=SourceAddress(
                instance=workload.account,
                scope=workload.region,
                resource_kind=workload.kind,
                resource_id=workload.resource_id,
            ),
            observations=AgentObservations(
                classification=classification,
                host_group=workload.cluster,
                # A container is installed as its image, at the digest it runs.
                install_path=", ".join(pinned_images(workload)) or None,
            ),
        ),
    )


def display_name(selected: SelectedWorkload, sharing: Mapping[str, int]) -> str:
    """`<workload> [<catalog agents>] (runs as <role>[, node role][, shared by N
    workloads]; ...)`; see the module docstring."""
    workload = selected.workload
    name = workload.name
    if selected.findings:
        name += f" [{', '.join(f.name for f in selected.findings)}]"
    labels = []
    for role in workload.roles:
        label = role.rsplit("/", 1)[-1] or role
        if role in workload.node_roles:
            label += ", node role"
        shared = sharing.get(role_key(role), 1)
        if shared > 1:
            label += f", shared by {shared} workloads"
        labels.append(label)
    if labels:
        name += f" (runs as {'; '.join(labels)})"
    return name


def settings_from(source_fields: Mapping[str, str]) -> ContainersSettings:
    """The regions and toggles from the source's non-sensitive fields."""
    regions = parse_group_names(source_fields.get(REGIONS_FIELD))
    if not regions:
        raise DiscoveryConfigurationError(
            f"ECS and EKS source is missing required field '{REGIONS_FIELD}'. It is a "
            f"source field, not a secret.",
        )
    bad = [r for r in regions if not REGION_NAME.match(r)]
    if bad:
        raise DiscoveryConfigurationError(
            f"ECS and EKS source's '{REGIONS_FIELD}' has value(s) that are not AWS "
            f"regions: {', '.join(repr(r) for r in bad)}. Use names such as us-east-1.",
        )
    return ContainersSettings(
        regions=regions,
        read_cloudtrail=_flag(source_fields, READ_CLOUDTRAIL_FIELD, default=True),
        report_all_workloads=_flag(source_fields, REPORT_ALL_FIELD, default=False),
    )


def _flag(source_fields: Mapping[str, str], name: str, default: bool) -> bool:
    raw = (source_fields.get(name) or "").strip().lower()
    if not raw:
        return default
    if raw not in _TRUE | _FALSE:
        raise DiscoveryConfigurationError(
            f"ECS and EKS source's '{name}' must be true or false.",
        )
    return raw in _TRUE


def _log_summary(
    workloads: Sequence[Workload],
    selected: Sequence[SelectedWorkload],
    records: Sequence[DiscoveredAgentRecord],
    scan: _Scan,
    logger: logging.Logger,
) -> None:
    by_kind: Counter[str] = Counter(w.kind for w in workloads)
    by_reason: Counter[str] = Counter(r for s in selected for r in s.reasons)
    logger.info(
        "ECS and EKS scan listed %s workload(s) (%s); %s reported (%s); %s AI-calling "
        "role(s) from %s model call event(s), %s of them refused; %s part(s) refused",
        len(workloads),
        ", ".join(f"{k}: {n}" for k, n in sorted(by_kind.items())) or "none",
        len(records),
        ", ".join(f"{k}: {n}" for k, n in sorted(by_reason.items())) or "none",
        scan.counts["ai_roles"],
        scan.counts["model_call_events"],
        scan.counts["refused_model_calls"],
        len(scan.denied),
    )
