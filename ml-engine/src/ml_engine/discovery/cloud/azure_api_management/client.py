"""Azure Resource Manager, as far as listing API Management's MCP servers needs it.

Three read-only lists, all `GET` on `https://management.azure.com`:

* `/subscriptions/{id}/providers/Microsoft.ApiManagement/service`, the subscription's
  API Management services.
* `{service}/apis`, a service's APIs. An MCP server is an API whose `properties.type`
  is `mcp`, which only API version `2025-09-01-preview` and later return, so that
  version is pinned on every API Management call. The reference lists no `type` among
  the fields `$filter` takes, so every API is listed and the type is read here.
* `{api}/tools`, the tools of an MCP server API Management built from a REST API. A
  server it only passes through to has none here: its tools are the upstream's.

`value` holds a page and `nextLink` the next page's whole URL. A `nextLink` is followed
only when it is on the host above: the request carries the token.

PUBLIC AZURE ONLY. The host and the token's scope are the public cloud's. A sovereign
cloud means its Resource Manager host, its scope and its Entra authority together.

NEVER READ: an API's `serviceUrl` and `mcpProperties`, which are the address of what is
behind it, and its policies, which can hold credentials. They are in the list response
or one call away, and no code here touches them.

WHAT AZURE ANSWERED. `ArmError.status_code` is Resource Manager's HTTP status, which
`failure_code` reads. Only its `error.code` is carried in the message, never its text.
"""

import logging
import re
import time
from typing import Any, Callable, Iterator, Mapping, Optional
from urllib.parse import quote, urlsplit

import requests
from azure.core.credentials import TokenCredential

from discovery.retry import MAX_ATTEMPTS, RETRY_STATUSES, backoff_seconds

ARM_HOST = "management.azure.com"
ARM_SCOPE = "https://management.azure.com/.default"

# The first version whose API list says which APIs are MCP servers.
API_VERSION = "2025-09-01-preview"
MCP_API_TYPE = "mcp"

# (connect, read), each page one bounded request.
REQUEST_TIMEOUT_SECONDS = (10.0, 60.0)
# A cap on pages so a `nextLink` that never ends cannot hold a scan forever.
MAX_PAGES = 1000

_SERVICE_ID = re.compile(
    r"^/subscriptions/(?P<subscription>[0-9a-f-]{36})/resourceGroups/(?P<group>[^/]+)"
    r"/providers/Microsoft\.ApiManagement/service/(?P<service>[^/]+)$",
    re.IGNORECASE,
)


class ArmError(RuntimeError):
    """A Resource Manager call that failed, with the HTTP status when it answered."""

    def __init__(self, message: str, status_code: Optional[int] = None) -> None:
        super().__init__(message)
        self.status_code = status_code


def service_path(subscription_id: str, service_id: object) -> Optional[str]:
    """A listed service's own path, or None when its id is not one in the subscription.

    Every later call is built on it, so it is rebuilt from its parts, never sent back
    as Azure wrote it.
    """
    match = _SERVICE_ID.match(service_id) if isinstance(service_id, str) else None
    if match is None or match["subscription"].lower() != subscription_id:
        return None
    return (
        f"/subscriptions/{subscription_id}/resourceGroups/{quote(match['group'], safe='')}"
        f"/providers/Microsoft.ApiManagement/service/{quote(match['service'], safe='')}"
    )


class ApiManagementClient:
    """One subscription's API Management services, their APIs and an API's tools.

    `should_stop` is asked before every request; when it answers True a listing ends as
    if Azure had no more pages.
    """

    def __init__(
        self,
        credential: TokenCredential,
        logger: Optional[logging.Logger] = None,
        session: Optional[requests.Session] = None,
        should_stop: Callable[[], bool] = lambda: False,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self._credential = credential
        self._log = logger or logging.getLogger(__name__)
        self._http = session or requests.Session()
        self._should_stop = should_stop
        self._sleep = sleep

    def services(self, subscription_id: str) -> Iterator[Mapping[str, Any]]:
        yield from self._list(
            f"/subscriptions/{subscription_id}/providers/Microsoft.ApiManagement"
            f"/service",
        )

    def apis(self, service: str) -> Iterator[Mapping[str, Any]]:
        """Every API of the service at `service`, a path from `service_path`."""
        yield from self._list(f"{service}/apis")

    def tools(self, service: str, api_name: str) -> Iterator[Mapping[str, Any]]:
        yield from self._list(f"{service}/apis/{quote(api_name, safe='')}/tools")

    def _list(self, path: str) -> Iterator[Mapping[str, Any]]:
        url = f"https://{ARM_HOST}{path}?api-version={API_VERSION}"
        seen: set[str] = set()
        for _ in range(MAX_PAGES):
            if self._should_stop():
                return
            seen.add(url)
            body = self._get(url, path)
            items = body.get("value")
            if not isinstance(items, list):
                raise ArmError(
                    f"Azure GET {path} answered without a value list",
                    status_code=200,
                )
            yield from (item for item in items if isinstance(item, dict))
            link = body.get("nextLink")
            if not isinstance(link, str) or not link or link in seen:
                return
            parts = urlsplit(link)
            if parts.scheme != "https" or parts.hostname != ARM_HOST:
                raise ArmError(
                    f"Azure GET {path} named a next page that is not on {ARM_HOST}; "
                    f"not followed",
                    status_code=200,
                )
            url = link
        self._log.warning(
            "Azure GET %s: stopped after %s pages; the list is incomplete",
            path,
            MAX_PAGES,
        )

    def _get(self, url: str, path: str) -> Mapping[str, Any]:
        """One GET, retried when the failure passes: every call is a read."""
        for attempt in range(1, MAX_ATTEMPTS + 1):
            token = self._credential.get_token(ARM_SCOPE).token
            try:
                resp = self._http.get(
                    url,
                    headers={
                        "Authorization": f"Bearer {token}",
                        "Accept": "application/json",
                    },
                    allow_redirects=False,
                    timeout=REQUEST_TIMEOUT_SECONDS,
                )
            except (requests.ConnectionError, requests.Timeout) as exc:
                if attempt == MAX_ATTEMPTS:
                    # The same kind, so Test Connection reads it as the network's.
                    raise type(exc)(f"Azure GET {path} unreachable") from None
                self._sleep(backoff_seconds(attempt, None))
                continue
            if resp.status_code == 200:
                try:
                    body = resp.json()
                except ValueError:
                    body = None
                if not isinstance(body, dict):
                    raise ArmError(
                        f"Azure GET {path} answered HTTP 200 with a body that is not "
                        f"Resource Manager's",
                        status_code=200,
                    )
                return body
            if resp.status_code in RETRY_STATUSES and attempt < MAX_ATTEMPTS:
                self._sleep(backoff_seconds(attempt, resp.headers.get("Retry-After")))
                continue
            raise ArmError(
                f"Azure GET {path} failed with HTTP {resp.status_code}"
                f"{_error_code(resp)}",
                status_code=resp.status_code,
            )
        raise AssertionError("unreachable: the last attempt returns or raises")


def _error_code(resp: requests.Response) -> str:
    """Resource Manager's own code for the failure, e.g. `AuthorizationFailed`."""
    try:
        code = (resp.json().get("error") or {}).get("code")
    except (ValueError, AttributeError):
        return ""
    if isinstance(code, str) and re.fullmatch(r"[A-Za-z0-9_.]{1,80}", code):
        return f" ({code})"
    return ""
