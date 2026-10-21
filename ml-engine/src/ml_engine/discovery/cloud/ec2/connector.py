"""EC2's side of a DISCOVER_AGENTS scan.

A CLOUD SOURCE THAT READS A MACHINE'S INVENTORY, as Compute Engine is. EC2 lists the
instances, and each instance's SSM custom inventory carries the same `arthur1.` payload a
Jamf Extension Attribute does (`integrations/endpoint-ai-discovery/docs/mdm/ec2.md`).
Decoding, matching and dating are the endpoint pipeline's and `discovery.cloud.
vm_inventory`'s; the records are `CloudAgentCreationSource`. What is left here is the
vendor tag, reading this source's fields, scoping by tag, and what only EC2 has to say
about an instance: where it is, and whether it can report at all.

EVERY INSTANCE IS LISTED; THE LOOKBACK IS APPLIED TO ITS STATUS LINE. An inventory entry
carries the time SSM received it, not the time the collector scanned, and SSM keeps an
instance's inventory for thirty days after its last upload, stopped or not. The status
line dates the VM, as on Compute Engine.

AN INSTANCE SSM DOES NOT MANAGE IS NAMED, NOT READ. A running instance missing from
`DescribeInstanceInformation` has no agent, no permission or no route to SSM, so nothing
it has could have been uploaded since; whatever SSM still holds for it is stale by
construction. It is counted as `not-ssm-managed`, so a fleet without SSM reads as a
deployment fault and not as machines with nothing on them. SSM leaves stopped instances
out of that listing, so a stopped instance is read anyway, and its status line decides.

TAGS STAND WHERE GROUPS DO, with Compute Engine's label rules: a selector is a
`key=value` pair matched exactly, exclude wins, a pair no instance carries is reported
with a count of zero. EC2 tags are case-sensitive, and a key may hold almost anything; one
holding `=` or `,` cannot be written as a selector.

ONE INSTANCE IS THE UNIT THAT CAN FAIL. An instance whose inventory cannot be read is
reported and skipped; a refused credential or a denied action is not one instance's
problem, and ends the scan.

EVERY UNREADABLE INSTANCE IS LISTED, NOT ONLY COUNTED. The instances this scan cannot see
are where unmanaged AI sits, so each goes on the run's coverage by instance id, Name tag,
account and region, and reason, up to the run store's cap.
"""

import logging
from dataclasses import dataclass, replace
from datetime import datetime, timedelta, timezone
from typing import Callable, ClassVar, Iterator, Mapping, Optional, Sequence

import boto3
from arthur_client.api_bindings import DiscoverySourceConfigSpec
from arthur_common.models.agent_discovery_schemas import DiscoveredAgentRecord
from arthur_common.models.agent_governance_schemas import Platform, RunsOn

from discovery.aws_credentials import (
    REGION_NAME,
    SENSITIVE_FIELDS,
    aws_session,
    describe_credentials,
)
from discovery.catalog import Matcher
from discovery.cloud.ec2.client import (
    ClientFactory,
    Ec2Client,
    Ec2Error,
    Instance,
    assemble,
    default_client_factory,
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
from job_executors.discovery_scan import DeviceCoverage, DiscoveryConfigurationError

VENDOR = "aws_ec2"

# Non-sensitive source fields, beside aws_credentials' role_arn and external_id.
REGIONS_FIELD = "regions"
INCLUDE_TAGS_FIELD = "include_tags"
EXCLUDE_TAGS_FIELD = "exclude_tags"

# Opt-in for the engine's own AWS credentials, as Compute Engine's for ADC.
ALLOW_DEFAULT_CREDENTIALS_ENV_VAR = "ARTHUR_ENGINE_AWS_EC2_ALLOW_DEFAULT_CREDENTIALS"

# The assumed role's session name, which the customer's CloudTrail shows.
SESSION_NAME = "arthur-ai-discovery"

# Device coverage reasons only EC2 produces, beside the payload's own and the ones every
# VM-carrying cloud shares (READ_FAILED, NOT_REPORTED_IN_WINDOW).
NOT_SSM_MANAGED = "not-ssm-managed"
UNSUPPORTED_PLATFORM = "unsupported-platform"
INVENTORY_INCOMPLETE = "inventory-incomplete"

__all__ = [
    "INVENTORY_INCOMPLETE",
    "NOT_REPORTED_IN_WINDOW",
    "NOT_SSM_MANAGED",
    "READ_FAILED",
    "UNSUPPORTED_PLATFORM",
    "Ec2Connector",
]

# An EC2 tag key's length limit. Any character is allowed in one.
_TAG_KEY_MAX = 128


@dataclass(frozen=True)
class Ec2Settings:
    regions: tuple[str, ...]
    include_tags: tuple[str, ...] = ()
    exclude_tags: tuple[str, ...] = ()


SessionFactory = Callable[
    [Mapping[str, Optional[str]], Mapping[str, str]],
    boto3.Session,
]


def source_session(
    credentials: Mapping[str, Optional[str]],
    source_fields: Mapping[str, str],
) -> boto3.Session:
    """The source's AWS session, under EC2's opt-in for the engine's own credentials.

    STS is asked in the first region the source scans.
    """
    regions = parse_group_names(source_fields.get(REGIONS_FIELD))
    return aws_session(
        credentials,
        source_fields,
        source="EC2 source",
        allow_default_env_var=ALLOW_DEFAULT_CREDENTIALS_ENV_VAR,
        session_name=SESSION_NAME,
        region_name=regions[0] if regions else None,
    )


class Ec2Connector:
    """Implements `job_executors.discovery_scan.DiscoverySourceConnector`,
    `ReportsDeviceCoverage` and `AcceptsStopCheck`.

    Holds one scan's coverage and stop check, which is safe only because a connector is
    built fresh for every scan -- see `DiscoveryConnectorFactory`.
    """

    SENSITIVE_FIELDS: ClassVar[frozenset[str]] = SENSITIVE_FIELDS

    def __init__(
        self,
        session_for: SessionFactory = source_session,
        clients_for: Callable[[boto3.Session], ClientFactory] = default_client_factory,
        clock: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
    ) -> None:
        self._session_for = session_for
        self._clients_for = clients_for
        self._clock = clock
        self._coverage: Optional[DeviceCoverage] = None
        self._should_stop: Callable[[], bool] = lambda: False
        self._stopped_early = False

    def device_coverage(self) -> Optional[DeviceCoverage]:
        """None if the scan failed before reading an instance, including on its
        settings."""
        return self._coverage

    def stop_when(self, should_stop: Callable[[], bool]) -> None:
        """Asked after every instance, so a stop never waits on another page."""
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
        session = self._session_for(credentials, source_fields)
        matcher = Matcher.from_source(catalog_yaml=config.query or None, logger=logger)
        client = Ec2Client(self._clients_for(session), logger)

        # Tag pairs are their own ids: nothing renames a tag out from under a scan.
        scope = DeviceScope(
            include={pair: pair for pair in settings.include_tags},
            exclude={pair: pair for pair in settings.exclude_tags},
        )
        coverage = self._coverage = scope.new_coverage()
        # A lookback of zero or less is the whole roster, as on Jamf.
        since = (
            self._clock() - timedelta(hours=lookback_hours)
            if lookback_hours > 0
            else None
        )

        logger.info(
            "EC2 scan starting in region(s) %s, catalog %s, %s agent(s), scope: %s, "
            "using %s. Every instance is listed; %s.",
            ", ".join(settings.regions),
            matcher.catalog_sha,
            matcher.agent_count,
            scope.describe(),
            describe_credentials(credentials, source_fields),
            (
                f"one whose status line shows no report in the last {lookback_hours}h "
                f"is counted and not published"
                if since is not None
                else "the lookback is 0, so every instance's last report is published"
            ),
        )

        carried: set[str] = set()
        reader = VmInventoryReader(coverage, matcher, VENDOR, since, logger)

        for region in settings.regions:
            managed = client.managed_instance_ids(region)
            for instance in self._until_stopped(client.instances(region)):
                device = _device_for(instance)
                carried.update(device.group_ids)
                if not scope.admit(device, coverage):
                    continue
                if instance.windows:
                    coverage.count_unreadable(
                        UNSUPPORTED_PLATFORM,
                        device.unreadable(UNSUPPORTED_PLATFORM),
                    )
                    continue
                running = instance.state == "running"
                if running and instance.id not in managed:
                    coverage.count_unreadable(
                        NOT_SSM_MANAGED,
                        device.unreadable(NOT_SSM_MANAGED),
                    )
                    continue

                try:
                    inventory = client.inventory(region, instance.id)
                except Ec2Error as e:
                    if e.status_code in (401, 403):
                        # The credential or its permission, not this instance: every
                        # instance behind it would fail the same way.
                        raise
                    if e.code == "InvalidInstanceId":
                        coverage.count_unreadable(
                            NOT_SSM_MANAGED,
                            device.unreadable(NOT_SSM_MANAGED),
                        )
                        continue
                    logger.warning("%s: inventory not read (%s)", instance.id, e)
                    coverage.count_unreadable(
                        READ_FAILED,
                        device.unreadable(READ_FAILED),
                    )
                    continue

                attributes, problem = assemble(inventory.entries if inventory else [])
                if problem is not None:
                    logger.warning(
                        "%s: inventory not usable (%s)",
                        instance.id,
                        problem,
                    )
                    coverage.count_unreadable(
                        INVENTORY_INCOMPLETE,
                        device.unreadable(INVENTORY_INCOMPLETE),
                    )
                    continue

                records = reader.read(
                    replace(device, attributes=attributes),
                    state=None if running else instance.state,
                )
                if records:
                    yield records
            if self._stopped_early:
                break

        if self._stopped_early:
            logger.info(
                "EC2 scan stopped early on request after %s instance(s)",
                coverage.devices_read,
            )

        reader.log_summary("EC2", "instance", journal="ec2.md, section 06")
        report_scope(
            scope,
            coverage,
            carried,
            self._stopped_early,
            logger,
            provider="EC2",
            noun="instance",
            selector="tag",
            fields="include_tags and exclude_tags",
        )

        seen, reporting = coverage.devices_in_scope, coverage.devices_decoded
        if seen and not reporting:
            # A scan that read instances and decoded none is not a fleet without agents.
            # Not an exception: a fleet whose collector was rolled out an hour ago is in
            # this state legitimately.
            logger.warning(
                "EC2 scan decoded 0 of %s instance(s). This reads as a clean fleet and "
                "is almost never one: the install association may not have run on "
                "these instances yet, SSM may not manage them, their inventory "
                "association may not gather custom inventory, they may not have "
                "reported within the lookback window, or no instance has finished its "
                "first run and upload. Each instance is listed with its reason under "
                "device_coverage.unreadable_devices in this job's "
                "discovery_scan_outcome log line.",
                seen,
            )


def settings_from(source_fields: Mapping[str, str]) -> Ec2Settings:
    """The regions and tag scope from the source's non-sensitive fields."""
    regions = parse_group_names(source_fields.get(REGIONS_FIELD))
    if not regions:
        raise DiscoveryConfigurationError(
            f"EC2 source is missing required field '{REGIONS_FIELD}'. It is a source "
            f"field, not a secret.",
        )
    bad = [r for r in regions if not REGION_NAME.match(r)]
    if bad:
        raise DiscoveryConfigurationError(
            f"EC2 source's '{REGIONS_FIELD}' has value(s) that are not AWS region "
            f"names: {', '.join(repr(r) for r in bad)}. A region name looks like "
            f"us-east-1.",
        )
    return Ec2Settings(
        regions=regions,
        include_tags=parse_tag_selectors(
            source_fields.get(INCLUDE_TAGS_FIELD),
            INCLUDE_TAGS_FIELD,
        ),
        exclude_tags=parse_tag_selectors(
            source_fields.get(EXCLUDE_TAGS_FIELD),
            EXCLUDE_TAGS_FIELD,
        ),
    )


def parse_tag_selectors(value: Optional[str], field: str) -> tuple[str, ...]:
    """`key=value` tag pairs from a comma-separated source field.

    A pair without `=`, or with a key EC2 could not have, fails the scan
    (`parse_selectors`).
    """
    return parse_selectors(
        value,
        field,
        source="EC2 source",
        selector="tag",
        key_ok=lambda key: 0 < len(key) <= _TAG_KEY_MAX,
        key_rule=f"A tag key is 1 to {_TAG_KEY_MAX} characters, and is matched "
        f"exactly, case included.",
    )


def _device_for(instance: Instance) -> ManagedDevice:
    """The instance as every endpoint carrier describes a device, before its values.

    `device_key` is the instance id. A relaunched instance gets a new one, so two
    instances that share a `Name` tag are never one machine.

    `platform` is Linux without asking the instance, for Compute Engine's reason: only a
    payload produces records, and the collector that writes one is the Linux build.
    """
    return ManagedDevice(
        device_key=instance.id,
        name=instance.name or None,
        platform=Platform.LINUX,
        group_ids=frozenset(f"{k}={v}" for k, v in instance.tags.items()),
        runs_on=RunsOn.AWS,
        address_scope=f"{instance.account}/{instance.region}",
    )
