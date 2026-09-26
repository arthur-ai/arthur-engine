"""The D-02 output contract, checked at the seam every connector crosses.

Beside the seam rather than in `discovery/`: that package is the connectors, and
importing it registers them, so the module the seam guards with cannot live there.

The contract is `arthur_common.DiscoveryOutputRecord`, read off the model rather than
restated here: app_plane checks a config and ML Engine checks every run, and a
hand-written copy in one repo is how the two silently stop describing the same thing.

Only the SET OF COLUMN NAMES is compared. The query text is never parsed, so a config
is judged on what it produced rather than on Arthur's reading of a language it does not
speak.

`unmapped_columns` is not pedantry. `DiscoveryOutputRecord` does not set
`extra="forbid"`, so pydantic's default drops an undeclared column on construction --
a query returning `agentName` beside `name` builds a valid record and loses the column
with no error anywhere. Once a record exists the raw column set is gone, which is why
the check reads columns rather than records.
"""

from datetime import datetime, timezone
from typing import Iterable, Mapping, Optional, Sequence

from arthur_client.api_bindings import OutputColumnCheckResult, ValidationOutcome
from arthur_common.models.agent_discovery_schemas import (
    DiscoveredAgentRecord,
    DiscoveryOutputRecord,
)

# What a CONNECTOR adds to what a source's QUERY returns. Derived rather than listed,
# for the same reason `required_columns()` is: a column added to either model must not
# need a second edit here to stay classified.
#
# These are never `unmapped`. A query owing `creation_source` would be a query owing a
# column no query can produce.
CONNECTOR_SUPPLIED_COLUMNS = frozenset(DiscoveredAgentRecord.model_fields) - frozenset(
    DiscoveryOutputRecord.model_fields,
)


class OutputContractError(Exception):
    """A batch that does not satisfy the output contract.

    Carries the check result so a caller can report per-column rather than re-deriving
    it from the message.
    """

    def __init__(self, message: str, result: OutputColumnCheckResult) -> None:
        super().__init__(message)
        self.result = result


def check_columns(columns: Iterable[str]) -> OutputColumnCheckResult:
    """Compare one run's column names against the contract.

    Read through `DiscoveryOutputRecord` and never through a record instance:
    `required_columns()` is inherited, so asking a `DiscoveredAgentRecord` what the
    contract requires gets the connector's columns back as though a query owed them.
    """
    supplied = {str(column) for column in columns}
    missing = sorted(DiscoveryOutputRecord.required_columns() - supplied)
    unmapped = sorted(
        supplied
        - DiscoveryOutputRecord.required_columns()
        - DiscoveryOutputRecord.optional_columns()
        - CONNECTOR_SUPPLIED_COLUMNS,
    )
    return OutputColumnCheckResult(
        outcome=(
            ValidationOutcome.FAIL if (missing or unmapped) else ValidationOutcome.PASS
        ),
        missing_columns=missing,
        unmapped_columns=unmapped,
        checked_at=datetime.now(timezone.utc),
    )


def passing_result() -> OutputColumnCheckResult:
    """The result for records that satisfy the contract by construction.

    A `DiscoveryOutputRecord` instance cannot be missing a required column -- pydantic
    refused to build it otherwise -- and carries no column the contract does not
    describe. Recorded as a real pass rather than left null so a run that published
    typed records is distinguishable from one that never got as far as checking.
    """
    return OutputColumnCheckResult(
        outcome=ValidationOutcome.PASS,
        missing_columns=[],
        unmapped_columns=[],
        checked_at=datetime.now(timezone.utc),
    )


def describe(result: OutputColumnCheckResult, subject: str) -> str:
    """The failure message for a FAIL result, naming the columns on both sides."""
    parts = []
    if result.missing_columns:
        parts.append(f"missing {', '.join(result.missing_columns)}")
    if result.unmapped_columns:
        parts.append(
            f"{', '.join(result.unmapped_columns)} not described by the contract",
        )
    return (
        f"{subject} does not satisfy the discovery output contract: "
        f"{'; '.join(parts)}."
    )


def check_batch(batch: Sequence[object], subject: str) -> OutputColumnCheckResult:
    """Hold a scanner to the contract before its batch reaches the sink.

    The seam's type hint is not enforcement -- nothing checks it at runtime -- and a
    batch that is not what it claims fails inside task resolution instead, naming the
    sink's problem rather than the connector's.

    A raw row is checked on its own keys, so a query that returned the wrong columns is
    told which ones. A row whose columns are right is still refused: shaping a row into
    a record is the connector's, and `creation_source` is a column no query returns.
    """
    for item in batch:
        if isinstance(item, DiscoveryOutputRecord):
            continue
        if isinstance(item, Mapping):
            result = check_columns(item.keys())
            raise OutputContractError(
                (
                    describe(result, subject)
                    if result.outcome is ValidationOutcome.FAIL
                    else f"{subject} yielded raw rows carrying the contract's columns "
                    f"but not shaped into DiscoveryOutputRecord."
                ),
                result,
            )
        # No columns to read, so the contract reports every required one as missing --
        # which is the truth about an object that supplies none of them.
        result = check_columns(())
        raise OutputContractError(
            f"{subject} yielded {type(item).__name__}, not a DiscoveryOutputRecord, "
            f"so it supplies none of the contract's columns: "
            f"{', '.join(result.missing_columns or [])}.",
            result,
        )
    return passing_result()


def result_payload(
    result: Optional[OutputColumnCheckResult],
) -> Optional[dict[str, object]]:
    """The result as JSON-serializable primitives.

    Built here rather than through the generated model's `to_dict`, which leaves
    `checked_at` as a datetime and cannot be handed to `json.dumps`.
    """
    if result is None:
        return None
    return {
        "outcome": result.outcome.value,
        "missing_columns": list(result.missing_columns or []),
        "unmapped_columns": list(result.unmapped_columns or []),
        "checked_at": result.checked_at.isoformat(),
    }
