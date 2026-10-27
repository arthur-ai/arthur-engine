"""Reading container workloads out of ECS, EKS and the Kubernetes API.

Read-only, list and describe calls only. Nothing is deployed, exec'd into or written
back, and no call reads a container's logs, a Secret or a ConfigMap.

THE AWS CALLS, through boto3 as every AWS source here:

- ECS: `ListClusters`, `ListServices` + `DescribeServices` (ten at a time), `ListTasks`
  (running and recently stopped) + `DescribeTasks` (a hundred at a time),
  `DescribeTaskDefinition` once per revision, and for tasks on EC2 with no task role
  `DescribeContainerInstances`, then EC2's `DescribeInstances` and IAM's
  `GetInstanceProfile` for the role the instance runs as.
- EKS: `ListClusters`, `DescribeCluster` (endpoint and CA), `ListNodegroups` +
  `DescribeNodegroup` (node roles), `ListFargateProfiles` + `DescribeFargateProfile`
  (which pods run on Fargate, with no node role), `ListPodIdentityAssociations` +
  `DescribePodIdentityAssociation` (the role each binds).
- STS: a presigned `GetCallerIdentity`, which is the token EKS's Kubernetes API takes
  (`k8s-aws-v1.` and the URL, base64url); it is signed here, never sent to STS.

THE KUBERNETES API IS ASKED FOR CONTROLLERS, NOT PODS, as on GKE: a pod's name changes
every rollout, the Deployment that owns it does not. Pods and Jobs are read for the
ones nothing owns. The cluster's endpoint is trusted only against the CA EKS returned.

ENV VALUES ARE NEVER KEPT. `DescribeTaskDefinition` and a pod template both carry their
containers' environment, and neither listing can be asked to leave it out. Only images,
roles, names, group, digests and timestamps are read off each object.

WHAT AWS ANSWERED. A refused credential is 401 and a denied action 403, on the
`status_code` `failure_code` reads. The Kubernetes API answers 401 to an IAM identity it
has no access entry for, which is that cluster's refusal and not the credential's, so
its errors are `KubernetesError`, apart from AWS's.
"""

import base64
import logging
import os
import tempfile
import time
from contextlib import contextmanager
from typing import Any, Callable, Iterator, Mapping, Optional, Sequence

import requests
from botocore.exceptions import (
    BotoCoreError,
    ClientError,
    NoCredentialsError,
    PartialCredentialsError,
)

from discovery.retry import MAX_ATTEMPTS, RETRY_STATUSES, backoff_seconds
from job_executors.discovery_scan import DiscoveryConfigurationError

PAGE_SIZE = 100
MAX_PAGES = 1000

# What ECS and EKS answer a describe call with at most, per call.
DESCRIBE_SERVICES_BATCH = 10
DESCRIBE_TASKS_BATCH = 100

_REFUSED_CODES = frozenset(
    {
        "AuthFailure",
        "ExpiredToken",
        "ExpiredTokenException",
        "IncompleteSignature",
        "InvalidClientTokenId",
        "InvalidSignatureException",
        "SignatureDoesNotMatch",
        "UnrecognizedClientException",
    },
)
_DENIED_CODES = frozenset(
    {"AccessDenied", "AccessDeniedException", "OptInRequired", "UnauthorizedOperation"},
)

TokenFactory = Callable[[str, str], str]
"""`(region, cluster name) -> bearer token` for that cluster's Kubernetes API."""


class AwsContainersError(RuntimeError):
    """An ECS, EKS, EC2, IAM or STS call failed in a way retrying will not fix.

    `status_code` is 401 or 403 when the credential or its permission is the cause, which
    `failure_code` reads; `code` is AWS's own error code, where there is one.
    """

    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        code: Optional[str] = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code


class KubernetesError(RuntimeError):
    """A cluster's Kubernetes API could not be read: refused (401/403), unreachable
    (no status), or failing. Always that one cluster's problem."""

    def __init__(self, message: str, status_code: Optional[int] = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class ScanStopped(Exception):
    """The scan's stop check fired before a call. Not a failure."""


class AwsContainersClient:
    """One scan's AWS and Kubernetes reads, one call at a time.

    `client_for` is `(service, region) -> boto3 client`, as Bedrock's; `token_for`
    mints a cluster's Kubernetes token; `http` carries the Kubernetes calls.
    """

    def __init__(
        self,
        client_for: Callable[[str, str], Any],
        token_for: TokenFactory,
        logger: Optional[logging.Logger] = None,
        should_stop: Callable[[], bool] = lambda: False,
        http: Optional[requests.Session] = None,
        sleep: Callable[[float], None] = time.sleep,
        timeout_seconds: float = 30.0,
    ) -> None:
        self._client_for = client_for
        self._token_for = token_for
        self._log = logger or logging.getLogger(__name__)
        self._should_stop = should_stop
        self._http = http or requests.Session()
        self._sleep = sleep
        self._timeout = timeout_seconds

    # --- ECS ----------------------------------------------------------------------

    def ecs_clusters(self, region: str) -> list[str]:
        """Every ECS cluster's ARN in the region."""
        return list(self._pages("ecs", region, "list_clusters", "clusterArns"))

    def ecs_services(self, region: str, cluster: str) -> list[Mapping[str, Any]]:
        """Every service in the cluster, described."""
        arns = list(
            self._pages(
                "ecs",
                region,
                "list_services",
                "serviceArns",
                cluster=cluster,
            ),
        )
        out: list[Mapping[str, Any]] = []
        for batch in _batches(arns, DESCRIBE_SERVICES_BATCH):
            body = self._call(
                "ecs",
                region,
                "describe_services",
                cluster=cluster,
                services=batch,
            )
            out.extend(body.get("services") or [])
        return out

    def ecs_tasks(self, region: str, cluster: str) -> list[Mapping[str, Any]]:
        """Every running task in the cluster, and those stopped recently enough that
        ECS still lists them (about an hour), described."""
        arns: list[str] = []
        for status in ("RUNNING", "STOPPED"):
            arns.extend(
                self._pages(
                    "ecs",
                    region,
                    "list_tasks",
                    "taskArns",
                    cluster=cluster,
                    desiredStatus=status,
                ),
            )
        out: list[Mapping[str, Any]] = []
        for batch in _batches(list(dict.fromkeys(arns)), DESCRIBE_TASKS_BATCH):
            body = self._call(
                "ecs",
                region,
                "describe_tasks",
                cluster=cluster,
                tasks=batch,
            )
            out.extend(body.get("tasks") or [])
        return out

    def task_definition(self, region: str, arn: str) -> Mapping[str, Any]:
        """One task definition revision."""
        body = self._call(
            "ecs",
            region,
            "describe_task_definition",
            taskDefinition=arn,
        )
        return body.get("taskDefinition") or {}

    def container_instance_roles(
        self,
        region: str,
        cluster: str,
        instance_arns: Sequence[str],
    ) -> list[str]:
        """The IAM roles the EC2 instances behind these container instances run as."""
        instance_ids: list[str] = []
        for batch in _batches(list(dict.fromkeys(instance_arns)), PAGE_SIZE):
            body = self._call(
                "ecs",
                region,
                "describe_container_instances",
                cluster=cluster,
                containerInstances=batch,
            )
            instance_ids.extend(
                str(ci["ec2InstanceId"])
                for ci in body.get("containerInstances") or []
                if ci.get("ec2InstanceId")
            )
        profiles: list[str] = []
        for batch in _batches(list(dict.fromkeys(instance_ids)), PAGE_SIZE):
            body = self._call("ec2", region, "describe_instances", InstanceIds=batch)
            for reservation in body.get("Reservations") or []:
                for instance in reservation.get("Instances") or []:
                    arn = str(
                        (instance.get("IamInstanceProfile") or {}).get("Arn") or ""
                    )
                    if arn:
                        profiles.append(arn.rsplit("/", 1)[-1])
        roles: list[str] = []
        for name in dict.fromkeys(profiles):
            body = self._call(
                "iam",
                region,
                "get_instance_profile",
                InstanceProfileName=name,
            )
            roles.extend(
                str(r["Arn"])
                for r in (body.get("InstanceProfile") or {}).get("Roles") or []
                if r.get("Arn")
            )
        return list(dict.fromkeys(roles))

    # --- EKS ----------------------------------------------------------------------

    def eks_clusters(self, region: str) -> list[str]:
        """Every EKS cluster's name in the region."""
        return list(self._pages("eks", region, "list_clusters", "clusters"))

    def eks_cluster(self, region: str, name: str) -> Mapping[str, Any]:
        body = self._call("eks", region, "describe_cluster", name=name)
        return body.get("cluster") or {}

    def node_roles(self, region: str, cluster: str) -> list[str]:
        """The node roles of the cluster's managed node groups."""
        roles: list[str] = []
        for group in self._pages(
            "eks",
            region,
            "list_nodegroups",
            "nodegroups",
            clusterName=cluster,
        ):
            body = self._call(
                "eks",
                region,
                "describe_nodegroup",
                clusterName=cluster,
                nodegroupName=group,
            )
            role = str((body.get("nodegroup") or {}).get("nodeRole") or "")
            if role:
                roles.append(role)
        return list(dict.fromkeys(roles))

    def fargate_selectors(
        self,
        region: str,
        cluster: str,
    ) -> list[tuple[str, dict[str, str]]]:
        """Every Fargate profile's selectors, as (namespace pattern, labels)."""
        out: list[tuple[str, dict[str, str]]] = []
        for profile in self._pages(
            "eks",
            region,
            "list_fargate_profiles",
            "fargateProfileNames",
            clusterName=cluster,
        ):
            body = self._call(
                "eks",
                region,
                "describe_fargate_profile",
                clusterName=cluster,
                fargateProfileName=profile,
            )
            for selector in (body.get("fargateProfile") or {}).get("selectors") or []:
                namespace = str(selector.get("namespace") or "")
                if namespace:
                    labels = {
                        str(k): str(v)
                        for k, v in (selector.get("labels") or {}).items()
                    }
                    out.append((namespace, labels))
        return out

    def pod_identity_roles(
        self,
        region: str,
        cluster: str,
    ) -> dict[tuple[str, str], str]:
        """(namespace, service account) -> the role its Pod Identity association binds."""
        out: dict[tuple[str, str], str] = {}
        for summary in self._pages(
            "eks",
            region,
            "list_pod_identity_associations",
            "associations",
            clusterName=cluster,
        ):
            body = self._call(
                "eks",
                region,
                "describe_pod_identity_association",
                clusterName=cluster,
                associationId=summary.get("associationId"),
            )
            association = body.get("association") or {}
            role = str(association.get("roleArn") or "")
            namespace = str(association.get("namespace") or "")
            account = str(association.get("serviceAccount") or "")
            if role and namespace and account:
                out[(namespace, account)] = role
        return out

    @contextmanager
    def kubernetes(
        self,
        region: str,
        cluster: Mapping[str, Any],
    ) -> Iterator["KubernetesApi"]:
        """The cluster's Kubernetes API, trusting only the CA EKS says it has.

        The CA is written to a temporary file because that is the form requests takes
        it in, and removed when the cluster is done.
        """
        endpoint = str(cluster.get("endpoint") or "")
        ca_b64 = str((cluster.get("certificateAuthority") or {}).get("data") or "")
        if not endpoint or not ca_b64:
            raise KubernetesError("EKS returned no endpoint or cluster CA")
        try:
            ca = base64.b64decode(ca_b64, validate=True)
        except ValueError as exc:
            raise KubernetesError(
                "EKS returned a cluster CA that is not base64"
            ) from exc
        name = str(cluster.get("name") or "")
        fd, path = tempfile.mkstemp(prefix="eks-ca-", suffix=".pem")
        try:
            with os.fdopen(fd, "wb") as f:
                f.write(ca)
            yield KubernetesApi(
                self,
                endpoint.rstrip("/"),
                path,
                lambda: self._token_for(region, name),
            )
        finally:
            os.unlink(path)

    # --- transport ----------------------------------------------------------------

    def _pages(
        self,
        service: str,
        region: str,
        operation: str,
        key: str,
        **kwargs: Any,
    ) -> Iterator[Any]:
        """Every item of a list call, following `nextToken`. ECS's and EKS's list
        calls all page this way and all take at most a hundred per page."""
        token: Optional[str] = None
        for _ in range(MAX_PAGES):
            args: dict[str, Any] = {**kwargs, "maxResults": PAGE_SIZE}
            if token:
                args["nextToken"] = token
            body = self._call(service, region, operation, **args)
            yield from body.get(key) or []
            next_token = body.get("nextToken")
            if not next_token or next_token == token:
                return
            token = next_token
        self._log.warning(
            "%s %s in %s still had pages after %s; the listing is incomplete",
            service,
            operation,
            region,
            MAX_PAGES,
        )

    def _call(
        self,
        service: str,
        region: str,
        operation: str,
        **kwargs: Any,
    ) -> Mapping[str, Any]:
        if self._should_stop():
            raise ScanStopped()
        try:
            body = getattr(self._client_for(service, region), operation)(**kwargs)
        except (ClientError, BotoCoreError) as e:
            raise _aws_error(service, region, e) from None
        return body if isinstance(body, Mapping) else {}

    def _kube_get(
        self,
        url: str,
        params: Mapping[str, Any],
        token: str,
        ca_path: str,
    ) -> Mapping[str, Any]:
        path = "/" + url.split("://", 1)[-1].split("/", 1)[-1]
        last: Optional[str] = None
        for attempt in range(1, MAX_ATTEMPTS + 1):
            if self._should_stop():
                raise ScanStopped()
            try:
                resp = self._http.get(
                    url,
                    params=params,
                    headers={
                        "Authorization": f"Bearer {token}",
                        "Accept": "application/json",
                    },
                    verify=ca_path,
                    timeout=self._timeout,
                    allow_redirects=False,
                )
            except requests.exceptions.SSLError as exc:
                raise KubernetesError(
                    f"GET {path} failed TLS verification against the cluster CA",
                ) from exc
            except (requests.ConnectionError, requests.Timeout) as exc:
                if attempt == MAX_ATTEMPTS:
                    raise KubernetesError(f"GET {path} unreachable: {exc}") from exc
                last = type(exc).__name__
                self._sleep(backoff_seconds(attempt, None))
                continue
            if resp.status_code == 200:
                try:
                    body = resp.json()
                except ValueError as exc:
                    raise KubernetesError(
                        f"GET {path} answered HTTP 200 with a body that is not JSON",
                        status_code=200,
                    ) from exc
                if not isinstance(body, dict):
                    raise KubernetesError(
                        f"GET {path} answered HTTP 200 with a body that is not an "
                        f"object",
                        status_code=200,
                    )
                return body
            if resp.status_code in RETRY_STATUSES and attempt < MAX_ATTEMPTS:
                self._sleep(backoff_seconds(attempt, resp.headers.get("Retry-After")))
                last = f"HTTP {resp.status_code}"
                continue
            raise KubernetesError(
                f"GET {path} failed with HTTP {resp.status_code}{_message(resp)}",
                status_code=resp.status_code,
            )
        raise KubernetesError(f"GET {path} still failing after {MAX_ATTEMPTS} ({last})")


class KubernetesApi:
    """One cluster's Kubernetes API, for the lifetime of its CA file."""

    def __init__(
        self,
        client: AwsContainersClient,
        base: str,
        ca_path: str,
        token: Callable[[], str],
    ) -> None:
        self._client = client
        self._base = base
        self._ca = ca_path
        self._token = token

    def items(self, path: str) -> Iterator[Mapping[str, Any]]:
        """Every object a cluster-wide list returns, following `metadata.continue`."""
        params: dict[str, Any] = {"limit": PAGE_SIZE}
        seen: set[str] = set()
        for _ in range(MAX_PAGES):
            page = self._client._kube_get(
                self._base + path,
                params,
                # Minted per page: a presigned token lasts minutes, and a large
                # cluster's listing can outlast it, which would read as a 401.
                self._token(),
                self._ca,
            )
            yield from page.get("items") or []
            token = (page.get("metadata") or {}).get("continue")
            if not token:
                return
            if token in seen:
                raise KubernetesError(
                    f"Kubernetes GET {path} repeated a continue token"
                )
            seen.add(token)
            params["continue"] = token
        raise KubernetesError(
            f"Kubernetes GET {path} still had pages after {MAX_PAGES}"
        )


def presigned_token(sts_client: Any, cluster: str) -> str:
    """EKS's Kubernetes bearer token: a presigned STS GetCallerIdentity URL naming the
    cluster in a signed `x-k8s-aws-id` header, as `aws eks get-token` mints it.

    `sts_client` must be this cluster's own: the header handler is registered on it.
    """

    def add_cluster_header(request: Any, **_: Any) -> None:
        request.headers["x-k8s-aws-id"] = cluster

    sts_client.meta.events.register(
        "before-sign.sts.GetCallerIdentity",
        add_cluster_header,
    )
    url = sts_client.generate_presigned_url(
        "get_caller_identity",
        Params={},
        ExpiresIn=60,
        HttpMethod="GET",
    )
    encoded = base64.urlsafe_b64encode(url.encode("utf-8")).decode("utf-8")
    return "k8s-aws-v1." + encoded.rstrip("=")


def _batches(items: Sequence[str], size: int) -> Iterator[list[str]]:
    for start in range(0, len(items), size):
        yield list(items[start : start + size])


def _aws_error(service: str, region: str, e: Exception) -> Exception:
    """The client's own error for a botocore failure, with the status `failure_code`
    reads. A missing credential is the source's configuration, not AWS's answer."""
    if isinstance(e, (NoCredentialsError, PartialCredentialsError)):
        return DiscoveryConfigurationError(
            f"ECS and EKS source has no usable AWS credentials ({e}). Set the source's "
            f"access key, or give this engine credentials of its own.",
        )
    if isinstance(e, ClientError):
        error = e.response.get("Error") or {}
        code = str(error.get("Code") or "")
        message = str(error.get("Message") or "").strip()[:300]
        operation = e.operation_name
        label = "STS" if operation == "AssumeRole" else service
        status: Optional[int] = None
        if code in _REFUSED_CODES:
            status = 401
        elif code in _DENIED_CODES:
            status = 403
        return AwsContainersError(
            f"{label} {operation} in {region} failed: {code}"
            f"{': ' + message if message else ''}",
            status_code=status,
            code=code or None,
        )
    return AwsContainersError(f"{service} in {region} could not be reached: {e}")


def _message(resp: requests.Response) -> str:
    """Kubernetes' own reason from its Status object, e.g. which verb was forbidden."""
    try:
        body = resp.json()
    except ValueError:
        return ""
    if not isinstance(body, dict) or body.get("kind") != "Status":
        return ""
    message = str(body.get("message") or "").strip()
    return f": {message[:300]}" if message else ""
