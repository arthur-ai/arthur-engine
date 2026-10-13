---
name: discovery-source-gateway
description: The Network & Gateway source-class contract for Shadow Agent Discovery (an LLM gateway or proxy that callers route model traffic through reports which callers used which models; e.g. LiteLLM proxy, Kong AI Gateway, Cloudflare AI Gateway, Zscaler, Portkey). Use once a vendor is classified `network_gateway`, or when reviewing a gateway connector. The class does not exist in arthur-common yet; the first gateway vendor must add it (references/new-class.md). It says what a gateway record carries, how to connect, how lookback and Test Connection behave, and which tests prove it.
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
---

# Network & Gateway source class

This skill owns what is true of every **gateway** source in the engine (`ml-engine/`). Platform and UI steps are covered by Arthur's internal discovery integration process skill.

## 0. First check whether the class exists

```bash
grep -n 'NETWORK_GATEWAY' <arthur-common>/src/arthur_common/models/agent_governance_schemas.py
grep -rn 'network_gateway' ml-engine/src/ml_engine/discovery ml-engine/src/ml_engine/job_executors/fetch_discovered_agents_executor.py
```

**Decided (2026-10-13):** the wire value is `network_gateway`, because the Platform coverage summary and the UI's coverage card already use it. The contract (inferred detection, a required `identity_basis`, `client_addresses`) comes from an earlier, unmerged `network` class design, with one change: `REGISTERED_AGENT` means "bound to the request's credential", not "listed in the registry".

No hit: this vendor is the **new source class** case. Do `references/new-class.md` first (arthur-common PR, release, pins), and say in the request thread that the class contract below is a proposal the discovery owners must approve before the arthur-common PR merges. The wire value is fixed already: the Platform's coverage class and the UI's coverage card use `network_gateway`, so arthur-common `SourceClass` and the Platform catalog's class list must use the same string.

## 1. What a gateway source is

Applications and agents send their LLM calls through a gateway (a proxy holding provider keys, budgets and routing). The gateway authenticates each **caller** (virtual key, consumer, team, app token) and logs every request with the caller, the model and the time. A gateway source asks the gateway's admin/usage API "which callers sent model traffic in the lookback window?" and turns each caller into a record.

| If the vendor... | Class |
|---|---|
| exposes an admin or usage API listing callers and their requests (LiteLLM proxy, Kong **Konnect** `/v2/api-requests`, Cloudflare AI Gateway) | **network_gateway** |
| has an agent registry too | **network_gateway**, and emit registered agents as well as callers |
| is self-hosted with no usage API, so per-consumer AI traffic exists only in log-plugin output (self-hosted Kong Gateway's `ai` log object) | `discovery-source-siem`, a query over those logs |
| only ships its request logs to the customer's SIEM | `discovery-source-siem` (a query over those logs) |
| lists deployed agent resources but sees no traffic | `discovery-source-cloud` |

## 2. The record contract (proposed `NetworkGatewayAgentCreationSource`)

| Part | Rule | Why |
|---|---|---|
| Creation source | `NetworkGatewayAgentCreationSource(type="NETWORK_GATEWAY", identity_basis=...)`, `SOURCE_CLASS=NETWORK_GATEWAY`, `DETECTION=INFERRED`, `VISIBILITY_CEILING=LIMITED`, `OBSERVABLE_FIELDS={"client_addresses", "host_group", "assigned_user"}` | The gateway logs *requests*; grouping requests into an *agent* (by binding, claimed id, key or address) is inferred, as a SIEM infers from log fields. `identity_basis` is per record: one scan yields every strength |
| One record per | **agent seen in the window**, identified by the strongest signal the gateway gives, in this order: (1) **registered agent**: the request's agent id equals the agent the request's own credential is **bound** to. LiteLLM: row `agent_id` == the `agent_id` that `/key/list?return_full_object=true` reports for that key. A bound key stamps the id with no header. Do **not** grade against the agent registry (`/v1/agents`): a least-privilege viewer key gets 200 with an empty list even when agents exist (run on LiteLLM 1.104, 2026-10-13); (2) **claimed agent**: any other agent id on the request (`X-LiteLLM-Agent-Id` on an unbound key, a real agent's id sent from the wrong key, or an id the registry never issued); (3) the **credential** (LiteLLM virtual key, Konnect consumer); (4) the **client address**, only when nothing else exists. Record which one you used. A key that sent nothing in the window is not a record (configured is not seen) | Discovery reports agents that are running; a shared key hides several agents |
| `external_id` | The gateway's id for the caller (LiteLLM hashed key `token`, Kong consumer id). Never the raw key, never an alias (aliases are optional and reusable) | stability, secrecy |
| `name` | The caller's alias, else team alias + short id, else the id | non-blank |
| `last_seen` | The newest request time for that caller in the window | traffic-based |
| `llm_models` | Distinct provider-qualified models the caller actually **used** (`openai/gpt-4o`), sorted. A model the gateway refused (403, not in the key's allow-list) is left out, but the refused request still counts toward `last_seen` | the gateway knows this exactly |
| `address.instance` | The gateway host from the parsed URL (lowercase host, port unless 443, path kept; never the netloc). Put the helper in `discovery/network_gateway/records.py` (`gateway_instance`) so every gateway vendor shares it | same rule as SIEM `_instance`, which is private to each SIEM connector |
| `address.scope` | The caller's team / workspace / gateway id when the gateway has one, else `None` | groups callers |
| `address.resource_id` | the caller id (= `external_id`) | |
| `address.query` | Absent (no customer query) | |
| `observations` | `client_addresses` = the source addresses the record's requests came from (one key used from several hosts shows here); `host_group` = team/project/workspace alias; `assigned_user` = the key owner or end user the gateway attributes the call to (personal data: only what the gateway reports, never inferred) | within `OBSERVABLE_FIELDS` |
| `identity_basis` | `registered_agent`: request agent id == the agent the request's own credential is bound to. `claimed_agent`: any other agent id. `credential`: no agent id, grouped by key. `client_address`: no credential either (unauthenticated gateway or logs) | required, per record |
| `runs_on` / `platform` / `service_names` | Unset. A gateway does not know where the caller runs; a key alias is not a globally unique service name | see `discovery-source-cloud` §2 on `service_names` |

## 3. Connection and credentials

- Fields (the Platform catalog entry): `base_url` (non-sensitive, must be https); one admin credential (sensitive); `ca_certificate` + `tls_verification` (`full|ca_only|off`) because gateways are usually self-hosted behind private CAs (mark the vendor as one where `ca_only` requires a CA certificate). SaaS gateways with a fixed host (Cloudflare) drop `base_url` and TLS fields and take an account id instead.
- `SENSITIVE_FIELDS: ClassVar[frozenset[str]]` on the connector names the credential keys. Standalone mode refuses a connector without it (`tests/unit/standalone/test_discovery_config.py:test_every_registered_connector_declares_its_secrets`), and its contents must equal the catalog entry's secret fields. Nothing in this repo checks that equality; the process skill's cross-repo invariant check does.
- Engine: `https://` only, `discovery/address.py:address_problem`, `discovery/siem/tls.py:tls_session` (import it; do not copy), `allow_redirects=False`, `(connect, read)` timeouts summing under 120 s.
- **Least privilege:** a read-only admin role, never the master key, when the gateway has one (LiteLLM: a user with role `proxy_admin_viewer` and a key for it; Kong: an RBAC role with read on consumers and analytics). Name the role in the field `description` and the docs.
- Never read or log request/response bodies or prompts the gateway stored. Read only caller, team, model, time, status.

## 4. Lookback, paging, batching

- **Lookback is a real window over traffic**: `start = now - lookback_hours`, `end = now`, sent as the API's date filter. `lookback_hours <= 0` means "everything the gateway retains" (send the earliest date the API accepts, and log that the window is the gateway's retention).
- Usage APIs page (LiteLLM `/spend/logs/ui` `page`/`page_size`); follow pages until `total_pages`, cap pages, stop check between pages, retry idempotent GETs via `discovery/retry.py`. A stop between pages yields the partial aggregate with a warning.
- The stop check is `AcceptsStopCheck.stop_when(should_stop)`, implemented structurally (`job_executors/discovery_scan.py`; do not import the Protocol): handed in before `scan`, asked before each page, and when it answers True you `return` cleanly. Test Connection's 120 s deadline (`PREVIEW_DEADLINE_SECONDS` in `job_executors/discovery_source_test_executor.py`) relies on it.
- LiteLLM facts (1.104): dates are UTC `YYYY-MM-DD HH:MM:SS` (ISO gives 400); `page_size` max 1000 (5000 gives 422); `start_date=1970-01-01 00:00:00` is accepted for "all retained"; LiteLLM logs refused requests too, so probing with a wrong key adds rows.
- Records are aggregates over all pages (one per caller), so collect then yield in `BATCH_SIZE` slices; log completeness (requests read, callers found, pages capped) before the first yield.
- An admin inventory call (LiteLLM `/key/list`, Konnect consumers) is optional enrichment for names and owners; its failure (403 on a narrower role) is a warning, not a scan failure.

## 5. Errors and Test Connection

The shared error model, which both the scan and Test Connection read:

| Situation | Raise | Scan `failure_code` / Test Connection category |
|---|---|---|
| Missing field, `http://` URL, bad URL, bad TLS mode, CA that won't load | `DiscoveryConfigurationError` (a `ValueError`; a CA-load failure is raised `from None`, never chained to `ssl.SSLError`) | `not_configured` / `configuration` |
| Gateway answered non-2xx | `<Vendor>Error(msg, status_code=n)` with a hint naming the least-privilege role | 401 `authentication_failed` / `authentication`; 403 `permission_denied` / `authorization`; else `provider_error` / `vendor_error` |
| 200 whose body is not the usage shape (a login page, a proxy) | `<Vendor>Error(..., status_code=200)` | `provider_error` / `vendor_error` |
| TLS handshake refused | `DiscoveryConfigurationError(...) from exc` | `not_configured` / `configuration` |
| Host unreachable or timed out | the same type: `raise type(exc)(msg) from exc` | `provider_error` / `network` or `timeout` |

Error text names the field and the fix, never the value. Gateway-specific:

- Zero requests in the window is success with a job-log line ("no traffic in the last N hours"), not an error.
- Never put the vendor's auth error text in an exception or log: gateways echo masked key fragments (LiteLLM: `Received=wron****0000`). Keep only the error type/code and add your own hint. (The Elastic client's `_error_of` / `_reason_suffix`, which put the vendor's error reason into the exception text, would leak it; do not copy that part.)
- Some gateways answer **401, not 403**, to a valid key without the admin role. On LiteLLM 1.104 a non-admin key gets 401 on `/spend/logs/ui` but a clean **403 on `/user/list`**. So **call an admin-only list first** (LiteLLM `GET /user/list?page_size=1`) in both scan and Test Connection: the wrong role then reads as `permission_denied`, not `authentication_failed`. `/key/info` answers 200 for any key and cannot check the role.
- Requests the gateway refused because the *caller's* credential was bad (LiteLLM rows with `metadata.error_information.error_code == "401"`) are not callers: skip and count them.
- Failed requests (`status: failure`, e.g. a key calling a model it is not allowed) still prove the caller exists; count them toward `last_seen`.
- A request the gateway refused for the key's scope (403, model not allowed) is logged **without** the agent id, so it falls back to credential identity; do not let it create a separate agent.
- Usage rows are written in batches (LiteLLM: 20–60 s after the request). A Test Connection right after sending traffic can legitimately see none of it.

## 6. Files (arthur-engine `ml-engine/`; arthur-common and release steps in references/new-class.md)

Verified on 2026-10-12 against arthur-engine `dev` `4de52ab4` and arthur-common `main` `600a527f`. Paths drift: if a file named here is missing, find the symbol, then update this line. The process skill's cross-repo invariant check is the guard that the engine and Platform halves agree. The first gateway vendor (LiteLLM) was proven on a local stack on that date; it is not merged, so there is no gateway connector to copy yet.

- arthur-engine: `discovery/network_gateway/__init__.py` (class docstring), `discovery/network_gateway/records.py` (shared caller → record builder; the second gateway vendor reuses it), `discovery/network_gateway/<vendor>/{__init__,client,connector}.py`, `_CREATION_SOURCE_TYPES["network_gateway"] = "NETWORK_GATEWAY"` in `job_executors/fetch_discovered_agents_executor.py`, tests, standalone docs section.
- Registry: in `discovery/__init__.py:source_connectors()` import `VENDOR as <X>_VENDOR` and the connector class, add the dict entry, add both names to `__all__`.
- arthur-common and the engine repins: `references/new-class.md` (first vendor). Platform and UI: the internal process skill.

## 7. Checklist

- [ ] Class exists (or `new-class.md` done and approved); wire value `network_gateway` everywhere.
- [ ] One record per caller seen in the window; `external_id` is the gateway's caller id, never a secret.
- [ ] `llm_models` from actual traffic; no `service_names`, `runs_on`.
- [ ] Lookback is the request window; `<= 0` is full retention and logged.
- [ ] https, TLS fields, `allow_redirects=False`; least-privilege role documented and tested (the viewer role can scan).
- [ ] No prompt/response bodies read or logged.
- [ ] `SENSITIVE_FIELDS` == the catalog's secret fields.
- [ ] Platform catalog entry: class network_gateway, query language none, availability preview.

## 8. Tests that prove it

Registration; request shape (date window from lookback, auth header, `allow_redirects=False`, timeout sum < 120); paging to `total_pages` and the page cap; aggregation (two requests by one key → one record, both models, newest time); failed requests count; caller without alias named by team + id; `NetworkGatewayAgentCreationSource` address (instance normalisation, scope = team, resource_id = caller id); `check_batch` passes; zero traffic is a logged success; enrichment 403 is a warning; 401/403 carry `status_code`; malformed 200; http/userinfo/bad TLS mode refused; stop check before each page; key material and bodies never in `caplog`. Capture live bodies from a running gateway (the process skill's local end-to-end recipe shows how to run LiteLLM locally) and pin them inline.

## 9. Proving it end to end

Follow the process skill's local end-to-end recipe, LiteLLM section: run the gateway, send traffic with two keys (plus requests carrying `X-LiteLLM-Agent-Id`, one registered via `/v1/agents` and one not, an MCP tool call, and one key used from two client containers), configure the source in the UI with the viewer key, Test Connection, scan, and check the Agents tab and the coverage grid (Network & Gateway is no longer a "No sensor" blind spot).
