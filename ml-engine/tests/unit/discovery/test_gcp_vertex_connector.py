"""The Vertex AI Agent Engine connector, against a fake Vertex SDK.

The test that matters most is the verbatim one. Tasks the legacy Vertex poller created
are mapped by Google's resource name exactly as the API returned it -- with the project
NUMBER in it -- and GenAI Engine joins a record to such a task only when a service name
matches that key byte for byte. A record that rebuilt the name from the configured project
ID would look right in every other test and mint a duplicate task for every agent a
customer already has.

The failure tests guard the other half of what an admin sees: a key Google refuses and
a project the key cannot read must arrive as `authentication_failed` and
`permission_denied`, not as the `provider_error` that sends them to Google's status page.
"""

import json
import logging
from datetime import datetime, timezone
from types import SimpleNamespace
from typing import Any, Iterable, Iterator, Optional, Sequence

import pytest
from arthur_client.api_bindings import DiscoverySourceConfigSpec
from arthur_common.models.agent_governance_schemas import (
    CloudAgentCreationSource,
    RunsOn,
)
from google.auth.credentials import Credentials
from google.auth.exceptions import RefreshError, TransportError
from google.genai.errors import APIError, ClientError, ServerError

from discovery import source_connectors
from discovery.cloud.gcp_vertex import connector as vertex
from discovery.cloud.gcp_vertex.connector import (
    ALLOW_ADC_ENV_VAR,
    DEFAULT_LOCATION,
    VENDOR,
    AgentEngineLister,
    VertexAgentEngineConnector,
    VertexSettings,
    credentials_from,
    parse_resource_name,
    settings_from,
)
from job_executors.discovery_output_contract import check_batch
from job_executors.discovery_scan import (
    DiscoveryErrorCode,
    DiscoveryPublishResult,
    DiscoveryScanOutcome,
    failure_code,
    run_source_scan,
)

LOG = logging.getLogger("discovery-test")

# The shape of the real data in the GCP test project: an ID in the source, a NUMBER in
# the resource names the API returns.
PROJECT_ID = "example-project-123456"
PROJECT_NUMBER = "123456789012"
PERSONAL_ASSISTANT = (
    f"projects/{PROJECT_NUMBER}/locations/us-central1/"
    "reasoningEngines/1111111111111111111"
)
IMAGE_SCORING = (
    f"projects/{PROJECT_NUMBER}/locations/us-central1/"
    "reasoningEngines/2222222222222222222"
)
UPDATED = datetime(2026, 1, 8, 16, 34, 10, tzinfo=timezone.utc)
CREATED = datetime(2026, 1, 6, 19, 43, 33, tzinfo=timezone.utc)

FIELDS = {"project_id": PROJECT_ID, "location": "us-central1"}
FAKE_KEY = {
    "type": "service_account",
    "project_id": PROJECT_ID,
    "private_key_id": "abc123",
    "private_key": "-----BEGIN PRIVATE KEY-----\nNOT-A-REAL-KEY\n-----END PRIVATE KEY-----\n",
    "client_email": "discovery@example-project-123456.iam.gserviceaccount.com",
    "client_id": "1234567890",
    "token_uri": "https://oauth2.googleapis.com/token",
}
CREDS = {"service_account_key": json.dumps(FAKE_KEY)}


def engine(
    name: str,
    display_name: Optional[str] = None,
    update_time: Optional[datetime] = UPDATED,
    create_time: Optional[datetime] = CREATED,
) -> SimpleNamespace:
    """An object shaped like the SDK's AgentEngine: the fields live on `api_resource`."""
    return SimpleNamespace(
        api_resource=SimpleNamespace(
            name=name,
            display_name=display_name,
            update_time=update_time,
            create_time=create_time,
        ),
    )


class FakeLister:
    def __init__(self, engines: Iterable[Any]) -> None:
        self.engines = list(engines)
        self.calls: list[tuple[VertexSettings, Optional[Credentials]]] = []

    def __call__(
        self,
        settings: VertexSettings,
        credentials: Optional[Credentials],
    ) -> Iterable[Any]:
        self.calls.append((settings, credentials))
        return iter(self.engines)


@pytest.fixture
def config() -> DiscoverySourceConfigSpec:
    return DiscoverySourceConfigSpec.model_construct(
        name="vertex",
        vendor=VENDOR,
        query=None,
    )


@pytest.fixture
def stub_key_loader(monkeypatch: pytest.MonkeyPatch) -> list[dict[str, Any]]:
    """Stands in for google-auth's key parser, which would reject the fake PEM."""
    loaded: list[dict[str, Any]] = []

    def from_service_account_info(info: dict[str, Any], scopes: list[str]) -> Any:
        loaded.append({"info": info, "scopes": scopes})
        return SimpleNamespace(service_account_email=info["client_email"])

    monkeypatch.setattr(
        vertex.service_account.Credentials,
        "from_service_account_info",
        staticmethod(from_service_account_info),
    )
    return loaded


def scan(
    lister: AgentEngineLister,
    config: DiscoverySourceConfigSpec,
    creds: Optional[dict[str, Optional[str]]] = None,
    fields: Optional[dict[str, str]] = None,
) -> list[list[Any]]:
    return [
        list(batch)
        for batch in VertexAgentEngineConnector(lister=lister).scan(
            config,
            24,
            CREDS if creds is None else creds,
            FIELDS if fields is None else fields,
            LOG,
        )
    ]


# --- identity: the no-duplicate rule ------------------------------------------------


def test_external_id_and_service_names_are_the_api_resource_name_verbatim(
    config: DiscoverySourceConfigSpec,
    stub_key_loader: list[dict[str, Any]],
) -> None:
    lister = FakeLister(
        [
            engine(PERSONAL_ASSISTANT, "personal-assistant"),
            engine(IMAGE_SCORING, "image-scoring"),
        ],
    )
    [batch] = scan(lister, config)

    assert [r.external_id for r in batch] == [PERSONAL_ASSISTANT, IMAGE_SCORING]
    assert [r.service_names for r in batch] == [[PERSONAL_ASSISTANT], [IMAGE_SCORING]]
    # The configured project ID must not leak into the identity: the legacy mapping key
    # carries the project number, and only the verbatim string matches it.
    for record in batch:
        assert PROJECT_ID not in record.external_id
        assert PROJECT_NUMBER in record.external_id


def test_a_record_carries_cloud_provenance_with_project_region_and_engine_id(
    config: DiscoverySourceConfigSpec,
    stub_key_loader: list[dict[str, Any]],
) -> None:
    [[record]] = scan(
        FakeLister([engine(PERSONAL_ASSISTANT, "personal-assistant")]), config
    )

    assert record.name == "personal-assistant"
    assert record.last_seen == UPDATED
    assert record.runs_on is RunsOn.GCP
    source = record.creation_source
    assert isinstance(source, CloudAgentCreationSource)
    assert source.vendor == "gcp_vertex"
    assert source.address.instance == PROJECT_ID
    assert source.address.scope == "us-central1"
    assert source.address.resource_id == "1111111111111111111"
    assert source.address.query is None


def test_region_comes_from_the_resource_name_not_the_configured_location(
    config: DiscoverySourceConfigSpec,
    stub_key_loader: list[dict[str, Any]],
) -> None:
    name = f"projects/{PROJECT_NUMBER}/locations/europe-west1/reasoningEngines/42"
    [[record]] = scan(FakeLister([engine(name, "eu-agent")]), config)
    assert record.creation_source.address.scope == "europe-west1"


def test_output_satisfies_the_discovery_output_contract(
    config: DiscoverySourceConfigSpec,
    stub_key_loader: list[dict[str, Any]],
) -> None:
    [batch] = scan(
        FakeLister([engine(PERSONAL_ASSISTANT, "personal-assistant")]), config
    )
    check_batch(batch, "Source config 'vertex' (gcp_vertex)")


# --- fields the API may leave out -------------------------------------------------


def test_display_name_falls_back_to_the_engine_id(
    config: DiscoverySourceConfigSpec,
    stub_key_loader: list[dict[str, Any]],
) -> None:
    [[record]] = scan(
        FakeLister([engine(PERSONAL_ASSISTANT, display_name=None)]), config
    )
    assert record.name == "1111111111111111111"


def test_last_seen_falls_back_to_create_time(
    config: DiscoverySourceConfigSpec,
    stub_key_loader: list[dict[str, Any]],
) -> None:
    [[record]] = scan(
        FakeLister([engine(PERSONAL_ASSISTANT, "a", update_time=None)]),
        config,
    )
    assert record.last_seen == CREATED


def test_an_engine_with_no_timestamps_is_skipped_not_dated_to_the_scan(
    config: DiscoverySourceConfigSpec,
    stub_key_loader: list[dict[str, Any]],
    caplog: pytest.LogCaptureFixture,
) -> None:
    lister = FakeLister(
        [
            engine(PERSONAL_ASSISTANT, "a", update_time=None, create_time=None),
            engine(IMAGE_SCORING, "b"),
        ],
    )
    with caplog.at_level(logging.WARNING):
        [batch] = scan(lister, config)
    assert [r.external_id for r in batch] == [IMAGE_SCORING]
    assert "neither an update nor a create time" in caplog.text


@pytest.mark.parametrize(
    "name",
    [
        "",
        "reasoningEngines/1",
        f"projects/{PROJECT_NUMBER}/locations/us-central1/agents/1",
        f"projects/{PROJECT_NUMBER}/locations//reasoningEngines/1",
        f"projects/{PROJECT_NUMBER}/locations/us-central1/reasoningEngines/1/extra",
    ],
)
def test_an_unaddressable_resource_name_is_skipped(
    name: str,
    config: DiscoverySourceConfigSpec,
    stub_key_loader: list[dict[str, Any]],
) -> None:
    assert scan(FakeLister([engine(name, "x")]), config) == []


def test_parse_resource_name() -> None:
    assert parse_resource_name(PERSONAL_ASSISTANT) == (
        PROJECT_NUMBER,
        "us-central1",
        "1111111111111111111",
    )


def test_records_are_batched(
    config: DiscoverySourceConfigSpec,
    stub_key_loader: list[dict[str, Any]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(vertex, "BATCH_SIZE", 2)
    names = [
        f"projects/{PROJECT_NUMBER}/locations/us-central1/reasoningEngines/{i}"
        for i in range(5)
    ]
    batches = scan(FakeLister([engine(n, n) for n in names]), config)
    assert [len(b) for b in batches] == [2, 2, 1]


def test_an_empty_project_yields_nothing(
    config: DiscoverySourceConfigSpec,
    stub_key_loader: list[dict[str, Any]],
) -> None:
    assert scan(FakeLister([]), config) == []


# --- settings ----------------------------------------------------------------------


def test_project_and_location_reach_the_lister(
    config: DiscoverySourceConfigSpec,
    stub_key_loader: list[dict[str, Any]],
) -> None:
    lister = FakeLister([])
    scan(lister, config, fields={"project_id": " my-proj ", "location": "asia-east1"})
    [(settings, _)] = lister.calls
    assert settings == VertexSettings(project_id="my-proj", location="asia-east1")


@pytest.mark.parametrize("location", [None, "", "  "])
def test_a_blank_location_defaults_to_us_central1(location: Optional[str]) -> None:
    fields = {"project_id": "p"}
    if location is not None:
        fields["location"] = location
    assert settings_from(fields).location == DEFAULT_LOCATION == "us-central1"


def test_a_missing_project_id_is_named() -> None:
    with pytest.raises(ValueError, match="project_id"):
        settings_from({"location": "us-central1"})


# --- credentials -------------------------------------------------------------------


def test_a_service_account_key_is_loaded_with_the_cloud_platform_scope(
    config: DiscoverySourceConfigSpec,
    stub_key_loader: list[dict[str, Any]],
) -> None:
    lister = FakeLister([])
    scan(lister, config)
    [loaded] = stub_key_loader
    assert loaded["info"] == FAKE_KEY
    assert loaded["scopes"] == ["https://www.googleapis.com/auth/cloud-platform"]
    [(_, credentials)] = lister.calls
    assert credentials is not None


def test_a_keyless_source_fails_unless_the_engine_opts_in_to_adc(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv(ALLOW_ADC_ENV_VAR, raising=False)
    with pytest.raises(ValueError, match="service_account_key") as exc:
        credentials_from({}, LOG)
    assert ALLOW_ADC_ENV_VAR in str(exc.value)

    monkeypatch.setenv(ALLOW_ADC_ENV_VAR, "false")
    with pytest.raises(ValueError):
        credentials_from({"service_account_key": ""}, LOG)


def test_a_keyless_source_uses_adc_when_the_engine_opts_in(
    config: DiscoverySourceConfigSpec,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(ALLOW_ADC_ENV_VAR, "true")
    lister = FakeLister([engine(PERSONAL_ASSISTANT, "personal-assistant")])
    [[record]] = scan(lister, config, creds={"service_account_key": None})
    [(_, credentials)] = lister.calls
    assert credentials is None  # None tells the SDK to use ADC
    assert record.external_id == PERSONAL_ASSISTANT


def test_a_key_is_used_even_when_adc_is_allowed(
    monkeypatch: pytest.MonkeyPatch,
    stub_key_loader: list[dict[str, Any]],
) -> None:
    monkeypatch.setenv(ALLOW_ADC_ENV_VAR, "true")
    assert credentials_from(CREDS, LOG) is not None
    assert len(stub_key_loader) == 1


def test_a_key_that_is_not_json_is_reported_without_its_content() -> None:
    secret = '{"type": "service_account", "private_key": "SUPER-SECRET"'
    with pytest.raises(ValueError, match="not valid JSON") as exc:
        credentials_from({"service_account_key": secret}, LOG)
    assert "SUPER-SECRET" not in str(exc.value)
    assert exc.value.__cause__ is None


@pytest.mark.parametrize(
    "key",
    [
        json.dumps({"type": "authorized_user", "refresh_token": "x"}),
        json.dumps({"type": "external_account", "credential_source": {"file": "/x"}}),
        json.dumps(["not", "an", "object"]),
    ],
)
def test_only_service_account_keys_are_accepted(key: str) -> None:
    """External-account configs can name an executable or a file on the engine's disk,
    which is not something a source's author should be able to point the engine at."""
    with pytest.raises(ValueError, match="not a service account key"):
        credentials_from({"service_account_key": key}, LOG)


def test_the_scan_never_logs_key_material(
    config: DiscoverySourceConfigSpec,
    stub_key_loader: list[dict[str, Any]],
    caplog: pytest.LogCaptureFixture,
) -> None:
    with caplog.at_level(logging.DEBUG):
        scan(FakeLister([engine(PERSONAL_ASSISTANT, "personal-assistant")]), config)
    assert "NOT-A-REAL-KEY" not in caplog.text
    assert "abc123" not in caplog.text
    assert PROJECT_ID in caplog.text  # the project is not a secret, and names the scan


# --- failures: what Google answered -------------------------------------------------


def google_error(code: int, status: str) -> APIError:
    """An error shaped like the SDK raises it: the status on `.code`, not `.status_code`."""
    body = {
        "error": {
            "code": code,
            "message": f"Permission denied on resource project {PROJECT_ID}.",
            "status": status,
        },
    }
    error: APIError = (ClientError if code < 500 else ServerError)(code, body, None)
    return error


class FailingLister:
    """Lists `engines`, then raises -- the way a page Google refuses part-way fails."""

    def __init__(self, error: BaseException, engines: Iterable[Any] = ()) -> None:
        self.error = error
        self.engines = list(engines)

    def __call__(
        self,
        settings: VertexSettings,
        credentials: Optional[Credentials],
    ) -> Iterator[Any]:
        yield from self.engines
        raise self.error


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


@pytest.mark.parametrize(
    ("code", "status", "expected"),
    [
        (401, "UNAUTHENTICATED", DiscoveryErrorCode.AUTHENTICATION_FAILED),
        (403, "PERMISSION_DENIED", DiscoveryErrorCode.PERMISSION_DENIED),
        (404, "NOT_FOUND", DiscoveryErrorCode.PROVIDER_ERROR),
        (503, "UNAVAILABLE", DiscoveryErrorCode.PROVIDER_ERROR),
    ],
)
def test_a_google_api_error_is_classified_by_the_status_it_carries(
    code: int,
    status: str,
    expected: DiscoveryErrorCode,
    config: DiscoverySourceConfigSpec,
    stub_key_loader: list[dict[str, Any]],
) -> None:
    error = google_error(code, status)
    raised_type = type(error)
    message = str(error)

    with pytest.raises(raised_type) as exc:
        scan(FailingLister(error), config)

    # The SDK's own exception, re-raised: same object, same type, same message. Only
    # the attribute `failure_code` reads has been added.
    assert exc.value is error
    assert type(exc.value) is raised_type
    assert str(exc.value) == message
    assert getattr(exc.value, "status_code") == code
    assert failure_code(exc.value) is expected


def test_a_lister_that_fails_on_the_call_is_classified_too(
    config: DiscoverySourceConfigSpec,
    stub_key_loader: list[dict[str, Any]],
) -> None:
    error = google_error(403, "PERMISSION_DENIED")

    def refuse(settings: VertexSettings, credentials: Optional[Credentials]) -> Any:
        raise error

    with pytest.raises(ClientError) as exc:
        scan(refuse, config)
    assert failure_code(exc.value) is DiscoveryErrorCode.PERMISSION_DENIED


def test_a_denied_project_reaches_the_run_as_permission_denied(
    config: DiscoverySourceConfigSpec,
    stub_key_loader: list[dict[str, Any]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """End to end through the scan loop, which is what writes the code to the run.

    The engine listed before the refusal is still published, and the exception
    `run_source_scan` re-raises is still the SDK's ClientError.
    """
    monkeypatch.setattr(vertex, "BATCH_SIZE", 1)
    outcome = DiscoveryScanOutcome(
        discovery_source_config_id=None,
        discovery_source_config_name="vertex",
        discovery_source_id=None,
        vendor=VENDOR,
        job_id="job",
        scan_id=None,
        lookback_hours=24,
    )
    sink = AcceptingSink()
    lister = FailingLister(
        google_error(403, "PERMISSION_DENIED"),
        [engine(PERSONAL_ASSISTANT, "personal-assistant")],
    )

    with pytest.raises(ClientError):
        run_source_scan(
            config=config,
            lookback_hours=24,
            workspace_id="workspace",
            data_plane_id="data-plane",
            outcome=outcome,
            connector=VertexAgentEngineConnector(lister=lister),
            sink=sink,
            logger=LOG,
            credentials=CREDS,
            source_fields=FIELDS,
        )

    assert outcome.error_code is DiscoveryErrorCode.PERMISSION_DENIED
    assert outcome.error is not None and outcome.error.startswith("ClientError: 403")
    assert sink.published == [PERSONAL_ASSISTANT]
    assert outcome.records_published == 1


def test_a_key_google_refuses_is_an_authentication_failure(
    config: DiscoverySourceConfigSpec,
    stub_key_loader: list[dict[str, Any]],
) -> None:
    """A revoked key never reaches Vertex: google-auth cannot mint a token, and the
    token endpoint's answer is a 400, which only the connector knows to read as 401."""
    error = RefreshError(
        "invalid_grant: Invalid JWT Signature.",
        {"error": "invalid_grant", "error_description": "Invalid JWT Signature."},
        retryable=False,
    )
    with pytest.raises(RefreshError) as exc:
        scan(FailingLister(error), config)
    assert exc.value is error
    assert failure_code(exc.value) is DiscoveryErrorCode.AUTHENTICATION_FAILED


def test_a_token_endpoint_outage_is_not_blamed_on_the_key(
    config: DiscoverySourceConfigSpec,
    stub_key_loader: list[dict[str, Any]],
) -> None:
    error = RefreshError(
        "temporarily_unavailable",
        {"error": "temporarily_unavailable"},
        retryable=True,
    )
    with pytest.raises(RefreshError) as exc:
        scan(FailingLister(error), config)
    assert not hasattr(exc.value, "status_code")
    assert failure_code(exc.value) is DiscoveryErrorCode.PROVIDER_ERROR


def test_an_unreachable_metadata_server_is_not_blamed_on_the_key(
    config: DiscoverySourceConfigSpec,
    stub_key_loader: list[dict[str, Any]],
) -> None:
    """google-auth wraps a metadata-server transport failure in a RefreshError it does
    not mark retryable; the cause, not the flag, says it is the network's fault."""
    cause = TransportError("Failed to retrieve http://metadata.google.internal/...")
    try:
        raise RefreshError(cause) from cause
    except RefreshError as raised:
        error = raised
    assert not error.retryable
    with pytest.raises(RefreshError) as exc:
        scan(FailingLister(error), config)
    assert exc.value is error
    assert exc.value.__cause__ is cause
    assert not hasattr(exc.value, "status_code")
    assert failure_code(exc.value) is DiscoveryErrorCode.PROVIDER_ERROR


# --- registration -------------------------------------------------------------------


def test_the_connector_is_registered() -> None:
    assert source_connectors()["gcp_vertex"] is VertexAgentEngineConnector
    connector = source_connectors()["gcp_vertex"]()
    assert isinstance(connector, VertexAgentEngineConnector)
    assert callable(getattr(connector, "scan", None))
