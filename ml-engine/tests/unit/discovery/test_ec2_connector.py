"""The EC2 client and connector, against a fake EC2 and SSM.

What matters most here is what an instance that cannot report looks like. SSM keeps an
instance's inventory for thirty days after its last upload, stopped or not; an instance
SSM does not manage cannot upload at all; and the payload arrives in parts that may not
make a whole. Each of those must be counted and named, never published as a clean machine
or as a live report.

The fake checks every request against botocore's own service model, so a call the real
API would refuse fails here rather than passing.
"""

import base64
import gzip
import hashlib
import io
import json
import logging
from dataclasses import asdict
from datetime import datetime, timezone
from typing import Any, Iterator, Optional

import boto3
import pytest
import yaml
from arthur_common.models.agent_governance_schemas import (
    CloudAgentCreationSource,
    Platform,
    RunsOn,
    SourceAddress,
)
from botocore.exceptions import ClientError, EndpointConnectionError
from botocore.session import Session as BotocoreSession
from botocore.validate import ParamValidator

from discovery import source_connectors
from discovery.cloud.ec2.client import (
    MAX_PARTS,
    MAX_VALUE_LENGTH,
    TYPE_NAME,
    Ec2Error,
    assemble,
)
from discovery.cloud.ec2.connector import (
    ALLOW_DEFAULT_CREDENTIALS_ENV_VAR,
    INVENTORY_INCOMPLETE,
    NOT_REPORTED_IN_WINDOW,
    NOT_SSM_MANAGED,
    READ_FAILED,
    UNSUPPORTED_PLATFORM,
    VENDOR,
    Ec2Connector,
    parse_tag_selectors,
    settings_from,
    source_session,
)
from job_executors.discovery_output_contract import check_batch
from job_executors.discovery_scan import (
    AcceptsStopCheck,
    DiscoveryConfigurationError,
    DiscoveryErrorCode,
    ReportsDeviceCoverage,
    failure_code,
)

SCAN_AT = 1790100381
LOG = logging.getLogger("discovery-test")
CATALOG = yaml.safe_dump(
    {
        "version": 2,
        "classifications": ["Coding agent"],
        "agents": [
            {
                "id": "codex-cli",
                "name": "Codex CLI",
                "classification": "Coding agent",
                "platforms": ["darwin", "linux"],
                "npm": ["@openai/codex"],
            },
        ],
    },
)
ACCOUNT = "123456789012"
REGION = "us-east-1"
FIELDS = {"regions": REGION}
CHUNK = 4096
MODELS = {svc: BotocoreSession().get_service_model(svc) for svc in ("ec2", "ssm")}


def frame(rows: list[dict[str, str]]) -> str:
    buf = io.BytesIO()
    with gzip.GzipFile(fileobj=buf, mode="wb", mtime=0) as gz:
        gz.write(json.dumps(rows).encode())
    return "arthur1." + base64.b64encode(buf.getvalue()).decode()


def row(kind: str, id: str, **over: str) -> dict[str, str]:
    base = {"kind": kind, "id": id, "ver": "", "loc": "", "extra": "", "perms": ""}
    base.update(over)
    return base


CODEX = frame(
    [
        row("npm", "@openai/codex", ver="0.5.0"),
        row("scan", "packages-linux", ver=str(SCAN_AT), extra="ok"),
    ],
)
OK_STATUS = "ok 2026-10-12T12:58:28Z rows=2 packages-linux=ok"
# The scan's clock: half an hour after OK_STATUS, inside the default 24h lookback.
NOW = datetime(2026, 10, 12, 13, 30, tzinfo=timezone.utc)


def entries(**values: str) -> list[dict[str, str]]:
    """What the reporter writes for these values: each split into 4,096-character
    parts, every part carrying the key, its number, the count and the whole's sha256."""
    out: list[dict[str, str]] = []
    for key, value in values.items():
        chunks = [value[i : i + CHUNK] for i in range(0, len(value), CHUNK)] or [""]
        digest = hashlib.sha256(value.encode()).hexdigest()
        out.extend(
            {
                "Key": key,
                "Part": str(n),
                "Parts": str(len(chunks)),
                "Sha256": digest,
                "Value": chunk,
            }
            for n, chunk in enumerate(chunks, 1)
        )
    return out


def reported(inventory: str = CODEX, status: str = OK_STATUS) -> list[dict[str, str]]:
    return entries(inventory=inventory, status=status)


def instance(
    ident: str,
    name: Optional[str] = None,
    state: str = "running",
    tags: Optional[dict[str, str]] = None,
    windows: bool = False,
) -> dict[str, Any]:
    """An instance as DescribeInstances returns it."""
    all_tags = {"Name": name or f"vm-{ident}", **(tags or {})}
    raw: dict[str, Any] = {
        "InstanceId": f"i-{ident:0>17}",
        "State": {"Code": 16, "Name": state},
        "Tags": [{"Key": k, "Value": v} for k, v in all_tags.items()],
        # Fields a scan must not read, keep or log.
        "PrivateIpAddress": "10.0.0.7",
        "IamInstanceProfile": {"Arn": "arn:aws:iam::123456789012:instance-profile/x"},
    }
    if windows:
        raw["Platform"] = "windows"
    return raw


def iid(ident: str) -> str:
    return f"i-{ident:0>17}"


def client_error(code: str, message: str, operation: str) -> ClientError:
    return ClientError({"Error": {"Code": code, "Message": message}}, operation)


def validate(service: str, operation: str, params: dict[str, Any]) -> None:
    shape = MODELS[service].operation_model(operation).input_shape
    report = ParamValidator().validate(params, shape)
    if report.has_errors():
        raise AssertionError(report.generate_report())


class FakeAws:
    """EC2's and SSM's three read calls, and a log of what was asked.

    `pages[region]` is DescribeInstances' pages for the region; `managed[region]` the
    instance ids DescribeInstanceInformation lists; `inventory[instance_id]` an
    instance's entries, an exception to raise, or missing for no entries. `errors`
    raises on the first call of `(service, operation)`.
    """

    def __init__(
        self,
        pages: dict[str, list[list[dict[str, Any]]]],
        managed: Optional[dict[str, set[str]]] = None,
        inventory: Optional[dict[str, Any]] = None,
        errors: Optional[dict[tuple[str, str], Exception]] = None,
    ) -> None:
        self.pages = pages
        if managed is None:
            managed = {
                region: {
                    raw["InstanceId"]
                    for page in region_pages
                    for raw in page
                    if raw["State"]["Name"] == "running"
                }
                for region, region_pages in pages.items()
            }
        self.managed = managed
        self.inventory = inventory or {}
        self.errors = errors or {}
        self.calls: list[tuple[str, str, str, dict[str, Any]]] = []

    def client_for(self, service: str, region: str) -> "FakeClient":
        return FakeClient(self, service, region)

    def reads(self) -> list[str]:
        """The instances whose inventory was read, by id, once per instance."""
        return list(
            dict.fromkeys(
                params["InstanceId"]
                for _, _, op, params in self.calls
                if op == "ListInventoryEntries"
            ),
        )


class FakePaginator:
    def __init__(self, client: "FakeClient", operation: str) -> None:
        self._client = client
        self._operation = operation

    def paginate(self, **kwargs: Any) -> Iterator[dict[str, Any]]:
        config = kwargs.pop("PaginationConfig", {})
        if "PageSize" in config:
            kwargs["MaxResults"] = config["PageSize"]
        return self._client.pages(self._operation, kwargs)


class FakeClient:
    def __init__(self, aws: FakeAws, service: str, region: str) -> None:
        self._aws = aws
        self._service = service
        self._region = region

    def _record(self, operation: str, params: dict[str, Any]) -> None:
        validate(self._service, operation, params)
        self._aws.calls.append((self._service, self._region, operation, dict(params)))
        error = self._aws.errors.pop((self._service, operation), None)
        if error is not None:
            raise error

    def get_paginator(self, name: str) -> FakePaginator:
        operation = {
            "describe_instances": "DescribeInstances",
            "describe_instance_information": "DescribeInstanceInformation",
        }[name]
        return FakePaginator(self, operation)

    def pages(self, operation: str, params: dict[str, Any]) -> Iterator[dict[str, Any]]:
        self._record(operation, params)
        if operation == "DescribeInstances":
            states = set(params["Filters"][0]["Values"])
            for page in self._aws.pages.get(self._region, [[]]):
                yield {
                    "Reservations": [
                        {
                            "OwnerId": ACCOUNT,
                            "Instances": [
                                raw for raw in page if raw["State"]["Name"] in states
                            ],
                        },
                    ],
                }
        else:
            yield {
                "InstanceInformationList": [
                    {"InstanceId": i, "PingStatus": "Online", "PlatformType": "Linux"}
                    for i in sorted(self._aws.managed.get(self._region, set()))
                ],
            }

    def list_inventory_entries(self, **params: Any) -> dict[str, Any]:
        self._record("ListInventoryEntries", params)
        answer = self._aws.inventory.get(params["InstanceId"], [])
        if isinstance(answer, Exception):
            raise answer
        start = int(params.get("NextToken") or 0)
        page = answer[start : start + params["MaxResults"]]
        body: dict[str, Any] = {
            "TypeName": params["TypeName"],
            "InstanceId": params["InstanceId"],
            "CaptureTime": "2026-10-12T13:00:00Z",
            "Entries": page,
        }
        if start + params["MaxResults"] < len(answer):
            body["NextToken"] = str(start + params["MaxResults"])
        return body


class FakeConfig:
    def __init__(self, query: Optional[str] = CATALOG) -> None:
        self.query = query
        self.vendor = VENDOR
        self.name = "acme ec2"


def connector_for(aws: FakeAws) -> Ec2Connector:
    return Ec2Connector(
        session_for=lambda creds, fields: boto3.Session(),
        clients_for=lambda session: aws.client_for,
        clock=lambda: NOW,
    )


def scan(
    aws: FakeAws,
    fields: Optional[dict[str, str]] = None,
    connector: Optional[Ec2Connector] = None,
    lookback_hours: int = 24,
) -> list[Any]:
    connector = connector or connector_for(aws)
    batches = connector.scan(
        FakeConfig(),  # type: ignore[arg-type]
        lookback_hours,
        {},
        fields or FIELDS,
        LOG,
    )
    return [record for batch in batches for record in batch]


def coverage_of(connector: Ec2Connector) -> dict[str, int]:
    coverage = connector.device_coverage()
    assert coverage is not None
    return dict(coverage.unreadable_by_reason)


def listed(
    connector: Ec2Connector,
) -> list[tuple[str, Optional[str], str, Optional[str]]]:
    """The unreadable instances the scan listed: id, Name tag, reason, last report."""
    coverage = connector.device_coverage()
    assert coverage is not None
    for device in coverage.unreadable_devices:
        assert device.location == f"{ACCOUNT}/{REGION}"
    return [
        (d.device_key, d.name, d.reason, d.last_reported)
        for d in coverage.unreadable_devices
    ]


# --- records --------------------------------------------------------------------------


def test_a_reporting_instance_is_a_cloud_record_on_aws_addressed_by_account_and_region() -> (
    None
):
    """A cloud record, addressed per (software, instance): the instance is the
    `instance`, so no two instances in an account are one agent."""
    aws = FakeAws(
        {REGION: [[instance("1", name="build-1")]]},
        inventory={iid("1"): reported()},
    )
    records = scan(aws)

    assert len(records) == 1
    record = records[0]
    assert record.external_id == f"{iid('1')}:codex-cli"
    assert record.runs_on is RunsOn.AWS
    assert record.platform is Platform.LINUX
    assert record.last_seen == datetime.fromtimestamp(SCAN_AT, tz=timezone.utc)
    check_batch(records, "Source config 'acme ec2' (aws_ec2)")
    source = record.creation_source
    assert isinstance(source, CloudAgentCreationSource)
    assert source.type == "CLOUD"
    assert source.vendor == "aws_ec2"
    assert source.address == SourceAddress(
        instance=iid("1"),
        scope=f"{ACCOUNT}/{REGION}",
        resource_kind="npm",
        resource_id="@openai/codex",
    )
    assert source.observations is not None
    assert source.observations.host_name == "build-1"
    assert aws.calls[-1][3]["TypeName"] == TYPE_NAME


def test_an_instance_relaunched_under_the_same_name_is_a_new_machine() -> None:
    before = FakeAws(
        {REGION: [[instance("111", name="build-1")]]},
        inventory={iid("111"): reported()},
    )
    after = FakeAws(
        {REGION: [[instance("222", name="build-1")]]},
        inventory={iid("222"): reported()},
    )
    [first], [second] = scan(before), scan(after)

    assert first.external_id != second.external_id
    assert first.creation_source.address.instance == iid("111")
    assert second.creation_source.address.instance == iid("222")


def test_every_page_of_every_region_is_read_and_a_payload_in_two_pages_reassembles() -> (
    None
):
    """A payload at the budget is 64 parts, and ListInventoryEntries pages at 50."""
    big = CODEX + "A" * (MAX_VALUE_LENGTH - len(CODEX))
    aws = FakeAws(
        {
            REGION: [[instance("1")], [instance("2")]],
            "eu-west-1": [[instance("3")]],
        },
        inventory={
            iid("1"): reported(),
            iid("2"): reported(),
            iid("3"): reported(inventory=big),
        },
    )
    connector = connector_for(aws)
    scan(aws, fields={"regions": f"{REGION}, eu-west-1"}, connector=connector)

    assert aws.reads() == [iid("1"), iid("2"), iid("3")]
    pages_for_3 = [
        c for c in aws.calls if c[2] == "ListInventoryEntries" and c[1] == "eu-west-1"
    ]
    assert len(pages_for_3) == 2
    # The padded payload frames as malformed past its gzip stream, which shows it
    # arrived whole: a part missing would have stopped it before decoding.
    assert coverage_of(connector) == {"malformed": 1}


def test_a_stopped_instance_is_still_read_and_its_records_are_dated_by_its_scan(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """SSM leaves stopped instances out of its managed list, and keeps their inventory."""
    aws = FakeAws(
        {REGION: [[instance("1", state="stopped")]]},
        inventory={iid("1"): reported()},
    )
    with caplog.at_level(logging.INFO):
        records = scan(aws)

    assert [r.external_id for r in records] == [f"{iid('1')}:codex-cli"]
    assert records[0].last_seen == datetime.fromtimestamp(SCAN_AT, tz=timezone.utc)
    assert "1 in-scope instance(s) were not running (stopped: 1)" in caplog.text
    assert "10.0.0.7" not in caplog.text, "the instance's own fields are never logged"


def test_an_instance_that_has_not_reported_in_the_lookback_is_counted_and_not_published() -> (
    None
):
    stale = "ok 2026-10-01T00:00:00Z rows=2 packages-linux=ok"
    aws = FakeAws(
        {REGION: [[instance("1", state="stopped"), instance("2")]]},
        inventory={iid("1"): reported(status=stale), iid("2"): reported()},
    )
    connector = connector_for(aws)
    records = scan(aws, connector=connector)

    assert [r.external_id for r in records] == [f"{iid('2')}:codex-cli"]
    assert coverage_of(connector) == {NOT_REPORTED_IN_WINDOW: 1}


def test_a_running_instance_ssm_does_not_manage_is_counted_by_name_and_not_read() -> (
    None
):
    """Whatever SSM still holds for it is stale by construction."""
    aws = FakeAws(
        {REGION: [[instance("1"), instance("2")]]},
        managed={REGION: {iid("2")}},
        inventory={iid("1"): reported(), iid("2"): reported()},
    )
    connector = connector_for(aws)
    records = scan(aws, connector=connector)

    assert [r.external_id for r in records] == [f"{iid('2')}:codex-cli"]
    assert aws.reads() == [iid("2")]
    assert coverage_of(connector) == {NOT_SSM_MANAGED: 1}


def test_an_instance_ssm_refuses_as_unknown_is_not_ssm_managed() -> None:
    aws = FakeAws(
        {REGION: [[instance("1", state="stopped")]]},
        inventory={
            iid("1"): client_error(
                "InvalidInstanceId",
                "Instances [[i-00000000000000001]] not in a valid state",
                "ListInventoryEntries",
            ),
        },
    )
    connector = connector_for(aws)
    assert scan(aws, connector=connector) == []
    assert coverage_of(connector) == {NOT_SSM_MANAGED: 1}


def test_a_windows_instance_is_counted_as_unsupported_and_not_read() -> None:
    aws = FakeAws({REGION: [[instance("1", windows=True)]]})
    connector = connector_for(aws)
    assert scan(aws, connector=connector) == []
    assert aws.reads() == []
    assert coverage_of(connector) == {UNSUPPORTED_PLATFORM: 1}


@pytest.mark.parametrize(
    "answer",
    [
        [],
        client_error(
            "InvalidTypeNameException",
            "The parameter type name is not valid.",
            "ListInventoryEntries",
        ),
    ],
    ids=["no-entries", "type-unknown-to-the-account"],
)
def test_an_instance_the_collector_never_reached_is_counted_and_the_fleet_is_not_called_clean(
    answer: Any,
    caplog: pytest.LogCaptureFixture,
) -> None:
    aws = FakeAws({REGION: [[instance("1")]]}, inventory={iid("1"): answer})
    connector = connector_for(aws)
    with caplog.at_level(logging.WARNING):
        assert scan(aws, connector=connector) == []

    assert coverage_of(connector) == {"never-reported": 1}
    assert listed(connector) == [(iid("1"), "vm-1", "never-reported", None)]
    assert "decoded 0 of 1 instance(s)" in caplog.text
    assert "device_coverage.unreadable_devices" in caplog.text


def test_every_unreadable_instance_is_listed_by_id_location_and_reason() -> None:
    """The machines a scan cannot see are where unmanaged AI sits, so each is a
    finding by identity, not a number."""
    stale = "ok 2026-10-01T00:00:00Z rows=2 packages-linux=ok"
    aws = FakeAws(
        {
            REGION: [
                [
                    instance("1", name="stale", state="stopped"),
                    instance("2", name="win", windows=True),
                    instance("3", name="unmanaged"),
                    instance("4", name="broken"),
                    instance("5", name="torn"),
                    instance("6", name="fine"),
                ],
            ],
        },
        managed={REGION: {iid("4"), iid("5"), iid("6")}},
        inventory={
            iid("1"): reported(status=stale),
            iid("4"): client_error("InternalServerError", "x", "ListInventoryEntries"),
            iid("5"): reported()[1:],
            iid("6"): reported(),
        },
    )
    connector = connector_for(aws)
    records = scan(aws, connector=connector)

    assert [r.external_id for r in records] == [f"{iid('6')}:codex-cli"]
    assert listed(connector) == [
        (iid("1"), "stale", NOT_REPORTED_IN_WINDOW, "2026-10-01T00:00:00+00:00"),
        (iid("2"), "win", UNSUPPORTED_PLATFORM, None),
        (iid("3"), "unmanaged", NOT_SSM_MANAGED, None),
        (iid("4"), "broken", READ_FAILED, None),
        (iid("5"), "torn", INVENTORY_INCOMPLETE, None),
    ]
    coverage = connector.device_coverage()
    assert coverage is not None
    assert coverage.devices_unreadable == 5
    assert asdict(coverage.unreadable_devices[0])["location"] == f"{ACCOUNT}/{REGION}"


def test_a_failed_run_keeps_the_last_good_scan_and_is_named(
    caplog: pytest.LogCaptureFixture,
) -> None:
    failed = f"{OK_STATUS} failed=2026-10-12T13:10:00Z osquery=absent"
    aws = FakeAws(
        {REGION: [[instance("1")]]},
        inventory={iid("1"): reported(status=failed)},
    )
    with caplog.at_level(logging.WARNING):
        records = scan(aws)

    assert [r.external_id for r in records] == [f"{iid('1')}:codex-cli"]
    assert (
        "1 instance(s) report that their collector's latest run failed" in caplog.text
    )
    assert "osquery=absent: 1" in caplog.text
    assert "ec2.md, section 06" in caplog.text


@pytest.mark.parametrize(
    "parts, named",
    [
        (lambda e: e[1:], "part(s) missing"),
        (lambda e: e + e[:1], "arrived twice"),
        (lambda e: [{**e[0], "Value": e[0]["Value"][:-1]}, *e[1:]], "do not hash"),
        (lambda e: [{**e[0], "Parts": "9"}, *e[1:]], "disagree"),
        (lambda e: [{**e[0], "Part": "0"}, *e[1:]], "out of range"),
        (lambda e: [{**e[0], "Key": "Inventory!"}, *e[1:]], "no usable key"),
    ],
    ids=["missing", "duplicate", "hash", "count", "range", "key"],
)
def test_parts_that_do_not_make_a_whole_are_no_value_rather_than_a_shorter_one(
    parts: Any,
    named: str,
) -> None:
    whole = entries(inventory="arthur1." + "x" * (3 * 4096), status=OK_STATUS)
    values, problem = assemble(parts(whole))
    assert values == {}
    assert problem is not None and named in problem


def test_an_instance_whose_parts_do_not_assemble_is_counted_and_not_published(
    caplog: pytest.LogCaptureFixture,
) -> None:
    aws = FakeAws(
        {REGION: [[instance("1"), instance("2")]]},
        inventory={iid("1"): reported()[1:], iid("2"): reported()},
    )
    connector = connector_for(aws)
    with caplog.at_level(logging.WARNING):
        records = scan(aws, connector=connector)

    assert [r.external_id for r in records] == [f"{iid('2')}:codex-cli"]
    assert coverage_of(connector) == {INVENTORY_INCOMPLETE: 1}
    assert f"{iid('1')}: inventory not usable" in caplog.text


def test_parts_assemble_in_order_whatever_order_they_arrive_in() -> None:
    value = "arthur1." + "".join(chr(65 + i % 26) * 4096 for i in range(5))
    values, problem = assemble(
        list(reversed(entries(inventory=value, status=OK_STATUS))),
    )
    assert problem is None
    assert values == {"arthur/inventory": value, "arthur/status": OK_STATUS}


def test_a_value_over_the_budget_is_refused_even_when_its_parts_agree() -> None:
    """In no more parts than the budget allows, the last one a character over SSM's
    cap, which only the agent enforces."""
    value = "A" * (MAX_VALUE_LENGTH + 1)
    digest = hashlib.sha256(value.encode()).hexdigest()
    parts = [
        {**e, "Sha256": digest} if e["Key"] == "inventory" else e
        for e in entries(inventory=value[:-1], status=OK_STATUS)
    ]
    last = max(i for i, e in enumerate(parts) if e["Key"] == "inventory")
    parts[last] = {**parts[last], "Value": parts[last]["Value"] + "A"}
    values, problem = assemble(parts)
    assert values == {}
    assert problem is not None and "over the collector's" in problem


def test_a_part_count_no_value_within_the_budget_needs_is_refused_unbuilt() -> None:
    """The count is the instance's to write. One part claiming a trillion would have
    the missing-part report build a range that size."""
    whole = entries(inventory="arthur1.x", status=OK_STATUS)
    claimed = [{**whole[0], "Parts": "1000000000000"}, *whole[1:]]
    values, problem = assemble(claimed)
    assert values == {}
    assert problem is not None and f"more than the {MAX_PARTS}" in problem


def test_the_most_parts_the_budget_needs_still_assemble() -> None:
    value = "A" * MAX_VALUE_LENGTH
    whole = entries(inventory=value, status=OK_STATUS)
    assert max(int(e["Parts"]) for e in whole) == MAX_PARTS
    values, problem = assemble(whole)
    assert problem is None
    assert values["arthur/inventory"] == value


# --- failures -------------------------------------------------------------------------


def test_one_unreadable_instance_is_reported_and_skipped(
    caplog: pytest.LogCaptureFixture,
) -> None:
    aws = FakeAws(
        {REGION: [[instance("1"), instance("2")]]},
        inventory={
            iid("1"): client_error(
                "InternalServerError",
                "An error occurred",
                "ListInventoryEntries",
            ),
            iid("2"): reported(),
        },
    )
    connector = connector_for(aws)
    with caplog.at_level(logging.WARNING):
        records = scan(aws, connector=connector)

    assert [r.external_id for r in records] == [f"{iid('2')}:codex-cli"]
    assert coverage_of(connector) == {READ_FAILED: 1}
    assert f"{iid('1')}: inventory not read" in caplog.text


@pytest.mark.parametrize(
    "error, code, named",
    [
        (
            client_error(
                "AccessDeniedException",
                "User is not authorized to perform: ssm:ListInventoryEntries",
                "ListInventoryEntries",
            ),
            DiscoveryErrorCode.PERMISSION_DENIED,
            "ssm:ListInventoryEntries",
        ),
        (
            client_error(
                "UnrecognizedClientException",
                "The security token included in the request is invalid.",
                "ListInventoryEntries",
            ),
            DiscoveryErrorCode.AUTHENTICATION_FAILED,
            "security token",
        ),
        (
            client_error(
                "AccessDenied",
                "User is not authorized to perform: sts:AssumeRole on resource",
                "AssumeRole",
            ),
            DiscoveryErrorCode.PERMISSION_DENIED,
            "STS AssumeRole",
        ),
    ],
    ids=["denied-action", "refused-credential", "role-not-assumable"],
)
def test_a_refused_credential_or_denied_action_ends_the_scan(
    error: ClientError,
    code: DiscoveryErrorCode,
    named: str,
) -> None:
    """Not one instance's problem: every instance behind it would fail the same way."""
    aws = FakeAws(
        {REGION: [[instance("1"), instance("2")]]},
        inventory={iid("1"): error, iid("2"): reported()},
    )
    with pytest.raises(Ec2Error) as exc:
        scan(aws)

    assert failure_code(exc.value) is code
    assert named in str(exc.value)
    assert aws.reads() == [iid("1")]


def test_a_denied_listing_ends_the_scan_before_any_instance_is_read() -> None:
    aws = FakeAws(
        {REGION: [[instance("1")]]},
        errors={
            ("ec2", "DescribeInstances"): client_error(
                "UnauthorizedOperation",
                "You are not authorized to perform this operation.",
                "DescribeInstances",
            ),
        },
    )
    with pytest.raises(Ec2Error) as exc:
        scan(aws)
    assert failure_code(exc.value) is DiscoveryErrorCode.PERMISSION_DENIED
    assert aws.reads() == []


def test_a_region_that_cannot_be_reached_is_named() -> None:
    aws = FakeAws(
        {REGION: [[instance("1")]]},
        errors={
            ("ssm", "DescribeInstanceInformation"): EndpointConnectionError(
                endpoint_url="https://ssm.us-east-1.amazonaws.com/",
            ),
        },
    )
    with pytest.raises(Ec2Error, match="us-east-1") as exc:
        scan(aws)
    assert failure_code(exc.value) is DiscoveryErrorCode.PROVIDER_ERROR
    assert "enabled for the account" in str(exc.value)


# --- tag scope ------------------------------------------------------------------------


def test_tag_scope_reads_only_the_instances_it_admits_and_counts_each_selector(
    caplog: pytest.LogCaptureFixture,
) -> None:
    aws = FakeAws(
        {
            REGION: [
                [
                    instance("1", tags={"env": "prod"}),
                    instance("2", tags={"env": "prod", "team": "contractors"}),
                    instance("3", tags={"env": "dev"}),
                    instance("4", tags={"Env": "prod"}),
                ],
            ],
        },
        inventory={iid(i): reported() for i in "1234"},
    )
    connector = connector_for(aws)
    with caplog.at_level(logging.INFO):
        records = scan(
            aws,
            fields={
                "regions": REGION,
                "include_tags": "env=prod, env=staging",
                "exclude_tags": "team=contractors",
            },
            connector=connector,
        )

    assert [r.external_id for r in records] == [f"{iid('1')}:codex-cli"]
    assert aws.reads() == [iid("1")]
    coverage = connector.device_coverage()
    assert coverage is not None
    assert coverage.devices_read == 4
    assert coverage.devices_in_scope == 1
    assert coverage.excluded_by_group == {"team=contractors": 1}
    assert coverage.included_by_group == {"env=prod": 1, "env=staging": 0}
    assert coverage.devices_outside_included_groups == 2, "tags match case and all"
    assert "no instance read carries tag selector(s) env=staging" in caplog.text


def test_a_scope_that_keeps_nothing_says_so(caplog: pytest.LogCaptureFixture) -> None:
    aws = FakeAws({REGION: [[instance("1")]]})
    with caplog.at_level(logging.WARNING):
        scan(aws, fields={"regions": REGION, "exclude_tags": "Name=vm-1"})
    assert "left all 1 instance(s) it read out of scope" in caplog.text


# --- settings and credentials ---------------------------------------------------------


@pytest.mark.parametrize(
    "fields, named",
    [
        ({}, "missing required field 'regions'"),
        ({"regions": "US East (N. Virginia)"}, "not AWS region names"),
        ({"regions": "us-east-1", "include_tags": "env"}, "not key=value tags"),
        ({"regions": "us-east-1", "exclude_tags": f"{'k' * 129}=v"}, "1 to 128"),
    ],
)
def test_settings_that_cannot_be_scanned_fail_as_not_configured(
    fields: dict[str, str],
    named: str,
) -> None:
    with pytest.raises(DiscoveryConfigurationError, match=named) as exc:
        settings_from(fields)
    assert failure_code(exc.value) is DiscoveryErrorCode.NOT_CONFIGURED


def test_settings_accept_several_regions_and_tidy_selectors() -> None:
    settings = settings_from(
        {
            "regions": "us-east-1, us-gov-west-1, us-east-1",
            "include_tags": " Env = Prod ,aws:autoscaling:groupName=web,Env=Prod",
        },
    )
    assert settings.regions == ("us-east-1", "us-gov-west-1")
    assert settings.include_tags == ("Env=Prod", "aws:autoscaling:groupName=web")
    assert parse_tag_selectors(None, "include_tags") == ()


@pytest.mark.parametrize(
    "credentials, fields, named",
    [
        ({}, {}, ALLOW_DEFAULT_CREDENTIALS_ENV_VAR),
        ({"access_key_id": "AKIAEXAMPLE"}, {}, "half an access key"),
        (
            {"access_key_id": "AKIAEXAMPLE", "secret_access_key": "s"},
            {"external_id": "x"},
            "without 'role_arn'",
        ),
        ({}, {"role_arn": "arn:aws:iam::123456789012:role/r"}, "no 'access_key_id'"),
    ],
    ids=["keyless", "half-key", "external-id-alone", "role-without-key-or-opt-in"],
)
def test_credentials_that_cannot_be_used_fail_as_not_configured(
    credentials: dict[str, str],
    fields: dict[str, str],
    named: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv(ALLOW_DEFAULT_CREDENTIALS_ENV_VAR, raising=False)
    with pytest.raises(DiscoveryConfigurationError, match=named) as exc:
        source_session(credentials, {"regions": REGION, **fields})
    assert failure_code(exc.value) is DiscoveryErrorCode.NOT_CONFIGURED


def test_an_access_key_is_used_as_given() -> None:
    session = source_session(
        {"access_key_id": "AKIAEXAMPLE", "secret_access_key": "secret"},
        {"regions": REGION},
    )
    credentials = session.get_credentials()
    assert credentials is not None
    assert credentials.access_key == "AKIAEXAMPLE"


def test_a_role_is_assumed_lazily_and_refreshably() -> None:
    """Nothing is fetched until a call needs it, and the session refreshes before the
    role's hour is up."""
    session = source_session(
        {"access_key_id": "AKIAEXAMPLE", "secret_access_key": "secret"},
        {
            "regions": REGION,
            "role_arn": "arn:aws:iam::123456789012:role/arthur-discovery",
            "external_id": "abc",
        },
    )
    credentials = session.get_credentials()
    assert credentials is not None
    assert credentials.method == "assume-role"
    assert session.region_name == REGION, "STS is asked in the first region scanned"
    assert hasattr(credentials, "refresh_needed")


def test_the_engine_s_own_credentials_need_the_engine_to_opt_in(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(ALLOW_DEFAULT_CREDENTIALS_ENV_VAR, "true")
    assert isinstance(source_session({}, {"regions": REGION}), boto3.Session)


# --- the seams ------------------------------------------------------------------------


def test_registered_with_its_secrets_declared_and_the_optional_protocols() -> None:
    assert source_connectors()[VENDOR] is Ec2Connector
    connector = Ec2Connector()
    assert connector.SENSITIVE_FIELDS == frozenset(
        {"access_key_id", "secret_access_key"},
    )
    assert isinstance(connector, ReportsDeviceCoverage)
    assert isinstance(connector, AcceptsStopCheck)
    assert connector.device_coverage() is None, "nothing read yet"


def test_a_stop_check_ends_the_scan_after_the_instance_in_hand() -> None:
    aws = FakeAws(
        {REGION: [[instance("1"), instance("2")]], "eu-west-1": [[instance("3")]]},
        inventory={iid(i): reported() for i in "123"},
    )
    connector = connector_for(aws)
    connector.stop_when(lambda: True)
    records = scan(aws, fields={"regions": f"{REGION},eu-west-1"}, connector=connector)

    assert [r.external_id for r in records] == [f"{iid('1')}:codex-cli"]
    assert aws.reads() == [iid("1")]
