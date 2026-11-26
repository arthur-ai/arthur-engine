"""The Kong connector, over a mocked wire.

The real client runs over `responses`. The bodies follow Kong's published Admin API
specification for Gateway Enterprise 3.16 and its `ai-mcp-proxy` plugin schema, not a
live capture: a list answers `data` / `next` / `offset`; a plugin has `id`, `name`,
`instance_name`, `enabled`, `route.id`, `created_at` / `updated_at` as Unix seconds and
`config`, whose `mode` is one of `passthrough-listener`, `conversion-listener`,
`conversion-only` and `listener`, with `tools` (each a `name`, `description`, `headers`
and more) and `server`. Ids are fakes of the same shape.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Optional

import pytest
import requests
import responses
from arthur_client.api_bindings import DiscoverySourceConfigSpec

from discovery import source_connectors, standalone_connectors
from discovery.network.kong.client import KongClient, KongError
from discovery.network.kong.connector import VENDOR, KongConnector, settings_from
from job_executors.discovery_output_contract import check_batch
from job_executors.discovery_scan import (
    AcceptsStopCheck,
    DiscoveryConfigurationError,
    DiscoveryErrorCode,
    McpServerDetection,
    McpServerRecord,
    failure_code,
)

LOG = logging.getLogger("test.kong")
BASE = "https://kong-admin.example.com:8444"
INSTANCE = "kong-admin.example.com:8444"
TOKEN = "kong-admin-token-secret"
CREDS = {"admin_token": TOKEN}
FIELDS = {"base_url": BASE}
UPDATED = 1792746000  # 2026-10-24T05:00:00Z
HEADER_SECRET = "Bearer upstream-header-secret"
REDIS_SECRET = "redis-password-secret"
PLUGIN_ID = "5a1c8d3e-0000-4000-8000-000000000001"
ROUTE_ID = "9b2d7f4a-0000-4000-8000-000000000002"


def plugin(
    plugin_id: str = PLUGIN_ID,
    mode: Optional[str] = "conversion-listener",
    name: str = "ai-mcp-proxy",
    tools: Optional[list[Any]] = None,
    **over: Any,
) -> dict[str, Any]:
    body: dict[str, Any] = {
        "id": plugin_id,
        "name": name,
        "instance_name": None,
        "enabled": True,
        "route": {"id": ROUTE_ID},
        "service": None,
        "created_at": UPDATED - 86400,
        "updated_at": UPDATED,
        "config": {
            "mode": mode,
            "tools": tools,
            "server": {
                "tag": "crm",
                "session": {"redis": {"password": REDIS_SECRET}},
            },
        },
    }
    body.update(over)
    return body


def tool(name: Optional[str]) -> dict[str, Any]:
    return {
        "name": name,
        "description": "calls upstream",
        "headers": {"Authorization": [HEADER_SECRET]},
    }


def listing(data: list[Any], offset: Optional[str] = None) -> dict[str, Any]:
    return {"data": data, "next": None, "offset": offset}


def kong(
    rsps: responses.RequestsMock,
    path: str,
    body: Any = None,
    status: int = 200,
) -> None:
    rsps.add(
        responses.GET,
        f"{BASE}{path}",
        json=listing([]) if body is None else body,
        status=status,
    )


def one_workspace(rsps: responses.RequestsMock, plugins: list[Any]) -> None:
    kong(rsps, "/workspaces", listing([{"id": "w1", "name": "default"}]))
    kong(rsps, "/default/plugins", listing(plugins))


def connector() -> KongConnector:
    return KongConnector(
        client_factory=lambda settings, log: KongClient(
            settings,
            logger=log,
            session=requests.Session(),
            sleep=lambda _: None,
        ),
    )


def scan(
    conn: Optional[KongConnector] = None,
    fields: Optional[dict[str, str]] = None,
    creds: Optional[dict[str, Optional[str]]] = None,
) -> list[Any]:
    batches = (conn or connector()).scan(
        DiscoverySourceConfigSpec.model_construct(name="kong", query=""),
        24,
        CREDS if creds is None else creds,
        FIELDS if fields is None else fields,
        LOG,
    )
    return [record for batch in batches for record in batch]


# --- registration -----------------------------------------------------------------


def test_it_is_a_standalone_only_connector_that_accepts_a_stop_check() -> None:
    assert standalone_connectors()[VENDOR] is KongConnector
    assert VENDOR not in source_connectors()
    assert isinstance(KongConnector(), AcceptsStopCheck)
    assert KongConnector.SENSITIVE_FIELDS == {"admin_token"}


# --- the record -------------------------------------------------------------------


@responses.activate
def test_a_conversion_listener_is_a_server_named_by_its_route_with_its_tools() -> None:
    one_workspace(
        responses.mock,
        [plugin(tools=[tool("get_order"), tool("cancel_order"), tool(None), "junk"])],
    )
    kong(responses.mock, f"/default/routes/{ROUTE_ID}", {"name": "orders-mcp"})

    [record] = scan()

    assert isinstance(record, McpServerRecord)
    assert record.external_id == f"kong:{INSTANCE}:default:mcp_server:{PLUGIN_ID}"
    assert record.name == "orders-mcp"
    assert record.last_seen == datetime.fromtimestamp(UPDATED, tz=timezone.utc)
    assert [t.name for t in record.tools] == ["cancel_order", "get_order"]
    assert record.detection is McpServerDetection.REGISTERED
    assert record.used_by is None
    check_batch([record], "Source config 'kong' (kong)")


@responses.activate
def test_an_instance_name_names_the_server_and_the_route_is_not_asked_for() -> None:
    one_workspace(
        responses.mock,
        [plugin(mode="passthrough-listener", instance_name="github-mcp")],
    )
    [record] = scan()
    assert record.name == "github-mcp"
    assert record.tools is None
    assert len(responses.calls) == 2


@responses.activate
@pytest.mark.parametrize("status", [403, 404])
def test_a_route_that_cannot_be_read_leaves_the_server_named_by_its_id(
    status: int,
) -> None:
    one_workspace(responses.mock, [plugin(mode="listener")])
    kong(responses.mock, f"/default/routes/{ROUTE_ID}", {}, status)
    [record] = scan()
    assert record.name == PLUGIN_ID


@responses.activate
def test_only_enabled_listening_mcp_plugins_are_servers(
    caplog: pytest.LogCaptureFixture,
) -> None:
    plugins = [
        plugin("p-rate", name="rate-limiting"),
        plugin("p-oauth", name="ai-mcp-oauth2"),
        plugin("p-tools", mode="conversion-only"),
        plugin("p-off", enabled=False),
        plugin("p-new", mode="some-future-mode"),
        plugin("p-undated", created_at=None, updated_at=None),
        plugin("p-kept", instance_name="kept"),
    ]
    one_workspace(responses.mock, plugins)
    with caplog.at_level(logging.INFO, logger=LOG.name):
        [record] = scan()
    assert record.name == "kept"
    assert "found 1 MCP server(s) in 1 workspace(s); 1 tools-only plugin(s) and 1" in (
        caplog.text
    )
    assert "1 ai-mcp-proxy plugin(s) in a mode this scan does not know" in caplog.text
    assert "1 MCP server(s) not reported, because Kong gave no time" in caplog.text


@responses.activate
def test_a_server_never_updated_is_dated_by_its_creation() -> None:
    one_workspace(responses.mock, [plugin(instance_name="x", updated_at=None)])
    [record] = scan()
    assert record.last_seen == datetime.fromtimestamp(UPDATED - 86400, tz=timezone.utc)


@responses.activate
def test_nothing_else_in_a_plugins_config_is_reported_or_logged(
    caplog: pytest.LogCaptureFixture,
) -> None:
    one_workspace(
        responses.mock, [plugin(tools=[tool("get_order")], instance_name="x")]
    )
    with caplog.at_level(logging.DEBUG):
        [record] = scan()
    for secret in (HEADER_SECRET, REDIS_SECRET, TOKEN):
        assert secret not in record.model_dump_json()
        assert secret not in caplog.text


# --- workspaces and paging --------------------------------------------------------


@responses.activate
def test_every_workspace_is_read_and_is_in_the_external_id() -> None:
    kong(
        responses.mock,
        "/workspaces",
        listing([{"name": "default"}, {"name": "team a"}]),
    )
    kong(responses.mock, "/default/plugins", listing([plugin(instance_name="one")]))
    kong(responses.mock, "/team%20a/plugins", listing([plugin(instance_name="two")]))

    records = scan()

    assert [r.external_id.split(":")[3] for r in records] == ["default", "team a"]
    assert len({r.external_id for r in records}) == 2


@responses.activate
def test_a_kong_without_workspaces_is_read_as_one() -> None:
    kong(responses.mock, "/workspaces", {"message": "Not found"}, 404)
    kong(responses.mock, "/plugins", listing([plugin(instance_name="one")]))
    [record] = scan()
    assert record.external_id == f"kong:{INSTANCE}:default:mcp_server:{PLUGIN_ID}"


@responses.activate
def test_every_page_is_read_and_a_repeated_offset_ends_the_walk() -> None:
    kong(responses.mock, "/workspaces", listing([{"name": "default"}]))
    url = f"{BASE}/default/plugins"
    responses.add(
        responses.GET,
        url,
        json=listing([plugin("p1", instance_name="a")], "o2"),
        match=[responses.matchers.query_param_matcher({"size": "1000"})],
    )
    responses.add(
        responses.GET,
        url,
        json=listing([plugin("p2", instance_name="b")], "o2"),
        match=[
            responses.matchers.query_param_matcher({"size": "1000", "offset": "o2"}),
        ],
    )
    assert [r.name for r in scan()] == ["a", "b"]
    assert len(responses.calls) == 3


@responses.activate
def test_every_call_sends_the_token_as_kongs_header_and_is_bounded() -> None:
    one_workspace(responses.mock, [plugin()])
    kong(responses.mock, f"/default/routes/{ROUTE_ID}", {"name": "orders-mcp"})
    scan()
    assert len(responses.calls) == 3
    for call in responses.calls:
        assert call.request.method == "GET"
        assert call.request.headers["Kong-Admin-Token"] == TOKEN
        assert "Authorization" not in call.request.headers
        assert call.request.req_kwargs["timeout"] == (10.0, 60.0)


@responses.activate
def test_a_redirect_is_never_followed() -> None:
    responses.add(
        responses.GET,
        f"{BASE}/workspaces",
        status=302,
        headers={"Location": "https://evil.example/"},
    )
    with pytest.raises(KongError) as raised:
        scan()
    assert raised.value.status_code == 302
    assert len(responses.calls) == 1


@responses.activate
def test_passing_failures_are_retried() -> None:
    url = f"{BASE}/workspaces"
    responses.add(responses.GET, url, status=503)
    responses.add(responses.GET, url, body=requests.ConnectionError("reset"))
    responses.add(responses.GET, url, json=listing([]))
    assert scan() == []
    assert len(responses.calls) == 3


# --- refusals ---------------------------------------------------------------------


@responses.activate
def test_a_refused_workspace_is_a_warning_and_the_rest_is_read(
    caplog: pytest.LogCaptureFixture,
) -> None:
    kong(responses.mock, "/workspaces", listing([{"name": "default"}, {"name": "b"}]))
    kong(responses.mock, "/default/plugins", {"message": f"token {TOKEN} denied"}, 403)
    kong(responses.mock, "/b/plugins", listing([plugin(instance_name="two")]))
    with caplog.at_level(logging.WARNING, logger=LOG.name):
        [record] = scan()
    assert record.name == "two"
    assert "Kong workspace default not read" in caplog.text
    assert TOKEN not in caplog.text


@responses.activate
def test_every_workspace_refused_fails_the_scan_as_permission_denied() -> None:
    kong(responses.mock, "/workspaces", listing([{"name": "default"}]))
    kong(responses.mock, "/default/plugins", {}, 403)
    with pytest.raises(KongError) as raised:
        scan()
    assert failure_code(raised.value) is DiscoveryErrorCode.PERMISSION_DENIED


@responses.activate
def test_a_rejected_token_is_an_authentication_failure_without_the_token() -> None:
    kong(responses.mock, "/workspaces", {"message": f"Invalid token {TOKEN}"}, 401)
    with pytest.raises(KongError) as raised:
        scan()
    assert failure_code(raised.value) is DiscoveryErrorCode.AUTHENTICATION_FAILED
    assert TOKEN not in str(raised.value)


@responses.activate
def test_an_answer_that_is_not_the_admin_apis_is_the_vendors_error() -> None:
    responses.add(responses.GET, f"{BASE}/workspaces", body="<html>Kong Manager</html>")
    with pytest.raises(KongError) as raised:
        scan()
    assert failure_code(raised.value) is DiscoveryErrorCode.PROVIDER_ERROR


@responses.activate
def test_a_stop_ends_the_scan_between_workspaces() -> None:
    kong(responses.mock, "/workspaces", listing([{"name": "default"}, {"name": "b"}]))
    kong(responses.mock, "/default/plugins", listing([plugin(instance_name="one")]))
    conn = connector()
    asked = iter([False, False, False])
    conn.stop_when(lambda: next(asked, True))
    [record] = scan(conn)
    assert record.name == "one"
    assert len(responses.calls) == 2


# --- settings ---------------------------------------------------------------------


@pytest.mark.parametrize(
    "fields, creds, said",
    [
        ({}, CREDS, "missing required field"),
        (FIELDS, {}, "missing required field"),
        ({"base_url": "http://kong-admin.example.com:8001"}, CREDS, "must be https"),
        ({"base_url": "https://user:pw@kong-admin.example.com"}, CREDS, "base_url"),
    ],
)
def test_bad_configuration_is_refused_before_anything_is_sent(
    fields: dict[str, str],
    creds: dict[str, Optional[str]],
    said: str,
) -> None:
    with pytest.raises(DiscoveryConfigurationError, match=said):
        settings_from(creds, fields)


def test_the_settings_never_print_the_token() -> None:
    assert TOKEN not in repr(settings_from(CREDS, FIELDS))
