import json
import logging
from datetime import datetime, timezone
from typing import Iterator, Mapping, Optional, Sequence

import pytest
from arthur_client.api_bindings import DiscoverySourceConfigSpec, ValidationOutcome
from arthur_common.models.agent_discovery_schemas import (
    DiscoveredAgentRecord,
    DiscoveryOutputRecord,
)

from job_executors.discovery_output_contract import (
    CONNECTOR_SUPPLIED_COLUMNS,
    OutputContractError,
    check_batch,
    check_columns,
    passing_result,
    result_payload,
)
from job_executors.discovery_scan import DiscoveryScanOutcome, run_source_scan

WORKSPACE_ID = "11111111-1111-1111-1111-111111111111"
DATA_PLANE_ID = "22222222-2222-2222-2222-222222222222"
SOURCE_ID = "44444444-4444-4444-4444-444444444444"
REQUIRED = ["external_id", "name", "last_seen"]


def _config(vendor: str = "splunk_enterprise") -> DiscoverySourceConfigSpec:
    return DiscoverySourceConfigSpec(
        discovery_source_id=SOURCE_ID,
        name="splunk prod",
        vendor=vendor,
        query="search index=agents",
        query_language="spl",
        lookback_window_seconds=3600,
    )


def _record(external_id: str = "a") -> DiscoveryOutputRecord:
    return DiscoveryOutputRecord(
        external_id=external_id,
        name=f"agent-{external_id}",
        last_seen=datetime(2026, 9, 17, 12, 0, tzinfo=timezone.utc),
    )


def _outcome() -> DiscoveryScanOutcome:
    return DiscoveryScanOutcome(
        discovery_source_config_id="33333333-3333-3333-3333-333333333333",
        discovery_source_config_name="splunk prod",
        discovery_source_id=SOURCE_ID,
        vendor="splunk_enterprise",
        job_id="77777777-7777-7777-7777-777777777777",
        scan_id=None,
        lookback_hours=1,
    )


class YieldingScanner:
    def __init__(self, batches: list[Sequence[object]]) -> None:
        self.batches = batches

    def scan(
        self,
        config: DiscoverySourceConfigSpec,
        lookback_hours: int,
        credentials: Mapping[str, Optional[str]],
        source_fields: Mapping[str, str],
        logger: logging.Logger,
    ) -> Iterator[Sequence[object]]:
        yield from self.batches


class RecordingSink:
    def __init__(self) -> None:
        self.batches: list[list[str]] = []

    def publish(
        self,
        workspace_id: str,
        data_plane_id: str,
        config: DiscoverySourceConfigSpec,
        records: Sequence[DiscoveryOutputRecord],
    ) -> int:
        self.batches.append([r.external_id for r in records])
        return len(records)


def _scan(
    batches: list[Sequence[object]],
) -> tuple[DiscoveryScanOutcome, RecordingSink]:
    outcome, sink = _outcome(), RecordingSink()
    run_source_scan(
        config=_config(),
        lookback_hours=1,
        workspace_id=WORKSPACE_ID,
        data_plane_id=DATA_PLANE_ID,
        outcome=outcome,
        scanner=YieldingScanner(batches),
        sink=sink,
        logger=logging.getLogger("test-output-contract"),
        credentials={},
        source_fields={},
    )
    return outcome, sink


# --- the contract itself ----------------------------------------------------------


def test_the_connector_columns_are_derived_from_the_two_models() -> None:
    """A column added to either model must not need a second edit here to stay
    classified, which is the same reason `required_columns()` is derived."""
    assert CONNECTOR_SUPPLIED_COLUMNS == frozenset(
        DiscoveredAgentRecord.model_fields,
    ) - frozenset(DiscoveryOutputRecord.model_fields)
    assert CONNECTOR_SUPPLIED_COLUMNS == {"creation_source", "task_id"}


def test_a_query_is_neither_asked_for_nor_faulted_on_the_connector_columns() -> None:
    """`creation_source` is a column no query can produce, so requiring it would fault
    every source, and flagging it as unmapped would fault every connector."""
    assert check_columns(REQUIRED).outcome is ValidationOutcome.PASS
    assert (
        check_columns(REQUIRED + sorted(CONNECTOR_SUPPLIED_COLUMNS)).outcome
        is ValidationOutcome.PASS
    )


def test_the_contract_is_read_through_the_output_record_not_the_connector_record() -> (
    None
):
    """`required_columns()` is inherited, so asking a `DiscoveredAgentRecord` what the
    contract requires answers for the connector's columns too. A validator reaching
    through a record instance would fault every well-formed query."""
    assert "creation_source" in DiscoveredAgentRecord.required_columns()
    assert "creation_source" not in DiscoveryOutputRecord.required_columns()
    assert check_columns(REQUIRED).missing_columns == []


def test_optional_columns_may_be_supplied_or_left_out() -> None:
    assert check_columns(REQUIRED + ["tools", "llm_models"]).outcome is (
        ValidationOutcome.PASS
    )
    assert check_columns(REQUIRED).outcome is ValidationOutcome.PASS


def test_a_missing_column_is_named() -> None:
    result = check_columns(["external_id"])
    assert result.outcome is ValidationOutcome.FAIL
    assert result.missing_columns == ["last_seen", "name"]
    assert result.unmapped_columns == []


def test_a_column_the_contract_does_not_describe_is_named() -> None:
    """`DiscoveryOutputRecord` does not set `extra="forbid"`, so pydantic drops an
    undeclared column on construction. A query returning `agentName` beside `name`
    builds a valid record and loses the column with no error anywhere -- the check
    reads columns rather than records for exactly this reason."""
    assert (
        "agentName"
        not in DiscoveryOutputRecord(
            external_id="a",
            name="n",
            last_seen=datetime(2026, 9, 17, tzinfo=timezone.utc),
            agentName="dropped",
        ).model_dump()
    )

    result = check_columns(REQUIRED + ["agentName"])
    assert result.outcome is ValidationOutcome.FAIL
    assert result.unmapped_columns == ["agentName"]
    assert result.missing_columns == []


def test_both_sides_are_reported_together() -> None:
    result = check_columns(["external_id", "agentName"])
    assert result.missing_columns == ["last_seen", "name"]
    assert result.unmapped_columns == ["agentName"]


# --- the batch guard --------------------------------------------------------------


def test_typed_records_satisfy_the_contract_by_construction() -> None:
    """Pydantic refused to build a record missing a required column, so a batch of
    them passes without a column ever being read off one."""
    assert check_batch([_record(), _record("b")], "source").outcome is (
        ValidationOutcome.PASS
    )


def test_raw_rows_are_refused_with_their_columns_named() -> None:
    with pytest.raises(OutputContractError) as caught:
        check_batch([{"external_id": "a", "agentName": "x"}], "Source config 'x'")
    assert "missing last_seen, name" in str(caught.value)
    assert "agentName not described by the contract" in str(caught.value)
    assert caught.value.result.outcome is ValidationOutcome.FAIL


def test_raw_rows_carrying_the_right_columns_are_still_refused() -> None:
    """Shaping a row into a record is the connector's: the sink resolves a record onto
    a task and reads `creation_source`, which no query returns."""
    row = {"external_id": "a", "name": "n", "last_seen": "2026-09-17T12:00:00Z"}
    with pytest.raises(OutputContractError) as caught:
        check_batch([row], "Source config 'x'")
    assert "not shaped into DiscoveryOutputRecord" in str(caught.value)
    assert caught.value.result.outcome is ValidationOutcome.PASS


def test_something_that_is_not_a_row_is_refused_by_type() -> None:
    with pytest.raises(OutputContractError) as caught:
        check_batch(["nope"], "Source config 'x'")
    assert "yielded str" in str(caught.value)
    assert caught.value.result.missing_columns == ["external_id", "last_seen", "name"]


# --- the run ----------------------------------------------------------------------


def test_a_failing_batch_never_reaches_the_sink() -> None:
    """Checked before publishing, so a batch that fails the contract is not
    half-delivered and the run names the columns rather than the sink naming whatever
    it choked on."""
    outcome, sink = _outcome(), RecordingSink()
    with pytest.raises(OutputContractError):
        run_source_scan(
            config=_config(),
            lookback_hours=1,
            workspace_id=WORKSPACE_ID,
            data_plane_id=DATA_PLANE_ID,
            outcome=outcome,
            scanner=YieldingScanner([[{"external_id": "a"}]]),
            sink=sink,
            logger=logging.getLogger("test-output-contract"),
            credentials={},
            source_fields={},
        )

    assert sink.batches == []
    assert outcome.records_published == 0
    assert outcome.batches_published == 0
    assert outcome.error is not None
    assert "missing last_seen, name" in outcome.error
    assert outcome.output_column_check is not None
    assert outcome.output_column_check.outcome is ValidationOutcome.FAIL


def test_an_earlier_good_batch_is_kept_when_a_later_one_fails_the_contract() -> None:
    """Same resiliency as any other mid-scan failure: what was already published
    stays, and the run reports both the contribution and the failure."""
    outcome, sink = _outcome(), RecordingSink()
    with pytest.raises(OutputContractError):
        run_source_scan(
            config=_config(),
            lookback_hours=1,
            workspace_id=WORKSPACE_ID,
            data_plane_id=DATA_PLANE_ID,
            outcome=outcome,
            scanner=YieldingScanner([[_record("a")], [{"external_id": "b"}]]),
            sink=sink,
            logger=logging.getLogger("test-output-contract"),
            credentials={},
            source_fields={},
        )

    assert sink.batches == [["a"]]
    assert outcome.records_published == 1
    assert outcome.output_column_check is not None
    assert outcome.output_column_check.outcome is ValidationOutcome.FAIL


def test_a_run_of_typed_records_records_a_pass() -> None:
    """A real pass rather than a null, so a run that published records is
    distinguishable from one that never got as far as checking."""
    outcome, sink = _scan([[_record("a"), _record("b")]])
    assert sink.batches == [["a", "b"]]
    assert outcome.output_column_check is not None
    assert outcome.output_column_check.outcome is ValidationOutcome.PASS


def test_a_run_that_never_produced_a_batch_records_no_check() -> None:
    outcome, sink = _scan([])
    assert sink.batches == []
    assert outcome.output_column_check is None


def test_the_outcome_payload_carries_the_check_and_is_json_serializable() -> None:
    """The outcome is emitted as JSON in the job log -- the exporter drops `extra` --
    so the check has to survive `json.dumps`, which the generated model's own
    `to_dict` does not: it leaves `checked_at` a datetime."""
    outcome = _outcome()
    outcome.output_column_check = passing_result()
    payload = json.loads(json.dumps(outcome.to_log_payload(), sort_keys=True))
    assert payload["output_column_check"]["outcome"] == "pass"
    assert payload["output_column_check"]["missing_columns"] == []
    assert isinstance(payload["output_column_check"]["checked_at"], str)
    assert result_payload(None) is None
