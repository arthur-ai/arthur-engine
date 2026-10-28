"""LiteLLM proxy's side of a DISCOVER_AGENTS scan.

Reads the proxy's request log (spend logs) over the scan's lookback and reports one
record per caller seen in it (`discovery.network.gateway_records`). THERE IS NO QUERY:
the catalog's query language is `none`, and a config's query is ignored.

WHICH CALLER A ROW PROVES, strongest first:

1. A row from a key bound to an agent (`agent_id` on the key in `/key/list`) is that
   agent, `registered_agent`. The proxy stamps the key's agent on the row whatever
   header the caller sent, and a `proxy_admin_viewer` key sees bindings even though
   `GET /v1/agents` answers it an empty list, so the binding is the registry evidence.
2. A row from an unbound key that carries an agent id (the `X-LiteLLM-Agent-Id`
   header) is that agent, `claimed_agent`: the caller said so and nothing checked it.
   UNLESS the id is bound to a DIFFERENT key. Then the caller is borrowing another
   agent's id, and the row folds into its own key's record instead; it is counted,
   never a record of the agent it named.
3. Any other row is its key, `credential`. Several agents sharing one key are one
   record. The key's id is the proxy's hash of it (`token`), never the key, never
   its alias.

ROWS THAT ARE NOT CALLERS:

* A request the proxy rejected because the key was invalid (`error_code` 401) is not
  a caller. Skipped and counted. A Test Connection made with a wrong key adds one.
* A refused request (a model the key may not use, a budget) is logged without the
  agent id. It joins its key's record when that record exists, moves `last_seen`, and
  adds no model. It never makes a record of its own.
* An MCP tool call counts on its caller's record, `last_seen` and the tool, and is
  never a record of its own. Without a caller record it is skipped and counted.
* An A2A call (`asend_message`) carries the CALLED agent's id, so it is read by its key.

A key with no requests in the window is not a record. When `/key/list` is refused
(enrichment is optional), bindings are unknown: a bound key's rows read as claimed
agents and a borrowed id cannot be told, which the job log says.
"""

import logging
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, ClassVar, Iterator, Mapping, Optional, Sequence

from arthur_client.api_bindings import DiscoverySourceConfigSpec
from arthur_common.models.agent_discovery_schemas import DiscoveredAgentRecord
from arthur_common.models.agent_governance_schemas import (
    RAW_CREDENTIAL_PREFIXES,
    IdentityBasis,
    NetworkCallerKind,
)

from discovery.address import address_problem
from discovery.network.gateway_records import (
    Caller,
    CallerKey,
    GatewayCallers,
    gateway_instance,
)
from discovery.network.litellm.client import (
    EARLIEST,
    LiteLLMClient,
    LiteLLMError,
    LiteLLMSettings,
    VirtualKey,
)
from discovery.siem.tls import parse_tls_verification
from job_executors.discovery_scan import DiscoveryConfigurationError

VENDOR = "litellm"

BASE_URL_FIELD = "base_url"
API_KEY_FIELD = "api_key"
CA_CERTIFICATE_FIELD = "ca_certificate"
TLS_VERIFICATION_FIELD = "tls_verification"

# Request log rows read per scan, across pages. A capped scan says so before its
# first batch.
MAX_ROWS = 250_000
BATCH_SIZE = 500

_MCP_CALL_TYPES = frozenset({"call_mcp_tool", "list_mcp_tools"})
_A2A_CALL_TYPE = "asend_message"
_INVALID_KEY_CODE = "401"

ClientFactory = Callable[[LiteLLMSettings, logging.Logger], LiteLLMClient]


def _default_client(settings: LiteLLMSettings, logger: logging.Logger) -> LiteLLMClient:
    return LiteLLMClient(settings, logger=logger)


@dataclass(frozen=True)
class _Row:
    """What one request log row says, read once."""

    request_id: str
    token: str
    when: datetime
    succeeded: bool
    invalid_key: bool
    claimed_agent: Optional[str]
    call_type: str
    model: Optional[str]
    tool: Optional[str]
    key_alias: Optional[str]
    team_alias: Optional[str]


@dataclass
class _Counts:
    read: int = 0
    duplicate: int = 0
    unreadable: int = 0
    invalid_key: int = 0
    no_key: int = 0
    borrowed_ids: int = 0
    refused_without_caller: int = 0
    tool_calls_without_caller: int = 0


class LiteLLMConnector:
    """Implements `job_executors.discovery_scan.DiscoverySourceConnector` and
    `AcceptsStopCheck` (structurally; the Protocols are not imported).

    Holds one scan's stop check, which is safe only because a connector is built fresh
    for every scan -- see `DiscoveryConnectorFactory`.
    """

    SENSITIVE_FIELDS: ClassVar[frozenset[str]] = frozenset({API_KEY_FIELD})

    def __init__(
        self,
        client_factory: ClientFactory = _default_client,
        now: Callable[[], float] = time.time,
        max_rows: int = MAX_ROWS,
    ) -> None:
        self._client_factory = client_factory
        self._now = now
        self._max_rows = max_rows
        self._should_stop: Callable[[], bool] = lambda: False

    def stop_when(self, should_stop: Callable[[], bool]) -> None:
        self._should_stop = should_stop

    def scan(
        self,
        config: DiscoverySourceConfigSpec,
        lookback_hours: int,
        credentials: Mapping[str, Optional[str]],
        source_fields: Mapping[str, str],
        logger: logging.Logger,
    ) -> Iterator[Sequence[DiscoveredAgentRecord]]:
        """`logger` is the JOB's, so what this reports reaches the Platform job log.

        A lookback of 0 reads everything the proxy still retains.
        """
        settings = settings_from(credentials, source_fields)
        instance = gateway_instance(settings.base_url)
        if (config.query or "").strip():
            logger.warning(
                "LiteLLM sources have no query; the source config's query is ignored.",
            )
        # Naive UTC, which is how the proxy reads start_date and end_date.
        end = datetime.fromtimestamp(self._now(), tz=timezone.utc).replace(tzinfo=None)
        start = (
            end - timedelta(hours=lookback_hours) if lookback_hours > 0 else EARLIEST
        )
        logger.info(
            "LiteLLM scan starting against %s, lookback %s",
            instance,
            (
                f"{lookback_hours}h"
                if lookback_hours > 0
                else "everything the proxy retains"
            ),
        )
        if self._should_stop():
            logger.info("LiteLLM scan stopped before anything was sent")
            return

        client = self._client_factory(settings, logger)
        # First, so a key without the admin viewer role reads as permission denied.
        client.probe_admin()
        keys = self._keys(client, logger)
        bound_agents = {k.agent_id: k.token for k in keys.values() if k.agent_id}

        callers = GatewayCallers()
        counts = _Counts()
        seen: set[str] = set()
        deferred: list[tuple[CallerKey, _Row]] = []
        capped = False
        for page in client.spend_pages(start, end, self._should_stop):
            for raw in page[: self._max_rows - counts.read]:
                counts.read += 1
                row = _row_of(raw)
                if row is None:
                    counts.unreadable += 1
                    continue
                if row.request_id in seen:
                    counts.duplicate += 1
                    continue
                seen.add(row.request_id)
                if row.invalid_key:
                    counts.invalid_key += 1
                    continue
                if not row.token or row.token.startswith(RAW_CREDENTIAL_PREFIXES):
                    counts.no_key += 1
                    continue
                key, borrowed = _caller_key(row, keys.get(row.token), bound_agents)
                if row.succeeded and row.call_type not in _MCP_CALL_TYPES:
                    counts.borrowed_ids += borrowed
                    caller = callers.caller(key)
                    _fold(caller, row, keys.get(row.token))
                    if row.model:
                        caller.models.add(row.model)
                else:
                    deferred.append((key, row))
            if counts.read >= self._max_rows:
                capped = True
                break

        # Refused requests and tool calls only join a caller already seen.
        for key, row in deferred:
            found = callers.get(key)
            if found is None:
                if row.call_type in _MCP_CALL_TYPES:
                    counts.tool_calls_without_caller += 1
                else:
                    counts.refused_without_caller += 1
                continue
            found.seen(row.when)
            if row.tool and row.succeeded:
                found.tools.add(row.tool)

        records = callers.records(VENDOR, instance)
        # Reported before the first batch is handed over, so a publish that fails part
        # way cannot leave a capped answer unannounced.
        self._report(logger, callers, counts, capped)
        for offset in range(0, len(records), BATCH_SIZE):
            yield records[offset : offset + BATCH_SIZE]

    def _keys(
        self,
        client: LiteLLMClient,
        logger: logging.Logger,
    ) -> dict[str, VirtualKey]:
        """The proxy's keys by hash. Enrichment: a refusal is a warning, not a failure."""
        keys: dict[str, VirtualKey] = {}
        try:
            for page in client.keys(self._should_stop):
                keys.update((k.token, k) for k in page)
        except LiteLLMError as exc:
            if exc.status_code not in (401, 403):
                raise
            logger.warning(
                "LiteLLM refused the key list (HTTP %s), so agent bindings are "
                "unknown: requests from a key bound to an agent read as claimed "
                "agents. Give the key's user the proxy_admin_viewer role.",
                exc.status_code,
            )
        return keys

    def _report(
        self,
        logger: logging.Logger,
        callers: GatewayCallers,
        counts: _Counts,
        capped: bool,
    ) -> None:
        """How complete the answer is and what it found, in counts only: never a key,
        an alias or an agent id from the log."""
        by_basis = callers.by_basis()
        logger.info(
            "LiteLLM scan read %s request log row(s): %s caller record(s) "
            "(%s registered agent(s), %s claimed agent id(s), %s key(s))",
            counts.read,
            len(callers),
            by_basis.get(IdentityBasis.REGISTERED_AGENT, 0),
            by_basis.get(IdentityBasis.CLAIMED_AGENT, 0),
            by_basis.get(IdentityBasis.CREDENTIAL, 0),
        )
        skipped = {
            "rejected for an invalid key": counts.invalid_key,
            "without a usable key": counts.no_key,
            "refused, from a key with no other request": counts.refused_without_caller,
            "MCP tool calls without a caller": counts.tool_calls_without_caller,
            "unreadable": counts.unreadable,
            "repeated across pages": counts.duplicate,
        }
        for reason, count in skipped.items():
            if count:
                logger.info("LiteLLM: %s row(s) skipped: %s", count, reason)
        if counts.borrowed_ids:
            logger.warning(
                "LiteLLM: %s request(s) sent an agent id bound to a different key; "
                "each was counted on its own key's record, not the agent's.",
                counts.borrowed_ids,
            )
        if capped:
            logger.warning(
                "LiteLLM scan stopped at its %s-row cap, so later requests were not "
                "read. Shorten the lookback window.",
                self._max_rows,
            )
        elif self._should_stop():
            logger.info(
                "LiteLLM scan stopped early after %s row(s); records cover what was "
                "read",
                counts.read,
            )
        if counts.read == 0:
            logger.info(
                "LiteLLM scan read no requests in the window. The proxy writes its "
                "request log 20-60 s after each request, and only with a database "
                "configured.",
            )


def _caller_key(
    row: _Row,
    key: Optional[VirtualKey],
    bound_agents: Mapping[str, str],
) -> tuple[CallerKey, bool]:
    """The record a row belongs to, and whether it borrowed another key's agent id."""
    if key is not None and key.agent_id:
        return (
            CallerKey(
                NetworkCallerKind.AGENT_ID,
                IdentityBasis.REGISTERED_AGENT,
                key.agent_id,
            ),
            False,
        )
    claim = row.claimed_agent if row.call_type != _A2A_CALL_TYPE else None
    if claim and not claim.startswith(RAW_CREDENTIAL_PREFIXES):
        owner = bound_agents.get(claim)
        if owner is None:
            return (
                CallerKey(
                    NetworkCallerKind.AGENT_ID,
                    IdentityBasis.CLAIMED_AGENT,
                    claim,
                ),
                False,
            )
        borrowed = owner != row.token
    else:
        borrowed = False
    return (
        CallerKey(NetworkCallerKind.VIRTUAL_KEY, IdentityBasis.CREDENTIAL, row.token),
        borrowed,
    )


def _fold(caller: Caller, row: _Row, key: Optional[VirtualKey]) -> None:
    caller.seen(row.when)
    if caller.key.basis is not IdentityBasis.CLAIMED_AGENT:
        caller.alias = caller.alias or (key.alias if key else None) or row.key_alias
    caller.team_alias = (
        caller.team_alias or (key.team_alias if key else None) or row.team_alias
    )


def _row_of(raw: Mapping[str, Any]) -> Optional[_Row]:
    """A request log row, or None when it names no request or no time."""
    request_id = _text(raw.get("request_id"))
    when = _time(raw.get("startTime"))
    if request_id is None or when is None:
        return None
    metadata = raw.get("metadata")
    metadata = metadata if isinstance(metadata, dict) else {}
    error = metadata.get("error_information")
    error_code = error.get("error_code") if isinstance(error, dict) else None
    status = _text(raw.get("status")) or _text(metadata.get("status"))
    return _Row(
        request_id=request_id,
        token=_text(raw.get("api_key")) or "",
        when=when,
        succeeded=status in (None, "success"),
        invalid_key=str(error_code).strip() == _INVALID_KEY_CODE,
        claimed_agent=_text(raw.get("agent_id")) or _text(metadata.get("agent_id")),
        call_type=_text(raw.get("call_type")) or "",
        model=_served_model(raw),
        tool=_text(raw.get("mcp_namespaced_tool_name")),
        key_alias=_text(metadata.get("user_api_key_alias")),
        team_alias=_text(metadata.get("user_api_key_team_alias")),
    )


def _served_model(raw: Mapping[str, Any]) -> Optional[str]:
    """The model as `<provider>/<model>`, as the proxy routed it."""
    model = _text(raw.get("model")) or _text(raw.get("model_group"))
    if model is None:
        return None
    provider = _text(raw.get("custom_llm_provider"))
    if provider and not model.lower().startswith(f"{provider.lower()}/"):
        return f"{provider}/{model}"
    return model


def _time(value: Any) -> Optional[datetime]:
    """A row time as aware UTC. The proxy stores naive UTC."""
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _text(value: Any) -> Optional[str]:
    if not isinstance(value, str):
        return None
    return value.strip() or None


def settings_from(
    credentials: Mapping[str, Optional[str]],
    source_fields: Mapping[str, str],
) -> LiteLLMSettings:
    """The proxy's address and trust from the source's fields, the key from its
    secrets. `base_url` is not a secret, so a failure can name the host."""
    url = (source_fields.get(BASE_URL_FIELD) or "").strip()
    api_key = (credentials.get(API_KEY_FIELD) or "").strip()
    missing = [
        name
        for name, value in ((BASE_URL_FIELD, url), (API_KEY_FIELD, api_key))
        if not value
    ]
    if missing:
        raise DiscoveryConfigurationError(
            f"LiteLLM source is missing required field(s): {', '.join(missing)}. "
            f"base_url is a source field; api_key is a secret.",
        )
    if not url.lower().startswith("https://"):
        # The key travels in a header. Over http it is in cleartext, and this is the
        # only place it can be refused before it is sent.
        raise DiscoveryConfigurationError(
            f"LiteLLM base_url must be https, got "
            f"{url.split('://', 1)[0] or url!r}. The API key travels in a request header.",
        )
    problem = address_problem(url)
    if problem:
        raise DiscoveryConfigurationError(
            f"LiteLLM base_url {problem}. Expected https://host or https://host:port.",
        )
    return LiteLLMSettings(
        base_url=url,
        api_key=api_key,
        ca_certificate=(source_fields.get(CA_CERTIFICATE_FIELD) or "").strip() or None,
        tls_verification=parse_tls_verification(
            source_fields.get(TLS_VERIFICATION_FIELD),
            "LiteLLM",
        ),
    )
