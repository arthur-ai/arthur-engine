"""An AWS organization as a cloud source's scope, for the AWS sources that span accounts.

A source that sets `accounts` reads each account through a role of one name, the member
role, assumed from the source's own session with the source's external ID: `all` is
every active account Organizations lists (`organizations:ListAccounts`, from the
management account or a delegated administrator), or the source names accounts by ID.
`regions: all` is each account's enabled regions. Each source asks Organizations and
DescribeRegions through its own client, so that a refusal is that source's error.

What is here is how those fields read, where they are asked, and the member role's
session, so that every source that spans accounts says them the same way.
"""

import re
from typing import Mapping, Optional, Sequence

import boto3
from botocore.exceptions import UnknownRegionError

from discovery.aws_credentials import assumed_role_session
from discovery.endpoint.scope import parse_group_names
from job_executors.discovery_scan import DiscoveryConfigurationError

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

# The member role's session name, which each account's CloudTrail shows.
SESSION_NAME = "arthur-ai-discovery"

_ACCOUNT_ID = re.compile(r"^[0-9]{12}$")
# IAM's own rule for a role name.
_ROLE_NAME = re.compile(r"^[\w+=,.@-]{1,64}$")


def is_all(values: Sequence[str]) -> bool:
    """Whether a list field says `all`, which it can only say alone."""
    return len(values) == 1 and values[0].lower() == ALL


def parse_accounts(
    source_fields: Mapping[str, str],
    source: str,
) -> tuple[Optional[tuple[str, ...]], bool]:
    """The accounts the source names, None when it names none, and whether it said
    `all`. `source` names the source in the error, such as "EC2 source"."""
    accounts = parse_group_names(source_fields.get(ACCOUNTS_FIELD))
    all_accounts = is_all(accounts)
    bad = [] if all_accounts else [a for a in accounts if not _ACCOUNT_ID.match(a)]
    if bad:
        raise DiscoveryConfigurationError(
            f"{source}'s '{ACCOUNTS_FIELD}' has value(s) that are not AWS account "
            f"IDs: {', '.join(repr(a) for a in bad)}. An account ID is 12 digits; "
            f"'{ALL}' alone scans every active account in the organization.",
        )
    return (None if all_accounts or not accounts else accounts), all_accounts


def parse_member_role_name(source_fields: Mapping[str, str], source: str) -> str:
    """The member role's name, `DEFAULT_MEMBER_ROLE_NAME` when the source sets none."""
    role_name = (
        source_fields.get(MEMBER_ROLE_NAME_FIELD) or ""
    ).strip() or DEFAULT_MEMBER_ROLE_NAME
    if not _ROLE_NAME.match(role_name):
        raise DiscoveryConfigurationError(
            f"{source}'s '{MEMBER_ROLE_NAME_FIELD}' is not an IAM role name: "
            f"{role_name!r}. It is the name alone, not an ARN.",
        )
    return role_name


def partition_for(region: str) -> Optional[str]:
    """The AWS partition a region is in, from botocore's endpoint data, or None for a
    name no partition claims."""
    try:
        return str(boto3.Session().get_partition_for_region(region))
    except UnknownRegionError:
        return None


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
