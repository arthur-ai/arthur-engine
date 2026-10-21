"""Reading VMs and their guest attributes out of the Compute Engine API.

Read-only, and outbound only. Nothing is installed on a VM, nothing connects to one, and
nothing is written back: each VM writes its own `arthur/` guest attributes through its
metadata server (`integrations/endpoint-ai-discovery/docs/mdm/gce.md`), and this reads
them through the same public API `gcloud compute instances get-guest-attributes` does.
The privileges are `compute.instances.list`, `compute.instances.getGuestAttributes` and
`compute.projects.get`, all in `roles/compute.viewer`.

THREE CALLS, NO SDK. One `aggregated/instances` listing per project, paged; one project
read for its metadata; one `getGuestAttributes` per in-scope VM. That is small enough to
make over REST with google-auth's `AuthorizedSession`, which is already a dependency,
rather than adding google-cloud-compute for it. A source scoped to an organization or a
folder adds Resource Manager's two listings, `projects` and `folders`, under the same
session: `resourcemanager.projects.list` and `resourcemanager.folders.list` on the parent,
both in `roles/browser`, and a token carrying `CLOUD_PLATFORM_READONLY_SCOPE`.

ONE CALL AT A TIME. A guest-attribute read is a call per VM, and Compute Engine's read
quota is per project per minute. Sequential calls pace themselves well inside it, and a
429 -- or the 403 Google sometimes sends for the same thing -- backs off rather than
failing the scan.
"""

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Iterator, Mapping, Optional
from urllib.parse import quote

import requests
from google.auth.exceptions import RefreshError

from discovery.gcp_credentials import mark_refused_credential
from discovery.retry import MAX_ATTEMPTS, RETRY_STATUSES, backoff_seconds

COMPUTE_API = "https://compute.googleapis.com/compute/v1"
COMPUTE_READONLY_SCOPE = "https://www.googleapis.com/auth/compute.readonly"
RESOURCE_MANAGER_API = "https://cloudresourcemanager.googleapis.com/v3"
# Resource Manager is outside the compute scope. Still read-only: a scope narrows what a
# token may do, and IAM says what the account may do at all.
CLOUD_PLATFORM_READONLY_SCOPE = (
    "https://www.googleapis.com/auth/cloud-platform.read-only"
)

# Google's reason on the 403 for a project where the Compute Engine API is not enabled.
# No VM can exist in such a project, so it is not a refusal.
API_NOT_ENABLED_REASON = "accessNotConfigured"

# The collector's reporter writes every key under this one namespace.
NAMESPACE = "arthur/"

# Instance or project metadata that turns guest attributes on. Off unless set.
GUEST_ATTRIBUTES_FLAG = "enable-guest-attributes"
# Instance or project metadata without which the OS Config agent acts on no policy, so
# nothing installs the collector. Off unless set.
OSCONFIG_FLAG = "enable-osconfig"
# The two keys a scan reads, and the only ones: metadata also carries startup scripts.
METADATA_FLAGS = (GUEST_ATTRIBUTES_FLAG, OSCONFIG_FLAG)

# The listing's own maximum.
PAGE_SIZE = 500
# Resource Manager's.
RESOURCE_MANAGER_PAGE_SIZE = 100

# Google's reasons for a 403 that is a rate limit, not a refusal.
_RATE_LIMIT_REASONS = frozenset(
    {"rateLimitExceeded", "userRateLimitExceeded", "RATE_LIMIT_EXCEEDED"},
)


class ComputeEngineError(RuntimeError):
    """A Compute Engine or Resource Manager call failed in a way retrying will not fix.

    `reason` is Google's own reason on the error, where there is one, such as
    `API_NOT_ENABLED_REASON`.
    """

    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        reason: Optional[str] = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.reason = reason


@dataclass(frozen=True)
class Instance:
    """One VM as the listing returned it, with only what a scan reads."""

    project: str
    zone: str
    id: str
    name: str
    status: str
    labels: Mapping[str, str] = field(default_factory=dict)
    guest_attributes_flag: Optional[str] = None
    """The VM's own `enable-guest-attributes` metadata, or None when it has none and
    the project's applies."""
    osconfig_flag: Optional[str] = None
    """The VM's own `enable-osconfig` metadata, or None when the project's applies."""


class ComputeEngineClient:
    """Lists a project's VMs and reads each one's `arthur/` guest attributes."""

    def __init__(
        self,
        session: requests.Session,
        logger: Optional[logging.Logger] = None,
        sleep: Any = time.sleep,
        timeout_seconds: float = 30.0,
    ) -> None:
        self._http = session
        self._log = logger or logging.getLogger(__name__)
        self._sleep = sleep
        self._timeout = timeout_seconds

    def instances(self, project: str) -> Iterator[Instance]:
        """Every VM in the project, across all zones, a page at a time.

        `returnPartialSuccess` keeps one unreachable zone from failing the listing; the
        zones it could not reach are logged, because the VMs in them are missing from
        this scan and nothing else would say so.
        """
        url = f"{COMPUTE_API}/projects/{_segment(project)}/aggregated/instances"
        params: dict[str, Any] = {
            "maxResults": PAGE_SIZE,
            "returnPartialSuccess": "true",
        }
        while True:
            page = self._get(url, params) or {}
            unreachable = page.get("unreachables") or []
            if unreachable:
                self._log.warning(
                    "Compute Engine could not list VMs in %s of project %s (%s); VMs "
                    "there are missing from this scan",
                    len(unreachable),
                    project,
                    ", ".join(str(u) for u in unreachable),
                )
            for scoped in (page.get("items") or {}).values():
                for raw in scoped.get("instances") or []:
                    yield _instance(project, raw)
            token = page.get("nextPageToken")
            if not token:
                return
            params["pageToken"] = token

    def projects_under(self, parent: str) -> Iterator[str]:
        """The ID of every active project under `parent`, folders walked depth first.

        `parent` is `organizations/N` or `folders/N`. Resource Manager lists a parent's
        direct children only, so each folder found is walked in turn. A project being
        deleted is left out: nothing in it can be read.
        """
        for project in self._listed(
            f"{RESOURCE_MANAGER_API}/projects",
            parent,
            "projects",
        ):
            if project.get("state") == "ACTIVE" and project.get("projectId"):
                yield str(project["projectId"])
        for folder in self._listed(
            f"{RESOURCE_MANAGER_API}/folders",
            parent,
            "folders",
        ):
            if folder.get("state", "ACTIVE") == "ACTIVE" and folder.get("name"):
                yield from self.projects_under(str(folder["name"]))

    def _listed(self, url: str, parent: str, key: str) -> Iterator[Mapping[str, Any]]:
        """One Resource Manager listing under `parent`, every page."""
        params: dict[str, Any] = {
            "parent": parent,
            "pageSize": RESOURCE_MANAGER_PAGE_SIZE,
        }
        while True:
            page = self._get(url, params) or {}
            yield from page.get(key) or []
            token = page.get("nextPageToken")
            if not token:
                return
            params["pageToken"] = token

    def project_flags(self, project: str) -> Mapping[str, Optional[str]]:
        """The project's `METADATA_FLAGS`, each None when unset. One read for both."""
        body = self._get(f"{COMPUTE_API}/projects/{_segment(project)}", {}) or {}
        metadata = body.get("commonInstanceMetadata")
        return {key: _metadata_value(metadata, key) for key in METADATA_FLAGS}

    def guest_attributes(self, instance: Instance) -> Optional[dict[str, str]]:
        """The VM's `arthur/` values as `namespace/key` -> value, or None when it has none.

        None is a VM nothing was ever written for: Compute Engine answers 404 for a
        namespace that does not exist.
        """
        url = (
            f"{COMPUTE_API}/projects/{_segment(instance.project)}"
            f"/zones/{_segment(instance.zone)}"
            f"/instances/{_segment(instance.name)}/getGuestAttributes"
        )
        body = self._get(url, {"queryPath": NAMESPACE}, missing_ok=True)
        if body is None:
            return None
        items = (body.get("queryValue") or {}).get("items") or []
        return {
            f"{item.get('namespace', '')}/{item.get('key', '')}": str(
                item.get("value") or "",
            )
            for item in items
        }

    # --- transport ----------------------------------------------------------------

    def _get(
        self,
        url: str,
        params: Mapping[str, Any],
        missing_ok: bool = False,
    ) -> Optional[dict[str, Any]]:
        last: Optional[str] = None
        api, path = _api_and_path(url)

        for attempt in range(1, MAX_ATTEMPTS + 1):
            try:
                resp = self._http.get(url, params=params, timeout=self._timeout)
            except RefreshError as e:
                # No token could be minted for the request. See gcp_credentials.
                mark_refused_credential(e)
                raise
            except (requests.ConnectionError, requests.Timeout) as exc:
                if attempt == MAX_ATTEMPTS:
                    raise ComputeEngineError(
                        f"{api} GET {path} unreachable: {exc}",
                    ) from exc
                last = type(exc).__name__
                self._sleep(backoff_seconds(attempt, None))
                continue

            if resp.status_code == 200:
                try:
                    body: dict[str, Any] = resp.json()
                except ValueError as exc:
                    # A proxy's page or a cut-off answer. Raised as this type so one
                    # VM's read is skipped like any other, rather than ending the scan.
                    raise ComputeEngineError(
                        f"{api} GET {path} answered HTTP 200 with a body "
                        f"that is not JSON",
                    ) from exc
                return body

            if resp.status_code == 404 and missing_ok:
                return None

            rate_limited = resp.status_code == 403 and _is_rate_limit(resp)
            retryable = resp.status_code in RETRY_STATUSES or rate_limited
            if retryable and attempt < MAX_ATTEMPTS:
                self._sleep(backoff_seconds(attempt, resp.headers.get("Retry-After")))
                last = f"HTTP {resp.status_code}"
                continue

            raise ComputeEngineError(
                f"{api} GET {path} failed with HTTP {resp.status_code}"
                f"{_google_message(resp)}",
                # A rate limit Google sent as 403 still says 429 once retries run out:
                # read as a 403, it would end the scan as permission denied, and Test
                # Connection would call it the same.
                status_code=429 if rate_limited else resp.status_code,
                reason=_google_reason(resp),
            )

        raise ComputeEngineError(
            f"{api} GET {path} still failing after {MAX_ATTEMPTS} attempts "
            f"({last})",
        )


def _api_and_path(url: str) -> tuple[str, str]:
    """Which API a URL calls, and its path there, for what an error says."""
    if url.startswith(RESOURCE_MANAGER_API):
        return "Resource Manager", url.removeprefix(RESOURCE_MANAGER_API)
    return "Compute Engine", url.removeprefix(COMPUTE_API)


def _segment(value: str) -> str:
    """One path segment, quoted. A domain-scoped project id keeps its colon."""
    return quote(value, safe=":")


def _instance(project: str, raw: Mapping[str, Any]) -> Instance:
    """The listing's VM, with its zone taken from the zone URL it carries."""
    return Instance(
        project=project,
        zone=str(raw.get("zone") or "").rsplit("/", 1)[-1],
        id=str(raw.get("id") or ""),
        name=str(raw.get("name") or ""),
        status=str(raw.get("status") or ""),
        labels={str(k): str(v) for k, v in (raw.get("labels") or {}).items()},
        guest_attributes_flag=_metadata_value(
            raw.get("metadata"),
            GUEST_ATTRIBUTES_FLAG,
        ),
        osconfig_flag=_metadata_value(raw.get("metadata"), OSCONFIG_FLAG),
    )


def _metadata_value(metadata: Optional[Mapping[str, Any]], key: str) -> Optional[str]:
    """One key's value from Compute Engine's `{"items": [{"key", "value"}]}` metadata.

    Only the named key is looked at. Metadata also carries startup scripts and whatever
    else a project keeps there, and none of it is read, kept or logged.
    """
    for item in (metadata or {}).get("items") or []:
        if item.get("key") == key:
            return str(item.get("value") or "")
    return None


def _error(resp: requests.Response) -> Mapping[str, Any]:
    try:
        body = resp.json()
    except ValueError:
        return {}
    error = body.get("error") if isinstance(body, dict) else None
    return error if isinstance(error, dict) else {}


def _reasons(resp: requests.Response) -> list[str]:
    """Google's reasons on an error, in the order it gave them."""
    error = _error(resp)
    found = [str(e.get("reason")) for e in error.get("errors") or [] if e.get("reason")]
    found += [
        str(d.get("reason")) for d in error.get("details") or [] if d.get("reason")
    ]
    return found


def _is_rate_limit(resp: requests.Response) -> bool:
    return bool(set(_reasons(resp)) & _RATE_LIMIT_REASONS)


def _google_reason(resp: requests.Response) -> Optional[str]:
    reasons = _reasons(resp)
    return reasons[0] if reasons else None


def _google_message(resp: requests.Response) -> str:
    """Google's own reason, e.g. which permission was missing on which project.

    Safe to carry: an API error names the request's resource and the missing
    permission, and the credential travels in a header Google does not echo.
    """
    message = str(_error(resp).get("message") or "").strip()
    return f": {message[:300]}" if message else ""
