"""Splunk connector: the search job lifecycle, the contract check and the records.

A fake search head stands in for the REST API. It holds jobs the way splunkd does --
created, polled, paged and deleted by sid -- so a test can tell a job that was cleaned
up from one that was left holding a search slot.
"""

import datetime as dt
import logging
import ssl
from typing import Any, Optional
from urllib.parse import urlsplit

import pytest
import requests
from arthur_common.models.agent_governance_schemas import SIEMAgentCreationSource
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.x509.oid import NameOID

from arthur_client_support import TEST_DISCOVERY_SOURCE_SUPPORTED
from discovery.siem.records import records_from_rows
from discovery.siem.splunk.client import SplunkClient, SplunkError, SplunkSettings
from discovery.siem.splunk.connector import (
    VENDOR,
    SplunkConnector,
    search_text,
    settings_from,
)
from discovery.siem.tls import TLSVerification, normalize_pem, tls_session
from job_executors.discovery_output_contract import OutputContractError, check_batch
from job_executors.discovery_scan import (
    DiscoveryConfigurationError,
    DiscoveryErrorCode,
    failure_code,
)

LOG = logging.getLogger("test.splunk")
CREDS = {"auth_token": "tok-123"}
FIELDS = {"base_url": "https://splunk.example.com:8089"}
QUERY = (
    "search index=arthur_proxy | stats max(_time) AS last_seen BY src, url_domain "
    '| eval external_id=src.":".url_domain, name=url_domain." client on ".src '
    "| table external_id name last_seen"
)
COLUMNS = ["external_id", "name", "last_seen"]


def connection_test_category(exc: BaseException) -> str:
    """What Test Connection calls a failure raised before any batch arrived."""
    if not TEST_DISCOVERY_SOURCE_SUPPORTED:
        pytest.skip("installed arthur-client predates TEST_DISCOVERY_SOURCE")
    from job_executors.discovery_source_test_executor import _classify

    return str(_classify(exc, contacted=False).category.value)


def row(i: int) -> dict[str, Any]:
    return {
        "external_id": f"10.0.0.{i}:api.anthropic.com",
        "name": f"api.anthropic.com client on 10.0.0.{i}",
        # Splunk's JSON results carry every value as a string, and `_time` is a
        # fractional epoch -- the shape Splunk 10.4.4 returns.
        "last_seen": f"{1790790000 + i}.191",
    }


class FakeResponse:
    def __init__(
        self,
        status: int,
        body: Any = None,
        raw: Optional[bytes] = None,
    ) -> None:
        self.status_code, self._body = status, body
        self.headers: dict[str, str] = {}
        # `raw` is a body that is not JSON, the way a proxy's own error page is.
        self.content = raw if raw is not None else (b"" if body is None else b"x")
        self._raw = raw

    def json(self) -> Any:
        if self._raw is not None or self._body is None:
            raise ValueError("Expecting value: line 1 column 1 (char 0)")
        return self._body


class FakeSplunk:
    """A search head holding jobs by sid."""

    def __init__(
        self,
        rows: Optional[list[dict[str, Any]]] = None,
        columns: Optional[list[str]] = None,
        states: Optional[list[str]] = None,
        finalized: bool = False,
        result_count: Optional[int] = None,
        create_status: int = 201,
        create_body: Any = None,
        failed: bool = False,
        max_rows: Optional[int] = None,
        messages: Optional[list[dict[str, str]]] = None,
    ) -> None:
        self.rows = rows if rows is not None else [row(1), row(2), row(3)]
        self.columns = columns if columns is not None else COLUMNS
        self.states = list(states or ["DONE"])
        self.finalized = finalized
        self.result_count = len(self.rows) if result_count is None else result_count
        self.create_status = create_status
        self.create_body = create_body
        self.failed = failed
        # `[restapi] maxresultrows`: no results request returns more, whatever it asks.
        self.max_rows = max_rows
        self.messages = messages or []
        self.calls: list[dict[str, Any]] = []
        self.jobs: set[str] = set()
        self.deleted: list[str] = []

    def request(self, method: str, url: str, **kw: Any) -> FakeResponse:
        path = urlsplit(url).path
        self.calls.append({"method": method, "path": path, **kw})
        if method == "POST" and path == "/services/search/v2/jobs":
            if self.create_status >= 400:
                return FakeResponse(self.create_status, self.create_body)
            self.jobs.add("sid-1")
            return FakeResponse(self.create_status, {"sid": "sid-1"})
        sid = path.split("/")[5]
        if method == "DELETE":
            self.jobs.discard(sid)
            self.deleted.append(sid)
            return FakeResponse(200, {})
        if path.endswith("/results"):
            offset, count = kw["params"]["offset"], kw["params"]["count"]
            count = min(count, self.max_rows or count)
            page = self.rows[offset : offset + count]
            fields = [{"name": c} for c in self.columns] if page else []
            return FakeResponse(200, {"fields": fields, "results": page})
        state = self.states.pop(0) if len(self.states) > 1 else self.states[0]
        return FakeResponse(
            200,
            {
                "entry": [
                    {
                        "content": {
                            "dispatchState": state,
                            "isDone": state == "DONE",
                            "isFailed": self.failed,
                            "isFinalized": self.finalized,
                            "resultCount": self.result_count,
                            "messages": (
                                [{"type": "FATAL", "text": "Unknown search command"}]
                                if self.failed
                                else self.messages
                            ),
                        },
                    },
                ],
            },
        )


class FakeConfig:
    def __init__(self, query: Optional[str] = QUERY) -> None:
        self.query = query
        self.vendor = VENDOR
        self.name = "acme splunk"


class FakeClock:
    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.now += seconds


def connector_for(fake: FakeSplunk, page_size: int = 2) -> SplunkConnector:
    clock = FakeClock()

    def factory(settings: SplunkSettings, logger: logging.Logger) -> SplunkClient:
        settings = SplunkSettings(**{**settings.__dict__, "page_size": page_size})
        return SplunkClient(settings, logger=logger, session=fake)  # type: ignore[arg-type]

    return SplunkConnector(client_factory=factory, sleep=clock.sleep, clock=clock)


def run(
    fake: FakeSplunk,
    connector: Optional[SplunkConnector] = None,
    config: Optional[FakeConfig] = None,
    lookback_hours: int = 24,
) -> list[list[Any]]:
    connector = connector or connector_for(fake)
    return [
        list(batch)
        for batch in connector.scan(
            config or FakeConfig(),  # type: ignore[arg-type]
            lookback_hours,
            CREDS,
            FIELDS,
            LOG,
        )
    ]


# --- the job lifecycle -------------------------------------------------------------


def test_a_scan_pages_results_into_batches_and_deletes_its_job() -> None:
    fake = FakeSplunk(states=["QUEUED", "RUNNING", "DONE"])

    batches = run(fake)

    # page_size 2 over 3 rows: one batch per page, so page 1 is published even if
    # page 2 fails
    assert [len(b) for b in batches] == [2, 1]
    assert fake.deleted == ["sid-1"] and not fake.jobs
    for batch in batches:
        check_batch(batch, "splunk")


def test_the_job_carries_the_lookback_beside_the_query_not_inside_it() -> None:
    fake = FakeSplunk()

    run(fake, lookback_hours=6)

    create = fake.calls[0]
    assert create["data"]["search"] == QUERY
    assert create["data"]["earliest_time"] == "-6h"
    assert create["data"]["latest_time"] == "now"
    assert create["headers"]["Authorization"] == "Bearer tok-123"
    assert create["allow_redirects"] is False
    assert all(c["params"]["output_mode"] == "json" for c in fake.calls)


def test_a_lookback_of_zero_searches_all_time() -> None:
    fake = FakeSplunk()

    run(fake, lookback_hours=0)

    assert "earliest_time" not in fake.calls[0]["data"]


def test_records_carry_the_instance_and_the_query_that_found_them() -> None:
    fake = FakeSplunk(rows=[row(7)])

    [[record]] = run(fake)

    assert record.external_id == "10.0.0.7:api.anthropic.com"
    assert record.last_seen.timestamp() == 1790790007.191
    source = record.creation_source
    assert isinstance(source, SIEMAgentCreationSource)
    assert source.vendor == "splunk_enterprise"
    assert source.address.instance == "splunk.example.com:8089"
    assert source.address.resource_id == record.external_id
    assert source.address.query == QUERY
    # proxy logs say nothing about where the machine is, so neither does the record
    assert record.runs_on is None and record.platform is None


def test_a_job_left_queued_past_the_limit_names_the_search_quota() -> None:
    fake = FakeSplunk(states=["QUEUED"])

    with pytest.raises(SplunkError, match="srchJobsQuota"):
        run(fake)
    assert fake.deleted == ["sid-1"]


def test_a_search_splunk_accepts_then_fails_is_the_querys_to_fix() -> None:
    fake = FakeSplunk(failed=True)

    with pytest.raises(
        DiscoveryConfigurationError, match="Unknown search command"
    ) as caught:
        run(fake)
    assert fake.deleted == ["sid-1"]
    assert "HTTP" not in str(caught.value)
    # a scheduled scan blames the config, not Splunk, and so does Test Connection
    assert failure_code(caught.value) is DiscoveryErrorCode.NOT_CONFIGURED
    assert connection_test_category(caught.value) == "configuration"


def test_a_search_splunk_refuses_to_parse_is_the_querys_to_fix() -> None:
    fake = FakeSplunk(
        create_status=400,
        create_body={
            "messages": [
                {"type": "FATAL", "text": "Unknown search command 'tabel'."},
            ],
        },
    )

    with pytest.raises(DiscoveryConfigurationError, match="tabel") as caught:
        run(fake)
    # Test Connection reads a status out of "HTTP 400" in the text, which would make
    # this a vendor error again
    assert "HTTP" not in str(caught.value)
    assert failure_code(caught.value) is DiscoveryErrorCode.NOT_CONFIGURED
    assert connection_test_category(caught.value) == "configuration"


def test_a_page_capped_by_maxresultrows_does_not_end_the_scan() -> None:
    """A search head whose maxresultrows is below the page size returns short pages;
    every row Splunk counted must still be read."""
    fake = FakeSplunk(rows=[row(i) for i in range(5)], max_rows=2)

    batches = run(fake, connector=connector_for(fake, page_size=4))

    assert sum(len(b) for b in batches) == 5


def test_a_search_that_finished_with_a_warning_says_so(
    caplog: pytest.LogCaptureFixture,
) -> None:
    fake = FakeSplunk(
        messages=[
            {"type": "INFO", "text": "Your timerange was substituted"},
            {
                "type": "WARN",
                "text": "Search peer idx-2 is down; results may be incomplete",
            },
        ],
    )

    with caplog.at_level(logging.WARNING):
        run(fake)

    assert "results may be incomplete" in caplog.text
    assert "timerange" not in caplog.text


def test_a_stop_while_splunk_is_still_searching_ends_the_scan_cleanly() -> None:
    """The deadline must hold while the search runs, which is where the time goes."""
    fake = FakeSplunk(states=["RUNNING"])
    connector = connector_for(fake)
    connector.stop_when(lambda: True)

    assert run(fake, connector) == []
    assert not any(c["path"].endswith("/results") for c in fake.calls)
    assert fake.deleted == ["sid-1"]


def test_a_stop_between_pages_keeps_what_was_published() -> None:
    fake = FakeSplunk(rows=[row(i) for i in range(5)])
    connector = connector_for(fake)
    connector.stop_when(lambda: True)
    # finished before the first poll's stop check
    fake.states = ["DONE"]

    assert [len(b) for b in run(fake, connector)] == [2]
    assert fake.deleted == ["sid-1"]


def test_responses_captured_from_splunk_10_4_parse() -> None:
    """Bodies from a real Splunk Enterprise 10.4.4, trimmed and with the host renamed.

    The fake above is written to these; this pins them, so a drift in the fake cannot
    hide a drift from what splunkd actually sends.
    """
    status = {
        "entry": [
            {
                "content": {
                    "dispatchState": "DONE",
                    "isDone": True,
                    "isFailed": False,
                    "isFinalized": False,
                    "resultCount": 2,
                    "messages": [
                        {
                            "type": "INFO",
                            "text": "Your timerange was substituted based on your "
                            "search string",
                        },
                    ],
                },
            },
        ],
    }
    results = {
        "preview": False,
        "init_offset": 0,
        "messages": [],
        "fields": [{"name": "external_id"}, {"name": "name"}, {"name": "last_seen"}],
        "results": [
            {
                "external_id": "splunk-host:Metrics",
                "name": "Metrics",
                "last_seen": "1790815578.191",
            },
        ],
        "highlighted": {},
    }

    class Captured:
        def request(self, method: str, url: str, **kw: Any) -> FakeResponse:
            return FakeResponse(
                200,
                results if url.endswith("/results") else status,
            )

    client = SplunkClient(settings_from(CREDS, FIELDS), session=Captured())  # type: ignore[arg-type]

    job = client.job_status("1790815582.9")
    assert (job.is_done, job.is_failed, job.is_finalized) == (True, False, False)
    assert job.result_count == 2
    assert job.messages == (
        "INFO: Your timerange was substituted based on your search string",
    )
    columns, rows = client.results("1790815582.9", offset=0)
    assert columns == COLUMNS
    [record] = records_from_rows(
        rows,
        vendor=VENDOR,
        instance="splunk-host:8089",
        query=QUERY,
        logger=LOG,
    )
    assert record.last_seen.timestamp() == 1790815578.191


# --- the contract ------------------------------------------------------------------


def test_columns_that_miss_the_contract_fail_before_any_record_is_built() -> None:
    rows = [{"external_id": "a", "agentName": "x", "last_seen": "1790790000"}]
    fake = FakeSplunk(rows=rows, columns=["external_id", "agentName", "last_seen"])

    with pytest.raises(OutputContractError) as caught:
        run(fake)

    assert caught.value.result.missing_columns == ["name"]
    assert caught.value.result.unmapped_columns == ["agentName"]
    assert fake.deleted == ["sid-1"]


def test_a_row_that_cannot_be_a_record_is_skipped_and_reported(
    caplog: pytest.LogCaptureFixture,
) -> None:
    bad = {**row(2), "external_id": "   "}
    fake = FakeSplunk(rows=[row(1), bad, row(3)])

    with caplog.at_level(logging.WARNING):
        batches = run(fake)

    assert [r.external_id for b in batches for r in b] == [
        "10.0.0.1:api.anthropic.com",
        "10.0.0.3:api.anthropic.com",
    ]
    assert "skipped" in caplog.text
    # field names and reasons, never the customer's values
    assert "external_id" in caplog.text


# --- how complete the answer is ----------------------------------------------------


def test_a_finalized_search_is_reported_as_partial(
    caplog: pytest.LogCaptureFixture,
) -> None:
    with caplog.at_level(logging.WARNING):
        run(FakeSplunk(finalized=True))

    assert "partial" in caplog.text


def test_fewer_rows_than_splunk_reported_is_reported_as_truncation(
    caplog: pytest.LogCaptureFixture,
) -> None:
    with caplog.at_level(logging.WARNING):
        run(FakeSplunk(rows=[row(1)], result_count=5))

    assert "truncated" in caplog.text


def test_zero_rows_says_it_cannot_tell_a_clean_estate_from_no_access(
    caplog: pytest.LogCaptureFixture,
) -> None:
    with caplog.at_level(logging.WARNING):
        assert run(FakeSplunk(rows=[])) == []

    assert "srchIndexesAllowed" in caplog.text


# --- failures Test Connection has to name ------------------------------------------


def test_a_refused_token_carries_its_status_and_the_likely_causes() -> None:
    fake = FakeSplunk(
        create_status=401,
        create_body={
            "messages": [{"type": "WARN", "text": "call not properly authenticated"}],
        },
    )

    with pytest.raises(SplunkError) as caught:
        run(fake)

    assert caught.value.status_code == 401
    assert "HTTP Event Collector" in str(caught.value)
    assert "call not properly authenticated" in str(caught.value)
    assert "tok-123" not in str(caught.value)


def test_an_unreachable_search_head_stays_a_connection_error() -> None:
    class Down:
        def request(self, *a: Any, **kw: Any) -> Any:
            raise requests.ConnectionError("connection refused")

    client = SplunkClient(settings_from(CREDS, FIELDS), session=Down())  # type: ignore[arg-type]

    with pytest.raises(requests.ConnectionError, match="engine inside its network"):
        client.create_job("search x", earliest=None, latest="now")


def test_a_tls_failure_says_which_setting_fixes_it() -> None:
    class BadCert:
        def request(self, *a: Any, **kw: Any) -> Any:
            raise requests.exceptions.SSLError("hostname mismatch")

    client = SplunkClient(settings_from(CREDS, FIELDS), session=BadCert())  # type: ignore[arg-type]

    with pytest.raises(SplunkError, match="ca_only"):
        client.create_job("search x", earliest=None, latest="now")


@pytest.mark.parametrize(
    "response,message",
    [
        (FakeResponse(200, raw=b"<html>Proxy login</html>"), "not JSON"),
        (FakeResponse(200, ["not", "an", "object"]), "JSON list"),
    ],
)
def test_a_success_body_that_is_not_a_json_object_is_a_splunk_error(
    response: FakeResponse,
    message: str,
) -> None:
    """A proxy or load balancer can answer 200 with its own page instead of splunkd."""

    class Answers:
        def request(self, *a: Any, **kw: Any) -> FakeResponse:
            return response

    client = SplunkClient(settings_from(CREDS, FIELDS), session=Answers())  # type: ignore[arg-type]

    with pytest.raises(SplunkError, match=message) as caught:
        client.create_job("search x", earliest=None, latest="now")
    # the host answered, so Test Connection must still read it as reachable
    assert caught.value.status_code == 200


def test_an_error_body_that_is_not_an_object_still_reports_the_status() -> None:
    class Answers:
        def request(self, *a: Any, **kw: Any) -> FakeResponse:
            return FakeResponse(401, ["unexpected"])

    client = SplunkClient(settings_from(CREDS, FIELDS), session=Answers())  # type: ignore[arg-type]

    with pytest.raises(SplunkError) as caught:
        client.create_job("search x", earliest=None, latest="now")
    assert caught.value.status_code == 401


# --- configuration -----------------------------------------------------------------


@pytest.mark.parametrize(
    "fields,creds,message",
    [
        ({}, CREDS, "base_url"),
        (FIELDS, {}, "auth_token"),
        ({"base_url": "http://splunk:8089"}, CREDS, "must be https"),
        ({**FIELDS, "tls_verification": "maybe"}, CREDS, "tls_verification"),
        ({"base_url": "https://admin:pw@splunk:8089"}, CREDS, "just https://host:port"),
        (
            {"base_url": "https://splunk:8089/en-US/app"},
            CREDS,
            "just https://host:port",
        ),
        ({"base_url": "https://splunk:8089?x=1"}, CREDS, "just https://host:port"),
    ],
)
def test_bad_configuration_is_refused_before_anything_is_sent(
    fields: dict[str, str],
    creds: dict[str, str],
    message: str,
) -> None:
    with pytest.raises(DiscoveryConfigurationError, match=message) as caught:
        settings_from(creds, fields)
    assert failure_code(caught.value) is DiscoveryErrorCode.NOT_CONFIGURED
    assert "pw" not in str(caught.value)


def test_settings_read_trust_from_the_source_fields() -> None:
    settings = settings_from(
        CREDS,
        {**FIELDS, "tls_verification": "ca_only", "ca_certificate": " PEM "},
    )

    assert settings.tls_verification is TLSVerification.CA_ONLY
    assert settings.ca_certificate == "PEM"
    assert settings_from(CREDS, FIELDS).tls_verification is TLSVerification.FULL


@pytest.mark.parametrize(
    "query,expected",
    [
        ("index=main | stats count", "search index=main | stats count"),
        ("search index=main", "search index=main"),
        ("SEARCH index=main", "SEARCH index=main"),
        ("| tstats count from datamodel=Web", "| tstats count from datamodel=Web"),
    ],
)
def test_a_query_from_the_search_bar_gets_the_search_the_api_requires(
    query: str,
    expected: str,
) -> None:
    assert search_text(query) == expected


def test_a_config_without_a_query_is_refused() -> None:
    with pytest.raises(DiscoveryConfigurationError, match="no query"):
        search_text("  ")


@pytest.mark.parametrize(
    "mode,check_hostname,verify_mode",
    [
        (TLSVerification.FULL, True, ssl.CERT_REQUIRED),
        (TLSVerification.CA_ONLY, False, ssl.CERT_REQUIRED),
        (TLSVerification.OFF, False, ssl.CERT_NONE),
    ],
)
def test_each_tls_mode_checks_what_it_says(
    mode: TLSVerification,
    check_hostname: bool,
    verify_mode: ssl.VerifyMode,
) -> None:
    session = tls_session(None, mode, "Splunk")
    adapter = session.get_adapter("https://h")
    context = adapter._ssl_context  # type: ignore[attr-defined]

    assert context.check_hostname is check_hostname
    assert context.verify_mode == verify_mode


@pytest.mark.parametrize("mode", [TLSVerification.FULL, TLSVerification.CA_ONLY])
def test_the_tls_settings_reach_a_connection_made_through_a_proxy(
    mode: TLSVerification,
) -> None:
    """Behind an HTTPS_PROXY, requests builds a separate pool that never sees
    `init_poolmanager`, so the CA and the hostname choice must be carried there too."""
    adapter = tls_session(None, mode, "Splunk").get_adapter("https://h")
    proxied = adapter.proxy_manager_for("http://proxy.example:3128")

    assert proxied.connection_pool_kw["ssl_context"] is adapter._ssl_context  # type: ignore[attr-defined]
    assert ("assert_hostname" in proxied.connection_pool_kw) is (
        mode is TLSVerification.CA_ONLY
    )


def test_a_ca_certificate_that_lost_its_line_breaks_still_loads() -> None:
    """A single-line form field strips every newline from a pasted certificate. Seen
    live: Splunk's cacert.pem saved as 1,388 characters with 0 newlines."""
    pem = _a_ca_pem()
    flattened = pem.replace("\n", "")

    assert normalize_pem(flattened) == normalize_pem(pem)
    tls_session(flattened, TLSVerification.CA_ONLY, "Splunk")  # does not raise


def test_a_ca_certificate_error_is_not_chained_to_the_ssl_error() -> None:
    """ssl.SSLError is an OSError; chained, a classifier reads it as the network."""
    with pytest.raises(DiscoveryConfigurationError) as caught:
        tls_session(
            "-----BEGIN CERTIFICATE-----nope-----END CERTIFICATE-----",
            TLSVerification.FULL,
            "Splunk",
        )

    assert caught.value.__cause__ is None
    assert caught.value.__suppress_context__ is True


def _a_ca_pem() -> str:
    """A throwaway self-signed CA certificate, made for the test."""
    key = ec.generate_private_key(ec.SECP256R1())
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "test ca")])
    now = dt.datetime.now(dt.timezone.utc)
    cert = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(key.public_key())
        .serial_number(1)
        .not_valid_before(now)
        .not_valid_after(now + dt.timedelta(days=1))
        .add_extension(x509.BasicConstraints(ca=True, path_length=None), critical=True)
        .sign(key, hashes.SHA256())
    )
    return cert.public_bytes(serialization.Encoding.PEM).decode()


def test_a_ca_certificate_that_is_not_pem_is_a_configuration_error() -> None:
    with pytest.raises(DiscoveryConfigurationError, match="ca_certificate") as caught:
        tls_session("nope", TLSVerification.FULL, "Splunk")
    assert failure_code(caught.value) is DiscoveryErrorCode.NOT_CONFIGURED


def test_a_ca_certificate_is_not_loaded_when_verification_is_off() -> None:
    """An admin whose CA will not load can still choose to scan without verifying."""
    tls_session("nope", TLSVerification.OFF, "Splunk")  # does not raise


class Flaky:
    """Fails the first calls of each kind, then answers the way `answer` says."""

    def __init__(self, failures: list[Any], answer: FakeResponse) -> None:
        self.failures, self.answer, self.methods = list(failures), answer, []

    def request(self, method: str, *a: Any, **kw: Any) -> FakeResponse:
        self.methods.append(method)
        if self.failures:
            failure = self.failures.pop(0)
            if isinstance(failure, Exception):
                raise failure
            return failure
        return self.answer


def _status_body() -> dict[str, Any]:
    return {"entry": [{"content": {"dispatchState": "DONE", "isDone": True}}]}


def test_a_status_poll_survives_a_passing_failure() -> None:
    """One 503 or dropped keep-alive must not fail a long search's poll."""
    flaky = Flaky(
        [requests.ConnectionError("reset"), FakeResponse(503, {})],
        FakeResponse(200, _status_body()),
    )
    client = SplunkClient(settings_from(CREDS, FIELDS), session=flaky, sleep=lambda s: None)  # type: ignore[arg-type]

    assert client.job_status("sid-1").is_done
    assert flaky.methods == ["GET", "GET", "GET"]


def test_creating_a_search_is_not_retried() -> None:
    """A retried POST that reached Splunk would start a second search."""
    flaky = Flaky([FakeResponse(503, {})], FakeResponse(201, {"sid": "sid-1"}))
    client = SplunkClient(settings_from(CREDS, FIELDS), session=flaky, sleep=lambda s: None)  # type: ignore[arg-type]

    with pytest.raises(SplunkError) as caught:
        client.create_job("search x", earliest=None, latest="now")
    assert caught.value.status_code == 503
    assert flaky.methods == ["POST"]


def test_a_search_head_without_the_v2_api_names_the_version() -> None:
    client = SplunkClient(
        settings_from(CREDS, FIELDS),
        session=Flaky([], FakeResponse(404, {})),  # type: ignore[arg-type]
    )

    with pytest.raises(SplunkError, match="9.0.1"):
        client.create_job("search x", earliest=None, latest="now")


def test_splunk_is_registered_for_its_vendor() -> None:
    import discovery  # noqa: F401 -- registration is the import's effect
    from job_executors.discovery_scan import SOURCE_CONNECTORS

    assert SOURCE_CONNECTORS[VENDOR] is SplunkConnector
