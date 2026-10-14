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
rather than adding google-cloud-compute for it.

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

# The collector's reporter writes every key under this one namespace.
NAMESPACE = "arthur/"

# Instance or project metadata that turns guest attributes on. Off unless set.
GUEST_ATTRIBUTES_FLAG = "enable-guest-attributes"

# The listing's own maximum.
PAGE_SIZE = 500

# Google's reasons for a 403 that is a rate limit, not a refusal.
_RATE_LIMIT_REASONS = frozenset(
    {"rateLimitExceeded", "userRateLimitExceeded", "RATE_LIMIT_EXCEEDED"},
)


class ComputeEngineError(RuntimeError):
    """A Compute Engine call failed in a way retrying will not fix."""

    def __init__(self, message: str, status_code: Optional[int] = None) -> None:
        super().__init__(message)
        self.status_code = status_code


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

    def project_guest_attributes_flag(self, project: str) -> Optional[str]:
        """The project's `enable-guest-attributes` metadata, or None when unset."""
        body = self._get(f"{COMPUTE_API}/projects/{_segment(project)}", {}) or {}
        return _metadata_value(
            body.get("commonInstanceMetadata"),
            GUEST_ATTRIBUTES_FLAG,
        )

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
        path = url.removeprefix(COMPUTE_API)

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
                        f"Compute Engine GET {path} unreachable: {exc}",
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
                        f"Compute Engine GET {path} answered HTTP 200 with a body "
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
                f"Compute Engine GET {path} failed with HTTP {resp.status_code}"
                f"{_google_message(resp)}",
                # A rate limit Google sent as 403 still says 429 once retries run out:
                # read as a 403, it would end the scan as permission denied, and Test
                # Connection would call it the same.
                status_code=429 if rate_limited else resp.status_code,
            )

        raise ComputeEngineError(
            f"Compute Engine GET {path} still failing after {MAX_ATTEMPTS} attempts "
            f"({last})",
        )


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
    )


def _metadata_value(metadata: Optional[Mapping[str, Any]], key: str) -> Optional[str]:
    """One key's value from Compute Engine's `{"items": [{"key", "value"}]}` metadata.

    Only the one key is looked at. Metadata also carries startup scripts and whatever
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


def _is_rate_limit(resp: requests.Response) -> bool:
    error = _error(resp)
    reasons = {str(e.get("reason")) for e in error.get("errors") or []}
    reasons |= {str(d.get("reason")) for d in error.get("details") or []}
    return bool(reasons & _RATE_LIMIT_REASONS)


def _google_message(resp: requests.Response) -> str:
    """Google's own reason, e.g. which permission was missing on which project.

    Safe to carry: an API error names the request's resource and the missing
    permission, and the credential travels in a header Google does not echo.
    """
    message = str(_error(resp).get("message") or "").strip()
    return f": {message[:300]}" if message else ""
