"""Kong Gateway's Admin API, as far as listing its MCP servers needs it.

Three read-only routes, all `GET`, all answered to an RBAC token with the default
`read-only` role:

* `/workspaces`, the workspaces. A Kong without them answers 404, and the scan reads
  its one unnamed workspace.
* `/{workspace}/plugins`, a workspace's plugins. The Admin API filters plugins by tag
  only, so every plugin is listed and the MCP ones are picked out by name.
* `/{workspace}/routes/{id}`, one route, for the name of the route an MCP server is on.

A list answers `data` and `offset`, and the next page is asked for by sending that
`offset` back; `size` is at most 1000.

A PLUGIN'S CONFIG HOLDS SECRETS. A session store's password, cloud credentials, and
whatever headers a tool sends upstream are all in `config`, which the list returns. So
a plugin is reduced to `McpPlugin` here, in the client, and nothing else of its config
leaves this module: its `mode` and its tools' names.

No error text from Kong is copied into an exception or the log.
"""

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Iterator, Optional
from urllib.parse import quote, urljoin

import requests

from discovery.retry import MAX_ATTEMPTS, RETRY_STATUSES, backoff_seconds
from discovery.siem.tls import TLSVerification, tls_session
from job_executors.discovery_scan import DiscoveryConfigurationError

# The plugin that makes a route an MCP server, or fronts one.
MCP_PLUGIN = "ai-mcp-proxy"

PAGE_SIZE = 1000
# A cap on pages so an offset that never ends cannot hold a scan forever.
MAX_PAGES = 1000
# (connect, read), each page one bounded request.
REQUEST_TIMEOUT_SECONDS = (10.0, 60.0)

WORKSPACES_PATH = "/workspaces"


class KongError(Exception):
    """An Admin API call that failed, carrying the HTTP status when Kong answered."""

    def __init__(self, message: str, status_code: Optional[int] = None) -> None:
        super().__init__(message)
        self.status_code = status_code


@dataclass(frozen=True)
class KongSettings:
    """Where the Admin API is and how to authenticate and trust it."""

    base_url: str
    admin_token: str = field(repr=False)
    ca_certificate: Optional[str] = None
    tls_verification: TLSVerification = TLSVerification.FULL


@dataclass(frozen=True)
class McpPlugin:
    """One `ai-mcp-proxy` plugin, with only what a record reads."""

    id: str
    mode: Optional[str]
    enabled: bool
    instance_name: Optional[str] = None
    route_id: Optional[str] = None
    changed: Optional[datetime] = None
    tools: tuple[str, ...] = ()


class KongClient:
    """One Kong, one token. Reads its workspaces, its MCP plugins and a route's name."""

    def __init__(
        self,
        settings: KongSettings,
        logger: Optional[logging.Logger] = None,
        session: Optional[requests.Session] = None,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self._s = settings
        self._log = logger or logging.getLogger(__name__)
        self._sleep = sleep
        self._http = session or tls_session(
            settings.ca_certificate,
            settings.tls_verification,
            "Kong",
        )

    def workspaces(self, should_stop: Callable[[], bool]) -> Optional[list[str]]:
        """Every workspace's name, or None when this Kong has no workspaces."""
        try:
            listed = list(self._list(WORKSPACES_PATH, should_stop))
        except KongError as exc:
            if exc.status_code != 404:
                raise
            return None
        return [
            name.strip()
            for name in (item.get("name") for item in listed)
            if isinstance(name, str) and name.strip()
        ]

    def mcp_plugins(
        self,
        workspace: Optional[str],
        should_stop: Callable[[], bool],
    ) -> Iterator[McpPlugin]:
        """The workspace's MCP plugins. None is a Kong without workspaces."""
        for item in self._list(f"{_prefix(workspace)}/plugins", should_stop):
            if item.get("name") != MCP_PLUGIN:
                continue
            plugin = _plugin_of(item)
            if plugin is not None:
                yield plugin

    def route_name(self, workspace: Optional[str], route_id: str) -> Optional[str]:
        """The route's name, or None when it has none or cannot be read."""
        path = f"{_prefix(workspace)}/routes/{quote(route_id, safe='')}"
        try:
            return _text(self._get(path, {}).get("name"))
        except KongError as exc:
            if exc.status_code not in (403, 404):
                raise
            return None

    def _list(
        self,
        path: str,
        should_stop: Callable[[], bool],
    ) -> Iterator[dict[str, Any]]:
        params: dict[str, Any] = {"size": PAGE_SIZE}
        seen: set[str] = set()
        for _ in range(MAX_PAGES):
            if should_stop():
                return
            body = self._get(path, params)
            data = body.get("data")
            if not isinstance(data, list):
                raise _not_kong(path)
            yield from (item for item in data if isinstance(item, dict))
            offset = body.get("offset")
            if not isinstance(offset, str) or not offset or offset in seen:
                return
            seen.add(offset)
            params = {"size": PAGE_SIZE, "offset": offset}
        self._log.warning(
            "Kong GET %s: stopped after %s pages; the list is incomplete",
            path,
            MAX_PAGES,
        )

    def _get(self, path: str, params: dict[str, Any]) -> dict[str, Any]:
        """One GET, retried when the failure passes: every route read is idempotent."""
        for attempt in range(1, MAX_ATTEMPTS + 1):
            try:
                resp = self._send(path, params)
            except (requests.ConnectionError, requests.Timeout):
                if attempt == MAX_ATTEMPTS:
                    raise
                self._sleep(backoff_seconds(attempt, None))
                continue
            if resp.status_code == 200:
                try:
                    body = resp.json()
                except ValueError:
                    body = None
                if not isinstance(body, dict):
                    raise _not_kong(path)
                return body
            if resp.status_code in RETRY_STATUSES and attempt < MAX_ATTEMPTS:
                self._sleep(backoff_seconds(attempt, resp.headers.get("Retry-After")))
                continue
            raise KongError(
                f"Kong GET {path} failed with HTTP {resp.status_code}"
                f"{_hint(resp.status_code)}",
                status_code=resp.status_code,
            )
        raise AssertionError("unreachable: the last attempt returns or raises")

    def _send(self, path: str, params: dict[str, Any]) -> requests.Response:
        try:
            return self._http.get(
                urljoin(self._s.base_url.rstrip("/") + "/", path.lstrip("/")),
                params=params,
                headers={
                    "Kong-Admin-Token": self._s.admin_token,
                    "Accept": "application/json",
                },
                # The token is a header. Refusing redirects says outright that this
                # client only ever talks to the host it was given.
                allow_redirects=False,
                timeout=REQUEST_TIMEOUT_SECONDS,
            )
        except requests.exceptions.SSLError as exc:
            raise DiscoveryConfigurationError(
                f"Kong GET {path}: TLS verification failed ({exc}). If the Admin API "
                f"uses a private CA, set ca_certificate; if its certificate does not "
                f"name the host the engine uses, set tls_verification to ca_only with "
                f"that ca_certificate.",
            ) from exc
        except (requests.ConnectionError, requests.Timeout) as exc:
            # Re-raised as the same kind so Test Connection still reads it as the
            # network failure it is.
            raise type(exc)(
                f"Kong GET {path} unreachable: {exc}. A self-hosted Admin API needs an "
                f"engine inside its network.",
            ) from exc


def _prefix(workspace: Optional[str]) -> str:
    return f"/{quote(workspace, safe='')}" if workspace else ""


def _plugin_of(item: dict[str, Any]) -> Optional[McpPlugin]:
    """The plugin reduced to what a record reads; see the module docstring."""
    plugin_id = _text(item.get("id"))
    if plugin_id is None:
        return None
    config = item.get("config")
    config = config if isinstance(config, dict) else {}
    tools = config.get("tools")
    names = {
        name
        for name in (
            _text(tool.get("name"))
            for tool in (tools if isinstance(tools, list) else [])
            if isinstance(tool, dict)
        )
        if name is not None
    }
    route = item.get("route")
    return McpPlugin(
        id=plugin_id,
        mode=_text(config.get("mode")),
        enabled=item.get("enabled") is not False,
        instance_name=_text(item.get("instance_name")),
        route_id=_text(route.get("id")) if isinstance(route, dict) else None,
        changed=_epoch(item.get("updated_at")) or _epoch(item.get("created_at")),
        tools=tuple(sorted(names)),
    )


def _epoch(value: Any) -> Optional[datetime]:
    """A Kong timestamp, Unix seconds, as aware UTC."""
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value <= 0:
        return None
    try:
        return datetime.fromtimestamp(value, tz=timezone.utc)
    except (OverflowError, OSError, ValueError):
        return None


def _text(value: Any) -> Optional[str]:
    if not isinstance(value, str):
        return None
    return value.strip() or None


def _not_kong(path: str) -> KongError:
    return KongError(
        f"Kong GET {path} answered HTTP 200 with a body that is not the Admin API's "
        f"answer. Check that base_url is Kong's Admin API, not its proxy port, Kong "
        f"Manager, or a login page in front of it.",
        status_code=200,
    )


def _hint(status: int) -> str:
    if status == 401:
        return ". Kong rejected admin_token: it may be wrong, or its admin removed."
    if status == 403:
        return (
            ". The token's admin may not read this: give it the read-only role in "
            "every workspace to be scanned."
        )
    return ""
