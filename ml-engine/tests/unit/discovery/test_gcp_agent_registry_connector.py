"""The Agent Registry connector, over a mocked wire.

The real client runs over `responses`, so the URLs, the paging and the error handling
are what the client sends and reads. The bodies follow Google's own discovery document
for `agentregistry` v1 (revision 20261114), not a live capture: `locations` answers
`locations` / `nextPageToken`, each with a `locationId`; `mcpServers` answers
`mcpServers` / `nextPageToken`, each with `name`, `mcpServerId`, `displayName`,
`interfaces` (`url`, `protocolBinding`), `tools` (`name`, `description`), `attributes`,
`createTime` and `updateTime`. Ids are fakes of the same shape.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Optional, Sequence

import pytest
import requests
import responses
from arthur_client.api_bindings import DiscoverySourceConfigSpec
from google.auth.exceptions import RefreshError

from discovery import source_connectors, standalone_connectors
from discovery.cloud.gcp_agent_registry.client import (
    AGENT_REGISTRY_API,
    CLOUD_PLATFORM_READONLY_SCOPE,
    AgentRegistryError,
)
from discovery.cloud.gcp_agent_registry.connector import (
    ALLOW_ADC_ENV_VAR,
    VENDOR,
    GcpAgentRegistryConnector,
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
PROJECT = "acme-agents-prod"
FIELDS = {"project_id": PROJECT}
ROOT = f"{AGENT_REGISTRY_API}/projects/{PROJECT}/locations"
ADDRESS_SECRET = "https://mcp.internal.example/mcp?key=address-secret-value"


@pytest.fixture(autouse=True)
def engine_identity(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(ALLOW_ADC_ENV_VAR, "true")


def server(
    server_id: str,
    location: str = "global",
    updated: Optional[str] = "2026-10-20T09:00:00.123456789Z",
    **over: Any,
) -> dict[str, Any]:
    body: dict[str, Any] = {
        "name": f"projects/{PROJECT}/locations/{location}/mcpServers/{server_id}",
        "mcpServerId": server_id,
        "displayName": f"{server_id} server",
        "description": "",
        "interfaces": [{"url": ADDRESS_SECRET, "protocolBinding": "JSONRPC"}],
        "attributes": {"agentregistry.googleapis.com/system/RuntimeIdentity": {}},
        "createTime": "2026-10-01T09:00:00Z",
    }
    if updated is not None:
        body["updateTime"] = updated
    body.update(over)
    return body


def locations(rsps: responses.RequestsMock, *ids: str) -> None:
    rsps.add(responses.GET, ROOT, json={"locations": [{"locationId": i} for i in ids]})


def servers(
    rsps: responses.RequestsMock,
    location: str,
    body: Any = None,
    status: int = 200,
) -> None:
    rsps.add(
        responses.GET,
        f"{ROOT}/{location}/mcpServers",
        json={} if body is None else body,
        status=status,
    )


def connector(
    scopes: Optional[list[Sequence[str]]] = None,
) -> GcpAgentRegistryConnector:
    def session_for(creds: Any, asked: Sequence[str]) -> requests.Session:
        if scopes is not None:
            scopes.append(asked)
        return requests.Session()

    return GcpAgentRegistryConnector(session_for=session_for, sleep=lambda _: None)


def scan(
    fields: Optional[dict[str, str]] = None,
    conn: Optional[GcpAgentRegistryConnector] = None,
    creds: Optional[dict[str, Optional[str]]] = None,
) -> list[Any]:
    batches = (conn or connector()).scan(
        DiscoverySourceConfigSpec.model_construct(name="registry", query=""),
        24,
        creds or {},
        fields or FIELDS,
        LOG,
    )
    return [record for batch in batches for record in batch]


# --- registration -----------------------------------------------------------------


def test_it_is_a_standalone_only_connector_that_accepts_a_stop_check() -> None:
    assert standalone_connectors()[VENDOR] is GcpAgentRegistryConnector
    assert VENDOR not in source_connectors()
    assert isinstance(GcpAgentRegistryConnector(), AcceptsStopCheck)
    assert GcpAgentRegistryConnector.SENSITIVE_FIELDS == {"service_account_key"}


# --- the record -------------------------------------------------------------------


@responses.activate
def test_a_registered_server_is_a_record_by_its_resource_name_with_its_tools() -> None:
    locations(responses.mock, "global")
    listed = server(
        "bigquery",
        tools=[
            {"name": "execute_sql", "description": "Run a query"},
            {"name": "list_datasets", "annotations": {"readOnlyHint": True}},
            {"name": " "},
            "junk",
        ],
    )
    servers(responses.mock, "global", {"mcpServers": [listed]})

    [record] = scan()

    assert isinstance(record, McpServerRecord)
    assert record.external_id == (
        f"projects/{PROJECT}/locations/global/mcpServers/bigquery"
    )
    assert record.name == "bigquery server"
    assert record.last_seen == datetime(
        2026, 10, 20, 9, 0, 0, 123456, tzinfo=timezone.utc
    )
    assert [t.name for t in record.tools] == ["execute_sql", "list_datasets"]
    assert record.detection is McpServerDetection.REGISTERED
    assert record.used_by is None and record.runs_on is None
    check_batch([record], "Source config 'registry' (gcp_agent_registry)")


@responses.activate
def test_a_server_is_named_by_its_id_when_it_has_no_display_name_and_dated_by_its_creation() -> (
    None
):
    locations(responses.mock, "global")
    listed = server("maps", updated=None, displayName="")
    servers(responses.mock, "global", {"mcpServers": [listed]})
    [record] = scan()
    assert record.name == "maps"
    assert record.last_seen == datetime(2026, 10, 1, 9, 0, tzinfo=timezone.utc)
    assert record.tools is None


@responses.activate
def test_a_server_without_a_name_or_a_time_is_skipped_and_said(
    caplog: pytest.LogCaptureFixture,
) -> None:
    locations(responses.mock, "global")
    listed = [
        server("undated", updated=None, createTime=None),
        server("misnamed", name="mcpServers/misnamed"),
        server("kept"),
    ]
    servers(responses.mock, "global", {"mcpServers": listed})
    with caplog.at_level(logging.INFO):
        [record] = scan()
    assert record.name == "kept server"
    assert "neither an update nor a create time" in caplog.text
    assert "unrecognised resource name" in caplog.text
    assert "found 1 MCP server(s) in 1 location(s) of acme-agents-prod; 2 skipped" in (
        caplog.text
    )


@responses.activate
def test_a_servers_address_is_never_reported_or_logged(
    caplog: pytest.LogCaptureFixture,
) -> None:
    locations(responses.mock, "global")
    servers(responses.mock, "global", {"mcpServers": [server("bigquery")]})
    with caplog.at_level(logging.DEBUG):
        [record] = scan()
    assert "address-secret-value" not in record.model_dump_json()
    assert "address-secret-value" not in caplog.text


# --- locations --------------------------------------------------------------------


@responses.activate
def test_every_listed_location_is_read_and_global_always_is() -> None:
    locations(responses.mock, "us", "europe-west1")
    servers(responses.mock, "global", {"mcpServers": [server("bigquery")]})
    servers(responses.mock, "us", {"mcpServers": [server("crm", "us")]})
    servers(responses.mock, "europe-west1")

    assert sorted(r.name for r in scan()) == ["bigquery server", "crm server"]


@responses.activate
def test_named_locations_are_read_with_global_and_the_list_is_not_asked_for() -> None:
    servers(responses.mock, "global")
    servers(responses.mock, "us", {"mcpServers": [server("crm", "us")]})

    [record] = scan({**FIELDS, "locations": "us, global"})

    assert record.name == "crm server"
    assert [c.request.url.split("?")[0] for c in responses.calls] == [
        f"{ROOT}/global/mcpServers",
        f"{ROOT}/us/mcpServers",
    ]


@responses.activate
def test_every_page_is_read_and_a_repeated_token_ends_the_walk() -> None:
    url = f"{ROOT}/global/mcpServers"
    responses.add(
        responses.GET,
        url,
        json={"mcpServers": [server("a")], "nextPageToken": "p2"},
        match=[responses.matchers.query_param_matcher({"pageSize": "100"})],
    )
    responses.add(
        responses.GET,
        url,
        json={"mcpServers": [server("b")], "nextPageToken": "p2"},
        match=[
            responses.matchers.query_param_matcher(
                {"pageSize": "100", "pageToken": "p2"},
            ),
        ],
    )
    assert [r.name for r in scan({**FIELDS, "locations": "global"})] == [
        "a server",
        "b server",
    ]
    assert len(responses.calls) == 2


@responses.activate
def test_calls_ask_for_the_read_only_scope_follow_no_redirect_and_are_bounded() -> None:
    responses.add(
        responses.GET,
        f"{ROOT}/global/mcpServers",
        status=302,
        headers={"Location": "https://evil.example/"},
    )
    asked: list[Sequence[str]] = []
    with pytest.raises(AgentRegistryError) as raised:
        scan({**FIELDS, "locations": "global"}, conn=connector(asked))
    assert raised.value.status_code == 302
    assert asked == [[CLOUD_PLATFORM_READONLY_SCOPE]]
    [call] = responses.calls
    assert call.request.method == "GET"
    assert call.request.req_kwargs["timeout"] == (10.0, 60.0)


@responses.activate
def test_passing_failures_are_retried() -> None:
    url = f"{ROOT}/global/mcpServers"
    responses.add(responses.GET, url, status=503)
    responses.add(responses.GET, url, body=requests.ConnectionError("reset"))
    responses.add(responses.GET, url, json={})
    assert scan({**FIELDS, "locations": "global"}) == []
    assert len(responses.calls) == 3


# --- refusals ---------------------------------------------------------------------


@responses.activate
@pytest.mark.parametrize("status", [403, 404])
def test_a_refused_location_is_a_warning_and_the_rest_is_read(
    status: int,
    caplog: pytest.LogCaptureFixture,
) -> None:
    locations(responses.mock, "us")
    servers(responses.mock, "global", {"mcpServers": [server("bigquery")]})
    servers(
        responses.mock,
        "us",
        {"error": {"status": "PERMISSION_DENIED", "message": "caller x@y lacks z"}},
        status,
    )
    with caplog.at_level(logging.WARNING):
        [record] = scan()
    assert record.name == "bigquery server"
    assert "location us not read" in caplog.text
    assert "(PERMISSION_DENIED)" in caplog.text
    assert "x@y" not in caplog.text


@responses.activate
def test_an_api_that_is_not_enabled_fails_the_scan_and_says_so() -> None:
    disabled = {
        "error": {
            "code": 403,
            "status": "PERMISSION_DENIED",
            "message": "Agent Registry API has not been used in project 1234",
            "details": [{"reason": "SERVICE_DISABLED", "domain": "googleapis.com"}],
        },
    }
    servers(responses.mock, "global", disabled, 403)
    servers(responses.mock, "us", disabled, 403)
    with pytest.raises(AgentRegistryError) as raised:
        scan({**FIELDS, "locations": "us"})
    assert failure_code(raised.value) is DiscoveryErrorCode.PERMISSION_DENIED
    assert "(PERMISSION_DENIED, SERVICE_DISABLED)" in str(raised.value)
    assert "1234" not in str(raised.value)


@responses.activate
def test_locations_the_account_cannot_list_is_permission_denied() -> None:
    responses.add(responses.GET, ROOT, json={}, status=403)
    with pytest.raises(AgentRegistryError) as raised:
        scan()
    assert failure_code(raised.value) is DiscoveryErrorCode.PERMISSION_DENIED


@responses.activate
def test_a_refused_credential_is_an_authentication_failure() -> None:
    responses.add(
        responses.GET,
        f"{ROOT}/global/mcpServers",
        body=RefreshError("invalid_grant: account not found"),
    )
    with pytest.raises(RefreshError) as raised:
        scan({**FIELDS, "locations": "global"})
    assert failure_code(raised.value) is DiscoveryErrorCode.AUTHENTICATION_FAILED


@responses.activate
def test_an_answer_that_is_not_googles_is_the_vendors_error() -> None:
    responses.add(responses.GET, ROOT, body="<html>Sign in</html>", status=200)
    with pytest.raises(AgentRegistryError) as raised:
        scan()
    assert failure_code(raised.value) is DiscoveryErrorCode.PROVIDER_ERROR


@responses.activate
def test_a_stop_ends_the_scan_between_locations() -> None:
    servers(responses.mock, "global", {"mcpServers": [server("bigquery")]})
    servers(responses.mock, "us", {"mcpServers": [server("crm", "us")]})
    conn = connector()
    asked = iter([False, False])
    conn.stop_when(lambda: next(asked, True))
    [record] = scan({**FIELDS, "locations": "us"}, conn=conn)
    assert record.name == "bigquery server"
    assert len(responses.calls) == 1


# --- settings and credentials -----------------------------------------------------


@pytest.mark.parametrize(
    "fields, said",
    [
        ({}, "missing required field 'project_id'"),
        ({"project_id": "My Project"}, "is not a project ID"),
        ({"project_id": PROJECT, "locations": "us,../x"}, "not location names"),
    ],
)
def test_bad_settings_are_configuration_errors(
    fields: dict[str, str],
    said: str,
) -> None:
    with pytest.raises(DiscoveryConfigurationError, match=said):
        settings_from(fields)


def test_a_source_without_a_key_needs_the_engines_opt_in(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv(ALLOW_ADC_ENV_VAR)
    with pytest.raises(DiscoveryConfigurationError) as raised:
        scan()
    assert "Agent Registry source has no 'service_account_key'" in str(raised.value)
    assert ALLOW_ADC_ENV_VAR in str(raised.value)
