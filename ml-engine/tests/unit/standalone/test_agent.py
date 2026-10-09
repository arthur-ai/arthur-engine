"""The standalone scheduler, against a fake clock and a runner the test controls.

Each scan the agent starts blocks until the test releases it, so the tests can hold a
scan running across ticks -- which is where the scheduling rules matter: a running
scan is never doubled up, capacity is never exceeded, and shutdown waits only so long.
"""

import logging
import threading
from typing import Any, Callable

import pytest

from standalone.agent import StandaloneDiscoveryAgent
from standalone.discovery_config import ResolvedScan, StandaloneDiscoveryConfig

INTERVAL = 3600.0
SINK_SECRET = "s1nk-s3cret-0007"


def config(
    sources: int = 2,
    run_on_start: bool = True,
    max_concurrent_scans: int = 2,
    scan_timeout: str = "6h",
) -> StandaloneDiscoveryConfig:
    return StandaloneDiscoveryConfig.model_validate(
        {
            "version": 1,
            "schedule": {
                "interval": "1h",
                "run_on_start": run_on_start,
                "max_concurrent_scans": max_concurrent_scans,
                "scan_timeout": scan_timeout,
            },
            "sources": [
                {
                    "name": f"vertex-{n}",
                    "vendor": "gcp_vertex",
                    "fields": [{"key": "project_id", "value": f"p{n}"}],
                    "configs": [
                        {
                            "name": "c",
                            "query": "",
                            "query_language": "none",
                            "lookback_window_seconds": 86400,
                        },
                    ],
                }
                for n in range(sources)
            ],
            "destination": {"type": "webhook", "url": "https://hooks.example.com/in"},
        },
    )


class Clock:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now


class HoldingRunner:
    """Records each scan started, and holds it running until released."""

    def __init__(self) -> None:
        self.started: list[str] = []
        self.stop_checks: list[Callable[[], bool]] = []
        self._gates: dict[str, threading.Event] = {}
        self._lock = threading.Lock()

    def __call__(
        self,
        scan: ResolvedScan,
        logger: logging.Logger,
        should_stop: Callable[[], bool],
    ) -> None:
        gate = threading.Event()
        with self._lock:
            self.started.append(scan.source_name)
            self.stop_checks.append(should_stop)
            self._gates[scan.source_name] = gate
        gate.wait(5)

    def release(self, name: str) -> None:
        self._gates[name].set()

    def release_all(self) -> None:
        for gate in list(self._gates.values()):
            gate.set()


class FakeHealthCheck:
    def __init__(self) -> None:
        self.started = False
        self.pings = 0

    def start_server(self) -> None:
        self.started = True

    def liveness_ping(self) -> None:
        self.pings += 1


class FakeSink:
    """Implements `Sink`: the engine's one sink, which only its owner may close."""

    def __init__(self) -> None:
        self.closed = False

    def send(self, events: Any) -> None:
        pass

    def secrets(self) -> tuple[str, ...]:
        return (SINK_SECRET,)

    def close(self) -> None:
        self.closed = True


def agent(
    runner: Any,
    clock: Clock,
    sink: Any = None,
    **schedule: Any,
) -> StandaloneDiscoveryAgent:
    return StandaloneDiscoveryAgent(
        config(**schedule),
        sink or FakeSink(),
        runner=runner,
        clock=clock,
        health_check=FakeHealthCheck(),  # type: ignore[arg-type]
    )


def wait_until_idle(subject: StandaloneDiscoveryAgent) -> None:
    for slot in subject._slots:
        if slot.thread is not None:
            slot.thread.join(5)


@pytest.fixture
def runner() -> Any:
    holding = HoldingRunner()
    yield holding
    holding.release_all()


def test_every_scan_starts_at_once_with_run_on_start(runner: HoldingRunner) -> None:
    subject = agent(runner, Clock())

    subject.tick()

    assert sorted(subject.running_scans()) == ["vertex-0/c", "vertex-1/c"]


def test_without_run_on_start_the_first_scan_waits_an_interval(
    runner: HoldingRunner,
) -> None:
    clock = Clock()
    subject = agent(runner, clock, run_on_start=False)

    subject.tick()
    assert subject.running_scans() == []

    clock.now += INTERVAL
    subject.tick()
    assert len(subject.running_scans()) == 2


def test_scans_beyond_capacity_wait_for_a_free_slot(runner: HoldingRunner) -> None:
    subject = agent(runner, Clock(), max_concurrent_scans=1)

    subject.tick()
    assert runner.started == ["vertex-0"]
    subject.tick()
    assert runner.started == ["vertex-0"]  # still full

    runner.release("vertex-0")
    wait_until_idle(subject)
    subject.tick()
    assert runner.started == ["vertex-0", "vertex-1"]


def test_a_running_scan_is_not_started_again(runner: HoldingRunner) -> None:
    clock = Clock()
    subject = agent(runner, clock, sources=1)

    subject.tick()
    clock.now += 2 * INTERVAL  # overdue, but still running
    subject.tick()
    assert runner.started == ["vertex-0"]

    runner.release("vertex-0")
    wait_until_idle(subject)
    subject.tick()  # overdue and finished: starts right away
    assert runner.started == ["vertex-0", "vertex-0"]


def test_a_scan_past_its_timeout_is_told_to_stop_and_frees_its_slot(
    runner: HoldingRunner,
) -> None:
    clock = Clock()
    subject = agent(runner, clock, max_concurrent_scans=1, scan_timeout="1m")

    subject.tick()
    assert runner.started == ["vertex-0"]

    clock.now += 59
    subject.tick()
    assert runner.started == ["vertex-0"]  # not yet past the timeout
    assert runner.stop_checks[0]() is False

    clock.now += 1  # vertex-0 hangs past scan_timeout
    subject.tick()
    assert runner.stop_checks[0]() is True
    assert runner.started == ["vertex-0", "vertex-1"]
    assert runner.stop_checks[1]() is False
    assert subject.running_scans() == ["vertex-1/c"]


def test_a_timed_out_scan_is_not_started_again_until_it_ends(
    runner: HoldingRunner,
) -> None:
    clock = Clock()
    subject = agent(runner, clock, sources=1, scan_timeout="1m")

    subject.tick()
    clock.now += 2 * INTERVAL  # timed out, overdue, and its thread still alive
    subject.tick()
    subject.tick()
    assert runner.started == ["vertex-0"]

    runner.release("vertex-0")
    wait_until_idle(subject)
    subject.tick()
    assert runner.started == ["vertex-0", "vertex-0"]
    assert runner.stop_checks[1]() is False  # the new run has a fresh stop check


def test_shutdown_names_a_timed_out_scan_still_running(
    runner: HoldingRunner,
    caplog: pytest.LogCaptureFixture,
) -> None:
    clock = Clock()
    subject = agent(runner, clock, sources=1, scan_timeout="1m")
    subject.tick()
    clock.now += 61
    subject.tick()

    with caplog.at_level(logging.WARNING):
        subject._drain(grace_seconds=0.0)

    assert "still running: vertex-0/c" in caplog.text


def test_the_next_run_is_one_interval_after_the_last_started(
    runner: HoldingRunner,
) -> None:
    clock = Clock()
    subject = agent(runner, clock, sources=1)

    subject.tick()
    runner.release("vertex-0")
    wait_until_idle(subject)

    clock.now += INTERVAL - 1
    subject.tick()
    assert runner.started == ["vertex-0"]

    clock.now += 1
    subject.tick()
    assert runner.started == ["vertex-0", "vertex-0"]


def test_shutdown_tells_running_scans_to_stop(runner: HoldingRunner) -> None:
    subject = agent(runner, Clock(), sources=1)
    subject.tick()
    assert runner.stop_checks[0]() is False

    subject.request_stop()

    assert runner.stop_checks[0]() is True


def test_shutdown_waits_for_scans_only_as_long_as_the_grace_period(
    runner: HoldingRunner,
    caplog: pytest.LogCaptureFixture,
) -> None:
    subject = agent(runner, Clock(), sources=1)
    subject.tick()

    with caplog.at_level(logging.WARNING):
        subject._drain(grace_seconds=0.05)

    assert "still running: vertex-0/c" in caplog.text


def test_run_scans_until_asked_to_stop(monkeypatch: pytest.MonkeyPatch) -> None:
    handlers: dict[int, Any] = {}
    monkeypatch.setattr(
        "standalone.agent.signal.signal",
        lambda signum, handler: handlers.__setitem__(signum, handler),
    )
    started: list[str] = []

    def stop_after_one_scan(scan: ResolvedScan, *args: Any) -> None:
        started.append(scan.source_name)
        subject.request_stop()

    sink = FakeSink()
    subject = agent(stop_after_one_scan, Clock(), sink=sink, sources=1)
    subject.run()

    assert started == ["vertex-0"]
    health_check = subject.health_check
    assert health_check.started and health_check.pings >= 1  # type: ignore[attr-defined]
    assert len(handlers) == 2  # SIGTERM and SIGINT
    assert subject.running_scans() == []
    assert sink.closed  # once, when the engine stops


def test_every_scan_sends_through_the_one_sink(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    used: list[Any] = []
    monkeypatch.setattr(
        "standalone.agent.run_scan",
        lambda scan, sink, *args: used.append(sink),
    )
    sink = FakeSink()
    subject = StandaloneDiscoveryAgent(
        config(sources=2),
        sink,  # type: ignore[arg-type]
        clock=Clock(),
        health_check=FakeHealthCheck(),  # type: ignore[arg-type]
    )

    subject.tick()
    wait_until_idle(subject)

    assert used == [sink, sink]
    assert not sink.closed


def test_scan_loggers_scrub_the_sinks_secrets(
    caplog: pytest.LogCaptureFixture,
) -> None:
    loggers: list[logging.Logger] = []
    subject = agent(lambda scan, log, stop: loggers.append(log), Clock(), sources=1)

    subject.tick()
    wait_until_idle(subject)
    with caplog.at_level(logging.INFO):
        loggers[0].info(f"sending with {SINK_SECRET}")

    assert SINK_SECRET not in caplog.text and "[redacted]" in caplog.text
