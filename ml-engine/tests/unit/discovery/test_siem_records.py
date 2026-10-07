"""Shared SIEM row handling: how rows that cannot become records are reported."""

import logging

import pytest

from discovery.siem.records import records_from_rows

LOG = logging.getLogger("test.siem.records")


def good(i: int) -> dict[str, str]:
    return {
        "external_id": f"10.0.0.{i}:api.anthropic.com",
        "name": f"client {i}",
        "last_seen": "1790790000",
    }


def test_the_same_problem_on_many_rows_is_logged_once_with_its_count(
    caplog: pytest.LogCaptureFixture,
) -> None:
    secret_value = "customer-log-value-must-not-be-logged"
    rows = [good(1), *({**good(i), "external_id": "   "} for i in range(2, 1002))]
    rows.append({**good(1002), "last_seen": secret_value})

    with caplog.at_level(logging.WARNING, logger=LOG.name):
        records = records_from_rows(
            rows, vendor="splunk_enterprise", instance="h:8089", query="q", logger=LOG
        )

    assert len(records) == 1
    lines = [r.getMessage() for r in caplog.records]
    # one line per distinct problem, each with its count, then the summary
    assert len(lines) == 3, lines
    assert any("1000 result row(s)" in line and "external_id" in line for line in lines)
    assert any("1 result row(s)" in line and "last_seen" in line for line in lines)
    assert (
        lines[-1] == "splunk_enterprise: 1001 of 1002 result row(s) skipped as invalid"
    )
    assert secret_value not in caplog.text
