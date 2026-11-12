"""The Azure AI Foundry connector, against fakes and a mocked wire.

Most tests hand the connector a fake `FoundryAgents`. A few run the real
azure-ai-projects client over `responses`, so the URLs, the api-version and the error
types are the SDK's own rather than what these tests assume them to be.

The failure tests guard what an admin sees: a principal Entra refuses and a project the
principal cannot read must arrive as `authentication_failed` and `permission_denied`,
not as the `provider_error` that sends them to Azure's status page.
"""

import logging
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any, Iterable, Iterator, Optional, Sequence

import pytest
import responses
from arthur_client.api_bindings import DiscoverySourceConfigSpec
from arthur_common.models.agent_governance_schemas import (
    CloudAgentCreationSource,
    RunsOn,
)
from azure.ai.projects.models import AgentDetails
from azure.core.credentials import AccessToken, TokenCredential
from azure.core.exceptions import (
    ClientAuthenticationError,
    HttpResponseError,
)
from azure.core.paging import ItemPaged
from azure.identity import ClientSecretCredential, DefaultAzureCredential
from responses import matchers

from discovery.cloud.azure_ai_foundry import connector as foundry
from discovery.cloud.azure_ai_foundry.client import (
    ALLOW_DEFAULT_CREDENTIAL_ENV_VAR,
    FoundryAgents,
    FoundrySettings,
    credential_from,
    project_agents,
    settings_from,
)
from discovery.cloud.azure_ai_foundry.connector import (
    VENDOR,
    AzureAIFoundryConnector,
    FoundryListingError,
    external_id_for,
)
from job_executors.discovery_output_contract import check_batch
from job_executors.discovery_scan import (
    DiscoveryConfigurationError,
    DiscoveryErrorCode,
    DiscoveryPublishResult,
    DiscoveryScanOutcome,
    failure_code,
    run_source_scan,
)

LOG = logging.getLogger("discovery-test")

ENDPOINT = "https://contoso-foundry.services.ai.azure.com/api/projects/support-bots"
TENANT = "72f988bf-86f1-41af-91ab-2d7cd011db47"
CLIENT = "00000000-1111-2222-3333-444444444444"
SECRET = "NOT-A-REAL-SECRET~abc123"
FIELDS = {"project_endpoint": ENDPOINT, "tenant_id": TENANT, "client_id": CLIENT}
CREDS: dict[str, Optional[str]] = {"client_secret": SECRET}
CREATED = datetime(2026, 1, 8, 16, 34, 10, tzinfo=timezone.utc)


def agent_json(
    name: str,
    *,
    state: str = "enabled",
    created_at: Optional[int] = int(CREATED.timestamp()),
    definition: Optional[dict[str, Any]] = None,
    version: str = "3",
) -> dict[str, Any]:
    """An agent as Foundry's REST API returns it."""
    latest: dict[str, Any] = {
        "object": "agent.version",
        "id": f"{name}:{version}",
        "name": name,
        "version": version,
        "metadata": {},
        "definition": definition
        or {
            "kind": "prompt",
            "model": "gpt-4o-mini",
            "instructions": "SECRET-PROMPT-TEXT",
            "tools": [
                {"type": "function", "name": "lookup_order", "parameters": {}},
                {"type": "code_interpreter"},
            ],
        },
    }
    if created_at is not None:
        latest["created_at"] = created_at
    return {
        "object": "agent",
        "id": f"asst_{name}",
        "name": name,
        "state": state,
        "versions": {"latest": latest},
    }


def resource_id(record: Any) -> str:
    rid: str = record.creation_source.address.resource_id
    return rid


def agent(name: str, **kwargs: Any) -> AgentDetails:
    """The SDK's own model, deserialized from the wire shape."""
    return AgentDetails(agent_json(name, **kwargs))


class FakeAgents:
    """Pages through the SDK's own `ItemPaged`.

    By default one page holding `agents`. `pages` gives (agents, next token) pairs
    instead. `error` is raised when the page after the last is asked for.
    """

    def __init__(
        self,
        agents: Iterable[Any] = (),
        error: Optional[Exception] = None,
        pages: Optional[list[tuple[list[Any], Optional[str]]]] = None,
    ):
        self.listed = list(agents)
        self.error = error
        self.pages = pages

    def list(self) -> ItemPaged[Any]:
        if self.pages is not None:
            pages = self.pages
        else:
            pages = [(self.listed, "more" if self.error else None)]
        served = iter(pages)
        error = self.error

        def get_next(_token: Optional[str] = None) -> Any:
            page = next(served, None)
            if page is None:
                assert error is not None
                raise error
            return page

        def extract_data(page: Any) -> tuple[Optional[str], Iterator[Any]]:
            agents, token = page
            return token, iter(agents)

        return ItemPaged(get_next, extract_data)


class FakeFactory:
    def __init__(self, agents: FakeAgents) -> None:
        self.agents = agents
        self.calls: list[tuple[FoundrySettings, TokenCredential]] = []

    @contextmanager
    def __call__(
        self,
        settings: FoundrySettings,
        credential: TokenCredential,
    ) -> Iterator[FoundryAgents]:
        self.calls.append((settings, credential))
        yield self.agents


@pytest.fixture
def config() -> DiscoverySourceConfigSpec:
    return DiscoverySourceConfigSpec.model_construct(
        name="foundry",
        vendor=VENDOR,
        query=None,
    )


def scan(
    factory: Any,
    config: DiscoverySourceConfigSpec,
    creds: Optional[dict[str, Optional[str]]] = None,
    fields: Optional[dict[str, str]] = None,
) -> list[list[Any]]:
    return [
        list(batch)
        for batch in AzureAIFoundryConnector(agents_factory=factory).scan(
            config,
            24,
            CREDS if creds is None else creds,
            FIELDS if fields is None else fields,
            LOG,
        )
    ]


# --- identity and address ---------------------------------------------------------


def test_external_id_is_the_project_endpoint_and_agent_name(
    config: DiscoverySourceConfigSpec,
) -> None:
    [batch] = scan(
        FakeFactory(FakeAgents([agent("triage"), agent("refunds")])),
        config,
    )
    assert [r.external_id for r in batch] == [
        f"{ENDPOINT}/agents/triage",
        f"{ENDPOINT}/agents/refunds",
    ]


def test_external_id_is_stable_across_spellings_of_the_endpoint(
    config: DiscoverySourceConfigSpec,
) -> None:
    spelled = ENDPOINT.replace("contoso-foundry", "Contoso-Foundry").replace(
        "https",
        "HTTPS",
    )
    fields = {**FIELDS, "project_endpoint": f"  {spelled}/ "}
    [[record]] = scan(FakeFactory(FakeAgents([agent("triage")])), config, fields=fields)
    assert record.external_id == f"{ENDPOINT}/agents/triage"
    assert external_id_for(settings_from(fields), "triage") == record.external_id


def test_a_record_carries_cloud_provenance_with_resource_project_and_agent_name(
    config: DiscoverySourceConfigSpec,
) -> None:
    [[record]] = scan(FakeFactory(FakeAgents([agent("triage")])), config)

    assert record.name == "triage"
    assert record.last_seen == CREATED
    assert record.runs_on is RunsOn.AZURE
    assert [m.name for m in record.llm_models] == ["gpt-4o-mini"]
    assert [t.name for t in record.tools] == ["lookup_order", "code_interpreter"]
    source = record.creation_source
    assert isinstance(source, CloudAgentCreationSource)
    assert source.vendor == "azure_ai_foundry"
    assert source.address.instance == "contoso-foundry"
    assert source.address.scope == "support-bots"
    assert source.address.resource_id == "triage"
    assert source.address.query is None
    assert source.observations.version == "3"


def test_the_prompt_is_never_copied_into_the_record(
    config: DiscoverySourceConfigSpec,
) -> None:
    [[record]] = scan(FakeFactory(FakeAgents([agent("triage")])), config)
    assert "SECRET-PROMPT-TEXT" not in record.model_dump_json()


def test_an_agent_without_a_model_or_tools_has_neither(
    config: DiscoverySourceConfigSpec,
) -> None:
    hosted = agent(
        "hosted-bot",
        definition={"kind": "hosted", "cpu": "1", "memory": "2Gi"},
    )
    [[record]] = scan(FakeFactory(FakeAgents([hosted])), config)
    assert record.llm_models is None
    assert record.tools is None


def test_output_satisfies_the_discovery_output_contract(
    config: DiscoverySourceConfigSpec,
) -> None:
    [batch] = scan(FakeFactory(FakeAgents([agent("triage")])), config)
    check_batch(batch, "Source config 'foundry' (azure_ai_foundry)")


def test_an_agent_with_no_creation_time_is_skipped_not_dated_to_the_scan(
    config: DiscoverySourceConfigSpec,
    caplog: pytest.LogCaptureFixture,
) -> None:
    undated = agent("undated", created_at=None)
    with caplog.at_level(logging.WARNING):
        [batch] = scan(FakeFactory(FakeAgents([undated, agent("triage")])), config)
    assert [resource_id(r) for r in batch] == ["triage"]
    assert "no latest version with a creation time" in caplog.text


def test_an_agent_listed_twice_fails_the_scan(
    config: DiscoverySourceConfigSpec,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The SDK pages on `last_id` alone; a repeat means it would page forever. What was
    already published stays, but the scan must not read as a complete inventory."""
    monkeypatch.setattr(foundry, "BATCH_SIZE", 1)
    looping = FakeAgents([agent("a"), agent("b"), agent("a"), agent("b")])
    published: list[str] = []
    with pytest.raises(FoundryListingError, match="listed agent a twice") as exc:
        for batch in AzureAIFoundryConnector(FakeFactory(looping)).scan(
            config,
            24,
            CREDS,
            FIELDS,
            LOG,
        ):
            published += [resource_id(r) for r in batch]
    assert published == ["a", "b"]
    assert failure_code(exc.value) is DiscoveryErrorCode.PROVIDER_ERROR


def test_a_repeated_page_token_fails_the_scan_even_without_agents(
    config: DiscoverySourceConfigSpec,
) -> None:
    """Empty pages that keep naming a next page never repeat an agent."""
    stalled = FakeAgents(
        pages=[([agent("a")], "t1"), ([], "t2"), ([], "t2"), ([], "t2")],
    )
    with pytest.raises(FoundryListingError, match="repeated the page token t2") as exc:
        scan(FakeFactory(stalled), config)
    assert failure_code(exc.value) is DiscoveryErrorCode.PROVIDER_ERROR


def test_agents_across_pages_are_all_listed(
    config: DiscoverySourceConfigSpec,
) -> None:
    paged = FakeAgents(
        pages=[([agent("a"), agent("b")], "t1"), ([agent("c")], "t2"), ([], None)],
    )
    [batch] = scan(FakeFactory(paged), config)
    assert [resource_id(r) for r in batch] == ["a", "b", "c"]


def test_an_external_agent_is_not_reported_as_running_on_azure(
    config: DiscoverySourceConfigSpec,
) -> None:
    external = agent(
        "on-gcp",
        definition={"kind": "external", "otel_agent_id": "on-gcp"},
    )
    [batch] = scan(FakeFactory(FakeAgents([agent("triage"), external])), config)
    assert [resource_id(r) for r in batch] == ["triage"]


class ClosingCredential(ClientSecretCredential):
    closed = 0

    def close(self) -> None:
        ClosingCredential.closed += 1


@pytest.mark.parametrize("error", [None, HttpResponseError(message="boom")])
def test_the_credential_is_closed_after_the_scan(
    error: Optional[Exception],
    config: DiscoverySourceConfigSpec,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(ClosingCredential, "closed", 0)
    monkeypatch.setattr(
        foundry,
        "credential_from",
        lambda settings, creds: ClosingCredential(TENANT, CLIENT, SECRET),
    )
    factory = FakeFactory(FakeAgents([agent("triage")], error))
    if error is None:
        scan(factory, config)
    else:
        with pytest.raises(HttpResponseError):
            scan(factory, config)
    assert ClosingCredential.closed == 1


def test_records_are_batched(
    config: DiscoverySourceConfigSpec,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(foundry, "BATCH_SIZE", 2)
    batches = scan(
        FakeFactory(FakeAgents([agent(f"agent-{i}") for i in range(5)])),
        config,
    )
    assert [len(b) for b in batches] == [2, 2, 1]


def test_an_empty_project_yields_nothing(config: DiscoverySourceConfigSpec) -> None:
    assert scan(FakeFactory(FakeAgents([])), config) == []


# --- settings ----------------------------------------------------------------------


def test_the_endpoint_and_principal_reach_the_factory(
    config: DiscoverySourceConfigSpec,
) -> None:
    factory = FakeFactory(FakeAgents([]))
    scan(factory, config)
    [(settings, credential)] = factory.calls
    assert settings == FoundrySettings(
        project_endpoint=ENDPOINT,
        resource_name="contoso-foundry",
        project_name="support-bots",
        tenant_id=TENANT,
        client_id=CLIENT,
    )
    assert isinstance(credential, ClientSecretCredential)


@pytest.mark.parametrize("value", [None, "", "  "])
def test_a_missing_project_endpoint_is_named(value: Optional[str]) -> None:
    fields = {"tenant_id": TENANT}
    if value is not None:
        fields["project_endpoint"] = value
    with pytest.raises(DiscoveryConfigurationError, match="project_endpoint") as exc:
        settings_from(fields)
    assert failure_code(exc.value) is DiscoveryErrorCode.NOT_CONFIGURED


@pytest.mark.parametrize(
    "endpoint",
    [
        "http://contoso.services.ai.azure.com/api/projects/p",
        "https://contoso.services.ai.azure.com",
        "https://contoso.services.ai.azure.com/api/projects",
        "https://contoso.services.ai.azure.com/api/projects/p/agents",
        "https://contoso.services.ai.azure.com/projects/p",
        "https://contoso.services.ai.azure.com/api/projects/p?x=1",
        "contoso.services.ai.azure.com/api/projects/p",
        # The scan sends the host a token, so only public Azure's Foundry domain.
        "https://attacker.example.com/api/projects/p",
        "https://contoso.services.ai.azure.com.example.com/api/projects/p",
        "https://services.ai.azure.com/api/projects/p",
        "https://a.contoso.services.ai.azure.com/api/projects/p",
        "https://contoso.services.ai.azure.us/api/projects/p",
        "https://user@contoso.services.ai.azure.com/api/projects/p",
        "https://contoso.services.ai.azure.com:8443/api/projects/p",
        "https://contoso.services.ai.azure.com:abc/api/projects/p",
    ],
)
def test_an_endpoint_that_is_not_a_project_endpoint_is_refused(endpoint: str) -> None:
    with pytest.raises(
        DiscoveryConfigurationError,
        match="not a Foundry project",
    ) as exc:
        settings_from({"project_endpoint": endpoint})
    assert failure_code(exc.value) is DiscoveryErrorCode.NOT_CONFIGURED


def test_the_default_https_port_is_normalised_away() -> None:
    settings = settings_from(
        {"project_endpoint": ENDPOINT.replace(".com/", ".com:443/")},
    )
    assert settings.project_endpoint == ENDPOINT


# --- credentials -------------------------------------------------------------------


def test_a_service_principal_is_used_when_all_three_are_set(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(ALLOW_DEFAULT_CREDENTIAL_ENV_VAR, "true")
    credential = credential_from(settings_from(FIELDS), CREDS)
    assert isinstance(credential, ClientSecretCredential)


@pytest.mark.parametrize(
    ("fields", "creds", "missing"),
    [
        ({"tenant_id": TENANT, "client_id": CLIENT}, {}, "'client_secret'"),
        ({"tenant_id": TENANT}, CREDS, "'client_id'"),
        ({"client_id": CLIENT}, {"client_secret": " "}, "'tenant_id', 'client_secret'"),
    ],
)
def test_a_partial_service_principal_is_refused_naming_what_is_missing(
    fields: dict[str, str],
    creds: dict[str, Optional[str]],
    missing: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Even with the default credential allowed: a half-set principal is a mistake,
    # not a request to scan as the engine.
    monkeypatch.setenv(ALLOW_DEFAULT_CREDENTIAL_ENV_VAR, "true")
    settings = settings_from({"project_endpoint": ENDPOINT, **fields})
    with pytest.raises(DiscoveryConfigurationError, match=missing) as exc:
        credential_from(settings, creds)
    assert SECRET not in str(exc.value)


def test_no_principal_fails_unless_the_engine_opts_in(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = settings_from({"project_endpoint": ENDPOINT})
    monkeypatch.delenv(ALLOW_DEFAULT_CREDENTIAL_ENV_VAR, raising=False)
    with pytest.raises(DiscoveryConfigurationError, match="client_secret") as exc:
        credential_from(settings, {})
    assert ALLOW_DEFAULT_CREDENTIAL_ENV_VAR in str(exc.value)
    assert failure_code(exc.value) is DiscoveryErrorCode.NOT_CONFIGURED

    monkeypatch.setenv(ALLOW_DEFAULT_CREDENTIAL_ENV_VAR, "false")
    with pytest.raises(DiscoveryConfigurationError):
        credential_from(settings, {"client_secret": None})


def test_no_principal_uses_the_default_credential_when_the_engine_opts_in(
    config: DiscoverySourceConfigSpec,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(ALLOW_DEFAULT_CREDENTIAL_ENV_VAR, "yes")
    factory = FakeFactory(FakeAgents([agent("triage")]))
    [[record]] = scan(
        factory,
        config,
        creds={"client_secret": None},
        fields={"project_endpoint": ENDPOINT},
    )
    [(_, credential)] = factory.calls
    assert isinstance(credential, DefaultAzureCredential)
    assert resource_id(record) == "triage"


def test_a_malformed_tenant_is_the_sources_to_fix() -> None:
    settings = settings_from({**FIELDS, "tenant_id": "not a tenant!"})
    with pytest.raises(DiscoveryConfigurationError, match="Invalid tenant") as exc:
        credential_from(settings, CREDS)
    assert SECRET not in str(exc.value)
    assert exc.value.__cause__ is None


def test_the_scan_never_logs_the_secret(
    config: DiscoverySourceConfigSpec,
    caplog: pytest.LogCaptureFixture,
) -> None:
    with caplog.at_level(logging.DEBUG):
        scan(FakeFactory(FakeAgents([agent("triage")])), config)
    assert SECRET not in caplog.text
    assert "SECRET-PROMPT-TEXT" not in caplog.text
    assert "support-bots" in caplog.text  # the project is not a secret, and names it


# --- failures: what Azure answered -------------------------------------------------


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


class StaticToken:
    """A TokenCredential that never calls Entra."""

    def __init__(self, error: Optional[Exception] = None) -> None:
        self.error = error
        self.scopes: list[tuple[str, ...]] = []

    def get_token(self, *scopes: str, **kwargs: Any) -> AccessToken:
        self.scopes.append(scopes)
        if self.error is not None:
            raise self.error
        return AccessToken("fake-token", int(time.time()) + 3600)


def wire_factory(credential: TokenCredential) -> Any:
    """The real `project_agents`, with the source's credential swapped for `credential`."""

    @contextmanager
    def factory(
        settings: FoundrySettings,
        _: TokenCredential,
    ) -> Iterator[FoundryAgents]:
        with project_agents(settings, credential) as agents:
            yield agents

    return factory


def add_listing(rsps: responses.RequestsMock, *agents: dict[str, Any]) -> None:
    """Foundry's list API over two pages: the agents, then an empty page.

    The SDK asks for the page after `last_id` until a page names none.
    """
    rsps.add(
        responses.GET,
        f"{ENDPOINT}/agents",
        match=[matchers.query_param_matcher({"api-version": "v1"})],
        json={
            "data": list(agents),
            "has_more": False,
            "first_id": agents[0]["id"] if agents else None,
            "last_id": agents[-1]["id"] if agents else None,
        },
    )
    if agents:
        rsps.add(
            responses.GET,
            f"{ENDPOINT}/agents",
            match=[
                matchers.query_param_matcher(
                    {"api-version": "v1", "after": agents[-1]["id"]},
                ),
            ],
            json={"data": [], "has_more": False, "first_id": None, "last_id": None},
        )


def error_body(code: str) -> dict[str, Any]:
    return {"error": {"code": code, "message": f"{code} on project support-bots"}}


@responses.activate
def test_the_real_sdk_lists_the_project_with_the_ai_azure_com_scope(
    config: DiscoverySourceConfigSpec,
) -> None:
    add_listing(responses.mock, agent_json("triage"), agent_json("refunds"))
    token = StaticToken()
    [batch] = scan(wire_factory(token), config)

    assert [resource_id(r) for r in batch] == ["triage", "refunds"]
    assert token.scopes[0] == ("https://ai.azure.com/.default",)
    assert responses.calls[0].request.headers["Authorization"] == "Bearer fake-token"


@responses.activate
def test_the_real_sdk_stalling_on_an_empty_page_fails_the_scan(
    config: DiscoverySourceConfigSpec,
) -> None:
    """The pinned SDK pages on `last_id` and ignores `has_more`, so a service that keeps
    answering an empty page naming the same `last_id` would be asked forever."""
    responses.add(
        responses.GET,
        f"{ENDPOINT}/agents",
        json={"data": [], "has_more": True, "first_id": None, "last_id": "asst_x"},
    )
    with pytest.raises(FoundryListingError, match="repeated the page token"):
        scan(wire_factory(StaticToken()), config)
    assert len(responses.calls) == 2


@pytest.mark.parametrize(
    ("status", "code", "expected"),
    [
        (401, "Unauthorized", DiscoveryErrorCode.AUTHENTICATION_FAILED),
        (403, "PermissionDenied", DiscoveryErrorCode.PERMISSION_DENIED),
        (404, "NotFound", DiscoveryErrorCode.PROVIDER_ERROR),
    ],
)
@responses.activate
def test_an_azure_http_error_is_classified_by_its_status(
    status: int,
    code: str,
    expected: DiscoveryErrorCode,
    config: DiscoverySourceConfigSpec,
) -> None:
    responses.add(
        responses.GET,
        f"{ENDPOINT}/agents",
        status=status,
        json=error_body(code),
    )
    with pytest.raises(HttpResponseError) as exc:
        scan(wire_factory(StaticToken()), config)
    assert exc.value.status_code == status
    assert failure_code(exc.value) is expected


def test_a_principal_entra_refuses_is_an_authentication_failure(
    config: DiscoverySourceConfigSpec,
) -> None:
    """Entra's token endpoint answers a wrong secret with a 400/401 of its own, raised by
    azure-identity before Foundry is asked; only the connector reads it as 401."""
    error = ClientAuthenticationError(
        message="AADSTS7000215: Invalid client secret provided.",
    )
    assert error.status_code is None
    with pytest.raises(ClientAuthenticationError) as exc:
        scan(wire_factory(StaticToken(error)), config)
    assert exc.value is error
    assert failure_code(exc.value) is DiscoveryErrorCode.AUTHENTICATION_FAILED


def test_a_denied_project_reaches_the_run_as_permission_denied(
    config: DiscoverySourceConfigSpec,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """End to end through the scan loop: the agent listed before the refusal is still
    published, and what `run_source_scan` re-raises is still the SDK's exception."""
    monkeypatch.setattr(foundry, "BATCH_SIZE", 1)
    with responses.RequestsMock() as rsps:
        rsps.add(
            responses.GET,
            f"{ENDPOINT}/agents",
            status=403,
            json=error_body("PermissionDenied"),
        )
        with project_agents(settings_from(FIELDS), StaticToken()) as real:
            try:
                list(real.list())
            except HttpResponseError as e:
                denied = e
    outcome = DiscoveryScanOutcome(
        discovery_source_config_id=None,
        discovery_source_config_name="foundry",
        discovery_source_id=None,
        vendor=VENDOR,
        job_id="job",
        scan_id=None,
        lookback_hours=24,
    )
    sink = AcceptingSink()

    with pytest.raises(HttpResponseError):
        run_source_scan(
            config=config,
            lookback_hours=24,
            workspace_id="workspace",
            data_plane_id="data-plane",
            outcome=outcome,
            connector=AzureAIFoundryConnector(
                agents_factory=FakeFactory(FakeAgents([agent("triage")], denied)),
            ),
            sink=sink,
            logger=LOG,
            credentials=CREDS,
            source_fields=FIELDS,
        )

    assert outcome.error_code is DiscoveryErrorCode.PERMISSION_DENIED
    assert outcome.error is not None and outcome.error.startswith("HttpResponseError")
    assert sink.published == [f"{ENDPOINT}/agents/triage"]


def test_a_missing_endpoint_reaches_the_run_as_not_configured(
    config: DiscoverySourceConfigSpec,
) -> None:
    outcome = DiscoveryScanOutcome(
        discovery_source_config_id=None,
        discovery_source_config_name="foundry",
        discovery_source_id=None,
        vendor=VENDOR,
        job_id="job",
        scan_id=None,
        lookback_hours=24,
    )
    with pytest.raises(DiscoveryConfigurationError):
        run_source_scan(
            config=config,
            lookback_hours=24,
            workspace_id="workspace",
            data_plane_id="data-plane",
            outcome=outcome,
            connector=AzureAIFoundryConnector(agents_factory=FakeFactory(FakeAgents())),
            sink=AcceptingSink(),
            logger=LOG,
            credentials=CREDS,
            source_fields={"tenant_id": TENANT},
        )
    assert outcome.error_code is DiscoveryErrorCode.NOT_CONFIGURED
