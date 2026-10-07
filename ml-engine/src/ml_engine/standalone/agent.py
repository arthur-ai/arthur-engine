"""The standalone engine's main loop: scan every configured source on an interval.

The counterpart of `JobAgent`. Where that one polls the Platform for jobs, this one
owns the schedule: each (source, config) pair is due once at startup -- or one interval
in, without `run_on_start` -- and again one interval after each run starts. A run still
going when its next one falls due is not doubled up; the next starts when it ends.

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
from types import FrameType
from typing import Callable, Optional

from health_check import MLEngineHealthCheck as HealthCheck
from standalone.discovery_config import ResolvedScan, StandaloneDiscoveryConfig
from standalone.scan import run_scan, scan_logger
from standalone.sinks.common import Sink

logger = logging.getLogger(__name__)

# How often the loop looks for a due scan. A scan runs for minutes and recurs over
# hours, so a second's slack in starting one costs nothing.
TICK_SECONDS = 1.0
# How long shutdown waits for running scans, matching JobAgent's.
SHUTDOWN_GRACE_SECONDS = 15.0

# Runs one scan to completion and never raises: (scan, its logger, should_stop).
ScanRunner = Callable[[ResolvedScan, logging.Logger, Callable[[], bool]], object]


@dataclass
class _Slot:
    """One (source, config) pair's place in the schedule."""

    scan: ResolvedScan
    logger: logging.Logger
    next_due: float
    thread: Optional[threading.Thread] = field(default=None, repr=False)

    def running(self) -> bool:
        return self.thread is not None and self.thread.is_alive()


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
    ) -> None:
        self._config = config
        self._sink = sink
        self._interval = config.schedule.interval.total_seconds()
        self._capacity = config.schedule.max_concurrent_scans
        self._clock = clock
        self._stopping = threading.Event()
        self._runner = runner or self._run_scan
        self.health_check = health_check or HealthCheck()
        now = clock()
        first_due = now if config.schedule.run_on_start else now + self._interval
        self._slots = [
            _Slot(scan=scan, logger=scan_logger(scan, sink), next_due=first_due)
            for scan in config.scans()
        ]

    def run(self) -> None:
        """Scan on schedule until SIGTERM or SIGINT, then drain and return."""
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)
        self.health_check.start_server()
        logger.info(
            f"Standalone discovery: {len(self._slots)} scan(s) every "
            f"{self._config.schedule.interval}, at most {self._capacity} at once, "
            f"sending to {self._config.destination.type}",
        )
        while not self._stopping.is_set():
            try:
                self.tick()
            except Exception:
                # One bad iteration must not end the engine, as in JobAgent's loop.
                logger.error(
                    "Unexpected error in the scan loop; continuing", exc_info=True
                )
            self.health_check.liveness_ping()
            self._stopping.wait(TICK_SECONDS)
        self._drain()

    def request_stop(self) -> None:
        """Start a graceful shutdown: no new scans, and running ones told to stop."""
        self._stopping.set()

    def tick(self) -> None:
        """Start every due scan there is room for, most overdue first."""
        now = self._clock()
        room = self._capacity - sum(slot.running() for slot in self._slots)
        due = sorted(
            (s for s in self._slots if not s.running() and s.next_due <= now),
            key=lambda s: s.next_due,
        )
        for slot in due[: max(room, 0)]:
            slot.next_due = now + self._interval
            slot.thread = threading.Thread(
                target=self._run_slot,
                args=(slot,),
                name=f"scan:{slot.scan.source_name}/{slot.scan.config.name}",
                daemon=True,
            )
            slot.thread.start()

    def running_scans(self) -> list[str]:
        return [
            f"{s.scan.source_name}/{s.scan.config.name}"
            for s in self._slots
            if s.running()
        ]

    def _run_slot(self, slot: _Slot) -> None:
        try:
            self._runner(slot.scan, slot.logger, self._stopping.is_set)
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
        deadline = self._clock() + grace_seconds
        for slot in self._slots:
            if slot.thread is not None:
                slot.thread.join(max(deadline - self._clock(), 0.0))
        abandoned = self.running_scans()
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
