import io
import json
import logging
from dataclasses import asdict
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
import urllib3
from arthur_client.api_bindings import (
    ApiClient,
    DiscoveryRunStatus,
    DiscoveryRunsV1Api,
)
from arthur_client.api_bindings.exceptions import ApiException
from arthur_client.api_bindings.rest import RESTResponse

from job_executors.discovery_run_reporter import (
    DELIVERY_ATTEMPTS,
    PlatformRunReporter,
    platform_outcome,
)
from job_executors.discovery_scan import DeviceCoverage, DiscoveryScanOutcome

JOB_ID = "77777777-7777-7777-7777-777777777777"
JOB_RUN_ID = "99999999-9999-9999-9999-999999999999"
STARTED = datetime(2026, 9, 30, 12, 0, tzinfo=timezone.utc)
FINISHED = datetime(2026, 9, 30, 12, 1, tzinfo=timezone.utc)


def _outcome(**changes: object) -> DiscoveryScanOutcome:
    outcome = DiscoveryScanOutcome(
        discovery_source_config_id="33333333-3333-3333-3333-333333333333",
        discovery_source_config_name="jamf prod",
        discovery_source_id="44444444-4444-4444-4444-444444444444",
        vendor="jamf_pro",
        job_id=JOB_ID,
        scan_id=None,
        lookback_hours=24,
        started_at=STARTED,
        finished_at=FINISHED,
        records_published=48,
        batches_published=1,
    )
    for name, value in changes.items():
        setattr(outcome, name, value)
    return outcome


class VendorHTTPError(RuntimeError):
    def __init__(self, status_code: int) -> None:
        super().__init__(f"token rejected for client {status_code}")
        self.status_code = status_code


def test_a_finished_scan_is_a_done_run_carrying_its_device_coverage() -> None:
    coverage = DeviceCoverage(
        devices_read=60,
        devices_in_scope=60,
        devices_decoded=55,
        devices_unreadable=5,
        unreadable_by_reason={"never-reported": 4, "no-cache": 1},
    )

    body = platform_outcome(_outcome(device_coverage=coverage))

    assert body.status == DiscoveryRunStatus.DONE
    assert (body.records_published, body.batches_published) == (48, 1)
    assert (body.error_count, body.error_code) == (0, None)
    assert body.device_coverage is not None
    assert body.device_coverage.to_dict() == asdict(coverage)


def test_a_failed_scan_is_a_failed_run_with_its_code_and_none_of_its_text() -> None:
    outcome = _outcome(records_published=20)
    outcome.record_failure(VendorHTTPError(401))

    body = platform_outcome(outcome)

    assert body.status == DiscoveryRunStatus.FAILED
    assert (body.error_count, body.error_code) == (1, "authentication_failed")
    assert body.records_published == 20
    sent = json.dumps(ApiClient().sanitize_for_serialization(body))
    assert "token rejected" not in sent
    assert "device_coverage" not in sent


class FakeRuns:
    """The run store's PUT, answering with each response in turn."""

    def __init__(self, *responses: object) -> None:
        self.responses = list(responses)
        self.calls: list[tuple[str, str, object, object]] = []

    def put_discovery_run_outcome(
        self,
        job_id: str,
        job_run_id: str,
        body: object,
        _request_timeout: object = None,
    ) -> object:
        self.calls.append((job_id, job_run_id, body, _request_timeout))
        response = self.responses.pop(0)
        if isinstance(response, BaseException):
            raise response
        return response


def _reporter(runs: FakeRuns, sleeps: list[float]) -> PlatformRunReporter:
    return PlatformRunReporter(
        runs,  # type: ignore[arg-type]
        job_id=JOB_ID,
        job_run_id=JOB_RUN_ID,
        logger=logging.getLogger("test-run-reporter"),
        sleep=sleeps.append,
    )


def test_an_outcome_is_delivered_for_its_job_attempt() -> None:
    runs = FakeRuns(SimpleNamespace(id="run-1"))

    _reporter(runs, []).report(_outcome())

    ((job_id, job_run_id, body, timeout),) = runs.calls
    assert (job_id, job_run_id) == (JOB_ID, JOB_RUN_ID)
    assert body == platform_outcome(_outcome())
    assert timeout is not None


def test_a_platform_that_is_briefly_down_gets_the_same_report_again() -> None:
    runs = FakeRuns(
        ApiException(status=503, reason="Service Unavailable"),
        ConnectionError("reset by peer"),
        SimpleNamespace(id="run-1"),
    )
    sleeps: list[float] = []

    _reporter(runs, sleeps).report(_outcome())

    assert len(runs.calls) == 3
    assert runs.calls[0][2] == runs.calls[2][2]
    assert sleeps == [1, 2]


@pytest.mark.parametrize(
    "failure",
    [
        ApiException(status=409, reason="Conflict"),
        ApiException(status=422, reason="Unprocessable Entity"),
    ],
)
def test_a_refused_report_is_logged_not_retried_and_never_raised(
    failure: ApiException,
    caplog: pytest.LogCaptureFixture,
) -> None:
    runs = FakeRuns(failure)

    with caplog.at_level(logging.ERROR):
        _reporter(runs, []).report(_outcome())

    assert len(runs.calls) == 1
    assert f"HTTP {failure.status}" in caplog.text


def test_an_unreachable_platform_gives_up_without_failing_the_job(
    caplog: pytest.LogCaptureFixture,
) -> None:
    runs = FakeRuns(*[ConnectionError("unreachable")] * DELIVERY_ATTEMPTS)

    with caplog.at_level(logging.ERROR):
        _reporter(runs, []).report(_outcome())

    assert len(runs.calls) == DELIVERY_ATTEMPTS
    assert "did not record this run's outcome" in caplog.text


def test_an_outcome_the_run_store_cannot_hold_is_logged_and_not_sent(
    caplog: pytest.LogCaptureFixture,
) -> None:
    runs = FakeRuns()

    with caplog.at_level(logging.ERROR):
        _reporter(runs, []).report(_outcome(records_published=-1))

    assert runs.calls == []
    assert "does not fit the Platform's run store" in caplog.text


def test_the_report_goes_through_the_generated_client(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Over a stubbed transport rather than a mock of the method, so a request the
    client cannot build, or a stored run it cannot read back, fails here."""
    client = DiscoveryRunsV1Api(ApiClient())
    stored = {
        **ApiClient().sanitize_for_serialization(platform_outcome(_outcome())),
        "id": "12121212-1212-1212-1212-121212121212",
        "job_id": JOB_ID,
        "job_run_id": JOB_RUN_ID,
        "organization_id": "13131313-1313-1313-1313-131313131313",
        "workspace_id": "11111111-1111-1111-1111-111111111111",
        "engine_id": "22222222-2222-2222-2222-222222222222",
        "scan_id": None,
        "discovery_source_config_id": "33333333-3333-3333-3333-333333333333",
        "discovery_source_config_name": "jamf prod",
        "discovery_source_id": "44444444-4444-4444-4444-444444444444",
        "vendor": "jamf_pro",
        "lookback_hours": 24,
        "received_at": FINISHED.isoformat(),
        "device_coverage": None,
    }
    client.api_client.call_api = MagicMock(  # type: ignore[method-assign]
        return_value=RESTResponse(
            urllib3.HTTPResponse(
                body=io.BytesIO(json.dumps(stored).encode()),
                headers={"content-type": "application/json"},
                status=200,
                preload_content=False,
            ),
        ),
    )

    with caplog.at_level(logging.INFO):
        PlatformRunReporter(
            client,
            job_id=JOB_ID,
            job_run_id=JOB_RUN_ID,
            logger=logging.getLogger("test-run-reporter-client"),
        ).report(_outcome())

    method, url, _headers, body, *_ = client.api_client.call_api.call_args.args
    assert method == "PUT"
    assert url.endswith(f"/v1/jobs/{JOB_ID}/runs/{JOB_RUN_ID}/discovery_outcome")
    assert (body["status"], body["records_published"]) == ("done", 48)
    assert "Recorded this scan as discovery run 12121212" in caplog.text
