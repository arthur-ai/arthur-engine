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


def test_validate_only_runs_no_connector(previewed: list[dict[str, Any]]) -> None:
    result = try_source(vertex(project_id="p"), None, [], validate_only=True)

    assert result == {"outcome": "valid"} and previewed == []
