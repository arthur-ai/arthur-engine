"""Bitdefender GravityZone's side of a DISCOVER_AGENTS scan.

A PULL CARRIER. Jamf hands back an attribute each Mac already reported; GravityZone has no
attribute that can hold the `arthur1.` value, no scheduled script runner and no inventory
sorted by report date. So the scan lists the managed endpoints, and asks each online one
for its value: `startCommandExecutionOnEndpoint` runs `COMMAND`, which prints the file the
collector wrote, and `getInvestigationFileUrl` hands back the output to download. From
the value on, `discovery.endpoint.records` builds the records exactly as it does for Jamf.

THE COLLECTOR IS SCHEDULED BY THE CUSTOMER, NOT BY THIS SCAN. The collectors are 55 to 68 KB
and a command is capped at 10,000 characters, so the collector cannot travel inline;
fetching and running it from the scan would make every scan an unattended root download.
The customer schedules it (a LaunchDaemon, a systemd timer, a Windows scheduled task; see
`integrations/endpoint-ai-discovery/docs/mdm/gravityzone.md`), and the command only prints
the framed value it wrote: `/var/lib/arthur/inventory.ea`, or
`%ProgramData%\\Arthur\\inventory.ea` on Windows.

AN ENDPOINT THAT CANNOT ANSWER IS A GAP, NOT A FAILURE. Offline (reported so, or not picking
the command up within `PICKUP_TIMEOUT_SECONDS`), out of the lookback window, a command
refused, failed or still running at `COMMAND_TIMEOUT_SECONDS`, an output that cannot be
read: each is counted and listed in the run's device coverage under its own reason, and the
scan goes on.
A key GravityZone refuses (401) ends it, and so does a command refused on every endpoint it
was sent to, because that is the key or the licence, not the fleet.

EVERY RUN ENUMERATES THE WHOLE ROSTER. GravityZone cannot filter or sort on `lastSeen`, so
the lookback is applied to each endpoint's `lastSeen` after listing it.

BOUNDED: at most `MAX_IN_FLIGHT` commands run at once, a new one starting as each finishes,
and the client spaces every call under GravityZone's per-key rate limit. That limit sets
the wall time: at least four calls an endpoint (details, start, a poll, the download) at
eight a second is 1.4 hours for 10,000 endpoints, and about 2 hours measured against a fake
that needs two polls each; see the runbook.
"""

import logging
import re
import time
from dataclasses import dataclass, replace
from datetime import datetime, timedelta, timezone
from typing import Callable, ClassVar, Iterator, Mapping, Optional, Sequence

from arthur_client.api_bindings import DiscoverySourceConfigSpec
from arthur_common.models.agent_discovery_schemas import DiscoveredAgentRecord
from arthur_common.models.agent_governance_schemas import Platform

from discovery.address import address_problem
from discovery.catalog import Matcher
from discovery.endpoint.device import ManagedDevice
from discovery.endpoint.gravityzone.client import (
    INVESTIGATION,
    TIMED_OUT_ERROR_CODE,
    GravityZoneClient,
    GravityZoneError,
    GravityZoneSettings,
    output_texts,
)
from discovery.endpoint.records import records_for
from discovery.endpoint.scope import DeviceScope
from job_executors.discovery_scan import DeviceCoverage, DiscoveryConfigurationError

VENDOR = "bitdefender_gravityzone"

# Non-sensitive: the Control Center API access URL, from My Account > API keys.
ACCESS_URL_FIELD = "access_url"
# Sensitive: the API key.
API_KEY_FIELD = "api_key"

# Where `collect.sh` and `collect-linux.sh` write the framed value, and where
# `collect-windows.ps1` does, under %ProgramData%.
INVENTORY_PATH = "/var/lib/arthur/inventory.ea"
WINDOWS_INVENTORY_PATH = r"%ProgramData%\Arthur\inventory.ea"

# Read-only, and a constant: nothing from a source field is ever spliced into a command
# that runs as root. The markers are printed with `%s` so that the literal marker never
# appears in the command itself, in case the output echoes the command line. A missing
# file prints `no-cache`, the same sentinel a Jamf attribute script prints.
COMMAND = (
    "printf 'ARTHUR-%s\\n' BEGIN; "
    f"cat {INVENTORY_PATH} 2>/dev/null || printf 'no-cache'; "
    "printf '\\nARTHUR-%s\\n' END"
)
# The same, for Windows. GRAVITYZONE DOES NOT SAY WHICH SHELL RUNS A WINDOWS COMMAND, so this
# is written to mean the same in both: `cmd /c "..."` is cmd.exe's own syntax inside cmd,
# and a native call to cmd.exe from PowerShell. Inside it, `&` separates, `||` runs the
# fallback when `type` finds no file, `echo.` ends the value's line (the driver writes it
# with no newline), and %ProgramData% is expanded by cmd.exe either way. The markers do
# appear in this command, but each is followed by `&`, never by the line break the parser
# needs after ARTHUR-BEGIN, so an echoed command line is not read as output.
WINDOWS_COMMAND = (
    'cmd /c "echo ARTHUR-BEGIN& '
    f"(type {WINDOWS_INVENTORY_PATH} 2>nul || echo no-cache)& "
    'echo.& echo ARTHUR-END"'
)
_VALUE = re.compile(r"ARTHUR-BEGIN\r?\n(.*?)\r?\n?ARTHUR-END", re.DOTALL)

# The name the value is given as a ManagedDevice attribute. `records_for` finds the value
# by its prefix, never by this name.
OUTPUT_ATTRIBUTE = "GravityZone command output"

# A SLIDING WINDOW, NOT WAVES. Up to MAX_IN_FLIGHT commands run at once, and a new one starts
# as soon as one finishes, so an endpoint that never answers holds one slot, not a wave.
# Polling is paced by the budget it may spend, POLL_REQUESTS_PER_SECOND of the client's
# eight a second, which leaves the rest for listing, details, starts and downloads: a
# command is polled at most every max(MIN_POLL_INTERVAL_SECONDS, in-flight / budget)
# seconds, oldest-due first.
MAX_IN_FLIGHT = 100
POLL_REQUESTS_PER_SECOND = 4.0
MIN_POLL_INTERVAL_SECONDS = 5.0
# A task GravityZone still reports `pending` (assigned, not started) this long after it was
# started was not picked up: the endpoint is off or unreachable. Its slot goes to the next
# endpoint rather than waiting out the full timeout.
PICKUP_TIMEOUT_SECONDS = 90.0
# From the start of a command to giving up on its output. GravityZone has its own execution
# limit (a task past it fails with errorCode -99997, 77209-1565959), but does not publish
# its length.
COMMAND_TIMEOUT_SECONDS = 300.0

# Coverage reasons this carrier adds to the endpoint pipeline's own.
OFFLINE = "offline"
NOT_SEEN_IN_WINDOW = "not-seen-in-window"
COMMAND_REFUSED = "command-refused"
COMMAND_FAILED = "command-failed"
COMMAND_TIMED_OUT = "command-timed-out"
OUTPUT_UNREADABLE = "output-unreadable"

# getManagedEndpointDetails `state` (77211-128484): 1 online, 2 offline, 3 suspended,
# 0 unknown -- and 2 and 3 are returned only for endpoints in a virtualization integration,
# so a laptop that is off reads 0 or 1. Anything but 2 and 3 is tried, and the command's
# own outcome decides: a laptop that is off ends at PICKUP_TIMEOUT_SECONDS.
_OFFLINE_STATES = frozenset({2, 3})

_LINUX_NAMES = (
    "linux",
    "ubuntu",
    "debian",
    "red hat",
    "rhel",
    "centos",
    "fedora",
    "suse",
    "amazon",
    "oracle",
    "rocky",
    "alma",
)

ClientFactory = Callable[[GravityZoneSettings, logging.Logger], GravityZoneClient]


@dataclass
class _Running:
    device: ManagedDevice
    activity_id: str
    started_at: float
    next_poll_at: float


def command_for(device: ManagedDevice) -> str:
    """The command for this endpoint's OS. An OS GravityZone names in a way this does not
    recognise is asked as a POSIX one, which is what every non-Windows endpoint is."""
    return WINDOWS_COMMAND if device.platform is Platform.WINDOWS else COMMAND


class GravityZoneConnector:
    """Implements `job_executors.discovery_scan.DiscoverySourceConnector`,
    `ReportsDeviceCoverage` and `AcceptsStopCheck`.

    Holds one scan's coverage and stop check, which is safe only because a connector is
    built fresh for every scan -- see `DiscoveryConnectorFactory`.
    """

    SENSITIVE_FIELDS: ClassVar[frozenset[str]] = frozenset({API_KEY_FIELD})

    def __init__(
        self,
        client_factory: Optional[ClientFactory] = None,
        sleep: Callable[[float], None] = time.sleep,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._client_factory: ClientFactory = client_factory or (
            lambda settings, log: GravityZoneClient(settings, logger=log)
        )
        self._sleep = sleep
        self._clock = clock
        self._coverage: Optional[DeviceCoverage] = None
        self._should_stop: Callable[[], bool] = lambda: False
        self._stopped_early = False
        self._started = 0
        self._refused = 0
        self._last_refusal: Optional[GravityZoneError] = None

    def device_coverage(self) -> Optional[DeviceCoverage]:
        """None if the scan failed before reading an endpoint."""
        return self._coverage

    def stop_when(self, should_stop: Callable[[], bool]) -> None:
        """Asked after every endpoint listed and on every poll, so a stop never waits
        on a wave of commands to finish."""
        self._should_stop = should_stop

    def _stopping(self) -> bool:
        if self._should_stop():
            self._stopped_early = True
        return self._stopped_early

    def scan(
        self,
        config: DiscoverySourceConfigSpec,
        lookback_hours: int,
        credentials: Mapping[str, Optional[str]],
        source_fields: Mapping[str, str],
        logger: logging.Logger,
    ) -> Iterator[Sequence[DiscoveredAgentRecord]]:
        settings = _settings_from(credentials, source_fields)
        matcher = Matcher.from_source(catalog_json=config.query or None, logger=logger)
        client = self._client_factory(settings, logger)

        # Before anything runs on an endpoint, so a key without the Investigation API
        # fails as the key's fault, once, instead of as every endpoint's.
        apis = client.enabled_apis()
        if apis is not None and INVESTIGATION not in apis:
            raise GravityZoneError(
                "The GravityZone API key does not have the Investigation API enabled. "
                "Create a key with the Network and Investigation APIs.",
                status_code=403,
            )

        coverage = self._coverage = DeviceScope.everything().new_coverage()
        since = _since(lookback_hours)
        logger.info(
            "GravityZone scan starting against %s, catalog %s, %s agent(s), lookback "
            "%sh (applied to lastSeen; every run lists the whole roster)",
            settings.access_url,
            matcher.catalog_sha,
            matcher.agent_count,
            lookback_hours,
        )

        targets = self._targets(client, since, coverage)
        yield from self._run(client, targets, matcher, coverage, logger)

        if self._stopped_early:
            logger.info(
                "GravityZone scan stopped early on request after %s endpoint(s)",
                coverage.devices_read,
            )
        logger.info(
            "GravityZone scan read %s endpoint(s): %s decoded, %s unreadable %s",
            coverage.devices_read,
            coverage.devices_decoded,
            coverage.devices_unreadable,
            dict(sorted(coverage.unreadable_by_reason.items())),
        )

        if self._refused and not self._started and self._last_refusal is not None:
            # Refused on every endpoint is the key, the role or the licence: failing the
            # scan says so, where a coverage list of refusals would read as the fleet.
            raise GravityZoneError(
                f"GravityZone refused the discovery command on all {self._refused} "
                f"endpoint(s) it was sent to ({self._last_refusal}). The API key needs "
                "the Investigation API; its user needs the Manage Networks and Advanced "
                "Investigation rights; the company needs EDR or XDR with the Remote "
                "Shell add-on and must not be partner-managed; and the endpoints' "
                "policy needs Remote Shell connection enabled (General > Agent > "
                "Communication).",
                status_code=self._last_refusal.status_code,
            ) from self._last_refusal

        if coverage.devices_in_scope and not coverage.devices_decoded:
            logger.warning(
                "GravityZone scan decoded 0 of %s endpoint(s). This reads as a clean "
                "fleet and is almost never one: the collector may not be installed or "
                "scheduled, the endpoints may be offline, or Remote Shell may not be "
                "enabled on them. The run's device coverage lists each by reason.",
                coverage.devices_in_scope,
            )

    def _targets(
        self,
        client: GravityZoneClient,
        since: Optional[datetime],
        coverage: DeviceCoverage,
    ) -> Iterator[ManagedDevice]:
        """Every listed endpoint that is sent a command; the rest are counted as gaps."""
        for item in client.endpoints():
            device, state = _device(item, client.endpoint_details(str(item["id"])))
            coverage.devices_read += 1
            coverage.devices_in_scope += 1
            reason = _skip_reason(device, state, since)
            if reason is not None:
                coverage.count_unreadable(reason, device.unreadable(reason))
            else:
                yield device
            if self._stopping():
                return

    def _poll_interval(self, in_flight: int) -> float:
        return max(MIN_POLL_INTERVAL_SECONDS, in_flight / POLL_REQUESTS_PER_SECOND)

    def _run(
        self,
        client: GravityZoneClient,
        targets: Iterator[ManagedDevice],
        matcher: Matcher,
        coverage: DeviceCoverage,
        logger: logging.Logger,
    ) -> Iterator[Sequence[DiscoveredAgentRecord]]:
        """Keep up to MAX_IN_FLIGHT commands running, polling the one most overdue.

        A slot is refilled before every poll, so a finished command is replaced at once and
        a stuck one delays nothing but its own slot.
        """
        running: list[_Running] = []
        exhausted = False
        while True:
            while not exhausted and len(running) < MAX_IN_FLIGHT:
                device = next(targets, None)
                if device is None or self._stopping():
                    exhausted = True
                    break
                job = self._start(client, device, coverage, logger, len(running))
                if job is not None:
                    running.append(job)
            if not running or self._stopping():
                return
            job = min(running, key=lambda j: j.next_poll_at)
            wait = job.next_poll_at - self._clock()
            if wait > 0:
                self._sleep(wait)
            if self._stopping():
                return
            reason, value = self._poll(client, job, logger)
            if reason is None and value is None:
                job.next_poll_at = self._clock() + self._poll_interval(len(running))
                continue
            running.remove(job)
            if reason is not None:
                coverage.count_unreadable(reason, job.device.unreadable(reason))
                continue
            device = replace(job.device, attributes={OUTPUT_ATTRIBUTE: value})
            read = records_for(device, matcher, VENDOR, logger)
            if read.unreadable is not None:
                coverage.count_unreadable(
                    read.unreadable.value,
                    device.unreadable(read.unreadable.value),
                )
                continue
            coverage.devices_decoded += 1
            if read.records:
                yield read.records

    def _start(
        self,
        client: GravityZoneClient,
        device: ManagedDevice,
        coverage: DeviceCoverage,
        logger: logging.Logger,
        in_flight: int,
    ) -> Optional[_Running]:
        try:
            activity = client.start_command(device.device_key, command_for(device))
        except GravityZoneError as exc:
            if exc.status_code == 401:
                raise
            self._refused += 1
            self._last_refusal = exc
            logger.warning("%s: command not started (%s)", device.device_key, exc)
            coverage.count_unreadable(
                COMMAND_REFUSED, device.unreadable(COMMAND_REFUSED)
            )
            return None
        self._started += 1
        now = self._clock()
        return _Running(device, activity, now, now + self._poll_interval(in_flight + 1))

    def _poll(
        self,
        client: GravityZoneClient,
        job: _Running,
        logger: logging.Logger,
    ) -> tuple[Optional[str], Optional[str]]:
        """(reason, None) for a gap, (None, value) for an output, (None, None) to wait.

        Never logs the value: it is the device's whole inventory.
        """
        key = job.device.device_key
        try:
            output = client.command_output(key, job.activity_id)
        except GravityZoneError as exc:
            if exc.status_code == 401:
                raise
            logger.warning("%s: command output not available (%s)", key, exc)
            return COMMAND_FAILED, None
        if output.state == "failed":
            logger.warning(
                "%s: GravityZone reports the command failed (errorCode %s)",
                key,
                output.error_code,
            )
            if output.error_code == TIMED_OUT_ERROR_CODE:
                return COMMAND_TIMED_OUT, None
            return COMMAND_FAILED, None
        if output.state != "done" or output.url is None:
            elapsed = self._clock() - job.started_at
            if not output.picked_up and elapsed >= PICKUP_TIMEOUT_SECONDS:
                logger.warning(
                    "%s: command not picked up after %.0fs; the endpoint is off or "
                    "unreachable",
                    key,
                    PICKUP_TIMEOUT_SECONDS,
                )
                return OFFLINE, None
            if elapsed >= COMMAND_TIMEOUT_SECONDS:
                logger.warning(
                    "%s: no command output after %.0fs",
                    key,
                    COMMAND_TIMEOUT_SECONDS,
                )
                return COMMAND_TIMED_OUT, None
            return None, None
        try:
            texts = list(output_texts(client.download(output.url)))
        except GravityZoneError as exc:
            if exc.status_code == 401:
                raise
            logger.warning("%s: command output not downloaded (%s)", key, exc)
            return OUTPUT_UNREADABLE, None
        value = command_value(texts)
        if value is None:
            logger.warning(
                "%s: command output carries no ARTHUR-BEGIN/ARTHUR-END block",
                key,
            )
            return OUTPUT_UNREADABLE, None
        return None, value


def command_value(texts: Sequence[str]) -> Optional[str]:
    """What `COMMAND` printed between its markers, from whichever text holds it."""
    for text in texts:
        match = _VALUE.search(text)
        if match:
            return match.group(1).strip()
    return None


def _device(
    item: Mapping[str, object],
    details: Mapping[str, object],
) -> tuple[ManagedDevice, Optional[int]]:
    """One endpoint as the pipeline's device, and its GravityZone state."""
    merged = {**item, **details}
    os_name = str(
        merged.get("operatingSystem") or merged.get("operatingSystemVersion") or ""
    )
    group = merged.get("group")
    group_id = group.get("id") if isinstance(group, dict) else merged.get("groupId")
    group_name = group.get("name") if isinstance(group, dict) else None
    state = merged.get("state")
    return (
        ManagedDevice(
            # The 24-hex endpoint id GravityZone addresses commands to. Its stability
            # across an agent reinstall is unverified.
            device_key=str(item["id"]),
            last_reported=_iso(merged.get("lastSeen")),
            name=_text(merged.get("name")),
            group=_text(group_name),
            os_version=os_name or None,
            platform=_platform(os_name),
            group_ids=frozenset({str(group_id)}) if group_id else frozenset(),
        ),
        state if isinstance(state, int) else None,
    )


def _skip_reason(
    device: ManagedDevice,
    state: Optional[int],
    since: Optional[datetime],
) -> Optional[str]:
    """Why no command is sent to this endpoint, or None to send one."""
    if since is not None and device.last_reported:
        seen = _parse(device.last_reported)
        if seen is not None and seen < since:
            return NOT_SEEN_IN_WINDOW
    if state in _OFFLINE_STATES:
        return OFFLINE
    return None


def _platform(os_name: str) -> Optional[Platform]:
    lowered = os_name.lower()
    if "windows" in lowered:
        return Platform.WINDOWS
    if "mac" in lowered or "os x" in lowered or "darwin" in lowered:
        return Platform.DARWIN
    if any(name in lowered for name in _LINUX_NAMES):
        return Platform.LINUX
    return None


def _text(value: object) -> Optional[str]:
    return str(value) if value else None


def _parse(value: str) -> Optional[datetime]:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def _iso(value: object) -> Optional[str]:
    """`lastSeen` as UTC ISO 8601; GravityZone's own form when it cannot be parsed."""
    if not value:
        return None
    parsed = _parse(str(value))
    if parsed is None:
        return str(value)
    return parsed.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _since(lookback_hours: int) -> Optional[datetime]:
    """The oldest `lastSeen` a scan sends a command to; None for every endpoint."""
    if lookback_hours <= 0:
        return None
    return datetime.now(timezone.utc) - timedelta(hours=lookback_hours)


def _settings_from(
    credentials: Mapping[str, Optional[str]],
    source_fields: Mapping[str, str],
) -> GravityZoneSettings:
    """The access URL from the source's fields, the key from its secrets.

    `access_url` is not a secret, so a failure can name the host that did not answer.
    """
    access_url = (source_fields.get(ACCESS_URL_FIELD) or "").strip()
    api_key = (credentials.get(API_KEY_FIELD) or "").strip()
    missing = [
        name
        for name, value in ((ACCESS_URL_FIELD, access_url), (API_KEY_FIELD, api_key))
        if not value
    ]
    if missing:
        raise DiscoveryConfigurationError(
            f"GravityZone source is missing required field(s): {', '.join(missing)}. "
            f"{ACCESS_URL_FIELD} is a source field; {API_KEY_FIELD} is a secret.",
        )
    if not access_url.lower().startswith("https://"):
        # The key travels in every request's Authorization header.
        raise DiscoveryConfigurationError(
            f"GravityZone access_url must be https, got "
            f"{access_url.split('://', 1)[0] or access_url!r}. Every request carries "
            "the API key.",
        )
    problem = address_problem(access_url)
    if problem:
        raise DiscoveryConfigurationError(f"GravityZone access_url {problem}.")
    return GravityZoneSettings(access_url=access_url, api_key=api_key)
