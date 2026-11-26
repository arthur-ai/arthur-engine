"""The Azure API Management connector, over a mocked wire.

The real client runs over `responses`, so the URLs, the pinned api-version and the
paging are what the client sends. The bodies follow Microsoft's REST reference for API
Management `2025-09-01-preview` as it documents them, not a live capture: a service list
and an API list each answer `value` / `nextLink`; an MCP server is an API whose
`properties.type` is `mcp`, with `properties.displayName`, `properties.isCurrent`,
`properties.serviceUrl`, `properties.mcpProperties` and `systemData`; its tools are
`.../apis/{api}/tools`. Ids are fakes of the same shape.
"""

import logging
import time
from datetime import datetime, timezone
from typing import Any, Optional

import pytest
import requests
import responses
from arthur_client.api_bindings import DiscoverySourceConfigSpec
from arthur_common.models.agent_governance_schemas import RunsOn
from azure.core.credentials import AccessToken, TokenCredential
from azure.core.exceptions import ClientAuthenticationError
from azure.identity import ClientSecretCredential, DefaultAzureCredential

from discovery import source_connectors, standalone_connectors
from discovery.cloud.azure_api_management import connector as apim
from discovery.cloud.azure_api_management.client import (
    API_VERSION,
    ARM_SCOPE,
    ApiManagementClient,
    ArmError,
)
from discovery.cloud.azure_api_management.connector import (
    ALLOW_DEFAULT_CREDENTIAL_ENV_VAR,
    VENDOR,
    AzureApiManagementConnector,
    settings_from,
)
from job_executors.discovery_output_contract import check_batch
from job_executors.discovery_scan import (
    AcceptsStopCheck,
    DiscoveryConfigurationError,
    DiscoveryErrorCode,
    McpServerDetection,
    McpServerRecord,
    failure_code,
)

LOG = logging.getLogger("discovery-test")
SUB = "11111111-2222-3333-4444-555555555555"
ARM = "https://management.azure.com"
SERVICES = f"{ARM}/subscriptions/{SUB}/providers/Microsoft.ApiManagement/service"
SERVICE_ID = (
    f"/subscriptions/{SUB}/resourceGroups/Platform-RG/providers/"
    f"Microsoft.ApiManagement/service/contoso-apim"
)
OTHER_ID = SERVICE_ID.replace("contoso-apim", "fabrikam-apim")
FIELDS = {"subscription_id": SUB}
MODIFIED = "2026-10-20T09:00:00.1234567Z"
TOKEN = "arm-token-secret-value"
UPSTREAM_SECRET = "https://mcp.internal.example/sse?key=upstream-secret-value"


class FakeCredential(TokenCredential):
    def __init__(self) -> None:
        self.scopes: list[str] = []

    def get_token(self, *scopes: str, **kwargs: Any) -> AccessToken:
        self.scopes.extend(scopes)
        return AccessToken(TOKEN, int(time.time()) + 3600)


def service(resource_id: str = SERVICE_ID) -> dict[str, Any]:
    return {"id": resource_id, "name": resource_id.rsplit("/", 1)[-1]}


def api(
    name: str,
    kind: Optional[str] = "mcp",
    modified: Optional[str] = MODIFIED,
    **properties: Any,
) -> dict[str, Any]:
    body: dict[str, Any] = {
        "id": f"{SERVICE_ID}/apis/{name}",
        "name": name,
        "type": "Microsoft.ApiManagement/service/apis",
        "properties": {
            "displayName": f"{name} display",
            "path": name,
            "isCurrent": True,
            "serviceUrl": UPSTREAM_SECRET,
            **properties,
        },
    }
    if kind is not None:
        body["properties"]["type"] = kind
    if modified is not None:
        body["systemData"] = {
            "createdAt": "2026-10-01T09:00:00Z",
            "lastModifiedAt": modified,
        }
    return body


def tool(name: str) -> dict[str, Any]:
    return {"name": name, "properties": {"displayName": name.title()}}


def page(items: list[Any], next_link: Optional[str] = None) -> dict[str, Any]:
    body: dict[str, Any] = {"value": items}
    if next_link:
        body["nextLink"] = next_link
    return body


def arm(
    rsps: responses.RequestsMock,
    url: str,
    body: Any = None,
    status: int = 200,
) -> None:
    rsps.add(responses.GET, url, json=page([]) if body is None else body, status=status)


def one_service(
    rsps: responses.RequestsMock,
    apis: list[Any],
    tools: Optional[dict[str, list[Any]]] = None,
) -> None:
    arm(rsps, SERVICES, page([service()]))
    arm(rsps, f"{ARM}{SERVICE_ID}/apis", page(apis))
    for name, listed in (tools or {}).items():
        arm(rsps, f"{ARM}{SERVICE_ID}/apis/{name}/tools", page(listed))


def scan(
    fields: Optional[dict[str, str]] = None,
    credential: Optional[TokenCredential] = None,
    connector: Optional[AzureApiManagementConnector] = None,
    monkeypatch: Optional[pytest.MonkeyPatch] = None,
) -> list[Any]:
    used = credential or FakeCredential()
    patch = monkeypatch or pytest.MonkeyPatch()
    patch.setattr(apim, "service_principal_credential", lambda *a, **kw: used)
    try:
        connector = connector or AzureApiManagementConnector(
            client_factory=lambda cred, log, stop: ApiManagementClient(
                cred,
                log,
                should_stop=stop,
                sleep=lambda _: None,
            ),
        )
        batches = connector.scan(
            DiscoverySourceConfigSpec.model_construct(name="apim", query=""),
            24,
            {},
            fields or FIELDS,
            LOG,
        )
        return [record for batch in batches for record in batch]
    finally:
        if monkeypatch is None:
            patch.undo()


# --- registration -----------------------------------------------------------------


def test_it_is_a_standalone_only_connector_that_accepts_a_stop_check() -> None:
    assert standalone_connectors()[VENDOR] is AzureApiManagementConnector
    assert VENDOR not in source_connectors()
    assert isinstance(AzureApiManagementConnector(), AcceptsStopCheck)
    assert AzureApiManagementConnector.SENSITIVE_FIELDS == {"client_secret"}


# --- the record -------------------------------------------------------------------


@responses.activate
def test_an_mcp_api_is_a_registered_server_by_its_lower_cased_resource_id() -> None:
    one_service(responses.mock, [api("Weather-MCP")], {"Weather-MCP": []})

    [record] = scan()

    assert isinstance(record, McpServerRecord)
    assert record.external_id == f"{SERVICE_ID}/apis/Weather-MCP".lower()
    assert record.name == "Weather-MCP display"
    assert record.last_seen == datetime(
        2026, 10, 20, 9, 0, 0, 123456, tzinfo=timezone.utc
    )
    assert record.runs_on is RunsOn.AZURE
    assert record.detection is McpServerDetection.REGISTERED
    assert record.tools is None and record.used_by is None
    check_batch([record], "Source config 'apim' (azure_api_management)")


@responses.activate
def test_only_apis_of_type_mcp_are_servers_and_other_revisions_are_skipped(
    caplog: pytest.LogCaptureFixture,
) -> None:
    apis = [
        api("orders", kind="http"),
        api("legacy", kind=None),
        api("weather-mcp"),
        api("weather-mcp;rev=2", isCurrent=False),
    ]
    one_service(responses.mock, apis, {"weather-mcp": []})
    with caplog.at_level(logging.INFO):
        records = scan()
    assert [r.name for r in records] == ["weather-mcp display"]
    assert "1 MCP server(s) among 4 API(s) in 1 service(s); 1 other revision(s)" in (
        caplog.text
    )


@responses.activate
def test_a_servers_tools_are_named_by_their_resource_names() -> None:
    one_service(
        responses.mock,
        [api("weather-mcp")],
        {"weather-mcp": [tool("get-forecast"), tool("get-alerts"), {"name": ""}]},
    )
    [record] = scan()
    assert [t.name for t in record.tools] == ["get-alerts", "get-forecast"]


@responses.activate
@pytest.mark.parametrize("status", [403, 404])
def test_tools_that_cannot_be_read_leave_the_server_without_them(
    status: int,
    caplog: pytest.LogCaptureFixture,
) -> None:
    one_service(responses.mock, [api("weather-mcp")])
    arm(responses.mock, f"{ARM}{SERVICE_ID}/apis/weather-mcp/tools", {}, status)
    with caplog.at_level(logging.WARNING):
        [record] = scan()
    assert record.tools is None
    assert "the tools of 1 MCP server(s) could not be read" in caplog.text


@responses.activate
def test_a_server_never_modified_is_dated_by_its_creation() -> None:
    listed = api("weather-mcp")
    del listed["systemData"]["lastModifiedAt"]
    one_service(responses.mock, [listed], {"weather-mcp": []})
    [record] = scan()
    assert record.last_seen == datetime(2026, 10, 1, 9, 0, tzinfo=timezone.utc)


@responses.activate
def test_a_server_without_a_time_is_skipped_and_said(
    caplog: pytest.LogCaptureFixture,
) -> None:
    one_service(responses.mock, [api("weather-mcp", modified=None)])
    with caplog.at_level(logging.WARNING):
        assert scan() == []
    assert "MCP server with no modification time" in caplog.text


@responses.activate
def test_the_upstream_address_is_never_reported_or_logged(
    caplog: pytest.LogCaptureFixture,
) -> None:
    listed = api(
        "weather-mcp",
        mcpProperties={"endpoints": [{"name": "sse", "uriTemplate": UPSTREAM_SECRET}]},
    )
    one_service(responses.mock, [listed], {"weather-mcp": []})
    with caplog.at_level(logging.DEBUG):
        [record] = scan()
    assert "upstream-secret-value" not in record.model_dump_json()
    assert "upstream-secret-value" not in caplog.text
    assert TOKEN not in caplog.text


# --- what is asked ----------------------------------------------------------------


@responses.activate
def test_every_call_is_a_get_with_the_pinned_version_the_token_and_no_redirects() -> (
    None
):
    one_service(responses.mock, [api("weather-mcp")], {"weather-mcp": []})
    credential = FakeCredential()
    scan(credential=credential)

    assert set(credential.scopes) == {ARM_SCOPE}
    assert len(responses.calls) == 3
    for call in responses.calls:
        assert call.request.method == "GET"
        assert call.request.url.endswith(f"?api-version={API_VERSION}")
        assert call.request.headers["Authorization"] == f"Bearer {TOKEN}"
        assert call.request.req_kwargs["timeout"] == (10.0, 60.0)


@responses.activate
def test_every_page_is_read_and_a_repeated_link_ends_the_walk() -> None:
    apis_url = f"{ARM}{SERVICE_ID}/apis"
    second = f"{apis_url}?api-version={API_VERSION}&%24skip=1"
    arm(responses.mock, SERVICES, page([service()]))
    responses.add(
        responses.GET,
        apis_url,
        json=page([api("a-mcp")], second),
        match=[responses.matchers.query_param_matcher({"api-version": API_VERSION})],
    )
    responses.add(
        responses.GET,
        apis_url,
        json=page([api("b-mcp")], second),
        match=[
            responses.matchers.query_param_matcher(
                {"api-version": API_VERSION, "$skip": "1"},
            ),
        ],
    )
    arm(responses.mock, f"{apis_url}/a-mcp/tools")
    arm(responses.mock, f"{apis_url}/b-mcp/tools")

    assert [r.name for r in scan()] == ["a-mcp display", "b-mcp display"]


@responses.activate
def test_a_next_page_on_another_host_is_never_sent_the_token() -> None:
    arm(responses.mock, SERVICES, page([], "https://evil.example/next"))
    with pytest.raises(ArmError) as raised:
        scan()
    assert "not on management.azure.com" in str(raised.value)
    assert len(responses.calls) == 1


@responses.activate
def test_a_redirect_is_never_followed() -> None:
    responses.add(
        responses.GET,
        SERVICES,
        status=302,
        headers={"Location": "https://evil.example/"},
    )
    with pytest.raises(ArmError) as raised:
        scan()
    assert raised.value.status_code == 302
    assert len(responses.calls) == 1


@responses.activate
def test_a_listed_service_outside_the_subscription_is_never_asked_for(
    caplog: pytest.LogCaptureFixture,
) -> None:
    elsewhere = SERVICE_ID.replace(SUB, "99999999-2222-3333-4444-555555555555")
    arm(responses.mock, SERVICES, page([service(elsewhere), {"id": "../x"}, "junk"]))
    with caplog.at_level(logging.INFO):
        assert scan() == []
    assert len(responses.calls) == 1
    assert "2 unusable item(s) skipped" in caplog.text


@responses.activate
def test_passing_failures_are_retried() -> None:
    responses.add(responses.GET, SERVICES, status=503)
    responses.add(responses.GET, SERVICES, body=requests.ConnectionError("reset"))
    arm(responses.mock, SERVICES, page([]))
    assert scan() == []
    assert len(responses.calls) == 3


# --- refusals ---------------------------------------------------------------------


@responses.activate
def test_a_refused_service_is_a_warning_and_the_rest_is_read(
    caplog: pytest.LogCaptureFixture,
) -> None:
    arm(responses.mock, SERVICES, page([service(), service(OTHER_ID)]))
    arm(
        responses.mock,
        f"{ARM}{SERVICE_ID}/apis",
        {"error": {"code": "AuthorizationFailed", "message": f"client {TOKEN}"}},
        403,
    )
    arm(responses.mock, f"{ARM}{OTHER_ID}/apis", page([api("weather-mcp")]))
    arm(responses.mock, f"{ARM}{OTHER_ID}/apis/weather-mcp/tools")
    with caplog.at_level(logging.WARNING):
        [record] = scan()
    assert record.external_id == f"{OTHER_ID}/apis/weather-mcp".lower()
    assert "service contoso-apim not read" in caplog.text
    assert "(AuthorizationFailed)" in caplog.text
    assert TOKEN not in caplog.text


@responses.activate
def test_every_service_refused_fails_the_scan_as_permission_denied() -> None:
    arm(responses.mock, SERVICES, page([service()]))
    arm(responses.mock, f"{ARM}{SERVICE_ID}/apis", {}, 403)
    with pytest.raises(ArmError) as raised:
        scan()
    assert failure_code(raised.value) is DiscoveryErrorCode.PERMISSION_DENIED


@responses.activate
def test_a_subscription_the_principal_cannot_list_is_permission_denied() -> None:
    arm(responses.mock, SERVICES, {"error": {"code": "AuthorizationFailed"}}, 403)
    with pytest.raises(ArmError) as raised:
        scan()
    assert failure_code(raised.value) is DiscoveryErrorCode.PERMISSION_DENIED


@responses.activate
def test_a_credential_entra_refuses_is_an_authentication_failure() -> None:
    class Refused(FakeCredential):
        def get_token(self, *scopes: str, **kwargs: Any) -> AccessToken:
            raise ClientAuthenticationError("AADSTS7000215: invalid client secret")

    with pytest.raises(ClientAuthenticationError) as raised:
        scan(credential=Refused())
    assert failure_code(raised.value) is DiscoveryErrorCode.AUTHENTICATION_FAILED


@responses.activate
def test_an_answer_that_is_not_resource_managers_is_the_vendors_error() -> None:
    responses.add(responses.GET, SERVICES, body="<html>Sign in</html>", status=200)
    with pytest.raises(ArmError) as raised:
        scan()
    assert failure_code(raised.value) is DiscoveryErrorCode.PROVIDER_ERROR


@responses.activate
def test_a_stop_before_the_first_service_reads_none_of_them() -> None:
    arm(responses.mock, SERVICES, page([service()]))
    stops = iter([False, True])
    connector = AzureApiManagementConnector(
        client_factory=lambda cred, log, stop: ApiManagementClient(
            cred, log, should_stop=stop
        ),
    )
    connector.stop_when(lambda: next(stops, True))
    assert scan(connector=connector) == []
    assert len(responses.calls) == 1


# --- settings and credentials -----------------------------------------------------


@pytest.mark.parametrize(
    "fields, said",
    [
        ({}, "missing required field 'subscription_id'"),
        ({"subscription_id": "my-subscription"}, "not an Azure subscription id"),
        ({"subscription_id": f"{SUB}/../x"}, "not an Azure subscription id"),
    ],
)
def test_bad_settings_are_configuration_errors(
    fields: dict[str, str],
    said: str,
) -> None:
    with pytest.raises(DiscoveryConfigurationError, match=said):
        settings_from(fields)


def test_the_subscription_id_is_lower_cased() -> None:
    assert settings_from({"subscription_id": f" {SUB.upper()} "}).subscription_id == SUB


def run(fields: dict[str, str], creds: dict[str, Optional[str]]) -> list[Any]:
    batches = AzureApiManagementConnector().scan(
        DiscoverySourceConfigSpec.model_construct(name="apim", query=""),
        24,
        creds,
        fields,
        LOG,
    )
    return [record for batch in batches for record in batch]


def test_a_source_without_a_principal_needs_the_engines_opt_in(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv(ALLOW_DEFAULT_CREDENTIAL_ENV_VAR, raising=False)
    with pytest.raises(DiscoveryConfigurationError) as raised:
        run(FIELDS, {})
    assert "Azure API Management source has no service principal" in str(raised.value)
    assert ALLOW_DEFAULT_CREDENTIAL_ENV_VAR in str(raised.value)


def test_a_partial_principal_names_what_is_missing_and_never_the_secret() -> None:
    fields = {**FIELDS, "tenant_id": "contoso.onmicrosoft.com"}
    with pytest.raises(DiscoveryConfigurationError) as raised:
        run(fields, {"client_secret": "s3cret-value"})
    assert "'client_id'" in str(raised.value)
    assert "s3cret-value" not in str(raised.value)


def test_the_principal_or_the_engines_identity_is_what_signs_in(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from discovery.azure_credentials import service_principal_credential

    kwargs = {
        "source": "Azure API Management source",
        "allow_default_env_var": ALLOW_DEFAULT_CREDENTIAL_ENV_VAR,
    }
    principal = service_principal_credential(
        "contoso.onmicrosoft.com",
        "22222222-2222-2222-2222-222222222222",
        {"client_secret": "s3cret-value"},
        **kwargs,
    )
    assert isinstance(principal, ClientSecretCredential)
    monkeypatch.setenv(ALLOW_DEFAULT_CREDENTIAL_ENV_VAR, "true")
    assert isinstance(
        service_principal_credential(None, None, {}, **kwargs),
        DefaultAzureCredential,
    )
