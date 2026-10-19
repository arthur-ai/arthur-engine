"""Reading EC2 instances and their SSM custom inventory.

Read-only, and outbound only. Nothing is installed on an instance, nothing connects to
one, and nothing is written back: each instance's reporter writes a custom inventory
file, its SSM Agent uploads it (`integrations/endpoint-ai-discovery/docs/mdm/ec2.md`),
and this reads it through the API `aws ssm list-inventory-entries` uses. The actions are
`ec2:DescribeInstances`, `ssm:DescribeInstanceInformation` and `ssm:ListInventoryEntries`.

THE VALUES ARRIVE IN PARTS. A custom inventory value holds at most 4,096 characters, so
the reporter splits each of its values -- `inventory`, `status` -- into entries that
carry the value's key, the part's number, the part count and the sha256 of the whole
value. `assemble` puts them back together. Parts that do not make exactly one whole --
one missing, one twice, counts that disagree, more of them than the budget needs, a hash
that does not match -- are no value at all rather than a shorter one: a truncated frame
would decode to fewer rows, and fewer rows read as fewer agents.

TWO LISTINGS PER REGION, THEN A READ PER INSTANCE. boto3's standard retry mode backs off
on SSM's and EC2's throttling answers, so a large fleet slows the scan rather than
failing it. A refused credential or a denied action is the source's problem, not one
instance's, and is raised with the `status_code` `failure_code` reads.
"""

import hashlib
import logging
import re
from dataclasses import dataclass, field
from typing import Any, Callable, Iterator, Mapping, Optional, Sequence

import boto3
from botocore.config import Config
from botocore.exceptions import (
    BotoCoreError,
    ClientError,
    NoCredentialsError,
    PartialCredentialsError,
)

from job_executors.discovery_scan import DiscoveryConfigurationError

# The custom inventory type the reporter writes, and its attributes. Shared with
# `deploy/report-ssm-inventory.sh`; changing either is a wire change.
TYPE_NAME = "Custom:ArthurAIDiscovery"
KEY = "Key"
PART = "Part"
PARTS = "Parts"
SHA256 = "Sha256"
VALUE = "Value"

# Values are named the way Compute Engine's guest attributes are, so that the shared VM
# pipeline reads `arthur/status` on either cloud.
NAMESPACE = "arthur/"

# The reporter writes both on every run, each with a value that names its state.
REQUIRED_KEYS = ("inventory", "status")

# The collector's budget for the framed value. A reassembled value longer than this was
# not written by a collector that respects it.
MAX_VALUE_LENGTH = 262144

# SSM's cap on one custom inventory value, in characters, and so the size of the
# reporter's parts.
PART_LENGTH = 4096

# The most parts a value within the budget is cut into. The count is the instance's to
# write, so a larger one is refused before anything is built from it.
MAX_PARTS = -(-MAX_VALUE_LENGTH // PART_LENGTH)

# ListInventoryEntries' own maximum page size.
PAGE_SIZE = 50

# Instances that can still report, or have and may again. A terminated or shutting-down
# instance is gone, so it is left out here, by its state: SSM goes on serving a
# terminated instance's last inventory, and reading it would publish a machine that no
# longer exists.
LISTED_STATES = ("pending", "running", "stopping", "stopped")

_KEY_NAME = re.compile(r"^[a-z][a-z0-9_-]{0,31}$")

_REFUSED_CODES = frozenset(
    {
        "AuthFailure",
        "ExpiredToken",
        "ExpiredTokenException",
        "IncompleteSignature",
        "InvalidClientTokenId",
        "SignatureDoesNotMatch",
        "UnrecognizedClientException",
    },
)
_DENIED_CODES = frozenset(
    {"AccessDenied", "AccessDeniedException", "OptInRequired", "UnauthorizedOperation"},
)


class Ec2Error(RuntimeError):
    """An EC2 or SSM call failed in a way retrying will not fix.

    `status_code` is 401 or 403 when the credential or its permission is the cause, which
    `failure_code` reads; `code` is AWS's own error code, where there is one.
    """

    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        code: Optional[str] = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code


@dataclass(frozen=True)
class Instance:
    """One instance as DescribeInstances returned it, with only what a scan reads."""

    region: str
    account: str
    id: str
    state: str
    windows: bool = False
    tags: Mapping[str, str] = field(default_factory=dict)

    @property
    def name(self) -> str:
        return self.tags.get("Name", "")


@dataclass(frozen=True)
class Inventory:
    """An instance's entries of the custom type, and when SSM last received them."""

    entries: Sequence[Mapping[str, str]]
    capture_time: Optional[str] = None


ClientFactory = Callable[[str, str], Any]


def default_client_factory(session: boto3.Session) -> ClientFactory:
    """`(service, region) -> client`, one client per pair, retrying in standard mode."""
    config = Config(
        retries={"mode": "standard", "max_attempts": 8},
        connect_timeout=10,
        read_timeout=30,
    )
    clients: dict[tuple[str, str], Any] = {}

    def client_for(service: str, region: str) -> Any:
        if (service, region) not in clients:
            clients[(service, region)] = session.client(
                service,
                region_name=region,
                config=config,
            )
        return clients[(service, region)]

    return client_for


class Ec2Client:
    """Lists a region's instances and reads each one's custom inventory."""

    def __init__(
        self,
        client_for: ClientFactory,
        logger: Optional[logging.Logger] = None,
    ) -> None:
        self._client_for = client_for
        self._log = logger or logging.getLogger(__name__)

    def instances(self, region: str) -> Iterator[Instance]:
        """Every instance in the region that is not terminated, a page at a time."""
        pages = self._call(
            "ec2",
            region,
            lambda ec2: ec2.get_paginator("describe_instances").paginate(
                Filters=[
                    {"Name": "instance-state-name", "Values": list(LISTED_STATES)},
                ],
            ),
        )
        for page in self._pages("ec2", region, pages):
            for reservation in page.get("Reservations") or []:
                account = str(reservation.get("OwnerId") or "")
                for raw in reservation.get("Instances") or []:
                    yield _instance(region, account, raw)

    def managed_instance_ids(self, region: str) -> frozenset[str]:
        """The region's instances SSM manages. Stopped ones are never among them."""
        pages = self._call(
            "ssm",
            region,
            lambda ssm: ssm.get_paginator("describe_instance_information").paginate(
                Filters=[{"Key": "ResourceType", "Values": ["EC2Instance"]}],
                PaginationConfig={"PageSize": 50},
            ),
        )
        return frozenset(
            str(info.get("InstanceId") or "")
            for page in self._pages("ssm", region, pages)
            for info in page.get("InstanceInformationList") or []
        )

    def inventory(self, region: str, instance_id: str) -> Optional[Inventory]:
        """The instance's entries of the custom type, or None when it has none.

        None is an instance nothing was ever uploaded for: SSM answers with no entries,
        or, in an account where no instance has ever uploaded the type, with
        `InvalidTypeNameException`. `InvalidInstanceId` -- an instance SSM does not
        know -- is raised with that code for the caller to count.
        """
        entries: list[Mapping[str, str]] = []
        capture_time: Optional[str] = None
        token: Optional[str] = None
        while True:
            kwargs: dict[str, Any] = {
                "InstanceId": instance_id,
                "TypeName": TYPE_NAME,
                "MaxResults": PAGE_SIZE,
            }
            if token:
                kwargs["NextToken"] = token
            try:
                page = self._call(
                    "ssm",
                    region,
                    lambda ssm: ssm.list_inventory_entries(**kwargs),
                )
            except Ec2Error as e:
                if e.code == "InvalidTypeNameException":
                    return None
                raise
            entries.extend(page.get("Entries") or [])
            capture_time = page.get("CaptureTime") or capture_time
            token = page.get("NextToken")
            if not token:
                break
        if not entries:
            return None
        return Inventory(entries=entries, capture_time=capture_time)

    # --- transport ----------------------------------------------------------------

    def _call(self, service: str, region: str, call: Callable[[Any], Any]) -> Any:
        try:
            return call(self._client_for(service, region))
        except (ClientError, BotoCoreError) as e:
            raise _error(service, region, e) from None

    def _pages(self, service: str, region: str, pages: Any) -> Iterator[Any]:
        """A paginator's pages, with its errors raised as the client's own."""
        iterator = iter(pages)
        while True:
            try:
                page = next(iterator)
            except StopIteration:
                return
            except (ClientError, BotoCoreError) as e:
                raise _error(service, region, e) from None
            yield page


def assemble(
    entries: Sequence[Mapping[str, str]],
) -> tuple[dict[str, str], Optional[str]]:
    """The reporter's values as `arthur/<key>` -> value, or why they cannot be read.

    Either every value assembles, or the instance has no values: an inventory whose
    status line arrived without the payload beside it would read as a VM with nothing
    on it. No entries at all is an instance nothing was uploaded for, and is no values
    without a problem.
    """
    if not entries:
        return {}, None
    parts: dict[str, dict[int, str]] = {}
    declared: dict[str, tuple[int, str]] = {}
    for entry in entries:
        key = str(entry.get(KEY) or "")
        if not _KEY_NAME.match(key):
            return {}, f"an entry names no usable key ({key[:40]!r})"
        try:
            part = int(str(entry.get(PART) or ""))
            count = int(str(entry.get(PARTS) or ""))
        except ValueError:
            return {}, f"{key}: an entry's part number or count is not a number"
        digest = str(entry.get(SHA256) or "").lower()
        if count > MAX_PARTS:
            return {}, (
                f"{key}: {count} parts, more than the {MAX_PARTS} a value within the "
                f"collector's budget is cut into"
            )
        if not 1 <= part <= count:
            return {}, f"{key}: part {part} of {count} is out of range"
        if declared.setdefault(key, (count, digest)) != (count, digest):
            return {}, f"{key}: its parts disagree about the count or the sha256"
        if part in parts.setdefault(key, {}):
            return {}, f"{key}: part {part} arrived twice"
        parts[key][part] = str(entry.get(VALUE) or "")

    absent = [key for key in REQUIRED_KEYS if key not in parts]
    if absent:
        return {}, f"no part of {' or '.join(absent)} arrived beside the rest"

    values: dict[str, str] = {}
    for key, pieces in parts.items():
        count, digest = declared[key]
        if len(pieces) != count:
            missing = sorted(set(range(1, count + 1)) - set(pieces))
            return {}, (
                f"{key}: {len(missing)} of {count} part(s) missing "
                f"(first: {missing[0]})"
            )
        value = "".join(pieces[i] for i in range(1, count + 1))
        if len(value) > MAX_VALUE_LENGTH:
            return {}, (
                f"{key}: {len(value)} characters, over the collector's "
                f"{MAX_VALUE_LENGTH:,}-character budget"
            )
        if hashlib.sha256(value.encode()).hexdigest() != digest:
            return {}, f"{key}: the parts do not hash to the sha256 they carry"
        values[f"{NAMESPACE}{key}"] = value
    return values, None


def _instance(region: str, account: str, raw: Mapping[str, Any]) -> Instance:
    return Instance(
        region=region,
        account=account,
        id=str(raw.get("InstanceId") or ""),
        state=str((raw.get("State") or {}).get("Name") or ""),
        windows=str(raw.get("Platform") or "").lower() == "windows",
        tags={
            str(tag.get("Key")): str(tag.get("Value") or "")
            for tag in raw.get("Tags") or []
            if tag.get("Key")
        },
    )


def _error(service: str, region: str, e: Exception) -> Exception:
    """The client's own error for a botocore failure, with the status `failure_code`
    reads. A missing credential is the source's configuration, not AWS's answer."""
    if isinstance(e, (NoCredentialsError, PartialCredentialsError)):
        return DiscoveryConfigurationError(
            f"EC2 source has no usable AWS credentials ({e}). Set the source's access "
            f"key, or give this engine credentials of its own.",
        )
    if isinstance(e, ClientError):
        error = e.response.get("Error") or {}
        code = str(error.get("Code") or "")
        message = str(error.get("Message") or "").strip()[:300]
        operation = e.operation_name
        # The role is assumed inside the first call that needs it, so its refusal
        # arrives from that call; it is STS's answer, about the role.
        label = "STS" if operation == "AssumeRole" else service.upper()
        status: Optional[int] = None
        if code in _REFUSED_CODES:
            status = 401
        elif code in _DENIED_CODES:
            status = 403
        return Ec2Error(
            f"{label} {operation} in {region} failed: {code}"
            f"{': ' + message if message else ''}",
            status_code=status,
            code=code or None,
        )
    return Ec2Error(
        f"{service.upper()} in {region} could not be reached: {e}. Check that the region "
        f"exists and is enabled for the account.",
    )
