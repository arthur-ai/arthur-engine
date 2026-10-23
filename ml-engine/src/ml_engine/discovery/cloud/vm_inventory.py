"""What a cloud does with one of its VMs once it has read the VM's inventory values.

Shared by every cloud whose VMs carry the endpoint collector's payload -- Compute Engine,
EC2. Each provider lists its own machines and reads its own transport; once a VM's values
are `ManagedDevice.attributes`, deciding whether they are current, decoding them and
counting what was read is the same on every cloud, and lives here.

THE STATUS LINE IS THE REPORT DATE. Neither cloud records when the collector last wrote:
a stopped VM keeps serving its last values, and so does one whose transport was turned
off after it reported. The collector's status line dates the last scan that succeeded,
and the reporter appends `failed=<UTC>` to a run that did not, so the newer of the two is
when the VM last reported. A VM that has not reported within the lookback is counted as
`not-reported-in-window` and not published -- what Jamf's report-date filter does by
leaving the Mac out. Publishing it again would keep its agents fresh on the Platform,
which dates evidence by when a scan last handed it over, not by `last_seen`. A VM still
reporting but failing keeps publishing its last good scan, as a Jamf Mac does. Records
are dated by the scan inside the payload, never by the read.

A DATE IN THE FUTURE IS THE VM'S CLOCK, NOT ITS REPORT. The status line is the VM's to
write, by the VM's clock, and the window only bounds it from below: a VM whose clock runs
ahead stays inside the lookback that much longer after it stops writing. Discovery comes
first, so it is still published, with no record dated past the scan's own clock. A date
more than `CLOCK_AHEAD_MARGIN` past that clock, read when the VM is, is logged with the
VM's id and how far ahead it is, so someone fixes its time sync.
"""

import logging
import re
from collections import Counter
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from typing import Callable, Mapping, Optional

from arthur_common.models.agent_discovery_schemas import DiscoveredAgentRecord
from arthur_common.models.agent_governance_schemas import CloudAgentCreationSource

from discovery.catalog import Matcher
from discovery.endpoint.device import ManagedDevice
from discovery.endpoint.records import records_for
from discovery.endpoint.scope import DeviceScope, parse_group_names
from job_executors.discovery_scan import DeviceCoverage, DiscoveryConfigurationError

# Device coverage reasons every VM-carrying cloud produces, beside the payload's own.
READ_FAILED = "read-failed"
NOT_REPORTED_IN_WINDOW = "not-reported-in-window"

# How far past this scan's own clock a VM's date may be before it is named: the drift of
# a clock that is merely fast, not one whose time sync is broken.
CLOCK_AHEAD_MARGIN = timedelta(minutes=15)

# The collector's reporter publishes the status line under this name on every cloud.
STATUS_ATTRIBUTE = "arthur/status"

# A timestamp on the status line: its own, and the reporter's `failed=<UTC>`.
_STATUS_TIMESTAMP = re.compile(r"\b(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z)")


class VmInventoryReader:
    """Decodes one scan's VMs and tallies what it read.

    Holds the scan's coverage, plus two counts `DeviceCoverage` has no field for: the
    VMs that were not running, by the provider's state, and the VMs whose latest run
    failed. Both count only VMs that reported within the window -- the summaries speak
    for those VMs' values, and say nothing true about one left out.
    """

    def __init__(
        self,
        coverage: DeviceCoverage,
        matcher: Matcher,
        vendor: str,
        since: Optional[datetime],
        logger: logging.Logger,
        *,
        clock: Callable[[], datetime],
    ) -> None:
        """`clock` is the scan's own, the one `since` was taken from. It is read again for
        each VM: a long scan's window starts when the scan does, but a VM that reported
        while it ran is dated after that, and is not ahead."""
        self.coverage = coverage
        self._matcher = matcher
        self._vendor = vendor
        self._since = since
        self._clock = clock
        self._log = logger
        self.not_running: Counter[str] = Counter()
        self.failed_runs: Counter[str] = Counter()

    def read(
        self,
        device: ManagedDevice,
        state: Optional[str],
    ) -> list[DiscoveredAgentRecord]:
        """The VM's records, or none, with the VM counted either way.

        `device` carries the VM's values as attributes. `state` is the provider's state
        for a VM that was not running when listed, None for one that was.
        """
        coverage = self.coverage
        # After the VM's values were read, so nothing it wrote before then is ahead.
        now = self._clock()
        status = device.attribute(STATUS_ATTRIBUTE)
        reported = last_reported(status)
        if reported is not None:
            device = replace(device, last_reported=reported.isoformat())
        if before(reported, self._since):
            coverage.count_unreadable(
                NOT_REPORTED_IN_WINDOW,
                device.unreadable(NOT_REPORTED_IN_WINDOW),
            )
            return []
        read = records_for(
            device,
            self._matcher,
            self._vendor,
            self._log,
            source_type=CloudAgentCreationSource,
        )
        dated = reported
        if reported is None and read.last_seen is not None:
            # No status line to date the VM by, so its payload's own scan does, whether
            # or not anything in it matched.
            dated = read.last_seen
            if before(dated, self._since):
                coverage.count_unreadable(
                    NOT_REPORTED_IN_WINDOW,
                    device.unreadable(NOT_REPORTED_IN_WINDOW),
                )
                return []
        if dated is not None and ahead(dated, now):
            self._warn_clock_ahead(device, dated, now)

        if state is not None:
            self.not_running[state or "UNKNOWN"] += 1
        self.failed_runs.update(failed_run(status))
        if read.unreadable is not None:
            coverage.count_unreadable(
                read.unreadable.value,
                device.unreadable(read.unreadable.value),
            )
            return []
        coverage.devices_decoded += 1
        # No VM can have seen anything after this scan's clock.
        return [
            record.model_copy(update={"last_seen": min(record.last_seen, now)})
            for record in read.records
        ]

    def _warn_clock_ahead(
        self,
        device: ManagedDevice,
        when: datetime,
        now: datetime,
    ) -> None:
        """Name the VM and its skew. The id and the skew only: never the value the date
        came from."""
        self._log.warning(
            "%s is dated %s min ahead of this scan's clock, so its clock is at least "
            "that fast. Published, with its records dated no later than this scan; "
            "until its time sync is fixed, its last values stay current that much "
            "longer once it stops reporting.",
            device.device_key,
            int((when - now).total_seconds() // 60),
        )

    def log_summary(self, provider: str, noun: str, journal: str) -> None:
        """The counts, the VMs that were not running, and the runs that failed.

        `noun` is what the provider calls a VM, `journal` where the runbook says to
        read a VM's journal.
        """
        coverage = self.coverage
        self._log.info(
            "%s scan read %s %s(s): %s decoded, %s unreadable%s",
            provider,
            coverage.devices_read,
            noun,
            coverage.devices_decoded,
            coverage.devices_unreadable,
            breakdown(coverage.unreadable_by_reason),
        )
        if self.not_running:
            self._log.info(
                "%s scan: %s in-scope %s(s) were not running%s. Their values are from "
                "before they stopped, and their records are dated by the scan inside "
                "them, not by this read.",
                provider,
                sum(self.not_running.values()),
                noun,
                breakdown(self.not_running),
            )
        if self.failed_runs:
            self._log.warning(
                "%s scan: %s %s(s) report that their collector's latest run failed%s; "
                "their inventory is the last scan that succeeded. The journal on each "
                "%s says why (%s).",
                provider,
                self.failed_runs["failed"],
                noun,
                breakdown({k: v for k, v in self.failed_runs.items() if k != "failed"}),
                noun,
                journal,
            )


def parse_selectors(
    value: Optional[str],
    field: str,
    *,
    source: str,
    selector: str,
    key_ok: Callable[[str], bool],
    key_rule: str,
) -> tuple[str, ...]:
    """`key=value` pairs from a comma-separated source field, as `key=value` strings.

    Spaces around the key and the value are dropped. A pair without `=`, or with a key
    the provider could not have (`key_ok`), fails the scan: unlike a pair no VM carries,
    it can never match anything, and only a person can say what was meant. `selector`
    is what the provider calls one ("label", "tag") and `key_rule` says what a key may
    be, for the message.
    """
    selectors: list[str] = []
    bad: list[str] = []
    for part in parse_group_names(value):
        key, sep, pair_value = part.partition("=")
        key, pair_value = key.strip(), pair_value.strip()
        if not sep or not key_ok(key):
            bad.append(part)
            continue
        selectors.append(f"{key}={pair_value}")
    if bad:
        raise DiscoveryConfigurationError(
            f"{source}'s '{field}' has selector(s) that are not key=value {selector}s: "
            f"{', '.join(repr(b) for b in bad)}. {key_rule}",
        )
    return tuple(dict.fromkeys(selectors))


def last_reported(status: Optional[str]) -> Optional[datetime]:
    """When the VM last reported: the newest timestamp on its status line.

    The line's own timestamp dates the last scan that succeeded; `failed=<UTC>` dates a
    later run that did not. None for a line with neither, such as a bare `no-cache`.

    A stamp that is not a real time is skipped: the line is the VM's to write, and one
    VM's bad value must not end the scan.
    """
    newest: Optional[datetime] = None
    for stamp in _STATUS_TIMESTAMP.findall(status or ""):
        try:
            when = datetime.strptime(stamp, "%Y-%m-%dT%H:%M:%SZ")
        except ValueError:
            continue
        when = when.replace(tzinfo=timezone.utc)
        if newest is None or when > newest:
            newest = when
    return newest


def before(when: Optional[datetime], since: Optional[datetime]) -> bool:
    """Whether `when` falls before the window. Nothing to compare is never before it."""
    return when is not None and since is not None and when < since


def ahead(when: datetime, now: datetime) -> bool:
    """Whether `when` is later than `now` by more than a fast clock accounts for."""
    return when > now + CLOCK_AHEAD_MARGIN


def failed_run(status: Optional[str]) -> list[str]:
    """What a status line says about its collector's latest run, when that run failed.

    `ok 2026-10-12T12:58:28Z … failed=<UTC> osquery=absent` is a VM whose last good scan
    is still the inventory while its latest run failed. Returned as "failed" plus the
    named cause, for counting across the fleet.
    """
    tokens = (status or "").split()
    if not any(t.startswith("failed=") for t in tokens):
        return []
    causes = [
        t for t in tokens if t == "osquery=absent" or t.startswith("inventory=refused:")
    ]
    return ["failed", *causes]


def report_scope(
    scope: DeviceScope,
    coverage: DeviceCoverage,
    carried: set[str],
    stopped_early: bool,
    logger: logging.Logger,
    *,
    provider: str,
    noun: str,
    selector: str,
    fields: str,
) -> None:
    """The scope's counts, and any selector no VM read carries.

    `selector` is what the provider calls one ("label", "tag"), and `fields` names the
    source fields that set them, for the person who has to fix a selector.
    """
    if not scope.is_restricted:
        return
    logger.info(
        "%s scan scope kept %s of %s %s(s); excluded %s%s",
        provider,
        coverage.devices_in_scope,
        coverage.devices_read,
        noun,
        coverage.devices_excluded,
        breakdown(coverage.excluded_by_group),
    )
    if scope.include:
        logger.info(
            "%s scan scope: %s %s(s) carry none of the included %ss; in scope%s",
            provider,
            coverage.devices_outside_included_groups,
            noun,
            selector,
            breakdown(coverage.included_by_group),
        )
    unmatched = [
        pair
        for pair in (*scope.include.values(), *scope.exclude.values())
        if pair not in carried
    ]
    if unmatched and not stopped_early:
        logger.warning(
            "%s scan: no %s read carries %s selector(s) %s, so they matched nothing. "
            "If that is not intended, check the source's %s; %ss are matched exactly.",
            provider,
            noun,
            selector,
            ", ".join(unmatched),
            fields,
            selector,
        )
    if coverage.devices_read and not coverage.devices_in_scope:
        logger.warning(
            "%s scan left all %s %s(s) it read out of scope (%s). If that is not "
            "intended, check the source's %s.",
            provider,
            coverage.devices_read,
            noun,
            scope.describe(),
            fields,
        )


def breakdown(counts: Mapping[str, int]) -> str:
    """` (TERMINATED: 2, SUSPENDED: 1)`, or nothing when there is nothing to break down."""
    if not counts:
        return ""
    return " (" + ", ".join(f"{name}: {count}" for name, count in counts.items()) + ")"
