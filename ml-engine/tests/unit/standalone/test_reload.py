"""A standalone engine picks up its config file's changes while it runs: sources at once,
everything else at the next restart, and a file it cannot use not at all."""

import textwrap
from pathlib import Path
from typing import Any

import pytest

from standalone.agent import RELOAD_CHECK_SECONDS, StandaloneDiscoveryAgent
from standalone.discovery_config import config_fingerprint, load_config
from tests.unit.standalone.test_agent import (
    Clock,
    FakeHealthCheck,
    FakeSink,
    HoldingRunner,
)


def source(name: str, project: str = "p", key_file: str = "") -> str:
    key = (
        f"\n      - {{key: service_account_key, value: {{file: {key_file}}}}}"
        if key_file
        else ""
    )
    return f"""
  - name: {name}
    vendor: gcp_vertex
    fields:
      - {{key: project_id, value: {project}}}{key}
    configs:
      - {{name: c, query: "", query_language: none, lookback_window_seconds: 86400}}"""


def config_text(*sources: str, interval: str = "1h", capacity: int = 4) -> str:
    return textwrap.dedent(f"""\
            version: 1
            schedule:
              interval: {interval}
              max_concurrent_scans: {capacity}
            destination:
              type: webhook
              url: https://hooks.example.com/in
            sources:""") + "".join(sources) + "\n"


@pytest.fixture
def runner() -> Any:
    holding = HoldingRunner()
    yield holding
    holding.release_all()


def start(path: Path, runner: HoldingRunner, clock: Clock) -> StandaloneDiscoveryAgent:
    config = load_config(path)
    assert config is not None
    subject = StandaloneDiscoveryAgent(
        config,
        FakeSink(),
        runner=runner,
        clock=clock,
        health_check=FakeHealthCheck(),  # type: ignore[arg-type]
        config_path=path,
    )
    subject.tick()
    return subject


def settle(subject: StandaloneDiscoveryAgent, clock: Clock) -> None:
    clock.now += RELOAD_CHECK_SECONDS
    subject.check_config()
    subject.tick()


def names(subject: StandaloneDiscoveryAgent) -> list[str]:
    return [slot.scan.source_name for slot in subject._slots]


def test_an_added_source_is_scanned_at_once(
    tmp_path: Path, runner: HoldingRunner
) -> None:
    path = tmp_path / "discovery.yaml"
    path.write_text(config_text(source("a")))
    clock = Clock()
    subject = start(path, runner, clock)
    runner.wait_for("a")
    assert runner.started == ["a"]

    path.write_text(config_text(source("a"), source("b")))
    settle(subject, clock)

    assert names(subject) == ["a", "b"]
    runner.wait_for("b")
    assert runner.started == ["a", "b"]  # a, still running, not doubled up
    assert subject.config_status().error is None


def test_asked_to_apply_the_file_an_added_source_starts_before_it_returns(
    tmp_path: Path, runner: HoldingRunner
) -> None:
    path = tmp_path / "discovery.yaml"
    path.write_text(config_text(source("a")))
    clock = Clock()
    subject = start(path, runner, clock)

    path.write_text(config_text(source("a"), source("b")))
    status, states = subject.apply_config_now()  # no time passes: no check is due

    runner.wait_for("a")
    runner.wait_for("b")
    assert runner.started == ["a", "b"]
    assert status.error is None
    assert {(s.source_name, s.status) for s in states} == {
        ("a", "running"),
        ("b", "running"),
    }


def test_asked_to_apply_an_unchanged_file_reloads_nothing(
    tmp_path: Path, runner: HoldingRunner, caplog: pytest.LogCaptureFixture
) -> None:
    path = tmp_path / "discovery.yaml"
    path.write_text(config_text(source("a")))
    clock = Clock()
    subject = start(path, runner, clock)
    loaded_at = subject.config_status().loaded_at

    subject.apply_config_now()

    assert subject.config_status().loaded_at == loaded_at
    assert "Reloaded" not in caplog.text


def test_asked_to_apply_a_file_it_cannot_use_says_why(
    tmp_path: Path, runner: HoldingRunner
) -> None:
    path = tmp_path / "discovery.yaml"
    path.write_text(config_text(source("a")))
    clock = Clock()
    subject = start(path, runner, clock)

    path.write_text(config_text(source("a"), source("a")))
    status, states = subject.apply_config_now()

    assert "used more than once" in (status.error or "")
    assert [s.source_name for s in states] == ["a"]


def test_a_changed_source_runs_again_with_the_change(
    tmp_path: Path, runner: HoldingRunner
) -> None:
    path = tmp_path / "discovery.yaml"
    path.write_text(config_text(source("a")))
    clock = Clock()
    subject = start(path, runner, clock)
    runner.release("a")
    subject._slots[0].thread.join(5)  # type: ignore[union-attr]

    path.write_text(config_text(source("a", project="other")))
    settle(subject, clock)

    runner.wait_for("a", runs=2)
    assert runner.started == ["a", "a"]
    assert subject._slots[0].scan.source_fields == {"project_id": "other"}


def test_a_removed_source_is_told_to_stop(
    tmp_path: Path, runner: HoldingRunner
) -> None:
    path = tmp_path / "discovery.yaml"
    path.write_text(config_text(source("a"), source("b")))
    clock = Clock()
    subject = start(path, runner, clock)

    runner.wait_for("a")
    runner.wait_for("b")
    path.write_text(config_text(source("a")))
    settle(subject, clock)

    assert names(subject) == ["a"]
    stops = dict(zip(runner.started, runner.stop_checks))
    assert stops["b"]() and not stops["a"]()


def retired_thread_ends(subject: StandaloneDiscoveryAgent) -> None:
    for slot in subject._retired:
        assert slot.thread is not None
        slot.thread.join(5)


def test_a_source_added_back_while_its_removed_scan_ends_waits_for_it(
    tmp_path: Path, runner: HoldingRunner
) -> None:
    path = tmp_path / "discovery.yaml"
    path.write_text(config_text(source("a"), source("b")))
    clock = Clock()
    subject = start(path, runner, clock)
    runner.wait_for("b")

    path.write_text(config_text(source("a")))
    settle(subject, clock)
    path.write_text(config_text(source("a"), source("b")))
    settle(subject, clock)

    # b's removed run hasn't reached a point where it can stop: not started again.
    assert runner.started.count("b") == 1
    assert ("b", "waiting") in {(s.source_name, s.status) for s in subject.scan_states()}

    runner.release("b")
    retired_thread_ends(subject)
    subject.tick()
    runner.wait_for("b", runs=2)


def test_a_removed_scan_still_ending_holds_its_slot(
    tmp_path: Path, runner: HoldingRunner
) -> None:
    path = tmp_path / "discovery.yaml"
    path.write_text(config_text(source("a"), capacity=1))
    clock = Clock()
    subject = start(path, runner, clock)
    runner.wait_for("a")

    path.write_text(config_text(source("b"), capacity=1))
    settle(subject, clock)

    assert runner.started == ["a"]  # b waits for the one slot a still holds

    runner.release("a")
    retired_thread_ends(subject)
    subject.tick()
    runner.wait_for("b")
    assert subject._retired == []


def test_a_changed_secret_file_counts_as_a_change(
    tmp_path: Path, runner: HoldingRunner
) -> None:
    (tmp_path / "key.json").write_text('{"k": 1}')
    path = tmp_path / "discovery.yaml"
    path.write_text(config_text(source("a", key_file="key.json")))
    before = config_fingerprint(path)

    (tmp_path / "key.json").write_text('{"k": 2}')

    assert config_fingerprint(path) != before


def test_a_changed_secret_file_named_through_a_variable_counts_as_a_change(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "key.json").write_text('{"k": 1}')
    monkeypatch.setenv("KEY_FILE", "key.json")
    path = tmp_path / "discovery.yaml"
    path.write_text(config_text(source("a", key_file='"${KEY_FILE}"')))
    before = config_fingerprint(path)

    (tmp_path / "key.json").write_text('{"k": 2}')

    assert config_fingerprint(path) != before


def test_fields_or_configs_that_are_not_lists_are_reported_not_raised(
    tmp_path: Path, runner: HoldingRunner
) -> None:
    path = tmp_path / "discovery.yaml"
    path.write_text(config_text(source("a")))
    clock = Clock()
    subject = start(path, runner, clock)

    broken_sources = (
        """
  - name: b
    vendor: gcp_vertex
    fields: 1
    configs: []""",
        """
  - name: b
    vendor: gcp_vertex
    fields: []
    configs: true""",
    )
    for broken in broken_sources:
        path.write_text(config_text(source("a"), broken))
        status, _ = subject.apply_config_now()

        assert status.error, broken
        assert names(subject) == ["a"]


def test_a_file_that_cannot_be_used_leaves_the_engine_as_it_was(
    tmp_path: Path, runner: HoldingRunner
) -> None:
    path = tmp_path / "discovery.yaml"
    path.write_text(config_text(source("a")))
    clock = Clock()
    subject = start(path, runner, clock)

    path.write_text(config_text(source("a"), source("a")))  # a name used twice
    settle(subject, clock)

    assert names(subject) == ["a"]
    assert "used more than once" in (subject.config_status().error or "")

    path.write_text(config_text(source("a"), source("b")))
    settle(subject, clock)
    assert names(subject) == ["a", "b"] and subject.config_status().error is None


def test_a_schedule_change_waits_for_a_restart(
    tmp_path: Path, runner: HoldingRunner
) -> None:
    path = tmp_path / "discovery.yaml"
    path.write_text(config_text(source("a")))
    clock = Clock()
    subject = start(path, runner, clock)

    path.write_text(config_text(source("a"), source("b"), interval="2h"))
    settle(subject, clock)

    assert subject.config_status().restart_required == ("schedule",)
    assert subject._interval == 3600  # unchanged
    assert names(subject) == ["a", "b"]  # sources applied anyway


def test_an_unchanged_file_is_not_reloaded(
    tmp_path: Path, runner: HoldingRunner
) -> None:
    path = tmp_path / "discovery.yaml"
    path.write_text(config_text(source("a")))
    clock = Clock()
    subject = start(path, runner, clock)
    loaded_at = subject.config_status().loaded_at

    settle(subject, clock)

    assert subject.config_status().loaded_at == loaded_at
