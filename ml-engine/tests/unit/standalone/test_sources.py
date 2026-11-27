"""The forms a dashboard adds a source with, and Test Connection without a Platform."""

from typing import Any

import pytest

from discovery import standalone_connectors
from standalone import sources
from standalone.discovery_config import (
    StandaloneConfigError,
    resolve_source,
    sensitive_fields,
    source_from_values,
)
from standalone.sources import source_types, try_source


def test_every_connector_has_a_form_that_agrees_on_its_secrets() -> None:
    forms = {entry["vendor"]: entry for entry in source_types()}

    assert forms.keys() == standalone_connectors().keys()
    for vendor, form in forms.items():
        secret = {f["name"] for f in form["fields"] if f["is_sensitive"]}
        assert secret == sensitive_fields(vendor), vendor


def vertex(**fields: str) -> dict[str, Any]:
    return {
        "name": "vertex",
        "vendor": "gcp_vertex",
        "fields": [{"key": k, "value": v} for k, v in fields.items()],
        "configs": [
            {
                "name": "c",
                "query": "",
                "query_language": "none",
                "lookback_window_seconds": 86400,
            },
        ],
    }


@pytest.fixture
def previewed(monkeypatch: pytest.MonkeyPatch) -> list[dict[str, Any]]:
    calls: list[dict[str, Any]] = []

    class Result:
        def model_dump(self, mode: str) -> dict[str, Any]:
            return {"outcome": "succeeded"}

    def fake(
        config: Any, lookback_hours: int, credentials: Any, *a: Any, **k: Any
    ) -> Any:
        calls.append({"config": config, "credentials": credentials})
        return Result()

    monkeypatch.setattr(sources, "preview_source", fake)
    return calls


def test_a_test_reads_values_literally(previewed: list[dict[str, Any]]) -> None:
    result = try_source(
        vertex(project_id="p", service_account_key="${ELASTIC_PASSWORD}"), None, []
    )

    assert result["outcome"] == "succeeded"
    assert previewed[0]["credentials"] == {"service_account_key": "${ELASTIC_PASSWORD}"}


def test_a_test_refuses_a_file_reference(previewed: list[dict[str, Any]]) -> None:
    raw = vertex(project_id="p")
    raw["fields"].append(
        {"key": "service_account_key", "value": {"file": "/etc/passwd"}}
    )

    with pytest.raises(StandaloneConfigError):
        try_source(raw, None, [])
    assert previewed == []


def test_a_secret_left_out_is_kept_from_the_named_source(
    previewed: list[dict[str, Any]],
) -> None:
    configured = resolve_source(
        source_from_values(vertex(project_id="p", service_account_key="KEY")),
    )

    try_source(
        vertex(project_id="new", service_account_key=""), None, configured, "vertex"
    )

    assert previewed[0]["credentials"] == {"service_account_key": "KEY"}
    assert previewed[0]["config"].source_fields == {"project_id": "new"}


def test_secrets_are_kept_only_from_a_source_of_the_same_vendor(
    previewed: list[dict[str, Any]],
) -> None:
    with pytest.raises(StandaloneConfigError, match="No configured gcp_vertex"):
        try_source(vertex(project_id="p"), None, [], "vertex")


@pytest.mark.parametrize(
    "fields",
    [1, "project_id", [1], [{"value": "p"}], [{"key": ["project_id"], "value": "p"}]],
)
@pytest.mark.parametrize("keep", [None, "vertex"])
def test_fields_that_are_not_key_value_objects_are_refused(
    previewed: list[dict[str, Any]], fields: Any, keep: Any
) -> None:
    configured = resolve_source(
        source_from_values(vertex(project_id="p", service_account_key="KEY")),
    )
    raw = {**vertex(), "fields": fields}

    with pytest.raises(StandaloneConfigError, match="list of {key, value} objects"):
        try_source(raw, None, configured, keep)
    assert previewed == []


def test_validate_only_runs_no_connector(previewed: list[dict[str, Any]]) -> None:
    result = try_source(vertex(project_id="p"), None, [], validate_only=True)

    assert result == {"outcome": "valid"} and previewed == []


def test_every_connector_says_where_its_secrets_go() -> None:
    forms = {entry["vendor"]: entry for entry in source_types()}

    assert sources.SECRET_DESTINATION_FIELDS.keys() == forms.keys()
    for vendor, deciding in sources.SECRET_DESTINATION_FIELDS.items():
        names = {f["name"] for f in forms[vendor]["fields"] if not f["is_sensitive"]}
        assert deciding <= names, vendor


def splunk(**fields: Any) -> dict[str, Any]:
    return {
        "name": "splunk",
        "vendor": "splunk_enterprise",
        "fields": [{"key": k, "value": v} for k, v in fields.items()],
        "configs": [
            {
                "name": "c",
                "query": "search index=main",
                "query_language": "spl",
                "lookback_window_seconds": 86400,
            },
        ],
    }


@pytest.fixture
def configured_splunk() -> list[Any]:
    return resolve_source(
        source_from_values(
            splunk(base_url="https://splunk.acme.com:8089", auth_token="TOKEN"),
        ),
    )


@pytest.mark.parametrize(
    "changed",
    [
        {"base_url": "https://evil.example.com:8089"},
        {"ca_certificate": "-----BEGIN CERTIFICATE-----"},
        {"tls_verification": "false"},
    ],
)
@pytest.mark.parametrize("validate_only", [False, True])
def test_a_kept_secret_is_not_sent_somewhere_new(
    previewed: list[dict[str, Any]],
    configured_splunk: list[Any],
    changed: dict[str, str],
    validate_only: bool,
) -> None:
    fields = {"base_url": "https://splunk.acme.com:8089", "auth_token": "", **changed}

    with pytest.raises(StandaloneConfigError, match="again") as e:
        try_source(splunk(**fields), None, configured_splunk, "splunk", validate_only)
    assert "TOKEN" not in str(e.value) and previewed == []


def test_a_secret_given_again_may_go_somewhere_new(
    previewed: list[dict[str, Any]], configured_splunk: list[Any]
) -> None:
    raw = splunk(base_url="https://splunk2.acme.com:8089", auth_token="NEW")

    try_source(raw, None, configured_splunk, "splunk")

    assert previewed[0]["credentials"] == {"auth_token": "NEW"}


def test_a_null_field_takes_the_configured_value(
    previewed: list[dict[str, Any]], configured_splunk: list[Any]
) -> None:
    try_source(
        splunk(base_url=None, auth_token=None), None, configured_splunk, "splunk"
    )

    assert previewed[0]["credentials"] == {"auth_token": "TOKEN"}
    assert previewed[0]["config"].source_fields == {
        "base_url": "https://splunk.acme.com:8089",
    }


def test_a_keyless_test_is_refused(previewed: list[dict[str, Any]]) -> None:
    with pytest.raises(StandaloneConfigError, match="own identity"):
        try_source(vertex(project_id="p"), None, [])
    assert previewed == []


def test_a_keyless_test_runs_as_configured(previewed: list[dict[str, Any]]) -> None:
    configured = resolve_source(source_from_values(vertex(project_id="p")))

    try_source(vertex(project_id="p"), None, configured)

    assert previewed[0]["credentials"] == {}


@pytest.mark.parametrize(
    "configured",
    [
        vertex(project_id="p", location="europe-west4"),
        vertex(project_id="p", service_account_key="KEY"),
    ],
)
def test_a_keyless_test_unlike_what_is_configured_is_refused(
    previewed: list[dict[str, Any]], configured: dict[str, Any]
) -> None:
    with pytest.raises(StandaloneConfigError, match="own identity"):
        try_source(
            vertex(project_id="p"), None, resolve_source(source_from_values(configured))
        )
    assert previewed == []
