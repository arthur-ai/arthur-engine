"""Which engine `job_agent.main` starts: standalone from a config file, or the Platform's."""

import textwrap
from pathlib import Path
from typing import Any

import pytest

import job_agent
from standalone.discovery_config import DISCOVERY_CONFIG_ENV_VAR
from standalone.sinks.webhook import WebhookSink

ENABLED = """
version: 1
schedule: {interval: 6h}
sources:
  - name: vertex
    vendor: gcp_vertex
    fields: [{key: project_id, value: p}]
    configs:
      - {name: c, query: "", query_language: none, lookback_window_seconds: 86400}
destination: {type: webhook, url: "https://hooks.example.com/in"}
"""


class Started:
    def __init__(self) -> None:
        self.engines: list[str] = []
        self.config: Any = None
        self.sink: Any = None


@pytest.fixture
def started(monkeypatch: pytest.MonkeyPatch) -> Started:
    record = Started()

    class FakeJobAgent:
        def run(self) -> None:
            record.engines.append("platform")

    class FakeStandaloneAgent:
        def __init__(self, config: Any, sink: Any) -> None:
            record.config = config
            record.sink = sink

        def run(self) -> None:
            record.engines.append("standalone")

    monkeypatch.setattr(job_agent, "JobAgent", FakeJobAgent)
    monkeypatch.setattr(job_agent, "StandaloneDiscoveryAgent", FakeStandaloneAgent)
    return record


def point_at(monkeypatch: pytest.MonkeyPatch, path: Path, text: str) -> None:
    path.write_text(textwrap.dedent(text))
    monkeypatch.setenv(DISCOVERY_CONFIG_ENV_VAR, str(path))


def test_no_config_polls_the_platform(
    monkeypatch: pytest.MonkeyPatch,
    started: Started,
) -> None:
    monkeypatch.delenv(DISCOVERY_CONFIG_ENV_VAR, raising=False)

    job_agent.main()

    assert started.engines == ["platform"]


def test_an_enabled_config_runs_standalone(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    started: Started,
) -> None:
    point_at(monkeypatch, tmp_path / "discovery.yaml", ENABLED)

    job_agent.main()

    assert started.engines == ["standalone"]
    assert started.config.sources[0].name == "vertex"
    # Built once from the config's destination, before the agent starts.
    assert isinstance(started.sink, WebhookSink)


def test_a_disabled_config_polls_the_platform(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    started: Started,
) -> None:
    point_at(monkeypatch, tmp_path / "discovery.yaml", "version: 1\nenabled: false\n")

    job_agent.main()

    assert started.engines == ["platform"]


def test_an_unusable_config_stops_the_engine_with_its_reason(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    started: Started,
) -> None:
    point_at(monkeypatch, tmp_path / "discovery.yaml", "version: 1\nschedule: {}\n")

    with pytest.raises(SystemExit) as e:
        job_agent.main()

    assert "is invalid" in str(e.value) and "schedule.interval" in str(e.value)
    assert started.engines == []
