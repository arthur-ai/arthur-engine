"""The Cloud Run and GKE connector, against a fake Google and a fake Kubernetes API.

What matters most here is identity: a workload is one record under the same name scan
after scan, whatever revision, execution or pod is running, and it carries the service
account it runs as, because that is what joins it to the AI calls it made.
"""

import base64
import logging
from datetime import datetime, timezone
from typing import Any, Optional

import pytest
import yaml
from arthur_common.models.agent_governance_schemas import (
    CloudAgentCreationSource,
    RunsOn,
    SourceAddress,
)

from discovery import source_connectors
from discovery.catalog import Matcher
from discovery.cloud.gcp_containers import client as containers_client
from discovery.cloud.gcp_containers.client import (
    CONTAINER_API,
    RESOURCE_MANAGER_API,
    RUN_V1_API,
    RUN_V2_API,
)
from discovery.cloud.gcp_containers.connector import (
    ALLOW_ADC_ENV_VAR,
    VENDOR,
    GcpContainersConnector,
    settings_from,
)
from discovery.cloud.gcp_containers.workloads import (
    CLOUD_RUN_JOB,
    GKE_WORKLOAD,
    REASON_AI_SERVICE_ACCOUNT,
    Workload,
    select_workloads,
)
from job_executors.discovery_output_contract import check_batch
from job_executors.discovery_scan import (
    AcceptsStopCheck,
    DiscoveryConfigurationError,
    DiscoveryErrorCode,
    failure_code,
)

LOG = logging.getLogger("discovery-test")
PROJECT = "demo-project"
NUMBER = "123456789012"
REGION = "us-central1"
CLUSTER = "demo-cluster"
ENDPOINT = "203.0.113.10"
KUBE = f"https://{ENDPOINT}"
APP_SA = f"demo-app@{PROJECT}.iam.gserviceaccount.com"
DEFAULT_SA = f"{NUMBER}-compute@developer.gserviceaccount.com"
NODE_SA = f"demo-nodes@{PROJECT}.iam.gserviceaccount.com"
UPDATED = "2026-09-01T12:00:00.123456789Z"
CATALOG = yaml.safe_dump(
    {
        "version": 2,
        "classifications": ["Coding agent"],
        "agents": [
            {
                "id": "goose",
                "name": "goose",
                "classification": "Coding agent",
                "platforms": ["darwin", "linux"],
                "images": ["ghcr.io/block/goose"],
            },
        ],
    },
)
GOOSE = "ghcr.io/block/goose:1.2@sha256:" + "a" * 64
PLAIN = "us-docker.pkg.dev/demo-project/apps/web:7"


# --- fakes ----------------------------------------------------------------------------


class FakeResponse:
    def __init__(self, status: int, body: Any = None) -> None:
        self.status_code = status
        self._body = body
        self.headers: dict[str, str] = {}

    def json(self) -> Any:
        if self._body is None:
            raise ValueError("no body")
        return self._body


def service(name: str, image: str = PLAIN, account: Optional[str] = APP_SA) -> Any:
    template: dict[str, Any] = {"containers": [{"image": image}]}
    if account:
        template["serviceAccount"] = account
    return {
        "name": f"projects/{PROJECT}/locations/{REGION}/services/{name}",
        "updateTime": UPDATED,
        "latestReadyRevision": f"projects/{PROJECT}/locations/{REGION}/"
        f"services/{name}/revisions/{name}-00042-xyz",
        "template": template,
    }


def job(name: str, image: str = PLAIN, account: Optional[str] = APP_SA) -> Any:
    task: dict[str, Any] = {"containers": [{"image": image}]}
    if account:
        task["serviceAccount"] = account
    return {
        "name": f"projects/{PROJECT}/locations/{REGION}/jobs/{name}",
        "createTime": UPDATED,
        "latestCreatedExecution": {
            "name": f"projects/{PROJECT}/locations/{REGION}/jobs/{name}/"
            f"executions/{name}-q7x2k",
        },
        "template": {"template": task},
    }


def k8s(
    kind: str,
    name: str,
    namespace: str = "agents",
    image: str = PLAIN,
    ksa: Optional[str] = None,
    owner: Optional[str] = None,
) -> Any:
    pod: dict[str, Any] = {
        "containers": [
            {
                "image": image,
                "env": [{"name": "API_TOKEN", "value": "do-not-read"}],
            },
        ],
    }
    if ksa:
        pod["serviceAccountName"] = ksa
    meta: dict[str, Any] = {
        "name": name,
        "namespace": namespace,
        "creationTimestamp": "2026-08-01T00:00:00Z",
    }
    if owner:
        meta["ownerReferences"] = [{"kind": owner, "name": "x"}]
    if kind == "pod":
        spec: dict[str, Any] = pod
    elif kind == "cronjob":
        spec = {"jobTemplate": {"spec": {"template": {"spec": pod}}}}
    else:
        spec = {"template": {"spec": pod}}
    return {"metadata": meta, "spec": spec, "status": {}}


def cluster(
    workload_pool: Optional[str] = None,
    node_sa: str = "default",
    mode: Optional[str] = None,
) -> Any:
    config: dict[str, Any] = {"serviceAccount": node_sa}
    if mode:
        config["workloadMetadataConfig"] = {"mode": mode}
    return {
        "name": CLUSTER,
        "location": REGION,
        "status": "RUNNING",
        "endpoint": ENDPOINT,
        "masterAuth": {
            "clusterCaCertificate": base64.b64encode(b"-----FAKE CA-----").decode(),
        },
        "workloadIdentityConfig": (
            {"workloadPool": workload_pool} if workload_pool else {}
        ),
        "nodePools": [{"name": "pool-1", "config": config}],
    }


class FakeGoogle:
    """Cloud Run, GKE, Resource Manager and one cluster's Kubernetes API.

    Each listing is a list of pages; a value that is a FakeResponse is answered as-is.
    """

    def __init__(
        self,
        services: Any = None,
        jobs: Any = None,
        regions: Any = None,
        clusters: Any = None,
        kube: Optional[dict[str, Any]] = None,
    ) -> None:
        self.services = [[]] if services is None else services
        self.jobs = {} if jobs is None else jobs
        self.regions = [[REGION]] if regions is None else regions
        self.clusters = [] if clusters is None else clusters
        self.kube = kube or {}
        self.calls: list[tuple[str, dict[str, Any], Optional[str]]] = []

    def get(
        self,
        url: str,
        params: dict[str, Any],
        timeout: float,
        allow_redirects: bool,
        verify: Optional[str] = None,
    ) -> FakeResponse:
        assert allow_redirects is False
        self.calls.append((url, dict(params), verify))
        if url == f"{RUN_V2_API}/projects/{PROJECT}/locations/-/services":
            return self._paged(self.services, params, "services")
        if url == f"{RUN_V1_API}/projects/{PROJECT}/locations":
            if isinstance(self.regions, FakeResponse):
                return self.regions
            return self._paged(
                [[{"locationId": r} for r in page] for page in self.regions],
                params,
                "locations",
            )
        if url.startswith(f"{RUN_V2_API}/projects/{PROJECT}/locations/") and (
            url.endswith("/jobs")
        ):
            region = url.split("/")[-2]
            return self._paged(self.jobs.get(region, [[]]), params, "jobs")
        if url == f"{CONTAINER_API}/projects/{PROJECT}/locations/-/clusters":
            if isinstance(self.clusters, FakeResponse):
                return self.clusters
            return FakeResponse(200, {"clusters": self.clusters})
        if url == f"{RESOURCE_MANAGER_API}/projects/{PROJECT}":
            return FakeResponse(200, {"projectNumber": NUMBER})
        if url.startswith(KUBE):
            assert verify is not None, "the Kubernetes API is called without its CA"
            pages = self.kube.get(url.removeprefix(KUBE), [[]])
            if isinstance(pages, FakeResponse):
                return pages
            index = int(params.get("continue") or 0)
            body: dict[str, Any] = {"items": pages[index], "metadata": {}}
            if index + 1 < len(pages):
                body["metadata"]["continue"] = str(index + 1)
            return FakeResponse(200, body)
        raise AssertionError(f"unexpected call {url}")

    @staticmethod
    def _paged(pages: Any, params: dict[str, Any], key: str) -> FakeResponse:
        if isinstance(pages, FakeResponse):
            return pages
        index = int(params.get("pageToken") or 0)
        body: dict[str, Any] = {key: pages[index]}
        if index + 1 < len(pages):
            body["nextPageToken"] = str(index + 1)
        return FakeResponse(200, body)

    def paths(self) -> list[str]:
        return [url for url, _, _ in self.calls]


class FakeConfig:
    def __init__(self, query: Optional[str] = CATALOG) -> None:
        self.query = query
        self.vendor = VENDOR
        self.name = "demo containers"


@pytest.fixture(autouse=True)
def no_backoff(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(containers_client, "backoff_seconds", lambda a, b: 0.0)


@pytest.fixture(autouse=True)
def adc(monkeypatch: pytest.MonkeyPatch) -> None:
    """Keyless sources, so no test needs a real service account key."""
    monkeypatch.setenv(ALLOW_ADC_ENV_VAR, "true")


def scan(
    fake: FakeGoogle,
    report_all: bool = True,
    ai_service_accounts: frozenset[str] = frozenset(),
    lookback_hours: int = 24,
    connector: Optional[GcpContainersConnector] = None,
) -> list[Any]:
    connector = connector or GcpContainersConnector(
        session_for=lambda creds: fake,  # type: ignore[arg-type,return-value]
        ai_service_accounts=ai_service_accounts,
    )
    fields = {
        "project_ids": PROJECT,
        "report_all_workloads": "true" if report_all else "false",
    }
    batches = connector.scan(
        FakeConfig(),  # type: ignore[arg-type]
        lookback_hours,
        {},
        fields,
        LOG,
    )
    return [record for batch in batches for record in batch]


def by_kind(records: list[Any], kind: str) -> list[Any]:
    return [r for r in records if r.creation_source.address.resource_kind == kind]


# --- records --------------------------------------------------------------------------


def test_a_cloud_run_service_is_addressed_by_project_region_and_its_own_name() -> None:
    records = scan(FakeGoogle(services=[[service("web")]]))

    assert len(records) == 1
    record = records[0]
    check_batch(records, "Source config 'demo containers' (gcp_containers)")
    assert record.external_id == f"projects/{PROJECT}/locations/{REGION}/services/web"
    assert record.runs_on is RunsOn.GCP
    assert record.last_seen == datetime(2026, 9, 1, 12, 0, 0, 123456, timezone.utc)
    assert record.name == f"web (runs as {APP_SA})"
    source = record.creation_source
    assert isinstance(source, CloudAgentCreationSource)
    assert source.vendor == "gcp_containers"
    assert source.address == SourceAddress(
        instance=PROJECT,
        scope=REGION,
        resource_kind="cloud_run_service",
        resource_id="web",
    )
    assert source.observations.service_names == []


def test_a_cloud_run_job_is_its_name_never_its_execution() -> None:
    records = scan(FakeGoogle(jobs={REGION: [[job("nightly")]]}))

    (record,) = records
    check_batch(records, "Source config 'demo containers' (gcp_containers)")
    assert record.external_id == f"projects/{PROJECT}/locations/{REGION}/jobs/nightly"
    assert record.creation_source.address.resource_kind == CLOUD_RUN_JOB
    assert record.creation_source.address.resource_id == "nightly"
    assert "q7x2k" not in record.external_id + record.name


def test_a_cloud_run_workload_without_an_account_runs_as_the_default_one() -> None:
    fake = FakeGoogle(services=[[service("web", account=None)]])

    (record,) = scan(fake)

    assert record.name == f"web (runs as {DEFAULT_SA})"
    assert f"{RESOURCE_MANAGER_API}/projects/{PROJECT}" in fake.paths()


def test_gke_workloads_are_controllers_by_stable_name_and_owned_objects_are_not() -> (
    None
):
    """A Deployment's pods carry a ReplicaSet hash and a CronJob's Jobs a timestamp;
    only the controller, and a pod or job nothing owns, is a workload."""
    fake = FakeGoogle(
        clusters=[cluster()],
        kube={
            "/apis/apps/v1/deployments": [[k8s("deployment", "planner")]],
            "/apis/batch/v1/cronjobs": [[k8s("cronjob", "digest")]],
            "/apis/batch/v1/jobs": [
                [
                    k8s("job", "digest-29340000", owner="CronJob"),
                    k8s("job", "one-off"),
                ],
            ],
            "/api/v1/pods": [
                [
                    k8s("pod", "planner-7d9f8c6b5-x2x9q", owner="ReplicaSet"),
                    k8s("pod", "scratch"),
                ],
            ],
        },
    )

    records = scan(fake)

    check_batch(records, "Source config 'demo containers' (gcp_containers)")
    ids = sorted(r.creation_source.address.resource_id for r in records)
    assert ids == [
        f"{CLUSTER}/agents/cronjob/digest",
        f"{CLUSTER}/agents/deployment/planner",
        f"{CLUSTER}/agents/job/one-off",
        f"{CLUSTER}/agents/pod/scratch",
    ]
    planner = next(r for r in records if r.name.startswith(f"{CLUSTER}/agents/planner"))
    assert planner.external_id == (
        f"projects/{PROJECT}/locations/{REGION}/clusters/{CLUSTER}"
        f"/k8s/namespaces/agents/apps/deployments/planner"
    )
    assert planner.creation_source.address.resource_kind == GKE_WORKLOAD
    assert planner.creation_source.address.scope == REGION
    assert planner.creation_source.observations.host_group == CLUSTER
    # No Workload Identity: the pods call Google as the node pool's account.
    assert planner.name.endswith(f"(runs as {DEFAULT_SA})")


def test_gke_system_namespaces_are_not_workloads() -> None:
    fake = FakeGoogle(
        clusters=[cluster()],
        kube={
            "/apis/apps/v1/daemonsets": [
                [
                    k8s("daemonset", "fluentbit", namespace="kube-system"),
                    k8s("daemonset", "collector", namespace="gmp-system"),
                ],
            ],
        },
    )

    assert scan(fake) == []


def test_workload_identity_reports_the_annotated_account_not_the_node() -> None:
    fake = FakeGoogle(
        clusters=[cluster(workload_pool=f"{PROJECT}.svc.id.goog", node_sa=NODE_SA)],
        kube={
            "/api/v1/serviceaccounts": [
                [
                    {
                        "metadata": {
                            "name": "planner",
                            "namespace": "agents",
                            "annotations": {"iam.gke.io/gcp-service-account": APP_SA},
                        },
                    },
                ],
            ],
            "/apis/apps/v1/deployments": [
                [
                    k8s("deployment", "planner", ksa="planner"),
                    k8s("deployment", "unbound", ksa="unbound"),
                ],
            ],
        },
    )

    records = {r.creation_source.address.resource_id: r for r in scan(fake)}

    assert records[f"{CLUSTER}/agents/deployment/planner"].name.endswith(
        f"(runs as {APP_SA})",
    )
    # A KSA with no annotation calls Google as a federated principal, not the node.
    assert records[f"{CLUSTER}/agents/deployment/unbound"].name == (
        f"{CLUSTER}/agents/unbound"
    )


def test_env_values_never_reach_a_record(caplog: pytest.LogCaptureFixture) -> None:
    fake = FakeGoogle(
        clusters=[cluster()],
        kube={"/apis/apps/v1/deployments": [[k8s("deployment", "planner")]]},
    )
    with caplog.at_level(logging.DEBUG):
        records = scan(fake)

    assert "do-not-read" not in repr(records) + caplog.text


# --- selection ------------------------------------------------------------------------


def test_only_a_catalog_image_is_reported_by_default_and_a_digest_still_matches() -> (
    None
):
    fake = FakeGoogle(services=[[service("agent", image=GOOSE), service("web")]])

    records = scan(fake, report_all=False)

    (record,) = records
    assert record.creation_source.address.resource_id == "agent"
    assert record.name == f"agent [goose] (runs as {APP_SA})"
    assert record.creation_source.observations.classification == "Coding agent"


def test_a_service_account_that_calls_ai_reports_a_workload_the_catalog_does_not_know() -> (
    None
):
    fake = FakeGoogle(
        services=[[service("web", account=APP_SA), service("other", account=NODE_SA)]],
    )

    records = scan(fake, report_all=False, ai_service_accounts=frozenset({APP_SA}))

    assert [r.creation_source.address.resource_id for r in records] == ["web"]


def test_select_workloads_is_a_pure_join_on_the_service_account() -> None:
    workload = Workload(
        project=PROJECT,
        location=REGION,
        kind=CLOUD_RUN_JOB,
        resource_id="nightly",
        external_id=f"projects/{PROJECT}/locations/{REGION}/jobs/nightly",
        name="nightly",
        images=(PLAIN,),
        service_accounts=(APP_SA,),
        last_seen=None,
    )
    matcher = Matcher.from_source(catalog_yaml=CATALOG)

    assert select_workloads([workload], matcher) == []
    (selected,) = select_workloads(
        [workload],
        matcher,
        ai_service_accounts=frozenset({APP_SA.upper()}),
    )
    assert selected.reasons == (REASON_AI_SERVICE_ACCOUNT,)
    assert selected.matched_service_accounts == (APP_SA,)
    assert selected.findings == ()


def test_the_lookback_is_not_applied() -> None:
    fake = FakeGoogle(services=[[service("web")]], jobs={REGION: [[job("nightly")]]})

    assert len(scan(fake, lookback_hours=1)) == len(scan(fake, lookback_hours=0)) == 2
    for _, params, _ in fake.calls:
        assert set(params) <= {"pageSize", "pageToken", "limit", "continue"}


# --- paging ---------------------------------------------------------------------------


def test_every_page_is_followed_on_cloud_run_and_on_kubernetes() -> None:
    fake = FakeGoogle(
        services=[[service("a")], [service("b")]],
        regions=[["us-central1"], ["europe-west1"]],
        jobs={"europe-west1": [[job("c")], [job("d")]]},
        clusters=[cluster()],
        kube={
            "/apis/apps/v1/deployments": [
                [k8s("deployment", "e")],
                [k8s("deployment", "f")],
            ],
        },
    )

    ids = sorted(r.creation_source.address.resource_id for r in scan(fake))

    assert ids == [
        "a",
        "b",
        "c",
        "d",
        f"{CLUSTER}/agents/deployment/e",
        f"{CLUSTER}/agents/deployment/f",
    ]


def test_a_repeated_page_token_ends_the_listing(
    caplog: pytest.LogCaptureFixture,
) -> None:
    class Looping(FakeGoogle):
        @staticmethod
        def _paged(pages: Any, params: dict[str, Any], key: str) -> FakeResponse:
            return FakeResponse(200, {key: pages[0], "nextPageToken": "same"})

    fake = Looping(services=[[service("a")]])
    with caplog.at_level(logging.WARNING):
        records = scan(fake)

    assert [r.creation_source.address.resource_id for r in records] == ["a", "a"]
    assert "repeated a page token" in caplog.text


# --- errors ---------------------------------------------------------------------------


def test_a_refused_api_is_a_warning_and_the_rest_is_still_reported(
    caplog: pytest.LogCaptureFixture,
) -> None:
    denied = FakeResponse(
        403,
        {"error": {"code": 403, "message": "Kubernetes Engine API has not been used"}},
    )
    fake = FakeGoogle(services=[[service("web")]], clusters=denied)

    with caplog.at_level(logging.WARNING):
        records = scan(fake)

    assert [r.creation_source.address.resource_id for r in records] == ["web"]
    assert f"GKE clusters in project {PROJECT} not listed" in caplog.text
    assert "HTTP 403" in caplog.text


def test_a_cluster_whose_kubernetes_api_refuses_is_a_warning(
    caplog: pytest.LogCaptureFixture,
) -> None:
    fake = FakeGoogle(
        services=[[service("web")]],
        clusters=[cluster()],
        kube={
            "/apis/apps/v1/deployments": FakeResponse(
                403,
                {"kind": "Status", "message": "deployments.apps is forbidden"},
            ),
        },
    )

    with caplog.at_level(logging.WARNING):
        records = scan(fake)

    assert [r.creation_source.address.resource_id for r in records] == ["web"]
    assert "deployments.apps is forbidden" in caplog.text


def test_when_nothing_can_be_listed_the_scan_fails_as_permission_denied() -> None:
    denied = FakeResponse(403, {"error": {"code": 403, "message": "denied"}})
    fake = FakeGoogle(services=denied, regions=denied, clusters=denied)

    with pytest.raises(containers_client.GcpContainersError) as exc:
        scan(fake)

    assert failure_code(exc.value) is DiscoveryErrorCode.PERMISSION_DENIED


def test_a_refused_credential_ends_the_scan_at_once() -> None:
    refused = FakeResponse(401, {"error": {"code": 401, "message": "invalid"}})
    fake = FakeGoogle(services=refused, clusters=[cluster()])

    with pytest.raises(containers_client.GcpContainersError) as exc:
        scan(fake)

    assert failure_code(exc.value) is DiscoveryErrorCode.AUTHENTICATION_FAILED
    assert not any(url.startswith(KUBE) for url in fake.paths())


def test_only_list_calls_are_made() -> None:
    fake = FakeGoogle(
        services=[[service("web", account=None)]],
        jobs={REGION: [[job("nightly")]]},
        clusters=[cluster(workload_pool=f"{PROJECT}.svc.id.goog")],
        kube={"/apis/apps/v1/deployments": [[k8s("deployment", "planner")]]},
    )
    scan(fake)

    for url in fake.paths():
        for forbidden in ("executions", "revisions", "secrets", "configmaps", "/log"):
            assert forbidden not in url, url


# --- settings, registration, stopping -------------------------------------------------


@pytest.mark.parametrize(
    "fields",
    [
        {},
        {"project_ids": "Demo Project"},
        {"project_ids": PROJECT, "regions": "us central"},
        {"project_ids": PROJECT, "report_all_workloads": "sometimes"},
    ],
)
def test_settings_that_cannot_be_scanned_fail_as_not_configured(
    fields: dict[str, str],
) -> None:
    with pytest.raises(DiscoveryConfigurationError) as exc:
        settings_from(fields)
    assert failure_code(exc.value) is DiscoveryErrorCode.NOT_CONFIGURED


def test_settings_default_to_every_region_and_catalog_matches_only() -> None:
    settings = settings_from({"project_ids": f"{PROJECT}, demo-project-2"})

    assert settings.project_ids == (PROJECT, "demo-project-2")
    assert settings.regions == ()
    assert settings.report_all_workloads is False
    assert settings_from(
        {"project_ids": PROJECT, "regions": "us-east4,europe-west1"},
    ).regions == ("us-east4", "europe-west1")


def test_configured_regions_are_the_only_ones_asked_for_jobs() -> None:
    fake = FakeGoogle(jobs={"us-east4": [[job("nightly")]]})
    connector = GcpContainersConnector(session_for=lambda c: fake)  # type: ignore[arg-type,return-value]

    list(
        connector.scan(
            FakeConfig(),  # type: ignore[arg-type]
            24,
            {},
            {"project_ids": PROJECT, "regions": "us-east4"},
            LOG,
        ),
    )

    assert f"{RUN_V1_API}/projects/{PROJECT}/locations" not in fake.paths()
    assert [u for u in fake.paths() if u.endswith("/jobs")] == [
        f"{RUN_V2_API}/projects/{PROJECT}/locations/us-east4/jobs",
    ]


def test_a_keyless_source_needs_the_engine_to_opt_in(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv(ALLOW_ADC_ENV_VAR)

    with pytest.raises(DiscoveryConfigurationError, match=ALLOW_ADC_ENV_VAR):
        scan(FakeGoogle())


def test_registered_with_its_secret_declared_and_a_stop_check() -> None:
    connector = source_connectors()[VENDOR]()

    assert isinstance(connector, GcpContainersConnector)
    assert GcpContainersConnector.SENSITIVE_FIELDS == frozenset(
        {"service_account_key"},
    )
    assert isinstance(connector, AcceptsStopCheck)


def test_a_stop_before_the_first_call_sends_nothing() -> None:
    fake = FakeGoogle(services=[[service("web")]])
    connector = GcpContainersConnector(session_for=lambda c: fake)  # type: ignore[arg-type,return-value]
    connector.stop_when(lambda: True)

    assert scan(fake, connector=connector) == []
    assert fake.calls == []
