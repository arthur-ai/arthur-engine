"""Elastic Security connector: the _query call, the contract check and the records.

A fake session stands in for Elasticsearch. Its responses are shaped on what a real
Elasticsearch 9.5.4 returned for the same requests: typed `columns` beside row-major
`values`, the `Warning` header ES|QL sends when a query has no LIMIT, and the error
bodies of a rejected key, an unreadable index and a query matching no index.
"""

import base64
import logging
from typing import Any, Optional

import pytest
import requests
from arthur_client.api_bindings import DiscoverySourceConfigSpec
from arthur_common.models.agent_governance_schemas import SIEMAgentCreationSource

import discovery  # noqa: F401  (registers the connectors)
from discovery.siem.elastic_security.client import (
    ElasticClient,
    ElasticError,
    ElasticSettings,
    warnings_from,
)
from discovery.siem.elastic_security.connector import (
    BATCH_SIZE,
    VENDOR,
    ElasticSecurityConnector,
    esql_text,
    settings_from,
)
from discovery.siem.tls import TLSVerification, parse_tls_verification, tls_session
from job_executors.discovery_output_contract import OutputContractError, check_batch
from job_executors.discovery_scan import SOURCE_CONNECTORS

LOG = logging.getLogger("test.elastic")
API_KEY = "QnIzRzlLQUJyTkRXZy12T2lwTVk6c2VjcmV0LXZhbHVl"
CREDS = {"api_key": API_KEY}
FIELDS = {"elasticsearch_url": "https://es.example.com:9243"}
QUERY = (
    'FROM logs-* | WHERE destination.domain IN ("api.openai.com", "api.anthropic.com") '
    "| STATS last_seen = MAX(@timestamp) BY external_id = host.name "
    "| EVAL name = external_id | LIMIT 10000"
)
# ES|QL puts STATS aggregates before the BY columns, so last_seen comes first.
COLUMNS = [
    {"name": "last_seen", "type": "date"},
    {"name": "external_id", "type": "keyword"},
    {"name": "name", "type": "keyword"},
]
NO_LIMIT_WARNING = (
    "299 Elasticsearch-9.5.4-9170df19cae1adb107b7b489b4d82dec66d7a337 "
    '"No limit defined, adding default limit of [1000]"'
)


def values(n: int) -> list[list[Any]]:
    return [
        [f"2026-09-30T23:{i % 60:02d}:00.000Z", f"ws-{i:04d}", f"ws-{i:04d}"]
        for i in range(n)
    ]


class FakeResponse:
    def __init__(
        self,
        status: int,
        body: Any = None,
        headers: Optional[dict[str, str]] = None,
    ) -> None:
        self.status_code = status
        self._body = body
        self.headers = headers or {}

    def json(self) -> Any:
        if self._body is None:
            raise ValueError("no body")
        return self._body


def ok(
    rows: Optional[list[list[Any]]] = None,
    columns: Optional[list[dict[str, str]]] = None,
    warning: Optional[str] = None,
    is_partial: bool = False,
) -> FakeResponse:
    return FakeResponse(
        200,
        {
            "took": 3,
            "is_partial": is_partial,
            "columns": COLUMNS if columns is None else columns,
            "values": values(3) if rows is None else rows,
        },
        {"Warning": warning} if warning else None,
    )


def error(status: int, kind: str, reason: str) -> FakeResponse:
    return FakeResponse(
        status,
        {"error": {"root_cause": [], "type": kind, "reason": reason}, "status": status},
    )


class FakeSession:
    def __init__(self, response: Any = None) -> None:
        self.response = response if response is not None else ok()
        self.calls: list[dict[str, Any]] = []

    def post(self, url: str, **kw: Any) -> FakeResponse:
        self.calls.append({"url": url, **kw})
        if isinstance(self.response, BaseException):
            raise self.response
        return self.response  # type: ignore[no-any-return]


def connector_with(session: FakeSession) -> ElasticSecurityConnector:
    return ElasticSecurityConnector(
        client_factory=lambda s, log: ElasticClient(s, logger=log, session=session)  # type: ignore[arg-type]
    )


def config(query: Optional[str] = QUERY) -> DiscoverySourceConfigSpec:
    return DiscoverySourceConfigSpec.model_construct(name="proxy logs", query=query)


def scan(
    session: FakeSession,
    *,
    lookback_hours: int = 24,
    query: Optional[str] = QUERY,
    fields: Optional[dict[str, str]] = None,
    logger: logging.Logger = LOG,
) -> list[Any]:
    batches = connector_with(session).scan(
        config(query),
        lookback_hours,
        CREDS,
        FIELDS if fields is None else fields,
        logger,
    )
    return [record for batch in batches for record in batch]


# -- registration --------------------------------------------------------------------


def test_importing_the_package_registers_the_connector() -> None:
    assert SOURCE_CONNECTORS[VENDOR] is ElasticSecurityConnector
    assert VENDOR == "elastic_security"


# -- the request ---------------------------------------------------------------------


def test_the_query_is_sent_untouched_and_the_lookback_rides_in_the_filter() -> None:
    session = FakeSession()
    scan(session, lookback_hours=48)
    (call,) = session.calls
    assert call["url"] == "https://es.example.com:9243/_query"
    assert call["json"]["query"] == QUERY
    assert call["json"]["filter"] == {
        "range": {"@timestamp": {"gte": "now-48h"}},
    }


def test_no_lookback_sends_no_filter() -> None:
    session = FakeSession()
    scan(session, lookback_hours=0)
    assert "filter" not in session.calls[0]["json"]


def test_the_key_is_sent_as_an_api_key_header_and_redirects_are_refused() -> None:
    session = FakeSession()
    scan(session)
    call = session.calls[0]
    assert call["headers"]["Authorization"] == f"ApiKey {API_KEY}"
    assert call["allow_redirects"] is False
    assert call["timeout"] < 120


def test_a_url_with_a_path_keeps_it() -> None:
    session = FakeSession()
    scan(session, fields={"elasticsearch_url": "https://proxy.example.com/es/"})
    assert session.calls[0]["url"] == "https://proxy.example.com/es/_query"


# -- records -------------------------------------------------------------------------


def test_rows_become_records_by_column_name_not_position() -> None:
    records = scan(FakeSession())
    assert [r.external_id for r in records] == ["ws-0000", "ws-0001", "ws-0002"]
    assert records[0].name == "ws-0000"
    assert records[0].last_seen.isoformat() == "2026-09-30T23:00:00+00:00"


def test_a_record_carries_the_cluster_and_the_query_in_its_provenance() -> None:
    record, *_ = scan(FakeSession())
    source = record.creation_source
    assert isinstance(source, SIEMAgentCreationSource)
    assert source.vendor == VENDOR
    assert source.address.instance == "es.example.com:9243"
    assert source.address.query == QUERY
    assert source.address.resource_id == record.external_id


def test_the_instance_never_carries_credentials_written_into_the_url() -> None:
    record, *_ = scan(
        FakeSession(),
        fields={"elasticsearch_url": "https://elastic:hunter2@es.example.com"},
    )
    assert record.creation_source.address.instance == "es.example.com"


def test_output_satisfies_the_discovery_output_contract() -> None:
    # Raises OutputContractError on a batch the contract refuses.
    check_batch(scan(FakeSession()), "Source config 'proxy logs' (elastic_security)")


def test_an_unmapped_column_fails_the_scan_instead_of_being_dropped() -> None:
    session = FakeSession(
        ok(
            columns=COLUMNS + [{"name": "hits", "type": "long"}],
            rows=[row + [40] for row in values(2)],
        )
    )
    with pytest.raises(OutputContractError) as exc:
        scan(session)
    assert "hits" in str(exc.value)


def test_a_missing_contract_column_fails_the_scan() -> None:
    session = FakeSession(ok(columns=COLUMNS[:2], rows=[r[:2] for r in values(2)]))
    with pytest.raises(OutputContractError) as exc:
        scan(session)
    assert "name" in str(exc.value)


def test_records_are_batched() -> None:
    session = FakeSession(ok(rows=values(BATCH_SIZE + 1)))
    batches = list(connector_with(session).scan(config(), 24, CREDS, FIELDS, LOG))
    assert [len(b) for b in batches] == [BATCH_SIZE, 1]


# -- how complete the answer is ------------------------------------------------------


def test_no_limit_and_a_full_default_page_is_reported_as_capped(
    caplog: pytest.LogCaptureFixture,
) -> None:
    session = FakeSession(ok(rows=values(1000), warning=NO_LIMIT_WARNING))
    with caplog.at_level(logging.WARNING, logger=LOG.name):
        scan(session)
    assert "no LIMIT and returned 1000 rows" in caplog.text


def test_the_no_limit_warning_alone_is_not_a_cap(
    caplog: pytest.LogCaptureFixture,
) -> None:
    # Elasticsearch sends it on every query without a LIMIT, complete or not.
    session = FakeSession(ok(rows=values(2), warning=NO_LIMIT_WARNING))
    with caplog.at_level(logging.WARNING, logger=LOG.name):
        assert len(scan(session)) == 2
    assert "LIMIT" not in caplog.text


def test_the_maximum_row_count_is_reported_as_capped(
    caplog: pytest.LogCaptureFixture,
) -> None:
    session = FakeSession(ok(rows=values(10_000)))
    with caplog.at_level(logging.WARNING, logger=LOG.name):
        scan(session)
    assert "Elasticsearch's maximum for one query" in caplog.text


def test_a_partial_result_is_reported(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.WARNING, logger=LOG.name):
        scan(FakeSession(ok(is_partial=True)))
    assert "partial" in caplog.text


def test_other_elasticsearch_warnings_reach_the_job_log(
    caplog: pytest.LogCaptureFixture,
) -> None:
    warning = (
        '299 Elasticsearch-9.5.4 "Line 1:52: evaluation of [MAX(x)] failed, '
        'treating result as null. Only first 20 failures recorded."'
    )
    with caplog.at_level(logging.WARNING, logger=LOG.name):
        scan(FakeSession(ok(warning=warning)))
    assert "evaluation of [MAX(x)] failed" in caplog.text


def test_a_query_matching_no_index_reports_it_rather_than_failing_the_contract(
    caplog: pytest.LogCaptureFixture,
) -> None:
    session = FakeSession(
        ok(columns=[{"name": "<no-fields>", "type": "null"}], rows=[])
    )
    with caplog.at_level(logging.WARNING, logger=LOG.name):
        assert scan(session) == []
    assert "matched no index" in caplog.text


def test_zero_rows_names_the_likely_causes(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.WARNING, logger=LOG.name):
        assert scan(FakeSession(ok(rows=[]))) == []
    assert "'read' on those indices" in caplog.text


def test_warnings_are_read_from_a_joined_header() -> None:
    joined = f'{NO_LIMIT_WARNING}, 299 Elasticsearch-9.5.4 "a, b"'
    assert warnings_from(joined) == [
        "No limit defined, adding default limit of [1000]",
        "a, b",
    ]


# -- stopping ------------------------------------------------------------------------


def test_a_stop_before_the_query_sends_nothing() -> None:
    session = FakeSession()
    connector = connector_with(session)
    connector.stop_when(lambda: True)
    assert list(connector.scan(config(), 24, CREDS, FIELDS, LOG)) == []
    assert session.calls == []


# -- the query -----------------------------------------------------------------------


def test_query_dsl_is_refused_before_anything_is_sent() -> None:
    session = FakeSession()
    with pytest.raises(ValueError, match="Query DSL"):
        scan(session, query='{"query": {"match_all": {}}}')
    assert session.calls == []


@pytest.mark.parametrize("query", [None, "", "   "])
def test_a_missing_query_is_named(query: Optional[str]) -> None:
    with pytest.raises(ValueError, match="no query"):
        esql_text(query)


def test_esql_is_passed_through_stripped() -> None:
    assert esql_text(f"  {QUERY}\n") == QUERY


# -- settings ------------------------------------------------------------------------


def test_missing_fields_are_named() -> None:
    with pytest.raises(ValueError) as exc:
        settings_from({}, {})
    assert "elasticsearch_url" in str(exc.value) and "api_key" in str(exc.value)


def test_http_is_refused_before_the_key_is_sent() -> None:
    session = FakeSession()
    with pytest.raises(ValueError, match="must be https"):
        scan(session, fields={"elasticsearch_url": "http://es.example.com:9200"})
    assert session.calls == []


def test_a_key_pasted_as_id_and_secret_is_encoded() -> None:
    settings = settings_from({"api_key": "Br3G9KAB:secret-value"}, FIELDS)
    assert settings.api_key == base64.b64encode(b"Br3G9KAB:secret-value").decode()


def test_an_encoded_key_is_used_as_it_is() -> None:
    assert settings_from(CREDS, FIELDS).api_key == API_KEY


def test_tls_fields_reach_the_settings() -> None:
    settings = settings_from(
        CREDS,
        {**FIELDS, "tls_verification": "CA_ONLY", "ca_certificate": " pem "},
    )
    assert settings.tls_verification is TLSVerification.CA_ONLY
    assert settings.ca_certificate == "pem"


def test_an_unknown_tls_mode_is_named() -> None:
    with pytest.raises(ValueError, match="full, ca_only, off"):
        parse_tls_verification("strict", "Elastic")


def test_a_ca_certificate_that_is_not_pem_is_named() -> None:
    with pytest.raises(ValueError, match="not a PEM certificate"):
        tls_session("not a certificate", TLSVerification.FULL, "Elastic")


def test_tls_off_turns_verification_off() -> None:
    assert tls_session(None, TLSVerification.OFF, "Elastic").verify is False
    assert tls_session(None, TLSVerification.CA_ONLY, "Elastic").verify is True


# -- failures ------------------------------------------------------------------------


def test_a_rejected_key_carries_its_status_and_a_hint() -> None:
    session = FakeSession(
        error(
            401,
            "security_exception",
            "unable to authenticate with provided credentials",
        )
    )
    with pytest.raises(ElasticError) as exc:
        scan(session)
    assert exc.value.status_code == 401
    assert "organization key" in str(exc.value)


def test_an_unknown_index_names_both_causes() -> None:
    session = FakeSession(
        error(400, "verification_exception", "Unknown index [secret-hr]")
    )
    with pytest.raises(ElasticError) as exc:
        scan(session)
    assert exc.value.status_code == 400
    assert "Unknown index [secret-hr]" in str(exc.value)
    assert "lacks 'read'" in str(exc.value)


def test_a_tls_failure_points_at_the_tls_fields() -> None:
    session = FakeSession(requests.exceptions.SSLError("certificate verify failed"))
    with pytest.raises(ElasticError, match="ca_certificate"):
        scan(session)


def test_an_unreachable_cluster_stays_a_connection_error() -> None:
    session = FakeSession(requests.ConnectionError("Name or service not known"))
    with pytest.raises(requests.ConnectionError, match="unreachable"):
        scan(session)


def test_the_scan_never_logs_the_api_key(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.DEBUG):
        scan(FakeSession(ok(rows=values(1000), warning=NO_LIMIT_WARNING)))
        with pytest.raises(ElasticError):
            scan(FakeSession(error(401, "security_exception", "bad key")))
    assert API_KEY not in caplog.text


def test_the_settings_object_is_what_the_client_is_built_from() -> None:
    seen: list[ElasticSettings] = []

    def factory(settings: ElasticSettings, log: logging.Logger) -> ElasticClient:
        seen.append(settings)
        return ElasticClient(settings, logger=log, session=FakeSession())  # type: ignore[arg-type]

    list(
        ElasticSecurityConnector(client_factory=factory).scan(
            config(), 24, CREDS, FIELDS, LOG
        )
    )
    assert seen[0].elasticsearch_url == FIELDS["elasticsearch_url"]


# -- responses captured from Elasticsearch 9.5.4 --------------------------------------

# Bodies exactly as a local Elasticsearch 9.5.4 returned them to a read-only API key
# (`read` on `logs-*`), so a change in what the parsing above assumes shows up here
# rather than against a customer's cluster. Captured from the reference query (with
# the host filter that keeps the answer short), a FROM matching no index, an index
# outside the key, and an unknown key.
CAPTURED_OK = {
    "took": 773,
    "is_partial": False,
    "completion_time_in_millis": 1790817188015,
    "documents_found": 95,
    "values_loaded": 190,
    "rows_emitted": 211,
    "bytes_read": 0,
    "read_nanos": 0,
    "cpu_nanos": 267979459,
    "start_time_in_millis": 1790817187242,
    "expiration_time_in_millis": 1791249187967,
    "columns": [
        {"name": "last_seen", "type": "date"},
        {"name": "external_id", "type": "keyword"},
        {"name": "name", "type": "keyword"},
    ],
    "values": [
        ["2026-09-30T23:49:39.000Z", "build-server-07", "build-server-07"],
        ["2026-09-30T23:35:53.000Z", "eng-laptop-042", "eng-laptop-042"],
        ["2026-09-30T23:26:47.000Z", "svc-ingest-02", "svc-ingest-02"],
    ],
}
CAPTURED_OK_WARNING = '299 Elasticsearch-9.5.4-9170df19cae1adb107b7b489b4d82dec66d7a337 "No limit defined, adding default limit of [1000]"'
CAPTURED_NO_FIELDS = {
    "took": 6,
    "is_partial": False,
    "completion_time_in_millis": 1790817188147,
    "documents_found": 0,
    "values_loaded": 0,
    "rows_emitted": 0,
    "bytes_read": 0,
    "read_nanos": 0,
    "cpu_nanos": 152583,
    "start_time_in_millis": 1790817188141,
    "expiration_time_in_millis": 1791249187967,
    "columns": [{"name": "<no-fields>", "type": "null"}],
    "values": [],
}
CAPTURED_UNKNOWN_INDEX = {
    "error": {
        "root_cause": [
            {"type": "verification_exception", "reason": "Unknown index [secret-hr]"}
        ],
        "type": "verification_exception",
        "reason": "Unknown index [secret-hr]",
    },
    "status": 400,
}
CAPTURED_BAD_KEY = {
    "error": {
        "root_cause": [
            {
                "type": "security_exception",
                "reason": "unable to authenticate with provided credentials and anonymous access is not allowed for this request",
                "additional_unsuccessful_credentials": "API key: unable to find apikey with id foo",
                "header": {
                    "WWW-Authenticate": [
                        'Basic realm="security", charset="UTF-8"',
                        'Bearer realm="security"',
                        "ApiKey",
                    ]
                },
            }
        ],
        "type": "security_exception",
        "reason": "unable to authenticate with provided credentials and anonymous access is not allowed for this request",
        "additional_unsuccessful_credentials": "API key: unable to find apikey with id foo",
        "header": {
            "WWW-Authenticate": [
                'Basic realm="security", charset="UTF-8"',
                'Bearer realm="security"',
                "ApiKey",
            ]
        },
    },
    "status": 401,
}


def test_responses_captured_from_elasticsearch_9_5_parse(
    caplog: pytest.LogCaptureFixture,
) -> None:
    session = FakeSession(
        FakeResponse(200, CAPTURED_OK, {"Warning": CAPTURED_OK_WARNING})
    )
    records = scan(session)
    assert [(r.external_id, r.name, r.last_seen.isoformat()) for r in records] == [
        ("build-server-07", "build-server-07", "2026-09-30T23:49:39+00:00"),
        ("eng-laptop-042", "eng-laptop-042", "2026-09-30T23:35:53+00:00"),
        ("svc-ingest-02", "svc-ingest-02", "2026-09-30T23:26:47+00:00"),
    ]
    # Three rows under the default cap: the no-LIMIT warning is not a truncation.
    with caplog.at_level(logging.WARNING, logger=LOG.name):
        scan(
            FakeSession(
                FakeResponse(200, CAPTURED_OK, {"Warning": CAPTURED_OK_WARNING})
            )
        )
    assert "LIMIT" not in caplog.text

    with caplog.at_level(logging.WARNING, logger=LOG.name):
        assert scan(FakeSession(FakeResponse(200, CAPTURED_NO_FIELDS))) == []
    assert "matched no index" in caplog.text

    with pytest.raises(ElasticError) as unknown:
        scan(FakeSession(FakeResponse(400, CAPTURED_UNKNOWN_INDEX)))
    assert unknown.value.status_code == 400
    assert "verification_exception: Unknown index [secret-hr]" in str(unknown.value)

    with pytest.raises(ElasticError) as bad_key:
        scan(FakeSession(FakeResponse(401, CAPTURED_BAD_KEY)))
    assert bad_key.value.status_code == 401
    assert "security_exception" in str(bad_key.value)


@pytest.mark.parametrize("body", [None, ["not", "an", "object"], {"error": "x"}])
def test_a_success_status_without_an_esql_result_is_the_vendors_error(
    body: Any,
) -> None:
    # A proxy's login page answers 200 too. A bare ValueError here would read as a
    # configuration mistake to Test Connection.
    session = FakeSession(FakeResponse(200, body, {"Content-Type": "text/html"}))
    with pytest.raises(ElasticError) as exc:
        scan(session)
    assert exc.value.status_code == 200
    assert "not an ES|QL result" in str(exc.value)


def test_an_error_body_that_is_not_an_object_still_reports_the_status() -> None:
    with pytest.raises(ElasticError) as exc:
        scan(FakeSession(FakeResponse(502, ["bad gateway"])))
    assert exc.value.status_code == 502
