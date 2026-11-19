"""The standalone engine's main loop: scan every configured source on an interval.

The counterpart of `JobAgent`. Where that one polls the Platform for jobs, this one
owns the schedule: each (source, config) pair is due once at startup -- or one interval
in, without `run_on_start` -- and again one interval after each run starts. A run still
going when its next one falls due is not doubled up; the next starts when it ends.
A run past `scan_timeout` is told to stop and gives up its slot, so one source that
hangs cannot keep the others from running.

A SCAN CAN BE ASKED FOR AHEAD OF ITS TIME. `run_now` makes a pair due at once, and
`standalone.control` serves it over HTTP when the engine is given a control token. An
asked-for scan is an ordinary run: it waits for room like any other, a pair already
running is not started again, and its next run is one interval after it starts.

THE CONFIG FILE IS WATCHED. Every few seconds the loop checks it, and the files its
`{file: path}` references read, for a change. A changed file is loaded and validated
whole, as at startup; one that cannot be used is logged and reported to the control API,
and the engine keeps scanning with what it had. Sources are applied at once: a new
(source, config) pair is due now, a changed one is due now unless it is running (its
next run uses the change), and a removed one is told to stop. A change to `schedule`,
`destination` or `emit_scan_outcomes` needs a restart, and is reported as such rather
than half-applied.

SCANS RUN AS DAEMON THREADS, as a light job does under `JobAgent`. A scan is I/O
against a vendor and a destination, and a daemon thread is one the process can exit
past: on shutdown each scan is told to stop at its connector's next safe point and
given a grace period, and one that has not finished by then is left behind rather than
holding the container open until it is killed.
"""

import logging
import signal
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import FrameType
from typing import Callable, Literal, Optional

from health_check import MLEngineHealthCheck as HealthCheck
from standalone.control import ControlServer, control_from_env
from standalone.discovery_config import (
    ResolvedScan,
    StandaloneConfigError,
    StandaloneDiscoveryConfig,
    config_fingerprint,
    load_config,
)
from standalone.scan import run_scan, scan_logger
from standalone.sinks.common import Sink

logger = logging.getLogger(__name__)

# How often the loop looks for a due scan. A scan runs for minutes and recurs over
# hours, so a second's slack in starting one costs nothing.
TICK_SECONDS = 1.0
# How long shutdown waits for running scans, matching JobAgent's.
SHUTDOWN_GRACE_SECONDS = 15.0
# How often the loop looks for a changed config file: soon enough that a source added
# from a dashboard is scanned within seconds, cheap enough to do forever.
RELOAD_CHECK_SECONDS = 5.0
# What a reloaded config cannot change without a restart.
RESTART_ONLY = ("schedule", "destination", "emit_scan_outcomes")

# Runs one scan to completion and never raises: (scan, its logger, should_stop).
ScanRunner = Callable[[ResolvedScan, logging.Logger, Callable[[], bool]], object]


@dataclass
class _Slot:
    """One (source, config) pair's place in the schedule."""

    scan: ResolvedScan
    logger: logging.Logger
    next_due: float
    thread: Optional[threading.Thread] = field(default=None, repr=False)
    # When the current run passes scan_timeout, and the stop check it was handed.
    deadline: float = 0.0
    stop: threading.Event = field(default_factory=threading.Event, repr=False)
    timed_out: bool = False
    # When the current or last run started, on the wall clock, for `scan_states`.
    started_at: Optional[datetime] = None

    def alive(self) -> bool:
        return self.thread is not None and self.thread.is_alive()

    def running(self) -> bool:
        """Alive and still holding a slot: a run past its timeout gives its slot up."""
        return self.alive() and not self.timed_out


# running: holds a slot. stopping: past scan_timeout, told to stop, not yet ended.
# waiting: due, and waiting for room. scheduled: next due at `next_due_at`.
ScanStatus = Literal["running", "stopping", "waiting", "scheduled"]


@dataclass(frozen=True)
class ConfigStatus:
    """The config the engine runs, as the control server reports it."""

    path: Optional[str]
    loaded_at: datetime
    # Why the file as it is now could not be used, or None if it is what is running.
    error: Optional[str] = None
    # Sections changed in the file that take effect only when the engine restarts.
    restart_required: tuple[str, ...] = ()


@dataclass(frozen=True)
class ScanState:
    """Where one (source, config) pair stands in the schedule, as `run_now` and the
    control server report it."""

    source_id: str
    source_name: str
    vendor: str
    config_name: str
    status: ScanStatus
    last_started_at: Optional[datetime]
    next_due_at: Optional[datetime]


class StandaloneDiscoveryAgent:
    """Runs the config's scans on its schedule, all sending through one `sink`.

    The sink is built by the caller from the config's destination and handed in, so the
    agent neither knows which target it is nor builds one per scan. The agent owns it
    from then on, and closes it when it stops.
    """

    def __init__(
        self,
        config: StandaloneDiscoveryConfig,
        sink: Sink,
        runner: Optional[ScanRunner] = None,
        clock: Callable[[], float] = time.monotonic,
        health_check: Optional[HealthCheck] = None,
        control: Optional[ControlServer] = None,
        wall_clock: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
        config_path: Optional[Path] = None,
    ) -> None:
        self._config = config
        self._config_path = config_path
        self._sink = sink
        self._interval = config.schedule.interval.total_seconds()
        self._capacity = config.schedule.max_concurrent_scans
        self._scan_timeout = config.schedule.scan_timeout.total_seconds()
        self._clock = clock
        self._wall_clock = wall_clock
        # Held by the loop while it schedules, and by `run_now` and `scan_states`, which
        # the control server calls from its own threads.
        self._lock = threading.Lock()
        # Held while the config file is checked and reloaded, by the loop or by
        # `apply_config_now`, which the control server calls.
        self._reload_lock = threading.Lock()
        self._stopping = threading.Event()
        self._runner = runner or self._run_scan
        self.health_check = health_check or HealthCheck()
        self.control = control if control is not None else control_from_env(self)
        now = clock()
        first_due = now if config.schedule.run_on_start else now + self._interval
        self._slots = [
            _Slot(scan=scan, logger=scan_logger(scan, sink), next_due=first_due)
            for scan in config.scans()
        ]
        # Pairs removed from the config while running, kept until shutdown so it can
        # wait for them as for any other.
        self._retired: list[_Slot] = []
        self._fingerprint = config_fingerprint(config_path) if config_path else ""
        self._next_reload_check = now + RELOAD_CHECK_SECONDS
        self._config_status = ConfigStatus(
            path=str(config_path) if config_path else None,
            loaded_at=wall_clock(),
        )

    def run(self) -> None:
        """Scan on schedule until SIGTERM or SIGINT, then drain and return."""
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)
        self.health_check.start_server()
        if self.control is not None:
            self.control.start()
        logger.info(
            f"Standalone discovery: {len(self._slots)} scan(s) every "
            f"{self._config.schedule.interval}, at most {self._capacity} at once, "
            f"sending to {self._config.destination.type}",
        )
        while not self._stopping.is_set():
            try:
                self.check_config()
                self.tick()
            except Exception:
                # One bad iteration must not end the engine, as in JobAgent's loop.
                logger.error(
                    "Unexpected error in the scan loop; continuing", exc_info=True
                )
            self.health_check.liveness_ping()
            self._stopping.wait(TICK_SECONDS)
        self._drain()

    def check_config(self) -> None:
        """Reload the config file if it, or a file it reads, has changed."""
        if self._config_path is None or self._clock() < self._next_reload_check:
            return
        self._reload_if_changed()

    def apply_config_now(self) -> tuple[ConfigStatus, list[ScanState]]:
        """Reload the config file now if it has changed, and start every scan that is
        due and has room, rather than within the next check and tick. For a dashboard
        that has just written the file: a source it added is running, or waiting for a
        slot, by the time this returns."""
        if self._config_path is not None:
            self._reload_if_changed()
        self.tick()
        return self.config_status(), self.scan_states()

    def _reload_if_changed(self) -> None:
        # Held so the loop's check and a control request can't both see the change
        # and reload it twice.
        with self._reload_lock:
            assert self._config_path is not None
            self._next_reload_check = self._clock() + RELOAD_CHECK_SECONDS
            fingerprint = config_fingerprint(self._config_path)
            if fingerprint == self._fingerprint:
                return
            self._fingerprint = fingerprint
            self.reload()

    def reload(self) -> None:
        """Load the config file and apply its sources, or keep what is running and say
        why not."""
        assert self._config_path is not None
        loaded_at = self._config_status.loaded_at
        try:
            config = load_config(self._config_path)
        except StandaloneConfigError as e:
            logger.error(
                f"{e}\nStill scanning with the config loaded at "
                f"{loaded_at.isoformat()}.",
            )
            self._set_status(error=str(e))
            return
        if config is None:
            message = (
                f"Discovery config {self._config_path} says enabled: false, which "
                f"takes effect when the engine restarts"
            )
            logger.warning(message)
            self._set_status(error=message)
            return
        restart = tuple(
            name
            for name in RESTART_ONLY
            if getattr(config, name) != getattr(self._config, name)
        )
        if restart:
            logger.warning(
                f"Discovery config {self._config_path} changed {', '.join(restart)}, "
                f"which take(s) effect when the engine restarts; its sources are "
                f"applied now",
            )
        self._apply_sources(config)
        self._config_status = ConfigStatus(
            path=str(self._config_path),
            loaded_at=self._wall_clock(),
            restart_required=restart,
        )

    def config_status(self) -> ConfigStatus:
        return self._config_status

    def configured_scans(self) -> list[ResolvedScan]:
        with self._lock:
            return [slot.scan for slot in self._slots]

    def _set_status(self, error: Optional[str]) -> None:
        current = self._config_status
        self._config_status = ConfigStatus(
            path=current.path,
            loaded_at=current.loaded_at,
            error=error,
            restart_required=current.restart_required,
        )

    def _apply_sources(self, config: StandaloneDiscoveryConfig) -> None:
        with self._lock:
            now = self._clock()
            old = {s.scan.discovery_source_config_id: s for s in self._slots}
            slots: list[_Slot] = []
            added, changed = [], []
            for scan in config.scans():
                name = f"{scan.source_name}/{scan.config.name}"
                slot = old.pop(scan.discovery_source_config_id, None)
                if slot is None:
                    slot = _Slot(
                        scan=scan,
                        logger=scan_logger(scan, self._sink),
                        next_due=now,
                    )
                    added.append(name)
                elif slot.scan != scan:
                    slot.scan = scan
                    slot.logger = scan_logger(scan, self._sink)
                    if not slot.alive():
                        slot.next_due = min(slot.next_due, now)
                    changed.append(name)
                slots.append(slot)
            removed = list(old.values())
            for slot in removed:
                if slot.alive():
                    slot.stop.set()
                    self._retired.append(slot)
            self._slots = slots
            # Only the sources change; the rest waits for a restart.
            self._config = config.model_copy(
                update={name: getattr(self._config, name) for name in RESTART_ONLY},
            )
        gone = [f"{s.scan.source_name}/{s.scan.config.name}" for s in removed]
        logger.info(
            (
                f"Reloaded {self._config_path}: "
                + "; ".join(
                    f"{label} {', '.join(names)}"
                    for label, names in (
                        ("added", added),
                        ("changed", changed),
                        ("removed", gone),
                    )
                    if names
                )
                if added or changed or gone
                else f"Reloaded {self._config_path}: no source changed"
            ),
        )

    def request_stop(self) -> None:
        """Start a graceful shutdown: no new scans, and running ones told to stop."""
        self._stopping.set()

    def tick(self) -> None:
        """Time out overdue scans, then start every due scan there is room for, most
        overdue first. A pair whose last run is still alive -- timed out or not -- is
        never started again alongside it."""
        with self._lock:
            self._tick()

    def _tick(self) -> None:
        now = self._clock()
        for slot in self._slots:
            if slot.running() and now >= slot.deadline:
                self._time_out(slot)
        room = self._capacity - sum(slot.running() for slot in self._slots)
        due = sorted(
            (s for s in self._slots if not s.alive() and s.next_due <= now),
            key=lambda s: s.next_due,
        )
        for slot in due[: max(room, 0)]:
            slot.next_due = now + self._interval
            slot.deadline = now + self._scan_timeout
            slot.stop = threading.Event()
            slot.timed_out = False
            slot.started_at = self._wall_clock()
            slot.thread = threading.Thread(
                target=self._run_slot,
                args=(slot,),
                name=f"scan:{slot.scan.source_name}/{slot.scan.config.name}",
                daemon=True,
            )
            slot.thread.start()

    def run_now(
        self,
        source_id: str,
        config_name: Optional[str] = None,
    ) -> list[ScanState]:
        """Make the source's pairs -- or the one named -- due now, and say where each
        stands. A pair still running is left as it is. None match: an empty list."""
        with self._lock:
            now = self._clock()
            matched = [
                slot
                for slot in self._slots
                if slot.scan.config.discovery_source_id == source_id
                and (config_name is None or slot.scan.config.name == config_name)
            ]
            for slot in matched:
                if not slot.alive():
                    slot.next_due = min(slot.next_due, now)
            states = [self._state(slot, now) for slot in matched]
        for state in states:
            name = f"'{state.source_name}/{state.config_name}'"
            if state.status == "waiting":
                logger.info(f"Scan of {name} asked for; it starts when a slot is free")
            else:
                logger.info(
                    f"Scan of {name} asked for, but it is already {state.status}"
                )
        return states

    def scan_states(self) -> list[ScanState]:
        """Every pair, in config order."""
        with self._lock:
            now = self._clock()
            return [self._state(slot, now) for slot in self._slots]

    def _state(self, slot: _Slot, now: float) -> ScanState:
        status: ScanStatus
        if slot.running():
            status = "running"
        elif slot.alive():
            status = "stopping"
        elif slot.next_due <= now:
            status = "waiting"
        else:
            status = "scheduled"
        next_due_at = None
        if status in ("waiting", "scheduled"):
            next_due_at = self._wall_clock() + timedelta(
                seconds=max(slot.next_due - now, 0.0),
            )
        return ScanState(
            source_id=slot.scan.config.discovery_source_id,
            source_name=slot.scan.source_name,
            vendor=str(slot.scan.config.vendor),
            config_name=slot.scan.config.name,
            status=status,
            last_started_at=slot.started_at,
            next_due_at=next_due_at,
        )

    def running_scans(self) -> list[str]:
        return [
            f"{s.scan.source_name}/{s.scan.config.name}"
            for s in self._slots
            if s.running()
        ]

    def _time_out(self, slot: _Slot) -> None:
        slot.timed_out = True
        slot.stop.set()
        slot.logger.error(
            f"Scan of '{slot.scan.source_name}/{slot.scan.config.name}' has run longer "
            f"than scan_timeout ({self._config.schedule.scan_timeout}). It has been told "
            f"to stop and no longer holds a slot; it is not started again until it ends.",
        )

    def _run_slot(self, slot: _Slot) -> None:
        # This run's own event: the slot's is replaced when the pair next starts.
        stop = slot.stop

        def should_stop() -> bool:
            return self._stopping.is_set() or stop.is_set()

        try:
            self._runner(slot.scan, slot.logger, should_stop)
        except Exception:
            # run_scan never raises; this guards a runner that does, so the thread's
            # end is logged rather than printed by threading's default hook.
            slot.logger.error("Scan ended with an unexpected error", exc_info=True)

    def _run_scan(
        self,
        scan: ResolvedScan,
        scan_log: logging.Logger,
        should_stop: Callable[[], bool],
    ) -> object:
        return run_scan(
            scan,
            self._sink,
            self._config.emit_scan_outcomes,
            scan_log,
            should_stop,
        )

    def _signal_handler(self, signum: int, _: FrameType | None) -> None:
        logger.info(f"Received signal {signum}, initiating graceful shutdown...")
        self.request_stop()

    def _drain(self, grace_seconds: float = SHUTDOWN_GRACE_SECONDS) -> None:
        if self.control is not None:
            # Nothing can be asked for once no new scans will start.
            self.control.stop()
        deadline = self._clock() + grace_seconds
        for slot in [*self._slots, *self._retired]:
            if slot.thread is not None:
                slot.thread.join(max(deadline - self._clock(), 0.0))
        abandoned = [
            f"{s.scan.source_name}/{s.scan.config.name}"
            for s in [*self._slots, *self._retired]
            if s.alive()
        ]
        if abandoned:
            logger.warning(
                f"Shutting down with scan(s) still running: {', '.join(abandoned)}. "
                f"What they delivered so far stays delivered; their outcomes are not "
                f"reported.",
            )
        # Last, after every scan that will finish has: one still running is about to
        # be abandoned with the process, and anything it sends from here would fail.
        self._sink.close()
        logger.info("Standalone discovery stopped.")
