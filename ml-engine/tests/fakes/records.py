"""A connector's output as a test of an agent-level behaviour reads it."""

from typing import Any, Iterable

from job_executors.discovery_scan import CorroboratingRecord


def agent_records(batches: Iterable[Iterable[Any]]) -> list[Any]:
    """Every record in `batches` that names an agent.

    A `CorroboratingRecord` is evidence for the agent record before it, so a test that
    counts machines, agents or what a scan dated reads the agent records alone.
    """
    return [
        record
        for batch in batches
        for record in batch
        if not isinstance(record, CorroboratingRecord)
    ]
