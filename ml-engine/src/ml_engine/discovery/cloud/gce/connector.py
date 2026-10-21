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
one whose collector's timer is gone, keeps serving its last values.
`discovery.cloud.vm_inventory` dates each VM by its status line instead, as on every
cloud whose VMs carry the payload.

GUEST ATTRIBUTES OFF IS NAMED, NOT READ. A VM whose `enable-guest-attributes` is not true
-- on the VM, or on its project when the VM does not say -- cannot have reported since it
was turned off, and what the API still serves for it is stale by construction. It is
counted as `guest-attributes-disabled` rather than decoded, so a fleet with the setting
off reads as a deployment fault and not as machines that stopped reporting.

OS CONFIG OFF IS NAMED TOO, ON A VM NOTHING WAS EVER WRITTEN FOR. The OS policy that
installs the collector is applied by the OS Config agent, which acts only where
`enable-osconfig` is true, on the VM or on its project. A VM with no `arthur/` namespace
and that key off can never be reached by the rollout, which is a different fact from a
rollout that has not reached it yet; it is counted as `osconfig-disabled`, so a VM whose
agent was turned off is visible by name. A VM that has reported keeps its own reasons:
what it wrote is evidence, whatever its key says now.

EVERY UNREADABLE VM IS LISTED, NOT ONLY COUNTED. The VMs this scan cannot see are where
unmanaged AI sits, so each goes on the run's coverage by instance id, name, project and
zone, and reason, up to the run store's cap.

LABELS STAND WHERE GROUPS DO. A selector is a `key=value` pair and is matched exactly;
`discovery.endpoint.scope` applies them with Jamf's rules, exclude winning. Unlike a
group name a label has no registry to resolve against, so a selector no VM carries is
reported with a count of zero and a warning rather than failing the scan.

ONE VM IS THE UNIT THAT CAN FAIL. A VM whose guest attributes cannot be read is reported
and skipped; a refused credential or a denied permission is not one VM's problem, and
ends the scan.

AN ORGANIZATION OR A FOLDER IS A ROSTER, NOT A LIST SOMEONE KEEPS. A source may name
projects, or a parent whose active projects Resource Manager lists, folders walked --
or both. A project nobody told the governance team about is in scope the day it is
created. Under a parent, one project the credential is refused is a denied scope the run
reports and the scan continues past, so the other hundred are read; a refusal of every
project it could have read fails the run, because a scan allowed to read nothing is not
a clean organization. A named project keeps failing the scan on a refusal, as it did.
"""

import logging
import re
from dataclasses import dataclass, replace
from datetime import datetime, timedelta, timezone
from typing import Callable, ClassVar, Iterator, Mapping, Optional, Sequence

import google.auth
import requests
from arthur_client.api_bindings import DiscoverySourceConfigSpec
from arthur_common.models.agent_discovery_schemas import DiscoveredAgentRecord
from arthur_common.models.agent_governance_schemas import Platform, RunsOn
from google.auth.credentials import Credentials
from google.auth.exceptions import DefaultCredentialsError
from google.auth.transport.requests import AuthorizedSession

from discovery.catalog import Matcher
from discovery.cloud.gce.client import (
    API_NOT_ENABLED_REASON,
    CLOUD_PLATFORM_READONLY_SCOPE,
    COMPUTE_READONLY_SCOPE,
    GUEST_ATTRIBUTES_FLAG,
    OSCONFIG_FLAG,
    ComputeEngineClient,
    ComputeEngineError,
    Instance,
)
from discovery.cloud.vm_inventory import (
    NOT_REPORTED_IN_WINDOW,
    READ_FAILED,
    VmInventoryReader,
    parse_selectors,
    report_scope,
)
from discovery.endpoint.device import ManagedDevice
from discovery.endpoint.scope import DeviceScope, parse_group_names
from discovery.gcp_credentials import (
    SERVICE_ACCOUNT_KEY_FIELD,
    service_account_credentials,
)
from job_executors.discovery_scan import (
    DENIED_PERMISSION,
    DENIED_UNREACHABLE,
    DeniedScope,
    DeviceCoverage,
    DiscoveryConfigurationError,
)

VENDOR = "gcp_compute_engine"

# Non-sensitive source fields. At least one of the three that name a scope.
PROJECT_IDS_FIELD = "project_ids"
ORGANIZATION_ID_FIELD = "organization_id"
FOLDER_IDS_FIELD = "folder_ids"
INCLUDE_LABELS_FIELD = "include_labels"
EXCLUDE_LABELS_FIELD = "exclude_labels"

# Opt-in for Application Default Credentials when a source has no key, as Vertex has.
ALLOW_ADC_ENV_VAR = "ARTHUR_ENGINE_GCP_COMPUTE_ENGINE_ALLOW_ADC"

# The device coverage reasons only Compute Engine produces, beside the payload's own and
# the ones every VM-carrying cloud shares (READ_FAILED, NOT_REPORTED_IN_WINDOW).
GUEST_ATTRIBUTES_DISABLED = "guest-attributes-disabled"
OSCONFIG_DISABLED = "osconfig-disabled"

__all__ = [
    "GUEST_ATTRIBUTES_DISABLED",
    "NOT_REPORTED_IN_WINDOW",
    "OSCONFIG_DISABLED",
    "READ_FAILED",
    "ComputeEngineConnector",
]

# A project id, optionally domain-scoped (`example.com:my-project`). Checked because it
# is a path segment in every call.
_PROJECT_ID = re.compile(r"^(?:[a-z0-9.-]+:)?[a-z][a-z0-9-]{4,28}[a-z0-9]$")

# A Compute Engine label key. Values may be empty.
_LABEL_KEY = re.compile(r"^[a-z][a-z0-9_-]{0,62}$")

# A Resource Manager organization or folder number, as it appears after the prefix.
_RESOURCE_NUMBER = re.compile(r"^[0-9]{1,30}$")


@dataclass(frozen=True)
class ComputeEngineSettings:
    project_ids: tuple[str, ...]
    include_labels: tuple[str, ...] = ()
    exclude_labels: tuple[str, ...] = ()
    organization_id: Optional[str] = None
    folder_ids: tuple[str, ...] = ()

    @property
    def parents(self) -> tuple[str, ...]:
        """The Resource Manager parents whose active projects the scan enumerates."""
        organization = (
            (f"organizations/{self.organization_id}",) if self.organization_id else ()
        )
        return (*organization, *(f"folders/{folder}" for folder in self.folder_ids))

    @property
    def scopes(self) -> list[str]:
        """What the credential's token must carry: Resource Manager is outside the
        compute scope, so a scan with parents to enumerate adds its read-only one."""
        scopes = [COMPUTE_READONLY_SCOPE]
        if self.parents:
            scopes.append(CLOUD_PLATFORM_READONLY_SCOPE)
        return scopes


def authorized_session(
    credentials: Optional[Credentials],
    scopes: Sequence[str],
) -> requests.Session:
    """A requests session that signs every call, refreshing its token as it goes.

    None is the engine's Application Default Credentials, which the caller has already
    checked the engine opted in to; `scopes` is what their token must carry.
    """
    if credentials is None:
        try:
            credentials, _ = google.auth.default(scopes=list(scopes))
        except DefaultCredentialsError as e:
            raise DiscoveryConfigurationError(
                f"Compute Engine source has no '{SERVICE_ACCOUNT_KEY_FIELD}', and this "
                f"engine has no Application Default Credentials to use instead: {e}",
            ) from None
    return AuthorizedSession(credentials)  # type: ignore[no-untyped-call]


class ComputeEngineConnector:
    """Implements `job_executors.discovery_scan.DiscoverySourceConnector`,
    `ReportsDeviceCoverage`, `ReportsDeniedScopes` and `AcceptsStopCheck`.

    Holds one scan's coverage and stop check, which is safe only because a connector is
    built fresh for every scan -- see `DiscoveryConnectorFactory`.
    """

    SENSITIVE_FIELDS: ClassVar[frozenset[str]] = frozenset({SERVICE_ACCOUNT_KEY_FIELD})

    def __init__(
        self,
        session_for: Callable[
            [Optional[Credentials], Sequence[str]],
            requests.Session,
        ] = authorized_session,
        clock: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
    ) -> None:
        self._session_for = session_for
        self._clock = clock
        self._coverage: Optional[DeviceCoverage] = None
        self._denied: list[DeniedScope] = []
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

    def denied_scopes(self) -> Sequence[DeniedScope]:
        """The enumerated projects the scan was refused, and continued past."""
        return tuple(self._denied)

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
            scopes=settings.scopes,
        )
        matcher = Matcher.from_source(catalog_yaml=config.query or None, logger=logger)
        client = ComputeEngineClient(
            self._session_for(google_credentials, settings.scopes),
            logger,
        )

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

        # The roster: the projects named, then every active project under each parent,
        # each once. A named project is read or the scan fails, as before there were
        # parents; an enumerated one the scan is refused is reported and passed over.
        projects: dict[str, bool] = {project: False for project in settings.project_ids}
        for parent in settings.parents:
            for project in client.projects_under(parent):
                projects.setdefault(project, True)
        enumerated = [project for project, listed in projects.items() if listed]

        logger.info(
            "Compute Engine scan starting against %s project(s)%s, catalog %s, %s "
            "agent(s), scope: %s, using %s. Every VM is listed; %s.",
            len(projects),
            (
                f" ({len(enumerated)} under {', '.join(settings.parents)})"
                if settings.parents
                else ""
            ),
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
        if not projects:
            logger.warning(
                "Compute Engine scan found no active project under %s. Nothing can be "
                "read, so this is the parent, or the credential's view of it, and not "
                "a fleet without VMs.",
                ", ".join(settings.parents),
            )

        carried: set[str] = set()
        reader = VmInventoryReader(coverage, matcher, VENDOR, since, logger)
        project_flags: dict[str, Mapping[str, Optional[str]]] = {}
        without_api: list[str] = []

        for project, listed in projects.items():
            try:
                yield from self._scan_project(
                    project,
                    client,
                    scope,
                    coverage,
                    reader,
                    project_flags,
                    carried,
                    logger,
                )
            except ComputeEngineError as e:
                if not listed or e.status_code == 401:
                    # A named project is the source's own choice, and a refused
                    # credential is not one project's problem: either ends the scan.
                    raise
                if e.status_code == 403 and e.reason == API_NOT_ENABLED_REASON:
                    # No Compute Engine API, so no VM can exist there.
                    without_api.append(project)
                    continue
                reason = (
                    DENIED_PERMISSION if e.status_code == 403 else DENIED_UNREACHABLE
                )
                self._denied.append(DeniedScope(f"projects/{project}", reason))
                logger.warning("projects/%s: not read (%s): %s", project, reason, e)
            if self._stopped_early:
                break

        if self._stopped_early:
            logger.info(
                "Compute Engine scan stopped early on request after %s VM(s)",
                coverage.devices_read,
            )

        if settings.parents:
            logger.info(
                "Compute Engine scope: %s project(s) under %s; %s without the Compute "
                "Engine API%s; %s refused%s",
                len(enumerated),
                ", ".join(settings.parents),
                len(without_api),
                _named(without_api),
                len(self._denied),
                _named([denied.scope for denied in self._denied]),
            )
        if self._denied and len(self._denied) == len(projects) - len(without_api):
            # Refused everywhere it could have read. Not a fleet without VMs: the
            # credential has no view of the scope it was given.
            raise ComputeEngineError(
                f"Compute Engine scan was refused every project it could read "
                f"({len(self._denied)}{_named([d.scope for d in self._denied])}). "
                f"Check the credential's roles/compute.viewer on the organization or "
                f"folder.",
                status_code=(
                    403
                    if all(d.reason == DENIED_PERMISSION for d in self._denied)
                    else None
                ),
            )

        reader.log_summary("Compute Engine", "VM", journal="gce.md, section 06")
        report_scope(
            scope,
            coverage,
            carried,
            self._stopped_early,
            logger,
            provider="Compute Engine",
            noun="VM",
            selector="label",
            fields="include_labels and exclude_labels",
        )

        seen, reporting = coverage.devices_in_scope, coverage.devices_decoded
        if seen and not reporting:
            # A scan that read VMs and decoded none is not a fleet without agents. Not an
            # exception, as on Jamf: a fleet whose collector was rolled out an hour ago
            # is in this state legitimately.
            logger.warning(
                "Compute Engine scan decoded 0 of %s VM(s). This reads as a clean fleet "
                "and is almost never one: the OS policy may not have rolled out to "
                "these VMs yet, the OS Config agent may not act on them "
                "(enable-osconfig off, or no service account on the VM), guest "
                "attributes may be off on the VMs or their project, the VMs may not "
                "have reported within the lookback window (stopped, or the collector's "
                "timer removed), or no VM has finished its first run, up to 15 minutes "
                "after boot. Each VM is listed with its reason under "
                "device_coverage.unreadable_devices in this job's "
                "discovery_scan_outcome log line.",
                seen,
            )

    def _scan_project(
        self,
        project: str,
        client: ComputeEngineClient,
        scope: DeviceScope,
        coverage: DeviceCoverage,
        reader: VmInventoryReader,
        project_flags: dict[str, Mapping[str, Optional[str]]],
        carried: set[str],
        logger: logging.Logger,
    ) -> Iterator[Sequence[DiscoveredAgentRecord]]:
        """One project's VMs. A refusal ends it with the error, for the caller to judge."""

        # Projects whose metadata the credential was refused, asked once each.
        refused_metadata: set[str] = set()

        def flag(instance: Instance, key: str, own: Optional[str]) -> Optional[str]:
            """The VM's own value for the key, else its project's.

            The project is read only when a VM does not say, so a role without
            compute.projects.get still scans a fleet that sets enable-guest-attributes
            per VM.
            """
            if own is not None:
                return own
            if instance.project not in project_flags:
                project_flags[instance.project] = client.project_flags(instance.project)
            return project_flags[instance.project][key]

        def osconfig_off(instance: Instance) -> bool:
            """Whether enable-osconfig is off for the VM, as far as the credential sees.

            The key only names a VM nothing was written for more finely than
            never-reported, so it is never a new way for a scan to fail: a credential
            refused the project's metadata leaves a VM that does not set the key itself
            with the reason it would have had without the check.
            """
            if instance.osconfig_flag is None and instance.project in refused_metadata:
                return False
            try:
                value = flag(instance, OSCONFIG_FLAG, instance.osconfig_flag)
            except ComputeEngineError as e:
                if e.status_code != 403:
                    raise
                refused_metadata.add(instance.project)
                logger.info(
                    "projects/%s: project metadata not readable (%s). A VM there that "
                    "does not set enable-osconfig itself is counted as never-reported "
                    "rather than %s.",
                    instance.project,
                    e,
                    OSCONFIG_DISABLED,
                )
                return False
            return not _flag_on(value)

        for instance in self._until_stopped(client.instances(project)):
            device = _device_for(instance)
            carried.update(device.group_ids)
            if not scope.admit(device, coverage):
                continue

            if not _flag_on(
                flag(instance, GUEST_ATTRIBUTES_FLAG, instance.guest_attributes_flag),
            ):
                coverage.count_unreadable(
                    GUEST_ATTRIBUTES_DISABLED,
                    device.unreadable(GUEST_ATTRIBUTES_DISABLED),
                )
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
                coverage.count_unreadable(READ_FAILED, device.unreadable(READ_FAILED))
                continue

            if attributes is None and osconfig_off(instance):
                # Nothing written, and the agent that would install the collector is
                # off: the rollout cannot reach this VM, as opposed to not yet.
                coverage.count_unreadable(
                    OSCONFIG_DISABLED,
                    device.unreadable(OSCONFIG_DISABLED),
                )
                continue

            records = reader.read(
                replace(device, attributes=attributes or {}),
                state=None if instance.status == "RUNNING" else instance.status,
            )
            if records:
                yield records


def settings_from(source_fields: Mapping[str, str]) -> ComputeEngineSettings:
    """The projects, parents and label scope from the source's non-sensitive fields."""
    projects = parse_group_names(source_fields.get(PROJECT_IDS_FIELD))
    organization = (source_fields.get(ORGANIZATION_ID_FIELD) or "").strip() or None
    folders = parse_group_names(source_fields.get(FOLDER_IDS_FIELD))
    if not projects and not organization and not folders:
        raise DiscoveryConfigurationError(
            f"Compute Engine source names nothing to scan: set '{PROJECT_IDS_FIELD}', "
            f"'{ORGANIZATION_ID_FIELD}' or '{FOLDER_IDS_FIELD}'. They are source "
            f"fields, not secrets.",
        )
    bad = [p for p in projects if not _PROJECT_ID.match(p)]
    if bad:
        raise DiscoveryConfigurationError(
            f"Compute Engine source's '{PROJECT_IDS_FIELD}' has value(s) that are not "
            f"GCP project IDs: {', '.join(repr(p) for p in bad)}. A project ID is 6 to "
            f"30 lowercase letters, digits and hyphens, not the project's name or "
            f"number.",
        )
    parents = (*((organization,) if organization else ()), *folders)
    bad = [n for n in parents if not _RESOURCE_NUMBER.match(n)]
    if bad:
        raise DiscoveryConfigurationError(
            f"Compute Engine source's '{ORGANIZATION_ID_FIELD}' or '{FOLDER_IDS_FIELD}' "
            f"has value(s) that are not organization or folder numbers: "
            f"{', '.join(repr(n) for n in bad)}. Use the number alone, without an "
            f"organizations/ or folders/ prefix.",
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
        organization_id=organization,
        folder_ids=folders,
    )


def parse_label_selectors(value: Optional[str], field: str) -> tuple[str, ...]:
    """`key=value` label pairs from a comma-separated source field.

    A pair without `=`, or with a key Compute Engine could not have, fails the scan
    (`parse_selectors`).
    """
    return parse_selectors(
        value,
        field,
        source="Compute Engine source",
        selector="label",
        key_ok=lambda key: bool(_LABEL_KEY.match(key)),
        key_rule="A label key starts with a lowercase letter and holds lowercase "
        "letters, digits, '_' and '-'.",
    )


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


def _named(items: Sequence[str]) -> str:
    """` (a, b, c, ...)` naming the first few, or nothing for none."""
    if not items:
        return ""
    shown = ", ".join(items[:10])
    return f" ({shown}{', ...' if len(items) > 10 else ''})"


def _flag_on(flag: Optional[str]) -> bool:
    """A metadata key that turns something on: `TRUE`, however cased. Unset is off."""
    return (flag or "").strip().lower() == "true"
