"""A SIEM result's columns and rows, as records. Nothing here knows which SIEM.

THE COLUMNS ARE CHECKED BEFORE A SINGLE RECORD IS BUILT. `DiscoveryOutputRecord` does not
forbid extra fields, so building first would let pydantic drop a column the contract
does not describe -- `agentName` beside `name`, a helper `hits` count -- with no error
anywhere. Once a record exists the result's own column list is gone, which is why the
check takes the vendor's column names rather than records.
"""

import logging
from collections import Counter
from typing import Any, Iterable, Mapping, Optional, Sequence

from arthur_client.api_bindings import ValidationOutcome
from arthur_common.models.agent_discovery_schemas import (
    DiscoveredAgentRecord,
    DiscoveryOutputRecord,
)
from arthur_common.models.agent_governance_schemas import (
    SIEMAgentCreationSource,
    SourceAddress,
)
from pydantic import ValidationError

from job_executors.discovery_output_contract import (
    OutputContractError,
    check_columns,
    describe,
)

# The columns a row may carry into a record, read off the contract rather than listed,
# so a column added to it is picked up without an edit here.
_CONTRACT_COLUMNS = frozenset(DiscoveryOutputRecord.model_fields)


def require_contract_columns(columns: Iterable[str], subject: str) -> None:
    """Fail a result whose columns are not the contract's, naming both sides.

    Raised as `OutputContractError` so the run records the per-column result, the same
    as a batch the scan loop refuses.
    """
    result = check_columns(columns)
    if result.outcome is ValidationOutcome.FAIL:
        raise OutputContractError(describe(result, subject), result)


def records_from_rows(
    rows: Sequence[Mapping[str, Any]],
    *,
    vendor: str,
    instance: str,
    query: str,
    logger: logging.Logger,
    scope: Optional[str] = None,
) -> list[DiscoveredAgentRecord]:
    """One record per row, stamped with where it came from.

    A row that does not make a record -- a blank `external_id`, a `last_seen` that is
    not a time, a multivalue field where one value was expected -- is reported and
    skipped. One bad row is the customer's data, not a broken scan, and the rows behind
    it are unaffected.

    The address names the SIGHTING: `resource_id` is the row's own `external_id`,
    because a SIEM has no other identifier for what it saw, and `query` is what produced
    it, so the record can be explained and re-run.
    """
    records: list[DiscoveredAgentRecord] = []
    skipped = 0
    # One line per distinct problem with its count, not one per row: a query whose
    # every row has the same bad column would otherwise log once per row.
    problems: Counter[str] = Counter()
    for row in rows:
        fields = {k: v for k, v in row.items() if k in _CONTRACT_COLUMNS}
        try:
            # The row on its own first, so a bad value is reported under the column
            # the customer's query named rather than under the address built from it.
            output = DiscoveryOutputRecord(**fields)
            records.append(
                DiscoveredAgentRecord(
                    **output.model_dump(exclude_unset=True),
                    creation_source=SIEMAgentCreationSource(
                        vendor=vendor,
                        address=SourceAddress(
                            instance=instance,
                            scope=scope,
                            resource_id=output.external_id,
                            query=query,
                        ),
                    ),
                ),
            )
        except ValidationError as exc:
            skipped += 1
            # The field names and pydantic's reasons, never the row's values: a log
            # line is not where a customer's log data should be copied to.
            problems.update(
                {
                    f"{'.'.join(str(p) for p in e['loc'])}: {e['msg']}"
                    for e in exc.errors()
                }
            )
    for problem, count in problems.most_common():
        logger.warning(
            "%s: %s result row(s) could not become a record (%s)",
            vendor,
            count,
            problem,
        )
    if skipped:
        logger.warning(
            "%s: %s of %s result row(s) skipped as invalid",
            vendor,
            skipped,
            len(rows),
        )
    return records
