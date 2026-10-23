"""The Bedrock connector, against a fake Bedrock, AgentCore, CloudTrail and STS.

What matters most here is who is reported. An agent or runtime the account lists is
reported once, by its ARN; a role CloudTrail saw calling a model is reported once per
region, with the models it called; a person -- an IAM Identity Center role, the root
user -- is counted and never reported. And what is read is only ever a list: the call
that would return a runtime's environment variables is never made.

The fake checks every request against botocore's own service model, so a call the real
API would refuse fails here rather than passing.
"""

import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import boto3
import pytest
from arthur_common.models.agent_governance_schemas import (
    CloudAgentCreationSource,
    RunsOn,
    SourceAddress,
)
from botocore.exceptions import ClientError, EndpointConnectionError
from botocore.session import Session as BotocoreSession
from botocore.validate import ParamValidator

from discovery import source_connectors
from discovery.cloud.aws_bedrock.client import (
    LOOKUP_INTERVAL_SECONDS,
    BedrockClient,
    BedrockError,
)
from discovery.cloud.aws_bedrock.connector import (
    ALLOW_DEFAULT_CREDENTIALS_ENV_VAR,
    VENDOR,
    BedrockConnector,
    settings_from,
    source_session,
)
from discovery.retry import MAX_ATTEMPTS
from job_executors.discovery_output_contract import check_batch
from job_executors.discovery_scan import (
    AcceptsStopCheck,
    DiscoveryConfigurationError,
    DiscoveryErrorCode,
    failure_code,
)

LOG = logging.getLogger("discovery-test")
ACCOUNT = "123456789012"
REGION = "us-east-1"
FIELDS = {"regions": REGION}
NOW = datetime(2026, 10, 12, 13, 30, tzinfo=timezone.utc)
UPDATED = datetime(2026, 9, 1, 8, 0, tzinfo=timezone.utc)
SERVICES = ("bedrock-agent", "bedrock-agentcore-control", "cloudtrail", "sts")
MODELS = {svc: BotocoreSession().get_service_model(svc) for svc in SERVICES}
ALLOWED_OPERATIONS = {
    "ListAgents",
    "ListAgentRuntimes",
    "LookupEvents",
    "GetCallerIdentity",
}

WORKLOAD_ROLE = f"arn:aws:iam::{ACCOUNT}:role/service-role/support-bot"
OTHER_ROLE = f"arn:aws:iam::{ACCOUNT}:role/batch-summariser"
SSO_ROLE = (
    f"arn:aws:iam::{ACCOUNT}:role/aws-reserved/sso.amazonaws.com/"
    f"AWSReservedSSO_PowerUserAccess_0123456789abcdef"
)
CLAUDE = "anthropic.claude-3-5-sonnet-20240620-v1:0"
TITAN = "amazon.titan-text-express-v1"


def validate(service: str, operation: str, params: dict[str, Any]) -> None:
    shape = MODELS[service].operation_model(operation).input_shape
    if shape is None:
        assert not params, f"{operation} takes no parameters"
        return
    report = ParamValidator().validate(params, shape)
    if report.has_errors():
        raise AssertionError(report.generate_report())


def client_error(code: str, operation: str, message: str = "no") -> ClientError:
    return ClientError({"Error": {"Code": code, "Message": message}}, operation)


def agent(ident: str, name: Optional[str] = None, **over: Any) -> dict[str, Any]:
    """An agent summary as ListAgents returns it: no ARN."""
    body: dict[str, Any] = {
        "agentId": ident,
        "agentName": name or f"agent-{ident}",
        "agentStatus": "PREPARED",
        "updatedAt": UPDATED,
        "latestAgentVersion": "1",
    }
    body.update(over)
    return body


def runtime(ident: str, region: str = REGION, **over: Any) -> dict[str, Any]:
    body: dict[str, Any] = {
        "agentRuntimeArn": f"arn:aws:bedrock-agentcore:{region}:{ACCOUNT}:runtime/{ident}",
        "agentRuntimeId": ident,
        "agentRuntimeVersion": "1",
        "agentRuntimeName": f"runtime_{ident}",
        "description": "",
        "lastUpdatedAt": UPDATED,
        "status": "READY",
    }
    body.update(over)
    return body


def event(
    role: Optional[str] = WORKLOAD_ROLE,
    model: Optional[str] = CLAUDE,
    name: str = "Converse",
    when: str = "2026-10-12T12:00:00Z",
    event_type: str = "AwsApiCall",
    user_arn: Optional[str] = None,
    identity_type: str = "AssumedRole",
    error_code: Optional[str] = None,
) -> dict[str, Any]:
    """A LookupEvents event, with its CloudTrailEvent JSON as AWS sends it."""
    who: dict[str, Any] = {"type": identity_type, "accountId": ACCOUNT}
    if role is not None:
        who["arn"] = f"arn:aws:sts::{ACCOUNT}:assumed-role/x/session-1"
        who["sessionContext"] = {
            "sessionIssuer": {"type": "Role", "arn": role, "accountId": ACCOUNT},
        }
    if user_arn is not None:
        who["arn"] = user_arn
    detail = {
        "eventVersion": "1.09",
        "userIdentity": who,
        "eventTime": when,
        "eventSource": "bedrock.amazonaws.com",
        "eventName": name,
        "awsRegion": REGION,
        "requestParameters": {"modelId": model} if model else None,
        "eventType": event_type,
        "recipientAccountId": ACCOUNT,
    }
    if error_code is not None:
        detail["errorCode"] = error_code
        detail["errorMessage"] = f"User: {who.get('arn')} is not authorized"
    return {
        "EventId": "e",
        "EventName": name,
        "EventSource": "bedrock.amazonaws.com",
        "EventTime": datetime.fromisoformat(when.replace("Z", "+00:00")),
        "CloudTrailEvent": json.dumps(detail),
    }


class FakeAws:
    """The four services' calls, and a log of what was asked.

    `agents[region]`, `runtimes[region]` and `events[region]` are each a list of pages.
    `errors[(service, operation)]` is a list of exceptions raised, one per call, before
    any answer is given; None lets that call through.
    """

    def __init__(
        self,
        agents: Optional[dict[str, list[list[dict[str, Any]]]]] = None,
        runtimes: Optional[dict[str, list[list[dict[str, Any]]]]] = None,
        events: Optional[dict[str, list[list[dict[str, Any]]]]] = None,
        errors: Optional[dict[tuple[str, str], list[Optional[Exception]]]] = None,
    ) -> None:
        self.agents = agents or {}
        self.runtimes = runtimes or {}
        self.events = events or {}
        self.errors = errors or {}
        self.calls: list[tuple[str, str, str, dict[str, Any]]] = []

    def client_for(self, service: str, region: str) -> "FakeClient":
        return FakeClient(self, service, region)

    def operations(self) -> set[str]:
        return {op for _, _, op, _ in self.calls}


class FakeClient:
    def __init__(self, aws: FakeAws, service: str, region: str) -> None:
        self._aws = aws
        self._service = service
        self._region = region

    def _record(self, operation: str, params: dict[str, Any]) -> None:
        validate(self._service, operation, params)
        self._aws.calls.append((self._service, self._region, operation, dict(params)))
        pending = self._aws.errors.get((self._service, operation))
        if pending:
            error = pending.pop(0)
            if error is not None:
                raise error

    def _page(
        self,
        pages: list[list[dict[str, Any]]],
        token: Optional[str],
        key: str,
        token_key: str,
    ) -> dict[str, Any]:
        index = int(token or 0)
        body: dict[str, Any] = {key: pages[index] if pages else []}
        if index + 1 < len(pages):
            body[token_key] = str(index + 1)
        return body

    def get_caller_identity(self, **params: Any) -> dict[str, Any]:
        self._record("GetCallerIdentity", params)
        return {
            "Account": ACCOUNT,
            "Arn": f"arn:aws:sts::{ACCOUNT}:assumed-role/scanner/arthur-ai-discovery",
            "UserId": "AROAEXAMPLE:arthur-ai-discovery",
        }

    def list_agents(self, **params: Any) -> dict[str, Any]:
        self._record("ListAgents", params)
        pages = self._aws.agents.get(self._region, [])
        return self._page(pages, params.get("nextToken"), "agentSummaries", "nextToken")

    def list_agent_runtimes(self, **params: Any) -> dict[str, Any]:
        self._record("ListAgentRuntimes", params)
        pages = self._aws.runtimes.get(self._region, [])
        return self._page(pages, params.get("nextToken"), "agentRuntimes", "nextToken")

    def lookup_events(self, **params: Any) -> dict[str, Any]:
        self._record("LookupEvents", params)
        pages = self._aws.events.get(self._region, [])
        return self._page(pages, params.get("NextToken"), "Events", "NextToken")


class FakeConfig:
    def __init__(self) -> None:
        self.query = ""
        self.vendor = VENDOR
        self.name = "acme bedrock"


class Sleeps:
    def __init__(self) -> None:
        self.seconds: list[float] = []

    def __call__(self, seconds: float) -> None:
        self.seconds.append(seconds)


def connector_for(aws: FakeAws, sleep: Optional[Sleeps] = None) -> BedrockConnector:
    return BedrockConnector(
        session_for=lambda creds, fields: boto3.Session(),
        clients_for=lambda session: aws.client_for,
        clock=lambda: NOW,
        sleep=sleep or Sleeps(),
    )


def scan(
    aws: FakeAws,
    fields: Optional[dict[str, str]] = None,
    connector: Optional[BedrockConnector] = None,
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


def by_kind(records: list[Any], kind: str) -> list[Any]:
    return [r for r in records if r.creation_source.address.resource_kind == kind]


# --- registration -----------------------------------------------------------------


def test_bedrock_is_registered_and_accepts_a_stop_check() -> None:
    connector = source_connectors()[VENDOR]()
    assert isinstance(connector, BedrockConnector)
    assert isinstance(connector, AcceptsStopCheck)
    assert BedrockConnector.SENSITIVE_FIELDS == {"access_key_id", "secret_access_key"}


# --- records ----------------------------------------------------------------------


def test_an_agent_is_a_cloud_record_on_aws_addressed_by_account_and_region() -> None:
    aws = FakeAws(agents={REGION: [[agent("AGENT12345", name="support")]]})
    [record] = scan(aws, fields={**FIELDS, "read_cloudtrail": "false"})

    assert record.external_id == f"arn:aws:bedrock:{REGION}:{ACCOUNT}:agent/AGENT12345"
    assert record.name == "support"
    assert record.last_seen == UPDATED
    assert record.runs_on is RunsOn.AWS
    source = record.creation_source
    assert isinstance(source, CloudAgentCreationSource)
    assert source.vendor == "aws_bedrock"
    assert source.address == SourceAddress(
        instance=ACCOUNT,
        scope=REGION,
        resource_kind="bedrock_agent",
        resource_id="AGENT12345",
    )
    check_batch([record], "Source config 'acme bedrock' (aws_bedrock)")


def test_a_runtime_is_addressed_by_its_id_and_identified_by_its_arn() -> None:
    aws = FakeAws(runtimes={REGION: [[runtime("support_rt-AbC123")]]})
    [record] = scan(aws, fields={**FIELDS, "read_cloudtrail": "false"})

    assert record.external_id == (
        f"arn:aws:bedrock-agentcore:{REGION}:{ACCOUNT}:runtime/support_rt-AbC123"
    )
    assert record.name == "runtime_support_rt-AbC123"
    assert record.creation_source.address == SourceAddress(
        instance=ACCOUNT,
        scope=REGION,
        resource_kind="agent_runtime",
        resource_id="support_rt-AbC123",
    )
    check_batch([record], "Source config 'acme bedrock' (aws_bedrock)")


def test_a_resource_without_an_update_time_is_skipped_and_named(
    caplog: pytest.LogCaptureFixture,
) -> None:
    aws = FakeAws(agents={REGION: [[agent("NOTIME", updatedAt=None)]]})
    with caplog.at_level(logging.WARNING):
        records = scan(aws, fields={**FIELDS, "read_cloudtrail": "false"})
    assert records == []
    assert "agent/NOTIME: Bedrock reported no update time" in caplog.text


def test_a_role_calling_models_is_one_record_per_region_with_its_models() -> None:
    aws = FakeAws(
        events={
            REGION: [
                [
                    event(model=CLAUDE, when="2026-10-12T10:00:00Z"),
                    event(model=TITAN, name="InvokeModel", when="2026-10-12T11:00:00Z"),
                    event(model=CLAUDE, when="2026-10-12T09:00:00Z"),
                ],
            ],
            "us-west-2": [[event(model=CLAUDE, when="2026-10-11T09:00:00Z")]],
        },
    )
    records = scan(
        aws,
        fields={"regions": f"{REGION},us-west-2", "list_agents": "false"},
    )

    assert len(records) == 2
    east, west = sorted(records, key=lambda r: r.creation_source.address.scope)
    assert east.external_id == f"{ACCOUNT}/{REGION}/iam_role/{WORKLOAD_ROLE}"
    assert east.name == f"support-bot calling {TITAN}, {CLAUDE}"
    assert [m.name for m in east.llm_models] == [TITAN, CLAUDE]
    assert east.last_seen == datetime(2026, 10, 12, 11, 0, tzinfo=timezone.utc)
    assert east.creation_source.address == SourceAddress(
        instance=ACCOUNT,
        scope=REGION,
        resource_kind="iam_role",
        resource_id=WORKLOAD_ROLE,
    )
    assert west.external_id == f"{ACCOUNT}/us-west-2/iam_role/{WORKLOAD_ROLE}"
    assert [m.name for m in west.llm_models] == [CLAUDE]
    check_batch(records, "Source config 'acme bedrock' (aws_bedrock)")


def test_an_iam_user_is_named_by_its_own_arn() -> None:
    user = f"arn:aws:iam::{ACCOUNT}:user/ci-runner"
    aws = FakeAws(
        events={REGION: [[event(role=None, user_arn=user, identity_type="IAMUser")]]},
    )
    [record] = scan(aws, fields={**FIELDS, "list_agents": "false"})
    assert record.external_id == f"{ACCOUNT}/{REGION}/iam_user/{user}"
    assert record.creation_source.address.resource_kind == "iam_user"
    assert record.name == f"ci-runner calling {CLAUDE}"


def test_an_sso_role_is_a_person_counted_and_not_reported(
    caplog: pytest.LogCaptureFixture,
) -> None:
    aws = FakeAws(
        events={REGION: [[event(role=SSO_ROLE) for _ in range(11)] + [event()]]},
    )
    with caplog.at_level(logging.INFO):
        records = scan(aws, fields={**FIELDS, "list_agents": "false"})

    assert [r.creation_source.address.resource_id for r in records] == [WORKLOAD_ROLE]
    assert "11 model call(s) by people (sso role: 11) counted, not reported" in (
        caplog.text
    )
    assert "AWSReservedSSO" not in " ".join(r.external_id for r in records)


def test_a_role_whose_every_call_was_refused_is_counted_and_not_reported(
    caplog: pytest.LogCaptureFixture,
) -> None:
    # As CloudTrail logs a refused Converse: errorCode set, no requestParameters.
    aws = FakeAws(
        events={
            REGION: [
                [
                    event(role=OTHER_ROLE, model=None, error_code="AccessDenied"),
                    event(model=CLAUDE, when="2026-10-12T10:00:00Z"),
                    event(
                        model=None,
                        error_code="AccessDenied",
                        when="2026-10-12T11:00:00Z",
                    ),
                ],
            ],
        },
    )
    with caplog.at_level(logging.INFO):
        [record] = scan(aws, fields={**FIELDS, "list_agents": "false"})

    assert record.creation_source.address.resource_id == WORKLOAD_ROLE
    assert [m.name for m in record.llm_models] == [CLAUDE]
    # The refused call is not when the role last called a model.
    assert record.last_seen == datetime(2026, 10, 12, 10, 0, tzinfo=timezone.utc)
    assert "2 refused model call(s) counted, not reported" in caplog.text
    assert "people and 2 refused call(s) not reported" in caplog.text


def test_a_call_that_failed_in_the_model_is_still_a_call() -> None:
    # Allowed, then failed while the model ran: the role did call it.
    aws = FakeAws(
        events={
            REGION: [
                [
                    event(
                        role=OTHER_ROLE,
                        model=TITAN,
                        error_code="ModelErrorException",
                        when="2026-10-12T11:00:00Z",
                    ),
                ],
            ],
        },
    )
    [record] = scan(aws, fields={**FIELDS, "list_agents": "false"})
    assert record.creation_source.address.resource_id == OTHER_ROLE
    assert [m.name for m in record.llm_models] == [TITAN]
    assert record.last_seen == datetime(2026, 10, 12, 11, 0, tzinfo=timezone.utc)


def test_a_persons_refused_call_is_counted_as_refused_not_as_a_persons_call(
    caplog: pytest.LogCaptureFixture,
) -> None:
    aws = FakeAws(
        events={
            REGION: [
                [
                    event(role=SSO_ROLE, model=None, error_code="AccessDenied"),
                    event(role=SSO_ROLE),
                ],
            ],
        },
    )
    with caplog.at_level(logging.INFO):
        assert scan(aws, fields={**FIELDS, "list_agents": "false"}) == []
    assert "1 refused model call(s) counted, not reported" in caplog.text
    assert "1 model call(s) by people (sso role: 1) counted, not reported" in (
        caplog.text
    )


def test_the_root_user_is_a_person() -> None:
    root = f"arn:aws:iam::{ACCOUNT}:root"
    aws = FakeAws(
        events={REGION: [[event(role=None, user_arn=root, identity_type="Root")]]},
    )
    assert scan(aws, fields={**FIELDS, "list_agents": "false"}) == []


def test_a_streaming_calls_service_event_copy_and_other_events_are_skipped() -> None:
    aws = FakeAws(
        events={
            REGION: [
                [
                    event(name="ConverseStream", when="2026-10-12T10:00:00Z"),
                    # The same stream's end, logged again: its time must not count.
                    event(
                        role=OTHER_ROLE,
                        name="ConverseStream",
                        event_type="AwsServiceEvent",
                        when="2026-10-12T12:00:00Z",
                    ),
                    event(role=OTHER_ROLE, name="ListFoundationModels", model=None),
                ],
            ],
        },
    )
    [record] = scan(aws, fields={**FIELDS, "list_agents": "false"})
    assert record.creation_source.address.resource_id == WORKLOAD_ROLE
    assert record.last_seen == datetime(2026, 10, 12, 10, 0, tzinfo=timezone.utc)


# --- what is asked ------------------------------------------------------------------


def test_only_list_calls_are_made_and_never_get_agent_runtime() -> None:
    """GetAgentRuntime returns a runtime's environment variables; GetAgent its prompt."""
    aws = FakeAws(
        agents={REGION: [[agent("A1")]]},
        runtimes={REGION: [[runtime("r1")]]},
        events={REGION: [[event()]]},
    )
    scan(aws)
    assert aws.operations() == ALLOWED_OPERATIONS
    assert not hasattr(FakeClient, "get_agent_runtime")


def test_the_lookback_sets_cloudtrails_window_and_zero_means_seven_days() -> None:
    aws = FakeAws()
    scan(aws, fields={**FIELDS, "list_agents": "false"}, lookback_hours=24)
    scan(aws, fields={**FIELDS, "list_agents": "false"}, lookback_hours=0)
    windows = [
        (params["StartTime"], params["EndTime"])
        for _, _, op, params in aws.calls
        if op == "LookupEvents"
    ]
    assert windows == [(NOW - timedelta(hours=24), NOW), (NOW - timedelta(days=7), NOW)]
    lookup = next(p for _, _, op, p in aws.calls if op == "LookupEvents")
    assert lookup["LookupAttributes"] == [
        {"AttributeKey": "EventSource", "AttributeValue": "bedrock.amazonaws.com"},
    ]


def test_the_lookback_is_not_applied_to_the_inventory() -> None:
    old = datetime(2024, 1, 1, tzinfo=timezone.utc)
    aws = FakeAws(agents={REGION: [[agent("OLD", updatedAt=old)]]})
    [record] = scan(
        aws,
        fields={**FIELDS, "read_cloudtrail": "false"},
        lookback_hours=1,
    )
    assert record.last_seen == old
    [(_, _, _, params)] = [c for c in aws.calls if c[2] == "ListAgents"]
    assert params == {"maxResults": 100}


def test_every_page_is_read_and_a_repeated_cursor_ends_the_walk() -> None:
    aws = FakeAws(
        agents={REGION: [[agent("A1")], [agent("A2")], [agent("A3")]]},
        events={REGION: [[event(model=CLAUDE)], [event(model=TITAN)]]},
    )
    records = scan(aws)
    assert len(by_kind(records, "bedrock_agent")) == 3
    [caller] = by_kind(records, "iam_role")
    assert {m.name for m in caller.llm_models} == {CLAUDE, TITAN}
    tokens = [p.get("NextToken") for _, _, op, p in aws.calls if op == "LookupEvents"]
    assert tokens == [None, "1"]

    class Repeating(FakeClient):
        def list_agents(self, **params: Any) -> dict[str, Any]:
            self._record("ListAgents", params)
            return {"agentSummaries": [agent("LOOP")], "nextToken": "same"}

    looping = FakeAws()
    client = BedrockClient(lambda s, r: Repeating(looping, s, r), LOG)
    assert [a["agentId"] for a in client.agents(REGION)] == ["LOOP", "LOOP"]


def test_lookups_are_paced_to_two_a_second_and_throttling_is_retried() -> None:
    aws = FakeAws(
        events={REGION: [[event()], [event()]]},
        errors={
            ("cloudtrail", "LookupEvents"): [
                client_error("ThrottlingException", "LookupEvents"),
                client_error("ThrottlingException", "LookupEvents"),
            ],
        },
    )
    sleeps = Sleeps()
    clock = iter(float(n) * 0.1 for n in range(1000))
    client = BedrockClient(
        aws.client_for,
        LOG,
        sleep=sleeps,
        monotonic=lambda: next(clock),
    )
    calls = list(client.model_calls(REGION, NOW - timedelta(hours=1), NOW))

    assert len(calls) == 2
    assert len([c for c in aws.calls if c[2] == "LookupEvents"]) == 4
    # Every request after the first waits out the rest of its half second.
    pacing = [s for s in sleeps.seconds if s <= LOOKUP_INTERVAL_SECONDS]
    assert len(pacing) >= 3
    assert all(s > 0 for s in sleeps.seconds)


def test_throttling_that_never_lets_up_is_a_warning_for_that_region(
    caplog: pytest.LogCaptureFixture,
) -> None:
    aws = FakeAws(
        agents={REGION: [[agent("A1")]]},
        errors={
            ("cloudtrail", "LookupEvents"): [
                client_error("ThrottlingException", "LookupEvents")
                for _ in range(MAX_ATTEMPTS)
            ],
        },
    )
    with caplog.at_level(logging.WARNING):
        records = scan(aws)
    assert [r.creation_source.address.resource_kind for r in records] == [
        "bedrock_agent",
    ]
    assert "Bedrock LookupEvents in us-east-1 not read" in caplog.text


# --- refusals ---------------------------------------------------------------------


def test_a_refused_api_is_a_warning_for_that_part_and_the_rest_is_read(
    caplog: pytest.LogCaptureFixture,
) -> None:
    aws = FakeAws(
        agents={REGION: [[agent("A1")]]},
        events={REGION: [[event()]]},
        errors={
            ("bedrock-agentcore-control", "ListAgentRuntimes"): [
                client_error("AccessDeniedException", "ListAgentRuntimes"),
            ],
        },
    )
    with caplog.at_level(logging.WARNING):
        records = scan(aws)

    assert sorted(r.creation_source.address.resource_kind for r in records) == [
        "bedrock_agent",
        "iam_role",
    ]
    assert "Bedrock ListAgentRuntimes in us-east-1 not read" in caplog.text
    assert "AccessDeniedException" in caplog.text


def test_a_region_without_agentcore_is_a_warning() -> None:
    aws = FakeAws(
        agents={REGION: [[agent("A1")]]},
        errors={
            ("bedrock-agentcore-control", "ListAgentRuntimes"): [
                EndpointConnectionError(endpoint_url="https://example.invalid"),
            ],
        },
    )
    records = scan(aws, fields={**FIELDS, "read_cloudtrail": "false"})
    assert len(records) == 1


def test_every_part_refused_fails_the_scan_as_permission_denied() -> None:
    denied = {
        ("bedrock-agent", "ListAgents"): [client_error("AccessDenied", "ListAgents")],
        ("bedrock-agentcore-control", "ListAgentRuntimes"): [
            client_error("AccessDeniedException", "ListAgentRuntimes"),
        ],
        ("cloudtrail", "LookupEvents"): [client_error("AccessDenied", "LookupEvents")],
    }
    with pytest.raises(BedrockError) as raised:
        scan(FakeAws(errors=denied))
    assert failure_code(raised.value) is DiscoveryErrorCode.PERMISSION_DENIED


def test_a_refused_credential_ends_the_scan_as_authentication_failed() -> None:
    aws = FakeAws(
        errors={
            ("sts", "GetCallerIdentity"): [
                client_error("ExpiredTokenException", "GetCallerIdentity"),
            ],
        },
    )
    with pytest.raises(BedrockError) as raised:
        scan(aws)
    assert failure_code(raised.value) is DiscoveryErrorCode.AUTHENTICATION_FAILED
    assert aws.operations() == {"GetCallerIdentity"}


def test_a_region_not_enabled_for_the_account_is_a_warning_not_the_credential(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """An opt-in region the account has not enabled refuses the token as a bad
    credential would; the credential was already proven in the first region."""
    aws = FakeAws(
        agents={REGION: [[agent("A1")]]},
        errors={
            ("bedrock-agent", "ListAgents"): [
                None,
                client_error("UnrecognizedClientException", "ListAgents"),
            ],
        },
    )
    fields = {"regions": f"{REGION},me-south-1", "read_cloudtrail": "false"}
    with caplog.at_level(logging.WARNING):
        records = scan(aws, fields=fields)
    assert [r.creation_source.address.resource_id for r in records] == ["A1"]
    assert "Bedrock ListAgents in me-south-1 not read" in caplog.text


def test_an_expired_token_in_a_later_region_still_ends_the_scan() -> None:
    aws = FakeAws(
        errors={
            ("bedrock-agent", "ListAgents"): [
                None,
                client_error("ExpiredTokenException", "ListAgents"),
            ],
        },
    )
    fields = {"regions": f"{REGION},me-south-1", "read_cloudtrail": "false"}
    with pytest.raises(BedrockError) as raised:
        scan(aws, fields=fields)
    assert failure_code(raised.value) is DiscoveryErrorCode.AUTHENTICATION_FAILED


def test_a_stop_before_the_first_list_sends_nothing_more() -> None:
    aws = FakeAws(agents={REGION: [[agent("A1")]]}, events={REGION: [[event()]]})
    connector = connector_for(aws)
    connector.stop_when(lambda: True)
    assert scan(aws, connector=connector) == []
    assert aws.operations() == {"GetCallerIdentity"}


# --- settings and credentials -------------------------------------------------------


@pytest.mark.parametrize(
    "fields,message",
    [
        ({}, "missing required field 'regions'"),
        ({"regions": "us-east-1, nowhere"}, "'nowhere'"),
        ({"regions": REGION, "list_agents": "maybe"}, "'list_agents' is 'maybe'"),
        (
            {"regions": REGION, "list_agents": "false", "read_cloudtrail": "FALSE"},
            "would read nothing",
        ),
    ],
)
def test_bad_settings_are_configuration_errors(
    fields: dict[str, str],
    message: str,
) -> None:
    with pytest.raises(DiscoveryConfigurationError, match=message) as raised:
        settings_from(fields)
    assert failure_code(raised.value) is DiscoveryErrorCode.NOT_CONFIGURED


def test_toggles_default_on_and_regions_are_comma_separated() -> None:
    settings = settings_from({"regions": " us-east-1 , us-west-2,us-east-1"})
    assert settings.regions == ("us-east-1", "us-west-2")
    assert settings.list_agents and settings.read_cloudtrail


def test_a_source_without_a_key_needs_the_engines_opt_in(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv(ALLOW_DEFAULT_CREDENTIALS_ENV_VAR, raising=False)
    with pytest.raises(DiscoveryConfigurationError) as raised:
        source_session({}, FIELDS)
    assert ALLOW_DEFAULT_CREDENTIALS_ENV_VAR in str(raised.value)
    assert ALLOW_DEFAULT_CREDENTIALS_ENV_VAR == (
        "ARTHUR_ENGINE_AWS_BEDROCK_ALLOW_DEFAULT_CREDENTIALS"
    )


def test_the_key_never_reaches_the_log(caplog: pytest.LogCaptureFixture) -> None:
    secret = "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
    aws = FakeAws(agents={REGION: [[agent("A1")]]})
    with caplog.at_level(logging.DEBUG):
        list(
            connector_for(aws).scan(
                FakeConfig(),  # type: ignore[arg-type]
                24,
                {"access_key_id": "AKIAEXAMPLE", "secret_access_key": secret},
                FIELDS,
                LOG,
            ),
        )
    assert secret not in caplog.text
    assert "AKIAEXAMPLE" not in caplog.text
    assert "the source's access key" in caplog.text
