"""Wiz's GraphQL API, as far as a discovery scan needs it.

THREE CALLS, ALL READS. A scan asks Wiz's token endpoint for an access token (OAuth 2.0
client credentials, form-encoded, `audience=wiz-api`), then pages through two queries on
the tenant's GraphQL endpoint: `cloudResources(filterBy: {type: [...]}, first, after)`
for the AI resources, and `graphSearch` for the AI technologies Wiz detected on
workloads (`HOSTED_TECHNOLOGY` entities that a `VIRTUAL_MACHINE`, `CONTAINER_IMAGE` or
`SERVERLESS` entity `RUNS`). Nothing else is ever sent: no mutation, no issue or
finding query, and nothing that reads a resource's contents. Each GraphQL call is a
POST, as every GraphQL call is, but the documents are queries and the same ones every
time, so repeating one is as safe as repeating a GET; every call is retried on 429 and
5xx through `discovery.retry`.

WHERE THE SHAPES COME FROM. Wiz's API reference needs a tenant login, and Wiz's hosts
are not reachable from where this was written, so nothing here was checked against a
live tenant. The token exchange follows `WizAuth.ts` in Wiz's own Backstage plugin
(github.com/wiz-sec-public/backstage-plugin-wiz); `cloudResources` is Cortex XSOAR's
`PULL_CLOUD_RESOURCES_NATIVE_QUERY` (github.com/demisto/content, Packs/Wiz), minus the
fields a record does not use; the error codes and their statuses are the Backstage
plugin's `ErrorHttpStatusMap`. The `graphSearch` call, its `GraphEntityQueryInput`
(`type`, `select`, `where: {<property>: {EQUALS: [...]}}`, `relationships` with a
reversed `RUNS`) and the `techName` and `version` properties of a `HOSTED_TECHNOLOGY`
follow a Wiz sensor inventory script (github.com/jtb75-org/wiz-sample-reports,
`sensor-versions/get-data.py`), which walks the same edge from `CONTAINER_IMAGE`; the
entity and edge names are in the Wiz Terraform provider's `GraphEntityType` and
`GraphRelationshipType` enums. That a `VIRTUAL_MACHINE` and a `SERVERLESS` reach their
technologies over the same `RUNS` edge, that `techName` takes `EQUALS`, and that a
workload's properties carry `subscriptionExternalId` are inferred, not confirmed.

ERRORS ARRIVE IN THE BODY. Wiz answers a GraphQL failure with an `errors[]` list whose
`extensions.code` says what went wrong, and often with HTTP 200. The code, not the HTTP
status, decides what is raised: UNAUTHENTICATED is 401, UNAUTHORIZED (a missing scope)
and FORBIDDEN_IP (the tenant's IP allowlist) are 403, RATE_LIMIT_EXCEEDED is 429 and is
retried like one, and BAD_USER_INPUT -- a type in the filter the tenant does not know --
is the source's `entity_types` to fix, so it is a configuration error with no status.
Only Wiz's codes reach an exception's text, never its free-text `message`, which can
quote what was sent.

Authenticated with a Wiz service account: `client_id` and `client_secret` from
Settings > Service Accounts. Least privilege is a service account with the
`read:resources` scope only, for both queries (not yet verified against a live tenant,
and inferred for `graphSearch`; see docs/standalone-discovery.md).
"""

import json
import logging
import math
import re
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable, Mapping, Optional, TypeVar

import requests

from discovery.retry import MAX_ATTEMPTS, RETRY_STATUSES, backoff_seconds
from job_executors.discovery_scan import DiscoveryConfigurationError

# auth_environment -> Wiz's token endpoint. The keys are the catalog's enum values.
TOKEN_URLS: Mapping[str, str] = {
    "commercial": "https://auth.app.wiz.io/oauth/token",
    "gov": "https://auth.gov.wiz.io/oauth/token",
    "fedramp": "https://auth.app.wiz.us/oauth/token",
}
TOKEN_AUDIENCE = "wiz-api"

# (connect, read). requests applies each separately, so together they must stay under
# Test Connection's 120s preview deadline (PREVIEW_DEADLINE_SECONDS).
REQUEST_TIMEOUT_SECONDS = (10.0, 60.0)

# The most nodes Wiz returns for one `first`.
PAGE_SIZE = 500

# A token is replaced this long before Wiz says it expires, so a long scan never sends
# one that lapses in flight.
TOKEN_REFRESH_MARGIN_SECONDS = 60.0

GRAPH_SEARCH_QUERY = """
query WorkloadTechnologySearch(
  $query: GraphEntityQueryInput
  $projectId: String!
  $first: Int
  $after: String
  $quick: Boolean = true
) {
  graphSearch(
    query: $query
    projectId: $projectId
    first: $first
    after: $after
    quick: $quick
  ) {
    nodes {
      entities {
        id
        name
        type
        providerUniqueId
        properties
        firstSeen
        lastSeen
      }
    }
    pageInfo {
      hasNextPage
      endCursor
    }
  }
}
""".strip()

# The Security Graph entity a detected technology is, and the workloads it is read on.
# A running CONTAINER is left out: its id changes with every restart, and the image it
# runs carries the same technologies under an id that does not.
TECHNOLOGY_ENTITY_TYPE = "HOSTED_TECHNOLOGY"
WORKLOAD_ENTITY_TYPES: tuple[str, ...] = (
    "VIRTUAL_MACHINE",
    "CONTAINER_IMAGE",
    "SERVERLESS",
)

CLOUD_RESOURCES_QUERY = """
query CloudResourceSearch($filterBy: CloudResourceFilters, $first: Int, $after: String) {
  cloudResources(filterBy: $filterBy, first: $first, after: $after) {
    nodes {
      id
      name
      type
      subscriptionId
      subscriptionExternalId
      graphEntity {
        id
        providerUniqueId
        name
        type
        properties
        firstSeen
        lastSeen
      }
    }
    pageInfo {
      hasNextPage
      endCursor
    }
  }
}
""".strip()

# Wiz's GraphQL `extensions.code` -> the HTTP status it stands for.
GRAPHQL_STATUS: Mapping[str, int] = {
    "UNAUTHENTICATED": 401,
    "UNAUTHORIZED": 403,
    "FORBIDDEN_IP": 403,
    "BAD_USER_INPUT": 400,
    "NOT_FOUND": 404,
    "RATE_LIMIT_EXCEEDED": 429,
    "INTERNAL": 500,
}

# The `properties` keys a record reads. Everything else in a resource's properties --
# tags, configuration, anything a customer wrote -- is dropped as the body is parsed.
REGION_KEYS = ("region", "location")
CLOUD_PLATFORM_KEY = "cloudPlatform"
# Fallbacks for `graphEntity.lastSeen`, most recent first.
TIMESTAMP_KEYS = ("updatedAt", "creationDate")
# A graph entity's own copies of what `cloudResources` returns beside it.
PROVIDER_ID_KEY = "providerUniqueId"
ACCOUNT_KEY = "subscriptionExternalId"
# A HOSTED_TECHNOLOGY's name and detected version.
TECH_NAME_KEY = "techName"
TECH_VERSION_KEY = "version"

_Read = TypeVar("_Read")

# An identifier-shaped error code (`invalid_client`, `UNAUTHORIZED`), the only part of an
# error body carried into an exception's text.
_ERROR_CODE = re.compile(r"^[A-Za-z0-9_.\-]{1,64}$")


class WizError(Exception):
    """A Wiz call that failed, carrying the HTTP status when Wiz answered.

    `status_code` is what `failure_code` and Test Connection read to tell a 401 from a
    host that never answered, so it is set whenever there was a response. For a GraphQL
    error it is the status Wiz's `extensions.code` stands for (see `GRAPHQL_STATUS`),
    whatever the HTTP status was.
    """

    def __init__(self, message: str, status_code: Optional[int] = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class ScanStopped(Exception):
    """The scan's stop check fired while a call was waiting to be retried.

    Never leaves the connector, which catches it and ends the scan as if the inventory
    had no more pages -- what `AcceptsStopCheck` asks of a connector told to stop.
    """


@dataclass(frozen=True)
class WizSettings:
    """Which tenant to read, how to authenticate, and which types to list."""

    api_endpoint_url: str
    # A key of TOKEN_URLS.
    auth_environment: str
    client_id: str
    client_secret: str
    entity_types: tuple[str, ...]
    # True when `entity_types` came from the source rather than the engine's default,
    # which changes what a BAD_USER_INPUT asks the customer to do.
    entity_types_overridden: bool = False
    timeout_seconds: tuple[float, float] = REQUEST_TIMEOUT_SECONDS

    @property
    def token_url(self) -> str:
        return TOKEN_URLS[self.auth_environment]


@dataclass(frozen=True)
class WizResource:
    """What a scan reads of one cloud resource. Everything else in the node is dropped."""

    # `graphEntity.id`, else the node's own `id`: Wiz's id for the resource.
    graph_id: str
    # The provider's own id (an ARN, an Azure resource path), when Wiz has one.
    provider_unique_id: Optional[str]
    name: Optional[str]
    entity_type: Optional[str]
    subscription_external_id: Optional[str]
    subscription_id: Optional[str]
    region: Optional[str]
    cloud_platform: Optional[str]
    # `graphEntity.lastSeen`, else the resource's update or creation time.
    last_seen: Optional[datetime]


@dataclass(frozen=True)
class ResourcePage:
    resources: list[WizResource]
    has_next_page: bool
    end_cursor: Optional[str]
    # Nodes Wiz returned with no id at all, so cannot be addressed.
    unaddressable: int = 0


@dataclass(frozen=True)
class WorkloadTechnology:
    """One technology Wiz detected on one workload. Everything else is dropped."""

    technology_name: str
    technology_version: Optional[str]
    # Wiz's id for the workload, for warnings only: never part of a record.
    workload_graph_id: str
    workload_type: str
    # The provider's own id (an ARN, a resource path, an image id), when Wiz has one.
    workload_provider_id: Optional[str]
    workload_name: Optional[str]
    account: Optional[str]
    region: Optional[str]
    cloud_platform: Optional[str]
    # The technology's `lastSeen`, else the workload's, else either's `updatedAt`.
    last_seen: Optional[datetime]


@dataclass(frozen=True)
class WorkloadPage:
    technologies: list[WorkloadTechnology]
    has_next_page: bool
    end_cursor: Optional[str]
    # Nodes without both a named technology and an identified workload.
    unaddressable: int = 0


class WizClient:
    """One tenant, one service account. Lists cloud resources of the configured types."""

    def __init__(
        self,
        settings: WizSettings,
        logger: Optional[logging.Logger] = None,
        session: Optional[requests.Session] = None,
        sleep: Callable[[float], None] = time.sleep,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._s = settings
        self._log = logger or logging.getLogger(__name__)
        self._http = session or requests.Session()
        self._sleep = sleep
        self._clock = clock
        self._should_stop: Callable[[], bool] = lambda: False
        self._access_token: Optional[str] = None
        self._token_expires_at = 0.0

    def stop_when(self, should_stop: Callable[[], bool]) -> None:
        """Asked before each retry, so a backoff never outlives a stop request."""
        self._should_stop = should_stop

    def cloud_resources_page(self, after: Optional[str] = None) -> ResourcePage:
        """One page of the configured types' resources, and how to ask for the next."""
        variables: dict[str, Any] = {
            "first": PAGE_SIZE,
            "filterBy": {"type": list(self._s.entity_types)},
        }
        if after is not None:
            variables["after"] = after
        resp, payload = self._graphql(
            "cloudResources",
            CLOUD_RESOURCES_QUERY,
            variables,
        )
        return _page_from(resp, payload)

    def workload_technologies_page(
        self,
        technologies: tuple[str, ...],
        after: Optional[str] = None,
    ) -> WorkloadPage:
        """One page of the named technologies on workloads, each with its workload."""
        variables: dict[str, Any] = {
            "first": PAGE_SIZE,
            "projectId": "*",
            "quick": True,
            "query": {
                "type": [TECHNOLOGY_ENTITY_TYPE],
                "select": True,
                "where": {TECH_NAME_KEY: {"EQUALS": list(technologies)}},
                "relationships": [
                    {
                        "type": [{"type": "RUNS", "reverse": True}],
                        "with": {
                            "type": list(WORKLOAD_ENTITY_TYPES),
                            "select": True,
                        },
                    },
                ],
            },
        }
        if after is not None:
            variables["after"] = after
        resp, payload = self._graphql("graphSearch", GRAPH_SEARCH_QUERY, variables)
        return _workload_page_from(resp, payload)

    # -- the token -----------------------------------------------------------------------

    def _refresh_token_if_due(self) -> None:
        """Fetch a token on the first call and again shortly before it lapses."""
        if self._access_token is None or self._clock() >= self._token_expires_at:
            self._access_token, lifetime = self._fetch_token()
            self._token_expires_at = self._clock() + max(
                0.0,
                lifetime - TOKEN_REFRESH_MARGIN_SECONDS,
            )

    def _fetch_token(self) -> tuple[str, float]:
        """A fresh access token and how many seconds it is good for."""
        resp, _ = self._send(
            "token",
            lambda: self._http.post(
                self._s.token_url,
                data={
                    "grant_type": "client_credentials",
                    "audience": TOKEN_AUDIENCE,
                    "client_id": self._s.client_id,
                    "client_secret": self._s.client_secret,
                },
                headers={
                    "Content-Type": "application/x-www-form-urlencoded",
                    "Accept": "application/json",
                },
                # The secret is in the body. Refusing redirects says outright that it
                # only ever goes to the token endpoint the source chose.
                allow_redirects=False,
                timeout=self._s.timeout_seconds,
            ),
            read=lambda r: (r.status_code, None),
        )
        if resp.status_code != 200:
            raise WizError(
                f"Wiz token request failed with HTTP {resp.status_code}"
                f"{_code_suffix(_oauth_error_code(resp))}"
                f"{_token_hint(resp.status_code)}",
                status_code=resp.status_code,
            )
        payload = _json_or_none(resp)
        token = payload.get("access_token") if isinstance(payload, dict) else None
        if not isinstance(token, str) or not token.strip():
            raise WizError(
                f"Wiz token request answered HTTP {resp.status_code} without an "
                f"access token ({resp.headers.get('Content-Type') or 'no content type'}). "
                f"Something between the engine and Wiz's token endpoint answered instead.",
                status_code=resp.status_code,
            )
        lifetime = payload.get("expires_in")
        if isinstance(lifetime, bool) or not isinstance(lifetime, (int, float)):
            # No lifetime: keep it for the scan. A lapsed token is then a 401, which
            # is still the right failure.
            return token, math.inf
        return token, float(lifetime)

    # -- the query -----------------------------------------------------------------------

    def _graphql(
        self,
        what: str,
        query: str,
        variables: dict[str, Any],
    ) -> tuple[requests.Response, Any]:
        """One GraphQL query's answer, retried when the failure passes. `what` names
        the query in errors."""
        resp, (payload, code) = self._send(
            what,
            lambda: self._http.post(
                self._s.api_endpoint_url,
                json={"query": query, "variables": variables},
                headers={
                    "Authorization": f"Bearer {self._access_token}",
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
                # The token is a header. requests drops Authorization on a redirect to
                # another host, but refusing redirects says outright that this client
                # only ever talks to the endpoint the source named.
                allow_redirects=False,
                timeout=self._s.timeout_seconds,
            ),
            read=_graphql_answer,
            # Outside the call's own error handling, so a token failure is reported as
            # the token request's rather than retried again as the query's.
            prepare=self._refresh_token_if_due,
        )
        status = _graphql_status(resp.status_code, code)
        if status != 200 or code is not None:
            raise self._graphql_failure(what, status, code or "")
        return resp, payload

    def _graphql_failure(
        self,
        what: str,
        status: int,
        code: str,
    ) -> Exception:
        if code == "BAD_USER_INPUT" and what == "graphSearch":
            # The engine's own query, which no source field shapes: Wiz's error, with
            # the status its code stands for.
            return WizError(
                "Wiz rejected the workload technology graphSearch query "
                "(BAD_USER_INPUT).",
                status_code=status,
            )
        if code == "BAD_USER_INPUT":
            # The source's type filter, so the source is reported as needing a change
            # rather than as Wiz failing. It carries no status_code, and its text avoids
            # "HTTP", either of which Test Connection would read as the vendor's error.
            # Returned, and raised by the caller outside any except block, so nothing
            # is chained to it.
            return DiscoveryConfigurationError(
                "Wiz rejected the cloudResources type filter (BAD_USER_INPUT). "
                + (
                    "Check that every name in entity_types is a Wiz Security Graph "
                    "entity type this tenant knows, in capitals, comma-separated."
                    if self._s.entity_types_overridden
                    else "entity_types is blank, so the engine's default AI entity "
                    "types were sent, and this tenant does not know at least one of "
                    "them. Set entity_types to the Wiz Security Graph entity types "
                    "that hold this tenant's AI agents."
                ),
            )
        if status == 404 and not code:
            return DiscoveryConfigurationError(
                "Wiz found no GraphQL API at api_endpoint_url. Use the tenant's API "
                "endpoint as Wiz shows it under User Settings > Tenant, ending in "
                "/graphql.",
            )
        if status == 200:
            # Errors with no code Wiz documents: Wiz answered, with a failure.
            return WizError(
                f"Wiz {what} query answered HTTP 200 with errors{_code_suffix(code)}.",
                status_code=200,
            )
        return WizError(
            f"Wiz {what} query failed with HTTP {status}"
            f"{_code_suffix(code)}{_graphql_hint(what, status, code)}",
            status_code=status,
        )

    # -- sending -------------------------------------------------------------------------

    def _send(
        self,
        what: str,
        call: Callable[[], requests.Response],
        read: Callable[[requests.Response], tuple[int, _Read]],
        prepare: Optional[Callable[[], None]] = None,
    ) -> tuple[requests.Response, _Read]:
        """One call, retried while it fails for a reason that passes. Both calls a scan
        makes are reads (see the module docstring), so repeating one is always safe.

        `read` says what the answer meant -- for a GraphQL answer its error code's
        status rather than the HTTP one, so a 200 carrying RATE_LIMIT_EXCEEDED is
        retried like a 429 -- and hands back what it parsed, so the body is read once.
        """
        for attempt in range(1, MAX_ATTEMPTS + 1):
            if prepare is not None:
                prepare()
            try:
                resp = call()
            except requests.exceptions.SSLError as exc:
                # Not the source's settings -- it has none for TLS -- but the engine's:
                # Wiz's hosts have public certificates, so a failure means something
                # between the two re-signs traffic. Not retried: a certificate does not
                # change between attempts. The same type, so it still reads as network.
                raise type(exc)(
                    f"Wiz {what} request: TLS verification failed "
                    f"({type(exc).__name__}). If the engine reaches the internet "
                    f"through a TLS-inspecting proxy, give the engine that proxy's CA "
                    f"(REQUESTS_CA_BUNDLE).",
                ) from exc
            except (requests.ConnectionError, requests.Timeout) as exc:
                if attempt < MAX_ATTEMPTS:
                    self._pause(backoff_seconds(attempt, None))
                    continue
                # Re-raised as the same type so Test Connection still reads it as the
                # network failure (or timeout) it is. requests' own text is left to the
                # chain.
                raise type(exc)(
                    f"Wiz {what} request unreachable after {MAX_ATTEMPTS} attempts "
                    f"({type(exc).__name__}). The engine needs outbound HTTPS to Wiz's "
                    f"token endpoint and to api_endpoint_url; check auth_environment "
                    f"and the data center in api_endpoint_url.",
                ) from exc
            status, parsed = read(resp)
            if status in RETRY_STATUSES and attempt < MAX_ATTEMPTS:
                self._pause(backoff_seconds(attempt, resp.headers.get("Retry-After")))
                continue
            return resp, parsed
        raise AssertionError("unreachable: the last attempt returns or raises")

    def _pause(self, seconds: float) -> None:
        if self._should_stop():
            raise ScanStopped()
        self._sleep(seconds)


# -- reading answers --------------------------------------------------------------------
#
# A 200 is not always Wiz's: a proxy or captive portal can answer 200 with HTML. That,
# and a body that is JSON but not the shape asked for, is Wiz's error with its status
# rather than a bare ValueError or KeyError, which Test Connection would read as a
# configuration mistake.


def _json_or_none(resp: requests.Response) -> Any:
    try:
        return resp.json()
    except ValueError:
        return None


def _graphql_answer(resp: requests.Response) -> tuple[int, tuple[Any, Optional[str]]]:
    """(the status the answer stands for, (its body, Wiz's error code)), for `_send`."""
    payload = _json_or_none(resp)
    code = _graphql_error_code(payload)
    return _graphql_status(resp.status_code, code), (payload, code)


def _graphql_status(http_status: int, code: Optional[str]) -> int:
    """A code in `GRAPHQL_STATUS` decides the status whatever the HTTP status said; any
    other keeps the HTTP status, so a 200 carrying errors is told apart from success by
    its code not being None."""
    return GRAPHQL_STATUS.get(code or "", http_status)


def _graphql_error_code(payload: Any) -> Optional[str]:
    """Wiz's error code: None when the answer carries no `errors`, "" when it carries
    errors with no code this module can read, and a code in `GRAPHQL_STATUS` in
    preference to any other."""
    errors = payload.get("errors") if isinstance(payload, dict) else None
    if not errors:
        return None
    code = ""
    for error in errors if isinstance(errors, list) else []:
        extensions = error.get("extensions") if isinstance(error, dict) else None
        candidate = extensions.get("code") if isinstance(extensions, dict) else None
        if isinstance(candidate, str) and _ERROR_CODE.match(candidate):
            if candidate in GRAPHQL_STATUS:
                return candidate
            code = code or candidate
    return code


def _page_from(resp: requests.Response, payload: Any) -> ResourcePage:
    data = payload.get("data") if isinstance(payload, dict) else None
    listing = data.get("cloudResources") if isinstance(data, dict) else None
    nodes = listing.get("nodes") if isinstance(listing, dict) else None
    page_info = listing.get("pageInfo") if isinstance(listing, dict) else None
    if not isinstance(nodes, list) or not isinstance(page_info, dict):
        raise WizError(
            f"Wiz cloudResources query answered HTTP {resp.status_code} with a body "
            f"that is not a cloudResources page "
            f"({resp.headers.get('Content-Type') or 'no content type'}). Check that "
            f"api_endpoint_url is the tenant's GraphQL endpoint, not the Wiz portal or "
            f"a proxy's login page.",
            status_code=resp.status_code,
        )
    resources: list[WizResource] = []
    unaddressable = 0
    for node in nodes:
        resource = _resource_from(node)
        if resource is None:
            unaddressable += 1
        else:
            resources.append(resource)
    cursor = page_info.get("endCursor")
    return ResourcePage(
        resources=resources,
        has_next_page=page_info.get("hasNextPage") is True,
        end_cursor=cursor if isinstance(cursor, str) and cursor else None,
        unaddressable=unaddressable,
    )


def _workload_page_from(resp: requests.Response, payload: Any) -> WorkloadPage:
    data = payload.get("data") if isinstance(payload, dict) else None
    listing = data.get("graphSearch") if isinstance(data, dict) else None
    nodes = listing.get("nodes") if isinstance(listing, dict) else None
    page_info = listing.get("pageInfo") if isinstance(listing, dict) else None
    if not isinstance(nodes, list) or not isinstance(page_info, dict):
        raise WizError(
            f"Wiz graphSearch query answered HTTP {resp.status_code} with a body that "
            f"is not a graphSearch page "
            f"({resp.headers.get('Content-Type') or 'no content type'}).",
            status_code=resp.status_code,
        )
    technologies: list[WorkloadTechnology] = []
    unaddressable = 0
    for node in nodes:
        technology = _workload_technology_from(node)
        if technology is None:
            unaddressable += 1
        else:
            technologies.append(technology)
    cursor = page_info.get("endCursor")
    return WorkloadPage(
        technologies=technologies,
        has_next_page=page_info.get("hasNextPage") is True,
        end_cursor=cursor if isinstance(cursor, str) and cursor else None,
        unaddressable=unaddressable,
    )


def _workload_technology_from(node: Any) -> Optional[WorkloadTechnology]:
    """A path's technology and workload, or None without a named one of each."""
    entities = node.get("entities") if isinstance(node, dict) else None
    if not isinstance(entities, list):
        return None
    technology = _first_entity(entities, (TECHNOLOGY_ENTITY_TYPE,))
    workload = _first_entity(entities, WORKLOAD_ENTITY_TYPES)
    if technology is None or workload is None:
        return None
    tech_properties = _properties(technology.get("properties"))
    name = _text(tech_properties.get(TECH_NAME_KEY)) or _text(technology.get("name"))
    workload_graph_id = _text(workload.get("id"))
    if name is None or workload_graph_id is None:
        return None
    properties = _properties(workload.get("properties"))
    return WorkloadTechnology(
        technology_name=name.strip(),
        technology_version=_text(tech_properties.get(TECH_VERSION_KEY)),
        workload_graph_id=workload_graph_id,
        workload_type=str(workload.get("type")),
        workload_provider_id=(
            _text(workload.get("providerUniqueId"))
            or _text(properties.get(PROVIDER_ID_KEY))
        ),
        workload_name=_text(workload.get("name")),
        account=_text(properties.get(ACCOUNT_KEY)),
        region=_first_text(properties, REGION_KEYS),
        cloud_platform=_text(properties.get(CLOUD_PLATFORM_KEY)),
        last_seen=_first_timestamp(
            [
                technology.get("lastSeen"),
                workload.get("lastSeen"),
                tech_properties.get("updatedAt"),
                properties.get("updatedAt"),
            ],
        ),
    )


def _first_entity(
    entities: list[Any],
    types: tuple[str, ...],
) -> Optional[dict[str, Any]]:
    return next(
        (e for e in entities if isinstance(e, dict) and e.get("type") in types),
        None,
    )


def _resource_from(node: Any) -> Optional[WizResource]:
    if not isinstance(node, dict):
        return None
    entity = node.get("graphEntity")
    entity = entity if isinstance(entity, dict) else {}
    graph_id = _text(entity.get("id")) or _text(node.get("id"))
    if graph_id is None:
        return None
    properties = _properties(entity.get("properties"))
    return WizResource(
        graph_id=graph_id,
        provider_unique_id=_text(entity.get("providerUniqueId")),
        name=_text(entity.get("name")) or _text(node.get("name")),
        entity_type=_text(entity.get("type")) or _text(node.get("type")),
        subscription_external_id=_text(node.get("subscriptionExternalId")),
        subscription_id=_text(node.get("subscriptionId")),
        region=_first_text(properties, REGION_KEYS),
        cloud_platform=_text(properties.get(CLOUD_PLATFORM_KEY)),
        last_seen=_first_timestamp(
            [entity.get("lastSeen"), *(properties.get(k) for k in TIMESTAMP_KEYS)],
        ),
    )


def _properties(raw: Any) -> dict[str, Any]:
    """`graphEntity.properties`, a JSON scalar: an object, or that object as a string."""
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except ValueError:
            return {}
    return raw if isinstance(raw, dict) else {}


def _text(value: Any) -> Optional[str]:
    return value if isinstance(value, str) and value.strip() else None


def _first_text(properties: Mapping[str, Any], keys: tuple[str, ...]) -> Optional[str]:
    return next((t for t in (_text(properties.get(k)) for k in keys) if t), None)


def _first_timestamp(values: list[Any]) -> Optional[datetime]:
    return next((t for t in map(_timestamp, values) if t is not None), None)


def _timestamp(value: Any) -> Optional[datetime]:
    """An ISO 8601 timestamp as an aware datetime (UTC when it names no zone), or None."""
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = datetime.fromisoformat(value.strip())
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def _oauth_error_code(resp: requests.Response) -> str:
    """The token endpoint's `error` (`invalid_client`), never its `error_description`."""
    body = _json_or_none(resp)
    code = body.get("error") if isinstance(body, dict) else None
    return code if isinstance(code, str) and _ERROR_CODE.match(code) else ""


def _code_suffix(code: str) -> str:
    return f" ({code})" if code else ""


def _token_hint(status: int) -> str:
    if status in (400, 401):
        return (
            ". Wiz did not accept client_id and client_secret: the service account may "
            "be deleted or its secret rotated, or auth_environment names another Wiz "
            "environment than the tenant's (commercial, gov or fedramp)"
        )
    if status == 403:
        return ". Wiz refused to issue a token to this service account"
    if status == 429:
        return ". Wiz's rate limit held through every retry; scan less often"
    return ""


def _graphql_hint(what: str, status: int, code: str) -> str:
    if code == "FORBIDDEN_IP":
        return (
            ". The tenant restricts API access to an IP allowlist that does not "
            "include the engine's egress address; add it to the tenant's allowed IP "
            "addresses"
        )
    if status == 401:
        return (
            ". Wiz did not accept the access token it issued: check that "
            "api_endpoint_url is this tenant's endpoint (User Settings > Tenant) and "
            "that auth_environment matches it"
        )
    if status == 403:
        return (
            f". The service account cannot run the {what} query: it needs the "
            f"read:resources scope"
        )
    if status == 429:
        return ". Wiz's rate limit held through every retry; scan less often"
    return ""
