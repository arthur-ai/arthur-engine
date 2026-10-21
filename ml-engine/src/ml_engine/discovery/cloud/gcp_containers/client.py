"""Reading container workloads out of Cloud Run, GKE and the Kubernetes API.

Read-only, list calls only. Nothing is deployed, exec'd into or written back, and no
call reads a container's logs, a Secret, a ConfigMap or an execution's output.

FIVE GOOGLE ENDPOINTS AND ONE KUBERNETES ONE, NO SDK. Over REST with google-auth's
`AuthorizedSession`, which is already a dependency, as Compute Engine does:

- Cloud Run v2 `projects/P/locations/-/services`: every service, across all regions.
- Cloud Run v1 `projects/P/locations`: the regions Cloud Run serves, because v2 jobs
  refuse the `-` wildcard (checked live: HTTP 400) and must be listed region by region.
- Cloud Run v2 `projects/P/locations/R/jobs`: one region's jobs.
- GKE v1 `projects/P/locations/-/clusters`: every cluster, with its endpoint, CA,
  Workload Identity pool and node pools' service accounts.
- Resource Manager v1 `projects/P`: the project NUMBER, read only when a workload runs
  as the Compute Engine default service account, whose email is built from it.
- The cluster's own Kubernetes API at its endpoint, verified against the cluster CA
  GKE returned, authorised by the same Google OAuth token.

THE KUBERNETES API IS ASKED FOR CONTROLLERS, NOT PODS. A pod's name carries a
ReplicaSet hash or a Job's timestamp and changes every rollout; the Deployment,
StatefulSet, DaemonSet or CronJob that owns it does not. Pods and Jobs are read only
for the ones nothing owns (`kubectl run`, a hand-made Job), which are their own
workload.

ENV VALUES ARE NEVER KEPT. A pod template carries its containers' `env`, and the
listing returns it whatever is asked for. Only the image, the service account name and
timestamps are read off each object; nothing else is copied, logged or returned.
"""

import base64
import logging
import os
import tempfile
import time
from contextlib import contextmanager
from typing import Any, Callable, Iterator, Mapping, Optional
from urllib.parse import quote

import requests
from google.auth.exceptions import RefreshError

from discovery.gcp_credentials import mark_refused_credential
from discovery.retry import MAX_ATTEMPTS, RETRY_STATUSES, backoff_seconds

RUN_V1_API = "https://run.googleapis.com/v1"
RUN_V2_API = "https://run.googleapis.com/v2"
CONTAINER_API = "https://container.googleapis.com/v1"
RESOURCE_MANAGER_API = "https://cloudresourcemanager.googleapis.com/v1"

PAGE_SIZE = 500

# A listing that keeps handing out page tokens past this is treated as broken rather
# than followed forever.
MAX_PAGES = 1000

# Google's reasons for a 403 that is a rate limit, not a refusal.
_RATE_LIMIT_REASONS = frozenset(
    {"rateLimitExceeded", "userRateLimitExceeded", "RATE_LIMIT_EXCEEDED"},
)


class GcpContainersError(RuntimeError):
    """A Cloud Run, GKE or Kubernetes call failed in a way retrying will not fix."""

    def __init__(self, message: str, status_code: Optional[int] = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class ScanStopped(Exception):
    """The scan's stop check fired before a call. Not a failure."""


class GcpContainersClient:
    """One scan's Google and Kubernetes reads, one call at a time."""

    def __init__(
        self,
        session: requests.Session,
        logger: Optional[logging.Logger] = None,
        should_stop: Callable[[], bool] = lambda: False,
        sleep: Any = time.sleep,
        timeout_seconds: float = 30.0,
    ) -> None:
        self._http = session
        self._log = logger or logging.getLogger(__name__)
        self._should_stop = should_stop
        self._sleep = sleep
        self._timeout = timeout_seconds

    # --- Cloud Run ----------------------------------------------------------------

    def cloud_run_services(self, project: str) -> Iterator[Mapping[str, Any]]:
        """Every Cloud Run service in the project, across all regions."""
        url = f"{RUN_V2_API}/projects/{_segment(project)}/locations/-/services"
        yield from self._google_pages(url, "services")

    def cloud_run_regions(self, project: str) -> list[str]:
        """The regions Cloud Run serves for this project, by id (`us-east4`)."""
        url = f"{RUN_V1_API}/projects/{_segment(project)}/locations"
        return [
            str(loc.get("locationId") or "")
            for loc in self._google_pages(url, "locations")
            if loc.get("locationId")
        ]

    def cloud_run_jobs(self, project: str, region: str) -> Iterator[Mapping[str, Any]]:
        """One region's Cloud Run jobs. Never their executions."""
        url = (
            f"{RUN_V2_API}/projects/{_segment(project)}"
            f"/locations/{_segment(region)}/jobs"
        )
        yield from self._google_pages(url, "jobs")

    # --- GKE ----------------------------------------------------------------------

    def gke_clusters(self, project: str) -> list[Mapping[str, Any]]:
        """Every GKE cluster in the project, in every location.

        The listing is not paged. Zones it could not reach are logged, because the
        clusters in them are missing from this scan and nothing else would say so.
        """
        url = f"{CONTAINER_API}/projects/{_segment(project)}/locations/-/clusters"
        body = self._get(url, {}) or {}
        missing = body.get("missingZones") or []
        if missing:
            self._log.warning(
                "GKE could not list clusters in %s location(s) of project %s (%s); "
                "workloads there are missing from this scan",
                len(missing),
                project,
                ", ".join(str(z) for z in missing),
            )
        return list(body.get("clusters") or [])

    def project_number(self, project: str) -> str:
        """The project's number, for the default compute service account's email."""
        body = self._get(f"{RESOURCE_MANAGER_API}/projects/{_segment(project)}", {})
        number = str((body or {}).get("projectNumber") or "")
        if not number:
            raise GcpContainersError(
                f"Resource Manager returned no projectNumber for {project}",
                status_code=200,
            )
        return number

    @contextmanager
    def kubernetes(self, cluster: Mapping[str, Any]) -> Iterator["KubernetesApi"]:
        """The cluster's Kubernetes API, trusting only the CA GKE says it has.

        The CA is written to a temporary file because that is the form requests takes
        it in, and removed when the cluster is done.
        """
        endpoint = str(cluster.get("endpoint") or "")
        ca_b64 = str(
            (cluster.get("masterAuth") or {}).get("clusterCaCertificate") or ""
        )
        if not endpoint or not ca_b64:
            raise GcpContainersError(
                "GKE returned no endpoint or cluster CA for the cluster",
            )
        try:
            ca = base64.b64decode(ca_b64, validate=True)
        except ValueError as exc:
            raise GcpContainersError(
                "GKE returned a cluster CA that is not base64",
            ) from exc
        fd, path = tempfile.mkstemp(prefix="gke-ca-", suffix=".pem")
        try:
            with os.fdopen(fd, "wb") as f:
                f.write(ca)
            yield KubernetesApi(self, f"https://{endpoint}", path)
        finally:
            os.unlink(path)

    # --- transport ----------------------------------------------------------------

    def _google_pages(self, url: str, key: str) -> Iterator[Mapping[str, Any]]:
        params: dict[str, Any] = {"pageSize": PAGE_SIZE}
        seen: set[str] = set()
        for _ in range(MAX_PAGES):
            page = self._get(url, params) or {}
            yield from page.get(key) or []
            token = page.get("nextPageToken")
            if not token:
                return
            if token in seen:
                self._log.warning(
                    "%s repeated a page token; the listing is incomplete",
                    _path(url),
                )
                return
            seen.add(token)
            params["pageToken"] = token
        self._log.warning(
            "%s still had pages after %s; the listing is incomplete",
            _path(url),
            MAX_PAGES,
        )

    def _get(
        self,
        url: str,
        params: Mapping[str, Any],
        verify: Optional[str] = None,
    ) -> Optional[dict[str, Any]]:
        last: Optional[str] = None
        path = _path(url)
        kwargs: dict[str, Any] = {
            "params": params,
            "timeout": self._timeout,
            "allow_redirects": False,
        }
        if verify is not None:
            kwargs["verify"] = verify

        for attempt in range(1, MAX_ATTEMPTS + 1):
            if self._should_stop():
                raise ScanStopped()
            try:
                resp = self._http.get(url, **kwargs)
            except RefreshError as e:
                # No token could be minted for the request. See gcp_credentials.
                mark_refused_credential(e)
                raise
            except requests.exceptions.SSLError as exc:
                # A cluster CA that does not verify its own endpoint is not transient.
                raise GcpContainersError(
                    f"GET {path} failed TLS verification against the cluster CA",
                ) from exc
            except (requests.ConnectionError, requests.Timeout) as exc:
                if attempt == MAX_ATTEMPTS:
                    raise GcpContainersError(f"GET {path} unreachable: {exc}") from exc
                last = type(exc).__name__
                self._sleep(backoff_seconds(attempt, None))
                continue

            if resp.status_code == 200:
                try:
                    body: dict[str, Any] = resp.json()
                except ValueError as exc:
                    raise GcpContainersError(
                        f"GET {path} answered HTTP 200 with a body that is not JSON",
                        status_code=200,
                    ) from exc
                if not isinstance(body, dict):
                    raise GcpContainersError(
                        f"GET {path} answered HTTP 200 with a body that is not an "
                        f"object",
                        status_code=200,
                    )
                return body

            rate_limited = resp.status_code == 403 and _is_rate_limit(resp)
            retryable = resp.status_code in RETRY_STATUSES or rate_limited
            if retryable and attempt < MAX_ATTEMPTS:
                self._sleep(backoff_seconds(attempt, resp.headers.get("Retry-After")))
                last = f"HTTP {resp.status_code}"
                continue

            raise GcpContainersError(
                f"GET {path} failed with HTTP {resp.status_code}{_message(resp)}",
                status_code=429 if rate_limited else resp.status_code,
            )

        raise GcpContainersError(
            f"GET {path} still failing after {MAX_ATTEMPTS} attempts ({last})",
        )


class KubernetesApi:
    """One cluster's Kubernetes API, for the lifetime of its CA file."""

    def __init__(self, client: GcpContainersClient, base: str, ca_path: str) -> None:
        self._client = client
        self._base = base
        self._ca = ca_path

    def items(self, path: str) -> Iterator[Mapping[str, Any]]:
        """Every object a cluster-wide list returns, following `metadata.continue`."""
        params: dict[str, Any] = {"limit": PAGE_SIZE}
        seen: set[str] = set()
        for _ in range(MAX_PAGES):
            page = self._client._get(self._base + path, params, verify=self._ca) or {}
            yield from page.get("items") or []
            token = (page.get("metadata") or {}).get("continue")
            if not token:
                return
            if token in seen:
                raise GcpContainersError(
                    f"Kubernetes GET {path} repeated a continue token",
                )
            seen.add(token)
            params["continue"] = token
        raise GcpContainersError(
            f"Kubernetes GET {path} still had pages after {MAX_PAGES}",
        )


def _segment(value: str) -> str:
    """One path segment, quoted. A domain-scoped project id keeps its colon."""
    return quote(value, safe=":")


def _path(url: str) -> str:
    """The URL without its host, which is what a log line needs to name the call."""
    return "/" + url.split("://", 1)[-1].split("/", 1)[-1]


def _error(resp: requests.Response) -> Mapping[str, Any]:
    try:
        body = resp.json()
    except ValueError:
        return {}
    if not isinstance(body, dict):
        return {}
    error = body.get("error")
    if isinstance(error, dict):
        return error
    # Kubernetes' own Status object.
    return body if body.get("kind") == "Status" else {}


def _is_rate_limit(resp: requests.Response) -> bool:
    error = _error(resp)
    reasons = {str(e.get("reason")) for e in error.get("errors") or []}
    reasons |= {str(d.get("reason")) for d in error.get("details") or []}
    return bool(reasons & _RATE_LIMIT_REASONS)


def _message(resp: requests.Response) -> str:
    """Google's or Kubernetes' own reason, e.g. which permission was missing.

    Safe to carry: an API error names the request's resource and the missing
    permission, and the credential travels in a header neither echoes.
    """
    message = str(_error(resp).get("message") or "").strip()
    return f": {message[:300]}" if message else ""
