"""Wiz's GraphQL API, as far as a discovery scan needs it.

THREE CALLS, ALL READS. A scan asks Wiz's token endpoint for an access token (OAuth 2.0
client credentials, form-encoded, `audience=wiz-api`), then pages through two queries on
the tenant's GraphQL endpoint: `cloudResourcesV2(filterBy: {type: {equals: [...]}},
first, after)` for the AI resources, and `hostedTechnologies(filterBy, first, after)`
for the machine-learning and AI technologies Wiz detected on `VIRTUAL_MACHINE`,
`CONTAINER_IMAGE` and `SERVERLESS` resources. Nothing else is ever sent: no mutation, no
issue or finding query, and nothing that reads a resource's contents. Each GraphQL call
is a POST, as every GraphQL call is, but the documents are queries and the same ones
every time, so repeating one is as safe as repeating a GET; every call is retried on
429 and 5xx through `discovery.retry`.

WHERE THE SHAPES COME FROM. Confirmed: every type, field, filter and enum value in the
two queries is in a Wiz GraphQL schema printed from live introspection and published at
github.com/ArcavenAE/stave (commit b893774, `spec/wiz-schema.graphql`): `CloudResourceV2`
(line 15753) and its `CloudResourceV2Filters`, `HostedTechnology` (61768),
`HostedTechnologyResource` (62019), `HostedTechnologyFilters` (61919), `Technology`
(88164, including `isCloudService: Boolean!` at 88185), `TechnologyCategory` (88245),
`TechnologyCategoryFilters.stackLayer` and the `TechnologyStackLayer` value
`MACHINE_LEARNING_AND_AI`. The same filter shapes are used by public integrations
(`type: {equals: [...]}` on `cloudResourcesV2`; `technologyV2: {category: {stackLayer:
[MACHINE_LEARNING_AND_AI]}}` and `resource: {type: {equals: [...]}}` on
`hostedTechnologies`, as in lindsp77/wiz-health-assessment-skill e4afe70
`scripts/generate_deck.py:743-751`). The token exchange follows `WizAuth.ts` in Wiz's own
Backstage plugin (github.com/wiz-sec-public/backstage-plugin-wiz), and the error codes
and their statuses are that plugin's `ErrorHttpStatusMap`. What no public source shows
is how Wiz spells each agent framework's name.

THE NATIVE ID. Confirmed from the schema: `CloudResourceV2` has `externalId: String!`
and a nullable `providerUniqueId`; a hosted technology's resource has only
`externalId: String!`, with `providerUniqueId` on its `graphEntity`. Confirmed from a live
run (ArcavenAE/stave 1cfb526, `_kos/findings/finding-010-*.md:39-43`):
`providerUniqueId` was set on 9 of 20 `cloudResourcesV2` records. Both fields are the
cloud provider's own ids, never Wiz's (strong inference: demisto/content f92da85
`Packs/Wiz/Integrations/Wiz/Wiz.py:2832` looks resources up by an ARN in
`providerUniqueId`, `README.md:461`; its `classifier-WizDefend_Mapper.json:65-67` maps
`externalId` to the "Unique (provider) cloud resource ID",
`incidentfield-Wiz_Resource_Cloud_ID.json:28`). `externalId` can be an id unique only
inside its account (an instance's short id where `providerUniqueId` is its ARN), so the
connector qualifies it; see `discovery.cloud.wiz.connector.native_id`.

ERRORS ARRIVE IN THE BODY. Wiz answers a GraphQL failure with an `errors[]` list whose
`extensions.code` says what went wrong, and often with HTTP 200. The code, not the HTTP
status, decides what is raised: UNAUTHENTICATED is 401, UNAUTHORIZED (a missing scope)
and FORBIDDEN_IP (the tenant's IP allowlist) are 403, RATE_LIMIT_EXCEEDED is 429 and is
retried like one, and BAD_USER_INPUT -- a type in the filter the tenant does not know --
is the source's `entity_types` to fix, so it is a configuration error with no status.
Only Wiz's codes reach an exception's text, never its free-text `message`, which can
quote what was sent -- with one exception: a denial's list of the scopes Wiz wanted,
which holds scope names only and is carried verbatim, rebuilt from tokens shaped like
`read:inventory` (confirmed format: ArcavenAE/stave 6728a95,
`_kos/findings/finding-009-*.md:29-34`, "access denied, at least one of the following is
required: [read:all read:permission_scopes]").

Authenticated with a Wiz service account: `client_id` and `client_secret` from
Settings > Service Accounts. The AI-SPM query needs `read:resources` (confirmed: the same
finding-010 run read `cloudResourcesV2` with a credential holding `read:resources` and
neither `read:inventory` nor `read:all`, whose scopes finding-009:31-34 lists).
`hostedTechnologies` is granted `read:resources` and `read:inventory`, or `read:all`
(unconfirmed: `read:inventory` is a real scope, AxtonGrams/terraform-provider-wiz 4fee5a8
`internal/common.go:87`, but no public source ties it to the query; a denial names the
scope Wiz wanted, so the job log says which). See docs/standalone-discovery.md.
"""

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

CLOUD_RESOURCES_QUERY = """
query CloudResourceSearch(
  $filterBy: CloudResourceV2Filters
  $first: Int
  $after: String
) {
  cloudResourcesV2(filterBy: $filterBy, first: $first, after: $after) {
    nodes {
      id
      name
      type
      nativeType
      externalId
      providerUniqueId
      cloudPlatform
      region
      regionLocation
      createdAt
      updatedAt
      firstSeen
      lastSeen
      cloudAccount {
        externalId
      }
    }
    pageInfo {
      hasNextPage
      endCursor
    }
  }
}
""".strip()

HOSTED_TECHNOLOGIES_QUERY = """
query WorkloadTechnologies(
  $filterBy: HostedTechnologyFilters
  $first: Int
  $after: String
) {
  hostedTechnologies(filterBy: $filterBy, first: $first, after: $after) {
    nodes {
      id
      name
      firstSeen
      updatedAt
      versionDetails {
        version
      }
      technology {
        id
        name
        isCloudService
        stackLayer
        categories {
          id
          name
        }
      }
      resource {
        id
        externalId
        name
        type
        nativeType
        cloudPlatform
        region
        regionLocation
        cloudAccount {
          externalId
        }
        graphEntity {
          providerUniqueId
        }
      }
    }
    pageInfo {
      hasNextPage
      endCursor
    }
  }
}
""".strip()

# The technology stack layer Wiz files AI frameworks and SDKs under.
AI_STACK_LAYER = "MACHINE_LEARNING_AND_AI"

# The resource types a hosted technology is read on. A running CONTAINER is left out:
# its id changes with every restart, and the image it runs carries the same
# technologies under an id that does not.
WORKLOAD_ENTITY_TYPES: tuple[str, ...] = (
    "VIRTUAL_MACHINE",
    "CONTAINER_IMAGE",
    "SERVERLESS",
)

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

# The region fields, in order: the provider's region name, else Wiz's location for it.
REGION_FIELDS = ("region", "regionLocation")
# A resource's timestamps, most recent first.
RESOURCE_TIMESTAMP_FIELDS = ("lastSeen", "updatedAt", "firstSeen", "createdAt")
# A hosted technology's, most recent first. It has no lastSeen.
TECHNOLOGY_TIMESTAMP_FIELDS = ("updatedAt", "firstSeen")

_Read = TypeVar("_Read")

# An identifier-shaped error code (`invalid_client`, `UNAUTHORIZED`), the only part of an
# error body carried into an exception's text besides a denial's scope list.
_ERROR_CODE = re.compile(r"^[A-Za-z0-9_.\-]{1,64}$")

_REQUIRED_SCOPES = re.compile(
    r"at least one of the following is required: \[([^\]]*)\]",
)
_SCOPE_NAME = re.compile(r"^[a-z][a-z0-9_]*:[a-z][a-z0-9_]*$")
_MAX_SCOPES_QUOTED = 32


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
    # Development only: a local fake Wiz that serves both calls instead of Wiz. See
    # `discovery.cloud.wiz.connector.local_override`.
    local_override_url: Optional[str] = None

    @property
    def token_url(self) -> str:
        if self.local_override_url is not None:
            return f"{self.local_override_url}/oauth/token"
        return TOKEN_URLS[self.auth_environment]

    @property
    def graphql_url(self) -> str:
        if self.local_override_url is not None:
            return f"{self.local_override_url}/graphql"
        return self.api_endpoint_url


@dataclass(frozen=True)
class WizResource:
    """What a scan reads of one cloud resource. Everything else in the node is dropped."""

    # Wiz's id for the resource, for de-duplication and warnings only.
    graph_id: str
    # The provider's own id (an ARN, an Azure resource path), when Wiz has one.
    provider_unique_id: Optional[str]
    # `externalId`: the provider's id in whatever form Wiz keeps it, possibly one unique
    # only inside its account.
    provider_external_id: Optional[str]
    name: Optional[str]
    entity_type: Optional[str]
    native_type: Optional[str]
    # `cloudAccount.externalId`: the AWS account, Azure subscription or GCP project id.
    account: Optional[str]
    region: Optional[str]
    cloud_platform: Optional[str]
    # `lastSeen`, else the resource's update, first-seen or creation time.
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

    # `technology.name`, never the hosted technology's own `name`, which is
    # "<technology> (<resource name>)".
    technology_name: str
    # Wiz's catalog id for the technology, a numeric string ("2599"), for the log only.
    technology_id: Optional[str]
    # `technology.isCloudService`: a managed service, which is AI-SPM's to report.
    is_cloud_service: bool
    technology_version: Optional[str]
    # Wiz's id for the workload, for warnings only: never part of a record.
    workload_graph_id: str
    workload_type: str
    workload_native_type: Optional[str]
    # `resource.graphEntity.providerUniqueId`: the provider's own id (an ARN, a
    # resource path, an image id), when Wiz has one.
    workload_provider_id: Optional[str]
    # `resource.externalId`, possibly unique only inside its account.
    workload_external_id: Optional[str]
    workload_name: Optional[str]
    account: Optional[str]
    region: Optional[str]
    cloud_platform: Optional[str]
    # The hosted technology's `updatedAt`, else its `firstSeen`.
    last_seen: Optional[datetime]


@dataclass(frozen=True)
class WorkloadPage:
    technologies: list[WorkloadTechnology]
    has_next_page: bool
    end_cursor: Optional[str]
    # Nodes without both a named technology and an identified resource.
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
            "filterBy": {"type": {"equals": list(self._s.entity_types)}},
        }
        if after is not None:
            variables["after"] = after
        resp, payload = self._graphql(
            "cloudResourcesV2",
            CLOUD_RESOURCES_QUERY,
            variables,
        )
        return _page_from(resp, payload)

    def workload_technologies_page(self, after: Optional[str] = None) -> WorkloadPage:
        """One page of the machine-learning and AI technologies on workloads, each with
        the resource it was detected on."""
        variables: dict[str, Any] = {
            "first": PAGE_SIZE,
            "filterBy": {
                "technologyV2": {"category": {"stackLayer": [AI_STACK_LAYER]}},
                "resource": {"type": {"equals": list(WORKLOAD_ENTITY_TYPES)}},
            },
        }
        if after is not None:
            variables["after"] = after
        resp, payload = self._graphql(
            "hostedTechnologies",
            HOSTED_TECHNOLOGIES_QUERY,
            variables,
        )
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
                self._s.graphql_url,
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
            raise self._graphql_failure(
                what,
                status,
                code or "",
                _required_scopes(payload),
            )
        return resp, payload

    def _graphql_failure(
        self,
        what: str,
        status: int,
        code: str,
        required_scopes: Optional[str] = None,
    ) -> Exception:
        if code == "BAD_USER_INPUT" and what == "hostedTechnologies":
            # The engine's own query, which no source field shapes: Wiz's error, with
            # the status its code stands for.
            return WizError(
                "Wiz rejected the workload hostedTechnologies query (BAD_USER_INPUT).",
                status_code=status,
            )
        if code == "BAD_USER_INPUT":
            # The source's type filter, so the source is reported as needing a change
            # rather than as Wiz failing. It carries no status_code, and its text avoids
            # "HTTP", either of which Test Connection would read as the vendor's error.
            # Returned, and raised by the caller outside any except block, so nothing
            # is chained to it.
            return DiscoveryConfigurationError(
                "Wiz rejected the cloudResourcesV2 type filter (BAD_USER_INPUT). "
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
            f"Wiz {what} query failed with HTTP {status}{_code_suffix(code)}"
            + (f": Wiz says {required_scopes}" if required_scopes else "")
            + _graphql_hint(what, status, code),
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


def _required_scopes(payload: Any) -> Optional[str]:
    """A denial's "at least one of the following is required: [...]", rebuilt from its
    scope names, or None when no error carries one made only of scope names."""
    errors = payload.get("errors") if isinstance(payload, dict) else None
    for error in errors if isinstance(errors, list) else []:
        message = error.get("message") if isinstance(error, dict) else None
        found = _REQUIRED_SCOPES.search(message) if isinstance(message, str) else None
        scopes = found.group(1).split() if found else []
        if 0 < len(scopes) <= _MAX_SCOPES_QUOTED and all(
            _SCOPE_NAME.match(scope) for scope in scopes
        ):
            return f"at least one of the following is required: [{' '.join(scopes)}]"
    return None


def _page_from(resp: requests.Response, payload: Any) -> ResourcePage:
    nodes, page_info = _listing(resp, payload, "cloudResourcesV2")
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
    nodes, page_info = _listing(resp, payload, "hostedTechnologies")
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


def _listing(
    resp: requests.Response,
    payload: Any,
    field: str,
) -> tuple[list[Any], dict[str, Any]]:
    """A connection's `nodes` and `pageInfo`, or Wiz's error when the body is not one."""
    data = payload.get("data") if isinstance(payload, dict) else None
    listing = data.get(field) if isinstance(data, dict) else None
    nodes = listing.get("nodes") if isinstance(listing, dict) else None
    page_info = listing.get("pageInfo") if isinstance(listing, dict) else None
    if not isinstance(nodes, list) or not isinstance(page_info, dict):
        raise WizError(
            f"Wiz {field} query answered HTTP {resp.status_code} with a body that is "
            f"not a {field} page "
            f"({resp.headers.get('Content-Type') or 'no content type'}). Check that "
            f"api_endpoint_url is the tenant's GraphQL endpoint, not the Wiz portal or "
            f"a proxy's login page.",
            status_code=resp.status_code,
        )
    return nodes, page_info


def _workload_technology_from(node: Any) -> Optional[WorkloadTechnology]:
    """A hosted technology and its resource, or None without a named technology and an
    identified resource. The name is `technology.name` only."""
    if not isinstance(node, dict):
        return None
    technology = _object(node.get("technology"))
    resource = _object(node.get("resource"))
    name = _text(technology.get("name"))
    workload_graph_id = _text(resource.get("id"))
    if name is None or workload_graph_id is None:
        return None
    return WorkloadTechnology(
        technology_name=name.strip(),
        technology_id=_text(technology.get("id")),
        is_cloud_service=technology.get("isCloudService") is True,
        technology_version=_text(_object(node.get("versionDetails")).get("version")),
        workload_graph_id=workload_graph_id,
        workload_type=str(resource.get("type")),
        workload_native_type=_text(resource.get("nativeType")),
        workload_provider_id=_text(
            _object(resource.get("graphEntity")).get("providerUniqueId"),
        ),
        workload_external_id=_text(resource.get("externalId")),
        workload_name=_text(resource.get("name")),
        account=_text(_object(resource.get("cloudAccount")).get("externalId")),
        region=_first_text(resource, REGION_FIELDS),
        cloud_platform=_text(resource.get("cloudPlatform")),
        last_seen=_first_timestamp(
            [node.get(field) for field in TECHNOLOGY_TIMESTAMP_FIELDS],
        ),
    )


def _resource_from(node: Any) -> Optional[WizResource]:
    if not isinstance(node, dict):
        return None
    graph_id = _text(node.get("id"))
    if graph_id is None:
        return None
    return WizResource(
        graph_id=graph_id,
        provider_unique_id=_text(node.get("providerUniqueId")),
        provider_external_id=_text(node.get("externalId")),
        name=_text(node.get("name")),
        entity_type=_text(node.get("type")),
        native_type=_text(node.get("nativeType")),
        account=_text(_object(node.get("cloudAccount")).get("externalId")),
        region=_first_text(node, REGION_FIELDS),
        cloud_platform=_text(node.get("cloudPlatform")),
        last_seen=_first_timestamp(
            [node.get(field) for field in RESOURCE_TIMESTAMP_FIELDS],
        ),
    )


def _object(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _text(value: Any) -> Optional[str]:
    return value if isinstance(value, str) and value.strip() else None


def _first_text(fields: Mapping[str, Any], keys: tuple[str, ...]) -> Optional[str]:
    return next((t for t in (_text(fields.get(k)) for k in keys) if t), None)


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
    if status == 403 and what == "hostedTechnologies":
        return (
            ". The service account cannot run the hostedTechnologies query: grant it "
            "read:resources and read:inventory, or read:all"
        )
    if status == 403:
        return (
            f". The service account cannot run the {what} query: it needs the "
            f"read:resources scope"
        )
    if status == 429:
        return ". Wiz's rate limit held through every retry; scan less often"
    return ""
