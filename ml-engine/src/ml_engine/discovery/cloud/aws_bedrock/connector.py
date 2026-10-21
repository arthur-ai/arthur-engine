"""AWS Bedrock's side of a DISCOVER_AGENTS scan.

TWO READINGS OF ONE ACCOUNT, per region, each switched by its own field:

- `list_agents`: the inventory. Bedrock's agents (`ListAgents`) and AgentCore's agent
  runtimes (`ListAgentRuntimes`), one record each. An inventory, not a log, so the
  lookback is not applied: an agent built a year ago and never edited is still there.
- `read_cloudtrail`: the callers. CloudTrail's management events for Bedrock's model
  calls (Converse, ConverseStream, InvokeModel, InvokeModelWithResponseStream) within
  the lookback, or the last seven days when the lookback is 0. One record per (IAM role,
  region), naming the models it called. A role is a workload: the agent that calls a
  model directly, with no Bedrock agent around it, shows up here and nowhere else.

THE RECORD. `instance` is the account id and `scope` the region, as every Bedrock record
is addressed. Three kinds of resource share the vendor, so each record names its kind:

==============  ================  ==============================================
resource_kind   resource_id       external_id
==============  ================  ==============================================
bedrock_agent   agent id          the agent's ARN, composed (ListAgents has none)
agent_runtime   runtime id        the runtime's ARN, verbatim
iam_role        role ARN          ``{account}/{region}/iam_role/{role ARN}``
iam_user        user ARN          ``{account}/{region}/iam_user/{user ARN}``
==============  ================  ==============================================

A caller is per region because a role calling models in two regions is two deployments
of the workload, as two agents in two regions are; the account is in its ARN already,
and in the external id so the id reads alone.

A PERSON IS NOT AN AGENT. An AWS IAM Identity Center (SSO) role is assumed by a person
at a console or a CLI, so its calls are counted and logged, never reported; so is the
root user's. Only workload identities become records.

A REFUSED PART IS A WARNING, NOT A FAILED SCAN. Each (part, region) is read on its own:
a role allowed `ListAgents` but not `LookupEvents`, or a region AgentCore does not run
in, loses that part and keeps the rest, with a warning naming what was not read. A
refused credential is not one part's problem and ends the scan; so does a scan in which
every part was refused, which would otherwise read as an account with no agents.

CREDENTIALS are `discovery.aws_credentials`', under this vendor's own opt-in for the
engine's identity.
"""

import logging
import time
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import (
    Callable,
    ClassVar,
    Iterator,
    Mapping,
    Optional,
    Sequence,
    TypeVar,
)

import boto3
from arthur_client.api_bindings import DiscoverySourceConfigSpec
from arthur_common.models.agent_discovery_schemas import DiscoveredAgentRecord
from arthur_common.models.agent_governance_schemas import (
    CloudAgentCreationSource,
    LLMModel,
    RunsOn,
    SourceAddress,
)

from discovery.aws_credentials import (
    REGION_NAME,
    SENSITIVE_FIELDS,
    aws_session,
    describe_credentials,
)
from discovery.cloud.aws_bedrock.client import (
    BedrockClient,
    BedrockError,
    ClientFactory,
    Identity,
    ModelCall,
    default_client_factory,
)
from discovery.endpoint.scope import parse_group_names
from job_executors.discovery_scan import DiscoveryConfigurationError

VENDOR = "aws_bedrock"

# Non-sensitive source fields, beside aws_credentials' role_arn and external_id.
REGIONS_FIELD = "regions"
LIST_AGENTS_FIELD = "list_agents"
READ_CLOUDTRAIL_FIELD = "read_cloudtrail"

# Opt-in for the engine's own AWS credentials, as EC2's.
ALLOW_DEFAULT_CREDENTIALS_ENV_VAR = (
    "ARTHUR_ENGINE_AWS_BEDROCK_ALLOW_DEFAULT_CREDENTIALS"
)

# The assumed role's session name, which the customer's CloudTrail shows.
SESSION_NAME = "arthur-ai-discovery"

BEDROCK_AGENT = "bedrock_agent"
AGENT_RUNTIME = "agent_runtime"
IAM_ROLE = "iam_role"
IAM_USER = "iam_user"

# The window CloudTrail is read over when the scan's lookback is 0.
DEFAULT_CLOUDTRAIL_LOOKBACK = timedelta(days=7)

# Records per published batch.
BATCH_SIZE = 100

# The path IAM Identity Center gives every role it creates for a permission set.
SSO_ROLE_PATH = "/aws-reserved/sso.amazonaws.com/"

_TRUE = frozenset({"true", "yes", "1"})
_FALSE = frozenset({"false", "no", "0"})
_REFUSED_STATUSES = (401,)
# What a region the account has not enabled answers with, as a refused credential
# would. Raised only from the region the credential was proven in.
_REGION_NOT_ENABLED_CODES = frozenset(
    {"InvalidClientTokenId", "UnrecognizedClientException"}
)

_T = TypeVar("_T")


@dataclass(frozen=True)
class BedrockSettings:
    regions: tuple[str, ...]
    list_agents: bool = True
    read_cloudtrail: bool = True


@dataclass
class _Caller:
    """What one identity's model calls in one region add up to."""

    arn: str
    kind: str
    models: set[str] = field(default_factory=set)
    last_seen: Optional[datetime] = None
    calls: int = 0


SessionFactory = Callable[
    [Mapping[str, Optional[str]], Mapping[str, str]],
    boto3.Session,
]


def source_session(
    credentials: Mapping[str, Optional[str]],
    source_fields: Mapping[str, str],
) -> boto3.Session:
    """The source's AWS session, under Bedrock's opt-in for the engine's own
    credentials. STS is asked in the first region the source scans."""
    regions = parse_group_names(source_fields.get(REGIONS_FIELD))
    return aws_session(
        credentials,
        source_fields,
        source="Bedrock source",
        allow_default_env_var=ALLOW_DEFAULT_CREDENTIALS_ENV_VAR,
        session_name=SESSION_NAME,
        region_name=regions[0] if regions else None,
    )


class BedrockConnector:
    """Implements `job_executors.discovery_scan.DiscoverySourceConnector` and
    `AcceptsStopCheck`.

    Holds one scan's stop check, which is safe only because a connector is built fresh
    for every scan -- see `DiscoveryConnectorFactory`.
    """

    SENSITIVE_FIELDS: ClassVar[frozenset[str]] = SENSITIVE_FIELDS

    def __init__(
        self,
        session_for: SessionFactory = source_session,
        clients_for: Callable[[boto3.Session], ClientFactory] = default_client_factory,
        clock: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self._session_for = session_for
        self._clients_for = clients_for
        self._clock = clock
        self._sleep = sleep
        self._should_stop: Callable[[], bool] = lambda: False

    def stop_when(self, should_stop: Callable[[], bool]) -> None:
        """Asked before every AWS request and every backoff sleep."""
        self._should_stop = should_stop

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
        client = BedrockClient(
            self._clients_for(session),
            logger,
            should_stop=self._should_stop,
            sleep=self._sleep,
        )

        end = self._clock()
        window = (
            timedelta(hours=lookback_hours)
            if lookback_hours > 0
            else DEFAULT_CLOUDTRAIL_LOOKBACK
        )
        start = end - window

        # Asked first: it needs no permission, so a refusal here is the credential.
        identity = client.identity(settings.regions[0])
        logger.info(
            "Bedrock scan starting in account %s, region(s) %s, using %s. Agents and "
            "runtimes: %s. CloudTrail model callers: %s.",
            identity.account,
            ", ".join(settings.regions),
            describe_credentials(credentials, source_fields),
            "listed (the lookback is not applied)" if settings.list_agents else "off",
            (
                f"read from {start.isoformat()} to {end.isoformat()}"
                if settings.read_cloudtrail
                else "off"
            ),
        )

        scan = _Scan(client, identity, settings.regions[0], logger)
        batch: list[DiscoveredAgentRecord] = []
        for region in settings.regions:
            parts: list[Iterator[DiscoveredAgentRecord]] = []
            if settings.list_agents:
                parts.append(scan.agents(region))
                parts.append(scan.runtimes(region))
            if settings.read_cloudtrail:
                parts.append(scan.callers(region, start, end))
            for part in parts:
                for record in part:
                    batch.append(record)
                    if len(batch) >= BATCH_SIZE:
                        yield batch
                        batch = []
                if self._should_stop():
                    break
            if self._should_stop():
                logger.info("Bedrock scan stopped early on request")
                break
        if batch:
            yield batch

        scan.log_summary(settings)
        if scan.read == 0 and scan.refused:
            # Every part in every region was refused: not an account with no agents.
            raise scan.refused[0]


class _Scan:
    """One scan's reading of each (part, region), and its tallies."""

    def __init__(
        self,
        client: BedrockClient,
        identity: Identity,
        identity_region: str,
        logger: logging.Logger,
    ) -> None:
        self._client = client
        self._identity = identity
        self._identity_region = identity_region
        self._log = logger
        self.counts: Counter[str] = Counter()
        self.people: Counter[str] = Counter()
        self.skipped = 0
        self.read = 0
        self.refused: list[BedrockError] = []

    def agents(self, region: str) -> Iterator[DiscoveredAgentRecord]:
        for summary in self._part("ListAgents", region, self._client.agents(region)):
            record = agent_record(summary, self._identity, region, self._log)
            if record is None:
                self.skipped += 1
                continue
            self.counts[BEDROCK_AGENT] += 1
            yield record

    def runtimes(self, region: str) -> Iterator[DiscoveredAgentRecord]:
        listing = self._client.agent_runtimes(region)
        for summary in self._part("ListAgentRuntimes", region, listing):
            record = runtime_record(summary, self._identity, region, self._log)
            if record is None:
                self.skipped += 1
                continue
            self.counts[AGENT_RUNTIME] += 1
            yield record

    def callers(
        self,
        region: str,
        start: datetime,
        end: datetime,
    ) -> Iterator[DiscoveredAgentRecord]:
        """Every model call in the window, then one record per workload identity.

        Collected first because one identity's calls are spread over every page. A
        failure part-way still yields what the pages before it held.
        """
        calls = self._part(
            "LookupEvents",
            region,
            self._client.model_calls(region, start, end),
        )
        callers, people, events = aggregate(calls)
        self.counts["model_call_events"] += events
        if people:
            self.people.update(people)
            self._log.info(
                "Bedrock in %s: %s model call(s) by people (%s) counted, not reported",
                region,
                sum(people.values()),
                ", ".join(f"{kind}: {n}" for kind, n in sorted(people.items())),
            )
        for caller in callers:
            self.counts[caller.kind] += 1
            yield caller_record(caller, self._identity, region)

    def _part(
        self,
        operation: str,
        region: str,
        items: Iterator[_T],
    ) -> Iterator[_T]:
        """`items`, with a refusal logged against this (part, region) and not raised.

        A refused credential is raised: every other part would be refused the same way.
        """
        try:
            yield from items
        except BedrockError as e:
            # A credential refused in the region it was proven in is the credential.
            # Elsewhere, these codes are what an opt-in region not enabled for the
            # account answers with; an expired token is still the credential.
            if e.status_code in _REFUSED_STATUSES and (
                region == self._identity_region
                or e.code not in _REGION_NOT_ENABLED_CODES
            ):
                raise
            self.refused.append(e)
            self._log.warning(
                "Bedrock %s in %s not read, the rest of the scan goes on: %s",
                operation,
                region,
                e,
            )
            return
        self.read += 1

    def log_summary(self, settings: BedrockSettings) -> None:
        self._log.info(
            "Bedrock scan found %s agent(s), %s runtime(s) and %s model-calling "
            "role(s) and user(s) from %s model call event(s); %s call(s) by people not "
            "reported; %s resource(s) skipped; %s part(s) refused",
            self.counts[BEDROCK_AGENT],
            self.counts[AGENT_RUNTIME],
            self.counts[IAM_ROLE] + self.counts[IAM_USER],
            self.counts["model_call_events"],
            sum(self.people.values()),
            self.skipped,
            len(self.refused),
        )


def aggregate(
    calls: Iterator[ModelCall],
) -> tuple[list[_Caller], Counter[str], int]:
    """(workload callers, people's calls by kind, events read) from one region's calls."""
    callers: dict[str, _Caller] = {}
    people: Counter[str] = Counter()
    events = 0
    for call in calls:
        events += 1
        person = _person(call)
        if person is not None:
            people[person] += 1
            continue
        kind = IAM_USER if ":user/" in call.caller_arn else IAM_ROLE
        caller = callers.setdefault(call.caller_arn, _Caller(call.caller_arn, kind))
        caller.calls += 1
        if call.model_id:
            caller.models.add(call.model_id)
        if caller.last_seen is None or call.event_time > caller.last_seen:
            caller.last_seen = call.event_time
    return sorted(callers.values(), key=lambda c: c.arn), people, events


def _person(call: ModelCall) -> Optional[str]:
    """Which kind of person made the call, or None for a workload."""
    if SSO_ROLE_PATH in call.caller_arn:
        return "sso role"
    if call.caller_type == "Root" or call.caller_arn.endswith(":root"):
        return "root"
    return None


def settings_from(source_fields: Mapping[str, str]) -> BedrockSettings:
    """The regions and parts from the source's non-sensitive fields."""
    regions = parse_group_names(source_fields.get(REGIONS_FIELD))
    if not regions:
        raise DiscoveryConfigurationError(
            f"Bedrock source is missing required field '{REGIONS_FIELD}'. It is a "
            f"source field, not a secret.",
        )
    bad = [r for r in regions if not REGION_NAME.match(r)]
    if bad:
        raise DiscoveryConfigurationError(
            f"Bedrock source's '{REGIONS_FIELD}' has value(s) that are not AWS region "
            f"names: {', '.join(repr(r) for r in bad)}. A region name looks like "
            f"us-east-1.",
        )
    list_agents = _toggle(source_fields, LIST_AGENTS_FIELD)
    read_cloudtrail = _toggle(source_fields, READ_CLOUDTRAIL_FIELD)
    if not list_agents and not read_cloudtrail:
        raise DiscoveryConfigurationError(
            f"Bedrock source has both '{LIST_AGENTS_FIELD}' and "
            f"'{READ_CLOUDTRAIL_FIELD}' off, so it would read nothing. Turn one on.",
        )
    return BedrockSettings(
        regions=regions,
        list_agents=list_agents,
        read_cloudtrail=read_cloudtrail,
    )


def _toggle(source_fields: Mapping[str, str], name: str) -> bool:
    """A true/false field, on when empty."""
    value = (source_fields.get(name) or "").strip().lower()
    if not value or value in _TRUE:
        return True
    if value in _FALSE:
        return False
    raise DiscoveryConfigurationError(
        f"Bedrock source's '{name}' is {value!r}; it is 'true' or 'false'.",
    )


def agent_record(
    summary: Mapping[str, object],
    identity: Identity,
    region: str,
    logger: logging.Logger,
) -> Optional[DiscoveredAgentRecord]:
    """A ListAgents summary's record, or None when it cannot be addressed or dated.

    The summary carries no ARN, so it is composed in the format AWS documents for an
    agent: `arn:<partition>:bedrock:<region>:<account>:agent/<agent id>`.
    """
    agent_id = str(summary.get("agentId") or "").strip()
    if not agent_id:
        logger.warning("Bedrock ListAgents in %s returned an agent with no id", region)
        return None
    arn = (
        f"arn:{identity.partition}:bedrock:{region}:{identity.account}:agent/{agent_id}"
    )
    return _inventory_record(
        kind=BEDROCK_AGENT,
        resource_id=agent_id,
        external_id=arn,
        name=str(summary.get("agentName") or "") or agent_id,
        updated=summary.get("updatedAt"),
        identity=identity,
        region=region,
        logger=logger,
    )


def runtime_record(
    summary: Mapping[str, object],
    identity: Identity,
    region: str,
    logger: logging.Logger,
) -> Optional[DiscoveredAgentRecord]:
    """A ListAgentRuntimes summary's record, or None when it cannot be addressed or
    dated."""
    runtime_id = str(summary.get("agentRuntimeId") or "").strip()
    arn = str(summary.get("agentRuntimeArn") or "").strip()
    if not runtime_id or not arn:
        logger.warning(
            "Bedrock ListAgentRuntimes in %s returned a runtime with no id or ARN (%r)",
            region,
            runtime_id or arn,
        )
        return None
    return _inventory_record(
        kind=AGENT_RUNTIME,
        resource_id=runtime_id,
        external_id=arn,
        name=str(summary.get("agentRuntimeName") or "") or runtime_id,
        updated=summary.get("lastUpdatedAt"),
        identity=identity,
        region=region,
        logger=logger,
    )


def caller_record(
    caller: _Caller,
    identity: Identity,
    region: str,
) -> DiscoveredAgentRecord:
    """One workload identity's record: who called which models, and when last."""
    assert caller.last_seen is not None  # set by the first call aggregated
    models = sorted(caller.models)
    short = caller.arn.rsplit("/", 1)[-1] or caller.arn
    return DiscoveredAgentRecord(
        external_id=f"{identity.account}/{region}/{caller.kind}/{caller.arn}",
        name=f"{short} calling {', '.join(models) if models else 'Bedrock'}",
        last_seen=caller.last_seen,
        llm_models=[LLMModel(name=m) for m in models] or None,
        runs_on=RunsOn.AWS,
        creation_source=CloudAgentCreationSource(
            vendor=VENDOR,
            address=SourceAddress(
                instance=identity.account,
                scope=region,
                resource_kind=caller.kind,
                resource_id=caller.arn,
            ),
        ),
    )


def _inventory_record(
    *,
    kind: str,
    resource_id: str,
    external_id: str,
    name: str,
    updated: object,
    identity: Identity,
    region: str,
    logger: logging.Logger,
) -> Optional[DiscoveredAgentRecord]:
    if not isinstance(updated, datetime):
        logger.warning(
            "%s: Bedrock reported no update time; skipped, because last_seen is "
            "required and inventing one would date the record to the scan",
            external_id,
        )
        return None
    last_seen = updated if updated.tzinfo else updated.replace(tzinfo=timezone.utc)
    return DiscoveredAgentRecord(
        external_id=external_id,
        name=name,
        last_seen=last_seen,
        runs_on=RunsOn.AWS,
        creation_source=CloudAgentCreationSource(
            vendor=VENDOR,
            address=SourceAddress(
                instance=identity.account,
                scope=region,
                resource_kind=kind,
                resource_id=resource_id,
            ),
        ),
    )
