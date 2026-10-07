"""The standalone discovery config file, from YAML on disk to what a connector reads.

The tests that matter most are the hand-off ones: a resolved scan is parsed by the
connector's own settings code, so the split between source fields and credentials is
checked by the code that consumes it rather than by a copy of its expectations.
"""

import logging
import textwrap
from datetime import timedelta
from pathlib import Path
from typing import Any

import pytest

from discovery import source_connectors
from discovery.cloud.gcp_vertex.connector import settings_from
from discovery.endpoint.jamf.connector import _settings_from as jamf_settings_from
from standalone.discovery_config import (
    DISCOVERY_CONFIG_ENV_VAR,
    StandaloneConfigError,
    load_config,
    standalone_config_path,
)
from standalone.sinks.siem.splunk_hec import SplunkHecDestination
from standalone.sinks.webhook import WebhookDestination

JAMF_SECRET = "jamf-s3cr3t-value-0001"
HEC_TOKEN = "hec-t0ken-value-0002"

FULL_CONFIG = """
version: 1
schedule:
  interval: 6h
  max_concurrent_scans: 2
sources:
  - name: corp-macs
    vendor: jamf_pro
    fields:
      - {key: base_url, value: https://acme.jamfcloud.com}
      - {key: client_id, value: "${JAMF_CLIENT_ID}"}
      - {key: client_secret, value: "${JAMF_CLIENT_SECRET}"}
      - {key: include_groups, value: "Engineering,Data Science"}
    configs:
      - name: all-macs
        query: {file: catalog.yaml}
        query_language: none
        lookback_window_seconds: 86400
  - name: vertex-prod
    vendor: gcp_vertex
    fields:
      - {key: project_id, value: acme-prod}
      - {key: location, value: europe-west4}
      - {key: service_account_key, value: {file: secrets/gcp.json}}
    configs:
      - name: agent-engines
        query: ""
        query_language: none
        lookback_window_seconds: 23400
destination:
  type: splunk_hec
  url: https://splunk.acme.internal:8088/services/collector/event
  token: ${HEC_TOKEN}
  index: ai_inventory
"""

GCP_KEY = '{\n  "type": "service_account",\n  "private_key": "-----BEGIN..."\n}\n'
CATALOG = "agents:\n  - name: claude-code\n"

VERTEX_SOURCE = """\
sources:
  - name: vertex
    vendor: gcp_vertex
    fields: [{key: project_id, value: p}]
    configs:
      - {name: c, query: "", query_language: none, lookback_window_seconds: 86400}
"""


def write(directory: Path, text: str, name: str = "discovery.yaml") -> Path:
    path = directory / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(text))
    return path


@pytest.fixture
def full_config(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("JAMF_CLIENT_ID", "jamf-client")
    monkeypatch.setenv("JAMF_CLIENT_SECRET", JAMF_SECRET)
    monkeypatch.setenv("HEC_TOKEN", HEC_TOKEN)
    write(tmp_path, GCP_KEY, "secrets/gcp.json")
    write(tmp_path, CATALOG, "catalog.yaml")
    return write(tmp_path, FULL_CONFIG)


def minimal(**overrides: str) -> str:
    """A valid one-source file, with top-level blocks swapped for `overrides`."""
    blocks = {
        "schedule": "schedule:\n  interval: 6h\n",
        "sources": VERTEX_SOURCE,
        "destination": textwrap.dedent(
            """\
            destination:
              type: webhook
              url: https://hooks.example.com/ingest
            """,
        ),
    }
    blocks.update(overrides)
    return "version: 1\n" + "".join(blocks.values())


def jamf_source(fields: str = "", config: str = "") -> str:
    """A Jamf source whose fields and first config can be extended."""
    return (
        textwrap.dedent(
            """\
        sources:
          - name: macs
            vendor: jamf_pro
            fields:
              - {key: base_url, value: https://acme.jamfcloud.com}
              - {key: client_id, value: a}
              - {key: client_secret, value: b}
        """,
        )
        + textwrap.indent(fields, "      ")
        + (
            "    configs:\n"
            "      - name: c\n"
            "        query: ''\n"
            "        query_language: none\n"
            "        lookback_window_seconds: 86400\n"
        )
        + textwrap.indent(config, "        ")
    )


def load_error(tmp_path: Path, text: str) -> str:
    with pytest.raises(StandaloneConfigError) as e:
        load_config(write(tmp_path, text))
    return str(e.value)


def test_loads_a_full_config(full_config: Path) -> None:
    config = load_config(full_config)

    assert config is not None
    assert config.schedule.interval == timedelta(hours=6)
    assert config.schedule.max_concurrent_scans == 2
    assert isinstance(config.destination, SplunkHecDestination)
    assert config.destination.token.get_secret_value() == HEC_TOKEN
    assert [s.name for s in config.sources] == ["corp-macs", "vertex-prod"]
    assert [s.config.name for s in config.scans()] == ["all-macs", "agent-engines"]


def test_jamf_scan_is_what_the_connector_reads(full_config: Path) -> None:
    config = load_config(full_config)
    assert config is not None
    jamf = config.scans()[0]

    settings = jamf_settings_from(jamf.credentials, jamf.source_fields)

    assert settings.base_url == "https://acme.jamfcloud.com"
    assert (settings.client_id, settings.client_secret) == ("jamf-client", JAMF_SECRET)
    assert settings.include_groups == ("Engineering", "Data Science")
    # Split by the connector's declaration: the URL stays readable in logs, and the
    # secrets never travel as ordinary fields.
    assert set(jamf.credentials) == {"client_id", "client_secret"}
    assert "client_secret" not in jamf.source_fields
    assert jamf.config.source_fields == jamf.source_fields
    assert jamf.config.vendor == "jamf_pro"
    assert jamf.config.query == CATALOG  # read verbatim, not trimmed
    assert jamf.lookback_hours == 24


def test_vertex_scan_is_what_the_connector_reads(full_config: Path) -> None:
    config = load_config(full_config)
    assert config is not None
    vertex = config.scans()[1]

    settings = settings_from(vertex.source_fields)

    assert (settings.project_id, settings.location) == ("acme-prod", "europe-west4")
    # Read from the file beside the config and trimmed, but otherwise intact.
    assert vertex.credentials == {"service_account_key": GCP_KEY.strip()}
    # 6.5 hours, rounded up as the Platform rounds a window when it dispatches it.
    assert vertex.lookback_hours == 7


def test_credentials_stay_out_of_reprs(full_config: Path) -> None:
    config = load_config(full_config)
    assert config is not None

    assert JAMF_SECRET not in repr(config)
    assert JAMF_SECRET not in str(config)
    assert JAMF_SECRET not in repr(config.scans())
    assert HEC_TOKEN not in repr(config)
    assert "client_secret=***" in repr(config.sources[0])


def test_ids_are_stable_and_distinct(full_config: Path) -> None:
    first = load_config(full_config)
    second = load_config(full_config)
    assert first is not None and second is not None

    def ids(scans: Any) -> list[tuple[str, str]]:
        return [
            (s.config.discovery_source_id, s.discovery_source_config_id) for s in scans
        ]

    assert ids(first.scans()) == ids(second.scans())
    assert len({i for pair in ids(first.scans()) for i in pair}) == 4


def test_a_source_can_have_several_configs(tmp_path: Path) -> None:
    text = minimal(
        sources=jamf_source(
            config="",
        )
        + "      - {name: d, query: '', query_language: none, "
        "lookback_window_seconds: 3600}\n",
    )
    config = load_config(write(tmp_path, text))
    assert config is not None

    scans = config.scans()

    assert [s.config.name for s in scans] == ["c", "d"]
    assert scans[0].config.discovery_source_id == scans[1].config.discovery_source_id
    assert scans[0].discovery_source_config_id != scans[1].discovery_source_config_id


def test_vertex_without_a_key_leaves_it_to_the_connector(tmp_path: Path) -> None:
    config = load_config(write(tmp_path, minimal()))
    assert config is not None

    # The connector decides between ADC and a configuration error, as it does for a
    # Platform job whose source has no key.
    assert config.scans()[0].credentials == {}


def test_a_config_cannot_restate_what_it_inherits(tmp_path: Path) -> None:
    message = load_error(
        tmp_path,
        minimal(sources=jamf_source(config="vendor: gcp_vertex\n")),
    )

    assert "vendor" in message and "come(s) from the source" in message


def test_a_vendor_with_no_connector_is_refused(tmp_path: Path) -> None:
    # A real DiscoverySourceVendor, but one this engine cannot scan.
    text = minimal(sources=VERTEX_SOURCE.replace("gcp_vertex", "microsoft_sentinel"))

    assert "no connector for vendor 'microsoft_sentinel'" in load_error(tmp_path, text)


def test_an_unknown_vendor_is_refused(tmp_path: Path) -> None:
    text = minimal(sources=VERTEX_SOURCE.replace("gcp_vertex", "not_a_vendor"))

    assert "sources.0.vendor" in load_error(tmp_path, text)


@pytest.fixture
def undeclared_connector(monkeypatch: pytest.MonkeyPatch) -> None:
    class Undeclared:
        pass

    connectors = {**source_connectors(), "microsoft_sentinel": Undeclared}
    monkeypatch.setattr(
        "standalone.discovery_config.source_connectors",
        lambda: connectors,
    )


@pytest.mark.usefixtures("undeclared_connector")
def test_a_connector_that_does_not_declare_secrets_is_refused(tmp_path: Path) -> None:
    text = minimal(sources=VERTEX_SOURCE.replace("gcp_vertex", "microsoft_sentinel"))

    assert "does not declare which of its fields" in load_error(tmp_path, text)


def test_every_registered_connector_declares_its_secrets() -> None:
    """Without it a connector can only be scanned via the Platform."""
    for vendor, connector in source_connectors().items():
        assert isinstance(
            getattr(connector, "SENSITIVE_FIELDS", None), frozenset
        ), vendor


def test_an_unknown_query_language_is_refused(tmp_path: Path) -> None:
    text = minimal(
        sources=VERTEX_SOURCE.replace("query_language: none", "query_language: sql")
    )

    assert "query_language must be one of" in load_error(tmp_path, text)


def test_a_repeated_field_is_refused(tmp_path: Path) -> None:
    text = minimal(sources=jamf_source(fields="- {key: client_secret, value: c}\n"))

    assert "client_secret are set more than once" in load_error(tmp_path, text)


def test_repeated_names_are_refused(tmp_path: Path) -> None:
    configs = minimal(
        sources=jamf_source() + "      - {name: c, query: '', query_language: none, "
        "lookback_window_seconds: 1}\n",
    )
    sources = minimal(sources=VERTEX_SOURCE + VERTEX_SOURCE.removeprefix("sources:\n"))

    assert "config name(s) c are used more than once" in load_error(tmp_path, configs)
    assert "source name(s) vertex are used more than once" in load_error(
        tmp_path,
        sources,
    )


def test_a_missing_required_key_is_named(tmp_path: Path) -> None:
    text = minimal(
        sources=VERTEX_SOURCE.replace(", lookback_window_seconds: 86400", ""),
    )

    assert "sources.0.configs.0.lookback_window_seconds" in load_error(tmp_path, text)


def test_unset_environment_variables_are_all_named(tmp_path: Path) -> None:
    text = minimal(
        sources=jamf_source(
            fields='- {key: extra_a, value: "${UNSET_A}"}\n'
            '- {key: extra_b, value: "prefix-${UNSET_B}"}\n',
        ),
    )

    message = load_error(tmp_path, text)

    assert "UNSET_A" in message and "UNSET_B" in message


def test_interpolated_values_are_not_reparsed_as_yaml(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # A value full of YAML syntax arrives as one string, not as structure.
    monkeypatch.setenv("KEY", 'x: [1, 2]\n"quoted": {a: b}')
    text = minimal(
        sources=VERTEX_SOURCE.replace(
            "fields: [{key: project_id, value: p}]",
            "fields: [{key: project_id, value: p}, "
            '{key: service_account_key, value: "${KEY}"}]',
        ),
    )

    config = load_config(write(tmp_path, text))
    assert config is not None

    assert config.scans()[0].credentials == {
        "service_account_key": 'x: [1, 2]\n"quoted": {a: b}',
    }


def test_errors_never_quote_a_credential(tmp_path: Path) -> None:
    text = minimal(
        sources=jamf_source(fields=f"- {{key: api_token, value: [{JAMF_SECRET}]}}\n"),
    )

    message = load_error(tmp_path, text)

    assert "sources.0.fields.3.value" in message
    assert JAMF_SECRET not in message


def test_yaml_errors_never_quote_the_line(tmp_path: Path) -> None:
    message = load_error(tmp_path, f'version: 1\ntoken: "{JAMF_SECRET}\n  bad: [\n')

    assert "not valid YAML" in message
    assert JAMF_SECRET not in message


def test_a_missing_file_reference_is_located(tmp_path: Path) -> None:
    text = minimal(
        sources=jamf_source(fields="- {key: extra, value: {file: missing-secret}}\n"),
    )

    message = load_error(tmp_path, text)

    assert "sources.0.fields.3.value" in message
    assert "missing-secret" in message


def test_a_misspelt_schedule_key_is_refused(tmp_path: Path) -> None:
    text = minimal(schedule="schedule:\n  interval: 6h\n  run_on_strat: false\n")

    assert "schedule.run_on_strat" in load_error(tmp_path, text)


def test_a_missing_destination_secret_file_is_located(tmp_path: Path) -> None:
    text = minimal(
        destination=textwrap.dedent(
            """\
            destination:
              type: splunk_hec
              url: https://splunk.example.com/services/collector/event
              token: {file: missing-token}
            """,
        ),
    )

    message = load_error(tmp_path, text)

    assert "destination.splunk_hec.token" in message
    assert "missing-token" in message


def test_a_misspelt_destination_key_is_refused(tmp_path: Path) -> None:
    text = minimal(
        destination=textwrap.dedent(
            """\
            destination:
              type: splunk_hec
              url: https://splunk.example.com/services/collector/event
              tokne: t
            """,
        ),
    )

    message = load_error(tmp_path, text)

    assert "tokne" in message and "token" in message


@pytest.mark.parametrize("allow", [False, True])
def test_http_destination_needs_an_explicit_opt_in(
    tmp_path: Path,
    allow: bool,
) -> None:
    text = minimal(
        destination=textwrap.dedent(
            f"""\
            destination:
              type: webhook
              url: http://localhost:8080/ingest
              allow_insecure_http: {str(allow).lower()}
            """,
        ),
    )

    if allow:
        config = load_config(write(tmp_path, text))
        assert config is not None
        assert isinstance(config.destination, WebhookDestination)
    else:
        assert "allow_insecure_http" in load_error(tmp_path, text)


@pytest.mark.parametrize(
    ("interval", "expected"),
    [
        ("90s", timedelta(seconds=90)),
        ("15m", timedelta(minutes=15)),
        ("6h", timedelta(hours=6)),
        ("1d", timedelta(days=1)),
        ("3600", timedelta(hours=1)),  # a YAML number is seconds
        ('"3600"', None),  # a string with no unit is ambiguous
        ("6 hours", None),
        ("30s", None),  # under the minimum
    ],
)
def test_interval_formats(
    tmp_path: Path,
    interval: str,
    expected: timedelta | None,
) -> None:
    text = minimal(schedule=f"schedule:\n  interval: {interval}\n")

    if expected is None:
        assert "schedule.interval" in load_error(tmp_path, text)
    else:
        config = load_config(write(tmp_path, text))
        assert config is not None
        assert config.schedule.interval == expected


def test_a_window_shorter_than_the_interval_warns(
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    text = minimal(schedule="schedule:\n  interval: 2d\n")

    with caplog.at_level(logging.WARNING):
        assert load_config(write(tmp_path, text)) is not None

    assert "vertex/c" in caplog.text and "lookback_window_seconds" in caplog.text


def test_a_full_enumeration_has_no_gap(tmp_path: Path) -> None:
    text = minimal(
        schedule="schedule:\n  interval: 2d\n",
        sources=VERTEX_SOURCE.replace("86400", "0"),
    )
    config = load_config(write(tmp_path, text))
    assert config is not None

    assert config.configs_with_gaps() == []
    assert config.scans()[0].lookback_hours == 0


def test_a_disabled_file_needs_nothing_else(tmp_path: Path) -> None:
    # Neither the unset variable nor the missing sections are an error once disabled.
    path = write(tmp_path, "version: 1\nenabled: false\ntoken: ${NEVER_SET}\n")

    assert load_config(path) is None


def test_a_missing_config_file_is_named(tmp_path: Path) -> None:
    with pytest.raises(StandaloneConfigError, match="nope.yaml"):
        load_config(tmp_path / "nope.yaml")


def test_config_path_comes_from_the_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv(DISCOVERY_CONFIG_ENV_VAR, raising=False)
    assert standalone_config_path() is None

    monkeypatch.setenv(DISCOVERY_CONFIG_ENV_VAR, "  ")
    assert standalone_config_path() is None

    monkeypatch.setenv(DISCOVERY_CONFIG_ENV_VAR, "/etc/arthur/discovery.yaml")
    assert standalone_config_path() == Path("/etc/arthur/discovery.yaml")
