"""Compute Engine's side of a DISCOVER_AGENTS scan.

A CLOUD SOURCE THAT READS A MACHINE'S INVENTORY. Compute Engine lists the VMs, and each
VM's guest attributes carry the same `arthur1.` payload a Jamf Extension Attribute does
(D-32, `integrations/endpoint-ai-discovery/docs/mdm/gce.md`). So the decoding, matching
and record shape are the endpoint pipeline's, `discovery.endpoint.records`, but the
records are `CloudAgentCreationSource`: the source class is the vendor's, and Compute
Engine is a cloud. What is left here is the vendor tag, reading this source's fields,
scoping by label, and the two things only Compute Engine has to say about a VM: where it
is, and whether it can report at all.

EVERY VM IS LISTED; THE LOOKBACK IS APPLIED TO ITS STATUS LINE. Nothing records when a
guest attribute was written, so there is no report date to page on, and a stopped VM, or
one whose collector's timer is gone, keeps serving its last values. The status line is
the report date instead: it dates the last scan that succeeded, and the reporter appends
`failed=<UTC>` to a run that did not, so the newer of the two is when the VM last
reported. A VM that has not reported within `lookback_hours` is counted as
`not-reported-in-window` and not published -- what Jamf's report-date filter does by
leaving the Mac out. Publishing it again would keep its agents fresh on the Platform,
which dates evidence by when a scan last handed it over, not by `last_seen`. A VM still
reporting but failing keeps publishing its last good scan, as a Jamf Mac does. Records
are dated by the scan inside the payload, never by this read.

GUEST ATTRIBUTES OFF IS NAMED, NOT READ. A VM whose `enable-guest-attributes` is not true
-- on the VM, or on its project when the VM does not say -- cannot have reported since it
was turned off, and what the API still serves for it is stale by construction. It is
counted as `guest-attributes-disabled` rather than decoded, so a fleet with the setting
off reads as a deployment fault and not as machines that stopped reporting.

LABELS STAND WHERE GROUPS DO. A selector is a `key=value` pair and is matched exactly;
`discovery.endpoint.scope` applies them with Jamf's rules, exclude winning. Unlike a
group name a label has no registry to resolve against, so a selector no VM carries is
reported with a count of zero and a warning rather than failing the scan.

ONE VM IS THE UNIT THAT CAN FAIL. A VM whose guest attributes cannot be read is reported
and skipped; a refused credential or a denied permission is not one VM's problem, and
ends the scan.
"""

import logging
import re
from collections import Counter
from dataclasses import dataclass, replace
from datetime import datetime, timedelta, timezone
from typing import Callable, ClassVar, Iterator, Mapping, Optional, Sequence

import google.auth
import requests
from arthur_client.api_bindings import DiscoverySourceConfigSpec
from arthur_common.models.agent_discovery_schemas import DiscoveredAgentRecord
from arthur_common.models.agent_governance_schemas import (
    CloudAgentCreationSource,
    Platform,
    RunsOn,
)
from google.auth.credentials import Credentials
from google.auth.exceptions import DefaultCredentialsError
from google.auth.transport.requests import AuthorizedSession

from discovery.catalog import Matcher
from discovery.cloud.gcp_compute_engine.client import (
    COMPUTE_READONLY_SCOPE,
    ComputeEngineClient,
    ComputeEngineError,
    Instance,
)
from discovery.endpoint.device import ManagedDevice
from discovery.endpoint.records import records_for
from discovery.endpoint.scope import DeviceScope, parse_group_names
from discovery.gcp_credentials import (
    SERVICE_ACCOUNT_KEY_FIELD,
    service_account_credentials,
)
from job_executors.discovery_scan import DeviceCoverage, DiscoveryConfigurationError

VENDOR = "gcp_compute_engine"

# Non-sensitive source fields.
PROJECT_IDS_FIELD = "project_ids"
INCLUDE_LABELS_FIELD = "include_labels"
EXCLUDE_LABELS_FIELD = "exclude_labels"

# Opt-in for Application Default Credentials when a source has no key, as Vertex has.
ALLOW_ADC_ENV_VAR = "ARTHUR_ENGINE_GCP_COMPUTE_ENGINE_ALLOW_ADC"

# Device coverage reasons only Compute Engine produces, beside the payload's own.
GUEST_ATTRIBUTES_DISABLED = "guest-attributes-disabled"
READ_FAILED = "read-failed"
NOT_REPORTED_IN_WINDOW = "not-reported-in-window"

# The collector's reporter writes the status line here (gce.md, section 05).
STATUS_ATTRIBUTE = "arthur/status"

# A timestamp on the status line: its own, and the reporter's `failed=<UTC>`.
_STATUS_TIMESTAMP = re.compile(r"\b(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z)")

# A project id, optionally domain-scoped (`example.com:my-project`). Checked because it
# is a path segment in every call.
_PROJECT_ID = re.compile(r"^(?:[a-z0-9.-]+:)?[a-z][a-z0-9-]{4,28}[a-z0-9]$")

# A Compute Engine label key. Values may be empty.
_LABEL_KEY = re.compile(r"^[a-z][a-z0-9_-]{0,62}$")


@dataclass(frozen=True)
class ComputeEngineSettings:
    project_ids: tuple[str, ...]
    include_labels: tuple[str, ...] = ()
    exclude_labels: tuple[str, ...] = ()


def authorized_session(credentials: Optional[Credentials]) -> requests.Session:
    """A requests session that signs every call, refreshing its token as it goes.

    None is the engine's Application Default Credentials, which the caller has already
    checked the engine opted in to.
    """
    if credentials is None:
        try:
            credentials, _ = google.auth.default(scopes=[COMPUTE_READONLY_SCOPE])
        except DefaultCredentialsError as e:
            raise DiscoveryConfigurationError(
                f"Compute Engine source has no '{SERVICE_ACCOUNT_KEY_FIELD}', and this "
                f"engine has no Application Default Credentials to use instead: {e}",
            ) from None
    return AuthorizedSession(credentials)  # type: ignore[no-untyped-call]


class ComputeEngineConnector:
    """Implements `job_executors.discovery_scan.DiscoverySourceConnector`,
    `ReportsDeviceCoverage` and `AcceptsStopCheck`.

    Holds one scan's coverage and stop check, which is safe only because a connector is
    built fresh for every scan -- see `DiscoveryConnectorFactory`.
    """

    SENSITIVE_FIELDS: ClassVar[frozenset[str]] = frozenset({SERVICE_ACCOUNT_KEY_FIELD})

    def __init__(
        self,
        session_for: Callable[
            [Optional[Credentials]],
            requests.Session,
        ] = authorized_session,
        clock: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
    ) -> None:
        self._session_for = session_for
        self._clock = clock
        self._coverage: Optional[DeviceCoverage] = None
        self._should_stop: Callable[[], bool] = lambda: False
        self._stopped_early = False

    def device_coverage(self) -> Optional[DeviceCoverage]:
        """None if the scan failed before reading a VM, including on its settings."""
        return self._coverage

    def stop_when(self, should_stop: Callable[[], bool]) -> None:
        """Asked after every VM, so a stop never waits on another page."""
        self._should_stop = should_stop

    def _until_stopped(self, instances: Iterator[Instance]) -> Iterator[Instance]:
        for instance in instances:
            yield instance
            if self._should_stop():
                self._stopped_early = True
                return

    def scan(
        self,
        config: DiscoverySourceConfigSpec,
        lookback_hours: int,
        credentials: Mapping[str, Optional[str]],
        source_fields: Mapping[str, str],
        logger: logging.Logger,
    ) -> Iterator[Sequence[DiscoveredAgentRecord]]:
        """`logger` is the JOB's, so what this reports reaches the Platform job log."""
        settings = settings_from(source_fields)
        google_credentials = service_account_credentials(
            credentials,
            source="Compute Engine source",
            allow_adc_env_var=ALLOW_ADC_ENV_VAR,
            scopes=[COMPUTE_READONLY_SCOPE],
        )
        matcher = Matcher.from_source(catalog_yaml=config.query or None, logger=logger)
        client = ComputeEngineClient(self._session_for(google_credentials), logger)

        # Label pairs are their own ids: nothing renames a label out from under a scan.
        scope = DeviceScope(
            include={pair: pair for pair in settings.include_labels},
            exclude={pair: pair for pair in settings.exclude_labels},
        )
        coverage = self._coverage = scope.new_coverage()
        # A lookback of zero or less is the whole roster, as on Jamf.
        since = (
            self._clock() - timedelta(hours=lookback_hours)
            if lookback_hours > 0
            else None
        )

        logger.info(
            "Compute Engine scan starting against project(s) %s, catalog %s, %s "
            "agent(s), scope: %s, using %s. Every VM is listed; %s.",
            ", ".join(settings.project_ids),
            matcher.catalog_sha,
            matcher.agent_count,
            scope.describe(),
            (
                "the source's service account key"
                if google_credentials is not None
                else "Application Default Credentials"
            ),
            (
                f"one whose status line shows no report in the last {lookback_hours}h "
                f"is counted and not published"
                if since is not None
                else "the lookback is 0, so every VM's last report is published"
            ),
        )

        carried: set[str] = set()
        not_running: Counter[str] = Counter()
        failed_runs: Counter[str] = Counter()
        project_flags: dict[str, Optional[str]] = {}

        for instance in self._until_stopped(
            _all_instances(client, settings.project_ids),
        ):
            device = _device_for(instance)
            carried.update(device.group_ids)
            if not scope.admit(device, coverage):
                continue

            flag = instance.guest_attributes_flag
            if flag is None:
                # Read only when a VM does not say, so a role without
                # compute.projects.get still scans a fleet that sets it per VM.
                if instance.project not in project_flags:
                    project_flags[instance.project] = (
                        client.project_guest_attributes_flag(instance.project)
                    )
                flag = project_flags[instance.project]
            if not _guest_attributes_on(flag):
                coverage.count_unreadable(GUEST_ATTRIBUTES_DISABLED)
                continue

            try:
                attributes = client.guest_attributes(instance)
            except ComputeEngineError as e:
                if e.status_code in (401, 403):
                    # The credential or its permission, not this VM: every VM behind it
                    # would fail the same way.
                    raise
                logger.warning(
                    "%s: guest attributes not read (%s)",
                    device.device_key,
                    e,
                )
                coverage.count_unreadable(READ_FAILED)
                continue

            device = replace(device, attributes=attributes or {})
            status = device.attribute(STATUS_ATTRIBUTE)
            reported = _last_reported(status)
            if reported is not None:
                device = replace(device, last_reported=reported.isoformat())
            if _before(reported, since):
                coverage.count_unreadable(NOT_REPORTED_IN_WINDOW)
                continue
            read = records_for(
                device,
                matcher,
                VENDOR,
                logger,
                source_type=CloudAgentCreationSource,
            )
            if (
                reported is None
                and read.records
                and _before(read.records[0].last_seen, since)
            ):
                # No status line to date the VM by, so its payload's own scan does.
                coverage.count_unreadable(NOT_REPORTED_IN_WINDOW)
                continue

            # Counted only for a VM that reported in the window: the summaries speak
            # for its values, and say nothing true about one left out.
            if instance.status != "RUNNING":
                not_running[instance.status or "UNKNOWN"] += 1
            failed_runs.update(_failed_run(status))
            if read.unreadable is not None:
                coverage.count_unreadable(read.unreadable.value)
                continue
            coverage.devices_decoded += 1
            if read.records:
                yield read.records

        if self._stopped_early:
            logger.info(
                "Compute Engine scan stopped early on request after %s VM(s)",
                coverage.devices_read,
            )

        logger.info(
            "Compute Engine scan read %s VM(s): %s decoded, %s unreadable%s",
            coverage.devices_read,
            coverage.devices_decoded,
            coverage.devices_unreadable,
            _breakdown(coverage.unreadable_by_reason),
        )
        _report_scope(scope, coverage, carried, self._stopped_early, logger)

        if not_running:
            logger.info(
                "Compute Engine scan: %s in-scope VM(s) were not running%s. Their values "
                "are from before they stopped, and their records are dated by the scan "
                "inside them, not by this read.",
                sum(not_running.values()),
                _breakdown(not_running),
            )
        if failed_runs:
            logger.warning(
                "Compute Engine scan: %s VM(s) report that their collector's latest run "
                "failed%s; their inventory is the last scan that succeeded. The journal "
                "on each VM says why (gce.md, section 06).",
                failed_runs["failed"],
                _breakdown({k: v for k, v in failed_runs.items() if k != "failed"}),
            )

        seen, reporting = coverage.devices_in_scope, coverage.devices_decoded
        if seen and not reporting:
            # A scan that read VMs and decoded none is not a fleet without agents. Not an
            # exception, as on Jamf: a fleet whose collector was rolled out an hour ago
            # is in this state legitimately.
            logger.warning(
                "Compute Engine scan decoded 0 of %s VM(s). This reads as a clean fleet "
                "and is almost never one: the collector may not be deployed (the "
                "runbook's OS policy targets VMs labelled arthur-ai-discovery=enabled), "
                "guest attributes may be off on the VMs or their project, the VMs may "
                "not have reported within the lookback window (stopped, or the "
                "collector's timer removed), or no VM has finished its first run, up to "
                "15 minutes after boot.",
                seen,
            )


def settings_from(source_fields: Mapping[str, str]) -> ComputeEngineSettings:
    """The projects and label scope from the source's non-sensitive fields."""
    projects = parse_group_names(source_fields.get(PROJECT_IDS_FIELD))
    if not projects:
        raise DiscoveryConfigurationError(
            f"Compute Engine source is missing required field '{PROJECT_IDS_FIELD}'. "
            f"It is a source field, not a secret.",
        )
    bad = [p for p in projects if not _PROJECT_ID.match(p)]
    if bad:
        raise DiscoveryConfigurationError(
            f"Compute Engine source's '{PROJECT_IDS_FIELD}' has value(s) that are not "
            f"GCP project IDs: {', '.join(repr(p) for p in bad)}. A project ID is 6 to "
            f"30 lowercase letters, digits and hyphens, not the project's name or "
            f"number.",
        )
    return ComputeEngineSettings(
        project_ids=projects,
        include_labels=parse_label_selectors(
            source_fields.get(INCLUDE_LABELS_FIELD),
            INCLUDE_LABELS_FIELD,
        ),
        exclude_labels=parse_label_selectors(
            source_fields.get(EXCLUDE_LABELS_FIELD),
            EXCLUDE_LABELS_FIELD,
        ),
    )


def parse_label_selectors(value: Optional[str], field: str) -> tuple[str, ...]:
    """`key=value` pairs from a comma-separated source field, as `key=value` strings.

    Spaces around the key and the value are dropped. A pair without `=`, or with a key
    Compute Engine could not have, fails the scan: unlike a pair no VM carries, it can
    never match anything, and only a person can say what was meant.
    """
    selectors: list[str] = []
    bad: list[str] = []
    for part in parse_group_names(value):
        key, sep, label_value = part.partition("=")
        key, label_value = key.strip(), label_value.strip()
        if not sep or not _LABEL_KEY.match(key):
            bad.append(part)
            continue
        selectors.append(f"{key}={label_value}")
    if bad:
        raise DiscoveryConfigurationError(
            f"Compute Engine source's '{field}' has selector(s) that are not "
            f"key=value labels: {', '.join(repr(b) for b in bad)}. A label key starts "
            f"with a lowercase letter and holds lowercase letters, digits, '_' and '-'.",
        )
    return tuple(dict.fromkeys(selectors))


def _all_instances(
    client: ComputeEngineClient,
    project_ids: Sequence[str],
) -> Iterator[Instance]:
    for project in project_ids:
        yield from client.instances(project)


def _device_for(instance: Instance) -> ManagedDevice:
    """The VM as every endpoint carrier describes a device, before its attributes.

    `device_key` is the instance's numeric id, never its name: a name is reused when a
    VM is deleted and recreated, which would merge two machines' records.

    `platform` is Linux without asking the VM. Only a payload produces records, and the
    collector that writes one on Compute Engine is the Linux build, which refuses any
    other OS by name -- so every VM with records runs Linux.
    """
    return ManagedDevice(
        device_key=instance.id,
        name=instance.name or None,
        platform=Platform.LINUX,
        group_ids=frozenset(f"{k}={v}" for k, v in instance.labels.items()),
        runs_on=RunsOn.GCP,
        address_scope=f"{instance.project}/{instance.zone}",
    )


def _guest_attributes_on(flag: Optional[str]) -> bool:
    """The VM's own setting, or its project's when it has none. Unset is off."""
    return (flag or "").strip().lower() == "true"


def _last_reported(status: Optional[str]) -> Optional[datetime]:
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


def _before(when: Optional[datetime], since: Optional[datetime]) -> bool:
    """Whether `when` falls before the window. Nothing to compare is never before it."""
    return when is not None and since is not None and when < since


def _failed_run(status: Optional[str]) -> list[str]:
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


def _report_scope(
    scope: DeviceScope,
    coverage: DeviceCoverage,
    carried: set[str],
    stopped_early: bool,
    logger: logging.Logger,
) -> None:
    """The scope's counts, and any selector no VM read carries."""
    if not scope.is_restricted:
        return
    logger.info(
        "Compute Engine scan scope kept %s of %s VM(s); excluded %s%s",
        coverage.devices_in_scope,
        coverage.devices_read,
        coverage.devices_excluded,
        _breakdown(coverage.excluded_by_group),
    )
    if scope.include:
        logger.info(
            "Compute Engine scan scope: %s VM(s) carry none of the included labels; "
            "in scope%s",
            coverage.devices_outside_included_groups,
            _breakdown(coverage.included_by_group),
        )
    unmatched = [
        pair
        for pair in (*scope.include.values(), *scope.exclude.values())
        if pair not in carried
    ]
    if unmatched and not stopped_early:
        logger.warning(
            "Compute Engine scan: no VM read carries label selector(s) %s, so they "
            "matched nothing. If that is not intended, check the source's "
            "include_labels and exclude_labels; labels are matched exactly.",
            ", ".join(unmatched),
        )
    if coverage.devices_read and not coverage.devices_in_scope:
        logger.warning(
            "Compute Engine scan left all %s VM(s) it read out of scope (%s). If that "
            "is not intended, check the source's include_labels and exclude_labels.",
            coverage.devices_read,
            scope.describe(),
        )


def _breakdown(counts: Mapping[str, int]) -> str:
    """` (TERMINATED: 2, SUSPENDED: 1)`, or nothing when there is nothing to break down."""
    if not counts:
        return ""
    return " (" + ", ".join(f"{name}: {count}" for name, count in counts.items()) + ")"
