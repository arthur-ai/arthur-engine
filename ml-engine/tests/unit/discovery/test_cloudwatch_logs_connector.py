"""CloudWatch Logs connector: paging FilterLogEvents and turning lines into records.

A fake `logs` client stands in for boto3's. Its answers follow the CloudWatch Logs API
shapes -- `FilterLogEvents` pages of `events` with `timestamp` in epoch milliseconds
and a `nextToken` that may come with an empty page, errors as botocore `ClientError`s
with the JSON protocol's 400 -- and the lines are those in `test_network_extractor`.
None was captured from a live account: no sandbox credentials were available.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Optional

import pytest
from arthur_client.api_bindings import DiscoverySourceConfigSpec
from arthur_common.models.agent_governance_schemas import (
    NetworkAgentCreationSource,
    RunsOn,
)
from botocore.exceptions import (
    ClientError,
    ConnectTimeoutError,
    EndpointConnectionError,
    NoCredentialsError,
)
from test_network_extractor import (
    FLOW_LINE,
    FLOW_NODATA_LINE,
    RESOLVER_ENDPOINT_LINE,
    RESOLVER_LINE,
)

from arthur_client_support import TEST_DISCOVERY_SOURCE_SUPPORTED
from discovery import source_connectors
from discovery.network.cloudwatch_logs import client as client_module
from discovery.network.cloudwatch_logs.client import (
    PAGE_LIMIT,
    CloudWatchLogsClient,
    CloudWatchLogsError,
    CloudWatchLogsSettings,
    logs_client_for,
)
from discovery.network.cloudwatch_logs.connector import (
    ALLOW_DEFAULT_CREDENTIALS_ENV_VAR,
    BATCH_SIZE,
    VENDOR,
    CloudWatchLogsConnector,
    extra_destinations_from,
    settings_from,
)
from discovery.network.records import MAX_DESTINATIONS
from job_executors.discovery_output_contract import check_batch
from job_executors.discovery_scan import (
    AcceptsStopCheck,
    DiscoveryConfigurationError,
    DiscoveryErrorCode,
    failure_code,
)
from job_executors.fetch_discovered_agents_executor import _CREATION_SOURCE_TYPES

LOG = logging.getLogger("test.cloudwatch_logs")
SECRET = "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
CREDS = {"secret_access_key": SECRET}
FIELDS = {
    "region": "us-west-2",
    "log_group_names": "/aws/route53resolver/prod-vpc",
    "log_format": "route53_resolver_query_log",
    "access_key_id": "AKIAIOSFODNN7EXAMPLE",
}
FLOW_FIELDS = {
    **FIELDS,
    "log_group_names": "/aws/vpc/flow-logs",
    "log_format": "vpc_flow_log_v2",
    "extra_inference_hosts": "104.18.32.0/23",
}
NOW = 1_792_000_000
EVENT_MS = 1_791_999_000_000


def event(message: str, ms: int = EVENT_MS) -> dict[str, Any]:
    return {
        "logStreamName": "vpc-7f3a91c2_i-0f1e2d3c4b5a69788",
        "timestamp": ms,
        "message": message,
        "ingestionTime": ms + 1500,
        "eventId": "37854512365477287341546538920237617153256784915087015936",
    }


def page(*messages: str, token: Optional[str] = None) -> dict[str, Any]:
    body: dict[str, Any] = {
        "events": [event(m) for m in messages],
        "searchedLogStreams": [],
        "ResponseMetadata": {"HTTPStatusCode": 200},
    }
    if token:
        body["nextToken"] = token
    return body


def aws_error(code: str, http: int = 400) -> ClientError:
    return ClientError(
        {
            "Error": {"Code": code, "Message": f"{code} message"},
            "ResponseMetadata": {"HTTPStatusCode": http},
        },
        "FilterLogEvents",
    )


class FakeLogs:
    """boto3's `logs` client, as far as the connector calls it: answers in order,
    the last one repeated."""

    def __init__(self, answers: Optional[list[Any]] = None) -> None:
        self.answers = list(answers) if answers is not None else [page(RESOLVER_LINE)]
        self.calls: list[dict[str, Any]] = []

    def filter_log_events(self, **kw: Any) -> Any:
        self.calls.append(kw)
        answer = self.answers.pop(0) if len(self.answers) > 1 else self.answers[0]
        if isinstance(answer, BaseException):
            raise answer
        return answer


def connector_with(
    logs: FakeLogs,
    sleeps: Optional[list[float]] = None,
    max_events: int = 1_000_000,
) -> CloudWatchLogsConnector:
    slept = sleeps if sleeps is not None else []
    return CloudWatchLogsConnector(
        client_factory=lambda s, log: CloudWatchLogsClient(
            s, logger=log, logs=logs, sleep=slept.append
        ),
        now=lambda: float(NOW),
        max_events=max_events,
    )


def config(query: str = "") -> DiscoverySourceConfigSpec:
    return DiscoverySourceConfigSpec.model_construct(name="vpc logs", query=query)


def scan(
    logs: FakeLogs,
    *,
    lookback_hours: int = 24,
    fields: Optional[dict[str, str]] = None,
    creds: Optional[dict[str, Optional[str]]] = None,
    query: str = "",
    connector: Optional[CloudWatchLogsConnector] = None,
) -> list[Any]:
    batches = (connector or connector_with(logs)).scan(
        config(query),
        lookback_hours,
        CREDS if creds is None else creds,
        FIELDS if fields is None else fields,
        LOG,
    )
    return [record for batch in batches for record in batch]


def connection_test_category(exc: BaseException) -> str:
    if not TEST_DISCOVERY_SOURCE_SUPPORTED:
        pytest.skip("installed arthur-client predates TEST_DISCOVERY_SOURCE")
    from job_executors.discovery_source_test_executor import _classify

    return str(_classify(exc, contacted=False).category.value)


# -- registration --------------------------------------------------------------------


def test_the_connector_is_registered_for_its_vendor() -> None:
    assert source_connectors()[VENDOR] is CloudWatchLogsConnector
    assert VENDOR == "aws_network"


def test_the_connector_declares_exactly_its_secrets() -> None:
    assert CloudWatchLogsConnector.SENSITIVE_FIELDS == frozenset({"secret_access_key"})


def test_fetched_network_evidence_keeps_its_class() -> None:
    assert _CREATION_SOURCE_TYPES["network"] == "NETWORK"


def test_the_settings_never_print_the_secret_key() -> None:
    assert SECRET not in repr(settings_from(CREDS, FIELDS))


# -- reading the log groups ------------------------------------------------------------


def test_each_log_group_is_read_for_the_lookback() -> None:
    logs = FakeLogs()
    scan(logs, lookback_hours=48, fields={**FIELDS, "log_group_names": "/a, /b\n/a"})
    assert [c["logGroupIdentifier"] for c in logs.calls] == ["/a", "/b"]
    assert {c["endTime"] for c in logs.calls} == {NOW * 1000}
    assert {c["startTime"] for c in logs.calls} == {(NOW - 48 * 3600) * 1000}
    assert {c["limit"] for c in logs.calls} == {PAGE_LIMIT}


def test_a_lookback_of_zero_reads_everything_retained() -> None:
    logs = FakeLogs()
    scan(logs, lookback_hours=0)
    assert logs.calls[0]["startTime"] == 0


def test_pages_are_followed_through_empty_ones_to_the_end() -> None:
    logs = FakeLogs(
        [
            page(RESOLVER_LINE, token="t1"),
            page(token="t2"),
            page(RESOLVER_ENDPOINT_LINE),
        ]
    )
    records = scan(logs)
    assert [c.get("nextToken") for c in logs.calls] == [None, "t1", "t2"]
    assert len(records) == 2


def test_a_repeated_token_ends_paging() -> None:
    logs = FakeLogs([page(RESOLVER_LINE, token="t1")])
    scan(logs)
    assert len(logs.calls) == 2


def test_a_config_query_is_ignored_and_says_so(
    caplog: pytest.LogCaptureFixture,
) -> None:
    with caplog.at_level(logging.WARNING):
        scan(FakeLogs(), query="fields @message")
    assert "query is ignored" in caplog.text


# -- the connector's stop check -------------------------------------------------------


def test_the_connector_accepts_a_stop_check() -> None:
    assert isinstance(CloudWatchLogsConnector(), AcceptsStopCheck)


def test_a_stop_before_reading_sends_nothing() -> None:
    logs = FakeLogs()
    connector = connector_with(logs)
    connector.stop_when(lambda: True)
    assert scan(logs, connector=connector) == []
    assert logs.calls == []


def test_a_stop_between_pages_reports_what_was_read() -> None:
    logs = FakeLogs([page(RESOLVER_LINE, token="t1"), page(RESOLVER_ENDPOINT_LINE)])
    connector = connector_with(logs)
    connector.stop_when(lambda: len(logs.calls) >= 1)
    records = scan(logs, connector=connector)
    assert len(logs.calls) == 1
    assert [r.external_id for r in records] == [
        "111122223333/us-west-2/instance/i-0f1e2d3c4b5a69788"
    ]


# -- records -------------------------------------------------------------------------


def test_an_instance_is_one_record_whatever_hosts_it_called() -> None:
    second = RESOLVER_LINE.replace(
        "bedrock-runtime.us-west-2.amazonaws.com.", "api.openai.com."
    ).replace("172.31.5.20", "172.31.5.21")
    unrelated = RESOLVER_LINE.replace(
        "bedrock-runtime.us-west-2.amazonaws.com.", "s3.us-west-2.amazonaws.com."
    )
    later = RESOLVER_LINE.replace("05:59:58Z", "07:00:00Z")
    (record,) = scan(FakeLogs([page(RESOLVER_LINE, second, unrelated, later)]))
    assert record.external_id == "111122223333/us-west-2/instance/i-0f1e2d3c4b5a69788"
    assert record.name == "i-0f1e2d3c4b5a69788 calling Amazon Bedrock, OpenAI"
    assert record.runs_on is RunsOn.AWS
    assert record.last_seen == datetime(2026, 10, 14, 7, 0, tzinfo=timezone.utc)
    bedrock, openai = record.creation_source.destinations
    assert (bedrock.host, bedrock.provider) == (
        "bedrock-runtime.us-west-2.amazonaws.com",
        "Amazon Bedrock",
    )
    assert (openai.host, openai.provider) == ("api.openai.com", "OpenAI")


def test_a_record_is_a_network_finding_addressed_by_the_host_where_it_is() -> None:
    """The host in instance and resource_id, its account and region in scope, never
    the VPC, which only some logs carry; the VPC is observed instead."""
    (record,) = scan(FakeLogs())
    source = record.creation_source
    assert isinstance(source, NetworkAgentCreationSource)
    assert source.vendor == VENDOR
    assert source.address.resource_kind == "instance"
    assert source.address.instance == "i-0f1e2d3c4b5a69788"
    assert source.address.scope == "111122223333/us-west-2"
    assert source.address.resource_id == "i-0f1e2d3c4b5a69788"
    assert source.address.query is None
    assert source.observations.host_name == "i-0f1e2d3c4b5a69788"
    assert source.observations.host_group == "vpc-7f3a91c2"
    assert source.observations.service_names == []


def test_last_seen_is_the_lines_own_time() -> None:
    later = RESOLVER_LINE.replace("05:59:58Z", "07:00:00Z")
    (record,) = scan(FakeLogs([page(RESOLVER_LINE, later)]))
    assert record.last_seen == datetime(2026, 10, 14, 7, 0, tzinfo=timezone.utc)


def test_a_line_without_a_time_falls_back_to_the_events() -> None:
    (record,) = scan(
        FakeLogs(
            [
                page(
                    RESOLVER_LINE.replace(
                        ',"query_timestamp":"2026-10-14T05:59:58Z"', ""
                    )
                )
            ]
        )
    )
    assert record.last_seen == datetime.fromtimestamp(EVENT_MS / 1000, tz=timezone.utc)


def test_a_source_without_an_instance_is_its_address_in_its_vpc() -> None:
    (record,) = scan(FakeLogs([page(RESOLVER_ENDPOINT_LINE)]))
    assert record.external_id == "111122223333/us-west-2/ip/vpc-7f3a91c2/10.20.0.15"
    assert record.name == "10.20.0.15 in vpc-7f3a91c2 calling OpenAI"
    assert record.runs_on is RunsOn.UNKNOWN
    address = record.creation_source.address
    assert (address.resource_kind, address.instance, address.scope) == (
        "ip",
        "vpc-7f3a91c2",
        "111122223333/us-west-2",
    )


def test_flow_logs_match_only_the_sources_own_ranges() -> None:
    elsewhere = FLOW_LINE.replace("104.18.33.45", "52.94.12.20")
    (record,) = scan(
        FakeLogs([page(FLOW_LINE, elsewhere, FLOW_NODATA_LINE)]), fields=FLOW_FIELDS
    )
    assert record.external_id == "111122223333/us-west-2/eni/eni-0a1b2c3d4e5f67890"
    assert record.name == "eni-0a1b2c3d4e5f67890 calling 104.18.32.0/23"
    address = record.creation_source.address
    assert (address.resource_kind, address.instance, address.scope) == (
        "eni",
        "eni-0a1b2c3d4e5f67890",
        "111122223333/us-west-2",
    )
    assert record.last_seen == datetime.fromtimestamp(1792000000, tz=timezone.utc)


def test_flow_logs_without_ranges_find_nothing(
    caplog: pytest.LogCaptureFixture,
) -> None:
    fields = {k: v for k, v in FLOW_FIELDS.items() if k != "extra_inference_hosts"}
    with caplog.at_level(logging.INFO):
        assert scan(FakeLogs([page(FLOW_LINE)]), fields=fields) == []
    assert "1 extracted" in caplog.text


def test_a_custom_regex_reads_a_custom_log() -> None:
    fields = {
        **FIELDS,
        "log_format": "custom",
        "extraction_regex": r"src=(?<src>\S+) vpc=(?<vpc_id>\S+) host=(?<dest>\S+)",
    }
    (record,) = scan(
        FakeLogs([page("ts=1 src=10.9.8.7 vpc=vpc-1 host=api.groq.com action=allow")]),
        fields=fields,
    )
    assert record.external_id == "us-west-2/ip/vpc-1/10.9.8.7"
    assert record.name == "10.9.8.7 in vpc-1 calling Groq"


def test_an_address_with_no_network_is_counted_not_guessed(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """One address in two VPCs is two hosts, so a line naming neither an instance, an
    interface nor a VPC cannot be placed."""
    fields = {
        **FIELDS,
        "log_format": "custom",
        "extraction_regex": r"src=(?<src>\S+) host=(?<dest>\S+)",
    }
    with caplog.at_level(logging.INFO):
        records = scan(
            FakeLogs([page("ts=1 src=10.9.8.7 host=api.groq.com action=allow")]),
            fields=fields,
        )
    assert records == []
    assert "1 call(s) to inference hosts skipped" in caplog.text
    assert "10.9.8.7" not in caplog.text


def test_a_records_destinations_are_capped_busiest_first() -> None:
    lines = [
        RESOLVER_LINE.replace("bedrock-runtime.us-west-2", f"bedrock-runtime.r{i}")
        for i in range(MAX_DESTINATIONS + 5)
    ]
    lines += [RESOLVER_LINE.replace("bedrock-runtime.us-west-2", "bedrock-runtime.r9")]
    (record,) = scan(FakeLogs([page(*lines)]))
    destinations = record.creation_source.destinations
    assert len(destinations) == MAX_DESTINATIONS
    assert destinations[0].host == "bedrock-runtime.r9.amazonaws.com"


def test_flow_log_destinations_are_the_addresses_called() -> None:
    (record,) = scan(FakeLogs([page(FLOW_LINE, FLOW_LINE)]), fields=FLOW_FIELDS)
    (destination,) = record.creation_source.destinations
    assert (destination.host, destination.provider) == (
        "104.18.33.45",
        "104.18.32.0/23",
    )


def test_many_providers_are_counted_in_the_name() -> None:
    hosts = ["api.openai.com", "api.anthropic.com", "api.groq.com", "api.x.ai"]
    lines = [
        RESOLVER_LINE.replace("bedrock-runtime.us-west-2.amazonaws.com", h)
        for h in hosts
    ]
    (record,) = scan(FakeLogs([page(*lines)]))
    assert (
        record.name == "i-0f1e2d3c4b5a69788 calling Anthropic, Groq, OpenAI and 1 more"
    )


def test_output_satisfies_the_discovery_output_contract() -> None:
    check_batch(scan(FakeLogs([page(RESOLVER_LINE, RESOLVER_ENDPOINT_LINE)])), "src")


def test_records_are_batched() -> None:
    lines = [
        RESOLVER_ENDPOINT_LINE.replace("10.20.0.15", f"10.20.{i // 250}.{i % 250}")
        for i in range(BATCH_SIZE + 3)
    ]
    batches = list(
        connector_with(FakeLogs([page(*lines)])).scan(config(), 24, CREDS, FIELDS, LOG)
    )
    assert [len(b) for b in batches] == [BATCH_SIZE, 3]


def test_a_capped_scan_is_reported_before_the_first_batch(
    caplog: pytest.LogCaptureFixture,
) -> None:
    logs = FakeLogs([page(RESOLVER_LINE, RESOLVER_LINE, token="t1")])
    batches = connector_with(logs, max_events=1).scan(config(), 24, CREDS, FIELDS, LOG)
    with caplog.at_level(logging.WARNING):
        next(iter(batches))
    assert "1-event cap" in caplog.text
    assert len(logs.calls) == 1


def test_a_log_nothing_matches_names_the_likely_cause(
    caplog: pytest.LogCaptureFixture,
) -> None:
    with caplog.at_level(logging.WARNING):
        scan(FakeLogs([page(FLOW_LINE)]))
    assert "no line matched the extractor" in caplog.text


def test_what_was_found_is_logged_without_log_values(
    caplog: pytest.LogCaptureFixture,
) -> None:
    with caplog.at_level(logging.DEBUG):
        scan(FakeLogs([page(RESOLVER_LINE, RESOLVER_ENDPOINT_LINE)]))
    assert "1 source(s) called Amazon Bedrock" in caplog.text
    for value in ("172.31.5.20", "i-0f1e2d3c4b5a69788", "vpc-7f3a91c2", "111122223333"):
        assert value not in caplog.text


# -- configuration ---------------------------------------------------------------------


def test_missing_fields_are_named() -> None:
    with pytest.raises(DiscoveryConfigurationError, match="region, log_group_names"):
        settings_from(CREDS, {"access_key_id": "AKIA"})


@pytest.mark.parametrize(
    "fields, match",
    [
        ({**FIELDS, "region": "us-west"}, "not an AWS region"),
        ({**FIELDS, "log_group_names": "bad group!"}, "neither a log group name"),
        (
            {**FIELDS, "log_group_names": ",".join(f"/g{i}" for i in range(21))},
            "at most 20",
        ),
        ({**FIELDS, "role_arn": "role/x"}, "not an IAM role ARN"),
        ({**FIELDS, "external_id": "e"}, "without role_arn"),
        ({**FIELDS, "log_format": "syslog"}, "must be one of"),
        (
            {k: v for k, v in FIELDS.items() if k != "log_format"},
            "missing required field.*log_format",
        ),
        ({**FIELDS, "log_format": "custom"}, "custom needs extraction_regex"),
        (
            {**FIELDS, "log_format": "custom", "extraction_regex": r"(?P<src>\S+)"},
            "extraction_regex has no named group",
        ),
        ({**FIELDS, "extra_inference_hosts": "localhost"}, "entry 1 needs"),
    ],
)
def test_bad_configuration_is_refused_before_anything_is_sent(
    fields: dict[str, str], match: str
) -> None:
    logs = FakeLogs()
    with pytest.raises(DiscoveryConfigurationError, match=match) as exc:
        scan(logs, fields=fields)
    assert failure_code(exc.value) is DiscoveryErrorCode.NOT_CONFIGURED
    assert logs.calls == []


def test_a_preset_ignores_a_regex_left_from_custom() -> None:
    fields = {**FIELDS, "extraction_regex": r"(?P<src>x)"}
    assert len(scan(FakeLogs(), fields=fields)) == 1


def test_a_log_group_arn_from_another_account_is_accepted() -> None:
    arn = "arn:aws:logs:us-west-2:444455556666:log-group:/aws/route53resolver/shared"
    assert settings_from(CREDS, {**FIELDS, "log_group_names": arn}).log_groups == (arn,)


def test_half_an_access_key_is_refused() -> None:
    with pytest.raises(DiscoveryConfigurationError, match="only one of"):
        settings_from({}, FIELDS)


def test_no_access_key_needs_the_engine_to_opt_in(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    keyless = {k: v for k, v in FIELDS.items() if k != "access_key_id"}
    monkeypatch.delenv(ALLOW_DEFAULT_CREDENTIALS_ENV_VAR, raising=False)
    with pytest.raises(
        DiscoveryConfigurationError, match=ALLOW_DEFAULT_CREDENTIALS_ENV_VAR
    ):
        settings_from({}, keyless)
    monkeypatch.setenv(ALLOW_DEFAULT_CREDENTIALS_ENV_VAR, "true")
    assert settings_from({}, keyless).access_key_id is None


def test_extra_destinations_are_lowercased_and_deduplicated() -> None:
    raw = "LLM.Example.com., llm.example.com\n10.0.0.0/8"
    assert extra_destinations_from({"extra_inference_hosts": raw}) == (
        "llm.example.com",
        "10.0.0.0/8",
    )


def test_too_many_extra_destinations_are_refused() -> None:
    raw = ",".join(f"h{i}.example.com" for i in range(101))
    with pytest.raises(DiscoveryConfigurationError, match="at most 100"):
        extra_destinations_from({"extra_inference_hosts": raw})


# -- the boto3 client ----------------------------------------------------------------


def test_the_logs_client_owns_no_retries_and_fits_the_preview_deadline() -> None:
    logs = logs_client_for(CloudWatchLogsSettings("eu-west-1", ("/g",), "AKIA", "s"))
    config = logs.meta.config
    assert config.retries["total_max_attempts"] == 1
    assert config.connect_timeout + config.read_timeout < 120
    assert logs.meta.region_name == "eu-west-1"


def test_a_role_is_assumed_with_its_external_id(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[str, dict[str, Any]]] = []

    class FakeSession:
        def __init__(self, **kw: Any) -> None:
            calls.append(("session", kw))

        def client(self, service: str, **kw: Any) -> Any:
            calls.append((service, kw))
            return self if service == "sts" else "logs-client"

        def assume_role(self, **kw: Any) -> dict[str, Any]:
            calls.append(("assume_role", kw))
            return {
                "Credentials": {
                    "AccessKeyId": "ASIATEMP",
                    "SecretAccessKey": "temp-secret",
                    "SessionToken": "temp-token",
                }
            }

    monkeypatch.setattr(client_module.boto3.session, "Session", FakeSession)
    settings = CloudWatchLogsSettings(
        "us-east-1",
        ("/g",),
        "AKIA",
        "s",
        role_arn="arn:aws:iam::123456789012:role/arthur-discovery",
        external_id="ext-1",
    )
    assert logs_client_for(settings) == "logs-client"
    (assume,) = [kw for op, kw in calls if op == "assume_role"]
    assert assume["RoleArn"] == settings.role_arn
    assert assume["ExternalId"] == "ext-1"
    assert [kw for op, kw in calls if op == "session"][-1]["aws_session_token"] == (
        "temp-token"
    )


# -- failures ------------------------------------------------------------------------


@pytest.mark.parametrize(
    "code, status, failure, category",
    [
        (
            "UnrecognizedClientException",
            401,
            DiscoveryErrorCode.AUTHENTICATION_FAILED,
            "authentication",
        ),
        (
            "ExpiredTokenException",
            401,
            DiscoveryErrorCode.AUTHENTICATION_FAILED,
            "authentication",
        ),
        (
            "AccessDeniedException",
            403,
            DiscoveryErrorCode.PERMISSION_DENIED,
            "authorization",
        ),
        (
            "InternalFailure",
            400,
            DiscoveryErrorCode.PROVIDER_ERROR,
            "vendor_error",
        ),
    ],
)
def test_a_refusal_carries_the_status_its_code_means(
    code: str,
    status: int,
    failure: DiscoveryErrorCode,
    category: str,
) -> None:
    with pytest.raises(ClientError) as exc:
        scan(FakeLogs([aws_error(code)]))
    assert getattr(exc.value, "status_code") == status
    assert failure_code(exc.value) is failure
    assert connection_test_category(exc.value) == category


@pytest.mark.parametrize(
    "code", ["ResourceNotFoundException", "InvalidParameterException"]
)
def test_a_log_group_aws_refuses_is_the_sources_to_fix(code: str) -> None:
    with pytest.raises(DiscoveryConfigurationError, match="log_group_names") as exc:
        scan(FakeLogs([aws_error(code)]))
    assert failure_code(exc.value) is DiscoveryErrorCode.NOT_CONFIGURED
    assert getattr(exc.value, "status_code", None) is None
    assert exc.value.__cause__ is None and exc.value.__context__ is None
    assert "HTTP" not in str(exc.value)
    assert connection_test_category(exc.value) == "configuration"


def test_throttling_and_dropped_connections_are_retried() -> None:
    sleeps: list[float] = []
    logs = FakeLogs(
        [
            aws_error("ThrottlingException"),
            EndpointConnectionError(endpoint_url="https://logs.x"),
            page(RESOLVER_LINE),
        ]
    )
    batches = connector_with(logs, sleeps).scan(config(), 24, CREDS, FIELDS, LOG)
    assert len([r for b in batches for r in b]) == 1
    assert len(logs.calls) == 3 and len(sleeps) == 2


def test_an_unreachable_endpoint_reads_as_the_network() -> None:
    with pytest.raises(ConnectionError) as exc:
        scan(FakeLogs([EndpointConnectionError(endpoint_url="https://logs.x")]))
    assert failure_code(exc.value) is DiscoveryErrorCode.PROVIDER_ERROR
    assert connection_test_category(exc.value) == "network"


def test_a_connect_timeout_reads_as_a_timeout() -> None:
    with pytest.raises(TimeoutError) as exc:
        scan(FakeLogs([ConnectTimeoutError(endpoint_url="https://logs.x")]))
    assert connection_test_category(exc.value) == "timeout"


def test_no_credential_at_all_is_the_sources_configuration() -> None:
    with pytest.raises(DiscoveryConfigurationError, match="no AWS credential") as exc:
        scan(FakeLogs([NoCredentialsError()]))
    assert failure_code(exc.value) is DiscoveryErrorCode.NOT_CONFIGURED


@pytest.mark.parametrize("body", [["not", "an", "object"], {"events": "x"}])
def test_an_answer_that_is_not_a_page_of_events_is_the_vendors_error(
    body: Any,
) -> None:
    with pytest.raises(CloudWatchLogsError) as exc:
        scan(FakeLogs([body]))
    assert exc.value.status_code == 200


def test_malformed_events_in_a_page_are_skipped() -> None:
    body = page(RESOLVER_LINE)
    body["events"] += [{"message": 3, "timestamp": 1}, "x", {"message": "m"}]
    assert len(scan(FakeLogs([body]))) == 1


def test_the_scan_never_logs_the_secret(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.DEBUG):
        scan(FakeLogs())
        with pytest.raises(ClientError):
            scan(FakeLogs([aws_error("UnrecognizedClientException")]))
    assert SECRET not in caplog.text


# -- a page in the shape AWS documents --------------------------------------------------

# A FilterLogEvents answer for a Route 53 Resolver query log group, field for field as
# the API reference describes it.
DOCUMENTED_FILTER_LOG_EVENTS: dict[str, Any] = {
    "events": [
        {
            "logStreamName": "vpc-7f3a91c2_i-0f1e2d3c4b5a69788",
            "timestamp": 1791971998000,
            "message": RESOLVER_LINE,
            "ingestionTime": 1791972003412,
            "eventId": "37854512365477287341546538920237617153256784915087015936",
        },
        {
            "logStreamName": "vpc-7f3a91c2_rslvr-in-0123456789abcdef0",
            "timestamp": 1791972072000,
            "message": RESOLVER_ENDPOINT_LINE,
            "ingestionTime": 1791972079021,
            "eventId": "37854513970989553204946487019348271846539301843812761600",
        },
    ],
    "searchedLogStreams": [],
    "ResponseMetadata": {
        "RequestId": "5b0f0b16-7f7e-4b0c-9d4c-5b1d6f3a2e10",
        "HTTPStatusCode": 200,
        "HTTPHeaders": {"content-type": "application/x-amz-json-1.1"},
        "RetryAttempts": 0,
    },
}


def test_responses_in_the_shape_aws_documents_parse() -> None:
    records = sorted(
        scan(FakeLogs([DOCUMENTED_FILTER_LOG_EVENTS])), key=lambda r: r.external_id
    )
    assert [r.external_id for r in records] == [
        "111122223333/us-west-2/instance/i-0f1e2d3c4b5a69788",
        "111122223333/us-west-2/ip/vpc-7f3a91c2/10.20.0.15",
    ]
    assert records[0].name == "i-0f1e2d3c4b5a69788 calling Amazon Bedrock"
