"""The job log exporter: what reaches the job's logs, and what also reaches its errors."""

import logging
from unittest.mock import MagicMock

from job_log_exporter import REPORT_AS_JOB_ERROR, ScopeJobLogExporter


def _record(
    message: str,
    level: int = logging.ERROR,
    **extra: object,
) -> logging.LogRecord:
    record = logging.LogRecord("job", level, __file__, 1, message, None, None)
    for key, value in extra.items():
        setattr(record, key, value)
    return record


def _exporter() -> tuple[ScopeJobLogExporter, MagicMock]:
    jobs_client = MagicMock()
    return ScopeJobLogExporter("job-1", "run-1", jobs_client), jobs_client


def _posted_errors(jobs_client: MagicMock) -> list[str]:
    return [
        error.error
        for c in jobs_client.post_job_errors.call_args_list
        for error in c.kwargs["job_errors"].errors
    ]


def test_an_error_flagged_for_the_job_is_posted_as_one_of_its_errors() -> None:
    """For a failure with no exception to carry, e.g. an agent the Agents API did not
    store while the rest of its batch landed."""
    exporter, jobs_client = _exporter()
    exporter.emit(_record("agent for task b was not stored", **REPORT_AS_JOB_ERROR))
    assert _posted_errors(jobs_client) == ["agent for task b was not stored"]
    assert jobs_client.post_job_logs.call_count == 1, "and it is still a log line"


def test_an_ordinary_error_line_stays_a_log_line() -> None:
    """Opt-in, so no existing error log starts counting against a job."""
    exporter, jobs_client = _exporter()
    exporter.emit(_record("something went sideways"))
    assert _posted_errors(jobs_client) == []
    assert jobs_client.post_job_logs.call_count == 1


def test_the_flag_does_nothing_below_error() -> None:
    exporter, jobs_client = _exporter()
    exporter.emit(
        _record("just so you know", level=logging.WARNING, **REPORT_AS_JOB_ERROR),
    )
    assert _posted_errors(jobs_client) == []
