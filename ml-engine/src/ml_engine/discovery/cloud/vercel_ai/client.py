"""Vercel's REST API, as far as a discovery scan needs it.

THREE READS, ALL GETS. A scan lists the team's projects (`GET /v10/projects`, paged),
reads each in-scope project's environment variables (`GET /v10/projects/{id}/env`), and
reads the team's integration configurations once (`GET /v1/integrations/configurations`).
Every call carries `teamId`, so a token that can see several teams only ever reads the
one the source names. All three are reads, so all three are retried on 429 and 5xx.

NAMES, NEVER VALUES. The env endpoint returns each variable's value alongside its name:
encrypted for `encrypted`/`sensitive`/`secret` variables, but PLAINTEXT for `plain` ones.
Nothing here asks for more than that -- `decrypt` is never sent, and the single-variable
endpoint `/v1/projects/{id}/env/{envId}`, which decrypts, is never called -- and what
does arrive is cut down to `key`, `type` and `target` the moment the body is parsed. A
value never reaches a dataclass, a log line or an exception's text. The project list
carries an `env` array of its own; it is not read for the same reason.

HOW THE PROJECT LIST PAGES. `pagination.next` is either a number (an `updatedAt`
timestamp, sent back as `until`) or, on newer accounts, a base32 continuation token
(sent back as `from`); the Vercel SDK models both. `null` ends the list. The connector
walks the pages so it can check its stop between them; this client makes one call per
method.

Authenticated with a Vercel access token, `Authorization: Bearer <token>`. Vercel
tokens carry the permissions of the user who created them within the team chosen at
creation; there is no read-only token scope, so least privilege is a matter of whose
token it is and how long it lives (see docs/standalone-discovery.md).
"""

import logging
import re
import time
from dataclasses import dataclass
from typing import Any, Callable, Optional, Union

import requests

from discovery.retry import MAX_ATTEMPTS, RETRY_STATUSES, backoff_seconds
from job_executors.discovery_scan import DiscoveryConfigurationError

API_BASE_URL = "https://api.vercel.com"

PROJECTS_PATH = "/v10/projects"
INTEGRATIONS_PATH = "/v1/integrations/configurations"


def project_env_path(project_id: str) -> str:
    return f"{PROJECTS_PATH}/{project_id}/env"


# (connect, read). requests applies each separately, so together they must stay under
# Test Connection's 120s preview deadline (PREVIEW_DEADLINE_SECONDS). Vercel answers a
# list call in well under a second; the read timeout is generous headroom, not a guess
# at how long a call takes.
REQUEST_TIMEOUT_SECONDS = (10.0, 50.0)

# The most projects Vercel returns in one page of `GET /v10/projects`.
PROJECTS_PAGE_LIMIT = 100

# A Vercel error body's `error.code` is an identifier like `forbidden` or `not_found`.
# Only that is carried into an exception's text: `error.message` is free text and can
# quote the team.
_ERROR_CODE = re.compile(r"^[A-Za-z0-9_.\-]{1,64}$")


class VercelError(Exception):
    """A Vercel call that failed, carrying the HTTP status when Vercel answered.

    `status_code` is what `failure_code` and Test Connection read to tell a 401 from a
    host that never answered, so it is set whenever there was a response.
    """

    def __init__(self, message: str, status_code: Optional[int] = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class ScanStopped(Exception):
    """The scan's stop check fired while a call was waiting to be retried.

    Never leaves the connector, which catches it and ends the scan as if the team had
    no more projects -- what `AcceptsStopCheck` asks of a connector told to stop.
    """


@dataclass(frozen=True)
class VercelSettings:
    """Which team to read and the token to read it with."""

    team_id: str
    access_token: str
    timeout_seconds: tuple[float, float] = REQUEST_TIMEOUT_SECONDS


@dataclass(frozen=True)
class Project:
    """What a scan reads of one project. Everything else in the body is dropped."""

    id: str
    name: str
    region: Optional[str]
    # Epoch milliseconds of everything that says the project was alive: its production
    # deployment's readyAt/createdAt, its latest deployments' createdAt/readyAt, and
    # its own updatedAt. Empty when Vercel returned none.
    activity_ms: tuple[int, ...] = ()


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


class VercelClient:
    """One team, one token. Lists projects, their variable names and integrations."""

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
                PROJECTS_PATH,
                forbidden=(
                    ". The token cannot list projects in this team: it was created for "
                    "a different team, or its user is not a member of team_id"
                ),
            )
        return _projects_page_from(resp)

    def project_env(self, project_id: str) -> Optional[ProjectEnv]:
        """The names of one project's environment variables, or None if the project no
        longer exists (deleted between the listing and this call)."""
        path = project_env_path(project_id)
        # No `decrypt`: see the module docstring.
        resp = self._get(path, {})
        if resp.status_code == 404:
            return None
        if resp.status_code != 200:
            raise _error(
                resp,
                path,
                forbidden=(
                    ". The token can list this project but not read its environment "
                    "variables: its user needs a team role that can view project "
                    "settings"
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
            raise _error(resp, INTEGRATIONS_PATH, forbidden="")
        return _configurations_from(resp)

    def _get(self, path: str, params: dict[str, str]) -> requests.Response:
        """One GET, retried when the failure passes. Every call is a read, so repeating
        one is always safe."""
        url = API_BASE_URL + path
        for attempt in range(1, MAX_ATTEMPTS + 1):
            try:
                resp = self._http.get(
                    url,
                    params={**params, "teamId": self._s.team_id},
                    headers={
                        "Authorization": f"Bearer {self._s.access_token}",
                        "Accept": "application/json",
                    },
                    # The token is a header. requests drops Authorization on a redirect
                    # to another host, but refusing redirects says outright that this
                    # client only ever talks to api.vercel.com.
                    allow_redirects=False,
                    timeout=self._s.timeout_seconds,
                )
            except requests.exceptions.SSLError as exc:
                # Not the source's settings -- it has none for TLS -- but the engine's:
                # api.vercel.com has a public certificate, so a failure means something
                # between the two re-signs traffic. Not retried: a certificate does not
                # change between attempts. The same type, so it still reads as network.
                raise type(exc)(
                    f"Vercel GET {path}: TLS verification failed "
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
                    f"Vercel GET {path} unreachable after {MAX_ATTEMPTS} attempts "
                    f"({type(exc).__name__}). The engine needs outbound HTTPS to "
                    f"api.vercel.com.",
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


def _json(resp: requests.Response, path: str) -> Any:
    try:
        return resp.json()
    except ValueError:
        raise VercelError(
            f"Vercel GET {path} answered HTTP {resp.status_code} with a body that is "
            f"not JSON ({resp.headers.get('Content-Type') or 'no content type'}). "
            f"Something between the engine and api.vercel.com answered instead.",
            status_code=resp.status_code,
        ) from None


def _malformed(resp: requests.Response, path: str, expected: str) -> VercelError:
    return VercelError(
        f"Vercel GET {path} answered HTTP {resp.status_code} with JSON that is not "
        f"{expected}.",
        status_code=resp.status_code,
    )


def _projects_page_from(resp: requests.Response) -> ProjectPage:
    payload = _json(resp, PROJECTS_PATH)
    pagination: Any = None
    if isinstance(payload, dict) and isinstance(payload.get("projects"), list):
        raw_projects = payload["projects"]
        pagination = payload.get("pagination")
    elif isinstance(payload, list):
        # The SDK models a bare array too, with no pagination: one page, all there is.
        raw_projects = payload
    else:
        raise _malformed(resp, PROJECTS_PATH, "a list of projects")

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
    region = raw.get("serverlessFunctionRegion")

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
        region=region if isinstance(region, str) and region.strip() else None,
        activity_ms=tuple(ms for ms in activity if ms is not None),
    )


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


def _env_from(resp: requests.Response, path: str) -> ProjectEnv:
    payload = _json(resp, path)
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
        raise _malformed(resp, path, "a list of environment variables")

    names: list[EnvVarName] = []
    for entry in entries:
        if not isinstance(entry, dict) or not isinstance(entry.get("key"), str):
            continue
        # Only these three are read; `value` is never touched.
        kind = entry.get("type")
        target = entry.get("target")
        if isinstance(target, str):
            targets: tuple[str, ...] = (target,)
        elif isinstance(target, list):
            targets = tuple(t for t in target if isinstance(t, str))
        else:
            targets = ()
        names.append(
            EnvVarName(
                key=entry["key"],
                type=kind if isinstance(kind, str) else None,
                targets=targets,
            ),
        )
    return ProjectEnv(
        names=names,
        hidden_production_count=hidden,
        more_pages=more_pages,
    )


def _configurations_from(resp: requests.Response) -> list[IntegrationConfiguration]:
    payload = _json(resp, INTEGRATIONS_PATH)
    if isinstance(payload, dict) and isinstance(payload.get("configurations"), list):
        entries = payload["configurations"]
    elif isinstance(payload, list):
        entries = payload
    else:
        raise _malformed(
            resp,
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


def _error(resp: requests.Response, path: str, forbidden: str) -> VercelError:
    """Vercel's non-2xx answer, with its status, its error code and a hint."""
    code = _error_code(resp)
    suffix = f" ({code})" if code else ""
    return VercelError(
        f"Vercel GET {path} failed with HTTP {resp.status_code}{suffix}"
        f"{_hint(resp.status_code, forbidden)}",
        status_code=resp.status_code,
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
