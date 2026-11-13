"""Cloud Run and GKE's side of a DISCOVER_AGENTS scan: container runtime inventory.

Lists every Cloud Run service, Cloud Run job and GKE workload in the configured projects
and reports the ones that are, or may be, agents. A container runtime lists every
workload, not only agents, so a workload is reported when:

- one of its images is an agent's in the catalog (an `images` identifier in the
  vendored catalog, or the source config's own), matched by the vendored matcher's
  container route; or
- it runs as a GCP service account that called a Vertex AI model in the lookback --
  read off each project's Data Access audit log by this scan itself, with the same
  reader and fold `gcp_vertex` uses, so no other source or job has to supply it; or
- the source sets `report_all_workloads`, which reports every workload so each one's
  service account is in the record for that join to use.

THE RECORD. `instance` is the project id, `scope` the region (a GKE cluster's location,
a zone for a zonal cluster), `resource_kind` one of `cloud_run_service`,
`cloud_run_job`, `gke_workload`, and `resource_id` the workload's stable name -- never
a revision, an execution or a pod. `external_id` is
`projects/{project}/locations/{location}/{kind}/{name}`: for Cloud Run that is Google's
own resource name verbatim (`.../services/N`, `.../jobs/N`); for GKE it is the path
Cloud Asset Inventory names the object by
(`.../clusters/C/k8s/namespaces/NS/apps/deployments/N`), without its host prefix.
`service_names` is left empty: no span from these workloads has been captured to show
what `service.name` they emit.

THE SERVICE ACCOUNT IS IN THE NAME. `AgentObservations` has no field for the identity a
workload runs as (`permissions` is what the agent may do, `assigned_user` is a person),
so the record's name carries it: `<workload> (runs as <account>, ...)`, with
`shared by N workloads` when several of the scan's workloads run as it. See
`workloads.py` for which account that is on each runtime.

THE LOOKBACK BOUNDS ONLY THE CALLERS. The workloads are an inventory, not a log: every
scan lists every workload as it is now. The audit-log read that names the AI-calling
service accounts covers the scan's lookback (30 days for a zero lookback, as in
`gcp_vertex`), and their models become the record's `llm_models`. Reading it needs
`roles/logging.privateLogViewer` and Data Access audit logs on for
`aiplatform.googleapis.com`; a refused read is a denied scope, and that project's
workloads are selected by catalog image (or `report_all_workloads`) only.

ONE REFUSED API IS A DENIED SCOPE. A project with the GKE API off, a role without
`run.jobs.list`, a cluster whose endpoint this engine cannot reach: each is logged,
reported as a denied scope on the run (`ReportsDeniedScopes`), and the rest of the scan
goes on. Only when nothing at all could be listed does the scan
fail, with the first refusal's status, so a key with no access reads as denied rather
than as a project without workloads. A refused credential ends the scan at once.

EVERYTHING IS COLLECTED BEFORE THE FIRST BATCH. The default service account's email
needs the project number, and the counts in the summary line need every listing; a
scan is a few dozen list calls, so the cost is one delay rather than lost records. A
stop check that fires mid-scan yields what was collected.
"""

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable, ClassVar, Iterator, Mapping, Optional, Sequence

import google.auth
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
from google.auth.credentials import Credentials
from google.auth.exceptions import (
    DefaultCredentialsError,
    GoogleAuthError,
    RefreshError,
)
from google.auth.transport.requests import AuthorizedSession

from discovery.catalog import Matcher
from discovery.cloud.gcp_containers.client import (
    GcpContainersClient,
    GcpContainersError,
    KubernetesApi,
    ScanStopped,
)
from discovery.cloud.gcp_containers.workloads import (
    CLOUD_RUN_JOB,
    CLOUD_RUN_SERVICE,
    K8S_KINDS,
    ClusterIdentity,
    SelectedWorkload,
    Workload,
    cloud_run_workload,
    gke_workload,
    resolve_default_accounts,
    select_workloads,
    workload_identity_annotations,
)
from discovery.cloud.gcp_vertex.audit import (
    AuditCounts,
    AuditReadError,
    Caller,
    EntryReader,
    audit_filter,
    fold,
    read_entries,
    since_for,
)
from discovery.endpoint.scope import parse_group_names
from discovery.gcp_credentials import (
    GCP_PROJECT_ID,
    SERVICE_ACCOUNT_KEY_FIELD,
    mark_refused_credential,
    service_account_credentials,
)
from job_executors.discovery_scan import (
    DENIED_PERMISSION,
    DENIED_UNREACHABLE,
    DeniedScope,
    DiscoveryConfigurationError,
)

VENDOR = "gcp_containers"

# Non-sensitive source fields.
PROJECT_IDS_FIELD = "project_ids"
REGIONS_FIELD = "regions"
REPORT_ALL_FIELD = "report_all_workloads"

# Opt-in for Application Default Credentials when a source has no key, as Vertex has.
ALLOW_ADC_ENV_VAR = "ARTHUR_ENGINE_GCP_CONTAINERS_ALLOW_ADC"

CLOUD_PLATFORM_SCOPE = "https://www.googleapis.com/auth/cloud-platform"

BATCH_SIZE = 100

_TRUE = frozenset({"true", "1", "yes"})
_FALSE = frozenset({"false", "0", "no", ""})


@dataclass(frozen=True)
class ContainersSettings:
    project_ids: tuple[str, ...]
    regions: tuple[str, ...] = ()
    """Regions to list Cloud Run jobs in. Empty is every region Cloud Run serves."""
    report_all_workloads: bool = False


def authorized_session(credentials: Optional[Credentials]) -> requests.Session:
    """A requests session that signs every call; None is the engine's ADC."""
    if credentials is None:
        try:
            credentials, _ = google.auth.default(scopes=[CLOUD_PLATFORM_SCOPE])
        except DefaultCredentialsError as e:
            raise DiscoveryConfigurationError(
                f"Cloud Run and GKE source has no '{SERVICE_ACCOUNT_KEY_FIELD}', and "
                f"this engine has no Application Default Credentials to use instead: "
                f"{e}",
            ) from None
    return AuthorizedSession(credentials)  # type: ignore[no-untyped-call]


class _Reads:
    """Which listings failed, so a scan that read nothing can say why, and which parts
    of the scope they were, so the run can report them."""

    def __init__(self, logger: logging.Logger) -> None:
        self._log = logger
        self.succeeded = 0
        self.failures: list[GcpContainersError] = []
        self.denied: list[DeniedScope] = []

    def failed(self, what: str, scope: str, e: GcpContainersError) -> None:
        if e.status_code == 401:
            raise e
        self._log.warning("%s not listed (%s); missing from this scan", what, e)
        self.failures.append(e)
        self.deny(
            scope, DENIED_PERMISSION if e.status_code == 403 else DENIED_UNREACHABLE
        )

    def deny(self, scope: str, reason: str) -> None:
        if all(d.scope != scope for d in self.denied):
            self.denied.append(DeniedScope(scope, reason))


class GcpContainersConnector:
    """Implements `job_executors.discovery_scan.DiscoverySourceConnector`,
    `ReportsDeniedScopes` and `AcceptsStopCheck`.

    Built fresh for every scan -- see `DiscoveryConnectorFactory` -- so it may hold
    that scan's stop check.
    """

    SENSITIVE_FIELDS: ClassVar[frozenset[str]] = frozenset({SERVICE_ACCOUNT_KEY_FIELD})

    def __init__(
        self,
        session_for: Callable[
            [Optional[Credentials]],
            requests.Session,
        ] = authorized_session,
        ai_service_accounts: frozenset[str] = frozenset(),
        audit_reader: Optional[EntryReader] = None,
    ) -> None:
        self._session_for = session_for
        self._ai_service_accounts = ai_service_accounts
        # None reads the module's `read_entries` at scan time, so a test can stub it.
        self._audit_reader = audit_reader
        self._should_stop: Callable[[], bool] = lambda: False
        self._denied: Sequence[DeniedScope] = ()

    def denied_scopes(self) -> Sequence[DeniedScope]:
        """The parts of the scope this scan was refused; asked once it ends."""
        return tuple(self._denied)

    def stop_when(self, should_stop: Callable[[], bool]) -> None:
        """Asked before every call, so a stop never waits on another listing."""
        self._should_stop = should_stop

    def scan(
        self,
        config: DiscoverySourceConfigSpec,
        lookback_hours: int,
        credentials: Mapping[str, Optional[str]],
        source_fields: Mapping[str, str],
        logger: logging.Logger,
    ) -> Iterator[Sequence[DiscoveredAgentRecord]]:
        """`logger` is the JOB's. `lookback_hours` bounds the audit-log read of
        AI-calling service accounts only: see the module."""
        settings = settings_from(source_fields)
        google_credentials = service_account_credentials(
            credentials,
            source="Cloud Run and GKE source",
            allow_adc_env_var=ALLOW_ADC_ENV_VAR,
            scopes=[CLOUD_PLATFORM_SCOPE],
        )
        matcher = Matcher.from_source(catalog_json=config.query or None, logger=logger)
        client = GcpContainersClient(
            self._session_for(google_credentials),
            logger,
            should_stop=self._should_stop,
        )
        logger.info(
            "Cloud Run and GKE scan starting against project(s) %s, catalog %s, "
            "using %s; reporting %s. Every workload is listed; the lookback bounds only "
            "the audit-log read of AI callers.",
            ", ".join(settings.project_ids),
            matcher.catalog_sha,
            (
                "the source's service account key"
                if google_credentials is not None
                else "Application Default Credentials"
            ),
            (
                "every workload"
                if settings.report_all_workloads
                else "workloads whose image is in the catalog or whose service "
                "account calls AI"
            ),
        )

        reads = _Reads(logger)
        self._denied = reads.denied
        workloads: list[Workload] = []
        stopped = False
        try:
            for project in settings.project_ids:
                workloads.extend(_cloud_run(client, project, settings, reads, logger))
                workloads.extend(_gke(client, project, reads, logger))
        except ScanStopped:
            stopped = True
            logger.info(
                "Cloud Run and GKE scan stopped early on request after %s workload(s)",
                len(workloads),
            )

        defaults: dict[str, Optional[str]] = {}

        def default_account(project: str) -> Optional[str]:
            if project not in defaults:
                defaults[project] = _default_account(client, project, logger)
            return defaults[project]

        if not stopped:
            try:
                workloads = [
                    resolve_default_accounts(w, default_account) for w in workloads
                ]
            except ScanStopped:
                stopped = True

        callers: dict[str, set[str]] = {}
        if not stopped:
            callers = self._ai_callers(
                settings.project_ids,
                google_credentials,
                lookback_hours,
                reads,
                logger,
            )
        selected = select_workloads(
            workloads,
            matcher,
            self._ai_service_accounts | frozenset(callers),
            settings.report_all_workloads,
        )
        sharing = accounts_shared(workloads)
        records = [
            r for r in (record_for(s, logger, callers, sharing) for s in selected) if r
        ]
        _log_summary(workloads, selected, records, logger)

        for start in range(0, len(records), BATCH_SIZE):
            yield records[start : start + BATCH_SIZE]

        if not stopped and reads.failures and not reads.succeeded:
            # Nothing at all could be listed: a key with no access, not an empty
            # estate. The first refusal carries the status failure_code reads.
            raise reads.failures[0]

    def _ai_callers(
        self,
        projects: Sequence[str],
        credentials: Optional[Credentials],
        lookback_hours: int,
        reads: _Reads,
        logger: logging.Logger,
    ) -> dict[str, set[str]]:
        """Each service account that called a Vertex AI model in the lookback, with
        the models it called, read off every project's Data Access audit log."""
        since = since_for(lookback_hours, datetime.now(timezone.utc))
        models: dict[str, set[str]] = {}
        for project in projects:
            if self._should_stop():
                break
            counts = AuditCounts()
            try:
                reader = self._audit_reader or read_entries
                found: dict[tuple[str, str], Caller] = fold(
                    reader(project, audit_filter(project, since), credentials),
                    counts,
                )
            except AuditReadError as e:
                if e.status_code == 401:
                    # A refused credential ends the scan, as it does for a listing.
                    raise GcpContainersError(
                        f"Vertex AI audit log read for project {project} was "
                        f"refused the credential: {e}",
                        status_code=401,
                    ) from e
                reads.deny(
                    f"projects/{project}/vertex-ai-audit-log",
                    (DENIED_PERMISSION if e.status_code == 403 else DENIED_UNREACHABLE),
                )
                logger.warning(
                    "Vertex AI audit log not read for project %s (HTTP %s), so its "
                    "AI-calling service accounts are unknown and its workloads are "
                    "selected by catalog image only.%s",
                    project,
                    e.status_code,
                    _audit_read_hint(e.status_code),
                )
                continue
            except RefreshError as e:
                # No token could be minted for the read. A refused credential ends the
                # scan as it does for a listing; see discovery.gcp_credentials.
                mark_refused_credential(e)
                if getattr(e, "status_code", None) == 401:
                    raise GcpContainersError(
                        f"Vertex AI audit log read for project {project} was "
                        f"refused the credential: {e}",
                        status_code=401,
                    ) from e
                reads.deny(
                    f"projects/{project}/vertex-ai-audit-log", DENIED_UNREACHABLE
                )
                logger.warning(
                    "Vertex AI audit log not read for project %s (%s); its workloads "
                    "are selected by catalog image only.",
                    project,
                    type(e).__name__,
                )
                continue
            except (requests.RequestException, GoogleAuthError, ValueError) as e:
                reads.deny(
                    f"projects/{project}/vertex-ai-audit-log", DENIED_UNREACHABLE
                )
                logger.warning(
                    "Vertex AI audit log not read for project %s (%s); its workloads "
                    "are selected by catalog image only.",
                    project,
                    type(e).__name__,
                )
                continue
            for caller in found.values():
                models.setdefault(caller.email.lower(), set()).update(caller.models)
            logger.info(
                "Vertex AI audit log for %s: %s model call(s) from %s service "
                "account(s) since %s%s",
                project,
                counts.calls,
                len({c.email for c in found.values()}),
                since.isoformat(),
                "; capped, older calls not read" if counts.capped else "",
            )
        return models


def _cloud_run(
    client: GcpContainersClient,
    project: str,
    settings: ContainersSettings,
    reads: _Reads,
    logger: logging.Logger,
) -> list[Workload]:
    out: list[Workload] = []
    try:
        services = list(client.cloud_run_services(project))
        reads.succeeded += 1
        out.extend(_cloud_run_workloads(project, services, CLOUD_RUN_SERVICE, logger))
    except GcpContainersError as e:
        reads.failed(
            f"Cloud Run services in project {project}",
            f"projects/{project}/cloud-run-services",
            e,
        )

    regions = settings.regions
    if not regions:
        try:
            regions = tuple(client.cloud_run_regions(project))
        except GcpContainersError as e:
            reads.failed(
                f"Cloud Run regions (for jobs) in project {project}",
                f"projects/{project}/cloud-run-jobs",
                e,
            )
            return out
    for region in regions:
        try:
            jobs = list(client.cloud_run_jobs(project, region))
            reads.succeeded += 1
            out.extend(_cloud_run_workloads(project, jobs, CLOUD_RUN_JOB, logger))
        except GcpContainersError as e:
            reads.failed(
                f"Cloud Run jobs in {project}/{region}",
                f"projects/{project}/locations/{region}/cloud-run-jobs",
                e,
            )
    return out


def _cloud_run_workloads(
    project: str,
    raws: Sequence[Mapping[str, object]],
    kind: str,
    logger: logging.Logger,
) -> list[Workload]:
    out = []
    for raw in raws:
        workload = cloud_run_workload(project, raw, kind)
        if workload is None:
            logger.warning(
                "Cloud Run returned a %s with an unrecognised name %r; skipped",
                kind,
                raw.get("name"),
            )
            continue
        out.append(workload)
    return out


def _gke(
    client: GcpContainersClient,
    project: str,
    reads: _Reads,
    logger: logging.Logger,
) -> list[Workload]:
    try:
        clusters = client.gke_clusters(project)
        reads.succeeded += 1
    except GcpContainersError as e:
        reads.failed(
            f"GKE clusters in project {project}", f"projects/{project}/gke-clusters", e
        )
        return []

    out: list[Workload] = []
    for cluster in clusters:
        label = f"GKE cluster {project}/{cluster.get('location')}/{cluster.get('name')}"
        if cluster.get("status") not in (None, "RUNNING", "RECONCILING", "DEGRADED"):
            logger.info("%s is %s; not listed", label, cluster.get("status"))
            continue
        identity = ClusterIdentity.of(cluster)
        try:
            with client.kubernetes(cluster) as kube:
                annotations = (
                    workload_identity_annotations(kube.items("/api/v1/serviceaccounts"))
                    if identity.workload_identity
                    else {}
                )
                replicasets = _deployment_replicasets(kube, label, logger)
                found: list[Workload] = []
                for path, kind, asset_kind in K8S_KINDS:
                    for raw in kube.items(path):
                        workload = gke_workload(
                            project,
                            cluster,
                            identity,
                            annotations,
                            kind,
                            asset_kind,
                            raw,
                            replicasets,
                        )
                        if workload is not None:
                            found.append(workload)
            # A cluster counts only when every kind was listed: half a cluster would
            # read as workloads that were deleted.
            out.extend(found)
            reads.succeeded += 1
        except GcpContainersError as e:
            reads.failed(
                f"Workloads in {label}",
                f"projects/{project}/locations/{cluster.get('location')}"
                f"/clusters/{cluster.get('name')}",
                e,
            )
    return out


def _deployment_replicasets(
    kube: KubernetesApi,
    label: str,
    logger: logging.Logger,
) -> Optional[frozenset[tuple[str, str]]]:
    """(namespace, name) of each ReplicaSet a Deployment owns, or None when they cannot
    be read, which folds every ReplicaSet's pods as before."""
    try:
        return frozenset(
            (
                str((rs.get("metadata") or {}).get("namespace") or ""),
                str((rs.get("metadata") or {}).get("name") or ""),
            )
            for rs in kube.items("/apis/apps/v1/replicasets")
            if any(
                o.get("kind") == "Deployment"
                for o in (rs.get("metadata") or {}).get("ownerReferences") or []
            )
        )
    except GcpContainersError as e:
        if e.status_code == 401:
            raise
        logger.warning(
            "ReplicaSets of %s not read (%s); pods of a ReplicaSet a custom controller "
            "owns are folded into it and not reported",
            label,
            e,
        )
        return None


def _default_account(
    client: GcpContainersClient,
    project: str,
    logger: logging.Logger,
) -> Optional[str]:
    """The project's Compute Engine default service account, or None if unknown."""
    try:
        number = client.project_number(project)
    except GcpContainersError as e:
        if e.status_code == 401:
            raise
        logger.warning(
            "Project %s's number could not be read (%s); workloads running as the "
            "Compute Engine default service account are reported without it",
            project,
            e,
        )
        return None
    return f"{number}-compute@developer.gserviceaccount.com"


def _audit_read_hint(status_code: int) -> str:
    """What a refused or failed audit-log read most likely needs, by its status."""
    if status_code == 403:
        return " Reading it needs roles/logging.privateLogViewer on the project."
    if status_code == 404:
        return " The project was not found; check the project ID."
    return ""


def record_for(
    selected: SelectedWorkload,
    logger: logging.Logger,
    caller_models: Optional[Mapping[str, set[str]]] = None,
    sharing: Optional[Mapping[str, int]] = None,
) -> Optional[DiscoveredAgentRecord]:
    """One reported workload's record, or None when it has no time to date it by.

    `caller_models` maps an AI-calling service account to the models it called; a
    workload that runs as one carries those models as its `llm_models`.
    """
    workload = selected.workload
    if workload.last_seen is None:
        logger.warning(
            "%s: neither an update nor a create time; skipped, because last_seen is "
            "required and inventing one would date the record to the scan",
            workload.external_id,
        )
        return None
    classification = next(
        (f.classification for f in selected.findings if f.classification),
        None,
    )
    models = sorted(
        {
            m
            for account in selected.matched_service_accounts
            for m in (caller_models or {}).get(account.lower(), set())
        }
    )
    return DiscoveredAgentRecord(
        external_id=workload.external_id,
        name=display_name(selected, sharing),
        last_seen=workload.last_seen,
        llm_models=[LLMModel(name=m) for m in models],
        runs_on=RunsOn.GCP,
        creation_source=CloudAgentCreationSource(
            vendor=VENDOR,
            address=SourceAddress(
                instance=workload.project,
                scope=workload.location,
                resource_kind=workload.kind,
                resource_id=workload.resource_id,
            ),
            observations=AgentObservations(
                classification=classification,
                host_group=workload.cluster,
                # A container is installed as its image: the references it declares.
                install_path=", ".join(workload.images) or None,
            ),
        ),
    )


def accounts_shared(workloads: Sequence[Workload]) -> dict[str, int]:
    """How many of the scan's workloads run as each service account (lower-cased)."""
    counts: dict[str, int] = {}
    for workload in workloads:
        for account in {a.lower() for a in workload.service_accounts}:
            counts[account] = counts.get(account, 0) + 1
    return counts


def display_name(
    selected: SelectedWorkload,
    sharing: Optional[Mapping[str, int]] = None,
) -> str:
    """`<workload> [<catalog agents>] (runs as <account>[, node account][, shared by N
    workloads])`.

    A node's account is marked, since every pod on the node calls Google as it. An
    account several workloads run as -- a node's account, one account for many jobs --
    says so, because a join on it (the audit log's callers) cannot tell those workloads
    apart: a match through it is weak.
    """
    workload = selected.workload
    name = workload.name
    if selected.findings:
        name += f" [{', '.join(f.name for f in selected.findings)}]"
    if workload.service_accounts:
        shared = max(
            (sharing or {}).get(a.lower(), 1) for a in workload.service_accounts
        )
        node = set(workload.node_service_accounts)
        accounts = ", ".join(
            f"{a}, node account" if a in node else a for a in workload.service_accounts
        )
        suffix = f", shared by {shared} workloads" if shared > 1 else ""
        name += f" (runs as {accounts}{suffix})"
    return name


def settings_from(source_fields: Mapping[str, str]) -> ContainersSettings:
    """The projects, job regions and report-all toggle from the source's fields."""
    projects = parse_group_names(source_fields.get(PROJECT_IDS_FIELD))
    if not projects:
        raise DiscoveryConfigurationError(
            f"Cloud Run and GKE source is missing required field "
            f"'{PROJECT_IDS_FIELD}'. It is a source field, not a secret.",
        )
    bad = [p for p in projects if not GCP_PROJECT_ID.match(p)]
    if bad:
        raise DiscoveryConfigurationError(
            f"Cloud Run and GKE source's '{PROJECT_IDS_FIELD}' has value(s) that are "
            f"not GCP project IDs: {', '.join(repr(p) for p in bad)}. A project ID is "
            f"6 to 30 lowercase letters, digits and hyphens, not the project's name or "
            f"number.",
        )
    regions = parse_group_names(source_fields.get(REGIONS_FIELD))
    bad_regions = [r for r in regions if not _is_region(r)]
    if bad_regions:
        raise DiscoveryConfigurationError(
            f"Cloud Run and GKE source's '{REGIONS_FIELD}' has value(s) that are not "
            f"Cloud Run regions: {', '.join(repr(r) for r in bad_regions)}. Use ids "
            f"such as us-central1, or leave it empty for every region.",
        )
    raw = (source_fields.get(REPORT_ALL_FIELD) or "").strip().lower()
    if raw not in _TRUE | _FALSE:
        raise DiscoveryConfigurationError(
            f"Cloud Run and GKE source's '{REPORT_ALL_FIELD}' must be true or false.",
        )
    return ContainersSettings(
        project_ids=projects,
        regions=regions,
        report_all_workloads=raw in _TRUE,
    )


def _is_region(value: str) -> bool:
    parts = value.split("-")
    return (
        len(parts) >= 2
        and all(p.isalnum() and p.islower() for p in parts if not p.isdigit())
        and parts[-1][-1:].isdigit()
    )


def _log_summary(
    workloads: Sequence[Workload],
    selected: Sequence[SelectedWorkload],
    records: Sequence[DiscoveredAgentRecord],
    logger: logging.Logger,
) -> None:
    by_kind: dict[str, int] = {}
    for w in workloads:
        by_kind[w.kind] = by_kind.get(w.kind, 0) + 1
    by_reason: dict[str, int] = {}
    for s in selected:
        for reason in s.reasons:
            by_reason[reason] = by_reason.get(reason, 0) + 1
    logger.info(
        "Cloud Run and GKE scan listed %s workload(s) (%s); %s reported (%s)",
        len(workloads),
        ", ".join(f"{k}: {n}" for k, n in sorted(by_kind.items())) or "none",
        len(records),
        ", ".join(f"{k}: {n}" for k, n in sorted(by_reason.items())) or "none",
    )
