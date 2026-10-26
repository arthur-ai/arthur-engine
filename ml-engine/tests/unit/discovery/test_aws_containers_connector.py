"""The ECS and EKS connector, against a fake AWS and a fake Kubernetes API.

What matters most here is identity: a workload is one record under the same name scan
after scan, whatever task or pod is running, and it carries the IAM role it runs as,
because that is what joins it to the Bedrock calls CloudTrail logged. Every AWS call the
fake answers is first checked against botocore's own model of that operation, so a
misspelt parameter fails here rather than against AWS.
"""

import base64
import json
import logging
from datetime import datetime, timezone
from types import SimpleNamespace
from typing import Any, Callable, Optional

import boto3
import pytest
from arthur_common.models.agent_governance_schemas import (
    CloudAgentCreationSource,
    RunsOn,
    SourceAddress,
)
from botocore.exceptions import ClientError
from botocore.session import Session as BotocoreSession
from botocore.validate import ParamValidator

from discovery import source_connectors
from discovery.aws_organization import BOOTSTRAP_REGION, DEFAULT_MEMBER_ROLE_NAME
from discovery.cloud.aws_containers.client import presigned_token
from discovery.cloud.aws_containers.connector import (
    ALLOW_DEFAULT_CREDENTIALS_ENV_VAR,
    VENDOR,
    AwsContainersConnector,
    settings_from,
    source_session,
)
from discovery.cloud.aws_containers.workloads import (
    ECS_SERVICE,
    ECS_TASK_GROUP,
    EKS_WORKLOAD,
    role_key,
)
from job_executors.discovery_output_contract import check_batch
from job_executors.discovery_scan import (
    DENIED_PERMISSION,
    DENIED_UNREACHABLE,
    AcceptsStopCheck,
    DeniedScope,
    DiscoveryConfigurationError,
    DiscoveryErrorCode,
    ReportsDeniedScopes,
    failure_code,
)
from tests.fakes.catalog import agent, document

LOG = logging.getLogger("discovery-test")
ACCOUNT = "123456789012"
REGION = "us-east-1"
FIELDS = {"regions": REGION}
NOW = datetime(2026, 10, 22, 12, 0, tzinfo=timezone.utc)
CREATED = datetime(2026, 9, 1, 8, 0, tzinfo=timezone.utc)
DEPLOYED = datetime(2026, 10, 1, 9, 0, tzinfo=timezone.utc)
STARTED = datetime(2026, 10, 22, 11, 0, tzinfo=timezone.utc)
CLUSTER = "prod"
CLUSTER_ARN = f"arn:aws:ecs:{REGION}:{ACCOUNT}:cluster/{CLUSTER}"
EKS = "agents-eks"
EKS_ENDPOINT = "https://ABCDEF.gr7.us-east-1.eks.amazonaws.com"
MODEL = "amazon.nova-micro-v1:0"
DIGEST = "sha256:" + "d" * 64
APP = "123456789012.dkr.ecr.us-east-1.amazonaws.com/support-bot:3"
SIDECAR = "public.ecr.aws/docker/library/busybox:1.37.0"
GOOSE = "ghcr.io/block/goose:1.2"
CATALOG = document(
    agent(
        "goose",
        "goose",
        "Coding agent",
        platforms=["darwin", "linux"],
        images=["ghcr.io/block/goose"],
    ),
)
SERVICES = ("ecs", "eks", "ec2", "iam", "sts", "cloudtrail", "organizations")
MODELS = {svc: BotocoreSession().get_service_model(svc) for svc in SERVICES}
SECRET_ENV = {"name": "API_TOKEN", "value": "do-not-read"}


def role(name: str, path: str = "") -> str:
    return f"arn:aws:iam::{ACCOUNT}:role/{path}{name}"


TASK_ROLE = role("support-bot-task")
EXEC_ROLE = role("ecsTaskExecutionRole")
INSTANCE_ROLE = role("ecs-instance")
NODE_ROLE = role("eks-nodes")
IRSA_ROLE = role("irsa-agent")
POD_ID_ROLE = role("podid-agent")


# --- AWS objects, as the APIs return them -----------------------------------------------


def task_definition(
    family: str,
    images: tuple[str, ...] = (APP,),
    task_role: Optional[str] = TASK_ROLE,
    exec_role: Optional[str] = EXEC_ROLE,
    revision: int = 1,
) -> dict[str, Any]:
    body: dict[str, Any] = {
        "taskDefinitionArn": f"arn:aws:ecs:{REGION}:{ACCOUNT}:task-definition/"
        f"{family}:{revision}",
        "family": family,
        "revision": revision,
        "containerDefinitions": [
            {"name": f"c{i}", "image": image, "environment": [SECRET_ENV]}
            for i, image in enumerate(images)
        ],
    }
    if task_role:
        body["taskRoleArn"] = task_role
    if exec_role:
        body["executionRoleArn"] = exec_role
    return body


def ecs_service(name: str, definition: dict[str, Any], launch: str = "FARGATE") -> Any:
    arn = definition["taskDefinitionArn"]
    return {
        "serviceName": name,
        "serviceArn": f"arn:aws:ecs:{REGION}:{ACCOUNT}:service/{CLUSTER}/{name}",
        "clusterArn": CLUSTER_ARN,
        "status": "ACTIVE",
        "launchType": launch,
        "taskDefinition": arn,
        "createdAt": CREATED,
        "deployments": [
            {
                "status": "PRIMARY",
                "taskDefinition": arn,
                "createdAt": DEPLOYED,
                "updatedAt": DEPLOYED,
            },
        ],
    }


def ecs_task(
    ident: str,
    definition: dict[str, Any],
    group: str,
    digests: Optional[dict[str, str]] = None,
    container_instance: Optional[str] = None,
    role_override: Optional[str] = None,
) -> Any:
    body: dict[str, Any] = {
        "taskArn": f"arn:aws:ecs:{REGION}:{ACCOUNT}:task/{CLUSTER}/{ident}",
        "clusterArn": CLUSTER_ARN,
        "taskDefinitionArn": definition["taskDefinitionArn"],
        "group": group,
        "lastStatus": "RUNNING",
        "createdAt": STARTED,
        "startedAt": STARTED,
        "containers": [
            {
                "name": c["name"],
                "image": c["image"],
                **(
                    {"imageDigest": digests[c["image"]]}
                    if digests and c["image"] in digests
                    else {}
                ),
            }
            for c in definition["containerDefinitions"]
        ],
        "overrides": {"containerOverrides": []},
    }
    if container_instance:
        body["containerInstanceArn"] = container_instance
    if role_override:
        body["overrides"]["taskRoleArn"] = role_override
    return body


def eks_cluster(name: str = EKS, status: str = "ACTIVE") -> Any:
    return {
        "name": name,
        "arn": f"arn:aws:eks:{REGION}:{ACCOUNT}:cluster/{name}",
        "status": status,
        "endpoint": EKS_ENDPOINT,
        "certificateAuthority": {
            "data": base64.b64encode(b"-----FAKE CA-----").decode(),
        },
    }


def k8s(
    kind: str,
    name: str,
    namespace: str = "agents",
    image: str = APP,
    ksa: Optional[str] = None,
    owner: Optional[str] = None,
    image_id: Optional[str] = None,
    labels: Optional[dict[str, str]] = None,
) -> Any:
    pod: dict[str, Any] = {"containers": [{"image": image, "env": [SECRET_ENV]}]}
    if ksa:
        pod["serviceAccountName"] = ksa
    meta: dict[str, Any] = {
        "name": name,
        "namespace": namespace,
        "creationTimestamp": "2026-08-01T00:00:00Z",
    }
    if owner:
        meta["ownerReferences"] = [{"kind": owner, "name": "x"}]
    template: dict[str, Any] = {"spec": pod}
    if labels:
        template["metadata"] = {"labels": labels}
    status: dict[str, Any] = {}
    if kind == "pod":
        spec: dict[str, Any] = pod
        if labels:
            meta["labels"] = labels
        if image_id:
            status["containerStatuses"] = [{"image": image, "imageID": image_id}]
    elif kind == "cronjob":
        spec = {"jobTemplate": {"spec": {"template": template}}}
    else:
        spec = {"template": template}
    return {"metadata": meta, "spec": spec, "status": status}


def service_account(
    name: str,
    namespace: str = "agents",
    irsa: Optional[str] = None,
) -> Any:
    meta: dict[str, Any] = {"name": name, "namespace": namespace}
    if irsa:
        meta["annotations"] = {"eks.amazonaws.com/role-arn": irsa}
    return {"metadata": meta}


def model_call(
    caller: str,
    model: Optional[str] = MODEL,
    error_code: Optional[str] = None,
    when: str = "2026-10-22T10:00:00Z",
) -> Any:
    detail: dict[str, Any] = {
        "eventVersion": "1.09",
        "userIdentity": {
            "type": "AssumedRole",
            "arn": f"arn:aws:sts::{ACCOUNT}:assumed-role/x/session",
            "sessionContext": {"sessionIssuer": {"type": "Role", "arn": caller}},
        },
        "eventTime": when,
        "eventSource": "bedrock.amazonaws.com",
        "eventName": "Converse",
        "requestParameters": {"modelId": model} if model else None,
        "eventType": "AwsApiCall",
    }
    if error_code:
        detail["errorCode"] = error_code
    return {
        "EventId": "e",
        "EventName": "Converse",
        "EventTime": datetime.fromisoformat(when.replace("Z", "+00:00")),
        "CloudTrailEvent": json.dumps(detail),
    }


def client_error(code: str, operation: str) -> ClientError:
    return ClientError({"Error": {"Code": code, "Message": "no"}}, operation)


# --- fakes ------------------------------------------------------------------------------


class FakeAws:
    """ECS, EKS, EC2, IAM, STS, CloudTrail and Organizations, as one account's state.

    `errors[(service, Operation)]` is raised by every such call; set it to refuse an API.
    `accounts_listed` is what ListAccounts answers, each account's `State` as AWS
    gives it now, or its retired `Status` when `account_field` says so;
    `regions_enabled` is what DescribeRegions answers, and `assume_error` what every
    call raises when the account's member role cannot be assumed: the role is fetched
    lazily, by the first call.
    """

    def __init__(self, account: str = ACCOUNT) -> None:
        self.account = account
        self.accounts_listed: list[tuple[str, str]] = []
        self.account_field = "State"
        self.regions_enabled: list[str] = [REGION]
        self.assume_error: Optional[Exception] = None
        self.services: dict[str, list[Any]] = {}
        self.tasks: dict[str, list[Any]] = {}
        self.definitions: dict[str, Any] = {}
        self.container_instances: dict[str, tuple[str, str, str]] = {}
        self.eks: dict[str, Any] = {}
        self.node_groups: dict[str, dict[str, str]] = {}
        self.pod_identity: dict[str, list[tuple[str, str, str]]] = {}
        self.fargate: dict[str, dict[str, list[dict[str, Any]]]] = {}
        self.events: dict[str, list[Any]] = {}
        self.errors: dict[tuple[str, str], Exception] = {}
        self.calls: list[tuple[str, str, str, dict[str, Any]]] = []

    def add_definition(self, definition: dict[str, Any]) -> dict[str, Any]:
        self.definitions[definition["taskDefinitionArn"]] = definition
        return definition

    def client_for(self, service: str, region: str) -> "FakeClient":
        return FakeClient(self, service, region)

    def operations(self) -> set[str]:
        return {op for _, _, op, _ in self.calls}


class FakeClient:
    def __init__(self, aws: FakeAws, service: str, region: str) -> None:
        self._aws = aws
        self._service = service
        self._region = region
        model = MODELS[service]
        self._operations = {_snake(name): name for name in model.operation_names}

    def __getattr__(self, snake: str) -> Callable[..., Any]:
        if snake.startswith("_"):
            raise AttributeError(snake)
        operation = self._operations[snake]

        def call(**params: Any) -> Any:
            shape = MODELS[self._service].operation_model(operation).input_shape
            if shape is not None:
                report = ParamValidator().validate(params, shape)
                assert not report.has_errors(), report.generate_report()
            self._aws.calls.append((self._service, self._region, operation, params))
            if self._aws.assume_error is not None:
                raise self._aws.assume_error
            error = self._aws.errors.get((self._service, operation))
            if error is not None:
                raise error
            handler = getattr(self, f"_{self._service}_{operation}", None) or getattr(
                self,
                f"_{operation}",
            )
            return handler(**params)

        return call

    # sts / cloudtrail

    def _GetCallerIdentity(self) -> Any:
        account = self._aws.account
        return {"Account": account, "Arn": f"arn:aws:sts::{account}:assumed-role/r/s"}

    def _LookupEvents(self, **params: Any) -> Any:
        return {"Events": self._aws.events.get(self._region, [])}

    # organizations / ec2 regions

    def _ListAccounts(self, **params: Any) -> Any:
        # One account per page, so paging is exercised.
        at = int(params.get("NextToken") or 0)
        listed = self._aws.accounts_listed
        body: dict[str, Any] = {
            "Accounts": [
                {"Id": i, self._aws.account_field: s} for i, s in listed[at : at + 1]
            ],
        }
        if at + 1 < len(listed):
            body["NextToken"] = str(at + 1)
        return body

    def _DescribeRegions(self, **params: Any) -> Any:
        assert params == {"AllRegions": False}, "only the regions the account enabled"
        return {"Regions": [{"RegionName": r} for r in self._aws.regions_enabled]}

    # ecs

    def _ListClusters(self, **params: Any) -> Any:
        return {
            "clusterArns": [CLUSTER_ARN] if self._region in self._aws.services else [],
        }

    def _ListServices(self, cluster: str, **params: Any) -> Any:
        return {
            "serviceArns": [
                s["serviceArn"] for s in self._aws.services.get(self._region, [])
            ],
        }

    def _DescribeServices(self, cluster: str, services: list[str]) -> Any:
        return {
            "services": [
                s
                for s in self._aws.services.get(self._region, [])
                if s["serviceArn"] in services
            ],
        }

    def _ListTasks(self, cluster: str, desiredStatus: str, **params: Any) -> Any:
        if desiredStatus != "RUNNING":
            return {"taskArns": []}
        return {
            "taskArns": [t["taskArn"] for t in self._aws.tasks.get(self._region, [])],
        }

    def _DescribeTasks(self, cluster: str, tasks: list[str]) -> Any:
        return {
            "tasks": [
                t
                for t in self._aws.tasks.get(self._region, [])
                if t["taskArn"] in tasks
            ],
        }

    def _DescribeTaskDefinition(self, taskDefinition: str) -> Any:
        return {"taskDefinition": self._aws.definitions[taskDefinition]}

    def _DescribeContainerInstances(
        self,
        cluster: str,
        containerInstances: list[str],
    ) -> Any:
        return {
            "containerInstances": [
                {
                    "containerInstanceArn": a,
                    "ec2InstanceId": self._aws.container_instances[a][0],
                }
                for a in containerInstances
            ],
        }

    def _DescribeInstances(self, InstanceIds: list[str]) -> Any:
        by_id = {v[0]: v for v in self._aws.container_instances.values()}
        return {
            "Reservations": [
                {
                    "Instances": [
                        {
                            "InstanceId": i,
                            "IamInstanceProfile": {
                                "Arn": f"arn:aws:iam::{ACCOUNT}:instance-profile/"
                                f"{by_id[i][1]}",
                            },
                        }
                        for i in InstanceIds
                    ],
                },
            ],
        }

    def _GetInstanceProfile(self, InstanceProfileName: str) -> Any:
        roles = [
            v[2]
            for v in self._aws.container_instances.values()
            if v[1] == InstanceProfileName
        ]
        return {"InstanceProfile": {"Roles": [{"Arn": roles[0]}]}}

    # eks

    def _eks_ListClusters(self, **params: Any) -> Any:
        return {"clusters": list(self._aws.eks)}

    def _DescribeCluster(self, name: str) -> Any:
        return {"cluster": self._aws.eks[name]}

    def _ListNodegroups(self, clusterName: str, **params: Any) -> Any:
        return {"nodegroups": list(self._aws.node_groups.get(clusterName, {}))}

    def _DescribeNodegroup(self, clusterName: str, nodegroupName: str) -> Any:
        return {
            "nodegroup": {
                "nodeRole": self._aws.node_groups[clusterName][nodegroupName],
            },
        }

    def _ListPodIdentityAssociations(self, clusterName: str, **params: Any) -> Any:
        return {
            "associations": [
                {"associationId": f"a-{i}", "namespace": ns, "serviceAccount": sa}
                for i, (ns, sa, _) in enumerate(
                    self._aws.pod_identity.get(clusterName, []),
                )
            ],
        }

    def _ListFargateProfiles(self, clusterName: str, **params: Any) -> Any:
        return {"fargateProfileNames": list(self._aws.fargate.get(clusterName, {}))}

    def _DescribeFargateProfile(self, clusterName: str, fargateProfileName: str) -> Any:
        selectors = self._aws.fargate[clusterName][fargateProfileName]
        return {"fargateProfile": {"selectors": selectors}}

    def _DescribePodIdentityAssociation(
        self,
        clusterName: str,
        associationId: str,
    ) -> Any:
        ns, sa, arn = self._aws.pod_identity[clusterName][int(associationId[2:])]
        return {"association": {"namespace": ns, "serviceAccount": sa, "roleArn": arn}}


def _snake(name: str) -> str:
    from botocore import xform_name

    return str(xform_name(name))


class FakeResponse:
    def __init__(self, status: int, body: Any = None) -> None:
        self.status_code = status
        self._body = body
        self.headers: dict[str, str] = {}

    def json(self) -> Any:
        if self._body is None:
            raise ValueError("no body")
        return self._body


class FakeKube:
    """One EKS cluster's Kubernetes API: path -> items, or a FakeResponse to answer."""

    def __init__(self, paths: Optional[dict[str, Any]] = None) -> None:
        self.paths = paths or {}
        self.calls: list[tuple[str, dict[str, str], Any]] = []

    def get(
        self,
        url: str,
        params: Any,
        headers: dict[str, str],
        verify: Any,
        **_: Any,
    ) -> Any:
        path = url[len(EKS_ENDPOINT) :]
        self.calls.append((path, headers, verify))
        answer = self.paths.get(path, [])
        if isinstance(answer, FakeResponse):
            return answer
        if isinstance(answer, Exception):
            raise answer
        return FakeResponse(200, {"items": answer, "metadata": {}})


class FakeConfig:
    def __init__(self, query: str = "") -> None:
        self.query = query
        self.vendor = VENDOR
        self.name = "acme containers"


def connector_for(
    aws: FakeAws,
    kube: Optional[FakeKube] = None,
) -> AwsContainersConnector:
    return AwsContainersConnector(
        session_for=lambda creds, fields: boto3.Session(),
        clients_for=lambda session: aws.client_for,
        tokens_for=lambda session: (lambda region, cluster: f"token-for-{cluster}"),
        http=kube or FakeKube(),  # type: ignore[arg-type]
        clock=lambda: NOW,
        sleep=lambda seconds: None,
    )


def scan(
    aws: FakeAws,
    fields: Optional[dict[str, str]] = None,
    kube: Optional[FakeKube] = None,
    connector: Optional[AwsContainersConnector] = None,
    catalog: str = "",
) -> list[Any]:
    connector = connector or connector_for(aws, kube)
    batches = connector.scan(
        FakeConfig(catalog),  # type: ignore[arg-type]
        24,
        {},
        fields or FIELDS,
        LOG,
    )
    return [record for batch in batches for record in batch]


def report_all(**more: str) -> dict[str, str]:
    return {**FIELDS, "report_all_workloads": "true", **more}


def by_id(records: list[Any]) -> dict[str, Any]:
    return {r.creation_source.address.resource_id: r for r in records}


def ecs_account(aws: Optional[FakeAws] = None) -> FakeAws:
    """One Fargate service with ten tasks on one digest and a sidecar."""
    aws = aws or FakeAws()
    d = aws.add_definition(task_definition("support-bot", images=(SIDECAR, APP)))
    aws.services[REGION] = [ecs_service("support-bot", d)]
    aws.tasks[REGION] = [
        ecs_task(f"t{i}", d, "service:support-bot", {APP: DIGEST}) for i in range(10)
    ]
    return aws


# --- registration ---------------------------------------------------------------------


def test_registered_with_its_protocols_and_secret_fields() -> None:
    connector = source_connectors()[VENDOR]()
    assert isinstance(connector, AwsContainersConnector)
    assert isinstance(connector, AcceptsStopCheck)
    assert isinstance(connector, ReportsDeniedScopes)
    assert AwsContainersConnector.SENSITIVE_FIELDS == {
        "access_key_id",
        "secret_access_key",
    }


# --- ECS --------------------------------------------------------------------------------


def test_a_service_is_one_record_whatever_its_tasks_and_names_its_task_role() -> None:
    [record] = scan(ecs_account(), report_all())

    assert record.external_id == (
        f"arn:aws:ecs:{REGION}:{ACCOUNT}:service/{CLUSTER}/support-bot"
    )
    assert record.creation_source == CloudAgentCreationSource(
        vendor=VENDOR,
        address=SourceAddress(
            instance=ACCOUNT,
            scope=REGION,
            resource_kind=ECS_SERVICE,
            resource_id=f"{CLUSTER}/support-bot",
        ),
        observations=record.creation_source.observations,
    )
    assert record.runs_on == RunsOn.AWS
    assert record.last_seen == DEPLOYED
    # The task role, never the execution role the ECS agent pulls with.
    assert record.name == f"{CLUSTER}/support-bot (runs as support-bot-task)"
    assert "ecsTaskExecutionRole" not in record.name
    observations = record.creation_source.observations
    assert observations.host_group == CLUSTER
    # Every container, the sidecar too; pinned to the digest its tasks report.
    assert observations.install_path == f"{SIDECAR}, {APP}@{DIGEST}"
    check_batch([record], "Source config 'acme containers' (aws_containers)")


def test_a_task_no_service_owns_is_its_group_and_reported_only_when_all_are() -> None:
    aws = FakeAws()
    d = aws.add_definition(
        task_definition("nightly-eval", task_role=None, exec_role=None),
    )
    aws.services[REGION] = []
    aws.tasks[REGION] = [
        ecs_task("a", d, "family:nightly-eval"),
        ecs_task("b", d, "family:nightly-eval", role_override=TASK_ROLE),
    ]

    assert scan(aws) == []
    [record] = scan(aws, report_all())
    assert record.creation_source.address.resource_kind == ECS_TASK_GROUP
    assert (
        record.creation_source.address.resource_id == f"{CLUSTER}/family:nightly-eval"
    )
    assert record.external_id == (
        f"{ACCOUNT}/{REGION}/ecs_task_group/{CLUSTER}/family:nightly-eval"
    )
    # RunTask's role override is the task's role.
    assert record.name == f"{CLUSTER}/family:nightly-eval (runs as support-bot-task)"
    assert record.last_seen == STARTED


def test_an_ec2_task_without_a_task_role_runs_as_its_instance_role() -> None:
    aws = FakeAws()
    d = aws.add_definition(task_definition("legacy", task_role=None))
    instance = f"arn:aws:ecs:{REGION}:{ACCOUNT}:container-instance/{CLUSTER}/ci-1"
    aws.container_instances[instance] = (
        "i-0abc",
        "ecs-instance-profile",
        INSTANCE_ROLE,
    )
    aws.services[REGION] = [ecs_service("legacy", d, launch="EC2")]
    aws.tasks[REGION] = [
        ecs_task("t", d, "service:legacy", container_instance=instance),
    ]

    [record] = scan(aws, report_all())
    assert record.name == f"{CLUSTER}/legacy (runs as ecs-instance, node role)"


def test_a_fargate_task_without_a_task_role_runs_as_nothing() -> None:
    aws = FakeAws()
    d = aws.add_definition(task_definition("static", task_role=None))
    aws.services[REGION] = [ecs_service("static", d)]
    aws.tasks[REGION] = [ecs_task("t", d, "service:static")]

    [record] = scan(aws, report_all())
    assert record.name == f"{CLUSTER}/static"
    assert ("ecs", REGION, "DescribeContainerInstances") not in {
        c[:3] for c in aws.calls
    }


def test_a_rollout_lists_both_deployments_images() -> None:
    aws = FakeAws()
    old = aws.add_definition(task_definition("bot", images=(APP,), revision=1))
    new = aws.add_definition(task_definition("bot", images=(GOOSE,), revision=2))
    service = ecs_service("bot", new)
    service["deployments"].append(
        {"status": "ACTIVE", "taskDefinition": old["taskDefinitionArn"]},
    )
    aws.services[REGION] = [service]
    aws.tasks[REGION] = []

    [record] = scan(aws, catalog=CATALOG)
    assert record.creation_source.observations.install_path == f"{GOOSE}, {APP}"
    assert record.name.startswith(f"{CLUSTER}/bot [goose]")


# --- CloudTrail: the second reason ------------------------------------------------------


def test_a_workload_whose_role_called_bedrock_is_reported_with_its_models() -> None:
    aws = ecs_account()
    # CloudTrail keeps the role's path; the task definition here does not.
    aws.events[REGION] = [model_call(role("support-bot-task", "service-role/"))]

    [record] = scan(aws)
    assert [m.name for m in record.llm_models] == [MODEL]
    assert ("cloudtrail", REGION, "LookupEvents") in {c[:3] for c in aws.calls}


def test_a_role_whose_every_call_was_refused_selects_nothing() -> None:
    # As in the Bedrock source: an IAM refusal is not a call.
    aws = ecs_account()
    aws.events[REGION] = [model_call(TASK_ROLE, model=None, error_code="AccessDenied")]

    assert scan(aws) == []


def test_a_bare_task_role_name_matches_the_arn_cloudtrail_names() -> None:
    # Defensive: ECS expands a bare taskRoleArn at registration (observed), but a bare
    # name must still match the ARN CloudTrail names, should one ever arrive.
    aws = FakeAws()
    d = aws.add_definition(task_definition("bot", task_role="support-bot-task"))
    aws.services[REGION] = [ecs_service("bot", d)]
    aws.tasks[REGION] = []
    aws.events[REGION] = [model_call(TASK_ROLE)]

    [record] = scan(aws)
    assert [m.name for m in record.llm_models] == [MODEL]
    assert record.name == f"{CLUSTER}/bot (runs as support-bot-task)"


def test_an_old_format_service_arn_gets_an_id_that_names_the_cluster() -> None:
    # arn:...:service/<name> has no cluster, so two clusters' "bot" would collide.
    aws = FakeAws()
    d = aws.add_definition(task_definition("bot"))
    service = ecs_service("bot", d)
    service["serviceArn"] = f"arn:aws:ecs:{REGION}:{ACCOUNT}:service/bot"
    aws.services[REGION] = [service]
    aws.tasks[REGION] = []

    [record] = scan(aws, report_all())
    assert record.external_id == f"{ACCOUNT}/{REGION}/ecs_service/{CLUSTER}/bot"


def test_reading_cloudtrail_can_be_turned_off() -> None:
    aws = ecs_account()
    aws.events[REGION] = [model_call(TASK_ROLE)]

    assert scan(aws, {**FIELDS, "read_cloudtrail": "false"}) == []
    assert "LookupEvents" not in aws.operations()


def test_a_role_shared_by_two_workloads_says_so() -> None:
    aws = FakeAws()
    a = aws.add_definition(task_definition("a"))
    b = aws.add_definition(task_definition("b"))
    aws.services[REGION] = [ecs_service("a", a), ecs_service("b", b)]
    aws.tasks[REGION] = []
    aws.events[REGION] = [model_call(TASK_ROLE)]

    records = scan(aws)
    assert sorted(r.name for r in records) == [
        f"{CLUSTER}/a (runs as support-bot-task, shared by 2 workloads)",
        f"{CLUSTER}/b (runs as support-bot-task, shared by 2 workloads)",
    ]


def test_role_keys_ignore_path_and_case() -> None:
    assert role_key(role("Bot", "service-role/")) == role_key(role("bot"))
    assert role_key("bot") == "bot"


# --- EKS --------------------------------------------------------------------------------


def eks_account(kube_paths: dict[str, Any]) -> tuple[FakeAws, FakeKube]:
    aws = FakeAws()
    aws.eks[EKS] = eks_cluster()
    aws.node_groups[EKS] = {"ng-1": NODE_ROLE}
    aws.pod_identity[EKS] = [("agents", "podid", POD_ID_ROLE)]
    # k8s(owner=...) names its owner "x": a Deployment's ReplicaSet, as most are.
    kube_paths.setdefault(
        "/apis/apps/v1/replicasets",
        [owned_by(k8s("replicaset", "x"), "Deployment", "web")],
    )
    return aws, FakeKube(kube_paths)


def test_eks_identity_is_irsa_then_pod_identity_then_the_node_role() -> None:
    aws, kube = eks_account(
        {
            "/api/v1/serviceaccounts": [
                service_account("irsa", irsa=IRSA_ROLE),
                service_account("podid"),
            ],
            "/apis/apps/v1/deployments": [
                k8s("deployment", "with-irsa", ksa="irsa"),
                k8s("deployment", "with-podid", ksa="podid"),
                k8s("deployment", "on-node"),
                k8s("deployment", "dns", namespace="kube-system"),
                k8s("deployment", "agent", namespace="amazon-guardduty"),
            ],
            "/api/v1/pods": [
                k8s("pod", "with-irsa-7d9f-abcde", owner="ReplicaSet"),
                k8s("pod", "debug", image_id=f"docker.io/x/y@{DIGEST}"),
            ],
            "/apis/batch/v1/cronjobs": [k8s("cronjob", "nightly", image=GOOSE)],
            "/apis/batch/v1/jobs": [k8s("job", "nightly-29001", owner="CronJob")],
        },
    )
    records = by_id(scan(aws, report_all(), kube))

    assert sorted(records) == [
        f"{EKS}/agents/cronjob/nightly",
        f"{EKS}/agents/deployment/on-node",
        f"{EKS}/agents/deployment/with-irsa",
        f"{EKS}/agents/deployment/with-podid",
        f"{EKS}/agents/pod/debug",
    ]
    irsa = records[f"{EKS}/agents/deployment/with-irsa"]
    assert irsa.name == f"{EKS}/agents/with-irsa (runs as irsa-agent)"
    assert irsa.external_id == (
        f"arn:aws:eks:{REGION}:{ACCOUNT}:cluster/{EKS}/k8s/namespaces/agents/"
        f"apps/deployments/with-irsa"
    )
    assert irsa.creation_source.address.resource_kind == EKS_WORKLOAD
    assert records[f"{EKS}/agents/deployment/with-podid"].name.endswith(
        "(runs as podid-agent)",
    )
    assert records[f"{EKS}/agents/deployment/on-node"].name.endswith(
        "(runs as eks-nodes, node role, shared by 3 workloads)",
    )
    assert records[
        f"{EKS}/agents/pod/debug"
    ].creation_source.observations.install_path == (f"{APP}@{DIGEST}")
    # The token goes to the cluster; the CA EKS returned is what the endpoint is checked
    # against.
    path, headers, verify = kube.calls[0]
    assert headers["Authorization"] == f"Bearer token-for-{EKS}"
    assert isinstance(verify, str) and verify.endswith(".pem")


def test_a_pod_a_fargate_profile_selects_has_no_node_role() -> None:
    aws, kube = eks_account(
        {
            "/apis/apps/v1/deployments": [
                k8s("deployment", "on-fargate", namespace="serverless"),
                k8s("deployment", "labelled", labels={"compute": "fargate", "x": "y"}),
                k8s("deployment", "on-node", labels={"compute": "ec2"}),
            ],
        },
    )
    aws.fargate[EKS] = {
        "fp-ns": [{"namespace": "server*"}],
        "fp-label": [{"namespace": "agents", "labels": {"compute": "farg?te"}}],
    }
    records = by_id(scan(aws, report_all(), kube))

    assert records[f"{EKS}/serverless/deployment/on-fargate"].name == (
        f"{EKS}/serverless/on-fargate"
    )
    assert records[f"{EKS}/agents/deployment/labelled"].name == f"{EKS}/agents/labelled"
    assert records[f"{EKS}/agents/deployment/on-node"].name.endswith(
        "(runs as eks-nodes, node role)",
    )


def test_the_kubernetes_token_is_minted_for_every_page() -> None:
    # A presigned token lasts minutes; a large cluster's listing can outlast one.
    minted: list[str] = []

    def tokens_for(session: Any) -> Callable[[str, str], str]:
        def token(region: str, cluster: str) -> str:
            minted.append(cluster)
            return f"token-{len(minted)}"

        return token

    aws, kube = eks_account({"/apis/apps/v1/deployments": [k8s("deployment", "a")]})
    connector = AwsContainersConnector(
        session_for=lambda creds, fields: boto3.Session(),
        clients_for=lambda session: aws.client_for,
        tokens_for=tokens_for,
        http=kube,  # type: ignore[arg-type]
        clock=lambda: NOW,
        sleep=lambda seconds: None,
    )
    scan(aws, report_all(), connector=connector)
    assert len(minted) == len(kube.calls) > 1
    assert len({h["Authorization"] for _, h, _ in kube.calls}) == len(kube.calls)


def test_an_operator_owned_controller_is_still_a_workload() -> None:
    # A model server's operator owns its Deployment; the custom resource is not listed.
    aws, kube = eks_account(
        {
            "/apis/apps/v1/deployments": [
                k8s("deployment", "llm-predictor", owner="InferenceService"),
            ],
            "/api/v1/pods": [k8s("pod", "llm-predictor-5d9f-x", owner="ReplicaSet")],
        },
    )
    [record] = scan(aws, report_all(), kube)
    assert record.creation_source.address.resource_id == (
        f"{EKS}/agents/deployment/llm-predictor"
    )


def owned_by(raw: Any, kind: str, name: str) -> Any:
    raw["metadata"]["ownerReferences"] = [{"kind": kind, "name": name}]
    return raw


def test_a_pod_of_a_replicaset_a_rollout_owns_is_its_own_workload() -> None:
    # An Argo Rollout owns its ReplicaSets, and the Rollout is not listed.
    aws, kube = eks_account(
        {
            "/apis/apps/v1/replicasets": [
                owned_by(k8s("replicaset", "web-5d9f"), "Deployment", "web"),
                owned_by(k8s("replicaset", "canary-7c4b"), "Rollout", "canary"),
            ],
            "/api/v1/pods": [
                owned_by(k8s("pod", "web-5d9f-x"), "ReplicaSet", "web-5d9f"),
                owned_by(k8s("pod", "canary-7c4b-y"), "ReplicaSet", "canary-7c4b"),
            ],
        },
    )
    records = by_id(scan(aws, report_all(), kube))
    assert sorted(records) == [f"{EKS}/agents/pod/canary-7c4b-y"]


def test_unreadable_replicasets_fold_every_replicaset_pod_as_before() -> None:
    aws, kube = eks_account(
        {
            "/apis/apps/v1/replicasets": FakeResponse(
                403,
                {"kind": "Status", "message": "forbidden"},
            ),
            "/api/v1/pods": [
                owned_by(k8s("pod", "canary-7c4b-y"), "ReplicaSet", "canary-7c4b"),
            ],
        },
    )
    connector = connector_for(aws, kube)
    assert scan(aws, report_all(), connector=connector) == []
    assert connector.denied_scopes() == ()


def test_pods_and_jobs_an_operator_owns_are_their_own_workloads() -> None:
    # KubeRay owns its pods and JobSet its Jobs directly; neither owner is listed.
    aws, kube = eks_account(
        {
            "/api/v1/pods": [
                k8s("pod", "ray-head", owner="RayCluster"),
                k8s("pod", "web-7d9f-x", owner="ReplicaSet"),
                k8s("pod", "trainer-0", owner="StatefulSet"),
                k8s("pod", "nightly-29001-abc", owner="Job"),
            ],
            "/apis/batch/v1/jobs": [
                k8s("job", "train-0", owner="JobSet"),
                k8s("job", "nightly-29001", owner="CronJob"),
            ],
        },
    )
    records = by_id(scan(aws, report_all(), kube))
    assert sorted(records) == [
        f"{EKS}/agents/job/train-0",
        f"{EKS}/agents/pod/ray-head",
    ]


def test_a_call_that_failed_in_the_model_still_selects_and_names_its_model() -> None:
    aws = ecs_account()
    aws.events[REGION] = [model_call(TASK_ROLE, error_code="ModelErrorException")]

    [record] = scan(aws)
    assert [m.name for m in record.llm_models] == [MODEL]


def test_an_eks_node_role_that_calls_bedrock_does_not_report_system_pods() -> None:
    aws, kube = eks_account(
        {
            "/apis/apps/v1/daemonsets": [
                k8s("daemonset", "aws-node", namespace="kube-system"),
            ],
            "/apis/apps/v1/deployments": [k8s("deployment", "on-node")],
        },
    )
    aws.events[REGION] = [model_call(NODE_ROLE)]

    [record] = scan(aws, FIELDS, kube)
    assert (
        record.creation_source.address.resource_id == f"{EKS}/agents/deployment/on-node"
    )


def test_a_kubernetes_401_is_that_clusters_refusal_and_the_scan_goes_on(
    caplog: pytest.LogCaptureFixture,
) -> None:
    aws, kube = eks_account(
        {
            "/api/v1/serviceaccounts": FakeResponse(
                401,
                {"kind": "Status", "message": "Unauthorized"},
            ),
        },
    )
    ecs_account(aws)
    connector = connector_for(aws, kube)
    with caplog.at_level(logging.WARNING):
        records = scan(aws, report_all(), connector=connector)

    assert [r.creation_source.address.resource_kind for r in records] == [ECS_SERVICE]
    assert connector.denied_scopes() == (
        DeniedScope(f"{ACCOUNT}/{REGION}/eks/{EKS}", DENIED_PERMISSION),
    )
    assert "access entry" in caplog.text


def test_an_unreachable_private_endpoint_is_a_denied_scope() -> None:
    import requests

    aws, kube = eks_account(
        {"/api/v1/serviceaccounts": requests.ConnectionError("timed out")},
    )
    ecs_account(aws)
    connector = connector_for(aws, kube)
    scan(aws, report_all(), connector=connector)
    assert connector.denied_scopes() == (
        DeniedScope(f"{ACCOUNT}/{REGION}/eks/{EKS}", DENIED_UNREACHABLE),
    )


def test_refused_pod_identity_costs_roles_not_the_cluster() -> None:
    aws, kube = eks_account(
        {
            "/api/v1/serviceaccounts": [service_account("podid")],
            "/apis/apps/v1/deployments": [k8s("deployment", "with-podid", ksa="podid")],
        },
    )
    aws.errors[("eks", "ListPodIdentityAssociations")] = client_error(
        "AccessDeniedException",
        "ListPodIdentityAssociations",
    )
    connector = connector_for(aws, kube)
    [record] = scan(aws, report_all(), connector=connector)
    assert record.name.endswith("(runs as eks-nodes, node role)")
    assert connector.denied_scopes() == ()


# --- refusals ---------------------------------------------------------------------------


def test_a_refused_credential_ends_the_scan() -> None:
    aws = ecs_account()
    aws.errors[("ecs", "ListClusters")] = client_error(
        "UnrecognizedClientException",
        "ListClusters",
    )
    with pytest.raises(Exception) as caught:
        scan(aws, report_all())
    assert failure_code(caught.value) == DiscoveryErrorCode.AUTHENTICATION_FAILED


def test_a_denied_listing_is_a_denied_scope_and_everything_denied_fails() -> None:
    aws = ecs_account()
    aws.eks[EKS] = eks_cluster()
    aws.errors[("ecs", "ListClusters")] = client_error(
        "AccessDeniedException",
        "ListClusters",
    )
    connector = connector_for(aws)
    records = scan(aws, report_all(read_cloudtrail="false"), connector=connector)
    assert records == []
    assert DeniedScope(f"{ACCOUNT}/{REGION}/ecs", DENIED_PERMISSION) in (
        connector.denied_scopes()
    )

    aws.errors[("eks", "ListClusters")] = client_error(
        "AccessDeniedException",
        "ListClusters",
    )
    with pytest.raises(Exception) as caught:
        scan(aws, report_all(read_cloudtrail="false"))
    assert failure_code(caught.value) == DiscoveryErrorCode.PERMISSION_DENIED


def test_listing_cluster_names_is_not_a_listing_when_every_cluster_is_refused() -> None:
    aws = ecs_account()
    aws.eks[EKS] = eks_cluster()
    aws.errors[("ecs", "ListServices")] = client_error(
        "AccessDeniedException", "ListServices"
    )
    aws.errors[("eks", "DescribeCluster")] = client_error(
        "AccessDeniedException", "DescribeCluster"
    )
    with pytest.raises(Exception) as caught:
        scan(aws, report_all(read_cloudtrail="false"))
    assert failure_code(caught.value) == DiscoveryErrorCode.PERMISSION_DENIED

    # A region with no ECS clusters answered, so refused EKS clusters alone do not fail.
    aws.services.clear()
    assert scan(aws, report_all(read_cloudtrail="false")) == []


def test_cloudtrail_alone_is_not_a_listing_so_refused_ecs_and_eks_fail() -> None:
    # The CloudTrail read answers; every workload listing is refused.
    aws = ecs_account()
    aws.eks[EKS] = eks_cluster()
    aws.events[REGION] = [model_call(TASK_ROLE)]
    aws.errors[("ecs", "ListClusters")] = client_error(
        "AccessDeniedException",
        "ListClusters",
    )
    aws.errors[("eks", "ListClusters")] = client_error(
        "AccessDeniedException",
        "ListClusters",
    )
    connector = connector_for(aws)
    with pytest.raises(Exception) as caught:
        scan(aws, report_all(), connector=connector)

    assert failure_code(caught.value) == DiscoveryErrorCode.PERMISSION_DENIED
    assert "LookupEvents" in aws.operations()
    assert connector.denied_scopes() == (
        DeniedScope(f"{ACCOUNT}/{REGION}/ecs", DENIED_PERMISSION),
        DeniedScope(f"{ACCOUNT}/{REGION}/eks", DENIED_PERMISSION),
    )


def test_env_values_never_reach_a_record_or_the_log(
    caplog: pytest.LogCaptureFixture,
) -> None:
    aws, kube = eks_account({"/apis/apps/v1/deployments": [k8s("deployment", "x")]})
    ecs_account(aws)
    with caplog.at_level(logging.DEBUG):
        records = scan(aws, report_all(), kube)
    assert records
    dumped = " ".join(r.model_dump_json() for r in records) + caplog.text
    assert "do-not-read" not in dumped


# --- an organization as the roster ------------------------------------------------------


ONE = "111111111111"
TWO = "222222222222"
WEST = "us-west-2"
ORG_FIELDS = {
    "regions": WEST,
    "accounts": "all",
    "external_id": "abc",
    "report_all_workloads": "true",
}
ASSUME_DENIED = client_error("AccessDenied", "AssumeRole")


class FakeOrg:
    """An organization: the source's own account, which lists the members, and each
    member account, reached through the member role the connector asks for."""

    def __init__(self, members: list[FakeAws]) -> None:
        self.own = FakeAws()
        self.own.accounts_listed = [(m.account, "ACTIVE") for m in members]
        self.own.accounts_listed.append(("333333333333", "SUSPENDED"))
        self.members = {m.account: m for m in members}
        self.sessions: list[Any] = []

    def clients(self, session: Any) -> Any:
        account = getattr(session, "account", None)
        return (self.members[account] if account else self.own).client_for

    def account_session(
        self,
        base: boto3.Session,
        account: str,
        role_name: str,
        external_id: Optional[str],
    ) -> Any:
        session = SimpleNamespace(
            account=account,
            role_name=role_name,
            external_id=external_id,
            region_name=base.region_name,
        )
        self.sessions.append(session)
        return session


def connector_for_org(org: FakeOrg) -> AwsContainersConnector:
    return AwsContainersConnector(
        session_for=lambda creds, fields: boto3.Session(region_name=BOOTSTRAP_REGION),
        clients_for=org.clients,
        tokens_for=lambda session: (lambda region, cluster: f"token-for-{cluster}"),
        http=FakeKube(),  # type: ignore[arg-type]
        clock=lambda: NOW,
        sleep=lambda seconds: None,
        account_session_for=org.account_session,
    )


def member(account: str, service: str, region: str = WEST) -> FakeAws:
    """A member account with one Fargate service, running as a task role of its own."""
    aws = FakeAws(account)
    aws.regions_enabled = [REGION, region]
    d = aws.add_definition(
        task_definition(
            service,
            task_role=f"arn:aws:iam::{account}:role/agent-task",
        ),
    )
    aws.services[region] = [ecs_service(service, d)]
    aws.tasks[region] = [ecs_task(f"{service}-1", d, f"service:{service}")]
    return aws


def accounts_of(records: list[Any]) -> set[tuple[str, str]]:
    return {
        (r.creation_source.address.instance, r.creation_source.address.resource_id)
        for r in records
    }


def test_every_active_account_is_read_through_the_member_role(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Organizations gives the roster, a suspended account left out; the member role is
    assumed per account with the source's external ID; STS and Organizations are asked
    in the partition's bootstrap region, the workloads in the regions named."""
    org = FakeOrg([member(ONE, "support-bot"), member(TWO, "billing-bot")])
    connector = connector_for_org(org)
    with caplog.at_level(logging.INFO):
        records = scan(org.own, ORG_FIELDS, connector=connector)

    assert accounts_of(records) == {
        (ONE, f"{CLUSTER}/support-bot"),
        (TWO, f"{CLUSTER}/billing-bot"),
    }
    assert [(s.account, s.role_name, s.external_id) for s in org.sessions] == [
        (ONE, DEFAULT_MEMBER_ROLE_NAME, "abc"),
        (TWO, DEFAULT_MEMBER_ROLE_NAME, "abc"),
    ]
    assert [(c[1], c[2]) for c in org.own.calls] == [
        (BOOTSTRAP_REGION, "ListAccounts"),
        (BOOTSTRAP_REGION, "ListAccounts"),
        (BOOTSTRAP_REGION, "ListAccounts"),
    ]
    one = org.members[ONE].calls
    assert [c[1] for c in one if c[2] == "GetCallerIdentity"] == [BOOTSTRAP_REGION]
    assert {c[1] for c in one if c[0] == "ecs"} == {WEST}
    assert connector.denied_scopes() == ()
    assert "reading 2 account(s) through role arthur-ai-discovery" in caplog.text
    assert "2 account(s) read through role arthur-ai-discovery; 0 refused" in (
        caplog.text
    )


def test_an_account_listed_with_only_the_retired_status_is_still_read() -> None:
    """Organizations retired `Status` for `State` on 2026-09-09; the fake answers with
    `State` everywhere else. An answer with only `Status` still names who is active."""
    org = FakeOrg([member(ONE, "support-bot")])
    org.own.account_field = "Status"
    records = scan(org.own, ORG_FIELDS, connector=connector_for_org(org))

    assert accounts_of(records) == {(ONE, f"{CLUSTER}/support-bot")}
    assert [s.account for s in org.sessions] == [ONE], "the suspended one is left out"


def test_named_accounts_are_read_without_asking_organizations() -> None:
    org = FakeOrg([member(ONE, "support-bot"), member(TWO, "billing-bot")])
    connector = connector_for_org(org)
    records = scan(
        org.own,
        {
            **report_all(),
            "regions": WEST,
            "accounts": TWO,
            "member_role_name": "Reader",
        },
        connector=connector,
    )

    assert accounts_of(records) == {(TWO, f"{CLUSTER}/billing-bot")}
    assert org.own.calls == [], "no listing was asked for"
    assert [(s.account, s.role_name, s.external_id) for s in org.sessions] == [
        (TWO, "Reader", None),
    ]


def test_an_account_whose_role_cannot_be_assumed_is_a_denied_scope(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """The role is assumed by the account's first call, so its refusal arrives there.
    That account is one scope, its regions unasked; every other account is read."""
    refused = member(TWO, "billing-bot")
    refused.assume_error = ASSUME_DENIED
    org = FakeOrg([member(ONE, "support-bot"), refused])
    connector = connector_for_org(org)
    with caplog.at_level(logging.WARNING):
        records = scan(org.own, ORG_FIELDS, connector=connector)

    assert accounts_of(records) == {(ONE, f"{CLUSTER}/support-bot")}
    assert connector.denied_scopes() == (DeniedScope(TWO, DENIED_PERMISSION),)
    assert [c[2] for c in refused.calls] == ["GetCallerIdentity"]
    assert f"{TWO}: not read (permission_denied): STS AssumeRole" in caplog.text


def test_a_member_accounts_refused_listing_names_that_account() -> None:
    denied = member(TWO, "billing-bot")
    denied.errors[("ecs", "ListClusters")] = client_error(
        "AccessDeniedException",
        "ListClusters",
    )
    org = FakeOrg([member(ONE, "support-bot"), denied])
    connector = connector_for_org(org)
    records = scan(org.own, ORG_FIELDS, connector=connector)

    assert accounts_of(records) == {(ONE, f"{CLUSTER}/support-bot")}
    assert connector.denied_scopes() == (
        DeniedScope(f"{TWO}/{WEST}/ecs", DENIED_PERMISSION),
    )


def test_every_account_refused_fails_the_scan() -> None:
    org = FakeOrg([member(ONE, "support-bot"), member(TWO, "billing-bot")])
    for refused in org.members.values():
        refused.assume_error = ASSUME_DENIED
    connector = connector_for_org(org)
    with pytest.raises(Exception) as caught:
        scan(org.own, ORG_FIELDS, connector=connector)

    assert failure_code(caught.value) == DiscoveryErrorCode.PERMISSION_DENIED
    assert "Check that role arthur-ai-discovery exists" in str(caught.value)
    assert connector.denied_scopes() == (
        DeniedScope(ONE, DENIED_PERMISSION),
        DeniedScope(TWO, DENIED_PERMISSION),
    )


def test_a_refused_credential_ends_an_organization_scan() -> None:
    """A 401 is the source's credential, whichever account's call met it."""
    refused = member(ONE, "support-bot")
    refused.assume_error = client_error("InvalidClientTokenId", "AssumeRole")
    org = FakeOrg([refused, member(TWO, "billing-bot")])
    with pytest.raises(Exception) as caught:
        scan(org.own, ORG_FIELDS, connector=connector_for_org(org))

    assert failure_code(caught.value) == DiscoveryErrorCode.AUTHENTICATION_FAILED
    assert org.members[TWO].calls == [], "the scan ended at the first account"


def test_a_refused_organization_listing_fails_the_scan() -> None:
    org = FakeOrg([member(ONE, "support-bot")])
    org.own.errors[("organizations", "ListAccounts")] = client_error(
        "AccessDeniedException",
        "ListAccounts",
    )
    with pytest.raises(Exception) as caught:
        scan(org.own, ORG_FIELDS, connector=connector_for_org(org))

    assert failure_code(caught.value) == DiscoveryErrorCode.PERMISSION_DENIED
    assert org.members[ONE].calls == []


def test_every_region_is_each_accounts_enabled_regions() -> None:
    org = FakeOrg([member(ONE, "support-bot")])
    records = scan(
        org.own,
        {**ORG_FIELDS, "regions": "all"},
        connector=connector_for_org(org),
    )

    assert accounts_of(records) == {(ONE, f"{CLUSTER}/support-bot")}
    calls = org.members[ONE].calls
    assert [c[1] for c in calls if c[2] == "DescribeRegions"] == [BOOTSTRAP_REGION]
    assert {c[1] for c in calls if c[0] == "ecs" and c[2] == "ListClusters"} == {
        REGION,
        WEST,
    }
    assert {c[1] for c in calls if c[2] == "LookupEvents"} == {REGION, WEST}


def test_one_accounts_model_callers_never_select_anothers_workloads() -> None:
    """Two accounts each run a role named agent-task; only ONE's called a model. Roles
    are keyed by account, so TWO's workload is not reported."""
    caller = member(ONE, "support-bot")
    caller.events[WEST] = [model_call(f"arn:aws:iam::{ONE}:role/agent-task")]
    org = FakeOrg([caller, member(TWO, "billing-bot")])
    records = scan(
        org.own,
        {**ORG_FIELDS, "report_all_workloads": "false"},
        connector=connector_for_org(org),
    )

    assert accounts_of(records) == {(ONE, f"{CLUSTER}/support-bot")}
    [record] = records
    assert [m.name for m in record.llm_models or []] == [MODEL]


def test_an_external_id_for_member_roles_needs_no_role_of_the_source_s_own() -> None:
    """With `accounts`, the external ID is the member roles'; the source's own session
    is asked in the bootstrap region. With a role of its own, it is sent to both."""
    key = {"access_key_id": "AKIAEXAMPLE", "secret_access_key": "secret"}
    session = source_session(
        key,
        {"regions": WEST, "accounts": "all", "external_id": "x"},
    )
    assert session.get_credentials().method != "assume-role"
    assert session.region_name == BOOTSTRAP_REGION

    hub = source_session(
        key,
        {
            "regions": WEST,
            "accounts": "all",
            "role_arn": "arn:aws:iam::123456789012:role/arthur-ai-discovery-hub",
            "external_id": "x",
        },
    )
    assert hub.get_credentials().method == "assume-role"


# --- settings ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "fields",
    [
        {},
        {"regions": "us-east-1,mars-1"},
        {"regions": REGION, "read_cloudtrail": "maybe"},
        {"regions": REGION, "report_all_workloads": "yes please"},
        {"regions": f"{REGION},us-gov-west-1"},
        {"regions": REGION, "accounts": "12345"},
        {"regions": REGION, "accounts": f"all,{ONE}"},
        {"regions": REGION, "accounts": "all", "member_role_name": "arn:aws:iam::x"},
    ],
)
def test_bad_settings_are_configuration_errors(fields: dict[str, str]) -> None:
    with pytest.raises(DiscoveryConfigurationError):
        settings_from(fields)


def test_toggles_default_to_cloudtrail_on_and_report_all_off() -> None:
    settings = settings_from({"regions": "us-east-1, us-west-2"})
    assert settings.regions == ("us-east-1", "us-west-2")
    assert settings.read_cloudtrail is True
    assert settings.report_all_workloads is False
    assert not settings.spans_accounts
    assert settings.home_region == "us-east-1", "one account: its first region"


def test_an_organization_and_every_region_are_asked_where_every_account_answers() -> (
    None
):
    settings = settings_from({"regions": "all", "accounts": "ALL"})
    assert settings.all_regions and settings.all_accounts and settings.spans_accounts
    assert settings.regions == ()
    assert settings.member_role_name == DEFAULT_MEMBER_ROLE_NAME
    assert settings.home_region == BOOTSTRAP_REGION

    named = settings_from({"regions": WEST, "accounts": f"{ONE}, {TWO}"})
    assert named.accounts == (ONE, TWO) and not named.all_accounts
    assert named.home_region == BOOTSTRAP_REGION

    gov = settings_from({"regions": "us-gov-east-1", "accounts": "all"})
    assert gov.home_region == "us-gov-west-1"


def test_a_source_without_a_key_needs_the_engines_opt_in(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv(ALLOW_DEFAULT_CREDENTIALS_ENV_VAR, raising=False)
    with pytest.raises(
        DiscoveryConfigurationError,
        match=ALLOW_DEFAULT_CREDENTIALS_ENV_VAR,
    ):
        AwsContainersConnector().scan(
            FakeConfig(),  # type: ignore[arg-type]
            24,
            {},
            FIELDS,
            LOG,
        ).__next__()


def test_the_eks_token_is_a_presigned_get_caller_identity_naming_the_cluster() -> None:
    sts = boto3.Session(
        aws_access_key_id="AKIAEXAMPLE",
        aws_secret_access_key="secret",
    ).client("sts", region_name=REGION)
    token = presigned_token(sts, EKS)

    assert token.startswith("k8s-aws-v1.")
    padded = token[len("k8s-aws-v1.") :] + "=" * (-len(token) % 4)
    url = base64.urlsafe_b64decode(padded).decode()
    assert "Action=GetCallerIdentity" in url
    assert "x-k8s-aws-id" in url
    assert "secret" not in url
