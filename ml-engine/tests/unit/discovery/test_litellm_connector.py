"""LiteLLM proxy connector: the admin probe, the key list, the request log and the fold.

A fake HTTP session stands in for the proxy. Its bodies follow LiteLLM proxy 1.104.0
(`ghcr.io/berriai/litellm:v1.104.0`) as its source defines them, not a live capture:
`/key/list?return_full_object=true` returns `keys` / `total_count` / `current_page` /
`total_pages`, each key with its hashed `token`, `key_alias`, `team_id`, `team_alias`
and `agent_id`; `/spend/logs/v2` returns `data` / `total` / `page` / `page_size` /
`total_pages` / `total_is_capped`, each row with the columns of its list query
(`request_id`, `call_type`, `api_key`, `startTime` as naive UTC, `model`,
`custom_llm_provider`, `status`, `agent_id`, `mcp_namespaced_tool_name`, and
`metadata` with `user_api_key_alias`, `user_api_key_team_alias` and
`error_information`). Ids, aliases, addresses and key fragments are fakes of the same
shape.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Optional

import pytest
import requests
from arthur_client.api_bindings import DiscoverySourceConfigSpec
from arthur_common.models.agent_governance_schemas import (
    Detection,
    IdentityBasis,
    NetworkAgentCreationSource,
)

from discovery import source_connectors
from discovery.network.gateway_records import gateway_instance
from discovery.network.litellm.client import (
    KEY_PAGE_SIZE,
    SPEND_PAGE_SIZE,
    LiteLLMClient,
    LiteLLMError,
    LiteLLMSettings,
)
from discovery.network.litellm.connector import (
    BATCH_SIZE,
    VENDOR,
    LiteLLMConnector,
    settings_from,
)
from job_executors.discovery_output_contract import check_batch
from job_executors.discovery_scan import (
    AcceptsStopCheck,
    DiscoveryConfigurationError,
    DiscoveryErrorCode,
    failure_code,
)

LOG = logging.getLogger("test.litellm")
API_KEY = "sk-viewer-9f3b2c71d4e8a6b0"
MASKED = "sk-v****a6b0"
CREDS = {"api_key": API_KEY}
FIELDS = {"base_url": "https://litellm.example.com:4400"}
INSTANCE = "litellm.example.com:4400"
NOW = datetime(2026, 10, 28, 12, 0, tzinfo=timezone.utc).timestamp()

TRIAGE_AGENT = "4d1f6a2e-9b7c-4e1a-8f3d-2c5b6a7e8f90"
CLAIMED_AGENT = "agent-claimed-demo"
BOUND_TOKEN = "a" * 64
CLAIMING_TOKEN = "b" * 64
CI_TOKEN = "c" * 64
SUPPORT_TOKEN = "d" * 64
INVOICE_TOKEN = "e" * 64
WRONG_KEY_TOKEN = "f" * 64


def key(
    token: str, alias: Optional[str], agent_id: Optional[str] = None
) -> dict[str, Any]:
    return {
        "token": token,
        "key_name": f"sk-...{token[-4:]}",
        "key_alias": alias,
        "team_id": "team-11",
        "team_alias": "platform",
        "agent_id": agent_id,
        "models": [],
        "blocked": None,
    }


KEYS = [
    key(BOUND_TOKEN, "triage-agent", TRIAGE_AGENT),
    key(CLAIMING_TOKEN, "sandbox"),
    key(CI_TOKEN, "shared-ci"),
    key(SUPPORT_TOKEN, "support-bot"),
    key(INVOICE_TOKEN, "invoice-agent"),
]


def row(
    request_id: str,
    token: str,
    at: str,
    *,
    alias: Optional[str] = None,
    agent_id: Optional[str] = None,
    status: str = "success",
    error_code: Optional[str] = None,
    model: str = "gpt-4o-mini",
    provider: str = "openai",
    call_type: str = "acompletion",
    tool: Optional[str] = None,
) -> dict[str, Any]:
    metadata: dict[str, Any] = {
        "status": status,
        "user_api_key_alias": alias,
        "user_api_key_team_alias": "platform",
        "requester_ip_address": "10.0.0.7",
    }
    if error_code is not None:
        metadata["error_information"] = {
            "error_code": error_code,
            "error_class": "ProxyException",
            "error_message": f"Authentication Error, Invalid proxy server token passed. Received={MASKED}",
        }
    return {
        "request_id": request_id,
        "call_type": call_type,
        "api_key": token,
        "spend": 0.0,
        "total_tokens": 21,
        "startTime": at,
        "endTime": at,
        "model": model,
        "model_group": model,
        "custom_llm_provider": provider,
        "user": "",
        "team_id": "team-11",
        "end_user": "",
        "requester_ip_address": "10.0.0.7",
        "status": status,
        "agent_id": agent_id,
        "mcp_namespaced_tool_name": tool,
        "metadata": metadata,
    }


# The traffic of the end-to-end handoff: one key bound to a registered agent, one
# unbound key claiming an agent id, three plain keys (one used from two clients), one of
# them borrowing the registered agent's id, refused requests, and a wrong key.
HANDOFF_ROWS = [
    row(
        "r1",
        BOUND_TOKEN,
        "2026-10-28T10:00:00",
        alias="triage-agent",
        agent_id=TRIAGE_AGENT,
    ),
    row(
        "r2",
        BOUND_TOKEN,
        "2026-10-28T10:05:00",
        alias="triage-agent",
        status="failure",
        error_code="403",
        model="claude-opus",
    ),
    row(
        "r3",
        CLAIMING_TOKEN,
        "2026-10-28T10:01:00",
        alias="sandbox",
        agent_id=CLAIMED_AGENT,
    ),
    row("r4", CI_TOKEN, "2026-10-28T10:02:00", alias="shared-ci"),
    row(
        "r5",
        CI_TOKEN,
        "2026-10-28T10:03:00",
        alias="shared-ci",
        model="claude-haiku",
        provider="anthropic",
    ),
    row("r6", SUPPORT_TOKEN, "2026-10-28T10:04:00", alias="support-bot"),
    row(
        "r7",
        SUPPORT_TOKEN,
        "2026-10-28T10:06:00",
        alias="support-bot",
        agent_id=TRIAGE_AGENT,
    ),
    row("r8", INVOICE_TOKEN, "2026-10-28T10:07:00", alias="invoice-agent"),
    row(
        "r9",
        INVOICE_TOKEN,
        "2026-10-28T10:09:00",
        alias="invoice-agent",
        status="failure",
        error_code="403",
        model="gpt-4o",
    ),
    row(
        "r10",
        WRONG_KEY_TOKEN,
        "2026-10-28T10:08:00",
        status="failure",
        error_code="401",
        model="",
    ),
]


class FakeResponse:
    def __init__(
        self, status: int, body: Any, headers: Optional[dict[str, str]] = None
    ) -> None:
        self.status_code = status
        self._body = body
        self.headers = headers or {"Content-Type": "application/json"}

    def json(self) -> Any:
        if isinstance(self._body, str):
            raise ValueError("not json")
        return self._body


def spend_page(
    data: list[dict[str, Any]], total_pages: int = 1, capped: bool = False
) -> FakeResponse:
    return FakeResponse(
        200,
        {
            "data": data,
            "total": len(data),
            "page": 1,
            "page_size": SPEND_PAGE_SIZE,
            "total_pages": total_pages,
            "total_is_capped": capped,
        },
    )


def keys_page(keys: list[dict[str, Any]], total_pages: int = 1) -> FakeResponse:
    return FakeResponse(
        200,
        {
            "keys": keys,
            "total_count": len(keys),
            "current_page": 1,
            "total_pages": total_pages,
        },
    )


class FakeSession:
    """Answers each route from its own queue; the last answer repeats."""

    def __init__(
        self,
        spend: Optional[list[Any]] = None,
        keys: Optional[list[Any]] = None,
        probe: Optional[list[Any]] = None,
    ) -> None:
        self.routes: dict[str, list[Any]] = {
            "/user/list": probe or [FakeResponse(200, {"users": [], "total": 1})],
            "/key/list": keys or [keys_page(KEYS)],
            "/spend/logs/v2": spend or [spend_page([])],
        }
        self.calls: list[dict[str, Any]] = []

    def get(self, url: str, **kwargs: Any) -> Any:
        path = url.split(INSTANCE, 1)[1]
        self.calls.append({"path": path, **kwargs})
        queue = self.routes[path]
        answer = queue.pop(0) if len(queue) > 1 else queue[0]
        if isinstance(answer, Exception):
            raise answer
        return answer

    def paths(self) -> list[str]:
        return [c["path"] for c in self.calls]


def connector(session: FakeSession, **kwargs: Any) -> LiteLLMConnector:
    return LiteLLMConnector(
        client_factory=lambda s, log: LiteLLMClient(s, logger=log, session=session, sleep=lambda _: None),  # type: ignore[arg-type]
        now=lambda: NOW,
        **kwargs,
    )


def config(query: str = "") -> DiscoverySourceConfigSpec:
    return DiscoverySourceConfigSpec.model_construct(name="LiteLLM prod", query=query)


def scan(
    session: FakeSession,
    lookback_hours: int = 24,
    fields: Optional[dict[str, str]] = None,
    creds: Optional[dict[str, Optional[str]]] = None,
    conn: Optional[LiteLLMConnector] = None,
    query: str = "",
) -> list[Any]:
    batches = (conn or connector(session)).scan(
        config(query),
        lookback_hours,
        CREDS if creds is None else creds,
        FIELDS if fields is None else fields,
        LOG,
    )
    return [record for batch in batches for record in batch]


def by_name(records: list[Any]) -> dict[str, Any]:
    return {r.name: r for r in records}


# -- registration ----------------------------------------------------------------------


def test_the_connector_is_registered_for_its_vendor() -> None:
    assert source_connectors()[VENDOR] is LiteLLMConnector
    assert VENDOR == "litellm"


def test_the_connector_declares_exactly_its_secrets() -> None:
    assert LiteLLMConnector.SENSITIVE_FIELDS == frozenset({"api_key"})


def test_the_settings_never_print_the_key() -> None:
    assert API_KEY not in repr(settings_from(CREDS, FIELDS))


# -- request shape ---------------------------------------------------------------------


def test_the_admin_probe_comes_first_then_the_keys_then_the_log() -> None:
    session = FakeSession()
    scan(session)
    assert session.paths() == ["/user/list", "/key/list", "/spend/logs/v2"]
    assert session.calls[0]["params"] == {"page": 1, "page_size": 1}


def test_every_call_sends_the_key_as_a_bearer_with_no_redirects_and_bounded_timeouts() -> (
    None
):
    session = FakeSession()
    scan(session)
    for call in session.calls:
        assert call["headers"]["Authorization"] == f"Bearer {API_KEY}"
        assert call["allow_redirects"] is False
        assert sum(call["timeout"]) < 120


def test_the_request_log_is_read_for_the_lookback_in_utc_oldest_first() -> None:
    session = FakeSession()
    scan(session, lookback_hours=48)
    params = session.calls[-1]["params"]
    assert params["start_date"] == "2026-10-26 12:00:00"
    assert params["end_date"] == "2026-10-28 12:00:00"
    assert params["page_size"] == SPEND_PAGE_SIZE == 1000
    assert (params["sort_by"], params["sort_order"]) == ("startTime", "asc")
    assert params["exclude_internal_health_checks"] == "true"


def test_a_lookback_of_zero_reads_everything_retained() -> None:
    session = FakeSession()
    scan(session, lookback_hours=0)
    assert session.calls[-1]["params"]["start_date"] == "1970-01-01 00:00:00"


def test_the_key_list_asks_for_full_objects() -> None:
    session = FakeSession()
    scan(session)
    params = session.calls[1]["params"]
    assert params["return_full_object"] == "true"
    assert params["size"] == KEY_PAGE_SIZE == 100


def test_a_config_query_is_ignored_and_says_so(
    caplog: pytest.LogCaptureFixture,
) -> None:
    with caplog.at_level(logging.WARNING, logger=LOG.name):
        scan(FakeSession(), query="select 1")
    assert "query is ignored" in caplog.text


# -- paging and the cap ----------------------------------------------------------------


def full_page(prefix: str) -> list[dict[str, Any]]:
    return [
        row(f"{prefix}{i}", CI_TOKEN, "2026-10-28T10:00:00")
        for i in range(SPEND_PAGE_SIZE)
    ]


def test_pages_are_followed_to_total_pages() -> None:
    session = FakeSession(
        spend=[
            spend_page(full_page("a"), total_pages=2),
            spend_page(full_page("b"), total_pages=2),
        ]
    )
    scan(session)
    assert [
        c["params"]["page"] for c in session.calls if c["path"] == "/spend/logs/v2"
    ] == [1, 2]


def test_a_capped_total_keeps_paging_until_a_short_page() -> None:
    session = FakeSession(
        spend=[
            spend_page(full_page("a"), total_pages=10, capped=True),
            spend_page(full_page("b"), total_pages=10, capped=True),
            spend_page(
                [row("c1", CI_TOKEN, "2026-10-28T11:00:00")],
                total_pages=10,
                capped=True,
            ),
        ],
    )
    [record] = scan(session)
    assert [
        c["params"]["page"] for c in session.calls if c["path"] == "/spend/logs/v2"
    ] == [1, 2, 3]
    assert record.last_seen == datetime(2026, 10, 28, 11, 0, tzinfo=timezone.utc)


def test_key_pages_are_followed_to_total_pages() -> None:
    first = [key(f"{i:064x}", f"k{i}") for i in range(KEY_PAGE_SIZE)]
    session = FakeSession(
        keys=[keys_page(first, total_pages=2), keys_page(KEYS, total_pages=2)]
    )
    scan(session)
    assert [c["params"]["page"] for c in session.calls if c["path"] == "/key/list"] == [
        1,
        2,
    ]


def test_a_capped_scan_is_reported_before_the_first_batch(
    caplog: pytest.LogCaptureFixture,
) -> None:
    session = FakeSession(spend=[spend_page(full_page("a"), total_pages=3)])
    with caplog.at_level(logging.INFO, logger=LOG.name):
        batches = connector(session, max_rows=10).scan(config(), 24, CREDS, FIELDS, LOG)
        next(batches)
        assert "10-row cap" in caplog.text
    assert [
        c["params"]["page"] for c in session.calls if c["path"] == "/spend/logs/v2"
    ] == [1]


def test_a_row_repeated_across_pages_is_counted_once(
    caplog: pytest.LogCaptureFixture,
) -> None:
    page = full_page("a")
    session = FakeSession(
        spend=[spend_page(page, total_pages=2), spend_page([page[-1]], total_pages=2)]
    )
    with caplog.at_level(logging.INFO, logger=LOG.name):
        scan(session)
    assert "1 row(s) skipped: repeated across pages" in caplog.text


def test_records_are_batched() -> None:
    rows = [
        row(f"r{i}", f"{i:064x}", "2026-10-28T10:00:00") for i in range(BATCH_SIZE + 1)
    ]
    session = FakeSession(spend=[spend_page(rows)], keys=[keys_page([])])
    batches = list(connector(session).scan(config(), 24, CREDS, FIELDS, LOG))
    assert [len(b) for b in batches] == [BATCH_SIZE, 1]


# -- identity and the fold -------------------------------------------------------------


def test_the_handoff_traffic_is_exactly_five_callers() -> None:
    """A registered agent, a claimed id, three keys; the borrowed id and the refused
    requests fold into their keys, and the wrong key is no caller at all."""
    records = scan(FakeSession(spend=[spend_page(HANDOFF_ROWS)]))
    got = {
        (
            r.name,
            r.creation_source.identity_basis,
            r.creation_source.address.resource_kind,
        )
        for r in records
    }
    assert got == {
        ("triage-agent", IdentityBasis.REGISTERED_AGENT, "agent_id"),
        (CLAIMED_AGENT, IdentityBasis.CLAIMED_AGENT, "agent_id"),
        ("shared-ci", IdentityBasis.CREDENTIAL, "virtual_key"),
        ("support-bot", IdentityBasis.CREDENTIAL, "virtual_key"),
        ("invoice-agent", IdentityBasis.CREDENTIAL, "virtual_key"),
    }


def test_a_bound_key_is_its_registered_agent_even_with_no_agent_id_on_the_row() -> None:
    records = by_name(
        scan(
            FakeSession(
                spend=[spend_page([row("r1", BOUND_TOKEN, "2026-10-28T10:00:00")])]
            )
        )
    )
    agent = records["triage-agent"]
    assert agent.creation_source.address.resource_id == TRIAGE_AGENT
    assert agent.external_id == f"litellm:{INSTANCE}:agent_id:{TRIAGE_AGENT}"
    assert agent.creation_source.identity_basis is IdentityBasis.REGISTERED_AGENT


def test_an_unbound_key_sending_an_agent_id_is_a_claimed_agent() -> None:
    [claimed] = scan(FakeSession(spend=[spend_page([HANDOFF_ROWS[2]])]))
    assert claimed.name == CLAIMED_AGENT
    assert claimed.external_id == f"litellm:{INSTANCE}:agent_id:{CLAIMED_AGENT}"
    assert claimed.creation_source.identity_basis is IdentityBasis.CLAIMED_AGENT


def test_an_agent_id_bound_to_another_key_folds_into_the_senders_key(
    caplog: pytest.LogCaptureFixture,
) -> None:
    with caplog.at_level(logging.INFO, logger=LOG.name):
        records = by_name(scan(FakeSession(spend=[spend_page(HANDOFF_ROWS)])))
    support = records["support-bot"]
    assert support.creation_source.address.resource_id == SUPPORT_TOKEN
    assert support.last_seen == datetime(2026, 10, 28, 10, 6, tzinfo=timezone.utc)
    assert records["triage-agent"].last_seen == datetime(
        2026, 10, 28, 10, 5, tzinfo=timezone.utc
    )
    assert "1 request(s) sent an agent id bound to a different key" in caplog.text
    assert TRIAGE_AGENT not in caplog.text


def test_a_plain_key_is_one_record_by_its_hash_never_its_alias() -> None:
    ci = by_name(scan(FakeSession(spend=[spend_page(HANDOFF_ROWS)])))["shared-ci"]
    assert ci.external_id == f"litellm:{INSTANCE}:virtual_key:{CI_TOKEN}"
    assert ci.creation_source.address.resource_id == CI_TOKEN
    assert ci.last_seen == datetime(2026, 10, 28, 10, 3, tzinfo=timezone.utc)
    assert [m.name for m in ci.llm_models] == [
        "anthropic/claude-haiku",
        "openai/gpt-4o-mini",
    ]


def test_a_request_rejected_for_an_invalid_key_is_skipped_and_counted(
    caplog: pytest.LogCaptureFixture,
) -> None:
    with caplog.at_level(logging.INFO, logger=LOG.name):
        records = scan(FakeSession(spend=[spend_page(HANDOFF_ROWS)]))
    assert all(WRONG_KEY_TOKEN not in r.external_id for r in records)
    assert "1 row(s) skipped: rejected for an invalid key" in caplog.text


def test_a_refused_request_moves_last_seen_but_adds_no_model() -> None:
    invoice = by_name(scan(FakeSession(spend=[spend_page(HANDOFF_ROWS)])))[
        "invoice-agent"
    ]
    assert invoice.last_seen == datetime(2026, 10, 28, 10, 9, tzinfo=timezone.utc)
    assert [m.name for m in invoice.llm_models] == ["openai/gpt-4o-mini"]


def test_a_refused_request_alone_is_no_record(caplog: pytest.LogCaptureFixture) -> None:
    refused = row(
        "r1", INVOICE_TOKEN, "2026-10-28T10:00:00", status="failure", error_code="403"
    )
    with caplog.at_level(logging.INFO, logger=LOG.name):
        assert scan(FakeSession(spend=[spend_page([refused])])) == []
    assert "refused, from a key with no other request" in caplog.text


def test_a_tool_call_counts_on_its_callers_record_and_is_never_one_of_its_own() -> None:
    rows = [
        row("r1", CI_TOKEN, "2026-10-28T10:00:00"),
        row(
            "r2",
            CI_TOKEN,
            "2026-10-28T10:30:00",
            call_type="call_mcp_tool",
            tool="github-get_issue",
            model="",
        ),
        row(
            "r3",
            SUPPORT_TOKEN,
            "2026-10-28T10:40:00",
            call_type="call_mcp_tool",
            tool="jira-search",
            model="",
        ),
    ]
    [ci] = scan(FakeSession(spend=[spend_page(rows)]))
    assert ci.name == "shared-ci"
    assert [t.name for t in ci.tools] == ["github-get_issue"]
    assert ci.last_seen == datetime(2026, 10, 28, 10, 30, tzinfo=timezone.utc)


def test_an_agent_to_agent_call_is_read_by_its_key_not_the_agent_it_called() -> None:
    a2a = row(
        "r1",
        CI_TOKEN,
        "2026-10-28T10:00:00",
        call_type="asend_message",
        agent_id=CLAIMED_AGENT,
    )
    [ci] = scan(FakeSession(spend=[spend_page([a2a])]))
    assert ci.creation_source.identity_basis is IdentityBasis.CREDENTIAL


def test_a_claimed_id_that_looks_like_a_key_is_read_as_its_sender() -> None:
    pasted = row(
        "r1",
        CLAIMING_TOKEN,
        "2026-10-28T10:00:00",
        agent_id="sk-live-pasted-into-header",
    )
    [record] = scan(FakeSession(spend=[spend_page([pasted])]))
    assert record.creation_source.identity_basis is IdentityBasis.CREDENTIAL
    assert "sk-live" not in record.external_id


def test_a_key_without_an_alias_is_named_by_its_team_and_short_hash() -> None:
    session = FakeSession(
        spend=[spend_page([row("r1", "9" * 64, "2026-10-28T10:00:00")])],
        keys=[keys_page([])],
    )
    [record] = scan(session)
    assert record.name == "platform 99999999"
    assert record.creation_source.observations.host_group == "platform"


def test_a_refused_key_list_warns_and_bound_keys_read_as_claimed(
    caplog: pytest.LogCaptureFixture,
) -> None:
    session = FakeSession(
        spend=[spend_page(HANDOFF_ROWS[:1])],
        keys=[FakeResponse(403, {"error": {"message": f"Received={MASKED}"}})],
    )
    with caplog.at_level(logging.WARNING, logger=LOG.name):
        [record] = scan(session)
    assert record.creation_source.identity_basis is IdentityBasis.CLAIMED_AGENT
    assert "refused the key list (HTTP 403)" in caplog.text
    assert MASKED not in caplog.text


def test_records_carry_the_caller_shape_and_their_detection() -> None:
    records = by_name(scan(FakeSession(spend=[spend_page(HANDOFF_ROWS)])))
    for record in records.values():
        source = record.creation_source
        assert isinstance(source, NetworkAgentCreationSource)
        assert source.vendor == "litellm"
        assert source.address.instance == INSTANCE
        assert source.address.scope is None
        assert source.address.query is None
        assert source.destinations == []
        assert record.runs_on is None
        assert source.observations.service_names == []
    assert (
        records["triage-agent"].creation_source.record_detection() is Detection.OBSERVED
    )
    assert records["shared-ci"].creation_source.record_detection() is Detection.OBSERVED
    assert (
        records[CLAIMED_AGENT].creation_source.record_detection() is Detection.INFERRED
    )


def test_output_satisfies_the_discovery_output_contract() -> None:
    records = scan(FakeSession(spend=[spend_page(HANDOFF_ROWS)]))
    check_batch(records, "LiteLLM")


def test_two_gateways_never_share_a_record() -> None:
    other = {"base_url": "https://litellm-eu.example.com"}
    session_a = FakeSession(spend=[spend_page(HANDOFF_ROWS[3:4])])
    session_b = FakeSession(spend=[spend_page(HANDOFF_ROWS[3:4])])
    [a] = scan(session_a)
    [b] = (
        LiteLLMConnector(
            client_factory=lambda s, log: LiteLLMClient(
                s, logger=log, session=_rehost(session_b), sleep=lambda _: None  # type: ignore[arg-type]
            ),
            now=lambda: NOW,
        )
        .scan(config(), 24, CREDS, other, LOG)
        .__next__()
    )
    assert a.external_id != b.external_id
    assert b.creation_source.address.instance == "litellm-eu.example.com"


def _rehost(session: FakeSession) -> Any:
    class Rehosted:
        def get(self, url: str, **kwargs: Any) -> Any:
            return session.get(
                url.replace("litellm-eu.example.com", INSTANCE), **kwargs
            )

    return Rehosted()


@pytest.mark.parametrize(
    ("url", "instance"),
    [
        ("https://LiteLLM.Example.com:443/", "litellm.example.com"),
        ("https://litellm.example.com:4400", "litellm.example.com:4400"),
        ("https://gw.example.com/litellm/", "gw.example.com/litellm"),
        ("https://[2001:db8::1]:4400", "[2001:db8::1]:4400"),
    ],
)
def test_the_gateway_instance_is_normalised(url: str, instance: str) -> None:
    assert gateway_instance(url) == instance


def test_zero_traffic_is_a_success_with_a_log_line(
    caplog: pytest.LogCaptureFixture,
) -> None:
    with caplog.at_level(logging.INFO, logger=LOG.name):
        assert scan(FakeSession()) == []
    assert "read no requests in the window" in caplog.text


# -- stopping --------------------------------------------------------------------------


def test_the_connector_accepts_a_stop_check() -> None:
    assert isinstance(LiteLLMConnector(), AcceptsStopCheck)


def test_a_stop_before_anything_sends_nothing() -> None:
    session = FakeSession()
    conn = connector(session)
    conn.stop_when(lambda: True)
    assert scan(session, conn=conn) == []
    assert session.calls == []


def test_a_stop_between_pages_reports_what_was_read() -> None:
    session = FakeSession(
        spend=[
            spend_page(full_page("a"), total_pages=2),
            spend_page(full_page("b"), total_pages=2),
        ]
    )
    conn = connector(session)

    def stop() -> bool:
        return any(c["path"] == "/spend/logs/v2" for c in session.calls)

    conn.stop_when(stop)
    [record] = scan(session, conn=conn)
    assert record.name == "shared-ci"
    assert [
        c["params"]["page"] for c in session.calls if c["path"] == "/spend/logs/v2"
    ] == [1]


# -- configuration ---------------------------------------------------------------------


@pytest.mark.parametrize(
    ("fields", "creds", "problem"),
    [
        ({}, CREDS, "missing required field(s): base_url"),
        (FIELDS, {}, "missing required field(s): api_key"),
        ({"base_url": "http://litellm.example.com"}, CREDS, "must be https"),
        (
            {"base_url": "https://admin:pw@litellm.example.com"},
            CREDS,
            "username or password",
        ),
        (
            {"base_url": "https://litellm.example.com:99999"},
            CREDS,
            "not a valid address",
        ),
        ({**FIELDS, "tls_verification": "strict"}, CREDS, "tls_verification"),
        ({**FIELDS, "tls_verification": "ca_only"}, CREDS, "has no ca_certificate"),
        (
            {**FIELDS, "tls_verification": "full", "ca_certificate": "not a pem"},
            CREDS,
            "not a PEM",
        ),
    ],
)
def test_bad_configuration_is_refused_before_anything_is_sent(
    fields: dict[str, str],
    creds: dict[str, str],
    problem: str,
) -> None:
    with pytest.raises(DiscoveryConfigurationError) as refused:
        settings = settings_from(creds, fields)
        LiteLLMClient(settings)
    assert problem in str(refused.value)
    assert failure_code(refused.value) is DiscoveryErrorCode.NOT_CONFIGURED
    assert "pw" not in str(refused.value)


# -- errors ----------------------------------------------------------------------------


def test_a_key_without_the_admin_viewer_role_is_permission_denied() -> None:
    session = FakeSession(
        probe=[FakeResponse(403, {"error": {"message": f"Received={MASKED}"}})]
    )
    with pytest.raises(LiteLLMError) as denied:
        scan(session)
    assert denied.value.status_code == 403
    assert failure_code(denied.value) is DiscoveryErrorCode.PERMISSION_DENIED
    assert "proxy_admin_viewer" in str(denied.value)
    assert MASKED not in str(denied.value)
    assert session.paths() == ["/user/list"]


def test_a_rejected_key_is_an_authentication_failure_without_its_fragment() -> None:
    session = FakeSession(
        probe=[
            FakeResponse(
                401, {"error": {"message": f"Authentication Error, Received={MASKED}"}}
            )
        ]
    )
    with pytest.raises(LiteLLMError) as rejected:
        scan(session)
    assert rejected.value.status_code == 401
    assert failure_code(rejected.value) is DiscoveryErrorCode.AUTHENTICATION_FAILED
    assert MASKED not in str(rejected.value)


def test_an_answer_that_is_not_the_proxys_is_the_vendors_error() -> None:
    session = FakeSession(
        spend=[FakeResponse(200, "<html>Sign in</html>", {"Content-Type": "text/html"})]
    )
    with pytest.raises(LiteLLMError) as wrong:
        scan(session)
    assert wrong.value.status_code == 200
    assert failure_code(wrong.value) is DiscoveryErrorCode.PROVIDER_ERROR


def test_a_200_without_data_is_the_vendors_error() -> None:
    with pytest.raises(LiteLLMError):
        scan(FakeSession(spend=[FakeResponse(200, {"rows": []})]))


def test_passing_failures_are_retried() -> None:
    session = FakeSession(
        spend=[
            FakeResponse(503, {}),
            requests.ConnectionError("reset"),
            spend_page(HANDOFF_ROWS[3:4]),
        ],
    )
    [record] = scan(session)
    assert record.name == "shared-ci"


def test_an_unreachable_proxy_stays_a_connection_error() -> None:
    session = FakeSession(probe=[requests.ConnectionError("refused")])
    with pytest.raises(requests.ConnectionError) as unreachable:
        scan(session)
    assert "unreachable" in str(unreachable.value)


def test_a_tls_failure_is_the_sources_to_fix() -> None:
    session = FakeSession(
        probe=[requests.exceptions.SSLError("certificate verify failed")]
    )
    with pytest.raises(DiscoveryConfigurationError) as refused:
        scan(session)
    assert isinstance(refused.value.__cause__, requests.exceptions.SSLError)
    assert "ca_certificate" in str(refused.value)


def test_the_scan_never_logs_the_key_aliases_or_error_text(
    caplog: pytest.LogCaptureFixture,
) -> None:
    with caplog.at_level(logging.DEBUG):
        scan(FakeSession(spend=[spend_page(HANDOFF_ROWS)]))
    for secret in (API_KEY, MASKED, CI_TOKEN, "shared-ci", "10.0.0.7", CLAIMED_AGENT):
        assert secret not in caplog.text
