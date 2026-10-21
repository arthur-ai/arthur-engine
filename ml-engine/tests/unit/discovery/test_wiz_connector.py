"""Wiz AI-SPM connector: the token, the one query, its errors, and the records.

A fake session stands in for Wiz's token endpoint and a tenant's GraphQL endpoint. Its
bodies are shaped on PUBLIC sources, NOT captured from a live tenant: Wiz's hosts are
not reachable from where these were written. The token exchange and the GraphQL error
codes follow Wiz's Backstage plugin (wiz-sec-public/backstage-plugin-wiz, `WizAuth.ts`
and `types/index.ts`); the `cloudResources` node follows the Cortex XSOAR integration's
`PULL_CLOUD_RESOURCES_NATIVE_QUERY` (demisto/content, Packs/Wiz); the `graphSearch`
node follows jtb75-org/wiz-sample-reports `sensor-versions/get-data.py`. The
`properties` keys (`region`, `cloudPlatform`, `updatedAt`, `creationDate`,
`subscriptionExternalId`), the AI entity type names and the AI technology names are the
connector's assumptions, unverified; the pinned bodies below are named for that.
"""

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Callable, Optional, Sequence

import pytest
import requests
from arthur_client.api_bindings import DiscoverySourceConfigSpec
from arthur_common.models.agent_governance_schemas import (
    CloudAgentCreationSource,
    RunsOn,
)

from discovery import source_connectors
from discovery.cloud.wiz import connector as wiz
from discovery.cloud.wiz.client import (
    CLOUD_RESOURCES_QUERY,
    GRAPH_SEARCH_QUERY,
    PAGE_SIZE,
    TOKEN_URLS,
    WizClient,
    WizError,
    WizSettings,
)
from discovery.cloud.wiz.connector import (
    API_ENDPOINT_URL_FIELD,
    AUTH_ENVIRONMENT_FIELD,
    CLIENT_ID_FIELD,
    CLIENT_SECRET_FIELD,
    DEFAULT_ENTITY_TYPES,
    ENTITY_TYPES_FIELD,
    GLOBAL_SCOPE,
    VENDOR,
    WORKLOAD_INVENTORY_SCOPE,
    WORKLOAD_TECHNOLOGIES,
    WizConnector,
    settings_from,
)
from discovery.retry import MAX_ATTEMPTS
from job_executors.discovery_output_contract import check_batch
from job_executors.discovery_scan import (
    DENIED_PERMISSION,
    DENIED_UNREACHABLE,
    AcceptsStopCheck,
    DeniedScope,
    DiscoveryConfigurationError,
    DiscoveryErrorCode,
    DiscoveryPublishResult,
    DiscoveryScanOutcome,
    failure_code,
    run_source_scan,
)

LOG = logging.getLogger("test.wiz")
ENDPOINT = "https://api.us17.app.wiz.io/graphql"
CLIENT_ID = "wizclientidnotreal0123456789abcdefghijklmnopqrstu"
SECRET = "wiz-test-client-secret-not-real-0123456789"
ACCESS_TOKEN = "eyJhbGciOiJSUzI1NiJ9.wiz-access-token-not-real.c2ln"
CREDS = {"client_secret": SECRET}
FIELDS = {"api_endpoint_url": ENDPOINT, "client_id": CLIENT_ID}

AWS_ACCOUNT = "123456789012"
AZURE_SUBSCRIPTION = "0A1B2C3D-4E5F-4A6B-8C7D-9E0F1A2B3C4D"
GCP_PROJECT = "my-gcp-project"

LAST_SEEN = "2026-10-01T12:00:00Z"
UPDATED = "2026-09-15T08:30:00Z"
CREATED = "2026-01-02T03:04:05Z"

FREE_TEXT = "free text from Wiz that must not be echoed: secret-ish detail"


def utc(text: str) -> datetime:
    return datetime.fromisoformat(text).astimezone(timezone.utc)


# -- bodies shaped on the public sources --------------------------------------------------


def node(
    gid: str,
    *,
    provider_id: Optional[str] = "default",
    name: Optional[str] = "support-agent",
    entity_type: str = "AI_AGENT",
    account: Optional[str] = AWS_ACCOUNT,
    subscription_id: Optional[str] = "6f3c1a2e-sub-wiz-internal",
    properties: Any = "default",
    last_seen: Optional[str] = LAST_SEEN,
) -> dict[str, Any]:
    """A `cloudResources` node as XSOAR's query selects it."""
    if provider_id == "default":
        provider_id = f"arn:aws:bedrock:us-east-1:{AWS_ACCOUNT}:agent/{gid.upper()}"
    if properties == "default":
        properties = {
            "cloudPlatform": "AWS",
            "region": "us-east-1",
            "nativeType": "bedrock#agent",
            "creationDate": CREATED,
            "tags": {"owner": "secret-ish-tag-value"},
        }
    return {
        "id": gid,
        "name": name,
        "type": entity_type,
        "subscriptionId": subscription_id,
        "subscriptionExternalId": account,
        "graphEntity": {
            "id": gid,
            "providerUniqueId": provider_id,
            "name": name,
            "type": entity_type,
            "properties": properties,
            "firstSeen": CREATED,
            "lastSeen": last_seen,
        },
    }


def page_body(
    nodes: Sequence[dict[str, Any]],
    *,
    has_next: bool = False,
    cursor: Optional[str] = None,
) -> dict[str, Any]:
    return {
        "data": {
            "cloudResources": {
                "nodes": list(nodes),
                "pageInfo": {"hasNextPage": has_next, "endCursor": cursor},
            },
        },
    }


def graphql_error(code: Optional[str], message: str = FREE_TEXT) -> dict[str, Any]:
    error: dict[str, Any] = {"message": message, "path": ["cloudResources"]}
    if code is not None:
        error["extensions"] = {"code": code}
    return {"errors": [error], "data": None}


VM_ARN = f"arn:aws:ec2:us-east-1:{AWS_ACCOUNT}:instance/i-0abc123def4567890"
LAMBDA_ARN = f"arn:aws:lambda:us-west-2:{AWS_ACCOUNT}:function:support-bot"
IMAGE_ID = (
    f"{AWS_ACCOUNT}.dkr.ecr.us-east-1.amazonaws.com/agents@sha256:"
    + "0123456789abcdef" * 4
)


def entity(
    gid: str,
    entity_type: str,
    *,
    name: Optional[str] = None,
    provider_id: Optional[str] = None,
    properties: Any = None,
    last_seen: Optional[str] = None,
) -> dict[str, Any]:
    """A `graphSearch` path entity as the query selects it."""
    return {
        "id": gid,
        "name": name,
        "type": entity_type,
        "providerUniqueId": provider_id,
        "properties": properties if properties is not None else {},
        "firstSeen": CREATED,
        "lastSeen": last_seen,
    }


def sighting(
    tech: str = "LangChain",
    *,
    workload_type: str = "VIRTUAL_MACHINE",
    workload_gid: str = "wiz-vm-1",
    provider_id: Optional[str] = VM_ARN,
    workload_name: Optional[str] = "agents-host-1",
    account: Optional[str] = AWS_ACCOUNT,
    platform: str = "AWS",
    region: Optional[str] = "us-east-1",
    version: Optional[str] = "0.3.7",
    tech_last_seen: Optional[str] = LAST_SEEN,
    workload_last_seen: Optional[str] = UPDATED,
) -> dict[str, Any]:
    """One HOSTED_TECHNOLOGY and the workload that RUNS it, as one `graphSearch` node."""
    workload_properties: dict[str, Any] = {
        "cloudPlatform": platform,
        "externalId": "i-0abc123def4567890",
        "nativeType": "virtualMachine",
        "tags": {"owner": "secret-ish-tag-value"},
    }
    if account is not None:
        workload_properties["subscriptionExternalId"] = account
    if region is not None:
        workload_properties["region"] = region
    tech_properties: dict[str, Any] = {"techName": tech, "techId": "90210"}
    if version is not None:
        tech_properties["version"] = version
    return {
        "entities": [
            entity(
                f"wiz-tech-{tech}-{workload_gid}",
                "HOSTED_TECHNOLOGY",
                name=tech,
                properties=tech_properties,
                last_seen=tech_last_seen,
            ),
            entity(
                workload_gid,
                workload_type,
                name=workload_name,
                provider_id=provider_id,
                properties=workload_properties,
                last_seen=workload_last_seen,
            ),
        ],
    }


def graph_body(
    nodes: Sequence[dict[str, Any]],
    *,
    has_next: bool = False,
    cursor: Optional[str] = None,
) -> dict[str, Any]:
    return {
        "data": {
            "graphSearch": {
                "nodes": list(nodes),
                "pageInfo": {"hasNextPage": has_next, "endCursor": cursor},
            },
        },
    }


EMPTY_GRAPH = graph_body([])


# One page and one token answer, shaped field for field on the public sources. Not
# captured live: see the module docstring.
TOKEN_SHAPED_LIKE_WIZ_AUTH_TS: dict[str, Any] = {
    "access_token": ACCESS_TOKEN,
    "expires_in": 86400,
    "token_type": "Bearer",
}
PAGE_SHAPED_LIKE_XSOAR_CLOUD_RESOURCES_QUERY: dict[str, Any] = page_body(
    [
        node("wiz-aws-agent"),
        node(
            "wiz-azure-agent",
            provider_id=(
                f"/subscriptions/{AZURE_SUBSCRIPTION.lower()}/resourceGroups/rg-ai/"
                f"providers/Microsoft.CognitiveServices/accounts/foundry/projects/p1/"
                f"agents/asst_1"
            ),
            name="invoice-agent",
            account=AZURE_SUBSCRIPTION,
            properties={
                "cloudPlatform": "Azure",
                "location": "eastus2",
                "updatedAt": UPDATED,
            },
        ),
        node(
            "wiz-gcp-service",
            provider_id=(
                f"projects/{GCP_PROJECT}/locations/us-central1/reasoningEngines/111"
            ),
            name="",
            entity_type="AI_SERVICE",
            account=GCP_PROJECT,
            properties=json.dumps({"cloudPlatform": "GCP", "region": "us-central1"}),
        ),
    ],
)


# -- the fake Wiz ---------------------------------------------------------------------------


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


Route = Any  # a response, an exception, a list consumed in order, or a callable


class FakeSession:
    """Routes POSTs to a token URL to `token`, and to the GraphQL endpoint to `graphql`
    for `cloudResources` or `workloads` for `graphSearch`. Anything else is a call the
    connector must not make."""

    def __init__(
        self,
        graphql: Route = None,
        token: Route = None,
        workloads: Route = None,
    ) -> None:
        self.graphql: Route = (
            ok(PAGE_SHAPED_LIKE_XSOAR_CLOUD_RESOURCES_QUERY)
            if graphql is None
            else graphql
        )
        self.token: Route = (
            ok(TOKEN_SHAPED_LIKE_WIZ_AUTH_TS) if token is None else token
        )
        self.workloads: Route = ok(EMPTY_GRAPH) if workloads is None else workloads
        self.calls: list[dict[str, Any]] = []

    def post(self, url: str, **kw: Any) -> FakeResponse:
        self.calls.append({"url": url, **kw})
        if url in TOKEN_URLS.values():
            route = self.token
        elif _is_graph_search(kw):
            route = self.workloads
        elif url == ENDPOINT or url.endswith("/graphql"):
            route = self.graphql
        else:
            raise AssertionError(f"unexpected call to {url}")
        if isinstance(route, list):
            route = route.pop(0) if len(route) > 1 else route[0]
        if callable(route) and not isinstance(route, FakeResponse):
            route = route(kw)
        if isinstance(route, BaseException):
            raise route
        assert isinstance(route, FakeResponse)
        return route

    def get(self, url: str, **kw: Any) -> FakeResponse:
        raise AssertionError(f"unexpected GET {url}")

    def token_calls(self) -> list[dict[str, Any]]:
        return [c for c in self.calls if c["url"] in TOKEN_URLS.values()]

    def graphql_calls(self) -> list[dict[str, Any]]:
        """The `cloudResources` calls."""
        return [
            c
            for c in self.calls
            if c["url"] not in TOKEN_URLS.values() and not _is_graph_search(c)
        ]

    def workload_calls(self) -> list[dict[str, Any]]:
        return [c for c in self.calls if _is_graph_search(c)]


def _is_graph_search(kw: dict[str, Any]) -> bool:
    body = kw.get("json")
    return isinstance(body, dict) and "graphSearch(" in str(body.get("query"))


def connector_with(
    session: FakeSession,
    sleeps: Optional[list[float]] = None,
    clock: Callable[[], float] = lambda: 1_000.0,
) -> WizConnector:
    def factory(settings: WizSettings, log: logging.Logger) -> WizClient:
        return WizClient(
            settings,
            logger=log,
            session=session,  # type: ignore[arg-type]
            sleep=(sleeps if sleeps is not None else []).append,
            clock=clock,
        )

    return WizConnector(client_factory=factory)


def config() -> DiscoverySourceConfigSpec:
    return DiscoverySourceConfigSpec.model_construct(
        name="wiz",
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
    connector: Optional[WizConnector] = None,
) -> list[Any]:
    batches = (connector or connector_with(session, sleeps)).scan(
        config(),
        lookback_hours,
        CREDS if creds is None else creds,
        FIELDS if fields is None else fields,
        LOG,
    )
    return [record for batch in batches for record in batch]


def ids(records: list[Any]) -> list[str]:
    return [r.external_id for r in records]


def one(n: dict[str, Any]) -> Any:
    (record,) = scan(FakeSession(ok(page_body([n]))))
    return record


def pages(*answers: dict[str, Any]) -> Callable[[dict[str, Any]], FakeResponse]:
    """A GraphQL route answering each request with the next body, repeating the last."""
    queue = list(answers)

    def answer(kw: dict[str, Any]) -> FakeResponse:
        return ok(queue.pop(0) if len(queue) > 1 else queue[0])

    return answer


# -- registration ---------------------------------------------------------------------------


def test_the_connector_is_registered_under_wiz_ai_spm() -> None:
    assert VENDOR == "wiz_ai_spm"
    assert source_connectors()[VENDOR] is WizConnector
    assert isinstance(source_connectors()[VENDOR](), WizConnector)


def test_the_connector_declares_exactly_its_secrets() -> None:
    # The same set the Platform catalog marks is_sensitive.
    assert WizConnector.SENSITIVE_FIELDS == frozenset({"client_secret"})
    assert (
        API_ENDPOINT_URL_FIELD,
        AUTH_ENVIRONMENT_FIELD,
        CLIENT_ID_FIELD,
        CLIENT_SECRET_FIELD,
        ENTITY_TYPES_FIELD,
    ) == (
        "api_endpoint_url",
        "auth_environment",
        "client_id",
        "client_secret",
        "entity_types",
    )


# -- the requests ----------------------------------------------------------------------------


def test_the_token_is_a_form_encoded_client_credentials_grant_for_wiz_api() -> None:
    session = FakeSession()
    scan(session)
    (call,) = session.token_calls()
    assert call["url"] == "https://auth.app.wiz.io/oauth/token"
    assert call["data"] == {
        "grant_type": "client_credentials",
        "audience": "wiz-api",
        "client_id": CLIENT_ID,
        "client_secret": SECRET,
    }
    assert call["headers"]["Content-Type"] == "application/x-www-form-urlencoded"
    assert "json" not in call


@pytest.mark.parametrize(
    "environment, url",
    [
        ("commercial", "https://auth.app.wiz.io/oauth/token"),
        ("gov", "https://auth.gov.wiz.io/oauth/token"),
        ("fedramp", "https://auth.app.wiz.us/oauth/token"),
        (" FedRAMP ", "https://auth.app.wiz.us/oauth/token"),
        ("", "https://auth.app.wiz.io/oauth/token"),
    ],
)
def test_auth_environment_chooses_the_token_endpoint(
    environment: str,
    url: str,
) -> None:
    session = FakeSession()
    scan(session, fields={**FIELDS, "auth_environment": environment})
    assert [c["url"] for c in session.token_calls()] == [url]


def test_every_query_carries_the_bearer_token_to_the_endpoint() -> None:
    session = FakeSession()
    scan(session)
    (call,) = session.graphql_calls()
    assert call["url"] == ENDPOINT
    assert call["headers"]["Authorization"] == f"Bearer {ACCESS_TOKEN}"
    assert call["json"]["query"] == CLOUD_RESOURCES_QUERY


def test_redirects_are_refused_and_each_timeout_fits_the_preview_deadline() -> None:
    session = FakeSession()
    scan(session)
    assert len(session.calls) == 3
    for call in session.calls:
        assert call["allow_redirects"] is False
        connect, read = call["timeout"]
        # Each applies on its own, so together they must fit Test Connection's 120s.
        assert connect + read < 120


def test_only_the_token_and_the_cloud_resources_query_are_ever_sent() -> None:
    session = FakeSession(
        pages(
            page_body([node("a")], has_next=True, cursor="c1"),
            page_body([node("b")]),
        ),
    )
    scan(session)
    assert len(session.token_calls()) == 1
    for call in session.graphql_calls():
        query = call["json"]["query"]
        assert query == CLOUD_RESOURCES_QUERY
        assert query.startswith("query CloudResourceSearch(")
        assert "mutation" not in query
        assert set(call["json"]["variables"]) <= {"first", "after", "filterBy"}
        assert set(call["json"]["variables"]["filterBy"]) == {"type"}


def test_the_default_entity_types_are_sent_when_entity_types_is_blank() -> None:
    session = FakeSession()
    scan(session, fields={**FIELDS, "entity_types": "  "})
    variables = session.graphql_calls()[0]["json"]["variables"]
    assert variables["filterBy"] == {"type": list(DEFAULT_ENTITY_TYPES)}
    assert variables["first"] == PAGE_SIZE == 500
    assert "after" not in variables


def test_the_default_entity_types_are_the_documented_unverified_pair() -> None:
    assert DEFAULT_ENTITY_TYPES == ("AI_AGENT", "AI_SERVICE")


def test_entity_types_overrides_the_default_trimmed_upper_cased_and_deduplicated() -> (
    None
):
    session = FakeSession()
    scan(
        session,
        fields={**FIELDS, "entity_types": " ai_agent, SERVERLESS ,AI_AGENT,, "},
    )
    variables = session.graphql_calls()[0]["json"]["variables"]
    assert variables["filterBy"] == {"type": ["AI_AGENT", "SERVERLESS"]}


def test_the_lookback_is_not_applied() -> None:
    first, second = FakeSession(), FakeSession()
    assert ids(scan(first, lookback_hours=1)) == ids(scan(second, lookback_hours=0))
    assert [c["json"] for c in first.graphql_calls()] == [
        c["json"] for c in second.graphql_calls()
    ]
    # No time filter of any kind rides in the query.
    assert set(first.graphql_calls()[0]["json"]["variables"]["filterBy"]) == {"type"}


# -- paging ------------------------------------------------------------------------------


def test_paging_follows_the_end_cursor() -> None:
    session = FakeSession(
        pages(
            page_body([node("a")], has_next=True, cursor="c1"),
            page_body([node("b")], has_next=True, cursor="c2"),
            page_body([node("c")]),
        ),
    )
    assert len(ids(scan(session))) == 3
    afters = [c["json"]["variables"].get("after") for c in session.graphql_calls()]
    assert afters == [None, "c1", "c2"]
    # One token for the whole scan.
    assert len(session.token_calls()) == 1


def test_a_cursor_wiz_repeats_ends_the_listing_with_a_warning(
    caplog: pytest.LogCaptureFixture,
) -> None:
    session = FakeSession(
        pages(
            page_body([node("a")], has_next=True, cursor="c1"),
            page_body([node("b")], has_next=True, cursor="c1"),
        ),
    )
    with caplog.at_level(logging.WARNING):
        records = scan(session)
    assert len(records) == 2
    assert len(session.graphql_calls()) == 2
    assert "already returned" in caplog.text


def test_more_pages_without_a_cursor_ends_the_listing_with_a_warning(
    caplog: pytest.LogCaptureFixture,
) -> None:
    session = FakeSession(ok(page_body([node("a")], has_next=True, cursor=None)))
    with caplog.at_level(logging.WARNING):
        assert len(scan(session)) == 1
    assert len(session.graphql_calls()) == 1
    assert "no cursor" in caplog.text


def test_the_resource_list_stops_at_its_page_cap_with_a_warning(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    monkeypatch.setattr(wiz, "MAX_PAGES", 3)
    counter = iter(range(100))

    def endless(kw: dict[str, Any]) -> FakeResponse:
        n = next(counter)
        return ok(page_body([node(f"r{n}")], has_next=True, cursor=f"c{n}"))

    session = FakeSession(endless)
    with caplog.at_level(logging.WARNING):
        records = scan(session)
    assert len(records) == 3
    assert len(session.graphql_calls()) == 3
    assert "stopped at 3 pages" in caplog.text
    assert "entity_types" in caplog.text


def test_a_resource_on_two_pages_is_one_record() -> None:
    session = FakeSession(
        pages(
            page_body([node("a"), node("b")], has_next=True, cursor="c1"),
            page_body([node("b"), node("c")]),
        ),
    )
    records = scan(session)
    assert len(records) == 3
    assert len(set(ids(records))) == 3


def test_a_node_without_any_id_is_skipped_with_a_warning(
    caplog: pytest.LogCaptureFixture,
) -> None:
    broken = node("x")
    broken["id"] = None
    broken["graphEntity"]["id"] = ""
    with caplog.at_level(logging.WARNING):
        records = scan(FakeSession(ok(page_body([broken, node("a")]))))
    assert len(records) == 1
    assert "without an id" in caplog.text


# -- the records ---------------------------------------------------------------------------


def test_a_record_carries_cloud_provenance_with_account_region_and_provider_id() -> (
    None
):
    record = one(node("wiz-1"))
    arn = f"arn:aws:bedrock:us-east-1:{AWS_ACCOUNT}:agent/WIZ-1"
    assert record.external_id == arn
    assert record.name == "support-agent"
    source = record.creation_source
    assert isinstance(source, CloudAgentCreationSource)
    assert source.vendor == "wiz_ai_spm"
    assert source.address.instance == AWS_ACCOUNT
    assert source.address.scope == "us-east-1"
    assert source.address.resource_id == arn
    assert source.address.query is None


def test_the_identity_is_the_providers_own_id_verbatim() -> None:
    """Every pinned resource is keyed on its `providerUniqueId` exactly as Wiz sent it:
    not lower-cased, not prefixed, never Wiz's `graphEntity.id`."""
    nodes = PAGE_SHAPED_LIKE_XSOAR_CLOUD_RESOURCES_QUERY["data"]["cloudResources"][
        "nodes"
    ]
    records = scan(FakeSession())
    expected = [n["graphEntity"]["providerUniqueId"] for n in nodes]
    assert ids(records) == expected
    assert [r.creation_source.address.resource_id for r in records] == expected
    wiz_ids = {n["graphEntity"]["id"] for n in nodes}
    for record in records:
        assert record.external_id not in wiz_ids
        assert not record.external_id.startswith("wiz:")


@pytest.mark.parametrize("provider_id", [None, "", "   "])
def test_a_resource_without_a_provider_id_is_skipped_naming_its_entity_type(
    provider_id: Optional[str],
    caplog: pytest.LogCaptureFixture,
) -> None:
    unkeyed = node(
        "3f9a-graph-id",
        provider_id=provider_id,
        entity_type="AI_SERVICE",
        name="secret-ish-display-name",
    )
    with caplog.at_level(logging.WARNING):
        records = scan(FakeSession(ok(page_body([unkeyed, node("a")]))))
    assert ids(records) == [f"arn:aws:bedrock:us-east-1:{AWS_ACCOUNT}:agent/A"]
    assert all("3f9a-graph-id" not in (r.external_id, r.name) for r in records)
    warning = next(
        r.getMessage() for r in caplog.records if "providerUniqueId" in r.getMessage()
    )
    assert "AI_SERVICE" in warning and "skipped" in warning
    assert "secret-ish" not in caplog.text


def test_the_region_falls_back_to_location() -> None:
    record = one(
        node(
            "a",
            properties={"cloudPlatform": "Azure", "location": "westeurope"},
        ),
    )
    assert record.creation_source.address.scope == "westeurope"


@pytest.mark.parametrize("properties", [{}, None, "not json", {"region": "  "}])
def test_a_resource_without_a_region_is_scoped_global(properties: Any) -> None:
    record = one(node("a", properties=properties))
    assert record.creation_source.address.scope == GLOBAL_SCOPE == "global"


def test_an_azure_subscription_is_lower_cased_and_others_are_kept_verbatim() -> None:
    azure = one(
        node("a", account=AZURE_SUBSCRIPTION, properties={"cloudPlatform": "Azure"}),
    )
    assert azure.creation_source.address.instance == AZURE_SUBSCRIPTION.lower()
    other = one(
        node("b", account="MixedCase-Project", properties={"cloudPlatform": "GCP"}),
    )
    assert other.creation_source.address.instance == "MixedCase-Project"


def test_the_account_falls_back_to_wizs_subscription_id() -> None:
    record = one(node("a", account=None, subscription_id="wiz-sub-1"))
    assert record.creation_source.address.instance == "wiz-sub-1"


def test_a_resource_with_no_account_is_skipped_naming_only_its_id(
    caplog: pytest.LogCaptureFixture,
) -> None:
    with caplog.at_level(logging.WARNING):
        records = scan(
            FakeSession(
                ok(page_body([node("orphan", account=None, subscription_id=None)])),
            ),
        )
    assert records == []
    assert "orphan" in caplog.text and "account" in caplog.text


@pytest.mark.parametrize(
    "platform, runs_on",
    [
        ("AWS", RunsOn.AWS),
        ("Azure", RunsOn.AZURE),
        ("GCP", RunsOn.GCP),
        ("OCI", None),
        ("Kubernetes", None),
        (None, None),
    ],
)
def test_runs_on_is_set_only_for_clouds_runs_on_has(
    platform: Optional[str],
    runs_on: Optional[RunsOn],
) -> None:
    properties = {"region": "r1"} if platform is None else {"cloudPlatform": platform}
    assert one(node("a", properties=properties)).runs_on is runs_on


def test_a_record_leaves_service_names_models_and_platform_unset() -> None:
    record = one(node("a"))
    assert record.llm_models is None
    assert record.platform is None
    assert record.creation_source.observations is None or not (
        record.creation_source.observations.service_names
    )


def test_a_resource_without_a_name_is_named_by_its_id() -> None:
    assert one(node("named-by-id", name=None)).name == "named-by-id"
    assert one(node("blank", name="  ")).name == "blank"


@pytest.mark.parametrize(
    "last_seen, properties, expected",
    [
        (LAST_SEEN, {"updatedAt": UPDATED, "creationDate": CREATED}, LAST_SEEN),
        (None, {"updatedAt": UPDATED, "creationDate": CREATED}, UPDATED),
        (None, {"creationDate": CREATED}, CREATED),
        ("not a time", {"creationDate": CREATED}, CREATED),
    ],
)
def test_last_seen_is_wizs_last_seen_else_update_else_creation(
    last_seen: Optional[str],
    properties: dict[str, Any],
    expected: str,
) -> None:
    assert one(node("a", last_seen=last_seen, properties=properties)).last_seen == utc(
        expected,
    )


def test_a_naive_timestamp_is_read_as_utc() -> None:
    record = one(node("a", last_seen="2026-10-01T12:00:00"))
    assert record.last_seen == datetime(2026, 10, 1, 12, tzinfo=timezone.utc)


def test_a_resource_with_no_timestamps_is_skipped_naming_only_its_id(
    caplog: pytest.LogCaptureFixture,
) -> None:
    undated = node("undated-1", last_seen=None, properties={"region": "us-east-1"})
    with caplog.at_level(logging.WARNING):
        records = scan(FakeSession(ok(page_body([undated, node("a")]))))
    assert len(records) == 1
    assert "undated-1" in caplog.text and "skipped" in caplog.text
    assert "support-agent" not in caplog.text


def test_output_satisfies_the_discovery_output_contract() -> None:
    records = scan(FakeSession())
    assert records
    check_batch(records, "wiz")


def test_records_are_batched(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(wiz, "BATCH_SIZE", 2)
    session = FakeSession(ok(page_body([node(f"r{i}") for i in range(5)])))
    batches = list(connector_with(session).scan(config(), 24, CREDS, FIELDS, LOG))
    assert [len(b) for b in batches] == [2, 2, 1]


def test_completeness_is_reported_before_the_first_batch(
    caplog: pytest.LogCaptureFixture,
) -> None:
    session = FakeSession(ok(page_body([node("a")], has_next=True, cursor=None)))
    batches = connector_with(session).scan(config(), 24, CREDS, FIELDS, LOG)
    with caplog.at_level(logging.INFO):
        next(iter(batches))
    assert "listed 1 resource(s) over 1 page(s)" in caplog.text
    assert "no cursor" in caplog.text


def test_an_empty_inventory_is_a_success_that_says_so(
    caplog: pytest.LogCaptureFixture,
) -> None:
    with caplog.at_level(logging.INFO):
        assert scan(FakeSession(ok(page_body([])))) == []
    assert "listed no resources" in caplog.text and "entity_types" in caplog.text


# -- the stop check ---------------------------------------------------------------------


def test_the_connector_accepts_a_stop_check() -> None:
    assert isinstance(WizConnector(), AcceptsStopCheck)


def test_a_stop_before_the_first_call_sends_nothing() -> None:
    session = FakeSession()
    connector = connector_with(session)
    connector.stop_when(lambda: True)
    assert scan(session, connector=connector) == []
    assert session.calls == []


def test_a_stop_between_pages_hands_over_what_was_found_and_says_so(
    caplog: pytest.LogCaptureFixture,
) -> None:
    session = FakeSession(
        pages(
            page_body([node("a")], has_next=True, cursor="c1"),
            page_body([node("b")]),
        ),
    )
    connector = connector_with(session)
    connector.stop_when(lambda: len(session.graphql_calls()) >= 1)
    with caplog.at_level(logging.WARNING):
        records = scan(session, connector=connector)
    assert len(records) == 1
    assert len(session.graphql_calls()) == 1
    assert "stopped early" in caplog.text


def test_a_stop_during_a_retry_backoff_ends_the_scan_without_sleeping() -> None:
    session = FakeSession(FakeResponse(503))
    sleeps: list[float] = []
    connector = connector_with(session, sleeps)
    calls = {"n": 0}

    def stop() -> bool:
        calls["n"] += 1
        return calls["n"] > 1  # the pre-call check passes; the backoff check stops

    connector.stop_when(stop)
    assert scan(session, connector=connector) == []
    assert sleeps == []
    assert len(session.graphql_calls()) == 1


# -- configuration refusals --------------------------------------------------------------


@pytest.mark.parametrize(
    "fields, creds, missing",
    [
        ({"client_id": CLIENT_ID}, CREDS, "api_endpoint_url"),
        ({"api_endpoint_url": ENDPOINT}, CREDS, "client_id"),
        (FIELDS, {}, "client_secret"),
        (FIELDS, {"client_secret": "  "}, "client_secret"),
        (FIELDS, {"client_secret": None}, "client_secret"),
    ],
)
def test_missing_fields_are_named_and_nothing_is_sent(
    fields: dict[str, str],
    creds: dict[str, Optional[str]],
    missing: str,
) -> None:
    session = FakeSession()
    with pytest.raises(DiscoveryConfigurationError) as exc:
        scan(session, fields=fields, creds=creds)
    assert missing in str(exc.value)
    assert failure_code(exc.value) is DiscoveryErrorCode.NOT_CONFIGURED
    assert session.calls == []


@pytest.mark.parametrize(
    "url",
    [
        "https://api.us17.app.wiz.io/graphql",
        "https://api.us17.app.wiz.io/graphql/",
        "  https://API.EU1.app.wiz.io/graphql  ",
        "https://api.us-gov1.app.wiz.io/graphql",
        "https://api.fedramp1.app.wiz.us/graphql",
    ],
)
def test_a_wiz_graphql_endpoint_is_accepted(url: str) -> None:
    settings = settings_from(CREDS, {**FIELDS, "api_endpoint_url": url})
    assert settings.api_endpoint_url == url.strip().rstrip("/").lower()


@pytest.mark.parametrize(
    "url",
    [
        "http://api.us17.app.wiz.io/graphql",
        "https://api.us17.app.wiz.io",
        "https://api.us17.app.wiz.io/graphql?x=1",
        "https://app.wiz.io/graphql",
        "https://api.us17.app.wiz.io.attacker.example/graphql",
        "https://api.us17.app.wiz.com/graphql",
        "https://user:pass@api.us17.app.wiz.io/graphql",
        "https://api.us17.app.wiz.io:8443/graphql",
        "https://api..app.wiz.io/graphql",
        "api.us17.app.wiz.io/graphql",
    ],
)
def test_anything_but_a_wiz_graphql_endpoint_is_refused_without_echoing_it(
    url: str,
) -> None:
    session = FakeSession()
    with pytest.raises(DiscoveryConfigurationError) as exc:
        scan(session, fields={**FIELDS, "api_endpoint_url": url})
    assert "api_endpoint_url" in str(exc.value)
    assert url not in str(exc.value)
    assert "pass" not in str(exc.value)
    assert session.calls == []


def test_an_unknown_auth_environment_is_refused() -> None:
    session = FakeSession()
    with pytest.raises(DiscoveryConfigurationError) as exc:
        scan(session, fields={**FIELDS, "auth_environment": "staging"})
    assert "auth_environment" in str(exc.value)
    assert "commercial, gov, fedramp" in str(exc.value)
    assert session.calls == []


@pytest.mark.parametrize("value", ["AI AGENT", "AI-AGENT", "1AI", "AI_AGENT;{x}"])
def test_an_entity_type_that_is_not_a_name_is_refused(value: str) -> None:
    session = FakeSession()
    with pytest.raises(DiscoveryConfigurationError) as exc:
        scan(session, fields={**FIELDS, "entity_types": value})
    assert "entity_types" in str(exc.value)
    assert session.calls == []


def test_the_settings_are_trimmed() -> None:
    settings = settings_from(
        {"client_secret": f"  {SECRET}\n"},
        {"api_endpoint_url": f" {ENDPOINT} ", "client_id": f" {CLIENT_ID} "},
    )
    assert settings.client_secret == SECRET
    assert settings.client_id == CLIENT_ID
    assert settings.api_endpoint_url == ENDPOINT
    assert settings.auth_environment == "commercial"
    assert settings.entity_types_overridden is False


# -- failures --------------------------------------------------------------------------------


def test_refused_client_credentials_are_an_authentication_failure_with_a_hint() -> None:
    session = FakeSession(
        token=FakeResponse(
            401,
            {"error": "access_denied", "error_description": FREE_TEXT},
        ),
    )
    with pytest.raises(WizError) as exc:
        scan(session)
    assert exc.value.status_code == 401
    assert failure_code(exc.value) is DiscoveryErrorCode.AUTHENTICATION_FAILED
    assert "client_id" in str(exc.value) and "auth_environment" in str(exc.value)
    assert "(access_denied)" in str(exc.value)
    assert FREE_TEXT not in str(exc.value)
    assert session.graphql_calls() == []


@pytest.mark.parametrize("http_status", [200, 401])
def test_unauthenticated_is_an_authentication_failure(http_status: int) -> None:
    session = FakeSession(FakeResponse(http_status, graphql_error("UNAUTHENTICATED")))
    with pytest.raises(WizError) as exc:
        scan(session)
    assert exc.value.status_code == 401
    assert failure_code(exc.value) is DiscoveryErrorCode.AUTHENTICATION_FAILED
    assert "api_endpoint_url" in str(exc.value)
    assert len(session.graphql_calls()) == 1


@pytest.mark.parametrize("http_status", [200, 403])
def test_a_missing_scope_is_permission_denied_naming_read_resources(
    http_status: int,
) -> None:
    with pytest.raises(WizError) as exc:
        scan(FakeSession(FakeResponse(http_status, graphql_error("UNAUTHORIZED"))))
    assert exc.value.status_code == 403
    assert failure_code(exc.value) is DiscoveryErrorCode.PERMISSION_DENIED
    assert "read:resources" in str(exc.value)
    assert FREE_TEXT not in str(exc.value)


def test_the_tenants_ip_allowlist_is_permission_denied_and_says_so() -> None:
    with pytest.raises(WizError) as exc:
        scan(FakeSession(FakeResponse(403, graphql_error("FORBIDDEN_IP"))))
    assert exc.value.status_code == 403
    assert failure_code(exc.value) is DiscoveryErrorCode.PERMISSION_DENIED
    assert "IP allowlist" in str(exc.value)
    assert "FORBIDDEN_IP" in str(exc.value)


@pytest.mark.parametrize(
    "fields, wording",
    [
        ({**FIELDS, "entity_types": "AI_THING"}, "every name in entity_types"),
        (FIELDS, "default AI entity types"),
    ],
)
def test_an_entity_type_wiz_does_not_know_is_the_sources_to_fix(
    fields: dict[str, str],
    wording: str,
) -> None:
    session = FakeSession(ok(graphql_error("BAD_USER_INPUT")))
    with pytest.raises(DiscoveryConfigurationError) as exc:
        scan(session, fields=fields)
    assert failure_code(exc.value) is DiscoveryErrorCode.NOT_CONFIGURED
    # No status for Test Connection to read as Wiz's error, on the exception, its
    # chain, or in its text.
    assert getattr(exc.value, "status_code", None) is None
    assert exc.value.__cause__ is None and exc.value.__context__ is None
    assert "HTTP" not in str(exc.value) and "400" not in str(exc.value)
    assert "entity_types" in str(exc.value) and wording in str(exc.value)
    assert FREE_TEXT not in str(exc.value)
    assert len(session.graphql_calls()) == 1


def test_no_graphql_api_at_the_endpoint_is_the_sources_to_fix() -> None:
    with pytest.raises(DiscoveryConfigurationError) as exc:
        scan(FakeSession(FakeResponse(404, text_body=True)))
    assert failure_code(exc.value) is DiscoveryErrorCode.NOT_CONFIGURED
    assert getattr(exc.value, "status_code", None) is None
    assert exc.value.__cause__ is None and exc.value.__context__ is None
    assert "HTTP" not in str(exc.value) and "404" not in str(exc.value)
    assert "api_endpoint_url" in str(exc.value)


def test_a_not_found_code_is_wizs_error_with_its_status() -> None:
    with pytest.raises(WizError) as exc:
        scan(FakeSession(ok(graphql_error("NOT_FOUND"))))
    assert exc.value.status_code == 404
    assert failure_code(exc.value) is DiscoveryErrorCode.PROVIDER_ERROR


@pytest.mark.parametrize("code", ["SOMETHING_NEW", None])
def test_errors_with_http_200_and_no_known_code_are_wizs_error(
    code: Optional[str],
) -> None:
    with pytest.raises(WizError) as exc:
        scan(FakeSession(ok(graphql_error(code))))
    assert exc.value.status_code == 200
    assert failure_code(exc.value) is DiscoveryErrorCode.PROVIDER_ERROR
    assert FREE_TEXT not in str(exc.value)


def test_a_rate_limit_inside_a_200_is_retried() -> None:
    sleeps: list[float] = []
    session = FakeSession(
        [ok(graphql_error("RATE_LIMIT_EXCEEDED")), ok(page_body([node("a")]))],
    )
    assert len(scan(session, sleeps=sleeps)) == 1
    assert len(session.graphql_calls()) == 2
    assert len(sleeps) == 1


def test_a_429_is_retried_after_what_wiz_asks() -> None:
    sleeps: list[float] = []
    session = FakeSession(
        [
            FakeResponse(
                429,
                graphql_error("RATE_LIMIT_EXCEEDED"),
                {"Retry-After": "7"},
            ),
            ok(page_body([node("a")])),
        ],
    )
    assert len(scan(session, sleeps=sleeps)) == 1
    assert sleeps == [7.0]


def test_a_rate_limit_that_persists_carries_429_after_every_retry() -> None:
    session = FakeSession(ok(graphql_error("RATE_LIMIT_EXCEEDED")))
    with pytest.raises(WizError) as exc:
        scan(session)
    assert exc.value.status_code == 429
    assert len(session.graphql_calls()) == MAX_ATTEMPTS


def test_a_5xx_that_persists_carries_its_status_after_every_retry() -> None:
    session = FakeSession(FakeResponse(502, text_body=True))
    with pytest.raises(WizError) as exc:
        scan(session)
    assert exc.value.status_code == 502
    assert failure_code(exc.value) is DiscoveryErrorCode.PROVIDER_ERROR
    assert len(session.graphql_calls()) == MAX_ATTEMPTS


def test_a_token_endpoint_5xx_is_retried() -> None:
    session = FakeSession(
        token=[FakeResponse(503), ok(TOKEN_SHAPED_LIKE_WIZ_AUTH_TS)],
    )
    assert len(scan(session)) == 3
    assert len(session.token_calls()) == 2


@pytest.mark.parametrize(
    "token_response",
    [
        FakeResponse(200, text_body=True),
        ok({"token_type": "Bearer"}),
        ok({"access_token": ""}),
        ok(["not", "an", "object"]),
    ],
)
def test_a_token_answer_without_a_token_is_wizs_error(token_response: Any) -> None:
    with pytest.raises(WizError) as exc:
        scan(FakeSession(token=token_response))
    assert exc.value.status_code == 200
    assert failure_code(exc.value) is DiscoveryErrorCode.PROVIDER_ERROR


@pytest.mark.parametrize(
    "response",
    [
        FakeResponse(200, text_body=True, headers={"Content-Type": "text/html"}),
        ok({"data": None}),
        ok({"data": {"cloudResources": None}}),
        ok({"data": {"cloudResources": {"nodes": "x", "pageInfo": {}}}}),
        ok({"data": {"cloudResources": {"nodes": []}}}),
        ok([1, 2, 3]),
    ],
)
def test_a_success_status_without_wizs_body_is_wizs_error(response: Any) -> None:
    with pytest.raises(WizError) as exc:
        scan(FakeSession(response))
    assert exc.value.status_code == 200
    assert failure_code(exc.value) is DiscoveryErrorCode.PROVIDER_ERROR
    assert "api_endpoint_url" in str(exc.value)


@pytest.mark.parametrize(
    "raised",
    [
        requests.ConnectionError("Failed to resolve api.us17.app.wiz.io"),
        requests.exceptions.ConnectTimeout("connect timed out"),
        requests.exceptions.ReadTimeout("read timed out"),
    ],
)
def test_an_unreachable_api_stays_the_same_network_error(raised: Exception) -> None:
    session = FakeSession(raised)
    with pytest.raises(type(raised)) as exc:
        scan(session)
    assert type(exc.value) is type(raised)
    assert exc.value.__cause__ is raised
    assert len(session.graphql_calls()) == MAX_ATTEMPTS
    # Unreachable is reported as the query's, once, not retried again around the token.
    assert len(session.token_calls()) == 1


def test_an_unreachable_token_endpoint_is_reported_as_the_tokens() -> None:
    session = FakeSession(token=requests.ConnectionError("no route"))
    with pytest.raises(requests.ConnectionError) as exc:
        scan(session)
    assert "token request" in str(exc.value)
    assert len(session.token_calls()) == MAX_ATTEMPTS
    assert session.graphql_calls() == []


def test_a_tls_failure_is_not_retried_and_names_the_engines_ca() -> None:
    session = FakeSession(requests.exceptions.SSLError("certificate verify failed"))
    with pytest.raises(requests.exceptions.SSLError) as exc:
        scan(session)
    assert len(session.graphql_calls()) == 1
    assert "REQUESTS_CA_BUNDLE" in str(exc.value)


def test_the_token_is_refreshed_before_it_lapses() -> None:
    now = {"t": 1_000.0}
    answers = pages(
        page_body([node("a")], has_next=True, cursor="c1"),
        page_body([node("b")], has_next=True, cursor="c2"),
        page_body([node("c")]),
    )

    def slow_page(kw: dict[str, Any]) -> FakeResponse:
        now["t"] += 40  # 120s lifetime less the 60s margin: due again after page 2
        return answers(kw)

    session = FakeSession(
        slow_page,
        token=ok({"access_token": ACCESS_TOKEN, "expires_in": 120}),
    )
    connector = connector_with(session, clock=lambda: now["t"])
    assert len(scan(session, connector=connector)) == 3
    assert [c["url"] in TOKEN_URLS.values() for c in session.calls] == [
        True,
        False,
        False,
        True,
        False,
        False,
    ]


def test_a_failure_part_way_hands_over_what_was_found_then_raises_unchanged(
    caplog: pytest.LogCaptureFixture,
) -> None:
    session = FakeSession(
        [
            ok(page_body([node("a")], has_next=True, cursor="c1")),
            ok(graphql_error("UNAUTHORIZED")),
        ],
    )
    got: list[Any] = []
    with caplog.at_level(logging.WARNING), pytest.raises(WizError) as exc:
        for batch in connector_with(session).scan(config(), 24, CREDS, FIELDS, LOG):
            got.extend(batch)
    assert len(got) == 1
    assert exc.value.status_code == 403
    assert "failed part-way" in caplog.text


def test_no_secret_or_token_reaches_logs_records_or_errors(
    caplog: pytest.LogCaptureFixture,
) -> None:
    texts: list[str] = []
    with caplog.at_level(logging.DEBUG):
        records = scan(FakeSession(workloads=ok(graph_body([sighting()]))))
        texts.extend(r.model_dump_json() for r in records)
        for session in (
            FakeSession(token=FakeResponse(401, {"error": "access_denied"})),
            FakeSession(ok(graphql_error("UNAUTHENTICATED"))),
            FakeSession(ok(graphql_error("BAD_USER_INPUT"))),
            FakeSession(FakeResponse(200, text_body=True)),
            FakeSession(workloads=FakeResponse(500, graphql_error("INTERNAL"))),
        ):
            with pytest.raises(Exception) as exc:
                scan(session)
            texts.append(str(exc.value))
    texts.append(caplog.text)
    for text in texts:
        assert SECRET not in text
        assert ACCESS_TOKEN not in text
        assert CLIENT_ID not in text
        assert "secret-ish" not in text


def test_responses_shaped_like_the_public_wiz_sources_parse() -> None:
    by_id = {r.external_id: r for r in scan(FakeSession())}
    aws = by_id[f"arn:aws:bedrock:us-east-1:{AWS_ACCOUNT}:agent/WIZ-AWS-AGENT"]
    assert aws.runs_on is RunsOn.AWS
    assert aws.last_seen == utc(LAST_SEEN)
    assert aws.creation_source.address.instance == AWS_ACCOUNT
    assert aws.creation_source.address.scope == "us-east-1"

    (azure,) = [r for r in by_id.values() if r.name == "invoice-agent"]
    assert azure.external_id.startswith(f"/subscriptions/{AZURE_SUBSCRIPTION.lower()}/")
    assert azure.runs_on is RunsOn.AZURE
    assert azure.creation_source.address.instance == AZURE_SUBSCRIPTION.lower()
    assert azure.creation_source.address.scope == "eastus2"

    gcp = by_id[f"projects/{GCP_PROJECT}/locations/us-central1/reasoningEngines/111"]
    # Properties arrive as a JSON string here, and the blank name falls back to the id.
    assert gcp.runs_on is RunsOn.GCP
    assert gcp.name == "wiz-gcp-service"
    assert gcp.creation_source.address.scope == "us-central1"
    check_batch(list(by_id.values()), "wiz")


# -- the workload inventory ----------------------------------------------------------------


def workload_scan(
    *nodes: dict[str, Any],
    caplog: Optional[pytest.LogCaptureFixture] = None,
) -> list[Any]:
    """The workload records only: the AI-SPM inventory answers empty."""
    session = FakeSession(ok(page_body([])), workloads=ok(graph_body(list(nodes))))
    if caplog is None:
        return scan(session)
    with caplog.at_level(logging.INFO):
        return scan(session)


def test_a_technology_on_a_vm_is_one_record_addressed_like_a_vms_software() -> None:
    (record,) = workload_scan(sighting())
    assert record.external_id == f"{VM_ARN}:langchain"
    assert record.name == "LangChain on agents-host-1"
    assert record.last_seen == utc(LAST_SEEN)
    assert record.runs_on is RunsOn.AWS
    source = record.creation_source
    assert isinstance(source, CloudAgentCreationSource)
    assert source.vendor == VENDOR
    assert source.address.instance == VM_ARN
    assert source.address.scope == f"{AWS_ACCOUNT}/us-east-1"
    assert source.address.resource_kind == "technology"
    assert source.address.resource_id == "LangChain"
    assert source.address.query is None
    assert source.observations.version == "0.3.7"
    assert source.observations.service_names == []
    assert not record.llm_models
    check_batch([record], "wiz")


def test_workload_records_carry_only_native_ids_never_wizs() -> None:
    records = workload_scan(
        sighting("OpenAI SDK", workload_type="SERVERLESS", provider_id=LAMBDA_ARN),
        sighting(
            "Model Context Protocol",
            workload_type="CONTAINER_IMAGE",
            provider_id=IMAGE_ID,
        ),
    )
    assert sorted(ids(records)) == sorted(
        [f"{LAMBDA_ARN}:openai-sdk", f"{IMAGE_ID}:model-context-protocol"],
    )
    for record in records:
        text = record.model_dump_json()
        assert "wiz-vm-1" not in text
        assert "wiz-tech-" not in text
        assert "90210" not in text


def test_a_workload_without_a_provider_id_is_skipped_naming_its_entity_type(
    caplog: pytest.LogCaptureFixture,
) -> None:
    records = workload_scan(
        sighting(workload_type="CONTAINER_IMAGE", provider_id=None),
        sighting("CrewAI"),
        caplog=caplog,
    )
    assert ids(records) == [f"{VM_ARN}:crewai"]
    assert "CONTAINER_IMAGE" in caplog.text
    assert "providerUniqueId" in caplog.text


def test_a_provider_id_in_the_workloads_properties_is_used_when_the_field_is_empty() -> (
    None
):
    node_ = sighting(provider_id=None)
    node_["entities"][1]["properties"]["providerUniqueId"] = VM_ARN
    (record,) = workload_scan(node_)
    assert record.creation_source.address.instance == VM_ARN


def test_technologies_not_on_the_list_are_left_out(
    caplog: pytest.LogCaptureFixture,
) -> None:
    records = workload_scan(
        sighting("OpenSSL"),
        sighting("nginx"),
        sighting("langchain"),
        caplog=caplog,
    )
    assert ids(records) == [f"{VM_ARN}:langchain"]
    assert "2 not on the engine's list" in caplog.text


def test_one_technology_on_one_workload_twice_is_one_record_dated_by_the_newest() -> (
    None
):
    older = sighting(tech_last_seen=CREATED, version="0.1.0")
    newer = sighting(tech_last_seen=LAST_SEEN, version="0.3.7")
    (record,) = workload_scan(older, newer, older)
    assert record.last_seen == utc(LAST_SEEN)
    assert record.creation_source.observations.version == "0.3.7"


def test_two_workloads_with_one_technology_are_two_records() -> None:
    other = f"arn:aws:ec2:us-east-1:{AWS_ACCOUNT}:instance/i-0fff"
    records = workload_scan(
        sighting(),
        sighting(workload_gid="wiz-vm-2", provider_id=other),
    )
    assert sorted(ids(records)) == sorted([f"{VM_ARN}:langchain", f"{other}:langchain"])


def test_last_seen_falls_back_to_the_workload_then_skips_without_one(
    caplog: pytest.LogCaptureFixture,
) -> None:
    (record,) = workload_scan(sighting(tech_last_seen=None))
    assert record.last_seen == utc(UPDATED)
    assert (
        workload_scan(
            sighting(tech_last_seen=None, workload_last_seen=None),
            caplog=caplog,
        )
        == []
    )
    assert "no lastSeen" in caplog.text


def test_a_workload_without_an_account_is_skipped_and_without_a_region_is_global(
    caplog: pytest.LogCaptureFixture,
) -> None:
    assert workload_scan(sighting(account=None), caplog=caplog) == []
    assert "names no cloud account" in caplog.text
    (record,) = workload_scan(sighting(region=None))
    assert record.creation_source.address.scope == f"{AWS_ACCOUNT}/{GLOBAL_SCOPE}"


def test_an_azure_workloads_account_is_lower_cased() -> None:
    (record,) = workload_scan(sighting(account=AZURE_SUBSCRIPTION, platform="Azure"))
    assert record.creation_source.address.scope == (
        f"{AZURE_SUBSCRIPTION.lower()}/us-east-1"
    )
    assert record.runs_on is RunsOn.AZURE


def test_a_path_without_a_technology_or_a_workload_is_skipped(
    caplog: pytest.LogCaptureFixture,
) -> None:
    lone = sighting()
    lone["entities"] = lone["entities"][:1]
    assert workload_scan(lone, {"entities": None}, caplog=caplog) == []
    assert "2 workload path(s)" in caplog.text


def test_the_workload_query_asks_for_the_listed_technologies_on_workloads() -> None:
    session = FakeSession()
    scan(session)
    (call,) = session.workload_calls()
    assert call["json"]["query"] == GRAPH_SEARCH_QUERY
    variables = call["json"]["variables"]
    assert variables["first"] == PAGE_SIZE
    assert variables["projectId"] == "*"
    assert "after" not in variables
    query = variables["query"]
    assert query["type"] == ["HOSTED_TECHNOLOGY"]
    assert query["where"] == {"techName": {"EQUALS": list(WORKLOAD_TECHNOLOGIES)}}
    (edge,) = query["relationships"]
    assert edge["type"] == [{"type": "RUNS", "reverse": True}]
    assert edge["with"] == {
        "type": ["VIRTUAL_MACHINE", "CONTAINER_IMAGE", "SERVERLESS"],
        "select": True,
    }


def test_only_the_token_and_the_two_queries_are_ever_sent() -> None:
    session = FakeSession(workloads=ok(graph_body([sighting()])))
    scan(session)
    queries = [c["json"]["query"] for c in session.calls if "json" in c]
    assert set(queries) == {CLOUD_RESOURCES_QUERY, GRAPH_SEARCH_QUERY}
    assert len(session.token_calls()) == 1
    for query in queries:
        assert query.lstrip().startswith("query ")
        assert "mutation" not in query
    assert len(session.calls) == 3


def test_workload_paging_follows_the_cursor_and_stops_on_a_repeat(
    caplog: pytest.LogCaptureFixture,
) -> None:
    other = f"arn:aws:ec2:us-east-1:{AWS_ACCOUNT}:instance/i-0fff"
    session = FakeSession(
        ok(page_body([])),
        workloads=pages(
            graph_body([sighting()], has_next=True, cursor="g1"),
            graph_body([sighting(provider_id=other)], has_next=True, cursor="g1"),
        ),
    )
    with caplog.at_level(logging.WARNING):
        records = scan(session)
    assert len(records) == 2
    afters = [c["json"]["variables"].get("after") for c in session.workload_calls()]
    assert afters == [None, "g1"]
    assert "already returned" in caplog.text


def test_the_workload_inventory_stops_at_its_page_cap(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    monkeypatch.setattr(wiz, "MAX_PAGES", 2)
    counter = {"n": 0}

    def endless(kw: dict[str, Any]) -> FakeResponse:
        counter["n"] += 1
        return ok(graph_body([sighting()], has_next=True, cursor=f"g{counter['n']}"))

    session = FakeSession(ok(page_body([])), workloads=endless)
    with caplog.at_level(logging.WARNING):
        scan(session)
    assert len(session.workload_calls()) == 2
    assert "workload inventory stopped at 2 pages" in caplog.text


def test_a_stop_after_the_resources_skips_the_workload_inventory_and_says_so(
    caplog: pytest.LogCaptureFixture,
) -> None:
    session = FakeSession()
    connector = connector_with(session)
    connector.stop_when(lambda: len(session.graphql_calls()) >= 1)
    with caplog.at_level(logging.WARNING):
        records = scan(session, connector=connector)
    assert len(records) == 3
    assert session.workload_calls() == []
    assert "workload inventory was not read" in caplog.text


@pytest.mark.parametrize(
    ("code", "reason"),
    [("UNAUTHORIZED", DENIED_PERMISSION), ("BAD_USER_INPUT", DENIED_UNREACHABLE)],
)
def test_a_refused_workload_inventory_is_partial_and_keeps_the_ai_spm_records(
    code: str,
    reason: str,
    caplog: pytest.LogCaptureFixture,
) -> None:
    session = FakeSession(workloads=ok(graphql_error(code)))
    connector = connector_with(session)
    with caplog.at_level(logging.WARNING):
        records = scan(session, connector=connector)
    assert len(records) == 3
    assert connector.denied_scopes() == (DeniedScope(WORKLOAD_INVENTORY_SCOPE, reason),)
    assert "refused the workload inventory" in caplog.text
    assert FREE_TEXT not in caplog.text


def test_any_other_workload_failure_publishes_what_was_found_then_raises(
    caplog: pytest.LogCaptureFixture,
) -> None:
    session = FakeSession(
        workloads=[
            ok(graph_body([sighting()], has_next=True, cursor="g1")),
            ok(graphql_error("UNAUTHENTICATED")),
        ],
    )
    connector = connector_with(session)
    got: list[Any] = []
    with caplog.at_level(logging.WARNING), pytest.raises(WizError) as exc:
        for batch in connector.scan(config(), 24, CREDS, FIELDS, LOG):
            got.extend(batch)
    assert exc.value.status_code == 401
    assert len(got) == 4
    assert connector.denied_scopes() == ()
    assert "failed part-way, in the workload inventory" in caplog.text


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
        discovery_source_config_name="wiz",
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


def test_a_scan_through_run_source_scan_publishes_the_resources() -> None:
    result, sink = outcome(), AcceptingSink()
    run(FakeSession(), result, sink)
    assert len(sink.published) == 3
    assert result.records_published == 3
    assert result.error is None
    assert result.output_column_check is not None


def test_refused_credentials_reach_the_run_as_authentication_failed() -> None:
    result, sink = outcome(), AcceptingSink()
    with pytest.raises(WizError):
        run(
            FakeSession(token=FakeResponse(401, {"error": "access_denied"})),
            result,
            sink,
        )
    assert result.error_code is DiscoveryErrorCode.AUTHENTICATION_FAILED
    assert result.error is not None and result.error.startswith("WizError: ")
    assert SECRET not in result.error
    assert sink.published == []


def test_a_failure_part_way_reaches_the_run_after_publishing_what_was_found() -> None:
    session = FakeSession(
        [
            ok(page_body([node("a")], has_next=True, cursor="c1")),
            FakeResponse(401, graphql_error("UNAUTHENTICATED")),
        ],
    )
    result, sink = outcome(), AcceptingSink()
    with pytest.raises(WizError):
        run(session, result, sink)
    assert len(sink.published) == 1
    assert result.error_code is DiscoveryErrorCode.AUTHENTICATION_FAILED


# -- a source id that arrives as a UUID object ---------------------------------------------

SOURCE_UUID = uuid.UUID("44444444-4444-4444-4444-444444444444")


def uuid_config() -> DiscoverySourceConfigSpec:
    """A config whose `discovery_source_id` is a `uuid.UUID`, not its string: what a
    caller that parsed the id hands over. `model_construct`, because the binding's own
    validation would refuse anything but a str."""
    return DiscoverySourceConfigSpec.model_construct(
        discovery_source_id=SOURCE_UUID,
        name="wiz",
        vendor=VENDOR,
        query="",
        query_language="none",
        lookback_window_seconds=86400,
        source_fields=FIELDS,
    )


def test_a_uuid_source_id_scans_like_a_string_one() -> None:
    """The connector never reads the source id, so a UUID object changes nothing in
    the records it builds."""
    batches = connector_with(FakeSession()).scan(uuid_config(), 24, CREDS, FIELDS, LOG)
    records = [record for batch in batches for record in batch]
    assert ids(records) == ids(scan(FakeSession()))
    check_batch(records, "wiz")


def test_a_uuid_source_id_runs_through_the_scan_loop_and_reports_its_string() -> None:
    sink = AcceptingSink()
    result = DiscoveryScanOutcome(
        discovery_source_config_id=None,
        discovery_source_config_name="wiz",
        discovery_source_id=str(SOURCE_UUID),
        vendor=VENDOR,
        job_id="job",
        scan_id=None,
        lookback_hours=24,
    )
    run_source_scan(
        config=uuid_config(),
        lookback_hours=24,
        workspace_id="workspace",
        data_plane_id="data-plane",
        outcome=result,
        connector=connector_with(FakeSession()),
        sink=sink,
        logger=LOG,
        credentials=CREDS,
        source_fields=FIELDS,
    )
    assert len(sink.published) == 3
    assert result.error is None
    assert result.records_published == 3
    assert result.discovery_source_id == "44444444-4444-4444-4444-444444444444"


def test_a_refused_workload_inventory_reaches_the_run_as_a_denied_scope() -> None:
    result, sink = outcome(), AcceptingSink()
    run(FakeSession(workloads=ok(graphql_error("UNAUTHORIZED"))), result, sink)
    assert result.records_published == 3
    assert result.error is None
    assert result.denied_scopes == [
        DeniedScope(WORKLOAD_INVENTORY_SCOPE, DENIED_PERMISSION),
    ]
