"""Google Cloud's Agent Registry API, as far as listing a project's MCP servers needs it.

Two read-only lists, both `GET` on `https://agentregistry.googleapis.com/v1`, over REST
with google-auth's `AuthorizedSession`, as the Compute Engine connector reads its API:

* `projects/{project}/locations`, the locations the registry runs in.
* `projects/{project}/locations/{location}/mcpServers`, the servers registered in one.
  A list does not span locations. Google's own MCP servers are registered in `global`
  when their product's API is enabled; one someone registered is wherever they put it.

Both page with `pageSize` / `pageToken` and answer `nextPageToken`. The permissions are
`agentregistry.locations.list` and `agentregistry.mcpServers.list`, both in
`roles/agentregistry.viewer`, under the `cloud-platform.read-only` scope.

NEVER READ: a server's `interfaces`, which are its addresses, and its `attributes`. Both
are in the list response and no code here touches them.

WHAT GOOGLE ANSWERED. `AgentRegistryError.status_code` is the HTTP status, which
`failure_code` reads. Only the error's `status` and `reason`, which are Google's own
constants, are carried in the message, never its text.
"""

import logging
import re
import time
from typing import Any, Callable, Iterator, Mapping, Optional
from urllib.parse import quote

import requests
from google.auth.exceptions import RefreshError

from discovery.gcp_credentials import mark_refused_credential
from discovery.retry import MAX_ATTEMPTS, RETRY_STATUSES, backoff_seconds

AGENT_REGISTRY_API = "https://agentregistry.googleapis.com/v1"
CLOUD_PLATFORM_READONLY_SCOPE = (
    "https://www.googleapis.com/auth/cloud-platform.read-only"
)

# Where Google registers its own MCP servers, whatever else the project uses.
GLOBAL_LOCATION = "global"

PAGE_SIZE = 100
# A cap on pages so a token that never ends cannot hold a scan forever.
MAX_PAGES = 1000
# (connect, read), each page one bounded request.
REQUEST_TIMEOUT_SECONDS = (10.0, 60.0)

_CONSTANT = re.compile(r"[A-Z0-9_]{1,60}")


class AgentRegistryError(RuntimeError):
    """An Agent Registry call that failed, with the HTTP status when Google answered."""

    def __init__(self, message: str, status_code: Optional[int] = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class AgentRegistryClient:
    """One project's registry locations, and the MCP servers in a location.

    `should_stop` is asked before every request; when it answers True a listing ends as
    if Google had no more pages.
    """

    def __init__(
        self,
        session: requests.Session,
        logger: Optional[logging.Logger] = None,
        should_stop: Callable[[], bool] = lambda: False,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self._http = session
        self._log = logger or logging.getLogger(__name__)
        self._should_stop = should_stop
        self._sleep = sleep

    def locations(self, project: str) -> Iterator[str]:
        """The id of every location the registry lists for the project."""
        path = f"projects/{quote(project, safe='')}/locations"
        for location in self._list(path, "locations"):
            location_id = location.get("locationId")
            if isinstance(location_id, str) and location_id.strip():
                yield location_id.strip()

    def mcp_servers(self, project: str, location: str) -> Iterator[Mapping[str, Any]]:
        """Every MCP server registered in one location of the project."""
        path = (
            f"projects/{quote(project, safe='')}/locations/{quote(location, safe='')}"
            f"/mcpServers"
        )
        yield from self._list(path, "mcpServers")

    def _list(self, path: str, key: str) -> Iterator[Mapping[str, Any]]:
        params: dict[str, Any] = {"pageSize": PAGE_SIZE}
        seen: set[str] = set()
        for _ in range(MAX_PAGES):
            if self._should_stop():
                return
            page = self._get(path, params)
            # proto3 JSON leaves an empty list out of the answer.
            items = page.get(key, [])
            if not isinstance(items, list):
                raise AgentRegistryError(
                    f"Agent Registry GET {path} answered with a {key} that is not a "
                    f"list",
                    status_code=200,
                )
            yield from (item for item in items if isinstance(item, dict))
            token = page.get("nextPageToken")
            if not isinstance(token, str) or not token or token in seen:
                return
            seen.add(token)
            params = {"pageSize": PAGE_SIZE, "pageToken": token}
        self._log.warning(
            "Agent Registry GET %s: stopped after %s pages; the list is incomplete",
            path,
            MAX_PAGES,
        )

    def _get(self, path: str, params: Mapping[str, Any]) -> Mapping[str, Any]:
        """One GET, retried when the failure passes: every call is a read."""
        url = f"{AGENT_REGISTRY_API}/{path}"
        for attempt in range(1, MAX_ATTEMPTS + 1):
            try:
                resp = self._http.get(
                    url,
                    params=params,
                    allow_redirects=False,
                    timeout=REQUEST_TIMEOUT_SECONDS,
                )
            except RefreshError as e:
                # No token could be minted for the request. See gcp_credentials.
                mark_refused_credential(e)
                raise
            except (requests.ConnectionError, requests.Timeout) as exc:
                if attempt == MAX_ATTEMPTS:
                    # The same kind, so Test Connection reads it as the network's.
                    raise type(exc)(f"Agent Registry GET {path} unreachable") from None
                self._sleep(backoff_seconds(attempt, None))
                continue
            if resp.status_code == 200:
                try:
                    body = resp.json()
                except ValueError:
                    body = None
                if not isinstance(body, dict):
                    raise AgentRegistryError(
                        f"Agent Registry GET {path} answered HTTP 200 with a body "
                        f"that is not Google's",
                        status_code=200,
                    )
                return body
            if resp.status_code in RETRY_STATUSES and attempt < MAX_ATTEMPTS:
                self._sleep(backoff_seconds(attempt, resp.headers.get("Retry-After")))
                continue
            raise AgentRegistryError(
                f"Agent Registry GET {path} failed with HTTP {resp.status_code}"
                f"{_reason(resp)}",
                status_code=resp.status_code,
            )
        raise AssertionError("unreachable: the last attempt returns or raises")


def _reason(resp: requests.Response) -> str:
    """Google's own constants for the failure: the error's `status` and, where it gives
    one, its `reason`, e.g. `PERMISSION_DENIED, SERVICE_DISABLED`."""
    try:
        error = resp.json().get("error")
    except (ValueError, AttributeError):
        return ""
    if not isinstance(error, dict):
        return ""
    found = [error.get("status")]
    details = error.get("details")
    for detail in details if isinstance(details, list) else []:
        if isinstance(detail, dict):
            found.append(detail.get("reason"))
    constants = [c for c in found if isinstance(c, str) and _CONSTANT.fullmatch(c)]
    return f" ({', '.join(dict.fromkeys(constants))})" if constants else ""
