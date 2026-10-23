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

AN ORGANIZATION IS A ROSTER, NOT A LIST SOMEONE KEEPS. `accounts` names accounts, or
`all` for every active one Organizations lists, each read through a role of one name
assumed from the source's own session; `regions` may be `all`, each account's enabled
regions. An account nobody told the governance team about is in scope the day it is
created. One account or region the scan is refused is a denied scope the run reports
and the scan continues past; refused everywhere, it fails, because a scan allowed to
read nothing is not a clean organization. Without `accounts`, the source's own account
fails the scan on a refusal, as it did.

EVERY UNREADABLE INSTANCE IS LISTED, NOT ONLY COUNTED. The instances this scan cannot see
are where unmanaged AI sits, so each goes on the run's coverage by instance id, Name tag,
account and region, and reason, up to the run store's cap.
"""

import logging
import re
from dataclasses import dataclass, replace
from datetime import datetime, timedelta, timezone
from typing import Callable, ClassVar, Iterator, Mapping, Optional, Sequence

import boto3
from arthur_client.api_bindings import DiscoverySourceConfigSpec
from arthur_common.models.agent_discovery_schemas import DiscoveredAgentRecord
from arthur_common.models.agent_governance_schemas import Platform, RunsOn
from botocore.exceptions import UnknownRegionError

from discovery.aws_credentials import (
    EXTERNAL_ID_FIELD,
    REGION_NAME,
    ROLE_ARN_FIELD,
    SENSITIVE_FIELDS,
    assumed_role_session,
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
from job_executors.discovery_scan import (
    DENIED_PERMISSION,
    DENIED_UNREACHABLE,
    DeniedScope,
    DeviceCoverage,
    DiscoveryConfigurationError,
)

VENDOR = "aws_ec2"

# Non-sensitive source fields, beside aws_credentials' role_arn and external_id.
REGIONS_FIELD = "regions"
INCLUDE_TAGS_FIELD = "include_tags"
EXCLUDE_TAGS_FIELD = "exclude_tags"
ACCOUNTS_FIELD = "accounts"
MEMBER_ROLE_NAME_FIELD = "member_role_name"
DEFAULT_MEMBER_ROLE_NAME = "arthur-ai-discovery"

# What `regions` or `accounts` says to mean every one: each region an account has
# enabled, every active account in the organization.
ALL = "all"

# Where STS, Organizations and DescribeRegions are asked: a region every account in the
# partition has enabled. Organizations answers from its partition's own endpoint whichever
# region asks, and opt-in regions exist only in the aws partition, where us-east-1 is
# never one. The partition is the source's named regions'; `regions: all` names none and
# is the aws partition's. A partition not listed is asked in the first region named.
BOOTSTRAP_REGIONS = {
    "aws": "us-east-1",
    "aws-us-gov": "us-gov-west-1",
    "aws-cn": "cn-north-1",
}
BOOTSTRAP_REGION = BOOTSTRAP_REGIONS["aws"]

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

_ACCOUNT_ID = re.compile(r"^[0-9]{12}$")
# IAM's own rule for a role name.
_ROLE_NAME = re.compile(r"^[\w+=,.@-]{1,64}$")


@dataclass(frozen=True)
class Ec2Settings:
    regions: tuple[str, ...]
    include_tags: tuple[str, ...] = ()
    exclude_tags: tuple[str, ...] = ()
    # `regions: all`: every region each account has enabled, asked per account.
    all_regions: bool = False
    # The accounts named, None for the credential's own.
    accounts: Optional[tuple[str, ...]] = None
    # `accounts: all`: every active account Organizations lists.
    all_accounts: bool = False
    member_role_name: str = DEFAULT_MEMBER_ROLE_NAME
    # The AWS partition the named regions are in, and so every ARN the scan builds.
    partition: str = "aws"

    @property
    def spans_accounts(self) -> bool:
        """Whether the scan reads accounts through the member role, one at a time."""
        return self.all_accounts or self.accounts is not None

    @property
    def bootstrap_region(self) -> str:
        """Where STS, Organizations and DescribeRegions are asked (`BOOTSTRAP_REGIONS`)."""
        return BOOTSTRAP_REGIONS.get(
            self.partition,
            self.regions[0] if self.regions else BOOTSTRAP_REGION,
        )


SessionFactory = Callable[
    [Mapping[str, Optional[str]], Mapping[str, str]],
    boto3.Session,
]
AccountSessionFactory = Callable[
    [boto3.Session, str, str, Optional[str]],
    boto3.Session,
]


def source_session(
    credentials: Mapping[str, Optional[str]],
    source_fields: Mapping[str, str],
) -> boto3.Session:
    """The source's AWS session, under EC2's opt-in for the engine's own credentials.

    STS is asked in the partition's bootstrap region. A source that spans accounts and
    assumes no role of its own has an external ID for its member roles alone, so the
    source's own session is built without it.
    """
    settings = settings_from(source_fields)
    fields = dict(source_fields)
    if settings.spans_accounts and not (fields.get(ROLE_ARN_FIELD) or "").strip():
        fields.pop(EXTERNAL_ID_FIELD, None)
    return aws_session(
        credentials,
        fields,
        source="EC2 source",
        allow_default_env_var=ALLOW_DEFAULT_CREDENTIALS_ENV_VAR,
        session_name=SESSION_NAME,
        region_name=settings.bootstrap_region,
    )


def member_session(
    base: boto3.Session,
    account: str,
    role_name: str,
    external_id: Optional[str],
) -> boto3.Session:
    """The session for one account of the organization: its member role, assumed from
    the source's own session with the source's external ID, as `SESSION_NAME`. The role's
    ARN is in the partition of the region the source's session asks in."""
    partition = (
        base.get_partition_for_region(base.region_name) if base.region_name else "aws"
    )
    return assumed_role_session(
        base,
        f"arn:{partition}:iam::{account}:role/{role_name}",
        external_id,
        SESSION_NAME,
        region_name=base.region_name,
    )


class Ec2Connector:
    """Implements `job_executors.discovery_scan.DiscoverySourceConnector`,
    `ReportsDeviceCoverage`, `ReportsDeniedScopes` and `AcceptsStopCheck`.

    Holds one scan's coverage and stop check, which is safe only because a connector is
    built fresh for every scan -- see `DiscoveryConnectorFactory`.
    """

    SENSITIVE_FIELDS: ClassVar[frozenset[str]] = SENSITIVE_FIELDS

    def __init__(
        self,
        session_for: SessionFactory = source_session,
        clients_for: Callable[[boto3.Session], ClientFactory] = default_client_factory,
        clock: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
        account_session_for: AccountSessionFactory = member_session,
    ) -> None:
        self._session_for = session_for
        self._clients_for = clients_for
        self._clock = clock
        self._account_session_for = account_session_for
        self._coverage: Optional[DeviceCoverage] = None
        self._denied: list[DeniedScope] = []
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

    def denied_scopes(self) -> Sequence[DeniedScope]:
        """The accounts and regions the scan was refused, and continued past."""
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
        session = self._session_for(credentials, source_fields)
        matcher = Matcher.from_source(catalog_yaml=config.query or None, logger=logger)
        own = Ec2Client(self._clients_for(session), logger)

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

        # The roster: the source's own account, or every account named or listed,
        # each read through the member role. The management account is one of them.
        targets: list[tuple[Optional[str], Ec2Client]] = [(None, own)]
        if settings.spans_accounts:
            accounts = settings.accounts or own.organization_accounts(
                settings.bootstrap_region,
            )
            external_id = (source_fields.get(EXTERNAL_ID_FIELD) or "").strip() or None
            targets = [
                (
                    account,
                    Ec2Client(
                        self._clients_for(
                            self._account_session_for(
                                session,
                                account,
                                settings.member_role_name,
                                external_id,
                            ),
                        ),
                        logger,
                    ),
                )
                for account in accounts
            ]

        logger.info(
            "EC2 scan starting in %s%s, catalog %s, %s agent(s), scope: %s, using %s. "
            "Every instance is listed; %s.",
            (
                "every enabled region"
                if settings.all_regions
                else f"region(s) {', '.join(settings.regions)}"
            ),
            (
                f" of {len(targets)} account(s) through role {settings.member_role_name}"
                if settings.spans_accounts
                else ""
            ),
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
        if settings.spans_accounts and not targets:
            logger.warning(
                "EC2 scan found no active account in the organization. Nothing can be "
                "read, so this is the credential's view of Organizations, not a fleet "
                "without instances.",
            )

        carried: set[str] = set()
        reader = VmInventoryReader(
            coverage,
            matcher,
            VENDOR,
            since,
            logger,
            clock=self._clock,
        )
        scanned = 0

        for account, client in targets:
            regions: Sequence[str] = settings.regions
            if settings.all_regions or account is not None:
                # A member account is asked which regions it has enabled even when the
                # source names them: an opt-in region it never enabled answers every
                # call as an authentication failure, which must not read as a refused
                # credential. Such a region is that account's denied scope.
                try:
                    enabled = client.enabled_regions(settings.bootstrap_region)
                except Ec2Error as e:
                    if not self._refused(settings, account, None, e, logger):
                        raise
                    continue
                if settings.all_regions:
                    regions = enabled
                else:
                    regions = [r for r in settings.regions if r in enabled]
                    for region in settings.regions:
                        if region not in enabled:
                            self._not_enabled(account, region, logger)
            for region in regions:
                try:
                    yield from self._scan_region(
                        client,
                        region,
                        scope,
                        coverage,
                        reader,
                        carried,
                        logger,
                    )
                except Ec2Error as e:
                    if not self._refused(settings, account, region, e, logger):
                        raise
                    if e.operation == "AssumeRole":
                        # The member role, not the region: every region of the account
                        # would be refused the same way, so the account is one scope.
                        break
                    continue
                scanned += 1
                if self._stopped_early:
                    break
            if self._stopped_early:
                break

        if self._stopped_early:
            logger.info(
                "EC2 scan stopped early on request after %s instance(s)",
                coverage.devices_read,
            )

        if settings.spans_accounts:
            logger.info(
                "EC2 scope: %s account(s); %s account-region(s) read; %s refused%s",
                len(targets),
                scanned,
                len(self._denied),
                _named([denied.scope for denied in self._denied]),
            )
        if self._denied and not scanned:
            # Refused everywhere it could have read. Not a fleet without instances:
            # the credential has no view of the scope it was given.
            raise Ec2Error(
                f"EC2 scan was refused every account and region it could read "
                f"({len(self._denied)}{_named([d.scope for d in self._denied])}). "
                f"Check that role {settings.member_role_name} exists in each account "
                f"and trusts this credential.",
                status_code=(
                    403
                    if all(d.reason == DENIED_PERMISSION for d in self._denied)
                    else None
                ),
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

    def _not_enabled(
        self,
        account: Optional[str],
        region: str,
        logger: logging.Logger,
    ) -> None:
        """A named region the account has not enabled: its denied scope, unasked."""
        scope = f"{account}/{region}"
        self._denied.append(DeniedScope(scope, DENIED_UNREACHABLE))
        logger.warning(
            "%s: not read (%s): the account has not enabled the region",
            scope,
            DENIED_UNREACHABLE,
        )

    def _refused(
        self,
        settings: Ec2Settings,
        account: Optional[str],
        region: Optional[str],
        error: Ec2Error,
        logger: logging.Logger,
    ) -> bool:
        """Whether a failure is one account's or region's, recorded as a denied scope.

        Only a scope that spans accounts has parts to be refused one at a time; the
        source's own account fails the scan as it always did. A refused credential --
        401, from any call -- is never one part's problem.
        """
        if not settings.spans_accounts or account is None:
            return False
        if error.status_code == 401:
            return False
        if error.operation == "AssumeRole":
            # The member role, so the whole account.
            scope = account
        else:
            scope = f"{account}/{region}" if region else account
        reason = DENIED_PERMISSION if error.status_code == 403 else DENIED_UNREACHABLE
        self._denied.append(DeniedScope(scope, reason))
        logger.warning("%s: not read (%s): %s", scope, reason, error)
        return True

    def _scan_region(
        self,
        client: Ec2Client,
        region: str,
        scope: DeviceScope,
        coverage: DeviceCoverage,
        reader: VmInventoryReader,
        carried: set[str],
        logger: logging.Logger,
    ) -> Iterator[Sequence[DiscoveredAgentRecord]]:
        """One region's instances. A refusal ends it with the error, for the caller."""
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


def settings_from(source_fields: Mapping[str, str]) -> Ec2Settings:
    """The regions, accounts and tag scope from the source's non-sensitive fields."""
    regions = parse_group_names(source_fields.get(REGIONS_FIELD))
    if not regions:
        raise DiscoveryConfigurationError(
            f"EC2 source is missing required field '{REGIONS_FIELD}'. It is a source "
            f"field, not a secret.",
        )
    all_regions = _is_all(regions)
    partitions: dict[str, str] = {}
    bad = []
    for region in () if all_regions else regions:
        partition = _partition_for(region) if REGION_NAME.match(region) else None
        if partition is None:
            bad.append(region)
        else:
            partitions[region] = partition
    if bad:
        raise DiscoveryConfigurationError(
            f"EC2 source's '{REGIONS_FIELD}' has value(s) that are not AWS region "
            f"names: {', '.join(repr(r) for r in bad)}. A region name looks like "
            f"us-east-1; '{ALL}' alone scans every region each account has enabled.",
        )
    if len(set(partitions.values())) > 1:
        raise DiscoveryConfigurationError(
            f"EC2 source's '{REGIONS_FIELD}' names regions in more than one AWS "
            f"partition ({', '.join(f'{r}: {p}' for r, p in partitions.items())}). One "
            f"credential reaches one partition; use a source for each.",
        )

    accounts = parse_group_names(source_fields.get(ACCOUNTS_FIELD))
    all_accounts = _is_all(accounts)
    bad = [] if all_accounts else [a for a in accounts if not _ACCOUNT_ID.match(a)]
    if bad:
        raise DiscoveryConfigurationError(
            f"EC2 source's '{ACCOUNTS_FIELD}' has value(s) that are not AWS account "
            f"IDs: {', '.join(repr(a) for a in bad)}. An account ID is 12 digits; "
            f"'{ALL}' alone scans every active account in the organization.",
        )
    role_name = (
        source_fields.get(MEMBER_ROLE_NAME_FIELD) or ""
    ).strip() or DEFAULT_MEMBER_ROLE_NAME
    if not _ROLE_NAME.match(role_name):
        raise DiscoveryConfigurationError(
            f"EC2 source's '{MEMBER_ROLE_NAME_FIELD}' is not an IAM role name: "
            f"{role_name!r}. It is the name alone, not an ARN.",
        )
    return Ec2Settings(
        regions=() if all_regions else regions,
        include_tags=parse_tag_selectors(
            source_fields.get(INCLUDE_TAGS_FIELD),
            INCLUDE_TAGS_FIELD,
        ),
        exclude_tags=parse_tag_selectors(
            source_fields.get(EXCLUDE_TAGS_FIELD),
            EXCLUDE_TAGS_FIELD,
        ),
        all_regions=all_regions,
        accounts=None if all_accounts or not accounts else accounts,
        all_accounts=all_accounts,
        member_role_name=role_name,
        partition=next(iter(partitions.values()), "aws"),
    )


def _partition_for(region: str) -> Optional[str]:
    """The AWS partition a region is in, from botocore's endpoint data, or None for a
    name no partition claims."""
    try:
        return str(boto3.Session().get_partition_for_region(region))
    except UnknownRegionError:
        return None


def _is_all(values: Sequence[str]) -> bool:
    """Whether a list field says `all`, which it can only say alone."""
    return len(values) == 1 and values[0].lower() == ALL


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


def _named(items: Sequence[str]) -> str:
    """` (a, b, c, ...)` naming the first few, or nothing for none."""
    if not items:
        return ""
    shown = ", ".join(items[:10])
    return f" ({shown}{', ...' if len(items) > 10 else ''})"


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
