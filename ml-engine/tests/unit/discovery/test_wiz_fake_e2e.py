"""The Wiz connector end to end against a fake Wiz on a local port (tests/fakes/wiz).

Nothing is mocked between the engine and the socket: the shipped client and
`requests` talk HTTP to a server that executes every query with graphql-core against
the pruned copy of Wiz's schema, over the synthetic tenant in tests/fakes/wiz/tenant.json.
The engine is pointed at it with ARTHUR_ENGINE_WIZ_API_BASE_URL_OVERRIDE, as an
engineer's laptop would be. Driven three ways: Test Connection's executor, a
standalone scan delivering to a webhook, and the connector's own scan under the
output contract. What the fake's data and error shapes are, and are not, is in its
docstring.
"""

import io
import logging
import textwrap
import time
from pathlib import Path
from typing import Any, Iterator, Optional
from unittest.mock import MagicMock

import pytest
from arthur_client.api_bindings import DiscoverySourceConfigSpec, DiscoverySourceVendor

from arthur_client_support import TEST_DISCOVERY_SOURCE_SUPPORTED
from discovery import source_connectors
from discovery.cloud.wiz.connector import (
    LOCAL_OVERRIDE_ENV_VAR,
    VENDOR,
    WORKLOAD_INVENTORY_SCOPE,
)
from job_executors.discovery_output_contract import check_batch
from job_executors.discovery_scan import (
    DENIED_PERMISSION,
    DeniedScope,
    DiscoveryErrorCode,
    DiscoveryScanOutcome,
)
from log_redaction import SecretRedactingFilter
from standalone.discovery_config import ResolvedScan, load_config
from standalone.scan import run_scan, scan_logger
from standalone.sinks.common import DISCOVERED_AGENT_EVENT, SCAN_OUTCOME_EVENT
from standalone.sinks.webhook import WebhookDestination
from tests.fakes.wiz import DEFAULT_CLIENT_ID, DEFAULT_CLIENT_SECRET, FakeWiz

# Validated as for Wiz, never contacted: the override sends both calls to the fake.
ENDPOINT = "https://api.us1.app.wiz.io/graphql"
FIELDS = {"api_endpoint_url": ENDPOINT, "client_id": DEFAULT_CLIENT_ID}
CREDS: dict[str, Optional[str]] = {"client_secret": DEFAULT_CLIENT_SECRET}
PAGE_SIZE = 3

AZURE_SUB = "9f8e7d6c-0000-4000-8000-00000000fa4e"
IMAGE = "sha256:fa4e000000000000000000000000000000000000000000000000000000000001"
AI_SPM_IDS = {
    "arn:aws:bedrock:us-east-1:111122223333:agent/FAKEAGNT01",
    f"/subscriptions/{AZURE_SUB}/resourceGroups/rg-fake-ai/providers/"
    "Microsoft.CognitiveServices/accounts/fake-foundry/projects/claims/agents/"
    "asst_FAKE0002",
    "gcp:fake-gcp-project-1:projects/fake-gcp-project-1/locations/us-central1/"
    "reasoningEngines/4444444444",
    "aws:111122223333:bedrock-us-east-2",
    f"/subscriptions/{AZURE_SUB}/resourceGroups/rg-fake-ai/providers/"
    "Microsoft.CognitiveServices/accounts/fake-openai",
    "//discoveryengine.googleapis.com/projects/fake-gcp-project-1/locations/global/"
    "collections/default_collection/engines/fake-engine",
}
WORKLOAD_IDS = {
    "arn:aws:ec2:us-east-1:111122223333:instance/i-0fake00000000001:langchain",
    f"aws:111122223333:{IMAGE}:crewai",
    "arn:aws:lambda:us-west-2:111122223333:function:fake-mcp-tools:"
    "model-context-protocol",
    "//compute.googleapis.com/projects/fake-gcp-project-1/zones/us-central1-a/"
    "instances/fake-gcp-vm:openai-python-sdk",
}
SCOPE_DENIAL = "at least one of the following is required: [read:inventory read:all]"


@pytest.fixture
def fake(
    request: pytest.FixtureRequest,
    monkeypatch: pytest.MonkeyPatch,
) -> Iterator[FakeWiz]:
    options = getattr(request, "param", {})
    with FakeWiz(page_size=PAGE_SIZE, **options) as server:
        monkeypatch.setenv(LOCAL_OVERRIDE_ENV_VAR, server.base_url)
        yield server


def with_fake(**options: Any) -> Any:
    return pytest.mark.parametrize("fake", [options], indirect=True)


@pytest.fixture
def job_log() -> tuple[logging.Logger, io.StringIO]:
    logger = logging.getLogger(f"test.wiz-e2e.{id(object())}")
    logger.setLevel(logging.INFO)
    logger.propagate = False
    logger.addFilter(SecretRedactingFilter())
    stream = io.StringIO()
    logger.addHandler(logging.StreamHandler(stream))
    return logger, stream


def config(fields: Optional[dict[str, str]] = None) -> DiscoverySourceConfigSpec:
    return DiscoverySourceConfigSpec(
        discovery_source_id="44444444-4444-4444-4444-444444444444",
        name="wiz fake tenant",
        vendor=VENDOR,
        query="",
        query_language="none",
        lookback_window_seconds=86400,
        source_fields=fields or FIELDS,
    )


def connector_scan(
    logger: logging.Logger,
    fields: Optional[dict[str, str]] = None,
) -> dict[str, Any]:
    """The connector's records by external_id, each batch through the output contract."""
    connector = source_connectors()[VENDOR]()
    records: dict[str, Any] = {}
    for batch in connector.scan(config(fields), 24, CREDS, fields or FIELDS, logger):
        check_batch(batch, "wiz fake tenant")
        records.update({r.external_id: r for r in batch})
    return records


# -- a full scan -----------------------------------------------------------------------


def test_a_scan_pages_both_inventories_and_keeps_the_native_ids(
    fake: FakeWiz,
    job_log: tuple[logging.Logger, io.StringIO],
) -> None:
    logger, log = job_log
    records = connector_scan(logger)

    assert set(records) == AI_SPM_IDS | WORKLOAD_IDS
    # Paged at the fake's page size: 7 AI resources (the AI_MODEL is filtered out by
    # type) in 3 pages, 10 AI-layer sightings on VMs, images and functions in 4.
    afters = {
        root: [v["after"] is not None for r, v in fake.variables if r == root]
        for root in ("cloudResourcesV2", "hostedTechnologies")
    }
    assert afters == {
        "cloudResourcesV2": [False, True, True],
        "hostedTechnologies": [False, True, True, True],
    }
    text = log.getvalue()
    assert (
        "Wiz scan listed 7 resource(s) over 3 page(s); 6 record(s), 1 skipped" in text
    )
    assert (
        "Wiz workload inventory listed 10 ML and AI technology sighting(s) over 4 "
        "page(s); 4 record(s), 1 skipped, 1 cloud service(s) left to the AI-SPM "
        "inventory, 3 not an agent framework, 1 duplicate(s)"
    ) in text


def test_the_native_id_rules_hold_on_the_wire(
    fake: FakeWiz,
    job_log: tuple[logging.Logger, io.StringIO],
) -> None:
    logger, log = job_log
    records = connector_scan(logger)
    text = log.getvalue()

    def address(external_id: str) -> Any:
        return records[external_id].creation_source.address

    # providerUniqueId verbatim, the account as Wiz has it.
    bedrock = address("arn:aws:bedrock:us-east-1:111122223333:agent/FAKEAGNT01")
    assert (bedrock.instance, bedrock.scope) == ("111122223333", "us-east-1")
    # Azure's subscription lower-cased in the address.
    azure = next(i for i in AI_SPM_IDS if "fake-foundry" in i)
    assert address(azure).instance == AZURE_SUB
    # externalId only: qualified; regionLocation stands in for region; no createdAt.
    service = address("aws:111122223333:bedrock-us-east-2")
    assert (service.resource_id, service.scope) == (
        "aws:111122223333:bedrock-us-east-2",
        "us-east-2",
    )
    assert (
        address(next(i for i in AI_SPM_IDS if "discoveryengine" in i)).scope == "global"
    )
    # Neither usable id: skipped, naming Wiz's entity type, never keyed on Wiz's id.
    assert not any("wiz-cr-0006" in i or "orphan" in i for i in records)
    assert (
        "Wiz resource wiz-cr-0006 of entity type AI_AGENT (unknown#agent) reported no "
        "providerUniqueId"
    ) in text
    assert "Wiz VIRTUAL_MACHINE wiz-res-vm-0005 (virtualMachine) reported no" in text

    # The same technology twice on one workload is one record, the newer sighting.
    langchain = records[
        "arn:aws:ec2:us-east-1:111122223333:instance/i-0fake00000000001:langchain"
    ]
    assert langchain.creation_source.observations.version == "0.3.9"
    assert langchain.creation_source.address.scope == "111122223333/us-east-1"
    assert langchain.creation_source.address.resource_kind == "technology"
    assert langchain.name == "LangChain on agent-host-1"


def test_cloud_services_and_non_agent_libraries_are_dropped_and_logged(
    fake: FakeWiz,
    job_log: tuple[logging.Logger, io.StringIO],
) -> None:
    logger, log = job_log
    records = connector_scan(logger)
    names = {r.name for r in records.values()}

    # PyTorch on a VM named "langchain-trainer": the resource's name never matches.
    assert not any(
        n.startswith(("PyTorch", "TensorFlow", "Anthropic", "Azure")) for n in names
    )
    # Filtered by Wiz: a technology outside the AI layer, and one on a running container.
    assert not any(n.startswith(("NGINX", "LangGraph")) for n in names)
    assert (
        "Wiz ML and AI technologies seen that the engine does not match as agent "
        "frameworks: Anthropic [4500], PyTorch [4102], TensorFlow [4310]"
    ) in log.getvalue()
    assert "langchain-trainer" not in log.getvalue()


@with_fake(token_lifetime=30)
def test_a_short_lived_token_is_renewed_before_each_call(
    fake: FakeWiz,
    job_log: tuple[logging.Logger, io.StringIO],
) -> None:
    connector_scan(job_log[0])
    paths = [path for path, _, _ in fake.requests]
    assert paths.count("/oauth/token") == paths.count("/graphql") == 7


# -- standalone: the scan as the engine runs it, to a webhook ---------------------------


def standalone_yaml(fake: FakeWiz, entity_types: str) -> str:
    return textwrap.dedent(
        f"""\
        version: 1
        schedule: {{interval: 1h}}
        sources:
          - name: wiz-fake
            vendor: wiz
            fields:
              - {{key: api_endpoint_url, value: "{ENDPOINT}"}}
              - {{key: client_id, value: {DEFAULT_CLIENT_ID}}}
              - {{key: client_secret, value: {DEFAULT_CLIENT_SECRET}}}
              - {{key: entity_types, value: "{entity_types}"}}
            configs:
              - {{name: inventory, query: "", query_language: none,
                  lookback_window_seconds: 86400}}
        destination:
          type: webhook
          url: {fake.base_url}/_sink
          allow_insecure_http: true
        """,
    )


def standalone(
    fake: FakeWiz,
    tmp_path: Path,
    entity_types: str = "",
) -> DiscoveryScanOutcome:
    """One standalone scan to a webhook on the fake, as the engine's scheduler runs it.

    The scan is resolved here rather than loaded from `standalone_yaml`: the pinned
    arthur-client has no `wiz` vendor yet, so `load_config` refuses the source (see
    `test_a_standalone_config_file_scans_wiz`).
    """
    fields = {**FIELDS, "entity_types": entity_types}
    scan = ResolvedScan(
        source_name="wiz-fake",
        discovery_source_config_id="cfg-wiz-fake",
        config=config(fields),
        lookback_hours=24,
        source_fields=fields,
        credentials=dict(CREDS),
    )
    sink = WebhookDestination(
        type="webhook",
        url=f"{fake.base_url}/_sink",
        allow_insecure_http=True,
    ).build_sink(logging.getLogger("test.wiz-e2e.sink"))
    try:
        return run_scan(scan, sink, True, scan_logger(scan, sink))
    finally:
        sink.close()


@pytest.mark.skipif(
    "wiz" not in {v.value for v in DiscoverySourceVendor},
    reason="the pinned arthur-client has no wiz DiscoverySourceVendor yet",
)
def test_a_standalone_config_file_scans_wiz(fake: FakeWiz, tmp_path: Path) -> None:
    path = tmp_path / "discovery.yaml"
    path.write_text(standalone_yaml(fake, ""))
    loaded = load_config(path)
    assert loaded is not None
    (scan,) = loaded.scans()
    sink = loaded.destination.build_sink(logging.getLogger("test.wiz-e2e.sink"))
    try:
        outcome = run_scan(scan, sink, True, scan_logger(scan, sink))
    finally:
        sink.close()
    assert outcome.error is None
    assert outcome.records_published == len(AI_SPM_IDS | WORKLOAD_IDS)


def test_a_standalone_scan_delivers_every_record_and_its_outcome(
    fake: FakeWiz,
    tmp_path: Path,
) -> None:
    outcome = standalone(fake, tmp_path)

    assert outcome.error is None
    assert outcome.records_published == 10
    assert outcome.denied_scopes == []
    agents = [e for e in fake.sink_events if e["event_type"] == DISCOVERED_AGENT_EVENT]
    assert {e["agent"]["external_id"] for e in agents} == AI_SPM_IDS | WORKLOAD_IDS
    assert {e["source"]["vendor"] for e in agents} == {"wiz"}
    (reported,) = [e for e in fake.sink_events if e["event_type"] == SCAN_OUTCOME_EVENT]
    assert reported["outcome"]["records_published"] == 10
    assert DEFAULT_CLIENT_SECRET not in str(fake.sink_events)


@with_fake(fault="missing-scope")
def test_a_missing_scope_costs_the_workload_inventory_only(
    fake: FakeWiz,
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    with caplog.at_level(logging.WARNING):
        outcome = standalone(fake, tmp_path)

    assert outcome.error is None
    assert outcome.records_published == len(AI_SPM_IDS)
    assert outcome.denied_scopes == [
        DeniedScope(WORKLOAD_INVENTORY_SCOPE, DENIED_PERMISSION),
    ]
    assert f"UNAUTHORIZED): Wiz says {SCOPE_DENIAL}" in caplog.text
    assert "or read:all. The AI-SPM records are still published" in caplog.text


@with_fake(fault="bad-credentials")
def test_refused_credentials_fail_the_scan_as_authentication(
    fake: FakeWiz,
    tmp_path: Path,
) -> None:
    outcome = standalone(fake, tmp_path)
    assert outcome.error_code == DiscoveryErrorCode.AUTHENTICATION_FAILED
    assert outcome.error is not None
    assert "HTTP 401 (access_denied)" in outcome.error
    assert DEFAULT_CLIENT_SECRET not in outcome.error


def test_an_entity_type_the_tenant_does_not_know_is_the_sources_to_fix(
    fake: FakeWiz,
    tmp_path: Path,
) -> None:
    outcome = standalone(fake, tmp_path, entity_types="AI_AGENT,AI_SPACESHIP")
    assert outcome.error_code == DiscoveryErrorCode.NOT_CONFIGURED
    assert outcome.error is not None
    assert "BAD_USER_INPUT" in outcome.error


# -- faults the client absorbs -----------------------------------------------------------


@with_fake(fault="rate-limit-once", retry_after="1")
def test_a_429_is_retried_after_retry_after(
    fake: FakeWiz,
    job_log: tuple[logging.Logger, io.StringIO],
) -> None:
    started = time.monotonic()
    records = connector_scan(job_log[0])
    assert time.monotonic() - started >= 1.0
    assert len(records) == 10
    statuses = [status for path, _, status in fake.requests if path == "/graphql"]
    assert statuses[:2] == [429, 200]


@with_fake(fault="rate-limit-in-200", retry_after="0")
def test_a_rate_limit_inside_a_200_is_retried(
    fake: FakeWiz,
    job_log: tuple[logging.Logger, io.StringIO],
) -> None:
    records = connector_scan(job_log[0])
    assert len(records) == 10
    assert fake.roots_requested()[:2] == ["cloudResourcesV2", "cloudResourcesV2"]


@with_fake(fault="repeated-cursor")
def test_a_repeated_cursor_ends_the_listing_with_a_warning(
    fake: FakeWiz,
    job_log: tuple[logging.Logger, io.StringIO],
) -> None:
    logger, log = job_log
    records = connector_scan(logger)
    assert fake.roots_requested().count("cloudResourcesV2") == 2
    # The seventh resource is on the page the loop never asks for.
    assert len(set(records) & AI_SPM_IDS) == 5
    assert "Wiz returned a page cursor it had already returned" in log.getvalue()


# -- Test Connection ---------------------------------------------------------------------

if TEST_DISCOVERY_SOURCE_SUPPORTED:
    from arthur_client.api_bindings import (
        DiscoverySourceReachability,
        DiscoverySourcesV1Api,
        DiscoverySourceTestErrorCategory,
        DiscoverySourceTestOutcome,
        Job,
        PutDiscoverySourceTestResult,
    )
    from arthur_client.api_bindings import (
        TestDiscoverySourceJobSpec as SourceTestJobSpec,
    )
    from arthur_client.api_bindings import (
        ValidationOutcome,
    )

    from job_executors.discovery_source_test_executor import DiscoverySourceTestExecutor

needs_test_connection = pytest.mark.skipif(
    not TEST_DISCOVERY_SOURCE_SUPPORTED,
    reason="installed arthur-client predates TEST_DISCOVERY_SOURCE",
)


def run_test_connection(logger: logging.Logger, preview_limit: int = 4) -> Any:
    """What the engine reports to the Platform for Test Connection on this source."""
    client = MagicMock(spec=DiscoverySourcesV1Api)
    client.retrieve_discovery_source_credentials.return_value = dict(CREDS)
    job = MagicMock(spec=Job)
    job.id = "77777777-7777-7777-7777-777777777777"
    spec = SourceTestJobSpec(
        workspace_id="11111111-1111-1111-1111-111111111111",
        data_plane_id="22222222-2222-2222-2222-222222222222",
        discovery_source_config_id="33333333-3333-3333-3333-333333333333",
        discovery_source_config=config(),
        lookback_hours=24,
        test_id="66666666-6666-6666-6666-666666666666",
        preview_limit=preview_limit,
    )
    DiscoverySourceTestExecutor(client, logger).execute(
        job,
        "99999999-9999-9999-9999-999999999999",
        spec,
    )
    result: PutDiscoverySourceTestResult = (
        client.put_discovery_source_test_result.call_args.kwargs[
            "put_discovery_source_test_result"
        ]
    )
    return result


@needs_test_connection
def test_test_connection_previews_rows_that_pass_the_column_check(
    fake: FakeWiz,
    job_log: tuple[logging.Logger, io.StringIO],
) -> None:
    result = run_test_connection(job_log[0])
    assert result.outcome == DiscoverySourceTestOutcome.SUCCEEDED
    assert result.reachability == DiscoverySourceReachability.REACHABLE
    assert result.output_column_check.outcome == ValidationOutcome.PASS
    assert len(result.rows) == 4
    assert result.truncated is True
    assert {r["external_id"] for r in result.rows} <= AI_SPM_IDS | WORKLOAD_IDS


@needs_test_connection
@with_fake(fault="bad-credentials")
def test_test_connection_reads_refused_credentials_as_authentication(
    fake: FakeWiz,
    job_log: tuple[logging.Logger, io.StringIO],
) -> None:
    result = run_test_connection(job_log[0])
    assert result.outcome == DiscoverySourceTestOutcome.FAILED
    assert result.error.category == DiscoverySourceTestErrorCategory.AUTHENTICATION
    assert result.error.vendor_status_code == 401
    assert result.reachability == DiscoverySourceReachability.REACHABLE
    assert (
        "Wiz token request failed with HTTP 401 (access_denied)" in result.error.message
    )
    assert DEFAULT_CLIENT_SECRET not in result.error.message


@needs_test_connection
@with_fake(fault="forbidden-ip")
def test_test_connection_names_the_ip_allowlist(
    fake: FakeWiz,
    job_log: tuple[logging.Logger, io.StringIO],
) -> None:
    result = run_test_connection(job_log[0])
    assert result.error.category == DiscoverySourceTestErrorCategory.AUTHORIZATION
    assert result.error.vendor_status_code == 403
    assert "HTTP 403 (FORBIDDEN_IP)" in result.error.message
    assert "IP allowlist" in result.error.message


@needs_test_connection
@with_fake(fault="missing-scope")
def test_test_connection_succeeds_and_logs_the_scopes_wiz_asked_for(
    fake: FakeWiz,
    job_log: tuple[logging.Logger, io.StringIO],
) -> None:
    logger, log = job_log
    result = run_test_connection(logger, preview_limit=50)
    assert result.outcome == DiscoverySourceTestOutcome.SUCCEEDED
    assert {r["external_id"] for r in result.rows} == AI_SPM_IDS
    assert SCOPE_DENIAL in log.getvalue()
