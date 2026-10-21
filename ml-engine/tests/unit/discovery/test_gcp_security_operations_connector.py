"""Google Security Operations connector: the dashboard query call, the contract check
and the records.

A fake session stands in for Google. No live instance was available, so its responses
are shaped on Google's published types for this method, `ExecuteDashboardQueryResponse`
in google-cloud-chronicle 0.6.4 (`google/cloud/chronicle_v1/types/dashboard_query.py`),
as proto3 JSON writes them: camelCase names, 64-bit integers as strings, a `list` of
values for a repeated cell, and fields left out when empty. Error bodies are Google's
standard `{"error": {code, message, status, details}}`.
"""

import json
import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Optional

import pytest
import requests
from arthur_client.api_bindings import DiscoverySourceConfigSpec
from arthur_common.models.agent_governance_schemas import SIEMAgentCreationSource
from google.auth.exceptions import DefaultCredentialsError, RefreshError

from discovery import gcp_credentials, source_connectors
from discovery.retry import MAX_ATTEMPTS
from discovery.siem.gcp_security_operations import client as client_module
from discovery.siem.gcp_security_operations.client import (
    CHRONICLE_READONLY_SCOPE,
    GcpSecurityOperationsClient,
    GcpSecurityOperationsError,
    GcpSecurityOperationsSettings,
    authorized_session,
)
from discovery.siem.gcp_security_operations.connector import (
    ALLOW_ADC_ENV_VAR,
    BATCH_SIZE,
    MAX_LOOKBACK_HOURS,
    VENDOR,
    GcpSecurityOperationsConnector,
    query_text,
    settings_from,
)
from job_executors.discovery_output_contract import OutputContractError, check_batch
from job_executors.discovery_scan import (
    AcceptsStopCheck,
    DiscoveryConfigurationError,
    DiscoveryErrorCode,
    failure_code,
)

LOG = logging.getLogger("test.gcp_security_operations")
NOW = datetime(2026, 10, 21, 12, 0, 0, tzinfo=timezone.utc)

PROJECT_ID = "acme-secops-prod"
INSTANCE_ID = "0c1d2e3f-4a5b-4c6d-8e7f-a0b1c2d3e4f5"
FIELDS = {"project_id": PROJECT_ID, "location": "us", "instance_id": INSTANCE_ID}
PARENT = f"projects/{PROJECT_ID}/locations/us/instances/{INSTANCE_ID}"
URL = f"https://us-chronicle.googleapis.com/v1/{PARENT}/dashboardQueries:execute"

PRIVATE_KEY = (
    "-----BEGIN PRIVATE KEY-----\nNOT-A-REAL-KEY-7f3a9c\n-----END PRIVATE KEY-----\n"
)
FAKE_KEY = {
    "type": "service_account",
    "project_id": PROJECT_ID,
    "private_key_id": "abc123",
    "private_key": PRIVATE_KEY,
    "client_email": "discovery@acme-secops-prod.iam.gserviceaccount.com",
    "client_id": "1234567890",
    "token_uri": "https://oauth2.googleapis.com/token",
}
KEY_JSON = json.dumps(FAKE_KEY)
CREDS: dict[str, Optional[str]] = {"service_account_key": KEY_JSON}


def _docs_samples() -> list[str]:
    """The YARA-L samples of the vendor's section of the standalone docs, so the tests
    run exactly what a customer is told to paste."""
    docs = (Path(__file__).parents[3] / "docs" / "standalone-discovery.md").read_text()
    section = re.search(
        r"#### `gcp_security_operations`.*?(?=\n#### |\n### |\Z)",
        docs,
        re.S,
    )
    assert section is not None
    return re.findall(r"```yara-l\n(.*?)```", section.group(0), re.S)


HOSTS_QUERY, GATEWAY_QUERY = _docs_samples()
QUERY = HOSTS_QUERY.strip()


# -- Google's wire shapes ------------------------------------------------------------


def s(value: str) -> dict[str, Any]:
    return {"value": {"stringVal": value}}


def i64(value: int) -> dict[str, Any]:
    return {"value": {"int64Val": str(value)}}


def ts(value: str) -> dict[str, Any]:
    return {"value": {"timestampVal": value}}


def null() -> dict[str, Any]:
    return {"value": {"nullVal": True}}


def strings(*values: str) -> dict[str, Any]:
    return {"list": {"values": [{"stringVal": v} for v in values]}}


SEEN = 1792497600  # 2026-10-20T12:00:00Z


def host_columns(n: int, prefix: str = "") -> dict[str, list[dict[str, Any]]]:
    hosts = [f"ws-{i:04d}.corp.example" for i in range(n)]
    return {
        f"{prefix}external_id": [s(h) for h in hosts],
        f"{prefix}name": [s(h) for h in hosts],
        f"{prefix}last_seen": [i64(SEEN + i) for i in range(n)],
    }


class FakeResponse:
    def __init__(
        self,
        status: int,
        body: Any = None,
        headers: Optional[dict[str, str]] = None,
    ) -> None:
        self.status_code = status
        self._body = body
        self.headers = headers or {}

    def json(self) -> Any:
        if self._body is None:
            raise ValueError("no body")
        return self._body


def ok(
    columns: Optional[dict[str, list[dict[str, Any]]]] = None,
    errors: Optional[list[dict[str, Any]]] = None,
) -> FakeResponse:
    body: dict[str, Any] = {
        "results": [
            {"column": name, "values": values}
            for name, values in (
                host_columns(3) if columns is None else columns
            ).items()
        ],
        "dataSources": ["UDM"],
        "timeWindow": {
            "startTime": "2026-10-20T12:00:00Z",
            "endTime": "2026-10-21T12:00:00Z",
        },
    }
    if errors:
        body["queryRuntimeErrors"] = errors
    return FakeResponse(200, body, {"Content-Type": "application/json; charset=UTF-8"})


def error(
    status: int,
    canonical: str,
    message: str,
    reason: Optional[str] = None,
) -> FakeResponse:
    details = (
        [
            {
                "@type": "type.googleapis.com/google.rpc.ErrorInfo",
                "reason": reason,
                "domain": "googleapis.com",
            },
        ]
        if reason
        else []
    )
    return FakeResponse(
        status,
        {
            "error": {
                "code": status,
                "message": message,
                "status": canonical,
                "details": details,
            },
        },
        {"Content-Type": "application/json; charset=UTF-8"},
    )


class FakeSession:
    """Answers each post with the next of `responses`, the last one repeating."""

    def __init__(self, *responses: Any) -> None:
        self.responses = list(responses) or [ok()]
        self.calls: list[dict[str, Any]] = []

    def post(self, url: str, **kw: Any) -> FakeResponse:
        self.calls.append({"url": url, **kw})
        response = self.responses[min(len(self.calls), len(self.responses)) - 1]
        if isinstance(response, BaseException):
            raise response
        return response  # type: ignore[no-any-return]


@pytest.fixture(autouse=True)
def stub_key_loader(monkeypatch: pytest.MonkeyPatch) -> list[dict[str, Any]]:
    """Stands in for google-auth's key parser, which would reject the fake PEM."""
    loaded: list[dict[str, Any]] = []

    def from_service_account_info(info: dict[str, Any], scopes: list[str]) -> Any:
        loaded.append({"info": info, "scopes": scopes})
        return SimpleNamespace(service_account_email=info["client_email"])

    monkeypatch.setattr(
        gcp_credentials.service_account.Credentials,
        "from_service_account_info",
        staticmethod(from_service_account_info),
    )
    monkeypatch.delenv(ALLOW_ADC_ENV_VAR, raising=False)
    return loaded


def connector_with(
    session: FakeSession,
    sleeps: Optional[list[float]] = None,
) -> GcpSecurityOperationsConnector:
    def factory(
        settings: GcpSecurityOperationsSettings,
        log: logging.Logger,
    ) -> GcpSecurityOperationsClient:
        return GcpSecurityOperationsClient(
            settings,
            logger=log,
            session=session,  # type: ignore[arg-type]
            sleep=(sleeps if sleeps is not None else []).append,
        )

    return GcpSecurityOperationsConnector(client_factory=factory, clock=lambda: NOW)


def config(
    query: Optional[str] = QUERY,
    language: Optional[str] = "yara_l",
) -> DiscoverySourceConfigSpec:
    return DiscoverySourceConfigSpec.model_construct(
        name="llm hosts",
        query=query,
        query_language=language,
    )


def scan(
    session: FakeSession,
    *,
    lookback_hours: int = 24,
    query: Optional[str] = QUERY,
    fields: Optional[dict[str, str]] = None,
    creds: Optional[dict[str, Optional[str]]] = None,
) -> list[Any]:
    batches = connector_with(session).scan(
        config(query),
        lookback_hours,
        CREDS if creds is None else creds,
        FIELDS if fields is None else fields,
        LOG,
    )
    return [record for batch in batches for record in batch]


# -- registration --------------------------------------------------------------------


def test_the_connector_is_registered() -> None:
    assert source_connectors()[VENDOR] is GcpSecurityOperationsConnector
    assert VENDOR == "gcp_security_operations"


def test_the_connector_declares_exactly_its_secrets() -> None:
    # The same set the Platform catalog marks is_sensitive.
    assert GcpSecurityOperationsConnector.SENSITIVE_FIELDS == frozenset(
        {"service_account_key"},
    )


# -- the request ---------------------------------------------------------------------


def test_the_query_is_sent_untouched_and_the_window_rides_beside_it() -> None:
    session = FakeSession()
    scan(session, lookback_hours=48)
    (call,) = session.calls
    assert call["url"] == URL
    assert call["json"] == {
        "query": {
            "query": QUERY,
            "input": {
                "timeWindow": {
                    "startTime": "2026-10-19T12:00:00Z",
                    "endTime": "2026-10-21T12:00:00Z",
                },
            },
        },
        "clearCache": True,
    }


def test_redirects_are_refused_and_the_timeouts_fit_test_connection() -> None:
    session = FakeSession()
    scan(session)
    call = session.calls[0]
    assert call["allow_redirects"] is False
    connect, read = call["timeout"]
    # Each applies on its own, so together they must fit Test Connection's 120s.
    assert connect + read < 120


@pytest.mark.parametrize(
    "location, host",
    [
        ("us", "us-chronicle.googleapis.com"),
        ("eu", "eu-chronicle.googleapis.com"),
        ("europe-west2", "europe-west2-chronicle.googleapis.com"),
        ("northamerica-northeast2", "northamerica-northeast2-chronicle.googleapis.com"),
        (" US ", "us-chronicle.googleapis.com"),
    ],
)
def test_the_host_is_built_from_the_region(location: str, host: str) -> None:
    session = FakeSession()
    scan(session, fields={**FIELDS, "location": location})
    region = host.split("-chronicle.", 1)[0]
    assert session.calls[0]["url"] == (
        f"https://{host}/v1/projects/{PROJECT_ID}/locations/{region}"
        f"/instances/{INSTANCE_ID}/dashboardQueries:execute"
    )


@pytest.mark.parametrize("lookback_hours", [0, -1, MAX_LOOKBACK_HOURS + 1, 10_000])
def test_a_window_google_will_not_serve_is_sent_as_90_days_and_said_so(
    lookback_hours: int,
    caplog: pytest.LogCaptureFixture,
) -> None:
    session = FakeSession()
    with caplog.at_level(logging.WARNING, logger=LOG.name):
        scan(session, lookback_hours=lookback_hours)
    window = session.calls[0]["json"]["query"]["input"]["timeWindow"]
    assert window == {
        "startTime": "2026-07-23T12:00:00Z",
        "endTime": "2026-10-21T12:00:00Z",
    }
    assert "at most the last 90 days" in caplog.text


def test_a_window_google_serves_is_sent_as_it_is_without_a_warning(
    caplog: pytest.LogCaptureFixture,
) -> None:
    session = FakeSession()
    with caplog.at_level(logging.WARNING, logger=LOG.name):
        scan(session, lookback_hours=MAX_LOOKBACK_HOURS)
    assert session.calls[0]["json"]["query"]["input"]["timeWindow"]["startTime"] == (
        "2026-07-23T12:00:00Z"
    )
    assert "90 days" not in caplog.text


# -- credentials ---------------------------------------------------------------------


def test_a_service_account_key_is_loaded_with_the_chronicle_readonly_scope(
    stub_key_loader: list[dict[str, Any]],
) -> None:
    settings = settings_from(CREDS, FIELDS)
    [loaded] = stub_key_loader
    assert loaded["info"] == FAKE_KEY
    assert loaded["scopes"] == [CHRONICLE_READONLY_SCOPE]
    assert CHRONICLE_READONLY_SCOPE == (
        "https://www.googleapis.com/auth/chronicle.readonly"
    )
    assert settings.credentials is not None


@pytest.mark.parametrize(
    "creds",
    [{}, {"service_account_key": None}, {"service_account_key": " "}],
)
def test_a_keyless_source_fails_unless_the_engine_opts_in_to_adc(
    creds: dict[str, Optional[str]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = FakeSession()
    with pytest.raises(DiscoveryConfigurationError, match=ALLOW_ADC_ENV_VAR) as exc:
        scan(session, creds=creds)
    assert failure_code(exc.value) is DiscoveryErrorCode.NOT_CONFIGURED
    assert session.calls == []

    monkeypatch.setenv(ALLOW_ADC_ENV_VAR, "false")
    with pytest.raises(DiscoveryConfigurationError):
        settings_from(creds, FIELDS)


def test_a_keyless_source_uses_the_engines_own_identity_when_it_opts_in(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(ALLOW_ADC_ENV_VAR, "true")
    assert settings_from({}, FIELDS).credentials is None
    assert ALLOW_ADC_ENV_VAR == "ARTHUR_ENGINE_GCP_SECURITY_OPERATIONS_ALLOW_ADC"


def test_the_engines_own_identity_is_asked_for_the_readonly_scope(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    asked: list[list[str]] = []

    def default(scopes: list[str]) -> tuple[Any, str]:
        asked.append(scopes)
        return SimpleNamespace(), "engine-project"

    monkeypatch.setattr(client_module.google.auth, "default", default)
    monkeypatch.setattr(client_module, "AuthorizedSession", lambda c: ("signed", c))
    session = authorized_session(None, [CHRONICLE_READONLY_SCOPE])
    assert asked == [[CHRONICLE_READONLY_SCOPE]]
    assert session[0] == "signed"  # type: ignore[index]


def test_an_engine_without_its_own_identity_is_a_configuration_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def default(scopes: list[str]) -> Any:
        raise DefaultCredentialsError("Your default credentials were not found.")

    monkeypatch.setattr(client_module.google.auth, "default", default)
    with pytest.raises(DiscoveryConfigurationError, match="service_account_key") as exc:
        authorized_session(None, [CHRONICLE_READONLY_SCOPE])
    assert exc.value.__cause__ is None


def test_a_key_that_is_not_json_is_reported_without_its_content() -> None:
    secret = '{"type": "service_account", "private_key": "SUPER-SECRET"'
    with pytest.raises(DiscoveryConfigurationError) as exc:
        settings_from({"service_account_key": secret}, FIELDS)
    assert "SUPER-SECRET" not in str(exc.value)
    assert "service_account_key" in str(exc.value)


def test_a_key_that_is_not_a_service_account_is_refused() -> None:
    key = json.dumps({"type": "external_account", "credential_source": {"file": "/x"}})
    with pytest.raises(DiscoveryConfigurationError, match="not a service account"):
        settings_from({"service_account_key": key}, FIELDS)


def test_a_refused_credential_reads_as_authentication_failed() -> None:
    session = FakeSession(
        RefreshError("invalid_grant: Invalid JWT Signature.", retryable=False),
    )
    with pytest.raises(RefreshError) as exc:
        scan(session)
    assert failure_code(exc.value) is DiscoveryErrorCode.AUTHENTICATION_FAILED


def test_a_token_endpoint_outage_is_not_a_refused_credential() -> None:
    session = FakeSession(RefreshError("temporarily_unavailable", retryable=True))
    with pytest.raises(RefreshError) as exc:
        scan(session)
    assert failure_code(exc.value) is DiscoveryErrorCode.PROVIDER_ERROR


# -- records -------------------------------------------------------------------------


def test_rows_become_records_by_column_name_not_position() -> None:
    columns = host_columns(2)
    reordered = {k: columns[k] for k in ("last_seen", "name", "external_id")}
    records = scan(FakeSession(ok(reordered)))
    assert [r.external_id for r in records] == [
        "ws-0000.corp.example",
        "ws-0001.corp.example",
    ]
    assert records[0].last_seen == datetime(2026, 10, 20, 12, 0, tzinfo=timezone.utc)


@pytest.mark.parametrize("prefix", ["", "$"])
def test_a_column_read_with_or_without_the_variable_sigil_is_the_contract_column(
    prefix: str,
) -> None:
    records = scan(FakeSession(ok(host_columns(2, prefix))))
    assert [r.name for r in records] == ["ws-0000.corp.example", "ws-0001.corp.example"]


def test_only_one_sigil_is_taken_off() -> None:
    columns = {**host_columns(1), "$$tools": [strings("search")]}
    with pytest.raises(OutputContractError, match=re.escape("$tools")):
        scan(FakeSession(ok(columns)))


def test_typed_values_are_unwrapped_into_what_the_record_takes() -> None:
    columns = {
        "external_id": [s("a"), s("b"), s("c")],
        "name": [s("Agent A"), s("Agent B"), s("Agent C")],
        "last_seen": [
            i64(SEEN),
            ts("2026-10-20T12:30:00.250Z"),
            {"value": {"uint64Val": str(SEEN)}},
        ],
        "llm_models": [
            strings("example-ai/chat-small", "example-ai/chat-large"),
            {"list": {}},
            null(),
        ],
        "data_sources": [strings("https://api.openai.com"), strings(), {}],
    }
    a, b, c = scan(FakeSession(ok(columns)))
    assert a.last_seen == datetime(2026, 10, 20, 12, 0, tzinfo=timezone.utc)
    assert b.last_seen == datetime(2026, 10, 20, 12, 30, 0, 250000, tzinfo=timezone.utc)
    assert c.last_seen == a.last_seen
    assert [m.name for m in a.llm_models] == [
        "example-ai/chat-small",
        "example-ai/chat-large",
    ]
    assert b.llm_models == [] and not c.llm_models
    assert [d.url for d in a.data_sources] == ["https://api.openai.com"]


def test_a_value_of_a_type_no_field_holds_is_read_as_empty_and_reported(
    caplog: pytest.LogCaptureFixture,
) -> None:
    columns = {
        **host_columns(2),
        "platform": [
            {"value": {"dateVal": {"year": 2026, "month": 10, "day": 20}}},
            {"value": {"bytesVal": "c2VjcmV0"}},
        ],
    }
    with caplog.at_level(logging.WARNING, logger=LOG.name):
        records = scan(FakeSession(ok(columns)))
    assert [r.platform for r in records] == [None, None]
    assert "2 value(s) in column platform" in caplog.text
    assert "c2VjcmV0" not in caplog.text


def test_a_bad_row_is_skipped_and_its_values_stay_out_of_the_log(
    caplog: pytest.LogCaptureFixture,
) -> None:
    columns = host_columns(2)
    columns["last_seen"][1] = s("alice@corp.example")
    with caplog.at_level(logging.WARNING, logger=LOG.name):
        records = scan(FakeSession(ok(columns)))
    assert [r.external_id for r in records] == ["ws-0000.corp.example"]
    assert "1 of 2 result row(s) skipped" in caplog.text
    assert "alice@corp.example" not in caplog.text


def test_a_record_carries_the_instance_and_the_query_in_its_provenance() -> None:
    record, *_ = scan(FakeSession())
    source = record.creation_source
    assert isinstance(source, SIEMAgentCreationSource)
    assert source.vendor == VENDOR
    assert source.address.instance == PARENT
    assert source.address.scope is None
    assert source.address.query == QUERY
    assert source.address.resource_id == record.external_id


def test_two_instances_in_one_region_are_two_instances_and_one_is_one() -> None:
    other = "9f8e7d6c-5b4a-4c3d-8e2f-1a0b9c8d7e6f"
    first, *_ = scan(FakeSession())
    second, *_ = scan(FakeSession(), fields={**FIELDS, "instance_id": other})
    again, *_ = scan(
        FakeSession(),
        fields={**FIELDS, "instance_id": INSTANCE_ID.upper()},
    )
    assert (
        first.creation_source.address.instance
        != second.creation_source.address.instance
    )
    assert (
        again.creation_source.address.instance == first.creation_source.address.instance
    )


def test_output_satisfies_the_discovery_output_contract() -> None:
    check_batch(
        scan(FakeSession()),
        "Source config 'llm hosts' (gcp_security_operations)",
    )


def test_an_unmapped_column_fails_the_scan_instead_of_being_dropped() -> None:
    columns = {**host_columns(2), "hits": [i64(40), i64(41)]}
    with pytest.raises(OutputContractError) as exc:
        scan(FakeSession(ok(columns)))
    assert "hits" in str(exc.value)
    assert failure_code(exc.value) is DiscoveryErrorCode.NOT_CONFIGURED


def test_a_missing_contract_column_fails_the_scan() -> None:
    columns = host_columns(2)
    del columns["last_seen"]
    with pytest.raises(OutputContractError) as exc:
        scan(FakeSession(ok(columns)))
    assert "last_seen" in str(exc.value)


def test_a_zero_row_result_with_wrong_columns_fails_the_contract() -> None:
    with pytest.raises(OutputContractError):
        scan(FakeSession(ok({"host": [], "last_seen": []})))


def test_a_zero_row_result_with_contract_columns_ends_with_a_warning(
    caplog: pytest.LogCaptureFixture,
) -> None:
    with caplog.at_level(logging.WARNING, logger=LOG.name):
        assert scan(FakeSession(ok(host_columns(0)))) == []
    assert "returned no rows" in caplog.text
    assert "data access scopes" in caplog.text


def test_an_answer_with_nothing_in_it_is_zero_rows() -> None:
    # proto3 JSON leaves an empty `results` out; Google still echoes the window.
    body = {
        "timeWindow": {
            "startTime": "2026-10-20T12:00:00Z",
            "endTime": "2026-10-21T12:00:00Z",
        },
    }
    assert scan(FakeSession(FakeResponse(200, body))) == []


def test_records_are_batched() -> None:
    session = FakeSession(ok(host_columns(BATCH_SIZE + 1)))
    batches = list(connector_with(session).scan(config(), 24, CREDS, FIELDS, LOG))
    assert [len(b) for b in batches] == [BATCH_SIZE, 1]


# -- how complete the answer is ------------------------------------------------------


def row_limit(reason: str, limit: str = "1000") -> dict[str, Any]:
    return {
        "errorTitle": "Row limit exceeded",
        "errorDescription": "Only the first rows were returned.",
        "errorSeverity": "WARNING",
        "warningReason": reason,
        "metadata": [{"key": "ROW_LIMIT", "value": limit}],
    }


def test_a_capped_answer_is_reported_before_the_first_batch_is_handed_over(
    caplog: pytest.LogCaptureFixture,
) -> None:
    session = FakeSession(ok(errors=[row_limit("DEFAULT_ROW_LIMIT_EXCEEDED")]))
    batches = connector_with(session).scan(config(), 24, CREDS, FIELDS, LOG)
    with caplog.at_level(logging.WARNING, logger=LOG.name):
        next(batches)
    assert "row limit of 1000 (DEFAULT_ROW_LIMIT_EXCEEDED)" in caplog.text


@pytest.mark.parametrize(
    "reason, fix",
    [
        ("DEFAULT_ROW_LIMIT_EXCEEDED", "Add a limit: section"),
        ("CURATED_QUERY_DEFAULT_ROW_LIMIT_EXCEEDED", "Add a limit: section"),
        ("ROW_LIMIT_EXCEEDED", "Aggregate to fewer rows"),
    ],
)
def test_each_row_limit_names_its_fix(
    reason: str,
    fix: str,
    caplog: pytest.LogCaptureFixture,
) -> None:
    with caplog.at_level(logging.WARNING, logger=LOG.name):
        scan(FakeSession(ok(errors=[row_limit(reason, "10000")])))
    assert reason in caplog.text and fix in caplog.text


def test_other_runtime_errors_are_reported_without_the_values_they_quote(
    caplog: pytest.LogCaptureFixture,
) -> None:
    severe = {
        "errorTitle": "Function failed on value 'alice@corp.example'",
        "errorDescription": "re.regex could not evaluate 'alice@corp.example'",
        "errorSeverity": "SEVERE",
    }
    with caplog.at_level(logging.WARNING, logger=LOG.name):
        scan(FakeSession(ok(errors=[severe])))
    assert "SEVERE runtime error" in caplog.text
    assert "may be incomplete" in caplog.text
    assert "alice@corp.example" not in caplog.text


# -- stopping and retrying -----------------------------------------------------------


def test_the_connector_accepts_a_stop_check() -> None:
    assert isinstance(GcpSecurityOperationsConnector(), AcceptsStopCheck)


def test_a_stop_before_the_query_sends_nothing() -> None:
    session = FakeSession()
    connector = connector_with(session)
    connector.stop_when(lambda: True)
    assert list(connector.scan(config(), 24, CREDS, FIELDS, LOG)) == []
    assert session.calls == []


def test_a_rate_limit_is_waited_out_and_the_query_sent_again() -> None:
    sleeps: list[float] = []
    session = FakeSession(
        FakeResponse(429, None, {"Retry-After": "2"}),
        error(503, "UNAVAILABLE", "The service is currently unavailable."),
        ok(),
    )
    batches = connector_with(session, sleeps).scan(config(), 24, CREDS, FIELDS, LOG)
    assert len([r for batch in batches for r in batch]) == 3
    assert len(session.calls) == 3
    assert sleeps[0] == 2.0 and len(sleeps) == 2


def test_a_stop_during_retries_ends_them_with_the_last_answer() -> None:
    session = FakeSession(error(429, "RESOURCE_EXHAUSTED", "Quota exceeded."))
    connector = connector_with(session)
    asked: list[bool] = []
    # The stop is asked before the query (no) and before the first retry (yes).
    connector.stop_when(lambda: asked.append(True) or len(asked) > 1)
    with pytest.raises(GcpSecurityOperationsError) as exc:
        list(connector.scan(config(), 24, CREDS, FIELDS, LOG))
    assert exc.value.status_code == 429
    assert len(session.calls) == 1


def test_a_lasting_server_error_keeps_its_status() -> None:
    session = FakeSession(error(500, "INTERNAL", "Internal error encountered."))
    with pytest.raises(GcpSecurityOperationsError) as exc:
        scan(session)
    assert exc.value.status_code == 500
    assert failure_code(exc.value) is DiscoveryErrorCode.PROVIDER_ERROR
    assert len(session.calls) == MAX_ATTEMPTS


# -- configuration -------------------------------------------------------------------


@pytest.mark.parametrize("query", [None, "", "   "])
def test_a_missing_query_is_named(query: Optional[str]) -> None:
    with pytest.raises(DiscoveryConfigurationError, match="no query"):
        query_text(config(query))


def test_yara_l_is_passed_through_stripped() -> None:
    assert query_text(config(f"\n  {QUERY}  \n")) == QUERY


def test_a_json_body_is_refused_before_anything_is_sent() -> None:
    session = FakeSession()
    body = json.dumps({"query": {"query": QUERY}, "clearCache": True})
    with pytest.raises(DiscoveryConfigurationError, match="JSON body"):
        scan(session, query=body)
    assert session.calls == []


@pytest.mark.parametrize("language", ["esql", "kql", "spl", "none", "", None, "yara-l"])
def test_a_config_in_another_language_is_refused_before_anything_is_sent(
    language: Optional[str],
) -> None:
    session = FakeSession()
    connector = connector_with(session)
    with pytest.raises(DiscoveryConfigurationError, match="yara_l") as exc:
        list(connector.scan(config(language=language), 24, CREDS, FIELDS, LOG))
    assert failure_code(exc.value) is DiscoveryErrorCode.NOT_CONFIGURED
    assert session.calls == []


def test_missing_fields_are_named() -> None:
    with pytest.raises(DiscoveryConfigurationError) as exc:
        settings_from(CREDS, {})
    assert all(f in str(exc.value) for f in ("project_id", "location", "instance_id"))


@pytest.mark.parametrize(
    "location",
    [
        "https://us-chronicle.googleapis.com",
        "us-chronicle.googleapis.com",
        "evil.example.com",
        "us.evil.example.com/x",
        "attacker.example#",
        "us:443",
        "us/../../x",
        "us?x=1",
        "us@evil.example.com",
        "us-",
        "us west",
        "-us",
        "asia-south",
    ],
)
def test_a_location_that_is_not_a_bare_region_is_refused_before_the_token_is_sent(
    location: str,
) -> None:
    session = FakeSession()
    with pytest.raises(DiscoveryConfigurationError, match="location") as exc:
        scan(session, fields={**FIELDS, "location": location})
    assert failure_code(exc.value) is DiscoveryErrorCode.NOT_CONFIGURED
    assert location.strip() not in str(exc.value)
    assert session.calls == []


@pytest.mark.parametrize(
    "field, value",
    [
        ("project_id", "acme/../other"),
        ("project_id", "Acme Prod"),
        ("project_id", "acme?x"),
        ("instance_id", f"{INSTANCE_ID}/dashboardQueries"),
        ("instance_id", "../x"),
        ("instance_id", "a#b"),
    ],
)
def test_an_id_that_is_not_one_path_segment_is_refused(field: str, value: str) -> None:
    session = FakeSession()
    with pytest.raises(DiscoveryConfigurationError, match=field):
        scan(session, fields={**FIELDS, field: value})
    assert session.calls == []


@pytest.mark.parametrize(
    "project_id",
    ["acme-secops-prod", "123456789012", "example.com:acme-prod"],
)
def test_a_project_id_or_number_is_accepted(project_id: str) -> None:
    assert (
        settings_from(CREDS, {**FIELDS, "project_id": project_id}).project_id
        == project_id
    )


# -- failures ------------------------------------------------------------------------


@pytest.mark.parametrize(
    "status, canonical, reason, code, hint",
    [
        (
            401,
            "UNAUTHENTICATED",
            None,
            DiscoveryErrorCode.AUTHENTICATION_FAILED,
            "was refused",
        ),
        (
            403,
            "PERMISSION_DENIED",
            "IAM_PERMISSION_DENIED",
            DiscoveryErrorCode.PERMISSION_DENIED,
            "chronicle.dashboardQueries.execute",
        ),
        (
            403,
            "PERMISSION_DENIED",
            "SERVICE_DISABLED",
            DiscoveryErrorCode.PERMISSION_DENIED,
            "Enable the Chronicle API",
        ),
        (
            403,
            "PERMISSION_DENIED",
            "ACCESS_TOKEN_SCOPE_INSUFFICIENT",
            DiscoveryErrorCode.PERMISSION_DENIED,
            "chronicle.readonly",
        ),
    ],
)
def test_a_refusal_carries_its_status_and_a_hint(
    status: int,
    canonical: str,
    reason: Optional[str],
    code: DiscoveryErrorCode,
    hint: str,
) -> None:
    session = FakeSession(
        error(status, canonical, "Request had invalid credentials.", reason),
    )
    with pytest.raises(GcpSecurityOperationsError) as exc:
        scan(session)
    assert exc.value.status_code == status
    assert failure_code(exc.value) is code
    assert hint in str(exc.value)
    assert len(session.calls) == 1


@pytest.mark.parametrize(
    "message",
    [
        "compilation error: line 3 column 1: unknown field 'principal.hostnme'",
        "a statistics query requires a match or outcome section",
    ],
)
def test_yara_l_google_rejects_is_the_source_configs_to_fix(message: str) -> None:
    with pytest.raises(DiscoveryConfigurationError) as exc:
        scan(FakeSession(error(400, "INVALID_ARGUMENT", message)))
    assert message in str(exc.value)
    # Not the vendor's fault on a scheduled scan, and no status for Test Connection
    # to read as one.
    assert failure_code(exc.value) is DiscoveryErrorCode.NOT_CONFIGURED
    assert getattr(exc.value, "status_code", None) is None
    # Raised outside any except block, so no original error rides on __context__
    # either: Test Connection walks __cause__ or __context__ for a status.
    assert exc.value.__cause__ is None
    assert exc.value.__context__ is None
    # Test Connection also reads a status out of the message text ("HTTP 400").
    assert "HTTP" not in str(exc.value)


def test_any_other_400_stays_the_vendors_error() -> None:
    with pytest.raises(GcpSecurityOperationsError) as exc:
        scan(FakeSession(error(400, "FAILED_PRECONDITION", "Instance is not ready.")))
    assert exc.value.status_code == 400
    assert failure_code(exc.value) is DiscoveryErrorCode.PROVIDER_ERROR


@pytest.mark.parametrize(
    "response, names",
    [
        (error(404, "NOT_FOUND", "Requested entity was not found."), "instance_id"),
        (FakeResponse(404, None, {"Content-Type": "text/html"}), "location"),
    ],
)
def test_a_404_names_the_fields_to_check(response: FakeResponse, names: str) -> None:
    with pytest.raises(DiscoveryConfigurationError, match=names) as exc:
        scan(FakeSession(response))
    assert failure_code(exc.value) is DiscoveryErrorCode.NOT_CONFIGURED
    assert exc.value.__context__ is None
    assert "HTTP" not in str(exc.value)


@pytest.mark.parametrize(
    "exc_type",
    [
        requests.ConnectionError,
        requests.ConnectTimeout,
        requests.ReadTimeout,
        requests.exceptions.SSLError,
    ],
)
def test_an_unreachable_host_keeps_its_exception_type(exc_type: type) -> None:
    session = FakeSession(exc_type("Name or service not known"))
    with pytest.raises(exc_type, match="unreachable") as exc:
        scan(session)
    assert type(exc.value) is exc_type
    assert "us-chronicle.googleapis.com" in str(exc.value)
    assert len(session.calls) == 1


@pytest.mark.parametrize(
    "body",
    [None, ["not", "an", "object"], {"error": "x"}, {"results": "x"}, {}],
)
def test_a_success_status_without_a_result_is_the_vendors_error(body: Any) -> None:
    session = FakeSession(FakeResponse(200, body, {"Content-Type": "text/html"}))
    with pytest.raises(GcpSecurityOperationsError) as exc:
        scan(session)
    assert exc.value.status_code == 200
    assert failure_code(exc.value) is DiscoveryErrorCode.PROVIDER_ERROR


@pytest.mark.parametrize(
    "results",
    [
        [{"values": [s("a")]}],
        [{"column": "", "values": [s("a")]}],
        [{"column": "name", "values": "a"}],
        [
            {"column": "name", "values": [s("a")]},
            {"column": "$name", "values": [s("a")]},
        ],
        [
            {"column": "name", "values": [s("a")]},
            {"column": "external_id", "values": []},
        ],
        [{"column": "name", "values": ["a"]}],
        [{"column": "name", "values": [{"value": "a"}]}],
        [{"column": "name", "values": [{"list": {"values": ["a"]}}]}],
        ["not a column"],
    ],
)
def test_a_malformed_result_is_the_vendors_error(results: list[Any]) -> None:
    session = FakeSession(FakeResponse(200, {"results": results}))
    with pytest.raises(GcpSecurityOperationsError, match="malformed") as exc:
        scan(session)
    assert exc.value.status_code == 200


def test_the_scan_never_logs_the_key_or_row_values(
    caplog: pytest.LogCaptureFixture,
) -> None:
    with caplog.at_level(logging.DEBUG):
        scan(FakeSession(ok(errors=[row_limit("ROW_LIMIT_EXCEEDED")])))
        with pytest.raises(GcpSecurityOperationsError):
            scan(
                FakeSession(
                    error(401, "UNAUTHENTICATED", "Request had invalid credentials."),
                ),
            )
    assert "NOT-A-REAL-KEY-7f3a9c" not in caplog.text
    assert "ws-0000.corp.example" not in caplog.text


def test_the_settings_object_is_what_the_client_is_built_from() -> None:
    seen: list[GcpSecurityOperationsSettings] = []

    def factory(
        settings: GcpSecurityOperationsSettings,
        log: logging.Logger,
    ) -> GcpSecurityOperationsClient:
        seen.append(settings)
        return GcpSecurityOperationsClient(settings, logger=log, session=FakeSession())  # type: ignore[arg-type]

    connector = GcpSecurityOperationsConnector(
        client_factory=factory,
        clock=lambda: NOW,
    )
    list(connector.scan(config(), 24, CREDS, FIELDS, LOG))
    assert (seen[0].project_id, seen[0].location, seen[0].instance_id) == (
        PROJECT_ID,
        "us",
        INSTANCE_ID,
    )
    assert seen[0].url == URL


# -- responses shaped on Google's published types ------------------------------------

# Every field `ExecuteDashboardQueryResponse` defines, as proto3 JSON writes it, for the
# docs' gateway sample: column metadata, value metadata, a list cell, a null cell, the
# window run, data sources, language features and a row-limit runtime error. Built from
# google-cloud-chronicle 0.6.4's types, not captured: no live instance was available.
# Hosts, ids and key names are fakes.
SHAPED_GATEWAY: dict[str, Any] = {
    "results": [
        {
            "column": "external_id",
            "values": [
                {"value": {"stringVal": "llm-gateway:svc-ci-runner"}},
                {"value": {"stringVal": "llm-gateway:svc-support-bot"}},
            ],
            "metadata": {"selected": True},
        },
        {
            "column": "name",
            "values": [
                {"value": {"stringVal": "svc-ci-runner"}},
                {"value": {"stringVal": "svc-support-bot"}},
            ],
        },
        {
            "column": "last_seen",
            "values": [
                {
                    "value": {
                        "int64Val": "1792497600",
                        "metadata": {
                            "fieldPaths": ["metadata.event_timestamp.seconds"],
                        },
                    },
                },
                {"value": {"int64Val": "1792494000"}},
            ],
        },
        {
            "column": "llm_models",
            "values": [
                {
                    "list": {
                        "values": [
                            {"stringVal": "example-ai/chat-large"},
                            {"stringVal": "example-ai/chat-small"},
                        ],
                    },
                },
                {"value": {"nullVal": True}},
            ],
        },
    ],
    "dataSources": ["UDM"],
    "timeWindow": {
        "startTime": "2026-10-20T12:00:00Z",
        "endTime": "2026-10-21T12:00:00Z",
    },
    "queryRuntimeErrors": [
        {
            "errorTitle": "Row limit exceeded",
            "errorDescription": "The query returned more rows than its limit.",
            "errorSeverity": "WARNING",
            "warningReason": "ROW_LIMIT_EXCEEDED",
            "metadata": [{"key": "ROW_LIMIT", "value": "10000"}],
        },
    ],
    "languageFeatures": ["MATCH", "OUTCOME", "LIMIT"],
}


def test_the_gateway_sample_query_result_becomes_one_record_per_credential_with_its_models(
    caplog: pytest.LogCaptureFixture,
) -> None:
    session = FakeSession(FakeResponse(200, SHAPED_GATEWAY))
    with caplog.at_level(logging.WARNING, logger=LOG.name):
        records = scan(session, query=GATEWAY_QUERY)

    assert session.calls[0]["json"]["query"]["query"] == GATEWAY_QUERY.strip()
    check_batch(records, "Source config 'llm hosts' (gcp_security_operations)")
    assert [
        (
            r.external_id,
            r.name,
            r.last_seen.isoformat(),
            [m.name for m in r.llm_models or []],
        )
        for r in records
    ] == [
        (
            "llm-gateway:svc-ci-runner",
            "svc-ci-runner",
            "2026-10-20T12:00:00+00:00",
            ["example-ai/chat-large", "example-ai/chat-small"],
        ),
        (
            "llm-gateway:svc-support-bot",
            "svc-support-bot",
            "2026-10-20T11:00:00+00:00",
            [],
        ),
    ]
    address = records[0].creation_source.address
    assert address.resource_id == records[0].external_id
    assert address.query == GATEWAY_QUERY.strip()
    assert "row limit of 10000 (ROW_LIMIT_EXCEEDED)" in caplog.text


def test_the_docs_samples_project_only_contract_columns() -> None:
    """Every match and outcome variable becomes a column, so each must be one the
    contract names."""
    for sample in (HOSTS_QUERY, GATEWAY_QUERY):
        variables = set(re.findall(r"\$(\w+)\s*=", sample))
        assert {"external_id", "name", "last_seen"} <= variables
        assert variables <= {
            "external_id",
            "name",
            "last_seen",
            "llm_models",
            "tools",
            "sub_agents",
            "data_sources",
            "runs_on",
            "platform",
        }
    assert "$llm_models" in GATEWAY_QUERY
