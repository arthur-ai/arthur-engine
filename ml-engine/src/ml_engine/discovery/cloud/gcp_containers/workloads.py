"""Container workloads on Google Cloud, read off the API objects and selected.

Pure: no call is made here. `client.py` fetches the objects; this turns each into one
`Workload` -- name, images, the GCP service account(s) it runs as -- and
`select_workloads` decides which are reported. Kept apart so the selection can be called
again with a different set of AI-calling service accounts without listing anything.

ONE WORKLOAD PER STABLE NAME. A Cloud Run service or job by its name, never a revision
or an execution. A GKE workload by its controller -- Deployment, StatefulSet, DaemonSet,
CronJob -- and only a Job or Pod that nothing owns stands for itself. A ReplicaSet's hash
or a Job's timestamp suffix would make every rollout a new agent.

WHICH GCP SERVICE ACCOUNT A WORKLOAD RUNS AS. That is what Vertex AI's audit log names
as the caller, so it is the key that joins a workload to the models it called.

- Cloud Run: the revision template's `serviceAccount`; when unset, Cloud Run runs as the
  Compute Engine default service account (`<project number>-compute@...`).
- GKE with Workload Identity on the cluster: the Kubernetes service account's
  `iam.gke.io/gcp-service-account` annotation. A KSA without one has no GCP service
  account to report: its pods call Google as a federated principal, not as the node.
- GKE without Workload Identity, or on a node pool that opts out of it
  (`GCE_METADATA`): the node pool's service account, which every pod on the node
  shares. Which pool a controller's pods land on is the scheduler's, so every such
  pool's account is listed. A match on one is a match on the node, not the workload,
  and the record says which account matched.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Iterable, Mapping, Optional, Sequence

from discovery.catalog import Finding, Matcher

CLOUD_RUN_SERVICE = "cloud_run_service"
CLOUD_RUN_JOB = "cloud_run_job"
GKE_WORKLOAD = "gke_workload"

# A GKE workload's controller kinds, as (list path, kind in resource_id, the path
# segment Cloud Asset Inventory names the kind by). Pods and Jobs are listed for the
# ones nothing owns.
K8S_KINDS: tuple[tuple[str, str, str], ...] = (
    ("/apis/apps/v1/deployments", "deployment", "apps/deployments"),
    ("/apis/apps/v1/statefulsets", "statefulset", "apps/statefulsets"),
    ("/apis/apps/v1/daemonsets", "daemonset", "apps/daemonsets"),
    ("/apis/batch/v1/cronjobs", "cronjob", "batch/cronjobs"),
    ("/apis/batch/v1/jobs", "job", "batch/jobs"),
    ("/api/v1/pods", "pod", "pods"),
)

# Namespaces GKE and Kubernetes run their own components in. Their workloads run on the
# node's service account like any other, so an AI-calling node account would otherwise
# report every one of them.
SYSTEM_NAMESPACES = frozenset({"kube-system", "kube-public", "kube-node-lease"})
SYSTEM_NAMESPACE_PREFIXES = ("gke-", "gmp-")

WORKLOAD_IDENTITY_ANNOTATION = "iam.gke.io/gcp-service-account"

# How the default compute service account is named before its project number is known.
DEFAULT_SERVICE_ACCOUNT = "default"

# Why a workload is reported.
REASON_CATALOG = "catalog"
REASON_AI_SERVICE_ACCOUNT = "ai_service_account"
REASON_REPORT_ALL = "report_all"


@dataclass(frozen=True)
class Workload:
    project: str
    location: str
    kind: str
    """CLOUD_RUN_SERVICE, CLOUD_RUN_JOB or GKE_WORKLOAD."""
    resource_id: str
    """The stable name: the service or job name; `<cluster>/<ns>/<kind>/<name>` on GKE."""
    external_id: str
    name: str
    images: tuple[str, ...]
    service_accounts: tuple[str, ...]
    """GCP service accounts it runs as. `DEFAULT_SERVICE_ACCOUNT` until resolved."""
    last_seen: Optional[datetime]
    cluster: Optional[str] = None
    k8s_service_account: Optional[str] = None


@dataclass(frozen=True)
class SelectedWorkload:
    workload: Workload
    findings: tuple[Finding, ...]
    reasons: tuple[str, ...]
    matched_service_accounts: tuple[str, ...] = field(default_factory=tuple)


def cloud_run_workload(
    project: str,
    raw: Mapping[str, Any],
    kind: str,
) -> Optional[Workload]:
    """One Cloud Run v2 Service or Job, or None when its name cannot be addressed.

    The name is Google's own (`projects/P/locations/L/services/N`), kept verbatim as
    `external_id`. A service's revision template is `template`; a job's task template is
    `template.template`.
    """
    name = str(raw.get("name") or "")
    parts = name.split("/")
    collection = "services" if kind == CLOUD_RUN_SERVICE else "jobs"
    if (
        len(parts) != 6
        or parts[0] != "projects"
        or parts[2] != "locations"
        or parts[4] != collection
        or not all(p.strip() for p in (parts[1], parts[3], parts[5]))
    ):
        return None
    template = raw.get("template") or {}
    if kind == CLOUD_RUN_JOB:
        template = template.get("template") or {}
    images = tuple(
        str(c.get("image")) for c in template.get("containers") or [] if c.get("image")
    )
    account = str(template.get("serviceAccount") or "") or DEFAULT_SERVICE_ACCOUNT
    return Workload(
        project=project,
        location=parts[3],
        kind=kind,
        resource_id=parts[5],
        external_id=name,
        name=parts[5],
        images=images,
        service_accounts=(account,),
        last_seen=_timestamp(raw.get("updateTime"))
        or _timestamp(raw.get("createTime")),
    )


@dataclass(frozen=True)
class ClusterIdentity:
    """What a GKE cluster says about the GCP identity its pods call Google with."""

    workload_identity: bool
    node_service_accounts: tuple[str, ...]
    """Accounts of the node pools on which a pod calls Google as the node."""

    @classmethod
    def of(cls, cluster: Mapping[str, Any]) -> "ClusterIdentity":
        pool = (cluster.get("workloadIdentityConfig") or {}).get("workloadPool")
        wi = bool(pool)
        accounts: list[str] = []
        for node_pool in cluster.get("nodePools") or []:
            config = node_pool.get("config") or {}
            mode = (config.get("workloadMetadataConfig") or {}).get("mode") or ""
            on_node = mode == "GCE_METADATA" or (mode != "GKE_METADATA" and not wi)
            if on_node:
                account = str(config.get("serviceAccount") or "")
                accounts.append(account or DEFAULT_SERVICE_ACCOUNT)
        return cls(
            workload_identity=wi,
            node_service_accounts=tuple(dict.fromkeys(accounts)),
        )


def gke_workload(
    project: str,
    cluster: Mapping[str, Any],
    identity: ClusterIdentity,
    annotations: Mapping[tuple[str, str], str],
    path_kind: str,
    asset_kind: str,
    raw: Mapping[str, Any],
) -> Optional[Workload]:
    """One Kubernetes object as a workload, or None when it is not its own workload.

    None for an object something owns (a ReplicaSet's pods, a CronJob's Jobs), one in a
    system namespace, and one with no name. `annotations` is (namespace, KSA) -> the
    GCP service account its Workload Identity annotation names.
    """
    meta = raw.get("metadata") or {}
    namespace = str(meta.get("namespace") or "")
    name = str(meta.get("name") or "")
    if not namespace or not name or meta.get("ownerReferences"):
        return None
    if namespace in SYSTEM_NAMESPACES or namespace.startswith(
        SYSTEM_NAMESPACE_PREFIXES,
    ):
        return None
    cluster_name = str(cluster.get("name") or "")
    location = str(cluster.get("location") or "")
    pod = _pod_spec(raw, path_kind)
    images = tuple(
        str(c.get("image"))
        for c in [*(pod.get("initContainers") or []), *(pod.get("containers") or [])]
        if c.get("image")
    )
    ksa = str(pod.get("serviceAccountName") or "") or "default"
    accounts: list[str] = []
    annotated = (
        annotations.get((namespace, ksa)) if identity.workload_identity else None
    )
    if annotated:
        accounts.append(annotated)
    accounts.extend(identity.node_service_accounts)
    return Workload(
        project=project,
        location=location,
        kind=GKE_WORKLOAD,
        resource_id=f"{cluster_name}/{namespace}/{path_kind}/{name}",
        external_id=(
            f"projects/{project}/locations/{location}/clusters/{cluster_name}"
            f"/k8s/namespaces/{namespace}/{asset_kind}/{name}"
        ),
        name=f"{cluster_name}/{namespace}/{name}",
        images=images,
        service_accounts=tuple(dict.fromkeys(accounts)),
        last_seen=_k8s_last_seen(raw),
        cluster=cluster_name,
        k8s_service_account=ksa,
    )


def workload_identity_annotations(
    service_accounts: Iterable[Mapping[str, Any]],
) -> dict[tuple[str, str], str]:
    """(namespace, KSA name) -> the GCP service account it is bound to, if any."""
    out: dict[tuple[str, str], str] = {}
    for raw in service_accounts:
        meta = raw.get("metadata") or {}
        value = (meta.get("annotations") or {}).get(WORKLOAD_IDENTITY_ANNOTATION)
        if value and meta.get("namespace") and meta.get("name"):
            out[(str(meta["namespace"]), str(meta["name"]))] = str(value)
    return out


def resolve_default_accounts(
    workload: Workload,
    default_account: Callable[[str], Optional[str]],
) -> Workload:
    """The workload with `DEFAULT_SERVICE_ACCOUNT` replaced by its project's email.

    Dropped when the email cannot be resolved: a placeholder is not an account anything
    can join on.
    """
    if DEFAULT_SERVICE_ACCOUNT not in workload.service_accounts:
        return workload
    resolved = default_account(workload.project)
    accounts = tuple(
        dict.fromkeys(
            (resolved if a == DEFAULT_SERVICE_ACCOUNT else a)
            for a in workload.service_accounts
            if a != DEFAULT_SERVICE_ACCOUNT or resolved
        ),
    )
    return Workload(**{**workload.__dict__, "service_accounts": accounts})


def select_workloads(
    workloads: Iterable[Workload],
    matcher: Matcher,
    ai_service_accounts: frozenset[str] = frozenset(),
    report_all: bool = False,
) -> list[SelectedWorkload]:
    """The workloads to report, each with why.

    A workload is reported when an image matches an agent in the catalog, when it runs
    as one of `ai_service_accounts` (the callers a Vertex AI audit-log read found), or
    always when `report_all` is set, so every workload's service account is there to be
    joined. Service accounts compare case-insensitively, as Google's emails do.
    """
    ai = {a.lower() for a in ai_service_accounts}
    selected: list[SelectedWorkload] = []
    for workload in workloads:
        findings = match_images(matcher, workload.images)
        matched = tuple(a for a in workload.service_accounts if a.lower() in ai)
        reasons: list[str] = []
        if findings:
            reasons.append(REASON_CATALOG)
        if matched:
            reasons.append(REASON_AI_SERVICE_ACCOUNT)
        if report_all and not reasons:
            reasons.append(REASON_REPORT_ALL)
        if reasons:
            selected.append(
                SelectedWorkload(workload, findings, tuple(reasons), matched),
            )
    return selected


def match_images(matcher: Matcher, images: Sequence[str]) -> tuple[Finding, ...]:
    """The catalog agents whose `images` name one of these image references.

    Through the vendored matcher's `container` route, which normalises each reference
    with `classify.image_repo` exactly as an endpoint's running-container row is. A
    digest (`@sha256:...`) is removed first: `image_repo` reads a tag, and a pinned
    reference would otherwise keep `@sha256` on its repository and match nothing.
    """
    rows = [{"kind": "container", "id": image.split("@", 1)[0]} for image in images]
    if not rows:
        return ()
    return matcher.match(rows).findings


def _pod_spec(raw: Mapping[str, Any], path_kind: str) -> Mapping[str, Any]:
    spec = raw.get("spec") or {}
    if path_kind == "pod":
        return spec
    if path_kind == "cronjob":
        spec = (spec.get("jobTemplate") or {}).get("spec") or {}
    return (spec.get("template") or {}).get("spec") or {}


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


def _timestamp(value: Any) -> Optional[datetime]:
    """An RFC 3339 time as Google and Kubernetes write it, or None."""
    if not value or not isinstance(value, str):
        return None
    text = value.strip().replace("Z", "+00:00")
    # Google writes nanoseconds; fromisoformat takes at most microseconds.
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
