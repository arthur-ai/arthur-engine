"""Vercel connector: the inventory, the extra signals, the heuristic and the records.

A fake session stands in for api.vercel.com and vercel.com, routed by path. NONE of its
bodies is captured from a live team: neither host is reachable from where these were
written. Each pinned body is named for what it is shaped on:

* `@vercel/sdk` 1.28.43 (getProjects, filterProjectEnvs, getConfigurations) and 1.28.51
  (listSharedEnvVariable, getTeam, createObservabilityQuery's request body,
  listDeploymentFiles' FileTree);
* the Vercel CLI 65.2.0, for what the SDK leaves untyped: how `vercel agent-runs
  projects` reads the undocumented Agent Runs answer, and how `vercel metrics` reads an
  observability query's rows;
* Vercel's API reference for file contents ("a JSON response containing the contents
  of the file encoded as base64"), whose key, `data`, is an assumption.

The tests that matter most are the value tests. Vercel's env endpoint returns a `plain`
variable's value in cleartext beside its name, so a single careless log line or record
field would copy a customer's configuration into the Platform. Every path that touches
an env body is run here with a recognisable plaintext value and checked for it.
"""

import base64
import json
import logging
from datetime import datetime, timezone
from typing import Any, Callable, Optional, Sequence, Union
from urllib.parse import urlsplit

import pytest
import requests
from arthur_client.api_bindings import DiscoverySourceConfigSpec
from arthur_common.models.agent_governance_schemas import CloudAgentCreationSource

from discovery import source_connectors
from discovery.cloud.vercel_ai import connector as vercel
from discovery.cloud.vercel_ai.client import (
    AGENT_RUNS_PATH,
    API_BASE_URL,
    DASHBOARD_BASE_URL,
    INTEGRATIONS_PATH,
    OBSERVABILITY_QUERY_PATH,
    PROJECTS_PATH,
    SHARED_ENV_PATH,
    EnvVarName,
    SharedEnvVarName,
    VercelClient,
    VercelError,
    VercelSettings,
    deployment_file_path,
    deployment_files_path,
    rollup_column,
    team_path,
)
from discovery.cloud.vercel_ai.connector import (
    ACCESS_TOKEN_FIELD,
    ACTIVITY_WINDOW_MAX_HOURS,
    AI_GATEWAY_METRIC,
    AI_INTEGRATION_SLUGS,
    BATCH_SIZE,
    EXTERNAL_API_METRIC,
    GLOBAL_SCOPE,
    INCLUDE_PROJECTS_FIELD,
    LLM_PROVIDER_ENV_KEYS,
    READ_DEPLOYMENT_SOURCES_FIELD,
    TEAM_ID_FIELD,
    VENDOR,
    VercelConnector,
    activity_window,
    granularity_for,
    is_ai_package,
    is_llm_host,
    llm_host_filter,
    settings_from,
)
from discovery.retry import MAX_ATTEMPTS
from job_executors.discovery_output_contract import check_batch
from job_executors.discovery_scan import (
    AcceptsStopCheck,
    DiscoveryConfigurationError,
    DiscoveryErrorCode,
    DiscoveryPublishResult,
    DiscoveryScanOutcome,
    failure_code,
    run_source_scan,
)

LOG = logging.getLogger("test.vercel_ai")
TEAM_ID = "team_a1B2c3D4e5F6g7H8i9J0k1L2"
TOKEN = "vercel-test-token-not-real-0123456789"
CREDS = {"access_token": TOKEN}
FIELDS = {"team_id": TEAM_ID}

# What must never leave the client: a `plain` variable's value is cleartext on the wire.
PLAIN_VALUE = "plaintext-value-that-must-never-leak"
ENCRYPTED_VALUE = "eyJ2IjoiZW5jcnlwdGVkLWJsb2Itbm90LXJlYWwifQ=="

T_CREATED = 1_756_684_800_000  # 2025-09-01T00:00:00Z
T_UPDATED = 1_759_276_800_000  # 2025-10-01T00:00:00Z
T_DEPLOYED = 1_759_363_200_000  # 2025-10-02T00:00:00Z
T_READY = 1_759_363_260_000  # 2025-10-02T00:01:00Z


def utc(ms: int) -> datetime:
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc)


# -- bodies shaped like @vercel/sdk 1.28.43's models -------------------------------------


def deployment(ms: int, ready_ms: Optional[int] = None, **extra: Any) -> dict[str, Any]:
    body: dict[str, Any] = {
        "id": f"dpl_{ms}",
        "createdAt": ms,
        "createdIn": "sfo1",
        "creator": {"uid": "usr_1", "username": "dev"},
        "deploymentHostname": "support-chat-abc123-team.vercel.app",
        "name": "support-chat",
        "plan": "pro",
        "private": True,
        "readyState": "READY",
        "target": "production",
        "type": "LAMBDAS",
        "url": "support-chat-abc123-team.vercel.app",
    }
    if ready_ms is not None:
        body["readyAt"] = ready_ms
    body.update(extra)
    return body


def project(
    pid: str,
    name: str,
    *,
    region: Optional[str] = "iad1",
    updated: Optional[int] = T_UPDATED,
    production: Optional[dict[str, Any]] = None,
    deployments: Optional[list[dict[str, Any]]] = None,
    **extra: Any,
) -> dict[str, Any]:
    """A `GET /v10/projects` entry, with the required fields the SDK model declares and
    an inline `env` carrying a plaintext value the connector must not read."""
    body: dict[str, Any] = {
        "accountId": TEAM_ID,
        "alias": [],
        "createdAt": T_CREATED,
        "deploymentExpiration": {"expirationDays": 180},
        "directoryListing": False,
        "env": [
            {
                "key": "SESSION_SECRET",
                "type": "plain",
                "value": PLAIN_VALUE,
                "target": ["production"],
            },
        ],
        "framework": "nextjs",
        "id": pid,
        "name": name,
        "nodeVersion": "22.x",
        "resourceConfig": {"functionDefaultRegions": ["iad1"]},
    }
    if region is not None:
        body["serverlessFunctionRegion"] = region
    if updated is not None:
        body["updatedAt"] = updated
    if production is not None:
        body["targets"] = {"production": production}
    if deployments is not None:
        body["latestDeployments"] = deployments
    body.update(extra)
    return body


def env_var(key: str, kind: str = "encrypted", **extra: Any) -> dict[str, Any]:
    """A `GET /v10/projects/{id}/env` entry. A plain one carries PLAIN_VALUE in clear."""
    body: dict[str, Any] = {
        "configurationId": None,
        "createdAt": T_CREATED,
        "createdBy": "usr_1",
        "decrypted": False,
        "id": f"env_{key.lower()}",
        "key": key,
        "securityIssues": [],
        "target": ["production", "preview"],
        "type": kind,
        "updatedAt": T_UPDATED,
        "value": PLAIN_VALUE if kind == "plain" else ENCRYPTED_VALUE,
    }
    body.update(extra)
    return body


def envs(*entries: dict[str, Any], hidden: int = 0) -> dict[str, Any]:
    return {"envs": list(entries), "hiddenProductionEnvCount": hidden}


def configuration(
    slug: str,
    *,
    projects: Union[list[str], str, None, object] = None,
    tags: Sequence[str] = (),
    **extra: Any,
) -> dict[str, Any]:
    """A `GET /v1/integrations/configurations?view=account` entry. `projects` left as
    the sentinel `ALL` is omitted, which is how Vercel says every project."""
    body: dict[str, Any] = {
        "createdAt": T_CREATED,
        "id": f"icfg_{slug}",
        "integration": {
            "icon": "https://vercel.com/api/www/avatar/x",
            "isLegacy": False,
            "name": slug,
            "tagIds": list(tags),
        },
        "integrationId": f"oac_{slug}",
        "ownerId": TEAM_ID,
        "scopes": ["read:project", "read-write:integration-resource"],
        "slug": slug,
        "source": "marketplace",
        "installationType": "marketplace",
        "type": "integration-configuration",
        "updatedAt": T_UPDATED,
        "userId": "usr_1",
    }
    if projects is not ALL:
        body["projects"] = projects
    body.update(extra)
    return body


ALL = object()

# A whole page, an env answer and an integrations answer, shaped field for field on the
# SDK's GetProjectsResponseBody2 / FilterProjectEnvsResponseBody3 /
# GetConfigurationsResponseBody2. Not captured live: see the module docstring.
PROJECTS_SHAPED_LIKE_VERCEL_SDK_1_28_43: dict[str, Any] = {
    "projects": [
        project(
            "prj_chat",
            "support-chat",
            production=deployment(T_DEPLOYED, T_READY),
            deployments=[deployment(T_DEPLOYED, T_READY)],
        ),
        project("prj_docs", "docs-site", region="fra1"),
        project("prj_img", "image-studio", region=None),
    ],
    "pagination": {"count": 3, "next": None, "prev": T_CREATED},
}
ENVS_SHAPED_LIKE_VERCEL_SDK_1_28_43: dict[str, Any] = envs(
    env_var("OPENAI_API_KEY", "sensitive"),
    env_var("NEXT_PUBLIC_SITE_URL", "plain", target=["production"]),
    env_var("DATABASE_URL", "encrypted", target="production"),
)
CONFIGURATIONS_SHAPED_LIKE_VERCEL_SDK_1_28_43: list[dict[str, Any]] = [
    configuration("xai", projects=["prj_img"], tags=["tag_ai"]),
    configuration("neon", projects=ALL, tags=["tag_storage"]),
]

TEAM_SLUG = "acme-ai"
# `GET /v2/teams/{teamId}`, the fields of @vercel/sdk 1.28.51's GetTeamResponseBody a
# scan could see; only `slug` is read.
TEAM_SHAPED_LIKE_VERCEL_SDK_1_28_51: dict[str, Any] = {
    "id": TEAM_ID,
    "slug": TEAM_SLUG,
    "name": "Acme AI",
    "createdAt": T_CREATED,
    "membership": {"role": "VIEWER", "confirmed": True},
}


def shared_var(
    key: str,
    projects: Sequence[str],
    kind: str = "encrypted",
    target: Sequence[str] = ("production", "preview"),
    **extra: Any,
) -> dict[str, Any]:
    """A `GET /v1/env` entry (ListSharedEnvVariableData). A plain one is cleartext."""
    body: dict[str, Any] = {
        "created": "2025-09-01T00:00:00.000Z",
        "createdAt": T_CREATED,
        "decrypted": False,
        "id": f"env_shared_{key.lower()}",
        "key": key,
        "ownerId": TEAM_ID,
        "projectId": list(projects),
        "securityIssues": [],
        "target": list(target),
        "type": kind,
        "updatedAt": T_UPDATED,
        "value": PLAIN_VALUE if kind == "plain" else ENCRYPTED_VALUE,
    }
    body.update(extra)
    return body


def shared(*entries: dict[str, Any], following: Any = None) -> dict[str, Any]:
    return {
        "data": list(entries),
        "pagination": {"count": len(entries), "next": following, "prev": None},
    }


SHARED_ENV_SHAPED_LIKE_VERCEL_SDK_1_28_51 = shared(
    shared_var("SENTRY_DSN", ["prj_chat", "prj_docs"], "plain"),
)


def agent_runs(*entries: dict[str, Any]) -> dict[str, Any]:
    """What `vercel agent-runs projects` (CLI 65.2.0) reads: `projects`, each naming
    its project and run count by one of the keys it tries."""
    return {"projects": list(entries)}


def runs_entry(pid: str, name: str, runs: Optional[int] = 3) -> dict[str, Any]:
    entry: dict[str, Any] = {
        "projectId": pid,
        "projectName": name,
        "avgDurationMs": 5400,
    }
    if runs is not None:
        entry["runs"] = runs
    return entry


AGENT_RUNS_SHAPED_LIKE_VERCEL_CLI_65_2_0 = agent_runs(
    runs_entry("prj_docs", "docs-site", 12),
)


def metric_rows(
    metric: str,
    *rows: dict[str, Any],
    series: bool = False,
) -> dict[str, Any]:
    """An observability answer as `vercel metrics` (CLI 65.2.0) reads it: flat rows of
    dimension values and the `<metric>_sum` rollup column, in `summary` (or `data`)."""
    column = rollup_column(metric)
    shaped = [
        {**{k: v for k, v in row.items() if k != "count"}, column: row["count"]}
        for row in rows
    ]
    if series:
        return {
            "data": [{"timestamp": "2025-10-01T00:00:00.000Z", **r} for r in shaped],
        }
    return {"summary": shaped, "data": [], "statistics": {"rowsRead": 10}}


def observability(
    gateway: Any = None,
    hosts: Any = None,
) -> Callable[[dict[str, Any]], Any]:
    """A POST route answering each metric with its own response."""

    def answer(kw: dict[str, Any]) -> Any:
        metric = kw["json"]["metric"]
        chosen = gateway if metric == AI_GATEWAY_METRIC else hosts
        if chosen is None:
            return ok(metric_rows(metric))
        if isinstance(chosen, list):
            return chosen.pop(0) if len(chosen) > 1 else chosen[0]
        return chosen

    return answer


def file_tree(*entries: dict[str, Any]) -> list[dict[str, Any]]:
    """`GET /v6/deployments/{id}/files`, an array of @vercel/sdk 1.28.51's FileTree."""
    return list(entries)


def tree_file(name: str, uid: str) -> dict[str, Any]:
    return {"name": name, "type": "file", "uid": uid, "mode": 33188}


def tree_dir(name: str, *children: dict[str, Any]) -> dict[str, Any]:
    return {
        "name": name,
        "type": "directory",
        "mode": 16877,
        "children": list(children),
    }


# What a package.json must never leak: anything in it but dependency names.
PACKAGE_SECRET = "package-json-content-that-must-never-leak"


def package_json(*names: str, **extra: Any) -> dict[str, Any]:
    """`GET /v8/deployments/{id}/files/{fileId}`: base64 JSON, key `data` assumed."""
    manifest = {
        "name": "support-chat",
        "scripts": {"build": f"next build --token {PACKAGE_SECRET}"},
        "dependencies": {name: "^1.0.0" for name in names},
        "devDependencies": {"typescript": "^5"},
        **extra,
    }
    return {"data": base64.b64encode(json.dumps(manifest).encode()).decode()}


# -- the fake api.vercel.com --------------------------------------------------------------


class FakeResponse:
    def __init__(
        self,
        status: int,
        body: Any = None,
        headers: Optional[dict[str, str]] = None,
        text_body: bool = False,
    ) -> None:
        self.status_code = status
        self._body = body
        self._text = text_body
        self.headers = headers or {}

    def json(self) -> Any:
        if self._text or self._body is None:
            raise ValueError("Expecting value: line 1 column 1 (char 0)")
        return json.loads(json.dumps(self._body))


def ok(body: Any, headers: Optional[dict[str, str]] = None) -> FakeResponse:
    return FakeResponse(200, body, headers)


def error(status: int, code: str = "forbidden", message: str = "") -> FakeResponse:
    return FakeResponse(status, {"error": {"code": code, "message": message}})


Route = Any  # a response, an exception, a list consumed in order, or a callable


def env_path(pid: str) -> str:
    return f"{PROJECTS_PATH}/{pid}/env"


def default_routes() -> dict[str, Route]:
    """The default team: no shared LLM key, no Agent Runs, no Observability Plus."""
    return {
        SHARED_ENV_PATH: ok(SHARED_ENV_SHAPED_LIKE_VERCEL_SDK_1_28_51),
        team_path(TEAM_ID): ok(TEAM_SHAPED_LIKE_VERCEL_SDK_1_28_51),
        AGENT_RUNS_PATH: ok(agent_runs()),
        OBSERVABILITY_QUERY_PATH: error(402, "payment_required"),
        PROJECTS_PATH: ok(PROJECTS_SHAPED_LIKE_VERCEL_SDK_1_28_43),
        INTEGRATIONS_PATH: ok(CONFIGURATIONS_SHAPED_LIKE_VERCEL_SDK_1_28_43),
        env_path("prj_chat"): ok(ENVS_SHAPED_LIKE_VERCEL_SDK_1_28_43),
        env_path("prj_docs"): ok(
            envs(env_var("NEXT_PUBLIC_SITE_URL", "plain"), env_var("DATABASE_URL")),
        ),
        env_path("prj_img"): ok(envs(env_var("BLOB_READ_WRITE_TOKEN"))),
    }


class FakeSession:
    def __init__(self, routes: Optional[dict[str, Route]] = None) -> None:
        self.routes = default_routes()
        self.routes.update(routes or {})
        self.calls: list[dict[str, Any]] = []

    def get(self, url: str, **kw: Any) -> FakeResponse:
        return self._answer("GET", url, kw)

    def post(self, url: str, **kw: Any) -> FakeResponse:
        return self._answer("POST", url, kw)

    def _answer(self, method: str, url: str, kw: dict[str, Any]) -> FakeResponse:
        path = urlsplit(url).path
        self.calls.append({"method": method, "url": url, "path": path, **kw})
        route = self.routes.get(path)
        if route is None:
            if path.startswith(PROJECTS_PATH + "/") and path.endswith("/env"):
                route = ok(envs())
            else:
                raise AssertionError(f"unexpected call to {path}")
        if isinstance(route, list):
            route = route.pop(0) if len(route) > 1 else route[0]
        if callable(route) and not isinstance(route, FakeResponse):
            route = route(kw)
        if isinstance(route, BaseException):
            raise route
        assert isinstance(route, FakeResponse)
        return route

    def paths(self) -> list[str]:
        return [c["path"] for c in self.calls]

    def calls_to(self, path: str) -> list[dict[str, Any]]:
        return [c for c in self.calls if c["path"] == path]


def connector_with(
    session: FakeSession,
    sleeps: Optional[list[float]] = None,
    clock: Callable[[], float] = lambda: 1_759_363_200.0,
) -> VercelConnector:
    def factory(settings: VercelSettings, log: logging.Logger) -> VercelClient:
        return VercelClient(
            settings,
            logger=log,
            session=session,  # type: ignore[arg-type]
            sleep=(sleeps if sleeps is not None else []).append,
            clock=clock,
        )

    return VercelConnector(client_factory=factory)


def config() -> DiscoverySourceConfigSpec:
    return DiscoverySourceConfigSpec.model_construct(
        name="vercel",
        vendor=VENDOR,
        query="",
    )


def scan(
    session: FakeSession,
    *,
    fields: Optional[dict[str, str]] = None,
    creds: Optional[dict[str, Optional[str]]] = None,
    lookback_hours: int = 24,
    sleeps: Optional[list[float]] = None,
) -> list[Any]:
    batches = connector_with(session, sleeps).scan(
        config(),
        lookback_hours,
        CREDS if creds is None else creds,
        FIELDS if fields is None else fields,
        LOG,
    )
    return [record for batch in batches for record in batch]


def ids(records: list[Any]) -> list[str]:
    return [r.external_id for r in records]


def with_projects(*bodies: dict[str, Any], **routes: Route) -> FakeSession:
    page = {
        "projects": list(bodies),
        "pagination": {"count": len(bodies), "next": None},
    }
    return FakeSession({PROJECTS_PATH: ok(page), INTEGRATIONS_PATH: ok([]), **routes})


def scan_logged(
    session: FakeSession,
    caplog: pytest.LogCaptureFixture,
    level: int = logging.INFO,
    **kw: Any,
) -> list[Any]:
    with caplog.at_level(level, logger=LOG.name):
        return scan(session, **kw)


def evidence_line(caplog: pytest.LogCaptureFixture, pid: str) -> str:
    [line] = [
        r.getMessage()
        for r in caplog.records
        if r.getMessage().startswith(f"Vercel project {pid} flagged by: ")
    ]
    return line


# -- registration --------------------------------------------------------------------------


def test_the_connector_is_registered_under_vercel_ai() -> None:
    assert VENDOR == "vercel_ai"
    assert source_connectors()[VENDOR] is VercelConnector
    assert isinstance(source_connectors()[VENDOR](), VercelConnector)


def test_the_connector_declares_exactly_its_secrets() -> None:
    # The same set the Platform catalog marks is_sensitive.
    assert VercelConnector.SENSITIVE_FIELDS == frozenset({"access_token"})
    assert (TEAM_ID_FIELD, ACCESS_TOKEN_FIELD, INCLUDE_PROJECTS_FIELD) == (
        "team_id",
        "access_token",
        "include_projects",
    )


# -- the requests ----------------------------------------------------------------------------


def test_every_call_carries_the_bearer_token_and_the_team_id() -> None:
    session = FakeSession()
    scan(session)
    assert session.calls
    for call in session.calls:
        if call["path"] == AGENT_RUNS_PATH:
            continue  # addressed by slug on the dashboard host; tested on its own
        assert call["url"].startswith(API_BASE_URL + "/")
        assert call["headers"]["Authorization"] == f"Bearer {TOKEN}"
        assert call["params"]["teamId"] == TEAM_ID


def test_redirects_are_refused_and_each_timeout_fits_the_preview_deadline() -> None:
    session = FakeSession()
    scan(session)
    for call in session.calls:
        assert call["allow_redirects"] is False
        connect, read = call["timeout"]
        # Each applies on its own, so together they must fit Test Connection's 120s.
        assert connect + read < 120


def test_variable_values_are_never_asked_to_be_decrypted() -> None:
    session = FakeSession()
    scan(session)
    for call in session.calls:
        assert "decrypt" not in call["params"]
        # The single-variable endpoints, which decrypt, are never called.
        assert not call["path"].startswith("/v1/projects/")
        assert not call["path"].startswith(SHARED_ENV_PATH + "/")
        if call["path"].endswith("/env") and call["path"] != SHARED_ENV_PATH:
            assert call["path"].startswith(f"{PROJECTS_PATH}/prj_")
            assert call["path"].count("/") == 4


def test_the_project_list_asks_for_full_pages_and_integrations_are_read_once() -> None:
    session = FakeSession()
    scan(session)
    assert session.calls[0]["path"] == PROJECTS_PATH
    assert session.calls[0]["params"]["limit"] == "100"
    integrations = [c for c in session.calls if c["path"] == INTEGRATIONS_PATH]
    assert len(integrations) == 1
    assert integrations[0]["params"]["view"] == "account"


def test_the_lookback_is_not_applied() -> None:
    # Not to the inventory: only Agent Runs and observability read a window.
    first, second = FakeSession(), FakeSession()
    assert ids(scan(first, lookback_hours=1)) == ids(scan(second, lookback_hours=0))
    activity = {AGENT_RUNS_PATH, OBSERVABILITY_QUERY_PATH}
    assert [c["params"] for c in first.calls if c["path"] not in activity] == [
        c["params"] for c in second.calls if c["path"] not in activity
    ]


# -- paging ------------------------------------------------------------------------------


def pages(*pages_: tuple[list[dict[str, Any]], Any]) -> Callable[[dict[str, Any]], Any]:
    """A projects route answering each request with the next (projects, next) page."""
    queue = list(pages_)

    def answer(kw: dict[str, Any]) -> FakeResponse:
        projects, following = queue.pop(0) if len(queue) > 1 else queue[0]
        return ok(
            {
                "projects": projects,
                "pagination": {"count": len(projects), "next": following, "prev": None},
            },
        )

    return answer


def chat(pid: str = "prj_chat", name: str = "support-chat") -> dict[str, Any]:
    return project(pid, name)


def test_a_numeric_next_cursor_is_sent_back_as_until() -> None:
    session = FakeSession(
        {
            PROJECTS_PATH: pages(
                ([chat("prj_a", "a")], 1_759_000_000_000),
                ([chat()], None),
            ),
            env_path("prj_a"): ok(envs(env_var("ANTHROPIC_API_KEY"))),
        },
    )
    assert ids(scan(session)) == ["prj_a", "prj_chat"]
    listing = [c["params"] for c in session.calls if c["path"] == PROJECTS_PATH]
    assert "until" not in listing[0] and "from" not in listing[0]
    assert listing[1]["until"] == "1759000000000"
    assert "from" not in listing[1]


def test_a_string_next_cursor_is_sent_back_as_from() -> None:
    session = FakeSession(
        {
            PROJECTS_PATH: pages(
                ([chat("prj_a", "a")], "GEZDGNBVGY3TQOJQ"),
                ([chat()], None),
            ),
            env_path("prj_a"): ok(envs(env_var("GROQ_API_KEY"))),
        },
    )
    assert ids(scan(session)) == ["prj_a", "prj_chat"]
    listing = [c["params"] for c in session.calls if c["path"] == PROJECTS_PATH]
    assert listing[1]["from"] == "GEZDGNBVGY3TQOJQ"
    assert "until" not in listing[1]


def test_a_cursor_vercel_repeats_ends_the_listing_with_a_warning(
    caplog: pytest.LogCaptureFixture,
) -> None:
    session = FakeSession({PROJECTS_PATH: pages(([chat()], "SAME"))})
    with caplog.at_level(logging.WARNING, logger=LOG.name):
        records = scan(session)
    assert ids(records) == ["prj_chat"]
    # The first page, then the page that handed the same cursor back: never a third.
    assert session.paths().count(PROJECTS_PATH) == 2
    assert "already returned" in caplog.text


def test_the_project_list_stops_at_its_page_cap_with_a_warning(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    monkeypatch.setattr(vercel, "MAX_PROJECT_PAGES", 3)
    counter = iter(range(1_000_000))

    def endless(kw: dict[str, Any]) -> FakeResponse:
        n = next(counter)
        return ok(
            {"projects": [chat(f"prj_{n}", f"p{n}")], "pagination": {"next": n + 1}},
        )

    session = FakeSession(
        {
            PROJECTS_PATH: endless,
            INTEGRATIONS_PATH: ok([configuration("openai", projects=ALL)]),
        },
    )
    with caplog.at_level(logging.WARNING, logger=LOG.name):
        records = scan(session)
    assert session.paths().count(PROJECTS_PATH) == 3
    assert len(records) == 3
    assert "stopped at 3 pages" in caplog.text


def test_a_project_on_two_pages_is_one_record() -> None:
    session = FakeSession({PROJECTS_PATH: pages(([chat()], 5), ([chat()], None))})
    assert ids(scan(session)) == ["prj_chat"]


def test_a_bare_list_of_projects_is_one_complete_page() -> None:
    session = FakeSession({PROJECTS_PATH: ok([chat()])})
    assert ids(scan(session)) == ["prj_chat"]
    assert session.paths().count(PROJECTS_PATH) == 1


# -- what makes a project an agent ---------------------------------------------------------


def test_the_provider_key_list_is_the_documented_one() -> None:
    assert LLM_PROVIDER_ENV_KEYS == {
        "AI_GATEWAY_API_KEY",
        "OPENAI_API_KEY",
        "AZURE_OPENAI_API_KEY",
        "ANTHROPIC_API_KEY",
        "GOOGLE_GENERATIVE_AI_API_KEY",
        "GEMINI_API_KEY",
        "XAI_API_KEY",
        "GROQ_API_KEY",
        "MISTRAL_API_KEY",
        "COHERE_API_KEY",
        "DEEPSEEK_API_KEY",
        "PERPLEXITY_API_KEY",
        "TOGETHER_AI_API_KEY",
        "FIREWORKS_API_KEY",
        "CEREBRAS_API_KEY",
        "DEEPINFRA_API_KEY",
        "OPENROUTER_API_KEY",
        "REPLICATE_API_TOKEN",
        "FAL_KEY",
        "HF_TOKEN",
    }


@pytest.mark.parametrize("key", sorted(LLM_PROVIDER_ENV_KEYS))
def test_a_project_with_an_llm_provider_key_is_flagged(key: str) -> None:
    session = with_projects(chat(), **{env_path("prj_chat"): ok(envs(env_var(key)))})
    assert ids(scan(session)) == ["prj_chat"]


@pytest.mark.parametrize(
    "key",
    ["MY_OPENAI_API_KEY", "openai_api_key", "OPENAI_API_KEY_OLD", "OPENAI_BASE_URL"],
)
def test_a_key_that_only_resembles_a_provider_key_is_not_flagged(key: str) -> None:
    session = with_projects(chat(), **{env_path("prj_chat"): ok(envs(env_var(key)))})
    assert scan(session) == []


def test_projects_without_an_ai_signal_yield_no_record() -> None:
    session = with_projects(
        project("prj_docs", "docs-site"),
        **{env_path("prj_docs"): ok(envs(env_var("DATABASE_URL")))},
    )
    assert scan(session) == []


def test_the_default_team_flags_one_project_by_key_and_one_by_integration() -> None:
    assert sorted(ids(scan(FakeSession()))) == ["prj_chat", "prj_img"]


def test_an_ai_tagged_integration_flags_only_the_projects_it_is_scoped_to() -> None:
    session = FakeSession(
        {
            INTEGRATIONS_PATH: ok(
                [configuration("some-llm", projects=["prj_docs"], tags=["tag_ai"])],
            ),
            env_path("prj_chat"): ok(envs()),
        },
    )
    assert ids(scan(session)) == ["prj_docs"]


@pytest.mark.parametrize(
    "entry",
    [
        configuration("agent-host", projects=["prj_docs"], tags=["tag_agents"]),
        configuration("openai", projects=["prj_docs"]),
        configuration("Together-AI", projects=["prj_docs"]),
        # Tags at the top level rather than under `integration`.
        {"slug": "x", "projects": ["prj_docs"], "tagIds": ["tag_ai"]},
    ],
)
def test_an_agents_tag_or_a_known_provider_slug_also_counts(
    entry: dict[str, Any],
) -> None:
    session = FakeSession(
        {INTEGRATIONS_PATH: ok([entry]), env_path("prj_chat"): ok(envs())},
    )
    assert ids(scan(session)) == ["prj_docs"]


def test_the_known_provider_slugs_are_lower_case() -> None:
    assert all(slug == slug.lower() for slug in AI_INTEGRATION_SLUGS)


@pytest.mark.parametrize("projects", [ALL, None, "all"])
def test_an_ai_integration_with_access_to_every_project_flags_them_all(
    projects: Any,
) -> None:
    session = FakeSession(
        {INTEGRATIONS_PATH: ok([configuration("groq", projects=projects)])},
    )
    assert sorted(ids(scan(session))) == ["prj_chat", "prj_docs", "prj_img"]


def test_a_non_ai_integration_flags_nothing() -> None:
    session = FakeSession(
        {
            INTEGRATIONS_PATH: ok(
                [configuration("neon", projects=ALL, tags=["tag_storage"])],
            ),
            env_path("prj_chat"): ok(envs()),
        },
    )
    assert scan(session) == []


@pytest.mark.parametrize("state", [{"disabledAt": T_UPDATED}, {"deletedAt": T_UPDATED}])
def test_a_disabled_or_deleted_ai_integration_flags_nothing(
    state: dict[str, int],
) -> None:
    session = FakeSession(
        {
            INTEGRATIONS_PATH: ok(
                [configuration("xai", projects=ALL, tags=["tag_ai"], **state)],
            ),
            env_path("prj_chat"): ok(envs()),
        },
    )
    assert scan(session) == []


def test_every_in_scope_projects_variables_are_read_so_its_evidence_is_whole() -> None:
    # prj_img is already flagged by its integration; its variables are still read.
    session = FakeSession()
    scan(session)
    assert env_path("prj_img") in session.paths()
    assert env_path("prj_chat") in session.paths()


def test_a_token_refused_the_integrations_list_still_scans_by_variable_names(
    caplog: pytest.LogCaptureFixture,
) -> None:
    session = FakeSession({INTEGRATIONS_PATH: error(403)})
    with caplog.at_level(logging.WARNING, logger=LOG.name):
        records = scan(session)
    assert ids(records) == ["prj_chat"]
    assert INTEGRATIONS_PATH in caplog.text
    assert env_path("prj_img") in session.paths()


def test_hidden_production_variables_are_reported_by_project_id(
    caplog: pytest.LogCaptureFixture,
) -> None:
    session = with_projects(
        project("prj_docs", "docs-site"),
        **{env_path("prj_docs"): ok(envs(env_var("DATABASE_URL"), hidden=2))},
    )
    with caplog.at_level(logging.WARNING, logger=LOG.name):
        assert scan(session) == []
    assert "prj_docs" in caplog.text
    assert "2 production environment variable(s)" in caplog.text


@pytest.mark.parametrize(
    "body",
    [
        [env_var("OPENAI_API_KEY")],
        {
            "envs": [env_var("OPENAI_API_KEY")],
            "pagination": {"count": 1, "next": None, "prev": None},
        },
        env_var("OPENAI_API_KEY"),
    ],
)
def test_env_answers_as_a_bare_list_a_paged_object_or_one_variable_are_read(
    body: Any,
) -> None:
    session = with_projects(chat(), **{env_path("prj_chat"): ok(body)})
    assert ids(scan(session)) == ["prj_chat"]


def test_an_env_answer_with_more_pages_is_reported(
    caplog: pytest.LogCaptureFixture,
) -> None:
    body = {
        "envs": [env_var("DATABASE_URL")],
        "pagination": {"count": 1, "next": 5, "prev": None},
    }
    session = with_projects(chat(), **{env_path("prj_chat"): ok(body)})
    with caplog.at_level(logging.WARNING, logger=LOG.name):
        scan(session)
    assert "only the first page" in caplog.text


def test_a_project_deleted_mid_scan_is_skipped_with_a_warning(
    caplog: pytest.LogCaptureFixture,
) -> None:
    session = with_projects(
        chat("prj_gone", "gone"),
        chat(),
        **{
            env_path("prj_gone"): error(404, "not_found"),
            env_path("prj_chat"): ok(envs(env_var("OPENAI_API_KEY"))),
        },
    )
    with caplog.at_level(logging.WARNING, logger=LOG.name):
        assert ids(scan(session)) == ["prj_chat"]
    assert "prj_gone" in caplog.text and "HTTP 404" in caplog.text


# -- include_projects ------------------------------------------------------------------------


def test_include_projects_limits_the_scan_by_name_or_id() -> None:
    session = FakeSession()
    records = scan(
        session,
        fields={**FIELDS, "include_projects": " support-chat , prj_img "},
    )
    assert sorted(ids(records)) == ["prj_chat", "prj_img"]
    assert env_path("prj_docs") not in session.paths()


def test_include_projects_names_not_in_the_team_are_reported(
    caplog: pytest.LogCaptureFixture,
) -> None:
    with caplog.at_level(logging.WARNING, logger=LOG.name):
        records = scan(
            FakeSession(),
            fields={**FIELDS, "include_projects": "support-chat,nope"},
        )
    assert ids(records) == ["prj_chat"]
    assert "not in this team" in caplog.text and "nope" in caplog.text


def test_include_projects_matching_nothing_reads_no_variables() -> None:
    session = FakeSession()
    assert scan(session, fields={**FIELDS, "include_projects": "nope"}) == []
    assert session.paths() == [PROJECTS_PATH]


@pytest.mark.parametrize("value", ["", "  ", " , "])
def test_an_empty_include_projects_scans_every_project(value: str) -> None:
    records = scan(FakeSession(), fields={**FIELDS, "include_projects": value})
    assert sorted(ids(records)) == ["prj_chat", "prj_img"]


# -- records -------------------------------------------------------------------------------


def test_a_record_carries_cloud_provenance_with_team_scope_and_project_id() -> None:
    [record] = [r for r in scan(FakeSession()) if r.external_id == "prj_chat"]
    assert record.name == "support-chat"
    source = record.creation_source
    assert isinstance(source, CloudAgentCreationSource)
    assert source.vendor == "vercel_ai"
    assert source.address.instance == TEAM_ID
    assert source.address.scope == GLOBAL_SCOPE
    assert source.address.resource_id == "prj_chat"
    assert source.address.query is None


def test_every_record_is_scoped_global_whatever_its_function_region() -> None:
    # prj_chat reports serverlessFunctionRegion iad1, prj_img none.
    records = scan(FakeSession())
    assert sorted(ids(records)) == ["prj_chat", "prj_img"]
    for record in records:
        assert record.creation_source.address.scope == GLOBAL_SCOPE == "global"


def test_a_record_leaves_runs_on_platform_models_and_service_names_unset() -> None:
    for record in scan(FakeSession()):
        assert record.runs_on is None
        assert record.platform is None
        assert not record.llm_models
        # Not claimed: see the connector's docstring on NO SERVICE NAMES.
        assert record.service_names == []


def test_a_project_without_a_name_is_named_by_its_id() -> None:
    session = with_projects(
        project("prj_x", ""),
        **{env_path("prj_x"): ok(envs(env_var("OPENAI_API_KEY")))},
    )
    assert [r.name for r in scan(session)] == ["prj_x"]


@pytest.mark.parametrize(
    "body, expected",
    [
        (project("prj_x", "x"), T_UPDATED),
        (project("prj_x", "x", production=deployment(T_DEPLOYED, T_READY)), T_READY),
        (project("prj_x", "x", production=deployment(T_DEPLOYED)), T_DEPLOYED),
        (
            project(
                "prj_x",
                "x",
                updated=None,
                deployments=[deployment(T_CREATED), deployment(T_DEPLOYED)],
            ),
            T_DEPLOYED,
        ),
        (
            project(
                "prj_x",
                "x",
                updated=T_READY + 1,
                production=deployment(T_DEPLOYED, T_READY),
            ),
            T_READY + 1,
        ),
        (
            project(
                "prj_x",
                "x",
                updated=None,
                production=deployment(T_DEPLOYED, T_READY),
            ),
            T_READY,
        ),
    ],
)
def test_last_seen_is_the_latest_of_production_deployments_and_update(
    body: dict[str, Any],
    expected: int,
) -> None:
    session = with_projects(
        body,
        **{env_path("prj_x"): ok(envs(env_var("OPENAI_API_KEY")))},
    )
    [record] = scan(session)
    assert record.last_seen == utc(expected)
    assert record.last_seen.tzinfo is not None


def test_a_project_with_no_timestamps_is_skipped_naming_only_its_id(
    caplog: pytest.LogCaptureFixture,
) -> None:
    session = with_projects(
        project(
            "prj_undated",
            "secret-name",
            updated=None,
            production={"readyAt": "soon"},
        ),
        chat(),
        **{
            env_path("prj_undated"): ok(envs(env_var("OPENAI_API_KEY"))),
            env_path("prj_chat"): ok(envs(env_var("OPENAI_API_KEY"))),
        },
    )
    with caplog.at_level(logging.WARNING, logger=LOG.name):
        assert ids(scan(session)) == ["prj_chat"]
    [warning] = [
        r.getMessage() for r in caplog.records if "prj_undated" in r.getMessage()
    ]
    assert "secret-name" not in warning


def test_output_satisfies_the_discovery_output_contract() -> None:
    records = scan(FakeSession())
    assert records
    check_batch(records, "Source config 'vercel' (vercel_ai)")


def test_records_are_batched(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(vercel, "BATCH_SIZE", 2)
    session = with_projects(
        *[chat(f"prj_{i}", f"p{i}") for i in range(5)],
        **{INTEGRATIONS_PATH: ok([configuration("openai", projects=ALL)])},
    )
    batches = list(connector_with(session).scan(config(), 24, CREDS, FIELDS, LOG))
    assert [len(b) for b in batches] == [2, 2, 1]
    assert BATCH_SIZE == 100


# -- how complete the answer is --------------------------------------------------------------


def test_completeness_is_reported_before_the_first_batch(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    monkeypatch.setattr(vercel, "MAX_PROJECT_PAGES", 1)
    session = FakeSession({PROJECTS_PATH: pages(([chat()], 99))})
    batches = connector_with(session).scan(config(), 24, CREDS, FIELDS, LOG)
    with caplog.at_level(logging.INFO, logger=LOG.name):
        first = next(batches)
    assert ids(list(first)) == ["prj_chat"]
    assert "listed 1 project(s) over 1 page(s)" in caplog.text
    assert "1 flagged (1 by environment variable)" in caplog.text
    assert "stopped at 1 pages" in caplog.text


def test_include_projects_filtering_is_counted(
    caplog: pytest.LogCaptureFixture,
) -> None:
    with caplog.at_level(logging.INFO, logger=LOG.name):
        scan(FakeSession(), fields={**FIELDS, "include_projects": "docs-site"})
    assert "2 outside include_projects; 1 scanned" in caplog.text


def test_a_team_with_no_projects_says_so(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.WARNING, logger=LOG.name):
        assert scan(with_projects()) == []
    assert "listed no projects" in caplog.text


# -- stopping -----------------------------------------------------------------------------


def test_the_connector_accepts_a_stop_check() -> None:
    assert isinstance(VercelConnector(), AcceptsStopCheck)


def test_a_stop_before_the_first_call_sends_nothing() -> None:
    session = FakeSession()
    connector = connector_with(session)
    connector.stop_when(lambda: True)
    assert list(connector.scan(config(), 24, CREDS, FIELDS, LOG)) == []
    assert session.calls == []


def test_a_stop_between_projects_hands_over_what_was_found_and_says_so(
    caplog: pytest.LogCaptureFixture,
) -> None:
    session = with_projects(
        chat("prj_1", "one"),
        chat("prj_2", "two"),
        **{
            env_path("prj_1"): ok(envs(env_var("OPENAI_API_KEY"))),
            env_path("prj_2"): ok(envs(env_var("OPENAI_API_KEY"))),
        },
    )
    connector = connector_with(session)
    # Everything up to the first project's variables, then stop.
    connector.stop_when(lambda: env_path("prj_1") in session.paths())
    with caplog.at_level(logging.WARNING, logger=LOG.name):
        records = [
            r for b in connector.scan(config(), 24, CREDS, FIELDS, LOG) for r in b
        ]
    assert ids(records) == ["prj_1"]
    assert env_path("prj_2") not in session.paths()
    assert "stopped early" in caplog.text


def test_a_stop_during_a_retry_backoff_ends_the_scan_without_sleeping() -> None:
    sleeps: list[float] = []
    session = FakeSession({PROJECTS_PATH: error(503, "service_unavailable")})
    connector = connector_with(session, sleeps)
    connector.stop_when(lambda: len(session.calls) >= 1)
    assert list(connector.scan(config(), 24, CREDS, FIELDS, LOG)) == []
    assert len(session.calls) == 1
    assert sleeps == []


# -- configuration -------------------------------------------------------------------------


@pytest.mark.parametrize(
    "creds, fields, missing",
    [
        ({}, {}, ["team_id", "access_token"]),
        (CREDS, {}, ["team_id"]),
        ({"access_token": "  "}, FIELDS, ["access_token"]),
        ({"access_token": None}, FIELDS, ["access_token"]),
    ],
)
def test_missing_fields_are_named_and_nothing_is_sent(
    creds: dict[str, Optional[str]],
    fields: dict[str, str],
    missing: list[str],
) -> None:
    session = FakeSession()
    with pytest.raises(DiscoveryConfigurationError) as exc:
        scan(session, creds=creds, fields=fields)
    for name in missing:
        assert name in str(exc.value)
    assert failure_code(exc.value) is DiscoveryErrorCode.NOT_CONFIGURED
    assert session.calls == []


def test_a_token_with_whitespace_inside_is_refused_without_echoing_it() -> None:
    broken = "abc def\nghi"
    with pytest.raises(DiscoveryConfigurationError, match="access_token") as exc:
        settings_from({"access_token": broken}, FIELDS)
    assert "abc" not in str(exc.value)


def test_a_team_id_with_whitespace_inside_is_refused_without_echoing_it() -> None:
    with pytest.raises(DiscoveryConfigurationError, match="team_id") as exc:
        settings_from(CREDS, {"team_id": "team_one two"})
    assert "team_one" not in str(exc.value)


def test_the_settings_are_trimmed() -> None:
    settings = settings_from(
        {"access_token": f" {TOKEN} "},
        {"team_id": f" {TEAM_ID} "},
    )
    assert (settings.team_id, settings.access_token) == (TEAM_ID, TOKEN)


# -- failures --------------------------------------------------------------------------------


def test_a_refused_token_is_an_authentication_failure_with_a_hint() -> None:
    with pytest.raises(VercelError) as exc:
        scan(FakeSession({PROJECTS_PATH: error(401, "forbidden", "Not authorized")}))
    assert exc.value.status_code == 401
    assert failure_code(exc.value) is DiscoveryErrorCode.AUTHENTICATION_FAILED
    assert "access_token" in str(exc.value) and "expired" in str(exc.value)


def test_a_token_without_access_to_the_team_is_permission_denied_with_a_hint() -> None:
    with pytest.raises(VercelError) as exc:
        scan(FakeSession({PROJECTS_PATH: error(403)}))
    assert exc.value.status_code == 403
    assert failure_code(exc.value) is DiscoveryErrorCode.PERMISSION_DENIED
    assert "team_id" in str(exc.value) and "different team" in str(exc.value)
    # Vercel answers a bad token with 403 too, so the hint covers both.
    for cause in ("invalid", "expired", "revoked"):
        assert cause in str(exc.value)


def test_an_unknown_team_is_the_sources_to_fix() -> None:
    with pytest.raises(DiscoveryConfigurationError) as exc:
        scan(
            FakeSession(
                {PROJECTS_PATH: error(404, "not_found", f"Team {TEAM_ID} not found")},
            ),
        )
    assert failure_code(exc.value) is DiscoveryErrorCode.NOT_CONFIGURED
    # No status for Test Connection to read as Vercel's error, on the exception, its
    # chain, or in its text.
    assert getattr(exc.value, "status_code", None) is None
    assert exc.value.__cause__ is None and exc.value.__context__ is None
    assert "HTTP" not in str(exc.value) and "404" not in str(exc.value)
    assert "team_id" in str(exc.value)
    assert TEAM_ID not in str(exc.value)


@pytest.mark.parametrize(
    "status, code",
    [
        (401, DiscoveryErrorCode.AUTHENTICATION_FAILED),
        (400, DiscoveryErrorCode.PROVIDER_ERROR),
    ],
)
def test_a_vendor_error_on_a_projects_variables_carries_its_status(
    status: int,
    code: DiscoveryErrorCode,
) -> None:
    with pytest.raises(VercelError) as exc:
        scan(FakeSession({env_path("prj_chat"): error(status)}))
    assert exc.value.status_code == status
    assert failure_code(exc.value) is code
    assert "prj_chat" in str(exc.value)


def test_a_failure_part_way_hands_over_what_was_found_then_raises_unchanged(
    caplog: pytest.LogCaptureFixture,
) -> None:
    session = with_projects(
        chat("prj_1", "one"),
        chat("prj_2", "two"),
        **{
            env_path("prj_1"): ok(envs(env_var("OPENAI_API_KEY"))),
            env_path("prj_2"): error(401),
        },
    )
    batches = connector_with(session).scan(config(), 24, CREDS, FIELDS, LOG)
    found: list[Any] = []
    with caplog.at_level(logging.INFO, logger=LOG.name):
        with pytest.raises(VercelError) as exc:
            for batch in batches:
                assert "failed part-way" in caplog.text
                found.extend(batch)
    assert ids(found) == ["prj_1"]
    assert exc.value.status_code == 401
    assert failure_code(exc.value) is DiscoveryErrorCode.AUTHENTICATION_FAILED
    assert env_path("prj_2") in str(exc.value)


@pytest.mark.parametrize("status", [403, 404, 500, 501, 503])
def test_a_403_404_or_5xx_on_one_projects_variables_skips_only_that_project(
    status: int,
    caplog: pytest.LogCaptureFixture,
) -> None:
    vendor_message = "Project restricted-config-name is not visible to you"
    session = with_projects(
        chat("prj_1", "one"),
        chat("prj_2", "two"),
        **{
            env_path("prj_1"): error(status, "some_code", vendor_message),
            env_path("prj_2"): ok(envs(env_var("OPENAI_API_KEY"))),
        },
    )
    batches = connector_with(session).scan(config(), 24, CREDS, FIELDS, LOG)
    with caplog.at_level(logging.INFO, logger=LOG.name):
        first = next(batches)
    assert ids(list(first)) == ["prj_2"]
    assert list(batches) == []
    warnings = [r.getMessage() for r in caplog.records if r.levelno == logging.WARNING]
    assert any("prj_1" in w and f"HTTP {status}" in w for w in warnings)
    assert "1 unreadable" in caplog.text and "answer is partial" in caplog.text
    assert vendor_message not in caplog.text and "some_code" not in caplog.text


def test_an_integrations_failure_other_than_403_fails_the_scan() -> None:
    with pytest.raises(VercelError) as exc:
        scan(FakeSession({INTEGRATIONS_PATH: error(401)}))
    assert exc.value.status_code == 401


@pytest.mark.parametrize(
    "raised",
    [
        requests.ConnectionError(
            "Max retries exceeded with url: /v10/projects?teamId=x",
        ),
        requests.exceptions.ConnectTimeout("connect timeout"),
        requests.exceptions.ReadTimeout("read timeout"),
    ],
)
def test_an_unreachable_api_stays_the_same_network_error(raised: Exception) -> None:
    sleeps: list[float] = []
    session = FakeSession({PROJECTS_PATH: raised})
    with pytest.raises(type(raised)) as exc:
        scan(session, sleeps=sleeps)
    assert type(exc.value) is type(raised)
    assert "unreachable" in str(exc.value)
    assert exc.value.__cause__ is raised
    assert len(session.calls) == MAX_ATTEMPTS
    assert len(sleeps) == MAX_ATTEMPTS - 1
    # requests' own text quotes the URL with its query string; it stays in the chain.
    assert "teamId" not in str(exc.value)


def test_a_tls_failure_is_not_retried_and_names_the_engines_ca() -> None:
    session = FakeSession(
        {PROJECTS_PATH: requests.exceptions.SSLError("cert verify failed")},
    )
    with pytest.raises(requests.exceptions.SSLError, match="REQUESTS_CA_BUNDLE") as exc:
        scan(session)
    assert isinstance(exc.value.__cause__, requests.exceptions.SSLError)
    assert len(session.calls) == 1


@pytest.mark.parametrize(
    "path, response",
    [
        (
            PROJECTS_PATH,
            FakeResponse(
                200,
                "<html>login</html>",
                {"Content-Type": "text/html"},
                text_body=True,
            ),
        ),
        (PROJECTS_PATH, ok({"error": "x"})),
        (PROJECTS_PATH, ok({"projects": "nope"})),
        (env_path("prj_chat"), FakeResponse(200, None, {"Content-Type": "text/html"})),
        (env_path("prj_chat"), ok({"variables": []})),
        (INTEGRATIONS_PATH, ok({"items": []})),
    ],
)
def test_a_success_status_without_vercels_body_is_vercels_error(
    path: str,
    response: FakeResponse,
) -> None:
    with pytest.raises(VercelError) as exc:
        scan(FakeSession({path: response}))
    assert exc.value.status_code == 200
    assert failure_code(exc.value) is DiscoveryErrorCode.PROVIDER_ERROR


def test_a_rate_limited_call_is_retried_after_what_vercel_asks() -> None:
    sleeps: list[float] = []
    session = FakeSession(
        {
            PROJECTS_PATH: [
                FakeResponse(
                    429,
                    {"error": {"code": "rate_limited"}},
                    {"Retry-After": "7"},
                ),
                ok(PROJECTS_SHAPED_LIKE_VERCEL_SDK_1_28_43),
            ],
        },
    )
    assert sorted(ids(scan(session, sleeps=sleeps))) == ["prj_chat", "prj_img"]
    assert sleeps == [7.0]
    assert session.paths().count(PROJECTS_PATH) == 2


def test_the_rate_limit_reset_is_honoured_when_retry_after_is_absent() -> None:
    sleeps: list[float] = []
    now = 1_759_363_200.0
    session = FakeSession(
        {
            INTEGRATIONS_PATH: [
                FakeResponse(429, {}, {"X-RateLimit-Reset": str(int(now) + 12)}),
                ok([]),
            ],
        },
    )
    connector = connector_with(session, sleeps, clock=lambda: now)
    list(connector.scan(config(), 24, CREDS, FIELDS, LOG))
    assert sleeps == [12.0]


def test_a_5xx_that_persists_carries_its_status_after_every_retry() -> None:
    sleeps: list[float] = []
    session = FakeSession({PROJECTS_PATH: error(503, "service_unavailable")})
    with pytest.raises(VercelError) as exc:
        scan(session, sleeps=sleeps)
    assert exc.value.status_code == 503
    assert len(session.calls) == MAX_ATTEMPTS
    assert len(sleeps) == MAX_ATTEMPTS - 1


def test_an_error_body_contributes_only_its_code() -> None:
    message = f"You don't have access to team {TEAM_ID} with token {TOKEN}"
    with pytest.raises(VercelError) as exc:
        scan(FakeSession({PROJECTS_PATH: error(403, "forbidden", message)}))
    assert "(forbidden)" in str(exc.value)
    assert TEAM_ID not in str(exc.value) and TOKEN not in str(exc.value)


# -- values and the token stay out ----------------------------------------------------------


def test_no_value_and_no_token_reach_logs_records_or_errors(
    caplog: pytest.LogCaptureFixture,
) -> None:
    raised: list[BaseException] = []
    with caplog.at_level(logging.DEBUG):
        records = scan(FakeSession())
        for routes in (
            {PROJECTS_PATH: error(401)},
            {env_path("prj_chat"): error(400)},
            {env_path("prj_chat"): ok({"variables": [env_var("X", "plain")]})},
            {PROJECTS_PATH: requests.ConnectionError(f"Bearer {TOKEN}")},
        ):
            with pytest.raises(Exception) as exc:
                scan(FakeSession(routes))
            raised.append(exc.value)
    dumped = json.dumps([r.model_dump(mode="json") for r in records])
    for text in [caplog.text, dumped, *(str(e) for e in raised)]:
        assert PLAIN_VALUE not in text
        assert ENCRYPTED_VALUE not in text
        assert TOKEN not in text
    for e in raised:
        assert TEAM_ID not in str(e)


def test_a_parsed_variable_has_no_field_for_its_value() -> None:
    assert set(EnvVarName.__dataclass_fields__) == {"key", "type", "targets"}
    assert set(SharedEnvVarName.__dataclass_fields__) == {
        "key",
        "type",
        "targets",
        "project_ids",
    }


# -- the pinned bodies -------------------------------------------------------------------------


def test_responses_shaped_like_vercel_sdk_1_28_43_parse() -> None:
    records = scan(FakeSession())
    by_id = {r.external_id: r for r in records}
    assert sorted(by_id) == ["prj_chat", "prj_img"]
    assert by_id["prj_chat"].last_seen == utc(T_READY)
    assert by_id["prj_chat"].creation_source.address.scope == "global"
    assert by_id["prj_img"].last_seen == utc(T_UPDATED)
    assert by_id["prj_img"].creation_source.address.scope == "global"


# -- end to end through the scan loop ---------------------------------------------------------


class AcceptingSink:
    def __init__(self) -> None:
        self.published: list[str] = []

    def publish(
        self,
        workspace_id: str,
        data_plane_id: str,
        config: DiscoverySourceConfigSpec,
        records: Sequence[Any],
    ) -> DiscoveryPublishResult:
        self.published.extend(r.external_id for r in records)
        return DiscoveryPublishResult(accepted=len(records))


def outcome() -> DiscoveryScanOutcome:
    return DiscoveryScanOutcome(
        discovery_source_config_id=None,
        discovery_source_config_name="vercel",
        discovery_source_id=None,
        vendor=VENDOR,
        job_id="job",
        scan_id=None,
        lookback_hours=24,
    )


def run(
    session: FakeSession,
    result: DiscoveryScanOutcome,
    sink: AcceptingSink,
) -> None:
    run_source_scan(
        config=config(),
        lookback_hours=24,
        workspace_id="workspace",
        data_plane_id="data-plane",
        outcome=result,
        connector=connector_with(session),
        sink=sink,
        logger=LOG,
        credentials=CREDS,
        source_fields=FIELDS,
    )


def test_a_scan_through_run_source_scan_publishes_the_flagged_projects() -> None:
    result, sink = outcome(), AcceptingSink()
    run(FakeSession(), result, sink)
    assert sorted(sink.published) == ["prj_chat", "prj_img"]
    assert result.records_published == 2
    assert result.error is None
    assert result.output_column_check is not None


def test_a_refused_token_reaches_the_run_as_authentication_failed() -> None:
    result, sink = outcome(), AcceptingSink()
    with pytest.raises(VercelError):
        run(FakeSession({PROJECTS_PATH: error(401)}), result, sink)
    assert result.error_code is DiscoveryErrorCode.AUTHENTICATION_FAILED
    assert result.error is not None and result.error.startswith("VercelError: ")
    assert TOKEN not in result.error
    assert sink.published == []


def test_a_failure_part_way_reaches_the_run_after_publishing_what_was_found() -> None:
    session = with_projects(
        chat("prj_1", "one"),
        chat("prj_2", "two"),
        **{
            env_path("prj_1"): ok(envs(env_var("OPENAI_API_KEY"))),
            env_path("prj_2"): error(401),
        },
    )
    result, sink = outcome(), AcceptingSink()
    with pytest.raises(VercelError):
        run(session, result, sink)
    assert sink.published == ["prj_1"]
    assert result.error_code is DiscoveryErrorCode.AUTHENTICATION_FAILED


# -- read_deployment_sources ------------------------------------------------------------


def test_the_opt_in_field_is_named_as_the_catalog_names_it() -> None:
    assert READ_DEPLOYMENT_SOURCES_FIELD == "read_deployment_sources"
    # Not a secret: it says what to read, not how to authenticate.
    assert READ_DEPLOYMENT_SOURCES_FIELD not in VercelConnector.SENSITIVE_FIELDS


@pytest.mark.parametrize(
    "value, expected",
    [
        (None, False),
        ("", False),
        ("  ", False),
        ("false", False),
        ("False", False),
        ("true", True),
        (" TRUE ", True),
    ],
)
def test_read_deployment_sources_is_off_unless_it_is_true(
    value: Optional[str],
    expected: bool,
) -> None:
    fields = dict(FIELDS)
    if value is not None:
        fields[READ_DEPLOYMENT_SOURCES_FIELD] = value
    assert settings_from(CREDS, fields).read_deployment_sources is expected


@pytest.mark.parametrize("value", ["yes", "1", "enabled", "treu"])
def test_any_other_read_deployment_sources_value_is_the_sources_to_fix(
    value: str,
) -> None:
    session = FakeSession()
    with pytest.raises(DiscoveryConfigurationError) as exc:
        scan(session, fields={**FIELDS, READ_DEPLOYMENT_SOURCES_FIELD: value})
    assert failure_code(exc.value) is DiscoveryErrorCode.NOT_CONFIGURED
    assert READ_DEPLOYMENT_SOURCES_FIELD in str(exc.value)
    assert "true, false" in str(exc.value)
    assert value not in str(exc.value)
    assert session.calls == []


# -- evidence ---------------------------------------------------------------------------


def test_each_flagged_project_logs_which_signals_fired_by_name_only(
    caplog: pytest.LogCaptureFixture,
) -> None:
    session = with_projects(
        chat(),
        **{
            env_path("prj_chat"): ok(
                envs(
                    env_var("OPENAI_API_KEY", "plain"),
                    env_var("ANTHROPIC_API_KEY", "sensitive", target=["production"]),
                    env_var("DATABASE_URL", "plain"),
                ),
            ),
            INTEGRATIONS_PATH: ok([configuration("groq", projects=["prj_chat"])]),
        },
    )
    scan_logged(session, caplog)
    line = evidence_line(caplog, "prj_chat")
    assert "environment variable(s) OPENAI_API_KEY (production, preview)" in line
    assert "ANTHROPIC_API_KEY (production)" in line
    assert "AI integration(s) groq" in line
    assert "DATABASE_URL" not in line
    assert PLAIN_VALUE not in caplog.text and ENCRYPTED_VALUE not in caplog.text


@pytest.mark.parametrize("target", ["preview", "development"])
def test_a_key_set_only_for_one_non_production_target_still_flags_and_says_which(
    target: str,
    caplog: pytest.LogCaptureFixture,
) -> None:
    session = with_projects(
        chat(),
        **{
            env_path("prj_chat"): ok(
                envs(env_var("OPENAI_API_KEY", target=[target])),
            ),
        },
    )
    assert ids(scan_logged(session, caplog)) == ["prj_chat"]
    line = evidence_line(caplog, "prj_chat")
    assert f"OPENAI_API_KEY ({target})" in line
    assert "production" not in line


def test_a_key_with_no_target_still_flags_and_says_so(
    caplog: pytest.LogCaptureFixture,
) -> None:
    body = env_var("OPENAI_API_KEY")
    del body["target"]
    session = with_projects(chat(), **{env_path("prj_chat"): ok(envs(body))})
    assert ids(scan_logged(session, caplog)) == ["prj_chat"]
    assert "OPENAI_API_KEY (no target)" in evidence_line(caplog, "prj_chat")


def test_the_signals_line_is_reported_before_the_first_batch(
    caplog: pytest.LogCaptureFixture,
) -> None:
    batches = connector_with(FakeSession()).scan(config(), 24, CREDS, FIELDS, LOG)
    with caplog.at_level(logging.INFO, logger=LOG.name):
        next(batches)
    assert "Vercel signals read: integrations read; shared variables read" in (
        caplog.text
    )
    assert "Observability Plus not enabled" in caplog.text
    assert "deployment sources not read (read_deployment_sources is off)" in (
        caplog.text
    )
    assert "Vercel project prj_chat flagged by: " in caplog.text


# -- team-shared variables --------------------------------------------------------------


def test_a_shared_llm_key_flags_exactly_the_projects_it_is_linked_to(
    caplog: pytest.LogCaptureFixture,
) -> None:
    session = FakeSession(
        {
            SHARED_ENV_PATH: ok(
                shared(
                    shared_var(
                        "ANTHROPIC_API_KEY",
                        ["prj_docs", "prj_elsewhere"],
                        "plain",
                        target=["preview"],
                    ),
                ),
            ),
            INTEGRATIONS_PATH: ok([]),
            env_path("prj_chat"): ok(envs()),
        },
    )
    assert ids(scan_logged(session, caplog)) == ["prj_docs"]
    line = evidence_line(caplog, "prj_docs")
    assert "shared variable(s) ANTHROPIC_API_KEY (preview)" in line
    assert PLAIN_VALUE not in caplog.text


def test_a_shared_variable_that_is_not_an_llm_key_flags_nothing() -> None:
    session = FakeSession(
        {
            SHARED_ENV_PATH: ok(shared(shared_var("SENTRY_DSN", ["prj_docs"]))),
            INTEGRATIONS_PATH: ok([]),
            env_path("prj_chat"): ok(envs()),
        },
    )
    assert scan(session) == []


def test_a_shared_variable_linked_to_no_project_flags_nothing() -> None:
    body = shared_var("OPENAI_API_KEY", [])
    del body["projectId"]
    session = FakeSession(
        {
            SHARED_ENV_PATH: ok(shared(body)),
            INTEGRATIONS_PATH: ok([]),
            env_path("prj_chat"): ok(envs()),
        },
    )
    assert scan(session) == []


def test_a_deleted_shared_variable_flags_nothing() -> None:
    session = FakeSession(
        {
            SHARED_ENV_PATH: ok(
                shared(shared_var("OPENAI_API_KEY", ["prj_docs"], deletedAt=T_UPDATED)),
            ),
            INTEGRATIONS_PATH: ok([]),
            env_path("prj_chat"): ok(envs()),
        },
    )
    assert scan(session) == []


@pytest.mark.parametrize(
    "response",
    [
        error(403),
        error(404, "not_found"),
        error(500, "internal"),
        ok({"variables": []}),
        FakeResponse(200, "<html/>", {"Content-Type": "text/html"}, text_body=True),
        requests.ConnectionError("down"),
    ],
)
def test_shared_variables_that_cannot_be_read_are_a_warning_not_a_failure(
    response: Any,
    caplog: pytest.LogCaptureFixture,
) -> None:
    session = FakeSession({SHARED_ENV_PATH: response})
    records = scan_logged(session, caplog)
    assert sorted(ids(records)) == ["prj_chat", "prj_img"]
    warnings = [r.getMessage() for r in caplog.records if r.levelno == logging.WARNING]
    assert any(SHARED_ENV_PATH in w and "not checked" in w for w in warnings)


def test_a_shared_variable_list_with_more_pages_is_reported(
    caplog: pytest.LogCaptureFixture,
) -> None:
    session = FakeSession({SHARED_ENV_PATH: ok(shared(following=7))})
    scan_logged(session, caplog, logging.WARNING)
    assert "more team-shared environment variables" in caplog.text


# -- Agent Runs -------------------------------------------------------------------------


def test_agent_runs_is_asked_on_the_dashboard_host_by_team_slug_as_the_cli_does() -> (
    None
):
    session = FakeSession()
    scan(session, lookback_hours=24)
    [team] = session.calls_to(team_path(TEAM_ID))
    assert team["url"] == API_BASE_URL + team_path(TEAM_ID)
    [call] = session.calls_to(AGENT_RUNS_PATH)
    assert call["method"] == "GET"
    assert call["url"] == DASHBOARD_BASE_URL + AGENT_RUNS_PATH
    assert call["headers"]["Authorization"] == f"Bearer {TOKEN}"
    assert call["allow_redirects"] is False
    params = call["params"]
    assert params["teamSlug"] == TEAM_SLUG
    assert params["view"] == "team" and params["environment"] == "production"
    assert "teamId" not in params
    now = 1_759_363_200
    assert (params["from"], params["to"]) == (str(now - 24 * 3600), str(now))


@pytest.mark.parametrize(
    "response",
    [error(403), error(404, "not_found"), ok({"id": TEAM_ID}), error(500)],
)
def test_without_the_teams_slug_agent_runs_is_asked_by_team_id(response: Any) -> None:
    session = FakeSession({team_path(TEAM_ID): response})
    scan(session)
    [call] = session.calls_to(AGENT_RUNS_PATH)
    assert call["params"]["teamSlug"] == TEAM_ID


def test_a_project_with_production_agent_runs_is_flagged_with_its_count(
    caplog: pytest.LogCaptureFixture,
) -> None:
    session = FakeSession(
        {AGENT_RUNS_PATH: ok(AGENT_RUNS_SHAPED_LIKE_VERCEL_CLI_65_2_0)},
    )
    records = scan_logged(session, caplog)
    assert sorted(ids(records)) == ["prj_chat", "prj_docs", "prj_img"]
    assert "Agent Runs (12 production run(s))" in evidence_line(caplog, "prj_docs")


@pytest.mark.parametrize(
    "entry",
    [
        {"projectName": "docs-site", "runCount": 2},
        {"name": "docs-site", "totalRuns": 2},
        {"project": "docs-site"},
        {"project": {"id": "prj_docs", "name": "docs-site"}},
        {"id": "prj_docs"},
    ],
)
def test_agent_runs_entries_are_matched_by_any_key_the_cli_reads(
    entry: dict[str, Any],
) -> None:
    session = with_projects(
        project("prj_docs", "docs-site"),
        **{AGENT_RUNS_PATH: ok({"items": [entry]})},
    )
    assert ids(scan(session)) == ["prj_docs"]


def test_a_project_agent_runs_reports_with_zero_runs_is_not_flagged() -> None:
    session = with_projects(
        project("prj_docs", "docs-site"),
        **{AGENT_RUNS_PATH: ok(agent_runs(runs_entry("prj_docs", "docs-site", 0)))},
    )
    assert scan(session) == []


def test_agent_runs_for_projects_outside_the_scan_are_not_reported(
    caplog: pytest.LogCaptureFixture,
) -> None:
    session = with_projects(
        project("prj_docs", "docs-site"),
        **{AGENT_RUNS_PATH: ok(agent_runs(runs_entry("prj_other", "other")))},
    )
    assert scan_logged(session, caplog) == []
    assert "1 project(s) outside this scan's projects" in caplog.text


@pytest.mark.parametrize(
    "response",
    [
        error(403),
        error(404, "not_found"),
        error(401),
        FakeResponse(307, None, {"Location": "https://vercel.com/login"}),
        FakeResponse(200, "<html>login</html>", {"Content-Type": "text/html"}, True),
        ok({"runs": "many"}),
        ok([1, 2]),
        requests.ConnectionError("dashboard unreachable"),
        requests.exceptions.ReadTimeout("slow"),
    ],
)
def test_agent_runs_that_cannot_be_read_is_one_warning_and_the_scan_goes_on(
    response: Any,
    caplog: pytest.LogCaptureFixture,
) -> None:
    session = FakeSession({AGENT_RUNS_PATH: response})
    records = scan_logged(session, caplog)
    assert sorted(ids(records)) == ["prj_chat", "prj_img"]
    warnings = [
        r.getMessage()
        for r in caplog.records
        if r.levelno == logging.WARNING and "Agent Runs" in r.getMessage()
    ]
    assert len(warnings) == 1
    assert "undocumented endpoint that may change" in warnings[0]
    assert TOKEN not in caplog.text


# -- Observability Plus -----------------------------------------------------------------


def test_a_team_without_observability_plus_is_said_once_and_asked_once(
    caplog: pytest.LogCaptureFixture,
) -> None:
    session = FakeSession()
    records = scan_logged(session, caplog)
    assert sorted(ids(records)) == ["prj_chat", "prj_img"]
    assert len(session.calls_to(OBSERVABILITY_QUERY_PATH)) == 1
    said = [r for r in caplog.records if "Observability Plus not enabled" in r.message]
    assert len(said) == 1 and said[0].levelno == logging.INFO


def test_a_token_refused_observability_is_a_warning_and_asked_once(
    caplog: pytest.LogCaptureFixture,
) -> None:
    session = FakeSession({OBSERVABILITY_QUERY_PATH: error(403)})
    records = scan_logged(session, caplog)
    assert sorted(ids(records)) == ["prj_chat", "prj_img"]
    assert len(session.calls_to(OBSERVABILITY_QUERY_PATH)) == 1
    assert "refused POST /v2/observability/query" in caplog.text


def test_the_queries_are_scoped_to_the_team_and_grouped_by_project() -> None:
    session = FakeSession({OBSERVABILITY_QUERY_PATH: observability()})
    scan(session, lookback_hours=24)
    gateway, hosts = session.calls_to(OBSERVABILITY_QUERY_PATH)
    for call in (gateway, hosts):
        assert call["method"] == "POST"
        assert call["url"] == API_BASE_URL + OBSERVABILITY_QUERY_PATH
        assert call["params"]["teamId"] == TEAM_ID
        assert call["allow_redirects"] is False
        body = call["json"]
        assert body["scope"] == {"type": "owner", "ownerId": TEAM_ID}
        assert body["aggregation"] == "sum"
        assert body["startTime"] == "2025-10-01T00:00:00.000Z"
        assert body["endTime"] == "2025-10-02T00:00:00.000Z"
        assert body["granularity"] == {"hours": 1}
    assert gateway["json"]["metric"] == "vercel.ai_gateway_request.count"
    assert gateway["json"]["groupBy"] == ["project_name", "ai_model", "auth_method"]
    assert "filter" not in gateway["json"]
    assert hosts["json"]["metric"] == "vercel.external_api_request.count"
    assert hosts["json"]["groupBy"] == ["project_name", "request_hostname"]
    assert hosts["json"]["filter"] == llm_host_filter()


def test_ai_gateway_traffic_flags_an_oidc_project_and_names_its_models(
    caplog: pytest.LogCaptureFixture,
) -> None:
    # The blind spot of key detection: OIDC, so no key at all.
    gateway = ok(
        metric_rows(
            AI_GATEWAY_METRIC,
            {
                "project_name": "docs-site",
                "ai_model": "openai/gpt-5",
                "auth_method": "oidc",
                "count": 40,
            },
            {
                "project_name": "docs-site",
                "ai_model": "anthropic/claude-sonnet-4.5",
                "auth_method": "oidc",
                "count": "2",
            },
            {
                "project_name": "not-in-team",
                "ai_model": "x/y",
                "auth_method": "api_key",
                "count": 1,
            },
        ),
    )
    session = FakeSession({OBSERVABILITY_QUERY_PATH: observability(gateway=gateway)})
    records = scan_logged(session, caplog)
    by_id = {r.external_id: r for r in records}
    assert sorted(by_id) == ["prj_chat", "prj_docs", "prj_img"]
    assert [m.name for m in by_id["prj_docs"].llm_models] == [
        "anthropic/claude-sonnet-4.5",
        "openai/gpt-5",
    ]
    assert by_id["prj_chat"].llm_models is None
    line = evidence_line(caplog, "prj_docs")
    assert "AI Gateway requests (models anthropic/claude-sonnet-4.5, openai/gpt-5" in (
        line
    )
    assert "auth oidc" in line
    check_batch(records, "Source config 'vercel' (vercel_ai)")


def test_a_gateway_group_with_zero_requests_flags_nothing() -> None:
    gateway = ok(
        metric_rows(
            AI_GATEWAY_METRIC,
            {"project_name": "docs-site", "ai_model": "m", "count": 0},
        ),
    )
    session = with_projects(
        project("prj_docs", "docs-site"),
        **{OBSERVABILITY_QUERY_PATH: observability(gateway=gateway)},
    )
    assert scan(session) == []


def test_a_time_series_answer_is_read_from_data(
    caplog: pytest.LogCaptureFixture,
) -> None:
    gateway = ok(
        metric_rows(
            AI_GATEWAY_METRIC,
            {"project_name": "docs-site", "ai_model": "m", "count": 1},
            {"project_name": "docs-site", "ai_model": "m", "count": 2},
            series=True,
        ),
    )
    session = with_projects(
        project("prj_docs", "docs-site"),
        **{OBSERVABILITY_QUERY_PATH: observability(gateway=gateway)},
    )
    [record] = scan_logged(session, caplog)
    assert [m.name for m in record.llm_models] == ["m"]


def test_llm_api_traffic_flags_a_project_and_other_hosts_do_not(
    caplog: pytest.LogCaptureFixture,
) -> None:
    hosts = ok(
        metric_rows(
            EXTERNAL_API_METRIC,
            {
                "project_name": "docs-site",
                "request_hostname": "bedrock-runtime.us-east-1.amazonaws.com",
                "count": 9,
            },
            {
                "project_name": "docs-site",
                "request_hostname": "API.OPENAI.COM",
                "count": 1,
            },
            # Returned anyway (a filter Vercel ignored): matched here too.
            {
                "project_name": "image-studio",
                "request_hostname": "s3.amazonaws.com",
                "count": 100,
            },
        ),
    )
    session = with_projects(
        project("prj_docs", "docs-site"),
        project("prj_img", "image-studio"),
        **{OBSERVABILITY_QUERY_PATH: observability(hosts=hosts)},
    )
    records = scan_logged(session, caplog)
    assert ids(records) == ["prj_docs"]
    line = evidence_line(caplog, "prj_docs")
    assert (
        "LLM API host(s) api.openai.com, bedrock-runtime.us-east-1.amazonaws.com"
        in line
    )


def test_a_refused_host_filter_is_asked_again_without_it(
    caplog: pytest.LogCaptureFixture,
) -> None:
    hosts = [
        error(400, "bad_request"),
        ok(
            metric_rows(
                EXTERNAL_API_METRIC,
                {
                    "project_name": "docs-site",
                    "request_hostname": "api.anthropic.com",
                    "count": 3,
                },
            ),
        ),
    ]
    session = with_projects(
        project("prj_docs", "docs-site"),
        **{OBSERVABILITY_QUERY_PATH: observability(hosts=hosts)},
    )
    assert ids(scan_logged(session, caplog)) == ["prj_docs"]
    _, filtered, unfiltered = session.calls_to(OBSERVABILITY_QUERY_PATH)
    assert "filter" in filtered["json"] and "filter" not in unfiltered["json"]
    assert "refused the LLM host filter" in caplog.text


@pytest.mark.parametrize(
    "response",
    [
        error(500, "internal"),
        error(400, "bad_request"),
        ok({"rows": []}),
        FakeResponse(200, "<html/>", {"Content-Type": "text/html"}, text_body=True),
        requests.ConnectionError("down"),
    ],
)
def test_a_failed_gateway_query_is_a_warning_and_the_host_query_is_still_asked(
    response: Any,
    caplog: pytest.LogCaptureFixture,
) -> None:
    hosts = ok(
        metric_rows(
            EXTERNAL_API_METRIC,
            {
                "project_name": "docs-site",
                "request_hostname": "api.groq.com",
                "count": 1,
            },
        ),
    )
    session = with_projects(
        project("prj_docs", "docs-site"),
        **{OBSERVABILITY_QUERY_PATH: observability(gateway=response, hosts=hosts)},
    )
    assert ids(scan_logged(session, caplog)) == ["prj_docs"]
    assert AI_GATEWAY_METRIC in caplog.text and "not checked" in caplog.text
    assert "observability partly read" in caplog.text


def test_a_failed_host_query_is_a_warning_and_the_gateway_still_counts(
    caplog: pytest.LogCaptureFixture,
) -> None:
    gateway = ok(
        metric_rows(
            AI_GATEWAY_METRIC,
            {"project_name": "docs-site", "ai_model": "m", "count": 1},
        ),
    )
    session = with_projects(
        project("prj_docs", "docs-site"),
        **{
            OBSERVABILITY_QUERY_PATH: observability(
                gateway=gateway,
                hosts=error(503, "unavailable"),
            ),
        },
    )
    assert ids(scan_logged(session, caplog)) == ["prj_docs"]
    assert EXTERNAL_API_METRIC in caplog.text and "HTTP 503" in caplog.text


def test_an_answer_with_as_many_groups_as_asked_for_is_reported(
    caplog: pytest.LogCaptureFixture,
) -> None:
    rows = [{"project_name": f"p{i}", "ai_model": "m", "count": 1} for i in range(100)]
    session = with_projects(
        project("prj_docs", "docs-site"),
        **{
            OBSERVABILITY_QUERY_PATH: observability(
                gateway=ok(metric_rows(AI_GATEWAY_METRIC, *rows)),
            ),
        },
    )
    scan_logged(session, caplog, logging.WARNING)
    assert "as many groups as were asked for" in caplog.text


@pytest.mark.parametrize(
    "host, expected",
    [
        ("api.openai.com", True),
        ("api.anthropic.com", True),
        ("ai-gateway.vercel.sh", True),
        ("generativelanguage.googleapis.com", True),
        ("us-central1-aiplatform.googleapis.com", True),
        ("my-resource.openai.azure.com", True),
        ("api.groq.com", True),
        ("api.mistral.ai", True),
        ("bedrock-runtime.eu-west-1.amazonaws.com", True),
        ("bedrock-runtime-fips.us-east-1.amazonaws.com", False),
        ("bedrock.us-east-1.amazonaws.com", False),
        ("s3.amazonaws.com", False),
        ("openai.com", False),
        (".openai.azure.com", False),
        ("api.stripe.com", False),
    ],
)
def test_llm_hosts_are_the_documented_ones(host: str, expected: bool) -> None:
    assert is_llm_host(host) is expected


def test_the_host_filter_names_every_host_it_matches() -> None:
    text = llm_host_filter()
    for host in ("api.openai.com", "api.anthropic.com", "ai-gateway.vercel.sh"):
        assert f"request_hostname eq '{host}'" in text
    assert (
        "(startswith(request_hostname, 'bedrock-runtime.') and "
        "endswith(request_hostname, '.amazonaws.com'))" in text
    )
    assert "endswith(request_hostname, '.openai.azure.com')" in text


@pytest.mark.parametrize(
    "lookback, hours",
    [(1, 1), (24, 24), (0, ACTIVITY_WINDOW_MAX_HOURS), (24 * 90, 24 * 30)],
)
def test_the_activity_window_is_the_lookback_capped_at_thirty_days(
    lookback: int,
    hours: int,
) -> None:
    start, end = activity_window(lookback, 1_000_000_000.5)
    assert end == 1_000_000_000
    assert end - start == hours * 3600


@pytest.mark.parametrize(
    "hours, expected",
    [
        (1, {"minutes": 1}),
        (2, {"minutes": 5}),
        (12, {"minutes": 15}),
        (72, {"hours": 1}),
        (720, {"hours": 4}),
        (721, {"days": 1}),
    ],
)
def test_the_granularity_is_the_one_the_cli_picks(
    hours: int,
    expected: dict[str, int],
) -> None:
    assert granularity_for(hours * 3600) == expected


# -- deployment sources (package.json) ---------------------------------------------------


def cli_project(
    pid: str = "prj_cli",
    name: str = "summarizer",
    dpl: str = "dpl_cli",
    meta: Optional[dict[str, str]] = None,
) -> dict[str, Any]:
    production = deployment(T_DEPLOYED, T_READY, id=dpl)
    if meta is not None:
        production["meta"] = meta
    return project(pid, name, production=production)


SOURCES_ON = {**FIELDS, READ_DEPLOYMENT_SOURCES_FIELD: "true"}


def test_deployment_sources_are_not_read_unless_the_source_opts_in() -> None:
    session = with_projects(cli_project())
    assert scan(session) == []
    assert not any("/deployments/" in path for path in session.paths())


def test_an_ai_library_in_src_package_json_flags_a_project_with_no_other_signal(
    caplog: pytest.LogCaptureFixture,
) -> None:
    session = with_projects(
        cli_project(),
        **{
            deployment_files_path("dpl_cli"): ok(
                file_tree(
                    tree_dir("src", tree_file("package.json", "file_pkg")),
                    tree_dir("out"),
                ),
            ),
            deployment_file_path("dpl_cli", "file_pkg"): ok(
                package_json("ai", "@ai-sdk/openai", "next", "zod"),
            ),
        },
    )
    records = scan_logged(session, caplog, fields=SOURCES_ON)
    assert ids(records) == ["prj_cli"]
    line = evidence_line(caplog, "prj_cli")
    assert "package(s) @ai-sdk/openai, ai in src/package.json" in line
    assert "next" not in line
    assert "1 package.json read" in caplog.text


def test_a_root_package_json_is_read_when_src_has_none() -> None:
    session = with_projects(
        cli_project(),
        **{
            deployment_files_path("dpl_cli"): ok(
                file_tree(tree_file("package.json", "file_root")),
            ),
            deployment_file_path("dpl_cli", "file_root"): ok(
                package_json("@anthropic-ai/sdk"),
            ),
        },
    )
    assert ids(scan(session, fields=SOURCES_ON)) == ["prj_cli"]


def test_a_package_json_without_ai_libraries_flags_nothing() -> None:
    session = with_projects(
        cli_project(),
        **{
            deployment_files_path("dpl_cli"): ok(
                file_tree(tree_dir("src", tree_file("package.json", "f"))),
            ),
            deployment_file_path("dpl_cli", "f"): ok(package_json("next", "react")),
        },
    )
    assert scan(session, fields=SOURCES_ON) == []


def test_a_deployment_whose_meta_names_a_git_commit_is_not_asked_for_files(
    caplog: pytest.LogCaptureFixture,
) -> None:
    session = with_projects(
        cli_project(meta={"githubCommitSha": "abc", "githubCommitRef": "main"}),
    )
    assert scan_logged(session, caplog, fields=SOURCES_ON) == []
    assert not any("/deployments/" in path for path in session.paths())
    assert "1 Git or without a file tree" in caplog.text


def test_a_file_tree_not_found_is_skipped_quietly(
    caplog: pytest.LogCaptureFixture,
) -> None:
    session = with_projects(
        cli_project(),
        **{
            deployment_files_path("dpl_cli"): FakeResponse(
                404,
                {"error": {"code": "not_found", "message": "File tree not found"}},
            ),
        },
    )
    assert scan_logged(session, caplog, fields=SOURCES_ON) == []
    assert not [r for r in caplog.records if r.levelno >= logging.WARNING]
    assert "1 Git or without a file tree" in caplog.text


def test_a_project_without_a_production_deployment_is_not_asked_for_files(
    caplog: pytest.LogCaptureFixture,
) -> None:
    session = with_projects(project("prj_x", "x"))
    assert scan_logged(session, caplog, fields=SOURCES_ON) == []
    assert not any("/deployments/" in path for path in session.paths())
    assert "1 without a production deployment" in caplog.text


def test_the_newest_production_entry_of_latest_deployments_is_used() -> None:
    body = project(
        "prj_cli",
        "summarizer",
        deployments=[
            deployment(T_CREATED, id="dpl_old", target="production"),
            deployment(T_DEPLOYED, id="dpl_new", target="production"),
            deployment(T_READY, id="dpl_preview", target="preview"),
        ],
    )
    session = with_projects(
        body,
        **{deployment_files_path("dpl_new"): ok(file_tree())},
    )
    scan(session, fields=SOURCES_ON)
    assert deployment_files_path("dpl_new") in session.paths()


def test_a_tree_without_a_package_json_reads_no_file(
    caplog: pytest.LogCaptureFixture,
) -> None:
    session = with_projects(
        cli_project(),
        **{
            deployment_files_path("dpl_cli"): ok(
                file_tree(tree_dir("src", tree_file("index.js", "f"))),
            ),
        },
    )
    assert scan_logged(session, caplog, fields=SOURCES_ON) == []
    assert "1 without a package.json" in caplog.text
    assert not any("/files/" in path for path in session.paths())


def test_refused_file_trees_are_one_summary_warning(
    caplog: pytest.LogCaptureFixture,
) -> None:
    session = with_projects(
        cli_project("prj_a", "a", "dpl_a"),
        cli_project("prj_b", "b", "dpl_b"),
        **{
            deployment_files_path("dpl_a"): error(403),
            deployment_files_path("dpl_b"): error(403),
        },
    )
    assert scan_logged(session, caplog, fields=SOURCES_ON) == []
    warnings = [r.getMessage() for r in caplog.records if r.levelno == logging.WARNING]
    assert [w for w in warnings if "file tree" in w] == [
        "Vercel refused 2 deployment file tree(s) to this token (403); those "
        "projects' package.json were not checked.",
    ]


@pytest.mark.parametrize(
    "contents",
    [
        ok({"data": "!!!not base64!!!"}),
        ok({"data": base64.b64encode(f"not json {PACKAGE_SECRET}".encode()).decode()}),
        ok({"data": base64.b64encode(json.dumps([PACKAGE_SECRET]).encode()).decode()}),
        ok({"data": "A" * (1024 * 1024)}),
        ok({"size": 3}),
        error(500, "internal"),
        requests.ConnectionError("down"),
    ],
)
def test_an_unreadable_package_json_is_a_warning_that_quotes_none_of_it(
    contents: Any,
    caplog: pytest.LogCaptureFixture,
) -> None:
    session = with_projects(
        cli_project(),
        chat(),
        **{
            env_path("prj_chat"): ok(envs(env_var("OPENAI_API_KEY"))),
            deployment_files_path("dpl_cli"): ok(
                file_tree(tree_dir("src", tree_file("package.json", "f"))),
            ),
            deployment_file_path("dpl_cli", "f"): contents,
        },
    )
    records = scan_logged(session, caplog, logging.DEBUG, fields=SOURCES_ON)
    assert ids(records) == ["prj_chat"]
    assert "prj_cli" in caplog.text and "package.json was not read" in caplog.text
    assert PACKAGE_SECRET not in caplog.text


def test_only_one_package_json_is_read_per_project() -> None:
    session = with_projects(
        cli_project(),
        **{
            deployment_files_path("dpl_cli"): ok(
                file_tree(
                    tree_dir("src", tree_file("package.json", "f_src")),
                    tree_file("package.json", "f_root"),
                ),
            ),
            deployment_file_path("dpl_cli", "f_src"): ok(package_json("openai")),
        },
    )
    assert ids(scan(session, fields=SOURCES_ON)) == ["prj_cli"]
    assert [p for p in session.paths() if "/files/" in p] == [
        deployment_file_path("dpl_cli", "f_src"),
    ]


@pytest.mark.parametrize(
    "name, expected",
    [
        ("ai", True),
        ("@ai-sdk/openai", True),
        ("@ai-sdk/react", True),
        ("openai", True),
        ("@anthropic-ai/sdk", True),
        ("@aws-sdk/client-bedrock-runtime", True),
        ("@aws-sdk/client-bedrock-agent-runtime", True),
        ("@aws-sdk/client-bedrock", True),
        ("langchain", True),
        ("@mastra/core", True),
        ("eve", True),
        ("@aws-sdk/client-s3", False),
        ("aiohttp", False),
        ("openai-edge-x", False),
        ("ai-sdk", False),
        ("@ai-sdkx/openai", False),
        ("react", False),
    ],
)
def test_ai_libraries_are_the_documented_ones(name: str, expected: bool) -> None:
    assert is_ai_package(name) is expected


def test_no_package_json_content_reaches_logs_records_or_errors(
    caplog: pytest.LogCaptureFixture,
) -> None:
    session = with_projects(
        cli_project(),
        **{
            deployment_files_path("dpl_cli"): ok(
                file_tree(tree_dir("src", tree_file("package.json", "f"))),
            ),
            deployment_file_path("dpl_cli", "f"): ok(
                package_json("ai", description=PACKAGE_SECRET),
            ),
        },
    )
    records = scan_logged(session, caplog, logging.DEBUG, fields=SOURCES_ON)
    dumped = json.dumps([r.model_dump(mode="json") for r in records])
    assert ids(records) == ["prj_cli"]
    assert PACKAGE_SECRET not in caplog.text and PACKAGE_SECRET not in dumped


# -- stopping between the new calls -----------------------------------------------------


@pytest.mark.parametrize(
    "last, never",
    [
        (INTEGRATIONS_PATH, SHARED_ENV_PATH),
        (SHARED_ENV_PATH, team_path(TEAM_ID)),
        (team_path(TEAM_ID), AGENT_RUNS_PATH),
        (AGENT_RUNS_PATH, OBSERVABILITY_QUERY_PATH),
        (deployment_files_path("dpl_cli"), deployment_file_path("dpl_cli", "f")),
    ],
)
def test_a_stop_after_each_extra_call_sends_nothing_more(
    last: str,
    never: str,
) -> None:
    session = with_projects(
        cli_project(),
        **{
            deployment_files_path("dpl_cli"): ok(
                file_tree(tree_dir("src", tree_file("package.json", "f"))),
            ),
            deployment_file_path("dpl_cli", "f"): ok(package_json("ai")),
        },
    )
    connector = connector_with(session)
    connector.stop_when(lambda: bool(session.calls) and session.paths()[-1] == last)
    list(connector.scan(config(), 24, CREDS, SOURCES_ON, LOG))
    assert last in session.paths()
    assert never not in session.paths()
    assert session.paths()[-1] == last


def test_a_stop_between_the_two_observability_queries_sends_only_one() -> None:
    session = FakeSession({OBSERVABILITY_QUERY_PATH: observability()})
    connector = connector_with(session)
    connector.stop_when(
        lambda: len(session.calls_to(OBSERVABILITY_QUERY_PATH)) == 1,
    )
    list(connector.scan(config(), 24, CREDS, FIELDS, LOG))
    assert len(session.calls_to(OBSERVABILITY_QUERY_PATH)) == 1


# -- every new signal at once, values and the token stay out -----------------------------


def test_no_value_token_or_file_content_reaches_logs_with_every_signal_on(
    caplog: pytest.LogCaptureFixture,
) -> None:
    session = with_projects(
        cli_project(),
        chat(),
        **{
            env_path("prj_chat"): ok(envs(env_var("OPENAI_API_KEY", "plain"))),
            SHARED_ENV_PATH: ok(
                shared(shared_var("ANTHROPIC_API_KEY", ["prj_chat"], "plain")),
            ),
            AGENT_RUNS_PATH: ok(agent_runs(runs_entry("prj_chat", "support-chat"))),
            OBSERVABILITY_QUERY_PATH: observability(
                gateway=ok(
                    metric_rows(
                        AI_GATEWAY_METRIC,
                        {
                            "project_name": "support-chat",
                            "ai_model": "openai/gpt-5",
                            "auth_method": "api_key",
                            "count": 5,
                        },
                    ),
                ),
            ),
            deployment_files_path("dpl_cli"): ok(
                file_tree(tree_dir("src", tree_file("package.json", "f"))),
            ),
            deployment_file_path("dpl_cli", "f"): ok(package_json("@mastra/core")),
        },
    )
    records = scan_logged(session, caplog, logging.DEBUG, fields=SOURCES_ON)
    assert sorted(ids(records)) == ["prj_chat", "prj_cli"]
    line = evidence_line(caplog, "prj_chat")
    for part in (
        "environment variable(s) OPENAI_API_KEY",
        "shared variable(s) ANTHROPIC_API_KEY",
        "Agent Runs (3 production run(s))",
        "AI Gateway requests (models openai/gpt-5; auth api_key)",
    ):
        assert part in line
    dumped = json.dumps([r.model_dump(mode="json") for r in records])
    for text in (caplog.text, dumped):
        assert PLAIN_VALUE not in text and ENCRYPTED_VALUE not in text
        assert TOKEN not in text and PACKAGE_SECRET not in text
