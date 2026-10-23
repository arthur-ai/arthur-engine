"""Container workloads on AWS, read off the API objects and selected.

Pure: no call is made here. `client.py` fetches the objects; this turns each into one
`Workload` -- name, images, the IAM role(s) it runs as -- and `select_workloads` decides
which are reported. Kept apart so the selection can be called again with a different set
of AI-calling roles without listing anything.

ONE WORKLOAD PER STABLE NAME. An ECS service by its name, never a task: a service's tasks
carry `group: service:<name>` and are folded into it, and a replaced task's new ARN is
the same workload. A task no service owns (`RunTask`, a scheduler, a batch job) stands
for its `group`, which is `family:<task definition family>` unless whoever ran it set
one. An EKS workload by its controller -- Deployment, StatefulSet, DaemonSet, CronJob --
and only a Job or Pod that nothing owns stands for itself, as on GKE.

WHICH IAM ROLE A WORKLOAD RUNS AS. That is what CloudTrail names as the caller of a
Bedrock model (`userIdentity.sessionContext.sessionIssuer.arn`), so it is the key that
joins a workload to the models it called.

- ECS: the task role (`taskRoleArn` on the task definition, or the one `RunTask`
  overrode). Never the execution role: that is the ECS agent's, for pulling the image
  and writing logs, and the application cannot call anything with it. A task on EC2
  with no task role reaches the container instance's own role through the instance
  metadata service, so that role is listed, marked as the node's; a Fargate task with no
  task role has no AWS identity at all.
- EKS: the role its Kubernetes service account's `eks.amazonaws.com/role-arn`
  annotation names (IRSA), which the SDKs' credential chain tries first; else the role
  an EKS Pod Identity association binds to that service account; else the managed node
  groups' node roles, which every pod on those nodes shares. Which group a controller's
  pods land on is the scheduler's, so every group's role is listed, marked as the node's.
  A pod a Fargate profile selects has no node role at all. Nodes outside managed node
  groups (self-managed, Karpenter, Auto Mode) are not listed by EKS, so their roles are
  not known here.

A ROLE MAY BE SHARED. Two services given one task role, or every pod on a node, run as
the same identity; a match on it says one of them called a model, not which. The record
says how many workloads in the scan share each role, and which roles are a node's.
"""

from dataclasses import dataclass, field
from datetime import datetime
from fnmatch import fnmatchcase
from typing import Any, Iterable, Mapping, Optional, Sequence

from discovery.catalog import Finding, Matcher

ECS_SERVICE = "ecs_service"
ECS_TASK_GROUP = "ecs_task_group"
EKS_WORKLOAD = "eks_workload"

# An EKS workload's controller kinds, as (list path, kind in resource_id, the path
# segment the external id names the kind by). Pods and Jobs are listed for the ones
# nothing owns.
K8S_KINDS: tuple[tuple[str, str, str], ...] = (
    ("/apis/apps/v1/deployments", "deployment", "apps/deployments"),
    ("/apis/apps/v1/statefulsets", "statefulset", "apps/statefulsets"),
    ("/apis/apps/v1/daemonsets", "daemonset", "apps/daemonsets"),
    ("/apis/batch/v1/cronjobs", "cronjob", "batch/cronjobs"),
    ("/apis/batch/v1/jobs", "job", "batch/jobs"),
    ("/api/v1/pods", "pod", "pods"),
)

# Namespaces Kubernetes and EKS add-ons run their own components in. Their pods run on
# the node role like any other, so an AI-calling node role would otherwise report every
# one of them.
SYSTEM_NAMESPACES = frozenset(
    {"kube-system", "kube-public", "kube-node-lease", "aws-observability"},
)
SYSTEM_NAMESPACE_PREFIXES = ("amazon-",)

IRSA_ANNOTATION = "eks.amazonaws.com/role-arn"

# The kinds an owner already stands for. A controller is listed whatever owns it.
_OWNED_BY_A_CONTROLLER = frozenset({"job", "pod"})

SERVICE_GROUP_PREFIX = "service:"

# Why a workload is reported.
REASON_CATALOG = "catalog"
REASON_AI_ROLE = "ai_role"
REASON_REPORT_ALL = "report_all"


@dataclass(frozen=True)
class Workload:
    account: str
    region: str
    kind: str
    """ECS_SERVICE, ECS_TASK_GROUP or EKS_WORKLOAD."""
    resource_id: str
    """The stable name: `<cluster>/<service>`, `<cluster>/<group>`, or
    `<cluster>/<ns>/<kind>/<name>` on EKS."""
    external_id: str
    name: str
    images: tuple[str, ...]
    """Every container's image as declared, init containers and sidecars included."""
    roles: tuple[str, ...]
    """IAM role ARNs it runs as."""
    last_seen: Optional[datetime]
    cluster: str
    digests: Mapping[str, tuple[str, ...]] = field(default_factory=dict)
    """Image as declared -> the manifest digests its running tasks or pods report."""
    node_roles: tuple[str, ...] = ()
    """Those of `roles` that are a node's or a container instance's, shared by every
    workload on it."""


@dataclass(frozen=True)
class SelectedWorkload:
    workload: Workload
    findings: tuple[Finding, ...]
    reasons: tuple[str, ...]
    matched_roles: tuple[str, ...] = ()
    models: tuple[str, ...] = ()
    """Models its matched roles were allowed to call, from CloudTrail."""


# --- ECS ------------------------------------------------------------------------------


def task_definition_images(task_definition: Mapping[str, Any]) -> tuple[str, ...]:
    return tuple(
        str(c.get("image"))
        for c in task_definition.get("containerDefinitions") or []
        if c.get("image")
    )


def task_digests(tasks: Iterable[Mapping[str, Any]]) -> dict[str, tuple[str, ...]]:
    """Image as the task names it -> the digests ECS resolved it to.

    ECS resolves a tag to a digest when a service deploys, so every task of one
    deployment reports the same one; two during a rollout. Empty when ECS recorded none
    (the image was never pulled, an old agent, a managed sidecar).
    """
    out: dict[str, list[str]] = {}
    for task in tasks:
        for container in task.get("containers") or []:
            image = str(container.get("image") or "")
            digest = str(container.get("imageDigest") or "")
            if image and digest:
                found = out.setdefault(image, [])
                if digest not in found:
                    found.append(digest)
    return {image: tuple(d) for image, d in out.items()}


def ecs_service_workload(
    account: str,
    region: str,
    cluster: str,
    service: Mapping[str, Any],
    task_definitions: Mapping[str, Mapping[str, Any]],
    tasks: Sequence[Mapping[str, Any]],
    instance_roles: Sequence[str] = (),
) -> Optional[Workload]:
    """One ECS service, or None when it has no name.

    `task_definitions` is ARN -> DescribeTaskDefinition's `taskDefinition`; every
    deployment's definition is read, so a rollout lists both images. `tasks` are this
    service's tasks; `instance_roles` the roles of the container instances its EC2 tasks
    run on, used only when a definition has no task role.
    """
    name = str(service.get("serviceName") or "")
    if not name:
        return None
    arns = [
        str(d.get("taskDefinition"))
        for d in service.get("deployments") or []
        if d.get("taskDefinition")
    ] or ([str(service["taskDefinition"])] if service.get("taskDefinition") else [])
    definitions = [
        task_definitions[a] for a in dict.fromkeys(arns) if a in task_definitions
    ]
    images = tuple(
        dict.fromkeys(i for d in definitions for i in task_definition_images(d))
    )
    roles = [
        role_arn(account, str(d.get("taskRoleArn")))
        for d in definitions
        if d.get("taskRoleArn")
    ]
    node_roles: tuple[str, ...] = ()
    if any(not d.get("taskRoleArn") for d in definitions):
        node_roles = tuple(instance_roles)
    times = [_as_datetime(service.get("createdAt"))] + [
        _as_datetime(d.get(key))
        for d in service.get("deployments") or []
        for key in ("updatedAt", "createdAt")
    ]
    seen = [t for t in times if t is not None]
    return Workload(
        account=account,
        region=region,
        kind=ECS_SERVICE,
        resource_id=f"{cluster}/{name}",
        external_id=_service_external_id(account, region, cluster, name, service),
        name=f"{cluster}/{name}",
        images=images,
        roles=tuple(dict.fromkeys([*roles, *node_roles])),
        last_seen=max(seen) if seen else None,
        cluster=cluster,
        digests=task_digests(tasks),
        node_roles=node_roles,
    )


def ecs_task_group_workload(
    account: str,
    region: str,
    cluster: str,
    group: str,
    tasks: Sequence[Mapping[str, Any]],
    task_definitions: Mapping[str, Mapping[str, Any]],
    instance_roles: Sequence[str] = (),
) -> Workload:
    """The tasks no service owns that share one `group`, as one workload."""
    definitions = [
        task_definitions[a]
        for a in dict.fromkeys(str(t.get("taskDefinitionArn") or "") for t in tasks)
        if a in task_definitions
    ]
    images = tuple(
        dict.fromkeys(i for d in definitions for i in task_definition_images(d))
    )
    by_arn = {str(d.get("taskDefinitionArn") or ""): d for d in definitions}
    roles: list[str] = []
    without_role = False
    for task in tasks:
        override = str((task.get("overrides") or {}).get("taskRoleArn") or "")
        definition = by_arn.get(str(task.get("taskDefinitionArn") or "")) or {}
        role = override or str(definition.get("taskRoleArn") or "")
        if role:
            roles.append(role_arn(account, role))
        else:
            without_role = True
    node_roles = tuple(instance_roles) if without_role else ()
    times = [
        _as_datetime(t.get(key))
        for t in tasks
        for key in ("stoppedAt", "startedAt", "createdAt")
    ]
    seen = [t for t in times if t is not None]
    return Workload(
        account=account,
        region=region,
        kind=ECS_TASK_GROUP,
        resource_id=f"{cluster}/{group}",
        external_id=f"{account}/{region}/{ECS_TASK_GROUP}/{cluster}/{group}",
        name=f"{cluster}/{group}",
        images=images,
        roles=tuple(dict.fromkeys([*roles, *node_roles])),
        last_seen=max(seen) if seen else None,
        cluster=cluster,
        digests=task_digests(tasks),
        node_roles=node_roles,
    )


def _service_external_id(
    account: str,
    region: str,
    cluster: str,
    name: str,
    service: Mapping[str, Any],
) -> str:
    """The service's ARN when it is the long format, which names the cluster
    (`service/<cluster>/<name>`). The old short format (`service/<name>`) does not, so
    two clusters' services of one name would share it; those get a composed id."""
    arn = str(service.get("serviceArn") or "")
    if arn.endswith(f":service/{cluster}/{name}"):
        return arn
    return f"{account}/{region}/{ECS_SERVICE}/{cluster}/{name}"


def service_name_of(task: Mapping[str, Any]) -> Optional[str]:
    """The service a task belongs to, or None for a task no service owns."""
    group = str(task.get("group") or "")
    return (
        group[len(SERVICE_GROUP_PREFIX) :]
        if group.startswith(SERVICE_GROUP_PREFIX)
        else None
    )


def task_group_of(task: Mapping[str, Any]) -> str:
    """A serviceless task's group, falling back to its definition's family."""
    group = str(task.get("group") or "")
    if group:
        return group
    arn = str(task.get("taskDefinitionArn") or "")
    family = arn.rsplit("/", 1)[-1].split(":", 1)[0]
    return f"family:{family}" if family else "family:unknown"


# --- EKS ------------------------------------------------------------------------------


@dataclass(frozen=True)
class ClusterIdentity:
    """What an EKS cluster says about the roles its pods call AWS with."""

    irsa: Mapping[tuple[str, str], str]
    """(namespace, service account) -> the role its IRSA annotation names."""
    pod_identity: Mapping[tuple[str, str], str]
    """(namespace, service account) -> the role an EKS Pod Identity association binds."""
    node_roles: tuple[str, ...]
    """Roles of the cluster's managed node groups."""
    fargate_selectors: tuple[tuple[str, Mapping[str, str]], ...] = ()
    """(namespace pattern, labels) of each Fargate profile selector. A pod one selects
    runs on Fargate, where there is no node role to fall back to."""

    def on_fargate(self, namespace: str, labels: Mapping[str, str]) -> bool:
        """Whether a Fargate profile selects pods in this namespace with these labels.
        Namespaces and label values take `*` and `?` wildcards, as EKS allows."""
        for pattern, wanted in self.fargate_selectors:
            if not fnmatchcase(namespace, pattern):
                continue
            if all(
                key in labels and fnmatchcase(labels[key], value)
                for key, value in wanted.items()
            ):
                return True
        return False


def irsa_annotations(
    service_accounts: Iterable[Mapping[str, Any]],
) -> dict[tuple[str, str], str]:
    """(namespace, service account) -> the role ARN its IRSA annotation names."""
    out: dict[tuple[str, str], str] = {}
    for raw in service_accounts:
        meta = raw.get("metadata") or {}
        value = (meta.get("annotations") or {}).get(IRSA_ANNOTATION)
        if value and meta.get("namespace") and meta.get("name"):
            out[(str(meta["namespace"]), str(meta["name"]))] = str(value).strip()
    return out


def eks_workload(
    account: str,
    region: str,
    cluster: Mapping[str, Any],
    identity: ClusterIdentity,
    path_kind: str,
    asset_kind: str,
    raw: Mapping[str, Any],
) -> Optional[Workload]:
    """One Kubernetes object as a workload, or None when it is not its own workload.

    None for a Job or Pod something owns (a CronJob's Jobs, a ReplicaSet's pods), one in
    a system namespace, and one with no name. A controller is its own workload even when
    something owns it: an operator's custom resource (a model server, a Ray cluster)
    commonly owns the Deployment or StatefulSet that runs it, and that custom resource
    is not listed here, so dropping the controller would drop the workload.
    """
    meta = raw.get("metadata") or {}
    namespace = str(meta.get("namespace") or "")
    name = str(meta.get("name") or "")
    if not namespace or not name:
        return None
    if path_kind in _OWNED_BY_A_CONTROLLER and meta.get("ownerReferences"):
        return None
    if namespace in SYSTEM_NAMESPACES or namespace.startswith(
        SYSTEM_NAMESPACE_PREFIXES,
    ):
        return None
    cluster_name = str(cluster.get("name") or "")
    cluster_arn = str(cluster.get("arn") or "") or (
        f"arn:aws:eks:{region}:{account}:cluster/{cluster_name}"
    )
    pod = _pod_spec(raw, path_kind)
    containers = [*(pod.get("initContainers") or []), *(pod.get("containers") or [])]
    images = tuple(str(c.get("image")) for c in containers if c.get("image"))
    ksa = str(pod.get("serviceAccountName") or "") or "default"
    own = identity.irsa.get((namespace, ksa)) or identity.pod_identity.get(
        (namespace, ksa),
    )
    on_fargate = identity.on_fargate(namespace, _pod_labels(raw, path_kind))
    node_roles = () if on_fargate else identity.node_roles
    roles = (own,) if own else node_roles
    return Workload(
        account=account,
        region=region,
        kind=EKS_WORKLOAD,
        resource_id=f"{cluster_name}/{namespace}/{path_kind}/{name}",
        external_id=f"{cluster_arn}/k8s/namespaces/{namespace}/{asset_kind}/{name}",
        name=f"{cluster_name}/{namespace}/{name}",
        images=images,
        roles=roles,
        last_seen=_k8s_last_seen(raw),
        cluster=cluster_name,
        digests=_pod_digests(raw, path_kind),
        node_roles=() if own else node_roles,
    )


# --- selection ------------------------------------------------------------------------


def role_arn(account: str, role: str) -> str:
    """The role as an ARN, since CloudTrail always names the caller by ARN.

    Defensive: ECS accepts a bare role name for `taskRoleArn` but expands it when the
    task definition is registered, and `DescribeTaskDefinition` returns the full ARN
    (observed). Whether a `RunTask` override is stored bare has not been observed, and a
    bare name would otherwise never match."""
    role = role.strip()
    if role.startswith("arn:"):
        return role
    return f"arn:aws:iam::{account}:role/{role}"


def role_key(arn: str) -> str:
    """`<account>/<role name>`, lowercased: what two spellings of one role share.

    A role's ARN carries its path (`role/service-role/x`), which CloudTrail's session
    issuer keeps and a task definition may or may not; IAM role names are unique per
    account regardless of case. A bare name, which ECS accepts for `taskRoleArn`, has no
    account and keys on the name alone.
    """
    parts = arn.split(":")
    if len(parts) >= 6 and parts[2] == "iam":
        return f"{parts[4]}/{parts[5].rsplit('/', 1)[-1]}".lower()
    return arn.rsplit("/", 1)[-1].lower()


def select_workloads(
    workloads: Iterable[Workload],
    matcher: Matcher,
    ai_roles: Mapping[str, frozenset[str]] = {},
    report_all: bool = False,
) -> list[SelectedWorkload]:
    """The workloads to report, each with why.

    `ai_roles` is `role_key` -> the models that role called. Reported when an image matches an agent in the catalog, when it runs as one
    of `ai_roles`, or always when `report_all` is set.
    """
    selected: list[SelectedWorkload] = []
    for workload in workloads:
        findings = match_images(matcher, workload.images)
        matched = tuple(r for r in workload.roles if role_key(r) in ai_roles)
        reasons: list[str] = []
        if findings:
            reasons.append(REASON_CATALOG)
        if matched:
            reasons.append(REASON_AI_ROLE)
        if report_all and not reasons:
            reasons.append(REASON_REPORT_ALL)
        if reasons:
            models = sorted({m for r in matched for m in ai_roles[role_key(r)]})
            selected.append(
                SelectedWorkload(
                    workload,
                    findings,
                    tuple(reasons),
                    matched,
                    tuple(models),
                ),
            )
    return selected


def role_sharing(workloads: Iterable[Workload]) -> dict[str, int]:
    """`role_key` -> how many of the scan's workloads run as it."""
    counts: dict[str, int] = {}
    for workload in workloads:
        for key in {role_key(r) for r in workload.roles}:
            counts[key] = counts.get(key, 0) + 1
    return counts


def match_images(matcher: Matcher, images: Sequence[str]) -> tuple[Finding, ...]:
    """The catalog agents whose `images` name one of these image references.

    Through the vendored matcher's `container` route, as an endpoint's running container
    is. A digest (`@sha256:...`) is removed first: `image_repo` reads a tag, and a pinned
    reference would otherwise keep `@sha256` on its repository and match nothing.
    """
    rows = [{"kind": "container", "id": image.split("@", 1)[0]} for image in images]
    if not rows:
        return ()
    return matcher.match(rows).findings


def pinned_images(workload: Workload) -> list[str]:
    """Each image with the digests it runs at, `image@sha256:...`; as declared when
    none was reported or the reference already pins one."""
    out: list[str] = []
    for image in workload.images:
        digests = workload.digests.get(image, ())
        if "@" in image or not digests:
            out.append(image)
        else:
            out.extend(f"{image}@{d}" for d in digests)
    return out


def _pod_labels(raw: Mapping[str, Any], path_kind: str) -> Mapping[str, str]:
    """The labels a controller's pods are created with, or a bare pod's own."""
    if path_kind == "pod":
        meta = raw.get("metadata") or {}
    else:
        spec = raw.get("spec") or {}
        if path_kind == "cronjob":
            spec = (spec.get("jobTemplate") or {}).get("spec") or {}
        meta = (spec.get("template") or {}).get("metadata") or {}
    return {str(k): str(v) for k, v in (meta.get("labels") or {}).items()}


def _pod_spec(raw: Mapping[str, Any], path_kind: str) -> Mapping[str, Any]:
    spec = raw.get("spec") or {}
    if path_kind == "pod":
        return spec
    if path_kind == "cronjob":
        spec = (spec.get("jobTemplate") or {}).get("spec") or {}
    return (spec.get("template") or {}).get("spec") or {}


def _pod_digests(raw: Mapping[str, Any], path_kind: str) -> dict[str, tuple[str, ...]]:
    """A bare pod's running images' digests, from `status.containerStatuses[].imageID`.

    Only a pod carries a status per container; a controller's pods are not listed, so
    its digests are not known here.
    """
    if path_kind != "pod":
        return {}
    status = raw.get("status") or {}
    out: dict[str, tuple[str, ...]] = {}
    for c in [
        *(status.get("initContainerStatuses") or []),
        *(status.get("containerStatuses") or []),
    ]:
        image = str(c.get("image") or "")
        image_id = str(c.get("imageID") or "")
        if image and "@sha256:" in image_id:
            out[image] = ("sha256:" + image_id.rsplit("@sha256:", 1)[-1],)
    return out


def _k8s_last_seen(raw: Mapping[str, Any]) -> Optional[datetime]:
    """The latest time the object says it changed: a status condition, a CronJob's
    last schedule, a pod's start, else when it was created."""
    status = raw.get("status") or {}
    times = [
        _timestamp(c.get(key))
        for c in status.get("conditions") or []
        for key in ("lastUpdateTime", "lastTransitionTime")
    ]
    times += [
        _timestamp(status.get("lastScheduleTime")),
        _timestamp(status.get("startTime")),
        _timestamp((raw.get("metadata") or {}).get("creationTimestamp")),
    ]
    found = [t for t in times if t is not None]
    return max(found) if found else None


def _as_datetime(value: Any) -> Optional[datetime]:
    """boto3 hands back aware datetimes; a string is parsed as Kubernetes' are."""
    if isinstance(value, datetime):
        return value if value.tzinfo is not None else None
    return _timestamp(value)


def _timestamp(value: Any) -> Optional[datetime]:
    """An RFC 3339 time as Kubernetes writes it, or None."""
    if not value or not isinstance(value, str):
        return None
    text = value.strip().replace("Z", "+00:00")
    if "." in text:
        head, _, rest = text.partition(".")
        zone_at = next((i for i, ch in enumerate(rest) if not ch.isdigit()), len(rest))
        digits, zone = rest[:zone_at], rest[zone_at:]
        text = f"{head}.{digits[:6]}{zone}"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    return parsed if parsed.tzinfo is not None else None
