"""Vercel's REST API, as far as a discovery scan needs it.

THE INVENTORY: THREE GETS. A scan lists the team's projects (`GET /v10/projects`,
paged), reads each in-scope project's environment variables (`GET
/v10/projects/{id}/env`), and reads the team's integration configurations once (`GET
/v1/integrations/configurations`). Every one carries `teamId`, so a token that can see
several teams only ever reads the one the source names.

THE EXTRA SIGNALS, NONE OF WHICH CAN FAIL A SCAN. Each of these adds recall to the
inventory; the connector turns any failure of one into a warning and goes on without
it, so this client raises `VercelError` (with the status) and leaves the decision there.

* `GET /v1/env`: the team's shared environment variables, and the projects each is
  linked to. Names only, as for project variables.
* `GET /v2/teams/{teamId}`: the team's slug, which Agent Runs is addressed by.
* `GET https://vercel.com/api/observability/agent-runs?teamSlug=..&view=team&
  environment=production`: the projects with Agent Runs. UNDOCUMENTED AND MAY CHANGE:
  it is what the Vercel CLI's `vercel agent-runs projects` calls (CLI 65.2.0), on the
  dashboard host rather than api.vercel.com, and it is in no published API reference
  or SDK. Its answer is read the way that CLI reads it: `projects` (or `items`), each
  entry naming its project by `projectId`/`projectName`/`name`/`project`/`id` and its
  run count by `runs`/`runCount`/`totalRuns`.
* `POST /v2/observability/query`: Observability Plus metrics, grouped by project. A
  team without Observability Plus answers 402, even on Pro. A query is a read, even
  though it is a POST, so it is retried like the GETs.
* `GET /v6/deployments/{id}/files` and `GET /v8/deployments/{id}/files/{fileId}`: one
  deployment's file tree and one file of it, base64 in a JSON body. Only when the
  source opts in with `read_deployment_sources`, because this reads code. Vercel keeps
  no file tree for a Git deployment and answers 404 ("File tree not found").

NAMES, NEVER VALUES. The env endpoints return each variable's value alongside its name:
encrypted for `encrypted`/`sensitive`/`secret` variables, but PLAINTEXT for `plain` ones.
Nothing here asks for more than that -- `decrypt` is never sent, and the single-variable
endpoints `/v1/projects/{id}/env/{envId}` and `/v1/env/{id}`, which decrypt, are never
called -- and what does arrive is cut down to `key`, `type`, `target` (and, for a shared
variable, its project ids) the moment the body is parsed. A value never reaches a
dataclass, a log line or an exception's text. The project list carries an `env` array
of its own; it is not read for the same reason. A package.json is decoded only far
enough to read its dependency NAMES; its text is never kept, logged or raised.

HOW THE PROJECT LIST PAGES. `pagination.next` is either a number (an `updatedAt`
timestamp, sent back as `until`) or, on newer accounts, a base32 continuation token
(sent back as `from`); the Vercel SDK models both. `null` ends the list. The connector
walks the pages so it can check its stop between them; this client makes one call per
method.

Authenticated with a Vercel access token, `Authorization: Bearer <token>`. Vercel
tokens carry the permissions of the user who created them within the team chosen at
creation; there is no read-only token scope, so least privilege depends on the plan. On
Enterprise, a member with the Enterprise Viewer role can read everything this client
calls. On Pro, Vercel's role docs say a Pro Viewer can read projects and deployments but
not observability data or team settings, so the Observability Plus query (and possibly
the team's shared variables) needs a Member or Owner token. Neither viewer role is yet
verified against a live team (see docs/standalone-discovery.md).
"""

import base64
import binascii
import json
import logging
import re
import time
from dataclasses import dataclass
from typing import Any, Callable, Mapping, Optional, Sequence, Union
from urllib.parse import quote

import requests

from discovery.retry import MAX_ATTEMPTS, RETRY_STATUSES, backoff_seconds
from job_executors.discovery_scan import DiscoveryConfigurationError

API_BASE_URL = "https://api.vercel.com"
# The dashboard host. Only Agent Runs is read here: see the module docstring.
DASHBOARD_BASE_URL = "https://vercel.com"

PROJECTS_PATH = "/v10/projects"
INTEGRATIONS_PATH = "/v1/integrations/configurations"
SHARED_ENV_PATH = "/v1/env"
AGENT_RUNS_PATH = "/api/observability/agent-runs"
OBSERVABILITY_QUERY_PATH = "/v2/observability/query"


def _segment(value: str) -> str:
    """One path segment. Vercel's ids are URL-safe already; this keeps them so."""
    return quote(value, safe="")


def project_env_path(project_id: str) -> str:
    return f"{PROJECTS_PATH}/{_segment(project_id)}/env"


def team_path(team_id: str) -> str:
    return f"/v2/teams/{_segment(team_id)}"


def deployment_files_path(deployment_id: str) -> str:
    return f"/v6/deployments/{_segment(deployment_id)}/files"


def deployment_file_path(deployment_id: str, file_id: str) -> str:
    return f"/v8/deployments/{_segment(deployment_id)}/files/{_segment(file_id)}"


# (connect, read). requests applies each separately, so together they must stay under
# Test Connection's 120s preview deadline (PREVIEW_DEADLINE_SECONDS). Vercel answers a
# list call in well under a second; the read timeout is generous headroom, not a guess
# at how long a call takes.
REQUEST_TIMEOUT_SECONDS = (10.0, 50.0)

# The most projects Vercel returns in one page of `GET /v10/projects`.
PROJECTS_PAGE_LIMIT = 100

# The most groups one observability query asks for.
OBSERVABILITY_QUERY_LIMIT = 100

# A package.json larger than this is not read: a real one is a few KiB, and the cap
# bounds what one deployment can make a scan hold. Checked on the base64 text before
# it is decoded (base64 is 4/3 of the bytes).
MAX_PACKAGE_JSON_BYTES = 512 * 1024

# Where a deployment's package.json is looked for in its file tree, in order. Vercel
# puts a CLI, API or v0 deployment's uploaded source under `src/`.
PACKAGE_JSON_PATHS: tuple[tuple[str, ...], ...] = (
    ("src", "package.json"),
    ("package.json",),
)

# A Vercel error body's `error.code` is an identifier like `forbidden` or `not_found`.
# Only that is carried into an exception's text: `error.message` is free text and can
# quote the team.
_ERROR_CODE = re.compile(r"^[A-Za-z0-9_.\-]{1,64}$")

# Deployment `meta` keys that only a Git deployment carries (`githubCommitSha`,
# `gitlabCommitRef`, `bitbucketCommitSha`, ...).
_GIT_META_PREFIXES = ("github", "gitlab", "bitbucket")


class VercelError(Exception):
    """A Vercel call that failed, carrying the HTTP status when Vercel answered.

    `status_code` is what `failure_code` and Test Connection read to tell a 401 from a
    host that never answered, so it is set whenever there was a response. `code` is
    Vercel's own error code when its body had one (`forbidden`, `not_found`, ...).
    """

    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        code: str = "",
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code


class ScanStopped(Exception):
    """The scan's stop check fired while a call was waiting to be retried.

    Never leaves the connector, which catches it and ends the scan as if the team had
    no more projects -- what `AcceptsStopCheck` asks of a connector told to stop.
    """


@dataclass(frozen=True)
class VercelSettings:
    """Which team to read, the token to read it with, and whether to read code."""

    team_id: str
    access_token: str
    timeout_seconds: tuple[float, float] = REQUEST_TIMEOUT_SECONDS
    read_deployment_sources: bool = False


@dataclass(frozen=True)
class DeploymentRef:
    """A project's latest production deployment, as far as reading its files goes."""

    id: str
    # Its `meta` names a Git commit, so Vercel keeps no file tree for it.
    from_git: bool


@dataclass(frozen=True)
class Project:
    """What a scan reads of one project. Everything else in the body is dropped."""

    id: str
    name: str
    # Epoch milliseconds of everything that says the project was alive: its production
    # deployment's readyAt/createdAt, its latest deployments' createdAt/readyAt, and
    # its own updatedAt. Empty when Vercel returned none.
    activity_ms: tuple[int, ...] = ()
    production_deployment: Optional[DeploymentRef] = None


# How to ask for the page after this one: ("until", "<timestamp>") or ("from", "<token>").
Cursor = tuple[str, str]


@dataclass(frozen=True)
class ProjectPage:
    projects: list[Project]
    next: Optional[Cursor]
    # Entries Vercel returned that had no project id, so cannot be addressed.
    unaddressable: int = 0


@dataclass(frozen=True)
class EnvVarName:
    """One environment variable, without its value. There is deliberately no field for
    the value: see the module docstring."""

    key: str
    type: Optional[str]
    targets: tuple[str, ...]


@dataclass(frozen=True)
class ProjectEnv:
    names: list[EnvVarName]
    # Production variables Vercel withheld from this token (`hiddenProductionEnvCount`).
    hidden_production_count: int = 0
    # Vercel said more variables exist than this one answer carried.
    more_pages: bool = False


@dataclass(frozen=True)
class SharedEnvVarName:
    """One team-shared variable, without its value, and the projects it is linked to."""

    key: str
    type: Optional[str]
    targets: tuple[str, ...]
    project_ids: frozenset[str]


@dataclass(frozen=True)
class SharedEnv:
    names: list[SharedEnvVarName]
    more_pages: bool = False


@dataclass(frozen=True)
class IntegrationConfiguration:
    """One installed integration, as far as attaching it to projects goes."""

    slug: str
    integration_id: Optional[str]
    tag_ids: frozenset[str]
    # The projects it may access; None when it may access every project in the team.
    project_ids: Optional[frozenset[str]]
    # False once Vercel reports it disabled or deleted.
    active: bool = True

    def covers(self, project_id: str) -> bool:
        return self.project_ids is None or project_id in self.project_ids


@dataclass(frozen=True)
class AgentRunsProject:
    """One project with Agent Runs: how Agent Runs named it, and its run count when
    the answer carried one."""

    project_id: Optional[str]
    project_name: Optional[str]
    runs: Optional[int]


@dataclass(frozen=True)
class MetricGroup:
    """One group of an observability query: its dimension values and its count, when
    the answer carried a number for it."""

    dimensions: Mapping[str, str]
    count: Optional[float]


@dataclass(frozen=True)
class MetricAnswer:
    groups: list[MetricGroup]
    # As many groups as were asked for came back, so there may be more.
    at_limit: bool = False


@dataclass(frozen=True)
class PackageManifest:
    """A package.json, cut down to the names of what it depends on."""

    path: str
    dependency_names: frozenset[str]


class VercelClient:
    """One team, one token. Every read a scan makes of Vercel."""

    def __init__(
        self,
        settings: VercelSettings,
        logger: Optional[logging.Logger] = None,
        session: Optional[requests.Session] = None,
        sleep: Callable[[float], None] = time.sleep,
        clock: Callable[[], float] = time.time,
    ) -> None:
        self._s = settings
        self._log = logger or logging.getLogger(__name__)
        self._http = session or requests.Session()
        self._sleep = sleep
        self._clock = clock
        self._should_stop: Callable[[], bool] = lambda: False

    def stop_when(self, should_stop: Callable[[], bool]) -> None:
        """Asked before each retry, so a backoff never outlives a stop request."""
        self._should_stop = should_stop

    def now(self) -> float:
        """Epoch seconds on the client's clock, which a time window is measured from."""
        return self._clock()

    # -- the inventory ------------------------------------------------------------------

    def projects_page(self, cursor: Optional[Cursor] = None) -> ProjectPage:
        """One page of the team's projects, and how to ask for the next."""
        params: dict[str, str] = {"limit": str(PROJECTS_PAGE_LIMIT)}
        if cursor is not None:
            params[cursor[0]] = cursor[1]
        resp = self._get(PROJECTS_PATH, params)
        if resp.status_code == 404:
            # Vercel's answer for a team that does not exist. The source's to fix, so it
            # carries no status_code and its text names no status, either of which Test
            # Connection would read as Vercel failing. Raised here, outside any except
            # block, so nothing is chained to it.
            raise DiscoveryConfigurationError(
                "Vercel found no team for the source's team_id. Use the team's ID "
                "(it starts team_), shown under the team's Settings > General, and a "
                "token created with access to that team.",
            )
        if resp.status_code != 200:
            raise _error(
                resp,
                "GET",
                PROJECTS_PATH,
                forbidden=(
                    ". Vercel refused the access_token for this team: the token is "
                    "invalid, expired or revoked (Vercel answers 403, not 401, for a "
                    "bad token), or it cannot see team_id because it was created for a "
                    "different team or its user is not a member (a viewer role is enough "
                    "to list projects). Create a new token under Account Settings > Tokens, "
                    "scoped to the team"
                ),
            )
        return _projects_page_from(resp)

    def project_env(self, project_id: str) -> ProjectEnv:
        """The names of one project's environment variables."""
        path = project_env_path(project_id)
        # No `decrypt`: see the module docstring.
        resp = self._get(path, {})
        if resp.status_code != 200:
            raise _error(
                resp,
                "GET",
                path,
                forbidden=(
                    ". The token can list this project but not read its environment "
                    "variables: its user needs a team role that can view this project"
                ),
            )
        return _env_from(resp, path)

    def integration_configurations(self) -> Optional[list[IntegrationConfiguration]]:
        """The team's installed integrations, or None when the token may not read them.

        A 403 is not fatal: environment variable names find most AI projects without
        it, and the connector says in the job log what was not checked.
        """
        resp = self._get(INTEGRATIONS_PATH, {"view": "account"})
        if resp.status_code == 403:
            return None
        if resp.status_code != 200:
            raise _error(resp, "GET", INTEGRATIONS_PATH, forbidden="")
        return _configurations_from(resp)

    # -- the extra signals: each raises VercelError, which the connector absorbs --------

    def shared_env(self) -> SharedEnv:
        """The names of the team's shared environment variables and their projects."""
        # No `decrypt`, and never `/v1/env/{id}`: see the module docstring.
        resp = self._get(SHARED_ENV_PATH, {})
        if resp.status_code != 200:
            raise _error(resp, "GET", SHARED_ENV_PATH, forbidden="")
        return _shared_env_from(resp)

    def team_slug(self) -> str:
        """The team's slug, from `GET /v2/teams/{teamId}`."""
        path = team_path(self._s.team_id)
        resp = self._get(path, {})
        if resp.status_code != 200:
            raise _error(resp, "GET", path, forbidden="")
        payload = _json(resp, "GET", path)
        slug = payload.get("slug") if isinstance(payload, dict) else None
        if not isinstance(slug, str) or not slug.strip():
            raise _malformed(resp, "GET", path, "a team with a slug")
        return slug.strip()

    def agent_runs_projects(
        self,
        team_slug: str,
        window: Optional[tuple[int, int]],
    ) -> list[AgentRunsProject]:
        """The team's projects with production Agent Runs. UNDOCUMENTED: see the module
        docstring. `window` is (from, to) in epoch seconds, as the CLI sends it.

        Addressed by `teamSlug` alone, without `teamId`, exactly as the CLI calls it.
        """
        params = {"teamSlug": team_slug, "view": "team", "environment": "production"}
        if window is not None:
            params["from"], params["to"] = str(window[0]), str(window[1])
        resp = self._send(
            "GET",
            DASHBOARD_BASE_URL,
            AGENT_RUNS_PATH,
            params,
            with_team_id=False,
        )
        if resp.status_code != 200:
            raise _error(resp, "GET", AGENT_RUNS_PATH, forbidden="")
        return _agent_runs_from(resp)

    def observability_query(
        self,
        metric: str,
        group_by: Sequence[str],
        window: tuple[str, str],
        granularity: Mapping[str, int],
        odata_filter: Optional[str] = None,
    ) -> MetricAnswer:
        """One Observability Plus query over the whole team, grouped by `group_by`.

        The body is shaped like `@vercel/sdk` 1.28.51's
        CreateObservabilityQueryRequestBody, with the scope and fields the Vercel CLI
        (65.2.0, `vercel metrics`) sends to this path: `{"type": "owner", "ownerId":
        <team id>}`, `aggregation` `sum`, ISO start and end times and a granularity.
        The SDK leaves the answer untyped; it is read as that CLI reads it: rows in
        `summary` (else `data`), each a flat object of dimension values and a rollup
        column named `<metric>_<aggregation>` with dots replaced by underscores.
        """
        body: dict[str, Any] = {
            "scope": {"type": "owner", "ownerId": self._s.team_id},
            "metric": metric,
            "aggregation": "sum",
            "groupBy": list(group_by),
            "startTime": window[0],
            "endTime": window[1],
            "granularity": dict(granularity),
            "limit": OBSERVABILITY_QUERY_LIMIT,
        }
        if odata_filter:
            body["filter"] = odata_filter
        resp = self._send("POST", API_BASE_URL, OBSERVABILITY_QUERY_PATH, {}, body)
        if resp.status_code != 200:
            raise _error(resp, "POST", OBSERVABILITY_QUERY_PATH, forbidden="")
        return _metric_answer_from(resp, metric, group_by)

    def deployment_package_json(self, deployment_id: str) -> Optional[PackageManifest]:
        """The dependency names in one deployment's package.json, or None when its
        file tree has none. A Git deployment's 404 is raised like any other status."""
        files = deployment_files_path(deployment_id)
        resp = self._get(files, {})
        if resp.status_code != 200:
            raise _error(resp, "GET", files, forbidden="")
        found = _package_json_in(_json(resp, "GET", files), resp, files)
        if found is None:
            return None
        path, file_id = found
        if self._should_stop():
            raise ScanStopped()
        contents = deployment_file_path(deployment_id, file_id)
        resp = self._get(contents, {})
        if resp.status_code != 200:
            raise _error(resp, "GET", contents, forbidden="")
        return PackageManifest(
            path=path,
            dependency_names=_dependency_names(resp, contents),
        )

    # -- transport ----------------------------------------------------------------------

    def _get(self, path: str, params: dict[str, str]) -> requests.Response:
        return self._send("GET", API_BASE_URL, path, params)

    def _send(
        self,
        method: str,
        base_url: str,
        path: str,
        params: dict[str, str],
        body: Optional[dict[str, Any]] = None,
        with_team_id: bool = True,
    ) -> requests.Response:
        """One call, retried when the failure passes. Every call is a read -- the one
        POST is a metrics query -- so repeating one is always safe."""
        url = base_url + path
        host = base_url.split("://", 1)[-1]
        query = {**params, "teamId": self._s.team_id} if with_team_id else dict(params)
        headers = {
            "Authorization": f"Bearer {self._s.access_token}",
            "Accept": "application/json",
        }
        for attempt in range(1, MAX_ATTEMPTS + 1):
            try:
                if method == "POST":
                    resp = self._http.post(
                        url,
                        params=query,
                        json=body,
                        headers=headers,
                        allow_redirects=False,
                        timeout=self._s.timeout_seconds,
                    )
                else:
                    resp = self._http.get(
                        url,
                        params=query,
                        headers=headers,
                        # The token is a header. requests drops Authorization on a
                        # redirect to another host, but refusing redirects says outright
                        # that this client only ever talks to Vercel's own hosts.
                        allow_redirects=False,
                        timeout=self._s.timeout_seconds,
                    )
            except requests.exceptions.SSLError as exc:
                # Not the source's settings -- it has none for TLS -- but the engine's:
                # Vercel's hosts have public certificates, so a failure means something
                # between the two re-signs traffic. Not retried: a certificate does not
                # change between attempts. The same type, so it still reads as network.
                raise type(exc)(
                    f"Vercel {method} {path}: TLS verification failed "
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
                # chain: it quotes the URL, query string and all.
                raise type(exc)(
                    f"Vercel {method} {path} unreachable after {MAX_ATTEMPTS} attempts "
                    f"({type(exc).__name__}). The engine needs outbound HTTPS to "
                    f"{host}.",
                ) from exc
            if resp.status_code in RETRY_STATUSES and attempt < MAX_ATTEMPTS:
                self._pause(backoff_seconds(attempt, self._retry_after(resp)))
                continue
            return resp
        raise AssertionError("unreachable: the last attempt returns or raises")

    def _pause(self, seconds: float) -> None:
        if self._should_stop():
            raise ScanStopped()
        self._sleep(seconds)

    def _retry_after(self, resp: requests.Response) -> Optional[str]:
        """Seconds to wait, from `Retry-After` or else Vercel's `X-RateLimit-Reset`
        (epoch seconds at which the window resets). `backoff_seconds` caps either."""
        retry_after = resp.headers.get("Retry-After")
        if retry_after:
            return str(retry_after)
        reset = resp.headers.get("X-RateLimit-Reset")
        if reset:
            try:
                return str(max(0.0, float(reset) - self._clock()))
            except ValueError:
                return None
        return None


# -- parsing ---------------------------------------------------------------------------
#
# A 200 is not always Vercel's: a proxy or captive portal can answer 200 with HTML. That,
# and a body that is JSON but not the shape asked for, is Vercel's error with its status
# rather than a bare ValueError or KeyError, which Test Connection would read as a
# configuration mistake.


def _json(resp: requests.Response, method: str, path: str) -> Any:
    try:
        return resp.json()
    except ValueError:
        raise VercelError(
            f"Vercel {method} {path} answered HTTP {resp.status_code} with a body that "
            f"is not JSON ({resp.headers.get('Content-Type') or 'no content type'}). "
            f"Something between the engine and Vercel answered instead.",
            status_code=resp.status_code,
        ) from None


def _malformed(
    resp: requests.Response,
    method: str,
    path: str,
    expected: str,
) -> VercelError:
    return VercelError(
        f"Vercel {method} {path} answered HTTP {resp.status_code} with JSON that is "
        f"not {expected}.",
        status_code=resp.status_code,
    )


def _projects_page_from(resp: requests.Response) -> ProjectPage:
    payload = _json(resp, "GET", PROJECTS_PATH)
    pagination: Any = None
    if isinstance(payload, dict) and isinstance(payload.get("projects"), list):
        raw_projects = payload["projects"]
        pagination = payload.get("pagination")
    elif isinstance(payload, list):
        # The SDK models a bare array too, with no pagination: one page, all there is.
        raw_projects = payload
    else:
        raise _malformed(resp, "GET", PROJECTS_PATH, "a list of projects")

    projects: list[Project] = []
    unaddressable = 0
    for raw in raw_projects:
        project = _project_from(raw)
        if project is None:
            unaddressable += 1
        else:
            projects.append(project)
    return ProjectPage(
        projects=projects,
        next=_cursor_from(pagination),
        unaddressable=unaddressable,
    )


def _project_from(raw: Any) -> Optional[Project]:
    if not isinstance(raw, dict):
        return None
    project_id = raw.get("id")
    if not isinstance(project_id, str) or not project_id.strip():
        return None
    name = raw.get("name")

    activity: list[Optional[int]] = [_ms(raw.get("updatedAt"))]
    targets = raw.get("targets")
    production = targets.get("production") if isinstance(targets, dict) else None
    if isinstance(production, dict):
        activity += [_ms(production.get("readyAt")), _ms(production.get("createdAt"))]
    deployments = raw.get("latestDeployments")
    if isinstance(deployments, list):
        for deployment in deployments:
            if isinstance(deployment, dict):
                activity += [
                    _ms(deployment.get("readyAt")),
                    _ms(deployment.get("createdAt")),
                ]

    return Project(
        id=project_id,
        name=name if isinstance(name, str) and name.strip() else project_id,
        activity_ms=tuple(ms for ms in activity if ms is not None),
        production_deployment=_production_deployment(production, deployments),
    )


def _production_deployment(production: Any, latest: Any) -> Optional[DeploymentRef]:
    """`targets.production`, else the newest production entry of `latestDeployments`."""
    candidates: list[dict[str, Any]] = []
    if isinstance(production, dict):
        candidates.append(production)
    elif isinstance(latest, list):
        candidates = sorted(
            (
                d
                for d in latest
                if isinstance(d, dict) and d.get("target") == "production"
            ),
            key=lambda d: _ms(d.get("createdAt")) or 0,
            reverse=True,
        )
    for deployment in candidates:
        deployment_id = deployment.get("id") or deployment.get("uid")
        if isinstance(deployment_id, str) and deployment_id.strip():
            meta = deployment.get("meta")
            from_git = isinstance(meta, dict) and any(
                isinstance(key, str) and key.lower().startswith(_GIT_META_PREFIXES)
                for key in meta
            )
            return DeploymentRef(id=deployment_id, from_git=from_git)
    return None


def _ms(value: Any) -> Optional[int]:
    """An epoch-milliseconds timestamp, or None for anything that is not one."""
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value <= 0:
        return None
    return int(value)


def _cursor_from(pagination: Any) -> Optional[Cursor]:
    """The next page's parameter: a number goes back as `until`, a token as `from`."""
    if not isinstance(pagination, dict):
        return None
    following: Union[None, bool, int, float, str] = pagination.get("next")
    if following is None or isinstance(following, bool):
        return None
    if isinstance(following, (int, float)):
        return ("until", str(int(following)))
    if isinstance(following, str) and following.strip():
        return ("from", following)
    return None


def _targets(target: Any) -> tuple[str, ...]:
    if isinstance(target, str):
        return (target,)
    if isinstance(target, list):
        return tuple(t for t in target if isinstance(t, str))
    return ()


def _env_from(resp: requests.Response, path: str) -> ProjectEnv:
    payload = _json(resp, "GET", path)
    hidden = 0
    more_pages = False
    if isinstance(payload, dict) and isinstance(payload.get("envs"), list):
        entries = payload["envs"]
        count = payload.get("hiddenProductionEnvCount")
        if isinstance(count, int) and not isinstance(count, bool):
            hidden = count
        pagination = payload.get("pagination")
        more_pages = isinstance(pagination, dict) and pagination.get("next") is not None
    elif isinstance(payload, list):
        entries = payload
    elif isinstance(payload, dict) and isinstance(payload.get("key"), str):
        # The SDK also models a single variable as the whole answer.
        entries = [payload]
    else:
        raise _malformed(resp, "GET", path, "a list of environment variables")

    names: list[EnvVarName] = []
    for entry in entries:
        if not isinstance(entry, dict) or not isinstance(entry.get("key"), str):
            continue
        # Only these three are read; `value` is never touched.
        kind = entry.get("type")
        names.append(
            EnvVarName(
                key=entry["key"],
                type=kind if isinstance(kind, str) else None,
                targets=_targets(entry.get("target")),
            ),
        )
    return ProjectEnv(
        names=names,
        hidden_production_count=hidden,
        more_pages=more_pages,
    )


def _shared_env_from(resp: requests.Response) -> SharedEnv:
    """`{"data": [...], "pagination": {...}}`, shaped like `@vercel/sdk` 1.28.51's
    ListSharedEnvVariableResponseBody. Each entry's `projectId` is the list of projects
    it is linked to."""
    payload = _json(resp, "GET", SHARED_ENV_PATH)
    more_pages = False
    if isinstance(payload, dict) and isinstance(payload.get("data"), list):
        entries = payload["data"]
        pagination = payload.get("pagination")
        more_pages = isinstance(pagination, dict) and pagination.get("next") is not None
    elif isinstance(payload, list):
        entries = payload
    else:
        raise _malformed(resp, "GET", SHARED_ENV_PATH, "a list of shared variables")

    names: list[SharedEnvVarName] = []
    for entry in entries:
        if not isinstance(entry, dict) or not isinstance(entry.get("key"), str):
            continue
        if entry.get("deletedAt"):
            continue
        # Only these four are read; `value` is never touched.
        kind = entry.get("type")
        projects = entry.get("projectId")
        if isinstance(projects, str):
            project_ids = frozenset({projects})
        elif isinstance(projects, list):
            project_ids = frozenset(p for p in projects if isinstance(p, str))
        else:
            project_ids = frozenset()
        names.append(
            SharedEnvVarName(
                key=entry["key"],
                type=kind if isinstance(kind, str) else None,
                targets=_targets(entry.get("target")),
                project_ids=project_ids,
            ),
        )
    return SharedEnv(names=names, more_pages=more_pages)


def _configurations_from(resp: requests.Response) -> list[IntegrationConfiguration]:
    payload = _json(resp, "GET", INTEGRATIONS_PATH)
    if isinstance(payload, dict) and isinstance(payload.get("configurations"), list):
        entries = payload["configurations"]
    elif isinstance(payload, list):
        entries = payload
    else:
        raise _malformed(
            resp,
            "GET",
            INTEGRATIONS_PATH,
            "a list of integration configurations",
        )

    configurations: list[IntegrationConfiguration] = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        slug = entry.get("slug")
        integration_id = entry.get("integrationId")
        tags: set[str] = set()
        for holder in (entry, entry.get("integration")):
            if isinstance(holder, dict) and isinstance(holder.get("tagIds"), list):
                tags.update(t for t in holder["tagIds"] if isinstance(t, str))
        projects = entry.get("projects")
        configurations.append(
            IntegrationConfiguration(
                slug=slug.strip().lower() if isinstance(slug, str) else "",
                integration_id=(
                    integration_id if isinstance(integration_id, str) else None
                ),
                tag_ids=frozenset(tags),
                # Vercel leaves `projects` out for a configuration with access to every
                # project; "all" is accepted as the same thing.
                project_ids=(
                    frozenset(p for p in projects if isinstance(p, str))
                    if isinstance(projects, list)
                    else None
                ),
                active=not entry.get("deletedAt") and not entry.get("disabledAt"),
            ),
        )
    return configurations


def _first_string(entry: Mapping[str, Any], *keys: str) -> Optional[str]:
    for key in keys:
        value = entry.get(key)
        if isinstance(value, str) and value:
            return value
    return None


def _first_count(entry: Mapping[str, Any], *keys: str) -> Optional[int]:
    for key in keys:
        value = entry.get(key)
        if isinstance(value, bool):
            continue
        if isinstance(value, (int, float)):
            return int(value)
    return None


def _agent_runs_from(resp: requests.Response) -> list[AgentRunsProject]:
    """Read as the Vercel CLI 65.2.0 reads `vercel agent-runs projects`: `projects`,
    else `items`, each entry an object."""
    payload = _json(resp, "GET", AGENT_RUNS_PATH)
    entries: Any = None
    if isinstance(payload, dict):
        entries = payload.get("projects")
        if not isinstance(entries, list):
            entries = payload.get("items")
    if not isinstance(entries, list):
        raise _malformed(resp, "GET", AGENT_RUNS_PATH, "a list of projects")

    found: list[AgentRunsProject] = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        project = entry.get("project")
        nested = project if isinstance(project, dict) else {}
        project_id = _first_string(entry, "projectId") or _first_string(nested, "id")
        project_name = (
            _first_string(entry, "projectName", "name")
            or _first_string(nested, "name")
            or (project if isinstance(project, str) and project else None)
            or _first_string(entry, "id")
        )
        if project_id is None and project_name is None:
            continue
        found.append(
            AgentRunsProject(
                project_id=project_id,
                project_name=project_name,
                runs=_first_count(entry, "runs", "runCount", "totalRuns"),
            ),
        )
    return found


def rollup_column(metric: str, aggregation: str = "sum") -> str:
    """The column a query answers its value in, named as the Vercel CLI names it."""
    return re.sub(r"[./]", "_", f"{metric}_{aggregation}")


def _number(value: Any) -> Optional[float]:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return None
    return None


def _metric_answer_from(
    resp: requests.Response,
    metric: str,
    group_by: Sequence[str],
) -> MetricAnswer:
    payload = _json(resp, "POST", OBSERVABILITY_QUERY_PATH)
    rows: Any = None
    if isinstance(payload, dict):
        rows = payload.get("summary")
        if not isinstance(rows, list) or not rows:
            rows = payload.get("data", rows)
    if not isinstance(rows, list):
        raise _malformed(resp, "POST", OBSERVABILITY_QUERY_PATH, "grouped metric rows")

    column = rollup_column(metric)
    # A time series repeats a group once per bucket; its counts are summed.
    totals: dict[tuple[tuple[str, str], ...], Optional[float]] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        dimensions = tuple(
            (name, row[name]) for name in group_by if isinstance(row.get(name), str)
        )
        if not dimensions:
            continue
        count = _number(row.get(column))
        if dimensions in totals:
            previous = totals[dimensions]
            totals[dimensions] = (
                None if previous is None or count is None else previous + count
            )
        else:
            totals[dimensions] = count
    return MetricAnswer(
        groups=[MetricGroup(dict(d), c) for d, c in totals.items()],
        at_limit=len(rows) >= OBSERVABILITY_QUERY_LIMIT,
    )


def _package_json_in(
    tree: Any,
    resp: requests.Response,
    path: str,
) -> Optional[tuple[str, str]]:
    """The (path, file id) of the first of `PACKAGE_JSON_PATHS` in a file tree shaped
    like `@vercel/sdk` 1.28.51's FileTree array."""
    if not isinstance(tree, list):
        raise _malformed(resp, "GET", path, "a file tree")
    for wanted in PACKAGE_JSON_PATHS:
        level: Any = tree
        node: Optional[dict[str, Any]] = None
        for part in wanted:
            node = _child(level, part)
            if node is None:
                break
            level = node.get("children")
        if node is not None and node.get("type") == "file":
            uid = node.get("uid")
            if isinstance(uid, str) and uid.strip():
                return "/".join(wanted), uid
    return None


def _child(level: Any, name: str) -> Optional[dict[str, Any]]:
    """The entry called `name` in one level of a file tree."""
    if not isinstance(level, list):
        return None
    for node in level:
        if isinstance(node, dict) and node.get("name") == name:
            return node
    return None


def _dependency_names(resp: requests.Response, path: str) -> frozenset[str]:
    """The names under `dependencies`, `devDependencies`, `peerDependencies` and
    `optionalDependencies` of a base64 package.json. NOTHING ELSE OF THE FILE IS KEPT,
    and a failure says what was wrong with it, never what it said."""
    payload = _json(resp, "GET", path)
    encoded: Any = payload
    if isinstance(payload, dict):
        encoded = next(
            (
                payload[k]
                for k in ("data", "content", "contents")
                if isinstance(payload.get(k), str)
            ),
            None,
        )
    if not isinstance(encoded, str):
        raise _malformed(resp, "GET", path, "base64 file contents")
    if len(encoded) > MAX_PACKAGE_JSON_BYTES * 4 // 3 + 4:
        raise VercelError(
            f"Vercel GET {path}: package.json is larger than "
            f"{MAX_PACKAGE_JSON_BYTES // 1024} KiB, so it was not read.",
            status_code=resp.status_code,
        )
    try:
        manifest = json.loads(base64.b64decode(encoded, validate=False))
    except (binascii.Error, ValueError):
        raise VercelError(
            f"Vercel GET {path}: package.json is not base64 JSON, so it was not read.",
            status_code=resp.status_code,
        ) from None
    if not isinstance(manifest, dict):
        raise VercelError(
            f"Vercel GET {path}: package.json is not a JSON object, so it was not read.",
            status_code=resp.status_code,
        )
    names: set[str] = set()
    for section in (
        "dependencies",
        "devDependencies",
        "peerDependencies",
        "optionalDependencies",
    ):
        block = manifest.get(section)
        if isinstance(block, dict):
            names.update(k for k in block if isinstance(k, str))
    return frozenset(names)


def _error(
    resp: requests.Response,
    method: str,
    path: str,
    forbidden: str,
) -> VercelError:
    """Vercel's non-2xx answer, with its status, its error code and a hint."""
    code = _error_code(resp)
    suffix = f" ({code})" if code else ""
    return VercelError(
        f"Vercel {method} {path} failed with HTTP {resp.status_code}{suffix}"
        f"{_hint(resp.status_code, forbidden)}",
        status_code=resp.status_code,
        code=code,
    )


def _error_code(resp: requests.Response) -> str:
    try:
        body = resp.json()
    except ValueError:
        return ""
    error = body.get("error") if isinstance(body, dict) else None
    code = error.get("code") if isinstance(error, dict) else None
    return code if isinstance(code, str) and _ERROR_CODE.match(code) else ""


def _hint(status: int, forbidden: str) -> str:
    if status == 401:
        return (
            ". The access_token was rejected: it is invalid, expired or revoked. "
            "Create a new token under Account Settings > Tokens, scoped to the team"
        )
    if status == 403:
        return forbidden
    if status == 429:
        return ". Vercel's rate limit held through every retry; scan less often"
    return ""
